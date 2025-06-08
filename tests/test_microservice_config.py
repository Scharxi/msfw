"""Tests for microservice-specific configuration."""

import os
import tempfile
import pytest
from pathlib import Path

from msfw.core.config import Config, ServiceConfig, EnvironmentConfig


@pytest.mark.unit
class TestServiceConfig:
    """Test service-specific configuration."""
    
    def test_service_config_defaults(self):
        """Test default service configuration values."""
        service = ServiceConfig()
        
        assert service.enabled is True
        assert service.host == "0.0.0.0"
        assert service.port == 8000
        assert service.workers == 1
        assert service.debug is False
        
        # All component configs should be None by default
        assert service.database is None
        assert service.redis is None
        assert service.security is None
        assert service.cors is None
        assert service.logging is None
        assert service.monitoring is None
    
    def test_service_config_custom_values(self):
        """Test service configuration with custom values."""
        service = ServiceConfig(
            enabled=False,
            host="127.0.0.1",
            port=9000,
            workers=4,
            debug=True
        )
        
        assert service.enabled is False
        assert service.host == "127.0.0.1"
        assert service.port == 9000
        assert service.workers == 4
        assert service.debug is True
    
    def test_service_config_port_validation(self):
        """Test port validation in service config."""
        # Valid ports
        service = ServiceConfig(port=8080)
        assert service.port == 8080
        
        # Invalid ports
        with pytest.raises(ValueError):
            ServiceConfig(port=0)
        
        with pytest.raises(ValueError):
            ServiceConfig(port=99999)


@pytest.mark.unit
class TestEnvironmentConfig:
    """Test environment-specific configuration."""
    
    def test_environment_config_defaults(self):
        """Test default environment configuration."""
        env = EnvironmentConfig()
        
        assert env.debug is False
        assert env.log_level == "INFO"
        assert env.services == {}
        
        # All global component configs should be None by default
        assert env.database is None
        assert env.redis is None
        assert env.security is None


@pytest.mark.unit
class TestMicroserviceConfiguration:
    """Test microservice configuration features."""
    
    def test_basic_service_configuration(self):
        """Test basic service configuration parsing."""
        config_content = '''
app_name = "Test App"
environment = "development"

[services.api]
enabled = true
port = 8000
debug = true

[services.worker]
enabled = false
port = 8001
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            f.flush()
            
            try:
                config = Config.from_file(f.name)
                
                # Check services are parsed
                assert "api" in config.services
                assert "worker" in config.services
                
                api_service = config.services["api"]
                assert api_service.enabled is True
                assert api_service.port == 8000
                assert api_service.debug is True
                
                worker_service = config.services["worker"]
                assert worker_service.enabled is False
                assert worker_service.port == 8001
                
            finally:
                os.unlink(f.name)
    
    def test_get_service_config_with_defaults(self):
        """Test getting service config with global defaults."""
        config_content = '''
app_name = "Test App"

[database]
url = "sqlite+aiosqlite:///./global.db"

[security]
secret_key = "global-secret"

[services.api]
enabled = true
port = 8000
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            f.flush()
            
            try:
                config = Config.from_file(f.name)
                
                # Get service config - should inherit global defaults
                api_config = config.get_service_config("api")
                
                assert api_config.enabled is True
                assert api_config.port == 8000
                
                # Should inherit global configs
                assert api_config.database.url == "sqlite+aiosqlite:///./global.db"
                assert api_config.security.secret_key == "global-secret"
                
            finally:
                os.unlink(f.name)
    
    def test_service_specific_component_config(self):
        """Test service-specific component configuration."""
        config_content = '''
app_name = "Test App"

[database]
url = "sqlite+aiosqlite:///./global.db"

[services.api]
enabled = true
port = 8000

[services.api.database]
url = "sqlite+aiosqlite:///./api.db"

[services.worker]
enabled = true
port = 8001

[services.worker.redis]
url = "redis://localhost:6379/1"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            f.flush()
            
            try:
                config = Config.from_file(f.name)
                
                # API service should have custom database
                api_config = config.get_service_config("api")
                assert api_config.database.url == "sqlite+aiosqlite:///./api.db"
                
                # Worker service should have custom redis but inherit global database
                worker_config = config.get_service_config("worker")
                assert worker_config.redis.url == "redis://localhost:6379/1"
                assert worker_config.database.url == "sqlite+aiosqlite:///./global.db"
                
            finally:
                os.unlink(f.name)
    
    def test_environment_specific_service_config(self):
        """Test environment-specific service configuration."""
        config_content = '''
app_name = "Test App"
environment = "development"

[services.api]
enabled = true
port = 8000
debug = true
workers = 1

[environments.development]
debug = true

[environments.development.services.api]
debug = true
workers = 1

[environments.production]
debug = false

