"""Audited, idempotent specialist execution with transactional persistence callback."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from vai_bd.agents.audit import SqlAgentRunStore
from vai_bd.agents.contracts import SpecialistInput, SpecialistName, SpecialistOutput
from vai_bd.agents.definitions import SPECIALISTS
from vai_bd.agents.runner import AgentRunner
from vai_bd.agents.validation import validate_specialist_exchange
from vai_bd.domain.audit import AgentRun
from vai_bd.domain.enums import RunStatus
from vai_bd.domain.refs import ObjectRevisionRef
from vai_bd.orchestrator.idempotency import (
    IdempotencyRepository,
    IdempotencyStatus,
)
from vai_bd.persistence.repositories import AuditRepository

PersistOutput = Callable[[Session, SpecialistOutput], tuple[ObjectRevisionRef, ...]]
Mutation = Callable[[Session], tuple[ObjectRevisionRef, ...]]


@dataclass(frozen=True)
class AgentPhaseResult:
    result_refs: tuple[ObjectRevisionRef, ...]
    output: SpecialistOutput | None
    run_id: str | None
    replayed: bool


class AgentPhaseExecutionError(RuntimeError):
    """A visible, resumable specialist phase failure."""


@dataclass(frozen=True)
class MutationResult:
    result_refs: tuple[ObjectRevisionRef, ...]
    replayed: bool


class IdempotentMutationExecutor:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def execute(
        self,
        *,
        operation: str,
        idempotency_key: str,
        request_payload: object,
        mutation: Mutation,
    ) -> MutationResult:
        request_digest = sha256(
            json.dumps(request_payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        with self.session_factory.begin() as session:
            previous = IdempotencyRepository(session).claim(
                operation, idempotency_key, request_digest
            )
        if previous is not None:
            if previous.status is IdempotencyStatus.SUCCEEDED:
                return MutationResult(previous.result_refs, True)
            raise AgentPhaseExecutionError(previous.error or "previous mutation failed")
        try:
            with self.session_factory.begin() as session:
                refs = mutation(session)
                IdempotencyRepository(session).succeed(operation, idempotency_key, refs)
            return MutationResult(refs, False)
        except Exception as exc:
            with self.session_factory.begin() as session:
                IdempotencyRepository(session).fail(operation, idempotency_key, _safe_failure(exc))
            raise


class AgentPhaseExecutor:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        runner: AgentRunner,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        id_factory: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self.session_factory = session_factory
        self.runner = runner
        self.clock = clock
        self.id_factory = id_factory
        self.run_store = SqlAgentRunStore(session_factory)

    async def execute(
        self,
        *,
        operation: str,
        idempotency_key: str,
        name: SpecialistName,
        agent_input: SpecialistInput,
        persist_output: PersistOutput,
    ) -> AgentPhaseResult:
        request_digest = sha256(
            json.dumps(agent_input.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest()
        with self.session_factory.begin() as session:
            previous = IdempotencyRepository(session).claim(
                operation, idempotency_key, request_digest
            )
        if previous is not None:
            if previous.status is IdempotencyStatus.SUCCEEDED:
                return AgentPhaseResult(previous.result_refs, None, None, True)
            raise AgentPhaseExecutionError(previous.error or "previous phase attempt failed")

        prompt = SPECIALISTS[name].prompt
        started = AgentRun(
            run_id=self.id_factory(),
            agent_name=name.value,
            prompt_version=f"{prompt.version}@sha256:{prompt.content_digest}",
            model_config_id=self.runner.model_config_id,
            input_revision_refs=agent_input.exact_input_refs,
            status=RunStatus.STARTED,
            started_at=self.clock(),
        )
        try:
            self.run_store.append_started(started)
        except Exception as exc:
            with self.session_factory.begin() as session:
                IdempotencyRepository(session).fail(
                    operation,
                    idempotency_key,
                    _safe_failure(exc),
                )
            raise AgentPhaseExecutionError(f"{operation} could not start") from exc
        try:
            runner_result = await self.runner.run(name, agent_input)
            validate_specialist_exchange(name, agent_input, runner_result.output)
            with self.session_factory.begin() as session:
                refs = persist_output(session, runner_result.output)
                terminal = started.model_copy(
                    update={
                        "output_revision_refs": refs,
                        "openai_trace_ref": runner_result.trace_ref,
                        "status": RunStatus.SUCCEEDED,
                        "completed_at": self.clock(),
                        "usage_metadata": runner_result.usage_metadata,
                    }
                )
                AuditRepository(session).finalize_agent_run(terminal)
                IdempotencyRepository(session).succeed(operation, idempotency_key, refs)
            return AgentPhaseResult(refs, runner_result.output, started.run_id, False)
        except Exception as exc:
            error = _safe_failure(exc)
            with self.session_factory.begin() as session:
                IdempotencyRepository(session).fail(operation, idempotency_key, error)
                terminal = started.model_copy(
                    update={
                        "status": RunStatus.FAILED,
                        "error": error,
                        "completed_at": self.clock(),
                    }
                )
                AuditRepository(session).finalize_agent_run(terminal)
            raise AgentPhaseExecutionError(f"{operation} failed") from exc


def _safe_failure(exc: Exception) -> str:
    """Persist exception classification, never provider messages or secrets."""

    return f"{type(exc).__name__}: details redacted"
