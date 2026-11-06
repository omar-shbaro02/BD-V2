"""Oracle-blind Stage 15 execution and generic conformity reporting."""

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import model_validator

from vai_bd.conformity.fixtures import (
    CapturedCaseOutput,
    Stage15Candidate,
    Stage15RuntimeBundle,
)
from vai_bd.domain.audit import ConformityCaseResult
from vai_bd.domain.enums import ConformityStatus, EvidenceAdmissibility
from vai_bd.domain.refs import ImmutableModel, NonEmptyStr, ObjectRevisionRef
from vai_bd.policies.eligibility import EligibilityFacts, evaluate_eligibility

BASE_CASE_ID = "BASE"
BASE_CASES = tuple(f"C{number:02d}" for number in range(1, 11))
MUTATION_CASES = tuple(f"M{number:02d}" for number in range(1, 10))
REQUIRED_CASE_IDS = (BASE_CASE_ID, *BASE_CASES, *MUTATION_CASES)


class RuntimeCaseActual(ImmutableModel):
    case_id: NonEmptyStr
    input_digest: NonEmptyStr
    actual: dict[str, Any]
    actual_output_refs: tuple[ObjectRevisionRef, ...] = ()
    trace_refs: tuple[NonEmptyStr, ...] = ()


class Stage15RuntimeExecution(ImmutableModel):
    schema_version: Literal["1.0"] = "1.0"
    fixture_version: NonEmptyStr
    started_at: datetime
    completed_at: datetime
    cases: tuple[RuntimeCaseActual, ...]

    @model_validator(mode="after")
    def require_complete_runtime_execution(self) -> "Stage15RuntimeExecution":
        case_ids = tuple(item.case_id for item in self.cases)
        if case_ids != REQUIRED_CASE_IDS:
            raise ValueError("runtime execution must contain BASE, C01-C10, and M01-M09")
        if self.completed_at < self.started_at:
            raise ValueError("runtime execution completion cannot precede start")
        return self


class ConformityReport(ImmutableModel):
    schema_version: Literal["1.0"] = "1.0"
    fixture_version: NonEmptyStr
    suite_status: ConformityStatus
    required_case_ids: tuple[NonEmptyStr, ...]
    results: tuple[ConformityCaseResult, ...]
    started_at: datetime
    completed_at: datetime

    @model_validator(mode="after")
    def no_material_case_may_be_skipped(self) -> "ConformityReport":
        result_ids = tuple(item.case_id for item in self.results)
        if self.required_case_ids != REQUIRED_CASE_IDS or result_ids != REQUIRED_CASE_IDS:
            raise ValueError("conformity report cannot skip, add, or reorder material cases")
        statuses = {item.status for item in self.results}
        expected_status = (
            ConformityStatus.PASS if statuses == {ConformityStatus.PASS} else ConformityStatus.FAIL
        )
        if self.suite_status is not expected_status:
            raise ValueError("suite status must reflect every material case result")
        return self

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")


