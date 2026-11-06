"""Inventory and invariant tests for all Phase 2 domain contracts."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from vai_bd.domain.actions import (
    ActionScope,
    CommercialActionOpportunity,
    RecommendationReleaseReadiness,
)
from vai_bd.domain.audit import (
    AgentRun,
    ConformityCaseResult,
    ExternalExecutionEligibilityDecision,
    MaterialImpactDecision,
    WorkflowTransition,
)
from vai_bd.domain.authorization import (
    AgentReviewRequest,
    HumanAuthorizationCurrentState,
    HumanAuthorizationEvent,
)
from vai_bd.domain.cycle import (
    CandidateUniverseCoverageState,
    CapacityEnvelope,
    CompanyCandidate,
    DecisionCycleContext,
    OfferProfile,
)
from vai_bd.domain.enums import (
    ActionScopeKind,
    ActionType,
    ActorKind,
    BlockingScope,
    ComparisonRelationship,
    ConfidenceLevel,
    ConformityStatus,
    CycleWorkflowState,
    DecisionCycleStatus,
    EffortUnit,
    EvidenceAdmissibility,
    EvidenceCurrentness,
    EvidenceDirectness,
    GateOutcome,
    HumanAuthorizationState,
    NeedStatus,
    OpportunityLifecycleState,
    QualificationOutcomeType,
    ReleaseReadinessState,
    RunStatus,
)
from vai_bd.domain.envelopes import GovernedObject
from vai_bd.domain.evidence import (
    ContradictionGroup,
    EvidenceRecord,
    MinimumEvidenceHardEligibilityGateResult,
    MissingEvidenceFlag,
)
from vai_bd.domain.opportunity import (
    CommercialOpportunityCase,
    CompanyOfferFit,
    ConfidenceAssessment,
    ContactabilityAssessment,
    DecisionOwnerHypothesis,
    NeedHypothesis,
    OpportunityState,
    PursuitDemand,
    QualificationOutcome,
)
from vai_bd.domain.portfolio import (
    AlternativePortfolio,
    CanonicalPairwiseComparison,
    CapacityBoundedAllocationCase,
    ComparativePriorityState,
    PriorityRelation,
    QualifiedUniverseSnapshot,
)
from vai_bd.domain.refs import (
    ActorRef,
    AllocationMemberReason,
    ExcludedOrUnresolvedRef,
    ObjectRevisionRef,
    SourceRef,
)

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
HUMAN = ActorRef(
    actor_id=UUID("00000000-0000-0000-0000-000000000001"),
    actor_kind=ActorKind.HUMAN,
    display_name="Operator",
)
SYSTEM = ActorRef(
    actor_id=UUID("00000000-0000-0000-0000-000000000002"),
    actor_kind=ActorKind.SYSTEM,
    display_name="System",
)


def ref(number: int, object_type: str = "TestObject", revision: int = 1) -> ObjectRevisionRef:
    return ObjectRevisionRef(
        object_id=UUID(f"00000000-0000-0000-0000-{number:012d}"),
        object_type=object_type,
        revision=revision,
    )


def envelope(number: int, object_type: str) -> dict[str, object]:
    return {
        "object_id": ref(number, object_type).object_id,
        "object_type": object_type,
        "revision": 1,
        "created_at": NOW,
        "created_by": SYSTEM,
    }


def valid_models() -> list[object]:
    source = SourceRef(source_id="S1", uri_or_reference="synthetic://source/1")
    scope = ActionScope(kind=ActionScopeKind.INTERNAL_RESEARCH, description="Research owner")
    opportunity_a = ref(40, "CommercialOpportunityCase")
    opportunity_b = ref(41, "CommercialOpportunityCase")
    return [
        ObjectRevisionRef(object_id=ref(1).object_id, object_type="Offer", revision=1),
        HUMAN,
        source,
        GovernedObject(**envelope(2, "Generic")),
        OfferProfile(
            **envelope(3, "OfferProfile"),
            name="Project controls",
            problem_statement="Improve decision quality",
            intended_buyer_roles=("COO",),
            fit_dimensions=("Complex delivery",),
            version="v1",
        ),
        DecisionCycleContext(
            **envelope(4, "DecisionCycleContext"),
            offer_ref=ref(3, "OfferProfile"),
            target_market_boundary="Northern Virginia",
            effective_date=date(2026, 10, 9),
            operator_ref=ref(5, "Operator"),
            status=DecisionCycleStatus.DRAFT,
        ),
        CapacityEnvelope(
            **envelope(6, "CapacityEnvelope"),
            decision_cycle_ref=ref(4, "DecisionCycleContext"),
            usable_time=Decimal("6"),
            unit=EffortUnit.HOUR,
            planning_horizon="week",
            max_meaningful_concurrent_pursuits=8,
            fixed_commitments=Decimal("1"),
            review_trigger="capacity changes",
            effective_date=date(2026, 10, 9),
        ),
        CandidateUniverseCoverageState(
            **envelope(7, "CandidateUniverseCoverageState"),
            decision_cycle_ref=ref(4, "DecisionCycleContext"),
            coverage_basis="supplied observations",
            coverage_limitations=("not exhaustive",),
            candidate_refs=(ref(8, "CompanyCandidate"),),
            coverage_status="PARTIAL",
        ),
        CompanyCandidate(
            **envelope(8, "CompanyCandidate"),
            universe_ref=ref(7, "CandidateUniverseCoverageState"),
            company_name="Synthetic Co",
            market_presence_claims=("present in market",),
            segment_claims=("construction",),
            source_refs=(source,),
            candidate_status="CANDIDATE",
        ),
        EvidenceRecord(
            **envelope(9, "EvidenceRecord"),
            candidate_ref=ref(8, "CompanyCandidate"),
            claim_text="Synthetic claim",
            source=source,
            source_type="synthetic",
            source_date=date(2026, 10, 1),
            observed_at=NOW,
            provenance="Stage 15 fixture",
            directness=EvidenceDirectness.DIRECT,
            currentness=EvidenceCurrentness.CURRENT,
            admissibility=EvidenceAdmissibility.ADMISSIBLE,
        ),
        MissingEvidenceFlag(
            candidate_ref=ref(8),
            missing_claim_or_fact="decision owner",
            why_material="needed for next action",
            investigation_action="identify role",
        ),
        ContradictionGroup(
            group_id="CG1",
            evidence_refs=(ref(9, "EvidenceRecord"), ref(10, "EvidenceRecord")),
            material_reason="claims conflict",
        ),
        MinimumEvidenceHardEligibilityGateResult(
            **envelope(11, "MinimumEvidenceHardEligibilityGateResult"),
            candidate_ref=ref(8),
            decision_cycle_ref=ref(4),
            outcome=GateOutcome.PROCEED,
            reasons=("minimum evidence present",),
            blocking_scope=BlockingScope.LOCAL,
        ),
        ConfidenceAssessment(
            **envelope(12, "ConfidenceAssessment"),
            claim_ref=ref(13),
            level=ConfidenceLevel.MEDIUM,
            rationale="one direct source",
            evidence_refs=(ref(9),),
        ),
        CompanyOfferFit(
            **envelope(13, "CompanyOfferFit"),
            candidate_ref=ref(8),
            offer_ref=ref(3),
            judgment="Strong",
            rationale="aligned delivery context",
            evidence_refs=(ref(9),),
            claim_confidence_ref=ref(12),
        ),
        NeedHypothesis(
            **envelope(14, "NeedHypothesis"),
            candidate_ref=ref(8),
            hypothesis="may need controls",
            status=NeedStatus.PROVISIONAL,
            rationale="need is inferential",
            evidence_refs=(ref(9),),
            claim_confidence_ref=ref(12),
        ),
        DecisionOwnerHypothesis(
            **envelope(15, "DecisionOwnerHypothesis"),
            candidate_ref=ref(8),
            role_hypothesis="COO",
            rationale="role owns delivery",
            evidence_refs=(ref(9),),
            claim_confidence_ref=ref(12),
        ),
        ContactabilityAssessment(
            **envelope(16, "ContactabilityAssessment"),
            candidate_ref=ref(8),
            assessment="Low",
            known_paths=(),
            constraints=("no named contact",),
            rationale="no current path",
            evidence_refs=(ref(9),),
            claim_confidence_ref=ref(12),
        ),
        QualificationOutcome(
            **envelope(17, "QualificationOutcome"),
            candidate_ref=ref(8),
            outcome=QualificationOutcomeType.QUALIFIED,
            rationale="fit supports consideration",
        ),
        CommercialOpportunityCase(
            **envelope(40, "CommercialOpportunityCase"),
            candidate_ref=ref(8),
            offer_ref=ref(3),
            fit_ref=ref(13),
            need_ref=ref(14),
            decision_owner_ref=ref(15),
            contactability_ref=ref(16),
            qualification_ref=ref(17),
            commercial_rationale="credible opportunity",
            material_uncertainties=("need provisional",),
        ),
        PursuitDemand(
            **envelope(18, "PursuitDemand"),
            opportunity_case_ref=opportunity_a,
            next_action_description="Research owner",
            estimated_effort=Decimal("1.5"),
            unit=EffortUnit.HOUR,
            smaller_credible_action_available=False,
            rationale="minimum credible action",
        ),
        OpportunityState(
            **envelope(19, "OpportunityState"),
            opportunity_case_ref=opportunity_a,
            state=OpportunityLifecycleState.ASSESSMENT_ACTIVE,
            rationale="assessment underway",
        ),
        ExcludedOrUnresolvedRef(object_ref=ref(20), reason="evidence required"),
        QualifiedUniverseSnapshot(
            **envelope(21, "QualifiedUniverseSnapshot"),
            decision_cycle_ref=ref(4),
            opportunity_case_revision_refs=(opportunity_a, opportunity_b),
            excluded_or_unresolved_refs_with_reasons=(),
        ),
        CanonicalPairwiseComparison(
            **envelope(22, "CanonicalPairwiseComparison"),
            snapshot_ref=ref(21),
            subject_opportunity_revision=opportunity_a,
            comparator_opportunity_revision=opportunity_b,
            relationship=ComparisonRelationship.ABOVE,
            material_reason="stronger current Need",
        ),
        PriorityRelation(
            **envelope(23, "PriorityRelation"),
            higher_or_subject_ref=opportunity_a,
            lower_or_comparator_ref=opportunity_b,
            relationship=ComparisonRelationship.ABOVE,
            material_reason="stronger current Need",
        ),
        ComparativePriorityState(
            **envelope(24, "ComparativePriorityState"),
            snapshot_ref=ref(21),
            partial_order=(),
            material_reasons=("comparison complete",),
        ),
        AlternativePortfolio(
            **envelope(25, "AlternativePortfolio"),
            opportunity_refs=(opportunity_a,),
            rationale="human review option",
        ),
        AllocationMemberReason(opportunity_ref=opportunity_a, reason="highest feasible"),
        CapacityBoundedAllocationCase(
            **envelope(26, "CapacityBoundedAllocationCase"),
            snapshot_ref=ref(21),
            capacity_envelope_ref=ref(6),
            priority_state_ref=ref(24),
            act_now=(opportunity_a,),
            deferred_capacity=(opportunity_b,),
            deferred_priority=(),
            investigate=(),
            capacity_consumption=Decimal("2"),
            capacity_unit=EffortUnit.HOUR,
            marginal_reasons=(),
            material_uncertainties=(),
        ),
        scope,
        CommercialActionOpportunity(
            **envelope(27, "CommercialActionOpportunity"),
            opportunity_case_ref=opportunity_a,
            comparative_priority_ref=ref(24),
            allocation_case_ref=ref(26),
            action_type=ActionType.EVIDENCE_GATHERING,
            action_description="Research owner",
            action_scope=scope,
            rationale="owner unresolved",
            evidence_refs=(ref(9),),
            material_uncertainties=("owner unknown",),
        ),
        RecommendationReleaseReadiness(
            **envelope(28, "RecommendationReleaseReadiness"),
            cao_revision_ref=ref(27),
            state=ReleaseReadinessState.RELEASE_READY,
            blocking_conditions=(),
            limitations=("owner unknown",),
        ),
        HumanAuthorizationEvent(
            authorization_id="AUTH1",
            cao_revision_ref=ref(27),
            state=HumanAuthorizationState.APPROVED,
            requested_human_authority_ref=HUMAN,
            actual_deciding_human_ref=HUMAN,
            decision_timestamp=NOW,
            authorized_action="Research owner",
            authorized_scope=scope,
            rationale="explicit approval",
        ),
        HumanAuthorizationCurrentState(
            cao_revision_ref=ref(27),
            state=HumanAuthorizationState.APPROVED,
            latest_event_id="AUTH1",
        ),
        AgentReviewRequest(cao_revision_ref=ref(27), review_reason="ready for review"),
        AgentRun(
            run_id="RUN1",
            agent_name="Evidence Intelligence",
            prompt_version="v1",
            model_config_id="test",
            input_revision_refs=(ref(8),),
            status=RunStatus.SUCCEEDED,
            started_at=NOW,
            completed_at=NOW,
        ),
        WorkflowTransition(
            transition_id="WT1",
            decision_cycle_ref=ref(4),
            from_state=CycleWorkflowState.DRAFT,
            to_state=CycleWorkflowState.INPUTS_READY,
            trigger="inputs supplied",
            actor=HUMAN,
            object_refs=(ref(3), ref(4), ref(6)),
            occurred_at=NOW,
        ),
        MaterialImpactDecision(
            decision_id="MID1",
            changed_ref=ref(6),
            dependent_ref=ref(26),
            materially_affected=True,
            rationale="capacity changed",
            decided_by=SYSTEM,
            policy_version="v1",
            decided_at=NOW,
        ),
        ExternalExecutionEligibilityDecision(
            decision_id="EED1",
            cao_revision_ref=ref(27),
            eligible=False,
            reasons=("external execution disabled",),
            policy_version="v1",
            decided_at=NOW,
        ),
        ConformityCaseResult(
            case_id="C01",
            input_fixture_version="v1",
            input_digest="abc",
            actual_output_refs=(opportunity_a,),
            expected_rule_refs=("Stage15.C01",),
            status=ConformityStatus.PASS,
            material_differences=(),
            trace_refs=(),
            started_at=NOW,
            completed_at=NOW,
            code_version="dev",
            prompt_versions={},
            model_config_id="fake",
        ),
    ]


@pytest.mark.parametrize("model", valid_models(), ids=lambda model: type(model).__name__)
def test_every_domain_model_accepts_valid_data_and_round_trips(model: object) -> None:
    model_type = type(model)
    serialized = model.model_dump(mode="json")  # type: ignore[attr-defined]
    assert model_type.model_validate(serialized) == model  # type: ignore[attr-defined]


@pytest.mark.parametrize("model", valid_models(), ids=lambda model: type(model).__name__)
def test_every_domain_model_rejects_unknown_fields(model: object) -> None:
    invalid = model.model_dump() | {"unexpected_field": True}  # type: ignore[attr-defined]
    with pytest.raises(ValidationError, match="unexpected_field"):
        type(model).model_validate(invalid)  # type: ignore[attr-defined]


def test_revision_cannot_supersede_another_identity() -> None:
    revision_data = envelope(100, "Test") | {
        "revision": 2,
        "supersedes_ref": ref(101, "Test"),
    }
    with pytest.raises(ValidationError, match="same object identity"):
        GovernedObject(**revision_data)


def test_further_investigation_requires_specific_action() -> None:
    with pytest.raises(ValidationError, match="specific action"):
        QualificationOutcome(
            **envelope(102, "QualificationOutcome"),
            candidate_ref=ref(8),
            outcome=QualificationOutcomeType.FURTHER_INVESTIGATION_REQUIRED,
            rationale="gap exists",
        )


def test_allocation_tiers_cannot_overlap() -> None:
    member = ref(40, "CommercialOpportunityCase")
    with pytest.raises(ValidationError, match="only one allocation tier"):
        CapacityBoundedAllocationCase(
            **envelope(103, "CapacityBoundedAllocationCase"),
            snapshot_ref=ref(21),
            capacity_envelope_ref=ref(6),
            priority_state_ref=ref(24),
            act_now=(member,),
            deferred_capacity=(member,),
            deferred_priority=(),
            investigate=(),
            capacity_consumption=Decimal("2"),
            capacity_unit=EffortUnit.HOUR,
            marginal_reasons=(),
            material_uncertainties=(),
        )


def test_release_ready_cannot_have_blocking_conditions() -> None:
    with pytest.raises(ValidationError, match="cannot have blocking"):
        RecommendationReleaseReadiness(
            **envelope(104, "RecommendationReleaseReadiness"),
            cao_revision_ref=ref(27),
            state=ReleaseReadinessState.RELEASE_READY,
            blocking_conditions=("missing dependency",),
            limitations=(),
        )


def test_approval_requires_actual_human_exact_action_and_scope() -> None:
    with pytest.raises(ValidationError, match="actual deciding actor must be human"):
        HumanAuthorizationEvent(
            authorization_id="AUTH-BAD",
            cao_revision_ref=ref(27),
            state=HumanAuthorizationState.APPROVED,
            requested_human_authority_ref=HUMAN,
            actual_deciding_human_ref=SYSTEM,
            decision_timestamp=NOW,
            authorized_action="Research owner",
            authorized_scope=ActionScope(
                kind=ActionScopeKind.INTERNAL_RESEARCH,
                description="Research owner",
            ),
            rationale="invalid system approval",
        )


def test_agent_review_request_has_no_authorization_state() -> None:
    fields = AgentReviewRequest.model_fields
    assert "state" not in fields
    assert "authorized_action" not in fields
    assert "authorized_scope" not in fields
