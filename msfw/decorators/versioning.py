"""Versioning decorators for MSFW applications."""

import functools
from typing import Any, Callable, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from msfw.core.versioning import (
    APIVersionManager, VersionInfo, VersioningStrategy, 
    version_manager as default_version_manager
)


def versioned_route(
    path: str,
    version: str,
    methods: Optional[List[str]] = None,
    *,
    deprecated: bool = False,
    tags: Optional[List[str]] = None,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    response_model: Optional[Any] = None,
    status_code: int = 200,
    dependencies: Optional[List[Depends]] = None,
    version_manager: APIVersionManager = None,
    **kwargs
):
    """
    Decorator to register a versioned route.
    
    Args:
        path: The route path
        version: API version (e.g., "1.0", "2.0", "1.2.3")
        methods: HTTP methods for this route
        deprecated: Whether this route version is deprecated
        tags: OpenAPI tags
        summary: Route summary
        description: Route description
        response_model: Pydantic model for response
        status_code: Default status code
        dependencies: FastAPI dependencies
        version_manager: Custom version manager (uses global by default)
        **kwargs: Additional FastAPI route parameters
    """
    methods = methods or ["GET"]
    vm = version_manager or default_version_manager
    
    def decorator(func: Callable) -> Callable:
        # Register the versioned route
        vm.register_versioned_route(
            path=path,
            func=func,
            methods=methods,
            version=version,
            deprecated=deprecated,
            tags=tags,
            summary=summary,
            description=description,
            response_model=response_model,
            status_code=status_code,
            dependencies=dependencies,
            **kwargs
        )
        
        # Wrap function to add version information
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if first argument is a Request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # Add version info to response if deprecated
            if deprecated and request:
                result = await func(*args, **kwargs)
                
                # If result is a dict, we can add deprecation info
                if isinstance(result, dict):
                    result["_meta"] = result.get("_meta", {})
                    result["_meta"]["deprecated"] = True
                    result["_meta"]["version"] = version
                
                return result
            
            return await func(*args, **kwargs)
        
        # Store version metadata on function
        wrapper._api_version = VersionInfo.from_string(version)
        wrapper._api_deprecated = deprecated
        wrapper._api_path = path
        
        return wrapper
    
    return decorator


def get_versioned(path: str, version: str, **kwargs):
    """Decorator for versioned GET routes."""
    return versioned_route(path, version, methods=["GET"], **kwargs)


def post_versioned(path: str, version: str, **kwargs):
    """Decorator for versioned POST routes."""
    return versioned_route(path, version, methods=["POST"], **kwargs)


def put_versioned(path: str, version: str, **kwargs):
    """Decorator for versioned PUT routes."""
    return versioned_route(path, version, methods=["PUT"], **kwargs)


def delete_versioned(path: str, version: str, **kwargs):
    """Decorator for versioned DELETE routes."""
    return versioned_route(path, version, methods=["DELETE"], **kwargs)


def patch_versioned(path: str, version: str, **kwargs):
    """Decorator for versioned PATCH routes."""
    return versioned_route(path, version, methods=["PATCH"], **kwargs)


def api_version(version: str, deprecated: bool = False):
    """
    Class decorator to mark all routes in a class with a specific version.
    
    Usage:
        @api_version("2.0")
        class UserAPIv2:
            @route("/users", methods=["GET"])
            async def get_users(self):
                return {"users": []}
    """
    def decorator(cls):
        # Add version metadata to class
        cls._api_version = VersionInfo.from_string(version)
        cls._api_deprecated = deprecated
        
        # Process all methods in the class
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            
            # Check if method has route decorator
            if hasattr(attr, '_route_info'):
                # Wrap the method with versioning
                original_method = attr
                
                @functools.wraps(original_method)
                async def versioned_method(*args, **kwargs):
                    return await original_method(*args, **kwargs)
                
                # Add version info
                versioned_method._api_version = cls._api_version
                versioned_method._api_deprecated = cls._api_deprecated
                
                setattr(cls, attr_name, versioned_method)
        
        return cls
    
    return decorator


def version_compatibility(*compatible_versions: str):
    """
    Decorator to specify version compatibility for a route.
    
    Usage:
        @version_compatibility("1.0", "1.1", "1.2")
        @versioned_route("/users", "1.2")
        async def get_users():
            return {"users": []}
    """
    def decorator(func: Callable) -> Callable:
        compatible_version_infos = [
            VersionInfo.from_string(v) for v in compatible_versions
        ]
        func._version_compatibility = compatible_version_infos
        return func
    
    return decorator


