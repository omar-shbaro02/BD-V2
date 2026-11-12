# Operator frontend product specification

Status: implementation brief for Bassam; not an implementation-completion claim.
Requested scope: expand the operator experience using the existing Python backend.
Read with [the technical handoff](12_FRONTEND_IMPLEMENTATION_HANDOFF.md).

## 1. Purpose and authority

The user must be able to decide what deserves attention, why, what remains
uncertain, what fits available capacity, and what the next credible action is.
They must also see whether an action is ready for review and whether a human
has authorized its exact revision and scope.

This brief elaborates the existing operator requirement. It preserves the
frozen implementation pack and its business distinctions. It authorizes planning
and local implementation of a richer interface, not a live pilot, deployment,
external execution, or changes to the five specialist responsibilities.
The frozen roadmap's instruction not to start with a polished frontend remains
the historical sequencing rule; backend and conformity work precede this work.

Use FastAPI server-rendered pages, Python presentation models, HTML, CSS, and
small progressive-enhancement JavaScript modules. A separate React/Vite app is
not required. PostgreSQL and SQLAlchemy remain behind application services;
browser code never accesses the database or OpenAI directly.

## 2. Users and main journey

The primary user is the business-development operator who configures a cycle,
reviews the discovered candidate universe, understands evidence and opportunity
judgments, and plans work within capacity. The human reviewer makes explicit
authorization decisions. These are interaction responsibilities, not a claim
that a production role/permission system already exists.

Primary journey:

1. Open Decision cycles and select the relevant offer, market, and effective date.
2. Read coverage limitations and active warnings before interpreting results.
3. Review the attention summary, then inspect the evidence behind an opportunity.
4. Compare commercial priority with the separate capacity allocation decision.
5. Inspect the next action, release readiness, and human authorization separately.
6. In the later integrated workflow, configure inputs, run an eligible phase,
   and submit or decide a review through authenticated server operations.

## 3. Navigation and screen structure

Keep `/operator` as the cycle index and `/operator/cycles/{cycle_id}` as the
cycle workspace. Use section anchors initially; do not invent new API resources
just to create tabs. Deep links to sections and opportunity revisions must work
without JavaScript. Keep the selected cycle visible in the page heading.

Workspace navigation: Overview, Candidates, Opportunities, Priority & Capacity,
Next Actions. Put revision and provenance details in contextual disclosures.
Workflow setup and review forms are a later delivery gate, not hidden controls
on the initial read-only interface.

### A. Decision cycles

Show offer name, market boundary, effective date, workflow state, opportunity
count, and warning count from `OperatorCycleSummary`. Make the offer/cycle link
the primary interaction. Display exact cycle revision in an expandable detail.

Provide search by offer/market and filters by workflow state using only supplied
values. Preserve filter values in the URL. Include Clear filters, visible result
count, no-cycle and no-match states. Filtering must not change persisted data.
Do not claim portfolio totals across cycles or completeness of a paginated list
unless the backend supplies the required coverage and totals.

### B. Cycle overview

At the top show offer name and summary, market boundary, effective date, workflow
state, cycle revision, planning horizon, available capacity with unit, and maximum
concurrent pursuits. Display coverage basis, status, and limitations nearby.

Place revision, freshness, and reassessment warnings above decision summaries.
Use an attention list grouped by recorded reassessment warnings, uncertainty,
investigation allocation, and review state. These are descriptive groupings of
backend results; do not calculate a new commercial ranking or global score.
If a required state is unavailable, show “Not available” with the reason.

Show counts of loaded candidates, qualified opportunities, allocation groups,
and prepared actions only when their meanings are explicit. An action count is
not a company count. Summaries link to the records they count. Absence of results
means “Not yet available” or an explicit empty state, never successful completion.

### C. Candidate universe

Show every supplied candidate, including excluded, blocked, and unresolved cases.
Columns: company, disposition, reason, evidence summary, freshness, revision.
Allow name search and disposition filtering; show filtered and total loaded
counts and a way to restore the complete list. Candidate cards/rows disclose
limitations and contradictions without forcing the user to read raw JSON.

