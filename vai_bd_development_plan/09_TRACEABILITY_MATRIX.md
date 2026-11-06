# Requirements Traceability Matrix

This matrix is the minimum mapping. Replace planned paths with exact symbols and
test IDs as implementation proceeds.

| Requirement/function | Planned implementation | Required verification |
|---|---|---|
| Configurable offer/market/operator/capacity | `domain/cycle.py`, cycle service | API + persistence tests; no fixture constants in policies |
| Candidate universe and coverage limitations | A1, discovery service/models | coverage/identity agent tests |
| Evidence provenance/directness/currentness/admissibility | evidence models/policies, A2 | C05, C06, C09, C10 |
| Source dependence | evidence dependency grouping | C05 + source-group unit tests |
| Contradiction preservation | contradiction model/policy | C06, M08 |
| Missing evidence is not negative | evidence/gate policies | C02, C07, C09 |
| Minimum-evidence/hard-eligibility gate | `policies/eligibility.py` | C06–C08, M07 |
| Fit separate from Need | A3 schemas/models | C01, C02, M09 |
| Owner separate from Contactability | A3 schemas/models | M09 + contract tests |
| Contactability not attractiveness | A3/A4 guardrails | C03 |
| Claim-scoped confidence | confidence model/A3 | schema and A3 tests |
| Four qualification outcomes | qualification model/A3 | C01–C10 coverage |
| Pursuit Demand not quality | demand model/A4 | C04, base allocation |
| Immutable qualified snapshot | snapshot repo/service | base + M02 history test |
| Canonical pairs/inverses | comparison policies | base 10 pairs + properties |
| Tie/near-tie/indeterminate/cycle | comparison policies/A4 | M03 + unit variants |
| Comparative Priority separate from Allocation | separate objects/UI columns | base + M01 + UI test |
| Capacity-bounded allocation | A4 + arithmetic validator | base, M01, M02, M06 |
| Residual-capacity inclusion without reorder | allocation invariant | base C02/C05 assertion |
| Alternative portfolios for review | allocation model/A4 | ambiguity test |
| Next credible action classification | A5/action model | M09 + A5 tests |
| Release readiness not Authorization | release policy/separate view | authority negative suite |
| Human-only authorization | authorization service/events | M04, M05, API auth tests |
| Exact action/scope/revision matching | execution policy | M04 + policy matrix |
| Supersession isolation | revision/auth policies | M04 |
| External execution disabled | configuration + policy | negative suite/startup test |
| Bounded reassessment | dependency graph/materiality records | M08 + capacity-change test |
| Capacity change does not change quality | reassessment/allocation policies | M01 |
| Local/portfolio/whole-cycle holds | orchestrator | C06, M03, M07 |
| Exactly five agents | agent registry | structural test |
| Deterministic non-agent Orchestrator | orchestrator/services | forbidden-authorship tests |
| Typed outputs only | Agents SDK adapter + Pydantic | malformed/free-form tests |
| Strict tool allowlists | five agent definitions | structural/contract test |
| Prompt injection boundary | shared prompt + validator | adversarial evidence test |
| Prompt/model/run traceability | manifests + agent_runs | audit integration test |
| Failure does not advance workflow | runner/orchestrator | injected API/schema failures |
| Oracle isolation | test layout/harness | static + unmounted runtime test |
| C01–C10 and M01–M09 | conformity suite | no-skip report assertion |
| Operator decision view | presenters/templates | required-content/UI distinction tests |
| Evidence Package v0.1 | build script | manifest completeness test |

## Completion protocol

For every row, add:

- source paragraph/file reference;
- exact code symbol(s);
- exact test ID(s);
- status: `NOT_STARTED`, `IMPLEMENTED`, `VERIFIED`, or `BLOCKED`;
- evidence-package artifact reference.

No row may be marked Verified solely by manual inspection when an automated test
is feasible.

