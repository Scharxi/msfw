# Service Communication SDK

MSFW includes a comprehensive SDK for inter-service communication with built-in resilience patterns, type safety, and service discovery.

## Overview

The Service SDK provides:

- **Circuit Breaker Pattern** - Automatic failure protection
- **Retry Logic** - Configurable retry strategies
- **Type-Safe Interfaces** - Pydantic-based service contracts
- **Service Discovery** - Automatic service registration and discovery
- **Load Balancing** - Multiple instance support
- **Health Monitoring** - Continuous health checks
- **Caching** - Response caching with TTL

## Basic Service Communication

### Initialize the SDK

```python
from msfw import ServiceSDK, call_service

# Initialize SDK with configuration
sdk = ServiceSDK(config=config)

# Register current service in service registry
await sdk.register_current_service(
    service_name="user-service",
    version="1.0.0",
    host="localhost",
    port=8000,
    health_check_path="/health"
)
```

### Simple Service Calls

```python
# Basic service call
result = await call_service(
    service="order-service",
    endpoint="/orders",
    method="GET",
    timeout=30.0,
    retry_attempts=3
)

if result.success:
    orders = result.data
    print(f"Retrieved {len(orders)} orders")
else:
    print(f"Service call failed: {result.error}")
    print(f"HTTP Status: {result.status_code}")
```

### HTTP Methods

```python
# GET request
users = await sdk.get_from_service(
    service_name="user-service",
    path="/users",
    params={"limit": 50, "active": True}
)

# POST request
new_user = await sdk.post_to_service(
    service_name="user-service",
    path="/users",
    data={
        "name": "John Doe",
        "email": "john@example.com"
    }
)

# PUT request
updated_user = await sdk.put_to_service(
    service_name="user-service",
    path="/users/123",
    data={"name": "John Smith"}
)

# DELETE request
await sdk.delete_from_service(
    service_name="user-service",
    path="/users/123"
)
```

## Circuit Breaker Pattern

The SDK includes automatic circuit breaker protection to prevent cascading failures.

### Circuit Breaker Configuration

```python
from msfw import CircuitBreakerConfig

# Configure circuit breaker
circuit_config = CircuitBreakerConfig(
    failure_threshold=5,        # Open after 5 failures
    success_threshold=2,        # Close after 2 successes
    timeout=60.0,              # Wait 60s before retry
    retry_attempts=3,          # Retry failed requests
    retry_delay=1.0,           # Initial retry delay
    retry_backoff=2.0,         # Backoff multiplier
    request_timeout=30.0       # Request timeout
)

# Get service client with circuit breaker
client = sdk.get_client(
    "order-service",
    circuit_config=circuit_config
)
```

### Circuit Breaker States

```python
# Make requests - circuit breaker handles failures automatically
try:
    response = await client.get("/orders/123")
    print("Order retrieved successfully")
except CircuitOpenError:
    print("Circuit breaker is open - service temporarily unavailable")
except ServiceClientError as e:
    print(f"Service error: {e}")

# Check circuit breaker status
circuit_states = client.get_circuit_state()
for endpoint, state in circuit_states.items():
    print(f"Circuit {endpoint}: {state.state} (failures: {state.failure_count})")
```

### Circuit Breaker with Context Manager

```python
# Automatic resource cleanup
async with sdk.service_client("payment-service") as client:
    try:
        response = await client.post("/payments", json={
            "amount": 1000,
            "currency": "USD",
            "card_token": "tok_123"
        })
        return response
    except CircuitOpenError:
        # Handle circuit breaker being open
        return {"error": "Payment service temporarily unavailable"}
```

## Type-Safe Service Interfaces

Define strongly typed interfaces for service communication:

### Basic Type-Safe Interface

