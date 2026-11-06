"""Canonical comparison pairs, inverses, completeness, and cycle analysis."""

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import combinations

from vai_bd.domain.enums import ComparisonRelationship
from vai_bd.domain.portfolio import CanonicalPairwiseComparison
from vai_bd.domain.refs import ObjectRevisionRef
from vai_bd.policies.results import PolicyCheck

Pair = tuple[ObjectRevisionRef, ObjectRevisionRef]

_INVERSE = {
    ComparisonRelationship.MATERIALLY_ABOVE: ComparisonRelationship.MATERIALLY_BELOW,
    ComparisonRelationship.ABOVE: ComparisonRelationship.BELOW,
    ComparisonRelationship.NEAR_TIE: ComparisonRelationship.NEAR_TIE,
    ComparisonRelationship.TIE: ComparisonRelationship.TIE,
    ComparisonRelationship.BELOW: ComparisonRelationship.ABOVE,
    ComparisonRelationship.MATERIALLY_BELOW: ComparisonRelationship.MATERIALLY_ABOVE,
    ComparisonRelationship.INDETERMINATE: ComparisonRelationship.INDETERMINATE,
}


@dataclass(frozen=True)
class ComparisonAnalysis:
    strict_edges: tuple[Pair, ...]
    material_edges: tuple[Pair, ...]
    cycles: tuple[tuple[ObjectRevisionRef, ...], ...]
    near_ties: tuple[Pair, ...]
    ties: tuple[Pair, ...]
    indeterminate_pairs: tuple[Pair, ...]


def inverse_relationship(relationship: ComparisonRelationship) -> ComparisonRelationship:
    return _INVERSE[relationship]


def canonical_pair(first: ObjectRevisionRef, second: ObjectRevisionRef) -> Pair:
    if first == second:
        raise ValueError("a comparison pair requires two distinct revisions")
    return tuple(sorted((first, second), key=_ref_key))  # type: ignore[return-value]


def generate_pairs(refs: Iterable[ObjectRevisionRef]) -> tuple[Pair, ...]:
    members = sorted(set(refs), key=_ref_key)
    return tuple(combinations(members, 2))


def validate_comparison_set(
    snapshot_refs: Iterable[ObjectRevisionRef],
    comparisons: Iterable[CanonicalPairwiseComparison],
) -> PolicyCheck:
    expected = set(generate_pairs(snapshot_refs))
    observed: list[Pair] = [
        canonical_pair(item.subject_opportunity_revision, item.comparator_opportunity_revision)
        for item in comparisons
    ]
    reasons: list[str] = []
    if len(observed) != len(set(observed)):
        reasons.append("duplicate_comparison_pair")
    missing = expected - set(observed)
    extra = set(observed) - expected
    if missing:
        reasons.append(f"missing_comparison_pairs:{len(missing)}")
    if extra:
        reasons.append(f"out_of_snapshot_comparison_pairs:{len(extra)}")
    return PolicyCheck(not reasons, tuple(reasons))


def analyze_comparisons(
    members: Iterable[ObjectRevisionRef],
    comparisons: Iterable[CanonicalPairwiseComparison],
) -> ComparisonAnalysis:
    member_set = set(members)
    strict: set[Pair] = set()
    material: set[Pair] = set()
    near_ties: set[Pair] = set()
    ties: set[Pair] = set()
    indeterminate: set[Pair] = set()
    for item in comparisons:
        subject = item.subject_opportunity_revision
        comparator = item.comparator_opportunity_revision
        if subject not in member_set or comparator not in member_set:
            continue
        relationship = item.relationship
        pair = canonical_pair(subject, comparator)
        if relationship in {
            ComparisonRelationship.MATERIALLY_ABOVE,
            ComparisonRelationship.ABOVE,
        }:
            edge = (subject, comparator)
            strict.add(edge)
            if relationship is ComparisonRelationship.MATERIALLY_ABOVE:
                material.add(edge)
        elif relationship in {
            ComparisonRelationship.MATERIALLY_BELOW,
            ComparisonRelationship.BELOW,
        }:
            edge = (comparator, subject)
            strict.add(edge)
            if relationship is ComparisonRelationship.MATERIALLY_BELOW:
                material.add(edge)
        elif relationship is ComparisonRelationship.NEAR_TIE:
            near_ties.add(pair)
        elif relationship is ComparisonRelationship.TIE:
            ties.add(pair)
        else:
            indeterminate.add(pair)

    return ComparisonAnalysis(
        strict_edges=tuple(sorted(strict, key=_pair_key)),
        material_edges=tuple(sorted(material, key=_pair_key)),
        cycles=_strongly_connected_cycles(member_set, strict),
        near_ties=tuple(sorted(near_ties, key=_pair_key)),
        ties=tuple(sorted(ties, key=_pair_key)),
        indeterminate_pairs=tuple(sorted(indeterminate, key=_pair_key)),
    )


def _strongly_connected_cycles(
    members: set[ObjectRevisionRef], edges: set[Pair]
) -> tuple[tuple[ObjectRevisionRef, ...], ...]:
    adjacency: dict[ObjectRevisionRef, list[ObjectRevisionRef]] = {member: [] for member in members}
    for higher, lower in edges:
        adjacency[higher].append(lower)
    index = 0
    indices: dict[ObjectRevisionRef, int] = {}
    lowlinks: dict[ObjectRevisionRef, int] = {}
    stack: list[ObjectRevisionRef] = []
    on_stack: set[ObjectRevisionRef] = set()
    components: list[tuple[ObjectRevisionRef, ...]] = []

    def visit(node: ObjectRevisionRef) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for neighbor in adjacency[node]:
            if neighbor not in indices:
                visit(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[neighbor])
        if lowlinks[node] == indices[node]:
            component: list[ObjectRevisionRef] = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            if len(component) > 1:
                components.append(tuple(sorted(component, key=_ref_key)))

    for member in sorted(members, key=_ref_key):
        if member not in indices:
            visit(member)
    return tuple(sorted(components, key=lambda component: _ref_key(component[0])))


def _ref_key(ref: ObjectRevisionRef) -> tuple[str, str, int]:
    return (ref.object_type, str(ref.object_id), ref.revision)


def _pair_key(pair: Pair) -> tuple[tuple[str, str, int], tuple[str, str, int]]:
    return (_ref_key(pair[0]), _ref_key(pair[1]))
