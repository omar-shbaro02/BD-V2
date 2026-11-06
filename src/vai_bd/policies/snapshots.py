"""Qualified-universe snapshot selection rules."""

from collections.abc import Mapping
from dataclasses import dataclass

from vai_bd.domain.enums import QualificationOutcomeType
from vai_bd.domain.refs import ExcludedOrUnresolvedRef, ObjectRevisionRef


@dataclass(frozen=True)
class SnapshotSelection:
    included_refs: tuple[ObjectRevisionRef, ...]
    excluded_or_unresolved: tuple[ExcludedOrUnresolvedRef, ...]


def select_snapshot_members(
    outcomes: Mapping[ObjectRevisionRef, QualificationOutcomeType],
) -> SnapshotSelection:
    included: list[ObjectRevisionRef] = []
    excluded: list[ExcludedOrUnresolvedRef] = []
    for ref, outcome in sorted(outcomes.items(), key=lambda item: _ref_key(item[0])):
        if outcome is QualificationOutcomeType.QUALIFIED:
            included.append(ref)
        else:
            excluded.append(ExcludedOrUnresolvedRef(object_ref=ref, reason=outcome.value))
    return SnapshotSelection(tuple(included), tuple(excluded))


def _ref_key(ref: ObjectRevisionRef) -> tuple[str, str, int]:
    return (ref.object_type, str(ref.object_id), ref.revision)
