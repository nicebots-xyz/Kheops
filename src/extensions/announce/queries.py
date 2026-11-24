# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""DB queries shared between the Discord views, the scheduler and the dashboard HTTP routes.

Every transition out of `SCHEDULED` is a conditional `UPDATE ... WHERE status = 'scheduled'`, so
when the scheduler, a "send now", an edit and a cancel race on the same row, exactly one wins and
the others see `None`/`False`. A row being sent is `SENDING` until its outcome is recorded.
"""

from datetime import UTC, datetime
from uuid import UUID

from tortoise_extensions.s3 import S3Object

from src.database.models import Announcement, AnnouncementStatus, AnnounceSettings, Guild

#: Most recent announcements shown by the history views.
MAX_HISTORY_DISPLAYED = 10
#: Due announcements picked up per scheduler tick, the rest wait for the next one.
MAX_DUE_PER_TICK = 50


async def get_or_create_settings(guild_id: int) -> AnnounceSettings:
    """Fetch or create a guild's announce settings, along with the `Guild` row they point to.

    Args:
        guild_id: The guild's ID.

    Returns:
        The guild's settings.

    """
    await Guild.get_or_create(id=guild_id)
    settings, _ = await AnnounceSettings.get_or_create(guild_id=guild_id)
    return settings


async def create_announcement(
    *,
    guild_id: int,
    channel_id: int,
    title: str,
    content: str,
    footer: str | None,
    role_ids_to_mention: list[int],
    image: bytes | None,
    image_filename: str | None,
    scheduled_for: datetime | None,
    created_by_id: int,
) -> Announcement:
    """Create an announcement, uploading its image first.

    Args:
        guild_id: The guild it belongs to.
        channel_id: The channel it is posted in.
        title: Its title.
        content: Its content.
        footer: Its footer, if any.
        role_ids_to_mention: The roles it pings.
        image: The image to attach, if any.
        image_filename: The sanitized filename of `image`.
        scheduled_for: When to send it, or `None` to send it right away.
        created_by_id: The member who created it.

    Returns:
        The new announcement. Without `scheduled_for`, it is created already `SENDING`, claimed for
        the caller, who must send it with `send.send_claimed`.

    """
    await Guild.get_or_create(id=guild_id)
    announcement = Announcement(
        guild_id=guild_id,
        channel_id=channel_id,
        title=title,
        content=content,
        footer=footer,
        role_ids_to_mention=role_ids_to_mention,
        image_filename=image_filename if image is not None else None,
        scheduled_for=scheduled_for,
        status=AnnouncementStatus.SCHEDULED if scheduled_for is not None else AnnouncementStatus.SENDING,
        created_by_id=created_by_id,
    )
    if image is not None:
        await announcement.image.write(image)
    try:
        await announcement.save()
    except BaseException:
        await announcement.image.delete()
        raise
    return announcement


async def due_announcement_ids(now: datetime, limit: int = MAX_DUE_PER_TICK) -> list[UUID]:
    """List the scheduled announcements whose time has come, oldest first.

    Args:
        now: The current time.
        limit: The maximum number of IDs returned.

    Returns:
        Their IDs.

    """
    return await (
        Announcement.filter(status=AnnouncementStatus.SCHEDULED, scheduled_for__lte=now)
        .order_by("scheduled_for")
        .limit(limit)
        .values_list("id", flat=True)
    )  # pyright: ignore[reportReturnType]


async def list_announcements(guild_id: int, *, limit: int = MAX_HISTORY_DISPLAYED) -> list[Announcement]:
    """List a guild's most recent announcements, newest first, whatever their status.

    Args:
        guild_id: The guild's ID.
        limit: The maximum number of announcements returned.

    Returns:
        The announcements.

    """
    return await Announcement.filter(guild_id=guild_id).order_by("-created_at").limit(limit)


async def claim_for_sending(announcement_id: UUID, guild_id: int | None = None) -> Announcement | None:
    """Move a scheduled announcement to `SENDING`, so only the caller sends it.

    Args:
        announcement_id: The announcement's ID.
        guild_id: The guild it must belong to, or `None` to not check it.

    Returns:
        The claimed announcement, or `None` if it is not scheduled (anymore).

    """
    query = Announcement.filter(id=announcement_id, status=AnnouncementStatus.SCHEDULED)
    if guild_id is not None:
        query = query.filter(guild_id=guild_id)
    if not await query.update(status=AnnouncementStatus.SENDING, updated_at=datetime.now(tz=UTC)):
        return None
    return await Announcement.get(id=announcement_id)


async def record_send_result(announcement: Announcement, message_id: int | None) -> None:
    """Record how sending a claimed announcement went.

    Args:
        announcement: The announcement, `SENDING`.
        message_id: The ID of the posted message, or `None` if sending failed.

    """
    if message_id is None:
        announcement.status = AnnouncementStatus.FAILED
        await announcement.save(update_fields=["status", "updated_at"])
        return
    announcement.status = AnnouncementStatus.SENT
    announcement.message_id = message_id
    announcement.sent_at = datetime.now(tz=UTC)
    await announcement.save(update_fields=["status", "message_id", "sent_at", "updated_at"])


async def fail_interrupted_sends() -> int:
    """Mark as failed the announcements left `SENDING` by a stopped process.

    Whether their message was posted is unknown, so they are never sent again, which could post
    them twice.

    Returns:
        The number of announcements marked as failed.

    """
    return await Announcement.filter(status=AnnouncementStatus.SENDING).update(
        status=AnnouncementStatus.FAILED, updated_at=datetime.now(tz=UTC)
    )


async def cancel_announcement(announcement_id: UUID, guild_id: int) -> bool:
    """Cancel a scheduled announcement.

    Args:
        announcement_id: The announcement's ID.
        guild_id: The guild it must belong to.

    Returns:
        Whether it was cancelled, `False` if it is not scheduled (anymore).

    """
    return bool(
        await Announcement.filter(id=announcement_id, guild_id=guild_id, status=AnnouncementStatus.SCHEDULED).update(
            status=AnnouncementStatus.CANCELLED, updated_at=datetime.now(tz=UTC)
        )
    )


async def update_announcement(
    announcement_id: UUID,
    guild_id: int,
    *,
    channel_id: int,
    title: str,
    content: str,
    footer: str | None,
    role_ids_to_mention: list[int],
    scheduled_for: datetime,
    image: bytes | None,
    image_filename: str | None,
    clear_image: bool = False,
) -> Announcement | None:
    """Overwrite a scheduled announcement's fields in place.

    Args:
        announcement_id: The announcement's ID.
        guild_id: The guild it must belong to.
        channel_id: The channel it is posted in.
        title: Its title.
        content: Its content.
        footer: Its footer, if any.
        role_ids_to_mention: The roles it pings.
        scheduled_for: When to send it.
        image: A new image replacing the current one, or `None` to keep the current one.
        image_filename: The sanitized filename of `image`.
        clear_image: Whether to remove the current image, when `image` is `None`.

    Returns:
        The updated announcement, or `None` if it does not exist or is not scheduled (anymore).

    """
    current = await Announcement.get_or_none(id=announcement_id, guild_id=guild_id)
    if current is None or current.status != AnnouncementStatus.SCHEDULED:
        return None

    values: dict[str, object] = {
        "channel_id": channel_id,
        "title": title,
        "content": content,
        "footer": footer,
        "role_ids_to_mention": role_ids_to_mention,
        "scheduled_for": scheduled_for,
        "updated_at": datetime.now(tz=UTC),
    }
    new_image = S3Object(current.image.storage)
    if image is not None:
        await new_image.write(image)
        values |= {"image": new_image.key, "image_filename": image_filename}
    elif clear_image:
        values |= {"image": None, "image_filename": None}

    try:
        updated = await Announcement.filter(
            id=announcement_id, guild_id=guild_id, status=AnnouncementStatus.SCHEDULED
        ).update(**values)
    except BaseException:
        await new_image.delete()
        raise
    if not updated:
        await new_image.delete()
        return None
    if "image" in values:
        await current.image.delete()
    return await Announcement.get(id=announcement_id)


__all__ = (
    "MAX_DUE_PER_TICK",
    "MAX_HISTORY_DISPLAYED",
    "cancel_announcement",
    "claim_for_sending",
    "create_announcement",
    "due_announcement_ids",
    "fail_interrupted_sends",
    "get_or_create_settings",
    "list_announcements",
    "record_send_result",
    "update_announcement",
)
