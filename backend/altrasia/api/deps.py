from __future__ import annotations

from fastapi import Header, HTTPException, Request

from altrasia.config import Settings
from altrasia.services import AppServices


def get_services(request: Request) -> AppServices:
    return request.app.state.services


def verify_auth(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    settings: Settings = request.app.state.settings
    if not settings.api_token:
        return
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        if token == settings.api_token:
            return
    raise HTTPException(status_code=401, detail="unauthorized")
