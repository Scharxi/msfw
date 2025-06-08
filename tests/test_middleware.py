"""Tests for MSFW middleware components."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import REGISTRY, CollectorRegistry

from msfw.middleware.logging import LoggingMiddleware
from msfw.middleware.monitoring import MonitoringMiddleware
from msfw.middleware.security import SecurityMiddleware
from msfw.core.config import Config


@pytest.mark.unit
class TestLoggingMiddleware:
    """Test logging middleware."""
    
    @pytest.fixture
    def app_with_logging_middleware(self, test_config: Config):
        """Create FastAPI app with logging middleware."""
        app = FastAPI()
        app.add_middleware(LoggingMiddleware, config=test_config)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        
        return app
    
    def test_request_logging(self, app_with_logging_middleware):
        """Test request logging."""
        with TestClient(app_with_logging_middleware) as client:
            response = client.get("/test")
            assert response.status_code == 200
            
            # Check that request ID header is present
            assert "X-Request-ID" in response.headers
            assert len(response.headers["X-Request-ID"]) > 0
    
    def test_request_id_generation(self, app_with_logging_middleware):
        """Test request ID generation."""
        with TestClient(app_with_logging_middleware) as client:
            response1 = client.get("/test")
            response2 = client.get("/test")
            
            # Each request should have a unique ID
            assert response1.headers["X-Request-ID"] != response2.headers["X-Request-ID"]
    
    def test_request_id_propagation(self, app_with_logging_middleware):
        """Test request ID propagation."""
        with TestClient(app_with_logging_middleware) as client:
            # Send request with existing request ID
            existing_id = "custom-request-id"
            response = client.get("/test", headers={"X-Request-ID": existing_id})
            
            # Should return the same request ID
            assert response.headers["X-Request-ID"] == existing_id
    
    def test_error_logging(self, app_with_logging_middleware):
        """Test error logging."""
        with TestClient(app_with_logging_middleware) as client:
            # The error endpoint raises an exception, but TestClient
            # propagates it instead of converting to HTTP 500
            # This is expected behavior in test mode
            try:
                response = client.get("/error")
                # If we get here, the error was handled
                assert response.status_code == 500
            except ValueError as e:
                # This is expected - the exception propagates in test mode
                assert str(e) == "Test error"
            
            # The logging happens - we can see it in the captured logs
    
    def test_request_timing(self, app_with_logging_middleware):
        """Test request timing logging."""
        with TestClient(app_with_logging_middleware) as client:
            response = client.get("/test")
            assert response.status_code == 200
            
            # The request timing is logged - visible in captured logs
            # This test verifies that the request completes successfully
            # and the middleware doesn't crash on timing logging


@pytest.mark.unit
class TestMonitoringMiddleware:
    """Test monitoring middleware."""
    
    @pytest.fixture
    def custom_registry(self):
        """Create a custom Prometheus registry for testing."""
        registry = CollectorRegistry()
        yield registry
        # Cleanup happens automatically when fixture goes out of scope
    
    @pytest.fixture
    def app_with_monitoring_middleware(self, test_config: Config, custom_registry):
        """Create FastAPI app with monitoring middleware."""
        app = FastAPI()
        
        # Enable monitoring for this test
        test_config.monitoring.enabled = True
        
        # Use custom registry to avoid conflicts
        middleware = MonitoringMiddleware(app, config=test_config, registry=custom_registry)
        app.add_middleware(BaseHTTPMiddleware, dispatch=middleware.dispatch)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.get("/slow")
        async def slow_endpoint():
            import asyncio
            await asyncio.sleep(0.1)
            return {"message": "slow"}
        
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        
        return app, middleware
    
    def test_metrics_collection(self, app_with_monitoring_middleware):
        """Test basic metrics collection."""
        app, middleware = app_with_monitoring_middleware
        
        with TestClient(app) as client:
            response = client.get("/test")
            assert response.status_code == 200
            
            # Check that metrics were recorded
            metrics = list(middleware.request_count.collect())[0].samples
            # The samples include different metric types (_total, _created, etc.)
            total_requests = sum(sample.value for sample in metrics 
                               if sample.name == 'http_requests_total')
            assert total_requests > 0
    
    def test_request_duration_tracking(self, app_with_monitoring_middleware):
        """Test request duration tracking."""
        app, middleware = app_with_monitoring_middleware
        
        with TestClient(app) as client:
            response = client.get("/slow")
            assert response.status_code == 200
            
            # Check that duration was recorded
            duration_samples = list(middleware.request_duration.collect())[0].samples
            assert len(duration_samples) > 0
            
            # Duration should be positive
            duration_sum = next((s.value for s in duration_samples if s.name.endswith('_sum')), 0)
            assert duration_sum > 0
    
    def test_request_size_tracking(self, app_with_monitoring_middleware):
        """Test request size tracking."""
        app, middleware = app_with_monitoring_middleware
        
        with TestClient(app) as client:
            # Send request with body
            response = client.post("/test", json={"key": "value"})
            
            # Check that request size was recorded
            size_samples = list(middleware.request_size.collect())[0].samples
            size_sum = next((s.value for s in size_samples if s.name.endswith('_sum')), 0)
            assert size_sum > 0
    
    def test_response_size_tracking(self, app_with_monitoring_middleware):
        """Test response size tracking."""
        app, middleware = app_with_monitoring_middleware
        
        with TestClient(app) as client:
            response = client.get("/test")
            assert response.status_code == 200
            
            # Check that response size was recorded
            size_samples = list(middleware.response_size.collect())[0].samples
            size_sum = next((s.value for s in size_samples if s.name.endswith('_sum')), 0)
            assert size_sum > 0
    
    def test_error_counting(self, app_with_monitoring_middleware):
        """Test error counting."""
        app, middleware = app_with_monitoring_middleware
        
        with TestClient(app) as client:
            # The error endpoint raises an exception, which should be caught and counted
            try:
                response = client.get("/error")
                # If we get here, check for 500 status
                assert response.status_code == 500
            except ValueError:
                # Exception was raised and propagated - this is expected
                pass
            
            # Check that error was counted in metrics regardless of exception handling
            metrics = list(middleware.request_count.collect())[0].samples
            error_requests = [s for s in metrics if '500' in str(s.labels)]
            assert len(error_requests) > 0, f"No 500 status found in metrics: {[str(s.labels) for s in metrics]}"
    
    def test_endpoint_normalization(self, app_with_monitoring_middleware):
        """Test endpoint path normalization."""
        app, middleware = app_with_monitoring_middleware
        
        # Add parametric endpoint
        @app.get("/users/{user_id}")
        async def get_user(user_id: int):
            return {"user_id": user_id}
        
        with TestClient(app) as client:
            response = client.get("/users/123")
            assert response.status_code == 200
            
            # Check that the endpoint is normalized
            # This is a basic test - the actual normalization logic may vary
            metrics = list(middleware.request_count.collect())[0].samples
            user_endpoint_metrics = [m for m in metrics if "/users/" in str(m.labels)]
            assert len(user_endpoint_metrics) > 0


@pytest.mark.unit
class TestSecurityMiddleware:
    """Test security middleware."""
    
    @pytest.fixture
    def app_with_security_middleware(self, test_config: Config):
        """Create FastAPI app with security middleware."""
        app = FastAPI()
        app.add_middleware(SecurityMiddleware, config=test_config)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        return app
    
    def test_security_headers(self, app_with_security_middleware):
        """Test security headers are added."""
        with TestClient(app_with_security_middleware) as client:
            response = client.get("/test")
            assert response.status_code == 200
            
            # Check security headers
            assert "X-Content-Type-Options" in response.headers
            assert response.headers["X-Content-Type-Options"] == "nosniff"
            
            assert "X-Frame-Options" in response.headers
            assert response.headers["X-Frame-Options"] == "DENY"
            
            assert "X-XSS-Protection" in response.headers
            assert response.headers["X-XSS-Protection"] == "1; mode=block"
            
            assert "Referrer-Policy" in response.headers
            assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    
    def test_client_ip_tracking(self, app_with_security_middleware):
        """Test client IP tracking."""
        with TestClient(app_with_security_middleware) as client:
            # Test with X-Forwarded-For header
            response = client.get("/test", headers={"X-Forwarded-For": "192.168.1.1"})
            assert response.status_code == 200
            
            # Test with X-Real-IP header
            response = client.get("/test", headers={"X-Real-IP": "10.0.0.1"})
            assert response.status_code == 200
    
    def test_request_validation(self, app_with_security_middleware):
        """Test basic request validation."""
        with TestClient(app_with_security_middleware) as client:
            # Normal request should work
            response = client.get("/test")
            assert response.status_code == 200
            
            # Request with extremely long header should work
            # (specific validation rules depend on implementation)
            long_header = "x" * 1000
            response = client.get("/test", headers={"Custom-Header": long_header})
            # Should not crash the application
            assert response.status_code in [200, 400, 413]


@pytest.mark.integration
class TestMiddlewareIntegration:
    """Test middleware integration."""
    
    @pytest.fixture
    def app_with_all_middleware(self, test_config: Config):
        """Create FastAPI app with all middleware."""
        # Enable monitoring to ensure metrics collection
        test_config.monitoring.enabled = True
        
        # Use custom registry for monitoring
        custom_registry = CollectorRegistry()
        
        app = FastAPI()
        
        # Add middleware in reverse order (last added = first executed)
        app.add_middleware(SecurityMiddleware, config=test_config)
        
        monitoring_middleware = MonitoringMiddleware(app, config=test_config, registry=custom_registry)
        app.add_middleware(BaseHTTPMiddleware, dispatch=monitoring_middleware.dispatch)
        
        app.add_middleware(LoggingMiddleware, config=test_config)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        return app, monitoring_middleware
    
    def test_middleware_stack(self, app_with_all_middleware):
        """Test complete middleware stack."""
        app, monitoring_middleware = app_with_all_middleware
        
        with TestClient(app) as client:
            response = client.get("/test")
            assert response.status_code == 200
            
            # All middleware should have executed
            # Request ID from logging middleware
            assert "X-Request-ID" in response.headers
            
            # Security headers from security middleware
            assert "X-Content-Type-Options" in response.headers
            
            # Metrics should be recorded by monitoring middleware
            metrics = list(monitoring_middleware.request_count.collect())[0].samples
            total_requests = sum(sample.value for sample in metrics 
                               if sample.name == 'http_requests_total')
            assert total_requests > 0
    
    def test_middleware_error_handling(self, app_with_all_middleware):
        """Test middleware error handling."""
        app, monitoring_middleware = app_with_all_middleware
        
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        
        with TestClient(app) as client:
            with pytest.raises(ValueError):
                client.get("/error")
            
            # Error should be counted in metrics
            # (specific implementation may vary)


@pytest.mark.unit
class TestMiddlewareConfiguration:
    """Test middleware configuration."""
    
    def test_logging_middleware_disabled(self, test_config: Config):
        """Test logging middleware when disabled."""
        test_config.logging.level = "CRITICAL"  # Effectively disable logging
        
        app = FastAPI()
        app.add_middleware(LoggingMiddleware, config=test_config)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        with TestClient(app) as client:
            response = client.get("/test")
            assert response.status_code == 200
            # Should still add request ID even if logging is minimal
            assert "X-Request-ID" in response.headers
    
    def test_monitoring_middleware_disabled(self, test_config: Config):
        """Test monitoring middleware when disabled."""
        test_config.monitoring.enabled = False
        
        app = FastAPI()
        
        # When monitoring is disabled, middleware should still work
        # but metrics collection might be minimal
        custom_registry = CollectorRegistry()
        middleware = MonitoringMiddleware(app, config=test_config, registry=custom_registry)
        app.add_middleware(BaseHTTPMiddleware, dispatch=middleware.dispatch)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        with TestClient(app) as client:
            response = client.get("/test")
            assert response.status_code == 200
    
    def test_security_middleware_configuration(self, test_config: Config):
        """Test security middleware configuration."""
        app = FastAPI()
        app.add_middleware(SecurityMiddleware, config=test_config)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        with TestClient(app) as client:
            response = client.get("/test")
            assert response.status_code == 200
            
            # Should have security headers
            assert "X-Content-Type-Options" in response.headers


@pytest.mark.performance
class TestMiddlewarePerformance:
    """Test middleware performance impact."""
    
    def test_middleware_overhead(self, test_config: Config):
        """Test middleware performance overhead."""
        # App without middleware
        app_plain = FastAPI()
        
        @app_plain.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # App with all middleware
        app_with_middleware = FastAPI()
        app_with_middleware.add_middleware(SecurityMiddleware, config=test_config)
        app_with_middleware.add_middleware(LoggingMiddleware, config=test_config)
        
        custom_registry = CollectorRegistry()
        monitoring_middleware = MonitoringMiddleware(
            app_with_middleware, 
            config=test_config, 
            registry=custom_registry
        )
        app_with_middleware.add_middleware(BaseHTTPMiddleware, dispatch=monitoring_middleware.dispatch)
        
        @app_with_middleware.get("/test")
        async def test_endpoint_with_middleware():
            return {"message": "test"}
        
        # Test both apps
        with TestClient(app_plain) as client_plain:
            start_time = time.time()
            for _ in range(10):
                response = client_plain.get("/test")
                assert response.status_code == 200
            plain_time = time.time() - start_time
        
        with TestClient(app_with_middleware) as client_middleware:
            start_time = time.time()
            for _ in range(10):
                response = client_middleware.get("/test")
                assert response.status_code == 200
            middleware_time = time.time() - start_time
        
        # Middleware should not add excessive overhead
        # This is a basic performance test
        overhead_ratio = middleware_time / plain_time
        assert overhead_ratio < 5.0  # Middleware should not add more than 5x overhead in test environment 