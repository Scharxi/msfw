# MSFW Documentation Setup Guide

Diese Anleitung zeigt Ihnen, wie Sie die umfassende Sphinx-Dokumentation für MSFW erstellen und verwenden.

## 🎯 Was wurde erstellt

Eine vollständige, zweisprachige Sphinx-Dokumentation mit:

- **Deutsch** als Hauptsprache
- **English** als Zweitsprache
- Markdown-Format mit MyST Parser
- Automatische API-Dokumentation
- GitHub Actions CI/CD
- Responsive Design mit RTD Theme

## 📁 Dokumentationsstruktur

```
docs/
├── conf.py                    # Sphinx-Konfiguration
├── index.md                   # Deutsche Hauptseite
├── en/
│   ├── index.md              # Englische Hauptseite
│   └── getting_started/      # Englische Erste-Schritte
│       └── installation.md
├── getting_started/          # Deutsche Erste-Schritte
│   ├── installation.md      # Installationsanleitung
│   ├── quick_start.md       # Schnellstart-Guide
│   └── basic_concepts.md    # Grundkonzepte
├── user_guide/              # Benutzerhandbuch (zu erstellen)
├── api/                     # API-Referenz (auto-generiert)
├── developer_guide/         # Entwicklerhandbuch (zu erstellen)
├── examples/                # Beispiele (zu erstellen)
├── _static/
│   └── custom.css          # Custom Styling
├── Makefile                 # Build-System
├── README.md               # Dokumentations-README
└── .github/workflows/docs.yml  # CI/CD Pipeline
```

## 🚀 Erste Schritte

### 1. Abhängigkeiten installieren

Wenn Sie noch keine Sphinx-Abhängigkeiten haben:

```bash
cd docs
make install-deps
```

Oder manuell:

```bash
pip install sphinx sphinx-intl sphinx-autodoc-typehints sphinx-rtd-theme myst-parser sphinx-copybutton
```

### 2. Dokumentation erstellen

```bash
cd docs

# Alle Sprachen
make html

# Nur Deutsch
make html-de

# Nur Englisch
make html-en
```

### 3. Lokal testen

```bash
# Development-Server mit Auto-Reload
make dev
# Verfügbar unter: http://localhost:8000

# Oder statischer Server
make serve
# Verfügbar unter: http://localhost:8080
```

## 🌍 Mehrsprachigkeit

### Unterstützte Sprachen

- **Deutsch** (`de`) - Hauptsprache
- **English** (`en`) - Zweitsprache

### Neue Inhalte hinzufügen

1. **Deutsche Version erstellen** (z.B. `user_guide/configuration.md`)
2. **Englische Version erstellen** (`en/user_guide/configuration.md`)
3. **Zu Navigation hinzufügen** (beide `index.md` Dateien)

### Übersetzungen verwalten

```bash
# Übersetzungsdateien generieren
make gettext

# Übersetzungen aktualisieren
make update-translations
```

## 📝 Content-Richtlinien

### Markdown mit MyST

```markdown
# Hauptüberschrift

## Unterüberschrift

```{note}
Dies ist eine Notiz.
```

```{tip}
Dies ist ein Tipp.
```

```{warning}
Dies ist eine Warnung.
```

```{danger}
Dies ist eine kritische Warnung.
```

# Code-Blöcke
```python
from msfw import MSFWApplication

app = MSFWApplication()
```

# Interne Verlinkung
[Andere Seite](other_page.md)

# Cross-References
{ref}`label-name`

# Bilder
![Alt Text](path/to/image.png)
```

### Schreibstil

**Deutsch:**
- Sie-Form verwenden
- Technische Begriffe erklären
- Vollständige Beispiele
- Freundlicher, professioneller Ton

**English:**
- Clear, concise language
- Active voice preferred
- Complete examples
- Professional tone

## 🏗️ Build-Targets

```bash
# Hauptbuilds
make html              # Alle Sprachen + Redirect
make html-de           # Nur Deutsch
make html-en           # Nur Englisch

# Development
make dev               # Auto-reload Server
make serve             # Statischer Server

# Quality Assurance
make lint              # Link-Checking
make stats             # Dokumentationsstatistiken

# API-Dokumentation
make autodoc           # API-Docs generieren

# Export-Formate
make pdf               # PDF (benötigt LaTeX)
make epub              # EPUB

# Wartung
make clean-all         # Alles löschen
make update-translations  # Übersetzungen aktualisieren

# Deployment
make deploy            # GitHub Pages
```

## 🔧 Erweiterte Konfiguration

### Custom CSS

