"""Tests for the MSFW module system."""

import pytest
from fastapi import APIRouter
from unittest.mock import AsyncMock, MagicMock

from msfw.core.config import Config
from msfw.core.module import Module, ModuleContext, ModuleManager, ModuleMetadata
from tests.conftest import MockModule

# Mark all async tests in this module
pytestmark = pytest.mark.asyncio


@pytest.mark.unit
class TestModuleMetadata:
    """Test module metadata."""
    
    def test_default_metadata(self):
        """Test default metadata values."""
        metadata = ModuleMetadata(name="test")
        
        assert metadata.name == "test"
        assert metadata.version == "1.0.0"
        assert metadata.description == ""
        assert metadata.author == ""
        assert metadata.dependencies == []
        assert metadata.tags == []
        assert metadata.enabled is True
    
    def test_custom_metadata(self):
        """Test custom metadata values."""
        metadata = ModuleMetadata(
            name="custom",
            version="2.0.0",
            description="Custom module",
            author="Test Author",
            dependencies=["dep1", "dep2"],
            tags=["tag1", "tag2"],
            enabled=False,
        )
        
        assert metadata.name == "custom"
        assert metadata.version == "2.0.0"
        assert metadata.description == "Custom module"
        assert metadata.author == "Test Author"
        assert metadata.dependencies == ["dep1", "dep2"]
        assert metadata.tags == ["tag1", "tag2"]
        assert metadata.enabled is False


@pytest.mark.unit
class TestModuleContext:
    """Test module context."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock FastAPI app."""
        return MagicMock()
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        return MagicMock(spec=Config)
    
    @pytest.fixture
    def mock_database(self):
        """Create a mock database."""
        return MagicMock()
    
    def test_context_creation(self, mock_app, mock_config, mock_database):
        """Test context creation."""
        context = ModuleContext(
            app=mock_app,
            config=mock_config,
            database=mock_database,
        )
        
        assert context.app == mock_app
        assert context.config == mock_config
        assert context.database == mock_database
        assert isinstance(context.router, APIRouter)
    
    def test_service_registration(self, mock_app, mock_config):
        """Test service registration and retrieval."""
        context = ModuleContext(app=mock_app, config=mock_config)
        
        # Register a service
        test_service = MagicMock()
        context.register_service("test_service", test_service)
        
        # Retrieve the service
        assert context.get_service("test_service") == test_service
        assert context.get_service("nonexistent") is None
    
    def test_hook_registration(self, mock_app, mock_config):
        """Test hook registration."""
        context = ModuleContext(app=mock_app, config=mock_config)
        
        # Register hooks
        handler1 = MagicMock()
        handler2 = MagicMock()
        
        context.register_hook("test_event", handler1)
        context.register_hook("test_event", handler2)
        context.register_hook("other_event", handler1)
        
        # Check internal state
        assert len(context._hooks["test_event"]) == 2
        assert len(context._hooks["other_event"]) == 1
    
    async def test_hook_triggering(self, mock_app, mock_config):
        """Test hook triggering."""
        context = ModuleContext(app=mock_app, config=mock_config)
        
        # Register sync and async handlers
        sync_handler = MagicMock(return_value="sync_result")
        async_handler = AsyncMock(return_value="async_result")
        
        context.register_hook("test_event", sync_handler)
        context.register_hook("test_event", async_handler)
        
        # Trigger hooks
        results = await context.trigger_hook("test_event", arg1="value1", arg2="value2")
        
        # Verify handlers were called
        sync_handler.assert_called_once_with(arg1="value1", arg2="value2")
        async_handler.assert_called_once_with(arg1="value1", arg2="value2")
        
        # Verify results
        assert results == ["sync_result", "async_result"]
    
    async def test_hook_error_handling(self, mock_app, mock_config):
        """Test hook error handling."""
        context = ModuleContext(app=mock_app, config=mock_config)
        
        # Register handlers that raise errors
        def failing_handler(**kwargs):
            raise ValueError("Test error")
        
        good_handler = MagicMock(return_value="good_result")
        
        context.register_hook("test_event", failing_handler)
        context.register_hook("test_event", good_handler)
        
        # Trigger hooks - should not raise but continue with other handlers
        results = await context.trigger_hook("test_event")
        
        # Good handler should still be called
        good_handler.assert_called_once()
        assert "good_result" in results


@pytest.mark.unit
class TestModuleBase:
    """Test base module functionality."""
    
    def test_module_properties(self, test_module: MockModule):
        """Test module properties."""
        assert test_module.name == "test_module"
        assert test_module.version == "1.0.0"
        assert test_module.description == "Test module for unit tests"
        assert test_module.dependencies == []
        assert test_module.is_initialized is False
    
    async def test_module_initialization(self, test_module: MockModule):
        """Test module initialization."""
        # Create mock context
        mock_context = MagicMock(spec=ModuleContext)
        
        # Initialize module
        await test_module.initialize(mock_context)
        
        # Verify initialization
        assert test_module.context == mock_context
        assert test_module.is_initialized is True
        assert test_module.metadata is not None
        assert test_module.metadata.name == "test_module"
    
    def test_route_registration(self, test_module: MockModule):
        """Test route registration."""
        router = MagicMock(spec=APIRouter)
        
        # Register routes
        test_module.register_routes(router)
        
        # Verify router methods were called
        router.get.assert_called()
    
    async def test_module_cleanup(self, test_module: MockModule):
        """Test module cleanup."""
        # Initialize first
        mock_context = MagicMock(spec=ModuleContext)
        await test_module.initialize(mock_context)
        
        # Should not raise any errors
        await test_module.cleanup()


