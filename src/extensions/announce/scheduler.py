# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, final, override

import discord
from discord.ext import tasks

from src.log import logger as base_logger

from .queries import due_announcement_ids, fail_interrupted_sends
from .send import send_scheduled

if TYPE_CHECKING:
    from uuid import UUID

    from src import custom
    from src.i18n.classes import RawTranslation

logger = base_logger.getChild("announce")

#: Announcements sent at once, bounding the images held in memory at the same time.
MAX_CONCURRENT_SENDS = 5


@final
class AnnounceSchedulerCog(discord.Cog):
    """Sends scheduled announcements once their time has come, checking every minute."""

    def __init__(self, bot: custom.Bot, strings: dict[str, RawTranslation]) -> None:
        self.bot: custom.Bot = bot
        self.strings: dict[str, RawTranslation] = strings
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_SENDS)

    @discord.Cog.listener("on_ready", once=True)
    async def on_ready(self) -> None:
        if failed := await fail_interrupted_sends():
            logger.warning(f"Marked {failed} announcements interrupted while sending as failed")
        self.send_due_loop.start()

    @override
    def cog_unload(self) -> None:
        self.send_due_loop.cancel()

    async def _send(self, announcement_id: UUID) -> None:
        """Send one due announcement, logging instead of raising so its siblings still go out.

        Args:
            announcement_id: The announcement's ID.

        """
        async with self._semaphore:
            try:
                await send_scheduled(self.bot, announcement_id, self.strings)
            except Exception:
                logger.exception(f"Failed to process due announcement {announcement_id}")

    @tasks.loop(minutes=1)
    async def send_due_loop(self) -> None:
        try:
            due = await due_announcement_ids(datetime.now(tz=UTC))
        except Exception:
            logger.exception("Failed to list due announcements")
            return
        async with asyncio.TaskGroup() as group:
            for announcement_id in due:
                group.create_task(self._send(announcement_id))


__all__ = ("AnnounceSchedulerCog",)
