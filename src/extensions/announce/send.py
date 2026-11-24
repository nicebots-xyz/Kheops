# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Builds and posts an announcement's Discord message from its DB row.

Shared by every path that makes an announcement appear in a channel: an instant send from the
builder, the scheduler loop, and "send now" from the history or the dashboard.
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING, Never

import discord
from discord import MediaGalleryItem
from discord.ui import DesignerView, MediaGallery, TextDisplay

from src import i18n
from src.database.models import Announcement, AnnouncementStatus
from src.log import logger as base_logger

from .queries import claim_for_sending, record_send_result
from .translations import ExtensionStrings

if TYPE_CHECKING:
    from uuid import UUID

    from src.i18n.classes import RawTranslation

logger = base_logger.getChild("announce")


def localize(strings: dict[str, RawTranslation], locale: str | None) -> ExtensionStrings:
    """Localize the extension's strings.

    Args:
        strings: The extension's raw strings.
        locale: The locale to localize for, `None` for the default one.

    Returns:
        The typed, localized strings.

    """
    return i18n.typed(i18n.apply_locale(strings, locale), ExtensionStrings)


def message_strings(bot: discord.Client, guild_id: int, strings: dict[str, RawTranslation]) -> ExtensionStrings:
    """Localize the strings of the announcement message itself, in the guild's locale.

    Args:
        bot: The bot, to look the guild up.
        guild_id: The guild the announcement is posted in.
        strings: The extension's raw strings.

    Returns:
        The typed strings, localized for the guild.

    """
    guild = bot.get_guild(guild_id)
    return localize(strings, guild.preferred_locale if guild is not None else None)


def _text_items(
    *,
    t: ExtensionStrings,
    title: str,
    content: str,
    footer: str | None,
    role_ids_to_mention: list[int],
    created_by_id: int,
) -> list[str]:
    """List the texts of an announcement message, in display order.

    Args:
        t: The strings of the message, localized for its guild.
        title: Its title.
        content: Its content.
        footer: Its footer, if any.
        role_ids_to_mention: The roles it pings.
        created_by_id: The member who created it.

    Returns:
        One text per text display.

    """
    items: list[str] = []
    if role_ids_to_mention:
        items.append(" ".join(f"<@&{role_id}>" for role_id in role_ids_to_mention))
    if title:
        items.append(f"# {title}")
    if content:
        items.append(content)
    if footer:
        items.append(f"-# {footer}")
    items.append(t.signature.format(author=f"<@{created_by_id}>"))
    return items


def text_length(
    *,
    t: ExtensionStrings,
    title: str,
    content: str,
    footer: str | None,
    role_ids_to_mention: list[int],
    created_by_id: int,
) -> int:
    """Count the text of an announcement message, which Discord caps at `MESSAGE_TEXT_MAX_LENGTH`.

    Args:
        t: The strings of the message, localized for its guild.
        title: Its title.
        content: Its content.
        footer: Its footer, if any.
        role_ids_to_mention: The roles it pings.
        created_by_id: The member who created it.

    Returns:
        The number of characters across its text displays.

    """
    items = _text_items(
        t=t,
        title=title,
        content=content,
        footer=footer,
        role_ids_to_mention=role_ids_to_mention,
        created_by_id=created_by_id,
    )
    return sum(len(item) for item in items)


def build_view(
    *,
    t: ExtensionStrings,
    title: str,
    content: str,
    footer: str | None,
    role_ids_to_mention: list[int],
    created_by_id: int,
    image_filename: str | None,
) -> DesignerView:
    """Build an announcement message.

    Args:
        t: The strings of the message, localized for its guild.
        title: Its title.
        content: Its content.
        footer: Its footer, if any.
        role_ids_to_mention: The roles it pings.
        created_by_id: The member who created it.
        image_filename: The filename of the attached image, if any.

    Returns:
        The message's view.

    """
    texts = _text_items(
        t=t,
        title=title,
        content=content,
        footer=footer,
        role_ids_to_mention=role_ids_to_mention,
        created_by_id=created_by_id,
    )
    components: list[discord.ui.ViewItem[DesignerView]] = [TextDisplay[DesignerView, Never](text) for text in texts]
    if image_filename:
        # Right under the title, or first when there is neither title nor mentions.
        position = int(bool(role_ids_to_mention)) + int(bool(title))
        components.insert(position, MediaGallery[DesignerView](MediaGalleryItem(f"attachment://{image_filename}")))
    return DesignerView(*components)


def image_file(data: bytes | None, filename: str | None) -> list[discord.File]:
    """Wrap an announcement's image as the files of its message.

    Args:
        data: The image, if any.
        filename: Its filename.

    Returns:
        The image as a single file, or no file.

    """
    if data is None or filename is None:
        return []
    return [discord.File(BytesIO(data), filename=filename)]


async def send_claimed(bot: discord.Client, announcement: Announcement, strings: dict[str, RawTranslation]) -> bool:
    """Post a claimed announcement in its channel and record the result on its row.

    Never raises: any failure marks it `FAILED`, never retried, and is logged.

    Args:
        bot: The bot posting it.
        announcement: The announcement, `SENDING`.
        strings: The extension's raw strings.

    Returns:
        Whether it was sent.

    """
    assert announcement.status == AnnouncementStatus.SENDING
    try:
        view = build_view(
            t=message_strings(bot, announcement.guild_id, strings),
            title=announcement.title,
            content=announcement.content,
            footer=announcement.footer,
            role_ids_to_mention=announcement.role_ids_to_mention,
            created_by_id=announcement.created_by_id,
            image_filename=announcement.image_filename,
        )
        files = image_file(await announcement.image.read(), announcement.image_filename)
        channel = bot.get_partial_messageable(announcement.channel_id)
        message = await channel.send(view=view, files=files)
    except Exception:
        logger.exception(f"Failed to send announcement {announcement.id} in channel {announcement.channel_id}")
        await record_send_result(announcement, None)
        return False
    await record_send_result(announcement, message.id)
    return True


async def send_scheduled(
    bot: discord.Client, announcement_id: UUID, strings: dict[str, RawTranslation], guild_id: int | None = None
) -> Announcement | None:
    """Claim a scheduled announcement, then send it.

    Args:
        bot: The bot posting it.
        announcement_id: The announcement's ID.
        strings: The extension's raw strings.
        guild_id: The guild it must belong to, or `None` to not check it.

    Returns:
        The announcement once sent or failed, or `None` if it is not scheduled (anymore).

    """
    announcement = await claim_for_sending(announcement_id, guild_id)
    if announcement is None:
        return None
    await send_claimed(bot, announcement, strings)
    return announcement


__all__ = (
    "build_view",
    "image_file",
    "localize",
    "message_strings",
    "send_claimed",
    "send_scheduled",
    "text_length",
)
