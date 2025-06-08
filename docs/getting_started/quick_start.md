# Quick Start

Lernen Sie MSFW in wenigen Minuten kennen! Diese Anleitung führt Sie durch die ersten Schritte mit dem Framework.

## 🎯 Was Sie lernen werden

- Ihre erste MSFW-Anwendung erstellen
- Module und Plugins verwenden
- Eine einfache API entwickeln
- Die Konfiguration verstehen

## 1. Erste Anwendung erstellen

### Minimale Anwendung

Erstellen Sie eine Datei `app.py`:

```python
from msfw import MSFWApplication, Config

# Konfiguration erstellen
config = Config()
config.app_name = "Meine erste MSFW App"
config.debug = True

# Anwendung erstellen
app = MSFWApplication(config)

# Health Check ist automatisch verfügbar
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Anwendung starten

```bash
python app.py
```

Ihre Anwendung ist jetzt verfügbar:
- **API**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Dokumentation**: http://localhost:8000/docs
- **Metrics**: http://localhost:8000/metrics

## 2. Ihr erstes Modul

Module enthalten die Geschäftslogik Ihrer Anwendung. Erstellen Sie `modules/user_module.py`:

```python
from msfw import Module
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

class User(BaseModel):
    id: int
    name: str
    email: str

class CreateUserRequest(BaseModel):
    name: str
    email: str

class UserModule(Module):
    def __init__(self):
        self.users: List[User] = []
        self.next_id = 1

    @property
    def name(self) -> str:
        return "user"

    def register_routes(self, router: APIRouter) -> None:
        @router.get("/users", response_model=List[User])
        async def list_users():
            """Alle Benutzer auflisten"""
            return self.users

        @router.post("/users", response_model=User)
        async def create_user(user_data: CreateUserRequest):
            """Neuen Benutzer erstellen"""
            user = User(
                id=self.next_id,
                name=user_data.name,
                email=user_data.email
            )
            self.users.append(user)
            self.next_id += 1
            return user

        @router.get("/users/{user_id}", response_model=User)
        async def get_user(user_id: int):
            """Benutzer nach ID abrufen"""
            for user in self.users:
                if user.id == user_id:
                    return user
            raise HTTPException(status_code=404, detail="User not found")
```

### Modul in der Anwendung registrieren

Aktualisieren Sie Ihre `app.py`:

```python
from msfw import MSFWApplication, Config
from modules.user_module import UserModule

config = Config()
config.app_name = "Benutzer API"

app = MSFWApplication(config)

# Modul registrieren
user_module = UserModule()
app.register_module(user_module)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 3. Konfiguration mit Datei

Erstellen Sie `config/settings.toml`:

```toml
# Anwendungskonfiguration
app_name = "${APP_NAME:MSFW Demo App}"
debug = "${DEBUG:true}"
environment = "${ENVIRONMENT:development}"

# Database-Konfiguration
[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"
echo = "${DATABASE_ECHO:false}"

# API-Konfiguration
[api]
title = "${API_TITLE:MSFW API}"
description = "Eine Demo-API mit MSFW"
version = "1.0.0"

# Sicherheit
[security]
secret_key = "${SECRET_KEY:dev-secret-key-change-in-production}"
access_token_expire_minutes = "${TOKEN_EXPIRE:30}"
```

### Konfiguration verwenden

```python
from msfw import MSFWApplication, load_config

# Konfiguration aus Datei laden
config = load_config("config/settings.toml")

app = MSFWApplication(config)
```

## 4. Database Integration

### Modell definieren

Erstellen Sie `models/user.py`:

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from msfw.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Async Database Service

```python
from msfw.core.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User

class UserService:
    @staticmethod
    async def create_user(session: AsyncSession, name: str, email: str) -> User:
        user = User(name=name, email=email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def get_users(session: AsyncSession) -> List[User]:
        result = await session.execute(select(User))
        return result.scalars().all()

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
        return await session.get(User, user_id)
```

### Modul mit Database

```python
from msfw import Module
from msfw.core.database import get_session
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

class DatabaseUserModule(Module):
    @property
    def name(self) -> str:
        return "database_user"

    def register_routes(self, router: APIRouter) -> None:
        @router.post("/users", response_model=UserResponse)
        async def create_user(
            user_data: CreateUserRequest,
            session: AsyncSession = Depends(get_session)
        ):
            return await UserService.create_user(
                session, user_data.name, user_data.email
            )

        @router.get("/users", response_model=List[UserResponse])
        async def list_users(session: AsyncSession = Depends(get_session)):
            return await UserService.get_users(session)
```

