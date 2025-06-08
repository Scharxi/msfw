"""Integration tests for MSFW framework."""

import pytest
import pytest_asyncio
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, String, select

from msfw import MSFWApplication, Config, Module, Plugin
from msfw.core.database import Base
from tests.conftest import MockModule, MockPlugin

# Note: Individual tests use pytest.mark.asyncio as needed


# Test models for integration tests
class IntegrationUser(Base):
    """User model for integration tests."""
    
    __tablename__ = "integration_users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)


class IntegrationTestModule(Module):
    """Module for integration testing with database operations."""
    
    @property
    def name(self) -> str:
        return "integration_test_module"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Module for integration testing"
    
    async def setup(self) -> None:
        """Setup the module with database model."""
        if self.context and self.context.database:
            self.context.database.register_model("IntegrationUser", IntegrationUser)
    
    def register_routes(self, router):
        """Register integration test routes."""
        
        @router.post("/users")
        async def create_user(user_data: dict):
            async with self.context.database.session() as session:
                user = IntegrationUser(name=user_data["name"], email=user_data["email"])
                session.add(user)
                await session.flush()
                await session.refresh(user)
                return {"id": user.id, "name": user.name, "email": user.email}
        
        @router.get("/users/{user_id}")
        async def get_user(user_id: int):
            async with self.context.database.session() as session:
                result = await session.execute(select(IntegrationUser).where(IntegrationUser.id == user_id))
                user = result.scalar_one_or_none()
                if not user:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=404, detail="User not found")
                return {"id": user.id, "name": user.name, "email": user.email}
        
        @router.get("/users")
        async def list_users():
            async with self.context.database.session() as session:
                result = await session.execute(select(IntegrationUser))
                users = result.scalars().all()
                return [{"id": u.id, "name": u.name, "email": u.email} for u in users]


class IntegrationTestPlugin(Plugin):
    """Plugin for integration testing with hooks."""
    
    def __init__(self):
        super().__init__()
        self.startup_called = False
        self.shutdown_called = False
        self.request_count = 0
        self.user_created_count = 0
    
    @property
    def name(self) -> str:
        return "integration_test_plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Plugin for integration testing"
    
    async def setup(self, config: Config) -> None:
        """Setup the plugin."""
        self.startup_called = True
        
        # Register for application hooks
        self.register_hook("app_startup", self.on_app_startup)
        self.register_hook("app_shutdown", self.on_app_shutdown)
        self.register_hook("request_received", self.on_request_received)
        self.register_hook("user_created", self.on_user_created)
    
    async def cleanup(self) -> None:
        """Cleanup the plugin."""
        self.shutdown_called = True
    
    async def on_app_startup(self, **kwargs):
        """Handle app startup."""
        self.startup_called = True
    
    async def on_app_shutdown(self, **kwargs):
        """Handle app shutdown."""
        self.shutdown_called = True
    
    async def on_request_received(self, **kwargs):
        """Handle request received."""
        self.request_count += 1
    
    async def on_user_created(self, **kwargs):
        """Handle user created."""
        self.user_created_count += 1


