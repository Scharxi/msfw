# Grundkonzepte

Verstehen Sie die fundamentalen Konzepte von MSFW und wie sie zusammenarbeiten, um eine leistungsstarke Microservice-Architektur zu schaffen.

## 🏗️ Architektur-Überblick

MSFW folgt einer modularen, plugin-basierten Architektur, die maximale Flexibilität und Erweiterbarkeit bietet.

```{mermaid}
graph TB
    App[MSFWApplication]
    App --> Config[Configuration]
    App --> Router[API Router]
    App --> DB[Database]
    App --> Middleware[Middleware Stack]
    
    Router --> M1[Module 1]
    Router --> M2[Module 2]
    Router --> MN[Module N]
    
    App --> P1[Plugin 1]
    App --> P2[Plugin 2]
    App --> PN[Plugin N]
    
    Config --> ENV[Environment Variables]
    Config --> Files[Config Files]
    
    DB --> Models[SQLAlchemy Models]
    DB --> Sessions[Async Sessions]
```

## 🧩 Module

Module sind die Bausteine Ihrer Anwendung. Sie enthalten:

- **Business Logic**: Kernfunktionalität Ihrer Anwendung
- **API Routes**: REST-Endpoints für externe Kommunikation
- **Data Models**: Strukturierte Datenrepräsentation
- **Services**: Wiederverwendbare Geschäftslogik

### Modul-Anatomie

```python
from msfw import Module
from fastapi import APIRouter
from pydantic import BaseModel

class ItemModule(Module):
    @property
    def name(self) -> str:
        return "item"  # Eindeutiger Modulname
    
    @property
    def prefix(self) -> str:
        return "/api/v1"  # URL-Präfix (optional)
    
    def register_routes(self, router: APIRouter) -> None:
        # Routes definieren
        pass
    
    async def startup(self) -> None:
        # Initialisierungslogik (optional)
        pass
    
    async def shutdown(self) -> None:
        # Cleanup-Logik (optional)
        pass
```

### Modul-Registrierung

```python
from msfw import MSFWApplication

app = MSFWApplication(config)

# Einzelnes Modul
app.register_module(ItemModule())

# Mehrere Module
app.register_modules([
    UserModule(),
    OrderModule(),
    ProductModule()
])

# Auto-Discovery
app.discover_modules("modules/")  # Lädt alle Module aus dem Verzeichnis
```

## 🔌 Plugins

Plugins erweitern die Funktionalität Ihrer Anwendung durch Event-Hooks und Middleware.

### Plugin-Typen

1. **Middleware-Plugins**: HTTP-Request/Response-Verarbeitung
2. **Event-Plugins**: Lifecycle-Events (startup, shutdown)
3. **Service-Plugins**: Zusätzliche Services (Caching, Logging)
4. **Integration-Plugins**: Externe Systeme (Databases, APIs)

### Plugin-Beispiel

```python
from msfw import Plugin, Config

class CachePlugin(Plugin):
    @property
    def name(self) -> str:
        return "cache"
    
    async def setup(self, config: Config) -> None:
        # Plugin-spezifische Konfiguration
        self.cache_backend = config.get("cache.backend", "redis")
        
        # Event-Hooks registrieren
        self.register_hook("app_startup", self.init_cache)
        self.register_hook("before_request", self.check_cache)
        self.register_hook("after_request", self.update_cache)
    
    async def init_cache(self, **kwargs):
        # Cache-Backend initialisieren
        pass
```

### Verfügbare Event-Hooks

- `app_startup`: Anwendungsstart
- `app_shutdown`: Anwendungsende
- `before_request`: Vor HTTP-Request
- `after_request`: Nach HTTP-Request
- `module_loaded`: Nach Modul-Registrierung
- `plugin_loaded`: Nach Plugin-Registrierung

## ⚙️ Konfiguration

MSFW bietet ein flexibles Konfigurationssystem mit:

### Environment Variable Interpolation

```toml
# config/settings.toml
app_name = "${APP_NAME:Default App Name}"
database_url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"
debug = "${DEBUG:false}"
```

### Hierarchische Konfiguration

