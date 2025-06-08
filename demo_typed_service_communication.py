#!/usr/bin/env python3
"""
MSFW Type-safe Service Communication Demo
========================================

Demonstrates advanced type-safe service communication using decorators:

1. Type-safe service calls with @service_call
2. Resilience patterns with decorators  
3. Service interfaces and CRUD operations
4. Error handling and validation
5. Real-world microservice patterns
"""

import asyncio
from typing import List, Optional
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field
from msfw import (
    HTTPMethod, ServiceCallResult, ServiceCallConfig,
    TypedServiceError, ServiceValidationError,
    service_call, retry_on_failure, circuit_breaker, 
    health_check, cached_service_call, service_interface
)


# Domain Models
class User(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool = True
    created_at: str


class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')


class UpdateUserRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    is_active: Optional[bool] = None


class Product(BaseModel):
    id: int
    name: str
    price: float
    category: str
    in_stock: bool


class OrderItem(BaseModel):
    product_id: int
    quantity: int
    price: float


class Order(BaseModel):
    id: int
    user_id: int
    items: List[OrderItem]
    total_amount: float
    status: str
    created_at: str


class CreateOrderRequest(BaseModel):
    user_id: int
    items: List[OrderItem]


# Service Interfaces with Type Safety
@service_interface("user-service", "/api/v1")
class UserService:
    """Type-safe user service interface."""
    
    @retry_on_failure(max_attempts=3, delay=0.5)
    @service_call("user-service", HTTPMethod.GET, "/users/{user_id}")
    async def get_user(self, user_id: int) -> User:
        """Get user by ID with automatic retries."""
        pass
    
    @service_call("user-service", HTTPMethod.POST, "/users")
    async def create_user(self, user_data: CreateUserRequest) -> User:
        """Create a new user."""
        pass
    
    @service_call("user-service", HTTPMethod.PUT, "/users/{user_id}")
    async def update_user(self, user_id: int, user_data: UpdateUserRequest) -> User:
        """Update user data."""
        pass
    
    @service_call("user-service", HTTPMethod.DELETE, "/users/{user_id}")
    async def delete_user(self, user_id: int) -> dict:
        """Delete a user."""
        pass
    
    @cached_service_call(ttl=300.0)  # Cache for 5 minutes
    @service_call("user-service", HTTPMethod.GET, "/users")
    async def list_users(self, limit: int = 10, offset: int = 0) -> List[User]:
        """List users with caching."""
        pass


@service_interface("product-service", "/api/v1")
class ProductService:
    """Type-safe product service interface."""
    
    @circuit_breaker(failure_threshold=5, recovery_timeout=60.0)
    @service_call("product-service", HTTPMethod.GET, "/products/{product_id}")
    async def get_product(self, product_id: int) -> Product:
        """Get product with circuit breaker protection."""
        pass
    
    @cached_service_call(ttl=600.0)  # Cache for 10 minutes
    @service_call("product-service", HTTPMethod.GET, "/categories/{category}/products")
    async def get_products_by_category(self, category: str, limit: int = 20) -> List[Product]:
        """Get products by category with caching."""
        pass
    
    @health_check(interval=30.0, timeout=5.0, failure_threshold=3)
    @service_call("product-service", HTTPMethod.GET, "/products/search")
    async def search_products(self, query: str, category: Optional[str] = None) -> List[Product]:
        """Search products with health monitoring."""
        pass


@service_interface("order-service", "/api/v1")
class OrderService:
    """Type-safe order service interface."""
    
    @retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0)
    @circuit_breaker(failure_threshold=3, recovery_timeout=30.0)
    @service_call("order-service", HTTPMethod.POST, "/orders")
    async def create_order(self, order_data: CreateOrderRequest) -> Order:
        """Create order with retry and circuit breaker protection."""
        pass
    
    @service_call("order-service", HTTPMethod.GET, "/orders/{order_id}")
    async def get_order(self, order_id: int) -> Order:
        """Get order by ID."""
        pass
    
    @service_call("order-service", HTTPMethod.GET, "/users/{user_id}/orders")
    async def get_user_orders(self, user_id: int, status: Optional[str] = None) -> List[Order]:
        """Get user's orders."""
        pass


