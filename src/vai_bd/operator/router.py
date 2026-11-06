"""Read-only server-rendered operator routes."""

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from vai_bd.api.contracts import ApiBackend
from vai_bd.operator.render import render_cycle_detail, render_cycle_list


def create_operator_router() -> APIRouter:
    router = APIRouter(prefix="/operator", tags=["operator"])

    def backend(request: Request) -> ApiBackend:
        return cast(ApiBackend, request.app.state.api_backend)

    Backend = Annotated[ApiBackend, Depends(backend)]

    @router.get("", response_class=HTMLResponse, include_in_schema=False)
    async def cycle_list(service: Backend) -> HTMLResponse:
        return HTMLResponse(render_cycle_list(await service.list_operator_cycles()))

    @router.get("/cycles/{cycle_id}", response_class=HTMLResponse, include_in_schema=False)
    async def cycle_detail(cycle_id: UUID, service: Backend) -> HTMLResponse:
        return HTMLResponse(render_cycle_detail(await service.operator_view(cycle_id)))

    return router
