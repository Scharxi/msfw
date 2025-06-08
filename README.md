# MSFW - Modular Microservices Framework

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)

Ein hochgradig modulares und erweiterbares Framework zum Erstellen von Microservices mit FastAPI, Pydantic und SQLAlchemy.

## 🚀 Features

- **🧩 Modulare Architektur**: Plugin-basiertes System für maximale Erweiterbarkeit
- **🔧 Intelligente Konfiguration**: 
  - Environment Variable Interpolation (`${VAR:default}`)
  - Microservice-spezifische Einstellungen
  - Umgebungsspezifische Konfiguration (dev/prod)
  - Git-freundlich & Container-ready
- **🔍 Auto-Discovery**: Automatische Erkennung von Modulen und Plugins
- **🗄️ Database Integration**: Vollständige SQLAlchemy 2.0 Unterstützung mit Async
- **📊 Monitoring**: Eingebaute Prometheus-Metriken und Health-Checks
- **🔐 Security**: Sicherheits-Middleware und Best Practices
- **📝 Structured Logging**: Strukturiertes Logging mit Correlation IDs
- **⚡ Performance**: Optimiert für hohe Performance und Skalierbarität
- **🛠️ CLI Tools**: Kommandozeilen-Interface für Projektmanagement

## 📦 Installation

```bash
pip install msfw
```

Oder für die Entwicklung:

```bash
git clone https://github.com/yourusername/msfw.git
cd msfw
pip install -e .
```

## 🏃‍♂️ Quick Start

### 1. Framework testen

```bash
python main.py
```

### 2. API erkunden

- **Demo**: http://localhost:8000/demo
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs
- **Metrics**: http://localhost:8000/metrics

### 3. Neues Projekt erstellen

```bash
msfw init mein-service
cd mein-service
pip install -r requirements.txt
python main.py
```

## 🧩 Module erstellen

Module sind wiederverwendbare Komponenten mit eigenen Routes, Models und Logik:

```bash
msfw create-module user --description="User management module"
```

Beispiel Module-Implementierung:

```python
from msfw import Module
from fastapi import APIRouter
from sqlalchemy import Column, Integer, String
from msfw.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True)

class UserModule(Module):
    @property
    def name(self) -> str:
        return "user"
    
    def register_routes(self, router: APIRouter) -> None:
        @router.get("/users")
        async def list_users():
            return {"users": []}
        
        @router.post("/users")
        async def create_user(user_data: dict):
            return {"message": "User created", "data": user_data}
```

## 🔌 Plugins erstellen

Plugins erweitern die Funktionalität durch Event-Hooks:

```bash
msfw create-plugin auth --description="Authentication plugin"
```

Beispiel Plugin-Implementierung:

```python
from msfw import Plugin, Config

class AuthPlugin(Plugin):
    @property
    def name(self) -> str:
        return "auth"
    
    async def setup(self, config: Config) -> None:
        # Event-Hooks registrieren
        self.register_hook("app_startup", self.on_startup)
        self.register_hook("before_request", self.authenticate)
    
    async def on_startup(self, **kwargs):
        print("Auth plugin initialized")
    
    async def authenticate(self, request, **kwargs):
        # Authentifizierungslogik
        pass
```

## ⚙️ Konfiguration

MSFW verfügt über ein hochentwickeltes Konfigurationssystem, das:
- 🔧 **Environment Variable Interpolation** unterstützt
- 🏢 **Microservice-spezifische Konfiguration** ermöglicht
- 🌍 **Umgebungsspezifische Einstellungen** (dev/prod) verwaltet
- 📦 **Container-ready** für Docker/Kubernetes ist
- 🔒 **Git-freundlich** (keine Secrets im Repository)

### 1. Grundlegende Konfiguration

```python
from msfw import MSFWApplication, load_config

# Konfiguration aus Datei laden (empfohlen)
config = load_config()  # Lädt config/settings.toml

# Oder programmatisch erstellen
config = Config()
config.app_name = "Mein Service"
config.debug = True

# Anwendung erstellen
app = MSFWApplication(config)
```

### 2. Konfigurationsdatei (`config/settings.toml`)

```toml
# MSFW Konfiguration mit Environment Variable Interpolation
app_name = "${APP_NAME:Mein MSFW Service}"
debug = "${DEBUG:false}"
environment = "${ENVIRONMENT:development}"

# Globale Database-Einstellungen
[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"
echo = "${DATABASE_ECHO:false}"

# Security-Einstellungen
[security]
secret_key = "${SECRET_KEY:change-me-in-production}"
access_token_expire_minutes = "${TOKEN_EXPIRE:30}"

# Logging-Einstellungen
[logging]
level = "${LOG_LEVEL:INFO}"
format = "${LOG_FORMAT:text}"  # "text" oder "json"

# Monitoring-Einstellungen
[monitoring]
enabled = "${MONITORING_ENABLED:true}"
prometheus_enabled = "${PROMETHEUS_ENABLED:true}"
```

