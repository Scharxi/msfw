"""API Versioning system for MSFW applications."""

import re
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass
from packaging import version as pkg_version

from fastapi import APIRouter, Request, HTTPException
from fastapi.routing import APIRoute
from pydantic import BaseModel


class VersioningStrategy(str, Enum):
    """API versioning strategies."""
    URL_PATH = "url_path"           # /api/v1/users
    HEADER = "header"               # X-API-Version: 1.0
    QUERY_PARAM = "query_param"     # ?version=1.0
    ACCEPT_HEADER = "accept_header" # Accept: application/vnd.api+json;version=1.0


@dataclass(frozen=True)
class VersionInfo:
    """Version information."""
    major: int
    minor: int
    patch: int = 0
    
    @classmethod
    def from_string(cls, version_str: str) -> "VersionInfo":
        """Create VersionInfo from version string."""
        # Handle v1, v1.0, 1.0.0 formats
        clean_version = version_str.strip().lower()
        if clean_version.startswith('v'):
            clean_version = clean_version[1:]
        
        # Parse version parts
        parts = clean_version.split('.')
        if len(parts) == 1:
            return cls(major=int(parts[0]), minor=0, patch=0)
        elif len(parts) == 2:
            return cls(major=int(parts[0]), minor=int(parts[1]), patch=0)
        elif len(parts) >= 3:
            return cls(major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2]))
        else:
            raise ValueError(f"Invalid version format: {version_str}")
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def to_url_version(self) -> str:
        """Convert to URL version format (v1, v2, etc.)."""
        return f"v{self.major}"
    
    def is_compatible_with(self, other: "VersionInfo") -> bool:
        """Check if this version is compatible with another version."""
        # Same major version is compatible
        return self.major == other.major
    
    def __eq__(self, other) -> bool:
        """Check equality."""
        if not isinstance(other, VersionInfo):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)
    
    def __lt__(self, other) -> bool:
        """Less than comparison."""
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
    
    def __le__(self, other) -> bool:
        """Less than or equal comparison."""
        return self < other or self == other
    
    def __gt__(self, other) -> bool:
        """Greater than comparison."""
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)
    
    def __ge__(self, other) -> bool:
        """Greater than or equal comparison."""
        return self > other or self == other
    
    def __hash__(self) -> int:
        """Make VersionInfo hashable for use as dictionary keys."""
        return hash((self.major, self.minor, self.patch))


class VersionedRoute:
    """Represents a versioned route."""
    
    def __init__(
        self,
        path: str,
        func: Callable,
        methods: List[str],
        version: VersionInfo,
        deprecated: bool = False,
        **kwargs
    ):
        self.path = path
        self.func = func
        self.methods = methods
        self.version = version
        self.deprecated = deprecated
        self.kwargs = kwargs


