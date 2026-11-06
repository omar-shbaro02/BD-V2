# Phase 11 hardening report

Date: 2026-10-19  
Profile: offline test configuration  
External execution: disabled

## Controls exercised

- Alembic downgrade to an empty database followed by upgrade through head.
- Upgrade from `0007_conformity_results` to `0008_idempotency_records`, including
  presence/absence checks for the new table.
- Concurrent same-key idempotency claims using separate PostgreSQL transactions.
  PostgreSQL conflict-safe insertion produces one claim and one visible
  `operation_in_progress` result rather than an integrity error.
- Transaction failure after a flushed write, proving the domain write rolls back
  while the idempotency failure record is retained.
- Same-key replay after failure and safe retry with a new operation key.
- Agent/provider failure injection, proving persisted audit and idempotency errors
  retain the exception class but redact raw exception messages.
- API unexpected-failure injection, proving the response contains a stable
  `internal_error` envelope and does not expose provider text.
- Test/conformity trace defaults exclude sensitive payloads and CI disables SDK
  tracing for offline runs.
- Static scanning of source, tests, fixtures, oracle placeholders, migrations,
  scripts, documentation, configuration, and logs for common credential
  signatures. Runtime source is separately checked for Stage 15 oracle coupling.
- The entire offline CI sequence was run twice from separate temporary source
  copies containing only project-controlled files. Each copy independently ran
  formatting, linting, strict typing, the hardening scan, migrations, and all
  tests against local PostgreSQL.

## Results

```text
ruff format --check: PASS (97 source/test/script/migration files)
ruff check: PASS
mypy --strict: PASS (60 source files)
hardening scan: PASS
complete PostgreSQL suite: PASS (170 tests)
isolated offline CI run 1: PASS (170 tests)
isolated offline CI run 2: PASS (170 tests)
live OpenAI smoke: NOT RUN (credentials/model not configured)
```

The workspace has not yet been committed, so the reproducibility runner uses
allowlisted isolated source copies rather than claiming a Git clean checkout.
The copy excludes the virtual environment, caches, ignored local configuration,
generated coverage data, and unrelated workspace files. No network access or
OpenAI credential is used.
