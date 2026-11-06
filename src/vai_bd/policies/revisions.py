"""Exact-revision usability policy for new downstream governed outputs."""

from collections.abc import Iterable, Mapping

from vai_bd.domain.enums import ObjectValidity
from vai_bd.domain.refs import ObjectRevisionRef
from vai_bd.policies.results import PolicyCheck


def check_required_revisions(
    required_refs: Iterable[ObjectRevisionRef],
    validity_by_ref: Mapping[ObjectRevisionRef, ObjectValidity],
) -> PolicyCheck:
    reasons: list[str] = []
    for ref in required_refs:
        validity = validity_by_ref.get(ref)
        label = f"{ref.object_type}:{ref.object_id}:r{ref.revision}"
        if validity is None:
            reasons.append(f"missing_required_revision:{label}")
        elif validity is not ObjectValidity.CURRENT:
            reasons.append(f"unusable_required_revision:{label}:{validity.value}")
    return PolicyCheck(not reasons, tuple(reasons))
