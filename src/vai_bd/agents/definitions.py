"""The exactly five bounded OpenAI Agents SDK specialist definitions."""

from dataclasses import dataclass
from typing import Any

from agents import Agent
from vai_bd.agents.contracts import (
    CommercialActionOutput,
    EvidenceIntelligenceOutput,
    MarketDiscoveryOutput,
    OpportunityIntelligenceOutput,
    PortfolioAllocationOutput,
    SpecialistName,
)
from vai_bd.agents.prompts import PromptBundle, load_prompt_bundles


@dataclass(frozen=True)
class SpecialistAgent:
    name: SpecialistName
    agent: Agent[Any]
    prompt: PromptBundle


_PROMPTS = load_prompt_bundles()

market_discovery_agent: Agent[Any] = Agent(
    name="Market Discovery Specialist",
    instructions=_PROMPTS[SpecialistName.MARKET_DISCOVERY].instructions,
    output_type=MarketDiscoveryOutput,
    tools=[],
    handoffs=[],
)
evidence_intelligence_agent: Agent[Any] = Agent(
    name="Evidence Intelligence Specialist",
    instructions=_PROMPTS[SpecialistName.EVIDENCE_INTELLIGENCE].instructions,
    output_type=EvidenceIntelligenceOutput,
    tools=[],
    handoffs=[],
)
opportunity_intelligence_agent: Agent[Any] = Agent(
    name="Opportunity Intelligence Specialist",
    instructions=_PROMPTS[SpecialistName.OPPORTUNITY_INTELLIGENCE].instructions,
    output_type=OpportunityIntelligenceOutput,
    tools=[],
    handoffs=[],
)
portfolio_allocation_agent: Agent[Any] = Agent(
    name="Portfolio and Allocation Intelligence Specialist",
    instructions=_PROMPTS[SpecialistName.PORTFOLIO_ALLOCATION].instructions,
    output_type=PortfolioAllocationOutput,
    tools=[],
    handoffs=[],
)
commercial_action_agent: Agent[Any] = Agent(
    name="Commercial Action Specialist",
    instructions=_PROMPTS[SpecialistName.COMMERCIAL_ACTION].instructions,
    output_type=CommercialActionOutput,
    tools=[],
    handoffs=[],
)

SPECIALISTS: dict[SpecialistName, SpecialistAgent] = {
    SpecialistName.MARKET_DISCOVERY: SpecialistAgent(
        SpecialistName.MARKET_DISCOVERY,
        market_discovery_agent,
        _PROMPTS[SpecialistName.MARKET_DISCOVERY],
    ),
    SpecialistName.EVIDENCE_INTELLIGENCE: SpecialistAgent(
        SpecialistName.EVIDENCE_INTELLIGENCE,
        evidence_intelligence_agent,
        _PROMPTS[SpecialistName.EVIDENCE_INTELLIGENCE],
    ),
    SpecialistName.OPPORTUNITY_INTELLIGENCE: SpecialistAgent(
        SpecialistName.OPPORTUNITY_INTELLIGENCE,
        opportunity_intelligence_agent,
        _PROMPTS[SpecialistName.OPPORTUNITY_INTELLIGENCE],
    ),
    SpecialistName.PORTFOLIO_ALLOCATION: SpecialistAgent(
        SpecialistName.PORTFOLIO_ALLOCATION,
        portfolio_allocation_agent,
        _PROMPTS[SpecialistName.PORTFOLIO_ALLOCATION],
    ),
    SpecialistName.COMMERCIAL_ACTION: SpecialistAgent(
        SpecialistName.COMMERCIAL_ACTION,
        commercial_action_agent,
        _PROMPTS[SpecialistName.COMMERCIAL_ACTION],
    ),
}
