"""Strict model-visible input and structured-output contracts for five specialists."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from vai_bd.domain.actions import ActionScope
from vai_bd.domain.enums import (
    ActionType,
    ComparisonRelationship,
    ConfidenceLevel,
    EffortUnit,
    EvidenceAdmissibility,
    EvidenceCurrentness,
    EvidenceDirectness,
    NeedStatus,
    QualificationOutcomeType,
)
from vai_bd.domain.refs import ImmutableModel, NonEmptyStr, ObjectRevisionRef, SourceRef


class SpecialistName(StrEnum):
    MARKET_DISCOVERY = "market_discovery"
    EVIDENCE_INTELLIGENCE = "evidence_intelligence"
    OPPORTUNITY_INTELLIGENCE = "opportunity_intelligence"
    PORTFOLIO_ALLOCATION = "portfolio_allocation"
    COMMERCIAL_ACTION = "commercial_action"


class UntrustedObservation(ImmutableModel):
    observation_id: NonEmptyStr
    content: NonEmptyStr
    source: SourceRef
    source_type: NonEmptyStr
    source_date: date | None = None
    provenance: NonEmptyStr
    restricted: bool = False


class AgentInput(ImmutableModel):
    exact_input_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def exact_refs_are_unique(self) -> "AgentInput":
        if len(self.exact_input_refs) != len(set(self.exact_input_refs)):
            raise ValueError("exact input revision references must be unique")
        return self


class MarketDiscoveryInput(AgentInput):
    decision_cycle_ref: ObjectRevisionRef
    offer_ref: ObjectRevisionRef
    target_market_boundary: NonEmptyStr
    segment_filters: tuple[NonEmptyStr, ...] = ()
    exclusions: tuple[NonEmptyStr, ...] = ()
    prior_universe_ref: ObjectRevisionRef | None = None
    prior_candidate_refs: tuple[ObjectRevisionRef, ...] = ()
    observations: tuple[UntrustedObservation, ...]
    exhaustive_coverage_supported: bool = False


class CandidateProposal(ImmutableModel):
    proposal_key: NonEmptyStr
    company_name: NonEmptyStr
    market_presence_claims: tuple[NonEmptyStr, ...] = Field(min_length=1)
    segment_claims: tuple[NonEmptyStr, ...] = Field(min_length=1)
    source_refs: tuple[SourceRef, ...] = Field(min_length=1)
    candidate_status: NonEmptyStr


class RemovedCandidateProposal(ImmutableModel):
    candidate_ref: ObjectRevisionRef
    reason: NonEmptyStr


class MarketDiscoveryOutput(ImmutableModel):
    referenced_input_refs: tuple[ObjectRevisionRef, ...]
    coverage_basis: NonEmptyStr
    coverage_limitations: tuple[NonEmptyStr, ...]
    coverage_status: NonEmptyStr
    claims_exhaustive_coverage: bool = False
    candidates: tuple[CandidateProposal, ...]
    added_candidate_keys: tuple[NonEmptyStr, ...] = ()
    removed_candidates: tuple[RemovedCandidateProposal, ...] = ()

    @model_validator(mode="after")
    def proposal_keys_are_consistent(self) -> "MarketDiscoveryOutput":
        keys = [candidate.proposal_key for candidate in self.candidates]
        if len(keys) != len(set(keys)):
            raise ValueError("candidate proposal keys must be unique")
        if not set(self.added_candidate_keys).issubset(keys):
            raise ValueError("added candidate keys must identify proposed candidates")
        return self


class EvidenceIntelligenceInput(AgentInput):
    candidate_ref: ObjectRevisionRef
    decision_cycle_ref: ObjectRevisionRef
    observations: tuple[UntrustedObservation, ...]
    prior_evidence_refs: tuple[ObjectRevisionRef, ...] = ()


class EvidenceProposal(ImmutableModel):
    proposal_key: NonEmptyStr
    claim_text: NonEmptyStr
    source: SourceRef
    source_type: NonEmptyStr
    source_date: date | None = None
    provenance: NonEmptyStr
    directness: EvidenceDirectness
    currentness: EvidenceCurrentness
    source_dependency_group: str | None = None
    contradicts_proposal_keys: tuple[NonEmptyStr, ...] = ()
    contradicts_existing_refs: tuple[ObjectRevisionRef, ...] = ()
    admissibility: EvidenceAdmissibility


class MissingEvidenceProposal(ImmutableModel):
    missing_claim_or_fact: NonEmptyStr
    why_material: NonEmptyStr
    investigation_action: NonEmptyStr


class ContradictionGroupProposal(ImmutableModel):
    group_key: NonEmptyStr
    evidence_proposal_keys: tuple[NonEmptyStr, ...] = Field(min_length=2)
    evidence_refs: tuple[ObjectRevisionRef, ...] = ()
    material_reason: NonEmptyStr


class SourceDependencyGroupProposal(ImmutableModel):
    group_key: NonEmptyStr
    evidence_proposal_keys: tuple[NonEmptyStr, ...] = Field(min_length=1)
    rationale: NonEmptyStr


class EvidenceIntelligenceOutput(ImmutableModel):
    referenced_input_refs: tuple[ObjectRevisionRef, ...]
    evidence_records: tuple[EvidenceProposal, ...]
    missing_evidence_flags: tuple[MissingEvidenceProposal, ...] = ()
    contradiction_groups: tuple[ContradictionGroupProposal, ...] = ()
    source_dependency_groups: tuple[SourceDependencyGroupProposal, ...] = ()

    @model_validator(mode="after")
    def proposal_links_exist(self) -> "EvidenceIntelligenceOutput":
        keys = [record.proposal_key for record in self.evidence_records]
        if len(keys) != len(set(keys)):
            raise ValueError("evidence proposal keys must be unique")
        known = set(keys)
        linked = {
            key for record in self.evidence_records for key in record.contradicts_proposal_keys
        }
        linked.update(
            key for group in self.contradiction_groups for key in group.evidence_proposal_keys
        )
        linked.update(
            key for group in self.source_dependency_groups for key in group.evidence_proposal_keys
        )
        if not linked.issubset(known):
            raise ValueError("evidence links must identify proposed evidence records")
        return self


class OpportunityIntelligenceInput(AgentInput):
    decision_cycle_ref: ObjectRevisionRef
    offer_ref: ObjectRevisionRef
    candidate_ref: ObjectRevisionRef
    gate_result_ref: ObjectRevisionRef
    gate_outcome: Literal["PROCEED"]
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)


class ConfidenceProposal(ImmutableModel):
    claim_key: NonEmptyStr
    level: ConfidenceLevel
    rationale: NonEmptyStr
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)


class FitProposal(ImmutableModel):
    judgment: NonEmptyStr
    rationale: NonEmptyStr
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)
    confidence_claim_key: NonEmptyStr


class NeedProposal(ImmutableModel):
    hypothesis: NonEmptyStr
    status: NeedStatus
    rationale: NonEmptyStr
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)
    confidence_claim_key: NonEmptyStr


class DecisionOwnerProposal(ImmutableModel):
    role_hypothesis: NonEmptyStr
    named_person_ref: ObjectRevisionRef | None = None
    rationale: NonEmptyStr
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)
    confidence_claim_key: NonEmptyStr


class ContactabilityProposal(ImmutableModel):
    assessment: NonEmptyStr
    known_paths: tuple[NonEmptyStr, ...]
    constraints: tuple[NonEmptyStr, ...]
    rationale: NonEmptyStr
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)
    confidence_claim_key: NonEmptyStr


class QualificationProposal(ImmutableModel):
    outcome: QualificationOutcomeType
    rationale: NonEmptyStr
    investigation_action: str | None = None
    material_review_reason: str | None = None

    @model_validator(mode="after")
    def explanation_matches_outcome(self) -> "QualificationProposal":
        if (
            self.outcome is QualificationOutcomeType.FURTHER_INVESTIGATION_REQUIRED
            and not self.investigation_action
        ):
            raise ValueError("further investigation requires a specific action")
        if (
            self.outcome is QualificationOutcomeType.INDETERMINATE_PENDING_MATERIAL_REVIEW
            and not self.material_review_reason
        ):
            raise ValueError("indeterminate qualification requires a review reason")
        return self


class OpportunityIntelligenceOutput(ImmutableModel):
    referenced_input_refs: tuple[ObjectRevisionRef, ...]
    confidences: tuple[ConfidenceProposal, ...] = Field(min_length=1)
    fit: FitProposal
    need: NeedProposal
    decision_owner: DecisionOwnerProposal
    contactability: ContactabilityProposal
    qualification: QualificationProposal
    commercial_rationale: NonEmptyStr
    material_uncertainties: tuple[NonEmptyStr, ...]
    recommended_investigation: str | None = None


class PairRequest(ImmutableModel):
    first: ObjectRevisionRef
    second: ObjectRevisionRef

    @model_validator(mode="after")
    def members_differ(self) -> "PairRequest":
        if self.first == self.second:
            raise ValueError("pair members must differ")
        return self


class PortfolioComparisonInput(AgentInput):
    operation: Literal["COMPARISON"] = "COMPARISON"
    snapshot_ref: ObjectRevisionRef
    opportunity_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=2)
    required_pairs: tuple[PairRequest, ...] = Field(min_length=1)


class PairwiseComparisonProposal(ImmutableModel):
    subject_ref: ObjectRevisionRef
    comparator_ref: ObjectRevisionRef
    relationship: ComparisonRelationship
    material_reason: NonEmptyStr
    secondary_factors: tuple[NonEmptyStr, ...] = ()


class ComparisonOperationOutput(ImmutableModel):
    operation: Literal["COMPARISON"] = "COMPARISON"
    referenced_input_refs: tuple[ObjectRevisionRef, ...]
    comparisons: tuple[PairwiseComparisonProposal, ...]
    material_reasons: tuple[NonEmptyStr, ...]


class DemandFact(ImmutableModel):
    opportunity_ref: ObjectRevisionRef
    demand_ref: ObjectRevisionRef
    estimated_effort: Decimal = Field(gt=0)
    unit: EffortUnit
    smaller_credible_action_available: bool


class PortfolioAllocationInput(AgentInput):
    operation: Literal["ALLOCATION"] = "ALLOCATION"
    snapshot_ref: ObjectRevisionRef
    priority_state_ref: ObjectRevisionRef
    capacity_envelope_ref: ObjectRevisionRef
    opportunity_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)
    demands: tuple[DemandFact, ...] = Field(min_length=1)
    available_capacity: Decimal = Field(ge=0)
    unit: EffortUnit
    planning_horizon: NonEmptyStr
    max_concurrent_pursuits: int = Field(gt=0)


class AllocationMemberProposal(ImmutableModel):
    opportunity_ref: ObjectRevisionRef
    reason: NonEmptyStr


class AlternativePortfolioProposal(ImmutableModel):
    opportunity_refs: tuple[ObjectRevisionRef, ...]
    rationale: NonEmptyStr


class AllocationOperationOutput(ImmutableModel):
    operation: Literal["ALLOCATION"] = "ALLOCATION"
    referenced_input_refs: tuple[ObjectRevisionRef, ...]
    act_now: tuple[ObjectRevisionRef, ...]
    deferred_capacity: tuple[ObjectRevisionRef, ...]
    deferred_priority: tuple[ObjectRevisionRef, ...]
    investigate: tuple[ObjectRevisionRef, ...]
    capacity_consumption: Decimal = Field(ge=0)
    capacity_unit: EffortUnit
    marginal_reasons: tuple[AllocationMemberProposal, ...]
    material_uncertainties: tuple[NonEmptyStr, ...]
    alternative_portfolios: tuple[AlternativePortfolioProposal, ...] = ()

    @model_validator(mode="after")
    def allocation_tiers_are_disjoint(self) -> "AllocationOperationOutput":
        members = (
            *self.act_now,
            *self.deferred_capacity,
            *self.deferred_priority,
            *self.investigate,
        )
        if len(members) != len(set(members)):
            raise ValueError("allocation tiers must be disjoint")
        return self


PortfolioOperationInput = Annotated[
    PortfolioComparisonInput | PortfolioAllocationInput, Field(discriminator="operation")
]


class PortfolioAllocationOutput(ImmutableModel):
    result: Annotated[
        ComparisonOperationOutput | AllocationOperationOutput,
        Field(discriminator="operation"),
    ]


class CommercialActionInput(AgentInput):
    opportunity_case_ref: ObjectRevisionRef
    comparative_priority_ref: ObjectRevisionRef
    allocation_case_ref: ObjectRevisionRef
    decision_owner_ref: ObjectRevisionRef
    contactability_ref: ObjectRevisionRef
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)
    material_uncertainties: tuple[NonEmptyStr, ...] = ()


class CommercialActionOutput(ImmutableModel):
    referenced_input_refs: tuple[ObjectRevisionRef, ...]
    action_type: ActionType
    action_description: NonEmptyStr
    action_scope: ActionScope
    decision_owner_ref: ObjectRevisionRef | None = None
    rationale: NonEmptyStr
    evidence_refs: tuple[ObjectRevisionRef, ...] = Field(min_length=1)
    material_uncertainties: tuple[NonEmptyStr, ...]
    draft_content: str | None = None


SpecialistInput = (
    MarketDiscoveryInput
    | EvidenceIntelligenceInput
    | OpportunityIntelligenceInput
    | PortfolioComparisonInput
    | PortfolioAllocationInput
    | CommercialActionInput
)
SpecialistOutput = (
    MarketDiscoveryOutput
    | EvidenceIntelligenceOutput
    | OpportunityIntelligenceOutput
    | PortfolioAllocationOutput
    | CommercialActionOutput
)
