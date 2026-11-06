"""HTTP contract tests using a deterministic in-process application-service port."""

import json
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from vai_bd.api.auth import test_signature as sign_test_actor
from vai_bd.api.contracts import (
    ApiOperation,
    CycleView,
    ExecutionEligibilityView,
    OperationResult,
)
from vai_bd.config import AppEnvironment, Settings
from vai_bd.domain.refs import ActorRef, ImmutableModel, ObjectRevisionRef
from vai_bd.main import create_app
from vai_bd.orchestrator.dependencies import PhasePreconditionError, WorkflowPhase
from vai_bd.orchestrator.idempotency import IdempotencyConflictError

AUTH_KEY = "phase-nine-test-key"
HUMAN_ID = UUID("10000000-0000-0000-0000-000000000001")


def ref(name: str, revision: int = 1) -> ObjectRevisionRef:
    return ObjectRevisionRef(object_id=uuid4(), object_type=name, revision=revision)


class WorkflowBackend:
    def __init__(self) -> None:
        self.refs = {
            name: ref(name)
            for name in (
                "OfferProfile",
                "OperatorProfile",
                "DecisionCycleContext",
                "CapacityEnvelope",
                "CandidateUniverseCoverageState",
                "CompanyCandidate",
                "EvidenceRecord",
                "MinimumEvidenceHardEligibilityGateResult",
                "CommercialOpportunityCase",
                "CommercialOpportunityCaseTwo",
                "QualificationOutcome",
                "QualificationOutcomeTwo",
                "QualifiedUniverseSnapshot",
                "ComparativePriorityState",
                "PursuitDemand",
                "PursuitDemandTwo",
                "CapacityBoundedAllocationCase",
                "DecisionOwnerHypothesis",
                "ContactabilityAssessment",
                "CommercialActionOpportunity",
                "RecommendationReleaseReadiness",
            )
        }
        self.calls: list[ApiOperation] = []
        self.claims: dict[tuple[ApiOperation, str], tuple[str, OperationResult]] = {}
        self.raise_precondition = False
        self.raise_unexpected = False

    async def execute(
        self,
        operation: ApiOperation,
        payload: ImmutableModel,
        idempotency_key: str,
        actor: ActorRef,
    ) -> OperationResult:
        assert actor.actor_kind.value == "HUMAN"
        if self.raise_unexpected:
            raise RuntimeError("provider-secret-must-not-leak")
        if self.raise_precondition:
            raise PhasePreconditionError(WorkflowPhase.ASSESSMENT, ("cycle_held",))
        digest = json.dumps(payload.model_dump(mode="json"), sort_keys=True)
        claim = (operation, idempotency_key)
        previous = self.claims.get(claim)
        if previous:
            if previous[0] != digest:
                raise IdempotencyConflictError("different payload")
            return previous[1].model_copy(update={"replayed": True})
        result = OperationResult(
            operation=operation,
            result_refs=self._results(operation),
            run_id=f"run-{operation.value}" if "run" in operation.value else None,
        )
        self.claims[claim] = (digest, result)
        self.calls.append(operation)
        return result

    async def get_cycle(self, cycle_id: UUID) -> CycleView:
        cycle = self.refs["DecisionCycleContext"]
        if cycle.object_id != cycle_id:
            raise AssertionError("unexpected cycle")
        return CycleView(cycle_id=cycle_id, cycle_ref=cycle, state="HUMAN_REVIEW_READY")

    async def execution_eligibility(self, cao_ref: ObjectRevisionRef) -> ExecutionEligibilityView:
        assert cao_ref == self.refs["CommercialActionOpportunity"]
        return ExecutionEligibilityView(
            cao_ref=cao_ref,
            eligible=False,
            reasons=("external_execution_restricted:test_profile",),
        )

    def _results(self, operation: ApiOperation) -> tuple[ObjectRevisionRef, ...]:
        names = {
            ApiOperation.CREATE_CYCLE: (
                "OfferProfile",
                "DecisionCycleContext",
                "CapacityEnvelope",
            ),
            ApiOperation.REVISE_CAPACITY: ("CapacityEnvelope",),
            ApiOperation.DISCOVERY: ("CandidateUniverseCoverageState", "CompanyCandidate"),
            ApiOperation.EVIDENCE: ("EvidenceRecord",),
            ApiOperation.ELIGIBILITY: ("MinimumEvidenceHardEligibilityGateResult",),
            ApiOperation.ASSESSMENT: (
                "CommercialOpportunityCase",
                "CommercialOpportunityCaseTwo",
                "QualificationOutcome",
                "QualificationOutcomeTwo",
                "DecisionOwnerHypothesis",
                "ContactabilityAssessment",
                "PursuitDemand",
                "PursuitDemandTwo",
            ),
            ApiOperation.SNAPSHOT: ("QualifiedUniverseSnapshot",),
            ApiOperation.COMPARISON: ("ComparativePriorityState",),
            ApiOperation.ALLOCATION: ("CapacityBoundedAllocationCase",),
            ApiOperation.ACTION_PREPARATION: ("CommercialActionOpportunity",),
            ApiOperation.RELEASE_EVALUATION: ("RecommendationReleaseReadiness",),
            ApiOperation.REVIEW_SUBMISSION: (),
            ApiOperation.AUTHORIZATION_DECISION: (),
            ApiOperation.REASSESSMENT: ("CapacityBoundedAllocationCase",),
        }[operation]
        return tuple(self.refs[name] for name in names)


