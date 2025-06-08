"""Test utilities for MSFW framework tests."""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from msfw.core.config import Config, DatabaseConfig
from msfw.core.database import Database, Base


async def create_test_database(
    url: Optional[str] = None,
    echo: bool = False
) -> AsyncGenerator[Database, None]:
    """Create a test database instance."""
    if url is None:
        url = "sqlite+aiosqlite:///:memory:"
    
    config = DatabaseConfig(url=url, echo=echo)
    database = Database(config)
    
    try:
        await database.initialize()
        await database.create_tables()
        yield database
    finally:
        await database.close()


def create_test_config(**overrides) -> Config:
    """Create a test configuration with optional overrides."""
    config = Config()
    config.debug = True
    config.database.url = "sqlite+aiosqlite:///:memory:"
    config.database.echo = False
    config.logging.level = "DEBUG"
    config.monitoring.enabled = True
    config.auto_discover_modules = False
    config.auto_discover_plugins = False
    
    # Apply overrides
    for key, value in overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            # Handle nested attributes like database.url
            keys = key.split('.')
            obj = config
            for k in keys[:-1]:
                obj = getattr(obj, k)
            setattr(obj, keys[-1], value)
    
    return config


async def wait_for_condition(
    condition_func,
    timeout: float = 5.0,
    interval: float = 0.1
) -> bool:
    """Wait for a condition to become true within a timeout."""
    start_time = asyncio.get_event_loop().time()
    
    while True:
        try:
            if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
                return True
        except Exception:
            pass
        
        current_time = asyncio.get_event_loop().time()
        if current_time - start_time >= timeout:
            return False
        
        await asyncio.sleep(interval)


def create_temp_project_structure() -> Path:
    """Create a temporary project structure for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create directories
    (temp_dir / "modules").mkdir()
    (temp_dir / "plugins").mkdir()
    (temp_dir / "config").mkdir()
    
    # Create basic files
    (temp_dir / "main.py").write_text("""
from msfw import MSFWApplication, Config

async def main():
    config = Config()
    app = MSFWApplication(config)
    await app.run()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
""")
    
    (temp_dir / "config" / "settings.toml").write_text("""
app_name = "Test Application"
debug = true

[database]
url = "sqlite+aiosqlite:///test.db"

