# Implementation Status

Last updated: 2026-10-19

## Phase 0 — Authority and inputs

Status: `COMPLETE_WITH_CARRY_FORWARD_ITEMS`

Completed:

- source implementation pack and development plan reviewed;
- frozen authority and explicit non-goals recorded in the root README;
- discontinued application excluded as a baseline;
- pre-code decisions recorded in ADRs 0001–0005.

Carry forward:

- ADR 0001 and ADR 0002 contain proposed governed vocabularies/policies that need
  governance confirmation before those fields are finalized in Phase 2/4;
- the original frozen Stage 15 input artifact remains unavailable; the user
  authorized a new, clearly versioned synthetic baseline for Phase 7.

## Phase 1 — Repository scaffold

Status: `COMPLETE`

Delivered:

- initialized Git repository on branch `main` (no commit created yet);
- Python package and FastAPI app factory;
- fail-closed environment configuration;
- local PostgreSQL Docker Compose service;
- project commands, CI workflow, and resolved dependency lock;
- OpenAI Agents SDK dependency installed but no agents or external tools created;
- health endpoint and initial unit tests;
- Stage 15 fixture/oracle isolation placeholders.

Verification:

```text
pip check: PASS
ruff format --check: PASS (16 files)
ruff check: PASS
mypy --strict: PASS (11 source files)
pytest: PASS (3 tests)
docker compose config --quiet: PASS
```

## Phase 2 — Pure domain contracts

Status: `COMPLETE`

Delivered:

- all source-defined enum families;
- immutable identity, actor, source, and exact-revision references;
- common revision/supersession/dependency envelope;
- configuration, discovery, evidence, eligibility-gate, opportunity, portfolio,
  allocation, commercial-action, release-readiness, authorization, workflow,
  audit, execution-decision, and conformity contracts;
- conditional validation for qualification, reassessment, allocation tiers,
  readiness, run lifecycle, exact approval scope, and human-only final decisions;
- an agent-safe review-request contract with no authorization state or authority;
- valid round-trip and invalid-extra-field tests for every domain model, plus
  focused invariant tests.

Verification:

```text
ruff format --check: PASS
ruff check: PASS
mypy --strict: PASS (21 source files)
pytest: PASS (91 tests)
domain coverage: 90% branch-aware
```

## Total project progress

Current weighted completion: **98%**.

The fixed phase weights are:

| Phase | Weight |
|---|---:|
| 0 Authority and inputs | 3% |
| 1 Repository scaffold | 5% |
| 2 Domain contracts | 10% |
| 3 Persistence and migrations | 12% |
| 4 Deterministic policies | 13% |
| 5 Five agent shells | 13% |
| 6 Orchestrator and services | 14% |
| 7 Stage 15 fixtures/oracle | 6% |
| 8 Conformity harness | 8% |
| 9 Governed API | 7% |
| 10 Operator view | 3% |
| 11 Hardening | 4% |
| 12 Evidence Package | 2% |

Percentages are earned when a phase gate passes, not merely when files exist.
Partial phase progress may be reported separately but is not added to the total
until its gate is satisfied.

## Phase 3 — Persistence and migrations

Status: `COMPLETE`

Delivered:

- SQLAlchemy 2.x PostgreSQL schema with explicit actors, identities, revisions,
  exact dependency edges, supersession edges, typed payloads, universe/snapshot
  membership, canonical comparisons, allocation membership, authorization
  events, agent runs, workflow/materiality/execution audit, and conformity rows;
- a database-enforced single active revision per object identity;
- seven ordered Alembic migrations with full downgrade and upgrade support;
- append/supersede repository with row locking and exact-current conflict checks;
- exact revision reconstruction that preserves immutable payloads while exposing
  current control validity such as `SUPERSEDED` or `REASSESSMENT_REQUIRED`;
- exact dependency/dependent queries and reassessment marking;
- immutable revision-specific snapshot membership;
- canonical unordered-pair uniqueness per snapshot;
- append-only authorization history isolated by exact CAO revision;
- append-only agent-run, workflow, materiality, execution, and conformity audit;
- transactional Unit of Work with commit and rollback behavior.

