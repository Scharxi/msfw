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


# Development Tools Commands

@app.command()
def generate(
    type: str = typer.Argument(help="Type to generate: api, model, test, docs"),
    name: str = typer.Argument(help="Name of the component"),
    description: str = typer.Option("", help="Description of the component"),
    output_dir: Optional[str] = typer.Option(None, help="Output directory"),
):
    """Generate scaffolding for API endpoints, database models, tests, or documentation."""
    
    # Validate component name
    if not _validate_name(name):
        console.print("[red]Invalid name. Use only letters, numbers, and underscores, starting with a letter.[/red]")
        raise typer.Exit(1)
    
    # Determine output directory
    if not output_dir:
        if type == "api":
            output_dir = "endpoints"
        elif type == "model":
            output_dir = "models"
        elif type == "test":
            output_dir = "tests"
        elif type == "docs":
            output_dir = "docs"
        else:
            console.print(f"[red]Unknown type: {type}. Valid types: api, model, test, docs[/red]")
            raise typer.Exit(1)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if type == "api":
        _generate_api_endpoint(name, description, output_path)
    elif type == "model":
        _generate_database_model(name, description, output_path)
    elif type == "test":
        _generate_test_template(name, description, output_path)
    elif type == "docs":
        _generate_documentation_template(name, description, output_path)
    else:
        console.print(f"[red]Unknown type: {type}[/red]")
        raise typer.Exit(1)


def _generate_api_endpoint(name: str, description: str, output_path: Path) -> None:
    """Generate API endpoint scaffolding."""
    class_name = _to_class_name(name)
    snake_name = _to_snake_case(name)
    desc = description or f"{name} API endpoint"
    
    endpoint_content = f'''"""
{class_name} API Endpoint
{desc}
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from msfw.core.database import get_db
from msfw.decorators import versioned_route
from models.{snake_name} import {class_name}  # Adjust import path as needed


router = APIRouter(prefix="/{snake_name}", tags=["{snake_name}"])


# Pydantic Models
class {class_name}Base(BaseModel):
    """Base {class_name} model."""
    name: str = Field(..., description="Name of the {snake_name}")
    description: Optional[str] = Field(None, description="Description of the {snake_name}")


class {class_name}Create({class_name}Base):
    """Create {class_name} model."""
    pass


class {class_name}Update(BaseModel):
    """Update {class_name} model."""
    name: Optional[str] = Field(None, description="Name of the {snake_name}")
    description: Optional[str] = Field(None, description="Description of the {snake_name}")


class {class_name}Response({class_name}Base):
    """Response {class_name} model."""
    id: int = Field(..., description="Unique identifier")
    
    class Config:
        from_attributes = True


# API Routes
@router.get("/", response_model=List[{class_name}Response])
@versioned_route("1.0")
async def get_{snake_name}s(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all {snake_name}s."""
    items = db.query({class_name}).offset(skip).limit(limit).all()
    return items


@router.get("/{{item_id}}", response_model={class_name}Response)
@versioned_route("1.0")
async def get_{snake_name}(
    item_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific {snake_name} by ID."""
    item = db.query({class_name}).filter({class_name}.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{class_name} not found"
        )
    return item


@router.post("/", response_model={class_name}Response, status_code=status.HTTP_201_CREATED)
@versioned_route("1.0")
async def create_{snake_name}(
    item: {class_name}Create,
    db: Session = Depends(get_db)
):
    """Create a new {snake_name}."""
    db_item = {class_name}(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{{item_id}}", response_model={class_name}Response)
@versioned_route("1.0")
async def update_{snake_name}(
    item_id: int,
    item: {class_name}Update,
    db: Session = Depends(get_db)
):
    """Update a {snake_name}."""
    db_item = db.query({class_name}).filter({class_name}.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{class_name} not found"
        )
    
    update_data = item.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_item, field, value)
    
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{{item_id}}", status_code=status.HTTP_204_NO_CONTENT)
@versioned_route("1.0")
async def delete_{snake_name}(
    item_id: int,
    db: Session = Depends(get_db)
):
    """Delete a {snake_name}."""
    db_item = db.query({class_name}).filter({class_name}.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{class_name} not found"
        )
    
    db.delete(db_item)
    db.commit()
'''
    
    file_path = output_path / f"{snake_name}.py"
    file_path.write_text(endpoint_content)
    console.print(f"[green]✓ API endpoint generated: {file_path}[/green]")


def _generate_database_model(name: str, description: str, output_path: Path) -> None:
    """Generate database model scaffolding."""
    class_name = _to_class_name(name)
    snake_name = _to_snake_case(name)
    desc = description or f"{name} database model"
    
    model_content = f'''"""
{class_name} Database Model
{desc}
"""

from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func

from msfw.core.database import Base


class {class_name}(Base):
    """
    {class_name} model.
    
    {desc}
    """
    __tablename__ = "{snake_name}s"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, doc="Unique identifier")
    
    # Core fields
    name = Column(String(255), nullable=False, index=True, doc="Name of the {snake_name}")
    description = Column(Text, nullable=True, doc="Description of the {snake_name}")
    
    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False, doc="Whether the {snake_name} is active")
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the {snake_name} was created"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="When the {snake_name} was last updated"
    )
    
    def __repr__(self) -> str:
        return f"<{class_name}(id={{self.id}}, name='{{self.name}}')>"
    
    def __str__(self) -> str:
        return self.name or f"{class_name} {{self.id}}"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {{
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }}
'''
    
    file_path = output_path / f"{snake_name}.py"
    file_path.write_text(model_content)
    console.print(f"[green]✓ Database model generated: {file_path}[/green]")


