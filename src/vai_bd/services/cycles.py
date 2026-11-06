"""Phase-oriented service facade used by the deterministic cycle orchestrator."""

from sqlalchemy.orm import Session

from vai_bd.agents.contracts import (
    CommercialActionInput,
    EvidenceIntelligenceInput,
    MarketDiscoveryInput,
    OpportunityIntelligenceInput,
    PortfolioAllocationInput,
    PortfolioComparisonInput,
    SpecialistName,
)
from vai_bd.domain.cycle import CapacityEnvelope, DecisionCycleContext, OfferProfile
from vai_bd.domain.enums import GateOutcome
from vai_bd.domain.refs import ObjectRevisionRef
from vai_bd.orchestrator.dependencies import WorkflowPhase, require_phase_inputs
from vai_bd.persistence.repositories import GovernedObjectRepository
from vai_bd.services.common import RevisionFactory, current_validities
from vai_bd.services.executor import AgentPhaseExecutor, AgentPhaseResult
from vai_bd.services.portfolio import allocation_persistence, comparison_persistence
from vai_bd.services.specialists import (
    action_persistence,
    assessment_persistence,
    discovery_persistence,
    evidence_persistence,
)


class DecisionCycleServices:
    def __init__(self, executor: AgentPhaseExecutor, factory: RevisionFactory) -> None:
        self.executor = executor
        self.factory = factory

    def bootstrap(
        self,
        session: Session,
        *,
        offer: OfferProfile,
        cycle: DecisionCycleContext,
        capacity: CapacityEnvelope | None = None,
    ) -> tuple[ObjectRevisionRef, ...]:
        if cycle.offer_ref != offer.revision_ref:
            raise ValueError("decision cycle must reference the exact supplied offer")
        if capacity is not None and capacity.decision_cycle_ref != cycle.revision_ref:
            raise ValueError("capacity must reference the exact supplied decision cycle")
        objects = GovernedObjectRepository(session)
        objects.append(offer)
        objects.append(cycle)
        refs = [offer.revision_ref, cycle.revision_ref]
        if capacity is not None:
            objects.append(capacity)
            refs.append(capacity.revision_ref)
        return tuple(refs)

    async def discovery(self, key: str, agent_input: MarketDiscoveryInput) -> AgentPhaseResult:
        self._require(WorkflowPhase.DISCOVERY, agent_input.exact_input_refs)
        return await self.executor.execute(
            operation="discovery",
            idempotency_key=key,
            name=SpecialistName.MARKET_DISCOVERY,
            agent_input=agent_input,
            persist_output=discovery_persistence(self.factory, agent_input),
        )

    async def evidence(self, key: str, agent_input: EvidenceIntelligenceInput) -> AgentPhaseResult:
        self._require(WorkflowPhase.EVIDENCE, agent_input.exact_input_refs)
        return await self.executor.execute(
            operation=f"evidence:{agent_input.candidate_ref.object_id}",
            idempotency_key=key,
            name=SpecialistName.EVIDENCE_INTELLIGENCE,
            agent_input=agent_input,
            persist_output=evidence_persistence(self.factory, agent_input),
        )

    async def assessment(
        self, key: str, agent_input: OpportunityIntelligenceInput
    ) -> AgentPhaseResult:
        self._require(
            WorkflowPhase.ASSESSMENT,
            agent_input.exact_input_refs,
            gate_outcome=GateOutcome(agent_input.gate_outcome),
        )
        return await self.executor.execute(
            operation=f"assessment:{agent_input.candidate_ref.object_id}",
            idempotency_key=key,
            name=SpecialistName.OPPORTUNITY_INTELLIGENCE,
            agent_input=agent_input,
            persist_output=assessment_persistence(self.factory, agent_input),
        )

    async def comparison(self, key: str, agent_input: PortfolioComparisonInput) -> AgentPhaseResult:
        self._require(WorkflowPhase.COMPARISON, agent_input.exact_input_refs)
        return await self.executor.execute(
            operation=f"comparison:{agent_input.snapshot_ref.object_id}",
            idempotency_key=key,
            name=SpecialistName.PORTFOLIO_ALLOCATION,
            agent_input=agent_input,
            persist_output=comparison_persistence(self.factory, agent_input),
        )

    async def allocation(self, key: str, agent_input: PortfolioAllocationInput) -> AgentPhaseResult:
        self._require(WorkflowPhase.ALLOCATION, agent_input.exact_input_refs)
        return await self.executor.execute(
            operation=f"allocation:{agent_input.snapshot_ref.object_id}",
            idempotency_key=key,
            name=SpecialistName.PORTFOLIO_ALLOCATION,
            agent_input=agent_input,
            persist_output=allocation_persistence(self.factory, agent_input),
        )

    async def action(self, key: str, agent_input: CommercialActionInput) -> AgentPhaseResult:
        self._require(WorkflowPhase.ACTION, agent_input.exact_input_refs)
        return await self.executor.execute(
            operation=f"action:{agent_input.opportunity_case_ref.object_id}",
            idempotency_key=key,
            name=SpecialistName.COMMERCIAL_ACTION,
            agent_input=agent_input,
            persist_output=action_persistence(self.factory, agent_input),
        )

    def _require(
        self,
        phase: WorkflowPhase,
        refs: tuple[ObjectRevisionRef, ...],
        *,
        gate_outcome: GateOutcome | None = None,
    ) -> None:
        with self.executor.session_factory() as session:
            require_phase_inputs(
                phase,
                refs,
                current_validities(session, refs),
                gate_outcome=gate_outcome,
            )
