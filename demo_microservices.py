#!/usr/bin/env python3
"""
MSFW Microservice Configuration Demo
====================================

Dieses Skript demonstriert das neue Microservice-Konfigurationssystem:

1. Service-spezifische Konfiguration 
2. Umgebungsspezifische Überschreibungen (dev/prod)
3. Flexible Umgebungsvariablen pro Service
4. Zentrale vs. service-spezifische Einstellungen

Jeder Microservice kann individuell konfiguriert werden!
"""

import os
import tempfile
from pathlib import Path

from msfw import Config, load_config


def demo_basic_microservice_config():
    """Demonstriert grundlegende Microservice-Konfiguration."""
    print("🚀 Demo: Grundlegende Microservice-Konfiguration")
    print("=" * 60)
    
    config_content = '''
# Globale Einstellungen (für alle Services)
app_name = "Microservices Demo"
environment = "development"

[database]
url = "sqlite+aiosqlite:///./global.db"
echo = false

[security]
secret_key = "global-secret"

# Service-spezifische Konfigurationen
[services.api]
enabled = true
host = "0.0.0.0"
port = 8000
debug = true

[services.api.database]
url = "sqlite+aiosqlite:///./api.db"

[services.worker]
enabled = true
host = "0.0.0.0"
port = 8001
debug = false

[services.worker.redis]
url = "redis://localhost:6379/1"

[services.notification]
enabled = false
port = 8002
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(config_content)
        f.flush()
        
        try:
            config = Config.from_file(f.name)
            
            print("🔍 Globale Konfiguration:")
            print(f"  app_name: {config.app_name}")
            print(f"  environment: {config.environment}")
            print(f"  global database: {config.database.url}")
            print()
            
            # Service-spezifische Konfigurationen
            print("🔍 API Service Konfiguration:")
            api_config = config.get_service_config("api")
            print(f"  enabled: {api_config.enabled}")
            print(f"  host: {api_config.host}")
            print(f"  port: {api_config.port}")
            print(f"  debug: {api_config.debug}")
            print(f"  database: {api_config.database.url}")
            print(f"  security (inherited): {api_config.security.secret_key}")
            print()
            
            print("🔍 Worker Service Konfiguration:")
            worker_config = config.get_service_config("worker")
            print(f"  enabled: {worker_config.enabled}")
            print(f"  port: {worker_config.port}")
            print(f"  debug: {worker_config.debug}")
            print(f"  redis: {worker_config.redis.url}")
            print(f"  database (inherited): {worker_config.database.url}")  # Fällt auf global zurück
            print()
            
            print("🔍 Notification Service Konfiguration:")
            notification_config = config.get_service_config("notification")
            print(f"  enabled: {notification_config.enabled}")
            print(f"  port: {notification_config.port}")
            print()
            
        finally:
            os.unlink(f.name)


def demo_environment_specific_config():
    """Demonstriert umgebungsspezifische Konfiguration."""
    print("🌍 Demo: Umgebungsspezifische Konfiguration (Dev vs Prod)")
    print("=" * 60)
    
    config_content = '''
app_name = "Multi-Environment App"
environment = "development"  # Wird durch ENV überschrieben

# Globale Defaults
[database]
url = "sqlite+aiosqlite:///./app.db"
echo = false

[security]
secret_key = "dev-secret"

# Services
[services.api]
enabled = true
port = 8000
debug = true
workers = 1

[services.worker]
enabled = false
port = 8001

# Development Environment
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

# Production Environment  
[environments.production]
debug = false
log_level = "WARNING"

[environments.production.database]
echo = false
pool_size = 20

[environments.production.security]
secret_key = "prod-secret-key"

[environments.production.services.api]
debug = false
workers = 4
port = 8000

[environments.production.services.worker]
enabled = true
workers = 2
port = 8001

[environments.production.services.api.database]
url = "postgresql://prod-db:5432/api"

