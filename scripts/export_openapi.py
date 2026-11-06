"""Regenerate the committed OpenAPI contract from the application factory."""

import json
from pathlib import Path

from vai_bd.config import AppEnvironment, Settings
from vai_bd.main import create_app

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs" / "openapi.json"


def main() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TEST,
        test_auth_signing_key="openapi-generation-only",
    )
    document = create_app(settings).openapi()
    TARGET.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
