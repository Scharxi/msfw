.PHONY: help install install-dev test test-unit test-integration test-e2e test-coverage lint format clean docs

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the package
	uv pip install -e .

install-dev: ## Install development dependencies
	uv pip install -e ".[dev,test]"

test: ## Run all tests
	uv run pytest --tb=no -q 

test-unit: ## Run unit tests only
	uv run pytest -m unit

test-integration: ## Run integration tests only
	uv run pytest -m integration

test-e2e: ## Run end-to-end tests only
	uv run pytest -m e2e

test-fast: ## Run fast tests (excluding slow and performance tests)
	uv run pytest -m "not slow and not performance"

test-coverage: ## Run tests with coverage report
	uv run pytest --cov=msfw --cov-report=html --cov-report=term-missing

test-coverage-xml: ## Run tests with XML coverage report
	uv run pytest --cov=msfw --cov-report=xml

lint: ## Run linting
	ruff check msfw tests
	uv run mypy msfw

format: ## Format code
	uv run black msfw tests
	uv run ruff check --fix msfw tests

clean: ## Clean up build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete

docs: ## Generate documentation
	@echo "Documentation generation not yet implemented"

run-demo: ## Run the demo application
	uv run python main.py

dev: ## Run development server with auto-reload
	uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

check: lint test-fast ## Run quick checks (lint + fast tests)

ci: lint test-coverage ## Run CI pipeline (lint + full test suite with coverage)

setup-hooks: ## Setup pre-commit hooks
	pre-commit install

update-deps: ## Update dependencies
	uv pip install --upgrade -e ".[dev,test]" 