[logging]
level = "DEBUG"
""")
    
    return temp_dir


class MockRequest:
    """Mock request object for testing middleware."""
    
    def __init__(
        self,
        method: str = "GET",
        url: str = "http://testserver/",
        headers: Optional[Dict[str, str]] = None,
        body: bytes = b"",
    ):
        self.method = method
        self.url = url
        self.headers = headers or {}
        self.body = body
        self.state = type('State', (), {})()
    
    def header(self, name: str, default: str = "") -> str:
        """Get header value."""
        return self.headers.get(name, default)


class MockResponse:
    """Mock response object for testing middleware."""
    
    def __init__(
        self,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        content: bytes = b"",
    ):
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content
    
    def header(self, name: str, value: str) -> None:
        """Set header value."""
        self.headers[name] = value


async def cleanup_database_tables(database: Database) -> None:
    """Clean up all tables in a database."""
    async with database.session() as session:
        # Get all table names
        tables = Base.metadata.tables.keys()
        
        # Drop all tables
        for table_name in tables:
            await session.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        
        await session.commit()


def assert_logs_contain(caplog, level: str, message: str) -> bool:
    """Assert that logs contain a specific message at a specific level."""
    for record in caplog.records:
        if record.levelname == level and message in record.message:
            return True
    return False


class DatabaseTestCase:
    """Base class for database test cases."""
    
    @classmethod
    async def setup_class(cls):
        """Set up database for the test class."""
        cls.database = Database(DatabaseConfig(url="sqlite+aiosqlite:///:memory:"))
        await cls.database.initialize()
    
    @classmethod
    async def teardown_class(cls):
        """Tear down database after test class."""
        if hasattr(cls, 'database'):
            await cls.database.close()
    
    async def setup_method(self):
        """Set up for each test method."""
        await self.database.create_tables()
    
    async def teardown_method(self):
        """Tear down after each test method."""
        await cleanup_database_tables(self.database)


def create_integration_test_data() -> Dict[str, Any]:
    """Create test data for integration tests."""
    return {
        "users": [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
            {"name": "Charlie", "email": "charlie@example.com"},
        ],
        "config": {
            "app_name": "Integration Test App",
            "debug": True,
            "database_url": "sqlite+aiosqlite:///:memory:",
        },
    }


async def simulate_load(
    target_function,
    concurrent_requests: int = 10,
    total_requests: int = 100
) -> Dict[str, Any]:
    """Simulate load on a target function."""
    import time
    
    semaphore = asyncio.Semaphore(concurrent_requests)
    results = []
    errors = []
    
    async def make_request():
        async with semaphore:
            try:
                start_time = time.time()
                if asyncio.iscoroutinefunction(target_function):
                    result = await target_function()
                else:
                    result = target_function()
                end_time = time.time()
                
                results.append({
                    "duration": end_time - start_time,
                    "result": result,
                })
            except Exception as e:
                errors.append(str(e))
    
    # Create tasks
    tasks = [make_request() for _ in range(total_requests)]
    
    # Run all tasks
    start_time = time.time()
    await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    # Calculate statistics
    durations = [r["duration"] for r in results]
    
    return {
        "total_requests": total_requests,
        "successful_requests": len(results),
        "failed_requests": len(errors),
        "total_duration": end_time - start_time,
        "average_duration": sum(durations) / len(durations) if durations else 0,
        "min_duration": min(durations) if durations else 0,
        "max_duration": max(durations) if durations else 0,
        "requests_per_second": total_requests / (end_time - start_time),
        "errors": errors,
    }


class EventCollector:
    """Utility class to collect events for testing."""
    
    def __init__(self):
        self.events = []
    
    async def collect(self, event_name: str, **kwargs):
        """Collect an event."""
        self.events.append({
            "name": event_name,
            "data": kwargs,
            "timestamp": asyncio.get_event_loop().time(),
        })
    
    def get_events(self, event_name: Optional[str] = None):
        """Get collected events, optionally filtered by name."""
        if event_name is None:
            return self.events
        return [e for e in self.events if e["name"] == event_name]
    
    def clear(self):
        """Clear collected events."""
        self.events.clear()
    
    def count(self, event_name: Optional[str] = None) -> int:
        """Count events, optionally filtered by name."""
        return len(self.get_events(event_name))


def create_mock_module(name: str, version: str = "1.0.0", dependencies: list = None):
    """Create a mock module for testing."""
    from msfw.core.module import Module
    
    class MockModule(Module):
        @property
        def name(self) -> str:
            return name
        
        @property
        def version(self) -> str:
            return version
        
        @property
        def dependencies(self) -> list:
            return dependencies or []
        
        def register_routes(self, router):
            @router.get(f"/{name}")
            async def mock_endpoint():
                return {"module": name, "version": version}
    
    return MockModule()


def create_mock_plugin(name: str, version: str = "1.0.0", priority: int = 100):
    """Create a mock plugin for testing."""
    from msfw.core.plugin import Plugin
    
    class MockPlugin(Plugin):
        def __init__(self):
            super().__init__()
            self.setup_called = False
            self.cleanup_called = False
            self.events = []
        
        @property
        def name(self) -> str:
            return name
        
        @property
        def version(self) -> str:
            return version
        
        @property
        def priority(self) -> int:
            return priority
        
        async def setup(self, config):
            self.setup_called = True
            self.register_hook("test_event", self.on_test_event)
        
        async def cleanup(self):
            self.cleanup_called = True
        
        async def on_test_event(self, **kwargs):
            self.events.append(kwargs)
    
    return MockPlugin() 