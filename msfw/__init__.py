"""
MSFW - Modular Microservices Framework
====================================

A highly modular and extensible framework for building microservices with FastAPI, 
Pydantic, and SQLAlchemy.

Features:
- Plugin-based architecture
- Configurable components
- Auto-discovery of modules
- Built-in authentication and authorization
- Database management with migrations
- Monitoring and observability
- Task queue integration
- Easy deployment and scaling
"""

from msfw.core.application import MSFWApplication
from msfw.core.config import Config
from msfw.core.database import Database
from msfw.core.plugin import Plugin, PluginManager
from msfw.core.module import Module, ModuleManager
from msfw.decorators import route, middleware, event_handler

__version__ = "0.1.0"
__all__ = [
    "MSFWApplication",
    "Config", 
    "Database",
    "Plugin",
    "PluginManager",
    "Module",
    "ModuleManager",
    "route",
    "middleware", 
    "event_handler",
] 