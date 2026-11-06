"""Concurrency, rollback, idempotency, and failure-injection hardening."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from threading import Event
from uuid import UUID

import pytest
from sqlalchemy import Engine, func, select

from vai_bd.domain.enums import ActorKind
from vai_bd.orchestrator.idempotency import (
    IdempotencyRepository,
    IdempotencyStatus,
    OperationInProgressError,
)
from vai_bd.persistence.database import create_session_factory
from vai_bd.persistence.orm import ActorRow, IdempotencyRecordRow
from vai_bd.services.executor import AgentPhaseExecutionError, IdempotentMutationExecutor


def test_concurrent_idempotency_claim_has_one_winner(migrated_engine: Engine) -> None:
    factory = create_session_factory(migrated_engine)
    claimed = Event()
    second_attempting = Event()
    release = Event()
    operation = "hardening-concurrent-claim"
    key = "same-key"
    digest = sha256(b"same request").hexdigest()

    def first_claim() -> None:
        with factory.begin() as session:
            assert IdempotencyRepository(session).claim(operation, key, digest) is None
            claimed.set()
            assert release.wait(timeout=5)

    def competing_claim() -> None:
        assert claimed.wait(timeout=5)
        second_attempting.set()
        with factory.begin() as session:
            IdempotencyRepository(session).claim(operation, key, digest)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(first_claim)
        assert claimed.wait(timeout=5)
        second = pool.submit(competing_claim)
        assert second_attempting.wait(timeout=5)
        release.set()
        first.result(timeout=5)
        with pytest.raises(OperationInProgressError):
            second.result(timeout=5)

    with factory() as session:
        count = session.scalar(
            select(func.count())
            .select_from(IdempotencyRecordRow)
            .where(
                IdempotencyRecordRow.operation == operation,
                IdempotencyRecordRow.idempotency_key == key,
            )
        )
        assert count == 1


def test_failed_mutation_rolls_back_and_persists_only_redacted_failure(
    migrated_engine: Engine,
) -> None:
    factory = create_session_factory(migrated_engine)
    executor = IdempotentMutationExecutor(factory)
    actor_id = UUID("91000000-0000-0000-0000-000000000001")
    operation = "hardening-failure-injection"

    def fail_after_write(session):  # type: ignore[no-untyped-def]
        session.add(
            ActorRow(
                actor_id=actor_id,
                actor_kind=ActorKind.SYSTEM.value,
                display_name="Must roll back",
            )
        )
        session.flush()
        raise RuntimeError("provider-secret-must-not-persist")

    with pytest.raises(RuntimeError, match="provider-secret"):
        executor.execute(
            operation=operation,
            idempotency_key="failed-attempt",
            request_payload={"case": "failure"},
            mutation=fail_after_write,
        )

    with factory() as session:
        assert session.get(ActorRow, actor_id) is None
        record = session.get(IdempotencyRecordRow, (operation, "failed-attempt"))
        assert record is not None
        assert record.status == IdempotencyStatus.FAILED.value
        assert record.error == "RuntimeError: details redacted"
        assert "provider-secret" not in (record.error or "")

    with pytest.raises(AgentPhaseExecutionError, match="details redacted"):
        executor.execute(
            operation=operation,
            idempotency_key="failed-attempt",
            request_payload={"case": "failure"},
            mutation=lambda _session: (),
        )

    result = executor.execute(
        operation=operation,
        idempotency_key="safe-retry",
        request_payload={"case": "failure"},
        mutation=lambda _session: (),
    )
    assert result.result_refs == ()
    assert result.replayed is False
