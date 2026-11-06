"""Workflow graph, precondition, scoped-hold, and concurrency control tests."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from vai_bd.domain.enums import (
    ActorKind,
    BlockingScope,
    CycleWorkflowState,
    GateOutcome,
    ObjectValidity,
)
from vai_bd.domain.refs import ActorRef, ObjectRevisionRef
from vai_bd.orchestrator.dependencies import (
    PhasePreconditionError,
    WorkflowPhase,
    require_phase_inputs,
)
from vai_bd.orchestrator.state import (
    HoldDecision,
    InvalidWorkflowTransitionError,
    create_transition,
    current_state,
    transition_allowed,
)

NOW = datetime(2026, 10, 16, 12, tzinfo=UTC)
ACTOR = ActorRef(
    actor_id=UUID("70000000-0000-0000-0000-000000000001"),
    actor_kind=ActorKind.SYSTEM,
    display_name="Orchestrator",
)


def ref(number: int, object_type: str) -> ObjectRevisionRef:
    return ObjectRevisionRef(
        object_id=UUID(f"70000000-0000-0000-0000-{number:012d}"),
        object_type=object_type,
        revision=1,
    )


def test_normal_workflow_is_forward_only_and_closed_is_terminal() -> None:
    assert transition_allowed(CycleWorkflowState.DRAFT, CycleWorkflowState.INPUTS_READY)
    assert not transition_allowed(CycleWorkflowState.DRAFT, CycleWorkflowState.EVIDENCE_READY)
    assert not transition_allowed(CycleWorkflowState.CLOSED, CycleWorkflowState.HELD)


def test_held_workflow_requires_explicit_resume_state() -> None:
    assert not transition_allowed(CycleWorkflowState.HELD, CycleWorkflowState.EVIDENCE_READY)
    assert transition_allowed(
        CycleWorkflowState.HELD,
        CycleWorkflowState.EVIDENCE_READY,
        resume_state=CycleWorkflowState.EVIDENCE_READY,
    )


def test_discontinuous_history_and_invalid_transition_fail_visibly() -> None:
    cycle = ref(1, "DecisionCycleContext")
    first = create_transition(
        transition_id="one",
        cycle_ref=cycle,
        current=CycleWorkflowState.DRAFT,
        target=CycleWorkflowState.INPUTS_READY,
        trigger="bootstrapped",
        actor=ACTOR,
        object_refs=(),
        occurred_at=NOW,
    )
    assert current_state((first,)) is CycleWorkflowState.INPUTS_READY
    with pytest.raises(InvalidWorkflowTransitionError):
        create_transition(
            transition_id="bad",
            cycle_ref=cycle,
            current=CycleWorkflowState.INPUTS_READY,
            target=CycleWorkflowState.ALLOCATION_READY,
            trigger="skip",
            actor=ACTOR,
            object_refs=(),
            occurred_at=NOW,
        )


def test_phase_preconditions_require_exact_current_types_and_proceed_gate() -> None:
    refs = (
        ref(1, "DecisionCycleContext"),
        ref(2, "OfferProfile"),
        ref(3, "CompanyCandidate"),
        ref(4, "MinimumEvidenceHardEligibilityGateResult"),
        ref(5, "EvidenceRecord"),
    )
    validities = {item: ObjectValidity.CURRENT for item in refs}
    assert (
        require_phase_inputs(
            WorkflowPhase.ASSESSMENT,
            refs,
            validities,
            gate_outcome=GateOutcome.PROCEED,
        )
        == refs
    )
    with pytest.raises(PhasePreconditionError, match="assessment_requires_proceed_gate"):
        require_phase_inputs(
            WorkflowPhase.ASSESSMENT,
            refs,
            validities,
            gate_outcome=GateOutcome.EVIDENCE_REQUIRED,
        )
    validities[refs[-1]] = ObjectValidity.SUPERSEDED
    with pytest.raises(PhasePreconditionError, match="SUPERSEDED"):
        require_phase_inputs(
            WorkflowPhase.ASSESSMENT,
            refs,
            validities,
            gate_outcome=GateOutcome.PROCEED,
        )


def test_local_and_portfolio_holds_do_not_hold_whole_cycle() -> None:
    assert not HoldDecision(BlockingScope.LOCAL, "local").holds_cycle
    assert not HoldDecision(BlockingScope.PORTFOLIO, "portfolio").holds_cycle
    assert HoldDecision(BlockingScope.WHOLE_CYCLE, "cycle").holds_cycle