### 3. Environment Variable Interpolation

Verwenden Sie `${VAR_NAME}` für erforderliche und `${VAR_NAME:default}` für optionale Variablen:

```toml
# Erforderliche Environment Variable (Fehler wenn nicht gesetzt)
secret_key = "${SECRET_KEY}"

# Optionale Variable mit Standardwert
debug = "${DEBUG:false}"
database_url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"

# Komplexe URLs
redis_url = "${REDIS_HOST:localhost}:${REDIS_PORT:6379}/${REDIS_DB:0}"
```

### 4. Microservice-spezifische Konfiguration

Konfigurieren Sie jeden Microservice individuell:

```toml
# Service-spezifische Konfigurationen
[services.api]
enabled = true
host = "${API_HOST:0.0.0.0}"
port = "${API_PORT:8000}"
debug = "${API_DEBUG:true}"
workers = 1

# API-spezifische Database
[services.api.database]
url = "${API_DATABASE_URL:sqlite+aiosqlite:///./api.db}"

[services.worker]
enabled = "${WORKER_ENABLED:false}"
host = "${WORKER_HOST:0.0.0.0}"
port = "${WORKER_PORT:8001}"

# Worker-spezifische Redis-Konfiguration
[services.worker.redis]
url = "${WORKER_REDIS_URL:redis://localhost:6379/1}"

[services.notification]
enabled = "${NOTIFICATION_ENABLED:false}"
port = "${NOTIFICATION_PORT:8002}"
```

### 5. Umgebungsspezifische Konfiguration (Dev/Prod)

Definieren Sie unterschiedliche Einstellungen für verschiedene Umgebungen:

```toml
# Development Environment
[environments.development]
debug = true
log_level = "DEBUG"

[environments.development.database]
echo = true  # SQL-Queries ausgeben

[environments.development.services.api]
debug = true
workers = 1

[environments.development.services.worker]
enabled = false  # Worker in Development deaktiviert

# Production Environment
[environments.production]
debug = false
log_level = "WARNING"

[environments.production.database]
echo = false
pool_size = 20

[environments.production.services.api]
debug = false
workers = 4
host = "0.0.0.0"

[environments.production.services.worker]
enabled = true
workers = 2

# Production-spezifische Database/Redis URLs
[environments.production.services.api.database]
url = "${PROD_API_DATABASE_URL:postgresql://api-db:5432/api}"

[environments.production.services.worker.redis]
url = "${PROD_WORKER_REDIS_URL:redis://redis:6379/0}"
```

### 6. Service-Konfiguration in Code verwenden

```python
from msfw import MSFWApplication, load_config

# Konfiguration laden
config = load_config()

# Service-spezifische Konfiguration abrufen
api_config = config.get_service_config("api")
worker_config = config.get_service_config("worker")

# Verwenden
print(f"API läuft auf Port: {api_config.port}")
print(f"Worker aktiviert: {worker_config.enabled}")
print(f"API Database: {api_config.database.url}")

# Environment-Konfiguration
env_config = config.get_current_environment_config()
print(f"Environment: {config.environment}")
print(f"Debug-Modus: {env_config.debug}")
```

### 7. Deployment-Szenarien

#### Docker Deployment
```bash
# .env Datei für Docker
ENVIRONMENT=production
SECRET_KEY=super-secret-key
API_DATABASE_URL=postgresql://db:5432/api
WORKER_REDIS_URL=redis://redis:6379/0
API_WORKERS=4
```

#### Kubernetes Deployment
```yaml
# ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  ENVIRONMENT: "production"
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  API_WORKERS: "6"
  WORKER_ENABLED: "true"
  WORKER_WORKERS: "3"

# Secret
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
data:
  SECRET_KEY: <base64-encoded-secret>
  API_DATABASE_URL: <base64-encoded-db-url>
```

### 8. Prioritätsreihenfolge

Die Konfiguration wird in folgender Reihenfolge überschrieben:

1. **Environment Variables** (höchste Priorität)
2. **Umgebungsspezifische TOML-Werte** (`[environments.production]`)
3. **Service-spezifische TOML-Werte** (`[services.api]`)
4. **Globale TOML-Werte**
5. **Framework-Defaults** (niedrigste Priorität)

### 9. Best Practices

