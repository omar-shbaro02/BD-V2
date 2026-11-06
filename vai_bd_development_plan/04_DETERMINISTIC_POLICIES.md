# Deterministic Policy Plan

All policies in this file are code-owned, versioned, side-effect-free where
possible, and unit-tested without model calls.

## 1. Evidence policies

- Validate provenance, source date/observation date, directness, currentness,
  admissibility, and dependency group.
- A restricted or unknown-admissibility record cannot satisfy an admissible
  evidence requirement.
- Group shared underlying claims; count the group once when independence matters.
- Preserve contradiction edges bidirectionally in presentation even if one
  canonical edge is stored.
- Compute currentness only from configured, auditable rules; never delete stale
  evidence.
- Represent missing evidence explicitly and never turn it into negative evidence.

## 2. Minimum-evidence / hard-eligibility gate

Inputs: exact candidate revision, decision-cycle revision, market boundary,
exclusions, and eligible evidence revisions.

Precedence must be specified and tested. Safe behavior:

1. Missing/invalid governing market boundary -> whole-cycle hold.
2. Material unresolved contradiction that prevents the check -> contradiction
   block at the narrowest valid scope.
3. Known hard exclusion supported by admissible evidence -> hard exclusion.
4. Insufficient admissible/current minimum evidence -> evidence required.
5. Otherwise -> proceed.

The result may not say Qualified or author commercial judgments.

## 3. Revision/currentness policy

Reject a downstream run when a required upstream ref is missing, superseded,
or marked reassessment-required. Historical queries may read it, but new
governed outputs may not treat it as current.

## 4. Snapshot and comparison policies

- Snapshot creation includes only exact revisions with `QUALIFIED` outcomes.
- Preserve excluded/unresolved refs and reasons alongside the comparison set.
- Generate `n*(n-1)/2` unordered pairs deterministically.
- Canonicalize pair identity independent of authoring/display direction.
- Store one authored relationship; derive its inverse for display.
- `TIE`, `NEAR_TIE`, and `INDETERMINATE` are symmetric.
- Detect strongly connected components in strict-above relations.
- Never topologically force a total order across ties, indeterminate sets, or
  cycles.

## 5. Capacity/allocation policies

Normalize capacity and demand to the same unit and planning horizon. Account for
fixed commitments before allocatable capacity. Enforce maximum meaningful
concurrent pursuits independently from time.

Allocation consumes the specialist-authored qualitative priority state; code
validates arithmetic and invariants. It must:

- protect materially superior feasible opportunities;
- allow a lower-priority item to use residual capacity when a higher-priority
  action cannot fit;
- retain the original priority relation;
- distinguish `deferred_capacity` from `deferred_priority`;
- avoid optimizing action count, company count, shortest duration, or utilization;
- return materially unresolved alternatives for human review;
- hold allocation when a material comparison cycle makes selection indefensible.

Test exact decimal arithmetic, zero residual capacity, fixed commitments,
concurrency caps, an oversized top priority, smaller credible alternatives, and
unit/horizon mismatch rejection.

## 6. Release readiness

Calculate from a versioned checklist:

- all required exact upstream revisions exist and are current;
- contradictions and limitations are disclosed;
- action type, description, scope, rationale, and evidence refs are present;
- allocation is valid when the recommendation depends on allocation;
- no unresolved defect could invalidate the recommendation.

Output only `NOT_READY`, `READY_WITH_DISCLOSED_LIMITATIONS`, or `RELEASE_READY`.
Never inspect authorization to determine readiness, and never interpret readiness
as approval.

## 7. External execution eligibility

Return true only when all conditions hold:

```text
authorization state == APPROVED
authorization exact CAO revision == requested CAO revision
authorized action == requested action
authorized scope == requested scope
actual deciding actor is authenticated HUMAN
decision timestamp exists
CAO and all execution-critical dependencies are CURRENT
CAO is not superseded
no applicable reassessment is required
external-action restriction allows this action
```

The conformity profile always makes the last condition false. Persist the
decision and reasons, not a manually editable eligibility flag.

## 8. Reassessment propagation

Traverse the revision dependency graph breadth-first from a material change.
For each direct dependent, run the versioned material-impact rule or create a
human-review request. Mark and continue only through materially affected nodes.
Record unaffected decisions too, including rationale, so bounded propagation is
auditable.

Special rules:

- Capacity revision -> allocation and dependent actions/readiness only; never Fit,
  Need, evidence, or commercial quality solely due to capacity.
- New candidate -> universe revision; if qualified, new snapshot and portfolio
  chain; historical snapshots unchanged.
- Source unreliability -> all evidence in the dependency group and only materially
  dependent downstream objects.
- Revised CAO -> old authorization remains historical and cannot transfer.
- Staleness -> evidence and material dependents become reassessment-required.

## 9. Mandatory property/invariant tests

- Inverse comparison of inverse comparison equals original.
- Pair count is exact and order-independent.
- Capacity changes never alter stored priority relations.
- Revision append never deletes history.
- Unknown/missing evidence never becomes disqualifying negative evidence.
- No non-human path can create an approved authorization event.
- Execution is always false in conformity configuration.
- Reassessment never marks an object with no dependency path from the change.

