# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Keeps an absence's public announcement message in sync with its DB row.

Called from both the Discord-side modal callbacks and the dashboard HTTP routes, so a change made
from either side always produces the same Discord-visible result. The public message only ever
shows the member and their dates — never the reason.
"""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import TYPE_CHECKING, Never

import discord
from discord.ui import Container, DesignerView, TextDisplay
from discord.utils import format_dt

from src.log import logger as base_logger

from .logic import duration_days

if TYPE_CHECKING:
    from datetime import date

    from src.database.models import Absence, AbsenceSettings

logger = base_logger.getChild("absence")

ABSENCE_COLOUR = discord.Colour.from_rgb(237, 139, 54)  # warm orange — distinct from other modules' cards


def _day(value: date) -> str:
    return format_dt(datetime.combine(value, time.min, tzinfo=UTC), style="D")


def _view(absence: Absence) -> DesignerView:
    days = duration_days(absence.start_date, absence.end_date)
    suffix = "" if days == 1 else "s"
    content = (
        f"## 📅 Absence signalée\n"
        f"<@{absence.member_id}> est absent(e) du {_day(absence.start_date)} au {_day(absence.end_date)}\n"
        f"-# Durée : **{days} jour{suffix}**"
    )
    return DesignerView(Container[DesignerView](TextDisplay[DesignerView, Never](content), colour=ABSENCE_COLOUR))


async def _existing_message(bot: discord.Client, absence: Absence) -> discord.Message | None:
    if absence.announce_message_id is None or absence.announce_channel_id is None:
        return None
    channel = bot.get_partial_messageable(absence.announce_channel_id)
    try:
        return await channel.fetch_message(absence.announce_message_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None


async def sync_announcement(bot: discord.Client, absence: Absence, settings: AbsenceSettings) -> None:
    """Create or update the public message for `absence`, persisting its location on the row."""
    channel_id = settings.announce_channel_id
    if channel_id is None:
        return

    existing = await _existing_message(bot, absence)
    if existing is not None:
        try:
            await existing.edit(view=_view(absence))
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(f"Could not edit announcement message for absence {absence.id}, re-posting")
        else:
            return

    channel = bot.get_partial_messageable(channel_id)
    try:
        message = await channel.send(view=_view(absence))
    except (discord.Forbidden, discord.HTTPException):
        logger.exception(f"Failed to post absence announcement in channel {channel_id}")
        return

    absence.announce_channel_id = channel_id
    absence.announce_message_id = message.id
    await absence.save(update_fields=["announce_channel_id", "announce_message_id"])


async def remove_announcement(bot: discord.Client, absence: Absence) -> None:
    """Delete the public message for `absence`, e.g. on cancellation."""
    existing = await _existing_message(bot, absence)
    if existing is not None:
        try:
            await existing.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            logger.warning(f"Could not delete announcement message for absence {absence.id}")

    absence.announce_message_id = None
    await absence.save(update_fields=["announce_message_id"])


__all__ = ("remove_announcement", "sync_announcement")
