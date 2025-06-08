# OpenAPI/Swagger Support in MSFW

MSFW provides comprehensive OpenAPI/Swagger support with advanced features for API documentation, versioning, and schema management.

## Features

- 🔧 **Comprehensive Configuration** - Full control over OpenAPI schema generation
- 📋 **API Versioning Integration** - Version-aware documentation generation
- 🎨 **Custom Documentation** - Enhanced Swagger UI and ReDoc interfaces
- 📤 **Schema Export** - Export schemas in JSON and YAML formats
- 🏷️ **Smart Tagging** - Automatic tag generation for versions and endpoints
- 🛠️ **CLI Tools** - Command-line tools for schema management
- 🔄 **Auto-generation** - Automatic OpenAPI schema generation with enhanced metadata

## Quick Start

### 1. Basic Setup

The OpenAPI features are enabled by default. Configure them in your application:

```python
from msfw import MSFWApplication, load_config

async def main():
    config = load_config()
    
    # Configure OpenAPI settings
    config.openapi.title = "My API"
    config.openapi.description = "A comprehensive API built with MSFW"
    config.openapi.contact = {
        "name": "API Team",
        "email": "api@example.com"
    }
    
    app = MSFWApplication(config)
    await app.initialize()
    await app.run()
```

### 2. Creating Documented Endpoints

Use MSFW decorators with OpenAPI metadata:

```python
from msfw import get, post, put, delete
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

@get(
    "/users",
    tags=["users"],
    summary="List Users",
    description="Get a list of all users in the system",
    response_model=List[User]
)
async def get_users():
    """Get all users."""
    return [{"id": 1, "name": "John", "email": "john@example.com"}]
```

### 3. Versioned Documentation

Create version-specific documentation:

```python
@get(
    "/api/v1/users",
    version="1.0",
    tags=["users"],
    summary="List Users (v1.0)",
    description="Legacy user listing endpoint",
    response_model=List[UserV1]
)
async def get_users_v1():
    """Get users in v1.0 format."""
    return users_v1_format

@get(
    "/api/v2/users", 
    version="2.0",
    tags=["users"],
    summary="List Users (v2.0)",
    description="Enhanced user listing with profiles",
    response_model=List[UserV2]
)
async def get_users_v2():
    """Get users in v2.0 format with enhanced profiles."""
    return users_v2_format
```

## Configuration

### OpenAPI Configuration Options

```python
from msfw import Config, OpenAPIConfig

config = Config()

# Basic settings
config.openapi.enabled = True
config.openapi.title = "My API"
config.openapi.description = "API description with markdown support"
config.openapi.version = "1.0.0"

# URL customization
config.openapi.docs_url = "/docs"
config.openapi.redoc_url = "/redoc"
config.openapi.openapi_url = "/openapi.json"

# Metadata
config.openapi.contact = {
    "name": "API Support",
    "url": "https://example.com/support",
    "email": "support@example.com"
}

config.openapi.license_info = {
    "name": "MIT",
    "url": "https://opensource.org/licenses/MIT"
}

config.openapi.terms_of_service = "https://example.com/terms"

# Tags for organizing endpoints
config.openapi.tags_metadata = [
    {
        "name": "users",
        "description": "User management operations",
        "externalDocs": {
            "description": "User API docs",
            "url": "https://example.com/docs/users"
        }
    }
]

# Security schemes
config.openapi.security_schemes = {
    "bearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
    },
    "apiKey": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key"
    }
}

# Export settings
config.openapi.export_formats = ["json", "yaml"]
config.openapi.export_path = "./openapi"
config.openapi.auto_export = True
```

### Environment-based Configuration

Configure via environment variables:

```bash
# .env file
OPENAPI_TITLE="My Production API"
OPENAPI_DESCRIPTION="Production API documentation"
OPENAPI_DOCS_URL="/documentation"
OPENAPI_ENABLED=true
```

## Advanced Features

### 1. Version-specific Documentation

Generate separate documentation for each API version:

```python
# Access version-specific docs
GET /docs?version=1.0  # Swagger UI for v1.0
GET /docs?version=2.0  # Swagger UI for v2.0
GET /redoc?version=1.0 # ReDoc for v1.0
GET /openapi.json?version=2.0  # Schema for v2.0
```

### 2. Custom OpenAPI Manager

For advanced customization:

```python
from msfw import OpenAPIManager, create_openapi_manager

# Create custom manager
openapi_manager = create_openapi_manager(config)

# Add custom tags
openapi_manager.add_tag_metadata(
    "admin", 
    "Administrative operations",
    external_docs={"url": "https://example.com/admin-docs"}
)

# Add custom schema components
openapi_manager.add_custom_schema_component(
    "schemas",
    "ErrorResponse",
    {
        "type": "object",
        "properties": {
            "error": {"type": "string"},
            "code": {"type": "integer"}
        }
    }
)
```

### 3. Enhanced Route Documentation

Automatic enhancement of route metadata:

```python
@get(
    "/api/v2/users/{id}",
    version="2.0",
    deprecated=False,  # Will add deprecation warnings automatically
    tags=["users"]     # Will auto-add version tags
)
async def get_user(id: int):
    """
    Get user by ID.
    
    This endpoint automatically gets enhanced with:
    - Version tags (v2.0) 
    - Auto-generated summary
    - Version info in description
    """
    pass
```

### 4. Schema Export

Export OpenAPI schemas for external tools:

```python
# Programmatic export
exported = openapi_manager.export_schema(
    app,
    formats=["json", "yaml"],
    output_dir="./schemas",
    version="2.0"
)
```

## CLI Commands

MSFW provides CLI commands for OpenAPI management:

### Export OpenAPI Schema

