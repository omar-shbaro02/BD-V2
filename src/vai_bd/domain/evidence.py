"""Evidence and minimum-eligibility control contracts."""

from datetime import date, datetime

from pydantic import field_validator, model_validator

from vai_bd.domain.enums import (
    BlockingScope,
    EvidenceAdmissibility,
    EvidenceCurrentness,
    EvidenceDirectness,
    GateOutcome,
)
from vai_bd.domain.envelopes import GovernedObject
from vai_bd.domain.refs import ImmutableModel, NonEmptyStr, ObjectRevisionRef, SourceRef


class EvidenceRecord(GovernedObject):
    candidate_ref: ObjectRevisionRef
    claim_text: NonEmptyStr
    source: SourceRef
    source_type: NonEmptyStr
    source_date: date | None = None
    observed_at: datetime
    provenance: NonEmptyStr
    directness: EvidenceDirectness
    currentness: EvidenceCurrentness
    source_dependency_group: str | None = None
    contradicts: tuple[ObjectRevisionRef, ...] = ()
    admissibility: EvidenceAdmissibility

    @field_validator("observed_at")
    @classmethod
    def observed_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def evidence_cannot_contradict_itself(self) -> "EvidenceRecord":
        if any(ref.object_id == self.object_id for ref in self.contradicts):
            raise ValueError("evidence cannot contradict itself")
        return self


class MissingEvidenceFlag(ImmutableModel):
    candidate_ref: ObjectRevisionRef
    missing_claim_or_fact: NonEmptyStr
    why_material: NonEmptyStr
    investigation_action: NonEmptyStr


class ContradictionGroup(ImmutableModel):
    group_id: NonEmptyStr
    evidence_refs: tuple[ObjectRevisionRef, ...]
    material_reason: NonEmptyStr

    @model_validator(mode="after")
    def require_multiple_evidence_records(self) -> "ContradictionGroup":
        if len(self.evidence_refs) < 2:
            raise ValueError("a contradiction group requires at least two records")
        return self


class MinimumEvidenceHardEligibilityGateResult(GovernedObject):
    candidate_ref: ObjectRevisionRef
    decision_cycle_ref: ObjectRevisionRef
    outcome: GateOutcome
    reasons: tuple[NonEmptyStr, ...]
    blocking_scope: BlockingScope

    @model_validator(mode="after")
    def require_reason(self) -> "MinimumEvidenceHardEligibilityGateResult":
        if not self.reasons:
            raise ValueError("gate results require at least one reason")
        return self
