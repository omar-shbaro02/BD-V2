"""Database ownership and failure cleanup for the parent npm launcher."""

from unittest.mock import Mock

import pytest
from scripts import dev

from vai_bd.config import Settings


@pytest.fixture
def lifecycle(monkeypatch: pytest.MonkeyPatch) -> dict[str, Mock]:
    settings = Settings(
        _env_file=None, database_url="postgresql+psycopg://vai_bd:vai_bd@localhost:5432/vai_bd"
    )
    mocks = {
        "ready": Mock(return_value=True),
        "start": Mock(),
        "compose_ps": Mock(return_value=""),
        "compose_stop": Mock(),
        "migrate": Mock(),
        "server": Mock(started=True),
    }
    monkeypatch.setattr(dev, "get_settings", lambda: settings)
    monkeypatch.setattr(dev, "database_ready", mocks["ready"])
    monkeypatch.setattr(dev, "start_database", mocks["start"])
    monkeypatch.setattr(dev.subprocess, "check_output", mocks["compose_ps"])
    monkeypatch.setattr(dev.subprocess, "run", mocks["compose_stop"])
    monkeypatch.setattr(dev.command, "upgrade", mocks["migrate"])
    monkeypatch.setattr(dev.uvicorn, "Server", lambda config: mocks["server"])
    monkeypatch.setattr(dev.threading.Thread, "start", lambda self: None)
    monkeypatch.setattr(dev.shutil, "which", lambda name: "docker")
    # Do not change the test process's own signal handlers.
    monkeypatch.setattr(dev.signal, "signal", Mock())
    return mocks


def test_existing_database_is_reused_without_compose(lifecycle: dict[str, Mock]) -> None:
    assert dev.run(0) == 0
    lifecycle["start"].assert_not_called()
    lifecycle["compose_stop"].assert_not_called()
    lifecycle["migrate"].assert_called_once()
    lifecycle["server"].run.assert_called_once()


@pytest.mark.parametrize("failure", [False, True])
def test_owned_database_is_stopped_on_exit_and_failure(
    lifecycle: dict[str, Mock], failure: bool
) -> None:
    lifecycle["ready"].side_effect = [False, True]
    if failure:
        lifecycle["migrate"].side_effect = RuntimeError("migration failure")
        with pytest.raises(RuntimeError, match="migration failure"):
            dev.run(0)
    else:
        assert dev.run(0) == 0
    lifecycle["start"].assert_called_once()
    lifecycle["compose_stop"].assert_called_once_with(
        dev.compose("stop", "db"), cwd=dev.ROOT, check=True, timeout=30
    )


def test_running_compose_database_is_never_stopped(lifecycle: dict[str, Mock]) -> None:
    lifecycle["ready"].side_effect = [False, True]
    lifecycle["compose_ps"].return_value = "existing-container"
    assert dev.run(0) == 0
    lifecycle["compose_stop"].assert_not_called()


def test_compose_start_failure_still_cleans_up(lifecycle: dict[str, Mock]) -> None:
    lifecycle["ready"].return_value = False
    lifecycle["start"].side_effect = RuntimeError("startup failure")
    with pytest.raises(RuntimeError, match="startup failure"):
        dev.run(0)
    lifecycle["compose_stop"].assert_called_once()
    lifecycle["server"].run.assert_not_called()


def test_custom_database_never_triggers_local_compose(
    lifecycle: dict[str, Mock], monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://host/custom")
    monkeypatch.setattr(dev, "get_settings", lambda: settings)
    lifecycle["ready"].return_value = False
    with pytest.raises(RuntimeError, match="Cannot connect"):
        dev.run(0)
    lifecycle["start"].assert_not_called()
    lifecycle["compose_stop"].assert_not_called()


def test_occupied_port_fails_before_migrations(lifecycle: dict[str, Mock]) -> None:
    import socket

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        with pytest.raises(OSError):
            dev.run(listener.getsockname()[1])
    lifecycle["migrate"].assert_not_called()
    lifecycle["start"].assert_not_called()
