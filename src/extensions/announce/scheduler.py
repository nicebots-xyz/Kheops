# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from typing import TYPE_CHECKING, final

import discord
from discord.ext import tasks

from src.log import logger as base_logger

from .queries import due_announcements
from .send import send_announcement

if TYPE_CHECKING:
    from src import custom

logger = base_logger.getChild("announce")


@final
class AnnounceSchedulerCog(discord.Cog):
    """Sends scheduled announcements once their time has come.

    A 1-minute tick (same technique as `stats_staff.tracking.TrackingCog`) rather than a generic
    scheduler library: this bot has none, and a dedicated announcement scheduler would be a lot
    of new infrastructure for "check one table every minute" — the simplest thing that works.
    """

    def __init__(self, bot: "custom.Bot") -> None:
        self.bot: custom.Bot = bot

    @discord.Cog.listener("on_ready", once=True)
    async def on_ready(self) -> None:
        self.send_due_loop.start()

    @tasks.loop(minutes=1)
    async def send_due_loop(self) -> None:
        try:
            for announcement in await due_announcements():
                await send_announcement(self.bot, announcement)
        except Exception:
            logger.exception("Failed to process due announcements")


__all__ = ("AnnounceSchedulerCog",)
