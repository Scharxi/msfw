# MSFW - Modular Microservices Framework

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)

Ein hochgradig modulares und erweiterbares Framework zum Erstellen von Microservices mit FastAPI, Pydantic und SQLAlchemy.

## Willkommen zur MSFW-Dokumentation

MSFW (Modular Microservices Framework) ist ein leistungsstarkes, plugin-basiertes Framework für die Entwicklung skalierbarer Microservices. Es bietet eine umfassende Lösung für moderne Anwendungsarchitekturen mit eingebauter Unterstützung für Monitoring, Sicherheit und erweiterte Konfigurationsmöglichkeiten.

```{note}
Diese Dokumentation ist auch in [English](en/index.md) verfügbar.
```

## 🚀 Hauptfunktionen

- **🧩 Modulare Architektur**: Plugin-basiertes System für maximale Erweiterbarkeit
- **🔧 Intelligente Konfiguration**: Environment Variable Interpolation und umgebungsspezifische Einstellungen
- **🔍 Auto-Discovery**: Automatische Erkennung von Modulen und Plugins
- **🗄️ Database Integration**: Vollständige SQLAlchemy 2.0 Unterstützung mit Async
- **📊 Monitoring**: Eingebaute Prometheus-Metriken und Health-Checks
- **🔐 Security**: Sicherheits-Middleware und Best Practices
- **📝 Structured Logging**: Strukturiertes Logging mit Correlation IDs
- **⚡ Performance**: Optimiert für hohe Performance und Skalierbarkeit
- **🛠️ CLI Tools**: Kommandozeilen-Interface für Projektmanagement

## 📚 Inhaltsverzeichnis

```{toctree}
:maxdepth: 2
:caption: Erste Schritte

getting_started/installation
getting_started/quick_start
getting_started/basic_concepts
```

```{toctree}
:maxdepth: 2
:caption: Benutzerhandbuch

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
:caption: API-Referenz

api/core
api/modules
api/plugins
api/middleware
api/cli
```

```{toctree}
:maxdepth: 2
:caption: Entwicklerhandbuch

developer_guide/architecture
developer_guide/contributing
developer_guide/testing
developer_guide/deployment
```

```{toctree}
:maxdepth: 2
:caption: Beispiele

examples/basic_service
examples/advanced_patterns
examples/microservice_communication
examples/typed_sdk
```

```{toctree}
:maxdepth: 1
:caption: Weitere Informationen

changelog
license
glossary
```

## 📖 Sprachversionen

- **Deutsch** (aktuelle Sprache)
- [English](en/index.md)

## Suche und Index

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search` 