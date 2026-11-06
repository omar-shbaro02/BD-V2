"""Create canonical comparisons and allocation membership."""

from alembic import op

from vai_bd.persistence.orm import AllocationMemberRow, CanonicalComparisonRow

revision = "0004_comparison_allocation"
down_revision = "0003_payload_membership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    CanonicalComparisonRow.__table__.create(bind)
    AllocationMemberRow.__table__.create(bind)


def downgrade() -> None:
    bind = op.get_bind()
    AllocationMemberRow.__table__.drop(bind)
    CanonicalComparisonRow.__table__.drop(bind)
