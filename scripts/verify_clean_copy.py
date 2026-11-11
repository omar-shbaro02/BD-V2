"""Run the complete offline CI sequence twice from isolated source copies."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPY_DIRECTORIES = (
    ".github",
    "docs",
    "migrations",
    "scripts",
    "src",
    "tests",
    "vai_bd_development_plan",
    "vai_bd_implementation_pack",
)
COPY_FILES = (
    ".gitattributes",
    ".env.example",
    ".gitignore",
    "alembic.ini",
    "docker-compose.yml",
    "Makefile",
    "pyproject.toml",
    "README.md",
    "requirements.lock",
)


def _ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".coverage"}
    return ignored.intersection(names)


def _copy_source(destination: Path) -> None:
    for name in COPY_DIRECTORIES:
        shutil.copytree(ROOT / name, destination / name, ignore=_ignore)
    for name in COPY_FILES:
        shutil.copy2(ROOT / name, destination / name)


def _commands(python: str, cache_dir: Path) -> tuple[tuple[str, ...], ...]:
    return (
        (python, "-m", "ruff", "format", "--check", "src", "tests", "scripts", "migrations"),
        (python, "-m", "ruff", "check", "src", "tests", "scripts", "migrations"),
        (python, "-m", "mypy", "--cache-dir", str(cache_dir)),
        (python, "scripts/hardening_scan.py"),
        (python, "-m", "pytest", "-q"),
    )


def main() -> None:
    # Preserve the virtual-environment launcher; resolving it follows the symlink
    # to the base interpreter and loses the installed offline toolchain.
    python = str(Path(sys.executable).absolute())
    for run_number in (1, 2):
        with tempfile.TemporaryDirectory(prefix=f"vai-bd-clean-{run_number}-") as temporary:
            checkout = Path(temporary)
            _copy_source(checkout)
            environment = os.environ.copy()
            environment.pop("OPENAI_API_KEY", None)
            environment.update(
                {
                    "APP_ENV": "test",
                    "EXTERNAL_EXECUTION_ALLOWED": "false",
                    "OPENAI_AGENTS_DISABLE_TRACING": "1",
                    "PYTHONPATH": str(checkout / "src"),
                    "TRACE_INCLUDE_SENSITIVE_DATA": "0",
                }
            )
            print(f"offline clean-copy run {run_number}/2")
            for command in _commands(python, checkout / ".mypy_cache"):
                subprocess.run(command, cwd=checkout, env=environment, check=True)
    print("PASS: two isolated offline CI runs completed")


if __name__ == "__main__":
    main()
