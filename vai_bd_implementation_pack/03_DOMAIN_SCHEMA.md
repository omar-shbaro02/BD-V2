# 03 — Canonical Domain Schema

This file defines the minimum logical schema. Technical tables/classes may differ, but business meaning must remain equivalent.

## 1. Common object envelope

Every governed mutable business object should contain:

```yaml
id: UUID
object_type: string
revision: integer
supersedes_id: UUID | null
validity: CURRENT | SUPERSEDED | REASSESSMENT_REQUIRED
created_at: datetime
created_by: actor_ref
effective_at: datetime | null
derived_from:
  - object_revision_ref
dependencies:
  - object_revision_ref
reassessment_trigger: string | null
reassessment_reason: string | null
```

### Rules

- `id + revision` identifies a specific business revision.
- A new material version must not overwrite historical meaning.
- Dependencies are revision-specific.
- Superseded records remain auditable.

## 2. Core objects

### OfferProfile

Purpose: define the offer being taken to market.

Minimum fields:

```yaml
offer_id
name
problem_statement
intended_buyer_roles
fit_dimensions
known_exclusions
version
```

### DecisionCycleContext

```yaml
decision_cycle_id
offer_ref
target_market_boundary
segment_filters
exclusions
effective_date
operator_ref
status
```

### CapacityEnvelope

```yaml
capacity_id
decision_cycle_ref
usable_time
unit
planning_horizon
max_meaningful_concurrent_pursuits
fixed_commitments
review_trigger
effective_date
```

### CandidateUniverseCoverageState

```yaml
universe_id
decision_cycle_ref
revision
coverage_basis
coverage_limitations
candidate_refs
added_candidates
removed_candidates
coverage_status
```

### CompanyCandidate

```yaml
candidate_id
universe_ref
company_name
market_presence_claims
segment_claims
source_refs
candidate_status
```

### EvidenceRecord

```yaml
evidence_id
candidate_ref
claim_text
source_uri_or_ref
source_type
source_date
observed_at
provenance
directness: DIRECT | INFERENTIAL
currentness: CURRENT | STALE | UNKNOWN
source_dependency_group: string | null
contradicts:
  - evidence_ref
admissibility: ADMISSIBLE | RESTRICTED | UNKNOWN
```

### MinimumEvidenceHardEligibilityGateResult

```yaml
gate_id
candidate_ref
decision_cycle_ref
outcome: PROCEED | EVIDENCE_REQUIRED | HARD_EXCLUSION | CONTRADICTION_BLOCK
reasons
blocking_scope: LOCAL | PORTFOLIO | WHOLE_CYCLE
```

### CompanyOfferFit

```yaml
fit_id
candidate_ref
offer_ref
judgment
rationale
evidence_refs
claim_confidence
```

### NeedHypothesis

```yaml
need_id
candidate_ref
hypothesis
status: SUPPORTED | PROVISIONAL | INSUFFICIENT | CONTRADICTORY
rationale
evidence_refs
claim_confidence
```

### DecisionOwnerHypothesis

```yaml
decision_owner_id
candidate_ref
role_hypothesis
named_person_ref_optional
rationale
evidence_refs
claim_confidence
```

### ContactabilityAssessment

```yaml
contactability_id
candidate_ref
assessment
known_paths
constraints
rationale
evidence_refs
claim_confidence
```

### QualificationOutcome

```yaml
qualification_id
candidate_ref
outcome:
  QUALIFIED
  FURTHER_INVESTIGATION_REQUIRED
  DISQUALIFIED_BY_KNOWN_EVIDENCE
  INDETERMINATE_PENDING_MATERIAL_REVIEW
rationale
investigation_action_optional
material_review_reason_optional
```

### CommercialOpportunityCase

```yaml
opportunity_case_id
candidate_ref
offer_ref
fit_ref
need_ref
decision_owner_ref
contactability_ref
qualification_ref
commercial_rationale
material_uncertainties
```

### PursuitDemand

```yaml
pursuit_demand_id
opportunity_case_ref
next_action_description
estimated_effort
unit
smaller_credible_action_available: bool
rationale
```

### QualifiedUniverseSnapshot

```yaml
snapshot_id
decision_cycle_ref
snapshot_revision
opportunity_case_revision_refs
excluded_or_unresolved_refs_with_reasons
created_at
```

### CanonicalPairwiseComparison

Canonical identity = unordered pair + snapshot.

```yaml
comparison_id
snapshot_ref
subject_opportunity_revision
comparator_opportunity_revision
relationship:
  MATERIALLY_ABOVE
  ABOVE
  NEAR_TIE
  TIE
  BELOW
  MATERIALLY_BELOW
  INDETERMINATE
material_reason
secondary_factors
```

Only one authored canonical comparison may exist for the pair. Inverse display values are derived.

### ComparativePriorityState

```yaml
priority_state_id
snapshot_ref
partial_order
cycles
near_ties
indeterminate_sets
material_reasons
```

### CapacityBoundedAllocationCase

```yaml
allocation_case_id
snapshot_ref
capacity_envelope_ref
priority_state_ref
act_now:
  - opportunity_revision_ref
deferred_capacity:
  - opportunity_revision_ref
deferred_priority:
  - opportunity_revision_ref
investigate:
  - opportunity_revision_ref
capacity_consumption
marginal_reasons
material_uncertainties
alternative_portfolios_for_human_review
```

### CommercialActionOpportunity

```yaml
cao_id
opportunity_case_ref
comparative_priority_ref
allocation_case_ref
action_type: EVIDENCE_GATHERING | COMMERCIAL_PURSUIT
action_description
decision_owner_ref
material_uncertainties
draft_content_optional
release_readiness_ref
```

### RecommendationReleaseReadiness

```yaml
release_id
cao_revision_ref
state: NOT_READY | READY_WITH_DISCLOSED_LIMITATIONS | RELEASE_READY
blocking_conditions
limitations
```

### OpportunityState

Lifecycle only:

```yaml
state:
  CANDIDATE
  ASSESSMENT_ACTIVE
  MONITORING
  REASSESSMENT_REQUIRED
  INACTIVE_FOR_CURRENT_DECISION_CYCLE
  ARCHIVED
```

Do not put Qualified, Act Now, Human Review Required, or Authorized for Pursuit here as authoritative states.

### HumanAuthorizationState

```yaml
authorization_id
cao_revision_ref
state:
  NOT_SUBMITTED
  PENDING_HUMAN_REVIEW
  APPROVED
  DECLINED
  RETURNED_FOR_REVISION
requested_human_authority_ref
actual_deciding_human_ref_optional
decision_timestamp_optional
authorized_action_optional
authorized_scope_optional
```

## 3. External execution eligibility

Do not store execution eligibility as a single manually editable approval flag.

Derive it from:

```text
HumanAuthorization == APPROVED
AND exact CAO revision matches
AND exact action matches
AND exact scope matches
AND CAO/object validity == CURRENT
AND no applicable REASSESSMENT_REQUIRED
AND not superseded by a material newer revision
AND no external-action restriction blocks the action
```

## 4. Confidence

Confidence belongs to the relevant claim/judgment.

Allowed qualitative levels:

- High
- Medium
- Low
- Indeterminate

Every confidence value must have a rationale and linked evidence.

Never create one global blended confidence score for the opportunity.
