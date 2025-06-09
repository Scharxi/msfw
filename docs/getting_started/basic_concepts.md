# Basic Concepts

Understand the fundamental concepts of MSFW and how they work together to create a powerful microservice architecture.

## 🏗️ Architecture Overview

MSFW follows a modular, plugin-based architecture that provides maximum flexibility and extensibility.

```{mermaid}
graph TB
    App[MSFWApplication]
    App --> Config[Configuration]
    App --> Router[API Router]
    App --> DB[Database]
    App --> Middleware[Middleware Stack]
    
    Router --> M1[Module 1]
    Router --> M2[Module 2]
    Router --> MN[Module N]
    
    App --> P1[Plugin 1]
    App --> P2[Plugin 2]
    App --> PN[Plugin N]
    
    Config --> ENV[Environment Variables]
    Config --> Files[Config Files]
    
    DB --> Models[SQLAlchemy Models]
    DB --> Sessions[Async Sessions]
```

## 🧩 Modules

Modules are the building blocks of your application. They contain:

- **Business Logic**: Core functionality of your application
- **API Routes**: REST endpoints for external communication
- **Data Models**: Structured data representation
- **Services**: Reusable business logic

### Module Anatomy

```python
from msfw import Module
from fastapi import APIRouter
from pydantic import BaseModel

class ItemModule(Module):
    @property
    def name(self) -> str:
        return "item"  # Unique module name
    
    @property
    def prefix(self) -> str:
        return "/api/v1"  # URL prefix (optional)
    
    def register_routes(self, router: APIRouter) -> None:
        # Define routes
        pass
    
    async def startup(self) -> None:
        # Initialization logic (optional)
        pass
    
    async def shutdown(self) -> None:
        # Cleanup logic (optional)
        pass
```

### Module Registration

```python
from msfw import MSFWApplication

app = MSFWApplication(config)

# Single module
app.register_module(ItemModule())

# Multiple modules
app.register_modules([
    UserModule(),
    OrderModule(),
    ProductModule()
])

# Auto-discovery
app.discover_modules("modules/")  # Loads all modules from directory
```

## 🔌 Plugins

Plugins extend your application's functionality through event hooks and middleware.

### Plugin Types

1. **Middleware Plugins**: HTTP request/response processing
2. **Event Plugins**: Lifecycle events (startup, shutdown)
3. **Service Plugins**: Additional services (caching, logging)
4. **Integration Plugins**: External systems (databases, APIs)

### Plugin Example

```python
from msfw import Plugin, Config

class CachePlugin(Plugin):
    @property
    def name(self) -> str:
        return "cache"
    
    async def setup(self, config: Config) -> None:
        # Plugin-specific configuration
        self.cache_backend = config.get("cache.backend", "redis")
        
        # Register event hooks
        self.register_hook("app_startup", self.init_cache)
        self.register_hook("before_request", self.check_cache)
        self.register_hook("after_request", self.update_cache)
    
    async def init_cache(self, **kwargs):
        # Initialize cache backend
        pass
```

### Available Event Hooks

- `app_startup`: Application startup
- `app_shutdown`: Application shutdown
- `before_request`: Before HTTP request
- `after_request`: After HTTP request
- `module_loaded`: After module registration
- `plugin_loaded`: After plugin registration

## ⚙️ Configuration System

MSFW features a sophisticated configuration system that solves the "double configuration" problem by combining file-based configuration with environment variable interpolation.

### Environment Variable Interpolation

The core feature that makes MSFW configuration powerful:

```toml
# config/settings.toml
app_name = "${APP_NAME:My MSFW Service}"
debug = "${DEBUG:false}"
database_url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"

[security]
secret_key = "${SECRET_KEY}"  # Required - will fail if not set
jwt_expire = "${JWT_EXPIRE:30}"  # Optional with default

[services.api]
port = "${API_PORT:8000}"
workers = "${API_WORKERS:4}"
```

