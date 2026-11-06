"""Transactional conversion of validated specialist proposals into domain revisions."""

from collections.abc import Callable
from typing import cast

from sqlalchemy.orm import Session

from vai_bd.agents.contracts import (
    CommercialActionInput,
    CommercialActionOutput,
    EvidenceIntelligenceInput,
    EvidenceIntelligenceOutput,
    MarketDiscoveryInput,
    MarketDiscoveryOutput,
    OpportunityIntelligenceInput,
    OpportunityIntelligenceOutput,
    SpecialistOutput,
)
from vai_bd.domain.actions import CommercialActionOpportunity
from vai_bd.domain.cycle import CandidateUniverseCoverageState, CompanyCandidate
from vai_bd.domain.evidence import EvidenceRecord
from vai_bd.domain.opportunity import (
    CommercialOpportunityCase,
    CompanyOfferFit,
    ConfidenceAssessment,
    ContactabilityAssessment,
    DecisionOwnerHypothesis,
    NeedHypothesis,
    QualificationOutcome,
)
from vai_bd.domain.refs import ObjectRevisionRef
from vai_bd.persistence.orm import CandidateUniverseMemberRow
from vai_bd.persistence.repositories import GovernedObjectRepository
from vai_bd.services.common import RevisionFactory

PersistCallback = Callable[[Session, SpecialistOutput], tuple[ObjectRevisionRef, ...]]


def discovery_persistence(
    factory: RevisionFactory, agent_input: MarketDiscoveryInput
) -> PersistCallback:
    def persist(session: Session, raw_output: SpecialistOutput) -> tuple[ObjectRevisionRef, ...]:
        output = cast(MarketDiscoveryOutput, raw_output)
        repository = GovernedObjectRepository(session)
        universe_ref = factory.new_ref("CandidateUniverseCoverageState")
        candidate_refs = {
            item.proposal_key: factory.new_ref("CompanyCandidate") for item in output.candidates
        }
        removed_refs = tuple(item.candidate_ref for item in output.removed_candidates)
        universe = CandidateUniverseCoverageState(
            **factory.envelope(universe_ref, dependencies=agent_input.exact_input_refs),
            decision_cycle_ref=agent_input.decision_cycle_ref,
            coverage_basis=output.coverage_basis,
            coverage_limitations=output.coverage_limitations,
            candidate_refs=tuple(candidate_refs.values()),
            added_candidates=tuple(candidate_refs[key] for key in output.added_candidate_keys),
            removed_candidates=removed_refs,
            coverage_status=output.coverage_status,
        )
        repository.append(universe)
        candidates: list[CompanyCandidate] = []
        for proposal in output.candidates:
            candidate = CompanyCandidate(
                **factory.envelope(
                    candidate_refs[proposal.proposal_key],
                    dependencies=(universe.revision_ref, *agent_input.exact_input_refs),
                ),
                universe_ref=universe.revision_ref,
                company_name=proposal.company_name,
                market_presence_claims=proposal.market_presence_claims,
                segment_claims=proposal.segment_claims,
                source_refs=proposal.source_refs,
                candidate_status=proposal.candidate_status,
            )
            repository.append(candidate)
            candidates.append(candidate)
            session.add(
                CandidateUniverseMemberRow(
                    universe_id=universe.object_id,
                    universe_revision=universe.revision,
                    candidate_id=candidate.object_id,
                    candidate_revision=candidate.revision,
                    disposition="INCLUDED",
                )
            )
        session.flush()
        return (universe.revision_ref, *(item.revision_ref for item in candidates))

    return persist


