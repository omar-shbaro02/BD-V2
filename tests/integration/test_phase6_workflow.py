"""End-to-end Phase 6 workflow with fake specialists and real PostgreSQL."""

from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import count
from uuid import UUID

import pytest
from sqlalchemy.orm import Session, sessionmaker

from vai_bd.agents.contracts import (
    AllocationMemberProposal,
    AllocationOperationOutput,
    CandidateProposal,
    CommercialActionInput,
    CommercialActionOutput,
    ComparisonOperationOutput,
    ConfidenceProposal,
    ContactabilityProposal,
    DecisionOwnerProposal,
    DemandFact,
    EvidenceIntelligenceInput,
    EvidenceIntelligenceOutput,
    EvidenceProposal,
    FitProposal,
    MarketDiscoveryInput,
    MarketDiscoveryOutput,
    NeedProposal,
    OpportunityIntelligenceInput,
    OpportunityIntelligenceOutput,
    PairRequest,
    PairwiseComparisonProposal,
    PortfolioAllocationInput,
    PortfolioAllocationOutput,
    PortfolioComparisonInput,
    QualificationProposal,
    SpecialistName,
    UntrustedObservation,
)
from vai_bd.agents.runner import FakeAgentRunner
from vai_bd.domain.actions import ActionScope, CommercialActionOpportunity
from vai_bd.domain.cycle import CapacityEnvelope, DecisionCycleContext, OfferProfile
from vai_bd.domain.enums import (
    ActionScopeKind,
    ActionType,
    ActorKind,
    BlockingScope,
    ComparisonRelationship,
    ConfidenceLevel,
    CycleWorkflowState,
    DecisionCycleStatus,
    EffortUnit,
    EvidenceAdmissibility,
    EvidenceCurrentness,
    EvidenceDirectness,
    GateOutcome,
    HumanAuthorizationState,
    NeedStatus,
    ObjectValidity,
    QualificationOutcomeType,
    ReleaseReadinessState,
)
from vai_bd.domain.opportunity import PursuitDemand
from vai_bd.domain.portfolio import (
    CapacityBoundedAllocationCase,
    ComparativePriorityState,
)
from vai_bd.domain.refs import ActorRef, ObjectRevisionRef, SourceRef
from vai_bd.orchestrator.cycle_runner import CycleRunner
from vai_bd.orchestrator.idempotency import IdempotencyConflictError, IdempotencyStatus
from vai_bd.persistence.orm import IdempotencyRecordRow
from vai_bd.persistence.repositories import AuditRepository, GovernedObjectRepository
from vai_bd.policies.eligibility import EligibilityFacts
from vai_bd.policies.reassessment import MaterialImpactDecision
from vai_bd.policies.release import ReleaseReadinessInputs
from vai_bd.policies.results import PolicyCheck
from vai_bd.services.common import RevisionFactory
from vai_bd.services.cycles import DecisionCycleServices
from vai_bd.services.executor import (
    AgentPhaseExecutionError,
    AgentPhaseExecutor,
    IdempotentMutationExecutor,
)
from vai_bd.services.lifecycle import (
    DeterministicDecisionService,
    HumanReviewService,
    ReassessmentService,
    WorkflowService,
)

NOW = datetime(2026, 10, 16, 12, tzinfo=UTC)
AGENT_ACTOR = ActorRef(
    actor_id=UUID("80000000-0000-0000-0000-000000000001"),
    actor_kind=ActorKind.AGENT,
    display_name="Governed specialists",
)
HUMAN = ActorRef(
    actor_id=UUID("80000000-0000-0000-0000-000000000002"),
    actor_kind=ActorKind.HUMAN,
    display_name="Authenticated operator",
)
SOURCE = SourceRef(source_id="phase6-source", uri_or_reference="synthetic://phase6")


def fixed_ref(number: int, object_type: str) -> ObjectRevisionRef:
    return ObjectRevisionRef(
        object_id=UUID(f"80000000-0000-0000-0000-{number:012d}"),
        object_type=object_type,
        revision=1,
    )


