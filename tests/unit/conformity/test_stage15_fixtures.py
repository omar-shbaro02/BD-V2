"""Stage 15 fixture integrity, provenance, and oracle-isolation tests."""

import json
import shutil
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from vai_bd.conformity import load_runtime_bundle

TESTS_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = TESTS_ROOT.parent
RUNTIME_ROOT = TESTS_ROOT / "fixtures" / "stage15"
ORACLE_ROOT = TESTS_ROOT / "oracle" / "stage15"
VERSION = "stage15-synthetic-v1.0.0"


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_runtime_bundle_is_complete_and_self_consistent() -> None:
    bundle = load_runtime_bundle(RUNTIME_ROOT)

    assert bundle.manifest.fixture_version == VERSION
    assert bundle.manifest.synthetic_only is True
    assert [item.case_id for item in bundle.base.candidates] == [
        f"C{number:02d}" for number in range(1, 11)
    ]
    assert [item.mutation_id for item in bundle.mutations] == [
        f"M{number:02d}" for number in range(1, 10)
    ]
    assert all(
        candidate.company_name.startswith("Synthetic ") for candidate in bundle.base.candidates
    )


def test_captured_outputs_cover_runtime_inputs_without_answer_key_material() -> None:
    bundle = load_runtime_bundle(RUNTIME_ROOT)
    observations_by_case = {
        item.case_id: {observation.observation_id for observation in item.observations}
        for item in bundle.base.candidates
    }

    for output in bundle.captured_outputs.cases:
        assert set(output.referenced_observation_ids) == observations_by_case[output.case_id]
    assert bundle.captured_outputs.portfolio.snapshot_members == (
        "C01",
        "C02",
        "C03",
        "C04",
        "C05",
    )
    assert len(bundle.captured_outputs.portfolio.pairwise_relations) == 10


def test_dataset_generator_payloads_reproduce_committed_artifacts() -> None:
    paths = sorted(RUNTIME_ROOT.rglob("*.json")) + sorted(ORACLE_ROOT.rglob("*.json"))
    before = {path: sha256(path.read_bytes()).hexdigest() for path in paths}

    subprocess.run(
        [sys.executable, "scripts/generate_stage15_dataset.py"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    after = {path: sha256(path.read_bytes()).hexdigest() for path in paths}
    assert after == before


def test_runtime_loader_never_reads_oracle(monkeypatch: pytest.MonkeyPatch) -> None:
    reads: list[Path] = []
    original_read_text = Path.read_text
    original_read_bytes = Path.read_bytes

    def tracked_text(path: Path, *args: object, **kwargs: object) -> str:
        reads.append(path)
        return original_read_text(path, *args, **kwargs)

    def tracked_bytes(path: Path, *args: object, **kwargs: object) -> bytes:
        reads.append(path)
        return original_read_bytes(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", tracked_text)
    monkeypatch.setattr(Path, "read_bytes", tracked_bytes)
    bundle = load_runtime_bundle(RUNTIME_ROOT)
    runtime_result = json.dumps(bundle.model_dump(mode="json"), sort_keys=True)

    assert runtime_result
    assert reads
    assert all("oracle" not in path.parts for path in reads)


def test_runtime_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    copied = tmp_path / "runtime"
    shutil.copytree(RUNTIME_ROOT, copied)
    base_path = copied / "base.json"
    base_path.write_text(base_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"fixture digest mismatch: base\.json"):
        load_runtime_bundle(copied)


def test_oracle_is_complete_and_bound_to_runtime_manifest() -> None:
    manifest = read_json(ORACLE_ROOT / "manifest.json")
    assert isinstance(manifest, dict)
    assert manifest["fixture_version"] == VERSION
    runtime_digest = sha256((RUNTIME_ROOT / "manifest.json").read_bytes()).hexdigest()
    assert manifest["runtime_manifest_sha256"] == runtime_digest

    files = manifest["files"]
    assert isinstance(files, list)
    assert len(files) == 10
    for item in files:
        assert isinstance(item, dict)
        path = ORACLE_ROOT / str(item["path"])
        assert path.is_file()
        assert sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_oracle_is_loaded_only_after_runtime_result_is_serialized() -> None:
    bundle = load_runtime_bundle(RUNTIME_ROOT)
    actual = json.dumps(bundle.captured_outputs.model_dump(mode="json"), sort_keys=True)
    assert actual

    expected = read_json(ORACLE_ROOT / "base_expected.json")
    assert isinstance(expected, dict)
    assert expected["comparison_order"] == ["C01", "C04", "C02", "C05", "C03"]
    assert len(expected["pairwise_relations"]) == 10
