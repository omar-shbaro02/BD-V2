"""Append-only repositories for governed revisions and human decisions."""

from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session

from vai_bd.domain.audit import (
    AgentRun,
    ConformityCaseResult,
    ExternalExecutionEligibilityDecision,
    MaterialImpactDecision,
    WorkflowTransition,
)
from vai_bd.domain.authorization import (
    HumanAuthorizationCurrentState,
    HumanAuthorizationEvent,
)
from vai_bd.domain.enums import HumanAuthorizationState, ObjectValidity, RunStatus
from vai_bd.domain.envelopes import GovernedObject
from vai_bd.domain.portfolio import (
    CanonicalPairwiseComparison,
    QualifiedUniverseSnapshot,
)
from vai_bd.domain.refs import ActorRef, ObjectRevisionRef
from vai_bd.persistence.orm import (
    ActorRow,
    AgentRunRow,
    CanonicalComparisonRow,
    ConformityCaseResultRow,
    DependencyRow,
    DomainPayloadRow,
    ExternalExecutionDecisionRow,
    HumanAuthorizationEventRow,
    MaterialImpactDecisionRow,
    ObjectIdentityRow,
    ObjectRevisionRow,
    SnapshotMemberRow,
    SupersessionRow,
    WorkflowTransitionRow,
)

TGoverned = TypeVar("TGoverned", bound=GovernedObject)


class PersistenceError(RuntimeError):
    """Base persistence contract error."""


class RevisionConflictError(PersistenceError):
    """The proposed revision does not follow the locked current revision."""


class MissingRevisionError(PersistenceError):
    """An exact referenced revision does not exist."""


class GovernedObjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _store_actor(self, actor: ActorRef) -> None:
        existing = self.session.get(ActorRow, actor.actor_id)
        if existing is None:
            self.session.add(
                ActorRow(
                    actor_id=actor.actor_id,
                    actor_kind=actor.actor_kind.value,
                    display_name=actor.display_name,
                )
            )
            self.session.flush()
        elif existing.actor_kind != actor.actor_kind.value:
            raise PersistenceError("actor kind cannot change")

    def _revision_row(self, ref: ObjectRevisionRef) -> ObjectRevisionRow | None:
        return self.session.get(ObjectRevisionRow, (ref.object_id, ref.revision))

    def require_revision(self, ref: ObjectRevisionRef) -> ObjectRevisionRow:
        row = self._revision_row(ref)
        if row is None or row.object_type != ref.object_type:
            raise MissingRevisionError(f"missing exact revision {ref}")
        return row

    def append(self, value: TGoverned) -> TGoverned:
        if value.validity is not ObjectValidity.CURRENT:
            raise RevisionConflictError("newly appended revisions must begin CURRENT")
        self._store_actor(value.created_by)
        identity = self.session.get(ObjectIdentityRow, value.object_id)
        active = self.session.scalar(
            select(ObjectRevisionRow)
            .where(
                ObjectRevisionRow.object_id == value.object_id,
                ObjectRevisionRow.validity != ObjectValidity.SUPERSEDED.value,
            )
            .with_for_update()
        )

        if identity is None:
            if value.revision != 1 or value.supersedes_ref is not None:
                raise RevisionConflictError("a new identity must begin at revision 1")
            identity = ObjectIdentityRow(
                object_id=value.object_id,
                object_type=value.object_type,
                created_at=value.created_at,
            )
            self.session.add(identity)
            self.session.flush()
        else:
            if identity.object_type != value.object_type:
                raise RevisionConflictError("object type cannot change across revisions")
            if active is None:
                raise RevisionConflictError("existing identity has no active revision")
            expected = ObjectRevisionRef(
                object_id=active.object_id,
                object_type=active.object_type,
                revision=active.revision,
            )
            if value.supersedes_ref != expected or value.revision != active.revision + 1:
                raise RevisionConflictError("successor must supersede the exact current revision")
            active.validity = ObjectValidity.SUPERSEDED.value

        for dependency in (*value.derived_from, *value.dependencies):
            self.require_revision(dependency)

        row = ObjectRevisionRow(
            object_id=value.object_id,
            revision=value.revision,
            object_type=value.object_type,
            validity=value.validity.value,
            created_at=value.created_at,
            created_by=value.created_by.actor_id,
            effective_at=value.effective_at,
            reassessment_trigger=value.reassessment_trigger,
            reassessment_reason=value.reassessment_reason,
        )
        self.session.add(row)
        self.session.flush()
        self.session.add(
            DomainPayloadRow(
                object_id=value.object_id,
                revision=value.revision,
                schema_name=type(value).__name__,
                payload=value.model_dump(mode="json"),
            )
        )
        for edge_kind, refs in (
            ("DERIVED_FROM", value.derived_from),
            ("DEPENDENCY", value.dependencies),
        ):
            for source in refs:
                self.session.add(
                    DependencyRow(
                        dependent_object_id=value.object_id,
                        dependent_revision=value.revision,
                        source_object_id=source.object_id,
                        source_revision=source.revision,
                        edge_kind=edge_kind,
                    )
                )
        if value.supersedes_ref is not None:
            self.session.add(
                SupersessionRow(
                    object_id=value.object_id,
                    predecessor_revision=value.supersedes_ref.revision,
                    successor_revision=value.revision,
                )
            )
        self.session.flush()
        return value

    def get_exact(self, ref: ObjectRevisionRef, model_type: type[TGoverned]) -> TGoverned:
        revision_row = self.require_revision(ref)
        payload = self.session.get(DomainPayloadRow, (ref.object_id, ref.revision))
        if payload is None or payload.schema_name != model_type.__name__:
            raise MissingRevisionError(f"missing {model_type.__name__} payload for {ref}")
        reconstructed = payload.payload | {
            "validity": revision_row.validity,
            "reassessment_trigger": revision_row.reassessment_trigger,
            "reassessment_reason": revision_row.reassessment_reason,
        }
        return model_type.model_validate(reconstructed)

    def mark_reassessment_required(
        self,
        ref: ObjectRevisionRef,
        *,
        trigger: str,
        reason: str,
    ) -> None:
        if not trigger.strip() or not reason.strip():
            raise PersistenceError("reassessment requires a non-empty trigger and reason")
        row = self.require_revision(ref)
        if row.validity != ObjectValidity.CURRENT.value:
            raise RevisionConflictError("only a current revision may require reassessment")
        row.validity = ObjectValidity.REASSESSMENT_REQUIRED.value
        row.reassessment_trigger = trigger
        row.reassessment_reason = reason
        self.session.flush()

    def get_current(self, object_id: UUID, model_type: type[TGoverned]) -> TGoverned | None:
        row = self.session.scalar(
            select(ObjectRevisionRow).where(
                ObjectRevisionRow.object_id == object_id,
                ObjectRevisionRow.validity == ObjectValidity.CURRENT.value,
            )
        )
        if row is None:
            return None
        return self.get_exact(
            ObjectRevisionRef(
                object_id=row.object_id,
                object_type=row.object_type,
                revision=row.revision,
            ),
            model_type,
        )

    def dependencies_of(self, ref: ObjectRevisionRef) -> tuple[ObjectRevisionRef, ...]:
        self.require_revision(ref)
        rows = self.session.scalars(
            select(DependencyRow).where(
                DependencyRow.dependent_object_id == ref.object_id,
                DependencyRow.dependent_revision == ref.revision,
            )
        ).all()
        return tuple(self._ref_for(row.source_object_id, row.source_revision) for row in rows)

    def dependents_of(self, ref: ObjectRevisionRef) -> tuple[ObjectRevisionRef, ...]:
        self.require_revision(ref)
        rows = self.session.scalars(
            select(DependencyRow).where(
                DependencyRow.source_object_id == ref.object_id,
                DependencyRow.source_revision == ref.revision,
            )
        ).all()
        return tuple(self._ref_for(row.dependent_object_id, row.dependent_revision) for row in rows)

    def _ref_for(self, object_id: UUID, revision: int) -> ObjectRevisionRef:
        row = self.session.get(ObjectRevisionRow, (object_id, revision))
        if row is None:
            raise MissingRevisionError("dependency edge references a missing revision")
        return ObjectRevisionRef(
            object_id=object_id,
            object_type=row.object_type,
            revision=revision,
        )


class SnapshotRepository:
    def __init__(self, session: Session, objects: GovernedObjectRepository) -> None:
        self.session = session
        self.objects = objects

    def append(self, snapshot: QualifiedUniverseSnapshot) -> QualifiedUniverseSnapshot:
        for member in snapshot.opportunity_case_revision_refs:
            self.objects.require_revision(member)
        self.objects.append(snapshot)
        self.session.add_all(
            SnapshotMemberRow(
                snapshot_id=snapshot.object_id,
                snapshot_revision=snapshot.revision,
                opportunity_id=member.object_id,
                opportunity_revision=member.revision,
            )
            for member in snapshot.opportunity_case_revision_refs
        )
        self.session.flush()
        return snapshot

    def members(self, snapshot_ref: ObjectRevisionRef) -> tuple[ObjectRevisionRef, ...]:
        rows = self.session.scalars(
            select(SnapshotMemberRow).where(
                SnapshotMemberRow.snapshot_id == snapshot_ref.object_id,
                SnapshotMemberRow.snapshot_revision == snapshot_ref.revision,
            )
        ).all()
        return tuple(
            self.objects._ref_for(row.opportunity_id, row.opportunity_revision) for row in rows
        )


