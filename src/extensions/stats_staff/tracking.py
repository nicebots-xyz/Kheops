# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, final

import discord
from discord.ext import tasks

from src.database.models import StaffMessageEvent, StaffRoleQuota, StaffStatsSettings, StaffVoiceSegment
from src.log import logger as base_logger

from .logic import is_valid_voice_state

if TYPE_CHECKING:
    from src import custom

logger = base_logger.getChild("stats_staff")

CHECKPOINT_INTERVAL = timedelta(minutes=1)


@final
class TrackingCog(discord.Cog):
    def __init__(self, bot: custom.Bot) -> None:
        self.bot: custom.Bot = bot
        self.open_segments: dict[tuple[int, int], StaffVoiceSegment] = {}
        self.checkpoint_loop: tasks.Loop = tasks.loop(minutes=1)(self.checkpoint_loop_meth)  # pyright: ignore [reportMissingTypeArgument]

    @discord.Cog.listener("on_ready", once=True)
    async def on_ready(self) -> None:
        logger.info("Stats staff tracking cog ready, reconciling voice segments")
        await self._reconcile_voice_segments()
        self.checkpoint_loop.start()

    def _is_member_valid_now(
        self, member: discord.Member, quota_role_ids: set[int], tracked_channel_ids: list[int]
    ) -> bool:
        if member.bot or not any(role.id in quota_role_ids for role in member.roles):
            return False
        voice_state = member.voice
        if voice_state is None or voice_state.channel is None:
            return False
        if voice_state.channel.id not in tracked_channel_ids:
            return False
        other_humans = sum(1 for m in voice_state.channel.members if not m.bot and m.id != member.id)
        return is_valid_voice_state(voice_state, other_humans=other_humans)

    async def _recompute_validity(
        self, member: discord.Member, quota_role_ids: set[int], tracked_channel_ids: list[int]
    ) -> None:
        valid = self._is_member_valid_now(member, quota_role_ids, tracked_channel_ids)
        key = (member.guild.id, member.id)
        open_segment = self.open_segments.get(key)
        now = datetime.now(tz=UTC)
        if valid and open_segment is None:
            assert member.voice is not None
            assert member.voice.channel is not None
            segment = await StaffVoiceSegment.create(
                guild_id=member.guild.id, member_id=member.id, channel_id=member.voice.channel.id, started_at=now
            )
            self.open_segments[key] = segment
        elif not valid and open_segment is not None:
            open_segment.ended_at = now
            await open_segment.save()
            del self.open_segments[key]

    async def checkpoint_loop_meth(self) -> None:
        """Roll every still-valid open voice segment over into a fresh one, closing invalid ones.

        Bounds how much voice time a crash or hard restart can over-credit (the reconciliation
        on the next startup closes whatever is still open, at its last checkpoint) to at most one
        checkpoint interval, instead of the full downtime. Also re-validates each segment against
        current settings/quotas/roles on every tick, so a quota role or tracked channel removed
        mid-session (and a member leaving the server) stops being credited within one interval,
        rather than silently forever.
        """
        now = datetime.now(tz=UTC)
        settings_cache: dict[int, StaffStatsSettings | None] = {}
        quota_role_ids_cache: dict[int, set[int]] = {}

        for key, segment in list(self.open_segments.items()):
            guild_id, member_id = key
            try:
                await self._checkpoint_one_segment(key, segment, now, settings_cache, quota_role_ids_cache)
            except Exception:
                logger.exception(f"Failed to checkpoint voice segment for member {member_id} in guild {guild_id}")

    async def _checkpoint_one_segment(
        self,
        key: tuple[int, int],
        segment: StaffVoiceSegment,
        now: datetime,
        settings_cache: dict[int, StaffStatsSettings | None],
        quota_role_ids_cache: dict[int, set[int]],
    ) -> None:
        guild_id, member_id = key
        still_valid = await self._revalidate_open_segment(guild_id, member_id, settings_cache, quota_role_ids_cache)

        if self.open_segments.get(key) is not segment:
            return  # closed or replaced concurrently while we were checking

        segment.ended_at = now
        await segment.save()

        if not still_valid:
            if self.open_segments.get(key) is segment:
                del self.open_segments[key]
            return

        if self.open_segments.get(key) is not segment:
            return  # closed concurrently between the save above and here

        new_segment = await StaffVoiceSegment.create(
            guild_id=guild_id, member_id=member_id, channel_id=segment.channel_id, started_at=now
        )
        if self.open_segments.get(key) is not segment:
            await new_segment.delete()
            return
        self.open_segments[key] = new_segment

    async def _revalidate_open_segment(
        self,
        guild_id: int,
        member_id: int,
        settings_cache: dict[int, StaffStatsSettings | None],
        quota_role_ids_cache: dict[int, set[int]],
    ) -> bool:
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return False
        member = guild.get_member(member_id)
        if member is None:
            return False
        if guild_id not in settings_cache:
            settings_cache[guild_id] = await StaffStatsSettings.get_or_none(guild_id=guild_id)
        settings = settings_cache[guild_id]
        if settings is None or not settings.voice_channel_ids:
            return False
        if guild_id not in quota_role_ids_cache:
            quota_role_ids_cache[guild_id] = {q.role_id for q in await StaffRoleQuota.filter(guild_id=guild_id)}
        return self._is_member_valid_now(member, quota_role_ids_cache[guild_id], settings.voice_channel_ids)

    async def _reconcile_voice_segments(self) -> None:
        now = datetime.now(tz=UTC)
        stale = await StaffVoiceSegment.filter(ended_at__isnull=True)
        for segment in stale:
            # Bounded to the last checkpoint instead of `now`: a segment left open across a crash
            # or hard restart was last known-valid at most one checkpoint interval before it was
            # orphaned, so closing it at the restart time instead would over-credit the entire
            # downtime.
            segment.ended_at = min(now, segment.started_at + CHECKPOINT_INTERVAL)
            await segment.save()

        all_settings = await StaffStatsSettings.all()
        for settings in all_settings:
            if not settings.voice_channel_ids:
                continue
            guild = self.bot.get_guild(settings.guild_id)
            if guild is None:
                continue
            quota_role_ids = {q.role_id for q in await StaffRoleQuota.filter(guild_id=guild.id)}
            for channel_id in settings.voice_channel_ids:
                channel = guild.get_channel(channel_id)
                if not isinstance(channel, discord.VoiceChannel):
                    continue
                for member in channel.members:
                    await self._recompute_validity(member, quota_role_ids, settings.voice_channel_ids)

    @discord.Cog.listener("on_voice_state_update")
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if member.bot:
            return
        settings = await StaffStatsSettings.get_or_none(guild_id=member.guild.id)
        if settings is None or not settings.voice_channel_ids:
            return
        quota_role_ids = {q.role_id for q in await StaffRoleQuota.filter(guild_id=member.guild.id)}
        if not quota_role_ids:
            return

        # A join/leave/mute toggle can flip whether *other* members in the channel count as
        # "alone", so every current member of an affected channel needs re-checking — not just
        # the member who triggered the event (who is included here too, so leaving voice entirely
        # closes their own segment the same way, without a separate special case).
        affected_members: dict[int, discord.Member] = {member.id: member}
        for state in (before, after):
            if state.channel is not None and state.channel.id in settings.voice_channel_ids:
                for other in state.channel.members:
                    affected_members[other.id] = other

        for affected in affected_members.values():
            await self._recompute_validity(affected, quota_role_ids, settings.voice_channel_ids)

    @discord.Cog.listener("on_message")
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None or not isinstance(message.author, discord.Member):
            return
        settings = await StaffStatsSettings.get_or_none(guild_id=message.guild.id)
        if settings is None or message.channel.id not in settings.message_channel_ids:
            return
        quota_role_ids = {q.role_id for q in await StaffRoleQuota.filter(guild_id=message.guild.id)}
        if not any(role.id in quota_role_ids for role in message.author.roles):
            return
        await StaffMessageEvent.create(
            guild_id=message.guild.id, member_id=message.author.id, channel_id=message.channel.id
        )


__all__ = ("TrackingCog",)
