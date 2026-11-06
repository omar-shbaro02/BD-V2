"""Shared semantic guardrails applied identically to fake and live results."""

from collections.abc import Iterable

from pydantic import BaseModel

from vai_bd.agents.contracts import (
    AllocationOperationOutput,
    CommercialActionInput,
    CommercialActionOutput,
    ComparisonOperationOutput,
    EvidenceIntelligenceInput,
    EvidenceIntelligenceOutput,
    MarketDiscoveryInput,
    MarketDiscoveryOutput,
    OpportunityIntelligenceInput,
    OpportunityIntelligenceOutput,
    PortfolioAllocationInput,
    PortfolioAllocationOutput,
    PortfolioComparisonInput,
    SpecialistInput,
    SpecialistName,
    SpecialistOutput,
)
from vai_bd.domain.enums import EvidenceAdmissibility
from vai_bd.domain.refs import ObjectRevisionRef
from vai_bd.policies.comparisons import canonical_pair


class SemanticGuardrailError(ValueError):
    """A schema-valid specialist result violates its governed role boundary."""


_CONTRACTS: dict[SpecialistName, tuple[type[BaseModel], type[BaseModel]]] = {
    SpecialistName.MARKET_DISCOVERY: (MarketDiscoveryInput, MarketDiscoveryOutput),
    SpecialistName.EVIDENCE_INTELLIGENCE: (
        EvidenceIntelligenceInput,
        EvidenceIntelligenceOutput,
    ),
    SpecialistName.OPPORTUNITY_INTELLIGENCE: (
        OpportunityIntelligenceInput,
        OpportunityIntelligenceOutput,
    ),
    SpecialistName.COMMERCIAL_ACTION: (CommercialActionInput, CommercialActionOutput),
}


def validate_specialist_exchange(
    name: SpecialistName,
    agent_input: SpecialistInput,
    output: SpecialistOutput,
) -> None:
    if name is SpecialistName.PORTFOLIO_ALLOCATION:
        _validate_portfolio_types(agent_input, output)
    else:
        input_type, output_type = _CONTRACTS[name]
        if not isinstance(agent_input, input_type) or not isinstance(output, output_type):
            raise SemanticGuardrailError(f"contract mismatch for {name.value}")

    exact_refs = set(agent_input.exact_input_refs)
    explicit_input_refs = set(_walk_refs(agent_input)) - exact_refs
    if not explicit_input_refs.issubset(exact_refs):
        raise SemanticGuardrailError("input contains a revision not declared in exact_input_refs")
    if set(_referenced_input_refs(output)) != exact_refs:
        raise SemanticGuardrailError("output must preserve the complete exact input reference set")
    output_refs = set(_walk_refs(output)) - set(_referenced_input_refs(output))
    if not output_refs.issubset(exact_refs):
        raise SemanticGuardrailError("output invented or used an unavailable revision reference")

    if isinstance(agent_input, MarketDiscoveryInput) and isinstance(output, MarketDiscoveryOutput):
        _validate_market_output(agent_input, output)
    elif isinstance(agent_input, EvidenceIntelligenceInput) and isinstance(
        output, EvidenceIntelligenceOutput
    ):
        _validate_evidence_output(agent_input, output)
    elif isinstance(agent_input, OpportunityIntelligenceInput) and isinstance(
        output, OpportunityIntelligenceOutput
    ):
        _validate_opportunity_output(agent_input, output)
    elif isinstance(output, PortfolioAllocationOutput):
        _validate_portfolio_output(agent_input, output)
    elif isinstance(agent_input, CommercialActionInput) and isinstance(
        output, CommercialActionOutput
    ):
        if not set(output.evidence_refs).issubset(agent_input.evidence_refs):
            raise SemanticGuardrailError("commercial action used unavailable evidence")
        if output.decision_owner_ref not in {None, agent_input.decision_owner_ref}:
            raise SemanticGuardrailError("commercial action changed the decision owner reference")


