#!/usr/bin/env python3
"""
Demonstration der neuen MSFW Konfiguration mit Umgebungsvariablen-Interpolation
================================================================================

Dieses Skript zeigt, wie das neue Konfigurationssystem das "doppelt gemoppelt" Problem löst:

1. Eine zentrale config.toml Datei (kann ins Git committet werden)  
2. Umgebungsvariablen-Interpolation in der TOML Datei: ${VAR_NAME:default}
3. Zusätzliche Umgebungsvariablen können TOML-Werte überschreiben

Keine separate .env Datei mehr nötig!
"""

import os
import tempfile
from pathlib import Path

from msfw import Config, load_config


def demo_basic_interpolation():
    """Demonstriert grundlegende Umgebungsvariablen-Interpolation."""
    print("🔧 Demo: Grundlegende Umgebungsvariablen-Interpolation")
    print("=" * 60)
    
    # Setze einige Umgebungsvariablen
    os.environ["DEMO_SECRET"] = "super-secret-key"
    os.environ["DEMO_DEBUG"] = "true"
    
    # Erstelle eine temporäre config.toml mit Interpolation
    config_content = '''
# Konfiguration mit Umgebungsvariablen-Interpolation
app_name = "${APP_NAME:Demo Application}"
debug = "${DEMO_DEBUG:false}"
host = "${HOST:localhost}"
port = "${PORT:8000}"

[security]
secret_key = "${DEMO_SECRET}"
algorithm = "HS256"

[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./demo.db}"
echo = "${DB_ECHO:false}"
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(config_content)
        f.flush()
        
        try:
            config = Config.from_file(f.name)
            
            print(f"✅ app_name: {config.app_name}")  # Verwendet Default
            print(f"✅ debug: {config.debug}")       # Aus Umgebungsvariable
            print(f"✅ host: {config.host}")         # Verwendet Default
            print(f"✅ port: {config.port}")         # Verwendet Default  
            print(f"✅ secret_key: {config.security.secret_key}")  # Aus Umgebungsvariable
            print(f"✅ database_url: {config.database.url}")       # Verwendet Default
            
        finally:
            os.unlink(f.name)
    
    print()


def demo_env_override():
    """Demonstriert, wie Umgebungsvariablen TOML-Werte überschreiben können."""
    print("🔄 Demo: Umgebungsvariablen überschreiben TOML-Werte")
    print("=" * 60)
    
    # Setze Umgebungsvariablen, die auch in der TOML-Datei stehen
    os.environ["APP_NAME"] = "Überschriebene App"
    os.environ["DATABASE__URL"] = "postgresql://localhost/overridden_db"
    
    config_content = '''
app_name = "${APP_NAME:Original App}"
debug = true

[database] 
url = "${DATABASE_URL:sqlite:///original.db}"
echo = false
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(config_content)
        f.flush()
        
        try:
            # Verwende from_file_and_env für die beste Flexibilität
            config = Config.from_file_and_env(f.name)
            
            print(f"✅ app_name: {config.app_name}")  # Überschrieben durch ENV
            print(f"✅ debug: {config.debug}")       # Aus TOML
            print(f"✅ database_url: {config.database.url}")  # Überschrieben durch ENV
            
        finally:
            os.unlink(f.name)
    
    print()


def demo_production_vs_development():
    """Zeigt, wie man verschiedene Umgebungen konfiguriert."""
    print("🚀 Demo: Produktions- vs. Entwicklungsumgebung")
    print("=" * 60)
    
    # Gemeinsame config.toml (würde ins Git committed)
    config_content = '''
# Gemeinsame Konfiguration für alle Umgebungen
app_name = "${APP_NAME:MSFW Application}"
debug = "${DEBUG:false}"
host = "${HOST:0.0.0.0}"
port = "${PORT:8000}"

[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"
echo = "${DATABASE_ECHO:false}"

[security]
secret_key = "${SECRET_KEY:dev-key-change-in-prod}"

[logging]
level = "${LOG_LEVEL:INFO}"
format = "${LOG_FORMAT:text}"
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(config_content)
        f.flush()
        
        try:
            print("📝 Entwicklungsumgebung (nur Defaults aus TOML):")
            # Keine speziellen Umgebungsvariablen gesetzt
            for key in ["DEBUG", "DATABASE_URL", "SECRET_KEY", "LOG_LEVEL"]:
                if key in os.environ:
                    del os.environ[key]
            
            dev_config = Config.from_file(f.name)
            print(f"  debug: {dev_config.debug}")
            print(f"  database: {dev_config.database.url}")
            print(f"  secret_key: {dev_config.security.secret_key}")
            print(f"  log_level: {dev_config.logging.level}")
            print()
            
            print("🏭 Produktionsumgebung (Überschreibung durch ENV):")
            # Setze Produktions-Umgebungsvariablen
            os.environ["DEBUG"] = "false"
            os.environ["DATABASE_URL"] = "postgresql://prod-server/myapp"
            os.environ["SECRET_KEY"] = "super-secure-production-key"
            os.environ["LOG_LEVEL"] = "WARNING"
            
            prod_config = Config.from_file(f.name)
            print(f"  debug: {prod_config.debug}")
            print(f"  database: {prod_config.database.url}")
            print(f"  secret_key: {prod_config.security.secret_key}")
            print(f"  log_level: {prod_config.logging.level}")
            
        finally:
            os.unlink(f.name)
    
    print()


def demo_load_config_convenience():
    """Zeigt die Verwendung der load_config() Convenience-Funktion."""
    print("🛠️  Demo: load_config() Convenience-Funktion")
    print("=" * 60)
    
    # Erstelle config/settings.toml
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    config_content = '''
app_name = "${APP_NAME:Load Config Demo}"
debug = "${DEBUG:true}"

[database]
url = "${DATABASE_URL:sqlite+aiosqlite:///./loadconfig_demo.db}"
'''
    
    config_file = config_dir / "settings.toml"
    config_file.write_text(config_content)
    
    try:
        # load_config() sucht automatisch nach config/settings.toml
        config = load_config()
        
        print(f"✅ Automatisch gefunden: {config_file}")
        print(f"✅ app_name: {config.app_name}")
        print(f"✅ debug: {config.debug}")
        print(f"✅ database_url: {config.database.url}")
        
    finally:
        config_file.unlink()
        config_dir.rmdir()
    
    print()


def main():
    """Führt alle Demos aus."""
    print("🎯 MSFW Konfiguration - Lösung für 'doppelt gemoppelt'")
    print("=" * 70)
    print("✨ Eine config.toml mit Umgebungsvariablen-Interpolation!")
    print("✨ Keine separate .env Datei mehr nötig!")
    print("✨ Git-freundlich und deployment-flexibel!")
    print()
    
    demo_basic_interpolation()
    demo_env_override()
    demo_production_vs_development()
    demo_load_config_convenience()
    
    print("🎉 Fazit:")
    print("   • Eine zentrale config.toml (Git-freundlich)")
    print("   • ${VAR_NAME:default} Syntax für Flexibilität")
    print("   • Umgebungsvariablen können alles überschreiben")
    print("   • Kein 'doppelt gemoppelt' mehr!")


if __name__ == "__main__":
    main() 