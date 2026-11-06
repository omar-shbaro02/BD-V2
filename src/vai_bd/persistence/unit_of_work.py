"""Transaction boundary exposing governed repositories."""

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from vai_bd.persistence.repositories import (
    AuditRepository,
    AuthorizationRepository,
    ComparisonRepository,
    GovernedObjectRepository,
    SnapshotRepository,
)


class UnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self.session: Session | None = None
        self.objects: GovernedObjectRepository
        self.snapshots: SnapshotRepository
        self.comparisons: ComparisonRepository
        self.authorizations: AuthorizationRepository
        self.audit: AuditRepository

    def __enter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        self.objects = GovernedObjectRepository(self.session)
        self.snapshots = SnapshotRepository(self.session, self.objects)
        self.comparisons = ComparisonRepository(self.session, self.objects)
        self.authorizations = AuthorizationRepository(self.session, self.objects)
        self.audit = AuditRepository(self.session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.session is None:
            return
        if exc_type is None:
            self.session.commit()
        else:
            self.session.rollback()
        self.session.close()

    def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("UnitOfWork is not active")
        self.session.commit()

    def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("UnitOfWork is not active")
        self.session.rollback()
