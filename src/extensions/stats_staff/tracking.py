# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, replace
from typing import TYPE_CHECKING, final
from uuid import UUID, uuid4

import discord
from discord.ext import tasks

from src.database.models import StaffMessageEvent, StaffRoleQuota, StaffStatsSettings, StaffVoiceSession
from src.database.utils.atomics import in_transaction
from src.log import logger as base_logger

from .logic import counting_channel_id, is_tracked_channel

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from src import custom

logger = base_logger.getChild("stats_staff")


# Field names match StaffVoiceSession / StaffMessageEvent, so rows are built with asdict().
@dataclass(slots=True)
class Session:
    id: UUID
    guild_id: int
    member_id: int
    channel_id: int
    started_at: datetime
    ended_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class PendingMessage:
    guild_id: int
    member_id: int
    channel_id: int
    created_at: datetime


class VoiceTracker:
    """Voice sessions and messages kept in memory until the next flush writes them.

    Every method is synchronous on purpose: asyncio only switches tasks at an `await`, so each call
    runs as one uninterrupted step and needs no lock.
    """

    def __init__(self) -> None:
        self.open: dict[tuple[int, int], Session] = {}
        self.closed: list[Session] = []
        self.messages: list[PendingMessage] = []

    def sync(self, guild_id: int, member_id: int, channel_id: int | None, now: datetime) -> None:
        """Record where a member is counting right now.

        Nothing changes while the member keeps counting in the same channel. Any change closes the
        open session, and a new one starts if the member is still counting.

        Args:
            guild_id: The guild.
            member_id: The member.
            channel_id: The channel the member counts in right now, or None if not counting.
            now: The current time.

        """
        key = (guild_id, member_id)
        current = self.open.get(key)
        if current is not None and current.channel_id == channel_id:
            return
        if current is not None:
            current.ended_at = now
            self.closed.append(self.open.pop(key))
        if channel_id is not None:
            self.open[key] = Session(uuid4(), guild_id, member_id, channel_id, now)

    def take(self, now: datetime) -> tuple[list[Session], list[Session], list[PendingMessage]]:
        """Hand over everything to write and forget what is finished.

        Args:
            now: The time open sessions are written up to.

        Returns:
            The finished sessions, copies of the open sessions ending at `now`, and the messages.

        """
        finished, messages = self.closed, self.messages
        self.closed, self.messages = [], []
        return finished, [replace(session, ended_at=now) for session in self.open.values()], messages

    def restore(self, finished: list[Session], messages: list[PendingMessage]) -> None:
        """Put back what a failed write did not save. Open sessions are simply rewritten next time."""
        self.closed[:0] = finished
        self.messages[:0] = messages


@dataclass(slots=True, frozen=True)
class TrackingConfig:
    message_channel_ids: frozenset[int]
    voice_channel_ids: frozenset[int]
    category_ids: frozenset[int]
    quota_role_ids: frozenset[int]


