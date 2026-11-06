# Repository Blueprint

## 1. Target tree

```text
.
├── README.md
├── pyproject.toml
├── uv.lock                         # or equivalent committed lock file
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml              # local PostgreSQL only
├── docs/
│   ├── adr/
│   ├── architecture.md
│   ├── api.md
│   └── traceability.md
├── migrations/
│   ├── env.py
│   └── versions/
├── src/vai_bd/
│   ├── main.py
│   ├── config.py
│   ├── clock.py
│   ├── ids.py
│   ├── domain/
│   │   ├── enums.py
│   │   ├── refs.py
│   │   ├── envelopes.py
│   │   ├── cycle.py
│   │   ├── evidence.py
│   │   ├── opportunity.py
│   │   ├── portfolio.py
│   │   ├── actions.py
│   │   └── authorization.py
│   ├── policies/
│   │   ├── eligibility.py
│   │   ├── evidence.py
│   │   ├── comparisons.py
│   │   ├── capacity.py
│   │   ├── revisions.py
│   │   ├── reassessment.py
│   │   ├── release.py
│   │   └── execution.py
│   ├── agents/
│   │   ├── base.py
│   │   ├── contracts.py
│   │   ├── runner.py
│   │   ├── market_discovery.py
│   │   ├── evidence_intelligence.py
│   │   ├── opportunity_intelligence.py
│   │   ├── portfolio_allocation.py
│   │   ├── commercial_action.py
│   │   └── prompts/
│   │       ├── shared_v1.txt
│   │       └── *_v1.txt
│   ├── persistence/
│   │   ├── database.py
│   │   ├── orm.py
│   │   ├── mappers.py
│   │   ├── repositories.py
│   │   └── unit_of_work.py
│   ├── services/
│   │   ├── cycles.py
│   │   ├── discovery.py
│   │   ├── evidence.py
│   │   ├── assessment.py
│   │   ├── portfolio.py
│   │   ├── actions.py
│   │   ├── authorization.py
│   │   └── conformity.py
│   ├── orchestrator/
│   │   ├── state.py
│   │   ├── dependencies.py
│   │   ├── cycle_runner.py
│   │   └── reassessment.py
│   ├── api/
│   │   ├── dependencies.py
│   │   ├── errors.py
│   │   ├── schemas.py
│   │   └── routers/
│   └── operator/
│       ├── presenters.py
│       ├── routes.py
│       └── templates/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   ├── agents/
│   ├── conformity/
│   ├── fixtures/stage15/
│   └── oracle/stage15/
├── scripts/
│   ├── seed_stage15.py
│   ├── run_conformity.py
│   └── build_evidence_package.py
└── evidence_package/               # generated, versioned output
```

## 2. Dependency direction

```text
API / operator -> services -> domain + policies + repositories
orchestrator    -> services + policies + agent runner
agents          -> agent contracts + bounded read-only tool interfaces
persistence     -> domain mappings
domain/policies -> no FastAPI, SQLAlchemy, OpenAI SDK, or test-oracle imports
```

The domain and deterministic policy layers must test without PostgreSQL or an
OpenAI API key.

## 3. Dependency groups

- Runtime: FastAPI, Uvicorn, Pydantic v2, pydantic-settings, SQLAlchemy 2.x,
  PostgreSQL driver, Alembic, OpenAI Agents SDK.
- Test: pytest, pytest-asyncio, HTTPX, property-testing library, coverage tool,
  and PostgreSQL test provisioning.
- Quality: formatter, linter, and static type checker.
- Template rendering: server-rendered templates are preferred for the minimal
  operator view; do not introduce a separate JavaScript application unless the
  view cannot meet acceptance criteria without it.

Pin all exact resolved versions in the lock file. Keep project constraints broad
enough for patch updates, but run the full suite before changing the lock.

## 4. Commands defined from day one

Expose stable project commands through the package manager or a Makefile:

```text
install, format, lint, typecheck, test-unit, test-integration,
test-conformity, test-all, db-up, db-down, migrate, serve,
build-evidence-package
```

CI runs format-check, lint, typecheck, unit, integration, API, agent-contract,
and conformity tests. Live OpenAI tests are opt-in and never required for the
default deterministic CI pass.

## 5. Environment variables

Document without values:

```text
APP_ENV
DATABASE_URL
OPENAI_API_KEY
OPENAI_MODEL
OPENAI_AGENTS_DISABLE_TRACING
TRACE_INCLUDE_SENSITIVE_DATA
EXTERNAL_EXECUTION_ALLOWED=false
TEST_AUTH_SIGNING_KEY              # local/test only
```

Application startup must reject `EXTERNAL_EXECUTION_ALLOWED=true` in the
conformity build profile.