def evidence_persistence(
    factory: RevisionFactory, agent_input: EvidenceIntelligenceInput
) -> PersistCallback:
    def persist(session: Session, raw_output: SpecialistOutput) -> tuple[ObjectRevisionRef, ...]:
        output = cast(EvidenceIntelligenceOutput, raw_output)
        repository = GovernedObjectRepository(session)
        proposal_refs = {
            item.proposal_key: factory.new_ref("EvidenceRecord") for item in output.evidence_records
        }
        records: list[EvidenceRecord] = []
        for proposal in output.evidence_records:
            contradiction_refs = (
                tuple(proposal_refs[key] for key in proposal.contradicts_proposal_keys)
                + proposal.contradicts_existing_refs
            )
            record = EvidenceRecord(
                **factory.envelope(
                    proposal_refs[proposal.proposal_key],
                    dependencies=agent_input.exact_input_refs,
                ),
                candidate_ref=agent_input.candidate_ref,
                claim_text=proposal.claim_text,
                source=proposal.source,
                source_type=proposal.source_type,
                source_date=proposal.source_date,
                observed_at=factory.clock(),
                provenance=proposal.provenance,
                directness=proposal.directness,
                currentness=proposal.currentness,
                source_dependency_group=proposal.source_dependency_group,
                contradicts=contradiction_refs,
                admissibility=proposal.admissibility,
            )
            repository.append(record)
            records.append(record)
        return tuple(item.revision_ref for item in records)

    return persist


