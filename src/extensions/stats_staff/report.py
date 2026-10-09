# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, final

import discord
from discord.ext import tasks
from discord.utils import format_dt

from src.database.models import StaffQuotaMode, StaffRoleQuota, StaffStatsSettings
from src.log import logger as base_logger

from .logic import (
    EUROPE_PARIS,
    chunk_text_lines,
    completion_ratio,
    evaluate_quota,
    previous_week_bounds,
    progress_bar,
    should_send_weekly_report,
    trend_arrow,
    week_start,
    weekly_report_deadline,
)
from .quotas import resolve_members_by_quota
from .stats import bulk_compute_stats

if TYPE_CHECKING:
    from src import custom

logger = base_logger.getChild("stats_staff")

TEXT_DISPLAY_MAX_CHARS = 3900


def _build_role_report_blocks(
    quota: StaffRoleQuota,
    role: discord.Role,
    members: list[discord.Member],
    stats_by_member: dict[int, tuple[int, float, int, float]],
    et_penalty: float,
) -> tuple[list[discord.ui.Container[discord.ui.DesignerView]], int, int, list[discord.Member]]:
    mode_label = "ET" if quota.mode == StaffQuotaMode.ALL else "OU"
    lines = [
        f"### {role.mention}",
        f"-# Quota : {quota.voice_minutes_required / 60:g}h vocal **{mode_label}** {quota.messages_required} messages",
    ]

    passed_count = 0
    zero_activity_members: list[discord.Member] = []
    for member in sorted(members, key=lambda m: m.display_name.lower()):
        messages, voice_minutes, last_messages, last_voice_minutes = stats_by_member.get(member.id, (0, 0.0, 0, 0.0))
        passed = evaluate_quota(
            quota.mode,
            messages=messages,
            messages_required=quota.messages_required,
            voice_minutes=voice_minutes,
            voice_minutes_required=quota.voice_minutes_required,
            et_penalty=et_penalty,
        )
        passed_count += passed
        ratio = completion_ratio(
            quota.mode,
            messages=messages,
            messages_required=quota.messages_required,
            voice_minutes=voice_minutes,
            voice_minutes_required=quota.voice_minutes_required,
        )
        last_ratio = completion_ratio(
            quota.mode,
            messages=last_messages,
            messages_required=quota.messages_required,
            voice_minutes=last_voice_minutes,
            voice_minutes_required=quota.voice_minutes_required,
        )

        if messages == 0 and voice_minutes == 0:
            zero_activity_members.append(member)
            emoji = "🚨"
        else:
            emoji = "✅" if passed else "❌"
        lines.append(
            f"{emoji} **{member.display_name}** — {voice_minutes / 60:.1f}h vocal · {messages} messages\n"
            + f"-# {progress_bar(ratio)} · {trend_arrow(ratio, last_ratio)} vs semaine dernière"
        )

    if not members:
        lines.append("-# Aucun membre.")
        colour = discord.Colour.light_grey()
    elif passed_count == len(members):
        colour = discord.Colour.green()
    elif passed_count == 0:
        colour = discord.Colour.red()
    else:
        colour = discord.Colour.gold()

    containers = [
        discord.ui.Container[discord.ui.DesignerView](discord.ui.TextDisplay(chunk), colour=colour)
        for chunk in chunk_text_lines(lines, TEXT_DISPLAY_MAX_CHARS)
    ]
    return containers, passed_count, len(members), zero_activity_members


