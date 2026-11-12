# VAI BD Development Plan

## Purpose

This directory converts the Founder-approved implementation pack in
`../vai_bd_implementation_pack/` into an executable, step-by-step development
plan. The source pack remains the business authority. These files add technical
specificity; they do not replace, reinterpret, or weaken frozen Stages 1–18.

## Authority order

When documents disagree, use this order:

1. Founder-approved and frozen Stages 1–18 referenced by the source pack.
2. `vai_bd_implementation_pack/01_GOVERNING_BASELINE.md`.
3. The remaining files in `vai_bd_implementation_pack/`.
4. This development plan.
5. Source code and generated documentation.

Stop and raise a governance issue if a lower-authority artifact cannot conform
to a higher-authority one. Never resolve the conflict by silently changing the
business meaning.

## What will be built

A minimum complete local application consisting of:

- a Python 3.11+ FastAPI backend;
- Pydantic v2 domain and agent contracts;
- PostgreSQL, SQLAlchemy 2.x, and Alembic persistence;
- exactly five OpenAI Agents SDK specialists;
- a deterministic Python Orchestrator;
- append-only revision, dependency, supersession, and audit records;
- Stage 15 synthetic fixtures, held-out oracle, and conformity runner;
- a minimal operator view;
- an Implementation-Conformity Evidence Package v0.1.

The OpenAI Agents SDK is appropriate because application code retains control
of persistence, tools, orchestration, and approvals while agents return typed
outputs. Current implementation references:

- [Agents SDK overview](https://developers.openai.com/api/docs/guides/agents/sdk)
- [Agent definitions and structured output](https://developers.openai.com/api/docs/guides/agents/define-agents)
- [Tracing and observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability)

Pin dependency versions in the lock file at implementation time. Do not pin a
model name in the domain; select it through configuration.

## Explicit non-goals

Do not implement or activate production deployment, a live pilot, real-company
data acquisition, browsing/scraping, paid third-party providers, email or social
outreach, CRM mutation, bulk messaging, purchases, or autonomous external
execution. The execution-eligibility policy is implemented and tested, but the
global external-action restriction remains false.

## Plan map

| File | Purpose |
|---|---|
| `01_REQUIREMENTS_AND_DECISIONS.md` | Invariants, assumptions, unresolved decisions, and stop conditions |
| `02_REPOSITORY_BLUEPRINT.md` | Exact target tree, dependency groups, and module boundaries |
| `03_DOMAIN_AND_PERSISTENCE.md` | Domain types, revision rules, database design, and migrations |
| `04_DETERMINISTIC_POLICIES.md` | Every code-owned rule and required unit tests |
| `05_AGENT_IMPLEMENTATION.md` | Five agents, I/O adapters, prompts, tools, guardrails, and audit |
| `06_ORCHESTRATION_API_AND_UI.md` | Workflow, services, endpoints, auth boundary, and operator view |
| `07_TEST_AND_CONFORMITY_PLAN.md` | Test pyramid, C01–C10, M01–M09, oracle isolation, and reports |
| `08_STEP_BY_STEP_BUILD.md` | Ordered implementation checklist with acceptance gates |
| `09_TRACEABILITY_MATRIX.md` | Requirement-to-code/test/deliverable mapping |
| `10_SECURITY_OPERATIONS_AND_EVIDENCE.md` | Security, failure handling, local operations, and handoff package |
| `11_FRONTEND_PRODUCT_SPEC.md` | Expanded operator screens, visual design, behavior, and acceptance scenarios |
| `12_FRONTEND_IMPLEMENTATION_HANDOFF.md` | Bassam's implementation gates, backend integration gaps, contracts, and verification |

## Working rules

- Complete steps in `08_STEP_BY_STEP_BUILD.md` in order.
- A step is complete only when its tests and acceptance checks pass.
- Runtime code must never import or read `tests/oracle/`.
- Never persist unvalidated agent prose as governed state.
- Never mutate a material historical revision in place.
- Never infer Human Authorization from model or workflow state.
- Record every departure or open question in an Architecture Decision Record.