@final
class TrackingCog(discord.Cog):
    def __init__(self, bot: custom.Bot) -> None:
        self.bot: custom.Bot = bot
        self.tracker: VoiceTracker = VoiceTracker()
        self.configs: dict[int, TrackingConfig] = {}
        self.flush_lock: asyncio.Lock = asyncio.Lock()

    @discord.Cog.listener("on_ready", once=True)
    async def on_ready(self) -> None:
        self.flush_loop.start()

    @tasks.loop(minutes=2)
    async def flush_loop(self) -> None:
        try:
            guild_ids = {settings.guild_id for settings in await StaffStatsSettings.all()}
            for guild_id in guild_ids | {guild_id for guild_id, _ in self.tracker.open}:
                await self.reload_config(guild_id)
        except Exception:
            logger.exception("Failed to reload staff stats config")
        await self.flush()

    async def reload_config(self, guild_id: int) -> None:
        """Reload a guild's tracked channels and quota roles, then re-check its members."""
        settings = await StaffStatsSettings.get_or_none(guild_id=guild_id)
        if settings is None:
            self.configs.pop(guild_id, None)
        else:
            role_ids = {quota.role_id for quota in await StaffRoleQuota.filter(guild_id=guild_id)}
            self.configs[guild_id] = TrackingConfig(
                frozenset(settings.message_channel_ids),
                frozenset(settings.voice_channel_ids),
                frozenset(settings.tracked_category_ids),
                frozenset(role_ids),
            )
        self._sync_guild(guild_id)

    async def flush(self) -> None:
        """Write pending sessions and messages. Readers flush first; a failed write is retried next time."""
        # The only lock: two flushes running at once could finish out of order and move a session's
        # `ended_at` backwards.
        async with self.flush_lock:
            finished, ongoing, messages = self.tracker.take(discord.utils.utcnow())
            try:
                async with in_transaction() as connection:
                    await StaffVoiceSession.bulk_create(
                        [StaffVoiceSession(**asdict(session)) for session in (*finished, *ongoing)],
                        on_conflict=["id"],
                        update_fields=["ended_at"],
                        using_db=connection,
                    )
                    await StaffMessageEvent.bulk_create(
                        [StaffMessageEvent(**asdict(message)) for message in messages], using_db=connection
                    )
            except Exception:
                self.tracker.restore(finished, messages)
                logger.exception("Failed to write staff stats, will retry on the next flush")

    def _want(self, member: discord.Member | None) -> int | None:
        config = self.configs.get(member.guild.id) if member is not None else None
        if member is None or config is None:
            return None
        return counting_channel_id(member, config.voice_channel_ids, config.category_ids, config.quota_role_ids)

    def _sync(self, members: Iterable[discord.Member]) -> None:
        now = discord.utils.utcnow()
        for member in members:
            self.tracker.sync(member.guild.id, member.id, self._want(member), now)

    def _sync_guild(self, guild_id: int) -> None:
        """Re-check everyone in the guild's tracked channels, and everyone with an open session."""
        now = discord.utils.utcnow()
        guild = self.bot.get_guild(guild_id)
        config = self.configs.get(guild_id)
        member_ids = {member_id for g, member_id in self.tracker.open if g == guild_id}
        if guild is not None and config is not None:
            for channel in guild.voice_channels:
                if is_tracked_channel(channel, config.voice_channel_ids, config.category_ids):
                    member_ids.update(member.id for member in channel.members)
        for member_id in member_ids:
            member = guild.get_member(member_id) if guild is not None else None
            self.tracker.sync(guild_id, member_id, self._want(member), now)

    @discord.Cog.listener("on_voice_state_update")
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        # py-cord updates its cache before running listeners, so the cache may already be newer than
        # `after`. Re-check the current state of everyone affected instead of comparing before/after:
        # one join, leave or mute can also change whether someone else in the channel is alone.
        affected = {member.id: member}
        for state in (before, after):
            if state.channel is not None:
                affected.update((other.id, other) for other in state.channel.members)
        self._sync(affected.values())

    @discord.Cog.listener("on_member_update")
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.roles != after.roles:
            self._sync([after])

    @discord.Cog.listener("on_message")
    async def on_message(self, message: discord.Message) -> None:
        author = message.author
        if message.guild is None or author.bot or not isinstance(author, discord.Member):
            return
        config = self.configs.get(message.guild.id)
        channel = message.channel
        if (
            config is None
            or isinstance(channel, discord.DMChannel | discord.GroupChannel | discord.PartialMessageable)
            or not is_tracked_channel(channel, config.message_channel_ids, config.category_ids)
        ):
            return
        if any(role.id in config.quota_role_ids for role in author.roles):
            self.tracker.messages.append(
                PendingMessage(message.guild.id, author.id, message.channel.id, message.created_at)
            )


__all__ = ("PendingMessage", "Session", "TrackingCog", "VoiceTracker")
