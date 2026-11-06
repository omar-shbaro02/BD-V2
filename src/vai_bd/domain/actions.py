"""Commercial action and release-readiness contracts."""

from pydantic import Field, model_validator

from vai_bd.domain.enums import ActionScopeKind, ActionType, ReleaseReadinessState
from vai_bd.domain.envelopes import GovernedObject
from vai_bd.domain.refs import ImmutableModel, NonEmptyStr, ObjectRevisionRef


class ActionScope(ImmutableModel):
    kind: ActionScopeKind
    description: NonEmptyStr
    target_refs: tuple[ObjectRevisionRef, ...] = ()


class CommercialActionOpportunity(GovernedObject):
    opportunity_case_ref: ObjectRevisionRef
    comparative_priority_ref: ObjectRevisionRef
    allocation_case_ref: ObjectRevisionRef
    action_type: ActionType
    action_description: NonEmptyStr
    action_scope: ActionScope
    decision_owner_ref: ObjectRevisionRef | None = None
    rationale: NonEmptyStr
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)
    material_uncertainties: tuple[NonEmptyStr, ...]
    draft_content: str | None = None


class RecommendationReleaseReadiness(GovernedObject):
    cao_revision_ref: ObjectRevisionRef
    state: ReleaseReadinessState
    blocking_conditions: tuple[NonEmptyStr, ...]
    limitations: tuple[NonEmptyStr, ...]

    @model_validator(mode="after")
    def readiness_conditions_match_state(self) -> "RecommendationReleaseReadiness":
        if self.state is ReleaseReadinessState.NOT_READY and not self.blocking_conditions:
            raise ValueError("not-ready recommendations require a blocking condition")
        if self.state is ReleaseReadinessState.RELEASE_READY and self.blocking_conditions:
            raise ValueError("release-ready recommendations cannot have blocking conditions")
        return self