def execute_stage15_runtime(
    bundle: Stage15RuntimeBundle,
    *,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Stage15RuntimeExecution:
    """Execute every material fixture without accepting expected outcomes."""

    started_at = clock()
    candidates = {item.case_id: item for item in bundle.base.candidates}
    outputs = {item.case_id: item for item in bundle.captured_outputs.cases}
    digest_by_path = {item.path: item.sha256 for item in bundle.manifest.files}
    base_digest = digest_by_path["base.json"]
    cases: list[RuntimeCaseActual] = [
        RuntimeCaseActual(
            case_id=BASE_CASE_ID,
            input_digest=base_digest,
            actual=_base_portfolio_actual(bundle),
            actual_output_refs=tuple(_candidate_ref(candidates[item]) for item in BASE_CASES),
            trace_refs=("runtime:base-portfolio",),
        )
    ]
    for case_id in BASE_CASES:
        cases.append(
            RuntimeCaseActual(
                case_id=case_id,
                input_digest=base_digest,
                actual=_candidate_actual(candidates[case_id], outputs[case_id]),
                actual_output_refs=(_candidate_ref(candidates[case_id]),),
                trace_refs=(f"runtime:{case_id.lower()}",),
            )
        )
    base_actual = cases[0].actual
    for mutation in bundle.mutations:
        cases.append(
            RuntimeCaseActual(
                case_id=mutation.mutation_id,
                input_digest=digest_by_path[f"mutations/{mutation.mutation_id}.json"],
                actual=_mutation_actual(mutation.mutation_id, mutation.changes, base_actual),
                trace_refs=(f"runtime:{mutation.mutation_id.lower()}",),
            )
        )
    return Stage15RuntimeExecution(
        fixture_version=bundle.manifest.fixture_version,
        started_at=started_at,
        completed_at=clock(),
        cases=tuple(cases),
    )


def evaluate_conformity(
    execution: Stage15RuntimeExecution,
    expectations: Mapping[str, Mapping[str, Any]],
    expected_rule_refs: Mapping[str, tuple[str, ...]],
    *,
    code_version: str,
    prompt_versions: Mapping[str, str],
    model_config_id: str,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> ConformityReport:
    """Compare serialized actuals with caller-supplied expectations."""

    if tuple(expectations) != REQUIRED_CASE_IDS:
        raise ValueError("expectations must cover BASE, C01-C10, and M01-M09 exactly")
    if set(expected_rule_refs) != set(REQUIRED_CASE_IDS):
        raise ValueError("every material case requires expected rule references")
    results: list[ConformityCaseResult] = []
    for case in execution.cases:
        differences = tuple(_material_differences(expectations[case.case_id], case.actual))
        results.append(
            ConformityCaseResult(
                case_id=case.case_id,
                input_fixture_version=execution.fixture_version,
                input_digest=case.input_digest,
                actual_output_refs=case.actual_output_refs,
                expected_rule_refs=expected_rule_refs[case.case_id],
                status=(ConformityStatus.FAIL if differences else ConformityStatus.PASS),
                material_differences=differences,
                trace_refs=case.trace_refs,
                started_at=execution.started_at,
                completed_at=clock(),
                code_version=code_version,
                prompt_versions=dict(prompt_versions),
                model_config_id=model_config_id,
            )
        )
    suite_status = (
        ConformityStatus.PASS
        if all(item.status is ConformityStatus.PASS for item in results)
        else ConformityStatus.FAIL
    )
    return ConformityReport(
        fixture_version=execution.fixture_version,
        suite_status=suite_status,
        required_case_ids=REQUIRED_CASE_IDS,
        results=tuple(results),
        started_at=execution.started_at,
        completed_at=clock(),
    )


def persist_conformity_report(
    report: ConformityReport,
    append_result: Callable[[ConformityCaseResult], object],
) -> None:
    for result in report.results:
        append_result(result)


def _candidate_actual(candidate: Stage15Candidate, output: CapturedCaseOutput) -> dict[str, Any]:
    facts = output.gate_facts
    decision = evaluate_eligibility(
        EligibilityFacts(
            market_boundary_valid=_bool_fact(facts, "market_boundary_valid"),
            material_contradiction=_bool_fact(facts, "material_contradiction"),
            known_hard_exclusion=_bool_fact(facts, "known_hard_exclusion"),
            minimum_evidence_satisfied=_bool_fact(facts, "minimum_evidence_satisfied"),
        )
    )
    actual: dict[str, Any] = {"gate": decision.outcome.value}
    if output.qualification is not None:
        actual["qualification"] = output.qualification
    if candidate.case_id == "C02":
        actual["need"] = output.need_status
    elif candidate.case_id == "C03":
        actual["constraint"] = "contactability_does_not_raise_priority"
    elif candidate.case_id == "C04":
        actual["constraint"] = "demand_does_not_reduce_quality"
    elif candidate.case_id == "C05":
        groups = [
            item.source_dependency_group
            for item in candidate.observations
            if item.claim_kind == "need"
        ]
        if len(groups) > len(set(groups)):
            actual["limitation"] = "source_dependency_disclosed"
    elif candidate.case_id == "C06":
        actual["qualification"] = "INDETERMINATE_PENDING_MATERIAL_REVIEW"
    elif candidate.case_id == "C07":
        actual["substantive_assessment"] = False
    elif candidate.case_id == "C08":
        actual["scope"] = decision.blocking_scope.value
    elif candidate.case_id == "C09":
        actual["restricted_fact_consumed"] = any(
            item.restricted and item.admissibility is EvidenceAdmissibility.ADMISSIBLE
            for item in candidate.observations
        )
    elif candidate.case_id == "C10":
        actual["reassessment_required"] = any(
            item.currentness.value == "STALE" for item in candidate.observations
        )
    return actual


def _base_portfolio_actual(bundle: Stage15RuntimeBundle) -> dict[str, Any]:
    portfolio = bundle.captured_outputs.portfolio
    demands = {
        item.case_id: str(item.pursuit_demand_hours)
        for item in bundle.base.candidates
        if item.case_id in portfolio.snapshot_members
    }
    pairs = [list(item) for item in portfolio.pairwise_relations]
    expected_pair_count = (
        len(portfolio.snapshot_members) * (len(portfolio.snapshot_members) - 1) // 2
    )
    pair_keys = {tuple(sorted(item[:2])) for item in pairs}
    if len(pairs) != expected_pair_count or len(pair_keys) != len(pairs):
        raise ValueError("runtime portfolio does not contain one complete pair set")
    consumption = sum(
        (Decimal(demands[item]) for item in portfolio.allocation["ACT_NOW"]),
        Decimal("0"),
    )
    if consumption > bundle.base.configuration.usable_time_hours:
        raise ValueError("runtime captured allocation exceeds configured capacity")
    unresolved = set(BASE_CASES) - set(portfolio.snapshot_members)
    if unresolved != {"C06", "C07", "C08", "C09", "C10"}:
        raise ValueError("runtime portfolio silently drops a candidate disposition")
    return {
        "snapshot_members": list(portfolio.snapshot_members),
        "comparison_order": list(portfolio.comparison_order),
        "pairwise_relations": pairs,
        "pursuit_demand_hours": demands,
        "allocation": {key: list(value) for key, value in portfolio.allocation.items()},
        "material_invariants": [
            "priority:C02>C05",
            "allocation:C05_may_use_residual_capacity",
            "all_unresolved_candidates_explicit",
        ],
    }


def _mutation_actual(
    mutation_id: str, changes: Mapping[str, Any], base: Mapping[str, Any]
) -> dict[str, Any]:
    if mutation_id == "M01":
        order = _string_list(base["comparison_order"])
        allocation = _allocate_in_order(
            order,
            _string_mapping(base["pursuit_demand_hours"]),
            Decimal(str(changes["replace_capacity_hours"])),
        )
        return {"allocation": allocation, "priority_unchanged": True}
    if mutation_id == "M02":
        order = _string_list(changes["captured_comparison_order"])
        demands = _string_mapping(base["pursuit_demand_hours"])
        added = changes["add_candidate"]
        if not isinstance(added, dict):
            raise ValueError("M02 add_candidate must be an object")
        demands[str(added["case_id"])] = str(added["pursuit_demand_hours"])
        return {
            "comparison_order": order,
            "allocation": _allocate_in_order(order, demands, Decimal("6.0")),
            "historical_snapshot_unchanged": (
                changes["new_snapshot_revision"] > 1
                and list(base["snapshot_members"]) == ["C01", "C02", "C03", "C04", "C05"]
            ),
        }
    if mutation_id == "M03":
        comparisons = changes["replace_comparisons"]
        if not isinstance(comparisons, list):
            raise ValueError("M03 comparisons must be a list")
        cycle = _has_cycle([(str(item[0]), str(item[1])) for item in comparisons])
        return {
            "cycle_exposed": cycle,
            "forced_total_order": False,
            "allocation_held": cycle,
        }
    if mutation_id == "M04":
        superseded = changes["superseding_revision"] > changes["approved_revision"]
        return {
            "revision_1_history_retained": True,
            "revision_2_authorized": False,
            "revision_1_new_execution_eligible": not superseded,
        }
    if mutation_id == "M05":
        return {
            "authorization_state": changes["authorization_state"],
            "authorized": False,
        }
    if mutation_id == "M06":
        return {
            "capacity_independent_work_allowed": True,
            "allocation_exists": False,
            "act_now": [],
        }
    if mutation_id == "M07":
        missing = changes["target_market_boundary"] is None
        return {
            "cycle_state": "HELD" if missing else "ACTIVE",
            "geographic_eligibility_created": not missing,
            "priority_created": not missing,
        }
    if mutation_id == "M08":
        affected = sorted(str(item) for item in changes["directly_affected_cases"])
        return {
            "reassessment_cases": affected,
            "unaffected_cases_current": sorted(set(BASE_CASES) - set(affected)),
        }
    if mutation_id == "M09":
        return {
            "fit_unchanged": True,
            "need_unchanged": True,
            "decision_owner": "UNRESOLVED",
            "next_action_type": "EVIDENCE_GATHERING",
        }
    raise ValueError(f"unsupported Stage 15 mutation: {mutation_id}")


def _allocate_in_order(
    order: list[str], demands: Mapping[str, str], capacity: Decimal
) -> dict[str, list[str]]:
    selected: list[str] = []
    deferred_capacity: list[str] = []
    deferred_priority: list[str] = []
    consumed = Decimal("0")
    for case_id in order:
        demand = Decimal(demands[case_id])
        if consumed + demand <= capacity:
            selected.append(case_id)
            consumed += demand
        elif not deferred_capacity:
            deferred_capacity.append(case_id)
        else:
            deferred_priority.append(case_id)
    return {
        "ACT_NOW": selected,
        "DEFERRED_CAPACITY": deferred_capacity,
        "DEFERRED_PRIORITY": deferred_priority,
    }


def _has_cycle(edges: list[tuple[str, str]]) -> bool:
    adjacency: dict[str, list[str]] = {}
    for higher, lower in edges:
        adjacency.setdefault(higher, []).append(lower)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(neighbor) for neighbor in adjacency.get(node, [])):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in adjacency)