def version_since(version: str):
    """
    Decorator to specify when a feature was introduced.
    
    Usage:
        @version_since("1.2")
        @versioned_route("/users/{id}/profile", "1.2")
        async def get_user_profile(id: int):
            return {"profile": {}}
    """
    def decorator(func: Callable) -> Callable:
        func._version_since = VersionInfo.from_string(version)
        return func
    
    return decorator


def version_until(version: str, removal_message: str = None):
    """
    Decorator to specify when a feature will be removed.
    
    Usage:
        @version_until("2.0", "Use /v2/users instead")
        @versioned_route("/users", "1.0", deprecated=True)
        async def get_users_v1():
            return {"users": []}
    """
    def decorator(func: Callable) -> Callable:
        func._version_until = VersionInfo.from_string(version)
        func._removal_message = removal_message
        return func
    
    return decorator


def version_evolution(
    changes: Dict[str, str],
    breaking_changes: Optional[List[str]] = None
):
    """
    Decorator to document version evolution and changes.
    
    Usage:
        @version_evolution(
            changes={
                "1.1": "Added pagination support",
                "1.2": "Added filtering options"
            },
            breaking_changes=["2.0: Removed legacy fields"]
        )
        @versioned_route("/users", "1.2")
        async def get_users():
            return {"users": []}
    """
    def decorator(func: Callable) -> Callable:
        func._version_changes = changes
        func._breaking_changes = breaking_changes or []
        return func
    
    return decorator


class VersionedRouter:
    """
    Router wrapper that automatically handles versioning for all routes.
    """
    
    def __init__(
        self,
        version: str,
        strategy: VersioningStrategy = VersioningStrategy.URL_PATH,
        deprecated: bool = False,
        **router_kwargs
    ):
        self.version = VersionInfo.from_string(version)
        self.strategy = strategy
        self.deprecated = deprecated
        
        # Create appropriate router based on strategy
        if strategy == VersioningStrategy.URL_PATH:
            prefix = router_kwargs.get('prefix', '/api')
            prefix = f"{prefix}/{self.version.to_url_version()}"
            router_kwargs['prefix'] = prefix
        
        self.router = APIRouter(**router_kwargs)
        
        # Add version tag
        if 'tags' not in router_kwargs:
            self.router.tags = [f"API v{self.version.major}"]
    
    def route(self, path: str, **kwargs):
        """Add a route with automatic versioning."""
        return versioned_route(
            path=path,
            version=str(self.version),
            deprecated=self.deprecated,
            **kwargs
        )
    
    def get(self, path: str, **kwargs):
        """Add a GET route with automatic versioning."""
        return self.route(path, methods=["GET"], **kwargs)
    
    def post(self, path: str, **kwargs):
        """Add a POST route with automatic versioning."""
        return self.route(path, methods=["POST"], **kwargs)
    
    def put(self, path: str, **kwargs):
        """Add a PUT route with automatic versioning."""
        return self.route(path, methods=["PUT"], **kwargs)
    
    def delete(self, path: str, **kwargs):
        """Add a DELETE route with automatic versioning."""
        return self.route(path, methods=["DELETE"], **kwargs)
    
    def patch(self, path: str, **kwargs):
        """Add a PATCH route with automatic versioning."""
        return self.route(path, methods=["PATCH"], **kwargs)
    
    def include_router(self, router: APIRouter, **kwargs):
        """Include another router with version context."""
        self.router.include_router(router, **kwargs)
    
    def add_api_route(self, path: str, endpoint: Callable, **kwargs):
        """Add API route with version tracking."""
        # Register with version manager
        methods = kwargs.get('methods', ['GET'])
        default_version_manager.register_versioned_route(
            path=path,
            func=endpoint,
            methods=methods,
            version=str(self.version),
            deprecated=self.deprecated,
            **kwargs
        )
        
        self.router.add_api_route(path, endpoint, **kwargs)


# Convenience functions for creating versioned routers
def create_v1_router(**kwargs) -> VersionedRouter:
    """Create a v1 API router."""
    return VersionedRouter("1.0", **kwargs)


def create_v2_router(**kwargs) -> VersionedRouter:
    """Create a v2 API router."""
    return VersionedRouter("2.0", **kwargs)


def create_versioned_router(version: str, **kwargs) -> VersionedRouter:
    """Create a versioned router for any version."""
    return VersionedRouter(version, **kwargs) 