"""Stable, redacted API errors and exception mapping."""

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from vai_bd.agents.validation import SemanticGuardrailError
from vai_bd.orchestrator.dependencies import PhasePreconditionError
from vai_bd.orchestrator.idempotency import (
    IdempotencyConflictError,
    OperationInProgressError,
)
from vai_bd.orchestrator.state import InvalidWorkflowTransitionError
from vai_bd.persistence.repositories import MissingRevisionError, RevisionConflictError
from vai_bd.services.common import ServiceConflictError
from vai_bd.services.executor import AgentPhaseExecutionError


class ApiError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", uuid4()))


def error_body(request: Request, code: str, message: str, details: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {"code": code, "message": message, "request_id": request_id(request)}
    }
    if details is not None:
        body["error"]["details"] = details
    return body


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            content=error_body(request, exc.code, exc.message), status_code=exc.status_code
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
            for item in exc.errors()
        ]
        return JSONResponse(
            content=error_body(request, "request_validation_failed", "Invalid request", details),
            status_code=422,
        )

    mappings: tuple[tuple[type[Exception], int, str, str], ...] = (
        (MissingRevisionError, 404, "missing_revision", "An exact revision was not found"),
        (RevisionConflictError, 409, "revision_conflict", "Revision conflict"),
        (ServiceConflictError, 409, "service_conflict", "Current state conflict"),
        (
            InvalidWorkflowTransitionError,
            409,
            "workflow_transition_conflict",
            "Workflow transition conflict",
        ),
        (IdempotencyConflictError, 409, "idempotency_conflict", "Idempotency conflict"),
        (OperationInProgressError, 409, "operation_in_progress", "Operation is in progress"),
        (PhasePreconditionError, 409, "phase_precondition_failed", "Phase precondition failed"),
        (SemanticGuardrailError, 422, "specialist_contract_failed", "Specialist output rejected"),
        (AgentPhaseExecutionError, 502, "agent_phase_failed", "Specialist phase failed"),
        (ValueError, 422, "policy_rejected", "Request was rejected by governed policy"),
    )
    for exception_type, status, code, message in mappings:

        async def mapped(
            request: Request,
            _exc: Exception,
            status_code: int = status,
            error_code: str = code,
            safe_message: str = message,
        ) -> JSONResponse:
            return JSONResponse(
                content=error_body(request, error_code, safe_message),
                status_code=status_code,
            )

        app.add_exception_handler(exception_type, mapped)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            content=error_body(request, "internal_error", "Internal service failure"),
            status_code=500,
        )
