# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Pydantic request/response models for the member_activity dashboard API routes."""

from datetime import date

from pydantic import BaseModel, Field

from .logic import StatsPeriod

#: Discord channel-select menus cap at 25 options — the config panel can't render/save more than
#: that, so the dashboard shouldn't be able to persist settings it can't display either.
MAX_SETTINGS_IDS = 25


class MemberStatsResponse(BaseModel):
    member_id: int
    period: StatsPeriod
    messages: int
    voice_minutes: float


class DailyHistoryEntry(BaseModel):
    day: date
    messages: int
    voice_minutes: float


class MemberHistoryResponse(BaseModel):
    member_id: int
    start: date
    end: date
    days: list[DailyHistoryEntry]


class MemberActivitySettingsResponse(BaseModel):
    message_channel_ids: list[int]
    voice_channel_ids: list[int]
    tracked_category_ids: list[int]


class MemberActivitySettingsUpdateRequest(BaseModel):
    message_channel_ids: list[int] = Field(max_length=MAX_SETTINGS_IDS)
    voice_channel_ids: list[int] = Field(max_length=MAX_SETTINGS_IDS)
    tracked_category_ids: list[int] = Field(max_length=MAX_SETTINGS_IDS)


__all__ = (
    "DailyHistoryEntry",
    "MemberActivitySettingsResponse",
    "MemberActivitySettingsUpdateRequest",
    "MemberHistoryResponse",
    "MemberStatsResponse",
)