```python
from msfw import service_interface, service_call, HTTPMethod
from pydantic import BaseModel
from typing import List, Optional

class User(BaseModel):
    id: int
    name: str
    email: str
    active: bool = True

class CreateUserRequest(BaseModel):
    name: str
    email: str

class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    active: Optional[bool] = None

@service_interface("user-service", "/api/v1")
class UserService:
    """Type-safe user service interface."""
    
    @service_call("user-service", HTTPMethod.GET, "/users/{user_id}")
    async def get_user(self, user_id: int) -> User:
        """Get user by ID with automatic type validation."""
        pass
    
    @service_call("user-service", HTTPMethod.POST, "/users")
    async def create_user(self, user_data: CreateUserRequest) -> User:
        """Create a new user."""
        pass
    
    @service_call("user-service", HTTPMethod.PUT, "/users/{user_id}")
    async def update_user(self, user_id: int, user_data: UpdateUserRequest) -> User:
        """Update a user."""
        pass
    
    @service_call("user-service", HTTPMethod.GET, "/users")
    async def list_users(self, limit: int = 20, active: bool = True) -> List[User]:
        """List users with pagination and filtering."""
        pass
    
    @service_call("user-service", HTTPMethod.DELETE, "/users/{user_id}")
    async def delete_user(self, user_id: int) -> None:
        """Delete a user."""
        pass

# Usage
user_service = UserService()

# All calls are type-safe and validated
user = await user_service.get_user(123)
print(f"User: {user.name} ({user.email})")

users = await user_service.list_users(limit=50, active=True)
print(f"Found {len(users)} active users")

new_user = await user_service.create_user(CreateUserRequest(
    name="Jane Doe",
    email="jane@example.com"
))
```

### Advanced Service Interface with Resilience

```python
from msfw import (
    service_interface, service_call, retry_on_failure, 
    circuit_breaker, cached_service_call, health_check
)

@service_interface("order-service", "/api/v1")
class OrderService:
    """Order service with full resilience patterns."""
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30.0)
    @retry_on_failure(max_attempts=2, delay=0.5, backoff=2.0)
    @service_call("order-service", HTTPMethod.POST, "/orders")
    async def create_order(self, order_data: CreateOrderRequest) -> Order:
        """Create order with circuit breaker and retry protection."""
        pass
    
    @cached_service_call(ttl=300.0)  # Cache for 5 minutes
    @service_call("order-service", HTTPMethod.GET, "/orders/{order_id}")
    async def get_order(self, order_id: int) -> Order:
        """Get order with caching."""
        pass
    
    @health_check(interval=30.0, timeout=5.0, failure_threshold=3)
    @service_call("order-service", HTTPMethod.GET, "/orders/search")
    async def search_orders(
        self, 
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Order]:
        """Search orders with health monitoring."""
        pass
    
    @retry_on_failure(max_attempts=3, delay=1.0)
    @service_call("order-service", HTTPMethod.PUT, "/orders/{order_id}/status")
    async def update_order_status(self, order_id: int, status: str) -> Order:
        """Update order status with retry logic."""
        pass

# Usage with error handling
order_service = OrderService()

try:
    order = await order_service.create_order(CreateOrderRequest(
        user_id=123,
        items=[{"product_id": 456, "quantity": 2}],
        total=2000
    ))
    print(f"Order created: {order.id}")
except ServiceClientError as e:
    print(f"Failed to create order: {e}")
except ValidationError as e:
    print(f"Invalid order data: {e}")
```

## Service Discovery & Registration

### Register Services

```python
# Register external service
await sdk.register_external_service(
    service_name="payment-service",
    host="payments.example.com",
    port=443,
    protocol="https",
    health_check_path="/health",
    version="2.0"
)

# Register with custom metadata
await sdk.register_external_service(
    service_name="notification-service",
    host="notifications.internal",
    port=8080,
    metadata={
        "region": "us-west-2",
        "team": "platform",
        "environment": "production"
    }
)
```

### Service Discovery

```python
# Discover available services
services = await sdk.discover_services("user-service")
for service in services:
    print(f"Service: {service.name}@{service.host}:{service.port}")
    print(f"Status: {service.status}")
    print(f"Version: {service.version}")

# Get service instance
instance = await sdk.get_service_instance("user-service")
if instance:
    print(f"Using service at {instance.host}:{instance.port}")
```

### Health Monitoring

```python
# Check service health
is_healthy = await sdk.health_check_service("user-service")
if is_healthy:
    print("Service is healthy")
else:
    print("Service is unhealthy")

# Get health status for all services
health_status = await sdk.get_all_service_health()
for service, status in health_status.items():
    print(f"{service}: {'✅' if status else '❌'}")

# Continuous health monitoring
@sdk.on_service_health_change
async def handle_health_change(service_name: str, is_healthy: bool):
    if is_healthy:
        print(f"Service {service_name} recovered")
    else:
        print(f"Service {service_name} became unhealthy")
```

## Advanced Features

### Request/Response Middleware

```python
@sdk.middleware
async def add_auth_header(request, call_next):
    """Add authentication header to all requests."""
    token = await get_auth_token()
    request.headers["Authorization"] = f"Bearer {token}"
    return await call_next(request)

@sdk.middleware
async def log_requests(request, call_next):
    """Log all service requests."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    print(f"Request to {request.url} took {duration:.2f}s")
    return response
```

### Batch Operations

