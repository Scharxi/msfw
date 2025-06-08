# Installation

This chapter guides you through the various installation options for MSFW.

## System Requirements

- **Python**: 3.13 or higher
- **Operating System**: Windows, macOS, Linux
- **RAM**: At least 512 MB (recommended: 2 GB or more)
- **Disk Space**: At least 100 MB free space

## Dependencies

MSFW is built on the following core libraries:

- **FastAPI** 0.104+ - Modern, fast web framework
- **Pydantic** 2.5+ - Data validation using Python types
- **SQLAlchemy** 2.0+ - SQL toolkit and ORM
- **Uvicorn** - ASGI server for production environments

## Installation via pip

### Basic installation

```bash
pip install msfw
```

### With development dependencies

```bash
pip install msfw[dev]
```

### With all optional dependencies

```bash
pip install msfw[all]
```

## Installation via uv (recommended)

[uv](https://github.com/astral-sh/uv) is an ultra-fast Python package manager:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install MSFW
uv add msfw

# With development dependencies
uv add --group dev msfw
```

## Development Installation

### Clone repository

```bash
git clone https://github.com/yourusername/msfw.git
cd msfw
```

### With uv (recommended)

```bash
# Set up development environment
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### With pip and virtualenv

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -e ".[dev]"
```

## Docker Installation

### Official Docker Image

```bash
# Start MSFW container
docker run -p 8000:8000 msfw/msfw:latest
```

### Build your own Docker image

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build image
docker build -t my-msfw-app .

# Start container
docker run -p 8000:8000 my-msfw-app
```

## Virtual Environment Setup

### Why virtual environments?

Virtual environments isolate project dependencies and prevent conflicts:

- **Isolation**: Each project has its own dependencies
- **Reproducibility**: Consistent environments across different systems
- **Security**: Prevents accidental system modifications

### With venv (standard)

```bash
# Create virtual environment
python -m venv msfw-env

# Activate
source msfw-env/bin/activate  # Linux/macOS
msfw-env\Scripts\activate     # Windows

# Install MSFW
pip install msfw

# Deactivate
deactivate
```

### With conda

```bash
# Create environment
conda create -n msfw python=3.13

# Activate
conda activate msfw

# Install MSFW
pip install msfw

# Deactivate
conda deactivate
```

## Verify Installation

### Basic verification

```bash
# Show MSFW version
python -c "import msfw; print(msfw.__version__)"

# Test CLI tool
msfw --help
```

### Complete test

```python
from msfw import MSFWApplication, Config

# Create simple application
config = Config()
config.app_name = "Test App"

app = MSFWApplication(config)

print("✅ MSFW successfully installed!")
```

## Common Installation Issues

### Issue: `ModuleNotFoundError`

**Solution**: Activate virtual environment or reinstall MSFW:

```bash
pip install --force-reinstall msfw
```

### Issue: Permission errors on Windows

**Solution**: Run PowerShell as administrator or use `--user` flag:

```bash
pip install --user msfw
```

### Issue: Compilation errors for C dependencies

**Solution**: Install build tools:

```bash
# Windows
pip install setuptools wheel

# Ubuntu/Debian
sudo apt-get install build-essential python3-dev

# macOS
xcode-select --install
```

### Issue: SSL certificate errors

**Solution**: Configure trusted hosts:

```bash
pip install --trusted-host pypi.org --trusted-host pypi.python.org msfw
```

## Next Steps

After successful installation, you can start with the [Quick Start](quick_start.md) or learn about the [Basic Concepts](basic_concepts.md).

```{tip}
For production environments, we recommend using Docker or a professional deployment tool like Kubernetes.
``` 