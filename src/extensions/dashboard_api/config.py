# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from pydantic import BaseModel, field_validator


class DashboardApiConfig(BaseModel):
    enabled: bool = False
    api_key_hashes: list[str] = []

    @field_validator("api_key_hashes", mode="before")
    @classmethod
    def _coerce_single_hash(cls, value: object) -> object:
        """Accept a bare string as a one-item list.

        Lets a single Docker/Kubernetes secret file (one hash, no JSON array) populate this field
        without any code change on the config-loading side, same as a YAML/env list would.
        """
        if isinstance(value, str):
            return [value]
        return value


__all__ = ("DashboardApiConfig",)
