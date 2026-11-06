"""Run Stage 15 with expected outcomes read only after runtime serialization."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from vai_bd.conformity import (
    BASE_CASES,
    MUTATION_CASES,
    evaluate_conformity,
    execute_stage15_runtime,
    load_runtime_bundle,
    serialize_runtime_execution,
)
from vai_bd.domain.enums import ConformityStatus

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "tests" / "fixtures" / "stage15"
EXPECTED_ROOT = ROOT / "tests" / "oracle" / "stage15"
REPORT_PATH = ROOT / "artifacts" / "conformity" / "stage15-report.json"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_expected_results() -> tuple[dict[str, Mapping[str, Any]], dict[str, tuple[str, ...]]]:
    base = read_json(EXPECTED_ROOT / "base_expected.json")
    expectations: dict[str, Mapping[str, Any]] = {
        "BASE": {
            key: value
            for key, value in base.items()
            if key
            not in {
                "schema_version",
                "fixture_version",
                "case_expectations",
                "expected_rule_refs",
            }
        }
    }
    case_expectations = base["case_expectations"]
    if not isinstance(case_expectations, dict):
        raise ValueError("base case expectations must be an object")
    for case_id in BASE_CASES:
        expected = case_expectations[case_id]
        if not isinstance(expected, dict):
            raise ValueError(f"expected object for {case_id}")
        expectations[case_id] = expected
    base_rules = tuple(str(item) for item in base["expected_rule_refs"])
    rules = {case_id: base_rules for case_id in ("BASE", *BASE_CASES)}
    for mutation_id in MUTATION_CASES:
        mutation = read_json(EXPECTED_ROOT / "mutations" / f"{mutation_id}.json")
        expected = mutation["expected"]
        if not isinstance(expected, dict):
            raise ValueError(f"expected object for {mutation_id}")
        expectations[mutation_id] = expected
        rules[mutation_id] = tuple(str(item) for item in mutation["expected_rule_refs"])
    return expectations, rules


def main() -> None:
    runtime = load_runtime_bundle(RUNTIME_ROOT)
    execution = execute_stage15_runtime(runtime)
    serialized_actual = serialize_runtime_execution(execution)
    if not serialized_actual:
        raise RuntimeError("runtime execution did not serialize")

    expectations, rules = load_expected_results()
    report = evaluate_conformity(
        execution,
        expectations,
        rules,
        code_version="phase8-conformity-v1",
        prompt_versions={"captured-test-double": runtime.manifest.fixture_version},
        model_config_id="deterministic-captured-fixture",
    )
    report.write_json(REPORT_PATH)
    print(
        f"{report.suite_status.value}: {len(report.results)} material cases; "
        f"report={REPORT_PATH.relative_to(ROOT)}"
    )
    if report.suite_status is not ConformityStatus.PASS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
