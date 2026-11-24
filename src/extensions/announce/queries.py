# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""DB queries shared between the Discord-side modal/views and the dashboard HTTP routes.

No overlap/concurrency concern like `absence` has (two announcements don't conflict with each
other), so these are plain CRUD — no advisory lock needed.
"""

from datetime import UTC, datetime

from src.database.models import Announcement, AnnouncementStatus, AnnounceSettings, Guild

#: History views (Discord and, later, the dashboard) only need recent entries, not the entire
#: guild history — keeps the query and the rendered list bounded.
MAX_HISTORY_DISPLAYED = 20


async def get_or_create_settings(guild_id: int) -> AnnounceSettings:
    """Fetch (or create) a guild's announce settings, ensuring the `Guild` row they FK to exists."""
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
    image_data: bytes | None,
    image_filename: str | None,
    scheduled_for: datetime | None,
    created_by_id: int,
) -> Announcement:
    """Create an announcement row.

    `scheduled_for=None` means "send right away" — the caller is expected to actually send it
    (see `send.send_announcement`) and update the row to `SENT` immediately after; this function
    only ever inserts a `SCHEDULED` row when deferred, matching the status default of `SENT`
    otherwise so a crash between insert and send never leaves a phantom "scheduled" entry that's
    actually already past.
    """
    await Guild.get_or_create(id=guild_id)
    return await Announcement.create(
        guild_id=guild_id,
        channel_id=channel_id,
        title=title,
        content=content,
        footer=footer,
        role_ids_to_mention=role_ids_to_mention,
        image_data=image_data,
        image_filename=image_filename,
        scheduled_for=scheduled_for,
        status=AnnouncementStatus.SCHEDULED if scheduled_for is not None else AnnouncementStatus.SENT,
        created_by_id=created_by_id,
    )


async def due_announcements(now: datetime | None = None) -> list[Announcement]:
    """Scheduled announcements whose time has come — picked up by the scheduler loop."""
    cutoff = now or datetime.now(tz=UTC)
    return await Announcement.filter(status=AnnouncementStatus.SCHEDULED, scheduled_for__lte=cutoff)


async def list_announcements(guild_id: int, *, limit: int = MAX_HISTORY_DISPLAYED) -> list[Announcement]:
    """Most recent announcements for a guild, newest first (scheduled ones included)."""
    return await Announcement.filter(guild_id=guild_id).order_by("-created_at").limit(limit)


async def cancel_announcement(announcement: Announcement) -> None:
    """Cancel a still-scheduled announcement — never touches one already sent/failed."""
    announcement.status = AnnouncementStatus.CANCELLED
    await announcement.save(update_fields=["status"])


async def update_announcement(
    announcement: Announcement,
    *,
    channel_id: int,
    title: str,
    content: str,
    footer: str | None,
    role_ids_to_mention: list[int],
    scheduled_for: datetime,
    image_data: bytes | None,
    image_filename: str | None,
    clear_image: bool,
) -> Announcement:
    """Overwrite a still-scheduled announcement's fields in place.

    Only ever called on a `SCHEDULED` row (checked by the caller) — editing a sent/cancelled/
    failed announcement doesn't make sense, there's nothing left to change before. `image_data`
    replaces the stored image when a new file was uploaded; `clear_image` removes it without a
    replacement; leaving both unset keeps the existing image untouched.
    """
    announcement.channel_id = channel_id
    announcement.title = title
    announcement.content = content
    announcement.footer = footer
    announcement.role_ids_to_mention = role_ids_to_mention
    announcement.scheduled_for = scheduled_for
    update_fields = [
        "channel_id",
        "title",
        "content",
        "footer",
        "role_ids_to_mention",
        "scheduled_for",
        "updated_at",
    ]
    if image_data is not None:
        announcement.image_data = image_data
        announcement.image_filename = image_filename
        update_fields += ["image_data", "image_filename"]
    elif clear_image:
        announcement.image_data = None
        announcement.image_filename = None
        update_fields += ["image_data", "image_filename"]
    await announcement.save(update_fields=update_fields)
    return announcement


__all__ = (
    "MAX_HISTORY_DISPLAYED",
    "cancel_announcement",
    "create_announcement",
    "due_announcements",
    "get_or_create_settings",
    "list_announcements",
    "update_announcement",
)
