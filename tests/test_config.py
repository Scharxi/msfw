"""Tests for the MSFW configuration system."""

import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from msfw.core.config import (
    Config,
    DatabaseConfig,
    SecurityConfig,
    LoggingConfig,
    MonitoringConfig,
    CorsConfig,
    RedisConfig,
)


@pytest.mark.unit
class TestDatabaseConfig:
    """Test database configuration."""
    
    def test_default_values(self):
        """Test default database configuration values."""
        config = DatabaseConfig()
        
        assert config.url == "sqlite+aiosqlite:///./app.db"
        assert config.echo is False
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600
    
    def test_custom_values(self):
        """Test custom database configuration values."""
        config = DatabaseConfig(
            url="postgresql+asyncpg://user:pass@localhost/test",
            echo=True,
            pool_size=10,
            max_overflow=20,
        )
        
        assert config.url == "postgresql+asyncpg://user:pass@localhost/test"
        assert config.echo is True
        assert config.pool_size == 10
        assert config.max_overflow == 20


@pytest.mark.unit
class TestSecurityConfig:
    """Test security configuration."""
    
    def test_default_values(self):
        """Test default security configuration values."""
        config = SecurityConfig()
        
        assert config.secret_key == "your-secret-key-change-in-production"
        assert config.algorithm == "HS256"
        assert config.access_token_expire_minutes == 30
        assert config.refresh_token_expire_days == 7
    
    def test_custom_values(self):
        """Test custom security configuration values."""
        config = SecurityConfig(
            secret_key="custom-secret-key",
            algorithm="RS256",
            access_token_expire_minutes=60,
        )
        
        assert config.secret_key == "custom-secret-key"
        assert config.algorithm == "RS256"
        assert config.access_token_expire_minutes == 60


@pytest.mark.unit
class TestMainConfig:
    """Test main configuration class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.app_name == "MSFW Application"
        assert config.version == "0.1.0"
        assert config.debug is False
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.workers == 1
        
        # Test nested configs
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.monitoring, MonitoringConfig)
    
    def test_port_validation(self):
        """Test port validation."""
        # Valid port
        config = Config(port=8080)
        assert config.port == 8080
        
        # Invalid ports should raise ValidationError
        with pytest.raises(ValidationError):
            Config(port=0)
        
        with pytest.raises(ValidationError):
            Config(port=99999)
    
    def test_custom_settings(self):
        """Test custom settings dictionary."""
        config = Config()
        
        # Test get/set methods
        config.set("custom.setting", "value")
        assert config.get("custom.setting") == "value"
        
        # Test nested settings
        config.set("nested.deep.setting", 42)
        assert config.get("nested.deep.setting") == 42
        
        # Test default value
        assert config.get("non.existent", "default") == "default"
    
    def test_update_method(self):
        """Test configuration update method."""
        config = Config()
        
        config.update(
            app_name="Updated App",
            debug=True,
            custom_setting="value"
        )
        
        assert config.app_name == "Updated App"
        assert config.debug is True
        assert config.settings["custom_setting"] == "value"
    
    def test_from_file_toml(self):
        """Test loading configuration from TOML file."""
        toml_content = """
app_name = "Test App"
debug = true
port = 9000

[database]
url = "sqlite+aiosqlite:///test.db"
echo = true

[security]
secret_key = "test-secret"
access_token_expire_minutes = 120
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            
            try:
                config = Config.from_file(f.name)
                
                assert config.app_name == "Test App"
                assert config.debug is True
                assert config.port == 9000
                assert config.database.url == "sqlite+aiosqlite:///test.db"
                assert config.database.echo is True
                assert config.security.secret_key == "test-secret"
                assert config.security.access_token_expire_minutes == 120
            finally:
                os.unlink(f.name)


