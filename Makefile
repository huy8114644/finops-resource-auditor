SHELL := /bin/bash
.DEFAULT_GOAL := help
VENV ?= .venv
BIN := $(abspath $(VENV))/bin
GITLEAKS_IMAGE ?= zricethezav/gitleaks:v8.24.3
export PATH := $(BIN):$(PATH)

.PHONY: all help setup lint typecheck test scan plan audit-demo build clean

all: lint typecheck test

help:
	@echo "FinOps Resource Auditor Commands:"
	@echo "  make setup        Install project in editable mode with development dependencies"
	@echo "  make lint         Run Ruff linter and code formatting check"
	@echo "  make typecheck    Run Mypy static type verification (strict mode)"
	@echo "  make test         Execute Pytest unit tests with coverage reporting"
	@echo "  make scan         Run Gitleaks credential scanning audit"
	@echo "  make plan         Render synthetic JSON offline; no AWS or notifications"
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
	@if command -v gitleaks >/dev/null 2>&1; then \
		gitleaks detect --no-git --source . --redact; \
	elif command -v docker >/dev/null 2>&1; then \
		docker run --rm -v "$(CURDIR):/repo:ro" $(GITLEAKS_IMAGE) detect --no-git --source /repo --redact; \
	else \
		echo "Install Gitleaks or Docker to run the required scan." >&2; exit 1; \
	fi

plan:
	$(BIN)/finops-audit --demo --format json

audit-demo:
	@echo "==> Executing offline FinOps discovery demo..."
	$(BIN)/finops-audit --demo --format text

build:
	@echo "==> Building source distribution and wheel packages..."
	$(BIN)/python -m build

clean:
	@echo "==> Cleaning local build and cache artifacts..."
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist/ build/ *.egg-info .coverage coverage.xml report.json demo-report.json
