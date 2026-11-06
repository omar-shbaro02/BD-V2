"""Fail closed on committed-secret signatures and runtime oracle coupling."""

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRECTORIES = (
    "src",
    "tests",
    "migrations",
    "scripts",
    "docs",
    "vai_bd_development_plan",
    "vai_bd_implementation_pack",
    ".github",
)
SCAN_FILES = (
    ".env.example",
    "alembic.ini",
    "docker-compose.yml",
    "Makefile",
    "pyproject.toml",
    "requirements.lock",
)
TEXT_SUFFIXES = {".html", ".ini", ".json", ".md", ".py", ".toml", ".txt", ".yml", ".yaml"}
SECRET_PATTERNS = {
    "openai_api_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "github_token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "bearer_token": re.compile(r"Authorization\s*[:=]\s*[\"']?Bearer\s+[A-Za-z0-9._-]{16,}"),
}
ORACLE_PATTERN = re.compile(
    r"(?:from|import)\s+tests\.oracle|tests/oracle|oracle/stage15", re.IGNORECASE
)


@dataclass(frozen=True)
class Finding:
    category: str
    path: str


def scan_repository(root: Path = ROOT) -> tuple[Finding, ...]:
    findings: set[Finding] = set()
    files = list(_project_files(root))
    for path in files:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = str(path.relative_to(root))
        for category, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                findings.add(Finding(category, relative))
        if relative.startswith("src/") and ORACLE_PATTERN.search(content):
            findings.add(Finding("runtime_oracle_dependency", relative))
    return tuple(sorted(findings, key=lambda item: (item.category, item.path)))


def _project_files(root: Path):  # type: ignore[no-untyped-def]
    for name in SCAN_FILES:
        path = root / name
        if path.is_file():
            yield path
    for name in SCAN_DIRECTORIES:
        directory = root / name
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                yield path
    for path in root.glob("*.log"):
        if path.is_file():
            yield path


def main() -> None:
    findings = scan_repository()
    if findings:
        for finding in findings:
            print(f"FAIL {finding.category}: {finding.path}")
        raise SystemExit(1)
    print("PASS: no credential signatures or runtime oracle dependencies found")


if __name__ == "__main__":
    main()
