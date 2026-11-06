# VAI Business Development Decision Intelligence — Implementation Pack

## Purpose

This pack is the implementation handoff for the **new VAI Business Development Decision Intelligence build**. It converts the Founder-approved and frozen Stages 1–18 business design into build instructions for Omar/Codex without changing the business logic.

## Authority

Highest authority for this pack:

1. Founder-approved and frozen Stages 1–18 from the current VAI BD build.
2. Corrected Stage 18 Expansion Path Baseline v0.2.
3. Stage 15 Synthetic Dataset Baseline v0.1 as the held-out design answer key.
4. Durable VAI doctrine: decision-first design, evidence discipline, priority/confidence separation, human validation, and no silent execution authority.
5. Historical BD/GTM material only where it does not conflict with the new build.

The discontinued earlier coded BD application is **historical only** and is not the implementation baseline.

## Current governed state

- Stages 1–18: PASS / FROZEN
- Implementation: AUTHORIZED / OPEN
- Implementation-Conformity: AUTHORIZED / OPEN / NOT PASSED
- Stage 19: UNAUTHORIZED
- Live pilot: UNAUTHORIZED
- Deployment / external execution: UNAUTHORIZED

## Owner

Implementation owner: **Omar**.

## OpenAI runtime decision

All five specialist reasoning components must be implemented as **OpenAI API agents** using the current OpenAI Agents SDK / Responses API stack.

The Orchestrator is **deterministic application code**, not a sixth substantive intelligence agent. It schedules, validates dependencies, applies holds, routes work, persists revisions, and invokes the five agents.

## Frozen specialist set

1. Market Discovery Specialist
2. Evidence Intelligence Specialist
3. Opportunity Intelligence Specialist
4. Portfolio & Allocation Intelligence Specialist
5. Commercial Action Specialist

Human Authorization remains outside the agent system.

## Files in this pack

- `01_GOVERNING_BASELINE.md` — non-negotiable frozen business logic and governance.
- `02_END_TO_END_FLOW.md` — complete decision flow and release gates.
- `03_DOMAIN_SCHEMA.md` — canonical objects, revisions, states, and relationships.
- `04_OPENAI_AGENT_ARCHITECTURE.md` — OpenAI Agents SDK architecture and orchestration pattern.
- `05_AGENT_IO_CONTRACTS.md` — exact responsibilities and I/O contracts for all five agents.
- `06_ORCHESTRATOR_CONTROL_LOGIC.md` — deterministic orchestration and blocking/reassessment rules.
- `07_API_STORAGE_AND_SERVICE_BOUNDARIES.md` — recommended implementation service boundaries and persistence model.
- `08_STAGE15_CONFORMITY_TEST_PLAN.md` — frozen synthetic cases and expected business behavior.
- `09_IMPLEMENTATION_ROADMAP_FOR_CODEX.md` — ordered build plan with acceptance gates.
- `10_SECURITY_GOVERNANCE_AND_EXTERNAL_ACTIONS.md` — authorization, tools, provider and execution restrictions.
- `11_CODEX_HANDOFF_PROMPT.md` — paste-ready Codex implementation mandate.
- `12_SYSTEM_DIAGRAMS.md` — Mermaid decision, runtime, reassessment, and authorization diagrams.
- `13_AGENT_PROMPT_TEMPLATES.md` — versionable instruction templates for all five OpenAI specialist agents.

## Core implementation rule

> Do not simplify the frozen business design by collapsing independent concepts into one score, one status, or one agent.

A technically elegant build that changes the decision meaning is non-conforming.
