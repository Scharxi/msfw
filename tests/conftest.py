"""Pytest configuration and shared fixtures for MSFW tests."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from msfw import MSFWApplication, Config, Module, Plugin
from msfw.core.database import Base, Database

# Disable service registry for all tests to avoid event loop issues
def pytest_configure(config):
    """Configure pytest and disable service registry for tests."""
    # Set environment variable to disable SDK for tests
    import os
    os.environ['MSFW_DISABLE_SDK'] = 'true'
    
    # Mock the service registry module to prevent event loop issues
    import sys
    from unittest.mock import MagicMock
    
    # Create a mock service registry module
    mock_service_registry = MagicMock()
    mock_service_registry.service_registry = MockServiceRegistry()
    mock_service_registry.ServiceRegistry = MockServiceRegistry
    mock_service_registry.ServiceInstance = MagicMock
    mock_service_registry.ServiceEndpoint = MagicMock
    mock_service_registry.ServiceStatus = MagicMock
    
    # Replace the module in sys.modules
    sys.modules['msfw.core.service_registry'] = mock_service_registry

    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (deselect with '-m \"not unit\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )


class MockServiceRegistry:
    """Mock service registry for tests to avoid event loop issues."""
    
    def __init__(self):
        self._services = {}
        self._callbacks = {}
    
    async def register_service(self, service, auto_heartbeat=True):
        pass
    
    async def deregister_service(self, service_name, endpoints=None):
        pass
    
    async def discover_service(self, service_name, version=None):
        return []
    
    async def shutdown(self):
        pass
    
    def add_callback(self, event, callback):
        pass


@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test function."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_registry() -> CollectorRegistry:
    """Create a separate Prometheus registry for tests."""
    return CollectorRegistry()


@pytest.fixture
def test_config() -> Config:
    """Create a test configuration."""
    import tempfile
    import os
    
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)  # Close the file descriptor since we'll let SQLAlchemy handle the file
    
    config = Config()
    config.app_name = "Test Application"
    config.debug = True
    config.database.url = f"sqlite+aiosqlite:///{db_path}"
    config.database.echo = False
    config.logging.level = "DEBUG"
    config.monitoring.enabled = False
    config.auto_discover_modules = False
    config.auto_discover_plugins = False
    return config


@pytest.fixture
async def test_database(test_config: Config) -> AsyncGenerator[Database, None]:
    """Create a test database."""
    database = Database(test_config.database)
    try:
        await database.initialize()
        yield database
    finally:
        try:
            await database.close()
        except Exception:
            pass


@pytest.fixture
async def test_app(test_config: Config) -> AsyncGenerator[MSFWApplication, None]:
    """Create a test MSFW application."""
    app = MSFWApplication(test_config)
    
    try:
        await app.initialize()
        yield app
    finally:
        # Cleanup
        try:
            await app.cleanup()
        except Exception:
            pass


@pytest.fixture
def test_client(test_app: MSFWApplication) -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(test_app.get_app())


class MockModule(Module):
    """Test module for testing purposes."""
    
    @property
    def name(self) -> str:
        return "test_module"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Test module for unit tests"
    
    async def setup(self) -> None:
        """Setup test module."""
        pass
    
    def register_routes(self, router):
        """Register test routes."""
        @router.get("/test")
        async def test_endpoint():
            return {"message": "test"}


class MockPlugin(Plugin):
    """Test plugin for testing purposes."""
    
    def __init__(self):
        super().__init__()
        self.setup_called = False
        self.cleanup_called = False
        self.hook_calls = []
    
    @property
    def name(self) -> str:
        return "test_plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Test plugin for unit tests"
    
    async def setup(self, config: Config) -> None:
        """Setup test plugin."""
        self.setup_called = True
        self.register_hook("test_event", self.on_test_event)
    
    async def cleanup(self) -> None:
        """Cleanup test plugin."""
        self.cleanup_called = True
    
    async def on_test_event(self, **kwargs):
        """Handle test event."""
        self.hook_calls.append(kwargs)


@pytest.fixture
def test_module() -> MockModule:
    """Create a test module instance."""
    return MockModule()


@pytest.fixture
def test_plugin() -> MockPlugin:
    """Create a test plugin instance."""
    return MockPlugin()


@pytest.fixture
def mock_project_structure(temp_dir: Path) -> Path:
    """Create a mock project structure for CLI tests."""
    project_dir = temp_dir / "test_project"
    project_dir.mkdir()
    
    # Create main.py
    (project_dir / "main.py").write_text("""
