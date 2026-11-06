"""Create agent-run, workflow, and material-impact audit tables."""

from alembic import op

from vai_bd.persistence.orm import (
    AgentRunRow,
    ExternalExecutionDecisionRow,
    MaterialImpactDecisionRow,
    WorkflowTransitionRow,
)

revision = "0006_run_workflow_audit"
down_revision = "0005_human_authorization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in (
        AgentRunRow.__table__,
        WorkflowTransitionRow.__table__,
        MaterialImpactDecisionRow.__table__,
        ExternalExecutionDecisionRow.__table__,
    ):
        table.create(bind)


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        ExternalExecutionDecisionRow.__table__,
        MaterialImpactDecisionRow.__table__,
        WorkflowTransitionRow.__table__,
        AgentRunRow.__table__,
    ):
        table.drop(bind, checkfirst=True)