[environments.production.services.worker.redis]
url = "redis://prod-redis:6379/0"
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(config_content)
        f.flush()
        
        try:
            print("📝 Development Environment:")
            # Development config
            dev_config = Config.from_file(f.name)
            dev_config.environment = "development"
            
            api_dev = dev_config.get_service_config("api")
            worker_dev = dev_config.get_service_config("worker")
            
            print(f"  Environment: {dev_config.environment}")
            print(f"  Global debug: {dev_config.get_current_environment_config().debug}")
            print(f"  API: port={api_dev.port}, debug={api_dev.debug}, workers={api_dev.workers}")
            print(f"  Worker: enabled={worker_dev.enabled}")
            print(f"  Database echo: {api_dev.database.echo}")
            print()
            
            print("🏭 Production Environment:")
            # Production config
            prod_config = Config.from_file(f.name)
            prod_config.environment = "production"
            
            api_prod = prod_config.get_service_config("api")
            worker_prod = prod_config.get_service_config("worker")
            
            print(f"  Environment: {prod_config.environment}")
            print(f"  Global debug: {prod_config.get_current_environment_config().debug}")
            print(f"  API: port={api_prod.port}, debug={api_prod.debug}, workers={api_prod.workers}")
            print(f"  Worker: enabled={worker_prod.enabled}, workers={worker_prod.workers}")
            print(f"  API Database: {api_prod.database.url}")
            print(f"  Worker Redis: {worker_prod.redis.url}")
            print(f"  Database echo: {api_prod.database.echo}")
            print()
            
        finally:
            os.unlink(f.name)


def demo_environment_variables():
    """Demonstriert Umgebungsvariablen für Microservices."""
    print("🔧 Demo: Umgebungsvariablen für Microservices")
    print("=" * 60)
    
    # Setze verschiedene Umgebungsvariablen
    os.environ["ENVIRONMENT"] = "production"
    os.environ["API_PORT"] = "9000"
    os.environ["API_DEBUG"] = "false"
    os.environ["WORKER_ENABLED"] = "true"
    os.environ["WORKER_REDIS_URL"] = "redis://custom-redis:6379/2"
    
    config_content = '''
app_name = "ENV Demo"
environment = "${ENVIRONMENT:development}"

[services.api]
enabled = true
port = "${API_PORT:8000}"
debug = "${API_DEBUG:true}"

[services.worker]
enabled = "${WORKER_ENABLED:false}"
port = 8001

[services.worker.redis]
url = "${WORKER_REDIS_URL:redis://localhost:6379/0}"

[environments.development]
debug = true

[environments.production] 
debug = false

[environments.production.services.api]
workers = 4

[environments.production.services.worker]
workers = 2
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(config_content)
        f.flush()
        
        try:
            config = Config.from_file(f.name)
            
            print(f"🔍 Environment: {config.environment} (aus ENV)")
            
            api_config = config.get_service_config("api")
            worker_config = config.get_service_config("worker")
            
            print(f"🔍 API Service:")
            print(f"  port: {api_config.port} (aus ENV)")
            print(f"  debug: {api_config.debug} (aus ENV)")
            print(f"  workers: {api_config.workers} (aus production env)")
            print()
            
            print(f"🔍 Worker Service:")
            print(f"  enabled: {worker_config.enabled} (aus ENV)")
            print(f"  workers: {worker_config.workers} (aus production env)")
            print(f"  redis: {worker_config.redis.url} (aus ENV)")
            print()
            
        finally:
            os.unlink(f.name)
            # Cleanup
            for key in ["ENVIRONMENT", "API_PORT", "API_DEBUG", "WORKER_ENABLED", "WORKER_REDIS_URL"]:
                if key in os.environ:
                    del os.environ[key]


def demo_service_deployment():
    """Demonstriert Deployment-Szenarien."""
    print("🚢 Demo: Deployment-Szenarien")
    print("=" * 60)
    
    config_content = '''
