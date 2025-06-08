"""Command line interface for MSFW."""

import os
import sys
import re
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="MSFW - Modular Microservices Framework")
console = Console()


def validate_name(name: str) -> bool:
    """Validate module/plugin name."""
    return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name))


def _to_class_name(name: str) -> str:
    """Convert name to class name format."""
    # Handle CamelCase input by preserving it
    if name[0].isupper() and any(c.isupper() for c in name[1:]):
        return name
    # Handle snake_case or lowercase
    return ''.join(word.capitalize() for word in name.split('_'))


def _to_snake_case(name: str) -> str:
    """Convert name to snake_case."""
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def _validate_name(name: str) -> bool:
    """Validate module/plugin name (alias for validate_name)."""
    return validate_name(name)


def generate_module_template(name: str, description: str) -> str:
    """Generate module template code."""
    class_name = _to_class_name(name)
    desc = description or f"{name} module"
    return f'''"""
{_to_class_name(name)} Module
{description}
"""

from msfw import Module
from fastapi import APIRouter


class {class_name}(Module):
    """Main module class."""
    
    @property
    def name(self) -> str:
        return "{name}"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "{desc}"
    
    async def setup(self) -> None:
        """Setup the module."""
        pass
    
    def register_routes(self, router: APIRouter) -> None:
        """Register module routes."""
        @router.get("/")
        async def get_{name}():
            return {{"message": "Hello from {name} module!"}}
        
        @router.get("/status")
        async def get_{name}_status():
            return {{"status": "active", "module": "{name}"}}
'''


def generate_plugin_template(name: str, description: str) -> str:
    """Generate plugin template code."""
    class_name = _to_class_name(name)
    desc = description or f"{name} plugin"
    return f'''"""
{_to_class_name(name)} Plugin
{description}
"""

from msfw import Plugin, Config


class {class_name}(Plugin):
    """Main plugin class."""
    
    @property
    def name(self) -> str:
        return "{name}"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "{desc}"
    
    async def setup(self, config: Config) -> None:
        """Setup the plugin."""
        # Register hooks
        self.register_hook("app_startup", self.on_startup)
        self.register_hook("app_shutdown", self.on_shutdown)
    
    async def cleanup(self) -> None:
        """Cleanup the plugin."""
        pass
    
    async def on_startup(self, **kwargs):
        """Handle application startup."""
        print(f"{_to_class_name(name)} plugin started")
    
    async def on_shutdown(self, **kwargs):
        """Handle application shutdown."""
        print(f"{_to_class_name(name)} plugin stopped")
'''


def create_project(path: str) -> None:
    """Create a new MSFW project."""
    project_dir = Path(path)
    
    if project_dir.exists():
        raise ValueError("Directory already exists")
    
    # Create project structure
    project_dir.mkdir(parents=True)
    
    # Create subdirectories
    (project_dir / "modules").mkdir()
    (project_dir / "plugins").mkdir()
    (project_dir / "config").mkdir()
    
    # Create main application file
    main_content = f'''"""Main application entry point."""

import asyncio
from msfw import MSFWApplication, load_config

async def main():
    """Main application function."""
    # Load configuration with environment variable support
    config = load_config()
    config.app_name = "{project_dir.name}"
    
    # Create and initialize application
    app = MSFWApplication(config)
    await app.initialize()
    
    # Run the application
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    (project_dir / "main.py").write_text(main_content)
    
    # Create configuration file with microservice support
    config_content = '''# MSFW Configuration with Microservice Support
# 
# Environment Variable Interpolation:
# Use ${VAR_NAME} for required environment variables
# Use ${VAR_NAME:default_value} for optional environment variables with defaults
#
# Examples:
# secret_key = "${SECRET_KEY}"                           # Required env var
# database_url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"  # With default
# debug = "${DEBUG:false}"                              # Boolean with default

# Application settings
app_name = "${APP_NAME:My MSFW Application}"
debug = "${DEBUG:true}"
host = "${HOST:0.0.0.0}"
port = "${PORT:8000}"
environment = "${ENVIRONMENT:development}"

