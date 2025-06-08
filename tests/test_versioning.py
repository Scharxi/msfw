"""Tests for API versioning functionality."""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from unittest.mock import Mock

from msfw.core.versioning import (
    VersionInfo, APIVersionManager, VersioningStrategy, 
    VersionedRoute, VersionedAPIRouter
)
from msfw.decorators import (
    route, get, post
)
from msfw.decorators.versioning import (
    VersionedRouter, api_version
)
from msfw.middleware.versioning import (
    APIVersioningMiddleware, ContentNegotiationMiddleware,
    VersionRoutingMiddleware
)


class TestVersionInfo:
    """Test VersionInfo class."""
    
    def test_version_info_creation(self):
        """Test creating VersionInfo from different formats."""
        # Test basic creation
        v1 = VersionInfo(1, 0, 0)
        assert str(v1) == "1.0.0"
        assert v1.to_url_version() == "v1"
        
        # Test from string
        v2 = VersionInfo.from_string("2.1.3")
        assert v2.major == 2
        assert v2.minor == 1
        assert v2.patch == 3
        
        # Test short versions
        v3 = VersionInfo.from_string("v1")
        assert v3.major == 1
        assert v3.minor == 0
        assert v3.patch == 0
        
        v4 = VersionInfo.from_string("2.1")
        assert v4.major == 2
        assert v4.minor == 1
        assert v4.patch == 0
    
    def test_version_info_comparison(self):
        """Test version comparison operations."""
        v1_0 = VersionInfo.from_string("1.0.0")
        v1_1 = VersionInfo.from_string("1.1.0")
        v2_0 = VersionInfo.from_string("2.0.0")
        
        # Test equality
        assert v1_0 == VersionInfo.from_string("1.0.0")
        assert v1_0 != v1_1
        
        # Test ordering
        assert v1_0 < v1_1
        assert v1_1 < v2_0
        assert v2_0 > v1_0
        assert v1_1 >= v1_0
        assert v1_0 <= v1_1
    
    def test_version_compatibility(self):
        """Test version compatibility logic."""
        v1_0 = VersionInfo.from_string("1.0.0")
        v1_1 = VersionInfo.from_string("1.1.0")
        v1_2 = VersionInfo.from_string("1.2.0")
        v2_0 = VersionInfo.from_string("2.0.0")
        
        # Same major version should be compatible
        assert v1_0.is_compatible_with(v1_1)
        assert v1_1.is_compatible_with(v1_0)
        assert v1_1.is_compatible_with(v1_2)
        
        # Different major version should not be compatible
        assert not v1_0.is_compatible_with(v2_0)
        assert not v2_0.is_compatible_with(v1_0)


