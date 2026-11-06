"""Version-one governed API routes."""

from collections.abc import Awaitable, Callable
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status

from vai_bd.agents.contracts import (
    CommercialActionInput,
    EvidenceIntelligenceInput,
    MarketDiscoveryInput,
    OpportunityIntelligenceInput,
    PortfolioAllocationInput,
    PortfolioComparisonInput,
)
from vai_bd.api.contracts import (
    ApiBackend,
    ApiOperation,
    AuthorizationDecisionRequest,
    CapacityRevisionRequest,
    CycleCreateRequest,
    CycleView,
    EligibilityRequest,
    ExecutionEligibilityView,
    OperationResult,
    ReassessmentRequest,
    ReleaseEvaluationRequest,
    ReviewSubmissionRequest,
    SnapshotRequest,
)
from vai_bd.api.errors import ApiError
from vai_bd.domain.refs import ActorRef, ImmutableModel, ObjectRevisionRef
from vai_bd.operator.models import OperatorCycleView

IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)]


def create_router(
    human_dependency: Callable[..., Awaitable[ActorRef]],
) -> APIRouter:
    router = APIRouter(prefix="/v1")
    Human = Annotated[ActorRef, Depends(human_dependency)]

    def backend(request: Request) -> ApiBackend:
        return cast(ApiBackend, request.app.state.api_backend)

    Backend = Annotated[ApiBackend, Depends(backend)]

    async def execute(
        service: ApiBackend,
        operation: ApiOperation,
        payload: ImmutableModel,
        key: str,
        actor: ActorRef,
    ) -> OperationResult:
        result = await service.execute(operation, payload, key, actor)
        if result.operation is not operation:
            raise ApiError(500, "backend_contract_error", "Backend returned the wrong operation")
        return result

    @router.post(
        "/decision-cycles", response_model=OperationResult, status_code=status.HTTP_201_CREATED
    )
    async def create_cycle(
        payload: CycleCreateRequest, key: IdempotencyKey, actor: Human, service: Backend
    ) -> OperationResult:
        return await execute(service, ApiOperation.CREATE_CYCLE, payload, key, actor)

    @router.get("/decision-cycles/{cycle_id}", response_model=CycleView)
    async def get_cycle(cycle_id: UUID, service: Backend) -> CycleView:
        return await service.get_cycle(cycle_id)

    @router.get("/decision-cycles/{cycle_id}/operator-view", response_model=OperatorCycleView)
    async def operator_view(cycle_id: UUID, service: Backend) -> OperatorCycleView:
        return await service.operator_view(cycle_id)

    @router.post("/decision-cycles/{cycle_id}/capacity-revisions", response_model=OperationResult)
    async def revise_capacity(
        cycle_id: UUID,
        payload: CapacityRevisionRequest,
        key: IdempotencyKey,
        actor: Human,
        service: Backend,
    ) -> OperationResult:
        _match_id(cycle_id, payload.cycle_ref, "decision cycle")
        return await execute(service, ApiOperation.REVISE_CAPACITY, payload, key, actor)

    @router.post("/decision-cycles/{cycle_id}/discovery-runs", response_model=OperationResult)
    async def discovery(
        cycle_id: UUID,
        payload: MarketDiscoveryInput,
        key: IdempotencyKey,
        actor: Human,
        service: Backend,
    ) -> OperationResult:
        _match_id(cycle_id, payload.decision_cycle_ref, "decision cycle")
        return await execute(service, ApiOperation.DISCOVERY, payload, key, actor)

    @router.post(
        "/candidates/{candidate_id}/revisions/{revision}/evidence-runs",
        response_model=OperationResult,
    )
    async def evidence(
        candidate_id: UUID,
        revision: int,
        payload: EvidenceIntelligenceInput,
        key: IdempotencyKey,
        actor: Human,
        service: Backend,
    ) -> OperationResult:
        _match_path(candidate_id, revision, payload.candidate_ref, "candidate")
        return await execute(service, ApiOperation.EVIDENCE, payload, key, actor)

    @router.post(
        "/candidates/{candidate_id}/revisions/{revision}/eligibility-evaluations",
        response_model=OperationResult,
    )
    async def eligibility(
        candidate_id: UUID,
        revision: int,
        payload: EligibilityRequest,
        key: IdempotencyKey,
        actor: Human,
        service: Backend,
    ) -> OperationResult:
        _match_path(candidate_id, revision, payload.candidate_ref, "candidate")
        return await execute(service, ApiOperation.ELIGIBILITY, payload, key, actor)

    @router.post(
        "/candidates/{candidate_id}/revisions/{revision}/assessment-runs",
        response_model=OperationResult,
    )
    async def assessment(
        candidate_id: UUID,
        revision: int,
        payload: OpportunityIntelligenceInput,
        key: IdempotencyKey,
        actor: Human,
        service: Backend,
    ) -> OperationResult:
        _match_path(candidate_id, revision, payload.candidate_ref, "candidate")
        return await execute(service, ApiOperation.ASSESSMENT, payload, key, actor)

    @router.post("/decision-cycles/{cycle_id}/qualified-snapshots", response_model=OperationResult)
    async def snapshot(
        cycle_id: UUID,
        payload: SnapshotRequest,
        key: IdempotencyKey,
        actor: Human,
        service: Backend,
    ) -> OperationResult:
        _match_id(cycle_id, payload.cycle_ref, "decision cycle")
        return await execute(service, ApiOperation.SNAPSHOT, payload, key, actor)

    @router.post(
        "/qualified-snapshots/{snapshot_id}/revisions/{revision}/comparison-runs",
        response_model=OperationResult,
    )
    async def comparison(
        snapshot_id: UUID,
        revision: int,
        payload: PortfolioComparisonInput,
        key: IdempotencyKey,
        actor: Human,
        service: Backend,
    ) -> OperationResult:
        _match_path(snapshot_id, revision, payload.snapshot_ref, "snapshot")
        return await execute(service, ApiOperation.COMPARISON, payload, key, actor)

    @router.post(
        "/qualified-snapshots/{snapshot_id}/revisions/{revision}/allocation-runs",
        response_model=OperationResult,
    )
    async def allocation(
        snapshot_id: UUID,
        revision: int,
        payload: PortfolioAllocationInput,
        key: IdempotencyKey,
        actor: Human,
        service: Backend,
    ) -> OperationResult:
        _match_path(snapshot_id, revision, payload.snapshot_ref, "snapshot")
        return await execute(service, ApiOperation.ALLOCATION, payload, key, actor)

    @router.post(
        "/allocations/{allocation_id}/revisions/{revision}/action-preparation-runs",
        response_model=OperationResult,
    )
    async def action_preparation(
        allocation_id: UUID,
        revision: int,
        payload: CommercialActionInput,
        key: IdempotencyKey,
        actor: Human,
        service: Backend,
    ) -> OperationResult:
        _require_exact_ref(payload.exact_input_refs, allocation_id, revision, "allocation")
        return await execute(service, ApiOperation.ACTION_PREPARATION, payload, key, actor)

    @router.post(
        "/commercial-actions/{cao_id}/revisions/{revision}/release-evaluations",
        response_model=OperationResult,
    )
    async def release_evaluation(
        cao_id: UUID,
        revision: int,
        payload: ReleaseEvaluationRequest,
        key: IdempotencyKey,
        actor: Human,
        service: Backend,
    ) -> OperationResult:
        _match_path(cao_id, revision, payload.cao_ref, "commercial action")
        return await execute(service, ApiOperation.RELEASE_EVALUATION, payload, key, actor)

    @router.post(
        "/commercial-actions/{cao_id}/revisions/{revision}/review-submissions",
        response_model=OperationResult,
    )
    async def review_submission(
        cao_id: UUID,
        revision: int,
        payload: ReviewSubmissionRequest,
        key: IdempotencyKey,
        actor: Human,
        service: Backend,
    ) -> OperationResult:
        _match_path(cao_id, revision, payload.cao_ref, "commercial action")
        return await execute(service, ApiOperation.REVIEW_SUBMISSION, payload, key, actor)

    @router.post(
        "/commercial-actions/{cao_id}/revisions/{revision}/authorization-decisions",
        response_model=OperationResult,
    )
    async def authorization_decision(
        cao_id: UUID,
        revision: int,
        payload: AuthorizationDecisionRequest,
        key: IdempotencyKey,
        actor: Human,
        service: Backend,
    ) -> OperationResult:
        _match_path(cao_id, revision, payload.cao_ref, "commercial action")
        return await execute(service, ApiOperation.AUTHORIZATION_DECISION, payload, key, actor)

    @router.get(
        "/commercial-actions/{cao_id}/revisions/{revision}/execution-eligibility",
        response_model=ExecutionEligibilityView,
    )
    async def execution_eligibility(
        cao_id: UUID, revision: int, service: Backend
    ) -> ExecutionEligibilityView:
        ref = ObjectRevisionRef(
            object_id=cao_id, object_type="CommercialActionOpportunity", revision=revision
        )
        return await service.execution_eligibility(ref)

    @router.post(
        "/objects/{object_id}/revisions/{revision}/reassessment-evaluations",
        response_model=OperationResult,
    )
    async def reassessment(
        object_id: UUID,
        revision: int,
        payload: ReassessmentRequest,
        key: IdempotencyKey,
        actor: Human,
        service: Backend,
    ) -> OperationResult:
        _match_path(object_id, revision, payload.changed_ref, "changed object")
        return await execute(service, ApiOperation.REASSESSMENT, payload, key, actor)

    return router


def _match_id(expected_id: UUID, ref: ObjectRevisionRef, label: str) -> None:
    if ref.object_id != expected_id:
        raise ApiError(409, "path_revision_mismatch", f"Path does not match exact {label} ref")


def _match_path(expected_id: UUID, revision: int, ref: ObjectRevisionRef, label: str) -> None:
    if revision < 1 or ref.object_id != expected_id or ref.revision != revision:
        raise ApiError(409, "path_revision_mismatch", f"Path does not match exact {label} ref")


def _require_exact_ref(
    refs: tuple[ObjectRevisionRef, ...], object_id: UUID, revision: int, label: str
) -> None:
    if not any(ref.object_id == object_id and ref.revision == revision for ref in refs):
        raise ApiError(409, "path_revision_mismatch", f"Path {label} is not an exact input ref")
