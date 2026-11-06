"""PostgreSQL-backed specialist run lifecycle audit adapter."""

from sqlalchemy.orm import Session, sessionmaker

from vai_bd.domain.audit import AgentRun
from vai_bd.persistence.repositories import AuditRepository


class SqlAgentRunStore:
    """Commit STARTED immediately, then commit exactly one terminal transition."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def append_started(self, run: AgentRun) -> None:
        with self._session_factory.begin() as session:
            AuditRepository(session).append_agent_run(run)

    def finalize(self, run: AgentRun) -> None:
        with self._session_factory.begin() as session:
            AuditRepository(session).finalize_agent_run(run)
