# API Versioning in MSFW

MSFW provides a comprehensive API versioning system that supports multiple versioning strategies and makes it easy to manage API evolution while maintaining backward compatibility.

## Features

- **Multiple Versioning Strategies**: URL path, headers, query parameters, and Accept header
- **Version Deprecation**: Mark versions as deprecated with custom messages and sunset dates
- **Automatic Route Resolution**: Intelligent routing to the best matching version
- **Service Discovery Integration**: Version-aware service discovery and communication
- **Middleware Support**: Automatic version detection and response headers
- **Backward Compatibility**: Seamless migration between API versions
- **OpenAPI Integration**: Versioned documentation generation

## Quick Start

### 1. Basic Setup

```python
from msfw import (
    MSFWApplication, Config,
    APIVersionManager, VersioningStrategy,
    create_versioning_middleware
)

# Configure version manager
from msfw.core.versioning import version_manager

version_manager.strategy = VersioningStrategy.URL_PATH
version_manager.add_version("1.0")
version_manager.add_version("2.0")
version_manager.deprecate_version("1.0", "Please migrate to v2.0")

# Create application
app = MSFWApplication(Config(app_name="my-api"))

# Add versioning middleware
middleware = create_versioning_middleware(version_manager)
for middleware_class, kwargs in middleware:
    app.app.add_middleware(middleware_class, **kwargs)

# Apply versioned routes to the FastAPI app
version_manager.apply_routes_to_app(app.app)
```

### 2. Creating Versioned Routes

```python
from msfw import get, post, put

# API v1.0 (deprecated)
@get("/users", version="1.0", deprecated=True)
async def get_users_v1():
    return [{"id": 1, "name": "John Doe"}]

# API v2.0 (current)
@get("/users", version="2.0")
async def get_users_v2():
    return [{"id": 1, "first_name": "John", "last_name": "Doe"}]

@post("/users", version="2.0")
async def create_user_v2(user_data: UserCreateV2):
    # Implementation
    return new_user
```

### 3. Alternative: Using Versioned Routers

For larger applications, you can also use version-specific routers:

```python
from msfw import create_v1_router, create_v2_router

# Create version-specific routers
v1_router = create_v1_router(deprecated=True)
v2_router = create_v2_router()

@v1_router.get("/users")
async def get_users_v1():
    return old_format_users()

@v2_router.get("/users")
async def get_users_v2():
    return new_format_users()

# Include in main app
app.include_router(v1_router.router)
app.include_router(v2_router.router)
```

## Versioning Strategies

### 1. URL Path Versioning (Default)

Routes include version in the URL path: `/api/v1/users`, `/api/v2/users`

```python
version_manager.strategy = VersioningStrategy.URL_PATH
version_manager.url_prefix = "/api"  # Results in /api/v1/, /api/v2/
```

**Pros:**
- Clear and visible in URLs
- Easy to test and debug
- Works with all HTTP clients
- Cacheable at different levels

**Cons:**
- URLs change between versions
- Can lead to URL proliferation

### 2. Header Versioning

Version specified in HTTP headers: `X-API-Version: 2.0`

```python
version_manager.strategy = VersioningStrategy.HEADER
version_manager.header_name = "X-API-Version"
```

**Pros:**
- URLs remain constant
- Clean separation of concerns
- Easy to implement version negotiation

**Cons:**
- Not visible in browser URLs
- Requires header support in clients

### 3. Query Parameter Versioning

Version specified as query parameter: `/users?version=2.0`

```python
version_manager.strategy = VersioningStrategy.QUERY_PARAM
version_manager.query_param_name = "version"
```

**Pros:**
- Visible in URLs
- Easy to test manually
- Works with simple HTTP clients

**Cons:**
- Can clutter URLs
- May interfere with other query parameters

### 4. Accept Header Versioning

Version specified in Accept header: `Accept: application/vnd.api+json;version=2.0`

```python
version_manager.strategy = VersioningStrategy.ACCEPT_HEADER
version_manager.accept_header_format = "application/vnd.api+json;version={version}"
```

**Pros:**
- Follows HTTP standards
- Supports content negotiation
- Professional API design

**Cons:**
- More complex to implement
- Requires understanding of HTTP content negotiation

## Advanced Features

### Unified Decorator API

MSFW provides a unified decorator API where version information is passed as parameters to the standard HTTP method decorators. This replaces the previous `@get_versioned`, `@post_versioned` etc. decorators for a cleaner, more consistent API:

