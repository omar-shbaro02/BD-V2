# Requirements and Pre-Code Decisions

## 1. Product question

The system answers: given a configured offer, market, decision cycle, and
capacity envelope, which opportunities deserve attention first, why, and what
is the next credible action?

It is decision intelligence, not a CRM, scraper, lead warehouse, universal
scorer, or outreach bot.

## 2. Invariants enforced in types, policies, prompts, and tests

- Evidence is separate from interpretation.
- Fit is separate from Need.
- Confidence is separate from Priority.
- Decision-Owner Hypothesis is separate from Contactability.
- Contactability is separate from commercial attractiveness.
- Pursuit Demand is separate from commercial quality.
- Comparative Priority is separate from Capacity Allocation.
- Recommendation and Release Readiness are separate from Authorization.
- Capacity changes do not rewrite opportunity quality.
- Missing evidence is not negative evidence.
- Dependent repetitions are not independent corroboration.
- Contradictions and stale evidence remain visible.
- Ties, near-ties, indeterminate comparisons, and cycles are legitimate.
- No opaque score, hidden probability, or unsupported weighting may force order.

## 3. Actor and authority model

Define actor kinds: `SYSTEM`, `AGENT`, and `HUMAN`. Persist actor identity and
kind on every governed revision and audit event.

Only an authenticated `HUMAN` actor may create a decision event whose state is
`APPROVED`, `DECLINED`, or `RETURNED_FOR_REVISION`. Agent output schemas must not
contain `HumanAuthorizationState`; the Orchestrator has no method that fabricates
a human identity.

For conformity-only local development, use a test authentication adapter that
accepts a signed test principal. The production identity provider is deliberately
unspecified and out of scope. Never label the test adapter production-ready.

## 4. Conservative technical resolutions

These decisions fill mechanical gaps without changing business meaning:

1. A revision reference is `{object_id, revision}`. `supersedes_id` alone is
   insufficient, so store `supersedes_revision` too.
2. All governed datetimes are timezone-aware UTC in storage and ISO 8601 at the
   API boundary. Business effective dates remain explicit dates.
3. Decimal effort values are stored in a normalized base unit. Initially the
   accepted unit is `HOUR`; conversion must be deterministic if more units are
   later added.
4. `CommercialActionOpportunity` gains `authorized_scope` (structured JSON)
   because execution eligibility requires an exact scope match.
5. Human authorization records are append-only events, not ordinary agent-owned
   governed objects. A current-state projection may be derived from them.
6. Qualified snapshots contain exact Commercial Opportunity Case revision refs;
   snapshot membership never changes in place.
7. Agent outputs first enter a validated pending-output boundary. A service then
   creates domain revisions transactionally; agents never write directly to DB.
8. Material-impact decisions are explicit records with rationale and deciding
   actor/policy version. Unknown materiality defaults to review, not “unaffected.”
9. Model failures and validation failures end the phase as failed/held; they do
   not generate substitute judgments.
10. The portfolio specialist may produce comparison and allocation judgments in
    separate invocations of the same specialist definition, preserving the exact
    five-agent constraint.

## 5. Decisions that must be recorded before their code step

Create ADRs for the following. The suggested defaults are implementation-safe,
but approval is required if they affect governed meaning.

| Decision | Suggested default | Boundary |
|---|---|---|
| Fit judgment vocabulary | Qualitative enum plus rationale | Must not imply Need |
| Contactability vocabulary | `HIGH/MEDIUM/LOW/INDETERMINATE` | Never commercial value |
| Coverage status vocabulary | `PARTIAL/SUFFICIENT_FOR_CYCLE/INDETERMINATE` | Never claim exhaustive without evidence |
| Evidence currentness rule | Explicit as-of policy per source type | Stale preserved, not current |
| Materiality policy | Rule result or human review record | No LLM-only propagation authority |
| Release-readiness defects | Versioned checklist | Does not imply Authorization |
| Test identity mechanism | Signed local test principal | Not a production IdP |
| Default model configuration | Environment/config record | Not part of domain schema |

Do not invent numeric cutoffs for business quality. Mechanical time/date
thresholds are allowed only when explicitly configured and auditable.

## 6. Configuration, never constants

Operator, offer, intended buyers, geography, segment boundary, exclusions,
usable time, planning horizon, and pursuit limit belong to persisted cycle
configuration. The Fadi/Northern Virginia/6-hour/8-pursuit setup is a fixture or
seed configuration only.

## 7. Stop conditions

Stop implementation and report the exact conflict when:

- frozen requirements cannot be satisfied together;
- an unauthorized external provider or action becomes necessary;
- a sixth substantive reasoning agent would be required;
- Human Authorization cannot remain outside agents;
- a forbidden conceptual distinction must be collapsed;
- the Stage 15 source data needed to create faithful fixtures is absent.

The last condition is especially important: do not manufacture the detailed
synthetic evidence records from only the expected summary in the source pack.

