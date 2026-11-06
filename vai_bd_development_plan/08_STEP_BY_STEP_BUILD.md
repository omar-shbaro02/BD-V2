# Step-by-Step Build Plan

Do not begin a later phase until the prior gate passes. Check each item in the
implementation branch and link its commit/test evidence.

## Phase 0 — Confirm authority and inputs

- [x] Read the complete source implementation pack.
- [x] Confirm whether the full frozen Stage 15 synthetic dataset exists; request
  it if only the summary answer key is available.
- [x] Create ADRs for the decision table in `01_REQUIREMENTS_AND_DECISIONS.md`.
- [x] Record the explicit non-goals and stop conditions in the root README.
- [x] Confirm no discontinued application code is being used as baseline.

Gate: authority, missing inputs, and unresolved governed vocabularies are visible.

## Phase 1 — Scaffold the repository

- [x] Create `pyproject.toml`, source layout, lock file, `.gitignore`, and
  secret-free `.env.example`.
- [x] Add configuration profiles: test, conformity, local-live.
- [x] Force external execution false in test/conformity profiles.
- [x] Add formatter, linter, type checker, pytest, coverage, and stable commands.
- [x] Add FastAPI health endpoint and empty app factory.
- [x] Add local PostgreSQL configuration and CI workflow.

Gate: clean install; format/lint/type/test commands run; no external-action code.

## Phase 2 — Implement pure domain contracts

- [x] Implement revision refs/envelope and all enums.
- [x] Implement configuration, discovery, evidence, gate, opportunity, portfolio,
  action, readiness, authorization, workflow, audit, and conformity models.
- [x] Add rationale/evidence-ref validators and cross-field invariants.
- [x] Exclude Approved authorization from all agent-facing schemas.
- [x] Add unit tests for valid and invalid examples of every model.

Gate: every object in the canonical schema has a typed representation and test.

## Phase 3 — Persistence and migrations

- [x] Implement ORM control tables and typed payload mapping.
- [x] Add exact revision, dependency, supersession, snapshot, comparison,
  authorization-event, run, and audit repositories.
- [x] Add Unit of Work and atomic append/supersede operation.
- [x] Create migrations in the sequence defined by the persistence plan.
- [x] Test database constraints, rollback, optimistic conflict, and history.

Gate: revisions cannot be overwritten; dependencies are queryable; snapshots and
authorization history are immutable/auditable.

## Phase 4 — Deterministic policies

- [x] Evidence dependency, admissibility, contradiction, and currentness rules.
- [x] Minimum-evidence/hard-eligibility gate and scope selection.
- [x] Revision/currentness validation.
- [x] Snapshot membership and complete pair generation.
- [x] Canonical uniqueness, inverse derivation, partial order, and cycle detection.
- [x] Capacity normalization/arithmetic and allocation invariant validator.
- [x] Release-readiness checklist.
- [x] Exact authorization/execution matching with global restriction.
- [x] Bounded reassessment propagation and materiality audit.
- [x] Property/invariant tests.

Gate: all policies pass without DB where pure and without any LLM call.

## Phase 5 — Five agent shells

- [x] Add shared and five specialist prompt files plus manifest/digests.
- [x] Add typed input/output contracts per specialist.
- [x] Define exactly five Agent objects with strict allowlists and output types.
- [x] Implement runner protocol, fake runner, and live Agents SDK adapter.
- [x] Add shared structured/semantic validation and injection boundary.
- [x] Implement transactional output-to-domain mapping.
- [x] Persist agent-run audit and trace mappings.
- [x] Test each permission boundary and failure behavior.

Gate: fake outputs cannot cross role boundaries or persist free-form/invalid state;
model selection remains configuration.

## Phase 6 — Orchestrator and services

- [x] Implement workflow transitions and phase preconditions.
- [x] Implement bootstrap, discovery, evidence, gate, assessment, snapshot,
  comparison, allocation, action, readiness, review, and reassessment services.
- [x] Preserve local vs portfolio vs whole-cycle hold scope.
- [x] Add idempotency and optimistic concurrency.
- [x] Make partial failures visible and resumable.
- [x] Test end-to-end workflow with fake agents and PostgreSQL.

Gate: exact upstream revisions appear on every material output; the Orchestrator
authors no Fit, Need, Priority, Allocation, or Authorization judgment.

## Phase 7 — Stage 15 fixtures and oracle

- [x] Transcribe approved synthetic inputs with provenance/version/digest.
- [x] Store expected outcomes separately in oracle files.
- [x] Add static and runtime oracle-isolation checks.
- [x] Add fake agent outputs driven only by runtime fixture inputs or explicit
  captured test doubles, never by oracle access.

Gate: runtime completes before oracle is mounted/read; leakage checks pass.

## Phase 8 — Conformity harness

- [x] Implement C01–C10 base runs.
- [x] Implement base snapshot, 10 pairs, priority, demand, and allocation checks.
- [x] Implement M01–M09 as independent reproducible mutations.
- [x] Implement negative boundary suite.
- [x] Persist/export machine-readable case results and material differences.
- [x] Make any material skip a suite failure.

Gate: complete conformity report exists; failures are explicit; oracle stays held out.

## Phase 9 — Governed API

- [x] Implement schemas, routers, exception mapping, and request IDs.
- [x] Add exact-revision mutation contracts and idempotency keys.
- [x] Add test authentication adapter and human-only authorization decisions.
- [x] Test every endpoint, conflict, hold, and authority failure.
- [x] Publish generated OpenAPI and a concise API guide.

Gate: the full decision cycle runs through an API test client; no non-human actor
can approve; no endpoint executes external action.

## Phase 10 — Minimal operator view

- [x] Add cycle list/detail and opportunity/portfolio presentation.
- [x] Show Priority and Allocation separately.
- [x] Show full candidate disposition, evidence limitations, contradiction,
  uncertainty, capacity reason, next action, readiness, and authorization.
- [x] Add accessibility/semantic HTML and presentation tests.
- [x] Verify no score or send/execute control appears.

Gate: an operator can answer “what, why, uncertainty, capacity effect, next action,
and authorization state” without reading internal schemas.

## Phase 11 — Hardening

- [x] Run migrations from empty and previous revision.
- [x] Run concurrency, rollback, idempotency, and failure-injection tests.
- [x] Scan repository/fixtures/logs for secrets and oracle imports.
- [x] Verify trace sensitive-data setting and error redaction.
- [x] Run full offline CI twice from a clean checkout.
- [x] Optionally run synthetic live-agent smoke tests when an authorized key exists.

Gate: reproducible clean build; no secrets; no external-action surface; all
material tests pass.

## Phase 12 — Evidence Package v0.1

- [ ] Record exact commit/version, dependency lock digest, migration head, and
  configuration profile.
- [ ] Export repository tree, setup/run instructions, architecture and agent maps.
- [ ] Export domain-to-code/test traceability.
- [ ] Include fixture/oracle manifests without exposing oracle to runtime.
- [ ] Include full conformity results, traces/log refs, failures/skips, known
  limitations, and exact remaining gaps.
- [ ] Mark implementation-conformity PASS only if the formal pass gate is met.

Gate: Founder/control-room handoff is complete. Deployment and live pilot remain
unauthorized.
