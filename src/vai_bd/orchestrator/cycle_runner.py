"""Non-substantive coordination of workflow state and scoped holds."""

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from vai_bd.domain.enums import BlockingScope, CycleWorkflowState
from vai_bd.domain.evidence import MinimumEvidenceHardEligibilityGateResult
from vai_bd.domain.refs import ObjectRevisionRef
from vai_bd.orchestrator.state import current_state
from vai_bd.persistence.repositories import AuditRepository
from vai_bd.services.lifecycle import WorkflowService, hold_for_gate


@dataclass(frozen=True)
class PhaseControlResult:
    cycle_state: CycleWorkflowState
    held_scope: BlockingScope | None
    reason: str | None


class CycleRunner:
    """Own sequencing only; specialist and policy services own all judgments."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        workflow: WorkflowService,
    ) -> None:
        self.session_factory = session_factory
        self.workflow = workflow

    def advance(
        self,
        *,
        cycle_ref: ObjectRevisionRef,
        target: CycleWorkflowState,
        trigger: str,
        object_refs: tuple[ObjectRevisionRef, ...],
    ) -> PhaseControlResult:
        with self.session_factory.begin() as session:
            transition = self.workflow.transition(
                session,
                cycle_ref=cycle_ref,
                target=target,
                trigger=trigger,
                object_refs=object_refs,
            )
        return PhaseControlResult(transition.to_state, None, None)

    def route_gate(
        self,
        *,
        cycle_ref: ObjectRevisionRef,
        gate: MinimumEvidenceHardEligibilityGateResult,
    ) -> PhaseControlResult:
        hold = hold_for_gate(gate)
        with self.session_factory.begin() as session:
            state = current_state(AuditRepository(session).workflow_transitions_for(cycle_ref))
            if hold is None:
                return PhaseControlResult(state, None, None)
            transition = self.workflow.apply_hold(session, cycle_ref, hold)
        state = transition.to_state if transition is not None else state
        return PhaseControlResult(state, hold.scope, hold.reason)

    def resume(
        self,
        *,
        cycle_ref: ObjectRevisionRef,
        resume_state: CycleWorkflowState,
        trigger: str,
        object_refs: tuple[ObjectRevisionRef, ...],
    ) -> PhaseControlResult:
        with self.session_factory.begin() as session:
            transition = self.workflow.transition(
                session,
                cycle_ref=cycle_ref,
                target=resume_state,
                trigger=trigger,
                object_refs=object_refs,
                resume_state=resume_state,
            )
        return PhaseControlResult(transition.to_state, None, None)
