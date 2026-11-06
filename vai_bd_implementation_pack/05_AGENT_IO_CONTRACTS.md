# 05 — Specialist Agent Responsibilities and I/O Contracts

All five specialists are OpenAI API agents. Each has a narrow responsibility and must emit typed structured outputs.

# A1 — Market Discovery Specialist

## Decision purpose

Construct and revise the candidate universe for a defined market/offer without qualifying or prioritizing companies.

## Inputs

```yaml
decision_cycle_context
  - decision_cycle_id
  - target_market_boundary
  - segment_filters
  - exclusions
  - effective_date
offer_profile
existing_candidate_universe_optional
admissible_discovery_observations
```

Initially, `admissible_discovery_observations` may be synthetic fixtures or manually supplied records. Do not add unapproved external web/provider tools by default.

## Outputs

```yaml
candidate_universe_revision
coverage_state
coverage_basis
coverage_limitations
candidates:
  - candidate_identity
  - observed_market_presence
  - source_refs
added_candidates
removed_candidates
```

## Must never output

- Fit
- Need
- Qualification
- Priority
- Allocation
- Human Authorization

# A2 — Evidence Intelligence Specialist

## Decision purpose

Normalize, classify, and preserve evidence without converting evidence directly into commercial judgments.

## Inputs

```yaml
candidate_revision
decision_cycle_context
raw_evidence_observations
existing_evidence_records_optional
```

## Outputs

```yaml
evidence_records:
  - claim
  - source
  - source_type
  - source_date
  - provenance
  - directness
  - currentness
  - dependency_group
  - contradiction_links
  - admissibility
missing_evidence_flags
contradiction_groups
source_dependency_groups
```

## Must never output

- Fit conclusion
- Need conclusion
- opportunity priority
- allocation
- authorization

# A3 — Opportunity Intelligence Specialist

## Decision purpose

Turn admissible evidence into explicit, separated opportunity judgments for one candidate.

## Inputs

```yaml
decision_cycle_context
offer_profile
candidate_revision
gate_result
evidence_record_revisions
```

Precondition: gate outcome must permit substantive assessment.

## Outputs

```yaml
company_offer_fit
need_hypothesis
decision_owner_hypothesis
contactability_assessment
claim_confidences
qualification_outcome
commercial_opportunity_case
material_uncertainties
recommended_investigation_if_needed
```

## Required reasoning constraints

- Fit independent from proven Need.
- Decision-Owner independent from Contactability.
- Contactability independent from commercial attractiveness.
- Confidence attaches to claims, not overall opportunity value.
- Weak direct Need evidence may remain provisional instead of negative.

## Must never output

- portfolio allocation
- Act Now status
- Human Authorization

# A4 — Portfolio & Allocation Intelligence Specialist

## Decision purpose

Compare qualified Commercial Opportunity Cases and allocate scarce capacity without collapsing priority into effort.

## Inputs — comparison run

```yaml
qualified_universe_snapshot
commercial_opportunity_case_revisions
```

## Outputs — comparison

```yaml
canonical_pairwise_comparisons
comparative_priority_state
cycles
near_ties
indeterminate_sets
material_reasons
```

## Inputs — allocation run

```yaml
qualified_universe_snapshot
comparative_priority_state
pursuit_demand_revisions
capacity_envelope
```

## Outputs — allocation

```yaml
capacity_bounded_allocation_case
  - act_now
  - deferred_capacity
  - deferred_priority
  - investigate
  - capacity_consumption
  - marginal_reasons
  - material_uncertainties
  - alternative_portfolios_for_human_review
```

## Required constraints

- do not create opaque numeric lead scores;
- do not force total order when evidence supports tie/cycle/indeterminate;
- protect materially superior feasible opportunities first;
- lower-priority residual-capacity inclusion does not change commercial ordering;
- changing capacity cannot rewrite Fit/Need/evidence.

## Must never output

- Human Authorization
- external execution instruction

# A5 — Commercial Action Specialist

## Decision purpose

Translate a governed opportunity/allocation state into the next credible action package for human review.

## Inputs

```yaml
commercial_opportunity_case_revision
comparative_priority_state_ref
capacity_allocation_case_ref
decision_owner_hypothesis_ref
contactability_ref
material_uncertainties
```

## Outputs

```yaml
commercial_action_opportunity
  - action_type: EVIDENCE_GATHERING | COMMERCIAL_PURSUIT
  - action_description
  - decision_owner_ref
  - rationale
  - evidence_refs
  - material_uncertainties
  - optional_draft
```

## Required constraints

- action is recommendation only;
- a draft is not execution;
- do not create authorization state;
- do not send messages;
- do not mutate CRM;
- do not call external commercial-action tools.

# Human Authorization — NOT AN AGENT

Human Authorization is application state created from an authenticated human decision event.

Agents may request that a Commercial Action Opportunity be reviewed, but may never write `APPROVED` themselves.
