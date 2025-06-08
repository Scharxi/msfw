"""Configuration management for MSFW applications."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dynaconf import Dynaconf
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseModel):
    """Database configuration."""
    
    url: str = Field(default="sqlite+aiosqlite:///./app.db")
    echo: bool = Field(default=False)
    pool_size: int = Field(default=5)
    max_overflow: int = Field(default=10)
    pool_timeout: int = Field(default=30)
    pool_recycle: int = Field(default=3600)


class RedisConfig(BaseModel):
    """Redis configuration."""
    
    url: str = Field(default="redis://localhost:6379/0")
    max_connections: int = Field(default=10)
    socket_timeout: float = Field(default=5.0)
    socket_connect_timeout: float = Field(default=5.0)


class SecurityConfig(BaseModel):
    """Security configuration."""
    
    secret_key: str = Field(default="your-secret-key-change-in-production")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    password_reset_expire_minutes: int = Field(default=15)


class CorsConfig(BaseModel):
    """CORS configuration."""
    
    allow_origins: List[str] = Field(default=["*"])
    allow_credentials: bool = Field(default=True)
    allow_methods: List[str] = Field(default=["*"])
    allow_headers: List[str] = Field(default=["*"])


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default="INFO")
    format: str = Field(default="text")  # "text" or "json"


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    
    enabled: bool = Field(default=True)
    prometheus_enabled: bool = Field(default=True)
    metrics_path: str = Field(default="/metrics")
    health_check_path: str = Field(default="/health")


class OpenAPIConfig(BaseModel):
    """OpenAPI/Swagger configuration."""
    
    enabled: bool = Field(default=True)
    title: Optional[str] = Field(default=None)  # Will use app_name if not provided
    description: Optional[str] = Field(default=None)  # Will use app description if not provided
    version: Optional[str] = Field(default=None)  # Will use app version if not provided
    docs_url: str = Field(default="/docs")
    redoc_url: str = Field(default="/redoc")
    openapi_url: str = Field(default="/openapi.json")
    
    # Advanced settings
    tags_metadata: Optional[List[Dict[str, Any]]] = Field(default=None)
    servers: Optional[List[Dict[str, str]]] = Field(default=None)
    contact: Optional[Dict[str, str]] = Field(default=None)
    license_info: Optional[Dict[str, str]] = Field(default=None)
    terms_of_service: Optional[str] = Field(default=None)
    
    # Security schemes
    security_schemes: Optional[Dict[str, Dict[str, Any]]] = Field(default=None)
    
    # Custom OpenAPI schema modifications
    include_in_schema: bool = Field(default=True)
    generate_unique_id_function: Optional[str] = Field(default=None)
    
    # UI customization
    swagger_ui_parameters: Optional[Dict[str, Any]] = Field(default=None)
    swagger_ui_oauth2_redirect_url: Optional[str] = Field(default="/docs/oauth2-redirect")
    swagger_ui_init_oauth: Optional[Dict[str, Any]] = Field(default=None)
    
    # Documentation options
    include_version_in_docs: bool = Field(default=True)
    include_deprecated_endpoints: bool = Field(default=True)
    group_by_tags: bool = Field(default=True)
    
    # Export options
    export_formats: List[str] = Field(default=["json", "yaml"])
    export_path: str = Field(default="./openapi")
    auto_export: bool = Field(default=False)


class ServiceConfig(BaseModel):
    """Configuration for a single microservice."""
    
    enabled: bool = Field(default=True)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=1)
    debug: bool = Field(default=False)
    
    # Service-specific components
    database: Optional[DatabaseConfig] = Field(default=None)
    redis: Optional[RedisConfig] = Field(default=None)
    security: Optional[SecurityConfig] = Field(default=None)
    cors: Optional[CorsConfig] = Field(default=None)
    logging: Optional[LoggingConfig] = Field(default=None)
    monitoring: Optional[MonitoringConfig] = Field(default=None)
    openapi: Optional[OpenAPIConfig] = Field(default=None)
    
    # Custom settings per service
    settings: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v


class EnvironmentConfig(BaseModel):
    """Configuration for a specific environment (dev, prod, etc.)."""
    
    # Global settings for this environment
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    
    # Service configurations in this environment
    services: Dict[str, ServiceConfig] = Field(default_factory=dict)
    
    # Global component configurations
    database: Optional[DatabaseConfig] = Field(default=None)
    redis: Optional[RedisConfig] = Field(default=None)
    security: Optional[SecurityConfig] = Field(default=None)
    cors: Optional[CorsConfig] = Field(default=None)
    logging: Optional[LoggingConfig] = Field(default=None)
    monitoring: Optional[MonitoringConfig] = Field(default=None)
    openapi: Optional[OpenAPIConfig] = Field(default=None)


class Config(BaseSettings):
    """Main application configuration."""
    
    # Application settings
    app_name: str = Field(default="MSFW Application")
    version: str = Field(default="0.1.0")
    description: str = Field(default="A modular microservices framework")
    debug: bool = Field(default=False)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=1)
    
    # Environment selection
    environment: str = Field(default="development")
    
    # Component configurations (global defaults)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    cors: CorsConfig = Field(default_factory=CorsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    openapi: OpenAPIConfig = Field(default_factory=OpenAPIConfig)
    
    # Environment-specific configurations
    environments: Dict[str, EnvironmentConfig] = Field(default_factory=dict)
    
    # Microservice configurations
    services: Dict[str, ServiceConfig] = Field(default_factory=dict)
    
    # Module and plugin settings
    modules_dir: str = Field(default="modules")
    modules_directory: str = Field(default="modules")  # Alias for modules_dir
    plugins_dir: str = Field(default="plugins")
    auto_discover_modules: bool = Field(default=True)
    auto_discover_plugins: bool = Field(default=True)
    
    # Additional settings
    settings: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid"
    )
        
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v

    def get_service_config(self, service_name: str) -> ServiceConfig:
        """Get configuration for a specific service, with environment overrides."""
        # Start with global service config
        service_config = self.services.get(service_name)
        
        if not service_config:
            # Create default service config
            service_config = ServiceConfig()
        
        # Apply environment-specific overrides
        env_config = self.environments.get(self.environment)
        if env_config and service_name in env_config.services:
            env_service_config = env_config.services[service_name]
            
            # Merge configurations - environment takes precedence
            merged_data = service_config.model_dump()
            env_data = env_service_config.model_dump(exclude_unset=True)
            
            # Deep merge
            def deep_merge(base: dict, override: dict) -> dict:
                for key, value in override.items():
                    if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                        base[key] = deep_merge(base[key], value)
                    elif value is not None:
                        base[key] = value
                return base
            
            merged_data = deep_merge(merged_data, env_data)
            service_config = ServiceConfig(**merged_data)
        
        # Apply global component defaults if service doesn't have them
        if service_config.database is None:
            service_config.database = self.database
        if service_config.redis is None:
            service_config.redis = self.redis
        if service_config.security is None:
            service_config.security = self.security
        if service_config.cors is None:
            service_config.cors = self.cors
        if service_config.logging is None:
            service_config.logging = self.logging
        if service_config.monitoring is None:
            service_config.monitoring = self.monitoring
        if service_config.openapi is None:
            service_config.openapi = self.openapi
        
        return service_config

    def get_current_environment_config(self) -> Optional[EnvironmentConfig]:
        """Get the configuration for the current environment."""
        return self.environments.get(self.environment)

    @staticmethod
    def _interpolate_env_vars(data: Any) -> Any:
        """
        Recursively interpolate environment variables in configuration data.
        
        Supports patterns:
        - ${VAR_NAME} - required variable, will raise error if not found
        - ${VAR_NAME:default_value} - optional variable with default value
        """
        if isinstance(data, str):
            # Pattern for ${VAR_NAME} or ${VAR_NAME:default}
            pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
            
            def replace_var(match):
                var_name = match.group(1)
                default_value = match.group(2)
                
                env_value = os.getenv(var_name)
                
                if env_value is not None:
                    return env_value
                elif default_value is not None:
                    return default_value
                else:
                    raise ValueError(f"Environment variable '{var_name}' is required but not set")
            
            return re.sub(pattern, replace_var, data)
        
        elif isinstance(data, dict):
            return {key: Config._interpolate_env_vars(value) for key, value in data.items()}
        
        elif isinstance(data, list):
            return [Config._interpolate_env_vars(item) for item in data]
        
        else:
            return data
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "Config":
        """Load configuration from file with environment variable interpolation."""
        import tomllib
        
        config_path = Path(config_path)
        
        with open(config_path, 'rb') as f:
            config_dict = tomllib.load(f)
        
        # Interpolate environment variables
        interpolated_dict = cls._interpolate_env_vars(config_dict)
            
        return cls(**interpolated_dict)
    
    @classmethod 
    def from_file_and_env(cls, config_path: Union[str, Path]) -> "Config":
        """
        Load configuration from TOML file with environment variable interpolation,
        then allow environment variables to override any values.
        
        This provides the best of both worlds:
        1. TOML file as the source of truth (can be committed to git)
        2. Environment variables for sensitive data and deployment-specific overrides
        3. Environment variable interpolation in TOML for flexibility
        """
        if Path(config_path).exists():
            # Load from file first (with interpolation)
            config = cls.from_file(config_path)
            
            # Create a new instance that will also read from environment
            # The environment variables will override any file values
            env_config = cls()
            
            # Merge configurations - env takes precedence
            config_dict = config.model_dump()
            env_dict = env_config.model_dump()
            
            # Deep merge function
            def deep_merge(base: dict, override: dict) -> dict:
                for key, value in override.items():
                    if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                        base[key] = deep_merge(base[key], value)
                    else:
                        # Only override if the env value is different from default
                        default_config = cls()
                        default_value = getattr(default_config, key, None)
                        if hasattr(default_config, key):
                            if isinstance(default_value, BaseModel):
                                default_dict = default_value.model_dump()
                                if value != default_dict:
                                    base[key] = value
                            else:
                                if value != default_value:
                                    base[key] = value
                        else:
                            base[key] = value
                return base
            
            merged_dict = deep_merge(config_dict, env_dict)
            return cls(**merged_dict)
        else:
            # Fallback to environment-only configuration
            return cls()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with dot notation support."""
        keys = key.split('.')
        value = self.settings
        
        try:
            for k in keys:
                if hasattr(self, k):
                    value = getattr(self, k)
                elif isinstance(value, dict):
                    value = value[k]
                else:
                    value = getattr(value, k)
            return value
        except (KeyError, AttributeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value with dot notation support."""
        keys = key.split('.')
        target = self.settings
        
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value
    
    def update(self, **kwargs) -> None:
        """Update configuration with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.settings[key] = value


def load_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """
    Convenience function to load configuration.
    
    Priority order:
    1. config_path if provided
    2. config/settings.toml
    3. settings.toml  
    4. Environment variables only
    """
    if config_path:
        return Config.from_file_and_env(config_path)
    
    # Try common config file locations
    for path in ["config/settings.toml", "settings.toml"]:
        if Path(path).exists():
            return Config.from_file_and_env(path)
    
    # Fallback to environment-only
    return Config() 