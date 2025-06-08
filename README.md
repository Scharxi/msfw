# MSFW - Modular Microservices Framework

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)

Ein hochgradig modulares und erweiterbares Framework zum Erstellen von Microservices mit FastAPI, Pydantic und SQLAlchemy.

## 🚀 Features

- **🧩 Modulare Architektur**: Plugin-basiertes System für maximale Erweiterbarkeit
- **🔧 Konfigurierbar**: Umfassende Konfigurationsmöglichkeiten mit Pydantic und Dynaconf
- **🔍 Auto-Discovery**: Automatische Erkennung von Modulen und Plugins
- **🗄️ Database Integration**: Vollständige SQLAlchemy 2.0 Unterstützung mit Async
- **📊 Monitoring**: Eingebaute Prometheus-Metriken und Health-Checks
- **🔐 Security**: Sicherheits-Middleware und Best Practices
- **📝 Structured Logging**: Strukturiertes Logging mit Correlation IDs
- **⚡ Performance**: Optimiert für hohe Performance und Skalierbarkeit
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

MSFW nutzt ein mächtiges Konfigurationssystem mit Umgebungsvariablen-Unterstützung:

```python
from msfw import MSFWApplication, Config

# Basis-Konfiguration
config = Config()
config.app_name = "Mein Service"
config.debug = True

# Database-Konfiguration
config.database.url = "postgresql+asyncpg://user:pass@localhost/db"
config.database.echo = True

# Security-Konfiguration
config.security.secret_key = "your-secret-key"
config.security.access_token_expire_minutes = 60

# Anwendung erstellen
app = MSFWApplication(config)
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
```

## 📁 Framework Struktur

```
msfw/
├── main.py              # Demo-Anwendung
├── msfw/                # Framework Code
│   ├── __init__.py      # Haupt-Exports
│   ├── core/            # Kern-Komponenten
│   │   ├── application.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── module.py
│   │   └── plugin.py
│   ├── middleware/      # Middleware-Komponenten
│   │   ├── logging.py
│   │   ├── monitoring.py
│   │   └── security.py
│   ├── decorators.py    # Decorator-System
│   └── cli.py          # CLI-Interface
├── examples/           # Beispiele
│   ├── basic_module.py
│   └── logging_plugin.py
└── pyproject.toml      # Projekt-Konfiguration
```

## 🏗️ Architektur-Prinzipien

### 1. Modularität
Jede Funktionalität ist in separaten, wiederverwendbaren Modulen organisiert.

### 2. Erweiterbarkeit
Plugin-System ermöglicht es, das Framework ohne Änderung des Kern-Codes zu erweitern.

### 3. Konfigurierbarkeit
Alles kann über Konfigurationsdateien, Umgebungsvariablen oder Code konfiguriert werden.

### 4. Observability
Eingebaute Metriken, Logging und Health-Checks für Produktions-Readiness.

### 5. Developer Experience
CLI-Tools und automatische Erkennung für einfache Entwicklung.

## 🤝 Contributing

Beiträge sind willkommen! Das Framework ist so konzipiert, dass es einfach zu erweitern ist:

1. Fork das Repository
2. Erstellen Sie einen Feature Branch
3. Implementieren Sie Ihre Änderungen
4. Fügen Sie Tests hinzu
5. Öffnen Sie einen Pull Request

## 📚 Beispiele

Das `examples/` Verzeichnis enthält vollständige Beispiele:

- **[Basic Module](examples/basic_module.py)** - CRUD-Operationen mit SQLAlchemy
- **[Logging Plugin](examples/logging_plugin.py)** - Event-basiertes Logging

## 🎯 Roadmap

- [ ] Authentication/Authorization Module
- [ ] Rate Limiting Plugin
- [ ] Caching Integration (Redis)
- [ ] Task Queue Integration (Celery)
- [ ] API Versioning
- [ ] GraphQL Support
- [ ] WebSocket Support
- [ ] Docker Integration
- [ ] Kubernetes Deployment Templates

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert.

---

**MSFW** - Baue modulare Microservices mit Leichtigkeit! 🚀

