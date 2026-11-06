# Test and Conformity Plan

## 1. Test layers

- Unit: Pydantic validation, enums, refs, every deterministic policy.
- Property: comparison inverses/pairs, revision history, capacity invariants,
  dependency propagation boundaries.
- Repository integration: constraints, transactions, rollback, concurrency,
  migrations, exact revision queries.
- Agent contracts: fake runner, structured outputs, prompts, tools, semantic
  guardrails, failure paths.
- Orchestrator integration: every phase, local/portfolio/whole-cycle holds,
  resumability, idempotency, reassessment.
- API: authentication boundary, status/error formats, stale refs, idempotency.
- Operator view: required distinctions and all candidate dispositions.
- Conformity: C01–C10 and M01–M09 against held-out oracle.
- Optional live smoke: one synthetic run per agent, never part of default CI.

## 2. Fixture/oracle isolation

```text
tests/fixtures/stage15/  # runtime-visible synthetic inputs only
tests/oracle/stage15/    # test-harness-only expected governed outcomes
```

Enforce isolation with:

- no oracle package marker imported by `src/`;
- a static test that scans runtime imports and file paths;
- runtime executed in a working directory/container without oracle mounted;
- actual results serialized before oracle is loaded;
- oracle access only in the assertion/reporting phase.

If the full frozen Stage 15 dataset is not present in the source materials, add a
blocking fixture-provenance note and request it. Do not reverse-engineer detailed
inputs from expected outputs.

Resolution (2026-10-19): the user explicitly authorized generation of a new
project-authored synthetic baseline. Version `stage15-synthetic-v1.0.0` follows
the documented scenario meanings but is not represented as the missing original
frozen artifact; ADR 0005 records this provenance decision.

## 3. Base cases C01–C10

| Case | Must prove |
|---|---|
| C01 | Strong Fit and current supported Need -> Qualified |
| C02 | Strong Fit, weak direct Need -> Qualified with provisional Need |
| C03 | High Contactability does not defeat stronger commercial quality |
| C04 | Strong case remains strong despite high Pursuit Demand |
| C05 | Source echoes share a dependency group; qualification discloses limitation |
| C06 | Market-presence contradiction blocks gate and leads to material review, not forced judgment |
| C07 | Insufficient minimum evidence -> evidence required, no substantive assessment |
| C08 | Supported outside-boundary fact -> hard exclusion for this cycle |
| C09 | Restricted-only critical fact is not consumed; investigation required |
| C10 | Material staleness -> investigation/reassessment, stale evidence retained |

Snapshot includes exactly C01–C05 and represents all other dispositions. Create
all 10 unique comparisons and validate `C01 > C04 > C02 > C05 > C03` materially,
without introducing a hidden numeric score.

With demands 2.0h, 3.0h, 1.5h, 1.0h, and 1.0h under 6h, validate Act Now C01,
C04, C05; C02 deferred by capacity; C03 deferred by lower priority. Assert C02
remains commercially above C05.

## 4. Mutation cases M01–M09

| Mutation | Required assertions |
|---|---|
| M01 4h | C01 and C02 Act Now; C04 deferred capacity; priority unchanged |
| M02 C12 | New universe/snapshot; historical snapshot unchanged; new order and allocation match oracle |
| M03 cycle | Cycle exposed; no forced total order; material allocation held |
| M04 supersession | R1 approval does not transfer; history retained; R1 cannot newly execute |
| M05 timeout | Pending remains non-authorized; escalation may be recorded only |
| M06 no capacity | Capacity-independent work continues; no allocation or Act Now |
| M07 no market | Whole cycle held; no geographic eligibility/relative priority |
| M08 source failure | All and only materially dependent objects reassessed |
| M09 no owner | Fit/Need retained; action may investigate Decision-Owner |

## 5. Negative authority and boundary suite

Every test must fail the build if any agent or Orchestrator can create Approved;
if Release Ready/Act Now/draft/timeout becomes authorization; if execution becomes
eligible in conformity mode; if a superseded or reassessment-required CAO is
eligible; or if external action tools appear in an agent allowlist.

Also test prompt-injection evidence, unsupported numeric probabilities, invented
refs, forbidden output fields, incomplete pairs, duplicate comparisons, unit
mismatch, missing dependencies, and model/schema failures.

## 6. Machine-readable report

For each case persist and export:

```yaml
case_id:
input_fixture_version:
input_digest:
actual_output_refs: []
expected_rule_refs: []
pass_fail:
material_differences: []
trace_refs: []
started_at:
completed_at:
code_version:
prompt_versions: {}
model_config_id:
```

No material case may be skipped. Environmental live-smoke tests may be reported
separately as not run, but never substitute for conformity cases.

## 7. Pass gate

PASS requires all C01–C10 and M01–M09 material meanings to match, all authority
boundary tests to pass, no oracle leakage, no skipped material test, and a report
that exposes all failures/differences. Textual wording need not be identical.