def assessment_persistence(
    factory: RevisionFactory, agent_input: OpportunityIntelligenceInput
) -> PersistCallback:
    def persist(session: Session, raw_output: SpecialistOutput) -> tuple[ObjectRevisionRef, ...]:
        output = cast(OpportunityIntelligenceOutput, raw_output)
        repository = GovernedObjectRepository(session)
        judgment_refs = {
            "fit": factory.new_ref("CompanyOfferFit"),
            "need": factory.new_ref("NeedHypothesis"),
            "owner": factory.new_ref("DecisionOwnerHypothesis"),
            "contact": factory.new_ref("ContactabilityAssessment"),
        }
        confidence_refs = {
            proposal.claim_key: factory.new_ref("ConfidenceAssessment")
            for proposal in output.confidences
        }
        claim_ref_by_key = {
            output.fit.confidence_claim_key: judgment_refs["fit"],
            output.need.confidence_claim_key: judgment_refs["need"],
            output.decision_owner.confidence_claim_key: judgment_refs["owner"],
            output.contactability.confidence_claim_key: judgment_refs["contact"],
        }
        if set(confidence_refs) != set(claim_ref_by_key):
            raise ValueError("assessment confidences must map one-to-one to the four judgments")
        confidences: list[ConfidenceAssessment] = []
        for proposal in output.confidences:
            confidence = ConfidenceAssessment(
                **factory.envelope(
                    confidence_refs[proposal.claim_key],
                    dependencies=agent_input.exact_input_refs,
                ),
                claim_ref=claim_ref_by_key[proposal.claim_key],
                level=proposal.level,
                rationale=proposal.rationale,
                evidence_refs=proposal.evidence_refs,
            )
            repository.append(confidence)
            confidences.append(confidence)
        fit = CompanyOfferFit(
            **factory.envelope(
                judgment_refs["fit"],
                dependencies=(
                    *agent_input.exact_input_refs,
                    confidence_refs[output.fit.confidence_claim_key],
                ),
            ),
            candidate_ref=agent_input.candidate_ref,
            offer_ref=agent_input.offer_ref,
            judgment=output.fit.judgment,
            rationale=output.fit.rationale,
            evidence_refs=output.fit.evidence_refs,
            claim_confidence_ref=confidence_refs[output.fit.confidence_claim_key],
        )
        need = NeedHypothesis(
            **factory.envelope(
                judgment_refs["need"],
                dependencies=(
                    *agent_input.exact_input_refs,
                    confidence_refs[output.need.confidence_claim_key],
                ),
            ),
            candidate_ref=agent_input.candidate_ref,
            hypothesis=output.need.hypothesis,
            status=output.need.status,
            rationale=output.need.rationale,
            evidence_refs=output.need.evidence_refs,
            claim_confidence_ref=confidence_refs[output.need.confidence_claim_key],
        )
        owner = DecisionOwnerHypothesis(
            **factory.envelope(
                judgment_refs["owner"],
                dependencies=(
                    *agent_input.exact_input_refs,
                    confidence_refs[output.decision_owner.confidence_claim_key],
                ),
            ),
            candidate_ref=agent_input.candidate_ref,
            role_hypothesis=output.decision_owner.role_hypothesis,
            named_person_ref=output.decision_owner.named_person_ref,
            rationale=output.decision_owner.rationale,
            evidence_refs=output.decision_owner.evidence_refs,
            claim_confidence_ref=confidence_refs[output.decision_owner.confidence_claim_key],
        )
        contactability = ContactabilityAssessment(
            **factory.envelope(
                judgment_refs["contact"],
                dependencies=(
                    *agent_input.exact_input_refs,
                    confidence_refs[output.contactability.confidence_claim_key],
                ),
            ),
            candidate_ref=agent_input.candidate_ref,
            assessment=output.contactability.assessment,
            known_paths=output.contactability.known_paths,
            constraints=output.contactability.constraints,
            rationale=output.contactability.rationale,
            evidence_refs=output.contactability.evidence_refs,
            claim_confidence_ref=confidence_refs[output.contactability.confidence_claim_key],
        )
        for judgment in (fit, need, owner, contactability):
            repository.append(judgment)
        qualification_ref = factory.new_ref("QualificationOutcome")
        qualification = QualificationOutcome(
            **factory.envelope(
                qualification_ref,
                dependencies=(
                    *agent_input.exact_input_refs,
                    fit.revision_ref,
                    need.revision_ref,
                    owner.revision_ref,
                    contactability.revision_ref,
                ),
            ),
            candidate_ref=agent_input.candidate_ref,
            outcome=output.qualification.outcome,
            rationale=output.qualification.rationale,
            investigation_action=output.qualification.investigation_action,
            material_review_reason=output.qualification.material_review_reason,
        )
        repository.append(qualification)
        case_ref = factory.new_ref("CommercialOpportunityCase")
        opportunity = CommercialOpportunityCase(
            **factory.envelope(
                case_ref,
                dependencies=(
                    *agent_input.exact_input_refs,
                    fit.revision_ref,
                    need.revision_ref,
                    owner.revision_ref,
                    contactability.revision_ref,
                    qualification.revision_ref,
                ),
            ),
            candidate_ref=agent_input.candidate_ref,
            offer_ref=agent_input.offer_ref,
            fit_ref=fit.revision_ref,
            need_ref=need.revision_ref,
            decision_owner_ref=owner.revision_ref,
            contactability_ref=contactability.revision_ref,
            qualification_ref=qualification.revision_ref,
            commercial_rationale=output.commercial_rationale,
            material_uncertainties=output.material_uncertainties,
        )
        repository.append(opportunity)
        return (
            *(item.revision_ref for item in confidences),
            fit.revision_ref,
            need.revision_ref,
            owner.revision_ref,
            contactability.revision_ref,
            qualification.revision_ref,
            opportunity.revision_ref,
        )

    return persist


def action_persistence(
    factory: RevisionFactory, agent_input: CommercialActionInput
) -> PersistCallback:
    def persist(session: Session, raw_output: SpecialistOutput) -> tuple[ObjectRevisionRef, ...]:
        output = cast(CommercialActionOutput, raw_output)
        action_ref = factory.new_ref("CommercialActionOpportunity")
        action = CommercialActionOpportunity(
            **factory.envelope(action_ref, dependencies=agent_input.exact_input_refs),
            opportunity_case_ref=agent_input.opportunity_case_ref,
            comparative_priority_ref=agent_input.comparative_priority_ref,
            allocation_case_ref=agent_input.allocation_case_ref,
            action_type=output.action_type,
            action_description=output.action_description,
            action_scope=output.action_scope,
            decision_owner_ref=output.decision_owner_ref,
            rationale=output.rationale,
            evidence_refs=output.evidence_refs,
            material_uncertainties=output.material_uncertainties,
            draft_content=output.draft_content,
        )
        GovernedObjectRepository(session).append(action)
        return (action.revision_ref,)

    return persist
