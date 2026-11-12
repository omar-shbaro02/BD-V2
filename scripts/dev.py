"""Run the existing operator UI/API and manage only the database we start."""

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from vai_bd.config import Settings, get_settings

ROOT = Path(__file__).resolve().parents[1]


def database_ready(settings: Settings) -> bool:
    engine = create_engine(settings.database_url, connect_args={"connect_timeout": 2})
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        engine.dispose()


def uses_compose_database(settings: Settings) -> bool:
    from sqlalchemy.engine import make_url

    url = make_url(settings.database_url)
    return (
        url.host in {"localhost", "127.0.0.1", "::1"}
        and url.port in {None, 5432}
        and url.database == "vai_bd"
        and url.username == "vai_bd"
        and url.password == "vai_bd"
    )


def compose(*args: str) -> list[str]:
    return ["docker", "compose", "--file", str(ROOT / "docker-compose.yml"), *args]


def start_database(stopping: threading.Event) -> None:
    process = subprocess.Popen(
        compose("up", "--detach", "--wait", "--wait-timeout", "60", "db"), cwd=ROOT
    )
    try:
        while process.poll() is None:
            if stopping.wait(0.1):
                return
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, process.args)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def run(port: int) -> int:
    os.chdir(ROOT)  # Reuse the existing .env, migration paths and app configuration.
    settings = get_settings()
    stopping = threading.Event()
    server = uvicorn.Server(
        uvicorn.Config("vai_bd.main:app", host="127.0.0.1", port=port, timeout_graceful_shutdown=10)
    )

    def stop(*_args: object) -> None:
        stopping.set()
        server.should_exit = True

    def control_pipe() -> None:
        # EOF also handles an unexpectedly exiting Node launcher.
        sys.stdin.buffer.read()
        stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, stop)
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, stop)
    threading.Thread(target=control_pipe, daemon=True).start()

    started_database = False
    try:
        # Fail before database mutations if another app already owns the port.
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", port))

        if stopping.is_set():
            return 0
        if not database_ready(settings):
            if stopping.is_set():
                return 0
            if not uses_compose_database(settings):
                raise RuntimeError(
                    "Cannot connect to DATABASE_URL. Start the configured PostgreSQL server."
                )
            if not shutil.which("docker"):
                raise RuntimeError(
                    "PostgreSQL is unavailable and Docker Compose is not installed. "
                    "Start Docker Desktop or configure DATABASE_URL in BD-V2/.env."
                )
            running = subprocess.check_output(
                compose("ps", "--status", "running", "--quiet", "db"),
                cwd=ROOT,
                text=True,
                timeout=15,
            ).strip()
            started_database = not bool(running)
            start_database(stopping)
            if stopping.is_set():
                return 0
            if not database_ready(settings):
                raise RuntimeError("PostgreSQL started but DATABASE_URL is not reachable.")

        if stopping.is_set():
            return 0
        print("Applying existing Alembic migrations...", flush=True)
        command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
        if stopping.is_set():
            return 0
        # Alembic's logging config disables existing loggers. Restore Uvicorn's
        # normal startup/access/shutdown logging after migrations have finished.
        server.config.configure_logging()
        print(f"Operator UI: http://127.0.0.1:{port}/operator", flush=True)
        print(f"API docs:    http://127.0.0.1:{port}/docs", flush=True)
        print("Press Ctrl+C to stop. Existing application service wiring is unchanged.", flush=True)
        server.run()
        return 0 if server.started else 1
    finally:
        if started_database:
            # Never remove the container/volume, or stop a pre-existing service.
            subprocess.run(compose("stop", "db"), cwd=ROOT, check=True, timeout=30)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        raise SystemExit(run(args.port))
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Development startup failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