```python
from msfw import Config

# Standardwerte
config = Config()
config.app_name = "My App"

# Aus Datei laden (überschreibt Standardwerte)
config.load_from_file("config/settings.toml")

# Environment Variables (überschreibt alles)
config.load_from_env()
```

### Konfigurationsvererbung

```toml
# config/base.toml
[database]
echo = false
pool_size = 10

# config/development.toml
[database]
url = "sqlite+aiosqlite:///./dev.db"
echo = true  # Überschreibt base.toml

# config/production.toml
[database]
url = "${DATABASE_URL}"  # Muss gesetzt sein
pool_size = 50  # Überschreibt base.toml
```

## 🗄️ Database Integration

MSFW nutzt SQLAlchemy 2.0 mit Async-Unterstützung.

### Modell-Definition

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from msfw.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Beziehungen
    orders = relationship("Order", back_populates="user")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total = Column(Integer)  # Cents
    
    # Beziehungen
    user = relationship("User", back_populates="orders")
```

### Async Database Sessions

```python
from msfw.core.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends

async def get_users(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User))
    return result.scalars().all()

async def create_user(user_data: UserCreate, session: AsyncSession = Depends(get_session)):
    user = User(**user_data.dict())
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
```

## 🔒 Sicherheit

MSFW bietet integrierte Sicherheitsfeatures:

### Authentication & Authorization

```python
from msfw.middleware.auth import JWTAuthMiddleware, require_auth
from fastapi import Depends

# JWT-Middleware
app.add_middleware(JWTAuthMiddleware, secret_key=config.secret_key)

# Route-Level-Schutz
@router.get("/protected")
async def protected_endpoint(current_user = Depends(require_auth)):
    return {"user": current_user}

# Role-basierte Berechtigung
@router.get("/admin")
async def admin_endpoint(current_user = Depends(require_auth(roles=["admin"]))):
    return {"message": "Admin access"}
```

### CORS & Security Headers

```python
from msfw.middleware.security import SecurityMiddleware

app.add_middleware(SecurityMiddleware, {
    "cors_origins": ["https://myapp.com"],
    "security_headers": True,
    "rate_limiting": True
})
```

## 📊 Monitoring & Observability

### Health Checks

Automatische Health-Check-Endpoints:

- `/health`: Grundlegende Systemgesundheit
- `/health/ready`: Bereitschaftsstatus
- `/health/live`: Lebendigkeitsstatus

```python
from msfw.core.health import HealthCheck

class DatabaseHealthCheck(HealthCheck):
    async def check(self) -> bool:
        try:
            # Database-Verbindung prüfen
            async with get_session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception:
            return False

# Health Check registrieren
app.register_health_check("database", DatabaseHealthCheck())
```

### Prometheus Metrics

Automatische Metriken:

- HTTP-Request-Metriken
- Response-Zeit-Histogramme
- Fehlerrate-Counter
- Anwendungsspezifische Metriken

```python
from msfw.core.metrics import metrics

# Custom Metric
user_registrations = metrics.counter(
    "user_registrations_total",
    "Total number of user registrations"
)

@router.post("/register")
async def register_user(user_data: UserCreate):
    user = await create_user(user_data)
    user_registrations.inc()  # Metric erhöhen
    return user
```

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

@router.post("/orders")
async def create_order(order_data: OrderCreate, current_user = Depends(require_auth)):
    logger.info(
        "Order creation started",
        user_id=current_user.id,
        order_total=order_data.total
    )
    
    try:
        order = await create_order(order_data, current_user.id)
        logger.info(
            "Order created successfully",
            order_id=order.id,
            user_id=current_user.id
        )
        return order
    except Exception as e:
        logger.error(
            "Order creation failed",
            user_id=current_user.id,
            error=str(e)
        )
        raise
```

## 🚀 Deployment-Konzepte

### Container-Ready

MSFW-Anwendungen sind für Container optimiert:

```dockerfile
FROM python:3.13-slim

# Non-root user
RUN useradd --create-home --shell /bin/bash app
USER app
WORKDIR /home/app

# Dependencies
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Application
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "main.py"]
```

### 12-Factor App Compliance

