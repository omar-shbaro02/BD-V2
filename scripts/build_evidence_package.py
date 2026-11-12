"""Build a source-bound, fail-closed offline Evidence Package v0.1."""

# ruff: noqa: E402

import argparse
import ast
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

# Direct invocation must resolve the repository's scripts package too.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alembic.config import Config
from alembic.script import ScriptDirectory
from scripts.hardening_scan import SECRET_PATTERNS, scan_repository
from scripts.run_stage15_conformity import load_expected_results
from scripts.verify_clean_copy import COPY_DIRECTORIES, COPY_FILES, _ignore
from sqlalchemy import create_engine, text

from vai_bd.agents.definitions import SPECIALISTS
from vai_bd.conformity import (
    evaluate_conformity,
    execute_stage15_runtime,
    load_runtime_bundle,
    serialize_runtime_execution,
)
from vai_bd.conformity.suite import ConformityReport
from vai_bd.domain.enums import ConformityStatus

DEFAULT_OUTPUT = ROOT / "evidence_package" / "generated"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_inventory(root: Path) -> dict[str, str]:
    files = [root / name for name in COPY_FILES]
    for directory in COPY_DIRECTORIES:
        for path in (root / directory).rglob("*"):
            if (
                path.is_file()
                and not any(_ignore("", [part]) for part in path.relative_to(root).parts)
                and path.suffix not in {".pyc", ".pyo"}
            ):
                if path.is_symlink():
                    raise ValueError("source symlinks cannot enter evidence")
                files.append(path)
    return {path.relative_to(root).as_posix(): digest(path) for path in sorted(files)}


def inventory_digest(inventory: dict[str, str]) -> str:
    return sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest()


def verify_package(directory: Path) -> None:
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("algorithm") != "sha256":
        raise ValueError("unsupported package digest algorithm")
    actual = {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file() and path != directory / "manifest.json"
    }
    if actual != set(manifest["files"]):
        raise ValueError("package file inventory mismatch")
    for name, expected in manifest["files"].items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory.resolve()) or digest(path) != expected:
            raise ValueError("package digest mismatch")


