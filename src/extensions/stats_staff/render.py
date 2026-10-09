# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import discord

from src.database.models import StaffQuotaMode, StaffRoleQuota, StaffStatsSettings

from .logic import EUROPE_PARIS, StatsPeriod, period_start, previous_week_bounds, progress_bar, quota_score, trend_arrow
from .stats import PERIOD_LABELS, get_stats

if TYPE_CHECKING:
    from .stats import Strings


def score_for(quota: StaffRoleQuota, stats: tuple[int, float], penalty: float) -> float:
    messages, voice_minutes = stats
    return quota_score(
        quota.mode,
        messages=messages,
        messages_required=quota.messages_required,
        voice_minutes=voice_minutes,
        voice_minutes_required=quota.voice_minutes_required,
        penalty=penalty,
    )


async def render_stats(
    member: discord.Member, quota: StaffRoleQuota | None, period: StatsPeriod, t: Strings
) -> discord.Embed:
    """Build the stats card of `member`: activity, quota and (for the current week) trend, side by side."""
    now = datetime.now(tz=EUROPE_PARIS)
    stats = (await get_stats(member.guild.id, period_start(period, now), now)).get(member.id, (0, 0.0))
    embed = discord.Embed(
        title=member.display_name, description=f"-# {PERIOD_LABELS[period]}", colour=discord.Colour.light_grey()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(
        name=t.card_activity, value=t.card_activity_value.format(messages=stats[0], hours=f"{stats[1] / 60:.1f}")
    )
    if quota is None:
        embed.add_field(name=t.card_quota, value=t.card_no_quota)
        return embed

    settings = await StaffStatsSettings.get_or_none(guild_id=member.guild.id)
    penalty = settings.et_substitution_penalty if settings is not None else 1.25
    score = score_for(quota, stats, penalty)
    passed = score >= 1
    mode = "ET" if quota.mode == StaffQuotaMode.ALL else "OU"
    embed.colour = discord.Colour.green() if passed else discord.Colour.red()
    embed.add_field(
        name=t.card_quota_mode.format(mode=mode),
        value=t.quota_requirement.format(
            hours=f"{quota.voice_minutes_required / 60:g}", mode=mode, messages=quota.messages_required
        )
        + f"\n{progress_bar(score)}\n"
        + (t.card_passed if passed else t.card_failed),
    )
    if period == StatsPeriod.WEEK:
        last_start, last_end = previous_week_bounds(now)
        last = (await get_stats(member.guild.id, last_start, last_end)).get(member.id, (0, 0.0))
        embed.add_field(
            name=t.card_trend, value=t.vs_last_week.format(trend=trend_arrow(score, score_for(quota, last, penalty)))
        )
    return embed


__all__ = ("render_stats", "score_for")