def fake_executor(
    factory: sessionmaker[Session],
    name: SpecialistName,
    output: object,
    run_counter: count,
) -> AgentPhaseExecutor:
    runner = FakeAgentRunner({name: (output,)})  # type: ignore[arg-type]
    return AgentPhaseExecutor(
        factory,
        runner,
        clock=lambda: NOW,
        id_factory=lambda: f"phase6-run-{next(run_counter)}",
    )


def opportunity_output(
    refs: tuple[ObjectRevisionRef, ...], evidence: ObjectRevisionRef
) -> OpportunityIntelligenceOutput:
    confidences = tuple(
        ConfidenceProposal(
            claim_key=key,
            level=ConfidenceLevel.MEDIUM,
            rationale="supplied evidence",
            evidence_refs=(evidence,),
        )
        for key in ("fit", "need", "owner", "contact")
    )
    return OpportunityIntelligenceOutput(
        referenced_input_refs=refs,
        confidences=confidences,
        fit=FitProposal(
            judgment="aligned",
            rationale="supported fit",
            evidence_refs=(evidence,),
            confidence_claim_key="fit",
        ),
        need=NeedProposal(
            hypothesis="plausible need",
            status=NeedStatus.PROVISIONAL,
            rationale="not yet directly confirmed",
            evidence_refs=(evidence,),
            confidence_claim_key="need",
        ),
        decision_owner=DecisionOwnerProposal(
            role_hypothesis="COO",
            rationale="role hypothesis",
            evidence_refs=(evidence,),
            confidence_claim_key="owner",
        ),
        contactability=ContactabilityProposal(
            assessment="research required",
            known_paths=(),
            constraints=("no named contact",),
            rationale="no supplied contact path",
            evidence_refs=(evidence,),
            confidence_claim_key="contact",
        ),
        qualification=QualificationProposal(
            outcome=QualificationOutcomeType.QUALIFIED,
            rationale="credible case with disclosed uncertainty",
        ),
        commercial_rationale="fit supported and need remains provisional",
        material_uncertainties=("need unconfirmed",),
    )