def vcs_identity(root: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()

    return {
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "version": tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"],
    }


def test_results(path: Path) -> dict[str, Any]:
    """Treat every failure, error, skip, or empty run as a failed gate."""
    if not path.is_file():
        return {"passed": [], "failed": ["missing JUnit report"], "skipped": []}
    passed, failed, skipped = [], [], []
    for case in ET.parse(path).getroot().iter("testcase"):
        nodeid = case.attrib.get("classname", "").replace(".", "/")
        nodeid += ".py::" + case.attrib.get("name", "")
        if case.find("skipped") is not None:
            skipped.append(nodeid)
        elif case.find("failure") is not None or case.find("error") is not None:
            failed.append(nodeid)
        else:
            passed.append(nodeid)
    return {"passed": passed, "failed": failed, "skipped": skipped}


def validate_manifests(root: Path) -> None:
    runtime = root / "tests/fixtures/stage15"
    oracle = root / "tests/oracle/stage15"
    for directory in (runtime, oracle):
        manifest = json.loads((directory / "manifest.json").read_text())
        for entry in manifest["files"]:
            path = (directory / entry["path"]).resolve()
            if not path.is_relative_to(directory.resolve()) or digest(path) != entry["sha256"]:
                raise ValueError("fixture/oracle integrity mismatch")
    expected = json.loads((oracle / "manifest.json").read_text())
    if expected["runtime_manifest_sha256"] != digest(runtime / "manifest.json"):
        raise ValueError("oracle is not bound to the current runtime manifest")


def gate(report: ConformityReport, checks: dict[str, int], tests: dict[str, Any]) -> bool:
    return (
        report.suite_status is ConformityStatus.PASS
        and bool(checks)
        and all(code == 0 for code in checks.values())
        and bool(tests["passed"])
        and not tests["failed"]
        and not tests["skipped"]
    )


def traceability(root: Path, tests: dict[str, Any]) -> list[dict[str, Any]]:
    rows = json.loads((root / "docs/traceability.json").read_text(encoding="utf-8"))
    passed = set(tests["passed"]) | {item.split("[")[0] for item in tests["passed"]}
    unsuccessful = {item.split("[")[0] for item in tests["failed"] + tests["skipped"]}
    for row in rows:
        for reference in row["code"]:
            filename, symbol = reference.split(":", 1)
            tree = ast.parse((root / filename).read_text(encoding="utf-8"))
            if symbol not in {getattr(node, "name", "") for node in ast.walk(tree)}:
                raise ValueError(f"traceability symbol missing: {reference}")
        if not row["tests"]:
            raise ValueError("traceability row has no automated test")
        row["status"] = (
            "VERIFIED"
            if all(
                test in passed and test.split("[")[0] not in unsuccessful for test in row["tests"]
            )
            else "BLOCKED"
        )
        row["evidence"] = "verification/tests.xml"
    return rows


def run_checks(root: Path, output: Path) -> tuple[dict[str, int], dict[str, Any]]:
    python = sys.executable
    commands = {
        "format": [
            python,
            "-m",
            "ruff",
            "format",
            "--check",
            "src",
            "tests",
            "scripts",
            "migrations",
        ],
        "lint": [python, "-m", "ruff", "check", "src", "tests", "scripts", "migrations"],
        "types": [python, "-m", "mypy"],
        "dependencies": [python, "-m", "pip", "check"],
        "hardening": [python, "scripts/hardening_scan.py"],
        "tests": [python, "-m", "pytest", "-q", f"--junitxml={output / 'tests.xml'}"],
    }
    environment = os.environ.copy()
    for key in ("OPENAI_API_KEY", "OPENAI_MODEL", "TEST_AUTH_SIGNING_KEY"):
        environment.pop(key, None)
    environment.update(
        APP_ENV="test",
        EXTERNAL_EXECUTION_ALLOWED="false",
        OPENAI_AGENTS_DISABLE_TRACING="1",
        TRACE_INCLUDE_SENSITIVE_DATA="0",
    )
    checks = {}
    for name, command in commands.items():
        print(f"Verifying {name}...", flush=True)
        with (output / f"{name}.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(
                command,
                cwd=root,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        checks[name] = result.returncode
    return checks, test_results(output / "tests.xml")


def build(output: Path) -> bool:
    if output.exists():
        raise ValueError("output already exists; choose a new --output directory")
    output = output.resolve()
    if output == ROOT or ROOT.is_relative_to(output):
        raise ValueError("output must not contain the source repository")
    if any(output.is_relative_to(ROOT / name) for name in COPY_DIRECTORIES):
        raise ValueError("output must not enter a source inventory directory")
    before = source_inventory(ROOT)
    identity = vcs_identity(ROOT)
    version = f"{identity['version']}+source.{inventory_digest(before)}"
    if scan_repository(ROOT):
        raise ValueError("source scan failed; evidence export refused")
    with tempfile.TemporaryDirectory(prefix="vai-bd-evidence-") as temporary:
        package = Path(temporary)
        verification = package / "verification"
        verification.mkdir()
        checks, tests = run_checks(ROOT, verification)
        runtime = load_runtime_bundle(ROOT / "tests/fixtures/stage15")
        execution = execute_stage15_runtime(runtime)
        # Serialize actuals before opening held-out expected outcomes.
        (verification / "runtime-actuals.json").write_text(
            serialize_runtime_execution(execution), encoding="utf-8"
        )
        validate_manifests(ROOT)
        expectations, rules = load_expected_results()
        report = evaluate_conformity(
            execution,
            expectations,
            rules,
            code_version=version,
            prompt_versions={name.value: item.prompt.version for name, item in SPECIALISTS.items()},
            model_config_id="deterministic-captured-fixture",
        )
        report.write_json(verification / "conformity-report.json")
        rows = traceability(ROOT, tests)
        checks["traceability"] = int(any(row["status"] != "VERIFIED" for row in rows))
        success = gate(report, checks, tests)
        for relative in before:
            destination = package / "source" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
            if digest(destination) != before[relative]:
                raise ValueError("copied source does not match verified source")
        if before != source_inventory(ROOT):
            raise ValueError("source changed during verification; rebuild required")
        write_json(package / "source-inventory.json", before)
        (package / "repository-tree.txt").write_text("\n".join(before) + "\n", encoding="utf-8")
        write_json(package / "traceability.json", rows)
        write_json(package / "verification/test-results.json", tests)
        write_json(
            package / "agents.json",
            {
                name.value: {
                    "responsibility": item.agent.name,
                    "prompt_version": item.prompt.version,
                    "prompt_digest": item.prompt.content_digest,
                    "tools": [],
                    "handoffs": [],
                    "model_config": "deterministic-captured-fixture (no live calls)",
                    "output_type": item.agent.output_type.__name__,
                }
                for name, item in SPECIALISTS.items()
            },
        )
        migration = ScriptDirectory.from_config(
            Config(str(ROOT / "alembic.ini"))
        ).get_current_head()
        summary = {
            "package_version": "0.1",
            "created_at": datetime.now(UTC).isoformat(),
            "identity": identity,
            "code_version": version,
            "source_sha256": inventory_digest(before),
            "profile": "test/conformity",
            "dependency_lock_sha256": before["requirements.lock"],
            "migration_head": migration,
            "implementation_conformity": "PASS" if success else "FAIL",
            "checks": checks,
            "failed_tests": tests["failed"],
            "skipped_tests": tests["skipped"],
            "deployment_authorized": False,
            "live_pilot_authorized": False,
            "external_actions_authorized": False,
            "python": platform.python_version(),
            "platform": platform.system(),
            "fixture_version": runtime.manifest.fixture_version,
            "runtime_manifest_sha256": before["tests/fixtures/stage15/manifest.json"],
            "oracle_manifest_sha256": before["tests/oracle/stage15/manifest.json"],
            "frozen_business_rules_version": next(
                iter(SPECIALISTS.values())
            ).prompt.frozen_business_rules_version,
        }
        database_url = os.environ.get(
            "TEST_DATABASE_URL",
            os.environ.get(
                "DATABASE_URL", "postgresql+psycopg://vai_bd:vai_bd@localhost:5432/vai_bd"
            ),
        )
        engine = create_engine(database_url)
        try:
            with engine.connect() as connection:
                summary["test_database_version"] = connection.scalar(text("SHOW server_version"))
        except Exception:
            summary["test_database_version"] = "unavailable; see integration test failures"
        finally:
            engine.dispose()
        write_json(package / "summary.json", summary)
        (package / "HANDOFF.md").write_text(
            "# Evidence Package v0.1\n\n"
            f"Implementation conformity: **{summary['implementation_conformity']}**.\n\n"
            "Start with summary.json, verification/test-results.json and traceability.json. "
            "Every payload file is SHA-256 bound in manifest.json. Source identity includes "
            "the base Git commit, dirty flag and exact exported source digest.\n\n"
            "Setup/run: source/README.md. Architecture: source/docs/architecture.md. "
            "Agent inventory: agents.json. Frozen authority and development plans are in source/. "
            "Full case results and synthetic trace references: "
            "verification/conformity-report.json; "
            "serialized actuals: verification/runtime-actuals.json. "
            "Command logs and JUnit evidence are in verification/.\n\n"
            "Runtime fixtures: source/tests/fixtures/stage15/. Held-out evaluator oracle: "
            "source/tests/oracle/stage15/. This is an evaluator handoff archive; do not mount "
            "the oracle into runtime or agent contexts. Runtime completed before oracle reads.\n\n"
            "Limitations: synthetic baseline replaces the unavailable original Stage 15 input; "
            "captured deterministic doubles make no live-model performance claim. "
            "Trace references are synthetic runtime identifiers, not hosted OpenAI traces. "
            "Database audit behavior is verified by integration tests, not a real-company "
            "audit export. ADRs 0001/0002 retain proposed governance decisions. "
            "Test authentication requires an approved identity provider before future deployment. "
            "Optional live-agent smoke was not run. Deployment, pilot, provider activation "
            "and external actions remain unauthorized.\n\n"
            "Any failed check, missing test evidence or skipped test prevents PASS. "
            "See summary.json for exact remaining verification gaps.\n",
            encoding="utf-8",
        )
        files = {
            p.relative_to(package).as_posix(): digest(p)
            for p in sorted(package.rglob("*"))
            if p.is_file()
        }
        write_json(package / "manifest.json", {"algorithm": "sha256", "files": files})
        verify_package(package)
        # Scan the export too, before publishing logs or source copies.
        for path in package.rglob("*"):
            if path.is_file():
                content = path.read_text(encoding="utf-8")
                if any(pattern.search(content) for pattern in SECRET_PATTERNS.values()):
                    raise ValueError("generated export scan failed; publication refused")
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(package, output)
    print(f"{summary['implementation_conformity']}: {output}")
    return success


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--verify", type=Path, help="verify an existing package without rerunning tests"
    )
    arguments = parser.parse_args()
    if arguments.verify:
        verify_package(arguments.verify)
        print("PASS: package inventory and SHA-256 digests match")
        return
    if not build(arguments.output):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