MSFW folgt den [12-Factor App](https://12factor.net/) Prinzipien:

1. **Codebase**: Ein Repository, mehrere Deployments
2. **Dependencies**: Explizite Abhängigkeitserklärung
3. **Config**: Konfiguration in Environment Variables
4. **Backing Services**: Services als angehängte Ressourcen
5. **Build/Release/Run**: Strikte Trennung der Phasen
6. **Processes**: Anwendung als stateless Prozesse
7. **Port Binding**: Services über Port-Binding exportieren
8. **Concurrency**: Skalierung über Prozessmodell
9. **Disposability**: Schneller Start und graceful Shutdown
10. **Dev/Prod Parity**: Entwicklung und Produktion ähnlich halten
11. **Logs**: Logs als Event-Streams behandeln
12. **Admin Processes**: Admin-Tasks als einmalige Prozesse

## 🔄 Lifecycle Management

```python
from msfw import MSFWApplication

class MyApp(MSFWApplication):
    async def startup(self):
        # Anwendungsstart
        await super().startup()
        await self.init_external_services()
    
    async def shutdown(self):
        # Graceful Shutdown
        await self.cleanup_resources()
        await super().shutdown()
    
    async def init_external_services(self):
        # Redis, Cache, etc.
        pass
    
    async def cleanup_resources(self):
        # Verbindungen schließen
        pass
```

## 📈 Performance & Skalierung

### Async/Await Pattern

```python
import asyncio
from typing import List

# Parallele Verarbeitung
async def process_orders(order_ids: List[int]) -> List[Order]:
    tasks = [process_single_order(order_id) for order_id in order_ids]
    return await asyncio.gather(*tasks)

# Connection Pooling
async def get_user_data(user_id: int) -> dict:
    async with get_session() as session:
        # Session automatisch zurückgegeben
        user = await session.get(User, user_id)
        return user.to_dict()
```

### Caching Strategien

```python
from msfw.plugins.cache import cache

@cache(ttl=300)  # 5 Minuten Cache
async def get_expensive_data(user_id: int) -> dict:
    # Aufwändige Berechnung
    return await compute_user_analytics(user_id)

# Cache-Invalidierung
@router.post("/users/{user_id}/update")
async def update_user(user_id: int, data: UserUpdate):
    user = await update_user_data(user_id, data)
    await cache.invalidate(f"get_expensive_data:{user_id}")
    return user
```

## 🧪 Testing-Strategien

### Unit Tests

```python
import pytest
from msfw import Config
from modules.user_module import UserModule

@pytest.fixture
def user_module():
    return UserModule()

def test_user_module_name(user_module):
    assert user_module.name == "user"

@pytest.mark.asyncio
async def test_user_creation(user_module):
    # Mock dependencies
    result = await user_module.create_user("test@example.com")
    assert result.email == "test@example.com"
```

### Integration Tests

```python
import pytest
from httpx import AsyncClient
from msfw import MSFWApplication, Config

@pytest.fixture
async def test_app():
    config = Config()
    config.testing = True
    config.database_url = "sqlite+aiosqlite:///:memory:"
    
    app = MSFWApplication(config)
    app.register_module(UserModule())
    return app

@pytest.mark.asyncio
async def test_user_api(test_app):
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post("/users", json={
            "email": "test@example.com",
            "name": "Test User"
        })
        assert response.status_code == 201
        assert response.json()["email"] == "test@example.com"
```

## 📚 Nächste Schritte

Jetzt da Sie die Grundkonzepte verstehen, können Sie:

1. **[Konfiguration](../user_guide/configuration.md)** - Erweiterte Konfigurationsmöglichkeiten
2. **[Module](../user_guide/modules.md)** - Detaillierte Modul-Entwicklung
3. **[Plugins](../user_guide/plugins.md)** - Plugin-System beherrschen
4. **[Database](../user_guide/database.md)** - Database-Integration vertiefen
5. **[Beispiele](../examples/basic_service.md)** - Praktische Anwendungen erkunden

```{tip}
Die Konzepte bauen aufeinander auf. Beginnen Sie mit einfachen Modulen und erweitern Sie schrittweise die Funktionalität.
``` 