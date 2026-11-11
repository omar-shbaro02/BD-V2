"""Evidence export integrity and fail-closed acceptance boundaries."""

import json
from pathlib import Path
from typing import Any

import pytest
from scripts import build_evidence_package as evidence
from tests.conformity.test_stage15_suite import passing_report


def test_manifest_covers_every_exported_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = json.loads((evidence.ROOT / "docs/traceability.json").read_text())
    passed = [test for row in rows for test in row["tests"]]

    def checks(root: Path, output: Path) -> tuple[dict[str, int], dict[str, Any]]:
        (output / "tests.xml").write_text("<testsuites/>", encoding="utf-8")
        return {"tests": 0}, {"passed": passed, "failed": [], "skipped": []}

    monkeypatch.setattr(evidence, "run_checks", checks)
    monkeypatch.setattr(
        evidence,
        "vcs_identity",
        lambda root: {"commit": "test-commit", "dirty": False, "version": "0.1"},
    )
    destination = tmp_path / "package"
    assert evidence.build(destination)
    manifest = json.loads((destination / "manifest.json").read_text())
    actual_files = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    # Nested fixture/prompt manifest files must also be covered.
    actual_files |= {
        path.relative_to(destination).as_posix()
        for path in (destination / "source").rglob("manifest.json")
    }
    assert set(manifest["files"]) == actual_files
    for name, expected in manifest["files"].items():
        assert evidence.digest(destination / name) == expected
    summary = json.loads((destination / "summary.json").read_text())
    assert summary["implementation_conformity"] == "PASS"
    assert summary["external_actions_authorized"] is False
    assert not (destination / "source/.env").exists()
    assert not (destination / "source/.git").exists()
    assert len(json.loads((destination / "agents.json").read_text())) == 5
    evidence.verify_package(destination)
    (destination / "HANDOFF.md").write_text("modified", encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        evidence.verify_package(destination)
    with pytest.raises(ValueError, match="already exists"):
        evidence.build(destination)


@pytest.mark.parametrize("kind", ["failed", "skipped", "empty", "command"])
def test_no_failure_skip_or_empty_verification_can_pass(kind: str) -> None:
    tests = {"passed": ["authority"], "failed": [], "skipped": []}
    checks = {"tests": 0}
    if kind == "empty":
        tests["passed"] = []
    elif kind == "command":
        checks["tests"] = 1
    else:
        tests[kind] = ["material test"]
    assert not evidence.gate(passing_report(), checks, tests)


def test_junit_exposes_failures_errors_and_skips(tmp_path: Path) -> None:
    path = tmp_path / "tests.xml"
    path.write_text(
        '<testsuites><testsuite><testcase classname="tests.unit.test_a" name="ok"/>'
        '<testcase name="bad"><failure/></testcase>'
        '<testcase name="error"><error/></testcase>'
        '<testcase name="skip"><skipped/></testcase></testsuite></testsuites>'
    )
    result = evidence.test_results(path)
    assert result["passed"] == ["tests/unit/test_a.py::ok"]
    assert len(result["failed"]) == 2
    assert len(result["skipped"]) == 1
    assert evidence.test_results(tmp_path / "missing.xml")["failed"]


def test_traceability_requires_executed_exact_parameter_and_valid_symbols() -> None:
    rows = json.loads((evidence.ROOT / "docs/traceability.json").read_text())
    passed = [test for row in rows for test in row["tests"]]
    verified = evidence.traceability(evidence.ROOT, {"passed": passed, "failed": [], "skipped": []})
    assert all(row["status"] == "VERIFIED" for row in verified)
    assert len(verified) >= 80
    blocked = evidence.traceability(evidence.ROOT, {"passed": [], "failed": [], "skipped": []})
    assert all(row["status"] == "BLOCKED" for row in blocked)


def test_fixture_and_oracle_integrity_is_checked_before_export(tmp_path: Path) -> None:
    evidence.validate_manifests(evidence.ROOT)
    import shutil

    for name in ("fixtures", "oracle"):
        shutil.copytree(evidence.ROOT / "tests" / name, tmp_path / "tests" / name)
    (tmp_path / "tests/oracle/stage15/base_expected.json").write_text("{}")
    with pytest.raises(ValueError, match="integrity mismatch"):
        evidence.validate_manifests(tmp_path)
