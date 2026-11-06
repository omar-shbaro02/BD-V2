"""Transport contracts for the governed HTTP boundary."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal, Protocol
from uuid import UUID

from pydantic import Field

from vai_bd.domain.enums import (
    BlockingScope,
    DecisionCycleStatus,
    EffortUnit,
    QualificationOutcomeType,
)
from vai_bd.domain.refs import ActorRef, ImmutableModel, NonEmptyStr, ObjectRevisionRef
from vai_bd.operator.models import OperatorCycleList, OperatorCycleView


class ApiOperation(StrEnum):
    CREATE_CYCLE = "create_cycle"
    REVISE_CAPACITY = "revise_capacity"
    DISCOVERY = "discovery"
    EVIDENCE = "evidence"
    ELIGIBILITY = "eligibility"
    ASSESSMENT = "assessment"
    SNAPSHOT = "snapshot"
    COMPARISON = "comparison"
    ALLOCATION = "allocation"
    ACTION_PREPARATION = "action_preparation"
    RELEASE_EVALUATION = "release_evaluation"
    REVIEW_SUBMISSION = "review_submission"
    AUTHORIZATION_DECISION = "authorization_decision"
    REASSESSMENT = "reassessment"


class OfferCreate(ImmutableModel):
    name: NonEmptyStr
    problem_statement: NonEmptyStr
    intended_buyer_roles: tuple[NonEmptyStr, ...] = Field(min_length=1)
    fit_dimensions: tuple[NonEmptyStr, ...] = Field(min_length=1)
    known_exclusions: tuple[NonEmptyStr, ...] = ()
    version: NonEmptyStr


class DecisionCycleCreate(ImmutableModel):
    target_market_boundary: NonEmptyStr
    segment_filters: tuple[NonEmptyStr, ...] = ()
    exclusions: tuple[NonEmptyStr, ...] = ()
    effective_date: date
    operator_ref: ObjectRevisionRef
    status: DecisionCycleStatus = DecisionCycleStatus.DRAFT


class CapacityCreate(ImmutableModel):
    usable_time: Decimal = Field(gt=0)
    unit: EffortUnit
    planning_horizon: NonEmptyStr
    max_meaningful_concurrent_pursuits: int = Field(gt=0)
    fixed_commitments: Decimal = Field(default=Decimal("0"), ge=0)
    review_trigger: NonEmptyStr
    effective_date: date


class CycleCreateRequest(ImmutableModel):
    offer: OfferCreate
    cycle: DecisionCycleCreate
    capacity: CapacityCreate | None = None


class CapacityRevisionRequest(ImmutableModel):
    cycle_ref: ObjectRevisionRef
    current_capacity_ref: ObjectRevisionRef
    usable_time: Decimal = Field(gt=0)
    unit: EffortUnit
    planning_horizon: NonEmptyStr
    max_meaningful_concurrent_pursuits: int = Field(gt=0)
    fixed_commitments: Decimal = Field(default=Decimal("0"), ge=0)
    review_trigger: NonEmptyStr
    effective_date: date


class QualificationMember(ImmutableModel):
    opportunity_ref: ObjectRevisionRef
    qualification_ref: ObjectRevisionRef
    outcome: QualificationOutcomeType


class SnapshotRequest(ImmutableModel):
    cycle_ref: ObjectRevisionRef
    members: tuple[QualificationMember, ...] = Field(min_length=1)


class EligibilityRequest(ImmutableModel):
    candidate_ref: ObjectRevisionRef
    cycle_ref: ObjectRevisionRef
    evidence_refs: tuple[ObjectRevisionRef, ...]
    market_boundary_valid: bool
    material_contradiction: bool
    contradiction_scope: BlockingScope = BlockingScope.LOCAL
    known_hard_exclusion: bool = False
    minimum_evidence_satisfied: bool = False


class ReleaseEvaluationRequest(ImmutableModel):
    cao_ref: ObjectRevisionRef
    evidence_sufficient: bool
    exact_action_defined: bool
    exact_scope_defined: bool
    material_uncertainty_resolved: bool
    dependencies_current: bool
    policy_constraints_satisfied: bool
    limitations: tuple[str, ...] = ()


class ReviewSubmissionRequest(ImmutableModel):
    cao_ref: ObjectRevisionRef
    rationale: NonEmptyStr


class AuthorizationDecisionRequest(ImmutableModel):
    cao_ref: ObjectRevisionRef
    state: Literal["APPROVED", "DECLINED", "RETURNED_FOR_REVISION"]
    rationale: NonEmptyStr


class ReassessmentRequest(ImmutableModel):
    changed_ref: ObjectRevisionRef
    reason: NonEmptyStr


class ExecutionEligibilityRequest(ImmutableModel):
    requested_action: NonEmptyStr
    requested_scope: dict[str, Any]


class OperationResult(ImmutableModel):
    operation: ApiOperation
    result_refs: tuple[ObjectRevisionRef, ...]
    run_id: str | None = None
    replayed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class CycleView(ImmutableModel):
    cycle_id: UUID
    cycle_ref: ObjectRevisionRef
    state: NonEmptyStr
    related_refs: tuple[ObjectRevisionRef, ...] = ()


class ExecutionEligibilityView(ImmutableModel):
    cao_ref: ObjectRevisionRef
    eligible: bool
    reasons: tuple[str, ...]
    external_action_performed: bool = False


class ApiBackend(Protocol):
    """Application-service port used by the HTTP adapter."""

    async def execute(
        self,
        operation: ApiOperation,
        payload: ImmutableModel,
        idempotency_key: str,
        actor: ActorRef,
    ) -> OperationResult: ...

    async def get_cycle(self, cycle_id: UUID) -> CycleView: ...

    async def execution_eligibility(
        self, cao_ref: ObjectRevisionRef
    ) -> ExecutionEligibilityView: ...

    async def list_operator_cycles(self) -> OperatorCycleList: ...

    async def operator_view(self, cycle_id: UUID) -> OperatorCycleView: ...


class UnconfiguredApiBackend:
    """Fail closed until a deployment wires its application-service backend."""

    @staticmethod
    def _unavailable() -> None:
        from vai_bd.api.errors import ApiError

        raise ApiError(503, "backend_unavailable", "Governed application backend is unavailable")

    async def execute(
        self,
        operation: ApiOperation,
        payload: ImmutableModel,
        idempotency_key: str,
        actor: ActorRef,
    ) -> OperationResult:
        self._unavailable()
        raise AssertionError("unreachable")

    async def get_cycle(self, cycle_id: UUID) -> CycleView:
        self._unavailable()
        raise AssertionError("unreachable")

    async def execution_eligibility(self, cao_ref: ObjectRevisionRef) -> ExecutionEligibilityView:
        self._unavailable()
        raise AssertionError("unreachable")

    async def list_operator_cycles(self) -> OperatorCycleList:
        self._unavailable()
        raise AssertionError("unreachable")

    async def operator_view(self, cycle_id: UUID) -> OperatorCycleView:
        self._unavailable()
        raise AssertionError("unreachable")
