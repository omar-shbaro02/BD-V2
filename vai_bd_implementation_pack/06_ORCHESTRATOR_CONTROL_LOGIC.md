# 06 — Deterministic Orchestrator and Control Logic

## 1. Principle

The Orchestrator is control-plane software.

It owns:

- sequencing
- dependency validation
- admissibility
- currentness checks
- hold/release logic
- reassessment propagation
- specialist invocation
- state persistence
- release-readiness calculation

It does not own substantive commercial intelligence.

## 2. State machine

Suggested cycle-level states:

```text
DRAFT
INPUTS_READY
DISCOVERY_READY
EVIDENCE_READY
ASSESSMENT_READY
QUALIFIED_UNIVERSE_READY
COMPARISON_READY
ALLOCATION_READY
ACTION_PACKAGES_READY
HUMAN_REVIEW_READY
ACTIVE_REASSESSMENT
HELD
CLOSED
```

These are implementation workflow states, not substitutes for authoritative business object states.

## 3. Dependency checks

### Before discovery

Require:

- Offer Profile
- target market boundary
- decision-cycle effective date

### Before eligibility gate

Require:

- candidate revision
- evidence set
- target-market boundary

### Before opportunity assessment

Require gate outcome = `PROCEED`.

### Before Qualified Universe Snapshot

Require explicit Qualification Outcome for each included opportunity.

### Before comparisons

Require immutable snapshot revision and exact opportunity-case revisions.

### Before allocation

Require:

- comparative state
- Pursuit Demand for each eligible opportunity
- current Capacity Envelope

### Before Commercial Action Opportunity

Require relevant opportunity, comparison, and allocation references.

### Before Release Ready

Require:

- required upstream objects current;
- material contradictions represented;
- no unresolved defect that could invalidate the recommendation;
- allocation state defensible where relevant.

Human Authorization is NOT required for Release Ready.

## 4. Deterministic external execution eligibility

Even though external execution is currently disabled, implement the policy function and test it.

Pseudo-rule:

```python
def eligible_for_external_execution(cao, auth, restrictions):
    return (
        auth.state == "APPROVED"
        and auth.cao_revision_ref == cao.revision_ref
        and auth.authorized_action == cao.action_description
        and auth.authorized_scope == cao.scope
        and cao.validity == "CURRENT"
        and not cao.reassessment_required
        and not cao.is_superseded
        and restrictions.allow_external_execution
    )
```

In the current build, `restrictions.allow_external_execution` must be `False`.

## 5. Reassessment propagation

Maintain a dependency graph of object revision refs.

On material upstream change:

```text
changed object
   |
   v
find direct dependents
   |
   v
material impact check
   |
   +-- no --> leave current
   |
   +-- yes --> mark Reassessment Required
                   |
                   v
             continue downstream
```

Special cases:

### Capacity changes

Reassess:

- Pursuit feasibility if dependent
- Allocation Case
- affected Commercial Action Opportunities

Do NOT reassess Fit/Need solely because capacity changed.

### New candidate

Create new Candidate Universe revision and, if qualified, new Qualified Universe Snapshot revision.

Do not mutate historical snapshots.

### Contradiction resolution

Reassess only claims and downstream objects that relied on the contradiction.

## 6. Comparison consistency checks

Enforce:

- one authored canonical comparison per unordered pair per snapshot;
- no contradictory duplicate authoring;
- explicit subject/comparator revisions;
- inverse derived in display layer;
- cycle detection.

If a material cycle affects allocation, allocation must be held or routed to human review.

## 7. Error philosophy

Fail visibly.

Never silently:

- invent missing capacity;
- invent market boundaries;
- drop unresolved opportunities;
- convert missing evidence to disqualification;
- convert model failure to positive result;
- auto-authorize action.
