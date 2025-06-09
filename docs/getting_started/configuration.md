# Configuration

MSFW features a sophisticated configuration system that eliminates the "double configuration" problem by combining file-based configuration with environment variable interpolation.

## The Problem

Traditional configuration systems often require:
- `config.toml` for static configuration
- `.env` file for environment variables
- Separate configuration for different environments

This leads to duplication and confusion about priority.

## The MSFW Solution

MSFW combines the best of both worlds:

- **Single configuration file** (`config/settings.toml`) - can be committed to Git
- **Environment variable interpolation** - `${VAR_NAME:default}` syntax  
- **Environment variables can override** - for deployment-specific values
- **Git-friendly** - no secrets in version control

## Environment Variable Interpolation

### Syntax

MSFW supports two interpolation patterns:

| Pattern | Description | Example |
|---------|-------------|---------|
| `${VAR_NAME}` | Required variable (fails if not set) | `${SECRET_KEY}` |
| `${VAR_NAME:default}` | Optional with default value | `${DEBUG:false}` |

### Basic Example

```toml
# config/settings.toml
app_name = "${APP_NAME:My MSFW Service}"
debug = "${DEBUG:false}"
port = "${PORT:8000}"

[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"
echo = "${DATABASE_ECHO:false}"

[security]
secret_key = "${SECRET_KEY}"  # Required - will fail if not set
access_token_expire_minutes = "${TOKEN_EXPIRE:30}"
```

### Complex Interpolation

Build complex values from multiple environment variables:

```toml
# Database connection from components
[database]
url = "postgresql://${DB_USER}:${DB_PASS}@${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME}"

# Redis URL with defaults
[redis]
url = "${REDIS_HOST:localhost}:${REDIS_PORT:6379}/${REDIS_DB:0}"

# Service discovery
[services.api]
url = "${API_PROTOCOL:http}://${API_HOST:localhost}:${API_PORT:8000}"

# File paths
[logging]
log_file = "${LOG_DIR:/var/log}/${APP_NAME:msfw}/app.log"
```

## Configuration Priority

MSFW follows a clear priority order:

1. **Environment Variables** (highest priority)
2. **Interpolated values** from TOML file
3. **Default values** in interpolation syntax
4. **Framework defaults** (lowest priority)

### Example

```toml
# config/settings.toml
debug = "${DEBUG:true}"  # Default: true
```

```bash
# Environment variable overrides TOML default
export DEBUG=false
```

Result: `debug = false` (environment variable wins)

## Loading Configuration

### Automatic Discovery

```python
from msfw import load_config

# Looks for config/settings.toml or settings.toml
config = load_config()
```

### Specific File

```python
from msfw import Config

# Only interpolation from file
config = Config.from_file("path/to/config.toml")

# File + environment variable overrides
config = Config.from_file_and_env("path/to/config.toml")
```

### Programmatic Configuration

```python
from msfw import Config

config = Config()
config.app_name = "My Service"
config.debug = True
config.database.url = "postgresql://localhost/mydb"
```

## Microservice Configuration

MSFW supports configuration for multiple services in one file:

```toml
# Global defaults apply to all services
debug = "${DEBUG:false}"

[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"
pool_size = "${DB_POOL_SIZE:10}"

# Service-specific configurations
[services.api]
enabled = true
host = "${API_HOST:0.0.0.0}"
port = "${API_PORT:8000}"
workers = "${API_WORKERS:4}"
debug = "${API_DEBUG:true}"

# API-specific database (overrides global)
[services.api.database]
url = "${API_DATABASE_URL:postgresql://db:5432/api}"
pool_size = "${API_DB_POOL_SIZE:20}"

[services.worker]
enabled = "${WORKER_ENABLED:false}"
port = "${WORKER_PORT:8001}"

[services.worker.redis]
url = "${WORKER_REDIS_URL:redis://localhost:6379/1}"

# Background task worker
[services.scheduler]
enabled = "${SCHEDULER_ENABLED:false}"
interval = "${SCHEDULER_INTERVAL:60}"

[services.scheduler.database]
url = "${SCHEDULER_DATABASE_URL:postgresql://db:5432/scheduler}"
```

### Accessing Service Configuration