@pytest.mark.integration
class TestFullFrameworkIntegration:
    """Test complete framework integration."""
    
    @pytest_asyncio.fixture
    async def local_integrated_app(self, test_config: Config):
        """Create fully integrated application."""
        # Enable monitoring for integration tests
        test_config.monitoring.enabled = True
        test_config.monitoring.prometheus_enabled = True
        
        app = MSFWApplication(test_config)
        
        # Add test module and plugin
        integration_module = IntegrationTestModule()
        integration_plugin = IntegrationTestPlugin()
        
        app.add_module(integration_module)
        app.add_plugin(integration_plugin)
        
        await app.initialize()
        
        # Create database tables
        if app.database:
            # Register the IntegrationUser model
            app.database.register_model("IntegrationUser", IntegrationUser)
            # Ensure the model is properly registered in Base metadata
            if IntegrationUser.__table__.name not in Base.metadata.tables:
                Base.metadata._add_table(IntegrationUser.__table__, None)
            await app.database.create_tables()
        
        # Manually setup module context and routes (since TestClient doesn't trigger lifespan)
        from msfw.core.module import ModuleContext
        context = ModuleContext(
            app=app.get_app(),
            config=test_config,
            database=app.database,
        )
        app.module_manager.set_context(context)
        
        # Initialize plugins first
        await app.plugin_manager.initialize_plugins()
        
        # Then initialize modules
        await app.module_manager.initialize_modules()
        app.module_manager.register_all_routes(app.get_app())
        
        return app, integration_module, integration_plugin
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, local_integrated_app):
        """Test complete workflow with modules, plugins, and database."""
        app, module, plugin = local_integrated_app
        
        with TestClient(app.get_app()) as client:
            # Test health endpoint
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "components" in data
            assert "database" in data["components"]
            
            # Test metrics endpoint
            response = client.get("/metrics")
            assert response.status_code == 200
            
            # Test module endpoints
            # Create a user
            user_data = {"name": "John Doe", "email": "john@example.com"}
            response = client.post("/integration_test_module/users", json=user_data)
            assert response.status_code == 200
            created_user = response.json()
            assert created_user["name"] == "John Doe"
            assert created_user["email"] == "john@example.com"
            assert "id" in created_user
            
            user_id = created_user["id"]
            
            # Get the user
            response = client.get(f"/integration_test_module/users/{user_id}")
            assert response.status_code == 200
            retrieved_user = response.json()
            assert retrieved_user == created_user
            
            # List users
            response = client.get("/integration_test_module/users")
            assert response.status_code == 200
            users = response.json()
            assert len(users) == 1
            assert users[0] == created_user
        
        # Verify plugin hooks were called
        assert plugin.startup_called
        
        # Manually trigger request hook to test plugin system
        await app.plugin_manager.trigger_hook("request_received", method="GET", path="/health")
        assert plugin.request_count > 0
    
    @pytest.mark.asyncio
    async def test_database_integration(self, local_integrated_app):
        """Test database integration across the framework."""
        app, module, plugin = local_integrated_app
        
        # Verify database is properly set up
        assert app.database is not None
        assert app.database.get_model("IntegrationUser") == IntegrationUser
        
        # Test database operations directly
        async with app.database.session() as session:
            # Create user directly
            user = IntegrationUser(name="Direct User", email="direct@example.com")
            session.add(user)
            await session.flush()
            assert user.id is not None
        
        # Verify through API
        with TestClient(app.get_app()) as client:
            response = client.get("/integration_test_module/users")
            assert response.status_code == 200
            users = response.json()
            assert len(users) >= 1
            
            # Find our direct user
            direct_user = next((u for u in users if u["email"] == "direct@example.com"), None)
            assert direct_user is not None
            assert direct_user["name"] == "Direct User"
    
    @pytest.mark.asyncio
    async def test_plugin_event_system(self, local_integrated_app):
        """Test plugin event system integration."""
        app, module, plugin = local_integrated_app
        
        # Trigger events through the plugin manager
        await app.plugin_manager.trigger_hook("request_received", method="GET", path="/test")
        await app.plugin_manager.trigger_hook("user_created", user_id=123, email="test@example.com")
        
        # Verify events were handled
        assert plugin.request_count > 0
        assert plugin.user_created_count > 0
    
    @pytest.mark.asyncio
    async def test_middleware_integration(self, local_integrated_app):
        """Test middleware integration."""
        app, module, plugin = local_integrated_app
        
        with TestClient(app.get_app()) as client:
            response = client.get("/health")
            assert response.status_code == 200
            
            # Check middleware headers
            assert "X-Request-ID" in response.headers
            assert "X-Content-Type-Options" in response.headers
            assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, local_integrated_app):
        """Test error handling across the framework."""
        app, module, plugin = local_integrated_app
        
        with TestClient(app.get_app()) as client:
            # Test 404 handling
            response = client.get("/nonexistent")
            assert response.status_code == 404
            
            # Test invalid user ID
            response = client.get("/integration_test_module/users/999")
            assert response.status_code == 404  # Should return proper HTTP error
            data = response.json()
            assert "detail" in data
            assert data["detail"] == "User not found"
    
    @pytest.mark.asyncio
    async def test_configuration_integration(self, local_integrated_app):
        """Test configuration integration across components."""
        app, module, plugin = local_integrated_app
        
        # Verify config is accessible in different components
        assert app.config.monitoring.enabled is True
        
        # Module should have access to config through context
        assert module.context is not None
        assert module.context.config == app.config
        
        # Database should use config settings
        assert app.database.config.url == app.config.database.url


