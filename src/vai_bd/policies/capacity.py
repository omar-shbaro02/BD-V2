"""Capacity arithmetic and qualitative-priority allocation invariants."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from vai_bd.domain.cycle import CapacityEnvelope
from vai_bd.domain.opportunity import PursuitDemand
from vai_bd.domain.portfolio import CapacityBoundedAllocationCase
from vai_bd.domain.refs import ObjectRevisionRef
from vai_bd.policies.results import PolicyCheck


@dataclass(frozen=True)
class DemandContext:
    demand: PursuitDemand
    planning_horizon: str


def allocatable_capacity(envelope: CapacityEnvelope) -> Decimal:
    return envelope.usable_time - envelope.fixed_commitments


def validate_allocation(
    allocation: CapacityBoundedAllocationCase,
    envelope: CapacityEnvelope,
    snapshot_members: tuple[ObjectRevisionRef, ...],
    demands: Mapping[ObjectRevisionRef, DemandContext],
    material_priority_edges: tuple[tuple[ObjectRevisionRef, ObjectRevisionRef], ...],
    material_cycles: tuple[tuple[ObjectRevisionRef, ...], ...] = (),
) -> PolicyCheck:
    """Validate arithmetic and precedence without rewriting qualitative priority."""

    reasons: list[str] = []
    tiers = {
        "act_now": set(allocation.act_now),
        "deferred_capacity": set(allocation.deferred_capacity),
        "deferred_priority": set(allocation.deferred_priority),
        "investigate": set(allocation.investigate),
    }
    allocated = set().union(*tiers.values())
    snapshot = set(snapshot_members)
    if allocation.capacity_envelope_ref != envelope.revision_ref:
        reasons.append("allocation_capacity_envelope_revision_mismatch")
    if allocated != snapshot:
        missing = len(snapshot - allocated)
        extra = len(allocated - snapshot)
        reasons.append(f"allocation_membership_mismatch:missing={missing}:extra={extra}")
    if allocation.capacity_unit is not envelope.unit:
        reasons.append("allocation_capacity_unit_mismatch")
    if material_cycles:
        reasons.append("material_comparison_cycle_requires_human_review")

    eligible_demands: dict[ObjectRevisionRef, PursuitDemand] = {}
    for ref in snapshot:
        context = demands.get(ref)
        if context is None:
            reasons.append(f"missing_pursuit_demand:{_label(ref)}")
            continue
        if context.demand.opportunity_case_ref != ref:
            reasons.append(f"pursuit_demand_opportunity_mismatch:{_label(ref)}")
            continue
        if context.demand.unit is not envelope.unit:
            reasons.append(f"demand_unit_mismatch:{_label(ref)}")
            continue
        if context.planning_horizon != envelope.planning_horizon:
            reasons.append(f"demand_horizon_mismatch:{_label(ref)}")
            continue
        eligible_demands[ref] = context.demand

    selected = tiers["act_now"]
    consumption = sum(
        (eligible_demands[ref].estimated_effort for ref in selected if ref in eligible_demands),
        Decimal("0"),
    )
    available = allocatable_capacity(envelope)
    if consumption != allocation.capacity_consumption:
        reasons.append("declared_capacity_consumption_mismatch")
    if consumption > available:
        reasons.append("allocation_exceeds_available_capacity")
    if len(selected) > envelope.max_meaningful_concurrent_pursuits:
        reasons.append("allocation_exceeds_concurrency_cap")

    residual = available - consumption
    for higher, lower in material_priority_edges:
        if lower not in selected or higher in selected:
            continue
        higher_demand = eligible_demands.get(higher)
        lower_demand = eligible_demands.get(lower)
        if higher_demand is None or lower_demand is None:
            continue
        replaceable_capacity = residual + lower_demand.estimated_effort
        if higher_demand.estimated_effort <= replaceable_capacity:
            reasons.append(
                f"materially_superior_feasible_opportunity_not_protected:{_label(higher)}"
            )
        elif higher not in tiers["deferred_capacity"]:
            reasons.append(f"oversized_superior_opportunity_not_deferred_capacity:{_label(higher)}")

    for ref in tiers["deferred_capacity"]:
        demand = eligible_demands.get(ref)
        time_and_slot_available = (
            demand is not None
            and demand.estimated_effort <= residual
            and len(selected) < envelope.max_meaningful_concurrent_pursuits
        )
        if time_and_slot_available:
            reasons.append(f"feasible_opportunity_in_deferred_capacity:{_label(ref)}")
        if demand is not None and demand.smaller_credible_action_available:
            reasons.append(f"smaller_credible_action_requires_explicit_demand:{_label(ref)}")

    return PolicyCheck(not reasons, tuple(reasons))


def _label(ref: ObjectRevisionRef) -> str:
    return f"{ref.object_type}:{ref.object_id}:r{ref.revision}"