Candidate names are not unique identifiers. The current candidate presentation
has no exact candidate ref; do not create mutation links or join candidates to
opportunities by name. The handoff defines the necessary contract addition.

### D. Qualified opportunity detail

Open an anchored detail section for an exact `opportunity_ref` from the workspace.
Show company, qualification and reason, Fit, Need, evidence summary, claim-level
confidence and rationale, contradictions, uncertainty, Pursuit Demand,
freshness, revision, and reassessment warning.

Show the matching priority, allocation, and next-action summaries as separately
labeled sections. Join on the complete opportunity ref, including revision and
object type. Keep multiple action records visible; do not overwrite them by
indexing solely on company or opportunity.

Do not render confidence as a company-wide probability or imply that strong Fit
establishes Need. Material contradictions and reassessment warnings must appear
before collapsed secondary details. “None recorded” must not become “Verified
absent.” Missing evidence must remain visible.

Evidence source links and observation dates are desirable, but the current
presentation supplies summaries rather than source records. Render links only
after the backend supplies authorized source metadata. Do not infer URLs or
expose restricted evidence, agent prompts, or provider traces.

### E. Priority & Capacity

Show two coordinated panels, or separate adjacent columns at wide widths:

| Commercial priority | Capacity allocation |
|---|---|
| Backend qualitative position and comparison reason | Backend allocation tier, capacity effect, and reason |
| Preserve ties, partial comparison, or unresolved state when supplied | Group Act Now, Deferred: capacity, Deferred: priority, Investigate |
| Never manufacture a numeric score or total ordering | Never interpret Act Now as permission to execute |

An opportunity table may bring these fields together, but each must retain its
own heading and explanation. On narrow screens preserve both labels in each
record. A lower-priority item fitting residual capacity must keep its commercial
priority and show its allocation reason; do not promote it visually to “best.”

Display available capacity, unit, planning horizon, concurrent-pursuit limit,
and per-item Pursuit Demand/capacity effect. Current effects and demand are text:
do not parse them to invent utilization percentages, remaining hours, or a
capacity chart. Add such graphics only with a backend-owned numeric projection
whose units, commitments, consumption, and remaining amount are explicit.
Show unfamiliar backend allocation states in an “Other reported states” group
with their original labels; never drop them from the view.

### F. Next Actions and human review

For each action show company/opportunity, action type, next credible action,
release-readiness state and reason, human-authorization state and reason.
Distinguish evidence gathering from commercial pursuit. Explain that readiness
and allocation are not authorization. No Send, Execute, outreach, CRM mutation,
or automated-execution control exists in this scope.

Initial delivery is read-only. Later authenticated review requires the exact
commercial-action revision, proposed action, structured scope, currentness,
review state, and blocking reasons from the server. These are not all present
in `ActionPresentation` today. Until the extension is implemented, show status
only; do not build a functioning approval form against an opportunity ref.

The later review panel must show the exact action/scope/revision being decided,
require a rationale, and offer Approve, Decline, Return for revision as explicit
decisions. Submission for review creates a pending state; it never approves.
An approval confirmation names the exact revision and scope. A changed revision
requires a new review. Refresh server state after every decision; never display
an optimistic approval or silently carry approval onto a new revision.

### G. Cycle setup and workflow controls: later integrated delivery

Provide labeled sections for offer/problem, intended buyer roles, Fit dimensions,
exclusions, offer version, market boundary/filters, effective date, and capacity.
Capacity includes usable time, effort unit, horizon, concurrent-pursuit limit,
fixed commitments, review trigger, and effective date. Use the existing create
and capacity-revision contracts; do not substitute free-text JSON entry.

Operator identity and its governed reference must come from trusted server
context, not a user-entered UUID or browser assertion. Capacity may be omitted
at cycle creation; explain which later phases are held until it is supplied.

