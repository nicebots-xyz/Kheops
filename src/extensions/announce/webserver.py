# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""HTTP API routes for announce, exposed to the dashboard backend.

Mounted under `/announce/v1`, every route protected by the shared
`src.extensions.dashboard_api.auth.require_api_key` dependency, same as `absence` and
`stats_staff`. The dashboard is trusted with IDs (channels, roles, authors): only what Discord or
this module would reject is checked here, with a 422 naming the rule.
"""

import mimetypes
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Response, UploadFile, status

from src.database.models import (
    CONTENT_MAX_LENGTH_ANNOUNCEMENT,
    FOOTER_MAX_LENGTH_ANNOUNCEMENT,
    IMAGE_EXTENSIONS_ANNOUNCEMENT,
    IMAGE_MAX_SIZE_ANNOUNCEMENT,
    MAX_ROLES_TO_MENTION_ANNOUNCEMENT,
    MESSAGE_TEXT_MAX_LENGTH_ANNOUNCEMENT,
    TITLE_MAX_LENGTH_ANNOUNCEMENT,
    Announcement,
)
from src.extensions.dashboard_api.auth import require_api_key

from .logic import sanitize_image_filename
from .queries import (
    cancel_announcement,
    create_announcement,
    get_or_create_settings,
    list_announcements,
    update_announcement,
)
from .schemas import AnnouncementResponse, AnnounceSettingsResponse, AnnounceSettingsUpdateRequest
from .send import message_strings, send_claimed, send_scheduled, text_length

if TYPE_CHECKING:
    import discord

    from src.i18n.classes import RawTranslation
    from src.startup.types import ExtensionConfig

Title = Annotated[str, Form(min_length=1, max_length=TITLE_MAX_LENGTH_ANNOUNCEMENT)]
Content = Annotated[str, Form(min_length=1, max_length=CONTENT_MAX_LENGTH_ANNOUNCEMENT)]
Footer = Annotated[str | None, Form(max_length=FOOTER_MAX_LENGTH_ANNOUNCEMENT)]
RoleIds = Annotated[list[int], Form(max_length=MAX_ROLES_TO_MENTION_ANNOUNCEMENT)]
Image = Annotated[UploadFile | None, File()]

_NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Announcement not found")


def _to_response(announcement: Announcement) -> AnnouncementResponse:
    return AnnouncementResponse(
        id=announcement.id,
        channel_id=announcement.channel_id,
        title=announcement.title,
        content=announcement.content,
        footer=announcement.footer,
        role_ids_to_mention=announcement.role_ids_to_mention,
        has_image=not announcement.image.is_empty,
        scheduled_for=announcement.scheduled_for,
        status=announcement.status,
        message_id=announcement.message_id,
        created_by_id=announcement.created_by_id,
        created_at=announcement.created_at,
        sent_at=announcement.sent_at,
    )


def _unprocessable(field: str, message: str) -> HTTPException:
    """Build a 422 shaped like FastAPI's own validation errors.

    Args:
        field: The offending form field.
        message: What is wrong with it.

    Returns:
        The exception to raise.

    """
    return HTTPException(
        status.HTTP_422_UNPROCESSABLE_CONTENT, [{"loc": ["body", field], "msg": message, "type": "value_error"}]
    )


async def _not_scheduled(announcement_id: UUID, guild_id: int) -> HTTPException:
    """Explain why an announcement could not be changed.

    Args:
        announcement_id: The announcement's ID.
        guild_id: The guild it must belong to.

    Returns:
        A 404 if it does not exist, otherwise a 409 naming its current status.

    """
    announcement = await Announcement.get_or_none(id=announcement_id, guild_id=guild_id)
    if announcement is None:
        return _NOT_FOUND
    return HTTPException(
        status.HTTP_409_CONFLICT, f"Announcement is {announcement.status.value}, only a scheduled one can be changed"
    )


def _check_future(scheduled_for: datetime | None) -> None:
    """Reject a send date that is already past.

    Args:
        scheduled_for: The requested send date, `None` for an instant send.

    Raises:
        HTTPException: 422 if the date is past.

    """
    if scheduled_for is not None and scheduled_for <= datetime.now(tz=UTC):
        raise _unprocessable("scheduled_for", "Must be in the future")


async def _read_image(image: UploadFile | None) -> tuple[bytes, str] | None:
    """Read and check an uploaded image.

    Args:
        image: The uploaded file, if any.

    Returns:
        The image and its sanitized filename, or `None` without an upload.

    Raises:
        HTTPException: 422 if the file is not an accepted image or is too large.

    """
    if image is None or not image.filename:
        return None
    filename = sanitize_image_filename(image.filename)
    if filename is None:
        accepted = ", ".join(sorted(IMAGE_EXTENSIONS_ANNOUNCEMENT))
        raise _unprocessable("image", f"Unsupported image type, accepted extensions are {accepted}")
    data = await image.read(IMAGE_MAX_SIZE_ANNOUNCEMENT + 1)
    if len(data) > IMAGE_MAX_SIZE_ANNOUNCEMENT:
        raise _unprocessable("image", f"Image is larger than {IMAGE_MAX_SIZE_ANNOUNCEMENT} bytes")
    return data, filename


def setup_webserver(app: FastAPI, bot: "discord.Client", config: "ExtensionConfig") -> None:
    strings = cast("dict[str, RawTranslation]", config.get("translations") or {})
    router = APIRouter(prefix="/announce/v1", dependencies=[Depends(require_api_key)])

    def check_text_length(
        guild_id: int, *, title: str, content: str, footer: str | None, role_ids: list[int], created_by_id: int
    ) -> None:
        """Reject an announcement whose rendered text Discord would refuse.

        Args:
            guild_id: The guild it is posted in, whose locale the signature uses.
            title: Its title.
            content: Its content.
            footer: Its footer, if any.
            role_ids: The roles it pings.
            created_by_id: The member credited as its author.

        Raises:
            HTTPException: 422 if the text is longer than `MESSAGE_TEXT_MAX_LENGTH`.

        """
        length = text_length(
            t=message_strings(bot, guild_id, strings),
            title=title,
            content=content,
            footer=footer,
            role_ids_to_mention=role_ids,
            created_by_id=created_by_id,
        )
        if length > MESSAGE_TEXT_MAX_LENGTH_ANNOUNCEMENT:
            raise _unprocessable(
                "content",
                f"Rendered announcement is {length} characters long, Discord allows at most "
                + f"{MESSAGE_TEXT_MAX_LENGTH_ANNOUNCEMENT} across title, content, footer, role mentions and signature",
            )

    @router.get("/guilds/{guild_id}/announcements")
    async def list_announcements_route(guild_id: int) -> list[AnnouncementResponse]:
        return [_to_response(a) for a in await list_announcements(guild_id)]

    @router.post("/guilds/{guild_id}/announcements", status_code=status.HTTP_201_CREATED)
    async def create_announcement_route(  # noqa: PLR0917 - one form field per parameter
        guild_id: int,
        channel_id: Annotated[int, Form()],
        title: Title,
        content: Content,
        created_by_id: Annotated[int, Form()],
        footer: Footer = None,
        role_ids_to_mention: RoleIds = [],  # noqa: B006 - FastAPI needs a literal default here  # pyright: ignore[reportCallInDefaultInitializer]
        scheduled_for: Annotated[datetime | None, Form()] = None,
        image: Image = None,
    ) -> AnnouncementResponse:
        _check_future(scheduled_for)
        check_text_length(
            guild_id,
            title=title,
            content=content,
            footer=footer or None,
            role_ids=role_ids_to_mention,
            created_by_id=created_by_id,
        )
        upload = await _read_image(image)

        announcement = await create_announcement(
            guild_id=guild_id,
            channel_id=channel_id,
            title=title,
            content=content,
            footer=footer or None,
            role_ids_to_mention=role_ids_to_mention,
            image=upload[0] if upload else None,
            image_filename=upload[1] if upload else None,
            scheduled_for=scheduled_for,
            created_by_id=created_by_id,
        )
        if scheduled_for is None:
            await send_claimed(bot, announcement, strings)
        return _to_response(announcement)

    @router.put("/guilds/{guild_id}/announcements/{announcement_id}")
    async def update_announcement_route(  # noqa: PLR0917 - one form field per parameter
        guild_id: int,
        announcement_id: UUID,
        channel_id: Annotated[int, Form()],
        title: Title,
        content: Content,
        scheduled_for: Annotated[datetime, Form()],
        footer: Footer = None,
        role_ids_to_mention: RoleIds = [],  # noqa: B006 - FastAPI needs a literal default here  # pyright: ignore[reportCallInDefaultInitializer]
        clear_image: Annotated[bool, Form()] = False,
        image: Image = None,
    ) -> AnnouncementResponse:
        current = await Announcement.get_or_none(id=announcement_id, guild_id=guild_id)
        if current is None:
            raise _NOT_FOUND
        _check_future(scheduled_for)
        check_text_length(
            guild_id,
            title=title,
            content=content,
            footer=footer or None,
            role_ids=role_ids_to_mention,
            created_by_id=current.created_by_id,
        )
        upload = await _read_image(image)

        announcement = await update_announcement(
            announcement_id,
            guild_id,
            channel_id=channel_id,
            title=title,
            content=content,
            footer=footer or None,
            role_ids_to_mention=role_ids_to_mention,
            scheduled_for=scheduled_for,
            image=upload[0] if upload else None,
            image_filename=upload[1] if upload else None,
            clear_image=clear_image,
        )
        if announcement is None:
            raise await _not_scheduled(announcement_id, guild_id)
        return _to_response(announcement)

    @router.get("/guilds/{guild_id}/announcements/{announcement_id}/image")
    async def get_announcement_image(guild_id: int, announcement_id: UUID) -> Response:
        announcement = await Announcement.get_or_none(id=announcement_id, guild_id=guild_id)
        if announcement is None or announcement.image.is_empty:
            raise _NOT_FOUND
        try:
            data = await announcement.image.read()
        except FileNotFoundError:
            raise _NOT_FOUND from None
        media_type, _ = mimetypes.guess_type(announcement.image_filename or "")
        return Response(data, media_type=media_type or "application/octet-stream")

    @router.delete("/guilds/{guild_id}/announcements/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def cancel_announcement_route(guild_id: int, announcement_id: UUID) -> None:
        if not await cancel_announcement(announcement_id, guild_id):
            raise await _not_scheduled(announcement_id, guild_id)

    @router.post("/guilds/{guild_id}/announcements/{announcement_id}/send-now")
    async def send_now_route(guild_id: int, announcement_id: UUID) -> AnnouncementResponse:
        announcement = await send_scheduled(bot, announcement_id, strings, guild_id)
        if announcement is None:
            raise await _not_scheduled(announcement_id, guild_id)
        return _to_response(announcement)

    @router.get("/guilds/{guild_id}/settings")
    async def get_settings(guild_id: int) -> AnnounceSettingsResponse:
        settings = await get_or_create_settings(guild_id)
        return AnnounceSettingsResponse(allowed_role_ids=settings.allowed_role_ids)

    @router.put("/guilds/{guild_id}/settings")
    async def update_settings(guild_id: int, payload: AnnounceSettingsUpdateRequest) -> AnnounceSettingsResponse:
        settings = await get_or_create_settings(guild_id)
        settings.allowed_role_ids = payload.allowed_role_ids
        await settings.save(update_fields=["allowed_role_ids"])
        return AnnounceSettingsResponse(allowed_role_ids=settings.allowed_role_ids)

    app.include_router(router)


__all__ = ("setup_webserver",)
