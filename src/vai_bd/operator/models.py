"""Read-only presentation contracts for the minimal operator view."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from vai_bd.domain.refs import ImmutableModel, NonEmptyStr, ObjectRevisionRef


class OperatorCycleSummary(ImmutableModel):
    cycle_id: UUID
    cycle_ref: ObjectRevisionRef
    offer_name: NonEmptyStr
    market_boundary: NonEmptyStr
    effective_date: date
    workflow_state: NonEmptyStr
    opportunity_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)


class OperatorCycleList(ImmutableModel):
    cycles: tuple[OperatorCycleSummary, ...]


class CoveragePresentation(ImmutableModel):
    basis: NonEmptyStr
    status: NonEmptyStr
    limitations: tuple[str, ...] = ()


class CandidatePresentation(ImmutableModel):
    name: NonEmptyStr
    disposition: NonEmptyStr
    reason: NonEmptyStr
    evidence_summary: NonEmptyStr
    evidence_limitations: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    revision_label: NonEmptyStr
    freshness: NonEmptyStr


class ConfidencePresentation(ImmutableModel):
    claim: NonEmptyStr
    level: NonEmptyStr
    rationale: NonEmptyStr


class OpportunityPresentation(ImmutableModel):
    opportunity_ref: ObjectRevisionRef
    company_name: NonEmptyStr
    qualification: NonEmptyStr
    qualification_reason: NonEmptyStr
    fit: NonEmptyStr
    need: NonEmptyStr
    evidence_summary: NonEmptyStr
    confidences: tuple[ConfidencePresentation, ...]
    contradictions: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()
    pursuit_demand: NonEmptyStr
    revision_label: NonEmptyStr
    freshness: NonEmptyStr
    reassessment_warning: str | None = None


class PriorityPresentation(ImmutableModel):
    opportunity_ref: ObjectRevisionRef
    position: NonEmptyStr
    reason: NonEmptyStr


class AllocationPresentation(ImmutableModel):
    opportunity_ref: ObjectRevisionRef
    tier: NonEmptyStr
    capacity_effect: NonEmptyStr
    reason: NonEmptyStr


class ActionPresentation(ImmutableModel):
    opportunity_ref: ObjectRevisionRef
    action_type: NonEmptyStr
    next_action: NonEmptyStr
    readiness: NonEmptyStr
    readiness_reason: NonEmptyStr
    authorization: NonEmptyStr
    authorization_reason: NonEmptyStr


class OperatorCycleView(ImmutableModel):
    cycle_id: UUID
    cycle_ref: ObjectRevisionRef
    offer_name: NonEmptyStr
    offer_summary: NonEmptyStr
    market_boundary: NonEmptyStr
    effective_date: date
    workflow_state: NonEmptyStr
    capacity_available: Decimal = Field(ge=0)
    capacity_unit: NonEmptyStr
    planning_horizon: NonEmptyStr
    capacity_limit: int = Field(gt=0)
    coverage: CoveragePresentation
    candidates: tuple[CandidatePresentation, ...]
    opportunities: tuple[OpportunityPresentation, ...]
    priority: tuple[PriorityPresentation, ...]
    allocation: tuple[AllocationPresentation, ...]
    actions: tuple[ActionPresentation, ...]
    warnings: tuple[str, ...] = ()
