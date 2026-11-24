# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Pydantic request/response models for the announce dashboard API routes.

Creating/updating an announcement accepts an optional image upload (multipart/form-data), which
FastAPI can't mix with a single Pydantic body model, so those routes take individual
`Form(...)`/`File(...)` parameters instead (see `webserver.py`).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.database.models import MAX_ALLOWED_ROLES_ANNOUNCEMENT, AnnouncementStatus


class AnnouncementResponse(BaseModel):
    id: UUID
    channel_id: int
    title: str
    content: str
    footer: str | None
    role_ids_to_mention: list[int]
    has_image: bool
    scheduled_for: datetime | None
    status: AnnouncementStatus
    message_id: int | None
    created_by_id: int
    created_at: datetime
    sent_at: datetime | None


class AnnounceSettingsResponse(BaseModel):
    allowed_role_ids: list[int]


class AnnounceSettingsUpdateRequest(BaseModel):
    allowed_role_ids: list[int] = Field(max_length=MAX_ALLOWED_ROLES_ANNOUNCEMENT)

    @field_validator("allowed_role_ids")
    @classmethod
    def _dedupe(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


__all__ = (
    "AnnounceSettingsResponse",
    "AnnounceSettingsUpdateRequest",
    "AnnouncementResponse",
)
