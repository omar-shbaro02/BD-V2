# 11 — Codex Handoff Prompt

Paste the following into Codex together with this entire implementation pack.

---

You are implementing the **new VAI Business Development Decision Intelligence build**.

The Markdown files in this pack are the implementation authority. Do not use or resume any older discontinued BD application as the baseline.

## Goal

Build the minimum complete runnable backend that conforms to the frozen VAI BD Stages 1–18 business design and produces an **Implementation-Conformity Evidence Package v0.1**.

## Mandatory architecture

- Python 3.11+
- FastAPI
- Pydantic
- PostgreSQL / SQLAlchemy / Alembic
- OpenAI Agents SDK for exactly five specialist reasoning agents:
  1. Market Discovery Specialist
  2. Evidence Intelligence Specialist
  3. Opportunity Intelligence Specialist
  4. Portfolio & Allocation Intelligence Specialist
  5. Commercial Action Specialist
- deterministic Python Orchestrator; it is not a sixth substantive agent
- Human Authorization outside all agents

## Hard business constraints

Preserve exactly:

- Evidence ≠ Interpretation
- Fit ≠ Need
- Confidence ≠ Priority
- Decision-Owner ≠ Contactability
- Contactability ≠ commercial attractiveness
- Pursuit Demand ≠ commercial quality
- Comparative Priority ≠ Capacity Allocation
- Recommendation ≠ Authorization
- Capacity constraint ≠ opportunity quality

Do not introduce an opaque universal lead score.

## Authorization constraints

- Act Now does not authorize execution.
- Release Ready does not authorize execution.
- Draft does not authorize execution.
- Silence/timeout does not authorize execution.
- R1 approval does not authorize R2.
- Superseded Approved R1 does not retain new-execution eligibility merely because historical approval exists.

No agent may create `APPROVED` Human Authorization.

## Build order

Follow `09_IMPLEMENTATION_ROADMAP_FOR_CODEX.md` strictly.

Do not start with UI.

Implement:

1. domain schema and revision persistence;
2. deterministic policies;
3. five OpenAI specialist agents with typed outputs;
4. deterministic Orchestrator;
5. Stage 15 fixture/oracle separation;
6. conformity harness;
7. API layer;
8. minimal operator view;
9. evidence package.

## Testing

Implement all C01–C10 and M01–M09 cases from `08_STAGE15_CONFORMITY_TEST_PLAN.md`.

Expected adjudications must remain held out and inaccessible to runtime reasoning.

No material case may be silently skipped.

## External actions

Do not implement or activate:

- live outreach
- scraping
- paid providers
- CRM mutation
- bulk messaging
- deployment
- real-company actions

## Required final deliverable

Return:

- exact commit/version;
- full repository tree;
- setup/run instructions;
- database migration status;
- agent prompt/version inventory;
- domain-to-code traceability matrix;
- Stage 15 fixture and oracle locations;
- complete conformity results;
- failed/skipped tests;
- OpenAI trace references where available;
- known limitations;
- exact remaining implementation gaps.

If any frozen requirement appears impossible or contradictory, STOP and report the exact conflict instead of silently changing the business logic.

---
