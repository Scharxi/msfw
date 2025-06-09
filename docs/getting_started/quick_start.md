# Quick Start

Get started with MSFW in minutes! This guide walks you through the core features of the Modular Microservices Framework.

## 🎯 What You'll Learn

- Run the demo application and explore its features
- Create modules with auto-discovery
- Build plugins with event hooks
- Use advanced configuration with environment interpolation
- Work with the Service SDK for inter-service communication

## 1. Test the Demo Application

MSFW comes with a comprehensive demo application that showcases all major features.

### Start the Demo

```bash
# From the project root
python main.py
```

The demo application will be available at:
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics
- **Service Info**: http://localhost:8000/info
- **API Versions**: http://localhost:8000/api/versions
- **Demo Endpoint**: http://localhost:8000/demo

### Explore the Demo Features

The demo showcases:
- **API Versioning**: Both v1.0 and v2.0 endpoints for users
- **OpenAPI Documentation**: Comprehensive Swagger docs
- **Module System**: Auto-discovered modules
- **Plugin Architecture**: Event-driven extensions
- **Service Communication**: Inter-service SDK
- **Configuration**: Environment variable interpolation

## 2. Understanding MSFW Architecture

MSFW is built around these core concepts:

```python
from msfw import MSFWApplication, load_config

# Load configuration with environment interpolation
config = load_config()  # Loads from config/settings.toml

# Create the application
app = MSFWApplication(config)

# Auto-discovery is enabled by default
# Modules from modules/ and plugins from plugins/ are loaded automatically

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app.get_app(), host="0.0.0.0", port=8000)
```

## 3. Creating Your First Module

Modules are self-contained components with their own routes, models, and lifecycle.

### Create a Module File

Create `modules/todo_module.py`:

```python
from msfw import Module
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

class Todo(BaseModel):
    id: int
    title: str
    completed: bool = False

class TodoCreate(BaseModel):
    title: str

class TodoModule(Module):
    def __init__(self):
        self.todos: List[Todo] = []
        self.next_id = 1

    @property
    def name(self) -> str:
        return "todo"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Simple todo management module"

    def register_routes(self, router: APIRouter) -> None:
        @router.get("/todos", response_model=List[Todo])
        async def list_todos():
            """Get all todos"""
            return self.todos

        @router.post("/todos", response_model=Todo)
        async def create_todo(todo_data: TodoCreate):
            """Create a new todo"""
            todo = Todo(
                id=self.next_id,
                title=todo_data.title
            )
            self.todos.append(todo)
            self.next_id += 1
            return todo

        @router.put("/todos/{todo_id}", response_model=Todo)
        async def update_todo(todo_id: int):
            """Toggle todo completion"""
            for todo in self.todos:
                if todo.id == todo_id:
                    todo.completed = not todo.completed
                    return todo
            return {"error": "Todo not found"}

    async def startup(self) -> None:
        """Called when module starts"""
        print(f"📝 Todo module started with {len(self.todos)} todos")

    async def shutdown(self) -> None:
        """Called when module shuts down"""
        print(f"📝 Todo module shutting down with {len(self.todos)} todos")

# Export the module for auto-discovery
module = TodoModule()
```

### Auto-Discovery in Action

With auto-discovery enabled (default), MSFW will automatically:
1. Find the `todo_module.py` file in the `modules/` directory
2. Load the `module` variable
3. Register its routes under `/todo/...`
4. Include it in the application lifecycle

Your endpoints will be available at:
- `GET /todo/todos` - List all todos
- `POST /todo/todos` - Create a new todo
- `PUT /todo/todos/{id}` - Toggle todo completion

## 4. Building a Plugin

Plugins extend functionality through event hooks and middleware.

### Create a Plugin File

Create `plugins/request_logger.py`:

```python
from msfw import Plugin, Config
import structlog
from fastapi import Request, Response

class RequestLoggerPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.request_count = 0
        self.logger = structlog.get_logger()

    @property
    def name(self) -> str:
        return "request_logger"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Logs all HTTP requests"

    async def setup(self, config: Config) -> None:
        """Setup plugin with event hooks"""
        # Register for application lifecycle events
        self.register_hook("app_startup", self.on_startup)
        self.register_hook("app_shutdown", self.on_shutdown)
        
        # Register middleware
        self.register_middleware(self.log_requests)

    async def on_startup(self, **kwargs):
        """Called when application starts"""
        self.logger.info("🔍 Request Logger Plugin activated")

    async def on_shutdown(self, **kwargs):
        """Called when application shuts down"""
        self.logger.info(
            "🔍 Request Logger Plugin shutting down", 
            total_requests=self.request_count
        )

    async def log_requests(self, request: Request, call_next):
        """Middleware to log all requests"""
        self.request_count += 1
        
        self.logger.info(
            "📥 HTTP Request",
            method=request.method,
            url=str(request.url),
            user_agent=request.headers.get("user-agent"),
            request_count=self.request_count
        )
        
        response = await call_next(request)
        
        self.logger.info(
            "📤 HTTP Response",
            status_code=response.status_code,
            request_count=self.request_count
        )
        
        return response

# Export for auto-discovery
plugin = RequestLoggerPlugin()
```