from msfw import MSFWApplication, Config

async def main():
    config = Config()
    app = MSFWApplication(config)
    await app.run()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
""")
    
    # Create directories
    (project_dir / "modules").mkdir()
    (project_dir / "plugins").mkdir()
    (project_dir / "config").mkdir()
    
    return project_dir


# Pytest marks for different test categories
pytestmark = [
    pytest.mark.asyncio,
]


@pytest.fixture
async def database():
    """Create a test database."""
    config = Config()
    config.database.url = "sqlite+aiosqlite:///:memory:"
    
    database = Database(config.database)
    await database.initialize()
    yield database
    await database.close()


@pytest.fixture
async def populated_database():
    """Create a database with test data."""
    config = Config()
    config.database.url = "sqlite+aiosqlite:///:memory:"
    
    database = Database(config.database)
    await database.initialize()
    
    # Add some test data here if needed
    
    yield database
    await database.close()


@pytest_asyncio.fixture
async def integrated_app():
    """Create a simplified integrated MSFW application for tests."""
    # Test module with simple mock operations - no database needed
    class TestCrudModule(Module):
        def __init__(self):
            super().__init__()
            self.users = {}  # In-memory storage
            self.next_id = 1
        
        @property
        def name(self) -> str:
            return "test_crud"
        
        @property
        def version(self) -> str:
            return "1.0.0"
        
        @property
        def description(self) -> str:
            return "Test CRUD module"
        
        async def setup(self) -> None:
            pass
        
        def register_routes(self, router):
            @router.get("/users")
            async def get_users():
                return list(self.users.values())
            
            @router.post("/users")
            async def create_user(user_data: dict):
                user = {
                    "id": self.next_id,
                    "name": user_data["name"],
                    "email": user_data["email"]
                }
                self.users[self.next_id] = user
                self.next_id += 1
                return user
            
            @router.get("/users/{user_id}")
            async def get_user(user_id: int):
                if user_id not in self.users:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=404, detail="User not found")
                return self.users[user_id]
    
    # Test plugin that tracks requests
    class TestRequestPlugin(Plugin):
        def __init__(self):
            super().__init__()
            self.request_count = 0
        
        @property
        def name(self) -> str:
            return "test_request_tracker"
        
        @property
        def version(self) -> str:
            return "1.0.0"
        
        @property
        def description(self) -> str:
            return "Test request tracking plugin"
        
        async def setup(self, config: Config) -> None:
            self.register_hook("request_received", self.on_request)
        
        async def cleanup(self) -> None:
            pass
        
        async def on_request(self, **kwargs):
            self.request_count += 1
    
    # Use in-memory database to avoid file system issues
    config = Config()
    config.database.url = "sqlite+aiosqlite:///:memory:"
    config.monitoring.enabled = True  # Enable monitoring for integration tests
    config.auto_discover_modules = False
    config.auto_discover_plugins = False
    
    app = MSFWApplication(config)
    
    try:
        await app.initialize()
        
        # Create test module and plugin
        module = TestCrudModule()
        plugin = TestRequestPlugin()
        
        # Add them to the app
        app.register_module(module)
        app.register_plugin(plugin)
        
        # Initialize them
        from msfw.core.module import ModuleContext
        context = ModuleContext(
            app=app.get_app(),
            config=config,
            database=app.database
        )
        module.context = context
        await module.setup()
        await plugin.setup(config)
        
        # Register routes with module prefix
        from fastapi import APIRouter
        router = APIRouter()
        module.register_routes(router)
        app.get_app().include_router(router, prefix=f"/{module.name}", tags=[module.name])
        
        yield app, module, plugin
        
    finally:
        # Ensure cleanup always happens
        try:
            await app.cleanup()
        except Exception:
            pass  # Ignore cleanup errors 