async def build_weekly_report_view(
    guild: discord.Guild, settings: StaffStatsSettings, now: datetime
) -> discord.ui.DesignerView:
    quotas = await StaffRoleQuota.filter(guild_id=guild.id)
    members_by_quota_id = await resolve_members_by_quota(guild, quotas)
    all_member_ids = [member.id for members in members_by_quota_id.values() for member in members]
    last_week_start, last_week_end = previous_week_bounds(now)
    stats_by_member = await bulk_compute_stats(guild.id, all_member_ids, now, last_week_start, last_week_end)

    role_blocks: list[discord.ui.Container[discord.ui.DesignerView]] = []
    total_passed = 0
    total_members = 0
    all_zero_activity: list[discord.Member] = []
    for quota in quotas:
        role = guild.get_role(quota.role_id)
        if role is None:
            continue
        members = members_by_quota_id.get(quota.id, [])
        blocks, passed_count, member_count, zero_activity_members = _build_role_report_blocks(
            quota, role, members, stats_by_member, settings.et_substitution_penalty
        )
        role_blocks.extend(blocks)
        total_passed += passed_count
        total_members += member_count
        all_zero_activity.extend(zero_activity_members)

    start = week_start(now)
    header_lines = [
        "## 📊 Rapport hebdomadaire des quotas staff",
        f"-# Semaine du {format_dt(start, style='D')} — {total_passed}/{total_members} quota(s) atteint(s)",
    ]
    items: list[discord.ui.ViewItem[discord.ui.DesignerView]] = [
        discord.ui.Container[discord.ui.DesignerView](discord.ui.TextDisplay("\n".join(header_lines)))
    ]

    if all_zero_activity and settings.responsible_role_id is not None:
        mention_chunks = chunk_text_lines(
            [member.mention for member in all_zero_activity], TEXT_DISPLAY_MAX_CHARS, sep=", "
        )
        alert_lines = [
            f"## 🚨 <@&{settings.responsible_role_id}> — aucune activité cette semaine",
            f"{len(all_zero_activity)} membre(s) n'ont fait ni message ni vocal cette semaine :",
            *mention_chunks,
        ]
        items.extend(
            discord.ui.Container[discord.ui.DesignerView](
                discord.ui.TextDisplay(chunk),
                colour=discord.Colour.dark_red(),
            )
            for chunk in chunk_text_lines(alert_lines, TEXT_DISPLAY_MAX_CHARS)
        )

    items.extend(role_blocks)
    return discord.ui.DesignerView(*items)


async def send_weekly_report(bot: custom.Bot, settings: StaffStatsSettings, now: datetime) -> None:
    assert settings.report_channel_id is not None
    guild = bot.get_guild(settings.guild_id)
    if guild is None:
        logger.warning(f"Guild {settings.guild_id} not found, skipping weekly staff report")
        return

    view = await build_weekly_report_view(guild, settings, now)
    channel = bot.get_partial_messageable(settings.report_channel_id)
    try:
        await channel.send(view=view)
    except (discord.Forbidden, discord.HTTPException):
        logger.exception(f"Failed to post weekly staff report in channel {settings.report_channel_id}")
        return

    # The deadline's date, not `now`'s — the grace window lets this fire a little into Monday,
    # and storing `now.date()` there would record the wrong day and never match
    # `weekly_report_deadline(...).date()` on a later check, causing an immediate re-send.
    settings.last_report_sent_date = weekly_report_deadline(now).date()
    await settings.save()


@final
class ReportCog(discord.Cog):
    def __init__(self, bot: custom.Bot) -> None:
        self.bot: custom.Bot = bot
        self.report_loop: tasks.Loop = tasks.loop(minutes=5)(self.report_loop_meth)  # pyright: ignore [reportMissingTypeArgument]

    @discord.Cog.listener("on_ready", once=True)
    async def on_ready(self) -> None:
        self.report_loop.start()

    async def report_loop_meth(self) -> None:
        try:
            now = datetime.now(tz=EUROPE_PARIS)
            all_settings = await StaffStatsSettings.filter(report_channel_id__isnull=False)
        except Exception:
            logger.exception("Failed to fetch staff stats settings for the weekly report loop")
            return

        for settings in all_settings:
            if not should_send_weekly_report(now, settings.last_report_sent_date):
                continue
            try:
                await send_weekly_report(self.bot, settings, now)
            except Exception:
                logger.exception(f"Failed to send weekly staff report for guild {settings.guild_id}")


__all__ = ("ReportCog", "build_weekly_report_view", "send_weekly_report")
