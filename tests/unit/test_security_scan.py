"""Repository security and oracle-isolation scan tests."""

from pathlib import Path

from scripts.hardening_scan import scan_repository


def test_repository_has_no_secret_signature_or_runtime_oracle_dependency() -> None:
    assert scan_repository() == ()


def test_scan_reports_paths_without_echoing_secret_values(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    secret = "sk-" + "a" * 24
    (source / "leak.py").write_text(f'TOKEN = "{secret}"\n', encoding="utf-8")
    findings = scan_repository(tmp_path)
    assert [(item.category, item.path) for item in findings] == [("openai_api_key", "src/leak.py")]
    assert all(secret not in repr(item) for item in findings)
