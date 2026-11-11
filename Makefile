.PHONY: help install format format-check lint typecheck test-unit test-integration test-conformity conformity-report test-all hardening-scan verify-reproducibility db-up db-down migrate serve build-evidence-package

PYTHON := $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,.venv/bin/python)

help:
	@echo "install                  Install runtime and development dependencies"
	@echo "format                   Format Python sources"
	@echo "format-check             Check Python formatting"
	@echo "lint                     Run Ruff lint checks"
	@echo "typecheck                Run strict mypy checks"
	@echo "test-unit                Run unit tests"
	@echo "test-integration         Run integration and API tests"
	@echo "test-conformity          Run Stage 15 conformity tests"
	@echo "conformity-report        Execute Stage 15 and export its report"
	@echo "test-all                 Run all tests"
	@echo "hardening-scan           Scan source for secret signatures and oracle coupling"
	@echo "verify-reproducibility   Run offline CI twice from isolated source copies"
	@echo "db-up / db-down          Start or stop local PostgreSQL"
	@echo "migrate                  Upgrade database to Alembic head"
	@echo "serve                    Start the local FastAPI service"
	@echo "build-evidence-package   Generate Evidence Package v0.1"

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.lock
	$(PYTHON) -m pip install --no-deps -e .

format:
	$(PYTHON) -m ruff format src tests scripts migrations
	$(PYTHON) -m ruff check --fix src tests scripts migrations

format-check:
	$(PYTHON) -m ruff format --check src tests scripts migrations

lint:
	$(PYTHON) -m ruff check src tests scripts migrations

typecheck:
	$(PYTHON) -m mypy

test-unit:
	$(PYTHON) -m pytest tests/unit

test-integration:
	$(PYTHON) -m pytest tests/integration tests/api

test-conformity:
	$(PYTHON) -m pytest tests/conformity

conformity-report:
	$(PYTHON) scripts/run_stage15_conformity.py

test-all:
	$(PYTHON) -m pytest

hardening-scan:
	$(PYTHON) scripts/hardening_scan.py

verify-reproducibility:
	$(PYTHON) scripts/verify_clean_copy.py

db-up:
	docker compose up -d db

db-down:
	docker compose down

migrate:
	$(PYTHON) -m alembic upgrade head

serve:
	$(PYTHON) -m uvicorn vai_bd.main:app --reload

build-evidence-package:
	$(PYTHON) scripts/build_evidence_package.py