class ComparisonRepository:
    def __init__(self, session: Session, objects: GovernedObjectRepository) -> None:
        self.session = session
        self.objects = objects

    def append(self, comparison: CanonicalPairwiseComparison) -> CanonicalPairwiseComparison:
        members = set(
            SnapshotRepository(self.session, self.objects).members(comparison.snapshot_ref)
        )
        pair = {
            comparison.subject_opportunity_revision,
            comparison.comparator_opportunity_revision,
        }
        if not pair.issubset(members):
            raise PersistenceError("both comparison opportunities must belong to the snapshot")
        ordered = sorted(
            pair,
            key=lambda item: (str(item.object_id), item.revision),
        )
        self.objects.append(comparison)
        self.session.add(
            CanonicalComparisonRow(
                comparison_id=comparison.object_id,
                comparison_revision=comparison.revision,
                snapshot_id=comparison.snapshot_ref.object_id,
                snapshot_revision=comparison.snapshot_ref.revision,
                first_opportunity_id=ordered[0].object_id,
                first_opportunity_revision=ordered[0].revision,
                second_opportunity_id=ordered[1].object_id,
                second_opportunity_revision=ordered[1].revision,
                relationship=comparison.relationship.value,
                material_reason=comparison.material_reason,
            )
        )
        self.session.flush()
        return comparison


class AuthorizationRepository:
    def __init__(self, session: Session, objects: GovernedObjectRepository) -> None:
        self.session = session
        self.objects = objects

    def append(self, event: HumanAuthorizationEvent) -> HumanAuthorizationEvent:
        self.objects.require_revision(event.cao_revision_ref)
        self.objects._store_actor(event.requested_human_authority_ref)
        if event.actual_deciding_human_ref is not None:
            self.objects._store_actor(event.actual_deciding_human_ref)
        self.session.add(
            HumanAuthorizationEventRow(
                authorization_id=event.authorization_id,
                cao_object_id=event.cao_revision_ref.object_id,
                cao_revision=event.cao_revision_ref.revision,
                state=event.state.value,
                requested_human_id=event.requested_human_authority_ref.actor_id,
                actual_deciding_human_id=(
                    event.actual_deciding_human_ref.actor_id
                    if event.actual_deciding_human_ref
                    else None
                ),
                decision_timestamp=event.decision_timestamp,
                authorized_action=event.authorized_action,
                authorized_scope=(
                    event.authorized_scope.model_dump(mode="json")
                    if event.authorized_scope
                    else None
                ),
                rationale=event.rationale,
                recorded_at=datetime.now(UTC),
            )
        )
        self.session.flush()
        return event

    def list_for_cao(self, cao_ref: ObjectRevisionRef) -> tuple[HumanAuthorizationEvent, ...]:
        rows = self.session.scalars(self._events_query(cao_ref)).all()
        adapter = TypeAdapter(HumanAuthorizationEvent)
        return tuple(adapter.validate_python(self._event_payload(row)) for row in rows)

    def current_state(self, cao_ref: ObjectRevisionRef) -> HumanAuthorizationCurrentState | None:
        row = self.session.scalar(
            self._events_query(cao_ref)
            .order_by(None)
            .order_by(HumanAuthorizationEventRow.sequence.desc())
        )
        if row is None:
            return None
        return HumanAuthorizationCurrentState(
            cao_revision_ref=cao_ref,
            state=HumanAuthorizationState(row.state),
            latest_event_id=row.authorization_id,
        )

    @staticmethod
    def _events_query(cao_ref: ObjectRevisionRef) -> Select[HumanAuthorizationEventRow]:
        return (
            select(HumanAuthorizationEventRow)
            .where(
                and_(
                    HumanAuthorizationEventRow.cao_object_id == cao_ref.object_id,
                    HumanAuthorizationEventRow.cao_revision == cao_ref.revision,
                )
            )
            .order_by(HumanAuthorizationEventRow.sequence)
        )

    def _event_payload(self, row: HumanAuthorizationEventRow) -> dict[str, object]:
        requested = self.session.get(ActorRow, row.requested_human_id)
        deciding = (
            self.session.get(ActorRow, row.actual_deciding_human_id)
            if row.actual_deciding_human_id
            else None
        )
        if requested is None:
            raise PersistenceError("authorization requester actor is missing")
        return {
            "authorization_id": row.authorization_id,
            "cao_revision_ref": self.objects._ref_for(row.cao_object_id, row.cao_revision),
            "state": row.state,
            "requested_human_authority_ref": self._actor_ref(requested),
            "actual_deciding_human_ref": self._actor_ref(deciding) if deciding else None,
            "decision_timestamp": row.decision_timestamp,
            "authorized_action": row.authorized_action,
            "authorized_scope": row.authorized_scope,
            "rationale": row.rationale,
        }

    @staticmethod
    def _actor_ref(row: ActorRow) -> dict[str, object]:
        return {
            "actor_id": row.actor_id,
            "actor_kind": row.actor_kind,
            "display_name": row.display_name,
        }