def _generate_test_template(name: str, description: str, output_path: Path) -> None:
    """Generate test template scaffolding."""
    class_name = _to_class_name(name)
    snake_name = _to_snake_case(name)
    desc = description or f"Tests for {name}"
    
    test_content = f'''"""
Test {class_name}
{desc}
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from httpx import AsyncClient
from fastapi import status

from msfw.core.application import MSFWApplication


class Test{class_name}:
    """Test suite for {class_name}."""
    
    @pytest.fixture
    async def app(self):
        """Create test application."""
        from msfw import load_config
        config = load_config()
        config.testing = True
        config.database.url = "sqlite+aiosqlite:///:memory:"
        
        app = MSFWApplication(config)
        await app.initialize()
        return app.app
    
    @pytest.fixture
    async def client(self, app):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_create_{snake_name}(self, client: AsyncClient):
        """Test creating a {snake_name}."""
        # Arrange
        {snake_name}_data = {{
            "name": "Test {class_name}",
            "description": "Test description"
        }}
        
        # Act
        response = await client.post("/{snake_name}/", json={snake_name}_data)
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == {snake_name}_data["name"]
        assert data["description"] == {snake_name}_data["description"]
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_get_{snake_name}s(self, client: AsyncClient):
        """Test getting all {snake_name}s."""
        # Act
        response = await client.get("/{snake_name}/")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_{snake_name}_by_id(self, client: AsyncClient):
        """Test getting a specific {snake_name}."""
        # Arrange - Create a {snake_name} first
        {snake_name}_data = {{
            "name": "Test {class_name}",
            "description": "Test description"
        }}
        create_response = await client.post("/{snake_name}/", json={snake_name}_data)
        created_item = create_response.json()
        
        # Act
        response = await client.get(f"/{snake_name}/{{created_item['id']}}")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == created_item["id"]
        assert data["name"] == {snake_name}_data["name"]
    
    @pytest.mark.asyncio
    async def test_get_{snake_name}_not_found(self, client: AsyncClient):
        """Test getting a non-existent {snake_name}."""
        # Act
        response = await client.get("/{snake_name}/999999")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_update_{snake_name}(self, client: AsyncClient):
        """Test updating a {snake_name}."""
        # Arrange - Create a {snake_name} first
        {snake_name}_data = {{
            "name": "Test {class_name}",
            "description": "Test description"
        }}
        create_response = await client.post("/{snake_name}/", json={snake_name}_data)
        created_item = create_response.json()
        
        update_data = {{
            "name": "Updated {class_name}",
            "description": "Updated description"
        }}
        
        # Act
        response = await client.put(f"/{snake_name}/{{created_item['id']}}", json=update_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    @pytest.mark.asyncio
    async def test_delete_{snake_name}(self, client: AsyncClient):
        """Test deleting a {snake_name}."""
        # Arrange - Create a {snake_name} first
        {snake_name}_data = {{
            "name": "Test {class_name}",
            "description": "Test description"
        }}
        create_response = await client.post("/{snake_name}/", json={snake_name}_data)
        created_item = create_response.json()
        
        # Act
        response = await client.delete(f"/{snake_name}/{{created_item['id']}}")
        
        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify it's actually deleted
        get_response = await client.get(f"/{snake_name}/{{created_item['id']}}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND


class Test{class_name}Unit:
    """Unit tests for {class_name} (without database)."""
    
    def test_{snake_name}_validation(self):
        """Test {snake_name} model validation."""
        # Add unit tests for model validation here
        pass
    
    @patch('your_module.external_service')
    def test_{snake_name}_with_mock(self, mock_service):
        """Test {snake_name} with mocked dependencies."""
        # Arrange
        mock_service.return_value = "mocked_result"
        
        # Act & Assert
        # Add your test logic here
        pass


class Test{class_name}Integration:
    """Integration tests for {class_name}."""
    
    @pytest.mark.integration
    async def test_{snake_name}_full_workflow(self):
        """Test complete {snake_name} workflow."""
        # Add integration tests here
        pass


class Test{class_name}Performance:
    """Performance tests for {class_name}."""
    
    @pytest.mark.performance
    async def test_{snake_name}_performance(self):
        """Test {snake_name} performance under load."""
        # Add performance tests here
        pass
'''
    
    file_path = output_path / f"test_{snake_name}.py"
    file_path.write_text(test_content)
    console.print(f"[green]✓ Test template generated: {file_path}[/green]")


