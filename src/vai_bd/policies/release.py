"""Authorization-independent recommendation release-readiness checklist."""

from dataclasses import dataclass

from vai_bd.domain.enums import ReleaseReadinessState
from vai_bd.policies.results import PolicyCheck


@dataclass(frozen=True)
class ReleaseReadinessInputs:
    upstream_revisions: PolicyCheck
    contradictions_disclosed: bool
    limitations_disclosed: bool
    action_type_present: bool
    action_description_present: bool
    action_scope_present: bool
    rationale_present: bool
    evidence_refs_present: bool
    allocation_required: bool
    allocation_valid: bool
    unresolved_material_defect: bool
    disclosed_limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReleaseReadinessDecision:
    state: ReleaseReadinessState
    blocking_conditions: tuple[str, ...]
    limitations: tuple[str, ...]


def evaluate_release_readiness(inputs: ReleaseReadinessInputs) -> ReleaseReadinessDecision:
    blockers = list(inputs.upstream_revisions.reasons)
    checks = {
        "contradictions_not_disclosed": inputs.contradictions_disclosed,
        "limitations_not_disclosed": inputs.limitations_disclosed,
        "action_type_missing": inputs.action_type_present,
        "action_description_missing": inputs.action_description_present,
        "action_scope_missing": inputs.action_scope_present,
        "rationale_missing": inputs.rationale_present,
        "evidence_refs_missing": inputs.evidence_refs_present,
    }
    blockers.extend(reason for reason, passed in checks.items() if not passed)
    if inputs.allocation_required and not inputs.allocation_valid:
        blockers.append("required_allocation_invalid")
    if inputs.unresolved_material_defect:
        blockers.append("unresolved_material_defect")
    if blockers:
        return ReleaseReadinessDecision(
            ReleaseReadinessState.NOT_READY, tuple(blockers), inputs.disclosed_limitations
        )
    if inputs.disclosed_limitations:
        return ReleaseReadinessDecision(
            ReleaseReadinessState.READY_WITH_DISCLOSED_LIMITATIONS,
            (),
            inputs.disclosed_limitations,
        )
    return ReleaseReadinessDecision(ReleaseReadinessState.RELEASE_READY, (), ())