```bash
# Export in JSON format
msfw export-openapi --format json

# Export in YAML format  
msfw export-openapi --format yaml

# Export both formats
msfw export-openapi --format both

# Export specific version
msfw export-openapi --version 2.0 --format json

# Custom output directory
msfw export-openapi --output-dir ./docs/schemas --format both
```

### List API Versions

```bash
# Show all available API versions
msfw list-versions
```

Output:
```
                API Versions                
┏━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Version ┃ Status    ┃ Deprecation Message  ┃
┡━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ 1.0     │ Active    │ -                    │
│ 2.0     │ Active    │ -                    │
└─────────┴───────────┴──────────────────────┘

📄 Documentation endpoints:
   Swagger UI: http://0.0.0.0:8000/docs
   ReDoc: http://0.0.0.0:8000/redoc
   OpenAPI Schema: http://0.0.0.0:8000/openapi.json
   Version List: http://0.0.0.0:8000/api/versions
```

## API Endpoints

MSFW automatically creates several documentation endpoints:

### Documentation Interfaces

- `GET /docs` - Swagger UI interface
- `GET /docs?version=X.Y` - Version-specific Swagger UI
- `GET /redoc` - ReDoc interface  
- `GET /redoc?version=X.Y` - Version-specific ReDoc

### Schema Endpoints

- `GET /openapi.json` - OpenAPI schema in JSON format
- `GET /openapi.json?version=X.Y` - Version-specific schema
- `GET /api/versions` - List all available API versions

### Version Information

```json
{
  "versions": [
    {
      "version": "1.0",
      "deprecated": false,
      "docs_url": "/docs?version=1.0",
      "openapi_url": "/openapi.json?version=1.0"
    },
    {
      "version": "2.0", 
      "deprecated": false,
      "docs_url": "/docs?version=2.0",
      "openapi_url": "/openapi.json?version=2.0"
    }
  ]
}
```

## Best Practices

### 1. Organize with Tags

Use consistent tagging for better organization:

```python
# Group related endpoints
@get("/users", tags=["users", "management"])
@post("/users", tags=["users", "management"])

# Version-specific grouping (auto-added)
@get("/api/v1/users", version="1.0", tags=["users"])  # Gets "v1.0" tag
@get("/api/v2/users", version="2.0", tags=["users"])  # Gets "v2.0" tag
```

### 2. Provide Rich Descriptions

Use markdown in descriptions:

```python
@get(
    "/users",
    description="""
    Get a list of users with optional filtering.
    
    ## Filtering Options
    
    - `active`: Filter by active status
    - `department`: Filter by department
    
    ## Example
    
    ```
    GET /users?active=true&department=engineering
    ```
    """
)
async def get_users():
    pass
```

### 3. Use Pydantic Models

Always define Pydantic models for request/response schemas:

```python
from pydantic import BaseModel, Field
from typing import Optional

class UserCreate(BaseModel):
    """Schema for creating a new user."""
    name: str = Field(..., description="Full name of the user")
    email: str = Field(..., description="Email address")
    department: Optional[str] = Field(None, description="User's department")

@post("/users", response_model=User)
async def create_user(user_data: UserCreate):
    """Create a new user with the provided information."""
    pass
```

### 4. Handle Deprecation Gracefully

```python
@get(
    "/api/v1/legacy-endpoint",
    version="1.0",
    deprecated=True,
    description="This endpoint is deprecated. Use /api/v2/new-endpoint instead."
)
async def legacy_endpoint():
    """Legacy endpoint - use v2 instead."""
    pass
```

### 5. Security Documentation

Document security requirements:

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@get(
    "/admin/users",
    dependencies=[Depends(security)],
    tags=["admin"],
    description="Admin-only endpoint requiring JWT authentication"
)
async def admin_get_users():
    """Get users (admin only)."""
    pass
```

## Integration with MSFW Features

### With Modules

```python
from msfw import Module
from fastapi import APIRouter

class UserModule(Module):
    def register_routes(self, router: APIRouter) -> None:
        @router.get(
            "/users",
            tags=[self.name, "management"],
            summary=f"List users ({self.name} module)"
        )
        async def get_users():
            return {"module": self.name}
```

### With Plugins

```python
from msfw import Plugin

class DocumentationPlugin(Plugin):
    async def setup(self, config):
        # Enhance OpenAPI with plugin-specific metadata
        if hasattr(self.app, 'openapi_manager'):
            self.app.openapi_manager.add_tag_metadata(
                self.name,
                f"Endpoints provided by {self.name} plugin"
            )
```

### With Service Communication

Document service-to-service APIs:

```python
@get(
    "/api/internal/health",
    tags=["internal", "monitoring"],
    description="Internal health check for service discovery",
    include_in_schema=False  # Hide from public docs
)
async def internal_health():
    """Internal health endpoint."""
    pass
```

## Examples

See the enhanced `main.py` for a complete example demonstrating:

- Basic and versioned endpoints
- Comprehensive OpenAPI configuration
- Custom tags and metadata
- Pydantic models for documentation
- CLI integration

Run the demo:

```bash
python main.py
```

Then visit:
- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/redoc - ReDoc
- http://localhost:8000/api/versions - Version information

## Troubleshooting

### Common Issues

1. **Missing Documentation**: Ensure endpoints have proper type hints and Pydantic models
2. **Version Conflicts**: Check version manager configuration
3. **Export Failures**: Verify output directory permissions
4. **Missing Tags**: Check if version tags are being auto-generated

### Debug Mode

Enable debug mode for more verbose output:

```python
config.debug = True
config.openapi.include_deprecated_endpoints = True
```

This comprehensive OpenAPI support makes MSFW ideal for building well-documented, version-aware APIs with professional documentation interfaces. 