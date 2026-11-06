"""Create durable orchestration idempotency records."""

from alembic import op

from vai_bd.persistence.orm import IdempotencyRecordRow

revision = "0008_idempotency_records"
down_revision = "0007_conformity_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    IdempotencyRecordRow.__table__.create(op.get_bind())


def downgrade() -> None:
    IdempotencyRecordRow.__table__.drop(op.get_bind())
