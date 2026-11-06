"""Exact-current dependency and phase-precondition enforcement."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from vai_bd.domain.enums import GateOutcome, ObjectValidity
from vai_bd.domain.refs import ObjectRevisionRef
from vai_bd.policies.revisions import check_required_revisions


class WorkflowPhase(StrEnum):
    BOOTSTRAP = "BOOTSTRAP"
    DISCOVERY = "DISCOVERY"
    EVIDENCE = "EVIDENCE"
    ASSESSMENT = "ASSESSMENT"
    SNAPSHOT = "SNAPSHOT"
    COMPARISON = "COMPARISON"
    ALLOCATION = "ALLOCATION"
    ACTION = "ACTION"
    READINESS = "READINESS"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    REASSESSMENT = "REASSESSMENT"


class PhasePreconditionError(RuntimeError):
    def __init__(self, phase: WorkflowPhase, reasons: tuple[str, ...]) -> None:
        self.phase = phase
        self.reasons = reasons
        super().__init__(f"{phase.value} preconditions failed: {', '.join(reasons)}")


@dataclass(frozen=True)
class PhaseRequirements:
    required_refs: tuple[ObjectRevisionRef, ...]
    required_object_types: frozenset[str]


def require_phase_inputs(
    phase: WorkflowPhase,
    refs: Iterable[ObjectRevisionRef],
    validity_by_ref: Mapping[ObjectRevisionRef, ObjectValidity],
    *,
    gate_outcome: GateOutcome | None = None,
) -> tuple[ObjectRevisionRef, ...]:
    exact_refs = tuple(refs)
    reasons: list[str] = []
    check = check_required_revisions(exact_refs, validity_by_ref)
    reasons.extend(check.reasons)
    types = {ref.object_type for ref in exact_refs}
    required_types = _required_types(phase)
    missing_types = sorted(required_types - types)
    reasons.extend(f"missing_required_object_type:{item}" for item in missing_types)
    if phase is WorkflowPhase.ASSESSMENT and gate_outcome is not GateOutcome.PROCEED:
        reasons.append("assessment_requires_proceed_gate")
    if reasons:
        raise PhasePreconditionError(phase, tuple(reasons))
    return exact_refs


def _required_types(phase: WorkflowPhase) -> frozenset[str]:
    return {
        WorkflowPhase.BOOTSTRAP: frozenset({"OfferProfile", "DecisionCycleContext"}),
        WorkflowPhase.DISCOVERY: frozenset({"OfferProfile", "DecisionCycleContext"}),
        WorkflowPhase.EVIDENCE: frozenset({"CompanyCandidate", "DecisionCycleContext"}),
        WorkflowPhase.ASSESSMENT: frozenset(
            {
                "DecisionCycleContext",
                "OfferProfile",
                "CompanyCandidate",
                "MinimumEvidenceHardEligibilityGateResult",
                "EvidenceRecord",
            }
        ),
        WorkflowPhase.SNAPSHOT: frozenset({"DecisionCycleContext", "QualificationOutcome"}),
        WorkflowPhase.COMPARISON: frozenset(
            {"QualifiedUniverseSnapshot", "CommercialOpportunityCase"}
        ),
        WorkflowPhase.ALLOCATION: frozenset(
            {
                "QualifiedUniverseSnapshot",
                "ComparativePriorityState",
                "PursuitDemand",
                "CapacityEnvelope",
            }
        ),
        WorkflowPhase.ACTION: frozenset(
            {
                "CommercialOpportunityCase",
                "ComparativePriorityState",
                "CapacityBoundedAllocationCase",
            }
        ),
        WorkflowPhase.READINESS: frozenset({"CommercialActionOpportunity"}),
        WorkflowPhase.HUMAN_REVIEW: frozenset({"CommercialActionOpportunity"}),
        WorkflowPhase.REASSESSMENT: frozenset(),
    }[phase]
