"""Strict runtime-only Stage 15 fixture loading with digest verification."""

import json
from datetime import date
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from vai_bd.domain.enums import (
    EvidenceAdmissibility,
    EvidenceCurrentness,
    EvidenceDirectness,
)
from vai_bd.domain.refs import ImmutableModel, NonEmptyStr, SourceRef


class FixtureFile(ImmutableModel):
    path: NonEmptyStr
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class RuntimeManifest(ImmutableModel):
    schema_version: Literal["1.0"]
    fixture_version: NonEmptyStr
    generated_on: date
    authorization: NonEmptyStr
    synthetic_only: Literal[True]
    source_specification: tuple[NonEmptyStr, ...]
    files: tuple[FixtureFile, ...] = Field(min_length=3)


class Stage15Observation(ImmutableModel):
    observation_id: NonEmptyStr
    claim_kind: NonEmptyStr
    content: NonEmptyStr
    source: SourceRef
    source_type: NonEmptyStr
    source_date: date | None = None
    provenance: NonEmptyStr
    directness: EvidenceDirectness
    currentness: EvidenceCurrentness
    admissibility: EvidenceAdmissibility
    restricted: bool = False
    source_dependency_group: str | None = None

    @model_validator(mode="after")
    def restricted_is_not_admissible(self) -> "Stage15Observation":
        if self.restricted and self.admissibility is EvidenceAdmissibility.ADMISSIBLE:
            raise ValueError("restricted fixture observations cannot be admissible")
        return self


class Stage15Candidate(ImmutableModel):
    case_id: NonEmptyStr
    candidate_id: UUID
    company_name: NonEmptyStr
    segment_claim: NonEmptyStr
    observations: tuple[Stage15Observation, ...] = Field(min_length=1)
    missing_material_facts: tuple[NonEmptyStr, ...] = ()
    pursuit_demand_hours: Decimal | None = Field(default=None, gt=0)
    next_action: str | None = None


class Stage15Configuration(ImmutableModel):
    operator_name: NonEmptyStr
    offer_name: NonEmptyStr
    problem_statement: NonEmptyStr
    intended_buyer_roles: tuple[NonEmptyStr, ...] = Field(min_length=1)
    fit_dimensions: tuple[NonEmptyStr, ...] = Field(min_length=1)
    target_market_boundary: NonEmptyStr
    segment_filters: tuple[NonEmptyStr, ...]
    exclusions: tuple[NonEmptyStr, ...]
    effective_date: date
    usable_time_hours: Decimal = Field(gt=0)
    planning_horizon: NonEmptyStr
    max_concurrent_pursuits: int = Field(gt=0)


class Stage15BaseFixture(ImmutableModel):
    schema_version: Literal["1.0"]
    fixture_version: NonEmptyStr
    synthetic_only: Literal[True]
    configuration: Stage15Configuration
    candidates: tuple[Stage15Candidate, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def candidate_cases_are_unique(self) -> "Stage15BaseFixture":
        case_ids = [item.case_id for item in self.candidates]
        candidate_ids = [item.candidate_id for item in self.candidates]
        if len(case_ids) != len(set(case_ids)) or len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate case and object identities must be unique")
        expected = [f"C{number:02d}" for number in range(1, 11)]
        if case_ids != expected:
            raise ValueError("base fixture must contain ordered cases C01 through C10")
        return self


class CapturedCaseOutput(ImmutableModel):
    case_id: NonEmptyStr
    referenced_observation_ids: tuple[NonEmptyStr, ...]
    missing_evidence_flags: tuple[NonEmptyStr, ...] = ()
    gate_facts: dict[str, bool | str]
    fit_judgment: str | None = None
    need_status: str | None = None
    decision_owner_status: str | None = None
    contactability: str | None = None
    qualification: str | None = None
    material_uncertainties: tuple[NonEmptyStr, ...] = ()


class CapturedPortfolioOutput(ImmutableModel):
    snapshot_members: tuple[NonEmptyStr, ...]
    comparison_order: tuple[NonEmptyStr, ...]
    pairwise_relations: tuple[tuple[NonEmptyStr, NonEmptyStr, NonEmptyStr], ...]
    allocation: dict[str, tuple[NonEmptyStr, ...]]


class CapturedAgentOutputs(ImmutableModel):
    schema_version: Literal["1.0"]
    fixture_version: NonEmptyStr
    cases: tuple[CapturedCaseOutput, ...]
    portfolio: CapturedPortfolioOutput


class Stage15Mutation(ImmutableModel):
    schema_version: Literal["1.0"]
    fixture_version: NonEmptyStr
    mutation_id: NonEmptyStr
    title: NonEmptyStr
    base_fixture_version: NonEmptyStr
    changes: dict[str, Any]


class Stage15RuntimeBundle(ImmutableModel):
    manifest: RuntimeManifest
    base: Stage15BaseFixture
    captured_outputs: CapturedAgentOutputs
    mutations: tuple[Stage15Mutation, ...]


def load_runtime_bundle(root: Path) -> Stage15RuntimeBundle:
    """Load runtime inputs without knowing or accessing any held-out oracle path."""

    manifest = RuntimeManifest.model_validate(_read_json(root / "manifest.json"))
    expected_paths = {"base.json", "captured_outputs.json"}
    expected_paths.update(f"mutations/M{number:02d}.json" for number in range(1, 10))
    declared_paths = {item.path for item in manifest.files}
    if declared_paths != expected_paths or len(manifest.files) != len(expected_paths):
        raise ValueError("runtime manifest must cover every expected file exactly once")
    for item in manifest.files:
        path = root / item.path
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != item.sha256:
            raise ValueError(f"fixture digest mismatch: {item.path}")
    base = Stage15BaseFixture.model_validate(_read_json(root / "base.json"))
    outputs = CapturedAgentOutputs.model_validate(_read_json(root / "captured_outputs.json"))
    mutations = tuple(
        Stage15Mutation.model_validate(_read_json(root / f"mutations/M{number:02d}.json"))
        for number in range(1, 10)
    )
    versions = {manifest.fixture_version, base.fixture_version, outputs.fixture_version}
    versions.update(item.fixture_version for item in mutations)
    if versions != {manifest.fixture_version}:
        raise ValueError("runtime fixture versions do not match")
    _validate_output_references(base, outputs)
    if tuple(item.mutation_id for item in mutations) != tuple(
        f"M{number:02d}" for number in range(1, 10)
    ):
        raise ValueError("runtime mutation set must contain M01 through M09")
    return Stage15RuntimeBundle(
        manifest=manifest,
        base=base,
        captured_outputs=outputs,
        mutations=mutations,
    )


def _validate_output_references(base: Stage15BaseFixture, outputs: CapturedAgentOutputs) -> None:
    observations = {
        item.observation_id for candidate in base.candidates for item in candidate.observations
    }
    cases = {candidate.case_id for candidate in base.candidates}
    if {item.case_id for item in outputs.cases} != cases:
        raise ValueError("captured outputs must cover the complete candidate universe")
    for item in outputs.cases:
        if not set(item.referenced_observation_ids).issubset(observations):
            raise ValueError(f"captured output {item.case_id} references unknown observations")
    portfolio_cases = set(outputs.portfolio.comparison_order)
    if not portfolio_cases.issubset(cases):
        raise ValueError("captured portfolio references unknown cases")


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))