[environments.production.services.api]
debug = false
workers = 4
port = 9000
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            f.flush()
            
            try:
                # Test development environment
                dev_config = Config.from_file(f.name)
                dev_config.environment = "development"
                
                api_dev = dev_config.get_service_config("api")
                assert api_dev.port == 8000  # From base service config
                assert api_dev.debug is True
                assert api_dev.workers == 1
                
                # Test production environment
                prod_config = Config.from_file(f.name)
                prod_config.environment = "production"
                
                api_prod = prod_config.get_service_config("api")
                assert api_prod.port == 9000  # Overridden by production env
                assert api_prod.debug is False
                assert api_prod.workers == 4
                
            finally:
                os.unlink(f.name)
    
    def test_nonexistent_service_config(self):
        """Test getting config for non-existent service."""
        config = Config()
        
        # Should return default service config
        service_config = config.get_service_config("nonexistent")
        assert isinstance(service_config, ServiceConfig)
        assert service_config.enabled is True
        assert service_config.port == 8000
    
    def test_environment_config_methods(self):
        """Test environment configuration methods."""
        config_content = '''
environment = "production"

[environments.development]
debug = true
log_level = "DEBUG"

[environments.production]
debug = false
log_level = "WARNING"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            f.flush()
            
            try:
                config = Config.from_file(f.name)
                
                # Test getting current environment config
                env_config = config.get_current_environment_config()
                assert env_config is not None
                assert env_config.debug is False
                assert env_config.log_level == "WARNING"
                
                # Test changing environment
                config.environment = "development"
                dev_env_config = config.get_current_environment_config()
                assert dev_env_config is not None
                assert dev_env_config.debug is True
                assert dev_env_config.log_level == "DEBUG"
                
            finally:
                os.unlink(f.name)
    
    def test_complex_microservice_scenario(self):
        """Test complex microservice configuration scenario."""
        config_content = '''
app_name = "Complex Microservices"
environment = "production"

# Global defaults
[database]
url = "sqlite+aiosqlite:///./app.db"
echo = false

[security]
secret_key = "global-secret"

# Services
[services.api]
enabled = true
host = "0.0.0.0"
port = 8000
debug = false

[services.api.database]
url = "postgresql://api-db:5432/api"

[services.worker]
enabled = true
port = 8001

[services.worker.redis]
url = "redis://worker-redis:6379/0"

[services.notification]
enabled = false
port = 8002

# Environment configurations
[environments.development]
debug = true

[environments.development.services.api]
debug = true
workers = 1

[environments.development.services.worker]
enabled = false

[environments.production]
debug = false

[environments.production.services.api]
workers = 4

[environments.production.services.worker]
workers = 2

[environments.production.services.notification]
enabled = true
workers = 1
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            f.flush()
            
            try:
                config = Config.from_file(f.name)
                
                # Test API service in production
                api_config = config.get_service_config("api")
                assert api_config.enabled is True
                assert api_config.port == 8000
                assert api_config.debug is False  # From production env
                assert api_config.workers == 4     # From production env
                assert api_config.database.url == "postgresql://api-db:5432/api"
                assert api_config.security.secret_key == "global-secret"
                
                # Test worker service in production
                worker_config = config.get_service_config("worker")
                assert worker_config.enabled is True
                assert worker_config.port == 8001
                assert worker_config.workers == 2  # From production env
                assert worker_config.redis.url == "redis://worker-redis:6379/0"
                assert worker_config.database.url == "sqlite+aiosqlite:///./app.db"  # Inherited
                
                # Test notification service in production (enabled by env)
                notification_config = config.get_service_config("notification")
                assert notification_config.enabled is True  # Overridden by production env
                assert notification_config.port == 8002
                assert notification_config.workers == 1     # From production env
                
            finally:
                os.unlink(f.name)


@pytest.mark.integration  
class TestMicroserviceEnvironmentVariables:
    """Test microservice configuration with environment variables."""
    
    def test_service_environment_variables(self):
        """Test service configuration with environment variables."""
        config_content = '''
app_name = "ENV Test"
environment = "${ENVIRONMENT:development}"

[services.api]
enabled = true
port = "${API_PORT:8000}"
debug = "${API_DEBUG:true}"

[services.worker]
enabled = "${WORKER_ENABLED:false}"

[services.worker.redis]
url = "${WORKER_REDIS_URL:redis://localhost:6379/0}"
'''
        
        # Set environment variables
        test_env = {
            "ENVIRONMENT": "production",
            "API_PORT": "9000",
            "API_DEBUG": "false", 
            "WORKER_ENABLED": "true",
            "WORKER_REDIS_URL": "redis://custom-host:6379/2"
        }
        
        for key, value in test_env.items():
            os.environ[key] = value
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
                f.write(config_content)
                f.flush()
                
                try:
                    config = Config.from_file(f.name)
                    
                    assert config.environment == "production"
                    
                    api_config = config.get_service_config("api")
                    assert api_config.port == 9000
                    assert api_config.debug is False
                    
                    worker_config = config.get_service_config("worker")
                    assert worker_config.enabled is True
                    assert worker_config.redis.url == "redis://custom-host:6379/2"
                    
                finally:
                    os.unlink(f.name)
                    
        finally:
            # Cleanup environment variables
            for key in test_env:
                if key in os.environ:
                    del os.environ[key] 