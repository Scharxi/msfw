"""Versioning middleware for MSFW applications."""

import logging
from typing import Callable

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from msfw.core.versioning import APIVersionManager, VersioningStrategy, VersionInfo


logger = logging.getLogger(__name__)


class APIVersioningMiddleware(BaseHTTPMiddleware):
    """Middleware for handling API versioning."""
    
    def __init__(
        self,
        app,
        version_manager: APIVersionManager,
        enable_deprecation_warnings: bool = True,
        enable_version_info_headers: bool = True
    ):
        super().__init__(app)
        self.version_manager = version_manager
        self.enable_deprecation_warnings = enable_deprecation_warnings
        self.enable_version_info_headers = enable_version_info_headers
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle versioning for each request."""
        try:
            # Extract version from request
            requested_version = self.version_manager.get_version_from_request(request)
            
            # Store version in request state for later use
            request.state.api_version = requested_version
            
            # Validate version
            if not self._is_version_supported(requested_version):
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "unsupported_api_version",
                        "message": f"API version {requested_version} is not supported",
                        "supported_versions": self.version_manager.get_available_versions()
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add version information to response headers
            if self.enable_version_info_headers:
                self._add_version_headers(response, requested_version)
            
            # Add deprecation warnings if needed
            if self.enable_deprecation_warnings:
                self._add_deprecation_headers(response, requested_version)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in versioning middleware: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "versioning_error",
                    "message": "An error occurred while processing API version"
                }
            )
    
    def _is_version_supported(self, version: VersionInfo) -> bool:
        """Check if the requested version is supported."""
        available_versions = [
            VersionInfo.from_string(v) 
            for v in self.version_manager.get_available_versions()
        ]
        
        if not available_versions:
            return True  # No versions defined, allow all
        
        # Check if exact version or compatible version exists
        for available in available_versions:
            if version == available or version.is_compatible_with(available):
                return True
        
        return False
    
    def _add_version_headers(self, response: Response, version: VersionInfo) -> None:
        """Add version information to response headers."""
        response.headers["X-API-Version"] = str(version)
        response.headers["X-API-Available-Versions"] = ",".join(
            self.version_manager.get_available_versions()
        )
    
    def _add_deprecation_headers(self, response: Response, version: VersionInfo) -> None:
        """Add deprecation headers if the version is deprecated."""
        if self.version_manager.is_version_deprecated(version):
            deprecation_info = self.version_manager.get_deprecation_info(version)
            
            response.headers["X-API-Deprecated"] = "true"
            if deprecation_info:
                response.headers["X-API-Deprecation-Message"] = deprecation_info["message"]
                if "sunset_date" in deprecation_info:
                    response.headers["X-API-Sunset"] = deprecation_info["sunset_date"]


class ContentNegotiationMiddleware(BaseHTTPMiddleware):
    """Middleware for content negotiation with versioning."""
    
    def __init__(
        self,
        app,
        version_manager: APIVersionManager,
        default_media_type: str = "application/json"
    ):
        super().__init__(app)
        self.version_manager = version_manager
        self.default_media_type = default_media_type
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle content negotiation with version support."""
        # Parse Accept header for version information
        accept_header = request.headers.get("accept", "")
        
        # Extract media type and version preferences
        media_type, version_info = self._parse_accept_header(accept_header)
        
        # Store content negotiation info in request state
        request.state.preferred_media_type = media_type
        if version_info:
            request.state.content_version = version_info
        
        response = await call_next(request)
        
        # Set appropriate Content-Type
        if not response.headers.get("content-type"):
            response.headers["Content-Type"] = media_type
        
        return response
    
    def _parse_accept_header(self, accept_header: str) -> tuple[str, VersionInfo]:
        """Parse Accept header for media type and version."""
        media_type = self.default_media_type
        version_info = None
        
        if not accept_header:
            return media_type, version_info
        
        # Simple parsing for main media type
        parts = accept_header.split(',')
        for part in parts:
            part = part.strip()
            
            # Check for JSON variants
            if 'application/json' in part or 'application/vnd' in part:
                media_type = part.split(';')[0].strip()
                
                # Look for version parameter
                if 'version=' in part:
                    import re
                    version_match = re.search(r'version=([0-9.]+)', part)
                    if version_match:
                        try:
                            version_info = VersionInfo.from_string(version_match.group(1))
                        except ValueError:
                            pass
                break
        
        return media_type, version_info


class VersionRoutingMiddleware(BaseHTTPMiddleware):
    """Middleware for routing requests to the correct versioned endpoints."""
    
    def __init__(
        self,
        app,
        version_manager: APIVersionManager,
        enable_automatic_routing: bool = True
    ):
        super().__init__(app)
        self.version_manager = version_manager
        self.enable_automatic_routing = enable_automatic_routing
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Route requests to appropriate versioned endpoints."""
        if not self.enable_automatic_routing:
            return await call_next(request)
        
        # Get the requested version (should be set by versioning middleware)
        requested_version = getattr(request.state, 'api_version', None)
        if not requested_version:
            requested_version = self.version_manager.get_version_from_request(request)
        
        # Find the best matching route
        path = request.url.path
        
        # Remove version prefix from path for matching if URL-based versioning
        if self.version_manager.strategy == VersioningStrategy.URL_PATH:
            # Remove /api/v1 style prefix for route matching
            import re
            path = re.sub(r'/api/v\d+', '', path)
            if not path:
                path = '/'
        
        best_route = self.version_manager.find_best_route_version(path, requested_version)
        
        if best_route:
            # Store route information for potential use in endpoint
            request.state.versioned_route = best_route
            request.state.route_version = best_route.version
            
            # Add deprecation warning if route is deprecated
            if best_route.deprecated:
                request.state.route_deprecated = True
        
        return await call_next(request)


def create_versioning_middleware(
    version_manager: APIVersionManager,
    enable_deprecation_warnings: bool = True,
    enable_version_info_headers: bool = True,
    enable_content_negotiation: bool = True,
    enable_automatic_routing: bool = True
) -> list:
    """Create a list of versioning middleware components."""
    middleware_list = []
    
    # Add main versioning middleware
    middleware_list.append(
        (APIVersioningMiddleware, {
            "version_manager": version_manager,
            "enable_deprecation_warnings": enable_deprecation_warnings,
            "enable_version_info_headers": enable_version_info_headers
        })
    )
    
    # Add content negotiation middleware if enabled
    if enable_content_negotiation:
        middleware_list.append(
            (ContentNegotiationMiddleware, {
                "version_manager": version_manager
            })
        )
    
    # Add routing middleware if enabled
    if enable_automatic_routing:
        middleware_list.append(
            (VersionRoutingMiddleware, {
                "version_manager": version_manager,
                "enable_automatic_routing": enable_automatic_routing
            })
        )
    
    return middleware_list 