```python
from msfw import get, post, put, delete, patch, route

# Standard decorators with version parameter
@get("/users", version="1.0", deprecated=True)
async def get_users_v1():
    return [{"id": 1, "name": "John Doe"}]

@post("/users", version="2.0", summary="Create user (v2)")
async def create_user_v2(user_data: UserV2):
    return new_user

# Generic route decorator
@route("/users/{id}", methods=["PATCH"], version="2.1")
async def patch_user(id: int, updates: UserUpdates):
    return updated_user
```

### Version Decorators

```python
from msfw import get, version_since, version_until, version_evolution

@get("/users/{id}/profile", version="2.1")
@version_since("1.2")
@version_until("3.0", "Use /v3/users/profile instead")
@version_evolution({
    "1.2": "Added user profile endpoint",
    "2.0": "Enhanced with additional fields",
    "2.1": "Added profile picture support"
})
async def get_user_profile(id: int):
    return user_profile
```

### Class-Based Versioning

```python
from msfw import get, post, api_version

@api_version("2.0")
class UserAPIv2:
    @get("/users", version="2.0")
    async def get_users(self):
        return users
    
    @post("/users", version="2.0")
    async def create_user(self, user_data: UserV2):
        return created_user
```

### Version Compatibility

```python
from msfw import get, version_compatibility

@get("/users", version="1.2")
@version_compatibility("1.0", "1.1", "1.2")
async def get_users_compatible():
    # This endpoint works for versions 1.0, 1.1, and 1.2
    return users
```

## Service Communication with Versioning

### Making Versioned Service Calls

```python
from msfw import ServiceSDK

sdk = ServiceSDK()

# Call specific version
users = await sdk.call_service(
    service_name="user-service",
    method="GET",
    path="/users",
    version="2.0"
)

# Version-aware service discovery
endpoint = await sdk.get_service_endpoint(
    service_name="user-service",
    version="2.0"
)
```

### Service Registration with Versions

```python
# Register service with version
await sdk.register_current_service(
    service_name="user-service",
    version="2.1.0",
    host="localhost",
    port=8000
)

# Discover services by version
services = await sdk.discover_services(
    service_name="user-service",
    version="2.0"  # Will match 2.x versions
)
```

## Data Model Evolution

### Example: User API Evolution

```python
# API v1.0 - Simple user model
class UserV1(BaseModel):
    id: int
    name: str
    email: str

# API v2.0 - Enhanced user model
class UserV2(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    
    @property
    def name(self) -> str:
        """Backward compatibility property."""
        return f"{self.first_name} {self.last_name}"

# Conversion helpers
def convert_user_v1_to_v2(user_v1: UserV1) -> UserV2:
    name_parts = user_v1.name.split(" ", 1)
    return UserV2(
        id=user_v1.id,
        first_name=name_parts[0],
        last_name=name_parts[1] if len(name_parts) > 1 else "",
        email=user_v1.email
    )

def convert_user_v2_to_v1(user_v2: UserV2) -> UserV1:
    return UserV1(
        id=user_v2.id,
        name=user_v2.name,  # Uses the property
        email=user_v2.email
    )
```

## Best Practices

### 1. Version Numbering

- Use semantic versioning: `major.minor.patch`
- Increment major version for breaking changes
- Increment minor version for backward-compatible additions
- Increment patch version for bug fixes

```python
# Good version progression
version_manager.add_version("1.0.0")  # Initial release
version_manager.add_version("1.1.0")  # Added new features
version_manager.add_version("1.1.1")  # Bug fixes
version_manager.add_version("2.0.0")  # Breaking changes
```

### 2. Deprecation Strategy

- Always provide deprecation warnings
- Set sunset dates for deprecated versions
- Provide migration guides

```python
version_manager.deprecate_version(
    "1.0",
    message="API v1.0 will be sunset on 2024-12-31. Please migrate to v2.0",
    sunset_date="2024-12-31"
)
```

### 3. Backward Compatibility

- Maintain backward compatibility within major versions
- Provide data transformation utilities
- Use optional fields for new features

```python
# Good: Optional new field
class UserV1_1(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None  # New optional field

# Bad: Required new field breaks compatibility
class UserV1_1_Bad(BaseModel):
    id: int
    name: str
    email: str
    phone: str  # Required field breaks v1.0 compatibility
```

### 4. Documentation

- Document API changes in version evolution decorators
- Maintain migration guides
- Use clear deprecation messages

```python
@get("/users", version="2.0")
@version_evolution({
    "1.0": "Initial user API",
    "1.1": "Added optional phone field",
    "2.0": "Split name into first_name and last_name fields"
})
async def get_users():
    return users
```

