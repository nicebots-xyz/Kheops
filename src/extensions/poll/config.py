# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, field_validator


class PollConfig(BaseModel):
    """Configuration of the poll extension.

    Attributes:
        enabled: Whether the extension is loaded.
        timezone: IANA timezone the end dates typed in the builder are expressed in.

    """

    enabled: bool = True
    timezone: str = "Europe/Paris"

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise ValueError(f"Unknown timezone {v!r}") from e
        return v

    @property
    def tz(self) -> ZoneInfo:
        """The configured timezone as a `ZoneInfo`."""
        return ZoneInfo(self.timezone)
