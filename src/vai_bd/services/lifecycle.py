"""Deterministic non-agent application services for the governed workflow."""

from collections.abc import Mapping
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from vai_bd.domain.actions import (
    CommercialActionOpportunity,
    RecommendationReleaseReadiness,
)
from vai_bd.domain.audit import MaterialImpactDecision, WorkflowTransition
from vai_bd.domain.authorization import HumanAuthorizationEvent
from vai_bd.domain.enums import (
    ActorKind,
    CycleWorkflowState,
    GateOutcome,
    HumanAuthorizationState,
    ObjectValidity,
    QualificationOutcomeType,
)
from vai_bd.domain.evidence import MinimumEvidenceHardEligibilityGateResult
from vai_bd.domain.portfolio import QualifiedUniverseSnapshot
from vai_bd.domain.refs import ActorRef, ObjectRevisionRef
from vai_bd.orchestrator.state import HoldDecision, create_transition, current_state
from vai_bd.persistence.repositories import (
    AuditRepository,
    AuthorizationRepository,
    GovernedObjectRepository,
    SnapshotRepository,
)
from vai_bd.policies.eligibility import EligibilityFacts, evaluate_eligibility
from vai_bd.policies.reassessment import MaterialImpactRule, propagate_reassessment
from vai_bd.policies.release import ReleaseReadinessInputs, evaluate_release_readiness
from vai_bd.policies.snapshots import select_snapshot_members
from vai_bd.services.common import RevisionFactory


class WorkflowService:
    def __init__(self, factory: RevisionFactory) -> None:
        self.factory = factory

    def transition(
        self,
        session: Session,
        *,
        cycle_ref: ObjectRevisionRef,
        target: CycleWorkflowState,
        trigger: str,
        object_refs: tuple[ObjectRevisionRef, ...],
        resume_state: CycleWorkflowState | None = None,
    ) -> WorkflowTransition:
        audit = AuditRepository(session)
        history = audit.workflow_transitions_for(cycle_ref)
        transition = create_transition(
            transition_id=str(uuid4()),
            cycle_ref=cycle_ref,
            current=current_state(history),
            target=target,
            trigger=trigger,
            actor=self.factory.actor,
            object_refs=object_refs,
            occurred_at=self.factory.clock(),
            resume_state=resume_state,
        )
        return audit.append_workflow_transition(transition)

    def apply_hold(
        self,
        session: Session,
        cycle_ref: ObjectRevisionRef,
        hold: HoldDecision,
    ) -> WorkflowTransition | None:
        if not hold.holds_cycle:
            return None
        refs = (hold.affected_ref,) if hold.affected_ref is not None else ()
        return self.transition(
            session,
            cycle_ref=cycle_ref,
            target=CycleWorkflowState.HELD,
            trigger=hold.reason,
            object_refs=refs,
        )


class DeterministicDecisionService:
    def __init__(self, factory: RevisionFactory) -> None:
        self.factory = factory

    def evaluate_gate(
        self,
        session: Session,
        *,
        candidate_ref: ObjectRevisionRef,
        cycle_ref: ObjectRevisionRef,
        facts: EligibilityFacts,
        evidence_refs: tuple[ObjectRevisionRef, ...],
    ) -> MinimumEvidenceHardEligibilityGateResult:
        decision = evaluate_eligibility(facts)
        gate_ref = self.factory.new_ref("MinimumEvidenceHardEligibilityGateResult")
        gate = MinimumEvidenceHardEligibilityGateResult(
            **self.factory.envelope(
                gate_ref,
                dependencies=(candidate_ref, cycle_ref, *evidence_refs),
            ),
            candidate_ref=candidate_ref,
            decision_cycle_ref=cycle_ref,
            outcome=decision.outcome,
            reasons=decision.reasons,
            blocking_scope=decision.blocking_scope,
        )
        return GovernedObjectRepository(session).append(gate)

    def create_snapshot(
        self,
        session: Session,
        *,
        cycle_ref: ObjectRevisionRef,
        qualification_by_opportunity: Mapping[
            ObjectRevisionRef, tuple[ObjectRevisionRef, QualificationOutcomeType]
        ],
    ) -> QualifiedUniverseSnapshot:
        outcomes = {
            opportunity_ref: outcome
            for opportunity_ref, (
                _qualification_ref,
                outcome,
            ) in qualification_by_opportunity.items()
        }
        selection = select_snapshot_members(outcomes)
        snapshot_ref = self.factory.new_ref("QualifiedUniverseSnapshot")
        dependencies = (
            cycle_ref,
            *qualification_by_opportunity.keys(),
            *(item[0] for item in qualification_by_opportunity.values()),
        )
        snapshot = QualifiedUniverseSnapshot(
            **self.factory.envelope(snapshot_ref, dependencies=dependencies),
            decision_cycle_ref=cycle_ref,
            opportunity_case_revision_refs=selection.included_refs,
            excluded_or_unresolved_refs_with_reasons=selection.excluded_or_unresolved,
        )
        return SnapshotRepository(session, GovernedObjectRepository(session)).append(snapshot)

    def evaluate_readiness(
        self,
        session: Session,
        *,
        cao_ref: ObjectRevisionRef,
        inputs: ReleaseReadinessInputs,
    ) -> RecommendationReleaseReadiness:
        decision = evaluate_release_readiness(inputs)
        readiness_ref = self.factory.new_ref("RecommendationReleaseReadiness")
        readiness = RecommendationReleaseReadiness(
            **self.factory.envelope(readiness_ref, dependencies=(cao_ref,)),
            cao_revision_ref=cao_ref,
            state=decision.state,
            blocking_conditions=decision.blocking_conditions,
            limitations=decision.limitations,
        )
        return GovernedObjectRepository(session).append(readiness)


