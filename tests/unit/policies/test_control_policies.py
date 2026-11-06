"""Capacity, readiness, execution, and reassessment policy tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from vai_bd.domain.actions import ActionScope, CommercialActionOpportunity
from vai_bd.domain.authorization import HumanAuthorizationEvent
from vai_bd.domain.cycle import CapacityEnvelope
from vai_bd.domain.enums import (
    ActionScopeKind,
    ActionType,
    ActorKind,
    EffortUnit,
    HumanAuthorizationState,
    ObjectValidity,
    ReleaseReadinessState,
)
from vai_bd.domain.opportunity import PursuitDemand
from vai_bd.domain.portfolio import CapacityBoundedAllocationCase
from vai_bd.domain.refs import ActorRef, ObjectRevisionRef
from vai_bd.policies.capacity import DemandContext, allocatable_capacity, validate_allocation
from vai_bd.policies.execution import (
    ExternalActionRestriction,
    conformity_restriction,
    evaluate_execution_eligibility,
)
from vai_bd.policies.reassessment import (
    MaterialImpactDecision,
    propagate_reassessment,
    source_dependency_group_roots,
)
from vai_bd.policies.release import ReleaseReadinessInputs, evaluate_release_readiness
from vai_bd.policies.results import PolicyCheck

NOW = datetime(2026, 10, 9, 12, tzinfo=UTC)
SYSTEM = ActorRef(
    actor_id=UUID("00000000-0000-0000-0000-000000000001"),
    actor_kind=ActorKind.SYSTEM,
    display_name="System",
)
HUMAN = ActorRef(
    actor_id=UUID("00000000-0000-0000-0000-000000000002"),
    actor_kind=ActorKind.HUMAN,
    display_name="Operator",
)


def ref(number: int, object_type: str = "CommercialOpportunityCase") -> ObjectRevisionRef:
    return ObjectRevisionRef(
        object_id=UUID(f"00000000-0000-0000-0000-{number:012d}"),
        object_type=object_type,
        revision=1,
    )


def base(number: int, object_type: str, **extra: object) -> dict[str, object]:
    return {
        "object_id": ref(number, object_type).object_id,
        "object_type": object_type,
        "revision": 1,
        "created_at": NOW,
        "created_by": SYSTEM,
        **extra,
    }


def envelope(*, usable: str = "10", fixed: str = "2", cap: int = 2) -> CapacityEnvelope:
    return CapacityEnvelope(
        **base(80, "CapacityEnvelope"),
        decision_cycle_ref=ref(81, "DecisionCycleContext"),
        usable_time=Decimal(usable),
        unit=EffortUnit.HOUR,
        planning_horizon="week",
        max_meaningful_concurrent_pursuits=cap,
        fixed_commitments=Decimal(fixed),
        review_trigger="change",
        effective_date=date(2026, 10, 9),
    )


def demand(number: int, opportunity: ObjectRevisionRef, effort: str) -> PursuitDemand:
    return PursuitDemand(
        **base(number, "PursuitDemand"),
        opportunity_case_ref=opportunity,
        next_action_description="next action",
        estimated_effort=Decimal(effort),
        unit=EffortUnit.HOUR,
        smaller_credible_action_available=False,
        rationale="fixture",
    )


def allocation(
    *,
    act_now: tuple[ObjectRevisionRef, ...],
    deferred_capacity: tuple[ObjectRevisionRef, ...] = (),
    deferred_priority: tuple[ObjectRevisionRef, ...] = (),
    investigate: tuple[ObjectRevisionRef, ...] = (),
    consumption: str,
) -> CapacityBoundedAllocationCase:
    return CapacityBoundedAllocationCase(
        **base(90, "CapacityBoundedAllocationCase"),
        snapshot_ref=ref(91, "QualifiedUniverseSnapshot"),
        capacity_envelope_ref=ref(80, "CapacityEnvelope"),
        priority_state_ref=ref(92, "ComparativePriorityState"),
        act_now=act_now,
        deferred_capacity=deferred_capacity,
        deferred_priority=deferred_priority,
        investigate=investigate,
        capacity_consumption=Decimal(consumption),
        capacity_unit=EffortUnit.HOUR,
        marginal_reasons=(),
        material_uncertainties=(),
    )


def contexts(
    values: dict[ObjectRevisionRef, PursuitDemand],
) -> dict[ObjectRevisionRef, DemandContext]:
    return {key: DemandContext(value, "week") for key, value in values.items()}


def test_capacity_subtracts_fixed_commitments_with_exact_decimals() -> None:
    assert allocatable_capacity(envelope(usable="5.50", fixed="1.25")) == Decimal("4.25")


def test_valid_allocation_allows_smaller_lower_item_when_top_cannot_fit() -> None:
    top, smaller = ref(1), ref(2)
    demands = contexts({top: demand(11, top, "9"), smaller: demand(12, smaller, "4")})
    result = validate_allocation(
        allocation(act_now=(smaller,), deferred_capacity=(top,), consumption="4"),
        envelope(usable="6", fixed="1"),
        (top, smaller),
        demands,
        ((top, smaller),),
    )
    assert result.is_valid


def test_materially_superior_feasible_item_is_protected() -> None:
    top, lower = ref(1), ref(2)
    result = validate_allocation(
        allocation(act_now=(lower,), deferred_priority=(top,), consumption="4"),
        envelope(usable="6", fixed="1"),
        (top, lower),
        contexts({top: demand(11, top, "5"), lower: demand(12, lower, "4")}),
        ((top, lower),),
    )
    assert not result.is_valid
    assert any(reason.startswith("materially_superior_feasible") for reason in result.reasons)


def test_capacity_validates_zero_residual_and_concurrency_independently() -> None:
    a, b = ref(1), ref(2)
    demands = contexts({a: demand(11, a, "2.5"), b: demand(12, b, "2.5")})
    full = validate_allocation(
        allocation(act_now=(a, b), consumption="5.0"),
        envelope(usable="5", fixed="0", cap=2),
        (a, b),
        demands,
        (),
    )
    assert full.is_valid
    capped = validate_allocation(
        allocation(act_now=(a, b), consumption="5.0"),
        envelope(usable="10", fixed="0", cap=1),
        (a, b),
        demands,
        (),
    )
    assert "allocation_exceeds_concurrency_cap" in capped.reasons


def test_capacity_rejects_horizon_mismatch_and_material_cycle() -> None:
    item = ref(1)
    result = validate_allocation(
        allocation(act_now=(item,), consumption="0"),
        envelope(),
        (item,),
        {item: DemandContext(demand(11, item, "2"), "month")},
        (),
        ((item, ref(2)),),
    )
    assert "material_comparison_cycle_requires_human_review" in result.reasons
    assert any(reason.startswith("demand_horizon_mismatch") for reason in result.reasons)


def test_capacity_requires_exact_envelope_and_opportunity_demand_refs() -> None:
    item = ref(1)
    mismatched_allocation = allocation(act_now=(item,), consumption="0").model_copy(
        update={"capacity_envelope_ref": ref(999, "CapacityEnvelope")}
    )
    wrong_demand = demand(11, ref(2), "2")
    result = validate_allocation(
        mismatched_allocation,
        envelope(),
        (item,),
        {item: DemandContext(wrong_demand, "week")},
        (),
    )
    assert "allocation_capacity_envelope_revision_mismatch" in result.reasons
    assert any(
        reason.startswith("pursuit_demand_opportunity_mismatch") for reason in result.reasons
    )


def test_capacity_validation_does_not_mutate_priority_edges() -> None:
    a, b = ref(1), ref(2)
    edges = ((a, b),)
    validate_allocation(
        allocation(act_now=(a,), deferred_priority=(b,), consumption="2"),
        envelope(),
        (a, b),
        contexts({a: demand(11, a, "2"), b: demand(12, b, "2")}),
        edges,
    )
    assert edges == ((a, b),)


def test_release_readiness_is_independent_of_authorization() -> None:
    ready = evaluate_release_readiness(
        ReleaseReadinessInputs(
            upstream_revisions=PolicyCheck(True),
            contradictions_disclosed=True,
            limitations_disclosed=True,
            action_type_present=True,
            action_description_present=True,
            action_scope_present=True,
            rationale_present=True,
            evidence_refs_present=True,
            allocation_required=True,
            allocation_valid=True,
            unresolved_material_defect=False,
        )
    )
    assert ready.state is ReleaseReadinessState.RELEASE_READY
    limited = evaluate_release_readiness(
        ReleaseReadinessInputs(
            **{**ready_inputs(), "disclosed_limitations": ("source age near threshold",)}
        )
    )
    assert limited.state is ReleaseReadinessState.READY_WITH_DISCLOSED_LIMITATIONS


def ready_inputs() -> dict[str, object]:
    return {
        "upstream_revisions": PolicyCheck(True),
        "contradictions_disclosed": True,
        "limitations_disclosed": True,
        "action_type_present": True,
        "action_description_present": True,
        "action_scope_present": True,
        "rationale_present": True,
        "evidence_refs_present": True,
        "allocation_required": False,
        "allocation_valid": False,
        "unresolved_material_defect": False,
    }


def cao(*, validity: ObjectValidity = ObjectValidity.CURRENT) -> CommercialActionOpportunity:
    dependency = ref(33, "EvidenceRecord")
    return CommercialActionOpportunity(
        **base(30, "CommercialActionOpportunity", validity=validity, dependencies=(dependency,)),
        opportunity_case_ref=ref(31),
        comparative_priority_ref=ref(32, "ComparativePriorityState"),
        allocation_case_ref=ref(34, "CapacityBoundedAllocationCase"),
        action_type=ActionType.COMMERCIAL_PURSUIT,
        action_description="send approved note",
        action_scope=ActionScope(
            kind=ActionScopeKind.EXTERNAL_COMMUNICATION,
            description="one email",
        ),
        rationale="approved pursuit",
        evidence_refs=(dependency,),
        material_uncertainties=(),
    )


def approval(item: CommercialActionOpportunity) -> HumanAuthorizationEvent:
    return HumanAuthorizationEvent(
        authorization_id="auth-1",
        cao_revision_ref=item.revision_ref,
        state=HumanAuthorizationState.APPROVED,
        requested_human_authority_ref=HUMAN,
        actual_deciding_human_ref=HUMAN,
        decision_timestamp=NOW,
        authorized_action="send approved note",
        authorized_scope=item.action_scope,
        rationale="human approved",
    )


def test_execution_requires_exact_current_approval() -> None:
    item = cao()
    result = evaluate_execution_eligibility(
        item,
        approval(item),
        "send approved note",
        item.action_scope,
        {item.dependencies[0]: ObjectValidity.CURRENT},
        ExternalActionRestriction(True, "operator-enabled environment"),
    )
    assert result.eligible


def test_execution_is_always_false_in_conformity_profile() -> None:
    item = cao()
    result = evaluate_execution_eligibility(
        item,
        approval(item),
        "send approved note",
        item.action_scope,
        {item.dependencies[0]: ObjectValidity.CURRENT},
        conformity_restriction(),
    )
    assert not result.eligible
    assert result.reasons == (
        "external_execution_restricted:conformity_profile_forbids_external_execution",
    )


def test_execution_rejects_mutually_matching_request_and_approval_that_differ_from_cao() -> None:
    item = cao()
    altered_scope = ActionScope(
        kind=ActionScopeKind.EXTERNAL_COMMUNICATION,
        description="different audience",
    )
    authorization = approval(item).model_copy(
        update={"authorized_action": "different action", "authorized_scope": altered_scope}
    )
    result = evaluate_execution_eligibility(
        item,
        authorization,
        "different action",
        altered_scope,
        {item.dependencies[0]: ObjectValidity.CURRENT},
        ExternalActionRestriction(True, "enabled"),
    )
    assert not result.eligible
    assert "requested_action_does_not_match_cao" in result.reasons
    assert "requested_scope_does_not_match_cao" in result.reasons


def test_reassessment_only_propagates_through_material_dependency_paths() -> None:
    changed, affected, downstream, unaffected, unrelated = (
        ref(1, "EvidenceRecord"),
        ref(2, "CompanyOfferFit"),
        ref(3, "CommercialOpportunityCase"),
        ref(4, "NeedHypothesis"),
        ref(5, "CommercialActionOpportunity"),
    )
    graph = {changed: (affected, unaffected), affected: (downstream,), unrelated: (downstream,)}

    def impact(_cause: ObjectRevisionRef, dependent: ObjectRevisionRef) -> MaterialImpactDecision:
        return MaterialImpactDecision(dependent != unaffected, "fixture materiality")

    result = propagate_reassessment(changed, graph, impact)
    assert set(result.marked_refs) == {affected, downstream}
    assert unaffected not in result.marked_refs
    assert unrelated not in result.marked_refs
    assert any(not decision.materially_affected for decision in result.decisions)


def test_capacity_reassessment_cannot_change_fit_need_or_evidence() -> None:
    changed = ref(1, "CapacityEnvelope")
    fit = ref(2, "CompanyOfferFit")
    allocation_ref = ref(3, "CapacityBoundedAllocationCase")
    action = ref(4, "CommercialActionOpportunity")
    graph = {changed: (fit, allocation_ref), allocation_ref: (action,)}
    result = propagate_reassessment(
        changed,
        graph,
        lambda _cause, _dependent: MaterialImpactDecision(True, "capacity impact"),
    )
    assert set(result.marked_refs) == {allocation_ref, action}
    fit_decision = next(item for item in result.decisions if item.dependent_ref == fit)
    assert not fit_decision.materially_affected


def test_source_unreliability_expands_only_the_shared_dependency_group() -> None:
    changed = ref(1, "EvidenceRecord")
    shared = ref(2, "EvidenceRecord")
    independent = ref(3, "EvidenceRecord")
    roots = source_dependency_group_roots(
        changed,
        {changed: "registry-record", shared: "registry-record", independent: "filing"},
    )
    assert roots == (changed, shared)
