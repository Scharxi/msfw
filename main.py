"""
MSFW Framework Demo Application
==============================

This demonstrates the key features of the MSFW (Modular Microservices Framework):
- Modular architecture with auto-discovery
- Plugin system with hooks
- Configurable components
- Database integration with SQLAlchemy
- Monitoring and observability
- Easy extensibility
"""

import asyncio
from pathlib import Path

from msfw import MSFWApplication, load_config


async def main():
    """Main application entry point."""
    print("🚀 Starting MSFW Demo Application")
    
    # Load configuration with environment variable support
    config = load_config()
    
    # Override specific settings for demo
    config.app_name = "MSFW Demo"
    config.version = "1.0.0" 
    config.debug = True
    config.database.url = "sqlite+aiosqlite:///./demo.db"
    config.database.echo = True
    
    # Create modules and plugins directories if they don't exist
    Path("modules").mkdir(exist_ok=True)
    Path("plugins").mkdir(exist_ok=True)
    
    # Create and initialize application
    app = MSFWApplication(config)
    await app.initialize()
    
    # Get the FastAPI app for custom routes
    fastapi_app = app.get_app()
    
    # Add a custom demo route
    @fastapi_app.get("/demo")
    async def demo_endpoint():
        """Demo endpoint showing framework capabilities."""
        return {
            "message": "Welcome to MSFW!",
            "framework": "Modular Microservices Framework",
            "features": [
                "Modular architecture",
                "Plugin system", 
                "Auto-discovery",
                "Database integration",
                "Monitoring & observability",
                "Easy configuration",
                "FastAPI integration",
                "SQLAlchemy support"
            ],
            "endpoints": {
                "health": "/health",
                "metrics": "/metrics", 
                "info": "/info",
                "docs": "/docs",
                "demo": "/demo"
            }
        }
    
    print("\n📋 Available endpoints:")
    print("  - Demo: http://localhost:8000/demo")
    print("  - Health: http://localhost:8000/health") 
    print("  - Metrics: http://localhost:8000/metrics")
    print("  - Info: http://localhost:8000/info")
    print("  - API Docs: http://localhost:8000/docs")
    print("\n🎯 Try creating modules and plugins:")
    print("  msfw create-module user --description='User management module'")
    print("  msfw create-plugin auth --description='Authentication plugin'")
    print()
    
    # Run the application
    await app.run(port=8000)


if __name__ == "__main__":
    asyncio.run(main())
