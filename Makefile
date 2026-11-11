SHELL := /bin/bash
VENV ?= .venv
BIN := $(abspath $(VENV))/bin
export PATH := $(BIN):$(PATH)

.PHONY: all help setup lint typecheck test scan audit-demo build clean

all: lint typecheck test

help:
	@echo "FinOps Resource Auditor Commands:"
	@echo "  make setup        Install project in editable mode with development dependencies"
	@echo "  make lint         Run Ruff linter and code formatting check"
	@echo "  make typecheck    Run Mypy static type verification (strict mode)"
	@echo "  make test         Execute Pytest unit tests with coverage reporting"
	@echo "  make scan         Run Gitleaks credential scanning audit"
	@echo "  make audit-demo   Execute offline FinOps audit using synthetic fixtures"
	@echo "  make build        Build Python sdist and wheel packages"
	@echo "  make clean        Remove build artifacts and temporary test caches"

setup:
	python3 -m venv $(VENV)
	$(BIN)/pip install -e '.[dev]'

lint:
	@echo "==> Running Ruff linter and style checks..."
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

typecheck:
	@echo "==> Running Mypy strict type analysis..."
	$(BIN)/mypy src

test:
	@echo "==> Running Pytest test suite with coverage..."
	$(BIN)/pytest

scan:
	@echo "==> Running Gitleaks credential scan..."
	@which gitleaks >/dev/null 2>&1 && gitleaks detect --verbose || echo "[INFO] gitleaks CLI not installed locally; enforced via GitHub Actions CI"

audit-demo:
	@echo "==> Executing offline FinOps discovery demo..."
	$(BIN)/finops-audit --demo --format text

build:
	@echo "==> Building source distribution and wheel packages..."
	$(BIN)/python -m build

clean:
	@echo "==> Cleaning local build and cache artifacts..."
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist/ build/ *.egg-info .coverage coverage.xml report.json demo-report.json
