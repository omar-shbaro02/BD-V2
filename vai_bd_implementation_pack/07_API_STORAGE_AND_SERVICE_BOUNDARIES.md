# 07 — API, Persistence, and Service Boundaries

## 1. Recommended initial stack

Recommended for the new build:

- Python 3.11+
- FastAPI
- Pydantic v2
- PostgreSQL for persistent governed state
- SQLAlchemy 2.x + Alembic
- OpenAI Agents SDK for the five specialist agents
- pytest for conformity tests
- optional React/Vite UI later; not required for first conformity milestone

The stack is an implementation recommendation. The frozen business meaning is authoritative.

## 2. Service modules

Suggested repository structure:

```text
app/
  api/
    decision_cycles.py
    candidates.py
    evidence.py
    opportunities.py
    portfolio.py
    actions.py
    authorizations.py
    conformity.py
  domain/
    models.py
    enums.py
    policies.py
    dependencies.py
  agents/
    market_discovery.py
    evidence_intelligence.py
    opportunity_intelligence.py
    portfolio_allocation.py
    commercial_action.py
    prompts/
  orchestrator/
    cycle_runner.py
    gates.py
    reassessment.py
    release_readiness.py
    execution_policy.py
  persistence/
    models.py
    repositories.py
    migrations/
  tests/
    fixtures/stage15/
    oracle/stage15/
    conformity/
```

## 3. API boundary examples

### Decision cycle

- `POST /decision-cycles`
- `GET /decision-cycles/{id}`
- `POST /decision-cycles/{id}/run-discovery`
- `POST /decision-cycles/{id}/run-assessment`
- `POST /decision-cycles/{id}/run-comparison`
- `POST /decision-cycles/{id}/run-allocation`
- `POST /decision-cycles/{id}/prepare-actions`

These endpoints should create or invoke governed revisions, not mutate one giant state blob.

### Human authorization

- `POST /commercial-actions/{cao_revision}/submit-for-review`
- `POST /commercial-actions/{cao_revision}/authorization-decisions`

Authorization endpoint must require authenticated human identity.

## 4. Persistence guidance

Prefer append/revision semantics for governed objects.

Avoid destructive in-place updates for material reasoning objects.

Suggested relational pattern:

```text
object_identity table
object_revision table
specific typed tables / JSONB payloads
explicit dependency edge table
explicit supersession edge
trace table
```

A simpler schema is acceptable if it still preserves exact revision lineage and dependencies.

## 5. Agent-run audit table

Minimum fields:

```yaml
run_id
agent_name
prompt_version
model_config
input_revision_refs
output_revision_refs
openai_trace_ref
status
error
started_at
completed_at
usage_metadata
```

## 6. Deterministic calculations

Keep these outside the LLM wherever practical:

- capacity arithmetic
- pair generation
- duplicate comparison detection
- inverse comparison derivation
- cycle detection
- revision checks
- supersession/currentness validation
- authorization matching
- blocking-scope propagation

Agents supply bounded qualitative judgments; code enforces invariants.

## 7. Configuration

Do not hard-code:

- Fadi
- Northern Virginia
- VAI Construction
- 6 hours/week
- 8 pursuits

Store them as Decision-Cycle / Offer / Capacity configuration.

## 8. Secrets

Use environment variables / secret manager.

Minimum current secret:

- `OPENAI_API_KEY`

Do not commit `.env` files or credentials.
