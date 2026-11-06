"""Create actors, identities, and immutable revision envelopes."""

from alembic import op

from vai_bd.persistence.orm import ActorRow, ObjectIdentityRow, ObjectRevisionRow

revision = "0001_core_revisions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in (ActorRow.__table__, ObjectIdentityRow.__table__, ObjectRevisionRow.__table__):
        table.create(bind)


def downgrade() -> None:
    bind = op.get_bind()
    for table in (ObjectRevisionRow.__table__, ObjectIdentityRow.__table__, ActorRow.__table__):
        table.drop(bind)