## Error Handling

### Version Not Supported

When a client requests an unsupported version:

```json
{
    "error": "unsupported_api_version",
    "message": "API version 3.0 is not supported",
    "supported_versions": ["1.0", "2.0", "2.1"]
}
```

### Deprecated Version Warning

Response headers for deprecated versions:

```
X-API-Deprecated: true
X-API-Deprecation-Message: API v1.0 is deprecated. Please use v2.0
X-API-Sunset: 2024-12-31
```

## Configuration Options

### APIVersionManager Configuration

```python
version_manager = APIVersionManager(
    strategy=VersioningStrategy.URL_PATH,
    default_version="2.0.0",
    header_name="X-API-Version",
    query_param_name="version",
    url_prefix="/api",
    strict_versioning=False  # Allow compatible versions
)
```

### Middleware Configuration

```python
middleware = create_versioning_middleware(
    version_manager=version_manager,
    enable_deprecation_warnings=True,
    enable_version_info_headers=True,
    enable_content_negotiation=True,
    enable_automatic_routing=True
)
```

## Testing Versioned APIs

### Unit Tests

```python
import pytest
from fastapi.testclient import TestClient

def test_api_v1():
    client = TestClient(app)
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    assert "X-API-Deprecated" in response.headers

def test_api_v2():
    client = TestClient(app)
    response = client.get("/api/v2/users")
    assert response.status_code == 200
    assert response.headers.get("X-API-Version") == "2.0"

def test_header_versioning():
    client = TestClient(app)
    response = client.get("/users", headers={"X-API-Version": "2.0"})
    assert response.status_code == 200
```

### Integration Tests

```python
async def test_service_versioning():
    sdk = ServiceSDK()
    
    # Test version-aware service calls
    v1_users = await sdk.call_service(
        "user-service", "GET", "/users", version="1.0"
    )
    v2_users = await sdk.call_service(
        "user-service", "GET", "/users", version="2.0"
    )
    
    assert len(v1_users) > 0
    assert len(v2_users) > 0
    assert "first_name" in v2_users[0]  # v2 specific field
```

## Migration Guide

### From Unversioned to Versioned API

1. **Add version manager to your application:**

```python
from msfw.core.versioning import version_manager

version_manager.add_version("1.0")  # Mark current API as v1.0
```

2. **Add versioning middleware:**

```python
from msfw.middleware.versioning import create_versioning_middleware

middleware = create_versioning_middleware(version_manager)
for middleware_class, kwargs in middleware:
    app.add_middleware(middleware_class, **kwargs)
```

3. **Convert existing routes:**

```python
# Before
@app.get("/users")
async def get_users():
    return users

# After
@get("/users", version="1.0")
async def get_users_v1():
    return users
```

4. **Plan your v2.0 migration:**

```python
# Add v2.0 with improvements
@get("/users", version="2.0")
async def get_users_v2():
    return enhanced_users

# Deprecate v1.0
version_manager.deprecate_version("1.0", "Use v2.0 for enhanced features")
```

## Complete Example

See `examples/versioned_api_example.py` for a complete working example that demonstrates:

- Multiple API versions (v1.0 and v2.0) using the unified decorator API
- Data model evolution (UserV1 vs UserV2)
- Deprecation handling with sunset dates
- URL path versioning strategy (`/api/v1.0/users`, `/api/v2.0/users`)
- Automatic route registration with `version_manager.apply_routes_to_app()`
- Service communication with version-aware calls
- Backward compatibility patterns
- Testing approaches

Run the example:
```bash
uv run python examples/versioned_api_example.py
```

Then test the versioned endpoints:
```bash
# API v1.0 (deprecated)
curl http://localhost:8000/api/v1.0/users

# API v2.0 (current)
curl http://localhost:8000/api/v2.0/users
```

## Performance Considerations

- **Route Caching**: Version resolution is cached for performance
- **Middleware Ordering**: Versioning middleware should be early in the stack
- **Service Discovery**: Version filtering happens at the registry level
- **Memory Usage**: Each version maintains separate route registrations

## Troubleshooting

### Common Issues

1. **Routes not found**: Ensure version is properly registered
2. **Middleware order**: Version middleware should be before auth/other middleware
3. **Service discovery**: Check version compatibility settings
4. **Headers missing**: Verify middleware configuration

### Debugging

Enable debug logging to see version resolution:

```python
import logging
logging.getLogger("msfw.core.versioning").setLevel(logging.DEBUG)
logging.getLogger("msfw.middleware.versioning").setLevel(logging.DEBUG)
``` 