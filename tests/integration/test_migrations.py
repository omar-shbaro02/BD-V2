"""Migration-chain verification."""

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect

TEST_DATABASE_URL = "postgresql+psycopg://vai_bd:vai_bd@localhost:5432/vai_bd"


def test_all_migrations_reach_expected_head(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == (
            "0008_idempotency_records"
        )


def test_all_required_tables_exist(migrated_engine: Engine) -> None:
    expected = {
        "actors",
        "object_identities",
        "object_revisions",
        "object_dependencies",
        "object_supersessions",
        "domain_payloads",
        "candidate_universe_members",
        "snapshot_members",
        "canonical_comparisons",
        "allocation_members",
        "human_authorization_events",
        "agent_runs",
        "workflow_transitions",
        "material_impact_decisions",
        "external_execution_decisions",
        "conformity_case_results",
        "idempotency_records",
    }
    assert expected <= set(inspect(migrated_engine).get_table_names())


def test_previous_revision_upgrades_to_head(migrated_engine: Engine) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.downgrade(config, "0007_conformity_results")
    with migrated_engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == (
            "0007_conformity_results"
        )
        assert "idempotency_records" not in inspect(connection).get_table_names()
    command.upgrade(config, "head")
    with migrated_engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == (
            "0008_idempotency_records"
        )
        assert "idempotency_records" in inspect(connection).get_table_names()