@pytest.mark.unit
class TestEnvironmentVariables:
    """Test environment variable integration."""
    
    def test_env_var_override(self, monkeypatch):
        """Test that environment variables override default values."""
        # Set environment variables
        monkeypatch.setenv("APP_NAME", "Env App")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("PORT", "9999")
        monkeypatch.setenv("DATABASE__URL", "postgresql://test")
        monkeypatch.setenv("SECURITY__SECRET_KEY", "env-secret")
        
        config = Config()
        
        assert config.app_name == "Env App"
        assert config.debug is True
        assert config.port == 9999
        assert config.database.url == "postgresql://test"
        assert config.security.secret_key == "env-secret"
    
    def test_nested_env_vars(self, monkeypatch):
        """Test nested environment variable handling."""
        monkeypatch.setenv("DATABASE__POOL_SIZE", "20")
        monkeypatch.setenv("DATABASE__ECHO", "true")
        monkeypatch.setenv("MONITORING__ENABLED", "false")
        
        config = Config()
        
        assert config.database.pool_size == 20
        assert config.database.echo is True
        assert config.monitoring.enabled is False


@pytest.mark.unit
class TestCorsConfig:
    """Test CORS configuration."""
    
    def test_default_cors_config(self):
        """Test default CORS configuration."""
        config = CorsConfig()
        
        assert config.allow_origins == ["*"]
        assert config.allow_credentials is True
        assert config.allow_methods == ["*"]
        assert config.allow_headers == ["*"]
    
    def test_custom_cors_config(self):
        """Test custom CORS configuration."""
        config = CorsConfig(
            allow_origins=["http://localhost:3000", "https://example.com"],
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["content-type", "authorization"],
        )
        
        assert config.allow_origins == ["http://localhost:3000", "https://example.com"]
        assert config.allow_credentials is False
        assert config.allow_methods == ["GET", "POST"]
        assert config.allow_headers == ["content-type", "authorization"]


@pytest.mark.unit
class TestRedisConfig:
    """Test Redis configuration."""
    
    def test_default_redis_config(self):
        """Test default Redis configuration."""
        config = RedisConfig()
        
        assert config.url == "redis://localhost:6379/0"
        assert config.max_connections == 10
        assert config.socket_timeout == 5.0
        assert config.socket_connect_timeout == 5.0
    
    def test_custom_redis_config(self):
        """Test custom Redis configuration."""
        config = RedisConfig(
            url="redis://localhost:6379/1",
            max_connections=20,
            socket_timeout=10.0,
        )
        
        assert config.url == "redis://localhost:6379/1"
        assert config.max_connections == 20
        assert config.socket_timeout == 10.0


@pytest.mark.unit
class TestLoggingConfig:
    """Test logging configuration."""
    
    def test_default_logging_config(self):
        """Test default logging configuration."""
        config = LoggingConfig()
        
        assert config.level == "INFO"
        assert config.format == "text"
    
    def test_custom_logging_config(self):
        """Test custom logging configuration."""
        config = LoggingConfig(
            level="DEBUG",
            format="json",
        )
        
        assert config.level == "DEBUG"
        assert config.format == "json"


@pytest.mark.unit
class TestMonitoringConfig:
    """Test monitoring configuration."""
    
    def test_default_monitoring_config(self):
        """Test default monitoring configuration."""
        config = MonitoringConfig()
        
        assert config.enabled is True
        assert config.prometheus_enabled is True
        assert config.metrics_path == "/metrics"
        assert config.health_check_path == "/health"
    
    def test_custom_monitoring_config(self):
        """Test custom monitoring configuration."""
        config = MonitoringConfig(
            enabled=False,
            prometheus_enabled=False,
            metrics_path="/custom-metrics",
            health_check_path="/custom-health",
        )
        
        assert config.enabled is False
        assert config.prometheus_enabled is False
        assert config.metrics_path == "/custom-metrics"
        assert config.health_check_path == "/custom-health"