def _generate_documentation_template(name: str, description: str, output_path: Path) -> None:
    """Generate documentation template."""
    class_name = _to_class_name(name)
    snake_name = _to_snake_case(name)
    desc = description or f"Documentation for {name}"
    
    doc_content = f'''# {class_name}

{desc}

## Overview

The {class_name} component provides functionality for [describe the main purpose here].

## Features

- Feature 1: [Description]
- Feature 2: [Description]
- Feature 3: [Description]

## Installation

```bash
# If this is a separate package
pip install msfw-{snake_name}

# Or if it's part of the main framework
# Already included in msfw
```

## Quick Start

```python
from msfw import MSFWApplication
from your_module.{snake_name} import {class_name}

# Basic usage example
{snake_name} = {class_name}()
```

## API Reference

### {class_name} Class

#### Constructor

```python
{class_name}(
    name: str,
    description: Optional[str] = None,
    **kwargs
)
```

**Parameters:**
- `name` (str): The name of the {snake_name}
- `description` (Optional[str]): Optional description
- `**kwargs`: Additional configuration options

#### Methods

##### `create()`

Creates a new {snake_name}.

```python
await {snake_name}.create()
```

**Returns:** {class_name} instance

##### `get(id: int)`

Retrieves a {snake_name} by ID.

```python
result = await {snake_name}.get(id=1)
```

**Parameters:**
- `id` (int): The {snake_name} ID

**Returns:** {class_name} instance or None

##### `update(data: dict)`

Updates the {snake_name} with new data.

```python
await {snake_name}.update({{"name": "New Name"}})
```

**Parameters:**
- `data` (dict): Fields to update

##### `delete()`

Deletes the {snake_name}.

```python
await {snake_name}.delete()
```

## REST API Endpoints

### GET /{snake_name}/

Get all {snake_name}s.

**Response:**
```json
[
  {{
    "id": 1,
    "name": "Example {class_name}",
    "description": "Example description",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }}
]
```

### GET /{snake_name}/{{id}}

Get a specific {snake_name} by ID.

**Parameters:**
- `id` (int): The {snake_name} ID

**Response:**
```json
{{
  "id": 1,
  "name": "Example {class_name}",
  "description": "Example description",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}}
```

### POST /{snake_name}/

Create a new {snake_name}.

**Request Body:**
```json
{{
  "name": "New {class_name}",
  "description": "Optional description"
}}
```

**Response:**
```json
{{
  "id": 2,
  "name": "New {class_name}",
  "description": "Optional description",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}}
```

### PUT /{snake_name}/{{id}}

Update an existing {snake_name}.

**Parameters:**
- `id` (int): The {snake_name} ID

**Request Body:**
```json
{{
  "name": "Updated {class_name}",
  "description": "Updated description"
}}
```

### DELETE /{snake_name}/{{id}}

Delete a {snake_name}.

**Parameters:**
- `id` (int): The {snake_name} ID

**Response:** 204 No Content

## Configuration

The {class_name} can be configured using the following options:

```toml
# config.toml
[{snake_name}]
enabled = true
option1 = "value1"
option2 = "value2"
```

### Configuration Options

- `enabled` (bool): Whether the {snake_name} is enabled (default: true)
- `option1` (str): Description of option1
- `option2` (str): Description of option2

## Examples

### Basic Usage

```python
from msfw import MSFWApplication, load_config
from your_module.{snake_name} import {class_name}

async def main():
    config = load_config()
    app = MSFWApplication(config)
    
    # Create a new {snake_name}
    {snake_name} = {class_name}(name="My {class_name}")
    await {snake_name}.create()
    
    print(f"Created {snake_name}: {{{snake_name}.id}}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Advanced Usage

```python
# Advanced example with custom configuration
{snake_name} = {class_name}(
    name="Advanced {class_name}",
    description="This is an advanced example",
    custom_option="custom_value"
)

# Use with context manager
async with {snake_name}:
    result = await {snake_name}.perform_operation()
    print(f"Result: {{result}}")
```

## Testing

To run tests for {class_name}:

```bash
# Run all tests
msfw test

# Run only {snake_name} tests
pytest tests/test_{snake_name}.py

# Run with coverage
pytest tests/test_{snake_name}.py --cov={snake_name}
```

## Error Handling

The {class_name} component raises the following exceptions:

- `{class_name}NotFoundError`: When a {snake_name} is not found
- `{class_name}ValidationError`: When validation fails
- `{class_name}OperationError`: When an operation fails

```python
from your_module.{snake_name} import {class_name}, {class_name}NotFoundError

try:
    {snake_name} = await {class_name}.get(id=999)
except {class_name}NotFoundError:
    print("{class_name} not found")
```

## Best Practices

1. **Naming**: Use clear, descriptive names for {snake_name}s
2. **Validation**: Always validate input data
3. **Error Handling**: Handle exceptions appropriately
4. **Testing**: Write comprehensive tests
5. **Documentation**: Keep documentation up to date

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a pull request

## Changelog

### Version 1.0.0
- Initial release
- Basic CRUD operations
- REST API endpoints

## License

This project is licensed under the MIT License - see the LICENSE file for details.
'''
    
    file_path = output_path / f"{snake_name}.md"
    file_path.write_text(doc_content)
    console.print(f"[green]✓ Documentation template generated: {file_path}[/green]")


