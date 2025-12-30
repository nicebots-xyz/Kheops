# Copyright (c) Communauté Les Frères Poulain
# SPDX-License-Identifier: MIT

from datetime import time
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, field_validator

EUROPE_PARIS = ZoneInfo("Europe/Paris")


def parse_time_field(v: Any, field_name: str) -> time:
    if isinstance(v, str):
        try:
            hours, minutes = map(int, v.split(":"))
            return time(hour=hours, minute=minutes, tzinfo=EUROPE_PARIS)
        except ValueError as e:
            raise ValueError("Time must be in HH:MM format") from e
    elif isinstance(v, time):
        return v
    raise TypeError(f"{field_name} must be a string or a time object")


class AfkNotifConfig(BaseModel):
    start_time: time
    stop_time: time
    afk_reminder_every: int
    afk_reminder_timeout: int
    guild_id: int
    role_id: int | None = None

    @field_validator("start_time", mode="before")
    @classmethod
    def parse_start_time(cls, v: Any) -> time:
        return parse_time_field(v, "start_time")

    @field_validator("stop_time", mode="before")
    @classmethod
    def parse_stop_time(cls, v: Any) -> time:
        return parse_time_field(v, "stop_time")