class TestAPIVersionManager:
    """Test APIVersionManager class."""
    
    def test_version_manager_creation(self):
        """Test creating version manager with different strategies."""
        # URL path strategy
        vm1 = APIVersionManager(strategy=VersioningStrategy.URL_PATH)
        assert vm1.strategy == VersioningStrategy.URL_PATH
        assert vm1.url_prefix == "/api"
        
        # Header strategy
        vm2 = APIVersionManager(
            strategy=VersioningStrategy.HEADER,
            header_name="X-API-Version"
        )
        assert vm2.strategy == VersioningStrategy.HEADER
        assert vm2.header_name == "X-API-Version"
    
    def test_version_management(self):
        """Test adding and managing versions."""
        vm = APIVersionManager()
        
        # Add versions
        vm.add_version("1.0")
        vm.add_version("2.0")
        vm.add_version("1.1")
        
        available = vm.get_available_versions()
        assert "1.0.0" in available
        assert "1.1.0" in available
        assert "2.0.0" in available
        assert len(available) == 3
    
    def test_version_deprecation(self):
        """Test version deprecation functionality."""
        vm = APIVersionManager()
        vm.add_version("1.0")
        vm.add_version("2.0")
        
        # Deprecate version
        vm.deprecate_version("1.0", "Use v2.0 instead", "2024-12-31")
        
        v1_0 = VersionInfo.from_string("1.0")
        assert vm.is_version_deprecated(v1_0)
        
        deprecation_info = vm.get_deprecation_info(v1_0)
        assert deprecation_info["message"] == "Use v2.0 instead"
        assert deprecation_info["sunset_date"] == "2024-12-31"
        
        v2_0 = VersionInfo.from_string("2.0")
        assert not vm.is_version_deprecated(v2_0)
    
    def test_route_registration(self):
        """Test registering versioned routes."""
        vm = APIVersionManager()
        
        async def test_handler():
            return {"test": "data"}
        
        # Register routes
        vm.register_versioned_route(
            path="/users",
            func=test_handler,
            methods=["GET"],
            version="1.0"
        )
        
        vm.register_versioned_route(
            path="/users", 
            func=test_handler,
            methods=["GET"],
            version="2.0"
        )
        
        # Test route finding
        v1_0 = VersionInfo.from_string("1.0")
        route = vm.find_best_route_version("/users", v1_0)
        assert route is not None
        assert route.version == v1_0
        
        v2_0 = VersionInfo.from_string("2.0")
        route = vm.find_best_route_version("/users", v2_0)
        assert route is not None
        assert route.version == v2_0
    
    def test_version_extraction_from_url(self):
        """Test extracting version from URL."""
        vm = APIVersionManager(strategy=VersioningStrategy.URL_PATH)
        
        # Mock request objects
        mock_request_v1 = Mock()
        mock_request_v1.url.path = "/api/v1/users"
        
        mock_request_v2 = Mock()
        mock_request_v2.url.path = "/api/v2/users"
        
        mock_request_default = Mock()
        mock_request_default.url.path = "/users"
        
        # Test extraction
        v1 = vm.get_version_from_request(mock_request_v1)
        assert v1.major == 1
        assert v1.minor == 0
        
        v2 = vm.get_version_from_request(mock_request_v2)
        assert v2.major == 2
        assert v2.minor == 0
        
        default = vm.get_version_from_request(mock_request_default)
        assert default == vm.default_version
    
    def test_version_extraction_from_header(self):
        """Test extracting version from header."""
        vm = APIVersionManager(strategy=VersioningStrategy.HEADER)
        
        # Mock request with version header
        mock_request = Mock()
        mock_request.headers = {"X-API-Version": "2.1"}
        
        version = vm.get_version_from_request(mock_request)
        assert version.major == 2
        assert version.minor == 1
        
        # Mock request without header
        mock_request_no_header = Mock()
        mock_request_no_header.headers = {}
        
        default_version = vm.get_version_from_request(mock_request_no_header)
        assert default_version == vm.default_version


class TestVersionedDecorators:
    """Test versioned route decorators."""
    
    def test_versioned_route_decorator(self):
        """Test versioned route decorator."""
        from msfw.core.versioning import version_manager
        
        # Clear any existing routes
        version_manager._versioned_routes.clear()
        
        @route("/test", methods=["GET"], version="1.0")
        async def test_endpoint():
            return {"version": "1.0"}
        
        # Check that route was registered
        assert "/test" in version_manager._versioned_routes
        routes = version_manager._versioned_routes["/test"]
        assert len(routes) == 1
        assert routes[0].version == VersionInfo.from_string("1.0")
        assert routes[0].func == test_endpoint
    
    def test_http_method_decorators(self):
        """Test HTTP method-specific decorators."""
        from msfw.core.versioning import version_manager
        
        # Clear any existing routes
        version_manager._versioned_routes.clear()
        
        @get("/users", version="1.0")
        async def get_users():
            return []
        
        @post("/users", version="1.0")
        async def create_user():
            return {}
        
        # Check routes were registered with correct methods
        routes = version_manager._versioned_routes["/users"]
        assert len(routes) == 2
        
        get_route = next(r for r in routes if "GET" in r.methods)
        post_route = next(r for r in routes if "POST" in r.methods)
        
        assert get_route.func == get_users
        assert post_route.func == create_user
    
    def test_api_version_class_decorator(self):
        """Test api_version class decorator."""
        
        @api_version("2.0", deprecated=True)
        class TestAPI:
            async def test_method(self):
                return {"test": "data"}
        
        assert TestAPI._api_version == VersionInfo.from_string("2.0")
        assert TestAPI._api_deprecated is True


class TestVersionedRouter:
    """Test VersionedRouter class."""
    
    def test_versioned_router_creation(self):
        """Test creating versioned router."""
        router = VersionedRouter("1.0", strategy=VersioningStrategy.URL_PATH)
        
        assert router.version == VersionInfo.from_string("1.0")
        assert router.strategy == VersioningStrategy.URL_PATH
        assert router.router.prefix == "/api/v1"
    
    def test_versioned_router_methods(self):
        """Test versioned router HTTP methods."""
        router = VersionedRouter("2.0")
        
        @router.get("/users")
        async def get_users():
            return []
        
        @router.post("/users")
        async def create_user():
            return {}
        
        # Check that decorators were applied
        assert hasattr(get_users, '_api_version')
        assert hasattr(create_user, '_api_version')


