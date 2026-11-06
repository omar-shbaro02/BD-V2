# Domain and Persistence Plan

## 1. Modeling rule

Use separate Pydantic models for separate business concepts even when fields
look similar. Never replace Fit, Need, Confidence, Priority, Demand, Allocation,
Readiness, and Authorization with a shared score/status abstraction.

Every governed model has an immutable revision envelope:

```text
object_id, object_type, revision, validity,
supersedes_ref?, created_at, created_by, effective_at?,
derived_from[], dependencies[], reassessment_trigger?, reassessment_reason?
```

Use `frozen=True` Pydantic models where practical. Mutation means creating a new
revision in one transaction.

## 2. Domain types to implement

Implement every source object:

- Configuration: `OfferProfile`, `DecisionCycleContext`, `CapacityEnvelope`.
- Discovery: `CandidateUniverseCoverageState`, `CompanyCandidate`.
- Evidence/control: `EvidenceRecord`, `MissingEvidenceFlag`,
  `ContradictionGroup`, `MinimumEvidenceHardEligibilityGateResult`.
- Opportunity: `CompanyOfferFit`, `NeedHypothesis`,
  `DecisionOwnerHypothesis`, `ContactabilityAssessment`, claim-scoped
  `ConfidenceAssessment`, `QualificationOutcome`, `CommercialOpportunityCase`,
  `PursuitDemand`, and `OpportunityState`.
- Portfolio: `QualifiedUniverseSnapshot`, `CanonicalPairwiseComparison`,
  `ComparativePriorityState`, `CapacityBoundedAllocationCase`.
- Action: `CommercialActionOpportunity`, `RecommendationReleaseReadiness`.
- Human control: `HumanAuthorizationEvent` and derived current state.
- Audit/control: `AgentRun`, `WorkflowTransition`, `MaterialImpactDecision`,
  `ExternalExecutionEligibilityDecision`, `ConformityCaseResult`.

All qualitative conclusions require rationale. All material claims require exact
evidence revision references. Confidence requires claim ref, level, rationale,
and evidence refs.

## 3. Enum families

Implement at minimum the exact source values for validity, evidence directness,
currentness, admissibility, gate outcome, blocking scope, Need status,
qualification outcome, comparison relationship, action type, release readiness,
opportunity lifecycle, authorization state, cycle workflow state, and run status.

Never reuse lifecycle state for qualification, allocation, review, or approval.
Never permit `APPROVED` in any agent-facing enum/schema.

## 4. Relational schema

Use explicit relational control tables plus typed JSON or typed tables for
payloads. Minimum tables:

```text
actors
object_identities
object_revisions
object_dependencies
object_supersessions
domain_payloads
candidate_universe_members
snapshot_members
canonical_comparisons
allocation_members
human_authorization_events
agent_runs
workflow_transitions
material_impact_decisions
conformity_case_results
```

Required constraints:

- unique `(object_id, revision)`;
- one `CURRENT` revision per identity where applicable;
- dependency endpoints reference exact existing revisions;
- supersession predecessor and successor share identity and object type;
- successor revision is greater than predecessor;
- one authored comparison per `(snapshot_id, snapshot_revision, unordered pair)`;
- a comparison cannot compare an opportunity with itself;
- both comparison members belong to the referenced snapshot;
- snapshot membership is immutable after creation;
- authorization references one exact CAO revision;
- final human decision requires actual human, timestamp, action, and scope;
- agent-run status and timestamps are internally consistent.

Use database constraints where possible and repeat critical validation in domain
policies for clear errors.

## 5. Revision transaction

For every material revision:

1. Lock/read the current revision.
2. Validate the caller and expected revision to prevent lost updates.
3. Validate all dependency refs exist and are eligible for use.
4. Insert the successor payload and revision envelope.
5. Mark the predecessor `SUPERSEDED`.
6. Insert the supersession edge.
7. Evaluate direct dependent materiality.
8. Mark affected dependents `REASSESSMENT_REQUIRED` and record why.
9. Write audit/workflow events.
10. Commit atomically; roll back the whole operation on error.

Non-material metadata corrections need a defined policy. Never use them to alter
the meaning of a historical governed decision.

## 6. Repository interfaces

Provide repositories for:

- get exact revision; get current revision; append revision;
- list dependencies/dependents recursively;
- supersede with optimistic concurrency;
- create/fetch immutable snapshots;
- insert and validate canonical comparisons;
- append authorization events and derive current state;
- record agent runs, workflow transitions, materiality decisions, and conformity
  results.

No repository method named generic `update` should exist for governed revisions.

## 7. Migration sequence

1. Actors and object identity/revision controls.
2. Dependency and supersession edges.
3. Domain payload storage and membership tables.
4. Comparison and allocation constraints.
5. Human authorization events.
6. Agent/audit/workflow tables.
7. Conformity results and indexes.

For every migration, test upgrade from empty, downgrade in development, and
upgrade from the immediately previous schema. Evidence-package output reports
the current Alembic head.

