"""
OpenAPI Schema Generation and Management for MSFW
==============================================

This module provides comprehensive OpenAPI support including:
- Custom schema generation with versioning support
- OpenAPI documentation customization
- Schema export in multiple formats
- Integration with MSFW's versioning system
"""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse, JSONResponse

from msfw.core.config import Config, OpenAPIConfig
from msfw.core.versioning import APIVersionManager, version_manager


class OpenAPIManager:
    """Manages OpenAPI schema generation and customization for MSFW applications."""
    
    def __init__(self, config: Config, version_manager: Optional[APIVersionManager] = None):
        self.config = config
        self.openapi_config = config.openapi
        self.version_manager = version_manager or globals().get('version_manager')
        self._custom_schemas: Dict[str, Dict] = {}
        self._tag_metadata: List[Dict[str, Any]] = []
        
    def generate_openapi_schema(
        self, 
        app: FastAPI, 
        version: Optional[str] = None,
        include_deprecated: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Generate OpenAPI schema for the application, optionally for a specific version.
        
        Args:
            app: FastAPI application instance
            version: Specific API version to generate schema for
            include_deprecated: Whether to include deprecated endpoints
            
        Returns:
            OpenAPI schema dictionary
        """
        # Use config defaults if not specified
        if include_deprecated is None:
            include_deprecated = self.openapi_config.include_deprecated_endpoints
            
        # Set up basic schema parameters
        title = self.openapi_config.title or self.config.app_name
        description = self.openapi_config.description or self.config.description
        schema_version = version or self.openapi_config.version or self.config.version
        
        # Include version in title if configured
        if version and self.openapi_config.include_version_in_docs:
            title = f"{title} (v{version})"
            
        # Generate base schema
        schema = get_openapi(
            title=title,
            version=schema_version,
            description=description,
            routes=app.routes,
            tags=self._get_combined_tags_metadata(),
            servers=self.openapi_config.servers,
            terms_of_service=self.openapi_config.terms_of_service,
            contact=self.openapi_config.contact,
            license_info=self.openapi_config.license_info,
        )
        
        # Add security schemes if configured
        if self.openapi_config.security_schemes:
            if "components" not in schema:
                schema["components"] = {}
            schema["components"]["securitySchemes"] = self.openapi_config.security_schemes
            
        # Filter by version if specified
        if version and self.version_manager:
            schema = self._filter_schema_by_version(schema, version, include_deprecated)
            
        # Apply custom schema modifications
        schema = self._apply_custom_modifications(schema, version)
        
        return schema
    
    def _filter_schema_by_version(
        self, 
        schema: Dict[str, Any], 
        version: str, 
        include_deprecated: bool
    ) -> Dict[str, Any]:
        """Filter OpenAPI schema to include only routes for the specified version."""
        if not self.version_manager:
            return schema
            
        filtered_paths = {}
        
        for path, path_item in schema.get("paths", {}).items():
            filtered_path_item = {}
            
            for method, operation in path_item.items():
                if method.lower() in ["get", "post", "put", "delete", "patch", "head", "options", "trace"]:
                    # Check if operation belongs to the specified version
                    operation_version = operation.get("tags", [])
                    if self._is_operation_for_version(operation, version, include_deprecated):
                        filtered_path_item[method] = operation
                        
            if filtered_path_item:
                filtered_paths[path] = filtered_path_item
                
        schema["paths"] = filtered_paths
        return schema
    
    def _is_operation_for_version(
        self, 
        operation: Dict[str, Any], 
        target_version: str, 
        include_deprecated: bool
    ) -> bool:
        """Check if an operation belongs to the target version."""
        # Check operation tags for version info
        tags = operation.get("tags", [])
        for tag in tags:
            if tag.startswith(f"v{target_version}"):
                # Check if deprecated and whether to include
                if operation.get("deprecated", False) and not include_deprecated:
                    return False
                return True
                
        # If no version tags, assume it belongs to all versions
        return True
    
    def _get_combined_tags_metadata(self) -> List[Dict[str, Any]]:
        """Get combined tags metadata from config and custom additions."""
        tags = []
        
        # Add configured tags
        if self.openapi_config.tags_metadata:
            tags.extend(self.openapi_config.tags_metadata)
            
        # Add custom tags
        tags.extend(self._tag_metadata)
        
        # Add version-based tags if version manager is available
        if self.version_manager and self.openapi_config.include_version_in_docs:
            for version_str in self.version_manager.get_available_versions():
                tag_name = f"v{version_str}"
                
                tag_metadata = {
                    "name": tag_name,
                    "description": f"API version {version_str} endpoints"
                }
                
                # Check if version is deprecated
                try:
                    from msfw.core.versioning import VersionInfo
                    version_info = VersionInfo.from_string(version_str)
                    if self.version_manager.is_version_deprecated(version_info):
                        tag_metadata["description"] += " (Deprecated)"
                except:
                    pass
                    
                tags.append(tag_metadata)
                
        return tags
    
    def _apply_custom_modifications(
        self, 
        schema: Dict[str, Any], 
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Apply custom schema modifications."""
        # Apply version-specific custom schemas
        version_key = f"v{version}" if version else "default"
        if version_key in self._custom_schemas:
            custom_schema = self._custom_schemas[version_key]
            schema = self._deep_merge_schemas(schema, custom_schema)
            
        return schema
    
    def _deep_merge_schemas(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two schema dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_schemas(result[key], value)
            else:
                result[key] = value
                
        return result
    
    def add_tag_metadata(self, name: str, description: str, external_docs: Optional[Dict] = None):
        """Add custom tag metadata to the OpenAPI schema."""
        tag_metadata = {"name": name, "description": description}
        if external_docs:
            tag_metadata["externalDocs"] = external_docs
            
        self._tag_metadata.append(tag_metadata)
    
    def add_custom_schema_component(
        self, 
        component_type: str, 
        name: str, 
        schema: Dict[str, Any],
        version: Optional[str] = None
    ):
        """Add custom schema components (models, responses, etc.)."""
        version_key = f"v{version}" if version else "default"
        
        if version_key not in self._custom_schemas:
            self._custom_schemas[version_key] = {"components": {}}
            
        if component_type not in self._custom_schemas[version_key]["components"]:
            self._custom_schemas[version_key]["components"][component_type] = {}
            
        self._custom_schemas[version_key]["components"][component_type][name] = schema
    
    def export_schema(
        self, 
        app: FastAPI, 
        formats: Optional[List[str]] = None,
        output_dir: Optional[str] = None,
        version: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Export OpenAPI schema in specified formats.
        
        Args:
            app: FastAPI application
            formats: List of formats to export (json, yaml)
            output_dir: Output directory path
            version: Specific version to export
            
        Returns:
            Dictionary mapping format to output file path
        """
        if formats is None:
            formats = self.openapi_config.export_formats
            
        if output_dir is None:
            output_dir = self.openapi_config.export_path
            
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        schema = self.generate_openapi_schema(app, version=version)
        exported_files = {}
        
        # Generate base filename
        base_name = "openapi"
        if version:
            base_name = f"openapi_v{version}"
            
        for format_type in formats:
            if format_type.lower() == "json":
                file_path = output_dir / f"{base_name}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(schema, f, indent=2, ensure_ascii=False)
                exported_files["json"] = str(file_path)
                
            elif format_type.lower() == "yaml":
                file_path = output_dir / f"{base_name}.yaml"
                with open(file_path, "w", encoding="utf-8") as f:
                    yaml.dump(schema, f, default_flow_style=False, allow_unicode=True)
                exported_files["yaml"] = str(file_path)
                
        return exported_files
    
    def setup_custom_docs_routes(self, app: FastAPI):
        """Set up custom documentation routes with enhanced features."""
        
        # Custom OpenAPI JSON endpoint with version support
        @app.get(self.openapi_config.openapi_url)
        async def get_openapi_schema(version: Optional[str] = None):
            """Get OpenAPI schema, optionally for a specific version."""
            if not self.openapi_config.enabled:
                return JSONResponse(
                    content={"error": "OpenAPI documentation is disabled"}, 
                    status_code=404
                )
                
            schema = self.generate_openapi_schema(app, version=version)
            return JSONResponse(content=schema)
        
        # Enhanced Swagger UI with version selector
        if self.openapi_config.docs_url:
            @app.get(self.openapi_config.docs_url, include_in_schema=False)
            async def custom_swagger_ui_html(version: Optional[str] = None):
                """Custom Swagger UI with version support."""
                if not self.openapi_config.enabled:
                    return HTMLResponse(
                        content="<h1>API Documentation Disabled</h1>", 
                        status_code=404
                    )
                
                openapi_url = self.openapi_config.openapi_url
                if version:
                    openapi_url = f"{openapi_url}?version={version}"
                    
                return get_swagger_ui_html(
                    openapi_url=openapi_url,
                    title=f"{self.config.app_name} - Swagger UI",
                    oauth2_redirect_url=self.openapi_config.swagger_ui_oauth2_redirect_url,
                    init_oauth=self.openapi_config.swagger_ui_init_oauth,
                    swagger_ui_parameters=self.openapi_config.swagger_ui_parameters,
                )
        
        # Enhanced ReDoc
        if self.openapi_config.redoc_url:
            @app.get(self.openapi_config.redoc_url, include_in_schema=False)
            async def custom_redoc_html(version: Optional[str] = None):
                """Custom ReDoc with version support."""
                if not self.openapi_config.enabled:
                    return HTMLResponse(
                        content="<h1>API Documentation Disabled</h1>", 
                        status_code=404
                    )
                
                openapi_url = self.openapi_config.openapi_url
                if version:
                    openapi_url = f"{openapi_url}?version={version}"
                    
                return get_redoc_html(
                    openapi_url=openapi_url,
                    title=f"{self.config.app_name} - ReDoc",
                )
        
        # Version listing endpoint
        if self.version_manager:
            @app.get("/api/versions", include_in_schema=False)
            async def list_api_versions():
                """List all available API versions."""
                versions = []
                available_versions = self.version_manager.get_available_versions()
                
                for version_str in available_versions:
                    try:
                        from msfw.core.versioning import VersionInfo
                        version_info = VersionInfo.from_string(version_str)
                        
                        deprecated = self.version_manager.is_version_deprecated(version_info)
                        deprecation_info = self.version_manager.get_deprecation_info(version_info)
                        
                        version_data = {
                            "version": version_str,
                            "deprecated": deprecated,
                            "docs_url": f"{self.openapi_config.docs_url}?version={version_str}",
                            "openapi_url": f"{self.openapi_config.openapi_url}?version={version_str}",
                        }
                        
                        if deprecated and deprecation_info:
                            version_data["deprecation_message"] = deprecation_info.get("message")
                            version_data["sunset_date"] = deprecation_info.get("sunset_date")
                            
                        versions.append(version_data)
                    except Exception as e:
                        # Fallback for any parsing issues
                        versions.append({
                            "version": version_str,
                            "deprecated": False,
                            "docs_url": f"{self.openapi_config.docs_url}?version={version_str}",
                            "openapi_url": f"{self.openapi_config.openapi_url}?version={version_str}",
                        })
                    
                return {"versions": versions}


def create_openapi_manager(config: Config, version_manager: Optional[APIVersionManager] = None) -> OpenAPIManager:
    """Create an OpenAPI manager instance."""
    return OpenAPIManager(config, version_manager)


def setup_openapi_documentation(
    app: FastAPI, 
    config: Config, 
    version_manager: Optional[APIVersionManager] = None
) -> OpenAPIManager:
    """
    Set up comprehensive OpenAPI documentation for a FastAPI application.
    
    Args:
        app: FastAPI application instance
        config: MSFW configuration
        version_manager: Optional version manager for versioned APIs
        
    Returns:
        OpenAPIManager instance for further customization
    """
    openapi_manager = create_openapi_manager(config, version_manager)
    
    if config.openapi.enabled:
        # Disable default docs endpoints (we'll create custom ones)
        app.docs_url = None
        app.redoc_url = None
        app.openapi_url = None
        
        # Set up custom documentation routes
        openapi_manager.setup_custom_docs_routes(app)
        
        # Auto-export schema if configured
        if config.openapi.auto_export:
            try:
                exported = openapi_manager.export_schema(app)
                print(f"✅ OpenAPI schema exported: {exported}")
            except Exception as e:
                print(f"⚠️ Failed to auto-export OpenAPI schema: {e}")
    
    return openapi_manager 