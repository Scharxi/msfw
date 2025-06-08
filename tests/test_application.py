"""Tests for the MSFW application."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from msfw import MSFWApplication, Config
from tests.conftest import MockModule, MockPlugin

# Mark all async tests in this module
pytestmark = pytest.mark.asyncio


@pytest.mark.integration
class TestMSFWApplication:
    """Test MSFW application integration."""
    
    async def test_application_initialization(self, test_config: Config):
        """Test application initialization."""
        app = MSFWApplication(test_config)
        
        # Initially not initialized
        assert not app.initialized
        assert app.database is None
        assert app.module_manager is None
        assert app.plugin_manager is None
        
        # Initialize
        await app.initialize()
        
        # Should be initialized
        assert app.initialized
        assert app.database is not None
        assert app.module_manager is not None
        assert app.plugin_manager is not None
        
        # Cleanup
        await app.cleanup()
    
    async def test_application_lifecycle(self, test_config: Config):
        """Test full application lifecycle."""
        app = MSFWApplication(test_config)
        
        # Initialize
        await app.initialize()
        assert app.initialized
        
        # Get FastAPI app
        fastapi_app = app.get_app()
        assert isinstance(fastapi_app, FastAPI)
        
        # Cleanup
        await app.cleanup()
    
    async def test_application_with_modules(self, test_config: Config, test_module: MockModule):
        """Test application with modules."""
        app = MSFWApplication(test_config)
        
        # Register module before initialization
        app.add_module(test_module)
        
        await app.initialize()
        
        # Module should be initialized
        assert test_module.is_initialized
        
        # Test client should work
        with TestClient(app.get_app()) as client:
            response = client.get("/test_module/test")
            assert response.status_code == 200
            assert response.json() == {"message": "test"}
        
        await app.cleanup()
    
    async def test_application_with_plugins(self, test_config: Config, test_plugin: MockPlugin):
        """Test application with plugins."""
        app = MSFWApplication(test_config)
        
        # Register plugin before initialization
        app.add_plugin(test_plugin)
        
        await app.initialize()
        
        # Plugin should be initialized
        assert test_plugin.initialized
        assert test_plugin.setup_called
        
        await app.cleanup()
        assert test_plugin.cleanup_called
    
    async def test_application_health_check(self, test_config: Config):
        """Test application health check endpoint."""
        test_config.monitoring.enabled = True
        app = MSFWApplication(test_config)
        await app.initialize()
        
        with TestClient(app.get_app()) as client:
            response = client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert "status" in data
            assert "timestamp" in data
            assert "database" in data
            assert data["status"] == "healthy"
        
        await app.cleanup()
    
    async def test_application_metrics_endpoint(self, test_config: Config):
        """Test application metrics endpoint."""
        test_config.monitoring.enabled = True
        test_config.monitoring.prometheus_enabled = True
        app = MSFWApplication(test_config)
        await app.initialize()
        
        with TestClient(app.get_app()) as client:
            response = client.get("/metrics")
            assert response.status_code == 200
            # Prometheus metrics should be text format
            assert response.headers["content-type"].startswith("text/plain")
        
        await app.cleanup()
    
    async def test_application_middleware_integration(self, test_config: Config):
        """Test application middleware integration."""
        test_config.monitoring.enabled = True
        app = MSFWApplication(test_config)
        await app.initialize()
        
        with TestClient(app.get_app()) as client:
            # Make a request to trigger middleware
            response = client.get("/health")
            assert response.status_code == 200
            
            # Check for middleware headers
            assert "X-Request-ID" in response.headers
        
        await app.cleanup()
    
    async def test_application_cors_middleware(self, test_config: Config):
        """Test CORS middleware."""
        test_config.cors.allow_origins = ["http://localhost:3000"]
        app = MSFWApplication(test_config)
        await app.initialize()
        
        with TestClient(app.get_app()) as client:
            # OPTIONS request for CORS preflight
            response = client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                }
            )
            assert response.status_code == 200
            assert "access-control-allow-origin" in response.headers
        
        await app.cleanup()
    
    async def test_application_auto_discovery(self, test_config: Config, temp_dir):
        """Test auto-discovery of modules and plugins."""
        # Create modules directory with a test module
        modules_dir = temp_dir / "modules"
        modules_dir.mkdir()
        
        module_file = modules_dir / "test_auto_module.py"
        module_file.write_text("""
