"""Module system for MSFW applications."""

import asyncio
import importlib
import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from fastapi import APIRouter, Depends, FastAPI
from pydantic import BaseModel

from msfw.core.config import Config
from msfw.core.database import Database


class ModuleMetadata(BaseModel):
    """Metadata for a module."""
    
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = []
    tags: List[str] = []
    enabled: bool = True


class ModuleContext:
    """Context passed to modules during initialization."""
    
    def __init__(
        self,
        app: FastAPI,
        config: Config,
        database: Optional[Database] = None,
        router: Optional[APIRouter] = None,
    ):
        self.app = app
        self.config = config
        self.database = database
        self.router = router or APIRouter()
        self._services: Dict[str, Any] = {}
        self._hooks: Dict[str, List[Callable]] = {}
    
    def register_service(self, name: str, service: Any) -> None:
        """Register a service in the module context."""
        self._services[name] = service
    
    def get_service(self, name: str) -> Any:
        """Get a service from the module context."""
        return self._services.get(name)
    
    def register_hook(self, event: str, handler: Callable) -> None:
        """Register a hook for an event."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)
    
    async def trigger_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """Trigger all hooks for an event."""
        results = []
        if event in self._hooks:
            for handler in self._hooks[event]:
                try:
                    if inspect.iscoroutinefunction(handler):
                        result = await handler(*args, **kwargs)
                    else:
                        result = handler(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    # Log error but continue with other hooks
                    print(f"Error in hook {handler.__name__}: {e}")
        return results


class Module(ABC):
    """Base class for all modules."""
    
    def __init__(self):
        self.metadata: Optional[ModuleMetadata] = None
        self.context: Optional[ModuleContext] = None
        self._initialized = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Module name."""
        pass
    
    @property
    def version(self) -> str:
        """Module version."""
        return "1.0.0"
    
    @property
    def description(self) -> str:
        """Module description."""
        return ""
    
    @property
    def dependencies(self) -> List[str]:
        """Module dependencies."""
        return []
    
    async def initialize(self, context: ModuleContext) -> None:
        """Initialize the module."""
        self.context = context
        self.metadata = ModuleMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            dependencies=self.dependencies,
        )
        await self.setup()
        self._initialized = True
    
    async def setup(self) -> None:
        """Setup the module. Override this method."""
        pass
    
    async def cleanup(self) -> None:
        """Cleanup the module. Override this method."""
        pass
    
    def register_routes(self, router: APIRouter) -> None:
        """Register routes. Override this method."""
        pass
    
    def register_middleware(self, app: FastAPI) -> None:
        """Register middleware. Override this method."""
        pass
    
    def register_dependencies(self) -> Dict[str, Callable]:
        """Register dependencies. Override this method."""
        return {}
    
    @property
    def is_initialized(self) -> bool:
        """Check if module is initialized."""
        return self._initialized


