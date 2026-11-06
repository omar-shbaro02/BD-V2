"""Offer, decision-cycle, capacity, and discovery contracts."""

from datetime import date
from decimal import Decimal

from pydantic import Field, model_validator

from vai_bd.domain.enums import DecisionCycleStatus, EffortUnit
from vai_bd.domain.envelopes import GovernedObject
from vai_bd.domain.refs import NonEmptyStr, ObjectRevisionRef, SourceRef


class OfferProfile(GovernedObject):
    name: NonEmptyStr
    problem_statement: NonEmptyStr
    intended_buyer_roles: tuple[NonEmptyStr, ...] = Field(min_length=1)
    fit_dimensions: tuple[NonEmptyStr, ...] = Field(min_length=1)
    known_exclusions: tuple[NonEmptyStr, ...] = ()
    version: NonEmptyStr


class DecisionCycleContext(GovernedObject):
    offer_ref: ObjectRevisionRef
    target_market_boundary: NonEmptyStr
    segment_filters: tuple[NonEmptyStr, ...] = ()
    exclusions: tuple[NonEmptyStr, ...] = ()
    effective_date: date
    operator_ref: ObjectRevisionRef
    status: DecisionCycleStatus


class CapacityEnvelope(GovernedObject):
    decision_cycle_ref: ObjectRevisionRef
    usable_time: Decimal = Field(gt=0)
    unit: EffortUnit
    planning_horizon: NonEmptyStr
    max_meaningful_concurrent_pursuits: int = Field(gt=0)
    fixed_commitments: Decimal = Field(default=Decimal("0"), ge=0)
    review_trigger: NonEmptyStr
    effective_date: date

    @model_validator(mode="after")
    def commitments_cannot_exceed_capacity(self) -> "CapacityEnvelope":
        if self.fixed_commitments > self.usable_time:
            raise ValueError("fixed commitments cannot exceed usable time")
        return self


class CandidateUniverseCoverageState(GovernedObject):
    decision_cycle_ref: ObjectRevisionRef
    coverage_basis: NonEmptyStr
    coverage_limitations: tuple[NonEmptyStr, ...]
    candidate_refs: tuple[ObjectRevisionRef, ...]
    added_candidates: tuple[ObjectRevisionRef, ...] = ()
    removed_candidates: tuple[ObjectRevisionRef, ...] = ()
    coverage_status: NonEmptyStr


class CompanyCandidate(GovernedObject):
    universe_ref: ObjectRevisionRef
    company_name: NonEmptyStr
    market_presence_claims: tuple[NonEmptyStr, ...] = Field(min_length=1)
    segment_claims: tuple[NonEmptyStr, ...] = Field(min_length=1)
    source_refs: tuple[SourceRef, ...] = Field(min_length=1)
    candidate_status: NonEmptyStr
