"""Pure governed domain contracts."""

from vai_bd.domain.actions import (
    ActionScope,
    CommercialActionOpportunity,
    RecommendationReleaseReadiness,
)
from vai_bd.domain.audit import (
    AgentRun,
    ConformityCaseResult,
    ExternalExecutionEligibilityDecision,
    MaterialImpactDecision,
    WorkflowTransition,
)
from vai_bd.domain.authorization import (
    AgentReviewRequest,
    HumanAuthorizationCurrentState,
    HumanAuthorizationEvent,
)
from vai_bd.domain.cycle import (
    CandidateUniverseCoverageState,
    CapacityEnvelope,
    CompanyCandidate,
    DecisionCycleContext,
    OfferProfile,
)
from vai_bd.domain.envelopes import GovernedObject
from vai_bd.domain.evidence import (
    ContradictionGroup,
    EvidenceRecord,
    MinimumEvidenceHardEligibilityGateResult,
    MissingEvidenceFlag,
)
from vai_bd.domain.opportunity import (
    CommercialOpportunityCase,
    CompanyOfferFit,
    ConfidenceAssessment,
    ContactabilityAssessment,
    DecisionOwnerHypothesis,
    NeedHypothesis,
    OpportunityState,
    PursuitDemand,
    QualificationOutcome,
)
from vai_bd.domain.portfolio import (
    AlternativePortfolio,
    CanonicalPairwiseComparison,
    CapacityBoundedAllocationCase,
    ComparativePriorityState,
    PriorityRelation,
    QualifiedUniverseSnapshot,
)
from vai_bd.domain.refs import ActorRef, ObjectRevisionRef, SourceRef

__all__ = [
    "ActionScope",
    "ActorRef",
    "AgentReviewRequest",
    "AgentRun",
    "AlternativePortfolio",
    "CandidateUniverseCoverageState",
    "CanonicalPairwiseComparison",
    "CapacityBoundedAllocationCase",
    "CapacityEnvelope",
    "CommercialActionOpportunity",
    "CommercialOpportunityCase",
    "CompanyCandidate",
    "CompanyOfferFit",
    "ComparativePriorityState",
    "ConfidenceAssessment",
    "ConformityCaseResult",
    "ContactabilityAssessment",
    "ContradictionGroup",
    "DecisionCycleContext",
    "DecisionOwnerHypothesis",
    "EvidenceRecord",
    "ExternalExecutionEligibilityDecision",
    "GovernedObject",
    "HumanAuthorizationCurrentState",
    "HumanAuthorizationEvent",
    "MaterialImpactDecision",
    "MinimumEvidenceHardEligibilityGateResult",
    "MissingEvidenceFlag",
    "NeedHypothesis",
    "ObjectRevisionRef",
    "OfferProfile",
    "OpportunityState",
    "PriorityRelation",
    "PursuitDemand",
    "QualificationOutcome",
    "QualifiedUniverseSnapshot",
    "RecommendationReleaseReadiness",
    "SourceRef",
    "WorkflowTransition",
]