class APIVersionManager:
    """Manages API versions and routing."""
    
    def __init__(
        self,
        strategy: VersioningStrategy = VersioningStrategy.URL_PATH,
        default_version: str = "1.0.0",
        header_name: str = "X-API-Version",
        query_param_name: str = "version",
        accept_header_format: str = "application/vnd.api+json;version={version}",
        url_prefix: str = "/api",
        strict_versioning: bool = False
    ):
        self.strategy = strategy
        self.default_version = VersionInfo.from_string(default_version)
        self.header_name = header_name
        self.query_param_name = query_param_name
        self.accept_header_format = accept_header_format
        self.url_prefix = url_prefix
        self.strict_versioning = strict_versioning
        
        # Storage for versioned routes
        self._versioned_routes: Dict[str, List[VersionedRoute]] = {}
        self._available_versions: List[VersionInfo] = []
        
        # Version deprecation tracking
        self._deprecated_versions: Dict[VersionInfo, str] = {}
        self._sunset_dates: Dict[VersionInfo, str] = {}
    
    def add_version(self, version: str) -> None:
        """Add a supported API version."""
        version_info = VersionInfo.from_string(version)
        if version_info not in self._available_versions:
            self._available_versions.append(version_info)
            self._available_versions.sort()
    
    def deprecate_version(
        self, 
        version: str, 
        message: str = None, 
        sunset_date: str = None
    ) -> None:
        """Mark a version as deprecated."""
        version_info = VersionInfo.from_string(version)
        self._deprecated_versions[version_info] = message or f"API version {version} is deprecated"
        if sunset_date:
            self._sunset_dates[version_info] = sunset_date
    
    def register_versioned_route(
        self,
        path: str,
        func: Callable,
        methods: List[str],
        version: str,
        deprecated: bool = False,
        **kwargs
    ) -> None:
        """Register a versioned route."""
        version_info = VersionInfo.from_string(version)
        
        # Add version if not already tracked
        if version_info not in self._available_versions:
            self.add_version(version)
        
        # Create versioned route
        versioned_route = VersionedRoute(
            path=path,
            func=func,
            methods=methods,
            version=version_info,
            deprecated=deprecated,
            **kwargs
        )
        
        # Store by path
        if path not in self._versioned_routes:
            self._versioned_routes[path] = []
        
        self._versioned_routes[path].append(versioned_route)
    
    def apply_routes_to_app(self, app) -> None:
        """Apply all registered versioned routes to the FastAPI app."""
        from fastapi import APIRouter
        
        for path, routes in self._versioned_routes.items():
            for route in routes:
                for method in route.methods:
                    # Create a versioned path
                    versioned_path = f"/api/v{route.version.major}.{route.version.minor}{path}"
                    
                    # Add route to app
                    method_name = method.lower()
                    if hasattr(app, method_name):
                        route_decorator = getattr(app, method_name)
                        
                        # Filter kwargs to only include FastAPI route parameters
                        route_kwargs = {
                            k: v for k, v in route.kwargs.items() 
                            if k in ['tags', 'summary', 'description', 'response_model', 
                                   'status_code', 'dependencies']
                        }
                        
                        route_decorator(versioned_path, **route_kwargs)(route.func)
    
    def get_version_from_request(self, request: Request) -> VersionInfo:
        """Extract version from request based on strategy."""
        if self.strategy == VersioningStrategy.URL_PATH:
            return self._get_version_from_url(request)
        elif self.strategy == VersioningStrategy.HEADER:
            return self._get_version_from_header(request)
        elif self.strategy == VersioningStrategy.QUERY_PARAM:
            return self._get_version_from_query(request)
        elif self.strategy == VersioningStrategy.ACCEPT_HEADER:
            return self._get_version_from_accept_header(request)
        else:
            return self.default_version
    
    def _get_version_from_url(self, request: Request) -> VersionInfo:
        """Extract version from URL path."""
        path = request.url.path
        
        # Look for version pattern in URL (e.g., /api/v1/, /v2/)
        version_pattern = r'/v(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:/|$)'
        match = re.search(version_pattern, path)
        
        if match:
            major = int(match.group(1))
            minor = int(match.group(2)) if match.group(2) else 0
            patch = int(match.group(3)) if match.group(3) else 0
            return VersionInfo(major=major, minor=minor, patch=patch)
        
        return self.default_version
    
    def _get_version_from_header(self, request: Request) -> VersionInfo:
        """Extract version from header."""
        version_str = request.headers.get(self.header_name)
        if version_str:
            try:
                return VersionInfo.from_string(version_str)
            except ValueError:
                pass
        
        return self.default_version
    
    def _get_version_from_query(self, request: Request) -> VersionInfo:
        """Extract version from query parameter."""
        version_str = request.query_params.get(self.query_param_name)
        if version_str:
            try:
                return VersionInfo.from_string(version_str)
            except ValueError:
                pass
        
        return self.default_version
    
    def _get_version_from_accept_header(self, request: Request) -> VersionInfo:
        """Extract version from Accept header."""
        accept = request.headers.get("accept", "")
        
        # Look for version in Accept header
        version_pattern = r'version=(\d+(?:\.\d+)?(?:\.\d+)?)'
        match = re.search(version_pattern, accept)
        
        if match:
            try:
                return VersionInfo.from_string(match.group(1))
            except ValueError:
                pass
        
        return self.default_version
    
    def find_best_route_version(
        self, 
        path: str, 
        requested_version: VersionInfo
    ) -> Optional[VersionedRoute]:
        """Find the best matching route for the requested version."""
        if path not in self._versioned_routes:
            return None
        
        routes = self._versioned_routes[path]
        
        # Sort routes by version (descending)
        sorted_routes = sorted(routes, key=lambda r: r.version, reverse=True)
        
        if self.strict_versioning:
            # Exact version match required
            for route in sorted_routes:
                if route.version == requested_version:
                    return route
        else:
            # Find highest compatible version
            for route in sorted_routes:
                if route.version.is_compatible_with(requested_version) and route.version <= requested_version:
                    return route
            
            # If no compatible version found, return the highest version
            if sorted_routes:
                return sorted_routes[0]
        
        return None
    
    def create_versioned_router(self, version: str) -> APIRouter:
        """Create a versioned router for a specific version."""
        version_info = VersionInfo.from_string(version)
        
        if self.strategy == VersioningStrategy.URL_PATH:
            prefix = f"{self.url_prefix}/{version_info.to_url_version()}"
        else:
            prefix = self.url_prefix
        
        router = APIRouter(prefix=prefix, tags=[f"API v{version_info.major}"])
        
        # Add version info to router
        router.version_info = version_info
        router.version_manager = self
        
        return router
    
    def get_available_versions(self) -> List[str]:
        """Get list of available API versions."""
        return [str(v) for v in sorted(self._available_versions)]
    
    def is_version_deprecated(self, version: VersionInfo) -> bool:
        """Check if a version is deprecated."""
        return version in self._deprecated_versions
    
    def get_deprecation_info(self, version: VersionInfo) -> Optional[Dict[str, str]]:
        """Get deprecation information for a version."""
        if version in self._deprecated_versions:
            info = {"message": self._deprecated_versions[version]}
            if version in self._sunset_dates:
                info["sunset_date"] = self._sunset_dates[version]
            return info
        return None


