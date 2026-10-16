# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Pydantic request/response models for the absence dashboard API routes."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.database.models import REASON_MAX_LENGTH_ABSENCE

#: Discord role-select menus cap at 25 options — the config panel can't render/save more than
#: that, so the dashboard shouldn't be able to persist settings it can't display either.
MAX_ALLOWED_ROLES = 25


class _RequiresReason(BaseModel):
    reason: str = Field(min_length=1, max_length=REASON_MAX_LENGTH_ABSENCE)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("reason must not be blank")
        return stripped


class AbsenceResponse(BaseModel):
    id: UUID
    member_id: int
    start_date: date
    end_date: date
    reason: str
    created_by_id: int
    cancelled: bool


class AbsenceCreateRequest(_RequiresReason):
    member_id: int
    start_date: date
    end_date: date
    created_by_id: int


class AbsenceUpdateRequest(_RequiresReason):
    start_date: date
    end_date: date


class AbsenceSettingsResponse(BaseModel):
    allowed_role_ids: list[int]
    announce_channel_id: int | None
    responsible_role_id: int | None


class AbsenceSettingsUpdateRequest(BaseModel):
    allowed_role_ids: list[int] = Field(max_length=MAX_ALLOWED_ROLES)
    announce_channel_id: int | None
    responsible_role_id: int | None


__all__ = (
    "AbsenceCreateRequest",
    "AbsenceResponse",
    "AbsenceSettingsResponse",
    "AbsenceSettingsUpdateRequest",
    "AbsenceUpdateRequest",
)