class TestVersioningMiddleware:
    """Test versioning middleware."""
    
    @pytest.fixture
    def mock_app(self):
        """Create mock ASGI app."""
        async def app(scope, receive, send):
            response = {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            }
            await send(response)
            await send({"type": "http.response.body", "body": b'{"test": "data"}'})
        
        return app
    
    @pytest.fixture
    def version_manager(self):
        """Create version manager for tests."""
        vm = APIVersionManager()
        vm.add_version("1.0")
        vm.add_version("2.0") 
        vm.deprecate_version("1.0", "Use v2.0")
        return vm
    
    def test_api_versioning_middleware_creation(self, mock_app, version_manager):
        """Test creating API versioning middleware."""
        middleware = APIVersioningMiddleware(
            mock_app,
            version_manager=version_manager
        )
        
        assert middleware.version_manager == version_manager
        assert middleware.enable_deprecation_warnings is True
        assert middleware.enable_version_info_headers is True
    
    @pytest.mark.asyncio
    async def test_version_detection(self, mock_app, version_manager):
        """Test version detection in middleware."""
        middleware = APIVersioningMiddleware(mock_app, version_manager)
        
        # Mock request with version header
        mock_request = Mock()
        mock_request.headers = {"X-API-Version": "1.0"}
        mock_request.state = Mock()
        
        async def mock_call_next(request):
            return Mock(headers={})
        
        # Test middleware processes request
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Check that version was stored in request state
        assert hasattr(mock_request.state, 'api_version')
    
    def test_content_negotiation_middleware(self, mock_app, version_manager):
        """Test content negotiation middleware."""
        middleware = ContentNegotiationMiddleware(mock_app, version_manager)
        
        assert middleware.version_manager == version_manager
        assert middleware.default_media_type == "application/json"
    
    def test_version_routing_middleware(self, mock_app, version_manager):
        """Test version routing middleware."""
        middleware = VersionRoutingMiddleware(
            mock_app,
            version_manager,
            enable_automatic_routing=True
        )
        
        assert middleware.version_manager == version_manager
        assert middleware.enable_automatic_routing is True


class TestVersioningIntegration:
    """Integration tests for versioning system."""
    
    def test_full_versioning_workflow(self):
        """Test complete versioning workflow."""
        from fastapi import FastAPI
        from msfw.core.versioning import version_manager
        from msfw.middleware.versioning import APIVersioningMiddleware
        
        # Setup
        app = FastAPI()
        version_manager._versioned_routes.clear()
        version_manager.add_version("1.0")
        version_manager.add_version("2.0")
        
        # Add middleware
        app.add_middleware(
            APIVersioningMiddleware,
            version_manager=version_manager
        )
        
        # Register versioned routes
        @get("/users", version="1.0", deprecated=True)
        async def get_users_v1():
            return [{"id": 1, "name": "John Doe"}]
        
        @get("/users", version="2.0")
        async def get_users_v2():
            return [{"id": 1, "first_name": "John", "last_name": "Doe"}]
        
        # Add routes to FastAPI
        app.get("/api/v1/users")(get_users_v1)
        app.get("/api/v2/users")(get_users_v2)
        
        # Test with TestClient
        client = TestClient(app)
        
        # Test v1 endpoint
        response_v1 = client.get("/api/v1/users")
        assert response_v1.status_code == 200
        assert "X-API-Version" in response_v1.headers
        
        # Test v2 endpoint
        response_v2 = client.get("/api/v2/users")
        assert response_v2.status_code == 200
        assert "X-API-Version" in response_v2.headers
    
    def test_version_deprecation_headers(self):
        """Test deprecation headers are added correctly."""
        from fastapi import FastAPI
        from msfw.core.versioning import version_manager
        from msfw.middleware.versioning import APIVersioningMiddleware
        
        app = FastAPI()
        version_manager._versioned_routes.clear()
        version_manager.add_version("1.0")
        version_manager.deprecate_version("1.0", "Use v2.0 instead")
        
        app.add_middleware(
            APIVersioningMiddleware,
            version_manager=version_manager
        )
        
        @get("/test", version="1.0", deprecated=True)
        async def test_endpoint():
            return {"test": "data"}
        
        app.get("/api/v1/test")(test_endpoint)
        
        client = TestClient(app)
        response = client.get("/api/v1/test")
        
        assert response.status_code == 200
        assert response.headers.get("X-API-Deprecated") == "true"
        assert "Use v2.0 instead" in response.headers.get("X-API-Deprecation-Message", "")


if __name__ == "__main__":
    pytest.main([__file__]) 