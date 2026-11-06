"""Workflow, agent-run, materiality, execution, and conformity audit contracts."""

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from vai_bd.domain.enums import (
    ConformityStatus,
    CycleWorkflowState,
    RunStatus,
)
from vai_bd.domain.refs import ActorRef, ImmutableModel, NonEmptyStr, ObjectRevisionRef


class AgentRun(ImmutableModel):
    run_id: NonEmptyStr
    agent_name: NonEmptyStr
    prompt_version: NonEmptyStr
    model_config_id: NonEmptyStr
    input_revision_refs: tuple[ObjectRevisionRef, ...]
    output_revision_refs: tuple[ObjectRevisionRef, ...] = ()
    openai_trace_ref: str | None = None
    status: RunStatus
    error: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    usage_metadata: dict[str, int] = Field(default_factory=dict)

    @field_validator("started_at", "completed_at")
    @classmethod
    def run_datetime_is_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("run timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def status_matches_completion(self) -> "AgentRun":
        if self.status is RunStatus.STARTED and self.completed_at is not None:
            raise ValueError("started runs cannot have a completion timestamp")
        if self.status is not RunStatus.STARTED and self.completed_at is None:
            raise ValueError("completed runs require a completion timestamp")
        if self.status is RunStatus.FAILED and not self.error:
            raise ValueError("failed runs require an error")
        return self


class WorkflowTransition(ImmutableModel):
    transition_id: NonEmptyStr
    decision_cycle_ref: ObjectRevisionRef
    from_state: CycleWorkflowState
    to_state: CycleWorkflowState
    trigger: NonEmptyStr
    actor: ActorRef
    object_refs: tuple[ObjectRevisionRef, ...]
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value


class MaterialImpactDecision(ImmutableModel):
    decision_id: NonEmptyStr
    changed_ref: ObjectRevisionRef
    dependent_ref: ObjectRevisionRef
    materially_affected: bool
    rationale: NonEmptyStr
    decided_by: ActorRef
    policy_version: NonEmptyStr
    decided_at: datetime

    @field_validator("decided_at")
    @classmethod
    def decided_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decided_at must be timezone-aware")
        return value


class ExternalExecutionEligibilityDecision(ImmutableModel):
    decision_id: NonEmptyStr
    cao_revision_ref: ObjectRevisionRef
    authorization_event_id: str | None = None
    eligible: bool
    reasons: tuple[NonEmptyStr, ...]
    policy_version: NonEmptyStr
    decided_at: datetime

    @field_validator("decided_at")
    @classmethod
    def decided_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decided_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def ineligible_decisions_require_reasons(self) -> "ExternalExecutionEligibilityDecision":
        if not self.eligible and not self.reasons:
            raise ValueError("ineligible execution decisions require reasons")
        return self


class ConformityCaseResult(ImmutableModel):
    case_id: NonEmptyStr
    input_fixture_version: NonEmptyStr
    input_digest: NonEmptyStr
    actual_output_refs: tuple[ObjectRevisionRef, ...]
    expected_rule_refs: tuple[NonEmptyStr, ...]
    status: ConformityStatus
    material_differences: tuple[NonEmptyStr, ...]
    trace_refs: tuple[NonEmptyStr, ...]
    started_at: datetime
    completed_at: datetime
    code_version: NonEmptyStr
    prompt_versions: dict[str, str]
    model_config_id: NonEmptyStr

    @field_validator("started_at", "completed_at")
    @classmethod
    def conformity_datetime_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("conformity timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def completion_must_follow_start(self) -> "ConformityCaseResult":
        if self.completed_at < self.started_at:
            raise ValueError("conformity completion cannot precede start")
        return self