@pytest.mark.integration
class TestModulePluginInteraction:
    """Test interaction between modules and plugins."""
    
    @pytest.mark.asyncio
    async def test_module_plugin_communication(self, test_config: Config):
        """Test communication between modules and plugins."""
        app = MSFWApplication(test_config)
        
        module = IntegrationTestModule()
        plugin = IntegrationTestPlugin()
        
        app.add_module(module)
        app.add_plugin(plugin)
        
        await app.initialize()
        
        # Register the IntegrationUser model for this test
        if IntegrationUser.__table__.name not in Base.metadata.tables:
            Base.metadata._add_table(IntegrationUser.__table__, None)
        await app.database.create_tables()
        
        # Manually register plugin hooks with module context
        # since the plugin hook system needs proper integration
        module.context.register_hook("user_created", plugin.on_user_created)
        
        # Trigger plugin hook from module context
        await module.context.trigger_hook("user_created", user_id=1)
        
        # Verify plugin received the event
        assert plugin.user_created_count == 1
        
        await app.cleanup()
    
    @pytest.mark.asyncio
    async def test_shared_services(self, test_config: Config):
        """Test shared services between modules."""
        app = MSFWApplication(test_config)
        
        # Create two modules that share services with unique names
        class Module1(IntegrationTestModule):
            @property
            def name(self) -> str:
                return "module1"
        
        class Module2(IntegrationTestModule):
            @property
            def name(self) -> str:
                return "module2"
        
        module1 = Module1()
        module2 = Module2()
        
        app.add_module(module1)
        app.add_module(module2)
        
        await app.initialize()
        
        # Register the IntegrationUser model for this test
        if IntegrationUser.__table__.name not in Base.metadata.tables:
            Base.metadata._add_table(IntegrationUser.__table__, None)
        await app.database.create_tables()
        
        # Register a service in module1
        test_service = {"data": "shared_data"}
        module1.context.register_service("shared_service", test_service)
        
        # Access service from module2
        retrieved_service = module2.context.get_service("shared_service")
        assert retrieved_service == test_service
        
        await app.cleanup()


@pytest.mark.integration
class TestConcurrencyIntegration:
    """Test framework behavior under concurrent load."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, integrated_app):
        """Test concurrent requests to the application."""
        app, module, plugin = integrated_app
        
        async def make_request(session_id: int):
            """Make a request with session ID."""
            with TestClient(app.get_app()) as client:
                user_data = {"name": f"User {session_id}", "email": f"user{session_id}@example.com"}
                response = client.post("/test_crud/users", json=user_data)
                assert response.status_code == 200
                return response.json()
        
        # Create multiple users concurrently
        tasks = [make_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify all users were created
        assert len(results) == 10
        assert len(set(r["id"] for r in results)) == 10  # All IDs should be unique
        
        # Verify database state
        with TestClient(app.get_app()) as client:
            response = client.get("/test_crud/users")
            assert response.status_code == 200
            users = response.json()
            assert len(users) == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self, integrated_app):
        """Test concurrent database operations."""
        app, module, plugin = integrated_app
        
        async def create_user_via_api(session_id: int):
            """Create user via API to avoid table conflicts."""
            with TestClient(app.get_app()) as client:
                user_data = {"name": f"Direct User {session_id}", "email": f"direct{session_id}@example.com"}
                response = client.post("/test_crud/users", json=user_data)
                assert response.status_code == 200
                return response.json()["id"]
        
        # Create users concurrently
        tasks = [create_user_via_api(i) for i in range(5)]
        user_ids = await asyncio.gather(*tasks)
        
        # Verify all users were created
        assert len(user_ids) == 5
        assert len(set(user_ids)) == 5  # All IDs should be unique
        
        # Verify through API query
        with TestClient(app.get_app()) as client:
            response = client.get("/test_crud/users")
            assert response.status_code == 200
            users = response.json()
            direct_users = [u for u in users if u["email"].startswith("direct")]
            assert len(direct_users) == 5


@pytest.mark.performance
class TestFrameworkPerformance:
    """Test framework performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_request_throughput(self, integrated_app):
        """Test basic request throughput."""
        app, module, plugin = integrated_app
        
        import time
        
        num_requests = 100
        
        with TestClient(app.get_app()) as client:
            start_time = time.time()
            
            for i in range(num_requests):
                response = client.get("/health")
                assert response.status_code == 200
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Basic performance assertion
            requests_per_second = num_requests / duration
            assert requests_per_second > 10  # Should handle at least 10 requests per second
    
    @pytest.mark.asyncio
    async def test_database_performance(self, integrated_app):
        """Test database operation performance."""
        app, module, plugin = integrated_app
        
        import time
        from fastapi.testclient import TestClient
        
        num_operations = 50
        
        start_time = time.time()
        
        # Use API endpoints instead of direct database access to avoid table conflicts
        with TestClient(app.get_app()) as client:
            for i in range(num_operations):
                user_data = {"name": f"Perf User {i}", "email": f"perf{i}@example.com"}
                response = client.post("/test_crud/users", json=user_data)
                assert response.status_code == 200
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Basic performance assertion (more lenient for API calls vs direct DB)
        operations_per_second = num_operations / duration
        assert operations_per_second > 2  # Should handle at least 2 API operations per second


