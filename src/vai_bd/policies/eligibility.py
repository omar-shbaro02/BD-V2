"""Minimum-evidence and hard-eligibility gate precedence."""

from dataclasses import dataclass

from vai_bd.domain.enums import BlockingScope, GateOutcome


@dataclass(frozen=True)
class EligibilityFacts:
    market_boundary_valid: bool
    material_contradiction: bool
    contradiction_scope: BlockingScope = BlockingScope.LOCAL
    known_hard_exclusion: bool = False
    minimum_evidence_satisfied: bool = False


@dataclass(frozen=True)
class EligibilityDecision:
    outcome: GateOutcome
    blocking_scope: BlockingScope
    reasons: tuple[str, ...]


def evaluate_eligibility(facts: EligibilityFacts) -> EligibilityDecision:
    """Apply the frozen gate precedence; this policy never qualifies a candidate."""

    if not facts.market_boundary_valid:
        return EligibilityDecision(
            GateOutcome.CONTRADICTION_BLOCK,
            BlockingScope.WHOLE_CYCLE,
            ("governing_market_boundary_missing_or_invalid",),
        )
    if facts.material_contradiction:
        return EligibilityDecision(
            GateOutcome.CONTRADICTION_BLOCK,
            facts.contradiction_scope,
            ("material_unresolved_contradiction",),
        )
    if facts.known_hard_exclusion:
        return EligibilityDecision(
            GateOutcome.HARD_EXCLUSION,
            BlockingScope.LOCAL,
            ("known_hard_exclusion_supported_by_admissible_evidence",),
        )
    if not facts.minimum_evidence_satisfied:
        return EligibilityDecision(
            GateOutcome.EVIDENCE_REQUIRED,
            BlockingScope.LOCAL,
            ("insufficient_admissible_current_evidence",),
        )
    return EligibilityDecision(GateOutcome.PROCEED, BlockingScope.LOCAL, ("gate_satisfied",))