def _validate_portfolio_types(agent_input: SpecialistInput, output: SpecialistOutput) -> None:
    if not isinstance(agent_input, (PortfolioComparisonInput, PortfolioAllocationInput)):
        raise SemanticGuardrailError("portfolio agent requires a portfolio operation input")
    if not isinstance(output, PortfolioAllocationOutput):
        raise SemanticGuardrailError("portfolio agent returned another specialist's output")
    if agent_input.operation != output.result.operation:
        raise SemanticGuardrailError(
            "portfolio operation output does not match requested operation"
        )


def _validate_market_output(
    agent_input: MarketDiscoveryInput, output: MarketDiscoveryOutput
) -> None:
    if output.claims_exhaustive_coverage and not agent_input.exhaustive_coverage_supported:
        raise SemanticGuardrailError("unsupported exhaustive coverage claim")
    allowed_sources = {item.source for item in agent_input.observations}
    if any(
        source not in allowed_sources
        for candidate in output.candidates
        for source in candidate.source_refs
    ):
        raise SemanticGuardrailError("candidate proposal used an unavailable source")
    if any(
        removal.candidate_ref not in agent_input.prior_candidate_refs
        for removal in output.removed_candidates
    ):
        raise SemanticGuardrailError("removal does not identify a prior candidate")


def _validate_evidence_output(
    agent_input: EvidenceIntelligenceInput, output: EvidenceIntelligenceOutput
) -> None:
    observations = {item.source: item for item in agent_input.observations}
    for record in output.evidence_records:
        observation = observations.get(record.source)
        if observation is None:
            raise SemanticGuardrailError("evidence proposal used an unavailable source")
        if observation.restricted and record.admissibility is EvidenceAdmissibility.ADMISSIBLE:
            raise SemanticGuardrailError("restricted evidence was labeled admissible")


def _validate_opportunity_output(
    agent_input: OpportunityIntelligenceInput, output: OpportunityIntelligenceOutput
) -> None:
    allowed = set(agent_input.evidence_refs)
    used = {
        *output.fit.evidence_refs,
        *output.need.evidence_refs,
        *output.decision_owner.evidence_refs,
        *output.contactability.evidence_refs,
        *(ref for confidence in output.confidences for ref in confidence.evidence_refs),
    }
    if not used.issubset(allowed):
        raise SemanticGuardrailError("opportunity judgment used unavailable evidence")
    confidence_keys = {item.claim_key for item in output.confidences}
    required = {
        output.fit.confidence_claim_key,
        output.need.confidence_claim_key,
        output.decision_owner.confidence_claim_key,
        output.contactability.confidence_claim_key,
    }
    if not required.issubset(confidence_keys):
        raise SemanticGuardrailError("judgment references a missing confidence proposal")


def _validate_portfolio_output(
    agent_input: SpecialistInput, output: PortfolioAllocationOutput
) -> None:
    if isinstance(agent_input, PortfolioComparisonInput) and isinstance(
        output.result, ComparisonOperationOutput
    ):
        expected = {canonical_pair(pair.first, pair.second) for pair in agent_input.required_pairs}
        observed = [
            canonical_pair(item.subject_ref, item.comparator_ref)
            for item in output.result.comparisons
        ]
        if len(observed) != len(set(observed)) or set(observed) != expected:
            raise SemanticGuardrailError("comparison output is incomplete or duplicates a pair")
    elif isinstance(agent_input, PortfolioAllocationInput) and isinstance(
        output.result, AllocationOperationOutput
    ):
        members = {
            *output.result.act_now,
            *output.result.deferred_capacity,
            *output.result.deferred_priority,
            *output.result.investigate,
        }
        if members != set(agent_input.opportunity_refs):
            raise SemanticGuardrailError("allocation output dropped or added an opportunity")


def _referenced_input_refs(output: SpecialistOutput) -> tuple[ObjectRevisionRef, ...]:
    if isinstance(output, PortfolioAllocationOutput):
        return output.result.referenced_input_refs
    return output.referenced_input_refs


def _walk_refs(value: object) -> Iterable[ObjectRevisionRef]:
    if isinstance(value, ObjectRevisionRef):
        yield value
    elif isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            yield from _walk_refs(getattr(value, field_name))
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_refs(item)
    elif isinstance(value, (tuple, list, set)):
        for item in value:
            yield from _walk_refs(item)
