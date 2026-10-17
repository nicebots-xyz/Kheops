# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Keeps an absence's public announcement message in sync with its DB row.

Called from both the Discord-side modal callbacks and the dashboard HTTP routes, so a change made
from either side always produces the same Discord-visible result. The public message only ever
shows the member and their dates — never the reason.
"""

from datetime import date
from typing import Never

import discord
from discord.ui import Container, DesignerView, TextDisplay

from src.database.models import Absence, AbsenceKind, AbsenceSettings
from src.log import logger as base_logger

from .logic import duration_days

logger = base_logger.getChild("absence")

ABSENCE_COLOUR = discord.Colour.from_rgb(220, 53, 34)  # red — fully unavailable
PARTIAL_ABSENCE_COLOUR = discord.Colour.from_rgb(237, 139, 54)  # warm orange — reduced availability


def _day(value: date) -> str:
    # Plain text, not Discord's <t:...> timestamp: that renders in each viewer's local timezone,
    # which can shift a date-only value to the adjacent calendar day near midnight UTC.
    return value.strftime("%d/%m/%Y")


def _view(absence: Absence) -> DesignerView:
    days = duration_days(absence.start_date, absence.end_date)
    suffix = "" if days == 1 else "s"
    if absence.kind == AbsenceKind.PARTIAL:
        title = "## 🟠 Disponibilité réduite signalée"
        body = (
            f"<@{absence.member_id}> a une disponibilité réduite du "
            f"{_day(absence.start_date)} au {_day(absence.end_date)}"
        )
        colour = PARTIAL_ABSENCE_COLOUR
        note_line = f"\n-# {absence.availability_note}" if absence.availability_note else ""
    else:
        title = "## 🔴 Absence signalée"
        body = f"<@{absence.member_id}> est absent(e) du {_day(absence.start_date)} au {_day(absence.end_date)}"
        colour = ABSENCE_COLOUR
        note_line = ""
    content = f"{title}\n{body}\n-# Durée : **{days} jour{suffix}**{note_line}"
    return DesignerView(Container[DesignerView](TextDisplay[DesignerView, Never](content), colour=colour))


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
            try:
                await existing.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                logger.warning(f"Could not delete stale announcement message for absence {absence.id}")
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
