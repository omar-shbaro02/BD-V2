# 09 — Implementation Roadmap for Codex

This is the ordered implementation plan. Do not skip ahead because later pieces appear easy.

## Milestone 0 — Repository and authority scaffold

Create the clean new-build repository.

Deliver:

- README with frozen-scope warning
- Python project configuration
- dependency management
- test runner
- `.env.example` without secrets
- configuration layer
- initial CI test command

Acceptance:

- repository clearly states old BD app is not baseline;
- no provider/external-action integration exists.

## Milestone 1 — Domain model and persistence

Implement canonical models/enums from `03_DOMAIN_SCHEMA.md`.

Deliver:

- Pydantic domain models
- SQLAlchemy persistence models
- migrations
- revision/supersession/dependency repositories

Acceptance:

- historical revisions preserved;
- exact dependencies queryable;
- Qualified Universe snapshots immutable by revision.

## Milestone 2 — Deterministic policies

Implement code-only policies:

- eligibility gate mechanics
- currentness checks
- pair creation
- canonical comparison uniqueness
- inverse derivation
- cycle detection
- capacity arithmetic
- execution eligibility
- reassessment propagation

Acceptance:

- policy tests pass without LLM calls.

## Milestone 3 — OpenAI specialist agent shells

Implement all five specialist Agents SDK agents with typed outputs.

Deliver per agent:

- instruction prompt
- prompt version
- Pydantic input/output adapter
- allowed tools
- guardrails
- unit tests using mocked model outputs

Acceptance:

- every agent rejects forbidden object types/authority;
- no free-form response is persisted as governed state.

## Milestone 4 — Deterministic Orchestrator

Implement cycle orchestration in code.

Deliver:

- dependency checks
- specialist invocation services
- hold/release flow
- reassessment propagation
- run audit/tracing hooks

Acceptance:

- Orchestrator never authors Fit/Need/Priority/Authorization;
- every material object references exact upstream revisions.

## Milestone 5 — Stage 15 fixture/oracle split

Create:

```text
tests/fixtures/stage15/
tests/oracle/stage15/
```

Fixtures contain only runtime inputs.

Oracle contains expected governed outcomes.

Acceptance:

- runtime code has no import/path access to oracle package;
- test harness reads oracle only after runtime result is produced.

## Milestone 6 — Conformity harness

Implement automated cases C01–C10 and M01–M09.

Produce machine-readable results:

```yaml
case_id
input_fixture_version
actual_output_refs
expected_rule_refs
pass_fail
material_differences
trace_refs
```

Acceptance:

- no material case skipped;
- all failures visible.

## Milestone 7 — API layer

Expose the minimum governed backend endpoints.

Do not build polished frontend yet.

Acceptance:

- full decision cycle can be executed through API/test client;
- human authorization requires an explicit authenticated decision event.

## Milestone 8 — Operator view

Implement a minimal operator-facing representation.

Show:

- what deserves attention
- why
- evidence summary
- uncertainty
- capacity deferrals
- investigation requirements
- next credible action
- authorization status

Acceptance:

- internal schema complexity is not dumped on operator;
- Priority remains visibly distinct from Allocation.

## Milestone 9 — Evidence Package v0.1

Generate:

- exact commit/version
- setup instructions
- architecture map
- agent responsibility map
- traceability matrix
- fixture/oracle packages
- conformity run results
- logs/traces
- known limitations
- skipped/failing tests

This is the required Founder/control-room return.

## Stop conditions

Stop and return to governance if:

- frozen requirements are internally impossible to implement simultaneously;
- an external provider/action becomes necessary but unauthorized;
- implementation would require adding a sixth substantive intelligence role;
- Human Authorization cannot remain external;
- the only practical implementation would collapse forbidden reasoning distinctions.

Do not silently redesign.
