# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""HTTP API routes for announce, exposed to the dashboard backend.

Mounted under `/announce/v1` and protected by the shared
`src.extensions.dashboard_api.auth.require_api_key` dependency — same convention as `absence`
and `stats_staff`.
"""

import io
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from src.database.models import Announcement, AnnouncementStatus
from src.extensions.dashboard_api.auth import require_api_key

from .queries import cancel_announcement, create_announcement, get_or_create_settings, list_announcements
from .schemas import AnnouncementResponse, AnnounceSettingsResponse, AnnounceSettingsUpdateRequest
from .send import send_announcement

if TYPE_CHECKING:
    import discord


def _to_response(announcement: Announcement) -> AnnouncementResponse:
    return AnnouncementResponse(
        id=announcement.id,
        channel_id=announcement.channel_id,
        title=announcement.title,
        content=announcement.content,
        footer=announcement.footer,
        role_ids_to_mention=announcement.role_ids_to_mention,
        has_image=announcement.image_data is not None,
        scheduled_for=announcement.scheduled_for,
        status=announcement.status,
        message_id=announcement.message_id,
        created_by_id=announcement.created_by_id,
        created_at=announcement.created_at,
        sent_at=announcement.sent_at,
    )


_NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Announcement not found")
_NOT_SCHEDULED = HTTPException(status.HTTP_409_CONFLICT, "Announcement is not scheduled")


def setup_webserver(app: FastAPI, bot: "discord.Client") -> None:
    router = APIRouter(prefix="/announce/v1", dependencies=[Depends(require_api_key)])

    @router.get("/guilds/{guild_id}/announcements")
    async def list_announcements_route(guild_id: int) -> list[AnnouncementResponse]:
        return [_to_response(a) for a in await list_announcements(guild_id)]

    @router.post("/guilds/{guild_id}/announcements", status_code=status.HTTP_201_CREATED)
    async def create_announcement_route(
        guild_id: int,
        channel_id: Annotated[int, Form()],
        title: Annotated[str, Form()],
        content: Annotated[str, Form()],
        created_by_id: Annotated[int, Form()],
        footer: Annotated[str | None, Form()] = None,
        role_ids_to_mention: Annotated[list[int], Form()] = [],  # noqa: B006 - FastAPI needs a literal default here  # pyright: ignore[reportCallInDefaultInitializer]
        scheduled_for: Annotated[datetime | None, Form()] = None,
        image: Annotated[UploadFile | None, File()] = None,
    ) -> AnnouncementResponse:
        if scheduled_for is not None and scheduled_for <= datetime.now(tz=UTC):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "scheduled_for must be in the future")

        image_data = await image.read() if image is not None and image.filename else None
        image_filename = image.filename if image is not None and image.filename else None

        announcement = await create_announcement(
            guild_id=guild_id,
            channel_id=channel_id,
            title=title,
            content=content,
            footer=footer or None,
            role_ids_to_mention=role_ids_to_mention,
            image_data=image_data,
            image_filename=image_filename,
            scheduled_for=scheduled_for,
            created_by_id=created_by_id,
        )
        if scheduled_for is None:
            await send_announcement(bot, announcement)
        return _to_response(announcement)

    @router.get("/guilds/{guild_id}/announcements/{announcement_id}/image")
    async def get_announcement_image(guild_id: int, announcement_id: UUID) -> StreamingResponse:
        announcement = await Announcement.get_or_none(id=announcement_id, guild_id=guild_id)
        if announcement is None or announcement.image_data is None:
            raise _NOT_FOUND
        return StreamingResponse(io.BytesIO(announcement.image_data), media_type="application/octet-stream")

    @router.delete("/guilds/{guild_id}/announcements/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def cancel_announcement_route(guild_id: int, announcement_id: UUID) -> None:
        announcement = await Announcement.get_or_none(id=announcement_id, guild_id=guild_id)
        if announcement is None:
            raise _NOT_FOUND
        if announcement.status != AnnouncementStatus.SCHEDULED:
            raise _NOT_SCHEDULED
        await cancel_announcement(announcement)

    @router.post("/guilds/{guild_id}/announcements/{announcement_id}/send-now")
    async def send_now_route(guild_id: int, announcement_id: UUID) -> AnnouncementResponse:
        announcement = await Announcement.get_or_none(id=announcement_id, guild_id=guild_id)
        if announcement is None:
            raise _NOT_FOUND
        if announcement.status != AnnouncementStatus.SCHEDULED:
            raise _NOT_SCHEDULED
        await send_announcement(bot, announcement)
        return _to_response(announcement)

    @router.get("/guilds/{guild_id}/settings")
    async def get_settings(guild_id: int) -> AnnounceSettingsResponse:
        settings = await get_or_create_settings(guild_id)
        return AnnounceSettingsResponse(allowed_role_ids=settings.allowed_role_ids)

    @router.put("/guilds/{guild_id}/settings")
    async def update_settings(guild_id: int, payload: AnnounceSettingsUpdateRequest) -> AnnounceSettingsResponse:
        guild = bot.get_guild(guild_id)
        if guild is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Guild not found")
        unknown_roles = [role_id for role_id in payload.allowed_role_ids if guild.get_role(role_id) is None]
        if unknown_roles:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"allowed_role_ids not in this guild: {unknown_roles}")

        settings = await get_or_create_settings(guild_id)
        settings.allowed_role_ids = payload.allowed_role_ids
        await settings.save(update_fields=["allowed_role_ids"])
        return AnnounceSettingsResponse(allowed_role_ids=settings.allowed_role_ids)

    app.include_router(router)


__all__ = ("setup_webserver",)
