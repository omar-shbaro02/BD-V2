"""Evidence, gate, snapshot, revision, and comparison policy tests."""

from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from vai_bd.domain.enums import (
    ActorKind,
    BlockingScope,
    ComparisonRelationship,
    EvidenceAdmissibility,
    EvidenceCurrentness,
    EvidenceDirectness,
    GateOutcome,
    ObjectValidity,
    QualificationOutcomeType,
)
from vai_bd.domain.evidence import EvidenceRecord
from vai_bd.domain.portfolio import CanonicalPairwiseComparison
from vai_bd.domain.refs import ActorRef, ObjectRevisionRef, SourceRef
from vai_bd.policies.comparisons import (
    analyze_comparisons,
    canonical_pair,
    generate_pairs,
    inverse_relationship,
    validate_comparison_set,
)
from vai_bd.policies.eligibility import EligibilityFacts, evaluate_eligibility
from vai_bd.policies.evidence import (
    SourceCurrentnessRule,
    bidirectional_contradictions,
    compute_currentness,
    independent_eligible_evidence,
)
from vai_bd.policies.revisions import check_required_revisions
from vai_bd.policies.snapshots import select_snapshot_members

NOW = datetime(2026, 10, 9, 12, tzinfo=UTC)
SYSTEM = ActorRef(
    actor_id=UUID("00000000-0000-0000-0000-000000000001"),
    actor_kind=ActorKind.SYSTEM,
    display_name="System",
)


def ref(number: int, object_type: str = "CommercialOpportunityCase") -> ObjectRevisionRef:
    return ObjectRevisionRef(
        object_id=UUID(f"00000000-0000-0000-0000-{number:012d}"),
        object_type=object_type,
        revision=1,
    )


def evidence(
    number: int,
    *,
    group: str | None = None,
    currentness: EvidenceCurrentness = EvidenceCurrentness.CURRENT,
    admissibility: EvidenceAdmissibility = EvidenceAdmissibility.ADMISSIBLE,
    contradicts: tuple[ObjectRevisionRef, ...] = (),
) -> EvidenceRecord:
    return EvidenceRecord(
        object_id=ref(number, "EvidenceRecord").object_id,
        object_type="EvidenceRecord",
        revision=1,
        created_at=NOW,
        created_by=SYSTEM,
        candidate_ref=ref(100, "CompanyCandidate"),
        claim_text=f"claim {number}",
        source=SourceRef(source_id=str(number), uri_or_reference=f"synthetic://{number}"),
        source_type="registry",
        source_date=date(2026, 10, 1),
        observed_at=NOW,
        provenance="fixture",
        directness=EvidenceDirectness.DIRECT,
        currentness=currentness,
        source_dependency_group=group,
        contradicts=contradicts,
        admissibility=admissibility,
    )


def comparison(
    number: int,
    subject: ObjectRevisionRef,
    comparator: ObjectRevisionRef,
    relationship: ComparisonRelationship,
) -> CanonicalPairwiseComparison:
    return CanonicalPairwiseComparison(
        object_id=ref(number, "CanonicalPairwiseComparison").object_id,
        object_type="CanonicalPairwiseComparison",
        revision=1,
        created_at=NOW,
        created_by=SYSTEM,
        snapshot_ref=ref(900, "QualifiedUniverseSnapshot"),
        subject_opportunity_revision=subject,
        comparator_opportunity_revision=comparator,
        relationship=relationship,
        material_reason="fixture comparison",
    )


def test_currentness_uses_configured_rule_and_preserves_unknown() -> None:
    record = evidence(1)
    rules = {"registry": SourceCurrentnessRule("registry", 10)}
    assert (
        compute_currentness(record, as_of=date(2026, 10, 9), rules=rules)
        is EvidenceCurrentness.CURRENT
    )
    assert (
        compute_currentness(record, as_of=date(2026, 10, 20), rules=rules)
        is EvidenceCurrentness.STALE
    )
    assert (
        compute_currentness(record, as_of=date(2026, 10, 9), rules={})
        is EvidenceCurrentness.UNKNOWN
    )
    assert record.currentness is EvidenceCurrentness.CURRENT


def test_evidence_independence_and_admissibility_are_enforced() -> None:
    records = (
        evidence(1, group="shared"),
        evidence(2, group="shared"),
        evidence(3, currentness=EvidenceCurrentness.STALE),
        evidence(4, admissibility=EvidenceAdmissibility.RESTRICTED),
        evidence(5),
    )
    selected = independent_eligible_evidence(records)
    assert tuple(item.object_id for item in selected) == (ref(1).object_id, ref(5).object_id)


