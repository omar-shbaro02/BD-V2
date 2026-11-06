"""Deterministic structured-output mapping into pending domain commands."""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from vai_bd.agents.contracts import (
    AllocationOperationOutput,
    CommercialActionOutput,
    ComparisonOperationOutput,
    EvidenceIntelligenceOutput,
    MarketDiscoveryOutput,
    OpportunityIntelligenceOutput,
    PortfolioAllocationOutput,
    SpecialistOutput,
)
from vai_bd.domain.refs import ObjectRevisionRef


@dataclass(frozen=True)
class PendingDomainCommand:
    """Typed proposal payload awaiting envelope creation and transactional persistence."""

    object_type: str
    payload: dict[str, Any]
    exact_dependencies: tuple[ObjectRevisionRef, ...]


def map_output_to_commands(output: SpecialistOutput) -> tuple[PendingDomainCommand, ...]:
    dependencies = _output_dependencies(output)
    if isinstance(output, MarketDiscoveryOutput):
        commands = [
            _command("CandidateUniverseCoverageState", output, dependencies),
            *(_command("CompanyCandidate", item, dependencies) for item in output.candidates),
        ]
    elif isinstance(output, EvidenceIntelligenceOutput):
        commands = [
            *(_command("EvidenceRecord", item, dependencies) for item in output.evidence_records),
            *(
                _command("MissingEvidenceFlag", item, dependencies)
                for item in output.missing_evidence_flags
            ),
            *(
                _command("ContradictionGroup", item, dependencies)
                for item in output.contradiction_groups
            ),
            *(
                _command("SourceDependencyGroup", item, dependencies)
                for item in output.source_dependency_groups
            ),
        ]
    elif isinstance(output, OpportunityIntelligenceOutput):
        commands = [
            *(_command("ConfidenceAssessment", item, dependencies) for item in output.confidences),
            _command("CompanyOfferFit", output.fit, dependencies),
            _command("NeedHypothesis", output.need, dependencies),
            _command("DecisionOwnerHypothesis", output.decision_owner, dependencies),
            _command("ContactabilityAssessment", output.contactability, dependencies),
            _command("QualificationOutcome", output.qualification, dependencies),
            _command("CommercialOpportunityCase", output, dependencies),
        ]
    elif isinstance(output, PortfolioAllocationOutput):
        result = output.result
        if isinstance(result, ComparisonOperationOutput):
            commands = [
                *(
                    _command("CanonicalPairwiseComparison", item, dependencies)
                    for item in result.comparisons
                ),
                _command("ComparativePriorityState", result, dependencies),
            ]
        elif isinstance(result, AllocationOperationOutput):
            commands = [_command("CapacityBoundedAllocationCase", result, dependencies)]
        else:  # pragma: no cover - discriminated union is exhaustive
            raise TypeError("unsupported portfolio operation output")
    elif isinstance(output, CommercialActionOutput):
        commands = [_command("CommercialActionOpportunity", output, dependencies)]
    else:  # pragma: no cover - union is exhaustive
        raise TypeError("unsupported specialist output")
    return tuple(commands)


def _command(
    object_type: str, value: BaseModel, dependencies: tuple[ObjectRevisionRef, ...]
) -> PendingDomainCommand:
    return PendingDomainCommand(
        object_type=object_type,
        payload=value.model_dump(mode="json", exclude={"referenced_input_refs"}),
        exact_dependencies=dependencies,
    )


def _output_dependencies(output: SpecialistOutput) -> tuple[ObjectRevisionRef, ...]:
    refs = (
        output.result.referenced_input_refs
        if isinstance(output, PortfolioAllocationOutput)
        else output.referenced_input_refs
    )
    return tuple(sorted(refs, key=lambda ref: (ref.object_type, str(ref.object_id), ref.revision)))