```python
# Batch requests to multiple services
async def get_user_with_orders(user_id: int):
    # Execute requests concurrently
    user_task = user_service.get_user(user_id)
    orders_task = order_service.get_user_orders(user_id)
    
    user, orders = await asyncio.gather(user_task, orders_task)
    
    return {
        "user": user,
        "orders": orders,
        "order_count": len(orders)
    }

# Batch with error handling
async def get_user_dashboard_data(user_id: int):
    results = await sdk.batch_call([
        ("user", user_service.get_user(user_id)),
        ("orders", order_service.get_user_orders(user_id)),
        ("notifications", notification_service.get_unread_count(user_id))
    ])
    
    dashboard_data = {}
    for name, result in results.items():
        if result.success:
            dashboard_data[name] = result.data
        else:
            dashboard_data[name] = None
            print(f"Failed to load {name}: {result.error}")
    
    return dashboard_data
```

### Service Versioning

```python
# Multiple service versions
v1_user_service = UserServiceV1()
v2_user_service = UserServiceV2()

# Gradual migration
async def get_user_with_fallback(user_id: int):
    try:
        # Try v2 first
        return await v2_user_service.get_user(user_id)
    except ServiceClientError:
        # Fallback to v1
        return await v1_user_service.get_user(user_id)
```

### Caching Integration

```python
from msfw import cached_service_call

class ProductService:
    @cached_service_call(
        ttl=600.0,              # Cache for 10 minutes
        key_func=lambda self, product_id: f"product:{product_id}",
        cache_on_error=True     # Cache error responses too
    )
    @service_call("product-service", HTTPMethod.GET, "/products/{product_id}")
    async def get_product(self, product_id: int) -> Product:
        pass
    
    @cached_service_call(ttl=300.0, vary_on=["category", "limit"])
    @service_call("product-service", HTTPMethod.GET, "/products")
    async def list_products(self, category: str, limit: int = 20) -> List[Product]:
        pass

# Manual cache control
product_service = ProductService()

# This will use cache if available
product = await product_service.get_product(123)

# Force cache refresh
product = await product_service.get_product(123, force_refresh=True)

# Clear specific cache entry
await product_service.clear_cache("product:123")
```

## Error Handling

### Service-Specific Error Handling

```python
from msfw import ServiceClientError, CircuitOpenError, ServiceTimeoutError

async def robust_service_call():
    try:
        return await user_service.get_user(123)
    except CircuitOpenError:
        # Circuit breaker is open
        return await get_user_from_cache(123)
    except ServiceTimeoutError:
        # Request timed out
        return await get_user_from_backup_service(123)
    except ServiceClientError as e:
        if e.status_code == 404:
            return None
        elif e.status_code >= 500:
            # Server error - log and retry later
            logger.error(f"Service error: {e}")
            raise
        else:
            # Client error - don't retry
            raise
```

### Global Error Handling

```python
@sdk.error_handler
async def handle_service_errors(error: ServiceClientError, context: dict):
    """Global error handler for all service calls."""
    service_name = context.get("service_name")
    endpoint = context.get("endpoint")
    
    logger.error(
        "Service call failed",
        service=service_name,
        endpoint=endpoint,
        error=str(error),
        status_code=error.status_code
    )
    
    # Send metrics
    metrics.increment(f"service_call_error.{service_name}")
    
    # Alert on critical services
    if service_name in ["payment-service", "auth-service"]:
        await send_alert(f"Critical service {service_name} is failing")
```

## Configuration

### SDK Configuration

```python
from msfw import ServiceSDKConfig

sdk_config = ServiceSDKConfig(
    default_timeout=30.0,
    default_retry_attempts=3,
    default_circuit_breaker_enabled=True,
    service_discovery_enabled=True,
    health_check_interval=30.0,
    cache_enabled=True,
    metrics_enabled=True
)

sdk = ServiceSDK(config=config, sdk_config=sdk_config)
```

### Per-Service Configuration

```toml
# config/settings.toml
[services.user_service]
host = "${USER_SERVICE_HOST:localhost}"
port = "${USER_SERVICE_PORT:8001}"
timeout = "${USER_SERVICE_TIMEOUT:30.0}"
circuit_breaker_enabled = true
retry_attempts = 3

[services.payment_service]
host = "${PAYMENT_SERVICE_HOST:payments.example.com}"
port = 443
protocol = "https"
timeout = 60.0
circuit_breaker_enabled = true
failure_threshold = 3
```

The Service Communication SDK provides a comprehensive solution for building resilient, type-safe microservice architectures with minimal boilerplate code. 