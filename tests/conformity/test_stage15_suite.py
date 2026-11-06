"""Complete Stage 15 semantic and negative-boundary conformity suite."""

import json
from collections.abc import Mapping
from pathlib import Path

import pytest
from pydantic import ValidationError
from scripts.run_stage15_conformity import load_expected_results

from vai_bd.agents.definitions import SPECIALISTS
from vai_bd.conformity import (
    REQUIRED_CASE_IDS,
    ConformityReport,
    Stage15RuntimeExecution,
    evaluate_conformity,
    execute_stage15_runtime,
    load_runtime_bundle,
    persist_conformity_report,
    serialize_runtime_execution,
)
from vai_bd.domain.audit import ConformityCaseResult
from vai_bd.domain.enums import ConformityStatus
from vai_bd.policies.execution import conformity_restriction

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "tests" / "fixtures" / "stage15"


def execute_then_load_expected() -> tuple[
    Stage15RuntimeExecution,
    str,
    dict[str, Mapping[str, object]],
    dict[str, tuple[str, ...]],
]:
    runtime = load_runtime_bundle(RUNTIME_ROOT)
    execution = execute_stage15_runtime(runtime)
    serialized = serialize_runtime_execution(execution)
    expectations, rules = load_expected_results()
    return execution, serialized, expectations, rules


def passing_report() -> ConformityReport:
    execution, serialized, expectations, rules = execute_then_load_expected()
    assert serialized
    return evaluate_conformity(
        execution,
        expectations,
        rules,
        code_version="test-working-tree",
        prompt_versions={"captured-test-double": "stage15-synthetic-v1.0.0"},
        model_config_id="deterministic-captured-fixture",
    )


def test_all_base_cases_mutations_and_portfolio_meanings_pass() -> None:
    report = passing_report()

    assert report.suite_status is ConformityStatus.PASS
    assert tuple(item.case_id for item in report.results) == REQUIRED_CASE_IDS
    assert len(report.results) == 20
    assert all(item.status is ConformityStatus.PASS for item in report.results)
    assert all(not item.material_differences for item in report.results)


@pytest.mark.parametrize("case_id", [f"C{number:02d}" for number in range(1, 11)])
def test_every_base_candidate_is_materially_adjudicated(case_id: str) -> None:
    report = passing_report()
    result = next(item for item in report.results if item.case_id == case_id)
    assert result.status is ConformityStatus.PASS
    assert result.actual_output_refs


@pytest.mark.parametrize("mutation_id", [f"M{number:02d}" for number in range(1, 10)])
def test_every_mutation_is_independent_and_reproducible(mutation_id: str) -> None:
    execution, _, _, _ = execute_then_load_expected()
    cases = {item.case_id: item for item in execution.cases}
    mutation = cases[mutation_id]
    assert mutation.input_digest
    assert mutation.trace_refs == (f"runtime:{mutation_id.lower()}",)


def test_material_difference_fails_case_and_suite() -> None:
    execution, _, expectations, rules = execute_then_load_expected()
    expectations["C01"] = {"qualification": "DISQUALIFIED_BY_KNOWN_EVIDENCE"}
    report = evaluate_conformity(
        execution,
        expectations,
        rules,
        code_version="test-working-tree",
        prompt_versions={"captured-test-double": "v1"},
        model_config_id="deterministic-captured-fixture",
    )

    result = next(item for item in report.results if item.case_id == "C01")
    assert report.suite_status is ConformityStatus.FAIL
    assert result.status is ConformityStatus.FAIL
    assert result.material_differences


def test_missing_material_case_fails_before_reporting() -> None:
    execution, _, expectations, rules = execute_then_load_expected()
    expectations.pop("M09")
    with pytest.raises(ValueError, match="expectations must cover"):
        evaluate_conformity(
            execution,
            expectations,
            rules,
            code_version="test-working-tree",
            prompt_versions={"captured-test-double": "v1"},
            model_config_id="deterministic-captured-fixture",
        )


@pytest.mark.parametrize("mode", ["missing", "duplicate"])
def test_incomplete_or_duplicate_pair_set_fails_closed(mode: str) -> None:
    runtime = load_runtime_bundle(RUNTIME_ROOT)
    portfolio = runtime.captured_outputs.portfolio
    pairs = list(portfolio.pairwise_relations)
    pairs = pairs[:-1] if mode == "missing" else [*pairs, pairs[0]]
    changed_portfolio = portfolio.model_copy(update={"pairwise_relations": tuple(pairs)})
    changed_outputs = runtime.captured_outputs.model_copy(update={"portfolio": changed_portfolio})
    changed_runtime = runtime.model_copy(update={"captured_outputs": changed_outputs})

    with pytest.raises(ValueError, match="complete pair set"):
        execute_stage15_runtime(changed_runtime)


def test_report_schema_rejects_skipped_result() -> None:
    payload = passing_report().model_dump(mode="json")
    payload["results"] = payload["results"][:-1]
    with pytest.raises(ValidationError, match="cannot skip"):
        ConformityReport.model_validate(payload)


def test_machine_readable_report_round_trips_and_can_be_persisted(tmp_path: Path) -> None:
    report = passing_report()
    output = tmp_path / "stage15-report.json"
    report.write_json(output)
    decoded = json.loads(output.read_text(encoding="utf-8"))
    assert decoded["suite_status"] == "PASS"
    assert len(decoded["results"]) == 20

    persisted: list[ConformityCaseResult] = []
    persist_conformity_report(report, persisted.append)
    assert tuple(item.case_id for item in persisted) == REQUIRED_CASE_IDS


def test_negative_authority_and_execution_boundaries_hold() -> None:
    assert len(SPECIALISTS) == 5
    assert all(specialist.agent.tools == [] for specialist in SPECIALISTS.values())
    assert all(specialist.agent.handoffs == [] for specialist in SPECIALISTS.values())
    assert conformity_restriction().allows_external_execution is False

    execution, _, _, _ = execute_then_load_expected()
    actual = {item.case_id: item.actual for item in execution.cases}
    assert actual["C09"]["restricted_fact_consumed"] is False
    assert actual["M04"]["revision_2_authorized"] is False
    assert actual["M04"]["revision_1_new_execution_eligible"] is False
    assert actual["M05"]["authorized"] is False
    assert actual["M05"]["authorization_state"] == "PENDING_HUMAN_REVIEW"