class AuditRepository:
    """Append-only run, workflow, materiality, execution, and conformity audit."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def append_agent_run(self, run: AgentRun) -> AgentRun:
        self.session.add(
            AgentRunRow(
                run_id=run.run_id,
                agent_name=run.agent_name,
                prompt_version=run.prompt_version,
                model_config=run.model_config_id,
                input_revision_refs=[
                    ref.model_dump(mode="json") for ref in run.input_revision_refs
                ],
                output_revision_refs=[
                    ref.model_dump(mode="json") for ref in run.output_revision_refs
                ],
                openai_trace_ref=run.openai_trace_ref,
                status=run.status.value,
                error=run.error,
                started_at=run.started_at,
                completed_at=run.completed_at,
                usage_metadata=run.usage_metadata,
            )
        )
        self.session.flush()
        return run

    def finalize_agent_run(self, run: AgentRun) -> AgentRun:
        row = self.session.get(AgentRunRow, run.run_id)
        if row is None:
            raise PersistenceError("agent run does not exist")
        if row.status != "STARTED" or run.status.value == "STARTED":
            raise PersistenceError("only a STARTED agent run may transition to terminal state")
        immutable_fields_match = (
            row.agent_name == run.agent_name
            and row.prompt_version == run.prompt_version
            and row.model_config == run.model_config_id
            and row.started_at == run.started_at
            and row.input_revision_refs
            == [ref.model_dump(mode="json") for ref in run.input_revision_refs]
        )
        if not immutable_fields_match:
            raise PersistenceError("agent run immutable audit fields cannot change")
        row.output_revision_refs = [ref.model_dump(mode="json") for ref in run.output_revision_refs]
        row.openai_trace_ref = run.openai_trace_ref
        row.status = run.status.value
        row.error = run.error
        row.completed_at = run.completed_at
        row.usage_metadata = run.usage_metadata
        self.session.flush()
        return run

    def append_workflow_transition(self, transition: WorkflowTransition) -> WorkflowTransition:
        self.session.add(
            WorkflowTransitionRow(
                transition_id=transition.transition_id,
                payload=transition.model_dump(mode="json"),
                occurred_at=transition.occurred_at,
            )
        )
        self.session.flush()
        return transition

    def workflow_transitions_for(
        self, cycle_ref: ObjectRevisionRef
    ) -> tuple[WorkflowTransition, ...]:
        rows = self.session.scalars(
            select(WorkflowTransitionRow).order_by(WorkflowTransitionRow.occurred_at)
        ).all()
        adapter = TypeAdapter(WorkflowTransition)
        return tuple(
            adapter.validate_python(row.payload)
            for row in rows
            if row.payload.get("decision_cycle_ref") == cycle_ref.model_dump(mode="json")
        )

    def get_agent_run(self, run_id: str) -> AgentRun | None:
        row = self.session.get(AgentRunRow, run_id)
        if row is None:
            return None
        return AgentRun(
            run_id=row.run_id,
            agent_name=row.agent_name,
            prompt_version=row.prompt_version,
            model_config_id=row.model_config,
            input_revision_refs=tuple(
                ObjectRevisionRef.model_validate(ref) for ref in row.input_revision_refs
            ),
            output_revision_refs=tuple(
                ObjectRevisionRef.model_validate(ref) for ref in row.output_revision_refs
            ),
            openai_trace_ref=row.openai_trace_ref,
            status=RunStatus(row.status),
            error=row.error,
            started_at=row.started_at,
            completed_at=row.completed_at,
            usage_metadata={key: int(value) for key, value in row.usage_metadata.items()},
        )

    def append_material_impact(self, decision: MaterialImpactDecision) -> MaterialImpactDecision:
        self.session.add(
            MaterialImpactDecisionRow(
                decision_id=decision.decision_id,
                payload=decision.model_dump(mode="json"),
                decided_at=decision.decided_at,
            )
        )
        self.session.flush()
        return decision

    def append_execution_decision(
        self, decision: ExternalExecutionEligibilityDecision
    ) -> ExternalExecutionEligibilityDecision:
        self.session.add(
            ExternalExecutionDecisionRow(
                decision_id=decision.decision_id,
                payload=decision.model_dump(mode="json"),
                decided_at=decision.decided_at,
            )
        )
        self.session.flush()
        return decision

    def append_conformity_result(self, result: ConformityCaseResult) -> ConformityCaseResult:
        self.session.add(
            ConformityCaseResultRow(
                case_id=result.case_id,
                input_fixture_version=result.input_fixture_version,
                status=result.status.value,
                payload=result.model_dump(mode="json"),
                completed_at=result.completed_at,
            )
        )
        self.session.flush()
        return result
