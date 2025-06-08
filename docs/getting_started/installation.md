# Installation

Dieses Kapitel führt Sie durch die verschiedenen Installationsmöglichkeiten von MSFW.

## Systemanforderungen

- **Python**: 3.13 oder höher
- **Betriebssystem**: Windows, macOS, Linux
- **RAM**: Mindestens 512 MB (empfohlen: 2 GB oder mehr)
- **Festplatte**: Mindestens 100 MB freier Speicherplatz

## Abhängigkeiten

MSFW basiert auf folgenden Kernbibliotheken:

- **FastAPI** 0.104+ - Moderne, schnelle Web-Framework
- **Pydantic** 2.5+ - Datenvalidierung mit Python-Typen
- **SQLAlchemy** 2.0+ - SQL-Toolkit und ORM
- **Uvicorn** - ASGI-Server für Produktionsumgebungen

## Installation über pip

### Grundinstallation

```bash
pip install msfw
```

### Mit entwicklungsabhängigkeiten

```bash
pip install msfw[dev]
```

### Mit allen optionalen Abhängigkeiten

```bash
pip install msfw[all]
```

## Installation über uv (empfohlen)

[uv](https://github.com/astral-sh/uv) ist ein ultraschneller Python-Paketmanager:

```bash
# uv installieren (falls nicht vorhanden)
curl -LsSf https://astral.sh/uv/install.sh | sh

# MSFW installieren
uv add msfw

# Mit Entwicklungsabhängigkeiten
uv add --group dev msfw
```

## Installation für Entwicklung

### Repository klonen

```bash
git clone https://github.com/yourusername/msfw.git
cd msfw
```

### Mit uv (empfohlen)

```bash
# Entwicklungsumgebung einrichten
uv sync

# Virtuelle Umgebung aktivieren
source .venv/bin/activate  # Linux/macOS
# oder
.venv\Scripts\activate     # Windows
```

### Mit pip und virtualenv

```bash
# Virtuelle Umgebung erstellen
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# oder
.venv\Scripts\activate     # Windows

# Abhängigkeiten installieren
pip install -e ".[dev]"
```

## Docker-Installation

### Offizielles Docker-Image

```bash
# MSFW-Container starten
docker run -p 8000:8000 msfw/msfw:latest
```

### Eigenes Docker-Image erstellen

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# System-Abhängigkeiten
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendung kopieren
COPY . .

# Port freigeben
EXPOSE 8000

# Anwendung starten
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Image erstellen
docker build -t mein-msfw-app .

# Container starten
docker run -p 8000:8000 mein-msfw-app
```

## Virtueller Environment Setup

### Warum virtuelle Umgebungen?

Virtuelle Umgebungen isolieren Projektabhängigkeiten und verhindern Konflikte:

- **Isolation**: Jedes Projekt hat seine eigenen Abhängigkeiten
- **Reproduzierbarkeit**: Konsistente Umgebungen über verschiedene Systeme
- **Sicherheit**: Verhindert versehentliche Systemänderungen

### Mit venv (Standard)

```bash
# Virtuelle Umgebung erstellen
python -m venv msfw-env

# Aktivieren
source msfw-env/bin/activate  # Linux/macOS
msfw-env\Scripts\activate     # Windows

# MSFW installieren
pip install msfw

# Deaktivieren
deactivate
```

### Mit conda

```bash
# Umgebung erstellen
conda create -n msfw python=3.13

# Aktivieren
conda activate msfw

# MSFW installieren
pip install msfw

# Deaktivieren
conda deactivate
```

## Installation verifizieren

### Grundlegende Überprüfung

```bash
# MSFW-Version anzeigen
python -c "import msfw; print(msfw.__version__)"

# CLI-Tool testen
msfw --help
```

### Vollständiger Test

```python
from msfw import MSFWApplication, Config

# Einfache Anwendung erstellen
config = Config()
config.app_name = "Test App"

app = MSFWApplication(config)

print("✅ MSFW erfolgreich installiert!")
```

## Häufige Installationsprobleme

### Problem: `ModuleNotFoundError`

**Lösung**: Virtuelle Umgebung aktivieren oder MSFW neu installieren:

```bash
pip install --force-reinstall msfw
```

### Problem: Berechtigungsfehler auf Windows

**Lösung**: PowerShell als Administrator ausführen oder `--user` Flag verwenden:

```bash
pip install --user msfw
```

### Problem: Kompilierungsfehler bei C-Abhängigkeiten

**Lösung**: Build-Tools installieren:

```bash
# Windows
pip install setuptools wheel

# Ubuntu/Debian
sudo apt-get install build-essential python3-dev

# macOS
xcode-select --install
```

### Problem: SSL-Zertifikatsfehler

**Lösung**: Vertrauenswürdige Hosts konfigurieren:

```bash
pip install --trusted-host pypi.org --trusted-host pypi.python.org msfw
```

## Nächste Schritte

Nach der erfolgreichen Installation können Sie mit dem [Quick Start](quick_start.md) beginnen oder die [Grundkonzepte](basic_concepts.md) kennenlernen.

```{tip}
Für Produktionsumgebungen empfehlen wir die Verwendung von Docker oder einem professionellen Deployment-Tool wie Kubernetes.
``` 