## 5. Advanced Configuration

MSFW's configuration system supports environment variable interpolation and microservice-specific settings.

### Configuration File

Create `config/settings.toml`:

```toml
# Main application settings
app_name = "${APP_NAME:My MSFW Service}"
version = "${VERSION:1.0.0}"
debug = "${DEBUG:true}"
environment = "${ENVIRONMENT:development}"

# Database configuration with interpolation
[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"
echo = "${DATABASE_ECHO:false}"
pool_size = "${DB_POOL_SIZE:10}"

# Service communication
[service_registry]
enabled = "${SERVICE_REGISTRY_ENABLED:false}"
url = "${SERVICE_REGISTRY_URL:http://localhost:8500}"

# Security settings
[security]
secret_key = "${SECRET_KEY:dev-secret-change-in-production}"
access_token_expire_minutes = "${TOKEN_EXPIRE:30}"

# Monitoring
[monitoring]
enabled = "${MONITORING_ENABLED:true}"
prometheus_enabled = "${PROMETHEUS_ENABLED:true}"

# OpenAPI documentation
[openapi]
title = "${API_TITLE:My MSFW API}"
description = "Built with MSFW - Modular Microservices Framework"
version = "${API_VERSION:1.0.0}"
```

### Using Configuration

```python
from msfw import load_config, MSFWApplication

# Load configuration with environment interpolation
config = load_config("config/settings.toml")

# Override programmatically if needed
config.app_name = "Custom Service Name"
config.debug = True

# Configuration is automatically passed to modules and plugins
app = MSFWApplication(config)
```

## 6. API Versioning

MSFW has built-in support for API versioning with decorators.

```python
from msfw import get, post, api_version

# Version 1.0 endpoint
@get("/users/{user_id}", version="1.0")
async def get_user_v1(user_id: int):
    return {"id": user_id, "name": "John Doe", "email": "john@example.com"}

# Version 2.0 with enhanced response
@get("/users/{user_id}", version="2.0")
async def get_user_v2(user_id: int):
    return {
        "id": user_id,
        "first_name": "John",
        "last_name": "Doe", 
        "email": "john@example.com",
        "profile": {"bio": "Software developer"}
    }
```

Clients can request specific versions:
- `GET /api/v1.0/users/1` - Version 1.0
- `GET /api/v2.0/users/1` - Version 2.0
- `Accept: application/vnd.api+json;version=2.0` - Content negotiation

## 7. Service Communication SDK

MSFW includes an SDK for inter-service communication with circuit breakers and retry logic.

```python
from msfw import ServiceSDK, call_service

# Initialize SDK
sdk = ServiceSDK(config=config)

# Register current service
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
    circuit_breaker_enabled=True,
    retry_attempts=3
)

if result.success:
    orders = result.data
else:
    print(f"Service call failed: {result.error}")
```

## 8. Testing Your Application

MSFW provides excellent testing support with dependency injection.

```python
import pytest
from httpx import AsyncClient
from msfw import MSFWApplication, Config

@pytest.fixture
async def test_app():
    config = Config()
    config.database.url = "sqlite+aiosqlite:///:memory:"
    config.auto_discover_modules = False  # Control module loading
    
    app = MSFWApplication(config)
    await app.initialize()
    return app

@pytest.mark.asyncio
async def test_todo_creation(test_app):
    # Test the auto-discovered module
    async with AsyncClient(app=test_app.get_app(), base_url="http://test") as client:
        response = await client.post("/todo/todos", json={"title": "Test task"})
        assert response.status_code == 200
        todo = response.json()
        assert todo["title"] == "Test task"
        assert todo["completed"] is False
```

## 9. CLI Tools

MSFW includes powerful CLI tools for project management:

```bash
# Create a new project
msfw init my-service

# Generate a module
msfw create-module auth --description="Authentication module"

# Generate a plugin  
msfw create-plugin cache --description="Caching plugin"

# Show project information
msfw info

# Run the application
msfw run --reload
```

## 🚀 Next Steps

Now that you understand the basics, explore:

1. **[Basic Concepts](basic_concepts.md)** - Deep dive into MSFW architecture
2. **Demo Application** - Study `main.py` for advanced patterns
3. **CLI Features** - Run `msfw --help` to see all available commands
4. **Configuration** - Explore environment-specific configs
5. **Service Communication** - Build distributed systems with the SDK

## Key Features Recap

✅ **Auto-discovery** of modules and plugins  
✅ **Environment variable interpolation** in configs  
✅ **Built-in API versioning** with content negotiation  
✅ **Service SDK** for microservice communication  
✅ **Event-driven architecture** with plugins  
✅ **Production-ready** monitoring and health checks  
✅ **SQLAlchemy 2.0** async database support  
✅ **Comprehensive testing** utilities 