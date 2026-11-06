"""Semantic and governance tests for the read-only operator experience."""

from decimal import Decimal
from typing import NoReturn
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from vai_bd.api.contracts import ApiOperation
from vai_bd.config import AppEnvironment, Settings
from vai_bd.domain.refs import ActorRef, ImmutableModel, ObjectRevisionRef
from vai_bd.main import create_app
from vai_bd.operator.models import (
    ActionPresentation,
    AllocationPresentation,
    CandidatePresentation,
    ConfidencePresentation,
    CoveragePresentation,
    OperatorCycleList,
    OperatorCycleSummary,
    OperatorCycleView,
    OpportunityPresentation,
    PriorityPresentation,
)


def ref(name: str) -> ObjectRevisionRef:
    return ObjectRevisionRef(object_id=uuid4(), object_type=name, revision=1)


class OperatorBackend:
    def __init__(self, view: OperatorCycleView) -> None:
        self.view = view

    async def list_operator_cycles(self) -> OperatorCycleList:
        return OperatorCycleList(
            cycles=(
                OperatorCycleSummary(
                    cycle_id=self.view.cycle_id,
                    cycle_ref=self.view.cycle_ref,
                    offer_name=self.view.offer_name,
                    market_boundary=self.view.market_boundary,
                    effective_date=self.view.effective_date,
                    workflow_state=self.view.workflow_state,
                    opportunity_count=len(self.view.opportunities),
                    warning_count=len(self.view.warnings),
                ),
            )
        )

    async def operator_view(self, cycle_id: UUID) -> OperatorCycleView:
        assert cycle_id == self.view.cycle_id
        return self.view

    async def execute(
        self,
        operation: ApiOperation,
        payload: ImmutableModel,
        idempotency_key: str,
        actor: ActorRef,
    ) -> NoReturn:
        raise AssertionError("operator pages are read-only")

    async def get_cycle(self, cycle_id: UUID) -> NoReturn:
        raise AssertionError("not used")

    async def execution_eligibility(self, cao_ref: ObjectRevisionRef) -> NoReturn:
        raise AssertionError("not used")


def operator_view() -> OperatorCycleView:
    cycle = ref("DecisionCycleContext")
    opportunity_one = ref("CommercialOpportunityCase")
    opportunity_two = ref("CommercialOpportunityCase")
    return OperatorCycleView(
        cycle_id=cycle.object_id,
        cycle_ref=cycle,
        offer_name="Governed <script>alert(1)</script> offer",
        offer_summary="Evidence-led commercial decision support.",
        market_boundary="Synthetic regional services market",
        effective_date="2026-10-16",
        workflow_state="HUMAN_REVIEW_READY",
        capacity_available=Decimal("12"),
        capacity_unit="HOUR",
        planning_horizon="Current planning week",
        capacity_limit=1,
        coverage=CoveragePresentation(
            basis="Approved synthetic sources",
            status="BOUNDED",
            limitations=("Private-company coverage is incomplete.",),
        ),
        candidates=(
            CandidatePresentation(
                name="Candidate North",
                disposition="QUALIFIED",
                reason="Minimum evidence gate passed.",
                evidence_summary="Two current independent observations.",
                revision_label="Candidate revision 1",
                freshness="Current as of 2026-10-16",
            ),
            CandidatePresentation(
                name="Candidate South",
                disposition="EVIDENCE_REQUIRED",
                reason="Buyer role remains unsupported.",
                evidence_summary="One inferential observation.",
                evidence_limitations=("Named decision owner is missing.",),
                contradictions=("Market-presence claims conflict.",),
                revision_label="Candidate revision 1",
                freshness="Review due",
            ),
        ),
        opportunities=(
            OpportunityPresentation(
                opportunity_ref=opportunity_one,
                company_name="Candidate North",
                qualification="QUALIFIED",
                qualification_reason="Fit and need are supported for this cycle.",
                fit="Strong operational fit for the defined offer.",
                need="Current need is supported by direct evidence.",
                evidence_summary="Current direct evidence with disclosed limits.",
                confidences=(
                    ConfidencePresentation(
                        claim="Operational need",
                        level="HIGH",
                        rationale="Two independent current sources agree.",
                    ),
                ),
                uncertainties=("Budget timing is not confirmed.",),
                pursuit_demand="8 HOUR",
                revision_label="Opportunity revision 1",
                freshness="Current",
            ),
            OpportunityPresentation(
                opportunity_ref=opportunity_two,
                company_name="Candidate East",
                qualification="QUALIFIED",
                qualification_reason="Evidence clears the deterministic gate.",
                fit="Plausible fit with a narrower use case.",
                need="Need is provisional.",
                evidence_summary="Evidence is admissible but partly inferential.",
                confidences=(
                    ConfidencePresentation(
                        claim="Decision ownership",
                        level="LOW",
                        rationale="Role is inferred rather than confirmed.",
                    ),
                ),
                contradictions=("Timing claims differ between sources.",),
                uncertainties=("Decision owner remains unconfirmed.",),
                pursuit_demand="6 HOUR",
                revision_label="Opportunity revision 1",
                freshness="Reassessment required",
                reassessment_warning="Capacity dependency changed.",
            ),
        ),
        priority=(
            PriorityPresentation(
                opportunity_ref=opportunity_one,
                position="ABOVE Candidate East",
                reason="More direct evidence supports current need.",
            ),
            PriorityPresentation(
                opportunity_ref=opportunity_two,
                position="BELOW Candidate North",
                reason="Decision ownership remains uncertain.",
            ),
        ),
        allocation=(
            AllocationPresentation(
                opportunity_ref=opportunity_one,
                tier="ACT_NOW",
                capacity_effect="Consumes 8 of 12 available hours.",
                reason="Highest feasible portfolio under the capacity limit.",
            ),
            AllocationPresentation(
                opportunity_ref=opportunity_two,
                tier="DEFERRED_CAPACITY",
                capacity_effect="Needs 6 hours; 4 remain.",
                reason="Commercially viable but does not fit residual capacity.",
            ),
        ),
        actions=(
            ActionPresentation(
                opportunity_ref=opportunity_one,
                action_type="EVIDENCE_GATHERING",
                next_action="Confirm the named decision owner internally.",
                readiness="READY_WITH_DISCLOSED_LIMITATIONS",
                readiness_reason="Budget timing remains disclosed.",
                authorization="PENDING_HUMAN_REVIEW",
                authorization_reason="No final human decision has been recorded.",
            ),
        ),
        warnings=("Candidate East requires reassessment after a capacity change.",),
    )