## 5. Plugin erstellen

Plugins erweitern die Funktionalität. Erstellen Sie `plugins/logging_plugin.py`:

```python
from msfw import Plugin, Config
import structlog

class LoggingPlugin(Plugin):
    @property
    def name(self) -> str:
        return "enhanced_logging"

    async def setup(self, config: Config) -> None:
        # Strukturiertes Logging konfigurieren
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Event-Hooks registrieren
        self.register_hook("app_startup", self.on_startup)
        self.register_hook("before_request", self.log_request)

    async def on_startup(self, **kwargs):
        logger = structlog.get_logger()
        logger.info("Enhanced Logging Plugin aktiviert")

    async def log_request(self, request, **kwargs):
        logger = structlog.get_logger()
        logger.info(
            "HTTP Request",
            method=request.method,
            url=str(request.url),
            client=request.client.host if request.client else None
        )
```

### Plugin registrieren

```python
from plugins.logging_plugin import LoggingPlugin

app = MSFWApplication(config)

# Plugin registrieren
logging_plugin = LoggingPlugin()
app.register_plugin(logging_plugin)
```

## 6. CLI-Integration

MSFW bietet ein mächtiges CLI-Tool:

```bash
# Neues Projekt erstellen
msfw init mein-projekt

# Modul erstellen
msfw create-module auth --description="Authentication module"

# Plugin erstellen
msfw create-plugin cache --description="Caching plugin"

# Development-Server starten
msfw run --reload

# Database-Migrationen
msfw db upgrade
```

## 7. Testing

Erstellen Sie `tests/test_user_module.py`:

```python
import pytest
from httpx import AsyncClient
from msfw import MSFWApplication, Config
from modules.user_module import UserModule

@pytest.fixture
async def app():
    config = Config()
    config.app_name = "Test App"
    config.testing = True
    
    app = MSFWApplication(config)
    app.register_module(UserModule())
    return app

@pytest.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_user(client):
    response = await client.post("/users", json={
        "name": "Test User",
        "email": "test@example.com"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_list_users(client):
    # Benutzer erstellen
    await client.post("/users", json={
        "name": "Test User",
        "email": "test@example.com"
    })
    
    # Benutzer auflisten
    response = await client.get("/users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 1
    assert users[0]["name"] == "Test User"
```

### Tests ausführen

```bash
# Alle Tests
pytest

# Mit Coverage
pytest --cov=msfw

# Bestimmte Tests
pytest tests/test_user_module.py -v
```

## 8. Environment Variables

Erstellen Sie `.env` für lokale Entwicklung:

```bash
# Anwendungskonfiguration
APP_NAME="Lokale Entwicklung"
DEBUG=true
ENVIRONMENT=development

# Database
DATABASE_URL="sqlite+aiosqlite:///./dev.db"
DATABASE_ECHO=true

# Sicherheit
SECRET_KEY="development-secret-key"
TOKEN_EXPIRE=60

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text
```

## 9. Vollständiges Beispiel

Hier ist eine vollständige Anwendung mit allem, was wir gelernt haben:

```python
# main.py
from msfw import MSFWApplication, load_config
from modules.user_module import DatabaseUserModule
from plugins.logging_plugin import LoggingPlugin

def create_app():
    # Konfiguration laden
    config = load_config()
    
    # Anwendung erstellen
    app = MSFWApplication(config)
    
    # Module registrieren
    app.register_module(DatabaseUserModule())
    
    # Plugins registrieren
    app.register_plugin(LoggingPlugin())
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

## 🚀 Nächste Schritte

Glückwunsch! Sie haben Ihre erste MSFW-Anwendung erstellt. Jetzt können Sie:

1. **[Grundkonzepte](basic_concepts.md)** vertiefen
2. **[Konfiguration](../user_guide/configuration.md)** erweitert nutzen
3. **[Module](../user_guide/modules.md)** komplexer gestalten
4. **[Plugins](../user_guide/plugins.md)** für erweiterte Funktionalität erstellen
5. **[Database](../user_guide/database.md)** für persistente Speicherung nutzen

```{tip}
Schauen Sie sich die [Beispiele](../examples/basic_service.md) an, um fortgeschrittene Patterns zu erlernen.
``` 