```python
from msfw import load_config

config = load_config()

# Get service-specific configuration with fallbacks
api_config = config.get_service_config("api")
worker_config = config.get_service_config("worker")

print(f"API Database: {api_config.database.url}")
print(f"Worker Redis: {worker_config.redis.url}")
```

## Environment-Specific Configuration

Define configurations for different environments:

```toml
# Environment selection
environment = "${ENVIRONMENT:development}"

# Environment-specific configurations
[environments.development]
debug = true
log_level = "DEBUG"

[environments.development.database]
echo = true
pool_size = 5

[environments.development.services.api]
debug = true
workers = 1

[environments.production]
debug = false
log_level = "WARNING"

[environments.production.database]
echo = false
pool_size = 20

[environments.production.services.api]
debug = false
workers = 4

[environments.production.services.api.database]
url = "${PROD_API_DATABASE_URL:postgresql://prod-db:5432/api}"

[environments.staging]
debug = false
log_level = "INFO"

[environments.staging.database]
url = "${STAGING_DATABASE_URL:postgresql://staging-db:5432/myapp}"
```

### Using Environment Configuration

```python
# Current environment config
env_config = config.get_current_environment_config()

# Service config with environment overrides
api_config = config.get_service_config("api")
```

## Dynamic Configuration Access

```python
# Dot notation access
debug_mode = config.get("debug", False)
database_pool = config.get("database.pool_size", 10)
api_workers = config.get("services.api.workers", 1)

# Setting values dynamically
config.set("custom.feature_flag", True)
config.set("cache.ttl", 300)

# Update multiple values
config.update(
    debug=False,
    workers=8,
    cache_enabled=True
)
```

## Security Best Practices

### Required Secrets

Mark sensitive configuration as required:

```toml
[security]
secret_key = "${SECRET_KEY}"  # No default - must be set
jwt_algorithm = "${JWT_ALGORITHM:HS256}"

[database]
password = "${DB_PASSWORD}"  # Required
host = "${DB_HOST:localhost}"  # Optional with default

[external_apis]
payment_api_key = "${PAYMENT_API_KEY}"  # Required
notification_token = "${NOTIFICATION_TOKEN}"  # Required
```

### Git-Safe Configuration

Only commit the TOML file with interpolation patterns:

```toml
# ✅ Safe to commit
secret_key = "${SECRET_KEY}"
database_url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"

# ❌ Never commit actual secrets
# secret_key = "actual-secret-key-here"
```

Set actual secrets via environment variables:

```bash
# .env (not committed to Git)
export SECRET_KEY="your-actual-secret-key"
export DATABASE_URL="postgresql://user:pass@db:5432/prod"
```

## Container Deployment

MSFW configuration works seamlessly with containers:

```dockerfile
# Dockerfile
FROM python:3.11-slim
COPY config/settings.toml /app/config/
# No secrets in the image
```

```yaml
# docker-compose.yml
services:
  api:
    build: .
    environment:
      - SECRET_KEY=production-secret
      - DATABASE_URL=postgresql://db:5432/myapp
      - DEBUG=false
      - API_WORKERS=4
```

```yaml
# kubernetes.yml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: api
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: secret-key
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: database-url
```

## Advanced Configuration

### Type Validation

Configuration values are automatically validated:

```python
# Port must be between 1-65535
config.port = 8000  # ✅ Valid

# Boolean conversion
config.debug = "true"   # Becomes True
config.debug = "false"  # Becomes False

# List/Dict support
config.allowed_hosts = ["localhost", "127.0.0.1"]
config.features = {"caching": True, "monitoring": False}
```

### Configuration Validation

```python
from msfw import Config
from pydantic import ValidationError

try:
    config = Config.from_file("config.toml")
except ValidationError as e:
    print(f"Configuration error: {e}")
    # Handle configuration errors
```

### CLI Configuration Management

MSFW includes CLI tools for configuration:

```bash
# Validate configuration
msfw config validate

# Show interpolated values
msfw config show

# Check environment variables
msfw config env-check

# Test different environments
msfw config validate --environment=production
```

This configuration system provides a powerful, flexible, and secure way to manage settings across different environments while maintaining Git-friendly practices. 