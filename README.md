# VAI Business Development Decision Intelligence

This repository is the clean implementation baseline for the new VAI Business
Development Decision Intelligence build. The discontinued earlier BD application
is historical only and must not be used as an implementation baseline.

## Authority

Business meaning is governed by [the frozen implementation pack](vai_bd_implementation_pack/00_README.md).
The executable sequence is defined by [the development plan](vai_bd_development_plan/00_README.md).
If code or planning material conflicts with the frozen pack, stop and report the
conflict rather than silently redesigning the product.

## Current scope

Authorized now:

- local/backend implementation;
- five OpenAI API specialist agents with typed outputs;
- a deterministic, non-substantive Python Orchestrator;
- Stage 15 synthetic conformity testing;
- persistence, audit, API, and a minimal operator view.

Not authorized:

- production deployment or a live pilot;
- real-company actions or outreach;
- scraping or restricted extraction;
- paid third-party providers;
- email, social, CRM, purchase, bulk-message, or autonomous execution tools.

Human Authorization remains outside every agent. `Act Now`, `Release Ready`, a
recommendation, a draft, silence, and timeout never constitute authorization.

## Status

Phases 0 through 11 are complete, representing 98% of the fixed weighted plan;
see [the implementation status](docs/implementation-status.md). Stage 15 has an
authorized, reproducible synthetic dataset, separately held oracle, complete
conformity harness, and machine-readable passing report.

## Local development

Prerequisites:

- Python 3.11 or 3.12 (CI uses 3.11);
- Docker with Docker Compose;
- PostgreSQL 17 through the provided Compose service.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
cp .env.example .env
docker compose up -d db
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m pytest
.venv/bin/uvicorn vai_bd.main:app --reload
```

The health endpoint is `GET /health`.
The governed API contract is described in [the API guide](docs/api-guide.md) and
the generated [OpenAPI document](docs/openapi.json).
The read-only operator view begins at `GET /operator`.

Offline quality and hardening commands:

```bash
make format-check lint typecheck
make hardening-scan
make conformity-report
make test-unit test-integration test-all
make verify-reproducibility
```

Offline tests require no OpenAI key and must not call a model. A synthetic live
smoke run is optional and remains disabled unless an authorized key and model
are explicitly provided. Stage 15 conformity uses captured deterministic test
doubles by default; it makes no live-model claim.

`make build-evidence-package` remains fail-closed until Phase 12. To stop local
services without deleting governed database data, use `docker compose stop`.
Do not use `docker compose down -v` unless permanent volume deletion is explicitly
intended and a suitable backup exists.

`requirements.lock` records the resolved development environment. The broader
constraints in `pyproject.toml` are the dependency policy; update the lock only
through a deliberate dependency change followed by the complete test suite.

## Stable commands

Run `make help` to see the project commands. The default test and quality commands
do not need an OpenAI API key and must not make model calls.
