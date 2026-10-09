# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Generic HTTP API scaffolding shared by every extension's dashboard routes.

This extension is the single source of truth for API-key authentication (see `auth.py`): any
other extension that exposes dashboard routes imports `require_api_key` from here instead of
rolling its own check. Its own `setup_webserver` only adds a `/dashboard_api/v1/health` route,
useful to verify a deployed API key works before any real route is wired up.
"""

from fastapi import APIRouter, Depends, FastAPI

from .auth import require_api_key

default = {"enabled": False}


def setup_webserver(app: FastAPI) -> None:
    router = APIRouter(prefix="/dashboard_api/v1", dependencies=[Depends(require_api_key)])

    @router.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    app.include_router(router)


__all__ = ("default", "require_api_key", "setup_webserver")
