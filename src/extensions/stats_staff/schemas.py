# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Pydantic request/response models for the stats_staff dashboard API routes."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from src.database.models import StaffQuotaMode

from .logic import StatsPeriod

#: Discord role/channel-select menus cap at 25 options — the config panel can't render/save more
#: than that, so the dashboard shouldn't be able to persist settings it can't display either.
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


class QuotaResponse(BaseModel):
    id: UUID
    role_id: int
    voice_minutes_required: int
    messages_required: int
    mode: StaffQuotaMode


class QuotaUpsertRequest(BaseModel):
    voice_minutes_required: int = Field(ge=0)
    messages_required: int = Field(ge=0)
    mode: StaffQuotaMode


class MemberQuotaRoleResponse(BaseModel):
    member_id: int
    role_id: int


class StaffStatsSettingsResponse(BaseModel):
    responsible_role_id: int | None
    report_channel_id: int | None
    message_channel_ids: list[int]
    voice_channel_ids: list[int]
    tracked_category_ids: list[int]
    et_substitution_penalty: float


class StaffStatsSettingsUpdateRequest(BaseModel):
    responsible_role_id: int | None
    report_channel_id: int | None
    message_channel_ids: list[int] = Field(max_length=MAX_SETTINGS_IDS)
    voice_channel_ids: list[int] = Field(max_length=MAX_SETTINGS_IDS)
    tracked_category_ids: list[int] = Field(max_length=MAX_SETTINGS_IDS)
    et_substitution_penalty: float


__all__ = (
    "DailyHistoryEntry",
    "MemberHistoryResponse",
    "MemberQuotaRoleResponse",
    "MemberStatsResponse",
    "QuotaResponse",
    "QuotaUpsertRequest",
    "StaffStatsSettingsResponse",
    "StaffStatsSettingsUpdateRequest",
)
