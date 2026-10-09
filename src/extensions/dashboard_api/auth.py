# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Shared bearer-token authentication for every dashboard API route.

The site's own backend calls this bot's API server-to-server (no browser, no user session), so a
single pre-shared key proves the caller is that backend. The key itself is never stored, only its
SHA-256 hash (see `config.py`) — generated and rotated by whoever issues the key, not by this bot.
Any extension that exposes dashboard routes should depend on `require_api_key` from here instead
of re-implementing the check, so auth stays consistent across extensions.
"""

from __future__ import annotations

import hashlib
import hmac
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import config

from .config import DashboardApiConfig

_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _load_config() -> DashboardApiConfig:
    _, raw = config.get_extension("dashboard_api", {"enabled": False})
    return DashboardApiConfig.model_validate(raw)


def require_api_key(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> None:
    """Raise unless `credentials` carries a key matching a configured hash.

    503 means the dashboard API has no key configured yet (nothing *can* authenticate); 401 means
    a key was expected but is missing or wrong.
    """
    dashboard_config = _load_config()
    if not dashboard_config.api_key_hashes:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Dashboard API has no key configured")
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Missing bearer token", headers={"WWW-Authenticate": "Bearer"}
        )
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    if not any(hmac.compare_digest(token_hash, known) for known in dashboard_config.api_key_hashes):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key", headers={"WWW-Authenticate": "Bearer"})


__all__ = ("require_api_key",)
