# MSFW Documentation

Willkommen zur MSFW (Modular Microservices Framework) Dokumentation! Diese Dokumentation ist sowohl auf Deutsch als auch auf Englisch verfügbar.

## 📚 Verfügbare Sprachen

- **Deutsch** (Standardsprache) - Umfassende Dokumentation auf Deutsch
- **English** - Complete documentation in English

## 🏗️ Build-Anweisungen

### Voraussetzungen

```bash
# Python 3.13+ erforderlich
python --version

# Sphinx und Abhängigkeiten installieren
make install-deps
# oder manuell:
pip install sphinx sphinx-intl sphinx-autodoc-typehints sphinx-rtd-theme myst-parser sphinx-copybutton
```

### Dokumentation erstellen

```bash
# Alle Sprachen erstellen
make html

# Nur deutsche Dokumentation
make html-de

# Nur englische Dokumentation  
make html-en

# Development-Server mit Auto-Reload
make dev
```

### Lokalen Server starten

```bash
# Dokumentation lokal bereitstellen
make serve
# Verfügbar unter: http://localhost:8080
```

## 📁 Projekt-Struktur

```
docs/
├── conf.py                 # Sphinx-Konfiguration
├── index.md               # Deutsche Hauptseite
├── en/
│   ├── index.md          # Englische Hauptseite
│   └── getting_started/   # Englische Erste-Schritte-Seiten
├── getting_started/       # Deutsche Erste-Schritte-Seiten
│   ├── installation.md
│   ├── quick_start.md
│   └── basic_concepts.md
├── user_guide/           # Benutzerhandbuch
├── api/                  # API-Referenz
├── developer_guide/      # Entwicklerhandbuch
├── examples/             # Beispiele
├── _static/              # Statische Dateien
│   └── custom.css       # Custom CSS
├── _templates/           # Template-Überschreibungen
├── locales/              # Übersetzungsdateien
├── Makefile             # Build-System
└── README.md            # Diese Datei
```

## 🌍 Internationalisierung

Diese Dokumentation nutzt Sphinx's i18n-Funktionen für mehrsprachige Unterstützung.

### Übersetzungen aktualisieren

```bash
# .pot-Dateien generieren
make gettext

# Übersetzungsdateien aktualisieren
make update-translations
```

### Neue Sprache hinzufügen

1. Sprache zu `LANGUAGES` in `Makefile` hinzufügen
2. Übersetzungsverzeichnis erstellen: `mkdir -p locales/{lang}/LC_MESSAGES`
3. Übersetzungsdateien generieren: `make update-translations`
4. Build-Targets für neue Sprache hinzufügen

## 📖 Inhaltsrichtlinien

### Markdown-Format

Wir verwenden MyST Parser für erweiterte Markdown-Funktionen:

```markdown
# Überschrift

## Unterüberschrift

```{note}
Dies ist eine Notiz-Admonition.
```

```{tip}
Dies ist ein Tipp.
```

```{warning}
Dies ist eine Warnung.
```

# Code-Blöcke mit Syntax-Highlighting
```python
from msfw import MSFWApplication

app = MSFWApplication()
```

# Interne Links
[Verweis auf andere Seite](other_page.md)

# Cross-References
{ref}`label-name`
```

### Schreibstil

**Deutsch:**
- Freundlicher, professioneller Ton
- "Sie" als Anrede verwenden
- Technische Begriffe bei erster Verwendung erklären
- Konkrete Beispiele verwenden

**English:**
- Clear, professional tone
- Use active voice when possible
- Explain technical terms on first use
- Provide concrete examples

### Code-Beispiele

- Vollständige, lauffähige Beispiele bevorzugen
- Kommentare in der jeweiligen Sprache
- Fehlerbehandlung zeigen
- Best Practices demonstrieren

## 🚀 Deployment

### GitHub Pages

```bash
# Auf GitHub Pages deployen
make deploy
```

### Docker

```dockerfile
FROM nginx:alpine
COPY docs/_build/html /usr/share/nginx/html
EXPOSE 80
```

### Statische Hosting-Services

Die gebaute Dokumentation in `_build/html/` kann auf jedem statischen Hosting-Service bereitgestellt werden:

- Netlify
- Vercel  
- GitHub Pages
- AWS S3
- Azure Static Web Apps

## 🔧 Erweiterte Features

### API-Dokumentation automatisch generieren

```bash
# API-Docs aus Docstrings generieren
make autodoc
```

### PDF-Export

```bash
# PDF für alle Sprachen (benötigt LaTeX)
make pdf

# Nur deutsche PDF
make pdf-de
```

### EPUB-Export

```bash
# EPUB für alle Sprachen
make epub
```

### Link-Checking

```bash
# Alle Links überprüfen
make lint
```

## 🧪 Testing

### Dokumentation testen

```bash
# Syntax-Checks
sphinx-build -W -b html docs/ docs/_build/test/

# Link-Checks
make lint

# Alle Sprachen testen
for lang in de en; do
    sphinx-build -W -b html -D language=$lang docs/ docs/_build/test/$lang/
done
```

### CI/CD Integration

Beispiel GitHub Actions Workflow:

```yaml
name: Documentation

on: [push, pull_request]

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          cd docs
          make install-deps
      
      - name: Build documentation
        run: |
          cd docs
          make html
      
      - name: Deploy to GitHub Pages
        if: github.ref == 'refs/heads/main'
        run: |
          cd docs
          make deploy
```

## 🤝 Beitragen

### Neue Seiten hinzufügen

1. Markdown-Datei erstellen
2. Zur entsprechenden `toctree` in `index.md` hinzufügen
3. Englische Version in `en/` erstellen
4. Dokumentation neu bauen und testen

### Bestehende Seiten bearbeiten

1. Entsprechende `.md`-Datei bearbeiten
2. Änderungen in beiden Sprachen vornehmen
3. Build testen: `make html`
4. Links überprüfen: `make lint`

### Feedback und Issues

- GitHub Issues für Bugs und Feature-Requests
- Discussions für Fragen und Verbesserungsvorschläge
- Pull Requests für direkte Beiträge

## 📊 Statistiken

```bash
# Dokumentationsstatistiken anzeigen
make stats
```

## 📞 Support

Bei Fragen zur Dokumentation:

- GitHub Issues: [Repository Issues](https://github.com/yourusername/msfw/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/msfw/discussions)
- E-Mail: docs@msfw.dev

---

**Hinweis:** Diese Dokumentation wird kontinuierlich erweitert und verbessert. Feedback und Beiträge sind immer willkommen! 