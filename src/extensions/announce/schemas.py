# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Pydantic request/response models for the announce dashboard API routes.

Creating/updating an announcement accepts an optional image upload (multipart/form-data), which
FastAPI can't mix with a single Pydantic body model — see `webserver.py`, where those routes take
individual `Form(...)`/`File(...)` parameters instead of one of the request models below.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.database.models import (
    CONTENT_MAX_LENGTH_ANNOUNCEMENT,
    FOOTER_MAX_LENGTH_ANNOUNCEMENT,
    MAX_ROLES_TO_MENTION_ANNOUNCEMENT,
    TITLE_MAX_LENGTH_ANNOUNCEMENT,
    AnnouncementStatus,
)

#: Discord role-select menus cap at 25 options — the config panel can't render/save more than
#: that (same reasoning as `absence.schemas.MAX_ALLOWED_ROLES`).
MAX_ALLOWED_ROLES = 25


class AnnouncementResponse(BaseModel):
    id: UUID
    channel_id: int
    title: str = Field(max_length=TITLE_MAX_LENGTH_ANNOUNCEMENT)
    content: str = Field(max_length=CONTENT_MAX_LENGTH_ANNOUNCEMENT)
    footer: str | None = Field(default=None, max_length=FOOTER_MAX_LENGTH_ANNOUNCEMENT)
    role_ids_to_mention: list[int] = Field(max_length=MAX_ROLES_TO_MENTION_ANNOUNCEMENT)
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
    allowed_role_ids: list[int] = Field(max_length=MAX_ALLOWED_ROLES)

    @field_validator("allowed_role_ids")
    @classmethod
    def _dedupe(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


__all__ = (
    "AnnounceSettingsResponse",
    "AnnounceSettingsUpdateRequest",
    "AnnouncementResponse",
)
