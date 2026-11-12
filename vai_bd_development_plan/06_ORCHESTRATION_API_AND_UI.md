# Orchestration, API, and Operator View

## 1. Cycle workflow

The deterministic state machine supports:

```text
DRAFT -> INPUTS_READY -> DISCOVERY_READY -> EVIDENCE_READY
-> ASSESSMENT_READY -> QUALIFIED_UNIVERSE_READY -> COMPARISON_READY
-> ALLOCATION_READY -> ACTION_PACKAGES_READY -> HUMAN_REVIEW_READY
```

`ACTIVE_REASSESSMENT`, `HELD`, and `CLOSED` are controlled side states. Persist
every transition with prior state, new state, trigger, actor, and exact refs.
Workflow state never substitutes for an authoritative business object.

## 2. Orchestrator phases

1. Bootstrap: require offer, valid market boundary/effective date, and persist
   capacity if available. Missing capacity blocks only capacity-dependent phases.
2. Discovery: call A1 and persist universe/candidate revisions.
3. Evidence: call A2 independently per candidate; local failures do not silently
   discard other candidates.
4. Gate: execute deterministic gate per candidate and assign block scope.
5. Assessment: call A3 only for `PROCEED` candidates.
6. Snapshot: freeze qualified exact opportunity revisions and explicitly list all
   excluded/unresolved candidates with reasons.
7. Comparison: generate pairs, call A4 comparison, validate completeness, derive
   inverses, detect cycles, persist priority state.
8. Allocation: require capacity and demand for every eligible opportunity; call A4
   allocation and verify deterministic arithmetic/invariants.
9. Actions: call A5 for relevant allocation/investigation items.
10. Readiness: calculate deterministic release readiness.
11. Human review: accept only authenticated human decision events.
12. Reassessment: create new revisions and propagate material impact narrowly.

The Orchestrator chooses when a specialist runs, never the commercial conclusion.

## 3. Idempotency and concurrency

All mutation/run endpoints accept an idempotency key. A repeated key returns the
same result or current operation status. Use optimistic expected-revision checks
and transaction locks for snapshot creation, supersession, comparison insertion,
and authorization decisions. Return conflict errors instead of overwriting work.

## 4. API surface

Minimum endpoints:

```text
POST   /decision-cycles
GET    /decision-cycles/{cycle_id}
POST   /decision-cycles/{cycle_id}/capacity-revisions
POST   /decision-cycles/{cycle_id}/discovery-runs
POST   /candidates/{candidate_ref}/evidence-runs
POST   /candidates/{candidate_ref}/eligibility-evaluations
POST   /candidates/{candidate_ref}/assessment-runs
POST   /decision-cycles/{cycle_id}/qualified-snapshots
POST   /qualified-snapshots/{snapshot_ref}/comparison-runs
POST   /qualified-snapshots/{snapshot_ref}/allocation-runs
POST   /allocations/{allocation_ref}/action-preparation-runs
POST   /commercial-actions/{cao_ref}/release-evaluations
POST   /commercial-actions/{cao_ref}/review-submissions
POST   /commercial-actions/{cao_ref}/authorization-decisions
GET    /commercial-actions/{cao_ref}/execution-eligibility
POST   /objects/{object_ref}/reassessment-evaluations
GET    /decision-cycles/{cycle_id}/operator-view
POST   /conformity-runs
GET    /conformity-runs/{run_id}
```

`object_ref` and other revision refs must contain identity and revision. Never use
an ambiguous “latest” ref in a mutation request.

## 5. API response/error rules

Return created object refs, workflow/run status, blocking reasons, and audit refs.
Use consistent errors for validation, missing dependency, stale revision,
authorization mismatch, held phase, conflict, agent failure, and policy failure.
Do not leak prompts, secrets, raw provider errors, or restricted evidence.

Long-running model-backed phases may return `202 Accepted` plus run ID; the local
MVP may execute synchronously behind the same service contract.

## 6. Human authorization service

Submission for review creates `PENDING_HUMAN_REVIEW`; it does not decide. A
decision request includes exact CAO ref, action, structured scope, and expected
current revision. Server identity supplies the actual human; clients cannot
self-assert it.

Reject approval when the CAO is superseded, reassessment-required, mismatched,
or the action/scope differs. A new CAO revision needs a new submission/decision.
Silence and timeout leave state non-approved.

## 7. Operator view

The baseline below is expanded by the
[frontend product specification](11_FRONTEND_PRODUCT_SPEC.md) and
[implementation handoff for Bassam](12_FRONTEND_IMPLEMENTATION_HANDOFF.md).
The expanded plan keeps the initial delivery read-only and server-rendered;
workflow and review forms follow separate backend-integration gates. The API
list above is a planning surface; use `src/vai_bd/api/router.py` and generated
OpenAPI for implemented paths and revision parameters.

Build a minimal read-only, server-rendered view after the API works. For each
cycle show:

- configured offer, market, cycle date, and capacity;
- coverage basis and limitations;
- full candidate disposition, including excluded/unresolved cases;
- qualified opportunities and qualitative comparative state;
- a separate allocation column for Act Now/deferred/investigate;
- reason, evidence summary, confidence by claim, contradictions, and uncertainty;
- Pursuit Demand and capacity consumption;
- next credible action and whether it is evidence gathering or pursuit;
- release readiness and human authorization as visibly separate states;
- revision, freshness, and reassessment warnings.

Never present a single lead score. Never make a lower-priority residual-capacity
selection look commercially superior. The UI has no external send/execute button
in the conformity build.

