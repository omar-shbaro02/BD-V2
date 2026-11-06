"""Separated opportunity judgments and lifecycle contracts."""

from decimal import Decimal

from pydantic import Field, model_validator

from vai_bd.domain.enums import (
    ConfidenceLevel,
    EffortUnit,
    NeedStatus,
    OpportunityLifecycleState,
    QualificationOutcomeType,
)
from vai_bd.domain.envelopes import GovernedObject
from vai_bd.domain.refs import NonEmptyStr, ObjectRevisionRef


class ConfidenceAssessment(GovernedObject):
    claim_ref: ObjectRevisionRef
    level: ConfidenceLevel
    rationale: NonEmptyStr
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)


class CompanyOfferFit(GovernedObject):
    candidate_ref: ObjectRevisionRef
    offer_ref: ObjectRevisionRef
    judgment: NonEmptyStr
    rationale: NonEmptyStr
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)
    claim_confidence_ref: ObjectRevisionRef


class NeedHypothesis(GovernedObject):
    candidate_ref: ObjectRevisionRef
    hypothesis: NonEmptyStr
    status: NeedStatus
    rationale: NonEmptyStr
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)
    claim_confidence_ref: ObjectRevisionRef


class DecisionOwnerHypothesis(GovernedObject):
    candidate_ref: ObjectRevisionRef
    role_hypothesis: NonEmptyStr
    named_person_ref: ObjectRevisionRef | None = None
    rationale: NonEmptyStr
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)
    claim_confidence_ref: ObjectRevisionRef


class ContactabilityAssessment(GovernedObject):
    candidate_ref: ObjectRevisionRef
    assessment: NonEmptyStr
    known_paths: tuple[NonEmptyStr, ...]
    constraints: tuple[NonEmptyStr, ...]
    rationale: NonEmptyStr
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)
    claim_confidence_ref: ObjectRevisionRef


class QualificationOutcome(GovernedObject):
    candidate_ref: ObjectRevisionRef
    outcome: QualificationOutcomeType
    rationale: NonEmptyStr
    investigation_action: str | None = None
    material_review_reason: str | None = None

    @model_validator(mode="after")
    def require_outcome_specific_explanation(self) -> "QualificationOutcome":
        if (
            self.outcome is QualificationOutcomeType.FURTHER_INVESTIGATION_REQUIRED
            and not self.investigation_action
        ):
            raise ValueError("further investigation requires a specific action")
        if (
            self.outcome is QualificationOutcomeType.INDETERMINATE_PENDING_MATERIAL_REVIEW
            and not self.material_review_reason
        ):
            raise ValueError("indeterminate qualification requires a material-review reason")
        return self


class CommercialOpportunityCase(GovernedObject):
    candidate_ref: ObjectRevisionRef
    offer_ref: ObjectRevisionRef
    fit_ref: ObjectRevisionRef
    need_ref: ObjectRevisionRef
    decision_owner_ref: ObjectRevisionRef
    contactability_ref: ObjectRevisionRef
    qualification_ref: ObjectRevisionRef
    commercial_rationale: NonEmptyStr
    material_uncertainties: tuple[NonEmptyStr, ...]


class PursuitDemand(GovernedObject):
    opportunity_case_ref: ObjectRevisionRef
    next_action_description: NonEmptyStr
    estimated_effort: Decimal = Field(gt=0)
    unit: EffortUnit
    smaller_credible_action_available: bool
    rationale: NonEmptyStr


class OpportunityState(GovernedObject):
    opportunity_case_ref: ObjectRevisionRef
    state: OpportunityLifecycleState
    rationale: NonEmptyStr
