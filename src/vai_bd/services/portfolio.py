"""Portfolio specialist output persistence plus deterministic consistency checks."""

from typing import cast

from sqlalchemy.orm import Session

from vai_bd.agents.contracts import (
    AllocationOperationOutput,
    ComparisonOperationOutput,
    PortfolioAllocationInput,
    PortfolioAllocationOutput,
    PortfolioComparisonInput,
    SpecialistOutput,
)
from vai_bd.domain.enums import ComparisonRelationship
from vai_bd.domain.opportunity import PursuitDemand
from vai_bd.domain.portfolio import (
    AlternativePortfolio,
    CanonicalPairwiseComparison,
    CapacityBoundedAllocationCase,
    ComparativePriorityState,
    PriorityRelation,
)
from vai_bd.domain.refs import AllocationMemberReason, ObjectRevisionRef
from vai_bd.persistence.orm import AllocationMemberRow
from vai_bd.persistence.repositories import (
    ComparisonRepository,
    GovernedObjectRepository,
)
from vai_bd.policies.capacity import DemandContext, validate_allocation
from vai_bd.policies.comparisons import analyze_comparisons, inverse_relationship
from vai_bd.services.common import RevisionFactory
from vai_bd.services.specialists import PersistCallback


def comparison_persistence(
    factory: RevisionFactory, agent_input: PortfolioComparisonInput
) -> PersistCallback:
    def persist(session: Session, raw_output: SpecialistOutput) -> tuple[ObjectRevisionRef, ...]:
        wrapped = cast(PortfolioAllocationOutput, raw_output)
        output = cast(ComparisonOperationOutput, wrapped.result)
        objects = GovernedObjectRepository(session)
        comparison_repository = ComparisonRepository(session, objects)
        comparisons: list[CanonicalPairwiseComparison] = []
        for proposal in output.comparisons:
            comparison_ref = factory.new_ref("CanonicalPairwiseComparison")
            comparison = CanonicalPairwiseComparison(
                **factory.envelope(
                    comparison_ref,
                    dependencies=(
                        agent_input.snapshot_ref,
                        proposal.subject_ref,
                        proposal.comparator_ref,
                    ),
                ),
                snapshot_ref=agent_input.snapshot_ref,
                subject_opportunity_revision=proposal.subject_ref,
                comparator_opportunity_revision=proposal.comparator_ref,
                relationship=proposal.relationship,
                material_reason=proposal.material_reason,
                secondary_factors=proposal.secondary_factors,
            )
            comparison_repository.append(comparison)
            comparisons.append(comparison)
        analysis = analyze_comparisons(agent_input.opportunity_refs, comparisons)
        authored_by_edge: dict[
            tuple[ObjectRevisionRef, ObjectRevisionRef], CanonicalPairwiseComparison
        ] = {}
        for comparison in comparisons:
            if comparison.relationship in {
                ComparisonRelationship.MATERIALLY_ABOVE,
                ComparisonRelationship.ABOVE,
            }:
                edge = (
                    comparison.subject_opportunity_revision,
                    comparison.comparator_opportunity_revision,
                )
            elif comparison.relationship in {
                ComparisonRelationship.MATERIALLY_BELOW,
                ComparisonRelationship.BELOW,
            }:
                edge = (
                    comparison.comparator_opportunity_revision,
                    comparison.subject_opportunity_revision,
                )
            else:
                continue
            authored_by_edge[edge] = comparison
        relations: list[PriorityRelation] = []
        for higher, lower in analysis.strict_edges:
            authored = authored_by_edge[(higher, lower)]
            relationship = authored.relationship
            if relationship in {
                ComparisonRelationship.MATERIALLY_BELOW,
                ComparisonRelationship.BELOW,
            }:
                relationship = inverse_relationship(relationship)
            relation_ref = factory.new_ref("PriorityRelation")
            relation = PriorityRelation(
                **factory.envelope(
                    relation_ref,
                    dependencies=(authored.revision_ref, higher, lower),
                ),
                higher_or_subject_ref=higher,
                lower_or_comparator_ref=lower,
                relationship=relationship,
                material_reason=authored.material_reason,
            )
            objects.append(relation)
            relations.append(relation)
        priority_ref = factory.new_ref("ComparativePriorityState")
        priority = ComparativePriorityState(
            **factory.envelope(
                priority_ref,
                dependencies=(
                    *agent_input.exact_input_refs,
                    *(item.revision_ref for item in comparisons),
                    *(item.revision_ref for item in relations),
                ),
            ),
            snapshot_ref=agent_input.snapshot_ref,
            partial_order=tuple(relations),
            cycles=analysis.cycles,
            near_ties=analysis.near_ties,
            indeterminate_sets=(
                *(tuple(pair) for pair in analysis.ties),
                *(tuple(pair) for pair in analysis.indeterminate_pairs),
            ),
            material_reasons=output.material_reasons,
        )
        objects.append(priority)
        return (
            *(item.revision_ref for item in comparisons),
            *(item.revision_ref for item in relations),
            priority.revision_ref,
        )

    return persist


