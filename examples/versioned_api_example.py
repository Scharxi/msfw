"""
Example demonstrating API versioning in MSFW.

This example shows how to:
1. Create versioned API endpoints
2. Handle version deprecation
3. Use different versioning strategies
4. Implement backward compatibility
"""

from typing import List, Optional
from datetime import datetime

from fastapi import Request, HTTPException, Depends
from pydantic import BaseModel

from msfw import (
    MSFWApplication, Config, Module, 
    route, get, post, put, delete,
    VersionedRouter, create_v1_router, create_v2_router,
    APIVersionManager, VersioningStrategy, VersionInfo,
    api_version, version_since, version_until, version_evolution
)


# Data models for different API versions
class UserV1(BaseModel):
    """User model for API v1."""
    id: int
    name: str
    email: str
    created_at: datetime


class UserV2(BaseModel):
    """User model for API v2 with additional fields."""
    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @property
    def name(self) -> str:
        """Backward compatibility property."""
        return f"{self.first_name} {self.last_name}"


class CreateUserV1(BaseModel):
    name: str
    email: str


class CreateUserV2(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None


class UpdateUserV1(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class UpdateUserV2(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


# Mock data storage
users_db = [
    {
        "id": 1,
        "first_name": "John",
        "last_name": "Doe", 
        "email": "john@example.com",
        "phone": "+1234567890",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    },
    {
        "id": 2,
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@example.com", 
        "phone": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
]


class UserAPIModule(Module):
    """Module demonstrating versioned user API."""
    
    @property
    def name(self) -> str:
        return "user_api"
    
    @property
    def version(self) -> str:
        return "2.0.0"
    
    @property
    def description(self) -> str:
        return "User API with versioning support"
    
    def _convert_user_to_v1(self, user_data: dict) -> UserV1:
        """Convert internal user data to v1 format."""
        return UserV1(
            id=user_data["id"],
            name=f"{user_data['first_name']} {user_data['last_name']}",
            email=user_data["email"],
            created_at=user_data["created_at"]
        )
    
    def _convert_user_to_v2(self, user_data: dict) -> UserV2:
        """Convert internal user data to v2 format."""
        return UserV2(**user_data)
    
    def _find_user_by_id(self, user_id: int) -> Optional[dict]:
        """Find user by ID."""
        return next((user for user in users_db if user["id"] == user_id), None)
    
    def register_routes(self, router):
        """Register versioned API routes."""
        
        # =================== API Version 1.0 Routes ===================
        
        @get("/users", version="1.0", 
             summary="Get all users (v1)", 
             response_model=List[UserV1],
             deprecated=True)
        @version_until("2.0", "Use /api/v2/users for enhanced user data")
        async def get_users_v1(request: Request):
            """Get all users - API v1 format."""
            return [self._convert_user_to_v1(user) for user in users_db]
        
        @get("/users/{user_id}", version="1.0",
             summary="Get user by ID (v1)",
             response_model=UserV1,
             deprecated=True)
        async def get_user_v1(user_id: int, request: Request):
            """Get user by ID - API v1 format."""
            user = self._find_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return self._convert_user_to_v1(user)
        
        @post("/users", version="1.0",
              summary="Create user (v1)",
              response_model=UserV1,
              deprecated=True)
        async def create_user_v1(user_data: CreateUserV1, request: Request):
            """Create new user - API v1."""
            # Split name into first and last name
            name_parts = user_data.name.split(" ", 1)
            new_user = {
                "id": max([u["id"] for u in users_db]) + 1,
                "first_name": name_parts[0],
                "last_name": name_parts[1] if len(name_parts) > 1 else "",
                "email": user_data.email,
                "phone": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            users_db.append(new_user)
            return self._convert_user_to_v1(new_user)
        
        @put("/users/{user_id}", version="1.0",
             summary="Update user (v1)",
             response_model=UserV1,
             deprecated=True)
        async def update_user_v1(user_id: int, user_data: UpdateUserV1, request: Request):
            """Update user - API v1."""
            user = self._find_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            if user_data.name:
                name_parts = user_data.name.split(" ", 1)
                user["first_name"] = name_parts[0]
                user["last_name"] = name_parts[1] if len(name_parts) > 1 else ""
            
            if user_data.email:
                user["email"] = user_data.email
            
            user["updated_at"] = datetime.now()
            return self._convert_user_to_v1(user)
        
        @delete("/users/{user_id}", version="1.0",
                summary="Delete user (v1)",
                deprecated=True)
        async def delete_user_v1(user_id: int, request: Request):
            """Delete user - API v1."""
            user = self._find_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            users_db.remove(user)
            return {"message": "User deleted successfully"}
        
        # =================== API Version 2.0 Routes ===================
        
        @get("/users", version="2.0",
             summary="Get all users (v2)",
             response_model=List[UserV2])
        @version_since("2.0")
        @version_evolution(
            changes={
                "2.0": "Added first_name, last_name, phone, updated_at fields"
            }
        )
        async def get_users_v2(request: Request):
            """Get all users - API v2 format with enhanced data."""
            return [self._convert_user_to_v2(user) for user in users_db]
        
        @get("/users/{user_id}", version="2.0",
             summary="Get user by ID (v2)",
             response_model=UserV2)
        async def get_user_v2(user_id: int, request: Request):
            """Get user by ID - API v2 format."""
            user = self._find_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return self._convert_user_to_v2(user)
        
        @post("/users", version="2.0",
              summary="Create user (v2)",
              response_model=UserV2)
        async def create_user_v2(user_data: CreateUserV2, request: Request):
            """Create new user - API v2 with enhanced fields."""
            new_user = {
                "id": max([u["id"] for u in users_db]) + 1,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "email": user_data.email,
                "phone": user_data.phone,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            users_db.append(new_user)
            return self._convert_user_to_v2(new_user)
        
        @put("/users/{user_id}", version="2.0",
             summary="Update user (v2)",
             response_model=UserV2)
        async def update_user_v2(user_id: int, user_data: UpdateUserV2, request: Request):
            """Update user - API v2 with enhanced fields."""
            user = self._find_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            if user_data.first_name:
                user["first_name"] = user_data.first_name
            if user_data.last_name:
                user["last_name"] = user_data.last_name
            if user_data.email:
                user["email"] = user_data.email
            if user_data.phone is not None:
                user["phone"] = user_data.phone
            
            user["updated_at"] = datetime.now()
            return self._convert_user_to_v2(user)
        
        @delete("/users/{user_id}", version="2.0",
                summary="Delete user (v2)")
        async def delete_user_v2(user_id: int, request: Request):
            """Delete user - API v2."""
            user = self._find_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            users_db.remove(user)
            return {
                "message": "User deleted successfully",
                "deleted_at": datetime.now(),
                "api_version": "2.0"
            }
        
        # =================== Version Information Routes ===================
        
        @route("/version", methods=["GET"], version="1.0")
        async def get_api_version_v1(request: Request):
            """Get API version information - v1."""
            return {
                "api_version": "1.0",
                "deprecated": True,
                "message": "Please migrate to API v2.0",
                "migration_guide": "/docs/migration"
            }
        
        @route("/version", methods=["GET"], version="2.0")
        async def get_api_version_v2(request: Request):
            """Get API version information - v2."""
            return {
                "api_version": "2.0",
                "status": "current",
                "features": [
                    "Enhanced user data model",
                    "Phone number support",
                    "Separate first/last names",
                    "Update timestamps"
                ]
            }


# Alternative approach using VersionedRouter
def create_user_api_with_routers():
    """Alternative approach using VersionedRouter classes."""
    
    # Create v1 router (deprecated)
    v1_router = create_v1_router(deprecated=True)
    
    @v1_router.get("/users")
    async def get_users_v1_alt():
        return [{"id": 1, "name": "John Doe", "email": "john@example.com"}]
    
    # Create v2 router (current)
    v2_router = create_v2_router()
    
    @v2_router.get("/users")
    async def get_users_v2_alt():
        return [{"id": 1, "first_name": "John", "last_name": "Doe", "email": "john@example.com"}]
    
    return v1_router, v2_router


def create_app_with_versioning():
    """Create MSFW application with API versioning."""
    
    # Configure API versioning
    from msfw.core.versioning import version_manager
    from msfw.middleware.versioning import create_versioning_middleware
    
    # Setup version manager
    version_manager.strategy = VersioningStrategy.URL_PATH
    version_manager.default_version = VersionInfo.from_string("2.0")
    version_manager.add_version("1.0")
    version_manager.add_version("2.0")
    version_manager.deprecate_version("1.0", "API v1.0 is deprecated. Please use v2.0")
    
    # Create application
    config = Config(
        app_name="versioned-user-api",
        version="2.0.0", 
        debug=True,
        host="0.0.0.0",
        port=8000
    )
    
    app = MSFWApplication(config)
    
    # Add user API module first
    user_module = UserAPIModule()
    app.add_module(user_module)
    
    # Initialize the app to create the FastAPI instance
    async def init_app():
        await app.initialize()
        
        # Add versioning middleware after initialization
        versioning_middleware = create_versioning_middleware(
            version_manager=version_manager,
            enable_deprecation_warnings=True,
            enable_version_info_headers=True,
            enable_content_negotiation=True
        )
        
        for middleware_class, middleware_kwargs in versioning_middleware:
            app.app.add_middleware(middleware_class, **middleware_kwargs)
        
        # Apply versioned routes to the FastAPI app
        version_manager.apply_routes_to_app(app.app)
    
    # Store the initialization function to call later
    app._init_versioning = init_app
    
    return app


# Example usage functions
async def example_service_calls():
    """Examples of making versioned service calls."""
    from msfw import ServiceSDK
    
    sdk = ServiceSDK()
    
    # Call API v1 (deprecated)
    users_v1 = await sdk.call_service(
        service_name="user-api",
        method="GET",
        path="/api/v1/users",
        version="1.0"
    )
    
    # Call API v2 (current)
    users_v2 = await sdk.call_service(
        service_name="user-api", 
        method="GET",
        path="/api/v2/users",
        version="2.0"
    )
    
    # Call with header-based versioning
    user_v2 = await sdk.call_service(
        service_name="user-api",
        method="GET", 
        path="/users/1",
        version="2.0"  # Will be sent as X-API-Version header
    )
    
    print(f"V1 Users: {users_v1}")
    print(f"V2 Users: {users_v2}")
    print(f"V2 User: {user_v2}")


if __name__ == "__main__":
    import uvicorn
    
    # Create the versioned application
    app = create_app_with_versioning()
    
    # Initialize and run
    async def startup():
        if hasattr(app, '_init_versioning'):
            await app._init_versioning()
        else:
            await app.initialize()
    
    import asyncio
    asyncio.run(startup())
    
    print("Starting versioned API server...")
    print("Available endpoints:")
    print("  - GET /api/v1/users (deprecated)")
    print("  - GET /api/v2/users (current)")
    print("  - POST /api/v1/users (deprecated)")
    print("  - POST /api/v2/users (current)")
    print("  - GET /api/v1/version")
    print("  - GET /api/v2/version")
    print("\nTry calling with different version headers:")
    print("  curl -H 'X-API-Version: 1.0' http://localhost:8000/users")
    print("  curl -H 'X-API-Version: 2.0' http://localhost:8000/users")
    
    uvicorn.run(app.app, host="0.0.0.0", port=8000) 