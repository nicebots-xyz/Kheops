# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, Never, final

import discord
from discord.ext import tasks
from discord.ui import Container, DesignerView, TextDisplay
from discord.utils import format_dt

from src.database.models import StaffQuotaMode, StaffRoleQuota, StaffStatsSettings
from src.i18n.classes import apply_locale
from src.log import logger as base_logger

from .logic import EUROPE_PARIS, chunk_text_lines, progress_bar, trend_arrow, week_start
from .quotas import members_by_quota
from .render import score_for
from .stats import get_stats

if TYPE_CHECKING:
    from src import custom
    from src.i18n.classes import RawTranslation

    from .stats import Strings
    from .tracking import TrackingCog

logger = base_logger.getChild("stats_staff")

# Components V2 messages hold at most 4000 characters of text in total.
MAX_MESSAGE_CHARS = 3900


def _view(content: str, colour: discord.Colour | None = None) -> DesignerView:
    return DesignerView(Container[DesignerView](TextDisplay[DesignerView, Never](content), colour=colour))


def _role_block(
    t: Strings,
    quota: StaffRoleQuota,
    role: discord.Role,
    members: list[discord.Member],
    stats: dict[int, tuple[int, float]],
    previous: dict[int, tuple[int, float]],
    penalty: float,
) -> tuple[list[DesignerView], int, list[discord.Member]]:
    mode = "ET" if quota.mode == StaffQuotaMode.ALL else "OU"
    hours = f"{quota.voice_minutes_required / 60:g}"
    lines = [f"### {role.mention}", t.report_quota.format(hours=hours, mode=mode, messages=quota.messages_required)]
    passed = 0
    inactive: list[discord.Member] = []
    for member in sorted(members, key=lambda m: m.display_name.lower()):
        messages, voice_minutes = stats.get(member.id, (0, 0.0))
        score = score_for(quota, (messages, voice_minutes), penalty)
        passed += score >= 1
        emoji = "✅" if score >= 1 else "❌"
        if messages == 0 and voice_minutes == 0:
            inactive.append(member)
            emoji = "🚨"
        last_score = score_for(quota, previous.get(member.id, (0, 0.0)), penalty)
        lines.append(
            t.report_member_line.format(
                emoji=emoji,
                name=member.display_name,
                hours=f"{voice_minutes / 60:.1f}",
                messages=messages,
                bar=progress_bar(score),
                trend=t.vs_last_week.format(trend=trend_arrow(score, last_score)),
            )
        )
    if not members:
        lines.append(t.report_no_members)
        colour = discord.Colour.light_grey()
    elif passed == len(members):
        colour = discord.Colour.green()
    elif passed == 0:
        colour = discord.Colour.red()
    else:
        colour = discord.Colour.gold()
    return [_view(chunk, colour) for chunk in chunk_text_lines(lines, MAX_MESSAGE_CHARS)], passed, inactive


async def build_report(
    guild: discord.Guild,
    settings: StaffStatsSettings,
    t: Strings,
    period: tuple[datetime, datetime],
    comparison: tuple[datetime, datetime],
) -> list[DesignerView]:
    """Build the report as a list of messages: a header (with the inactivity alert), then one per role.

    Args:
        guild: The guild.
        settings: The guild's stats settings.
        t: The strings, already in the guild's locale.
        period: The `(start, end)` being reported.
        comparison: The `(start, end)` the trend compares with.

    Returns:
        One view per message to send, in order.

    """
    quotas = await StaffRoleQuota.filter(guild_id=guild.id)
    grouped = await members_by_quota(guild, quotas)
    stats = await get_stats(guild.id, *period)
    previous = await get_stats(guild.id, *comparison)

    role_views: list[DesignerView] = []
    total_passed = total_members = 0
    inactive: list[discord.Member] = []
    for quota in quotas:
        role = guild.get_role(quota.role_id)
        if role is None:
            continue
        members = grouped.get(quota.id, [])
        views, passed, role_inactive = _role_block(
            t, quota, role, members, stats, previous, settings.et_substitution_penalty
        )
        role_views += views
        total_passed += passed
        total_members += len(members)
        inactive += role_inactive

    header = [
        _view(t.report_header.format(date=format_dt(period[0], style="D"), passed=total_passed, total=total_members))
    ]
    if inactive and settings.responsible_role_id is not None:
        alert = t.report_alert.format(
            role=f"<@&{settings.responsible_role_id}>",
            count=len(inactive),
            members=", ".join(member.mention for member in inactive),
        )
        header.append(_view(alert, discord.Colour.dark_red()))
    return header + role_views


@final
class ReportCog(discord.Cog):
    def __init__(self, bot: custom.Bot, tracking: TrackingCog, strings: dict[str, RawTranslation]) -> None:
        self.bot: custom.Bot = bot
        self.tracking: TrackingCog = tracking
        self.strings: dict[str, RawTranslation] = strings

    @discord.Cog.listener("on_ready", once=True)
    async def on_ready(self) -> None:
        self.report_loop.start()

    @tasks.loop(time=time(0, 5, tzinfo=EUROPE_PARIS))
    async def report_loop(self) -> None:
        """Every Monday at 00:05, report the week that just ended."""
        now = datetime.now(tz=EUROPE_PARIS)
        if now.weekday() != 0:
            return
        await self.tracking.flush()
        end = week_start(now)
        start = end - timedelta(days=7)
        for settings in await StaffStatsSettings.filter(report_channel_id__isnull=False):
            try:
                await self.send_report(settings, (start, end), (start - timedelta(days=7), start))
            except Exception:
                logger.exception(f"Failed to send the weekly staff report for guild {settings.guild_id}")

    async def send_report(
        self, settings: StaffStatsSettings, period: tuple[datetime, datetime], comparison: tuple[datetime, datetime]
    ) -> None:
        guild = self.bot.get_guild(settings.guild_id)
        if guild is None or settings.report_channel_id is None:
            return
        t = apply_locale(self.strings, guild.preferred_locale)
        views = await build_report(guild, settings, t, period, comparison)
        channel = self.bot.get_partial_messageable(settings.report_channel_id)
        # The weekly report pings ONLY the responsible role: not the staff roles in the headers, not the
        # inactive members listed in the alert. To change who gets pinged by the report, change it here.
        mentions = discord.AllowedMentions(
            everyone=False,
            users=False,
            roles=[discord.Object(settings.responsible_role_id)] if settings.responsible_role_id else False,
        )
        for view in views:
            await channel.send(view=view, allowed_mentions=mentions)


__all__ = ("ReportCog", "build_report")