class DependentModule(Module):
    """Test module with dependencies."""
    
    @property
    def name(self) -> str:
        return "dependent_module"
    
    @property
    def dependencies(self) -> list:
        return ["test_module"]


class CircularDependencyModule(Module):
    """Test module that creates circular dependency."""
    
    @property
    def name(self) -> str:
        return "circular_module"
    
    @property
    def dependencies(self) -> list:
        return ["dependent_module"]


@pytest.mark.integration
class TestModuleManager:
    """Test module manager."""
    
    @pytest.fixture
    def manager(self, test_config: Config):
        """Create a module manager."""
        return ModuleManager(test_config)
    
    def test_module_registration(self, manager: ModuleManager, test_module: MockModule):
        """Test module registration."""
        # Register module
        manager.register_module(test_module)
        
        # Verify registration
        assert manager.get_module("test_module") == test_module
        assert "test_module" in manager.list_modules()
    
    def test_duplicate_module_registration(self, manager: ModuleManager, test_module: MockModule):
        """Test duplicate module registration."""
        # Register module
        manager.register_module(test_module)
        
        # Try to register same module again
        with pytest.raises(ValueError, match="Module 'test_module' already registered"):
            manager.register_module(test_module)
    
    def test_module_removal(self, manager: ModuleManager, test_module: MockModule):
        """Test module removal."""
        # Register and then remove
        manager.register_module(test_module)
        assert "test_module" in manager.list_modules()
        
        manager.remove_module("test_module")
        assert "test_module" not in manager.list_modules()
        assert manager.get_module("test_module") is None
    
    async def test_module_initialization_order(self, manager: ModuleManager):
        """Test module initialization with dependencies."""
        # Create modules with dependencies
        base_module = MockModule()
        dependent_module = DependentModule()
        
        # Register in reverse order
        manager.register_module(dependent_module)
        manager.register_module(base_module)
        
        # Set context
        mock_context = MagicMock(spec=ModuleContext)
        manager.set_context(mock_context)
        
        # Initialize modules
        await manager.initialize_modules()
        
        # Both should be initialized
        assert base_module.is_initialized
        assert dependent_module.is_initialized
    
    async def test_circular_dependency_detection(self, manager: ModuleManager):
        """Test circular dependency detection."""
        # Create circular dependency by creating modules with circular dependencies
        
        # Create a module that depends on circular_module
        class TestDependentModule(Module):
            @property
            def name(self) -> str:
                return "dependent_module"
            
            @property
            def dependencies(self) -> list:
                return ["circular_module"]
        
        # CircularDependencyModule already depends on "dependent_module"
        base_module = MockModule()
        dependent_module = TestDependentModule()
        circular_module = CircularDependencyModule()
        
        manager.register_module(base_module)
        manager.register_module(dependent_module)
        manager.register_module(circular_module)
        
        mock_context = MagicMock(spec=ModuleContext)
        manager.set_context(mock_context)
        
        # Should raise error due to circular dependency:
        # dependent_module -> circular_module -> dependent_module
        with pytest.raises(ValueError, match="Circular dependency detected"):
            await manager.initialize_modules()
    
    async def test_module_cleanup(self, manager: ModuleManager, test_module: MockModule):
        """Test module cleanup."""
        manager.register_module(test_module)
        
        mock_context = MagicMock(spec=ModuleContext)
        manager.set_context(mock_context)
        
        # Initialize and then cleanup
        await manager.initialize_modules()
        await manager.cleanup_modules()
        
        # Should not raise errors
    
    async def test_route_registration(self, manager: ModuleManager, test_module: MockModule):
        """Test route registration from modules."""
        # Set up context and initialize module first
        mock_context = MagicMock(spec=ModuleContext)
        manager.set_context(mock_context)
        manager.register_module(test_module)
        
        # Initialize the module so it's marked as initialized
        await manager.initialize_modules()
        
        # Register routes
        mock_app = MagicMock()
        manager.register_all_routes(mock_app)
        
        # Verify router was included
        mock_app.include_router.assert_called()
    
    def test_middleware_registration(self, manager: ModuleManager, test_module: MockModule):
        """Test middleware registration from modules."""
        mock_app = MagicMock()
        manager.register_module(test_module)
        
        # Should not raise errors even if module doesn't register middleware
        manager.register_all_middleware(mock_app)
    
    def test_dependency_registration(self, manager: ModuleManager, test_module: MockModule):
        """Test dependency registration from modules."""
        manager.register_module(test_module)
        
        # Should return empty dict since test module doesn't register dependencies
        deps = manager.register_all_dependencies()
        assert isinstance(deps, dict)


@pytest.mark.unit
class TestModuleDependencies:
    """Test module dependency resolution."""
    
    def test_simple_dependency_order(self):
        """Test simple dependency ordering."""
        manager = ModuleManager(Config())
        
        base_module = MockModule()
        dependent_module = DependentModule()
        
        manager.register_module(dependent_module)
        manager.register_module(base_module)
        
        # Test the private dependency sorting method
        sorted_modules = manager._sort_by_dependencies()
        
        # Base module should come before dependent module
        assert sorted_modules.index("test_module") < sorted_modules.index("dependent_module")
    
    def test_missing_dependency(self):
        """Test handling of missing dependencies."""
        manager = ModuleManager(Config())
        
        # Register only dependent module without its dependency
        dependent_module = DependentModule()
        manager.register_module(dependent_module)
        
        # Should still work (missing dependencies are ignored)
        sorted_modules = manager._sort_by_dependencies()
        assert "dependent_module" in sorted_modules 