@pytest.mark.unit
class TestEnvironmentVariableInterpolation:
    """Test environment variable interpolation in configuration."""

    def test_simple_env_var_interpolation(self, monkeypatch):
        """Test simple environment variable interpolation."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        
        result = Config._interpolate_env_vars("${TEST_VAR}")
        assert result == "test_value"

    def test_env_var_with_default(self, monkeypatch):
        """Test environment variable with default value."""
        # Unset variable should use default
        result = Config._interpolate_env_vars("${UNSET_VAR:default_value}")
        assert result == "default_value"
        
        # Set variable should override default
        monkeypatch.setenv("SET_VAR", "env_value")
        result = Config._interpolate_env_vars("${SET_VAR:default_value}")
        assert result == "env_value"

    def test_required_env_var_missing(self):
        """Test that missing required environment variable raises error."""
        with pytest.raises(ValueError, match="Environment variable 'MISSING_VAR' is required"):
            Config._interpolate_env_vars("${MISSING_VAR}")

    def test_complex_string_interpolation(self, monkeypatch):
        """Test interpolation in complex strings."""
        monkeypatch.setenv("DB_HOST", "localhost")
        monkeypatch.setenv("DB_NAME", "myapp")
        
        result = Config._interpolate_env_vars("postgresql://${DB_HOST}:5432/${DB_NAME}")
        assert result == "postgresql://localhost:5432/myapp"

    def test_dict_interpolation(self, monkeypatch):
        """Test interpolation in dictionary values."""
        monkeypatch.setenv("SECRET", "mysecret")
        
        data = {
            "security": {
                "secret_key": "${SECRET}",
                "static_value": "unchanged"
            }
        }
        
        result = Config._interpolate_env_vars(data)
        assert result["security"]["secret_key"] == "mysecret"
        assert result["security"]["static_value"] == "unchanged"

    def test_list_interpolation(self, monkeypatch):
        """Test interpolation in list values."""
        monkeypatch.setenv("HOST1", "host1.com")
        monkeypatch.setenv("HOST2", "host2.com")
        
        data = ["${HOST1}", "${HOST2:default.com}", "static.com"]
        
        result = Config._interpolate_env_vars(data)
        assert result == ["host1.com", "host2.com", "static.com"]

    def test_from_file_with_interpolation(self, monkeypatch):
        """Test loading configuration from file with interpolation."""
        monkeypatch.setenv("TEST_SECRET", "env-secret-key")
        monkeypatch.setenv("TEST_DB_HOST", "env-db-host")
        
        toml_content = """
app_name = "${APP_NAME:Test App}"
debug = "${DEBUG:true}"

[database]
url = "postgresql://${TEST_DB_HOST}:5432/testdb"

[security]
secret_key = "${TEST_SECRET}"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            
            try:
                config = Config.from_file(f.name)
                
                assert config.app_name == "Test App"  # Uses default
                assert config.debug is True
                assert config.database.url == "postgresql://env-db-host:5432/testdb"
                assert config.security.secret_key == "env-secret-key"
            finally:
                os.unlink(f.name)

    def test_boolean_interpolation(self, monkeypatch):
        """Test boolean value interpolation."""
        monkeypatch.setenv("ENABLE_FEATURE", "true")
        monkeypatch.setenv("DISABLE_FEATURE", "false")
        
        # Test direct boolean interpolation
        assert Config._interpolate_env_vars("${ENABLE_FEATURE}") == "true"
        assert Config._interpolate_env_vars("${DISABLE_FEATURE}") == "false"
        
        # Test with defaults
        assert Config._interpolate_env_vars("${UNSET_BOOL:true}") == "true"

    def test_from_file_and_env_priority(self, monkeypatch):
        """Test that environment variables override file values in from_file_and_env."""
        # Set environment variables
        monkeypatch.setenv("APP_NAME", "Env Override App")
        monkeypatch.setenv("DATABASE__URL", "postgresql://env-override")
        
        toml_content = """
app_name = "${APP_NAME:File App}"
debug = true

[database]
url = "${DATABASE_URL:sqlite:///file.db}"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            
            try:
                config = Config.from_file_and_env(f.name)
                
                # Environment variable should override the interpolated value
                assert config.app_name == "Env Override App"
                # Environment variable should override the interpolated database URL
                assert config.database.url == "postgresql://env-override"
                # Values not set in env should use file values
                assert config.debug is True
            finally:
                os.unlink(f.name) 