def test_contradictions_are_bidirectional() -> None:
    first = evidence(1, contradicts=(ref(2, "EvidenceRecord"),))
    second = evidence(2)
    graph = bidirectional_contradictions((first, second))
    assert graph[first.revision_ref] == (second.revision_ref,)
    assert graph[second.revision_ref] == (first.revision_ref,)


@pytest.mark.parametrize(
    ("facts", "outcome", "scope"),
    [
        (
            EligibilityFacts(False, False),
            GateOutcome.CONTRADICTION_BLOCK,
            BlockingScope.WHOLE_CYCLE,
        ),
        (
            EligibilityFacts(True, True, BlockingScope.PORTFOLIO, True, True),
            GateOutcome.CONTRADICTION_BLOCK,
            BlockingScope.PORTFOLIO,
        ),
        (
            EligibilityFacts(True, False, known_hard_exclusion=True),
            GateOutcome.HARD_EXCLUSION,
            BlockingScope.LOCAL,
        ),
        (EligibilityFacts(True, False), GateOutcome.EVIDENCE_REQUIRED, BlockingScope.LOCAL),
        (
            EligibilityFacts(True, False, minimum_evidence_satisfied=True),
            GateOutcome.PROCEED,
            BlockingScope.LOCAL,
        ),
    ],
)
def test_gate_precedence(
    facts: EligibilityFacts, outcome: GateOutcome, scope: BlockingScope
) -> None:
    decision = evaluate_eligibility(facts)
    assert decision.outcome is outcome
    assert decision.blocking_scope is scope


def test_missing_evidence_never_becomes_disqualification() -> None:
    decision = evaluate_eligibility(EligibilityFacts(True, False))
    assert decision.outcome is GateOutcome.EVIDENCE_REQUIRED
    assert decision.outcome is not GateOutcome.HARD_EXCLUSION


def test_required_revision_check_rejects_missing_and_noncurrent() -> None:
    current, superseded, missing = ref(1), ref(2), ref(3)
    check = check_required_revisions(
        (current, superseded, missing),
        {current: ObjectValidity.CURRENT, superseded: ObjectValidity.SUPERSEDED},
    )
    assert not check.is_valid
    assert len(check.reasons) == 2


def test_snapshot_includes_only_qualified_and_preserves_other_reasons() -> None:
    qualified, investigate, disqualified = ref(1), ref(2), ref(3)
    result = select_snapshot_members(
        {
            investigate: QualificationOutcomeType.FURTHER_INVESTIGATION_REQUIRED,
            qualified: QualificationOutcomeType.QUALIFIED,
            disqualified: QualificationOutcomeType.DISQUALIFIED_BY_KNOWN_EVIDENCE,
        }
    )
    assert result.included_refs == (qualified,)
    assert {item.object_ref for item in result.excluded_or_unresolved} == {
        investigate,
        disqualified,
    }


def test_pair_generation_is_exact_deterministic_and_order_independent() -> None:
    members = (ref(3), ref(1), ref(2), ref(4))
    expected = generate_pairs(members)
    assert len(expected) == 6
    assert generate_pairs(reversed(members)) == expected
    assert all(pair == canonical_pair(*pair) for pair in expected)


@pytest.mark.parametrize("relationship", list(ComparisonRelationship))
def test_comparison_inverse_is_an_involution(relationship: ComparisonRelationship) -> None:
    assert inverse_relationship(inverse_relationship(relationship)) is relationship


def test_comparison_completeness_and_cycle_exposure() -> None:
    a, b, c = ref(1), ref(2), ref(3)
    comparisons = (
        comparison(11, a, b, ComparisonRelationship.MATERIALLY_ABOVE),
        comparison(12, b, c, ComparisonRelationship.ABOVE),
        comparison(13, c, a, ComparisonRelationship.ABOVE),
    )
    assert validate_comparison_set((a, b, c), comparisons).is_valid
    analysis = analyze_comparisons((a, b, c), comparisons)
    assert analysis.cycles == ((a, b, c),)
    assert analysis.material_edges == ((a, b),)


def test_symmetric_relationships_do_not_create_strict_edges() -> None:
    a, b, c = ref(1), ref(2), ref(3)
    comparisons = (
        comparison(11, a, b, ComparisonRelationship.TIE),
        comparison(12, b, c, ComparisonRelationship.NEAR_TIE),
        comparison(13, a, c, ComparisonRelationship.INDETERMINATE),
    )
    analysis = analyze_comparisons((a, b, c), comparisons)
    assert analysis.strict_edges == ()
    assert analysis.ties == ((a, b),)
    assert analysis.near_ties == ((b, c),)
    assert analysis.indeterminate_pairs == ((a, c),)
