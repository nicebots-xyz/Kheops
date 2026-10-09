# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Pydantic request/response models for the stats_staff dashboard API routes."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from src.database.models import StaffQuotaMode

from .logic import StatsPeriod


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


__all__ = (
    "DailyHistoryEntry",
    "MemberHistoryResponse",
    "MemberStatsResponse",
    "QuotaResponse",
    "QuotaUpsertRequest",
)
