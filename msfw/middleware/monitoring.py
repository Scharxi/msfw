"""Monitoring middleware for MSFW applications."""

import time
from typing import Callable, Optional

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, REGISTRY
from starlette.middleware.base import BaseHTTPMiddleware

from msfw.core.config import Config


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting metrics and monitoring."""
    
    def __init__(self, app, config: Config, registry: Optional[CollectorRegistry] = None):
        super().__init__(app)
        self.config = config
        self.registry = registry or REGISTRY
        
        # Initialize metrics with the specified registry
        self._init_metrics()
    
    def _init_metrics(self):
        """Initialize Prometheus metrics."""
        try:
            self.request_count = Counter(
                "http_requests_total",
                "Total HTTP requests",
                ["method", "endpoint", "status"],
                registry=self.registry
            )
            
            self.request_duration = Histogram(
                "http_request_duration_seconds",
                "HTTP request duration",
                ["method", "endpoint"],
                registry=self.registry
            )
            
            self.request_size = Histogram(
                "http_request_size_bytes",
                "HTTP request size in bytes",
                ["method", "endpoint"],
                registry=self.registry
            )
            
            self.response_size = Histogram(
                "http_response_size_bytes", 
                "HTTP response size in bytes",
                ["method", "endpoint", "status"],
                registry=self.registry
            )
            
            self.active_requests = Gauge(
                "http_requests_active",
                "Currently active HTTP requests",
                registry=self.registry
            )
        except ValueError as e:
            # Handle case where metrics already exist (e.g., in tests)
            if "Duplicated timeseries" in str(e) or "already exists" in str(e):
                # Find existing metrics from registry
                self._find_existing_metrics()
            else:
                raise
    
    def _find_existing_metrics(self):
        """Find existing metrics in the registry."""
        # Initialize with None first
        self.request_count = None
        self.request_duration = None
        self.request_size = None
        self.response_size = None
        self.active_requests = None
        
        # Search through registry for existing metrics
        for collector in self.registry._collector_to_names:
            if hasattr(collector, '_name'):
                if collector._name == 'http_requests_total':
                    self.request_count = collector
                elif collector._name == 'http_request_duration_seconds':
                    self.request_duration = collector
                elif collector._name == 'http_request_size_bytes':
                    self.request_size = collector
                elif collector._name == 'http_response_size_bytes':
                    self.response_size = collector
                elif collector._name == 'http_requests_active':
                    self.active_requests = collector
        
        # If any metrics are still None, create them with a modified name
        if self.request_count is None:
            self.request_count = Counter(
                f"http_requests_total_{id(self)}",
                "Total HTTP requests",
                ["method", "endpoint", "status"],
                registry=self.registry
            )
        
        if self.request_duration is None:
            self.request_duration = Histogram(
                f"http_request_duration_seconds_{id(self)}",
                "HTTP request duration",
                ["method", "endpoint"],
                registry=self.registry
            )
        
        if self.request_size is None:
            self.request_size = Histogram(
                f"http_request_size_bytes_{id(self)}",
                "HTTP request size in bytes",
                ["method", "endpoint"],
                registry=self.registry
            )
        
        if self.response_size is None:
            self.response_size = Histogram(
                f"http_response_size_bytes_{id(self)}",
                "HTTP response size in bytes",
                ["method", "endpoint", "status"],
                registry=self.registry
            )
        
        if self.active_requests is None:
            self.active_requests = Gauge(
                f"http_requests_active_{id(self)}",
                "Currently active HTTP requests",
                registry=self.registry
            )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with monitoring."""
        if not self.config.monitoring.enabled:
            return await call_next(request)
        
        # Extract endpoint for metrics
        endpoint = self._get_endpoint(request)
        method = request.method
        
        # Track active requests
        self.active_requests.inc()
        
        # Track request size
        request_size = self._get_request_size(request)
        self.request_size.labels(method=method, endpoint=endpoint).observe(request_size)
        
        # Start timing
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Track metrics
            status = str(response.status_code)
            self.request_count.labels(
                method=method, 
                endpoint=endpoint, 
                status=status
            ).inc()
            
            self.request_duration.labels(
                method=method, 
                endpoint=endpoint
            ).observe(duration)
            
            # Track response size
            response_size = self._get_response_size(response)
            self.response_size.labels(
                method=method, 
                endpoint=endpoint, 
                status=status
            ).observe(response_size)
            
            return response
            
        except Exception as exc:
            # Track error metrics
            self.request_count.labels(
                method=method, 
                endpoint=endpoint, 
                status="500"
            ).inc()
            
            duration = time.time() - start_time
            self.request_duration.labels(
                method=method, 
                endpoint=endpoint
            ).observe(duration)
            
            raise
        
        finally:
            # Decrement active requests
            self.active_requests.dec()
    
    def _get_endpoint(self, request: Request) -> str:
        """Extract endpoint pattern from request."""
        # Try to get route pattern
        if hasattr(request, "scope") and "route" in request.scope:
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path
        
        # Fallback to path
        path = request.url.path
        
        # Normalize path for better grouping
        # Remove IDs and other variable parts
        path_parts = path.split("/")
        normalized_parts = []
        
        for part in path_parts:
            if not part:
                continue
            # Replace numeric IDs with placeholder
            if part.isdigit():
                normalized_parts.append("{id}")
            # Replace UUIDs with placeholder
            elif self._is_uuid(part):
                normalized_parts.append("{uuid}")
            else:
                normalized_parts.append(part)
        
        return "/" + "/".join(normalized_parts) if normalized_parts else "/"
    
    def _is_uuid(self, value: str) -> bool:
        """Check if string is a UUID."""
        try:
            import uuid
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False
    
    def _get_request_size(self, request: Request) -> int:
        """Get request size in bytes."""
        size = 0
        
        # Add headers size
        for name, value in request.headers.items():
            size += len(name.encode()) + len(value.encode()) + 4  # ": " + "\r\n"
        
        # Add content length if available
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size += int(content_length)
            except ValueError:
                pass
        
        return size
    
    def _get_response_size(self, response: Response) -> int:
        """Get response size in bytes."""
        size = 0
        
        # Add headers size
        for name, value in response.headers.items():
            size += len(name.encode()) + len(str(value).encode()) + 4
        
        # Add body size if available
        if hasattr(response, "body") and response.body:
            if isinstance(response.body, bytes):
                size += len(response.body)
            elif isinstance(response.body, str):
                size += len(response.body.encode())
        
        return size 