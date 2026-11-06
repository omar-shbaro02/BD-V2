"""Common immutable revision envelope for governed domain objects."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from vai_bd.domain.enums import ObjectValidity
from vai_bd.domain.refs import ActorRef, ImmutableModel, NonEmptyStr, ObjectRevisionRef


class GovernedObject(ImmutableModel):
    object_id: UUID
    object_type: NonEmptyStr
    revision: int = Field(ge=1)
    validity: ObjectValidity = ObjectValidity.CURRENT
    supersedes_ref: ObjectRevisionRef | None = None
    created_at: datetime
    created_by: ActorRef
    effective_at: datetime | None = None
    derived_from: tuple[ObjectRevisionRef, ...] = ()
    dependencies: tuple[ObjectRevisionRef, ...] = ()
    reassessment_trigger: str | None = None
    reassessment_reason: str | None = None

    @field_validator("created_at", "effective_at")
    @classmethod
    def datetime_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("governed datetimes must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_revision_envelope(self) -> "GovernedObject":
        refs = (*self.derived_from, *self.dependencies)
        if len(refs) != len(set(refs)):
            raise ValueError("derived/dependency revision references must be unique")
        if self.supersedes_ref is not None:
            if self.supersedes_ref.object_id != self.object_id:
                raise ValueError("a revision may supersede only the same object identity")
            if self.supersedes_ref.object_type != self.object_type:
                raise ValueError("a revision may supersede only the same object type")
            if self.supersedes_ref.revision >= self.revision:
                raise ValueError("a superseded revision must precede its successor")
        reassessment_fields = (self.reassessment_trigger, self.reassessment_reason)
        if self.validity is ObjectValidity.REASSESSMENT_REQUIRED and not all(reassessment_fields):
            raise ValueError("reassessment-required objects need trigger and reason")
        return self

    @property
    def revision_ref(self) -> ObjectRevisionRef:
        return ObjectRevisionRef(
            object_id=self.object_id,
            object_type=self.object_type,
            revision=self.revision,
        )
