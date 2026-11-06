"""Fail-closed signed test authentication adapter."""

import hmac
from hashlib import sha256
from uuid import UUID

from fastapi import Header

from vai_bd.api.errors import ApiError
from vai_bd.config import AppEnvironment, Settings
from vai_bd.domain.enums import ActorKind
from vai_bd.domain.refs import ActorRef


def test_signature(key: str, actor_id: UUID, display_name: str) -> str:
    message = f"{actor_id}:{display_name}".encode()
    return hmac.new(key.encode(), message, sha256).hexdigest()


def human_actor_dependency(settings: Settings):  # type: ignore[no-untyped-def]
    async def authenticated_human(
        actor_id: str | None = Header(default=None, alias="X-Test-Actor-Id"),
        display_name: str | None = Header(default=None, alias="X-Test-Actor-Name"),
        signature: str | None = Header(default=None, alias="X-Test-Auth-Signature"),
        actor_kind: str | None = Header(default=None, alias="X-Test-Actor-Kind"),
    ) -> ActorRef:
        if settings.app_env not in {AppEnvironment.TEST, AppEnvironment.CONFORMITY}:
            raise ApiError(
                401, "authentication_unavailable", "No authentication adapter configured"
            )
        if actor_kind is not None and actor_kind != ActorKind.HUMAN.value:
            raise ApiError(403, "human_authority_required", "Human authority is required")
        if not settings.test_auth_signing_key or not actor_id or not display_name or not signature:
            raise ApiError(401, "authentication_required", "Signed test authentication is required")
        try:
            parsed_id = UUID(actor_id)
        except ValueError as exc:
            raise ApiError(401, "invalid_authentication", "Invalid authentication") from exc
        expected = test_signature(settings.test_auth_signing_key, parsed_id, display_name)
        if not hmac.compare_digest(signature, expected):
            raise ApiError(401, "invalid_authentication", "Invalid authentication")
        return ActorRef(
            actor_id=parsed_id,
            actor_kind=ActorKind.HUMAN,
            display_name=display_name,
        )

    return authenticated_human
