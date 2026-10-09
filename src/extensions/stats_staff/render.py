# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from datetime import datetime

import discord

from src.database.models import StaffQuotaMode, StaffStatsSettings

from .logic import (
    EUROPE_PARIS,
    StatsPeriod,
    completion_ratio,
    evaluate_quota,
    previous_week_bounds,
    progress_bar,
    trend_arrow,
)
from .quotas import find_quota_role
from .stats import PERIOD_LABELS, compute_stats, compute_stats_range


async def render_stats(member: discord.Member, period: StatsPeriod) -> discord.ui.DesignerView:
    quota = await find_quota_role(member)
    now = datetime.now(tz=EUROPE_PARIS)
    messages, voice_minutes = await compute_stats(member.guild.id, member.id, period, now)
    period_label = PERIOD_LABELS[period]

    header = discord.ui.Section[discord.ui.DesignerView](
        discord.ui.TextDisplay(f"## {member.display_name}\n-# {period_label}"),
        accessory=discord.ui.Thumbnail(member.display_avatar.url),
    )
    activity_block = discord.ui.TextDisplay(  # pyright: ignore[reportUnknownVariableType]
        f"### 📈 Activité\n**{messages}** messages · **{voice_minutes / 60:.1f}h** de vocal"
    )

    if quota is None:
        container = discord.ui.Container[discord.ui.DesignerView](
            header,
            discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large),
            activity_block,
            discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large),
            discord.ui.TextDisplay("-# Ce membre n'a pas de rôle avec quota configuré."),
            colour=discord.Colour.light_grey(),
        )
        return discord.ui.DesignerView(container)

    settings = await StaffStatsSettings.get_or_none(guild_id=member.guild.id)
    et_penalty = settings.et_substitution_penalty if settings is not None else 1.25
    passed = evaluate_quota(
        quota.mode,
        messages=messages,
        messages_required=quota.messages_required,
        voice_minutes=voice_minutes,
        voice_minutes_required=quota.voice_minutes_required,
        et_penalty=et_penalty,
    )
    ratio = completion_ratio(
        quota.mode,
        messages=messages,
        messages_required=quota.messages_required,
        voice_minutes=voice_minutes,
        voice_minutes_required=quota.voice_minutes_required,
    )
    mode_label = "ET" if quota.mode == StaffQuotaMode.ALL else "OU"
    status_label = "Quota atteint" if passed else "Quota non atteint"
    status_emoji = "✅" if passed else "❌"

    quota_block = discord.ui.TextDisplay(  # pyright: ignore[reportUnknownVariableType]
        f"### 🎯 Quota ({mode_label})\n"
        + f"{quota.voice_minutes_required / 60:g}h vocal **{mode_label}** {quota.messages_required} messages\n"
        + f"{progress_bar(ratio)}\n"
        + f"{status_emoji} **{status_label}**"
    )

    items: list[discord.ui.ViewItem[discord.ui.DesignerView]] = [
        header,
        discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large),
        activity_block,
        discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large),
        quota_block,
    ]

    if period == StatsPeriod.WEEK:
        last_week_start, last_week_end = previous_week_bounds(now)
        last_messages, last_voice_minutes = await compute_stats_range(
            member.guild.id, member.id, last_week_start, last_week_end
        )
        last_ratio = completion_ratio(
            quota.mode,
            messages=last_messages,
            messages_required=quota.messages_required,
            voice_minutes=last_voice_minutes,
            voice_minutes_required=quota.voice_minutes_required,
        )
        items.append(discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large))
        items.append(
            discord.ui.TextDisplay(  # pyright: ignore[reportUnknownArgumentType]
                f"### 📊 Tendance\n{trend_arrow(ratio, last_ratio)} vs semaine dernière"
            )
        )

    container = discord.ui.Container[discord.ui.DesignerView](
        *items,
        colour=discord.Colour.green() if passed else discord.Colour.red(),
    )
    return discord.ui.DesignerView(container)


__all__ = ("render_stats",)