# Global Database settings (defaults for all services)
[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"
echo = "${DATABASE_ECHO:false}"

# Global Security settings
[security]
secret_key = "${SECRET_KEY:your-secret-key-change-in-production}"

# Global Logging settings
[logging]
level = "${LOG_LEVEL:INFO}"
format = "${LOG_FORMAT:text}"

# Global Monitoring settings
[monitoring]
enabled = "${MONITORING_ENABLED:true}"
prometheus_enabled = "${PROMETHEUS_ENABLED:true}"

# Microservice-specific configurations
[services.api]
enabled = true
host = "${API_HOST:0.0.0.0}"
port = "${API_PORT:8000}"
debug = "${API_DEBUG:true}"

[services.api.database]
url = "${API_DATABASE_URL:sqlite+aiosqlite:///./api.db}"

[services.worker]
enabled = "${WORKER_ENABLED:false}"
host = "${WORKER_HOST:0.0.0.0}"
port = "${WORKER_PORT:8001}"

[services.worker.redis]
url = "${WORKER_REDIS_URL:redis://localhost:6379/1}"

# Environment-specific configurations
[environments.development]
debug = true
log_level = "DEBUG"

[environments.development.database]
echo = true

[environments.development.services.api]
debug = true
workers = 1

[environments.development.services.worker]
enabled = false

[environments.production]
debug = false
log_level = "WARNING"

[environments.production.database]
echo = false
pool_size = 20

[environments.production.services.api]
debug = false
workers = 4

[environments.production.services.worker]
enabled = true
workers = 2

[environments.production.services.api.database]
url = "${PROD_API_DATABASE_URL:postgresql://db:5432/api}"

[environments.production.services.worker.redis]
url = "${PROD_WORKER_REDIS_URL:redis://redis:6379/0}"
'''
    
    (project_dir / "config" / "settings.toml").write_text(config_content)
    
    # Create requirements file
    requirements_content = '''msfw>=0.1.0
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
sqlalchemy>=2.0.0
structlog>=23.0.0
'''
    
    (project_dir / "requirements.txt").write_text(requirements_content)
    
    # Create README
    readme_content = f'''# {project_dir.name}

A microservice built with MSFW (Modular Microservices Framework).

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python main.py
   ```

## Project Structure

- `main.py` - Application entry point
- `modules/` - Custom modules
- `plugins/` - Custom plugins
- `config/` - Configuration files
'''
    
    (project_dir / "README.md").write_text(readme_content)


def _create_module_util(project_path: str, name: str, description: str = "") -> None:
    """Create a new module."""
    if not validate_name(name):
        raise ValueError("Invalid module name")
    
    project_dir = Path(project_path)
    modules_dir = project_dir / "modules"
    
    if not modules_dir.exists():
        raise ValueError("No modules directory found")
    
    module_file = modules_dir / f"{name}.py"
    if module_file.exists():
        raise ValueError(f"Module {name} already exists")
    
    template = generate_module_template(name, description)
    module_file.write_text(template)


def _create_plugin_util(project_path: str, name: str, description: str = "") -> None:
    """Create a new plugin."""
    if not validate_name(name):
        raise ValueError("Invalid plugin name")
    
    project_dir = Path(project_path)
    plugins_dir = project_dir / "plugins"
    
    if not plugins_dir.exists():
        raise ValueError("No plugins directory found")
    
    plugin_file = plugins_dir / f"{name}.py"
    if plugin_file.exists():
        raise ValueError(f"Plugin {name} already exists")
    
    template = generate_plugin_template(name, description)
    plugin_file.write_text(template)


def _run_dev_util(project_path: str, host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run development server."""
    project_dir = Path(project_path)
    main_file = project_dir / "main.py"
    
    if not main_file.exists():
        raise ValueError("No main.py found")
    
    cmd = [
        "uvicorn",
        "main:app",
        "--host", host,
        "--port", str(port),
        "--reload"
    ]
    
    subprocess.run(cmd, cwd=project_dir)


def main() -> None:
    """Main CLI entry point."""
    app()


@app.command()
def init(
    name: str = typer.Argument(help="Project name"),
    template: str = typer.Option("basic", help="Project template"),
    directory: Optional[str] = typer.Option(None, help="Project directory"),
):
    """Initialize a new MSFW project."""
    project_dir = Path(directory) if directory else Path(name)
    
    if project_dir.exists():
        console.print(f"[red]Directory {project_dir} already exists![/red]")
        raise typer.Exit(1)
    
    # Create project structure
    project_dir.mkdir()
    
    # Create subdirectories
    (project_dir / "modules").mkdir()
    (project_dir / "plugins").mkdir()
    (project_dir / "config").mkdir()
    
    # Create main application file
    main_content = f'''"""Main application entry point for {name}."""

import asyncio
from msfw import MSFWApplication, load_config

async def main():
    """Main application function."""
    # Load configuration with environment variable support
    config = load_config()
    
    # Create and initialize application
    app = MSFWApplication(config)
    await app.initialize()
    
    # Run the application
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    (project_dir / "main.py").write_text(main_content)
    
    # Create configuration file with microservice support
    config_content = '''# MSFW Configuration with Microservice Support
# 
# Environment Variable Interpolation:
# Use ${VAR_NAME} for required environment variables
# Use ${VAR_NAME:default_value} for optional environment variables with defaults
#
# Examples:
# secret_key = "${SECRET_KEY}"                           # Required env var
# database_url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"  # With default
# debug = "${DEBUG:false}"                              # Boolean with default

# Application settings
app_name = "${APP_NAME:My MSFW Application}"
debug = "${DEBUG:true}"
host = "${HOST:0.0.0.0}"
port = "${PORT:8000}"
environment = "${ENVIRONMENT:development}"

# Global Database settings (defaults for all services)
[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"
echo = "${DATABASE_ECHO:false}"

# Global Security settings
[security]
secret_key = "${SECRET_KEY:your-secret-key-change-in-production}"

# Global Logging settings
[logging]
level = "${LOG_LEVEL:INFO}"
format = "${LOG_FORMAT:text}"

# Global Monitoring settings
[monitoring]
enabled = "${MONITORING_ENABLED:true}"
prometheus_enabled = "${PROMETHEUS_ENABLED:true}"

# Microservice-specific configurations
[services.api]
enabled = true
host = "${API_HOST:0.0.0.0}"
port = "${API_PORT:8000}"
debug = "${API_DEBUG:true}"

[services.api.database]
url = "${API_DATABASE_URL:sqlite+aiosqlite:///./api.db}"

[services.worker]
enabled = "${WORKER_ENABLED:false}"
host = "${WORKER_HOST:0.0.0.0}"
port = "${WORKER_PORT:8001}"

[services.worker.redis]
url = "${WORKER_REDIS_URL:redis://localhost:6379/1}"

# Environment-specific configurations
[environments.development]
debug = true
log_level = "DEBUG"

[environments.development.database]
echo = true

[environments.development.services.api]
debug = true
workers = 1

[environments.development.services.worker]
enabled = false

[environments.production]
debug = false
log_level = "WARNING"

[environments.production.database]
echo = false
pool_size = 20

[environments.production.services.api]
debug = false
workers = 4

[environments.production.services.worker]
enabled = true
workers = 2

[environments.production.services.api.database]
url = "${PROD_API_DATABASE_URL:postgresql://db:5432/api}"

[environments.production.services.worker.redis]
url = "${PROD_WORKER_REDIS_URL:redis://redis:6379/0}"
'''
    
    (project_dir / "config" / "settings.toml").write_text(config_content)
    
    # Create environment file template (optional, for local development)
    env_content = '''# Environment variables for MSFW (optional)
# The configuration will use defaults from settings.toml if these are not set
#
# Uncomment and set the variables you want to override:

# General settings
# APP_NAME=My Custom App
# DEBUG=true
# ENVIRONMENT=development

# Database
# DATABASE_URL=postgresql://localhost/myapp
# SECRET_KEY=your-dev-secret-key

# API Service
# API_HOST=0.0.0.0
# API_PORT=8000
# API_DEBUG=true
# API_DATABASE_URL=postgresql://localhost/api_db

# Worker Service
# WORKER_ENABLED=true
# WORKER_HOST=0.0.0.0
# WORKER_PORT=8001
# WORKER_REDIS_URL=redis://localhost:6379/1

# Production overrides (set in deployment)
# ENVIRONMENT=production
# PROD_API_DATABASE_URL=postgresql://prod-db:5432/api
# PROD_WORKER_REDIS_URL=redis://prod-redis:6379/0
'''
    
    (project_dir / ".env.example").write_text(env_content)
    
    console.print(f"[green]✓ Created MSFW project '{name}' in {project_dir}[/green]")
    console.print("\nNext steps:")
    console.print(f"  cd {project_dir}")
    console.print("  pip install -r requirements.txt")
    console.print("  python main.py")


@app.command()
def create_module(
    name: str = typer.Argument(help="Module name"),
    description: str = typer.Option("", help="Module description"),
):
    """Create a new module."""
    modules_dir = Path("modules")
    if not modules_dir.exists():
        console.print("[red]No modules directory found. Run this in a MSFW project.[/red]")
        raise typer.Exit(1)
    
    module_dir = modules_dir / name
    if module_dir.exists():
        console.print(f"[red]Module {name} already exists![/red]")
        raise typer.Exit(1)
    
    module_dir.mkdir()
    
    # Create module init file
    init_content = f'''"""
{name.title()} Module
{description}
"""

from msfw import Module
from fastapi import APIRouter


class {name.title()}Module(Module):
    """Main module class."""
    
    @property
    def name(self) -> str:
        return "{name}"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "{description or f'{name} module'}"
    
    async def setup(self) -> None:
        """Setup the module."""
        pass
    
    def register_routes(self, router: APIRouter) -> None:
        """Register module routes."""
        @router.get("/")
        async def get_{name}():
            return {{"message": "Hello from {name} module!"}}
        
        @router.post("/")
        async def create_{name}(data: dict):
            return {{"message": "Created in {name} module", "data": data}}
'''
    
    (module_dir / "__init__.py").write_text(init_content)
    
    console.print(f"[green]✓ Created module '{name}' in modules/{name}/[/green]")


@app.command()
def create_plugin(
    name: str = typer.Argument(help="Plugin name"),
    description: str = typer.Option("", help="Plugin description"),
):
    """Create a new plugin."""
    plugins_dir = Path("plugins")
    if not plugins_dir.exists():
        console.print("[red]No plugins directory found. Run this in a MSFW project.[/red]")
        raise typer.Exit(1)
    
    plugin_file = plugins_dir / f"{name}.py"
    if plugin_file.exists():
        console.print(f"[red]Plugin {name} already exists![/red]")
        raise typer.Exit(1)
    
    # Create plugin file
    plugin_content = f'''"""
{name.title()} Plugin
{description}
"""

from msfw import Plugin, Config


class {name.title()}Plugin(Plugin):
    """Main plugin class."""
    
    @property
    def name(self) -> str:
        return "{name}"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "{description or f'{name} plugin'}"
    
    async def setup(self, config: Config) -> None:
        """Setup the plugin."""
        # Register hooks
        self.register_hook("app_startup", self.on_startup)
        self.register_hook("app_shutdown", self.on_shutdown)
    
    async def on_startup(self, **kwargs):
        """Handle application startup."""
        print(f"{name.title()} plugin started")
    
    async def on_shutdown(self, **kwargs):
        """Handle application shutdown."""
        print(f"{name.title()} plugin stopped")
'''
    
    plugin_file.write_text(plugin_content)
    
    console.print(f"[green]✓ Created plugin '{name}' in plugins/{name}.py[/green]")


@app.command()
def run(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
    workers: int = typer.Option(1, help="Number of worker processes"),
):
    """Run the MSFW application."""
    if not Path("main.py").exists():
        console.print("[red]No main.py found. Run this in a MSFW project.[/red]")
        raise typer.Exit(1)
    
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
    )


@app.command()
def info():
    """Show project information."""
    if not Path("main.py").exists():
        console.print("[red]No main.py found. Run this in a MSFW project.[/red]")
        raise typer.Exit(1)
    
    # Project info
    console.print("[bold blue]MSFW Project Information[/bold blue]")
    console.print()
    
    # Modules
    modules_dir = Path("modules")
    if modules_dir.exists():
        modules = [d.name for d in modules_dir.iterdir() if d.is_dir() and not d.name.startswith('_')]
        table = Table(title="Modules")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        
        for module in modules:
            table.add_row(module, "Directory")
        
        console.print(table)
        console.print()
    
    # Plugins
    plugins_dir = Path("plugins")
    if plugins_dir.exists():
        plugins = [f.stem for f in plugins_dir.iterdir() if f.suffix == '.py' and not f.name.startswith('_')]
        table = Table(title="Plugins")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        
        for plugin in plugins:
            table.add_row(plugin, "File")
        
        console.print(table)


@app.command()
def dev():
    """Start development server with auto-reload."""
    if not Path("main.py").exists():
        console.print("[red]No main.py found. Run this in a MSFW project.[/red]")
        raise typer.Exit(1)
    
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1,
    )


@app.command()
def export_openapi(
    format: str = typer.Option("json", help="Export format (json, yaml, both)"),
    output_dir: str = typer.Option("./openapi", help="Output directory"),
    version: Optional[str] = typer.Option(None, help="Specific API version to export"),
    config_file: Optional[str] = typer.Option(None, help="Configuration file path"),
):
    """Export OpenAPI schema in specified format(s)."""
    import asyncio
    from msfw import MSFWApplication, load_config, OpenAPIManager
    
    async def export_schema():
        try:
            # Load configuration
            if config_file:
                config = load_config(config_file)
            else:
                config = load_config()
            
            # Create and initialize application
            app = MSFWApplication(config)
            await app.initialize()
            
            # Get the OpenAPI manager
            openapi_manager = app.openapi_manager
            if not openapi_manager:
                console.print("❌ OpenAPI manager not available", style="red")
                return
            
            # Determine formats to export
            formats = []
            if format.lower() == "both":
                formats = ["json", "yaml"]
            elif format.lower() in ["json", "yaml"]:
                formats = [format.lower()]
            else:
                console.print(f"❌ Unsupported format: {format}. Use 'json', 'yaml', or 'both'", style="red")
                return
            
            # Export schema
            console.print(f"📄 Exporting OpenAPI schema...", style="blue")
            if version:
                console.print(f"   Version: {version}", style="dim")
            console.print(f"   Format(s): {', '.join(formats)}", style="dim")
            console.print(f"   Output: {output_dir}", style="dim")
            
            exported_files = openapi_manager.export_schema(
                app.app,
                formats=formats,
                output_dir=output_dir,
                version=version
            )
            
            console.print("✅ Successfully exported OpenAPI schema:", style="green")
            for format_type, file_path in exported_files.items():
                console.print(f"   {format_type.upper()}: {file_path}", style="dim")
                
        except Exception as e:
            console.print(f"❌ Failed to export OpenAPI schema: {e}", style="red")
            raise typer.Exit(1)
    
    asyncio.run(export_schema())


@app.command()
def list_versions():
    """List all available API versions in the current application."""
    import asyncio
    from msfw import MSFWApplication, load_config
    
    async def show_versions():
        try:
            # Load configuration
            config = load_config()
            
            # Create and initialize application
            app = MSFWApplication(config)
            await app.initialize()
            
            # Get version manager
            from msfw.core.versioning import version_manager
            
            available_versions = version_manager.get_available_versions()
            if not available_versions:
                console.print("ℹ️ No API versions configured", style="yellow")
                return
            
            # Create table
            table = Table(title="API Versions")
            table.add_column("Version", style="cyan", no_wrap=True)
            table.add_column("Status", style="green")
            table.add_column("Deprecation Message", style="yellow")
            table.add_column("Sunset Date", style="red")
            
            for version_str in available_versions:
                try:
                    from msfw.core.versioning import VersionInfo
                    version_info = VersionInfo.from_string(version_str)
                    
                    status = "Deprecated" if version_manager.is_version_deprecated(version_info) else "Active"
                    
                    deprecation_info = version_manager.get_deprecation_info(version_info)
                    deprecation_msg = deprecation_info.get("message", "-") if deprecation_info else "-"
                    sunset_date = deprecation_info.get("sunset_date", "-") if deprecation_info else "-"
                    
                    table.add_row(
                        version_str,
                        status,
                        deprecation_msg,
                        sunset_date
                    )
                except Exception as e:
                    # Fallback for any parsing issues
                    table.add_row(version_str, "Active", "-", "-")
            
            console.print(table)
            
            # Show endpoints
            if config.openapi.enabled:
                console.print("\n📄 Documentation endpoints:")
                console.print(f"   Swagger UI: http://{config.host}:{config.port}{config.openapi.docs_url}")
                console.print(f"   ReDoc: http://{config.host}:{config.port}{config.openapi.redoc_url}")
                console.print(f"   OpenAPI Schema: http://{config.host}:{config.port}{config.openapi.openapi_url}")
                console.print(f"   Version List: http://{config.host}:{config.port}/api/versions")
                
        except Exception as e:
            console.print(f"❌ Failed to list versions: {e}", style="red")
            raise typer.Exit(1)
    
    asyncio.run(show_versions())


@app.command()
def update(
    framework: bool = typer.Option(False, help="Update MSFW framework version"),
    dependencies: bool = typer.Option(False, help="Update project dependencies"),
    all: bool = typer.Option(False, help="Update both framework and dependencies"),
):
    """Update MSFW framework and/or project dependencies."""
    if not (framework or dependencies or all):
        console.print("[yellow]Please specify what to update: --framework, --dependencies, or --all[/yellow]")
        raise typer.Exit(1)
    
    if framework or all:
        console.print("[blue]Updating MSFW framework...[/blue]")
        try:
            subprocess.run(
                ["pip", "install", "--upgrade", "msfw"],
                check=True
            )
            console.print("[green]✓ MSFW framework updated successfully[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to update MSFW framework: {e}[/red]")
            raise typer.Exit(1)
    
    if dependencies or all:
        console.print("[blue]Updating project dependencies...[/blue]")
        try:
            # Update pip first
            subprocess.run(
                ["pip", "install", "--upgrade", "pip"],
                check=True
            )
            
            # Update all dependencies
            subprocess.run(
                ["pip", "install", "--upgrade", "-r", "requirements.txt"],
                check=True
            )
            console.print("[green]✓ Project dependencies updated successfully[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to update dependencies: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def migrate(
    message: str = typer.Option(None, help="Migration message"),
    revision: str = typer.Option(None, help="Specific revision to migrate to"),
    downgrade: bool = typer.Option(False, help="Downgrade instead of upgrade"),
):
    """Manage database migrations."""
    try:
        import alembic
        from alembic.config import Config as AlembicConfig
        from alembic import command
    except ImportError:
        console.print("[red]Alembic is not installed. Please install it first:[/red]")
        console.print("pip install alembic")
        raise typer.Exit(1)
    
    # Validate arguments
    if not revision and not message:
        console.print("[red]Either --message (for new migration) or --revision (to run migration) is required[/red]")
        raise typer.Exit(1)
    
    # Initialize Alembic config
    alembic_cfg = AlembicConfig("alembic.ini" if Path("alembic.ini").exists() else None)
    
    # Check if alembic is initialized
    if not Path("alembic.ini").exists():
        console.print("[blue]Initializing Alembic...[/blue]")
        try:
            # Set up config for new installation
            alembic_cfg.set_main_option("script_location", "migrations")
            alembic_cfg.set_main_option("sqlalchemy.url", "sqlite+aiosqlite:///./app.db")
            
            # Create alembic.ini file
            alembic_ini_content = '''# A generic, single database configuration.

[alembic]
# path to migration scripts
script_location = migrations

# template used to generate migration files
# file_template = %%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the python-dateutil library that can be
# installed by adding `alembic[tz]` to the pip requirements
# string value is passed to dateutil.tz.gettz()
# leave blank for localtime
# timezone =

# max length of characters to apply to the
# "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version path separator; As mentioned above, this is the character used to split
# version_locations. The default within new alembic.ini files is "os", which uses
# os.pathsep. If this key is omitted entirely, it falls back to the legacy
# behavior of splitting on spaces and/or commas.
# Valid values for version_path_separator are:
#
# version_path_separator = :
# version_path_separator = ;
# version_path_separator = space
version_path_separator = os

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

sqlalchemy.url = sqlite+aiosqlite:///./app.db

[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79 REVISION_SCRIPT_FILENAME

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
'''
            Path("alembic.ini").write_text(alembic_ini_content)
            
            # Create migrations directory
            Path("migrations").mkdir(exist_ok=True)
            Path("migrations/versions").mkdir(exist_ok=True)
            
            # Create env.py
            env_py = '''"""Alembic environment configuration."""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from msfw.core.database import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
            (Path("migrations") / "env.py").write_text(env_py)
            
            # Create script.py.mako
            script_mako = '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
'''
            (Path("migrations") / "script.py.mako").write_text(script_mako)
            
            # Reload config to pick up alembic.ini
            alembic_cfg = AlembicConfig("alembic.ini")
            
            console.print("[green]✓ Alembic initialized successfully[/green]")
        except Exception as e:
            console.print(f"[red]Failed to initialize Alembic: {e}[/red]")
            raise typer.Exit(1)
    
    # Create new migration
    if not revision:
        console.print(f"[blue]Creating new migration: {message}[/blue]")
        try:
            command.revision(alembic_cfg, message=message, autogenerate=True)
            console.print("[green]✓ Migration created successfully[/green]")
        except Exception as e:
            console.print(f"[red]Failed to create migration: {e}[/red]")
            raise typer.Exit(1)
    else:
        # Run migration
        console.print(f"[blue]Running migration to revision: {revision}[/blue]")
        try:
            if downgrade:
                command.downgrade(alembic_cfg, revision)
                console.print("[green]✓ Migration downgraded successfully[/green]")
            else:
                command.upgrade(alembic_cfg, revision)
                console.print("[green]✓ Migration upgraded successfully[/green]")
        except Exception as e:
            console.print(f"[red]Failed to run migration: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def test(
    coverage: bool = typer.Option(False, help="Run tests with coverage reporting"),
    unit: bool = typer.Option(False, help="Run only unit tests"),
    integration: bool = typer.Option(False, help="Run only integration tests"),
    e2e: bool = typer.Option(False, help="Run only end-to-end tests"),
    verbose: bool = typer.Option(False, help="Show verbose test output"),
):
    """Run tests with optional coverage reporting."""
    try:
        import pytest
    except ImportError:
        console.print("[red]pytest is not installed. Please install it first:[/red]")
        console.print("pip install pytest pytest-asyncio pytest-cov")
        raise typer.Exit(1)
    
    # Build pytest arguments
    args = []
    
    # Add coverage if requested
    if coverage:
        try:
            import pytest_cov
        except ImportError:
            console.print("[red]pytest-cov is not installed. Please install it first:[/red]")
            console.print("pip install pytest-cov")
            raise typer.Exit(1)
        args.extend(["--cov=msfw", "--cov-report=term-missing"])
    
    # Add test type filters
    if unit:
        args.append("-m unit")
    elif integration:
        args.append("-m integration")
    elif e2e:
        args.append("-m e2e")
    
    # Add verbosity
    if verbose:
        args.append("-v")
    
    # Run tests
    console.print("[blue]Running tests...[/blue]")
    try:
        result = pytest.main(args)
        if result == 0:
            console.print("[green]✓ All tests passed successfully[/green]")
        else:
            console.print(f"[red]Tests failed with exit code {result}[/red]")
            raise typer.Exit(result)
    except Exception as e:
        console.print(f"[red]Failed to run tests: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app() 