@app.command()
def lint(
    fix: bool = typer.Option(False, help="Automatically fix issues where possible"),
    strict: bool = typer.Option(False, help="Use strict linting rules"),
    format_check: bool = typer.Option(True, help="Check code formatting"),
    type_check: bool = typer.Option(True, help="Run type checking"),
    security_check: bool = typer.Option(False, help="Run security checks"),
    complexity_check: bool = typer.Option(False, help="Check code complexity"),
    exclude: Optional[str] = typer.Option(None, help="Exclude patterns (comma-separated)"),
):
    """Run code quality checks with ruff, black, mypy, and optional security tools."""
    
    console.print("[blue]Running code quality checks...[/blue]")
    
    # Build exclude patterns
    exclude_patterns = []
    if exclude:
        exclude_patterns = [pattern.strip() for pattern in exclude.split(",")]
    
    default_excludes = ["__pycache__", ".git", ".venv", "build", "dist", "*.egg-info"]
    exclude_patterns.extend(default_excludes)
    
    issues_found = False
    
    # 1. Ruff linting
    console.print("\n[cyan]1. Running Ruff linting...[/cyan]")
    try:
        ruff_cmd = ["ruff", "check", "."]
        
        if fix:
            ruff_cmd.append("--fix")
        
        if strict:
            ruff_cmd.extend(["--select", "ALL"])
        
        if exclude_patterns:
            exclude_str = ",".join(p for p in exclude_patterns if p.strip())
            if exclude_str:
                ruff_cmd.extend(["--exclude", exclude_str])
        
        result = subprocess.run(ruff_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(f"[yellow]{result.stderr}[/yellow]")
        
        if result.returncode != 0:
            issues_found = True
            console.print("[red]✗ Ruff found linting issues[/red]")
        else:
            console.print("[green]✓ Ruff linting passed[/green]")
            
    except FileNotFoundError:
        console.print("[yellow]⚠ Ruff not found. Install with: pip install ruff[/yellow]")
    
    # 2. Black formatting check
    if format_check:
        console.print("\n[cyan]2. Running Black formatting check...[/cyan]")
        try:
            black_cmd = ["black", "--check", "--diff", "."]
            
            if exclude_patterns:
                valid_patterns = [p for p in exclude_patterns if p.strip()]
                if valid_patterns:
                    black_cmd.extend(["--exclude", "|".join(valid_patterns)])
            
            result = subprocess.run(black_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.stdout:
                console.print(result.stdout)
            if result.stderr:
                console.print(f"[yellow]{result.stderr}[/yellow]")
            
            if result.returncode != 0:
                issues_found = True
                console.print("[red]✗ Black found formatting issues[/red]")
                if fix:
                    console.print("[blue]Running Black formatter...[/blue]")
                    fix_cmd = ["black", "."]
                    if exclude_patterns:
                        for pattern in exclude_patterns:
                            fix_cmd.extend(["--exclude", pattern])
                    subprocess.run(fix_cmd, encoding='utf-8', errors='replace')
                    console.print("[green]✓ Code formatted with Black[/green]")
            else:
                console.print("[green]✓ Black formatting check passed[/green]")
                
        except FileNotFoundError:
            console.print("[yellow]⚠ Black not found. Install with: pip install black[/yellow]")
    
    # 3. MyPy type checking
    if type_check:
        console.print("\n[cyan]3. Running MyPy type checking...[/cyan]")
        try:
            mypy_cmd = ["mypy", "."]
            
            if exclude_patterns:
                valid_patterns = [p for p in exclude_patterns if p.strip()]
                if valid_patterns:
                    exclude_regex = "|".join(valid_patterns)
                    mypy_cmd.extend(["--exclude", exclude_regex])
            
            result = subprocess.run(mypy_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.stdout:
                console.print(result.stdout)
            if result.stderr:
                console.print(f"[yellow]{result.stderr}[/yellow]")
            
            if result.returncode != 0:
                issues_found = True
                console.print("[red]✗ MyPy found type issues[/red]")
            else:
                console.print("[green]✓ MyPy type checking passed[/green]")
                
        except FileNotFoundError:
            console.print("[yellow]⚠ MyPy not found. Install with: pip install mypy[/yellow]")
    
    # 4. Security check with bandit
    if security_check:
        console.print("\n[cyan]4. Running Bandit security check...[/cyan]")
        try:
            bandit_cmd = ["bandit", "-r", "."]
            
            if exclude_patterns:
                exclude_dirs = [p for p in exclude_patterns if not p.startswith("*.") and p.strip()]
                if exclude_dirs:
                    bandit_cmd.extend(["--exclude", ",".join(exclude_dirs)])
            
            result = subprocess.run(bandit_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.stdout:
                console.print(result.stdout)
            if result.stderr:
                console.print(f"[yellow]{result.stderr}[/yellow]")
            
            if result.returncode != 0:
                issues_found = True
                console.print("[red]✗ Bandit found security issues[/red]")
            else:
                console.print("[green]✓ Bandit security check passed[/green]")
                
        except FileNotFoundError:
            console.print("[yellow]⚠ Bandit not found. Install with: pip install bandit[/yellow]")
    
    # 5. Complexity check with radon
    if complexity_check:
        console.print("\n[cyan]5. Running Radon complexity check...[/cyan]")
        try:
            radon_cmd = ["radon", "cc", ".", "-s"]
            
            result = subprocess.run(radon_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.stdout:
                console.print(result.stdout)
            if result.stderr:
                console.print(f"[yellow]{result.stderr}[/yellow]")
            
            # Radon doesn't fail on high complexity, just reports it
            console.print("[green]✓ Radon complexity check completed[/green]")
                
        except FileNotFoundError:
            console.print("[yellow]⚠ Radon not found. Install with: pip install radon[/yellow]")
    
    # Summary
    console.print("\n[cyan]Summary:[/cyan]")
    if issues_found:
        console.print("[red]✗ Code quality issues found. Please fix them before committing.[/red]")
        if not fix:
            console.print("[yellow]Tip: Use --fix to automatically fix some issues[/yellow]")
        raise typer.Exit(1)
    else:
        console.print("[green]✓ All code quality checks passed![/green]")


@app.command()
def format(
    check: bool = typer.Option(False, help="Only check formatting, don't make changes"),
    exclude: Optional[str] = typer.Option(None, help="Exclude patterns (comma-separated)"),
    line_length: int = typer.Option(88, help="Maximum line length"),
):
    """Format code using black."""
    try:
        import subprocess
        import shutil
        
        if not shutil.which("black"):
            console.print("❌ Black is not installed. Install it with: pip install black", style="red")
            raise typer.Exit(1)
        
        # Base command
        cmd = ["black"]
        
        if check:
            cmd.append("--check")
        
        if line_length != 88:
            cmd.extend(["--line-length", str(line_length)])
        
        # Add exclude patterns
        exclude_patterns = []
        if exclude:
            exclude_patterns.extend(exclude.split(","))
        
        # Always exclude common directories
        exclude_patterns.extend([
            "__pycache__",
            ".venv",
            "venv",
            ".git",
            "build",
            "dist",
            "*.egg-info"
        ])
        
        if exclude_patterns:
            cmd.extend(["--exclude", "|".join(exclude_patterns)])
        
        # Add current directory
        cmd.append(".")
        
        console.print(f"🎨 Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(result.stderr, style="red")
        
        if result.returncode == 0:
            if check:
                console.print("✅ Code is properly formatted", style="green")
            else:
                console.print("✅ Code formatting completed", style="green")
        else:
            if check:
                console.print("❌ Code formatting issues found", style="red")
            else:
                console.print("❌ Code formatting failed", style="red")
            raise typer.Exit(result.returncode)
            
    except Exception as e:
        console.print(f"❌ Formatting failed: {e}", style="red")
        raise typer.Exit(1)


# Environment Management Commands
env_app = typer.Typer(help="Environment management commands")
app.add_typer(env_app, name="env")


@env_app.command("list")
def list_environments(
    config_file: Optional[str] = typer.Option(None, help="Configuration file path"),
    verbose: bool = typer.Option(False, help="Show detailed environment information"),
):
    """List all available environments."""
    try:
        from msfw.core.config import load_config
        
        # Load configuration
        if config_file:
            config = load_config(config_file)
        else:
            config = load_config()
        
        console.print("🌍 Available Environments", style="bold blue")
        console.print("=" * 50)
        
        if not config.environments:
            console.print("No environments configured", style="yellow")
            console.print("\n💡 Define environments in your configuration file:")
            console.print("""
[environments.development]
debug = true
log_level = "DEBUG"

[environments.production]
debug = false
log_level = "WARNING"
            """)
            return
        
        # Create table for environments
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Environment", style="cyan")
        table.add_column("Current", style="green")
        table.add_column("Debug", style="yellow")
        table.add_column("Log Level", style="blue")
        
        if verbose:
            table.add_column("Services", style="purple")
        
        for env_name, env_config in config.environments.items():
            current_marker = "✓" if env_name == config.environment else ""
            services_info = ""
            
            if verbose and env_config.services:
                services_info = ", ".join([
                    f"{name}({cfg.port})" 
                    for name, cfg in env_config.services.items() 
                    if cfg.enabled
                ])
            
            row = [
                env_name,
                current_marker,
                str(env_config.debug),
                env_config.log_level,
            ]
            
            if verbose:
                row.append(services_info or "None")
            
            table.add_row(*row)
        
        console.print(table)
        
        console.print(f"\n📍 Current environment: [bold green]{config.environment}[/bold green]")
        
        if verbose:
            current_env = config.get_current_environment_config()
            if current_env:
                console.print(f"\n🔍 Current Environment Details:")
                console.print(f"  Debug: {current_env.debug}")
                console.print(f"  Log Level: {current_env.log_level}")
                
                if current_env.services:
                    console.print("  Services:")
                    for service_name, service_config in current_env.services.items():
                        status = "enabled" if service_config.enabled else "disabled"
                        console.print(f"    - {service_name}: {status} (port: {service_config.port})")
        
    except Exception as e:
        console.print(f"❌ Failed to list environments: {e}", style="red")
        raise typer.Exit(1)


@env_app.command("switch")
def switch_environment(
    environment: str = typer.Argument(help="Environment name to switch to"),
    config_file: Optional[str] = typer.Option(None, help="Configuration file path"),
    validate: bool = typer.Option(True, help="Validate environment configuration"),
):
    """Switch to a different environment."""
    try:
        from msfw.core.config import load_config
        import os
        
        # Load configuration to validate environment exists
        if config_file:
            config = load_config(config_file)
        else:
            config = load_config()
        
        # Check if environment exists
        if environment not in config.environments:
            console.print(f"❌ Environment '{environment}' not found", style="red")
            console.print("\n🌍 Available environments:")
            for env_name in config.environments.keys():
                console.print(f"  - {env_name}")
            raise typer.Exit(1)
        
        # Validate environment if requested
        if validate:
            env_config = config.environments[environment]
            validation_errors = []
            
            # Check for missing required environment variables
            for service_name, service_config in env_config.services.items():
                if service_config.enabled:
                    # Check if port is reasonable
                    if not (1 <= service_config.port <= 65535):
                        validation_errors.append(f"Service '{service_name}' has invalid port: {service_config.port}")
            
            if validation_errors:
                console.print(f"❌ Environment '{environment}' validation failed:", style="red")
                for error in validation_errors:
                    console.print(f"  - {error}")
                
                if not typer.confirm("Continue anyway?"):
                    raise typer.Exit(1)
        
        # Set environment variable
        os.environ["ENVIRONMENT"] = environment
        
        # Update .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            lines = env_file.read_text().splitlines()
            updated_lines = []
            env_found = False
            
            for line in lines:
                if line.startswith("ENVIRONMENT="):
                    updated_lines.append(f"ENVIRONMENT={environment}")
                    env_found = True
                else:
                    updated_lines.append(line)
            
            if not env_found:
                updated_lines.append(f"ENVIRONMENT={environment}")
            
            env_file.write_text("\n".join(updated_lines) + "\n")
            console.print(f"📝 Updated .env file", style="blue")
        else:
            # Create .env file
            env_file.write_text(f"ENVIRONMENT={environment}\n")
            console.print(f"📝 Created .env file", style="blue")
        
        console.print(f"✅ Switched to environment: [bold green]{environment}[/bold green]")
        
        # Show environment details
        env_config = config.environments[environment]
        console.print(f"\n🔍 Environment Details:")
        console.print(f"  Debug: {env_config.debug}")
        console.print(f"  Log Level: {env_config.log_level}")
        
        if env_config.services:
            enabled_services = [name for name, cfg in env_config.services.items() if cfg.enabled]
            if enabled_services:
                console.print(f"  Enabled Services: {', '.join(enabled_services)}")
        
    except Exception as e:
        console.print(f"❌ Failed to switch environment: {e}", style="red")
        raise typer.Exit(1)


@env_app.command("validate")
def validate_environment(
    environment: Optional[str] = typer.Option(None, help="Environment to validate (current if not specified)"),
    config_file: Optional[str] = typer.Option(None, help="Configuration file path"),
    strict: bool = typer.Option(False, help="Use strict validation rules"),
):
    """Validate environment configuration."""
    try:
        from msfw.core.config import load_config
        import re
        
        # Load configuration
        if config_file:
            config = load_config(config_file)
        else:
            config = load_config()
        
        # Determine which environment to validate
        if environment is None:
            environment = config.environment
            console.print(f"🔍 Validating current environment: [bold cyan]{environment}[/bold cyan]")
        else:
            console.print(f"🔍 Validating environment: [bold cyan]{environment}[/bold cyan]")
        
        # Check if environment exists
        if environment not in config.environments:
            console.print(f"❌ Environment '{environment}' not found in configuration", style="red")
            raise typer.Exit(1)
        
        env_config = config.environments[environment]
        errors = []
        warnings = []
        
        # Validate global environment settings
        if not env_config.log_level or env_config.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            errors.append("Invalid log level (must be DEBUG, INFO, WARNING, ERROR, or CRITICAL)")
        
        # Validate services in this environment
        for service_name, service_config in env_config.services.items():
            service_prefix = f"Service '{service_name}'"
            
            # Port validation
            if not (1 <= service_config.port <= 65535):
                errors.append(f"{service_prefix}: Invalid port {service_config.port} (must be 1-65535)")
            
            # Check for port conflicts
            for other_name, other_config in env_config.services.items():
                if (other_name != service_name and 
                    other_config.enabled and service_config.enabled and
                    other_config.port == service_config.port):
                    errors.append(f"{service_prefix}: Port conflict with service '{other_name}' (both use port {service_config.port})")
            
            # Validate database URL if specified
            if service_config.database and service_config.database.url:
                db_url = service_config.database.url
                if not (db_url.startswith(('sqlite', 'postgresql', 'mysql')) or 
                       '${' in db_url):  # Allow environment variable interpolation
                    warnings.append(f"{service_prefix}: Database URL format may be invalid")
            
            # Validate Redis URL if specified  
            if service_config.redis and service_config.redis.url:
                redis_url = service_config.redis.url
                if not (redis_url.startswith('redis://') or '${' in redis_url):
                    warnings.append(f"{service_prefix}: Redis URL should start with 'redis://'")
            
            # Strict validation rules
            if strict:
                # Production environment checks
                if environment.lower() in ['production', 'prod']:
                    if service_config.debug:
                        warnings.append(f"{service_prefix}: Debug mode enabled in production environment")
                    
                    if service_config.workers < 2:
                        warnings.append(f"{service_prefix}: Consider using multiple workers in production")
                
                # Security checks
                if (service_config.security and 
                    service_config.security.secret_key and 
                    service_config.security.secret_key in ['dev-secret-key', 'change-me-in-production']):
                    errors.append(f"{service_prefix}: Using default secret key (security risk)")
        
        # Check for missing required environment variables in production
        if strict and environment.lower() in ['production', 'prod']:
            critical_vars = ['SECRET_KEY', 'DATABASE_URL']
            for var in critical_vars:
                if var not in os.environ:
                    warnings.append(f"Environment variable '{var}' not set (may be required for production)")
        
        # Report results
        console.print("=" * 50)
        
        if errors:
            console.print(f"❌ Validation failed with {len(errors)} error(s):", style="red")
            for error in errors:
                console.print(f"  • {error}", style="red")
        
        if warnings:
            console.print(f"\n⚠️  {len(warnings)} warning(s):", style="yellow")
            for warning in warnings:
                console.print(f"  • {warning}", style="yellow")
        
        if not errors and not warnings:
            console.print("✅ Environment configuration is valid", style="green")
        elif not errors:
            console.print("✅ Environment configuration is valid (with warnings)", style="green")
        
        console.print("=" * 50)
        
        if errors:
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"❌ Failed to validate environment: {e}", style="red")
        raise typer.Exit(1)


# Secrets Management Commands
secrets_app = typer.Typer(help="Secure secrets management commands")
app.add_typer(secrets_app, name="secrets")


@secrets_app.command("list")
def list_secrets(
    environment: Optional[str] = typer.Option(None, help="Environment to list secrets for"),
    show_values: bool = typer.Option(False, help="Show secret values (use with caution)"),
    config_file: Optional[str] = typer.Option(None, help="Configuration file path"),
):
    """List configured secrets and their sources."""
    try:
        from msfw.core.config import load_config
        import os
        import re
        
        # Load configuration
        if config_file:
            config = load_config(config_file)
        else:
            config = load_config()
        
        target_env = environment or config.environment
        console.print(f"🔐 Secrets for environment: [bold cyan]{target_env}[/bold cyan]")
        console.print("=" * 60)
        
        # Find all environment variable references in config
        secrets_info = {}
        
        def extract_env_vars(data, path=""):
            """Recursively extract environment variable references."""
            if isinstance(data, str):
                # Find ${VAR_NAME} or ${VAR_NAME:default} patterns
                pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
                matches = re.findall(pattern, data)
                for var_name, default_value in matches:
                    full_path = f"{path}.{var_name}" if path else var_name
                    secrets_info[var_name] = {
                        'path': path,
                        'default': default_value,
                        'value': os.getenv(var_name, default_value),
                        'is_set': var_name in os.environ,
                        'is_secret': any(keyword in var_name.lower() 
                                       for keyword in ['secret', 'key', 'password', 'token', 'auth'])
                    }
            elif isinstance(data, dict):
                for key, value in data.items():
                    new_path = f"{path}.{key}" if path else key
                    extract_env_vars(value, new_path)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    extract_env_vars(item, f"{path}[{i}]")
        
        # Extract from global config
        config_dict = config.model_dump()
        extract_env_vars(config_dict)
        
        # Extract from target environment
        if target_env in config.environments:
            env_config_dict = config.environments[target_env].model_dump()
            extract_env_vars(env_config_dict)
        
        if not secrets_info:
            console.print("No environment variables found in configuration", style="yellow")
            return
        
        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Variable", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("Status", style="green")
        table.add_column("Default", style="yellow")
        
        if show_values:
            table.add_column("Current Value", style="red")
        
        # Sort by secret status and name
        sorted_secrets = sorted(secrets_info.items(), 
                              key=lambda x: (not x[1]['is_secret'], x[0]))
        
        for var_name, info in sorted_secrets:
            var_type = "🔐 Secret" if info['is_secret'] else "📝 Config"
            status = "✅ Set" if info['is_set'] else "❌ Not Set"
            default = info['default'] if info['default'] else "None"
            
            row = [var_name, var_type, status, default]
            
            if show_values:
                if info['is_secret'] and info['is_set']:
                    # Mask secret values
                    value = info['value']
                    if len(value) > 8:
                        masked_value = value[:2] + "*" * (len(value) - 4) + value[-2:]
                    else:
                        masked_value = "*" * len(value)
                    row.append(masked_value)
                else:
                    row.append(info['value'] or "None")
            
            table.add_row(*row)
        
        console.print(table)
        
        # Summary
        secret_vars = [name for name, info in secrets_info.items() if info['is_secret']]
        config_vars = [name for name, info in secrets_info.items() if not info['is_secret']]
        unset_secrets = [name for name, info in secrets_info.items() 
                        if info['is_secret'] and not info['is_set']]
        
        console.print(f"\n📊 Summary:")
        console.print(f"  Secrets: {len(secret_vars)}")
        console.print(f"  Config Variables: {len(config_vars)}")
        console.print(f"  Unset Secrets: {len(unset_secrets)}")
        
        if unset_secrets:
            console.print(f"\n⚠️  Unset secrets may cause runtime errors:", style="yellow")
            for secret in unset_secrets:
                console.print(f"    - {secret}", style="yellow")
        
    except Exception as e:
        console.print(f"❌ Failed to list secrets: {e}", style="red")
        raise typer.Exit(1)


@secrets_app.command("set")
def set_secret(
    name: str = typer.Argument(help="Secret name"),
    value: Optional[str] = typer.Option(None, help="Secret value (will prompt if not provided)"),
    environment: Optional[str] = typer.Option(None, help="Environment to set secret for"),
    persist: bool = typer.Option(True, help="Persist to .env file"),
):
    """Set a secret value."""
    try:
        import os
        from pathlib import Path
        import getpass
        
        # Get secret value
        if value is None:
            value = getpass.getpass(f"Enter value for {name}: ")
        
        if not value:
            console.print("❌ Empty value provided", style="red")
            raise typer.Exit(1)
        
        # Set environment variable
        os.environ[name] = value
        console.print(f"✅ Set {name} in current session", style="green")
        
        # Persist to .env file if requested
        if persist:
            env_file = Path(".env")
            lines = []
            
            if env_file.exists():
                lines = env_file.read_text().splitlines()
            
            # Update or add the secret
            updated = False
            for i, line in enumerate(lines):
                if line.startswith(f"{name}="):
                    lines[i] = f"{name}={value}"
                    updated = True
                    break
            
            if not updated:
                lines.append(f"{name}={value}")
            
            env_file.write_text("\n".join(lines) + "\n")
            console.print(f"💾 Persisted {name} to .env file", style="blue")
            
            # Add .env to .gitignore if not already there
            gitignore = Path(".gitignore")
            if gitignore.exists():
                gitignore_content = gitignore.read_text()
                if ".env" not in gitignore_content:
                    gitignore.write_text(gitignore_content + "\n.env\n")
                    console.print("📝 Added .env to .gitignore", style="blue")
            else:
                gitignore.write_text(".env\n")
                console.print("📝 Created .gitignore with .env entry", style="blue")
        
        console.print(f"🔐 Secret '{name}' has been set successfully", style="green")
        
    except KeyboardInterrupt:
        console.print("\n❌ Operation cancelled", style="red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Failed to set secret: {e}", style="red")
        raise typer.Exit(1)


@secrets_app.command("unset")  
def unset_secret(
    name: str = typer.Argument(help="Secret name to unset"),
    from_env: bool = typer.Option(True, help="Remove from current environment"),
    from_file: bool = typer.Option(True, help="Remove from .env file"),
):
    """Unset a secret value."""
    try:
        import os
        from pathlib import Path
        
        removed_locations = []
        
        # Remove from current environment
        if from_env and name in os.environ:
            del os.environ[name]
            removed_locations.append("current session")
        
        # Remove from .env file
        if from_file:
            env_file = Path(".env")
            if env_file.exists():
                lines = env_file.read_text().splitlines()
                original_count = len(lines)
                lines = [line for line in lines if not line.startswith(f"{name}=")]
                
                if len(lines) < original_count:
                    env_file.write_text("\n".join(lines) + "\n")
                    removed_locations.append(".env file")
        
        if removed_locations:
            locations_str = " and ".join(removed_locations)
            console.print(f"✅ Removed '{name}' from {locations_str}", style="green")
        else:
            console.print(f"⚠️  Secret '{name}' was not found in any location", style="yellow")
        
    except Exception as e:
        console.print(f"❌ Failed to unset secret: {e}", style="red")
        raise typer.Exit(1)


@secrets_app.command("validate")
def validate_secrets(
    environment: Optional[str] = typer.Option(None, help="Environment to validate"),
    config_file: Optional[str] = typer.Option(None, help="Configuration file path"),
    strict: bool = typer.Option(False, help="Strict validation (fail on warnings)"),
):
    """Validate that all required secrets are configured."""
    try:
        from msfw.core.config import load_config
        import os
        import re
        
        # Load configuration  
        if config_file:
            config = load_config(config_file)
        else:
            config = load_config()
        
        # Determine which environment to validate
        if environment is None:
            environment = config.environment
            console.print(f"🔍 Validating current environment: [bold cyan]{environment}[/bold cyan]")
        else:
            console.print(f"🔍 Validating environment: [bold cyan]{environment}[/bold cyan]")
        
        # Check if environment exists
        if environment not in config.environments:
            console.print(f"❌ Environment '{environment}' not found in configuration", style="red")
            raise typer.Exit(1)
        
        env_config = config.environments[environment]
        errors = []
        warnings = []
        
        # Validate global environment settings
        if not env_config.log_level or env_config.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            errors.append("Invalid log level (must be DEBUG, INFO, WARNING, ERROR, or CRITICAL)")
        
        # Validate services in this environment
        for service_name, service_config in env_config.services.items():
            service_prefix = f"Service '{service_name}'"
            
            # Port validation
            if not (1 <= service_config.port <= 65535):
                errors.append(f"{service_prefix}: Invalid port {service_config.port} (must be 1-65535)")
            
            # Check for port conflicts
            for other_name, other_config in env_config.services.items():
                if (other_name != service_name and 
                    other_config.enabled and service_config.enabled and
                    other_config.port == service_config.port):
                    errors.append(f"{service_prefix}: Port conflict with service '{other_name}' (both use port {service_config.port})")
            
            # Validate database URL if specified
            if service_config.database and service_config.database.url:
                db_url = service_config.database.url
                if not (db_url.startswith(('sqlite', 'postgresql', 'mysql')) or 
                       '${' in db_url):  # Allow environment variable interpolation
                    warnings.append(f"{service_prefix}: Database URL format may be invalid")
            
            # Validate Redis URL if specified  
            if service_config.redis and service_config.redis.url:
                redis_url = service_config.redis.url
                if not (redis_url.startswith('redis://') or '${' in redis_url):
                    warnings.append(f"{service_prefix}: Redis URL should start with 'redis://'")
            
            # Strict validation rules
            if strict:
                # Production environment checks
                if environment.lower() in ['production', 'prod']:
                    if service_config.debug:
                        warnings.append(f"{service_prefix}: Debug mode enabled in production environment")
                    
                    if service_config.workers < 2:
                        warnings.append(f"{service_prefix}: Consider using multiple workers in production")
                
                # Security checks
                if (service_config.security and 
                    service_config.security.secret_key and 
                    service_config.security.secret_key in ['dev-secret-key', 'change-me-in-production']):
                    errors.append(f"{service_prefix}: Using default secret key (security risk)")
        
        # Check for missing required environment variables in production
        if strict and environment.lower() in ['production', 'prod']:
            critical_vars = ['SECRET_KEY', 'DATABASE_URL']
            for var in critical_vars:
                if var not in os.environ:
                    warnings.append(f"Environment variable '{var}' not set (may be required for production)")
        
        # Report results
        console.print("=" * 50)
        
        if errors:
            console.print(f"❌ Validation failed with {len(errors)} error(s):", style="red")
            for error in errors:
                console.print(f"  • {error}", style="red")
        
        if warnings:
            console.print(f"\n⚠️  {len(warnings)} warning(s):", style="yellow")
            for warning in warnings:
                console.print(f"  • {warning}", style="yellow")
        
        if not errors and not warnings:
            console.print("✅ Environment configuration is valid", style="green")
        elif not errors:
            console.print("✅ Environment configuration is valid (with warnings)", style="green")
        
        console.print("=" * 50)
        
        if errors:
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"❌ Failed to validate environment: {e}", style="red")
        raise typer.Exit(1)


@secrets_app.command("generate")
def generate_secret(
    name: Optional[str] = typer.Argument(None, help="Secret name"),
    length: int = typer.Option(32, help="Secret length"),
    charset: str = typer.Option("alphanumeric", help="Character set: alphanumeric, hex, base64, or custom"),
    custom_chars: Optional[str] = typer.Option(None, help="Custom character set"),
    set_env: bool = typer.Option(False, help="Set as environment variable"),
):
    """Generate a secure random secret."""
    try:
        import secrets
        import string
        
        # Define character sets
        charsets = {
            'alphanumeric': string.ascii_letters + string.digits,
            'hex': string.hexdigits.lower(),
            'base64': string.ascii_letters + string.digits + '+/',
            'ascii': string.ascii_letters + string.digits + string.punctuation,
        }
        
        if charset == 'custom' and custom_chars:
            chars = custom_chars
        elif charset in charsets:
            chars = charsets[charset]
        else:
            console.print(f"❌ Unknown charset: {charset}", style="red")
            console.print(f"Available charsets: {', '.join(charsets.keys())}, custom")
            raise typer.Exit(1)
        
        # Generate secret
        if charset == 'hex' and length % 2 == 1:
            length += 1  # Ensure even length for hex
        
        secret_value = ''.join(secrets.choice(chars) for _ in range(length))
        
        if name:
            console.print(f"🔐 Generated secret for '{name}':", style="green")
            console.print(f"   {name}={secret_value}")
            
            if set_env:
                os.environ[name] = secret_value
                console.print(f"✅ Set {name} in current session", style="green")
                
                # Optionally save to .env
                if typer.confirm("Save to .env file?"):
                    from pathlib import Path
                    env_file = Path(".env")
                    lines = []
                    
                    if env_file.exists():
                        lines = env_file.read_text().splitlines()
                    
                    # Update or add
                    updated = False
                    for i, line in enumerate(lines):
                        if line.startswith(f"{name}="):
                            lines[i] = f"{name}={secret_value}"
                            updated = True
                            break
                    
                    if not updated:
                        lines.append(f"{name}={secret_value}")
                    
                    env_file.write_text("\n".join(lines) + "\n")
                    console.print(f"💾 Saved to .env file", style="blue")
        else:
            console.print(f"🔐 Generated secret:", style="green")
            console.print(f"   {secret_value}")
        
    except Exception as e:
        console.print(f"❌ Failed to generate secret: {e}", style="red")
        raise typer.Exit(1)


if __name__ == "__main__":
    app() 