"""PostgreSQL persistence coverage for complete conformity reports."""

from pathlib import Path

from scripts.run_stage15_conformity import load_expected_results
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vai_bd.conformity import (
    evaluate_conformity,
    execute_stage15_runtime,
    load_runtime_bundle,
    persist_conformity_report,
    serialize_runtime_execution,
)
from vai_bd.persistence.orm import ConformityCaseResultRow
from vai_bd.persistence.repositories import AuditRepository

ROOT = Path(__file__).resolve().parents[2]


def test_complete_conformity_report_is_append_only_persisted(db_session: Session) -> None:
    runtime = load_runtime_bundle(ROOT / "tests" / "fixtures" / "stage15")
    execution = execute_stage15_runtime(runtime)
    assert serialize_runtime_execution(execution)
    expectations, rules = load_expected_results()
    report = evaluate_conformity(
        execution,
        expectations,
        rules,
        code_version="test-working-tree",
        prompt_versions={"captured-test-double": runtime.manifest.fixture_version},
        model_config_id="deterministic-captured-fixture",
    )

    repository = AuditRepository(db_session)
    persist_conformity_report(report, repository.append_conformity_result)

    count = db_session.scalar(select(func.count()).select_from(ConformityCaseResultRow))
    stored_ids = db_session.scalars(
        select(ConformityCaseResultRow.case_id).order_by(ConformityCaseResultRow.result_id)
    ).all()
    assert count == 20
    assert tuple(stored_ids) == report.required_case_ids
