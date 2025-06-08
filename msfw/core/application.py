"""Main application class for MSFW."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

from msfw.core.config import Config
from msfw.core.database import Database, DatabaseManager, db_manager
from msfw.core.module import Module, ModuleContext, ModuleManager
from msfw.core.plugin import Plugin, PluginManager, PREDEFINED_HOOKS
from msfw.core.openapi import OpenAPIManager, setup_openapi_documentation
from msfw.core.versioning import version_manager
from msfw.middleware.logging import LoggingMiddleware
from msfw.middleware.monitoring import MonitoringMiddleware
from msfw.middleware.security import SecurityMiddleware
from msfw.sdk import ServiceSDK


# Metrics registry will be handled in middleware to avoid import-time registration


class MSFWApplication:
    """Main MSFW application class."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.app: Optional[FastAPI] = None
        self._fastapi_app: Optional[FastAPI] = None  # Alias for tests
        self.database: Optional[Database] = None
        self.module_manager: Optional[ModuleManager] = None
        self.plugin_manager: Optional[PluginManager] = None
        self.openapi_manager: Optional[OpenAPIManager] = None
        self.sdk: Optional[ServiceSDK] = None
        self._initialized = False
        self._pending_modules: list = []  # For modules added before init
        self._pending_plugins: list = []  # For plugins added before init
        self._setup_logging()
    
    @property
    def initialized(self) -> bool:
        """Check if application is initialized."""
        return self._initialized
    
    def add_module(self, module: "Module") -> None:
        """Add a module to the application."""
        if not self.module_manager:
            # Store for later registration
            self._pending_modules.append(module)
        else:
            self.module_manager.register_module(module)
    
    def add_plugin(self, plugin: "Plugin") -> None:
        """Add a plugin to the application."""
        if not self.plugin_manager:
            # Store for later registration
            self._pending_plugins.append(plugin)
        else:
            self.plugin_manager.register_plugin(plugin)
    
    def _setup_logging(self) -> None:
        """Setup structured logging."""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
                if self.config.logging.format == "json"
                else structlog.dev.ConsoleRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        logging.basicConfig(
            level=getattr(logging, self.config.logging.level.upper()),
            format="%(message)s",
        )
    
    async def initialize(self) -> None:
        """Initialize the application."""
        if self._initialized:
            return
        
        # Create FastAPI app
        self.app = FastAPI(
            title=self.config.openapi.title or self.config.app_name,
            version=self.config.openapi.version or self.config.version,
            description=self.config.openapi.description or self.config.description,
            debug=self.config.debug,
            docs_url=None,  # Will be handled by OpenAPI manager
            redoc_url=None,  # Will be handled by OpenAPI manager
            openapi_url=None,  # Will be handled by OpenAPI manager
            lifespan=self._lifespan,
        )
        self._fastapi_app = self.app  # Keep alias for tests
        
        # Setup database
        await self._setup_database()
        
        # Setup plugin manager
        self.plugin_manager = PluginManager(self.config)
        
        # Register predefined hooks
        for hook_name, description in PREDEFINED_HOOKS:
            self.plugin_manager.register_hook(hook_name, description)
        
        # Setup module manager
        self.module_manager = ModuleManager(self.config)
        
        # Setup service SDK (disabled for tests)
        import os
        if not os.environ.get('MSFW_DISABLE_SDK'):
            self.sdk = ServiceSDK(config=self.config)
        else:
            self.sdk = None
        
        # Setup middleware
        self._setup_middleware()
        
        # Setup routes
        self._setup_routes()
        
        # Register routes from decorator registry
        try:
            from msfw.decorators import RouteRegistry
            RouteRegistry.register_routes(self.app)
        except Exception as e:
            # If route registration fails, just continue
            import structlog
            logger = structlog.get_logger()
            logger.debug("Route registration failed", error=str(e))
            
        # Apply versioned routes to app
        try:
            from msfw.core.versioning import version_manager as vm
            vm.apply_routes_to_app(self.app)
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.debug("Versioned route registration failed", error=str(e))
        
        # Setup OpenAPI documentation AFTER all routes are registered
        self.openapi_manager = setup_openapi_documentation(
            self.app, 
            self.config, 
            version_manager
        )
        
        # Auto-discover plugins and modules
        if self.config.auto_discover_plugins:
            self.plugin_manager.discover_plugins(self.config.plugins_dir)
        
        if self.config.auto_discover_modules:
            self.module_manager.discover_modules(self.config.modules_directory)
        
        # Register pending modules and plugins
        for module in self._pending_modules:
            self.module_manager.register_module(module)
        self._pending_modules.clear()
        
        for plugin in self._pending_plugins:
            self.plugin_manager.register_plugin(plugin)
        self._pending_plugins.clear()
        
        # Initialize plugins for tests (since TestClient doesn't trigger lifespan)
        if self.plugin_manager:
            await self.plugin_manager.initialize_plugins()
        
        # Auto-register service if enabled
        if hasattr(self.config, 'app_name') and self.sdk:
            try:
                await self.sdk.register_current_service(
                    service_name=self.config.app_name,
                    version=getattr(self.config, 'version', '1.0.0'),
                    host=self.config.host,
                    port=self.config.port
                )
            except Exception as e:
                structlog.get_logger().warning(f"Failed to auto-register service: {e}")
        
        # Initialize module context early so it's available for tests
        if self.module_manager and self.database:
            from msfw.core.module import ModuleContext
            context = ModuleContext(
                app=self.app,
                config=self.config,
                database=self.database,
            )
            self.module_manager.set_context(context)
            
            # Initialize modules for tests (since TestClient doesn't trigger lifespan)
            await self.module_manager.initialize_modules()
            
            # Register module routes
            self.module_manager.register_all_routes(self.app)
        
        self._initialized = True
    
    async def _setup_database(self) -> None:
        """Setup database connection."""
        self.database = db_manager.add_database(
            "default", 
            self.config.database, 
            is_default=True
        )
        await self.database.initialize()
    
    def _setup_middleware(self) -> None:
        """Setup application middleware."""
        if not self.app:
            return
        
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors.allow_origins,
            allow_credentials=self.config.cors.allow_credentials,
            allow_methods=self.config.cors.allow_methods,
            allow_headers=self.config.cors.allow_headers,
        )
        
        # GZip middleware
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # Custom middleware
        self.app.add_middleware(SecurityMiddleware, config=self.config)
        self.app.add_middleware(LoggingMiddleware, config=self.config)
        
        if self.config.monitoring.enabled:
            from starlette.middleware.base import BaseHTTPMiddleware
            self.app.add_middleware(
                BaseHTTPMiddleware,
                dispatch=MonitoringMiddleware(self.app, config=self.config).dispatch
            )
    
    def _setup_routes(self) -> None:
        """Setup application routes."""
        if not self.app:
            return
        
        # Health check endpoint (only if monitoring is enabled)
        if self.config.monitoring.enabled:
            @self.app.get(self.config.monitoring.health_check_path)
            async def health_check():
                """Health check endpoint."""
                from datetime import datetime, timezone
                
                health_status = {
                    "status": "healthy", 
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "components": {}
                }
                
                # Check database
                if self.database:
                    db_healthy = await self.database.health_check()
                    db_status = {"status": "healthy" if db_healthy else "unhealthy"}
                    health_status["components"]["database"] = db_status
                    # Also include at top level for backward compatibility
                    health_status["database"] = db_status
                
                # Check modules
                if self.module_manager:
                    modules = self.module_manager.list_modules()
                    health_status["components"]["modules"] = {
                        "status": "healthy",
                        "count": len(modules),
                        "initialized": sum(1 for m in modules.values() if m.is_initialized)
                    }
                
                # Check plugins
                if self.plugin_manager:
                    plugins = self.plugin_manager.list_enabled_plugins()
                    health_status["components"]["plugins"] = {
                        "status": "healthy",
                        "count": len(plugins),
                        "enabled": len(plugins)
                    }
                
                overall_healthy = all(
                    comp.get("status") == "healthy" 
                    for comp in health_status["components"].values()
                )
                health_status["status"] = "healthy" if overall_healthy else "unhealthy"
                
                return health_status
        
        # Metrics endpoint (only if monitoring and prometheus are enabled)
        if self.config.monitoring.enabled and self.config.monitoring.prometheus_enabled:
            @self.app.get(self.config.monitoring.metrics_path)
            async def metrics():
                """Prometheus metrics endpoint."""
                from prometheus_client import generate_latest, REGISTRY
                return Response(
                    generate_latest(REGISTRY),
                    media_type="text/plain"
                )
        
        # Info endpoint
        @self.app.get("/info")
        async def info():
            """Application information endpoint."""
            info_data = {
                "name": self.config.app_name,
                "version": self.config.version,
                "debug": self.config.debug,
            }
            
            if self.module_manager:
                modules = self.module_manager.list_modules()
                info_data["modules"] = {
                    name: {
                        "version": module.version,
                        "description": module.description,
                        "initialized": module.is_initialized,
                    }
                    for name, module in modules.items()
                }
            
            if self.plugin_manager:
                plugins = self.plugin_manager.list_plugins()
                info_data["plugins"] = {
                    name: {
                        "version": plugin.version,
                        "description": plugin.description,
                        "enabled": plugin.enabled,
                        "initialized": plugin.initialized,
                    }
                    for name, plugin in plugins.items()
                }
            
            return info_data
    
    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """Application lifespan manager."""
        # Startup
        logger = structlog.get_logger()
        logger.info("Starting MSFW application", app_name=self.config.app_name)
        
        # Trigger startup hook
        if self.plugin_manager:
            await self.plugin_manager.trigger_hook("app_startup", app=app)
        
        # Initialize plugins
        if self.plugin_manager:
            await self.plugin_manager.initialize_plugins()
        
        # Initialize modules
        if self.module_manager and self.database:
            context = ModuleContext(
                app=app,
                config=self.config,
                database=self.database,
            )
            self.module_manager.set_context(context)
            await self.module_manager.initialize_modules()
            
            # Register module routes and middleware
            self.module_manager.register_all_routes(app)
            self.module_manager.register_all_middleware(app)
        
        logger.info("MSFW application started successfully")
        
        yield
        
        # Shutdown
        logger.info("Shutting down MSFW application")
        
        # Trigger shutdown hook
        if self.plugin_manager:
            await self.plugin_manager.trigger_hook("app_shutdown", app=app)
        
        # Cleanup modules
        if self.module_manager:
            await self.module_manager.cleanup_modules()
        
        # Cleanup plugins
        if self.plugin_manager:
            await self.plugin_manager.cleanup_plugins()
        
        # Close database
        if self.database:
            await self.database.close()
        
        # Shutdown SDK
        if self.sdk:
            await self.sdk.shutdown()
        
        logger.info("MSFW application shut down successfully")
    
    def register_module(self, module: Module) -> None:
        """Register a module."""
        if not self.module_manager:
            raise RuntimeError("Application not initialized")
        self.module_manager.register_module(module)
    
    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin."""
        if not self.plugin_manager:
            raise RuntimeError("Application not initialized")
        self.plugin_manager.register_plugin(plugin)
    
    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        if not self.app:
            raise RuntimeError("Application not initialized")
        return self.app
    
    def get_database(self, name: str = "default") -> Database:
        """Get a database instance."""
        return db_manager.get_database(name)
    
    async def cleanup(self) -> None:
        """Cleanup application resources."""
        if not self._initialized:
            return
        
        logger = structlog.get_logger()
        logger.info("Cleaning up MSFW application")
        
        # Cleanup modules
        if self.module_manager:
            await self.module_manager.cleanup_modules()
        
        # Cleanup plugins
        if self.plugin_manager:
            await self.plugin_manager.cleanup_plugins()
        
        # Close database
        if self.database:
            await self.database.close()
        
        # Shutdown SDK
        if self.sdk:
            await self.sdk.shutdown()
        
        self._initialized = False
        logger.info("MSFW application cleanup completed")
    
    async def run(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs
    ) -> None:
        """Run the application."""
        import uvicorn
        
        if not self._initialized:
            await self.initialize()
        
        # Create server config
        config = uvicorn.Config(
            self.app,
            host=host or self.config.host,
            port=port or self.config.port,
            **kwargs
        )
        
        # Create and run server
        server = uvicorn.Server(config)
        await server.serve()
    
    def run_sync(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs
    ) -> None:
        """Run the application synchronously (for use outside async context)."""
        import uvicorn
        import asyncio
        
        async def start():
            if not self._initialized:
                await self.initialize()
        
        # Initialize if needed
        asyncio.run(start())
        
        # Run with uvicorn.run (blocking)
        uvicorn.run(
            self.app,
            host=host or self.config.host,
            port=port or self.config.port,
            **kwargs
        ) 