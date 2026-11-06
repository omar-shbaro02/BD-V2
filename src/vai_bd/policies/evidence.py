"""Deterministic evidence currentness, independence, and contradiction rules."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date

from vai_bd.domain.enums import EvidenceAdmissibility, EvidenceCurrentness
from vai_bd.domain.evidence import EvidenceRecord
from vai_bd.domain.refs import ObjectRevisionRef


@dataclass(frozen=True)
class SourceCurrentnessRule:
    source_type: str
    maximum_age_days: int

    def __post_init__(self) -> None:
        if not self.source_type.strip():
            raise ValueError("source_type must not be blank")
        if self.maximum_age_days < 0:
            raise ValueError("maximum_age_days must be non-negative")


def compute_currentness(
    record: EvidenceRecord,
    *,
    as_of: date,
    rules: Mapping[str, SourceCurrentnessRule],
) -> EvidenceCurrentness:
    """Compute currentness without mutating or discarding the evidence record."""

    rule = rules.get(record.source_type)
    if rule is None or record.source_date is None or record.source_date > as_of:
        return EvidenceCurrentness.UNKNOWN
    age_days = (as_of - record.source_date).days
    if age_days <= rule.maximum_age_days:
        return EvidenceCurrentness.CURRENT
    return EvidenceCurrentness.STALE


def satisfies_admissible_current_requirement(record: EvidenceRecord) -> bool:
    return (
        record.admissibility is EvidenceAdmissibility.ADMISSIBLE
        and record.currentness is EvidenceCurrentness.CURRENT
    )


def independent_eligible_evidence(
    records: Iterable[EvidenceRecord],
) -> tuple[EvidenceRecord, ...]:
    """Return one eligible record per underlying dependency group."""

    selected: dict[str, EvidenceRecord] = {}
    for record in sorted(records, key=lambda item: _ref_key(item.revision_ref)):
        if not satisfies_admissible_current_requirement(record):
            continue
        dependency_key = record.source_dependency_group or str(record.object_id)
        selected.setdefault(dependency_key, record)
    return tuple(selected.values())


def bidirectional_contradictions(
    records: Iterable[EvidenceRecord],
) -> dict[ObjectRevisionRef, tuple[ObjectRevisionRef, ...]]:
    """Expand authored contradiction links into a symmetric presentation graph."""

    graph: dict[ObjectRevisionRef, set[ObjectRevisionRef]] = {}
    for record in records:
        origin = record.revision_ref
        graph.setdefault(origin, set())
        for target in record.contradicts:
            graph[origin].add(target)
            graph.setdefault(target, set()).add(origin)
    return {
        ref: tuple(sorted(targets, key=_ref_key))
        for ref, targets in sorted(graph.items(), key=lambda item: _ref_key(item[0]))
    }


def _ref_key(ref: ObjectRevisionRef) -> tuple[str, str, int]:
    return (ref.object_type, str(ref.object_id), ref.revision)
