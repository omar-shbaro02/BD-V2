"""FastAPI application entry point."""

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request

from vai_bd.api.auth import human_actor_dependency
from vai_bd.api.contracts import ApiBackend, UnconfiguredApiBackend
from vai_bd.api.errors import install_exception_handlers
from vai_bd.api.router import create_router
from vai_bd.config import Settings, get_settings
from vai_bd.operator.router import create_operator_router


def create_app(
    settings: Settings | None = None, *, api_backend: ApiBackend | None = None
) -> FastAPI:
    """Create the HTTP application without initiating external integrations."""
    resolved = settings or get_settings()
    application = FastAPI(
        title=resolved.app_name,
        version=resolved.app_version,
        description=(
            "Governed business-development decision intelligence. "
            "External commercial execution is disabled."
        ),
    )
    application.state.api_backend = api_backend or UnconfiguredApiBackend()
    install_exception_handlers(application)

    @application.middleware("http")
    async def attach_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        supplied = request.headers.get("X-Request-ID", "").strip()
        safe = supplied if supplied and len(supplied) <= 100 else str(uuid4())
        request.state.request_id = safe
        response = await call_next(request)
        response.headers["X-Request-ID"] = safe
        return response

    @application.get("/health", tags=["system"])
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": resolved.app_name,
            "version": resolved.app_version,
            "environment": resolved.app_env,
            "external_execution_allowed": False,
        }

    application.include_router(create_router(human_actor_dependency(resolved)))
    application.include_router(create_operator_router())

    return application


app = create_app()