### Configuration Patterns

**Required Variables**: `${VAR_NAME}` - Application fails if not set
```toml
secret_key = "${SECRET_KEY}"
database_url = "${DATABASE_URL}"
```

**Optional with Defaults**: `${VAR_NAME:default}` - Uses default if not set
```toml
debug = "${DEBUG:false}"
port = "${PORT:8000}"
redis_url = "${REDIS_URL:redis://localhost:6379/0}"
```

**Complex Interpolation**: Build URLs from multiple variables
```toml
database_url = "postgresql://${DB_USER}:${DB_PASS}@${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME}"
redis_url = "${REDIS_HOST:localhost}:${REDIS_PORT:6379}/${REDIS_DB:0}"
```

### Configuration Priority

1. **Environment Variables** (highest priority)
2. **Interpolated values** from TOML file
3. **Default values** in interpolation syntax
4. **Framework defaults** (lowest priority)

### Loading Configuration

```python
from msfw import load_config, Config

# Automatic discovery (recommended)
config = load_config()  # Looks for config/settings.toml or settings.toml

# Specific file with interpolation
config = Config.from_file("path/to/config.toml")

# File + environment override
config = Config.from_file_and_env("path/to/config.toml")

# Programmatic configuration
config = Config()
config.app_name = "My Service"
config.debug = True
```

### Microservice-Specific Configuration

MSFW supports configuration for multiple services in one file:

```toml
# Global defaults
debug = "${DEBUG:false}"

[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"
pool_size = "${DB_POOL_SIZE:10}"

# Service-specific configurations
[services.api]
enabled = true
port = "${API_PORT:8000}"
workers = "${API_WORKERS:4}"
debug = "${API_DEBUG:true}"

[services.api.database]
url = "${API_DATABASE_URL:postgresql://db:5432/api}"

[services.worker]
enabled = "${WORKER_ENABLED:false}"
port = "${WORKER_PORT:8001}"

[services.worker.redis]
url = "${WORKER_REDIS_URL:redis://localhost:6379/1}"

# Environment-specific configurations
[environments.development]
debug = true
log_level = "DEBUG"

[environments.production]
debug = false
log_level = "WARNING"
```

## 🌐 Service Communication SDK

MSFW includes a comprehensive SDK for inter-service communication with resilience patterns built-in.

### Basic Service Communication

```python
from msfw import ServiceSDK, call_service

# Initialize SDK
sdk = ServiceSDK(config=config)

# Register current service in service registry
await sdk.register_current_service(
    service_name="user-service",
    version="1.0.0",
    host="localhost",
    port=8000
)

# Call another service
result = await call_service(
    service="order-service",
    endpoint="/orders",
    method="GET",
    timeout=30.0,
    retry_attempts=3,
    circuit_breaker_enabled=True
)

if result.success:
    orders = result.data
    print(f"Retrieved {len(orders)} orders")
else:
    print(f"Service call failed: {result.error}")
```

### Circuit Breaker Pattern

The SDK includes automatic circuit breaker protection:

```python
from msfw import ServiceClient, CircuitBreakerConfig

# Configure circuit breaker
circuit_config = CircuitBreakerConfig(
    failure_threshold=5,        # Open after 5 failures
    success_threshold=2,        # Close after 2 successes
    timeout=60.0,              # Wait 60s before retry
    retry_attempts=3,          # Retry failed requests
    request_timeout=30.0       # Request timeout
)

# Get service client with circuit breaker
client = sdk.get_client(
    "order-service",
    circuit_config=circuit_config
)

# Make requests - circuit breaker handles failures automatically
try:
    response = await client.get("/orders/123")
    print("Order retrieved successfully")
except ServiceClientError as e:
    print(f"Service unavailable: {e}")
```

### Type-Safe Service Interfaces

Define type-safe interfaces for service communication:

