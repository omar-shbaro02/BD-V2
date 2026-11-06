"""Create exact dependency and supersession edges."""

from alembic import op

from vai_bd.persistence.orm import DependencyRow, SupersessionRow

revision = "0002_dependency_edges"
down_revision = "0001_core_revisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    DependencyRow.__table__.create(bind)
    SupersessionRow.__table__.create(bind)


def downgrade() -> None:
    bind = op.get_bind()
    SupersessionRow.__table__.drop(bind)
    DependencyRow.__table__.drop(bind)