from msfw import Module

class AutoTestModule(Module):
    @property
    def name(self) -> str:
        return "auto_test_module"
    
    def register_routes(self, router):
        @router.get("/auto")
        async def auto_endpoint():
            return {"message": "auto"}

module = AutoTestModule()
""")
        
        # Enable auto-discovery
        test_config.auto_discover_modules = True
        test_config.modules_directory = str(modules_dir)
        
        app = MSFWApplication(test_config)
        await app.initialize()
        
        # Module should be discovered and registered
        modules = app.module_manager.list_modules()
        assert "auto_test_module" in modules
        
        # Test the endpoint (routes are prefixed with module name)
        with TestClient(app.get_app()) as client:
            response = client.get("/auto_test_module/auto")
            assert response.status_code == 200
            assert response.json() == {"message": "auto"}
        
        await app.cleanup()
    
    async def test_application_database_integration(self, test_config: Config):
        """Test application database integration."""
        # Enable monitoring for this test to have health endpoint
        test_config.monitoring.enabled = True
        
        app = MSFWApplication(test_config)
        await app.initialize()
        
        # Database should be accessible
        assert app.database is not None
        
        # Health check should include database status
        with TestClient(app.get_app()) as client:
            response = client.get("/health")
            data = response.json()
            assert "database" in data  # Top-level backward compatibility
            assert "components" in data
            assert "database" in data["components"]
            assert data["components"]["database"]["status"] == "healthy"
        
        await app.cleanup()
    
    @patch('uvicorn.Server.serve')
    async def test_application_run(self, mock_serve, test_config: Config):
        """Test application run method."""
        app = MSFWApplication(test_config)
        
        # Mock serve to return immediately
        mock_serve.return_value = None
        
        # Run should call uvicorn.Server.serve
        await app.run()
        
        mock_serve.assert_called_once()
    
    async def test_application_error_handling(self, test_config: Config):
        """Test application error handling."""
        app = MSFWApplication(test_config)
        await app.initialize()
        
        with TestClient(app.get_app()) as client:
            # Test 404 handling
            response = client.get("/nonexistent")
            assert response.status_code == 404
        
        await app.cleanup()


@pytest.mark.integration
class TestApplicationConfiguration:
    """Test application configuration handling."""
    
    async def test_debug_mode(self, test_config: Config):
        """Test debug mode configuration."""
        test_config.debug = True
        app = MSFWApplication(test_config)
        await app.initialize()
        
        fastapi_app = app.get_app()
        assert fastapi_app.debug is True
        
        await app.cleanup()
    
    async def test_app_metadata(self, test_config: Config):
        """Test application metadata configuration."""
        test_config.app_name = "Test Application"
        test_config.version = "2.0.0"
        test_config.description = "Test description"
        
        app = MSFWApplication(test_config)
        await app.initialize()
        
        fastapi_app = app.get_app()
        assert fastapi_app.title == "Test Application"
        assert fastapi_app.version == "2.0.0"
        assert fastapi_app.description == "Test description"
        
        await app.cleanup()
    
    async def test_monitoring_disabled(self, test_config: Config):
        """Test application with monitoring disabled."""
        test_config.monitoring.enabled = False
        app = MSFWApplication(test_config)
        await app.initialize()
        
        with TestClient(app.get_app()) as client:
            # Health endpoint should not exist
            response = client.get("/health")
            assert response.status_code == 404
            
            # Metrics endpoint should not exist
            response = client.get("/metrics")
            assert response.status_code == 404
        
        await app.cleanup()


@pytest.mark.integration
class TestApplicationEvents:
    """Test application event handling."""
    
    async def test_startup_events(self, test_config: Config, test_plugin: MockPlugin):
        """Test startup event handling."""
        app = MSFWApplication(test_config)
        app.add_plugin(test_plugin)
        
        await app.initialize()
        
        # Plugin should have received startup event
        assert test_plugin.setup_called
        
        await app.cleanup()
    
    async def test_shutdown_events(self, test_config: Config, test_plugin: MockPlugin):
        """Test shutdown event handling."""
        app = MSFWApplication(test_config)
        app.add_plugin(test_plugin)
        
        await app.initialize()
        await app.cleanup()
        
        # Plugin should have received shutdown event
        assert test_plugin.cleanup_called


@pytest.mark.unit
class TestApplicationUtilities:
    """Test application utility methods."""
    
    def test_application_creation(self, test_config: Config):
        """Test application creation."""
        app = MSFWApplication(test_config)
        
        assert app.config == test_config
        assert not app.initialized
        assert app._fastapi_app is None
    
    def test_module_addition_before_init(self, test_config: Config, test_module: MockModule):
        """Test adding modules before initialization."""
        app = MSFWApplication(test_config)
        
        # Should be able to add modules before initialization
        app.add_module(test_module)
        
        # Module should be in pending list
        assert test_module in app._pending_modules
    
    def test_plugin_addition_before_init(self, test_config: Config, test_plugin: MockPlugin):
        """Test adding plugins before initialization."""
        app = MSFWApplication(test_config)
        
        # Should be able to add plugins before initialization
        app.add_plugin(test_plugin)
        
        # Plugin should be in pending list
        assert test_plugin in app._pending_plugins
    
    async def test_multiple_initialization_attempts(self, test_config: Config):
        """Test multiple initialization attempts."""
        app = MSFWApplication(test_config)
        
        # First initialization
        await app.initialize()
        assert app.initialized
        
        # Second initialization should not raise error
        await app.initialize()
        assert app.initialized
        
        await app.cleanup()
    
    async def test_cleanup_without_initialization(self, test_config: Config):
        """Test cleanup without initialization."""
        app = MSFWApplication(test_config)
        
        # Cleanup without initialization should not raise error
        await app.cleanup()
    
    def test_get_app_before_initialization(self, test_config: Config):
        """Test getting FastAPI app before initialization."""
        app = MSFWApplication(test_config)
        
        # Should raise error if not initialized
        with pytest.raises(RuntimeError, match="Application not initialized"):
            app.get_app()


@pytest.mark.e2e
class TestApplicationEndToEnd:
    """End-to-end application tests."""
    
    async def test_full_application_workflow(self, test_config: Config):
        """Test complete application workflow."""
        # Enable monitoring for this test
        test_config.monitoring.enabled = True
        test_config.monitoring.prometheus_enabled = True
        
        # Create application
        app = MSFWApplication(test_config)
        
        # Add a test module
        test_module = MockModule()
        app.add_module(test_module)
        
        # Add a test plugin
        test_plugin = MockPlugin()
        app.add_plugin(test_plugin)
        
        # Initialize
        await app.initialize()
        
        # Verify everything is working
        with TestClient(app.get_app()) as client:
            # Test module endpoint (modules are prefixed with their name)
            response = client.get("/test_module/test")
            assert response.status_code == 200
            assert response.json() == {"message": "test"}
            
            # Test health endpoint
            response = client.get("/health")
            assert response.status_code == 200
            
            # Test metrics endpoint
            response = client.get("/metrics")
            assert response.status_code == 200
        
        # Verify plugin hooks were called
        assert test_plugin.setup_called
        
        # Cleanup
        await app.cleanup()
        assert test_plugin.cleanup_called
    
    async def test_application_with_database_operations(self, test_config: Config):
        """Test application with actual database operations."""
        app = MSFWApplication(test_config)
        await app.initialize()
        
        # Test database session
        async with app.database.session() as session:
            # This should work without errors
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            assert result is not None
        
        await app.cleanup() 