@pytest.fixture
def backend() -> WorkflowBackend:
    return WorkflowBackend()


@pytest.fixture
def client(backend: WorkflowBackend) -> TestClient:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TEST,
        test_auth_signing_key=AUTH_KEY,
    )
    return TestClient(create_app(settings, api_backend=backend))


def auth_headers(kind: str = "HUMAN") -> dict[str, str]:
    name = "Test Operator"
    return {
        "X-Test-Actor-Id": str(HUMAN_ID),
        "X-Test-Actor-Name": name,
        "X-Test-Actor-Kind": kind,
        "X-Test-Auth-Signature": sign_test_actor(AUTH_KEY, HUMAN_ID, name),
    }


def post(client: TestClient, path: str, payload: dict[str, Any], key: str) -> dict[str, Any]:
    response = client.post(
        path,
        json=payload,
        headers={**auth_headers(), "Idempotency-Key": key, "X-Request-ID": f"request-{key}"},
    )
    assert response.status_code in {200, 201}, response.text
    assert response.headers["X-Request-ID"] == f"request-{key}"
    return response.json()


def as_json(value: ObjectRevisionRef) -> dict[str, Any]:
    return value.model_dump(mode="json")


def test_full_governed_cycle_through_api(client: TestClient, backend: WorkflowBackend) -> None:
    r = backend.refs
    cycle = r["DecisionCycleContext"]
    candidate = r["CompanyCandidate"]
    snapshot = r["QualifiedUniverseSnapshot"]
    allocation = r["CapacityBoundedAllocationCase"]
    cao = r["CommercialActionOpportunity"]

    post(
        client,
        "/v1/decision-cycles",
        {
            "offer": {
                "name": "Synthetic offer",
                "problem_statement": "Synthetic problem",
                "intended_buyer_roles": ["Owner"],
                "fit_dimensions": ["Need"],
                "version": "1",
            },
            "cycle": {
                "target_market_boundary": "Synthetic market",
                "effective_date": "2026-10-16",
                "operator_ref": as_json(r["OperatorProfile"]),
                "status": "DRAFT",
            },
            "capacity": {
                "usable_time": "20",
                "unit": "HOUR",
                "planning_horizon": "week",
                "max_meaningful_concurrent_pursuits": 2,
                "review_trigger": "capacity changed",
                "effective_date": "2026-10-16",
            },
        },
        "01",
    )
    view = client.get(f"/v1/decision-cycles/{cycle.object_id}")
    assert view.status_code == 200
    post(
        client,
        f"/v1/decision-cycles/{cycle.object_id}/capacity-revisions",
        {
            "cycle_ref": as_json(cycle),
            "current_capacity_ref": as_json(r["CapacityEnvelope"]),
            "usable_time": "20",
            "unit": "HOUR",
            "planning_horizon": "week",
            "max_meaningful_concurrent_pursuits": 2,
            "review_trigger": "capacity changed",
            "effective_date": "2026-10-16",
        },
        "02",
    )
    observation = {
        "observation_id": "o1",
        "content": "Synthetic observation",
        "source": {"source_id": "s1", "uri_or_reference": "fixture:s1"},
        "source_type": "synthetic",
        "provenance": "phase9-test",
    }
    post(
        client,
        f"/v1/decision-cycles/{cycle.object_id}/discovery-runs",
        {
            "exact_input_refs": [as_json(cycle), as_json(r["OfferProfile"])],
            "decision_cycle_ref": as_json(cycle),
            "offer_ref": as_json(r["OfferProfile"]),
            "target_market_boundary": "Synthetic market",
            "observations": [observation],
        },
        "03",
    )
    post(
        client,
        f"/v1/candidates/{candidate.object_id}/revisions/1/evidence-runs",
        {
            "exact_input_refs": [as_json(candidate), as_json(cycle)],
            "candidate_ref": as_json(candidate),
            "decision_cycle_ref": as_json(cycle),
            "observations": [observation],
        },
        "04",
    )
    post(
        client,
        f"/v1/candidates/{candidate.object_id}/revisions/1/eligibility-evaluations",
        {
            "candidate_ref": as_json(candidate),
            "cycle_ref": as_json(cycle),
            "evidence_refs": [as_json(r["EvidenceRecord"])],
            "market_boundary_valid": True,
            "material_contradiction": False,
            "minimum_evidence_satisfied": True,
        },
        "05",
    )
    assessment_refs = [
        cycle,
        r["OfferProfile"],
        candidate,
        r["MinimumEvidenceHardEligibilityGateResult"],
        r["EvidenceRecord"],
    ]
    post(
        client,
        f"/v1/candidates/{candidate.object_id}/revisions/1/assessment-runs",
        {
            "exact_input_refs": [as_json(item) for item in assessment_refs],
            "decision_cycle_ref": as_json(cycle),
            "offer_ref": as_json(r["OfferProfile"]),
            "candidate_ref": as_json(candidate),
            "gate_result_ref": as_json(r["MinimumEvidenceHardEligibilityGateResult"]),
            "gate_outcome": "PROCEED",
            "evidence_refs": [as_json(r["EvidenceRecord"])],
        },
        "06",
    )
    post(
        client,
        f"/v1/decision-cycles/{cycle.object_id}/qualified-snapshots",
        {
            "cycle_ref": as_json(cycle),
            "members": [
                {
                    "opportunity_ref": as_json(r["CommercialOpportunityCase"]),
                    "qualification_ref": as_json(r["QualificationOutcome"]),
                    "outcome": "QUALIFIED",
                },
                {
                    "opportunity_ref": as_json(r["CommercialOpportunityCaseTwo"]),
                    "qualification_ref": as_json(r["QualificationOutcomeTwo"]),
                    "outcome": "QUALIFIED",
                },
            ],
        },
        "07",
    )
    opportunities = [r["CommercialOpportunityCase"], r["CommercialOpportunityCaseTwo"]]
    post(
        client,
        f"/v1/qualified-snapshots/{snapshot.object_id}/revisions/1/comparison-runs",
        {
            "exact_input_refs": [as_json(snapshot), *(as_json(item) for item in opportunities)],
            "snapshot_ref": as_json(snapshot),
            "opportunity_refs": [as_json(item) for item in opportunities],
            "required_pairs": [
                {"first": as_json(opportunities[0]), "second": as_json(opportunities[1])}
            ],
        },
        "08",
    )
    allocation_refs = [
        snapshot,
        r["ComparativePriorityState"],
        r["CapacityEnvelope"],
        *opportunities,
        r["PursuitDemand"],
        r["PursuitDemandTwo"],
    ]
    post(
        client,
        f"/v1/qualified-snapshots/{snapshot.object_id}/revisions/1/allocation-runs",
        {
            "exact_input_refs": [as_json(item) for item in allocation_refs],
            "snapshot_ref": as_json(snapshot),
            "priority_state_ref": as_json(r["ComparativePriorityState"]),
            "capacity_envelope_ref": as_json(r["CapacityEnvelope"]),
            "opportunity_refs": [as_json(item) for item in opportunities],
            "demands": [
                {
                    "opportunity_ref": as_json(opportunities[0]),
                    "demand_ref": as_json(r["PursuitDemand"]),
                    "estimated_effort": "5",
                    "unit": "HOUR",
                    "smaller_credible_action_available": False,
                },
                {
                    "opportunity_ref": as_json(opportunities[1]),
                    "demand_ref": as_json(r["PursuitDemandTwo"]),
                    "estimated_effort": "5",
                    "unit": "HOUR",
                    "smaller_credible_action_available": False,
                },
            ],
            "available_capacity": "20",
            "unit": "HOUR",
            "planning_horizon": "week",
            "max_concurrent_pursuits": 2,
        },
        "09",
    )
    action_refs = [
        r["CommercialOpportunityCase"],
        r["ComparativePriorityState"],
        allocation,
        r["DecisionOwnerHypothesis"],
        r["ContactabilityAssessment"],
        r["EvidenceRecord"],
    ]
    post(
        client,
        f"/v1/allocations/{allocation.object_id}/revisions/1/action-preparation-runs",
        {
            "exact_input_refs": [as_json(item) for item in action_refs],
            "opportunity_case_ref": as_json(r["CommercialOpportunityCase"]),
            "comparative_priority_ref": as_json(r["ComparativePriorityState"]),
            "allocation_case_ref": as_json(allocation),
            "decision_owner_ref": as_json(r["DecisionOwnerHypothesis"]),
            "contactability_ref": as_json(r["ContactabilityAssessment"]),
            "evidence_refs": [as_json(r["EvidenceRecord"])],
        },
        "10",
    )
    post(
        client,
        f"/v1/commercial-actions/{cao.object_id}/revisions/1/release-evaluations",
        {
            "cao_ref": as_json(cao),
            "evidence_sufficient": True,
            "exact_action_defined": True,
            "exact_scope_defined": True,
            "material_uncertainty_resolved": True,
            "dependencies_current": True,
            "policy_constraints_satisfied": True,
        },
        "11",
    )
    post(
        client,
        f"/v1/commercial-actions/{cao.object_id}/revisions/1/review-submissions",
        {"cao_ref": as_json(cao), "rationale": "Ready for human review"},
        "12",
    )
    post(
        client,
        f"/v1/commercial-actions/{cao.object_id}/revisions/1/authorization-decisions",
        {
            "cao_ref": as_json(cao),
            "state": "APPROVED",
            "rationale": "Approved by test operator",
        },
        "13",
    )
    eligibility = client.get(
        f"/v1/commercial-actions/{cao.object_id}/revisions/1/execution-eligibility"
    )
    assert eligibility.status_code == 200
    assert eligibility.json()["eligible"] is False
    assert eligibility.json()["external_action_performed"] is False
    post(
        client,
        f"/v1/objects/{r['CapacityEnvelope'].object_id}/revisions/1/reassessment-evaluations",
        {"changed_ref": as_json(r["CapacityEnvelope"]), "reason": "Capacity changed"},
        "14",
    )
    assert backend.calls == list(ApiOperation)


