"""Deterministic cycle workflow transitions and scoped hold decisions."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from vai_bd.domain.audit import WorkflowTransition
from vai_bd.domain.enums import BlockingScope, CycleWorkflowState
from vai_bd.domain.refs import ActorRef, ObjectRevisionRef


class InvalidWorkflowTransitionError(RuntimeError):
    """The requested transition is not allowed by the workflow graph."""


_FORWARD: dict[CycleWorkflowState, CycleWorkflowState] = {
    CycleWorkflowState.DRAFT: CycleWorkflowState.INPUTS_READY,
    CycleWorkflowState.INPUTS_READY: CycleWorkflowState.DISCOVERY_READY,
    CycleWorkflowState.DISCOVERY_READY: CycleWorkflowState.EVIDENCE_READY,
    CycleWorkflowState.EVIDENCE_READY: CycleWorkflowState.ASSESSMENT_READY,
    CycleWorkflowState.ASSESSMENT_READY: CycleWorkflowState.QUALIFIED_UNIVERSE_READY,
    CycleWorkflowState.QUALIFIED_UNIVERSE_READY: CycleWorkflowState.COMPARISON_READY,
    CycleWorkflowState.COMPARISON_READY: CycleWorkflowState.ALLOCATION_READY,
    CycleWorkflowState.ALLOCATION_READY: CycleWorkflowState.ACTION_PACKAGES_READY,
    CycleWorkflowState.ACTION_PACKAGES_READY: CycleWorkflowState.HUMAN_REVIEW_READY,
}


@dataclass(frozen=True)
class HoldDecision:
    scope: BlockingScope
    reason: str
    affected_ref: ObjectRevisionRef | None = None

    @property
    def holds_cycle(self) -> bool:
        return self.scope is BlockingScope.WHOLE_CYCLE


def transition_allowed(
    current: CycleWorkflowState,
    target: CycleWorkflowState,
    *,
    resume_state: CycleWorkflowState | None = None,
) -> bool:
    if current is CycleWorkflowState.CLOSED:
        return False
    if target is CycleWorkflowState.HELD:
        return current is not CycleWorkflowState.HELD
    if current is CycleWorkflowState.HELD:
        return resume_state is not None and target is resume_state
    if target is CycleWorkflowState.ACTIVE_REASSESSMENT:
        return current not in {
            CycleWorkflowState.DRAFT,
            CycleWorkflowState.HELD,
            CycleWorkflowState.CLOSED,
        }
    if current is CycleWorkflowState.ACTIVE_REASSESSMENT:
        return resume_state is not None and target is resume_state
    if target is CycleWorkflowState.CLOSED:
        return current is CycleWorkflowState.HUMAN_REVIEW_READY
    return _FORWARD.get(current) is target


def create_transition(
    *,
    transition_id: str,
    cycle_ref: ObjectRevisionRef,
    current: CycleWorkflowState,
    target: CycleWorkflowState,
    trigger: str,
    actor: ActorRef,
    object_refs: tuple[ObjectRevisionRef, ...],
    occurred_at: datetime,
    resume_state: CycleWorkflowState | None = None,
) -> WorkflowTransition:
    if not transition_allowed(current, target, resume_state=resume_state):
        raise InvalidWorkflowTransitionError(f"cannot transition from {current} to {target}")
    return WorkflowTransition(
        transition_id=transition_id,
        decision_cycle_ref=cycle_ref,
        from_state=current,
        to_state=target,
        trigger=trigger,
        actor=actor,
        object_refs=object_refs,
        occurred_at=occurred_at,
    )


def current_state(
    transitions: Iterable[WorkflowTransition],
    *,
    initial: CycleWorkflowState = CycleWorkflowState.DRAFT,
) -> CycleWorkflowState:
    state = initial
    for item in sorted(transitions, key=lambda transition: transition.occurred_at):
        if item.from_state is not state:
            raise InvalidWorkflowTransitionError("workflow history is discontinuous")
        state = item.to_state
    return state