def allocation_persistence(
    factory: RevisionFactory, agent_input: PortfolioAllocationInput
) -> PersistCallback:
    def persist(session: Session, raw_output: SpecialistOutput) -> tuple[ObjectRevisionRef, ...]:
        from vai_bd.domain.cycle import CapacityEnvelope

        wrapped = cast(PortfolioAllocationOutput, raw_output)
        output = cast(AllocationOperationOutput, wrapped.result)
        objects = GovernedObjectRepository(session)
        capacity = objects.get_exact(agent_input.capacity_envelope_ref, CapacityEnvelope)
        priority = objects.get_exact(agent_input.priority_state_ref, ComparativePriorityState)
        demand_contexts: dict[ObjectRevisionRef, DemandContext] = {}
        effort_by_opportunity = {}
        for item in agent_input.demands:
            demand = objects.get_exact(item.demand_ref, PursuitDemand)
            demand_contexts[item.opportunity_ref] = DemandContext(
                demand=demand, planning_horizon=agent_input.planning_horizon
            )
            effort_by_opportunity[item.opportunity_ref] = demand.estimated_effort
        alternatives: list[AlternativePortfolio] = []
        for proposal in output.alternative_portfolios:
            alternative_ref = factory.new_ref("AlternativePortfolio")
            alternative = AlternativePortfolio(
                **factory.envelope(
                    alternative_ref,
                    dependencies=(agent_input.priority_state_ref, *proposal.opportunity_refs),
                ),
                opportunity_refs=proposal.opportunity_refs,
                rationale=proposal.rationale,
            )
            objects.append(alternative)
            alternatives.append(alternative)
        allocation_ref = factory.new_ref("CapacityBoundedAllocationCase")
        allocation = CapacityBoundedAllocationCase(
            **factory.envelope(allocation_ref, dependencies=agent_input.exact_input_refs),
            snapshot_ref=agent_input.snapshot_ref,
            capacity_envelope_ref=agent_input.capacity_envelope_ref,
            priority_state_ref=agent_input.priority_state_ref,
            act_now=output.act_now,
            deferred_capacity=output.deferred_capacity,
            deferred_priority=output.deferred_priority,
            investigate=output.investigate,
            capacity_consumption=output.capacity_consumption,
            capacity_unit=output.capacity_unit,
            marginal_reasons=tuple(
                AllocationMemberReason(opportunity_ref=item.opportunity_ref, reason=item.reason)
                for item in output.marginal_reasons
            ),
            material_uncertainties=output.material_uncertainties,
            alternative_portfolios_for_human_review=tuple(alternatives),
        )
        material_edges = tuple(
            (item.higher_or_subject_ref, item.lower_or_comparator_ref)
            for item in priority.partial_order
            if item.relationship is ComparisonRelationship.MATERIALLY_ABOVE
        )
        check = validate_allocation(
            allocation,
            capacity,
            agent_input.opportunity_refs,
            demand_contexts,
            material_edges,
            priority.cycles,
        )
        if not check.is_valid:
            raise ValueError("invalid allocation: " + "; ".join(check.reasons))
        objects.append(allocation)
        tiers = {
            "ACT_NOW": allocation.act_now,
            "DEFERRED_CAPACITY": allocation.deferred_capacity,
            "DEFERRED_PRIORITY": allocation.deferred_priority,
            "INVESTIGATE": allocation.investigate,
        }
        reason_by_ref = {item.opportunity_ref: item.reason for item in allocation.marginal_reasons}
        for tier, members in tiers.items():
            for member in members:
                session.add(
                    AllocationMemberRow(
                        allocation_id=allocation.object_id,
                        allocation_revision=allocation.revision,
                        opportunity_id=member.object_id,
                        opportunity_revision=member.revision,
                        tier=tier,
                        reason=reason_by_ref.get(member),
                        effort=effort_by_opportunity.get(member),
                    )
                )
        session.flush()
        return (*(item.revision_ref for item in alternatives), allocation.revision_ref)

    return persist
