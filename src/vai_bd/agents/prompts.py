"""Versioned prompt loading with fail-closed content-digest validation."""

import json
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from vai_bd.agents.contracts import SpecialistName

PROMPT_DIRECTORY = Path(__file__).with_name("prompts")


class PromptIntegrityError(RuntimeError):
    """Raised when prompt files no longer match their approved manifest."""


@dataclass(frozen=True)
class PromptBundle:
    name: SpecialistName
    version: str
    frozen_business_rules_version: str
    created_at: date
    approved_for_implementation_by: str
    content_digest: str
    instructions: str


def load_prompt_bundles() -> dict[SpecialistName, PromptBundle]:
    manifest = _load_manifest()
    shared = (PROMPT_DIRECTORY / "shared.md").read_text(encoding="utf-8")
    bundles: dict[SpecialistName, PromptBundle] = {}
    prompt_entries = manifest["prompts"]
    if not isinstance(prompt_entries, dict):
        raise PromptIntegrityError("prompt manifest entries must be an object")
    for name in SpecialistName:
        raw = prompt_entries.get(name.value)
        if not isinstance(raw, dict):
            raise PromptIntegrityError(f"missing prompt manifest entry: {name.value}")
        role_file = _required_string(raw, "role_file")
        role_path = PROMPT_DIRECTORY / role_file
        if role_path.parent != PROMPT_DIRECTORY or role_path.suffix != ".md":
            raise PromptIntegrityError(f"invalid role prompt path: {role_file}")
        instructions = shared + "\n" + role_path.read_text(encoding="utf-8")
        actual_digest = sha256(instructions.encode()).hexdigest()
        expected_digest = _required_string(raw, "content_digest")
        if actual_digest != expected_digest:
            raise PromptIntegrityError(f"prompt digest mismatch: {name.value}")
        bundles[name] = PromptBundle(
            name=name,
            version=_required_string(raw, "prompt_version"),
            frozen_business_rules_version=_required_string(
                manifest, "frozen_business_rules_version"
            ),
            created_at=date.fromisoformat(_required_string(manifest, "created_at")),
            approved_for_implementation_by=_required_string(
                manifest, "approved_for_implementation_by"
            ),
            content_digest=actual_digest,
            instructions=instructions,
        )
    return bundles


def _load_manifest() -> dict[str, Any]:
    parsed = json.loads((PROMPT_DIRECTORY / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise PromptIntegrityError("prompt manifest must be an object")
    return parsed


def _required_string(values: dict[str, Any], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PromptIntegrityError(f"prompt manifest field must be a string: {key}")
    return value
