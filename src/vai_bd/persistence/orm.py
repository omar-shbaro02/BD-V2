"""Relational persistence schema for governed state and audit history."""

from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: ClassVar[dict[object, object]] = {dict[str, Any]: JSONB}


class ActorRow(Base):
    __tablename__ = "actors"

    actor_id: Mapped[UUID] = mapped_column(primary_key=True)
    actor_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)


class ObjectIdentityRow(Base):
    __tablename__ = "object_identities"

    object_id: Mapped[UUID] = mapped_column(primary_key=True)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ObjectRevisionRow(Base):
    __tablename__ = "object_revisions"

    object_id: Mapped[UUID] = mapped_column(
        ForeignKey("object_identities.object_id", ondelete="RESTRICT"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    validity: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("actors.actor_id", ondelete="RESTRICT"), nullable=False
    )
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reassessment_trigger: Mapped[str | None] = mapped_column(Text)
    reassessment_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        PrimaryKeyConstraint("object_id", "revision"),
        Index(
            "uq_object_revisions_one_active",
            "object_id",
            unique=True,
            postgresql_where=text("validity IN ('CURRENT', 'REASSESSMENT_REQUIRED')"),
        ),
    )


class DependencyRow(Base):
    __tablename__ = "object_dependencies"

    dependent_object_id: Mapped[UUID]
    dependent_revision: Mapped[int]
    source_object_id: Mapped[UUID]
    source_revision: Mapped[int]
    edge_kind: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint(
            "dependent_object_id",
            "dependent_revision",
            "source_object_id",
            "source_revision",
            "edge_kind",
        ),
        ForeignKeyConstraint(
            ["dependent_object_id", "dependent_revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["source_object_id", "source_revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
            ondelete="RESTRICT",
        ),
        Index("ix_object_dependencies_source", "source_object_id", "source_revision"),
    )


class SupersessionRow(Base):
    __tablename__ = "object_supersessions"

    object_id: Mapped[UUID]
    predecessor_revision: Mapped[int]
    successor_revision: Mapped[int]

    __table_args__ = (
        PrimaryKeyConstraint("object_id", "predecessor_revision", "successor_revision"),
        UniqueConstraint(
            "object_id",
            "predecessor_revision",
            name="uq_object_supersessions_predecessor",
        ),
        UniqueConstraint(
            "object_id",
            "successor_revision",
            name="uq_object_supersessions_successor",
        ),
        ForeignKeyConstraint(
            ["object_id", "predecessor_revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
            name="fk_object_supersessions_predecessor",
        ),
        ForeignKeyConstraint(
            ["object_id", "successor_revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
            name="fk_object_supersessions_successor",
        ),
    )


class DomainPayloadRow(Base):
    __tablename__ = "domain_payloads"

    object_id: Mapped[UUID]
    revision: Mapped[int]
    schema_name: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("object_id", "revision"),
        ForeignKeyConstraint(
            ["object_id", "revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
            ondelete="CASCADE",
        ),
    )


class CandidateUniverseMemberRow(Base):
    __tablename__ = "candidate_universe_members"

    universe_id: Mapped[UUID]
    universe_revision: Mapped[int]
    candidate_id: Mapped[UUID]
    candidate_revision: Mapped[int]
    disposition: Mapped[str] = mapped_column(String(30), nullable=False, default="INCLUDED")
    reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        PrimaryKeyConstraint(
            "universe_id", "universe_revision", "candidate_id", "candidate_revision"
        ),
        ForeignKeyConstraint(
            ["universe_id", "universe_revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["candidate_id", "candidate_revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
        ),
    )


class SnapshotMemberRow(Base):
    __tablename__ = "snapshot_members"

    snapshot_id: Mapped[UUID]
    snapshot_revision: Mapped[int]
    opportunity_id: Mapped[UUID]
    opportunity_revision: Mapped[int]

    __table_args__ = (
        PrimaryKeyConstraint(
            "snapshot_id", "snapshot_revision", "opportunity_id", "opportunity_revision"
        ),
        ForeignKeyConstraint(
            ["snapshot_id", "snapshot_revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["opportunity_id", "opportunity_revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
        ),
    )


class CanonicalComparisonRow(Base):
    __tablename__ = "canonical_comparisons"

    comparison_id: Mapped[UUID]
    comparison_revision: Mapped[int]
    snapshot_id: Mapped[UUID]
    snapshot_revision: Mapped[int]
    first_opportunity_id: Mapped[UUID]
    first_opportunity_revision: Mapped[int]
    second_opportunity_id: Mapped[UUID]
    second_opportunity_revision: Mapped[int]
    relationship: Mapped[str] = mapped_column(String(30), nullable=False)
    material_reason: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("comparison_id", "comparison_revision"),
        UniqueConstraint(
            "snapshot_id",
            "snapshot_revision",
            "first_opportunity_id",
            "first_opportunity_revision",
            "second_opportunity_id",
            "second_opportunity_revision",
            name="uq_canonical_comparison_pair",
        ),
        ForeignKeyConstraint(
            ["comparison_id", "comparison_revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["snapshot_id", "snapshot_revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
        ),
    )


class AllocationMemberRow(Base):
    __tablename__ = "allocation_members"

    allocation_id: Mapped[UUID]
    allocation_revision: Mapped[int]
    opportunity_id: Mapped[UUID]
    opportunity_revision: Mapped[int]
    tier: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    effort: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))

    __table_args__ = (
        PrimaryKeyConstraint(
            "allocation_id", "allocation_revision", "opportunity_id", "opportunity_revision"
        ),
        ForeignKeyConstraint(
            ["allocation_id", "allocation_revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["opportunity_id", "opportunity_revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
        ),
    )


class HumanAuthorizationEventRow(Base):
    __tablename__ = "human_authorization_events"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    authorization_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    cao_object_id: Mapped[UUID]
    cao_revision: Mapped[int]
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    requested_human_id: Mapped[UUID] = mapped_column(ForeignKey("actors.actor_id"), nullable=False)
    actual_deciding_human_id: Mapped[UUID | None] = mapped_column(ForeignKey("actors.actor_id"))
    decision_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    authorized_action: Mapped[str | None] = mapped_column(Text)
    authorized_scope: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["cao_object_id", "cao_revision"],
            ["object_revisions.object_id", "object_revisions.revision"],
        ),
        Index("ix_human_authorization_cao", "cao_object_id", "cao_revision", "sequence"),
    )


class AgentRunRow(Base):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_config: Mapped[str] = mapped_column(String(100), nullable=False)
    input_revision_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    output_revision_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    openai_trace_ref: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usage_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class WorkflowTransitionRow(Base):
    __tablename__ = "workflow_transitions"

    transition_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MaterialImpactDecisionRow(Base):
    __tablename__ = "material_impact_decisions"

    decision_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExternalExecutionDecisionRow(Base):
    __tablename__ = "external_execution_decisions"

    decision_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConformityCaseResultRow(Base):
    __tablename__ = "conformity_case_results"

    result_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(30), nullable=False)
    input_fixture_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_conformity_case_version", "case_id", "input_fixture_version"),)


class IdempotencyRecordRow(Base):
    __tablename__ = "idempotency_records"

    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    result_revision_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (PrimaryKeyConstraint("operation", "idempotency_key"),)