# Global version manager instance
version_manager = APIVersionManager()


def versioned_route(
    path: str,
    version: str,
    methods: Optional[List[str]] = None,
    deprecated: bool = False,
    **kwargs
):
    """Decorator for versioned routes."""
    methods = methods or ["GET"]
    
    def decorator(func: Callable) -> Callable:
        version_manager.register_versioned_route(
            path=path,
            func=func,
            methods=methods,
            version=version,
            deprecated=deprecated,
            **kwargs
        )
        return func
    
    return decorator


def get_versioned_route(path: str, version: str, **kwargs):
    """Decorator for versioned GET routes."""
    return versioned_route(path, version, methods=["GET"], **kwargs)


def post_versioned_route(path: str, version: str, **kwargs):
    """Decorator for versioned POST routes."""
    return versioned_route(path, version, methods=["POST"], **kwargs)


def put_versioned_route(path: str, version: str, **kwargs):
    """Decorator for versioned PUT routes."""
    return versioned_route(path, version, methods=["PUT"], **kwargs)


def delete_versioned_route(path: str, version: str, **kwargs):
    """Decorator for versioned DELETE routes."""
    return versioned_route(path, version, methods=["DELETE"], **kwargs)


class VersionedAPIRouter(APIRouter):
    """APIRouter with built-in versioning support."""
    
    def __init__(
        self,
        version: str,
        strategy: VersioningStrategy = VersioningStrategy.URL_PATH,
        **kwargs
    ):
        self.version_info = VersionInfo.from_string(version)
        self.strategy = strategy
        
        # Set prefix based on strategy
        if strategy == VersioningStrategy.URL_PATH:
            prefix = kwargs.get('prefix', '/api')
            prefix = f"{prefix}/{self.version_info.to_url_version()}"
            kwargs['prefix'] = prefix
        
        super().__init__(**kwargs)
        
        # Add version tag
        if 'tags' not in kwargs:
            self.tags = [f"API v{self.version_info.major}"]
    
    def add_api_route(self, path: str, endpoint: Callable, **kwargs):
        """Override to add version tracking."""
        # Register with version manager
        methods = kwargs.get('methods', ['GET'])
        version_manager.register_versioned_route(
            path=path,
            func=endpoint,
            methods=methods,
            version=str(self.version_info),
            **kwargs
        )
        
        super().add_api_route(path, endpoint, **kwargs) 