# 01 — Governing Baseline and Non-Negotiable Business Logic

## 1. Product identity

**VAI Business Development Decision Intelligence** is a governed system for deciding:

> Given available BD capacity, which opportunities in the target market deserve attention first for the offer being taken to market, why, and what is the next credible commercial action?

The product is **not** fundamentally a lead database, scraper, CRM, outreach bot, generic sales platform, or universal lead-scoring engine.

## 2. First controlled-proof context

Pilot-instance configuration only:

- Operator: Fadi
- Market: Northern Virginia, United States
- Initial offer: VAI Construction / Project Control Decision Intelligence
- Approximate usable BD time: 6 hours/week
- Approximate meaningful concurrent pursuits: 8

These values must be configurable and must never become product constants.

## 3. Core reasoning invariants

The implementation MUST preserve the following separations:

- Evidence ≠ Interpretation
- Fit ≠ proven Need
- Confidence ≠ Priority
- Decision-Owner Hypothesis ≠ Contactability
- Contactability ≠ commercial attractiveness
- Pursuit Demand ≠ commercial quality
- Comparative Priority ≠ Capacity Allocation
- Recommendation ≠ Authorization
- Capacity constraint ≠ opportunity quality

Do not implement a single opaque score that collapses these concepts.

## 4. Evidence rules

Every material Evidence Record must preserve at minimum:

- source
- source type
- date
- provenance
- currentness
- direct vs inferential status
- source dependence / shared underlying claim
- contradiction relationships
- object revision / validity

Rules:

- repeated reporting of one underlying claim is not independent corroboration;
- missing evidence is not negative evidence;
- contradictory evidence is preserved, never averaged away;
- stale evidence is not current evidence;
- restricted or unauthorized evidence must not be silently consumed.

## 5. Qualification rules

The first gate is the **Minimum-Evidence / Hard-Eligibility Gate**. It may determine only:

- whether minimum evidence exists to continue;
- whether the company is inside the target-market boundary;
- whether a known hard exclusion applies;
- whether contradiction prevents further assessment.

It must not declare full commercial qualification before substantive opportunity assessment.

Qualification Outcome values:

- Qualified for comparative commercial consideration
- Further Investigation Required
- Disqualified by Known Evidence
- Indeterminate Pending Material Review

Distinction:

- **Further Investigation Required** = a specific, actionable, potentially resolvable evidence gap exists.
- **Indeterminate Pending Material Review** = ambiguity, contradiction, or unresolved judgment prevents reliable qualification and requires material review.

Strong Fit with weak direct Need evidence may remain qualified, but Need must remain provisional and claim-level confidence reduced.

## 6. Comparison rules

Comparative reasoning is qualitative and explicit.

Allowed comparison states should support at least:

- Materially Above
- Above
- Near Tie
- Tie
- Below
- Materially Below
- Indeterminate

Rules:

- contactability may break genuinely close comparisons but cannot displace materially stronger commercial opportunity quality;
- confidence is support for a claim, not opportunity value;
- Pursuit Demand is resource requirement, not commercial value;
- ties, near-ties, indeterminate comparisons, and cycles are valid outcomes;
- no hidden probability or unsupported numeric weight may be used to force ranking.

## 7. Capacity-allocation rules

For every qualified opportunity, represent the approximate time/attention required for its next credible action.

Allocation must:

- protect materially superior feasible opportunities first;
- use Pursuit Demand to test feasibility, sequence actions, compare commercially comparable opportunities, and use residual capacity;
- never maximize company count, action count, shortest duration, or capacity utilization as a hidden proxy for value;
- allow a lower-priority opportunity to enter Act Now when a higher-priority action cannot fit, without relabeling the lower-priority case as commercially superior;
- return materially unresolved portfolio alternatives for human review rather than choose arbitrarily.

Capacity changes may change allocation and sequence. They must not silently change Fit, Need, evidence, confidence, or commercial quality.

## 8. Human authorization rules

The following do NOT authorize external execution:

- Act Now
- Release Ready
- high priority
- high confidence
- generated draft
- recommendation
- user opening/viewing output
- silence
- timeout

External execution requires explicit Human Authorization tied to:

- exact Commercial Action Opportunity revision
- exact action
- exact scope
- deciding human
- decision timestamp

Revision integrity:

- R1 approval does not authorize materially revised R2.
- If R2 supersedes R1, historical R1 approval remains auditable but does not preserve new execution eligibility for superseded R1.

## 9. Reassessment rules

Reassessment is bounded by material dependency propagation.

When an upstream object changes:

1. identify the changed revision;
2. identify dependent downstream revisions;
3. mark materially affected objects `Reassessment Required`;
4. leave unaffected objects current;
5. propagate only as far as material impact reaches.

Do not blindly rerun the entire cycle.

## 10. Product/implementation boundary

Implementation is authorized, but the following remain unauthorized unless separately approved:

- live pilot execution
- production deployment
- paid providers
- paid APIs
- scraping
- restricted automated extraction
- automated outreach
- bulk messaging
- CRM execution
- autonomous external action

The OpenAI API is selected as the agent runtime by current implementation direction; this does not imply authorization for unrelated external providers or external commercial execution.
