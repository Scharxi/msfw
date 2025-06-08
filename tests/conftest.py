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


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
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
    await database.initialize()
    yield database
    await database.close()


@pytest.fixture
async def test_app(test_config: Config) -> AsyncGenerator[MSFWApplication, None]:
    """Create a test MSFW application."""
    app = MSFWApplication(test_config)
    await app.initialize()
    yield app
    
    # Cleanup
    if app.database:
        await app.database.close()


@pytest.fixture
def test_client(test_app: MSFWApplication) -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(test_app.get_app())


class TestModule(Module):
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


class TestPlugin(Plugin):
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
def test_module() -> TestModule:
    """Create a test module instance."""
    return TestModule()


@pytest.fixture
def test_plugin() -> TestPlugin:
    """Create a test plugin instance."""
    return TestPlugin()


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
    """Create a fully integrated MSFW application with modules and plugins."""
    from sqlalchemy import Column, Integer, String
    from msfw.core.database import Base
    import uuid
    
    # Test User model - use unique table name to avoid conflicts
    unique_suffix = str(uuid.uuid4()).replace('-', '')[:8]
    
    class User(Base):
        __tablename__ = f"conftest_users_{unique_suffix}"
        id = Column(Integer, primary_key=True)
        name = Column(String(50))
        email = Column(String(100))
    
    # Test module with CRUD operations
    class TestCrudModule(Module):
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
            from fastapi import Depends
            from sqlalchemy import select
            from sqlalchemy.ext.asyncio import AsyncSession
            
            async def get_db():
                async with self.context.database.session() as session:
                    yield session
            
            @router.get("/users")
            async def get_users(db: AsyncSession = Depends(get_db)):
                result = await db.execute(select(User))
                users = result.scalars().all()
                return [{"id": u.id, "name": u.name, "email": u.email} for u in users]
            
            @router.post("/users")
            async def create_user(user_data: dict, db: AsyncSession = Depends(get_db)):
                user = User(**user_data)
                db.add(user)
                await db.commit()
                await db.refresh(user)
                return {"id": user.id, "name": user.name, "email": user.email}
            
            @router.get("/users/{user_id}")
            async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if not user:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=404, detail="User not found")
                return {"id": user.id, "name": user.name, "email": user.email}
    
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
    
    # Create application with file-based SQLite to avoid table sharing issues
    import tempfile
    import os
    
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)  # Close the file descriptor, we just need the path
    
    config = Config()
    config.database.url = f"sqlite+aiosqlite:///{db_path}"
    config.monitoring.enabled = True
    config.auto_discover_modules = False
    config.auto_discover_plugins = False
    
    app = MSFWApplication(config)
    await app.initialize()
    
    # Register test models
    app.database.register_model("User", User)
    await app.database.create_tables()
    
    # Add module and plugin
    module = TestCrudModule()
    plugin = TestRequestPlugin()
    
    app.register_module(module)
    app.register_plugin(plugin)
    
    # Initialize them manually
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
    
    # Cleanup
    await app.cleanup()
    
    # Remove temporary database file
    try:
        os.unlink(db_path)
    except OSError:
        pass  # File might already be deleted


def pytest_configure(config):
    """Configure pytest with custom markers."""
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