```toml
# ✅ Gut: Git-freundliche Konfiguration
secret_key = "${SECRET_KEY:dev-secret-only}"
database_url = "${DATABASE_URL:sqlite+aiosqlite:///./dev.db}"

# ✅ Gut: Umgebungsabhängige Defaults
debug = "${DEBUG:true}"  # Development
# ENVIRONMENT=production DEBUG=false  # Production

# ✅ Gut: Service-spezifische Ports
[services.api]
port = "${API_PORT:8000}"

[services.worker] 
port = "${WORKER_PORT:8001}"

# ❌ Vermeiden: Hardcoded Secrets
# secret_key = "hardcoded-secret"  # NIEMALS!
```

### 10. Migration von alter Konfiguration

```python
# Alt: Separate .env + config Dateien
config = Config()  # Liest nur .env

# Neu: Einheitliche settings.toml mit Environment-Support
config = load_config()  # Liest settings.toml + Environment Variables
```

### 💡 Konfiguration: Zusammenfassung

Das neue MSFW-Konfigurationssystem löst das **"doppelt gemoppelt"** Problem und bietet:

✅ **Eine zentrale Konfigurationsdatei** (`config/settings.toml`)  
✅ **Git-freundlich** - Keine Secrets im Repository  
✅ **Microservice-granular** - Jeder Service individuell konfigurierbar  
✅ **Umgebungsabhängig** - Automatische dev/prod Unterscheidung  
✅ **Container-ready** - Perfect für Docker/Kubernetes  
✅ **Environment Variable Support** - Flexibel überschreibbar  

**Beispiel: Ein Service in verschiedenen Umgebungen**
```bash
# Development
ENVIRONMENT=development API_DEBUG=true

# Production  
ENVIRONMENT=production API_WORKERS=4 API_DATABASE_URL=postgresql://...
```

## 🗄️ Database Integration

MSFW bietet vollständige SQLAlchemy 2.0 Unterstützung:

```python
from msfw.core.database import Base
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

class MyModel(Base):
    __tablename__ = "my_table"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

# In Modulen verwenden
async with self.context.database.session() as session:
    result = await session.execute(select(MyModel))
    items = result.scalars().all()
```

## 📊 Monitoring & Observability

### Health Checks

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "components": {
    "database": {"status": "healthy"},
    "modules": {"status": "healthy", "count": 3},
    "plugins": {"status": "healthy", "count": 2}
  }
}
```

### Prometheus Metriken

```bash
curl http://localhost:8000/metrics
```

Verfügbare Metriken:
- `http_requests_total` - Anzahl HTTP-Requests
- `http_request_duration_seconds` - Request-Dauer
- `http_request_size_bytes` - Request-Größe
- `http_response_size_bytes` - Response-Größe

## 🛠️ CLI Commands

```bash
# Projekt initialisieren
msfw init my-project

# Module erstellen
msfw create-module auth --description="Authentication module"

# Plugin erstellen  
msfw create-plugin cache --description="Caching plugin"

# Entwicklungsserver starten
msfw dev

# Produktionsserver starten
msfw run --workers 4

# Projektinfo anzeigen
msfw info

# Framework und Dependencies aktualisieren
msfw update --framework  # Nur Framework aktualisieren
msfw update --dependencies  # Nur Dependencies aktualisieren
msfw update --all  # Beides aktualisieren

# Datenbank-Migrationen verwalten
msfw migrate --message "Add user table"  # Neue Migration erstellen
msfw migrate --revision abc123  # Zu spezifischer Revision migrieren
msfw migrate --revision abc123 --downgrade  # Migration zurückrollen

# Tests ausführen
msfw test  # Alle Tests ausführen
msfw test --coverage  # Mit Coverage-Report
msfw test --unit  # Nur Unit-Tests
msfw test --integration  # Nur Integration-Tests
msfw test --e2e  # Nur End-to-End Tests
msfw test --verbose  # Ausführliche Ausgabe
```

## 📁 Framework Struktur

```
### ✅ Implementiert
- [x] **Microservice-spezifische Konfiguration** - Individuell konfigurierbare Services
- [x] **Environment Variable Interpolation** - Git-freundliche Konfiguration
- [x] **Umgebungsspezifische Einstellungen** - Dev/Prod Environment Support
- [x] **Container-ready Configuration** - Docker/Kubernetes Integration
- [x] **Enhanced CLI Commands** - Update, Migration und Testing Commands

### 🚧 In Entwicklung
- [ ] Authentication/Authorization Module
- [ ] Rate Limiting Plugin
- [ ] Caching Integration (Redis)
- [ ] Task Queue Integration (Celery)

### 📋 Geplant
- [X] API Versioning
- [ ] GraphQL Support
- [ ] WebSocket Support
- [ ] Performance Profiling Tools