def client() -> tuple[TestClient, OperatorCycleView]:
    view = operator_view()
    settings = Settings(_env_file=None, app_env=AppEnvironment.TEST)
    return TestClient(create_app(settings, api_backend=OperatorBackend(view))), view


def test_cycle_list_and_detail_are_semantic_escaped_and_read_only() -> None:
    http, view = client()
    listing = http.get("/operator")
    assert listing.status_code == 200
    assert listing.headers["content-type"].startswith("text/html")
    assert "Decision cycles" in listing.text
    assert f"/operator/cycles/{view.cycle_id}" in listing.text
    assert "<script>" not in listing.text
    assert "&lt;script&gt;" in listing.text

    detail = http.get(f"/operator/cycles/{view.cycle_id}")
    assert detail.status_code == 200
    for semantic_marker in (
        '<html lang="en">',
        '<nav aria-label="Breadcrumb">',
        '<main id="main-content">',
        'aria-labelledby="candidates-heading"',
        'aria-labelledby="opportunities-heading"',
        "<details>",
        "<summary>",
    ):
        assert semantic_marker in detail.text
    for operator_answer in (
        "Candidate North",
        "Minimum evidence gate passed.",
        "Budget timing is not confirmed.",
        "Consumes 8 of 12 available hours.",
        "Confirm the named decision owner internally.",
        "READY_WITH_DISCLOSED_LIMITATIONS",
        "PENDING_HUMAN_REVIEW",
        "Reassessment required",
    ):
        assert operator_answer in detail.text

    assert detail.text.index("Comparative priority") < detail.text.index("Capacity allocation")
    lowered = detail.text.lower()
    assert "<button" not in lowered
    assert "<form" not in lowered
    assert "<input" not in lowered
    assert "lead score" not in lowered
    assert ">send<" not in lowered
    assert ">execute<" not in lowered


def test_operator_json_projection_matches_html_source() -> None:
    http, view = client()
    response = http.get(f"/v1/decision-cycles/{view.cycle_id}/operator-view")
    assert response.status_code == 200
    body = response.json()
    assert body["cycle_ref"]["revision"] == 1
    assert body["priority"][0]["position"] == "ABOVE Candidate East"
    assert body["allocation"][0]["tier"] == "ACT_NOW"
    assert body["actions"][0]["authorization"] == "PENDING_HUMAN_REVIEW"
