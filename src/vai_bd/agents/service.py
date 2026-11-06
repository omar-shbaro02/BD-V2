"""Shared governed run pipeline for all five specialist agents."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from vai_bd.agents.contracts import SpecialistInput, SpecialistName, SpecialistOutput
from vai_bd.agents.definitions import SPECIALISTS
from vai_bd.agents.mapping import PendingDomainCommand, map_output_to_commands
from vai_bd.agents.runner import AgentRunner
from vai_bd.agents.validation import validate_specialist_exchange
from vai_bd.domain.audit import AgentRun
from vai_bd.domain.enums import RunStatus
from vai_bd.domain.refs import ObjectRevisionRef


class AgentRunStore(Protocol):
    def append_started(self, run: AgentRun) -> None: ...

    def finalize(self, run: AgentRun) -> None: ...


class CommandStore(Protocol):
    def persist_batch(
        self, commands: tuple[PendingDomainCommand, ...]
    ) -> tuple[ObjectRevisionRef, ...]: ...


class SpecialistRunFailed(RuntimeError):
    """A specialist run failed before validated state could be persisted."""


class SpecialistService:
    def __init__(
        self,
        runner: AgentRunner,
        run_store: AgentRunStore,
        command_store: CommandStore,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        id_factory: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self.runner = runner
        self.run_store = run_store
        self.command_store = command_store
        self.clock = clock
        self.id_factory = id_factory

    async def invoke(self, name: SpecialistName, agent_input: SpecialistInput) -> SpecialistOutput:
        started = AgentRun(
            run_id=self.id_factory(),
            agent_name=name.value,
            prompt_version=(
                f"{SPECIALISTS[name].prompt.version}@sha256:"
                f"{SPECIALISTS[name].prompt.content_digest}"
            ),
            model_config_id=self.runner.model_config_id,
            input_revision_refs=agent_input.exact_input_refs,
            status=RunStatus.STARTED,
            started_at=self.clock(),
        )
        self.run_store.append_started(started)
        try:
            result = await self.runner.run(name, agent_input)
            validate_specialist_exchange(name, agent_input, result.output)
            commands = map_output_to_commands(result.output)
            output_refs = self.command_store.persist_batch(commands)
        except Exception as exc:
            failed = started.model_copy(
                update={
                    "status": RunStatus.FAILED,
                    "error": _safe_failure(exc),
                    "completed_at": self.clock(),
                }
            )
            self.run_store.finalize(failed)
            raise SpecialistRunFailed(f"{name.value} run failed") from exc
        completed = started.model_copy(
            update={
                "output_revision_refs": output_refs,
                "openai_trace_ref": result.trace_ref,
                "status": RunStatus.SUCCEEDED,
                "completed_at": self.clock(),
                "usage_metadata": result.usage_metadata,
            }
        )
        self.run_store.finalize(completed)
        return result.output


def _safe_failure(exc: Exception) -> str:
    """Retain a useful failure class without persisting provider/error payloads."""

    return f"{type(exc).__name__}: details redacted"


class InMemoryAgentRunStore:
    def __init__(self) -> None:
        self.runs: dict[str, AgentRun] = {}

    def append_started(self, run: AgentRun) -> None:
        if run.run_id in self.runs or run.status is not RunStatus.STARTED:
            raise ValueError("run must be a new STARTED record")
        self.runs[run.run_id] = run

    def finalize(self, run: AgentRun) -> None:
        current = self.runs.get(run.run_id)
        if current is None or current.status is not RunStatus.STARTED:
            raise ValueError("only a STARTED run may be finalized")
        if run.status is RunStatus.STARTED:
            raise ValueError("finalized run must be terminal")
        self.runs[run.run_id] = run


class InMemoryCommandStore:
    """Atomic test store: a rejected batch leaves no pending domain state."""

    def __init__(self) -> None:
        self.batches: list[tuple[PendingDomainCommand, ...]] = []

    def persist_batch(
        self, commands: tuple[PendingDomainCommand, ...]
    ) -> tuple[ObjectRevisionRef, ...]:
        self.batches.append(commands)
        return ()
