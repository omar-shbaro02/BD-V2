# Architecture Status

The architecture is defined by the frozen implementation pack and expanded in
the development plan. The implemented modular monolith now includes FastAPI,
deterministic policies and workflow services, PostgreSQL revision/audit and
idempotency persistence, and five bounded OpenAI Agents SDK specialists invoked
through an application-owned runner boundary.

No external action integration is present. The orchestrator owns sequencing,
exact-current dependency checks, scoped holds, persistence, and reassessment; it
does not author commercial judgments or Human Authorization.

## Service and authority map

```text
Authenticated human -> FastAPI schemas/auth -> application service port
                                            -> cycle/workflow services
                                            -> exact-revision repositories -> PostgreSQL
                                            -> specialist runner -> five typed specialists
                                            -> deterministic policy validation
Operator HTML/JSON <- read-only presentation contracts
```

`api/contracts.py:ApiBackend` is the injectable service boundary; the default
backend fails closed until a host wires an implementation. `services/cycles.py`
coordinates persisted operations, `services/executor.py` owns transactional
agent execution and idempotency, and `services/lifecycle.py` owns deterministic
readiness, review and reassessment. `orchestrator/` checks sequencing, inputs and
hold scope. `persistence/` retains exact revisions and append-only audit history.

## Specialist responsibility map

| Specialist | Typed responsibility | Tools/handoffs |
|---|---|---|
| Market Discovery | Candidate universe and coverage limitations | None |
| Evidence Intelligence | Provenance, currentness, admissibility and evidence gaps | None |
| Opportunity Intelligence | Separate Fit, Need, owner, contactability and qualification judgments | None |
| Portfolio and Allocation | Separate canonical comparisons and capacity allocation operations | None |
| Commercial Action | Next credible action and draft recommendation | None |

Definitions are in `agents/definitions.py`; contracts and semantic guards are in
`agents/contracts.py` and `agents/validation.py`. The prompt manifest records
versions/digests. Model selection is configuration; evidence-package verification
uses captured deterministic doubles and makes no live-model claim.

## Conformity and handoff boundary

`conformity/` consumes runtime fixtures only. The evaluator scripts serialize
actuals before reading held-out expected outcomes. The evidence package contains
both fixture and oracle directories for reviewer use; it must never become a
runtime input directory. Generated logs, JUnit results, exact source inventory,
agent inventory and traceability are SHA-256 bound in the package manifest.

