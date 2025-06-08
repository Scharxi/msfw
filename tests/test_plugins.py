"""Tests for the MSFW plugin system."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from msfw.core.config import Config
from msfw.core.plugin import Plugin, PluginHook, PluginManager, PluginMetadata
from tests.conftest import TestPlugin

# Individual async tests are marked with @pytest.mark.asyncio


@pytest.mark.unit
class TestPluginMetadata:
    """Test plugin metadata."""
    
    def test_default_metadata(self):
        """Test default metadata values."""
        metadata = PluginMetadata(name="test")
        
        assert metadata.name == "test"
        assert metadata.version == "1.0.0"
        assert metadata.description == ""
        assert metadata.author == ""
        assert metadata.license == ""
        assert metadata.website == ""
        assert metadata.tags == []
        assert metadata.enabled is True
        assert metadata.priority == 100
    
    def test_custom_metadata(self):
        """Test custom metadata values."""
        metadata = PluginMetadata(
            name="custom",
            version="2.0.0",
            description="Custom plugin",
            author="Test Author",
            license="MIT",
            website="https://example.com",
            tags=["tag1", "tag2"],
            enabled=False,
            priority=50,
        )
        
        assert metadata.name == "custom"
        assert metadata.version == "2.0.0"
        assert metadata.description == "Custom plugin"
        assert metadata.author == "Test Author"
        assert metadata.license == "MIT"
        assert metadata.website == "https://example.com"
        assert metadata.tags == ["tag1", "tag2"]
        assert metadata.enabled is False
        assert metadata.priority == 50


@pytest.mark.unit
class TestPluginHook:
    """Test plugin hook functionality."""
    
    def test_hook_creation(self):
        """Test hook creation."""
        hook = PluginHook("test_hook", "Test hook description")
        
        assert hook.name == "test_hook"
        assert hook.description == "Test hook description"
        assert hook.handlers == []
    
    def test_handler_registration(self):
        """Test handler registration."""
        hook = PluginHook("test_hook")
        
        handler1 = MagicMock()
        handler2 = MagicMock()
        
        # Register handlers with different priorities
        hook.register(handler1, priority=100)
        hook.register(handler2, priority=50)
        
        # Handlers should be sorted by priority
        assert len(hook.handlers) == 2
        assert hook.handlers[0][0] == 50  # Lower priority first
        assert hook.handlers[0][1] == handler2
        assert hook.handlers[1][0] == 100
        assert hook.handlers[1][1] == handler1
    
    @pytest.mark.asyncio
    async def test_hook_triggering(self):
        """Test hook triggering."""
        hook = PluginHook("test_hook")
        
        # Register sync and async handlers
        sync_handler = MagicMock(return_value="sync_result")
        async_handler = AsyncMock(return_value="async_result")
        
        hook.register(sync_handler, priority=100)
        hook.register(async_handler, priority=50)
        
        # Trigger hook
        results = await hook.trigger(arg1="value1", arg2="value2")
        
        # Verify handlers were called in priority order
        async_handler.assert_called_once_with(arg1="value1", arg2="value2")
        sync_handler.assert_called_once_with(arg1="value1", arg2="value2")
        
        # Verify results
        assert results == ["async_result", "sync_result"]
    
    @pytest.mark.asyncio
    async def test_hook_error_handling(self):
        """Test hook error handling."""
        hook = PluginHook("test_hook")
        
        def failing_handler(**kwargs):
            raise ValueError("Test error")
        
        good_handler = MagicMock(return_value="good_result")
        
        hook.register(failing_handler, priority=50)
        hook.register(good_handler, priority=100)
        
        # Should not raise but continue with other handlers
        results = await hook.trigger()
        
        # Good handler should still execute
        good_handler.assert_called_once()
        assert "good_result" in results
    
    def test_handler_unregistration(self):
        """Test handler unregistration."""
        hook = PluginHook("test_hook")
        
        handler1 = MagicMock()
        handler2 = MagicMock()
        
        hook.register(handler1)
        hook.register(handler2)
        assert len(hook.handlers) == 2
        
        # Unregister one handler
        hook.unregister(handler1)
        assert len(hook.handlers) == 1
        assert hook.handlers[0][1] == handler2


@pytest.mark.unit
class TestPluginBase:
    """Test base plugin functionality."""
    
    def test_plugin_properties(self, test_plugin: TestPlugin):
        """Test plugin properties."""
        assert test_plugin.name == "test_plugin"
        assert test_plugin.version == "1.0.0"
        assert test_plugin.description == "Test plugin for unit tests"
        assert test_plugin.author == ""
        assert test_plugin.priority == 100
        assert test_plugin.enabled is True
        assert test_plugin.initialized is False
    
    @pytest.mark.asyncio
    async def test_plugin_initialization(self, test_plugin: TestPlugin):
        """Test plugin initialization."""
        config = Config()
        
        # Initialize plugin
        await test_plugin.initialize(config)
        
        # Verify initialization
        assert test_plugin.initialized is True
        assert test_plugin.setup_called is True
        assert test_plugin.metadata is not None
        assert test_plugin.metadata.name == "test_plugin"
    
    @pytest.mark.asyncio
    async def test_plugin_cleanup(self, test_plugin: TestPlugin):
        """Test plugin cleanup."""
        config = Config()
        await test_plugin.initialize(config)
        
        # Cleanup
        await test_plugin.cleanup()
        
        assert test_plugin.cleanup_called is True
    
    def test_plugin_enable_disable(self, test_plugin: TestPlugin):
        """Test plugin enable/disable."""
        assert test_plugin.enabled is True
        
        test_plugin.disable()
        assert test_plugin.enabled is False
        
        test_plugin.enable()
        assert test_plugin.enabled is True
    
    def test_hook_registration(self, test_plugin: TestPlugin):
        """Test hook registration in plugin."""
        handler = MagicMock()
        
        test_plugin.register_hook("test_event", handler)
        
        hooks = test_plugin.get_hooks()
        assert "test_event" in hooks
        assert handler in hooks["test_event"]


@pytest.mark.integration
class TestPluginManager:
    """Test plugin manager."""
    
    @pytest.fixture
    def manager(self, test_config: Config):
        """Create a plugin manager."""
        return PluginManager(test_config)
    
    def test_plugin_registration(self, manager: PluginManager, test_plugin: TestPlugin):
        """Test plugin registration."""
        # Register plugin
        manager.register_plugin(test_plugin)
        
        # Verify registration
        assert manager.get_plugin("test_plugin") == test_plugin
        assert "test_plugin" in manager.list_plugins()
        assert "test_plugin" in manager.list_enabled_plugins()
    
    def test_duplicate_plugin_registration(self, manager: PluginManager, test_plugin: TestPlugin):
        """Test duplicate plugin registration."""
        # Register plugin
        manager.register_plugin(test_plugin)
        
        # Try to register same plugin again
        with pytest.raises(ValueError, match="Plugin 'test_plugin' already registered"):
            manager.register_plugin(test_plugin)
    
    def test_plugin_enable_disable(self, manager: PluginManager, test_plugin: TestPlugin):
        """Test plugin enable/disable through manager."""
        manager.register_plugin(test_plugin)
        
        # Disable plugin
        manager.disable_plugin("test_plugin")
        assert test_plugin.enabled is False
        assert "test_plugin" not in manager.list_enabled_plugins()
        
        # Enable plugin
        manager.enable_plugin("test_plugin")
        assert test_plugin.enabled is True
        assert "test_plugin" in manager.list_enabled_plugins()
    
    def test_plugin_removal(self, manager: PluginManager, test_plugin: TestPlugin):
        """Test plugin removal."""
        manager.register_plugin(test_plugin)
        assert "test_plugin" in manager.list_plugins()
        
        manager.remove_plugin("test_plugin")
        assert "test_plugin" not in manager.list_plugins()
        assert manager.get_plugin("test_plugin") is None
    
    def test_hook_registration(self, manager: PluginManager):
        """Test hook registration in manager."""
        # Register a hook
        hook = manager.register_hook("test_event", "Test event description")
        
        assert isinstance(hook, PluginHook)
        assert hook.name == "test_event"
        assert hook.description == "Test event description"
        
        # Get hook
        retrieved_hook = manager.get_hook("test_event")
        assert retrieved_hook == hook
        
        # List hooks
        hooks = manager.list_hooks()
        assert "test_event" in hooks
    
    def test_duplicate_hook_registration(self, manager: PluginManager):
        """Test duplicate hook registration returns same hook."""
        hook1 = manager.register_hook("test_event", "Description 1")
        hook2 = manager.register_hook("test_event", "Description 2")
        
        # Should return the same hook instance
        assert hook1 == hook2
    
    @pytest.mark.asyncio
    async def test_hook_triggering(self, manager: PluginManager):
        """Test hook triggering through manager."""
        # Register hook and handler
        hook = manager.register_hook("test_event")
        handler = AsyncMock(return_value="result")
        hook.register(handler)
        
        # Trigger hook through manager
        results = await manager.trigger_hook("test_event", arg="value")
        
        handler.assert_called_once_with(arg="value")
        assert results == ["result"]
    
    @pytest.mark.asyncio
    async def test_nonexistent_hook_triggering(self, manager: PluginManager):
        """Test triggering non-existent hook."""
        results = await manager.trigger_hook("nonexistent_event")
        assert results == []
    
    @pytest.mark.asyncio
    async def test_plugin_initialization_by_priority(self, manager: PluginManager):
        """Test plugin initialization respects priority."""
        # Use the dedicated priority test plugins instead
        high_priority_plugin = HighPriorityPlugin()
        low_priority_plugin = LowPriorityPlugin()
        
        # Register in reverse priority order
        manager.register_plugin(low_priority_plugin)
        manager.register_plugin(high_priority_plugin)
        
        # Initialize plugins
        await manager.initialize_plugins()
        
        # Both should be initialized
        assert high_priority_plugin.initialized
        assert low_priority_plugin.initialized
    
    @pytest.mark.asyncio
    async def test_plugin_cleanup(self, manager: PluginManager, test_plugin: TestPlugin):
        """Test plugin cleanup."""
        manager.register_plugin(test_plugin)
        await manager.initialize_plugins()
        
        # Cleanup
        await manager.cleanup_plugins()
        
        assert test_plugin.cleanup_called
    
    @pytest.mark.asyncio
    async def test_plugin_hook_integration(self, manager: PluginManager, test_plugin: TestPlugin):
        """Test plugin hook integration."""
        # Initialize plugin (which registers hooks)
        manager.register_plugin(test_plugin)
        await manager.initialize_plugins()
        
        # Trigger the hook that plugin registered for
        await manager.trigger_hook("test_event", data="test_data")
        
        # Verify plugin received the hook call
        assert len(test_plugin.hook_calls) == 1
        assert test_plugin.hook_calls[0]["data"] == "test_data"


class HighPriorityPlugin(Plugin):
    """Test plugin with high priority."""
    
    def __init__(self):
        super().__init__()
        self.initialized_order = None
    
    @property
    def name(self) -> str:
        return "high_priority"
    
    @property
    def priority(self) -> int:
        return 10
    
    async def setup(self, config: Config) -> None:
        # Track initialization order
        if not hasattr(HighPriorityPlugin, 'initialization_counter'):
            HighPriorityPlugin.initialization_counter = 0
        HighPriorityPlugin.initialization_counter += 1
        self.initialized_order = HighPriorityPlugin.initialization_counter


class LowPriorityPlugin(Plugin):
    """Test plugin with low priority."""
    
    def __init__(self):
        super().__init__()
        self.initialized_order = None
    
    @property
    def name(self) -> str:
        return "low_priority"
    
    @property
    def priority(self) -> int:
        return 200
    
    async def setup(self, config: Config) -> None:
        # Track initialization order
        if not hasattr(HighPriorityPlugin, 'initialization_counter'):
            HighPriorityPlugin.initialization_counter = 0
        HighPriorityPlugin.initialization_counter += 1
        self.initialized_order = HighPriorityPlugin.initialization_counter


@pytest.mark.integration
class TestPluginPriority:
    """Test plugin priority handling."""
    
    @pytest.mark.asyncio
    async def test_initialization_priority_order(self, test_config: Config):
        """Test that plugins are initialized in priority order."""
        manager = PluginManager(test_config)
        
        # Reset counter
        if hasattr(HighPriorityPlugin, 'initialization_counter'):
            HighPriorityPlugin.initialization_counter = 0
        
        high_plugin = HighPriorityPlugin()
        low_plugin = LowPriorityPlugin()
        
        # Register in reverse priority order
        manager.register_plugin(low_plugin)
        manager.register_plugin(high_plugin)
        
        # Initialize
        await manager.initialize_plugins()
        
        # High priority should initialize first
        assert high_plugin.initialized_order < low_plugin.initialized_order


@pytest.mark.unit
class TestPluginDiscovery:
    """Test plugin discovery functionality."""
    
    def test_discover_plugins_no_directory(self, test_config: Config):
        """Test discovering plugins when directory doesn't exist."""
        manager = PluginManager(test_config)
        
        # Should not raise error
        manager.discover_plugins("nonexistent_directory")
        
        # No plugins should be registered
        assert len(manager.list_plugins()) == 0
    
    def test_discover_plugins_empty_directory(self, test_config: Config, temp_dir):
        """Test discovering plugins in empty directory."""
        manager = PluginManager(test_config)
        plugins_dir = temp_dir / "plugins"
        plugins_dir.mkdir()
        
        # Should not raise error
        manager.discover_plugins(str(plugins_dir))
        
        # No plugins should be registered
        assert len(manager.list_plugins()) == 0 