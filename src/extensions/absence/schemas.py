# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Pydantic request/response models for the absence dashboard API routes."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from src.database.models import REASON_MAX_LENGTH_ABSENCE


class AbsenceResponse(BaseModel):
    id: UUID
    member_id: int
    start_date: date
    end_date: date
    reason: str
    created_by_id: int
    cancelled: bool


class AbsenceCreateRequest(BaseModel):
    member_id: int
    start_date: date
    end_date: date
    reason: str = Field("", max_length=REASON_MAX_LENGTH_ABSENCE)
    created_by_id: int


class AbsenceUpdateRequest(BaseModel):
    start_date: date
    end_date: date
    reason: str = Field("", max_length=REASON_MAX_LENGTH_ABSENCE)


class AbsenceSettingsResponse(BaseModel):
    allowed_role_ids: list[int]
    announce_channel_id: int | None
    responsible_role_id: int | None


class AbsenceSettingsUpdateRequest(BaseModel):
    allowed_role_ids: list[int]
    announce_channel_id: int | None
    responsible_role_id: int | None


__all__ = (
    "AbsenceCreateRequest",
    "AbsenceResponse",
    "AbsenceSettingsResponse",
    "AbsenceSettingsUpdateRequest",
    "AbsenceUpdateRequest",
)