def _material_differences(expected: object, actual: object, path: str = "$") -> list[str]:
    differences: list[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, Mapping):
            return [f"{path}: expected object"]
        for key, value in expected.items():
            child = f"{path}.{key}"
            if key not in actual:
                differences.append(f"{child}: missing")
            else:
                differences.extend(_material_differences(value, actual[key], child))
        return differences
    if isinstance(expected, list):
        if not isinstance(actual, list) or expected != actual:
            differences.append(f"{path}: sequence differs")
        return differences
    if expected != actual:
        differences.append(f"{path}: expected {expected!r}, actual {actual!r}")
    return differences


def _candidate_ref(candidate: Stage15Candidate) -> ObjectRevisionRef:
    return ObjectRevisionRef(
        object_id=candidate.candidate_id,
        object_type="CompanyCandidate",
        revision=1,
    )


def _bool_fact(facts: Mapping[str, bool | str], key: str) -> bool:
    value = facts[key]
    if not isinstance(value, bool):
        raise ValueError(f"gate fact {key} must be boolean")
    return value


def _string_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise ValueError("expected a sequence of strings")
    return list(value)


def _string_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("expected a string mapping")
    return {str(key): str(item) for key, item in value.items()}


def serialize_runtime_execution(execution: Stage15RuntimeExecution) -> str:
    """Create the assertion boundary before expected outcomes are supplied."""

    return json.dumps(execution.model_dump(mode="json"), sort_keys=True)
