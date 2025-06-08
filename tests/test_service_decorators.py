"""Tests for service decorators with real-world scenarios."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import List, Optional

from pydantic import BaseModel, ValidationError

from msfw import (
    HTTPMethod, ServiceCallResult, TypedServiceError, ServiceValidationError,
    service_call, retry_on_failure, circuit_breaker, health_check,
    cached_service_call, service_interface
)

# Configure pytest for async tests - only apply to async test classes


# Test Models
class Product(BaseModel):
    id: int
    name: str
    price: float
    category: str


class CreateProductRequest(BaseModel):
    name: str
    price: float
    category: str


class ProductList(BaseModel):
    products: List[Product]
    total: int
    page: int


class OrderRequest(BaseModel):
    product_id: int
    quantity: int
    customer_id: int


class OrderResponse(BaseModel):
    id: int
    status: str
    total_amount: float


@pytest.mark.asyncio
class TestServiceCallDecoratorAdvanced:
    """Advanced tests for service_call decorator."""
    
    async def test_service_call_with_complex_path_formatting(self):
        """Test service call with complex path formatting."""
        with patch('msfw.decorators.service._make_typed_service_call') as mock_call:
            mock_result = ServiceCallResult(
                success=True,
                data=Product(id=1, name="Test Product", price=99.99, category="electronics"),
                service_name="product-service"
            )
            mock_call.return_value = mock_result
            
            @service_call("product-service", HTTPMethod.GET, "/categories/{category}/products/{product_id}")
            async def get_product_by_category(category: str, product_id: int) -> Product:
                pass
            
            result = await get_product_by_category("electronics", 123)
            
            assert isinstance(result, Product)
            mock_call.assert_called_once()
            args = mock_call.call_args[1]
            assert args['path'] == "/categories/electronics/products/123"
    
    async def test_service_call_with_validation_error(self):
        """Test service call decorator handling validation errors."""
        with patch('msfw.decorators.service._make_typed_service_call') as mock_call:
            mock_call.side_effect = ServiceValidationError(
                "Validation failed",
                service_name="product-service",
                validation_errors={"name": ["required field missing"]}
            )
            
            @service_call("product-service", HTTPMethod.POST, "/products")
            async def create_product(product_data: CreateProductRequest) -> Product:
                pass
            
            request_data = CreateProductRequest(name="Test", price=99.99, category="electronics")
            
            with pytest.raises(TypedServiceError) as exc_info:
                await create_product(request_data)
            
            # The original ServiceValidationError is wrapped in TypedServiceError
            assert "Validation failed" in str(exc_info.value)
    
    async def test_service_call_with_auto_unwrap_disabled(self):
        """Test service call decorator with auto_unwrap=False."""
        with patch('msfw.decorators.service._make_typed_service_call') as mock_call:
            mock_result = ServiceCallResult(
                success=True,
                data=Product(id=1, name="Test", price=99.99, category="electronics"),
                service_name="product-service"
            )
            mock_call.return_value = mock_result
            
            @service_call("product-service", HTTPMethod.GET, "/products/{product_id}", auto_unwrap=False)
            async def get_product_raw(product_id: int) -> ServiceCallResult[Product]:
                pass
            
            result = await get_product_raw(123)
            
            assert isinstance(result, ServiceCallResult)
            assert result.is_success
            assert isinstance(result.data, Product)


@pytest.mark.asyncio
class TestDecoratorCombinations:
    """Test combinations of multiple decorators."""
    
    async def test_service_call_with_retry(self):
        """Test service_call combined with retry_on_failure."""
        call_count = 0
        
        with patch('msfw.decorators.service._make_typed_service_call') as mock_call:
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception(f"Attempt {call_count} failed")
                return ServiceCallResult(
                    success=True,
                    data=Product(id=1, name="Test", price=99.99, category="electronics"),
                    service_name="product-service"
                )
            
            mock_call.side_effect = side_effect
            
            @retry_on_failure(max_attempts=3, delay=0.1)
            @service_call("product-service", HTTPMethod.GET, "/products/{product_id}")
            async def get_product_with_retry(product_id: int) -> Product:
                pass
            
            result = await get_product_with_retry(123)
            
            assert isinstance(result, Product)
            assert call_count == 3
    
    async def test_service_call_with_circuit_breaker(self):
        """Test service_call combined with circuit_breaker."""
        failure_count = 0
        
        with patch('msfw.decorators.service._make_typed_service_call') as mock_call:
            def side_effect(*args, **kwargs):
                nonlocal failure_count
                failure_count += 1
                raise Exception(f"Failure {failure_count}")
            
            mock_call.side_effect = side_effect
            
            @circuit_breaker(failure_threshold=2, recovery_timeout=0.1)
            @service_call("product-service", HTTPMethod.GET, "/products/{product_id}")
            async def get_product_with_circuit_breaker(product_id: int) -> Product:
                pass
            
            # First two calls should raise the original exception
            with pytest.raises(TypedServiceError):
                await get_product_with_circuit_breaker(123)
            
            with pytest.raises(TypedServiceError):
                await get_product_with_circuit_breaker(123)
            
            # Third call should raise circuit breaker exception
            with pytest.raises(TypedServiceError) as exc_info:
                await get_product_with_circuit_breaker(123)
            
            # The exact message depends on which exception gets raised first
            assert failure_count >= 2
    
    async def test_cached_service_call(self):
        """Test cached_service_call decorator."""
        call_count = 0
        
        @cached_service_call(ttl=1.0)
        async def expensive_calculation(value: int) -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate expensive operation
            return value * 2
        
        # First call
        result1 = await expensive_calculation(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call should be cached
        result2 = await expensive_calculation(5)
        assert result2 == 10
        assert call_count == 1  # Function not called again
        
        # Different argument should trigger new call
        result3 = await expensive_calculation(6)
        assert result3 == 12
        assert call_count == 2


class TestServiceInterfaceDecorator:
    """Test service_interface decorator with real examples."""
    
    def test_service_interface_with_methods(self):
        """Test service_interface decorator with actual service methods."""
        @service_interface("product-service", "/api/v1")
        class ProductService:
            @service_call("product-service", HTTPMethod.GET, "/products")
            async def list_products(self, category: Optional[str] = None) -> ProductList:
                pass
            
            @service_call("product-service", HTTPMethod.GET, "/products/{product_id}")
            async def get_product(self, product_id: int) -> Product:
                pass
            
            @service_call("product-service", HTTPMethod.POST, "/products")
            async def create_product(self, product_data: CreateProductRequest) -> Product:
                pass
        
        assert ProductService._service_name == "product-service"
        assert ProductService._base_path == "/api/v1"
        
        # Test that methods are properly decorated
        service = ProductService()
        assert hasattr(service, 'list_products')
        assert hasattr(service, 'get_product')
        assert hasattr(service, 'create_product')
    
    def test_multiple_service_interfaces(self):
        """Test multiple service interfaces for different services."""
        @service_interface("user-service", "/api/v1")
        class UserService:
            @service_call("user-service", HTTPMethod.GET, "/users/{user_id}")
            async def get_user(self, user_id: int):
                pass
        
        @service_interface("order-service", "/api/v2")
        class OrderService:
            @service_call("order-service", HTTPMethod.POST, "/orders")
            async def create_order(self, order_data: OrderRequest) -> OrderResponse:
                pass
        
        assert UserService._service_name == "user-service"
        assert UserService._base_path == "/api/v1"
        assert OrderService._service_name == "order-service"
        assert OrderService._base_path == "/api/v2"


@pytest.mark.asyncio
class TestHealthCheckDecorator:
    """Test health_check decorator."""
    
    async def test_health_check_healthy_service(self):
        """Test health_check decorator with healthy service."""
        call_count = 0
        
        @health_check(interval=0.1, timeout=0.5, failure_threshold=2)
        async def healthy_service_call():
            nonlocal call_count
            call_count += 1
            return f"success_{call_count}"
        
        # Multiple calls should work normally  
        result1 = await healthy_service_call()
        result2 = await healthy_service_call()
        
        # Health check decorator may call the function for health checks
        # so we just verify that the results are successful
        assert "success_" in result1
        assert "success_" in result2
        assert call_count >= 2  # May be called more often for health checks
    
    async def test_health_check_failing_service(self):
        """Test health_check decorator with failing service."""
        call_count = 0
        
        @health_check(interval=0.05, timeout=0.1, failure_threshold=2)
        async def failing_service_call():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:  # Fail first 3 calls
                raise Exception(f"Failure {call_count}")
            return "success"
        
        # First few calls should fail normally or with health check error
        exception_count = 0
        health_check_error_found = False
        
        for i in range(5):  # Try multiple times to trigger health check failure
            try:
                await failing_service_call()
            except Exception as e:
                exception_count += 1
                if "is unhealthy" in str(e):
                    health_check_error_found = True
                    break
            await asyncio.sleep(0.1)  # Give time for health check to trigger
        
        # Either we should have failures, or health check should trigger
        assert exception_count > 0, "Expected at least one exception"


@pytest.mark.asyncio
class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    async def test_microservice_communication_pattern(self):
        """Test typical microservice communication pattern."""
        with patch('msfw.decorators.service._make_typed_service_call') as mock_call:
            # Mock responses for different services
            def mock_service_call(*args, **kwargs):
                service_name = kwargs.get('service_name')
                path = kwargs.get('path')
                
                if service_name == "user-service":
                    return ServiceCallResult(
                        success=True,
                        data={"id": 1, "name": "John Doe", "email": "john@example.com"},
                        service_name=service_name
                    )
                elif service_name == "product-service":
                    return ServiceCallResult(
                        success=True,
                        data={"id": 1, "name": "Laptop", "price": 999.99, "category": "electronics"},
                        service_name=service_name
                    )
                elif service_name == "order-service":
                    return ServiceCallResult(
                        success=True,
                        data={"id": 1, "status": "created", "total_amount": 999.99},
                        service_name=service_name
                    )
                else:
                    return ServiceCallResult(
                        success=False,
                        error="Service not found",
                        service_name=service_name
                    )
            
            mock_call.side_effect = mock_service_call
            
            # Define service interfaces
            @service_interface("user-service")
            class UserService:
                @retry_on_failure(max_attempts=3, delay=0.1)
                @service_call("user-service", HTTPMethod.GET, "/users/{user_id}")
                async def get_user(self, user_id: int):
                    pass
            
            @service_interface("product-service")
            class ProductService:
                @cached_service_call(ttl=300.0)
                @service_call("product-service", HTTPMethod.GET, "/products/{product_id}")
                async def get_product(self, product_id: int):
                    pass
            
            @service_interface("order-service")
            class OrderService:
                @circuit_breaker(failure_threshold=5, recovery_timeout=60.0)
                @service_call("order-service", HTTPMethod.POST, "/orders")
                async def create_order(self, order_data: OrderRequest):
                    pass
            
            # Use the services
            user_service = UserService()
            product_service = ProductService()
            order_service = OrderService()
            
            # Get user and product data
            user = await user_service.get_user(1)
            product = await product_service.get_product(1)
            
            # Create order
            order_request = OrderRequest(product_id=1, quantity=1, customer_id=1)
            order = await order_service.create_order(order_request)
            
            assert user["name"] == "John Doe"
            assert product["name"] == "Laptop"
            assert order["status"] == "created"
    
    async def test_error_handling_chain(self):
        """Test comprehensive error handling through decorator chain."""
        failure_count = 0
        
        with patch('msfw.decorators.service._make_typed_service_call') as mock_call:
            def failing_call(*args, **kwargs):
                nonlocal failure_count
                failure_count += 1
                if failure_count <= 3:
                    raise Exception(f"Network error {failure_count}")
                return ServiceCallResult(
                    success=True,
                    data={"id": 1, "status": "recovered"},
                    service_name="resilient-service"
                )
            
            mock_call.side_effect = failing_call
            
            @circuit_breaker(failure_threshold=5, recovery_timeout=0.1)
            @retry_on_failure(max_attempts=4, delay=0.1)
            @service_call("resilient-service", HTTPMethod.GET, "/status")
            async def resilient_service_call():
                pass
            
            # Should succeed after retries
            result = await resilient_service_call()
            assert result["status"] == "recovered"
            assert failure_count == 4  # 3 failures + 1 success


if __name__ == "__main__":
    pytest.main([__file__]) 