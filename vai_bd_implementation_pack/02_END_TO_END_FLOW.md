# 02 — End-to-End Decision Flow

## 1. Canonical flow

```text
Offer Profile
+ Target Market / Decision Cycle
+ Capacity Envelope
        |
        v
Candidate Universe / Coverage State
        |
        v
Company Candidate
        |
        v
Evidence Records
        |
        v
Minimum-Evidence / Hard-Eligibility Gate
        |
        +---- HOLD / INVESTIGATE / EXCLUDE when required
        |
        v
Company–Offer Fit
+ Need Hypothesis
+ Decision-Owner Hypothesis
+ Contactability Assessment
        |
        v
Evidence / Confidence / Contradiction Assessment
        |
        v
Qualification Outcome
        |
        +---- Further Investigation
        +---- Indeterminate Review
        +---- Disqualified
        |
        v
Commercial Opportunity Case
        |
        v
Pursuit Demand
        |
        v
Qualified Universe Snapshot
        |
        v
Canonical Pairwise Comparisons
        |
        v
Comparative Priority State
        |
        v
Capacity-Bounded Allocation Case
        |
        v
Commercial Action Opportunity
        |
        v
Recommendation Release Readiness
        |
        v
Human Review / Authorization (when external action proposed)
        |
        v
External Execution Eligibility
```

## 2. Orchestrator flow by phase

### Phase A — Cycle bootstrap

Required:

- Offer Profile
- target market / geography / segment boundary
- effective decision-cycle date
- Capacity Envelope

If market or capacity is missing, the Orchestrator must hold downstream operations that depend on it.

### Phase B — Discovery

Invoke **Market Discovery Specialist**.

Outputs:

- candidate records
- candidate-universe revision
- coverage state
- coverage limitations

The specialist does not qualify or prioritize.

### Phase C — Evidence normalization

For each candidate, invoke **Evidence Intelligence Specialist**.

Outputs:

- Evidence Records
- source lineage/dependence
- contradictions
- currentness
- direct/inferential classification
- explicit missing-evidence flags

The specialist does not decide Fit, Need, Priority, or Allocation.

### Phase D — Eligibility gate

Run deterministic / rule-backed checks using persisted evidence and Decision-Cycle Context.

Possible gate outcomes:

- Proceed
- Evidence Required
- Hard Exclusion
- Material Contradiction Blocks Assessment

The gate is a control object, not a full opportunity judgment.

### Phase E — Opportunity assessment

Invoke **Opportunity Intelligence Specialist** only for candidates allowed to proceed.

Outputs:

- Company–Offer Fit
- Need Hypothesis
- Decision-Owner Hypothesis
- Contactability Assessment
- claim-level confidence
- Qualification Outcome
- Commercial Opportunity Case

### Phase F — Qualified Universe

Create an immutable/versioned `QualifiedUniverseSnapshot` containing the exact Commercial Opportunity Case revisions eligible for comparison.

Do not compare against a moving universe without snapshot identity.

### Phase G — Comparative priority

Invoke **Portfolio & Allocation Intelligence Specialist** to author one canonical pairwise record per opportunity pair for the snapshot.

Rules:

- inverse relationships are derived;
- duplicate conflicting authored comparisons are invalid;
- comparison cycles are exposed;
- no total order is forced when evidence does not support one.

### Phase H — Capacity allocation

The same specialist uses:

- Comparative Priority State
- Pursuit Demand
- Capacity Envelope

Outputs:

- full qualified universe
- Act Now portfolio
- Deferred / Investigation tiers
- capacity consumed
- marginal inclusion/exclusion reasons
- material uncertainty

### Phase I — Commercial action

Invoke **Commercial Action Specialist** for the relevant allocation outputs.

Every recommendation explicitly labels the next credible action as either:

- further evidence gathering; or
- commercial pursuit.

Outputs may include a draft, but never execution.

### Phase J — Release readiness

Deterministic Orchestrator check.

`Release Ready` means ready to present to the authorized human.

It does not mean execution is authorized.

### Phase K — Human Authorization

Human-originated state only.

Possible states:

- Not Submitted
- Pending Human Review
- Approved
- Declined
- Returned for Revision

No model or system state may infer `Approved`.

### Phase L — Reassessment

Triggers include:

- new evidence
- contradiction resolution
- stale evidence
- changed capacity
- new candidate
- changed target market
- revised recommendation

The Orchestrator marks impacted revisions and propagates only through material dependencies.

## 3. Local vs portfolio vs whole-cycle blocking

### Local block

Affects one candidate/opportunity only.

Example: unresolved decision-owner evidence.

### Portfolio block

Affects comparison or allocation across multiple qualified opportunities.

Example: a shared source becomes unreliable across C01, C02, C04.

### Whole-cycle block

Affects governing cycle context.

Example: missing/invalid target-market boundary.

The Orchestrator controls block scope. Specialists do not self-declare whole-cycle authority.
