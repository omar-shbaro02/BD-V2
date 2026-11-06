"""Shared service factories and exact-revision helpers."""

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from vai_bd.domain.enums import ObjectValidity
from vai_bd.domain.refs import ActorRef, ObjectRevisionRef
from vai_bd.persistence.repositories import GovernedObjectRepository


class ServiceConflictError(RuntimeError):
    """A service expected a current exact revision but state changed."""


class RevisionFactory:
    def __init__(
        self,
        actor: ActorRef,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        uuid_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self.actor = actor
        self.clock = clock
        self.uuid_factory = uuid_factory

    def new_ref(self, object_type: str) -> ObjectRevisionRef:
        return ObjectRevisionRef(object_id=self.uuid_factory(), object_type=object_type, revision=1)

    def envelope(
        self,
        ref: ObjectRevisionRef,
        *,
        dependencies: Iterable[ObjectRevisionRef] = (),
        derived_from: Iterable[ObjectRevisionRef] = (),
    ) -> dict[str, Any]:
        return {
            "object_id": ref.object_id,
            "object_type": ref.object_type,
            "revision": ref.revision,
            "created_at": self.clock(),
            "created_by": self.actor,
            "dependencies": _unique_refs(dependencies),
            "derived_from": _unique_refs(derived_from),
        }


def current_validities(
    session: Session, refs: Iterable[ObjectRevisionRef]
) -> dict[ObjectRevisionRef, ObjectValidity]:
    repository = GovernedObjectRepository(session)
    result: dict[ObjectRevisionRef, ObjectValidity] = {}
    for ref in refs:
        row = repository.require_revision(ref)
        result[ref] = ObjectValidity(row.validity)
    return result


def require_expected_current(
    session: Session, ref: ObjectRevisionRef, expected_revision: int
) -> None:
    if ref.revision != expected_revision:
        raise ServiceConflictError("request expected a different revision")
    row = GovernedObjectRepository(session).require_revision(ref)
    if row.validity != ObjectValidity.CURRENT.value:
        raise ServiceConflictError("exact revision is no longer current")


def _unique_refs(refs: Iterable[ObjectRevisionRef]) -> tuple[ObjectRevisionRef, ...]:
    return tuple(dict.fromkeys(refs))
