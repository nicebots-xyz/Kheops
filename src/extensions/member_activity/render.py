# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import discord

from .logic import EUROPE_PARIS, StatsPeriod, period_start
from .stats import PERIOD_LABELS, get_stats

if TYPE_CHECKING:
    from .translations import ExtensionStrings as Strings


async def render_activity(member: discord.Member, period: StatsPeriod, t: Strings) -> discord.Embed:
    """Build the activity card of `member`: messages and voice time, no quota or conformity notion."""
    now = datetime.now(tz=EUROPE_PARIS)
    stats = (await get_stats(member.guild.id, period_start(period, now), now)).get(member.id, (0, 0.0))
    embed = discord.Embed(
        title=member.display_name, description=f"-# {PERIOD_LABELS[period]}", colour=discord.Colour.blurple()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(
        name=t.card_activity, value=t.card_activity_value.format(messages=stats[0], hours=f"{stats[1] / 60:.1f}")
    )
    return embed


__all__ = ("render_activity",)
