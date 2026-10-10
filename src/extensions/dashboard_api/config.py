# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from pydantic import BaseModel


class DashboardApiConfig(BaseModel):
    enabled: bool = False
    api_key_hashes: list[str] = []


__all__ = ("DashboardApiConfig",)
