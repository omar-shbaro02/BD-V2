"""Fake and opt-in live adapters behind one specialist runner contract."""

import json
from collections import defaultdict, deque
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol, Self, cast

from pydantic import TypeAdapter

from agents import RunConfig, Runner, gen_trace_id
from vai_bd.agents.contracts import (
    CommercialActionOutput,
    EvidenceIntelligenceOutput,
    MarketDiscoveryOutput,
    OpportunityIntelligenceOutput,
    PortfolioAllocationOutput,
    SpecialistInput,
    SpecialistName,
    SpecialistOutput,
)
from vai_bd.agents.definitions import SPECIALISTS
from vai_bd.config import Settings


@dataclass(frozen=True)
class AgentRunnerResult:
    output: SpecialistOutput
    trace_ref: str | None
    usage_metadata: dict[str, int]


class AgentRunner(Protocol):
    model_config_id: str

    async def run(
        self, name: SpecialistName, agent_input: SpecialistInput
    ) -> AgentRunnerResult: ...


_OUTPUT_ADAPTERS: dict[SpecialistName, TypeAdapter[SpecialistOutput]] = {
    SpecialistName.MARKET_DISCOVERY: TypeAdapter(MarketDiscoveryOutput),
    SpecialistName.EVIDENCE_INTELLIGENCE: TypeAdapter(EvidenceIntelligenceOutput),
    SpecialistName.OPPORTUNITY_INTELLIGENCE: TypeAdapter(OpportunityIntelligenceOutput),
    SpecialistName.PORTFOLIO_ALLOCATION: TypeAdapter(PortfolioAllocationOutput),
    SpecialistName.COMMERCIAL_ACTION: TypeAdapter(CommercialActionOutput),
}


class FakeAgentRunner:
    """Deterministic queued outputs; schema checks are intentionally not bypassable."""

    model_config_id = "fake-agent-runner-v1"

    def __init__(
        self,
        outputs: Mapping[SpecialistName, tuple[SpecialistOutput | dict[str, object], ...]],
    ) -> None:
        self._outputs: defaultdict[SpecialistName, deque[SpecialistOutput | dict[str, object]]] = (
            defaultdict(deque)
        )
        for name, values in outputs.items():
            self._outputs[name].extend(values)

    async def run(self, name: SpecialistName, agent_input: SpecialistInput) -> AgentRunnerResult:
        del agent_input
        if not self._outputs[name]:
            raise RuntimeError(f"no fake output queued for {name.value}")
        output = _OUTPUT_ADAPTERS[name].validate_python(self._outputs[name].popleft())
        return AgentRunnerResult(output=output, trace_ref=None, usage_metadata={})


class LiveAgentRunner:
    """OpenAI Agents SDK adapter; construction is allowed without making an API call."""

    def __init__(
        self,
        *,
        model: str,
        tracing_disabled: bool,
        trace_include_sensitive_data: bool,
        max_turns: int = 4,
    ) -> None:
        if not model.strip():
            raise ValueError("live agent runner requires a configured model")
        if max_turns < 1:
            raise ValueError("max_turns must be positive")
        self.model = model
        self.tracing_disabled = tracing_disabled
        self.trace_include_sensitive_data = trace_include_sensitive_data
        self.max_turns = max_turns
        config_material = json.dumps(
            {
                "model": model,
                "tracing_disabled": tracing_disabled,
                "trace_include_sensitive_data": trace_include_sensitive_data,
                "max_turns": max_turns,
            },
            sort_keys=True,
        )
        self.model_config_id = "openai-agents-" + sha256(config_material.encode()).hexdigest()[:16]

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        if not settings.openai_model or not settings.openai_api_key:
            raise ValueError("live agent runner requires configured OpenAI credentials and model")
        return cls(
            model=settings.openai_model,
            tracing_disabled=settings.openai_agents_disable_tracing,
            trace_include_sensitive_data=settings.trace_include_sensitive_data,
        )

    async def run(self, name: SpecialistName, agent_input: SpecialistInput) -> AgentRunnerResult:
        specialist = SPECIALISTS[name]
        trace_id = gen_trace_id()
        result = await Runner.run(
            specialist.agent,
            serialize_agent_input(agent_input),
            max_turns=self.max_turns,
            run_config=RunConfig(
                model=self.model,
                tracing_disabled=self.tracing_disabled,
                trace_include_sensitive_data=self.trace_include_sensitive_data,
                workflow_name=f"vai-bd:{name.value}",
                trace_id=trace_id,
                trace_metadata={
                    "specialist": name.value,
                    "prompt_version": specialist.prompt.version,
                    "prompt_digest": specialist.prompt.content_digest,
                },
            ),
        )
        output = _OUTPUT_ADAPTERS[name].validate_python(result.final_output)
        usage = result.context_wrapper.usage
        return AgentRunnerResult(
            output=output,
            trace_ref=trace_id,
            usage_metadata={
                "requests": usage.requests,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
            },
        )


def serialize_agent_input(agent_input: SpecialistInput) -> str:
    """Serialize governed fields separately from escaped, explicitly untrusted evidence."""

    payload = agent_input.model_dump(mode="json")
    observations = payload.pop("observations", [])
    governed_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    untrusted_json = json.dumps(observations, sort_keys=True, separators=(",", ":"))
    untrusted_json = untrusted_json.replace("<", "\\u003c").replace(">", "\\u003e")
    return (
        "<governed_input>\n"
        + governed_json
        + "\n</governed_input>\n<untrusted_evidence>\n"
        + untrusted_json
        + "\n</untrusted_evidence>"
    )


def cast_specialist_output(value: object) -> SpecialistOutput:
    """Narrow a value already validated by a name-specific output adapter."""

    return cast(SpecialistOutput, value)
