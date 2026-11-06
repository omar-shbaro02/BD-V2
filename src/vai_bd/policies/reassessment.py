"""Bounded breadth-first reassessment propagation over exact dependency edges."""

from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from vai_bd.domain.refs import ObjectRevisionRef

MaterialImpactRule = Callable[[ObjectRevisionRef, ObjectRevisionRef], "MaterialImpactDecision"]


@dataclass(frozen=True)
class MaterialImpactDecision:
    materially_affected: bool
    rationale: str
    requires_human_review: bool = False


@dataclass(frozen=True)
class ReassessmentRecord:
    changed_ref: ObjectRevisionRef
    dependent_ref: ObjectRevisionRef
    materially_affected: bool
    rationale: str
    requires_human_review: bool


@dataclass(frozen=True)
class ReassessmentPropagation:
    marked_refs: tuple[ObjectRevisionRef, ...]
    decisions: tuple[ReassessmentRecord, ...]


_CAPACITY_ALLOWED_TYPES = {
    "PursuitDemand",
    "CapacityBoundedAllocationCase",
    "CommercialActionOpportunity",
    "RecommendationReleaseReadiness",
}


def source_dependency_group_roots(
    changed_evidence_ref: ObjectRevisionRef,
    dependency_group_by_evidence: Mapping[ObjectRevisionRef, str | None],
) -> tuple[ObjectRevisionRef, ...]:
    """Expand source unreliability to records sharing the exact dependency group."""

    group = dependency_group_by_evidence.get(changed_evidence_ref)
    if group is None:
        return (changed_evidence_ref,)
    return tuple(
        sorted(
            (
                ref
                for ref, candidate_group in dependency_group_by_evidence.items()
                if candidate_group == group
            ),
            key=_ref_key,
        )
    )


def propagate_reassessment(
    changed_ref: ObjectRevisionRef,
    dependents_by_ref: Mapping[ObjectRevisionRef, tuple[ObjectRevisionRef, ...]],
    impact_rule: MaterialImpactRule,
) -> ReassessmentPropagation:
    """Visit reachable dependents, continuing only through material impacts."""

    queue: deque[ObjectRevisionRef] = deque((changed_ref,))
    visited_edges: set[tuple[ObjectRevisionRef, ObjectRevisionRef]] = set()
    marked: set[ObjectRevisionRef] = set()
    decisions: list[ReassessmentRecord] = []
    capacity_change = changed_ref.object_type == "CapacityEnvelope"
    while queue:
        cause = queue.popleft()
        for dependent in sorted(dependents_by_ref.get(cause, ()), key=_ref_key):
            edge = (cause, dependent)
            if edge in visited_edges:
                continue
            visited_edges.add(edge)
            if capacity_change and dependent.object_type not in _CAPACITY_ALLOWED_TYPES:
                decision = MaterialImpactDecision(
                    False, "capacity_change_cannot_alter_commercial_quality_judgments"
                )
            else:
                decision = impact_rule(cause, dependent)
            decisions.append(
                ReassessmentRecord(
                    changed_ref=cause,
                    dependent_ref=dependent,
                    materially_affected=decision.materially_affected,
                    rationale=decision.rationale,
                    requires_human_review=decision.requires_human_review,
                )
            )
            if decision.materially_affected and dependent not in marked:
                marked.add(dependent)
                queue.append(dependent)
    return ReassessmentPropagation(
        tuple(sorted(marked, key=_ref_key)),
        tuple(decisions),
    )


def _ref_key(ref: ObjectRevisionRef) -> tuple[str, str, int]:
    return (ref.object_type, str(ref.object_id), ref.revision)
