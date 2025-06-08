"""
MSFW Framework Demo Application
==============================

This demonstrates the key features of the MSFW (Modular Microservices Framework):
- Modular architecture with auto-discovery
- Plugin system with hooks
- Configurable components
- Database integration with SQLAlchemy
- Monitoring and observability
- **OpenAPI/Swagger documentation with versioning support**
- Easy extensibility
"""

import asyncio
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

from msfw import MSFWApplication, load_config, get, post, put, delete


# Pydantic models for OpenAPI documentation
class User(BaseModel):
    id: int
    name: str
    email: str
    active: bool = True


class UserCreate(BaseModel):
    name: str
    email: str


class UserCreateV2(BaseModel):
    first_name: str
    last_name: str
    email: str
    profile: Optional[dict] = None


class UserV2(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    profile: Optional[dict] = None
    active: bool = True


def main():
    """Main application entry point."""
    print("🚀 Starting MSFW Demo Application with OpenAPI Support")
    
    # Load configuration with environment variable support
    config = load_config()
    
    # Override specific settings for demo
    config.app_name = "MSFW Demo API"
    config.version = "1.0.0" 
    config.description = "A comprehensive demo of the MSFW framework with OpenAPI/Swagger documentation"
    config.debug = True
    config.database.url = "sqlite+aiosqlite:///./demo.db"
    config.database.echo = True
    
    # Configure OpenAPI settings
    config.openapi.title = "MSFW Demo API Documentation"
    config.openapi.description = """
    ## Welcome to MSFW Demo API
    
    This API demonstrates the capabilities of the **Modular Microservices Framework (MSFW)** including:
    
    - 🚀 **Modular Architecture** - Plugin and module system
    - 📋 **API Versioning** - Multiple API versions with backward compatibility
    - 📄 **OpenAPI Integration** - Comprehensive documentation
    - 🔒 **Security** - Built-in authentication and authorization
    - 📊 **Monitoring** - Health checks and metrics
    - 🛠️ **Easy Configuration** - Environment-based settings
    
    ### API Versions
    
    - **v1.0** - Initial API with basic user management
    - **v2.0** - Enhanced API with extended user profiles
    
    ### Getting Started
    
    1. Check the [health endpoint](/health) to verify the service is running
    2. Explore the available API versions at [/api/versions](/api/versions)
    3. Try the demo endpoints below
    """
    config.openapi.contact = {
        "name": "MSFW Team",
        "url": "https://github.com/your-org/msfw",
        "email": "msfw@example.com"
    }
    config.openapi.license_info = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
    config.openapi.tags_metadata = [
        {
            "name": "demo",
            "description": "Demo endpoints showing framework capabilities"
        },
        {
            "name": "users",
            "description": "User management operations"
        },
        {
            "name": "v1.0",
            "description": "API Version 1.0 endpoints"
        },
        {
            "name": "v2.0", 
            "description": "API Version 2.0 endpoints with enhanced features"
        }
    ]
    
    # Create modules and plugins directories if they don't exist
    Path("modules").mkdir(exist_ok=True)
    Path("plugins").mkdir(exist_ok=True)
    
    # Define demo endpoint function that will be registered later
    async def demo_endpoint():
        """Demo endpoint showing framework capabilities."""
        return {
            "message": "Welcome to MSFW!",
            "framework": "Modular Microservices Framework",
            "features": [
                "Modular architecture",
                "Plugin system", 
                "Auto-discovery",
                "Database integration",
                "Monitoring & observability",
                "Easy configuration",
                "FastAPI integration",
                "SQLAlchemy support",
                "OpenAPI/Swagger documentation",
                "API versioning"
            ],
            "endpoints": {
                "health": "/health",
                "metrics": "/metrics", 
                "info": "/info",
                "docs": "/docs",
                "redoc": "/redoc",
                "versions": "/api/versions",
                "demo": "/demo"
            }
        }
    
    # Versioned API endpoints demonstrating API evolution
    
    # Version 1.0 - Basic user management
    @get(
        "/users",
        version="1.0",
        tags=["users", "v1.0"],
        summary="List Users (v1.0)",
        description="Get a list of all users in the system (v1.0 format)",
        response_model=List[User]
    )
    async def get_users_v1():
        """Get all users (v1.0 format)."""
        return [
            {"id": 1, "name": "John Doe", "email": "john@example.com", "active": True},
            {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "active": True}
        ]
    
    @get(
        "/users/{user_id}",
        version="1.0",
        tags=["users", "v1.0"],
        summary="Get User (v1.0)",
        description="Get a specific user by ID (v1.0 format)",
        response_model=User
    )
    async def get_user_v1(user_id: int):
        """Get a specific user (v1.0 format)."""
        return {"id": user_id, "name": "John Doe", "email": "john@example.com", "active": True}
    
    @post(
        "/users",
        version="1.0",
        tags=["users", "v1.0"],
        summary="Create User (v1.0)",
        description="Create a new user (v1.0 format)",
        response_model=User,
        status_code=201
    )
    async def create_user_v1(user_data: UserCreate):
        """Create a new user (v1.0 format)."""
        return {
            "id": 999,
            "name": user_data.name,
            "email": user_data.email,
            "active": True
        }
    
    # Version 2.0 - Enhanced user management with profiles
    @get(
        "/users",
        version="2.0",
        tags=["users", "v2.0"],
        summary="List Users (v2.0)",
        description="Get a list of all users with enhanced profile information (v2.0 format)",
        response_model=List[UserV2]
    )
    async def get_users_v2():
        """Get all users (v2.0 format with enhanced profiles)."""
        return [
            {
                "id": 1,
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "profile": {"department": "Engineering", "role": "Senior Developer"},
                "active": True
            },
            {
                "id": 2,
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane@example.com",
                "profile": {"department": "Product", "role": "Product Manager"},
                "active": True
            }
        ]
    
    @get(
        "/users/{user_id}",
        version="2.0",
        tags=["users", "v2.0"],
        summary="Get User (v2.0)",
        description="Get a specific user by ID with enhanced profile (v2.0 format)",
        response_model=UserV2
    )
    async def get_user_v2(user_id: int):
        """Get a specific user (v2.0 format with enhanced profile)."""
        return {
            "id": user_id,
            "first_name": "John",
            "last_name": "Doe", 
            "email": "john@example.com",
            "profile": {"department": "Engineering", "role": "Senior Developer"},
            "active": True
        }
    
    @post(
        "/users",
        version="2.0",
        tags=["users", "v2.0"],
        summary="Create User (v2.0)",
        description="Create a new user with enhanced profile support (v2.0 format)",
        response_model=UserV2,
        status_code=201
    )
    async def create_user_v2(user_data: UserCreateV2):
        """Create a new user (v2.0 format with enhanced profile)."""
        return {
            "id": 999,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "email": user_data.email,
            "profile": user_data.profile or {},
            "active": True
        }
    
    @put(
        "/users/{user_id}",
        version="2.0",
        tags=["users", "v2.0"],
        summary="Update User (v2.0)",
        description="Update an existing user with profile information (v2.0 only)",
        response_model=UserV2
    )
    async def update_user_v2(user_id: int, user_data: UserCreateV2):
        """Update an existing user (v2.0 format)."""
        return {
            "id": user_id,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "email": user_data.email,
            "profile": user_data.profile or {},
            "active": True
        }
    
    @delete(
        "/users/{user_id}",
        version="2.0",
        tags=["users", "v2.0"],
        summary="Delete User (v2.0)",
        description="Delete a user by ID (v2.0 only)",
        status_code=204
    )
    async def delete_user_v2(user_id: int):
        """Delete a user (v2.0 only)."""
        return {"message": f"User {user_id} deleted successfully"}
    
    # Create application AFTER all routes are defined
    app = MSFWApplication(config)
    
    # Add a custom demo route after initialization
    async def setup_demo_route():
        await app.initialize()
        fastapi_app = app.get_app()
        
        # Add demo endpoint as a non-versioned route
        fastapi_app.get(
            "/demo",
            tags=["demo"],
            summary="Framework Demo",
            description="Demo endpoint showing MSFW framework capabilities",
            response_model=dict
        )(demo_endpoint)
        
        return fastapi_app
    
    # Initialize app
    import asyncio
    asyncio.run(setup_demo_route())
    
    print("\n📋 Available endpoints:")
    print("  - Demo: http://localhost:8000/demo")
    print("  - Health: http://localhost:8000/health") 
    print("  - Metrics: http://localhost:8000/metrics")
    print("  - Info: http://localhost:8000/info")
    print("\n📄 API Documentation:")
    print("  - Swagger UI: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")
    print("  - OpenAPI Schema: http://localhost:8000/openapi.json")
    print("  - API Versions: http://localhost:8000/api/versions")
    print("\n🎯 Try versioned endpoints:")
    print("  - Users v1.0: http://localhost:8000/api/v1.0/users")
    print("  - Users v2.0: http://localhost:8000/api/v2.0/users")
    print("\n🛠️ CLI commands:")
    print("  msfw export-openapi --format json")
    print("  msfw export-openapi --format yaml")
    print("  msfw list-versions")
    print()
    
    # Run the application
    app.run_sync(port=8000)


if __name__ == "__main__":
    main()