class ModuleManager:
    """Manages application modules."""
    
    def __init__(self, config: Config):
        self.config = config
        self._modules: Dict[str, Module] = {}
        self._module_order: List[str] = []
        self._context: Optional[ModuleContext] = None
    
    def set_context(self, context: ModuleContext) -> None:
        """Set the module context."""
        self._context = context
        
        # Apply context to all registered modules
        for module in self._modules.values():
            module.context = context
    
    def register_module(self, module: Module) -> None:
        """Register a module."""
        if module.name in self._modules:
            raise ValueError(f"Module '{module.name}' already registered")
        
        self._modules[module.name] = module
        self._module_order.append(module.name)
        
        # Set context on the module if we have one
        if self._context:
            module.context = self._context
    
    def get_module(self, name: str) -> Optional[Module]:
        """Get a module by name."""
        return self._modules.get(name)
    
    def list_modules(self) -> Dict[str, Module]:
        """List all registered modules."""
        return self._modules.copy()
    
    def remove_module(self, name: str) -> None:
        """Remove a module."""
        if name in self._modules:
            del self._modules[name]
            if name in self._module_order:
                self._module_order.remove(name)
    
    async def initialize_modules(self) -> None:
        """Initialize all modules in dependency order."""
        if not self._context:
            raise RuntimeError("Module context not set")
        
        # Sort modules by dependencies
        sorted_modules = self._sort_by_dependencies()
        
        for module_name in sorted_modules:
            module = self._modules[module_name]
            try:
                await module.initialize(self._context)
                print(f"Initialized module: {module_name}")
            except Exception as e:
                print(f"Failed to initialize module {module_name}: {e}")
                raise
    
    async def cleanup_modules(self) -> None:
        """Cleanup all modules in reverse order."""
        for module_name in reversed(self._module_order):
            module = self._modules[module_name]
            try:
                await module.cleanup()
                print(f"Cleaned up module: {module_name}")
            except Exception as e:
                print(f"Error cleaning up module {module_name}: {e}")
    
    def register_all_routes(self, app: FastAPI) -> None:
        """Register routes from all modules."""
        for module in self._modules.values():
            if module.is_initialized:
                router = APIRouter()
                module.register_routes(router)
                if router.routes:
                    app.include_router(
                        router,
                        prefix=f"/{module.name}",
                        tags=[module.name],
                    )
    
    def register_all_middleware(self, app: FastAPI) -> None:
        """Register middleware from all modules."""
        for module in self._modules.values():
            if module.is_initialized:
                module.register_middleware(app)
    
    def register_all_dependencies(self) -> Dict[str, Callable]:
        """Register dependencies from all modules."""
        dependencies = {}
        for module in self._modules.values():
            if module.is_initialized:
                module_deps = module.register_dependencies()
                dependencies.update(module_deps)
        return dependencies
    
    def discover_modules(self, modules_dir: str) -> None:
        """Auto-discover modules from a directory."""
        modules_path = Path(modules_dir)
        if not modules_path.exists():
            return
        
        for module_path in modules_path.iterdir():
            if module_path.is_dir() and not module_path.name.startswith('_'):
                # Directory-based module
                self._load_module_from_path(module_path)
            elif (module_path.is_file() and 
                  module_path.suffix == '.py' and 
                  not module_path.name.startswith('_')):
                # Single-file module
                self._load_module_from_file(module_path)
    
    def _load_module_from_path(self, module_path: Path) -> None:
        """Load a module from a directory path."""
        module_file = module_path / "__init__.py"
        if not module_file.exists():
            return
        
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(
                module_path.name, 
                module_file
            )
            if spec and spec.loader:
                module_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module_mod)
                
                # Look for Module classes
                for name, obj in inspect.getmembers(module_mod):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, Module) and 
                        obj != Module):
                        module_instance = obj()
                        self.register_module(module_instance)
                        break
        except Exception as e:
            print(f"Failed to load module from {module_path}: {e}")
    
    def _load_module_from_file(self, module_file: Path) -> None:
        """Load a module from a single file."""
        try:
            # Import the module
            module_name = module_file.stem
            spec = importlib.util.spec_from_file_location(
                module_name, 
                module_file
            )
            if spec and spec.loader:
                module_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module_mod)
                
                # Look for Module classes or a module variable
                module_instance = None
                
                # First, look for a 'module' variable (like in the test)
                if hasattr(module_mod, 'module') and isinstance(module_mod.module, Module):
                    module_instance = module_mod.module
                else:
                    # Look for Module classes
                    for name, obj in inspect.getmembers(module_mod):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, Module) and 
                            obj != Module):
                            module_instance = obj()
                            break
                
                if module_instance:
                    self.register_module(module_instance)
                    
        except Exception as e:
            print(f"Failed to load module from {module_file}: {e}")
    
    def _sort_by_dependencies(self) -> List[str]:
        """Sort modules by their dependencies using topological sort."""
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(module_name: str):
            if module_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {module_name}")
            
            if module_name not in visited:
                temp_visited.add(module_name)
                
                # Visit dependencies first
                module = self._modules[module_name]
                for dep in module.dependencies:
                    if dep in self._modules:
                        visit(dep)
                
                temp_visited.remove(module_name)
                visited.add(module_name)
                result.append(module_name)
        
        for module_name in self._module_order:
            if module_name not in visited:
                visit(module_name)
        
        return result 