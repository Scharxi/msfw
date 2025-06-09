# MSFW Documentation

Welcome to MSFW (Modular Microservices Framework) - a highly modular and extensible framework for building microservices with FastAPI, Pydantic, and SQLAlchemy.

## 🚀 Key Features

MSFW provides a comprehensive framework for building production-ready microservices:

### 🧩 Modular Architecture
- **Plugin-based system** for maximum extensibility
- **Auto-discovery** of modules and plugins from directories
- **Module system** with lifecycle management (startup/shutdown)
- **Event hooks** for application lifecycle events

### 🔧 Advanced Configuration
- **Environment Variable Interpolation** with `${VAR:default}` syntax
- **Microservice-specific configuration** for multi-service deployments
- **Environment-specific settings** (development/production)
- **Git-friendly & Container-ready** configuration management

### 🌐 API Versioning & OpenAPI
- **Built-in API versioning** with decorator-based version management
- **Automatic OpenAPI/Swagger documentation** generation
- **Version compatibility** and evolution tracking
- **Content negotiation** for different API versions

### 🔄 Service Communication
- **Service SDK** for inter-service communication
- **Service Registry** for service discovery
- **Circuit breaker** patterns for resilience
- **Typed service interfaces** with automatic validation

### 🗄️ Database & Data Management
- **SQLAlchemy 2.0** with full async support
- **Database manager** for multiple database connections
- **Migration support** and schema management
- **Connection pooling** and health checks

### 📊 Monitoring & Observability
- **Built-in Prometheus metrics** at `/metrics`
- **Health checks** with component-level status
- **Structured logging** with correlation IDs
- **Performance monitoring** and request tracking

### 🔐 Security & Middleware
- **Security middleware** with best practices
- **CORS configuration** for cross-origin requests
- **Authentication/Authorization** integration
- **Request/Response middleware** pipeline

## Quick Start

```bash
# Install MSFW
pip install msfw

# Test the framework
python main.py

# Explore the demo API
open http://localhost:8000/docs
```

## Getting Started

```{toctree}
:maxdepth: 2

getting_started/installation
getting_started/quick_start
getting_started/basic_concepts
```

## What Makes MSFW Special?

Unlike other frameworks, MSFW is designed specifically for microservices architecture with:

- **Real auto-discovery**: Modules and plugins are automatically found and loaded
- **Advanced configuration**: Environment variable interpolation and microservice-specific configs
- **Built-in versioning**: API versions are first-class citizens with automatic routing
- **Service communication**: Built-in SDK for service-to-service communication
- **Production-ready**: Monitoring, health checks, and observability out of the box

## Architecture Overview

MSFW applications are built from these core components:

- **MSFWApplication**: The main application class that orchestrates everything
- **Modules**: Self-contained business logic units with routes and models
- **Plugins**: Extensions that add functionality through event hooks
- **Configuration**: Flexible config system with environment interpolation
- **Service SDK**: For communication between microservices
- **Database Manager**: SQLAlchemy-based data persistence layer

## Next Steps

1. Follow the [Quick Start](getting_started/quick_start.md) guide
2. Learn about [Basic Concepts](getting_started/basic_concepts.md)
3. Explore the demo application in `main.py`
4. Check out the CLI tools with `msfw --help`

The documentation covers everything from basic usage to advanced patterns for building scalable microservice architectures. 