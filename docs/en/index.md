# MSFW - Modular Microservices Framework

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)

A highly modular and extensible framework for building microservices with FastAPI, Pydantic, and SQLAlchemy.

## Welcome to MSFW Documentation

MSFW (Modular Microservices Framework) is a powerful, plugin-based framework for developing scalable microservices. It provides a comprehensive solution for modern application architectures with built-in support for monitoring, security, and advanced configuration capabilities.

```{note}
This documentation is also available in [German](../index.md).
```

## 🚀 Key Features

- **🧩 Modular Architecture**: Plugin-based system for maximum extensibility
- **🔧 Intelligent Configuration**: Environment variable interpolation and environment-specific settings
- **🔍 Auto-Discovery**: Automatic detection of modules and plugins
- **🗄️ Database Integration**: Full SQLAlchemy 2.0 support with Async
- **📊 Monitoring**: Built-in Prometheus metrics and health checks
- **🔐 Security**: Security middleware and best practices
- **📝 Structured Logging**: Structured logging with correlation IDs
- **⚡ Performance**: Optimized for high performance and scalability
- **🛠️ CLI Tools**: Command-line interface for project management

## 📚 Table of Contents

```{toctree}
:maxdepth: 2
:caption: Getting Started

getting_started/installation
getting_started/quick_start
getting_started/basic_concepts
```

```{toctree}
:maxdepth: 2
:caption: User Guide

user_guide/configuration
user_guide/modules
user_guide/plugins
user_guide/database
user_guide/monitoring
user_guide/security
user_guide/cli
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api/core
api/modules
api/plugins
api/middleware
api/cli
```

```{toctree}
:maxdepth: 2
:caption: Developer Guide

developer_guide/architecture
developer_guide/contributing
developer_guide/testing
developer_guide/deployment
```

```{toctree}
:maxdepth: 2
:caption: Examples

examples/basic_service
examples/advanced_patterns
examples/microservice_communication
examples/typed_sdk
```

```{toctree}
:maxdepth: 1
:caption: Additional Information

changelog
license
glossary
```

## 📖 Language Versions

- [Deutsch](../index.md)
- **English** (current language)

## Search and Index

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search` 