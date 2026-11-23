# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Builds and posts an announcement's Discord message from its DB row.

Shared by every path that can make an announcement actually appear in a channel: an instant send
right after the modal is submitted, the scheduler loop picking up a due one, and (later) a
dashboard "send now" route — one render, one send, never duplicated per caller (same idea as
`absence/announce.py`).
"""

from datetime import UTC, datetime
from io import BytesIO
from typing import Never

import discord
from discord import MediaGalleryItem
from discord.ui import DesignerView, MediaGallery, TextDisplay

from src.database.models import Announcement, AnnouncementStatus
from src.log import logger as base_logger

logger = base_logger.getChild("announce")


def build_view(
    *,
    title: str,
    content: str,
    footer: str | None,
    role_ids_to_mention: list[int],
    created_by_id: int,
    image_filename: str | None,
) -> DesignerView:
    components: list[discord.ui.ViewItem[DesignerView]] = []

    if role_ids_to_mention:
        components.append(
            TextDisplay[DesignerView, Never](" ".join(f"<@&{role_id}>" for role_id in role_ids_to_mention))
        )
    if title:
        components.append(TextDisplay[DesignerView, Never](f"# {title}"))
    if image_filename:
        components.append(MediaGallery[DesignerView](MediaGalleryItem(f"attachment://{image_filename}")))
    if content:
        components.append(TextDisplay[DesignerView, Never](content))
    if footer:
        components.append(TextDisplay[DesignerView, Never](f"-# {footer}"))
    components.append(TextDisplay[DesignerView, Never](f"-# Annonce effectuée par <@{created_by_id}>"))

    return DesignerView(*components)


def _file(announcement: Announcement) -> discord.File | None:
    if announcement.image_data is None or announcement.image_filename is None:
        return None
    return discord.File(BytesIO(announcement.image_data), filename=announcement.image_filename)


async def send_announcement(bot: discord.Client, announcement: Announcement) -> bool:
    """Post `announcement` in its target channel and record the result on the row.

    Returns whether the send succeeded. Never raises on a Discord-side failure (missing channel,
    missing permission, …) — the caller (instant send or the scheduler loop) is responsible for
    telling the user/logging, this just marks the row `FAILED` so the scheduler never retries a
    send that can't succeed.
    """
    channel = bot.get_partial_messageable(announcement.channel_id)
    view = build_view(
        title=announcement.title,
        content=announcement.content,
        footer=announcement.footer,
        role_ids_to_mention=announcement.role_ids_to_mention,
        created_by_id=announcement.created_by_id,
        image_filename=announcement.image_filename,
    )
    file = _file(announcement)

    try:
        message = await channel.send(view=view, files=[file] if file is not None else [])
    except (discord.Forbidden, discord.HTTPException):
        logger.exception(f"Failed to send announcement {announcement.id} in channel {announcement.channel_id}")
        announcement.status = AnnouncementStatus.FAILED
        await announcement.save(update_fields=["status"])
        return False

    announcement.message_id = message.id
    announcement.status = AnnouncementStatus.SENT
    announcement.sent_at = datetime.now(tz=UTC)
    await announcement.save(update_fields=["message_id", "status", "sent_at"])
    return True


__all__ = ("build_view", "send_announcement")
