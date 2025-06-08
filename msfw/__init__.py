"""
MSFW - Modular Microservices Framework
====================================

A highly modular and extensible framework for building microservices with FastAPI, 
Pydantic, and SQLAlchemy.

Features:
- Plugin-based architecture
- Configurable components
- Auto-discovery of modules
- Built-in authentication and authorization
- Database management with migrations
- Monitoring and observability
- Task queue integration
- Easy deployment and scaling
"""

from msfw.core.application import MSFWApplication
from msfw.core.config import Config, load_config
from msfw.core.database import Database
from msfw.core.plugin import Plugin, PluginManager
from msfw.core.module import Module, ModuleManager
from msfw.decorators import (
    route, get, post, put, delete, patch, middleware, event_handler,
    service_call, retry_on_failure, circuit_breaker, 
    health_check, cached_service_call, service_interface
)
from msfw.decorators.versioning import (
    api_version, version_compatibility, version_since, version_until,
    version_evolution, VersionedRouter, create_v1_router, create_v2_router, 
    create_versioned_router
)
from msfw.core.versioning import (
    APIVersionManager, VersionInfo, VersioningStrategy, VersionedAPIRouter,
    version_manager
)
from msfw.middleware.versioning import (
    APIVersioningMiddleware, ContentNegotiationMiddleware, VersionRoutingMiddleware,
    create_versioning_middleware
)
from msfw.sdk import ServiceSDK, ServiceClient, call_service, register_service, get_service_client
from msfw.core.service_registry import ServiceRegistry, ServiceInstance, ServiceEndpoint
from msfw.core.service_client import CircuitBreakerConfig, ServiceClientError
from msfw.core.types import (
    HTTPMethod, ServiceCallResult, ServiceCallConfig,
    TypedServiceError, ServiceValidationError, ServiceMethodDefinition
)

__version__ = "0.1.0"
__all__ = [
    "MSFWApplication",
    "Config", 
    "load_config",
    "Database",
    "Plugin",
    "PluginManager",
    "Module",
    "ModuleManager",
    "route",
    "get",
    "post", 
    "put",
    "delete",
    "patch",
    "middleware", 
    "event_handler",
    # Service Communication SDK
    "ServiceSDK",
    "ServiceClient", 
    "ServiceRegistry",
    "ServiceInstance",
    "ServiceEndpoint",
    "CircuitBreakerConfig",
    "ServiceClientError",
    # Service Communication Types
    "HTTPMethod",
    "ServiceCallResult",
    "ServiceCallConfig", 
    "TypedServiceError",
    "ServiceValidationError",
    "ServiceMethodDefinition",
    # Service Decorators
    "service_call",
    "retry_on_failure",
    "circuit_breaker",
    "health_check", 
    "cached_service_call",
    "service_interface",
    # API Versioning
    "APIVersionManager",
    "VersionInfo",
    "VersioningStrategy",
    "VersionedAPIRouter",
    "version_manager",
    "api_version",
    "version_compatibility",
    "version_since",
    "version_until", 
    "version_evolution",
    "VersionedRouter",
    "create_v1_router",
    "create_v2_router",
    "create_versioned_router",
    # Versioning Middleware
    "APIVersioningMiddleware",
    "ContentNegotiationMiddleware", 
    "VersionRoutingMiddleware",
    "create_versioning_middleware",
    # Convenience functions
    "call_service",
    "register_service",
    "get_service_client",
] 