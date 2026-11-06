"""Snapshot, comparison, priority, and allocation contracts."""

from decimal import Decimal

from pydantic import Field, model_validator

from vai_bd.domain.enums import ComparisonRelationship, EffortUnit
from vai_bd.domain.envelopes import GovernedObject
from vai_bd.domain.refs import (
    AllocationMemberReason,
    ExcludedOrUnresolvedRef,
    NonEmptyStr,
    ObjectRevisionRef,
)


class QualifiedUniverseSnapshot(GovernedObject):
    decision_cycle_ref: ObjectRevisionRef
    opportunity_case_revision_refs: tuple[ObjectRevisionRef, ...]
    excluded_or_unresolved_refs_with_reasons: tuple[ExcludedOrUnresolvedRef, ...]

    @model_validator(mode="after")
    def snapshot_members_must_be_unique(self) -> "QualifiedUniverseSnapshot":
        if len(self.opportunity_case_revision_refs) != len(
            set(self.opportunity_case_revision_refs)
        ):
            raise ValueError("snapshot opportunity revisions must be unique")
        return self


class CanonicalPairwiseComparison(GovernedObject):
    snapshot_ref: ObjectRevisionRef
    subject_opportunity_revision: ObjectRevisionRef
    comparator_opportunity_revision: ObjectRevisionRef
    relationship: ComparisonRelationship
    material_reason: NonEmptyStr
    secondary_factors: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def comparison_members_must_differ(self) -> "CanonicalPairwiseComparison":
        if self.subject_opportunity_revision == self.comparator_opportunity_revision:
            raise ValueError("an opportunity cannot be compared with itself")
        return self


class PriorityRelation(GovernedObject):
    higher_or_subject_ref: ObjectRevisionRef
    lower_or_comparator_ref: ObjectRevisionRef
    relationship: ComparisonRelationship
    material_reason: NonEmptyStr


class ComparativePriorityState(GovernedObject):
    snapshot_ref: ObjectRevisionRef
    partial_order: tuple[PriorityRelation, ...]
    cycles: tuple[tuple[ObjectRevisionRef, ...], ...] = ()
    near_ties: tuple[tuple[ObjectRevisionRef, ObjectRevisionRef], ...] = ()
    indeterminate_sets: tuple[tuple[ObjectRevisionRef, ...], ...] = ()
    material_reasons: tuple[NonEmptyStr, ...]


class AlternativePortfolio(GovernedObject):
    opportunity_refs: tuple[ObjectRevisionRef, ...]
    rationale: NonEmptyStr


class CapacityBoundedAllocationCase(GovernedObject):
    snapshot_ref: ObjectRevisionRef
    capacity_envelope_ref: ObjectRevisionRef
    priority_state_ref: ObjectRevisionRef
    act_now: tuple[ObjectRevisionRef, ...]
    deferred_capacity: tuple[ObjectRevisionRef, ...]
    deferred_priority: tuple[ObjectRevisionRef, ...]
    investigate: tuple[ObjectRevisionRef, ...]
    capacity_consumption: Decimal = Field(ge=0)
    capacity_unit: EffortUnit
    marginal_reasons: tuple[AllocationMemberReason, ...]
    material_uncertainties: tuple[NonEmptyStr, ...]
    alternative_portfolios_for_human_review: tuple[AlternativePortfolio, ...] = ()

    @model_validator(mode="after")
    def allocation_tiers_must_be_disjoint(self) -> "CapacityBoundedAllocationCase":
        tiers = (
            self.act_now,
            self.deferred_capacity,
            self.deferred_priority,
            self.investigate,
        )
        flattened = tuple(ref for tier in tiers for ref in tier)
        if len(flattened) != len(set(flattened)):
            raise ValueError("an opportunity may appear in only one allocation tier")
        return self
