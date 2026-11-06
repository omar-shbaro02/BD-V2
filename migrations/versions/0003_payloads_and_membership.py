"""Create typed payload and immutable universe/snapshot membership."""

from alembic import op

from vai_bd.persistence.orm import (
    CandidateUniverseMemberRow,
    DomainPayloadRow,
    SnapshotMemberRow,
)

revision = "0003_payload_membership"
down_revision = "0002_dependency_edges"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in (
        DomainPayloadRow.__table__,
        CandidateUniverseMemberRow.__table__,
        SnapshotMemberRow.__table__,
    ):
        table.create(bind)


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        SnapshotMemberRow.__table__,
        CandidateUniverseMemberRow.__table__,
        DomainPayloadRow.__table__,
    ):
        table.drop(bind)
