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
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    cors: CorsConfig = Field(default_factory=CorsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
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