# 04 — OpenAI API Agent Architecture

## 1. Runtime choice

Use the **OpenAI Agents SDK for Python**, which runs OpenAI models through the Responses API.

Recommended pattern:

- five specialist agents implemented with `Agent`;
- invoked by deterministic Python orchestration code via `Runner`;
- structured outputs validated with Pydantic models;
- function tools used only for bounded data access/calculation;
- tracing enabled for every governed run;
- no specialist receives authority to perform external commercial actions.

## 2. Why code orchestration instead of a sixth LLM manager

The frozen Stage 9 Orchestrator owns process integrity, not substantive commercial truth.

Therefore the preferred architecture is:

```text
FastAPI / Application Service
        |
        v
Deterministic Orchestrator
  |     |     |     |     |
  v     v     v     v     v
A1     A2     A3     A4     A5
OpenAI OpenAI OpenAI OpenAI OpenAI
Agent  Agent  Agent  Agent  Agent
```

The Orchestrator decides **when** an agent may run based on dependencies and state. It does not create Fit, Need, Priority, Allocation, or Authorization judgments itself.

## 3. Agents

- `market_discovery_agent`
- `evidence_intelligence_agent`
- `opportunity_intelligence_agent`
- `portfolio_allocation_agent`
- `commercial_action_agent`

## 4. Structured output requirement

Every agent must return a typed output model.

No agent response should be accepted directly as free-form domain state.

Pattern:

```python
from pydantic import BaseModel
from agents import Agent, Runner

class SomeOutput(BaseModel):
    ...

agent = Agent(
    name="...",
    instructions="...",
    output_type=SomeOutput,
    tools=[...],
)

result = await Runner.run(agent, input_payload)
validated = result.final_output
```

Persist only validated business objects.

## 5. Tools

Agents may call only tools granted to their bounded responsibility.

Examples of initially safe internal tools:

- fetch decision-cycle context
- fetch candidate records
- fetch evidence records
- persist draft agent output into a pending review area
- deterministic date/currentness helper
- deterministic pair-generation helper
- deterministic capacity arithmetic helper

External browsing/data-provider tools should remain disabled until separately authorized.

## 6. Guardrails

Implement guardrails at two levels.

### Agent-level

Reject output that:

- invents unavailable evidence;
- emits unauthorized object types;
- collapses forbidden concepts;
- creates external action authority;
- returns unsupported numerical probabilities;
- omits evidence references for material judgments.

### Orchestrator-level

Reject transitions when:

- dependencies are missing;
- upstream object is stale/superseded;
- required market/capacity inputs are absent;
- candidate is blocked by gate;
- comparison snapshot is inconsistent;
- authorization scope/revision does not match.

## 7. Sessions and memory

Do not use conversational memory as the authoritative business state.

Business state lives in the application database.

Use agent sessions only for short-lived run continuity if needed. Before each material decision run, construct the input from persisted canonical objects and exact revision references.

## 8. Tracing

Enable OpenAI Agents SDK tracing for every specialist run.

Persist a mapping:

```text
domain_run_id
agent_name
input_object_revisions
OpenAI trace/run reference
validated output revision
prompt/instruction version
model configuration identifier
started_at
completed_at
```

Tracing supports debugging and conformity review but does not replace domain audit records.

## 9. Prompt versioning

Each agent instruction set must have:

```yaml
prompt_name
prompt_version
frozen_business_rules_version
created_at
approved_for_implementation_by
```

Changing a prompt that can alter governed business behavior requires a conformity regression run.

## 10. Model choice

Keep model selection configurable behind one adapter/config object. The business logic must not depend on a specific model name.

Do not encode model-specific behavior into the domain schema.

## 11. API key / provider boundary

Use OpenAI API credentials only through secure environment configuration.

Never put API keys into Markdown, source control, test fixtures, prompts, or agent memory.

OpenAI agent calls are authorized as part of the requested implementation direction. This does not authorize unrelated third-party providers or external commercial execution.
