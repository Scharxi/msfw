"""Plugin system for MSFW applications."""

import asyncio
import importlib.util
import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type

from pydantic import BaseModel

from msfw.core.config import Config


class PluginMetadata(BaseModel):
    """Metadata for a plugin."""
    
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    license: str = ""
    website: str = ""
    tags: List[str] = []
    enabled: bool = True
    priority: int = 100  # Lower numbers have higher priority


class PluginHook:
    """Represents a plugin hook point."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.handlers: List[Callable] = []
    
    def register(self, handler: Callable, priority: int = 100) -> None:
        """Register a handler for this hook."""
        self.handlers.append((priority, handler))
        self.handlers.sort(key=lambda x: x[0])  # Sort by priority
    
    async def trigger(self, *args, **kwargs) -> List[Any]:
        """Trigger all handlers for this hook."""
        results = []
        for priority, handler in self.handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    result = await handler(*args, **kwargs)
                else:
                    result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Error in hook handler {handler.__name__}: {e}")
        return results
    
    def unregister(self, handler: Callable) -> None:
        """Unregister a handler from this hook."""
        self.handlers = [(p, h) for p, h in self.handlers if h != handler]


class Plugin(ABC):
    """Base class for all plugins."""
    
    def __init__(self):
        self.metadata: Optional[PluginMetadata] = None
        self._enabled = True
        self._initialized = False
        self._hooks: Dict[str, List[Callable]] = {}
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass
    
    @property
    def version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    @property
    def description(self) -> str:
        """Plugin description."""
        return ""
    
    @property
    def author(self) -> str:
        """Plugin author."""
        return ""
    
    @property
    def priority(self) -> int:
        """Plugin priority (lower numbers have higher priority)."""
        return 100
    
    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled
    
    @property
    def initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized
    
    async def initialize(self, config: Config) -> None:
        """Initialize the plugin."""
        self.metadata = PluginMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            priority=self.priority,
        )
        await self.setup(config)
        self._initialized = True
    
    async def setup(self, config: Config) -> None:
        """Setup the plugin. Override this method."""
        pass
    
    async def cleanup(self) -> None:
        """Cleanup the plugin. Override this method."""
        pass
    
    def enable(self) -> None:
        """Enable the plugin."""
        self._enabled = True
    
    def disable(self) -> None:
        """Disable the plugin."""
        self._enabled = False
    
    def register_hook(self, hook_name: str, handler: Callable) -> None:
        """Register a hook handler."""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(handler)
    
    def get_hooks(self) -> Dict[str, List[Callable]]:
        """Get all registered hooks."""
        return self._hooks.copy()


class PluginManager:
    """Manages application plugins."""
    
    def __init__(self, config: Config):
        self.config = config
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, PluginHook] = {}
        self._enabled_plugins: Set[str] = set()
    
    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin."""
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin '{plugin.name}' already registered")
        
        self._plugins[plugin.name] = plugin
        if plugin.enabled:
            self._enabled_plugins.add(plugin.name)
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)
    
    def list_plugins(self) -> Dict[str, Plugin]:
        """List all registered plugins."""
        return self._plugins.copy()
    
    def list_enabled_plugins(self) -> Dict[str, Plugin]:
        """List all enabled plugins."""
        return {
            name: plugin 
            for name, plugin in self._plugins.items() 
            if name in self._enabled_plugins
        }
    
    def enable_plugin(self, name: str) -> None:
        """Enable a plugin."""
        if name in self._plugins:
            self._plugins[name].enable()
            self._enabled_plugins.add(name)
    
    def disable_plugin(self, name: str) -> None:
        """Disable a plugin."""
        if name in self._plugins:
            self._plugins[name].disable()
            self._enabled_plugins.discard(name)
    
    def remove_plugin(self, name: str) -> None:
        """Remove a plugin."""
        if name in self._plugins:
            del self._plugins[name]
            self._enabled_plugins.discard(name)
    
    def register_hook(self, name: str, description: str = "") -> PluginHook:
        """Register a new hook point."""
        if name in self._hooks:
            return self._hooks[name]
        
        hook = PluginHook(name, description)
        self._hooks[name] = hook
        return hook
    
    def get_hook(self, name: str) -> Optional[PluginHook]:
        """Get a hook by name."""
        return self._hooks.get(name)
    
    def list_hooks(self) -> Dict[str, PluginHook]:
        """List all registered hooks."""
        return self._hooks.copy()
    
    async def initialize_plugins(self) -> None:
        """Initialize all enabled plugins."""
        # Sort plugins by priority
        enabled_plugins = [
            self._plugins[name] 
            for name in self._enabled_plugins
        ]
        enabled_plugins.sort(key=lambda p: p.priority)
        
        for plugin in enabled_plugins:
            try:
                await plugin.initialize(self.config)
                
                # Register plugin hooks
                for hook_name, handlers in plugin.get_hooks().items():
                    hook = self.register_hook(hook_name)
                    for handler in handlers:
                        hook.register(handler, plugin.priority)
                
                print(f"Initialized plugin: {plugin.name}")
            except Exception as e:
                print(f"Failed to initialize plugin {plugin.name}: {e}")
                self.disable_plugin(plugin.name)
    
    async def cleanup_plugins(self) -> None:
        """Cleanup all plugins."""
        for plugin in self._plugins.values():
            if plugin.initialized:
                try:
                    await plugin.cleanup()
                    print(f"Cleaned up plugin: {plugin.name}")
                except Exception as e:
                    print(f"Error cleaning up plugin {plugin.name}: {e}")
    
    async def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Trigger a hook and return results from all handlers."""
        hook = self._hooks.get(hook_name)
        if hook:
            return await hook.trigger(*args, **kwargs)
        return []
    
    def discover_plugins(self, plugins_dir: str) -> None:
        """Auto-discover plugins from a directory."""
        plugins_path = Path(plugins_dir)
        if not plugins_path.exists():
            return
        
        for plugin_path in plugins_path.iterdir():
            if plugin_path.is_dir() and not plugin_path.name.startswith('_'):
                self._load_plugin_from_path(plugin_path)
            elif plugin_path.suffix == '.py' and not plugin_path.name.startswith('_'):
                self._load_plugin_from_file(plugin_path)
    
    def _load_plugin_from_path(self, plugin_path: Path) -> None:
        """Load a plugin from a directory path."""
        plugin_file = plugin_path / "__init__.py"
        if not plugin_file.exists():
            return
        
        self._load_plugin_from_file(plugin_file, plugin_path.name)
    
    def _load_plugin_from_file(self, plugin_file: Path, module_name: Optional[str] = None) -> None:
        """Load a plugin from a file path."""
        try:
            # Import the plugin module
            module_name = module_name or plugin_file.stem
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            
            if spec and spec.loader:
                plugin_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin_mod)
                
                # Look for Plugin classes
                for name, obj in inspect.getmembers(plugin_mod):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, Plugin) and 
                        obj != Plugin):
                        plugin_instance = obj()
                        self.register_plugin(plugin_instance)
                        break
        except Exception as e:
            print(f"Failed to load plugin from {plugin_file}: {e}")


# Predefined hooks for common use cases
PREDEFINED_HOOKS = [
    ("app_startup", "Triggered when the application starts up"),
    ("app_shutdown", "Triggered when the application shuts down"),
    ("before_request", "Triggered before processing a request"),
    ("after_request", "Triggered after processing a request"),
    ("before_database_init", "Triggered before database initialization"),
    ("after_database_init", "Triggered after database initialization"),
    ("before_module_init", "Triggered before module initialization"),
    ("after_module_init", "Triggered after module initialization"),
    ("user_login", "Triggered when a user logs in"),
    ("user_logout", "Triggered when a user logs out"),
    ("user_register", "Triggered when a user registers"),
] 