"""Durable idempotency claims for mutation and specialist-run services."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from vai_bd.domain.refs import ObjectRevisionRef
from vai_bd.persistence.orm import IdempotencyRecordRow


class IdempotencyStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class IdempotencyConflictError(RuntimeError):
    """The same key was reused for different request content."""


class OperationInProgressError(RuntimeError):
    """A matching operation is already in progress."""


@dataclass(frozen=True)
class IdempotencyResult:
    status: IdempotencyStatus
    result_refs: tuple[ObjectRevisionRef, ...]
    error: str | None = None


class IdempotencyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def claim(self, operation: str, key: str, request_digest: str) -> IdempotencyResult | None:
        if not operation.strip() or not key.strip() or len(request_digest) != 64:
            raise ValueError("operation, idempotency key, and SHA-256 request digest are required")
        inserted = self.session.scalar(
            insert(IdempotencyRecordRow)
            .values(
                operation=operation,
                idempotency_key=key,
                request_digest=request_digest,
                status=IdempotencyStatus.IN_PROGRESS.value,
                result_revision_refs=[],
                started_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(index_elements=("operation", "idempotency_key"))
            .returning(IdempotencyRecordRow.operation)
        )
        if inserted is not None:
            return None
        row = self.session.get(IdempotencyRecordRow, (operation, key), with_for_update=True)
        if row is None:
            raise OperationInProgressError("matching operation claim is not yet visible")
        if row.request_digest != request_digest:
            raise IdempotencyConflictError("idempotency key was reused with a different request")
        status = IdempotencyStatus(row.status)
        if status is IdempotencyStatus.IN_PROGRESS:
            raise OperationInProgressError("matching operation is already in progress")
        return IdempotencyResult(
            status=status,
            result_refs=tuple(
                ObjectRevisionRef.model_validate(item) for item in row.result_revision_refs
            ),
            error=row.error,
        )

    def succeed(
        self,
        operation: str,
        key: str,
        result_refs: tuple[ObjectRevisionRef, ...],
    ) -> None:
        row = self._in_progress(operation, key)
        row.status = IdempotencyStatus.SUCCEEDED.value
        row.result_revision_refs = [ref.model_dump(mode="json") for ref in result_refs]
        row.completed_at = datetime.now(UTC)
        self.session.flush()

    def fail(self, operation: str, key: str, error: str) -> None:
        if not error.strip():
            raise ValueError("failed operation requires an error")
        row = self._in_progress(operation, key)
        row.status = IdempotencyStatus.FAILED.value
        row.error = error
        row.completed_at = datetime.now(UTC)
        self.session.flush()

    def _in_progress(self, operation: str, key: str) -> IdempotencyRecordRow:
        row = self.session.get(IdempotencyRecordRow, (operation, key), with_for_update=True)
        if row is None or row.status != IdempotencyStatus.IN_PROGRESS.value:
            raise IdempotencyConflictError("operation is not in progress")
        return row