class HumanReviewService:
    def submit(
        self,
        session: Session,
        *,
        cao_ref: ObjectRevisionRef,
        requested_human: ActorRef,
        rationale: str,
    ) -> HumanAuthorizationEvent:
        if requested_human.actor_kind is not ActorKind.HUMAN:
            raise ValueError("review authority must be human")
        _require_current_cao(session, cao_ref)
        event = HumanAuthorizationEvent(
            authorization_id=str(uuid4()),
            cao_revision_ref=cao_ref,
            state=HumanAuthorizationState.PENDING_HUMAN_REVIEW,
            requested_human_authority_ref=requested_human,
            rationale=rationale,
        )
        return AuthorizationRepository(session, GovernedObjectRepository(session)).append(event)

    def decide(
        self,
        session: Session,
        *,
        cao_ref: ObjectRevisionRef,
        deciding_human: ActorRef,
        state: HumanAuthorizationState,
        rationale: str,
        decided_at: datetime,
    ) -> HumanAuthorizationEvent:
        if deciding_human.actor_kind is not ActorKind.HUMAN:
            raise ValueError("authorization decision must come from an authenticated human")
        if state not in {
            HumanAuthorizationState.APPROVED,
            HumanAuthorizationState.DECLINED,
            HumanAuthorizationState.RETURNED_FOR_REVISION,
        }:
            raise ValueError("decision must be a terminal human authorization state")
        objects = GovernedObjectRepository(session)
        cao = objects.get_exact(cao_ref, CommercialActionOpportunity)
        if cao.validity is not ObjectValidity.CURRENT:
            raise ValueError("authorization requires a current exact CAO revision")
        repository = AuthorizationRepository(session, objects)
        current = repository.current_state(cao_ref)
        if current is None or current.state is not HumanAuthorizationState.PENDING_HUMAN_REVIEW:
            raise ValueError("CAO must be pending human review")
        pending_event = repository.list_for_cao(cao_ref)[-1]
        event = HumanAuthorizationEvent(
            authorization_id=str(uuid4()),
            cao_revision_ref=cao_ref,
            state=state,
            requested_human_authority_ref=pending_event.requested_human_authority_ref,
            actual_deciding_human_ref=deciding_human,
            decision_timestamp=decided_at,
            authorized_action=(
                cao.action_description if state is HumanAuthorizationState.APPROVED else None
            ),
            authorized_scope=(
                cao.action_scope if state is HumanAuthorizationState.APPROVED else None
            ),
            rationale=rationale,
        )
        return repository.append(event)


class ReassessmentService:
    def __init__(self, factory: RevisionFactory, policy_version: str = "1.0.0") -> None:
        self.factory = factory
        self.policy_version = policy_version

    def propagate(
        self,
        session: Session,
        *,
        changed_ref: ObjectRevisionRef,
        impact_rule: MaterialImpactRule,
    ) -> tuple[ObjectRevisionRef, ...]:
        objects = GovernedObjectRepository(session)
        graph: dict[ObjectRevisionRef, tuple[ObjectRevisionRef, ...]] = {}
        frontier = [changed_ref]
        seen: set[ObjectRevisionRef] = set()
        while frontier:
            ref = frontier.pop(0)
            if ref in seen:
                continue
            seen.add(ref)
            dependents = objects.dependents_of(ref)
            graph[ref] = dependents
            frontier.extend(dependents)
        result = propagate_reassessment(changed_ref, graph, impact_rule)
        audit = AuditRepository(session)
        for item in result.decisions:
            audit.append_material_impact(
                MaterialImpactDecision(
                    decision_id=str(uuid4()),
                    changed_ref=item.changed_ref,
                    dependent_ref=item.dependent_ref,
                    materially_affected=item.materially_affected,
                    rationale=item.rationale,
                    decided_by=self.factory.actor,
                    policy_version=self.policy_version,
                    decided_at=self.factory.clock(),
                )
            )
        for ref in result.marked_refs:
            objects.mark_reassessment_required(
                ref,
                trigger=f"material change in {changed_ref.object_type}",
                reason="bounded material-impact policy marked this dependent",
            )
        return result.marked_refs


def hold_for_gate(
    gate: MinimumEvidenceHardEligibilityGateResult,
) -> HoldDecision | None:
    if gate.outcome is GateOutcome.PROCEED:
        return None
    return HoldDecision(
        scope=gate.blocking_scope,
        reason="; ".join(gate.reasons),
        affected_ref=gate.candidate_ref,
    )


def _require_current_cao(session: Session, ref: ObjectRevisionRef) -> None:
    cao = GovernedObjectRepository(session).get_exact(ref, CommercialActionOpportunity)
    if cao.validity is not ObjectValidity.CURRENT:
        raise ValueError("review submission requires a current exact CAO revision")
