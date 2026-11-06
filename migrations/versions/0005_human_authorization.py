"""Create append-only human authorization history."""

from alembic import op

from vai_bd.persistence.orm import HumanAuthorizationEventRow

revision = "0005_human_authorization"
down_revision = "0004_comparison_allocation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    HumanAuthorizationEventRow.__table__.create(op.get_bind())


def downgrade() -> None:
    HumanAuthorizationEventRow.__table__.drop(op.get_bind())