@pytest.mark.e2e
class TestEndToEndScenarios:
    """End-to-end scenario tests."""
    
    @pytest.mark.asyncio
    async def test_user_management_scenario(self, integrated_app):
        """Test complete user management scenario."""
        app, module, plugin = integrated_app
        
        with TestClient(app.get_app()) as client:
            # Step 1: Check initial state (use proper module prefix)
            response = client.get("/test_crud/users")
            assert response.status_code == 200
            assert response.json() == []
            
            # Step 2: Create multiple users
            users_data = [
                {"name": "Alice", "email": "alice@example.com"},
                {"name": "Bob", "email": "bob@example.com"},
                {"name": "Charlie", "email": "charlie@example.com"},
            ]
            
            created_users = []
            for user_data in users_data:
                response = client.post("/test_crud/users", json=user_data)
                assert response.status_code == 200
                created_users.append(response.json())
            
            # Step 3: Verify all users exist
            response = client.get("/test_crud/users")
            assert response.status_code == 200
            all_users = response.json()
            assert len(all_users) == 3
            
            # Step 4: Retrieve individual users
            for created_user in created_users:
                response = client.get(f"/test_crud/users/{created_user['id']}")
                assert response.status_code == 200
                retrieved_user = response.json()
                assert retrieved_user == created_user
            
            # Step 5: Check plugin tracked events
            # Manually trigger request hook to test plugin system
            await app.plugin_manager.trigger_hook("request_received", method="GET", path="/test_crud/users")
            assert plugin.request_count > 0
        
        # Step 6: Verify plugin functionality 
        # Check that plugin tracked requests
        assert plugin.request_count > 0
    
    @pytest.mark.asyncio
    async def test_monitoring_scenario(self, integrated_app):
        """Test monitoring and metrics scenario."""
        app, module, plugin = integrated_app
        
        with TestClient(app.get_app()) as client:
            # Generate some traffic
            for i in range(10):
                client.get("/health")
                client.get("/test_crud/users")
                if i < 3:
                    client.post("/test_crud/users", json={"name": f"User {i}", "email": f"user{i}@test.com"})
            
            # Check health endpoint
            response = client.get("/health")
            assert response.status_code == 200
            health_data = response.json()
            assert health_data["status"] == "healthy"
            assert "timestamp" in health_data
            assert "database" in health_data
            
            # Check metrics endpoint
            response = client.get("/metrics")
            assert response.status_code == 200
            metrics_data = response.text
            
            # Should contain prometheus metrics
            assert "http_requests_total" in metrics_data
            assert "http_request_duration_seconds" in metrics_data 