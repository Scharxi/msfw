# MSFW Konfiguration mit Umgebungsvariablen-Interpolation

## Das Problem: "Doppelt gemoppelt"

Früher gab es zwei separate Konfigurationsmethoden:
- `config.toml` für statische Konfiguration
- `.env` Datei für Umgebungsvariablen

Das führte zu doppelter Konfiguration und Verwirrung über Prioritäten.

## Die Lösung: Eine config.toml mit Interpolation

Die neue MSFW-Konfiguration kombiniert das Beste aus beiden Welten:

### ✨ Hauptfeatures

1. **Eine zentrale `config.toml`** - kann ins Git committet werden
2. **Umgebungsvariablen-Interpolation** - `${VAR_NAME:default}` Syntax
3. **Umgebungsvariablen können überschreiben** - für deployment-spezifische Werte
4. **Git-freundlich** - keine Secrets in der Versionskontrolle

## Syntax

### Grundlegende Interpolation

```toml
# config/settings.toml
app_name = "${APP_NAME:My Application}"
debug = "${DEBUG:false}"
port = "${PORT:8000}"

[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"
echo = "${DATABASE_ECHO:false}"

[security]
secret_key = "${SECRET_KEY:dev-key-change-in-production}"
```

### Unterstützte Patterns

| Pattern | Beschreibung | Beispiel |
|---------|-------------|----------|
| `${VAR_NAME}` | Erforderliche Umgebungsvariable | `${SECRET_KEY}` |
| `${VAR_NAME:default}` | Optional mit Default-Wert | `${DEBUG:false}` |

## Verwendung

### 1. Einfache Konfiguration laden

```python
from msfw import load_config

# Lädt automatisch config/settings.toml oder settings.toml
config = load_config()
```

### 2. Spezifische Datei laden

```python
from msfw import Config

# Nur Interpolation aus der Datei
config = Config.from_file("path/to/config.toml")

# Datei + Umgebungsvariablen-Überschreibung  
config = Config.from_file_and_env("path/to/config.toml")
```

### 3. Prioritäten verstehen

1. **Umgebungsvariablen** (höchste Priorität)
2. **Interpolierte Werte** aus der TOML-Datei
3. **Default-Werte** in der Interpolation
4. **Framework-Defaults** (niedrigste Priorität)

## Beispiele

### Entwicklungsumgebung

```toml
# config/settings.toml
app_name = "${APP_NAME:My Dev App}"
debug = "${DEBUG:true}"

[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./dev.db}"

[security]
secret_key = "${SECRET_KEY:dev-secret-key}"
```

**Ohne Umgebungsvariablen:**
- `app_name` = "My Dev App"
- `debug` = true  
- `database.url` = "sqlite+aiosqlite:///./dev.db"
- `secret_key` = "dev-secret-key"

### Produktionsumgebung

**Dieselbe config.toml + Umgebungsvariablen:**

```bash
export APP_NAME="Production App"
export DEBUG="false"
export DATABASE_URL="postgresql://prod-server/myapp"
export SECRET_KEY="super-secure-production-key"
```

**Resultat:**
- `app_name` = "Production App" ← überschrieben
- `debug` = false ← überschrieben
- `database.url` = "postgresql://prod-server/myapp" ← überschrieben  
- `secret_key` = "super-secure-production-key" ← überschrieben

### Docker Deployment

```dockerfile
# Dockerfile
ENV DEBUG=false
ENV DATABASE_URL=postgresql://db:5432/app
ENV SECRET_KEY=production-secret
```

Die config.toml bleibt unverändert!

## Migration von alter Konfiguration

### Vorher (doppelt gemoppelt)

```toml
# config.toml
app_name = "My App"
debug = true
```

```bash
# .env  
DATABASE_URL=sqlite:///app.db
SECRET_KEY=secret
```

### Nachher (vereinheitlicht)

```toml
# config/settings.toml
app_name = "${APP_NAME:My App}"
debug = "${DEBUG:true}"

[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"

[security]
secret_key = "${SECRET_KEY:dev-secret-change-in-prod}"
```

```python
# main.py
from msfw import MSFWApplication, load_config

config = load_config()  # Lädt config + ENV automatisch
app = MSFWApplication(config)
```

## Best Practices

### 1. Git-freundliche Konfiguration

✅ **Committen:**
```toml
# Defaults und Struktur ins Git
secret_key = "${SECRET_KEY:change-me-in-production}"
debug = "${DEBUG:false}"
```

❌ **Nicht committen:**
```toml
# Nie echte Secrets ins Git!
secret_key = "real-production-secret"
```

### 2. Dokumentation der Umgebungsvariablen

```toml
# config/settings.toml

# Erforderliche Umgebungsvariablen für Produktion:
# - SECRET_KEY: Sicherer Schlüssel für JWT-Tokens
# - DATABASE_URL: PostgreSQL Verbindungsstring  
# - REDIS_URL: Redis Cache URL

app_name = "${APP_NAME:MSFW Application}"
debug = "${DEBUG:false}"

[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"

[security]
secret_key = "${SECRET_KEY}"  # Erforderlich!
```

### 3. .env.example für Entwickler

```bash
# .env.example (Optional für lokale Entwicklung)
# Kopiere diese Datei zu .env und passe die Werte an

# APP_NAME=My Custom App
# DEBUG=true
# DATABASE_URL=postgresql://localhost/myapp
# SECRET_KEY=your-dev-secret-key
```

## Vorteile

✅ **Keine doppelte Konfiguration mehr**  
✅ **Git-freundlich** - keine Secrets in der Versionskontrolle  
✅ **Deployment-flexibel** - Umgebungsvariablen überschreiben alles  
✅ **Entwicklerfreundlich** - sinnvolle Defaults in der TOML  
✅ **Container-ready** - perfekt für Docker/Kubernetes  
✅ **Dokumentiert** - Konfiguration ist selbsterklärend  

## Testing

```python
import os
from msfw import Config

def test_config_interpolation():
    # Setze Test-Umgebungsvariablen
    os.environ["TEST_SECRET"] = "test-secret"
    
    config = Config.from_file("test-config.toml")
    
    assert config.security.secret_key == "test-secret"
```

Die neue Konfiguration macht MSFW noch einfacher und flexibler! 🚀 