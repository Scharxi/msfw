"""Configuration management for MSFW applications."""

import os
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
    format: str = Field(default="json")
    handlers: List[str] = Field(default=["console"])
    file_path: Optional[str] = Field(default=None)
    max_file_size: str = Field(default="10MB")
    backup_count: int = Field(default=5)


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
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "Config":
        """Load configuration from file using simple TOML parsing."""
        import tomllib
        
        config_path = Path(config_path)
        
        with open(config_path, 'rb') as f:
            config_dict = tomllib.load(f)
            
        return cls(**config_dict)
    
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