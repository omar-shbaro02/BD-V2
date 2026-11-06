"""Human-originated authorization contracts; never agent output contracts."""

from datetime import datetime

from pydantic import field_validator, model_validator

from vai_bd.domain.actions import ActionScope
from vai_bd.domain.enums import ActorKind, HumanAuthorizationState
from vai_bd.domain.refs import ActorRef, ImmutableModel, NonEmptyStr, ObjectRevisionRef


class HumanAuthorizationEvent(ImmutableModel):
    authorization_id: NonEmptyStr
    cao_revision_ref: ObjectRevisionRef
    state: HumanAuthorizationState
    requested_human_authority_ref: ActorRef
    actual_deciding_human_ref: ActorRef | None = None
    decision_timestamp: datetime | None = None
    authorized_action: str | None = None
    authorized_scope: ActionScope | None = None
    rationale: NonEmptyStr

    @field_validator("decision_timestamp")
    @classmethod
    def decision_timestamp_is_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("decision_timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def final_decision_requires_human_and_exact_scope(self) -> "HumanAuthorizationEvent":
        if self.requested_human_authority_ref.actor_kind is not ActorKind.HUMAN:
            raise ValueError("requested authorization authority must be human")
        final_states = {
            HumanAuthorizationState.APPROVED,
            HumanAuthorizationState.DECLINED,
            HumanAuthorizationState.RETURNED_FOR_REVISION,
        }
        if self.state in final_states:
            if self.actual_deciding_human_ref is None:
                raise ValueError("final authorization decisions require an actual human")
            if self.actual_deciding_human_ref.actor_kind is not ActorKind.HUMAN:
                raise ValueError("the actual deciding actor must be human")
            if self.decision_timestamp is None:
                raise ValueError("final authorization decisions require a timestamp")
        if self.state is HumanAuthorizationState.APPROVED and (
            not self.authorized_action or self.authorized_scope is None
        ):
            raise ValueError("approval requires exact action and scope")
        return self


class HumanAuthorizationCurrentState(ImmutableModel):
    cao_revision_ref: ObjectRevisionRef
    state: HumanAuthorizationState
    latest_event_id: NonEmptyStr


class AgentReviewRequest(ImmutableModel):
    """The only authorization-adjacent shape agents may emit."""

    cao_revision_ref: ObjectRevisionRef
    review_reason: NonEmptyStr