def test_auth_path_idempotency_hold_and_no_execution_surface(
    client: TestClient, backend: WorkflowBackend
) -> None:
    cycle = backend.refs["DecisionCycleContext"]
    path = f"/v1/decision-cycles/{cycle.object_id}/capacity-revisions"
    payload = {
        "cycle_ref": as_json(cycle),
        "current_capacity_ref": as_json(backend.refs["CapacityEnvelope"]),
        "usable_time": "20",
        "unit": "HOUR",
        "planning_horizon": "week",
        "max_meaningful_concurrent_pursuits": 1,
        "review_trigger": "change",
        "effective_date": "2026-10-16",
    }
    assert client.post(path, json=payload, headers={"Idempotency-Key": "x"}).status_code == 401
    nonhuman = client.post(
        path,
        json=payload,
        headers={**auth_headers("AGENT"), "Idempotency-Key": "x"},
    )
    assert nonhuman.status_code == 403
    bad_path = client.post(
        f"/v1/decision-cycles/{uuid4()}/capacity-revisions",
        json=payload,
        headers={**auth_headers(), "Idempotency-Key": "x"},
    )
    assert bad_path.status_code == 409
    first = client.post(path, json=payload, headers={**auth_headers(), "Idempotency-Key": "same"})
    replay = client.post(path, json=payload, headers={**auth_headers(), "Idempotency-Key": "same"})
    assert first.status_code == 200 and replay.json()["replayed"] is True
    changed = payload | {"usable_time": "21"}
    conflict = client.post(
        path, json=changed, headers={**auth_headers(), "Idempotency-Key": "same"}
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"
    backend.raise_precondition = True
    held = client.post(path, json=payload, headers={**auth_headers(), "Idempotency-Key": "held"})
    assert held.status_code == 409
    assert held.json()["error"]["code"] == "phase_precondition_failed"

    backend.raise_precondition = False
    backend.raise_unexpected = True
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TEST,
        test_auth_signing_key=AUTH_KEY,
    )
    safe_client = TestClient(
        create_app(settings, api_backend=backend), raise_server_exceptions=False
    )
    unexpected = safe_client.post(
        path, json=payload, headers={**auth_headers(), "Idempotency-Key": "unexpected"}
    )
    assert unexpected.status_code == 500
    assert unexpected.json()["error"]["code"] == "internal_error"
    assert "provider-secret-must-not-leak" not in unexpected.text

    paths = client.get("/openapi.json").json()["paths"]
    forbidden = [item for item in paths if item.endswith("/execute") or item.endswith("/send")]
    assert forbidden == []