```python
from msfw import service_interface, service_call, HTTPMethod
from pydantic import BaseModel
from typing import List

class User(BaseModel):
    id: int
    name: str
    email: str

class CreateUserRequest(BaseModel):
    name: str
    email: str

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
    
    @service_call("user-service", HTTPMethod.GET, "/users")
    async def list_users(self, limit: int = 20) -> List[User]:
        """List users with pagination."""
        pass

# Usage
user_service = UserService()
user = await user_service.get_user(123)
users = await user_service.list_users(limit=50)
```

### Service Discovery & Registry

```python
# Register external services
await sdk.register_external_service(
    service_name="payment-service",
    host="payments.example.com",
    port=443,
    protocol="https"
)

# Service health checks
is_healthy = await sdk.health_check_service("payment-service")

# Load balancing (if multiple instances)
async with sdk.service_client("payment-service") as client:
    # Automatically routes to healthy instance
    response = await client.post("/payments", json=payment_data)
```

## 🔀 API Versioning

MSFW has built-in API versioning that makes versioning a first-class citizen.

### Version Strategies

MSFW supports multiple versioning strategies:

1. **URL Path** (default): `/api/v1.0/users`, `/api/v2.0/users`
2. **Header**: `X-API-Version: 1.0`
3. **Query Parameter**: `/users?version=1.0`
4. **Content Negotiation**: `Accept: application/vnd.api+json;version=1.0`

### Decorator-Based Versioning

```python
from msfw import get, post, put, delete

# Version 1.0 endpoints
@get("/users/{user_id}", version="1.0", tags=["users", "v1.0"])
async def get_user_v1(user_id: int):
    """Get user (v1.0 format)."""
    return {
        "id": user_id,
        "name": "John Doe",
        "email": "john@example.com"
    }

@post("/users", version="1.0", tags=["users", "v1.0"])
async def create_user_v1(user_data: UserCreateV1):
    """Create user (v1.0 format)."""
    return {"id": 123, "name": user_data.name, "email": user_data.email}

# Version 2.0 endpoints with enhanced features
@get("/users/{user_id}", version="2.0", tags=["users", "v2.0"])
async def get_user_v2(user_id: int):
    """Get user (v2.0 format with profile)."""
    return {
        "id": user_id,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "profile": {
            "bio": "Software developer",
            "avatar_url": "https://example.com/avatar.jpg"
        }
    }

@post("/users", version="2.0", tags=["users", "v2.0"])
async def create_user_v2(user_data: UserCreateV2):
    """Create user (v2.0 format with profile)."""
    return {
        "id": 123,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "email": user_data.email,
        "profile": user_data.profile
    }
```

### Versioned Routers

For better organization, use versioned routers:

```python
from msfw import VersionedRouter

# Create version-specific routers
v1_router = VersionedRouter("1.0", prefix="/api")
v2_router = VersionedRouter("2.0", prefix="/api")

@v1_router.get("/users")
async def list_users_v1():
    return [{"id": 1, "name": "John", "email": "john@example.com"}]

@v2_router.get("/users")
async def list_users_v2():
    return [{
        "id": 1,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "profile": {"bio": "Developer"}
    }]

# Include routers in main app
app.include_router(v1_router.router)
app.include_router(v2_router.router)
```

### Version Compatibility & Deprecation

```python
from msfw import version_compatibility, api_version

@version_compatibility("1.0", "1.1", "1.2")
@get("/users", version="1.2")
async def get_users():
    """Compatible with versions 1.0, 1.1, and 1.2."""
    return {"users": []}

# Deprecate old versions
@get("/legacy-endpoint", version="1.0", deprecated=True)
async def legacy_endpoint():
    """This endpoint is deprecated."""
    return {"message": "Please use v2.0"}

# Class-level versioning
@api_version("2.0", deprecated=False)
class UserAPIv2:
    @get("/users")
    async def get_users(self):
        return {"users": []}
```

