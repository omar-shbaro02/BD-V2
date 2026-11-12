# Frontend implementation handoff for Bassam

Read [the product specification](11_FRONTEND_PRODUCT_SPEC.md) first. This file
defines integration work and delivery gates. All items below are planned unless
explicitly identified as existing. No frontend code is delivered by this brief.

## 1. Existing implementation and material gaps

| Area | Existing source | Current reality |
|---|---|---|
| Application | `src/vai_bd/main.py` | `create_app(api_backend=...)` accepts a service adapter; default `app` installs `UnconfiguredApiBackend` |
| Service boundary | `src/vai_bd/api/contracts.py` | Typed `ApiBackend` protocol; default methods fail with 503 `backend_unavailable` |
| UI contracts | `src/vai_bd/operator/models.py` | Typed cycle list/detail projections available for rendering |
| HTML | `src/vai_bd/operator/router.py`, `render.py` | `/operator` and `/operator/cycles/{cycle_id}`; escaped server-rendered HTML and inline CSS |
| JSON API | `src/vai_bd/api/router.py`, `docs/openapi.json` | `/v1` routes and typed request/response contracts exist; not proof of a wired runnable workflow |
| Authentication | `src/vai_bd/api/auth.py` | Signed HUMAN test adapter only in test/conformity profiles; local/local-live mutations return authentication unavailable |
| Persistence/services | `src/vai_bd/persistence/`, `services/`, `orchestrator/` | Existing implementation to reuse through adapters; do not bypass it in page handlers |

Important correction to startup expectations: `/health` can return 200 while
`/operator` returns 503. The npm launcher starts Uvicorn; it does not configure
the application-service adapter, authentication, database, or synthetic data.
Do not describe this as a usable end-to-end UI until the integration gate passes.

There is no JSON cycle-list route in the current router, no generic revision
detail route, and no run-status polling route. Do not assume the earlier minimum
endpoint list is the implemented contract. Read source and generated OpenAPI.

## 2. Technical implementation approach

Keep one FastAPI application and origin. HTML handlers call `ApiBackend` or a
typed application-service facade directly; they do not make HTTP requests back
to their own JSON endpoints. Reuse the same validation, policy, identity,
idempotency, and persistence semantics for HTML and JSON mutations.

Refactor `render.py` into small escaped render functions or server templates.
If adding a template engine, declare it in `pyproject.toml` and deliberately
update `requirements.lock`; do not assume it is installed. Extract CSS to
`src/vai_bd/operator/static/operator.css` and optional JavaScript to local modules.
Mount a scoped static path, for example `/operator/static`, and verify wheel
packaging includes assets/templates. Use no CDN or external asset dependency.
Keep the source layout and dependency direction in the repository blueprint.

Keep standard HTML forms, links, and disclosures usable without JavaScript.
Use JavaScript for filtering, optional detail enhancement, pending-state feedback,
and supported refreshes only. Do not add a client-side policy engine or a Node
runtime dependency for serving pages. `npm run dev` remains a convenience wrapper
for Python/Uvicorn, not a frontend bundler.

## 3. Field mapping and contract limits

| Screen/component | Current projection fields | Implementation rule |
|---|---|---|
| Cycle index | `OperatorCycleList.cycles` and `OperatorCycleSummary` | Server calls `list_operator_cycles()`; no existing public JSON list endpoint |
| Context/coverage | `OperatorCycleView` context fields, `coverage`, `warnings` | Show units and limitations; missing backend is an error |
| Candidates | `candidates` | Display current fields; exact candidate ref needed before candidate mutations |
| Opportunity detail | `opportunities` | Key by full `opportunity_ref`; separate Fit, Need, and confidence by claim |
| Portfolio | `priority`, `allocation` | Join exact refs; preserve supplied meaning; show unexpected tiers |
| Next actions | `actions` | Multiple per opportunity allowed; current fields support status display only |
| Revision detail | current refs, labels, freshness strings | No fabricated history or “last updated” times |

Do not parse presentation prose into domain facts. Do not derive historical
trends, pipeline revenue, win probabilities, success rates, or urgency scores.
The current fields cannot support those metrics.

Backend-owned contract extensions, in this order:

