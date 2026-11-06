"""Application health endpoint tests."""

from fastapi.testclient import TestClient

from vai_bd.config import AppEnvironment, Settings
from vai_bd.main import create_app


def test_health_reports_safe_runtime_state() -> None:
    app = create_app(Settings(_env_file=None, app_env=AppEnvironment.TEST))
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "VAI Business Development Decision Intelligence",
        "version": "0.1.0.dev0",
        "environment": "test",
        "external_execution_allowed": False,
    }
