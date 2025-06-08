"""Decorators for MSFW applications."""

import functools
from typing import Any, Callable, Dict, List, Optional, Union

from fastapi import APIRouter, Depends
from starlette.middleware.base import BaseHTTPMiddleware


# Global registry for decorated functions
_route_registry: List[Dict[str, Any]] = []
_middleware_registry: List[Dict[str, Any]] = []
_event_registry: List[Dict[str, Any]] = []


def route(
    path: str,
    methods: Optional[List[str]] = None,
    *,
    tags: Optional[List[str]] = None,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    response_model: Optional[Any] = None,
    status_code: int = 200,
    dependencies: Optional[List[Depends]] = None,
    **kwargs
):
    """Decorator to register a route."""
    methods = methods or ["GET"]
    
    def decorator(func: Callable) -> Callable:
        _route_registry.append({
            "path": path,
            "methods": methods,
            "func": func,
            "tags": tags,
            "summary": summary,
            "description": description,
            "response_model": response_model,
            "status_code": status_code,
            "dependencies": dependencies,
            "kwargs": kwargs,
        })
        return func
    
    return decorator


def get(path: str, **kwargs):
    """Decorator for GET routes."""
    return route(path, methods=["GET"], **kwargs)


def post(path: str, **kwargs):
    """Decorator for POST routes."""
    return route(path, methods=["POST"], **kwargs)


def put(path: str, **kwargs):
    """Decorator for PUT routes."""
    return route(path, methods=["PUT"], **kwargs)


def delete(path: str, **kwargs):
    """Decorator for DELETE routes."""
    return route(path, methods=["DELETE"], **kwargs)


def patch(path: str, **kwargs):
    """Decorator for PATCH routes."""
    return route(path, methods=["PATCH"], **kwargs)


def middleware(
    middleware_class: Optional[type] = None,
    *,
    priority: int = 100,
    **kwargs
):
    """Decorator to register middleware."""
    def decorator(func_or_class: Union[Callable, type]) -> Union[Callable, type]:
        if middleware_class:
            # Using provided middleware class
            _middleware_registry.append({
                "middleware_class": middleware_class,
                "priority": priority,
                "kwargs": kwargs,
            })
            return func_or_class
        else:
            # Function-based middleware
            _middleware_registry.append({
                "middleware_class": func_or_class,
                "priority": priority,
                "kwargs": kwargs,
            })
            return func_or_class
    
    return decorator


def event_handler(event: str, priority: int = 100):
    """Decorator to register an event handler."""
    def decorator(func: Callable) -> Callable:
        _event_registry.append({
            "event": event,
            "handler": func,
            "priority": priority,
        })
        return func
    
    return decorator


def on_startup(priority: int = 100):
    """Decorator for startup event handlers."""
    return event_handler("app_startup", priority)


def on_shutdown(priority: int = 100):
    """Decorator for shutdown event handlers."""
    return event_handler("app_shutdown", priority)


def before_request(priority: int = 100):
    """Decorator for before request handlers."""
    return event_handler("before_request", priority)


def after_request(priority: int = 100):
    """Decorator for after request handlers."""
    return event_handler("after_request", priority)


def dependency(name: str):
    """Decorator to register a dependency provider."""
    def decorator(func: Callable) -> Callable:
        # Store dependency info in function
        func._msfw_dependency_name = name
        return func
    
    return decorator


def inject(dependency_name: str):
    """Decorator to inject a dependency into a function."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # This would be resolved by the DI container
            # For now, just pass through
            return await func(*args, **kwargs)
        return wrapper
    
    return decorator


class RouteRegistry:
    """Registry for managing decorated routes."""
    
    @staticmethod
    def get_routes() -> List[Dict[str, Any]]:
        """Get all registered routes."""
        return _route_registry.copy()
    
    @staticmethod
    def clear_routes():
        """Clear all registered routes."""
        _route_registry.clear()
    
    @staticmethod
    def register_routes(router: APIRouter):
        """Register all routes with a router."""
        for route_info in _route_registry:
            methods = route_info["methods"]
            path = route_info["path"]
            func = route_info["func"]
            
            route_kwargs = {
                "tags": route_info.get("tags"),
                "summary": route_info.get("summary"),
                "description": route_info.get("description"),
                "response_model": route_info.get("response_model"),
                "status_code": route_info.get("status_code", 200),
                "dependencies": route_info.get("dependencies"),
                **route_info.get("kwargs", {}),
            }
            
            # Remove None values
            route_kwargs = {k: v for k, v in route_kwargs.items() if v is not None}
            
            for method in methods:
                if method.upper() == "GET":
                    router.get(path, **route_kwargs)(func)
                elif method.upper() == "POST":
                    router.post(path, **route_kwargs)(func)
                elif method.upper() == "PUT":
                    router.put(path, **route_kwargs)(func)
                elif method.upper() == "DELETE":
                    router.delete(path, **route_kwargs)(func)
                elif method.upper() == "PATCH":
                    router.patch(path, **route_kwargs)(func)
                elif method.upper() == "HEAD":
                    router.head(path, **route_kwargs)(func)
                elif method.upper() == "OPTIONS":
                    router.options(path, **route_kwargs)(func)


class MiddlewareRegistry:
    """Registry for managing decorated middleware."""
    
    @staticmethod
    def get_middleware() -> List[Dict[str, Any]]:
        """Get all registered middleware."""
        return sorted(_middleware_registry, key=lambda x: x["priority"])
    
    @staticmethod
    def clear_middleware():
        """Clear all registered middleware."""
        _middleware_registry.clear()


class EventRegistry:
    """Registry for managing decorated event handlers."""
    
    @staticmethod
    def get_handlers() -> List[Dict[str, Any]]:
        """Get all registered event handlers."""
        return sorted(_event_registry, key=lambda x: x["priority"])
    
    @staticmethod
    def clear_handlers():
        """Clear all registered event handlers."""
        _event_registry.clear()
    
    @staticmethod
    def get_handlers_for_event(event: str) -> List[Callable]:
        """Get all handlers for a specific event."""
        return [
            item["handler"] 
            for item in _event_registry 
            if item["event"] == event
        ]


# Convenience function to reset all registries
def reset_registries():
    """Reset all decorator registries."""
    RouteRegistry.clear_routes()
    MiddlewareRegistry.clear_middleware()
    EventRegistry.clear_handlers() 