Verification:

```text
ruff format --check: PASS
ruff check: PASS
mypy --strict: PASS (25 source files)
Alembic downgrade head -> base: PASS
Alembic upgrade base -> 0007_conformity_results: PASS (7 migrations)
PostgreSQL integration tests: PASS (11 tests)
complete test suite: PASS (102 tests)
```

The local PostgreSQL container is healthy and remains running for the next phase.

## Phase 4 — Deterministic policies

Status: `COMPLETE`

Delivered:

- configurable, auditable evidence-currentness rules that preserve stale and
  unknown records, enforce admissibility, and deduplicate shared dependency
  groups for independence requirements;
- bidirectional contradiction presentation and explicit missing-evidence behavior;
- fixed-precedence minimum-evidence/hard-eligibility decisions with narrowest
  valid blocking scope and no qualification authority;
- exact-revision usability checks for missing, superseded, and
  reassessment-required dependencies;
- qualified-only snapshot selection with retained excluded/unresolved reasons;
- deterministic unordered pair generation, canonical identity, inverse
  relationships, completeness checks, partial-order extraction, symmetric
  ties/near-ties/indeterminacy, and strongly connected comparison cycles;
- exact-decimal allocatable-capacity arithmetic with fixed commitments, unit and
  horizon checks, independent concurrency enforcement, tier validation,
  materially superior feasible-item protection, residual capacity behavior,
  and smaller-action review requirements;
- an authorization-independent release-readiness checklist;
- exact CAO revision/action/scope/human/timestamp/current-dependency execution
  checks and an always-false conformity restriction;
- bounded breadth-first reassessment propagation with recorded affected and
  unaffected materiality decisions, capacity-change scope protection, and
  source-dependency-group expansion;
- property/invariant coverage for inverse involution, pair counts and ordering,
  immutable priority inputs, non-disqualifying missing evidence, conformity
  execution denial, and dependency-bounded reassessment.

Verification:

```text
ruff format --check: PASS (46 source/test files)
ruff check: PASS
mypy --strict: PASS (35 source files)
policy tests: PASS (35 tests, 87% branch-aware policy coverage)
unit tests: PASS (126 tests)
complete suite with PostgreSQL: PASS (137 tests)
```

## Phase 5 — Five bounded specialist agent shells

Status: `COMPLETE`

Delivered:

- exactly five OpenAI Agents SDK `Agent` objects: Market Discovery, Evidence
  Intelligence, Opportunity Intelligence, Portfolio and Allocation, and
  Commercial Action;
- no tools, MCP servers, handoffs, persistent conversational memory, external
  provider access, authorization capability, or execution capability on any
  specialist;
- strict Pydantic input/output contracts, including separate comparison and
  allocation operations through the single portfolio specialist;
- shared and role-specific prompt files with versions, frozen-rules metadata,
  implementation authority, SHA-256 digests, and fail-closed integrity loading;
- an explicit untrusted-evidence serialization boundary that escapes delimiter
  injection and instructs every specialist to treat evidence as data;
- role-specific semantic guardrails for source echoing, restricted evidence,
  exact revision preservation, confidence links, complete canonical pairs,
  allocation membership, exhaustive-coverage claims, and action evidence/owner
  references;
- deterministic mapping from validated structured outputs to typed pending
  domain-command batches; rejected outputs never reach that boundary;
- one `AgentRunner` protocol, deterministic queued fake runner, and opt-in live
  Agents SDK adapter with configured model, bounded turns, trace controls, usage
  capture, and generated trace references;
- a common run service that records STARTED before invocation and exactly one
  SUCCEEDED or FAILED terminal transition, including prompt version/digest,
  model configuration identifier, input/output refs, trace ref, error, and usage;
- repository enforcement of immutable run identity fields during the allowed
  STARTED-to-terminal audit transition;
- fail-closed `local-live` configuration requiring both API credentials and an
  explicit model identifier.