# Business Logic with Type-safe Service Communication
class ECommerceService:
    """Business logic using type-safe service communication."""
    
    def __init__(self):
        self.user_service = UserService()
        self.product_service = ProductService()
        self.order_service = OrderService()
    
    async def create_complete_order(
        self, 
        user_id: int, 
        product_items: List[tuple[int, int]]  # (product_id, quantity)
    ) -> Order:
        """Create a complete order with validation and error handling."""
        
        try:
            # 1. Validate user exists
            user = await self.user_service.get_user(user_id)
            if not user.is_active:
                raise ValueError(f"User {user_id} is not active")
            
            # 2. Get product details and validate availability
            order_items = []
            total_amount = 0.0
            
            for product_id, quantity in product_items:
                product = await self.product_service.get_product(product_id)
                
                if not product.in_stock:
                    raise ValueError(f"Product {product_id} is out of stock")
                
                item_total = product.price * quantity
                order_items.append(OrderItem(
                    product_id=product_id,
                    quantity=quantity,
                    price=product.price
                ))
                total_amount += item_total
            
            # 3. Create the order
            create_request = CreateOrderRequest(
                user_id=user_id,
                items=order_items
            )
            
            order = await self.order_service.create_order(create_request)
            
            print(f"✅ Order {order.id} created successfully for user {user.name}")
            print(f"   Total amount: ${order.total_amount}")
            print(f"   Items: {len(order.items)}")
            
            return order
            
        except TypedServiceError as e:
            print(f"❌ Service error: {e}")
            raise
        except ServiceValidationError as e:
            print(f"❌ Validation error: {e.validation_errors}")
            raise
        except ValueError as e:
            print(f"❌ Business logic error: {e}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            raise
    
    async def get_user_profile_with_orders(self, user_id: int) -> dict:
        """Get complete user profile with order history."""
        
        try:
            # Get user and orders concurrently
            user_task = self.user_service.get_user(user_id)
            orders_task = self.order_service.get_user_orders(user_id)
            
            user, orders = await asyncio.gather(user_task, orders_task)
            
            # Calculate order statistics
            total_orders = len(orders)
            total_spent = sum(order.total_amount for order in orders)
            
            return {
                "user": user,
                "order_summary": {
                    "total_orders": total_orders,
                    "total_spent": total_spent,
                    "recent_orders": orders[:5]  # Last 5 orders
                }
            }
            
        except Exception as e:
            print(f"❌ Error getting user profile: {e}")
            raise


# Demo Functions
async def demo_basic_service_calls():
    """Demo basic type-safe service calls."""
    print("🔧 Demo: Basic Type-safe Service Calls")
    print("=" * 60)
    
    user_service = UserService()
    
    # This would normally work with real services
    print("📝 Creating user with validation...")
    try:
        # This demonstrates type safety - IDE will show auto-completion
        create_request = CreateUserRequest(
            name="John Doe",
            email="john@example.com"
        )
        
        # This call is type-safe and will validate the request
        print(f"   Request: {create_request}")
        print("   ✅ Request model validation passed")
        
        # The decorator would handle the actual service call
        print("   🔄 Would call: POST /api/v1/users")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()


async def demo_validation_errors():
    """Demo validation error handling."""
    print("🔍 Demo: Validation Error Handling")
    print("=" * 60)
    
    try:
        # Invalid email format
        invalid_request = CreateUserRequest(
            name="",  # Too short
            email="invalid-email"  # Invalid format
        )
        print(f"❌ This shouldn't happen: {invalid_request}")
        
    except Exception as e:
        print(f"✅ Validation caught invalid data: {type(e).__name__}")
        print(f"   Details: {str(e)[:100]}...")
    
    print()


async def demo_decorator_combinations():
    """Demo combining multiple decorators."""
    print("🛠️  Demo: Decorator Combinations")
    print("=" * 60)
    
    print("🔄 Service with retry + circuit breaker:")
    print("   @retry_on_failure(max_attempts=3)")
    print("   @circuit_breaker(failure_threshold=5)")
    print("   @service_call('order-service', HTTPMethod.POST, '/orders')")
    print("   async def create_order(order_data: CreateOrderRequest) -> Order:")
    print()
    
    print("💾 Service with caching + health checks:")
    print("   @cached_service_call(ttl=300.0)")
    print("   @health_check(interval=30.0)")
    print("   @service_call('product-service', HTTPMethod.GET, '/products')")
    print("   async def list_products() -> List[Product]:")
    print()
    
    print("✅ All decorators work together seamlessly!")
    print()


async def demo_service_interfaces():
    """Demo service interface patterns."""
    print("📚 Demo: Service Interface Patterns")
    print("=" * 60)
    
    print("🏗️  Service Interface Example:")
    print()
    print("@service_interface('user-service', '/api/v1')")
    print("class UserService:")
    print("    @service_call('user-service', HTTPMethod.GET, '/users/{user_id}')")
    print("    async def get_user(self, user_id: int) -> User:")
    print("        pass")
    print()
    print("    @service_call('user-service', HTTPMethod.POST, '/users')")
    print("    async def create_user(self, user_data: CreateUserRequest) -> User:")
    print("        pass")
    print()
    
    print("✅ Benefits:")
    print("   • Type safety with IDE autocompletion")
    print("   • Automatic request/response validation")
    print("   • Centralized service configuration")
    print("   • Consistent error handling")
    print("   • Built-in resilience patterns")
    print()


async def demo_business_logic():
    """Demo business logic with type-safe services."""
    print("💼 Demo: Business Logic with Type-safe Services")
    print("=" * 60)
    
    ecommerce = ECommerceService()
    
    print("🛒 Creating complete order flow:")
    print("   1. Validate user exists and is active")
    print("   2. Check product availability and prices")
    print("   3. Calculate total amount")
    print("   4. Create order with validation")
    print()
    
    # This would work with real services
    print("📦 Sample order creation:")
    print("   User ID: 123")
    print("   Products: [(1, 2), (3, 1)]  # (product_id, quantity)")
    print("   ✅ All type checking happens at compile time!")
    print()
    
    print("🔍 Benefits of type-safe approach:")
    print("   • Catch errors early (IDE + mypy)")
    print("   • Self-documenting APIs")
    print("   • Automatic request validation")
    print("   • Consistent error handling")
    print("   • Better testing and mocking")
    print()


async def demo_error_handling_patterns():
    """Demo advanced error handling patterns."""
    print("⚠️  Demo: Advanced Error Handling Patterns")
    print("=" * 60)
    
    print("🔧 Error Types in MSFW SDK:")
    print()
    
    print("1. TypedServiceError:")
    print("   - Service communication failures")
    print("   - Network timeouts")
    print("   - Service unavailable")
    print()
    
    print("2. ServiceValidationError:")
    print("   - Request/response validation failures") 
    print("   - Detailed field-level errors")
    print("   - Pydantic integration")
    print()
    
    print("3. Circuit Breaker Errors:")
    print("   - Service overload protection")
    print("   - Automatic recovery")
    print("   - Configurable thresholds")
    print()
    
    print("✅ All errors are type-safe and include rich context!")
    print()


@asynccontextmanager
async def demo_context():
    """Demo context manager."""
    print("🎯 MSFW Type-safe Service Communication")
    print("=" * 70)
    print("✨ Type-safe decorators with @service_call")
    print("✨ Resilience patterns (retry, circuit breaker)")
    print("✨ Service interfaces and CRUD operations")
    print("✨ Validation and error handling")
    print("✨ Real-world microservice patterns")
    print()
    
    try:
        yield
    finally:
        print("🧹 Demo completed")


async def main():
    """Run type-safe service communication demos."""
    async with demo_context():
        await demo_basic_service_calls()
        await demo_validation_errors()
        await demo_decorator_combinations()
        await demo_service_interfaces()
        await demo_business_logic()
        await demo_error_handling_patterns()
        
        print("🎉 Type-safe Service Communication Summary:")
        print("   • Strong typing with Pydantic models ✅")
        print("   • IDE autocompletion and error detection ✅")
        print("   • Automatic request/response validation ✅")
        print("   • Resilience patterns with decorators ✅")
        print("   • Clean service interface definitions ✅")
        print("   • Comprehensive error handling ✅")
        print("   • Production-ready patterns ✅")
        print()
        print("🚀 Ready for type-safe microservice development!")


if __name__ == "__main__":
    asyncio.run(main()) 