Styling in `docs/_static/custom.css`:

```css
/* Custom Admonitions */
.admonition.tip {
    border-left-color: #28a745;
}

/* Language Selector */
.language-selector {
    position: fixed;
    top: 10px;
    right: 10px;
}
```

### Sphinx-Konfiguration

Hauptkonfiguration in `docs/conf.py`:

```python
# Sprache ändern
language = 'de'  # oder 'en'

# Extensions hinzufügen
extensions = [
    'sphinx.ext.autodoc',
    'myst_parser',
    # ...
]

# Theme-Optionen
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': True,
}
```

## 🚀 Automatisierung

### GitHub Actions

Die Dokumentation wird automatisch erstellt bei:

- Push auf `main` oder `develop`
- Pull Requests auf `main`
- Änderungen in `docs/` oder `msfw/`

### CI/CD Features

- ✅ **Build-Tests** für beide Sprachen
- ✅ **Link-Checking** 
- ✅ **Automatisches Deployment** auf GitHub Pages
- ✅ **PR-Kommentare** mit Build-Status
- ✅ **PDF-Generation** (optional)

### GitHub Pages Setup

1. **Repository Settings** → **Pages**
2. **Source**: GitHub Actions
3. Die Dokumentation ist verfügbar unter:
   - Deutsch: `https://username.github.io/msfw/de/`
   - English: `https://username.github.io/msfw/en/`

## 📚 Nächste Schritte

### Zu erstellende Seiten

1. **Benutzerhandbuch** (`user_guide/`)
   - `configuration.md` - Erweiterte Konfiguration
   - `modules.md` - Modul-Entwicklung
   - `plugins.md` - Plugin-System
   - `database.md` - Database-Integration
   - `monitoring.md` - Monitoring & Metriken
   - `security.md` - Sicherheitsfeatures
   - `cli.md` - CLI-Befehle

2. **API-Referenz** (`api/`)
   - `core.md` - Kern-APIs
   - `modules.md` - Modul-APIs
   - `plugins.md` - Plugin-APIs
   - `middleware.md` - Middleware-APIs
   - `cli.md` - CLI-APIs

3. **Entwicklerhandbuch** (`developer_guide/`)
   - `architecture.md` - Architektur-Überblick
   - `contributing.md` - Beitragsrichtlinien
   - `testing.md` - Test-Strategien
   - `deployment.md` - Deployment-Guide

4. **Beispiele** (`examples/`)
   - `basic_service.md` - Grundlegender Service
   - `advanced_patterns.md` - Erweiterte Patterns
   - `microservice_communication.md` - Service-Kommunikation
   - `typed_sdk.md` - Typed SDK

5. **Weitere Seiten**
   - `changelog.md` - Versionshistorie
   - `license.md` - Lizenzinformationen
   - `glossary.md` - Glossar

### Template für neue Seiten

```markdown
# Seitentitel

Kurze Beschreibung der Seite.

## Übersicht

Was behandelt diese Seite?

## Beispiel

```python
# Vollständiges Beispiel
from msfw import MSFWApplication

app = MSFWApplication()
```

## Best Practices

- Tipp 1
- Tipp 2

## Weitere Informationen

- [Verwandte Seite](other_page.md)
- [API-Referenz](../api/module.md)

```{tip}
Hilfreicher Tipp für den Benutzer.
```
```

## 🛠️ Wartung

### Regelmäßige Aufgaben

```bash
# Links überprüfen
make lint

# Übersetzungen aktualisieren
make update-translations

# API-Dokumentation neu generieren
make autodoc

# Build testen
make html
```

### Deployment überwachen

- GitHub Actions Status in Repository-Tabs
- GitHub Pages Deployment-Status
- Dokumentation unter: `https://username.github.io/msfw/`

### Updates

Bei MSFW-Updates:

1. `make autodoc` - API-Docs aktualisieren
2. Entsprechende Seiten anpassen
3. `make html` - Build testen
4. Git Push - Automatisches Deployment

## 📞 Support

Bei Problemen:

1. **GitHub Issues** - Bugs und Feature-Requests
2. **GitHub Discussions** - Fragen und Ideen  
3. **Documentation README** - Lokale Hilfe (`docs/README.md`)

---

**Glückwunsch!** 🎉 Sie haben jetzt eine professionelle, zweisprachige Dokumentation für MSFW. Die Struktur ist vollständig vorbereitet und das Build-System funktioniert automatisch.

Beginnen Sie mit dem Ausfüllen der Inhalte in der gewünschten Reihenfolge und nutzen Sie die vorbereiteten Templates als Ausgangspunkt. 