Verification:

```text
ruff format --check: PASS (61 source/test files)
ruff check: PASS
mypy --strict: PASS (43 source files)
agent-shell tests: PASS (15 tests, 85% branch-aware agents-package coverage)
unit tests: PASS (142 tests)
complete suite with PostgreSQL: PASS (154 tests)
live OpenAI model calls: NOT RUN (opt-in only)
```

The implementation follows the official OpenAI Agents SDK pattern of focused
agents with Pydantic structured outputs and application-owned Runner handling.

## Phase 6 — Deterministic orchestrator and services

Status: `COMPLETE`

Delivered:

- an explicit forward-only workflow graph with controlled `HELD`,
  `ACTIVE_REASSESSMENT`, resume, and terminal `CLOSED` behavior;
- persisted workflow transitions containing actor, trigger, prior/next state,
  timestamp, and exact affected revision references;
- exact-current phase preconditions for bootstrap, discovery, evidence,
  assessment, snapshot, comparison, allocation, action, readiness, human review,
  and reassessment;
- scope-preserving local, portfolio, and whole-cycle hold routing, where only a
  whole-cycle hold changes the cycle workflow to `HELD`;
- transactional specialist-output conversion into governed discovery, evidence,
  separated opportunity judgments, immutable snapshots, canonical comparisons,
  qualitative priority state, capacity allocation, and commercial actions;
- deterministic gate, snapshot, release-readiness, human-review, authorization,
  and bounded reassessment services;
- direct exact-upstream dependency references on material outputs, with
  service-owned UUIDs, timestamps, actors, and revision envelopes;
- server-owned human authorization decisions that copy the exact current CAO
  action/scope and preserve the originally requested human authority;
- durable PostgreSQL idempotency records with request digests, in-progress,
  success/failure status, result refs, replay, and conflicting-key rejection;
- atomic success commits spanning domain revisions, terminal agent-run audit,
  and idempotency results; rejected or failed specialist outputs persist no
  partial governed state and remain visibly resumable with a new operation key;
- optimistic exact-current revision checks and existing repository row-locking
  protections retained at mutation boundaries;
- migration `0008_idempotency_records` with downgrade support;
- a full fake-agent PostgreSQL workflow covering bootstrap through human review,
  followed by capacity reassessment that marks allocation/action/readiness while
  leaving the qualitative priority state current.

Verification:

```text
ruff format --check: PASS (82 source/test/migration files)
ruff check: PASS
mypy --strict: PASS (53 source files)
Phase 6 focused tests: PASS (6 tests, 90% branch-aware orchestration/service coverage)
unit tests: PASS (147 tests)
complete suite with PostgreSQL: PASS (160 tests)
Alembic downgrade head -> base and upgrade -> 0008_idempotency_records: PASS
live OpenAI model calls: NOT RUN (fake runner used)
```

## Phase 7 — Stage 15 fixtures and oracle

Status: `COMPLETE`

Delivered:

- an explicitly authorized, fully fictional `stage15-synthetic-v1.0.0` baseline,
  documented as a new project artifact rather than the missing original dataset;
- ten base candidates C01–C10 with stable UUID5 identities, evidence provenance,
  source dates, admissibility/currentness/directness, dependency groups, missing
  material facts, pursuit demands, and next actions;
- independent runtime mutations M01–M09, including C12, capacity, comparison
  cycle, supersession, review timeout, missing configuration, shared-source
  failure, and missing-owner scenarios;
- explicit captured fake-agent outputs referencing only runtime observations;
- a separately stored held-out oracle containing base and mutation expectations;
- runtime and oracle manifests with versions, provenance, per-file SHA-256
  digests, and an oracle binding to the exact runtime-manifest digest;
- a deterministic generator and strict Pydantic runtime loader that verifies
  file integrity, versions, case coverage, mutation completeness, and refs;
- tests proving deterministic regeneration, corruption rejection, complete
  runtime coverage, manifest binding, and runtime execution without oracle reads.

Verification:

```text
ruff check (Phase 7 files): PASS
mypy --strict --no-incremental (conformity runtime package): PASS
Phase 7 focused tests: PASS (7 tests)
hardening scan: PASS
complete suite with PostgreSQL: PASS (177 tests)
```

## Phase 8 — Conformity harness

Status: `COMPLETE`

Delivered:

- an oracle-blind runtime executor covering the base portfolio, C01–C10, and
  independent M01–M09 mutations;
- deterministic eligibility, evidence restriction/staleness, source dependency,
  comparison completeness/cycle, qualitative priority, capacity, supersession,
  non-response, missing-input, reassessment, and concept-separation assertions;
- explicit base validation for the five-member snapshot, all ten unique pairs,
  `C01 > C04 > C02 > C05 > C03`, exact-decimal demand, feasible allocation,
  residual-capacity behavior, and representation of every unresolved case;
- a serialization boundary that completes runtime execution before the held-out
  expected outcomes are read;
- a generic material-difference evaluator with case and suite PASS/FAIL states;
- a fail-closed report contract requiring exactly BASE, C01–C10, and M01–M09,
  with no skip state and no missing, additional, or reordered material cases;
- machine-readable JSON export with fixture version/digest, actual output refs,
  expected rule refs, material differences, traces, timestamps, code version,
  prompt versions, and model configuration;
- append-only PostgreSQL persistence for all 20 report rows;
- focused negative-boundary coverage for restricted evidence, comparison gaps
  and duplicates, authorization transfer, timeout-as-approval, specialist tools,
  conformity execution, oracle isolation, and material mismatch reporting;
- stable `make conformity-report` and `make test-conformity` commands;
- a passing report at `artifacts/conformity/stage15-report.json`.

Verification:

```text
Stage 15 report: PASS (20 material cases)
Phase 7/8 focused tests: PASS (34 tests)
PostgreSQL conformity persistence: PASS (1 test)
ruff format --check: PASS (105 source/test/script/migration files)
ruff check: PASS
mypy --strict: PASS (63 source files; cache disabled for low-disk workspace)
hardening scan: PASS
complete suite with PostgreSQL: PASS (205 tests)
```

## Phase 9 — Governed API

Status: `COMPLETE`

Delivered:

- versioned FastAPI routes for cycle creation/read, capacity revision,
  discovery, evidence, eligibility, assessment, snapshot, comparison,
  allocation, action preparation, release readiness, review submission, human
  authorization, execution-eligibility read, and reassessment;
- strict Pydantic request/response schemas and an injectable application-service
  port, with a fail-closed default when no backend is configured;
- exact identity-and-revision matching between mutation paths and request
  bodies, plus a required bounded `Idempotency-Key` contract;
- stable redacted error envelopes for validation, missing revision, revision and
  idempotency conflicts, in-progress operations, phase/hold preconditions,
  specialist contract rejection, and specialist execution failure;
- request-ID generation/propagation on every response;
- signed HMAC test/conformity authentication that derives a human actor on the
  server, rejects non-human assertions, and is unavailable in local/live
  profiles;
- no external-action endpoint: the only execution-related route is a read-only
  eligibility decision that reports `external_action_performed: false`;
- an API-client workflow test exercising every route from bootstrap through
  authorization and reassessment, plus authority, path conflict, hold,
  idempotent replay, conflicting-key, and prohibited execution-surface checks;
- committed generated OpenAPI and a concise governed API guide.

Verification:

```text
ruff format --check: PASS (89 source/test/script/migration files)
ruff check: PASS
mypy --strict: PASS (57 source files)
Phase 9 focused tests: PASS (3 tests)
complete suite with PostgreSQL: PASS (162 tests)
external actions/model calls: NOT RUN and no HTTP execution route exists
```

## Phase 10 — Minimal operator view

