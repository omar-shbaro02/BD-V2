"""Create conformity result storage and indexes."""

from alembic import op

from vai_bd.persistence.orm import ConformityCaseResultRow

revision = "0007_conformity_results"
down_revision = "0006_run_workflow_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ConformityCaseResultRow.__table__.create(op.get_bind())


def downgrade() -> None:
    ConformityCaseResultRow.__table__.drop(op.get_bind())
