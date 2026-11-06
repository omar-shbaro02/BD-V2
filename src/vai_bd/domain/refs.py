"""Identity and exact-revision reference types."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from vai_bd.domain.enums import ActorKind

NonEmptyStr = Annotated[str, Field(min_length=1)]
PositiveRevision = Annotated[int, Field(ge=1)]


class ImmutableModel(BaseModel):
    """Immutable, strict domain value object."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class ObjectRevisionRef(ImmutableModel):
    object_id: UUID
    object_type: NonEmptyStr
    revision: PositiveRevision


class ActorRef(ImmutableModel):
    actor_id: UUID
    actor_kind: ActorKind
    display_name: NonEmptyStr


class SourceRef(ImmutableModel):
    source_id: NonEmptyStr
    uri_or_reference: NonEmptyStr


class ExcludedOrUnresolvedRef(ImmutableModel):
    object_ref: ObjectRevisionRef
    reason: NonEmptyStr


class AllocationMemberReason(ImmutableModel):
    opportunity_ref: ObjectRevisionRef
    reason: NonEmptyStr