app_name = "Deployment Demo"
environment = "${ENVIRONMENT:development}"

# Globale Produktions-Database
[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"

[security]
secret_key = "${SECRET_KEY:dev-secret}"

# Services
[services.api]
enabled = true
host = "0.0.0.0"
port = "${API_PORT:8000}"

[services.worker] 
enabled = "${WORKER_ENABLED:false}"
host = "0.0.0.0"
port = "${WORKER_PORT:8001}"

[services.notification]
enabled = "${NOTIFICATION_ENABLED:false}"
port = "${NOTIFICATION_PORT:8002}"

# Production Environment
[environments.production]
debug = false

[environments.production.services.api]
workers = "${API_WORKERS:4}"

[environments.production.services.worker]  
workers = "${WORKER_WORKERS:2}"

[environments.production.services.api.database]
url = "${API_DATABASE_URL:postgresql://api-db:5432/api}"

[environments.production.services.worker.redis]
url = "${WORKER_REDIS_URL:redis://worker-redis:6379/0}"

[environments.production.services.notification.redis]
url = "${NOTIFICATION_REDIS_URL:redis://notification-redis:6379/1}"
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(config_content)
        f.flush()
        
        try:
            print("🐳 Kubernetes Deployment Scenario:")
            
            # Simuliere Kubernetes Environment Variables
            k8s_env = {
                "ENVIRONMENT": "production",
                "SECRET_KEY": "k8s-secret-from-vault",
                "API_PORT": "8000",
                "API_WORKERS": "6",
                "API_DATABASE_URL": "postgresql://api-db.default.svc.cluster.local:5432/api",
                "WORKER_ENABLED": "true",
                "WORKER_PORT": "8001", 
                "WORKER_WORKERS": "3",
                "WORKER_REDIS_URL": "redis://redis.default.svc.cluster.local:6379/0",
                "NOTIFICATION_ENABLED": "true",
                "NOTIFICATION_PORT": "8002",
                "NOTIFICATION_REDIS_URL": "redis://redis.default.svc.cluster.local:6379/1"
            }
            
            # Setze K8s Environment
            for key, value in k8s_env.items():
                os.environ[key] = value
            
            config = Config.from_file(f.name)
            
            print(f"  Environment: {config.environment}")
            print(f"  Secret Key: {config.security.secret_key}")
            print()
            
            for service_name in ["api", "worker", "notification"]:
                service_config = config.get_service_config(service_name)
                print(f"  {service_name.upper()} Service:")
                print(f"    enabled: {service_config.enabled}")
                print(f"    port: {service_config.port}")
                if hasattr(service_config, 'workers'):
                    print(f"    workers: {service_config.workers}")
                if service_config.database:
                    print(f"    database: {service_config.database.url}")
                if service_config.redis:
                    print(f"    redis: {service_config.redis.url}")
                print()
            
            # Cleanup
            for key in k8s_env:
                if key in os.environ:
                    del os.environ[key]
                    
        finally:
            os.unlink(f.name)


def main():
    """Führt alle Microservice-Demos aus."""
    print("🎯 MSFW Microservice Configuration")
    print("=" * 70)
    print("✨ Service-spezifische Konfiguration!")
    print("✨ Dev/Prod Umgebungen!")
    print("✨ Flexible Umgebungsvariablen!")
    print("✨ Deployment-ready!")
    print()
    
    demo_basic_microservice_config()
    print()
    
    demo_environment_specific_config()
    print()
    
    demo_environment_variables()
    print()
    
    demo_service_deployment()
    
    print("🎉 Fazit:")
    print("   • Jeder Service kann individuell konfiguriert werden")
    print("   • Dev/Prod Umgebungen werden automatisch verwaltet")
    print("   • Umgebungsvariablen pro Service möglich")
    print("   • Perfect für Container-Deployments (Docker/K8s)")
    print("   • Eine config.toml für alle Services!")


if __name__ == "__main__":
    main() 