1. Implement and wire a real `ApiBackend` composition over existing services and
   repositories, including list and operator projections. Add a deterministic
   local synthetic preview adapter or seed path for UI development, explicitly
   configured and visibly labeled. It must never load `tests/oracle/`, claim live
   results, or silently replace failed real services with demo data.
2. Add exact `candidate_ref` to candidate presentation before candidate-level
   controls. Add backend-projected evidence source references, safe URLs, dates,
   and access limitations if evidence drill-down is delivered.
3. For review, add exact `cao_ref`, exact action and structured scope, currentness,
   review state, and server-computed available decisions/block reasons. Project
   only authorized information. Do not infer action identity from array order.
4. For workflow controls, add a typed control projection with phase identifier,
   scope refs, prerequisites, allowed/held state, reasons, and available result
   refs. Assemble agent inputs through services, not browser policy toggles.
5. For capacity graphics/history, add explicit numeric quantities and units or
   authorized revision-history projections before implementing those visuals.

Each extension needs Python models, actual service projection, fixtures,
authorization/data-access rules, and meaningful tests. Update OpenAPI only when
public API schemas change. Preserve current consumers through deliberate
compatibility decisions; do not mark required missing facts with invented defaults.

## 4. Existing route integration map

All JSON routes below use `/v1`. HTML handlers reuse their underlying service
operations. Refer to `api/contracts.py`, `agents/contracts.py`, and generated
OpenAPI for payloads; the browser must not reconstruct agent input envelopes.

| User task | Existing route after `/v1` | Integration requirement |
|---|---|---|
| Read cycle | `GET /decision-cycles/{id}` | Lightweight refs/state, not a full UI projection |
| Read workspace | `GET /decision-cycles/{id}/operator-view` | `OperatorCycleView` |
| Create cycle | `POST /decision-cycles` | Offer + cycle + optional capacity; trusted operator ref |
| Revise capacity | `POST /decision-cycles/{id}/capacity-revisions` | Exact cycle and current capacity refs |
| Discover | `POST /decision-cycles/{id}/discovery-runs` | Service assembles `MarketDiscoveryInput` |
| Gather evidence | `POST /candidates/{id}/revisions/{revision}/evidence-runs` | Exact candidate ref and typed specialist input |
| Evaluate eligibility | `POST /candidates/{id}/revisions/{revision}/eligibility-evaluations` | Policy inputs established by trusted service, not guessed UI booleans |
| Assess opportunity | `POST /candidates/{id}/revisions/{revision}/assessment-runs` | Exact candidate and input refs |
| Freeze qualified universe | `POST /decision-cycles/{id}/qualified-snapshots` | Server-assembled exact qualification members |
| Compare / allocate | `POST /qualified-snapshots/{id}/revisions/{revision}/comparison-runs` or `/allocation-runs` | Preserve separate operations and output states |
| Prepare actions | `POST /allocations/{id}/revisions/{revision}/action-preparation-runs` | Exact allocation included in specialist inputs |
| Evaluate readiness | `POST /commercial-actions/{id}/revisions/{revision}/release-evaluations` | Service establishes policy facts |
| Submit review | `POST /commercial-actions/{id}/revisions/{revision}/review-submissions` | `cao_ref` and rationale; creates pending review |
| Decide review | `POST /commercial-actions/{id}/revisions/{revision}/authorization-decisions` | `cao_ref`, terminal decision, rationale; authenticated human |
| Inspect execution eligibility | `GET /commercial-actions/{id}/revisions/{revision}/execution-eligibility` | Informational only; performs no external action |
| Reassess | `POST /objects/{id}/revisions/{revision}/reassessment-evaluations` | Exact changed ref and reason; effects remain server-owned |

No new generic execution endpoint is part of this work. A workflow route existing
does not make its UI control deliverable before the prerequisites above are met.

## 5. Identity, security, and operation behavior

Implement a trusted local human-authentication/session adapter before enabling
workflow or review writes. Define who can read cycle data and who can decide a
review, then enforce those rules server-side. Do not expose test HMAC keys,
OpenAI keys, database credentials, or signed test-identity generation to browser
code. Keep test/conformity identity confined to those profiles.