Frontend expansion planning update (2026-11-11): the baseline status below is
historical. The expanded UI and integration gates are **PLANNED / NOT DELIVERED**;
see [the frontend product specification](../vai_bd_development_plan/11_FRONTEND_PRODUCT_SPEC.md)
and [Bassam's implementation handoff](../vai_bd_development_plan/12_FRONTEND_IMPLEMENTATION_HANDOFF.md).
Source inspection confirms the default application still installs
`UnconfiguredApiBackend`, and local human authentication is not wired. Existing
API/presentation tests do not establish that the default app serves populated
cycle data. The expansion must wire and verify those dependencies before claiming
a usable local end-to-end operator experience.

Status: `COMPLETE`

Delivered:

- a read-only server-rendered cycle index at `/operator` and cycle detail at
  `/operator/cycles/{cycle_id}`;
- a strict operator projection contract and
  `GET /v1/decision-cycles/{cycle_id}/operator-view` JSON endpoint;
- decision context covering offer, market, effective date, capacity, planning
  horizon, coverage basis, status, and disclosed limitations;
- complete candidate disposition, including excluded/unresolved reasons,
  evidence summaries, limitations, contradictions, revision, and freshness;
- qualified-opportunity presentation covering Fit, Need, claim-level confidence,
  evidence, contradiction, uncertainty, Pursuit Demand, and reassessment state;
- visibly separate comparative-priority and capacity-allocation panels, including
  Act Now, capacity deferral, priority deferral, investigation, capacity effect,
  and marginal reason;
- next credible action, action type, release readiness, and human authorization
  shown as distinct concepts;
- responsive semantic HTML with landmarks, heading hierarchy, breadcrumb, skip
  navigation, native disclosure controls, escaped operator content, and reduced-
  motion support;
- presentation tests proving the information needed for operator decisions is
  visible while forms, buttons, lead scores, and send/execute controls are absent.

Verification:

```text
ruff format --check: PASS (93 source/test/script/migration files)
ruff check: PASS
mypy --strict: PASS (60 source files)
Phase 10 focused tests: PASS (2 tests, 99% branch-aware operator coverage)
complete suite with PostgreSQL: PASS (164 tests)
browser automation: NOT AVAILABLE; HTML semantics and presentation contract tested
```

## Phase 11 — Hardening

Status: `COMPLETE`

Delivered:

- conflict-safe PostgreSQL idempotency claims using atomic insert-on-conflict,
  with concurrent same-key tests proving one winner and one stable in-progress
  response rather than an integrity failure;
- migration verification from an empty database and from the immediately
  preceding `0007_conformity_results` revision to the current head;
- transaction rollback and failure-injection coverage proving flushed domain
  writes do not survive failure, failed claims remain visible, same-key failure
  replay is blocked, and a new-key retry can proceed;
- provider/agent error sanitization in both specialist pipelines and idempotency
  audit, retaining exception classification without raw provider text;
- a catch-all redacted API failure envelope, tested with secret-bearing injected
  failures;
- repository credential-signature scanning and a separate runtime-source check
  preventing Stage 15 oracle imports or paths;
- trace-safety assertions confirming sensitive trace payloads default off and CI
  explicitly disables tracing/sensitive data for offline verification;
- expanded CI/Make quality scope covering source, tests, scripts, and migrations;
- a reproducibility runner that creates two fresh allowlisted source copies and
  independently runs formatting, linting, strict typing, security scanning,
  migrations, and the complete PostgreSQL test suite without network/model use;
- updated local operating instructions and a detailed hardening report.

Verification:

```text
ruff format --check: PASS (97 source/test/script/migration files)
ruff check: PASS
mypy --strict: PASS (60 source files)
hardening scan: PASS
complete suite with PostgreSQL: PASS (170 tests)
isolated offline CI run 1: PASS (170 tests)
isolated offline CI run 2: PASS (170 tests)
live OpenAI smoke: NOT RUN (credentials/model not configured)
```

The repository has no initial commit, so clean-build verification used isolated
allowlisted source copies rather than misreporting a Git checkout. See
[the Phase 11 hardening report](hardening-report.md).

## Next

Phase 12 is next: assemble the final evidence package from the now-complete
implementation, hardening, and conformity artifacts. Total weighted completion
is **98%**.
