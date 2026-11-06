"""Append-only repository and transaction tests against PostgreSQL."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vai_bd.domain.actions import ActionScope
from vai_bd.domain.audit import (
    AgentRun,
    ConformityCaseResult,
    ExternalExecutionEligibilityDecision,
    MaterialImpactDecision,
    WorkflowTransition,
)
from vai_bd.domain.authorization import HumanAuthorizationEvent
from vai_bd.domain.enums import (
    ActionScopeKind,
    ActorKind,
    ComparisonRelationship,
    ConformityStatus,
    CycleWorkflowState,
    HumanAuthorizationState,
    ObjectValidity,
    RunStatus,
)
from vai_bd.domain.envelopes import GovernedObject
from vai_bd.domain.portfolio import CanonicalPairwiseComparison, QualifiedUniverseSnapshot
from vai_bd.domain.refs import ActorRef, ObjectRevisionRef
from vai_bd.persistence.database import create_session_factory
from vai_bd.persistence.orm import (
    AgentRunRow,
    ConformityCaseResultRow,
    ExternalExecutionDecisionRow,
    MaterialImpactDecisionRow,
    ObjectRevisionRow,
    WorkflowTransitionRow,
)
from vai_bd.persistence.repositories import (
    AuditRepository,
    AuthorizationRepository,
    ComparisonRepository,
    GovernedObjectRepository,
    PersistenceError,
    RevisionConflictError,
    SnapshotRepository,
)
from vai_bd.persistence.unit_of_work import UnitOfWork

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
SYSTEM = ActorRef(
    actor_id=UUID("10000000-0000-0000-0000-000000000001"),
    actor_kind=ActorKind.SYSTEM,
    display_name="System",
)
HUMAN = ActorRef(
    actor_id=UUID("10000000-0000-0000-0000-000000000002"),
    actor_kind=ActorKind.HUMAN,
    display_name="Human",
)


def governed(
    number: int,
    object_type: str,
    *,
    revision: int = 1,
    supersedes: ObjectRevisionRef | None = None,
    dependencies: tuple[ObjectRevisionRef, ...] = (),
) -> GovernedObject:
    return GovernedObject(
        object_id=UUID(f"20000000-0000-0000-0000-{number:012d}"),
        object_type=object_type,
        revision=revision,
        supersedes_ref=supersedes,
        created_at=NOW,
        created_by=SYSTEM,
        dependencies=dependencies,
    )


def test_append_supersede_preserves_history_and_exact_dependencies(db_session: Session) -> None:
    repo = GovernedObjectRepository(db_session)
    source = governed(1, "EvidenceRecord")
    dependent = governed(2, "CommercialOpportunityCase", dependencies=(source.revision_ref,))
    repo.append(source)
    repo.append(dependent)

    successor = governed(
        2,
        "CommercialOpportunityCase",
        revision=2,
        supersedes=dependent.revision_ref,
        dependencies=(source.revision_ref,),
    )
    repo.append(successor)

    historical = repo.get_exact(dependent.revision_ref, GovernedObject)
    assert historical.revision == 1
    assert historical.validity is ObjectValidity.SUPERSEDED
    assert repo.get_current(successor.object_id, GovernedObject) == successor
    assert repo.dependencies_of(successor.revision_ref) == (source.revision_ref,)
    assert repo.dependents_of(source.revision_ref) == (
        dependent.revision_ref,
        successor.revision_ref,
    )
    old_row = db_session.get(ObjectRevisionRow, (dependent.object_id, 1))
    assert old_row is not None
    assert old_row.validity == ObjectValidity.SUPERSEDED.value


def test_reassessment_changes_control_validity_without_overwriting_payload(
    db_session: Session,
) -> None:
    repo = GovernedObjectRepository(db_session)
    value = governed(60, "NeedHypothesis")
    repo.append(value)
    repo.mark_reassessment_required(
        value.revision_ref,
        trigger="source became unreliable",
        reason="claim depended on source group S1",
    )

    reloaded = repo.get_exact(value.revision_ref, GovernedObject)
    assert reloaded.validity is ObjectValidity.REASSESSMENT_REQUIRED
    assert reloaded.reassessment_trigger == "source became unreliable"
    assert reloaded.reassessment_reason == "claim depended on source group S1"
    assert repo.get_current(value.object_id, GovernedObject) is None


def test_successor_must_match_locked_current_revision(db_session: Session) -> None:
    repo = GovernedObjectRepository(db_session)
    initial = governed(3, "OfferProfile")
    repo.append(initial)
    invalid = governed(3, "OfferProfile", revision=3, supersedes=initial.revision_ref)
    with pytest.raises(RevisionConflictError, match="exact current revision"):
        repo.append(invalid)


def test_transaction_rollback_removes_partial_revision(db_session: Session) -> None:
    repo = GovernedObjectRepository(db_session)
    value = governed(4, "OfferProfile")
    nested = db_session.begin_nested()
    repo.append(value)
    nested.rollback()
    assert repo.get_current(value.object_id, GovernedObject) is None


def test_snapshot_membership_is_revision_specific_and_historical(db_session: Session) -> None:
    objects = GovernedObjectRepository(db_session)
    snapshots = SnapshotRepository(db_session, objects)
    opportunity_a = governed(10, "CommercialOpportunityCase")
    opportunity_b = governed(11, "CommercialOpportunityCase")
    objects.append(opportunity_a)
    objects.append(opportunity_b)
    snapshot_v1 = QualifiedUniverseSnapshot(
        object_id=UUID("20000000-0000-0000-0000-000000000012"),
        object_type="QualifiedUniverseSnapshot",
        revision=1,
        created_at=NOW,
        created_by=SYSTEM,
        decision_cycle_ref=opportunity_a.revision_ref,
        opportunity_case_revision_refs=(opportunity_a.revision_ref,),
        excluded_or_unresolved_refs_with_reasons=(),
    )
    snapshots.append(snapshot_v1)
    snapshot_v2 = snapshot_v1.model_copy(
        update={
            "revision": 2,
            "supersedes_ref": snapshot_v1.revision_ref,
            "opportunity_case_revision_refs": (
                opportunity_a.revision_ref,
                opportunity_b.revision_ref,
            ),
        }
    )
    snapshots.append(snapshot_v2)

    assert snapshots.members(snapshot_v1.revision_ref) == (opportunity_a.revision_ref,)
    assert set(snapshots.members(snapshot_v2.revision_ref)) == {
        opportunity_a.revision_ref,
        opportunity_b.revision_ref,
    }


def test_canonical_pair_is_unique_regardless_of_authored_direction(db_session: Session) -> None:
    objects = GovernedObjectRepository(db_session)
    snapshots = SnapshotRepository(db_session, objects)
    comparisons = ComparisonRepository(db_session, objects)
    opportunity_a = governed(20, "CommercialOpportunityCase")
    opportunity_b = governed(21, "CommercialOpportunityCase")
    objects.append(opportunity_a)
    objects.append(opportunity_b)
    snapshot = QualifiedUniverseSnapshot(
        object_id=UUID("20000000-0000-0000-0000-000000000022"),
        object_type="QualifiedUniverseSnapshot",
        revision=1,
        created_at=NOW,
        created_by=SYSTEM,
        decision_cycle_ref=opportunity_a.revision_ref,
        opportunity_case_revision_refs=(opportunity_a.revision_ref, opportunity_b.revision_ref),
        excluded_or_unresolved_refs_with_reasons=(),
    )
    snapshots.append(snapshot)
    first = CanonicalPairwiseComparison(
        object_id=UUID("20000000-0000-0000-0000-000000000023"),
        object_type="CanonicalPairwiseComparison",
        revision=1,
        created_at=NOW,
        created_by=SYSTEM,
        snapshot_ref=snapshot.revision_ref,
        subject_opportunity_revision=opportunity_a.revision_ref,
        comparator_opportunity_revision=opportunity_b.revision_ref,
        relationship=ComparisonRelationship.ABOVE,
        material_reason="A stronger",
    )
    comparisons.append(first)
    duplicate = first.model_copy(
        update={
            "object_id": UUID("20000000-0000-0000-0000-000000000024"),
            "subject_opportunity_revision": opportunity_b.revision_ref,
            "comparator_opportunity_revision": opportunity_a.revision_ref,
            "relationship": ComparisonRelationship.BELOW,
        }
    )
    with pytest.raises(IntegrityError):
        comparisons.append(duplicate)


def test_authorization_events_are_append_only_and_revision_isolated(db_session: Session) -> None:
    objects = GovernedObjectRepository(db_session)
    authorizations = AuthorizationRepository(db_session, objects)
    cao_v1 = governed(30, "CommercialActionOpportunity")
    objects.append(cao_v1)
    pending = HumanAuthorizationEvent(
        authorization_id="AUTH-PENDING",
        cao_revision_ref=cao_v1.revision_ref,
        state=HumanAuthorizationState.PENDING_HUMAN_REVIEW,
        requested_human_authority_ref=HUMAN,
        rationale="submitted",
    )
    approved = HumanAuthorizationEvent(
        authorization_id="AUTH-APPROVED",
        cao_revision_ref=cao_v1.revision_ref,
        state=HumanAuthorizationState.APPROVED,
        requested_human_authority_ref=HUMAN,
        actual_deciding_human_ref=HUMAN,
        decision_timestamp=NOW,
        authorized_action="Research owner",
        authorized_scope=ActionScope(
            kind=ActionScopeKind.INTERNAL_RESEARCH,
            description="Research owner",
        ),
        rationale="approved",
    )
    authorizations.append(pending)
    authorizations.append(approved)
    cao_v2 = governed(
        30,
        "CommercialActionOpportunity",
        revision=2,
        supersedes=cao_v1.revision_ref,
    )
    objects.append(cao_v2)

    assert authorizations.list_for_cao(cao_v1.revision_ref) == (pending, approved)
    assert authorizations.current_state(cao_v1.revision_ref).state is (
        HumanAuthorizationState.APPROVED
    )
    assert authorizations.current_state(cao_v2.revision_ref) is None


def test_audit_repository_records_every_audit_family(db_session: Session) -> None:
    object_ref = governed(40, "CommercialActionOpportunity").revision_ref
    audit = AuditRepository(db_session)
    audit.append_agent_run(
        AgentRun(
            run_id="RUN-AUDIT",
            agent_name="Evidence Intelligence",
            prompt_version="v1",
            model_config_id="fake",
            input_revision_refs=(object_ref,),
            status=RunStatus.SUCCEEDED,
            started_at=NOW,
            completed_at=NOW,
        )
    )
    audit.append_workflow_transition(
        WorkflowTransition(
            transition_id="TRANSITION-AUDIT",
            decision_cycle_ref=object_ref,
            from_state=CycleWorkflowState.DRAFT,
            to_state=CycleWorkflowState.INPUTS_READY,
            trigger="inputs supplied",
            actor=SYSTEM,
            object_refs=(object_ref,),
            occurred_at=NOW,
        )
    )
    audit.append_material_impact(
        MaterialImpactDecision(
            decision_id="MATERIAL-AUDIT",
            changed_ref=object_ref,
            dependent_ref=object_ref,
            materially_affected=False,
            rationale="no dependency change",
            decided_by=SYSTEM,
            policy_version="v1",
            decided_at=NOW,
        )
    )
    audit.append_execution_decision(
        ExternalExecutionEligibilityDecision(
            decision_id="EXECUTION-AUDIT",
            cao_revision_ref=object_ref,
            eligible=False,
            reasons=("external execution disabled",),
            policy_version="v1",
            decided_at=NOW,
        )
    )
    audit.append_conformity_result(
        ConformityCaseResult(
            case_id="C01",
            input_fixture_version="v1",
            input_digest="digest",
            actual_output_refs=(object_ref,),
            expected_rule_refs=("Stage15.C01",),
            status=ConformityStatus.PASS,
            material_differences=(),
            trace_refs=(),
            started_at=NOW,
            completed_at=NOW,
            code_version="dev",
            prompt_versions={},
            model_config_id="fake",
        )
    )

    for row_type in (
        AgentRunRow,
        WorkflowTransitionRow,
        MaterialImpactDecisionRow,
        ExternalExecutionDecisionRow,
        ConformityCaseResultRow,
    ):
        assert db_session.scalar(select(func.count()).select_from(row_type)) == 1


def test_agent_run_audit_allows_one_started_to_terminal_transition(
    db_session: Session,
) -> None:
    audit = AuditRepository(db_session)
    started = AgentRun(
        run_id="RUN-LIFECYCLE",
        agent_name="market_discovery",
        prompt_version="1.0.0",
        model_config_id="fake-agent-runner-v1",
        input_revision_refs=(),
        status=RunStatus.STARTED,
        started_at=NOW,
    )
    audit.append_agent_run(started)
    completed = started.model_copy(
        update={"status": RunStatus.SUCCEEDED, "completed_at": NOW, "usage_metadata": {}}
    )
    audit.finalize_agent_run(completed)
    row = db_session.get(AgentRunRow, "RUN-LIFECYCLE")
    assert row is not None
    assert row.status == RunStatus.SUCCEEDED.value
    with pytest.raises(PersistenceError, match="only a STARTED"):
        audit.finalize_agent_run(completed)


def test_unit_of_work_commits_and_rolls_back(migrated_engine: Engine) -> None:
    factory = create_session_factory(migrated_engine)
    committed = governed(50, "OfferProfile")
    with UnitOfWork(factory) as uow:
        uow.objects.append(committed)

    with factory() as session:
        assert (
            GovernedObjectRepository(session).get_current(committed.object_id, GovernedObject)
            == committed
        )

    rolled_back = governed(51, "OfferProfile")
    with pytest.raises(RuntimeError, match="force rollback"), UnitOfWork(factory) as uow:
        uow.objects.append(rolled_back)
        raise RuntimeError("force rollback")

    with factory() as session:
        assert (
            GovernedObjectRepository(session).get_current(rolled_back.object_id, GovernedObject)
            is None
        )