With cookie-backed forms, implement CSRF protection and appropriate cookie
attributes. Escaping must remain on for company names, evidence, reasons, and
model output. Allow only safe authorized URL schemes for evidence links. Do not
render model-supplied HTML or display raw exceptions/provider payloads.

Every logical mutation gets an idempotency key. Preserve the same key and body
for retry after uncertain delivery; a deliberate changed operation gets a new
key. A browser refresh or double click must not trigger duplicate work. Disable
the submitted control while pending, but rely on server enforcement for safety.
Do not mark an operation complete merely because `OperationResult` includes a
run ID. There is no implemented polling endpoint: support synchronous completion
first; add a tested status contract before asynchronous monitoring.

On 409 distinguish stale refs, in-progress operations, idempotency conflict, and
phase holds by stable error code. Refresh facts and ask the user to review changed
content before retrying a stale decision. On 422 show field errors or policy
rejection without losing safe form input. On 401/403 explain access state. On
502/503 show a retryable service failure with request ID. Never silently rerun a
model-backed operation or auto-retry an approval with changed revision refs.

## 6. Delivery sequence and owner boundaries

| Gate | Bassam / frontend deliverable | Backend integration deliverable | Acceptance |
|---|---|---|---|
| F0: runnable preview | Refined page shell and explicit preview banner | Wired deterministic synthetic adapter or seed/composition path | `/operator` and detail show known synthetic cases; unavailable adapter still returns a clear error |
| F1: read-only workspace | All screens A-F in read-only form, filters, responsive styles, disclosures, accessible errors | Complete existing projections; optional candidate/source additions scoped explicitly | Product-spec scenarios 1-9 pass; no mutation controls |
| F2: workflow workspace | Setup/capacity forms and eligible phase controls | Trusted identity, write access, CSRF where needed, input facade and capability projection | Real governed revisions created; holds, retries, conflicts and failures demonstrated |
| F3: explicit human review | Exact-action review panel and decision confirmation | CAO/action/scope projection, currentness enforcement and human-only decisions | Scenario 10 passes; stale approval rejected; external execution remains disabled |

Bassam owns frontend implementation against these contracts. The backend
implementer owns adapter wiring, identity, projection additions, and service
input assembly; coordinate those changes in the same reviewable delivery or
linked changes. Do not present an unwired UI as backend-complete.

These gates supplement the completed Phase 10 baseline. They do not rewrite its
historical test results or claim that Phase 12 evidence-package work is complete.

## 7. Verification and handoff evidence

Use synthetic runtime fixtures, not oracle content, for UI previews. Include
excluded/unresolved candidates, contradictory evidence, empty results, unknown
states, multiple action records, stale revisions, partial comparison, residual
capacity allocation, pending/declined/approved review, and service failures.

Extend existing presentation/API tests where relevant. Test meaning and failure
behavior: required distinctions, exact-ref joins, complete disposition, escaping,
safe links, unavailable-service HTML, identity/CSRF and stale decision rejection.
Retain the no-forms/no-buttons assertions for the read-only delivery; change tests
deliberately when authenticated workflow pages are added, while retaining the
prohibition on external send/execute controls everywhere.

Run project format/lint/type checks and relevant Python tests. For template,
asset, dependency, or service-boundary changes run the affected packaging and
integration checks. Visually inspect desktop, 768 px, and 320 px layouts,
200% zoom, long names/reasons, keyboard focus, filters, errors, and JavaScript
disabled. Capture screenshots and record any browser checks not performed.

Deliver source/assets, adapter/contract changes, tests, screenshots, exact local
setup commands, synthetic fixture configuration, known gaps, and updated status.
No secrets, no live-company data, no deployment, and no outreach are needed.

## 8. Bassam's starting checklist

- [ ] Read frozen business distinctions and this two-file specification.
- [ ] Confirm default 503 behavior and identify the adapter composition to use.
- [ ] Agree the F0/F1 projection contract before building dependent screens.
- [ ] Build the responsive read-only workspace with synthetic scenarios.
- [ ] Demonstrate product acceptance scenarios and record visual checks.
- [ ] Deliver F2 only with server identity and complete service input assembly.
- [ ] Deliver F3 only with exact CAO/action/scope and human-decision enforcement.
- [ ] Update implementation status with actual results and remaining limitations.