### Client Version Requests

Clients can request specific versions:

```bash
# URL path versioning (default)
GET /api/v1.0/users/123
GET /api/v2.0/users/123

# Header versioning
GET /users/123
X-API-Version: 2.0

# Query parameter versioning
GET /users/123?version=2.0

# Content negotiation
GET /users/123
Accept: application/vnd.api+json;version=2.0
```

## 🎯 Decorator System

MSFW provides a comprehensive decorator system for routes, middleware, and service communication.

### Route Decorators

```python
from msfw import route, get, post, put, delete, patch

# Basic route decorator
@route("/items", methods=["GET", "POST"])
async def handle_items():
    return {"items": []}

# HTTP method-specific decorators
@get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}

@post("/users", status_code=201)
async def create_user(user_data: dict):
    return {"id": 123, **user_data}

@put("/users/{user_id}")
async def update_user(user_id: int, user_data: dict):
    return {"id": user_id, **user_data}

@delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int):
    return None

# Enhanced with OpenAPI metadata
@get(
    "/users/{user_id}",
    tags=["users"],
    summary="Get User",
    description="Retrieve a user by ID",
    response_model=User,
    version="1.0"
)
async def get_user_detailed(user_id: int):
    return {"id": user_id, "name": "John"}
```

### Service Communication Decorators

```python
from msfw import service_call, retry_on_failure, circuit_breaker, cached_service_call

# Basic service call
@service_call("user-service", HTTPMethod.GET, "/users/{user_id}")
async def get_user(user_id: int) -> User:
    pass

# With retry logic
@retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0)
@service_call("order-service", HTTPMethod.POST, "/orders")
async def create_order(order_data: CreateOrderRequest) -> Order:
    pass

# With circuit breaker
@circuit_breaker(failure_threshold=5, recovery_timeout=60.0)
@service_call("payment-service", HTTPMethod.POST, "/payments")
async def process_payment(payment_data: PaymentRequest) -> PaymentResult:
    pass

# With caching
@cached_service_call(ttl=300.0)  # Cache for 5 minutes
@service_call("product-service", HTTPMethod.GET, "/products/{product_id}")
async def get_product(product_id: int) -> Product:
    pass

# Combined resilience patterns
@circuit_breaker(failure_threshold=3, recovery_timeout=30.0)
@retry_on_failure(max_attempts=2, delay=0.5)
@cached_service_call(ttl=600.0)
@service_call("catalog-service", HTTPMethod.GET, "/categories/{category}/products")
async def get_products_by_category(category: str) -> List[Product]:
    pass
```

### Event & Middleware Decorators

```python
from msfw import event_handler, middleware, on_startup, on_shutdown

# Event handlers
@event_handler("app_startup", priority=100)
async def initialize_database():
    print("Database initialized")

@event_handler("app_shutdown", priority=100)
async def cleanup_resources():
    print("Resources cleaned up")

# Convenience decorators
@on_startup(priority=50)
async def setup_logging():
    print("Logging configured")

@on_shutdown(priority=150)
async def save_metrics():
    print("Metrics saved")

# Custom middleware
@middleware(priority=100)
class RequestTimingMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        start_time = time.time()
        await self.app(scope, receive, send)
        duration = time.time() - start_time
        print(f"Request took {duration:.2f}s")
```

### Health Check Decorators

```python
from msfw import health_check

@health_check(interval=30.0, timeout=5.0, failure_threshold=3)
@service_call("notification-service", HTTPMethod.GET, "/health")
async def check_notification_service():
    """Health check with automatic monitoring."""
    pass

# Custom health checks
@health_check(interval=60.0)
async def check_database_connection():
    """Custom health check for database."""
    try:
        await database.execute("SELECT 1")
        return True
    except Exception:
        return False
```

All these features work together to create a powerful, production-ready microservice framework that handles configuration, service communication, API versioning, and more with minimal boilerplate code. 