@pytest.mark.asyncio
async def test_complete_fake_agent_cycle_is_persisted_and_resumable(
    db_session: Session,
) -> None:
    nested_factory = sessionmaker(
        bind=db_session.connection(),
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    factory = RevisionFactory(AGENT_ACTOR, clock=lambda: NOW)
    mutation_executor = IdempotentMutationExecutor(nested_factory)
    run_counter = count(1)

    offer_ref = fixed_ref(1, "OfferProfile")
    cycle_ref = fixed_ref(2, "DecisionCycleContext")
    capacity_ref = fixed_ref(3, "CapacityEnvelope")
    offer = OfferProfile(
        **factory.envelope(offer_ref),
        name="Governed offer",
        problem_statement="Improve decision quality",
        intended_buyer_roles=("COO",),
        fit_dimensions=("complex delivery",),
        version="v1",
    )
    cycle = DecisionCycleContext(
        **factory.envelope(cycle_ref, dependencies=(offer_ref,)),
        offer_ref=offer_ref,
        target_market_boundary="synthetic market",
        effective_date=date(2026, 10, 16),
        operator_ref=fixed_ref(99, "Operator"),
        status=DecisionCycleStatus.ACTIVE,
    )
    capacity = CapacityEnvelope(
        **factory.envelope(capacity_ref, dependencies=(cycle_ref,)),
        decision_cycle_ref=cycle_ref,
        usable_time=Decimal("8"),
        unit=EffortUnit.HOUR,
        planning_horizon="week",
        max_meaningful_concurrent_pursuits=2,
        fixed_commitments=Decimal("1"),
        review_trigger="capacity change",
        effective_date=date(2026, 10, 16),
    )
    bootstrap_services = DecisionCycleServices(
        fake_executor(
            nested_factory,
            SpecialistName.MARKET_DISCOVERY,
            {},
            run_counter,
        ),
        factory,
    )
    boot = mutation_executor.execute(
        operation="bootstrap",
        idempotency_key="bootstrap-1",
        request_payload={"cycle": str(cycle_ref.object_id)},
        mutation=lambda session: bootstrap_services.bootstrap(
            session, offer=offer, cycle=cycle, capacity=capacity
        ),
    )
    replay = mutation_executor.execute(
        operation="bootstrap",
        idempotency_key="bootstrap-1",
        request_payload={"cycle": str(cycle_ref.object_id)},
        mutation=lambda session: (),
    )
    assert replay.replayed and replay.result_refs == boot.result_refs
    with pytest.raises(IdempotencyConflictError):
        mutation_executor.execute(
            operation="bootstrap",
            idempotency_key="bootstrap-1",
            request_payload={"cycle": "different-request"},
            mutation=lambda session: (),
        )

    workflow = WorkflowService(factory)
    cycle_runner = CycleRunner(nested_factory, workflow)
    cycle_runner.advance(
        cycle_ref=cycle_ref,
        target=CycleWorkflowState.INPUTS_READY,
        trigger="bootstrap complete",
        object_refs=boot.result_refs,
    )

    observation = UntrustedObservation(
        observation_id="obs-1",
        content="synthetic company is present",
        source=SOURCE,
        source_type="synthetic",
        source_date=date(2026, 10, 1),
        provenance="phase6 fixture",
    )
    discovery_input = MarketDiscoveryInput(
        exact_input_refs=(cycle_ref, offer_ref),
        decision_cycle_ref=cycle_ref,
        offer_ref=offer_ref,
        target_market_boundary="synthetic market",
        observations=(observation,),
    )
    discovery_output = MarketDiscoveryOutput(
        referenced_input_refs=discovery_input.exact_input_refs,
        coverage_basis="supplied fixture",
        coverage_limitations=("not exhaustive",),
        coverage_status="PARTIAL",
        candidates=(
            CandidateProposal(
                proposal_key="candidate",
                company_name="Synthetic Company",
                market_presence_claims=("present",),
                segment_claims=("target segment",),
                source_refs=(SOURCE,),
                candidate_status="CANDIDATE",
            ),
        ),
        added_candidate_keys=("candidate",),
    )
    discovery_services = DecisionCycleServices(
        fake_executor(
            nested_factory,
            SpecialistName.MARKET_DISCOVERY,
            discovery_output,
            run_counter,
        ),
        factory,
    )
    discovery = await discovery_services.discovery("discovery-1", discovery_input)
    candidate_ref = discovery.result_refs[1]
    replay_discovery = await discovery_services.discovery("discovery-1", discovery_input)
    assert replay_discovery.replayed and replay_discovery.result_refs == discovery.result_refs
    rejected_output = discovery_output.model_copy(update={"claims_exhaustive_coverage": True})
    rejected_services = DecisionCycleServices(
        fake_executor(
            nested_factory,
            SpecialistName.MARKET_DISCOVERY,
            rejected_output,
            run_counter,
        ),
        factory,
    )
    with pytest.raises(AgentPhaseExecutionError):
        await rejected_services.discovery("discovery-invalid", discovery_input)
    with nested_factory() as session:
        rejected_claim = session.get(IdempotencyRecordRow, ("discovery", "discovery-invalid"))
        assert rejected_claim is not None
        assert rejected_claim.status == IdempotencyStatus.FAILED.value
    cycle_runner.advance(
        cycle_ref=cycle_ref,
        target=CycleWorkflowState.DISCOVERY_READY,
        trigger="discovery complete",
        object_refs=discovery.result_refs,
    )

    evidence_input = EvidenceIntelligenceInput(
        exact_input_refs=(candidate_ref, cycle_ref),
        candidate_ref=candidate_ref,
        decision_cycle_ref=cycle_ref,
        observations=(observation,),
    )
    evidence_output = EvidenceIntelligenceOutput(
        referenced_input_refs=evidence_input.exact_input_refs,
        evidence_records=(
            EvidenceProposal(
                proposal_key="evidence",
                claim_text="synthetic company is present",
                source=SOURCE,
                source_type="synthetic",
                source_date=date(2026, 10, 1),
                provenance="phase6 fixture",
                directness=EvidenceDirectness.DIRECT,
                currentness=EvidenceCurrentness.CURRENT,
                admissibility=EvidenceAdmissibility.ADMISSIBLE,
            ),
        ),
    )
    evidence_services = DecisionCycleServices(
        fake_executor(
            nested_factory,
            SpecialistName.EVIDENCE_INTELLIGENCE,
            evidence_output,
            run_counter,
        ),
        factory,
    )
    evidence_result = await evidence_services.evidence("evidence-1", evidence_input)
    evidence_ref = evidence_result.result_refs[0]
    cycle_runner.advance(
        cycle_ref=cycle_ref,
        target=CycleWorkflowState.EVIDENCE_READY,
        trigger="evidence complete",
        object_refs=evidence_result.result_refs,
    )

    decisions = DeterministicDecisionService(factory)
    with nested_factory.begin() as session:
        gate = decisions.evaluate_gate(
            session,
            candidate_ref=candidate_ref,
            cycle_ref=cycle_ref,
            facts=EligibilityFacts(
                market_boundary_valid=True,
                material_contradiction=False,
                minimum_evidence_satisfied=True,
            ),
            evidence_refs=(evidence_ref,),
        )
    assert cycle_runner.route_gate(cycle_ref=cycle_ref, gate=gate).held_scope is None

    assessment_refs: list[
        tuple[ObjectRevisionRef, ObjectRevisionRef, ObjectRevisionRef, ObjectRevisionRef]
    ] = []
    for attempt in (1, 2):
        exact_refs = (cycle_ref, offer_ref, candidate_ref, gate.revision_ref, evidence_ref)
        assessment_input = OpportunityIntelligenceInput(
            exact_input_refs=exact_refs,
            decision_cycle_ref=cycle_ref,
            offer_ref=offer_ref,
            candidate_ref=candidate_ref,
            gate_result_ref=gate.revision_ref,
            gate_outcome="PROCEED",
            evidence_refs=(evidence_ref,),
        )
        assessment_output = opportunity_output(exact_refs, evidence_ref)
        assessment_services = DecisionCycleServices(
            fake_executor(
                nested_factory,
                SpecialistName.OPPORTUNITY_INTELLIGENCE,
                assessment_output,
                run_counter,
            ),
            factory,
        )
        result = await assessment_services.assessment(f"assessment-{attempt}", assessment_input)
        assessment_refs.append(
            (
                result.result_refs[-1],
                result.result_refs[-2],
                result.result_refs[6],
                result.result_refs[7],
            )
        )
    cycle_runner.advance(
        cycle_ref=cycle_ref,
        target=CycleWorkflowState.ASSESSMENT_READY,
        trigger="assessments complete",
        object_refs=tuple(item[0] for item in assessment_refs),
    )

    with nested_factory.begin() as session:
        snapshot = decisions.create_snapshot(
            session,
            cycle_ref=cycle_ref,
            qualification_by_opportunity={
                opportunity: (qualification, QualificationOutcomeType.QUALIFIED)
                for opportunity, qualification, _owner, _contact in assessment_refs
            },
        )
    opportunity_one, opportunity_two = assessment_refs[0][0], assessment_refs[1][0]
    cycle_runner.advance(
        cycle_ref=cycle_ref,
        target=CycleWorkflowState.QUALIFIED_UNIVERSE_READY,
        trigger="snapshot frozen",
        object_refs=(snapshot.revision_ref,),
    )

    comparison_refs = (snapshot.revision_ref, opportunity_one, opportunity_two)
    comparison_input = PortfolioComparisonInput(
        exact_input_refs=comparison_refs,
        snapshot_ref=snapshot.revision_ref,
        opportunity_refs=(opportunity_one, opportunity_two),
        required_pairs=(PairRequest(first=opportunity_one, second=opportunity_two),),
    )
    comparison_output = PortfolioAllocationOutput(
        result=ComparisonOperationOutput(
            referenced_input_refs=comparison_refs,
            comparisons=(
                PairwiseComparisonProposal(
                    subject_ref=opportunity_one,
                    comparator_ref=opportunity_two,
                    relationship=ComparisonRelationship.ABOVE,
                    material_reason="stronger current fit evidence",
                ),
            ),
            material_reasons=("transparent qualitative comparison",),
        )
    )
    comparison_services = DecisionCycleServices(
        fake_executor(
            nested_factory,
            SpecialistName.PORTFOLIO_ALLOCATION,
            comparison_output,
            run_counter,
        ),
        factory,
    )
    comparison = await comparison_services.comparison("comparison-1", comparison_input)
    priority_ref = comparison.result_refs[-1]
    cycle_runner.advance(
        cycle_ref=cycle_ref,
        target=CycleWorkflowState.COMPARISON_READY,
        trigger="comparison complete",
        object_refs=comparison.result_refs,
    )

    demand_refs: list[ObjectRevisionRef] = []
    with nested_factory.begin() as session:
        objects = GovernedObjectRepository(session)
        for index, opportunity in enumerate((opportunity_one, opportunity_two), start=1):
            demand_ref = factory.new_ref("PursuitDemand")
            demand = PursuitDemand(
                **factory.envelope(demand_ref, dependencies=(opportunity,)),
                opportunity_case_ref=opportunity,
                next_action_description=f"next action {index}",
                estimated_effort=Decimal("2"),
                unit=EffortUnit.HOUR,
                smaller_credible_action_available=False,
                rationale="fixture demand",
            )
            objects.append(demand)
            demand_refs.append(demand.revision_ref)
    allocation_refs = (
        snapshot.revision_ref,
        priority_ref,
        capacity_ref,
        opportunity_one,
        opportunity_two,
        *demand_refs,
    )
    allocation_input = PortfolioAllocationInput(
        exact_input_refs=allocation_refs,
        snapshot_ref=snapshot.revision_ref,
        priority_state_ref=priority_ref,
        capacity_envelope_ref=capacity_ref,
        opportunity_refs=(opportunity_one, opportunity_two),
        demands=(
            DemandFact(
                opportunity_ref=opportunity,
                demand_ref=demand_ref,
                estimated_effort=Decimal("2"),
                unit=EffortUnit.HOUR,
                smaller_credible_action_available=False,
            )
            for opportunity, demand_ref in zip(
                (opportunity_one, opportunity_two), demand_refs, strict=True
            )
        ),
        available_capacity=Decimal("7"),
        unit=EffortUnit.HOUR,
        planning_horizon="week",
        max_concurrent_pursuits=2,
    )
    allocation_output = PortfolioAllocationOutput(
        result=AllocationOperationOutput(
            referenced_input_refs=allocation_refs,
            act_now=(opportunity_one,),
            deferred_capacity=(),
            deferred_priority=(opportunity_two,),
            investigate=(),
            capacity_consumption=Decimal("2"),
            capacity_unit=EffortUnit.HOUR,
            marginal_reasons=(
                AllocationMemberProposal(opportunity_ref=opportunity_one, reason="higher priority"),
                AllocationMemberProposal(
                    opportunity_ref=opportunity_two, reason="deferred by priority"
                ),
            ),
            material_uncertainties=(),
        )
    )
    allocation_services = DecisionCycleServices(
        fake_executor(
            nested_factory,
            SpecialistName.PORTFOLIO_ALLOCATION,
            allocation_output,
            run_counter,
        ),
        factory,
    )
    allocation_result = await allocation_services.allocation("allocation-1", allocation_input)
    allocation_ref = allocation_result.result_refs[-1]
    cycle_runner.advance(
        cycle_ref=cycle_ref,
        target=CycleWorkflowState.ALLOCATION_READY,
        trigger="allocation validated",
        object_refs=allocation_result.result_refs,
    )

    owner_ref, contact_ref = assessment_refs[0][2], assessment_refs[0][3]
    action_refs = (
        opportunity_one,
        priority_ref,
        allocation_ref,
        owner_ref,
        contact_ref,
        evidence_ref,
    )
    action_input = CommercialActionInput(
        exact_input_refs=action_refs,
        opportunity_case_ref=opportunity_one,
        comparative_priority_ref=priority_ref,
        allocation_case_ref=allocation_ref,
        decision_owner_ref=owner_ref,
        contactability_ref=contact_ref,
        evidence_refs=(evidence_ref,),
        material_uncertainties=("owner unnamed",),
    )
    action_output = CommercialActionOutput(
        referenced_input_refs=action_refs,
        action_type=ActionType.EVIDENCE_GATHERING,
        action_description="identify the named decision owner",
        action_scope=ActionScope(
            kind=ActionScopeKind.INTERNAL_RESEARCH,
            description="internal research only",
        ),
        decision_owner_ref=owner_ref,
        rationale="owner must be identified before outreach",
        evidence_refs=(evidence_ref,),
        material_uncertainties=("owner unnamed",),
        draft_content="Research checklist; not authorization to send.",
    )
    action_services = DecisionCycleServices(
        fake_executor(
            nested_factory,
            SpecialistName.COMMERCIAL_ACTION,
            action_output,
            run_counter,
        ),
        factory,
    )
    action_result = await action_services.action("action-1", action_input)
    action_ref = action_result.result_refs[0]
    cycle_runner.advance(
        cycle_ref=cycle_ref,
        target=CycleWorkflowState.ACTION_PACKAGES_READY,
        trigger="action prepared",
        object_refs=(action_ref,),
    )

    with nested_factory.begin() as session:
        readiness = decisions.evaluate_readiness(
            session,
            cao_ref=action_ref,
            inputs=ReleaseReadinessInputs(
                upstream_revisions=PolicyCheck(True),
                contradictions_disclosed=True,
                limitations_disclosed=True,
                action_type_present=True,
                action_description_present=True,
                action_scope_present=True,
                rationale_present=True,
                evidence_refs_present=True,
                allocation_required=True,
                allocation_valid=True,
                unresolved_material_defect=False,
                disclosed_limitations=("owner unnamed",),
            ),
        )
        review = HumanReviewService()
        review.submit(
            session,
            cao_ref=action_ref,
            requested_human=HUMAN,
            rationale="ready for human review",
        )
        approval = review.decide(
            session,
            cao_ref=action_ref,
            deciding_human=HUMAN,
            state=HumanAuthorizationState.APPROVED,
            rationale="approved exact internal research action",
            decided_at=NOW,
        )
    assert readiness.state is ReleaseReadinessState.READY_WITH_DISCLOSED_LIMITATIONS
    assert approval.authorized_action == action_output.action_description
    cycle_runner.advance(
        cycle_ref=cycle_ref,
        target=CycleWorkflowState.HUMAN_REVIEW_READY,
        trigger="human review recorded",
        object_refs=(readiness.revision_ref, action_ref),
    )
    cycle_runner.advance(
        cycle_ref=cycle_ref,
        target=CycleWorkflowState.ACTIVE_REASSESSMENT,
        trigger="capacity changed",
        object_refs=(capacity_ref,),
    )

    with nested_factory.begin() as session:
        marked = ReassessmentService(factory).propagate(
            session,
            changed_ref=capacity_ref,
            impact_rule=lambda _changed, _dependent: MaterialImpactDecision(
                True, "capacity-dependent feasibility changed"
            ),
        )
    assert allocation_ref in marked
    assert action_ref in marked
    assert readiness.revision_ref in marked

    whole_cycle_gate = gate.model_copy(
        update={
            "outcome": GateOutcome.CONTRADICTION_BLOCK,
            "blocking_scope": BlockingScope.WHOLE_CYCLE,
            "reasons": ("governing boundary invalidated",),
        }
    )
    held = cycle_runner.route_gate(cycle_ref=cycle_ref, gate=whole_cycle_gate)
    assert held.cycle_state is CycleWorkflowState.HELD
    assert held.held_scope is BlockingScope.WHOLE_CYCLE
    resumed = cycle_runner.resume(
        cycle_ref=cycle_ref,
        resume_state=CycleWorkflowState.ACTIVE_REASSESSMENT,
        trigger="boundary corrected",
        object_refs=(cycle_ref,),
    )
    assert resumed.cycle_state is CycleWorkflowState.ACTIVE_REASSESSMENT

    with nested_factory() as session:
        objects = GovernedObjectRepository(session)
        assert objects.get_exact(action_ref, CommercialActionOpportunity).validity is (
            ObjectValidity.REASSESSMENT_REQUIRED
        )
        assert (
            objects.get_exact(allocation_ref, CapacityBoundedAllocationCase).validity
            is ObjectValidity.REASSESSMENT_REQUIRED
        )
        assert (
            objects.get_exact(priority_ref, ComparativePriorityState).validity
            is ObjectValidity.CURRENT
        )
        assert session.get(IdempotencyRecordRow, ("discovery", "discovery-1")) is not None
        transitions = AuditRepository(session).workflow_transitions_for(cycle_ref)
        assert transitions[-1].to_state is CycleWorkflowState.ACTIVE_REASSESSMENT