Show workflow state separately from business decisions. Each eligible phase
control must name its scope, prerequisites, and any model call before submission.
The server determines eligibility and assembles exact inputs through services.
Do not ask operators to manufacture agent envelopes, policy booleans, or revision
graphs. No “Run everything” control in the first workflow delivery. Hold and
failure states retain prior results visibly marked with their currentness.

## 4. Visual design to implement

Use a calm, dense-enough decision workspace, building on the existing cream,
ink, and green palette rather than introducing an unrelated marketing design.
Define reusable tokens in a local stylesheet:

| Token | Initial value/use |
|---|---|
| Canvas / surface | `#f4f1e8` / `#fffdf7` |
| Primary text / secondary text | `#17201d` / `#66716c` |
| Accent / accent background | `#0f6655` / `#dcebe5` |
| Divider | `#d8d2c3` |
| Warning / warning background | `#9b4b24` / `#fff7ef` |
| Error / error background | `#9f2525` / `#fff0f0` |
| Spacing | 4, 8, 12, 16, 24, 32, 48 px |
| Corner radius | 8 px controls, 12 px panels |

Use system sans-serif at 16 px with at least 1.5 line height for body content;
keep headings restrained and avoid the existing oversized title taking over
the workspace. Maximum workspace width around 1280 px, fluid side gutters,
tabular numerals for quantities, explicit units, and readable long reasons.
Use badges for states with text and color; green alone must never imply approval.
Reserve warning/error emphasis for conditions requiring attention. Keep empty
states visually neutral. Validate token combinations for accessible contrast.

Desktop: context and warnings first, section navigation, then decision tables
and details. Below approximately 768 px use stacked labeled records and single
column panels. Support 320 px screens and 200% zoom without lost controls or
page-wide overflow; a wide comparison table may scroll in a labeled region.

Reusable components: page shell, cycle selector, context summary, warning list,
state badge, filter bar, result count, candidate row, opportunity detail,
claim-confidence list, priority panel, allocation group, action card, empty
state, service-error panel, and later form field/error and review confirmation.

## 5. Accessibility, state, and language

Use semantic landmarks, one H1, logical headings, skip navigation, visible focus,
keyboard-operable filters/disclosures, proper table headers/captions, explicit
form labels, and error summaries linked to invalid fields. Do not rely on hover,
color, or icons alone. Respect reduced motion. Announce asynchronous updates
without moving focus unexpectedly; restore focus when a detail panel closes.

Always handle loading where asynchronous, empty cycle, no filter matches,
missing phase output, not found, authentication unavailable, permission denied,
revision conflict, service unavailable, phase held, and model-run failure.
Server-rendered first loads should return useful accessible HTML error pages.
Show a safe request ID for support. A 503 is not an empty portfolio.

If refresh fails while existing data remains, label it as previously loaded,
show the failed refresh, and require revalidation before a write. A browser load
timestamp is not an evidence-freshness timestamp. Do not invent freshness limits.

Use plain labels: “Why this matters”, “What is uncertain”, “Capacity effect”,
“Next credible action”, “Release readiness”, “Human authorization”. Keep exact
revision IDs and technical terminology available in details for traceability.

## 6. Acceptance scenarios

1. An operator can explain what deserves attention and why, uncertainty, capacity
   effect, next action, readiness, and authorization without reading schemas.
2. An excluded/unresolved candidate remains discoverable and has a visible reason.
3. A low-priority residual-capacity selection stays lower priority while its
   Act Now allocation is explained separately.
4. A Release Ready action with pending authorization never looks approved.
5. Contradiction or reassessment warnings remain visible before expansion.
6. Two revisions of an opportunity do not merge, and multiple actions survive.
7. Missing fields never become guessed scores, capacity totals, or source links.
8. A service-adapter failure shows an unavailable state with request ID, not
   “No decision cycles”. Synthetic previews are visibly identified.
9. All primary tasks work with keyboard, narrow viewport, and JavaScript disabled;
   JavaScript adds convenience without changing decision meaning.
10. Later write delivery proves authenticated exact-revision decisions,
    idempotent retries, stale-revision handling, and no external execution.
