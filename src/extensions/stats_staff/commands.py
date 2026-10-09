# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, final

import discord

from src.database.models import StaffStatsSettings

from .logic import EUROPE_PARIS, StatsPeriod
from .quotas import find_quota_role
from .render import render_stats
from .report import build_weekly_report_view
from .stats import PERIOD_CHOICES, get_or_create_settings
from .views import ConfigPanelView

if TYPE_CHECKING:
    from src import custom


async def _is_responsible_or_admin(ctx: custom.ApplicationContext) -> bool:
    assert isinstance(ctx.author, discord.Member)
    if ctx.author.guild_permissions.administrator:
        return True
    settings = await StaffStatsSettings.get_or_none(guild_id=ctx.author.guild.id)
    if settings is None or settings.responsible_role_id is None:
        return False
    return settings.responsible_role_id in (role.id for role in ctx.author.roles)


@final
class CommandsCog(discord.Cog):
    def __init__(self, bot: custom.Bot) -> None:
        self.bot: custom.Bot = bot

    stats_staff = discord.SlashCommandGroup("stats-staff", "Staff activity statistics")

    @stats_staff.command(name="me", description="View my own staff statistics")
    async def me(
        self,
        ctx: custom.ApplicationContext,
        periode: str = discord.Option(str, "Période", choices=PERIOD_CHOICES, default=StatsPeriod.WEEK.value),  # pyright: ignore[reportArgumentType, reportCallInDefaultInitializer]
    ) -> None:
        assert isinstance(ctx.author, discord.Member)
        if await find_quota_role(ctx.author) is None:
            await ctx.respond("Tu n'as pas de rôle avec un quota configuré.", ephemeral=True)
            return
        view = await render_stats(ctx.author, StatsPeriod(periode))
        await ctx.respond(view=view, ephemeral=True)

    @stats_staff.command(name="view", description="View a staff member's statistics")
    async def view(
        self,
        ctx: custom.ApplicationContext,
        membre: discord.Member,
        periode: str = discord.Option(str, "Période", choices=PERIOD_CHOICES, default=StatsPeriod.WEEK.value),  # pyright: ignore[reportArgumentType, reportCallInDefaultInitializer]
    ) -> None:
        if not await _is_responsible_or_admin(ctx):
            await ctx.respond("Tu n'as pas la permission de voir les statistiques d'un autre membre.", ephemeral=True)
            return
        view = await render_stats(membre, StatsPeriod(periode))
        await ctx.respond(view=view, ephemeral=True)

    stats_staff_admin = discord.SlashCommandGroup(
        "stats-staff-admin",
        "Staff statistics administration",
        default_member_permissions=discord.Permissions(administrator=True),
    )

    @stats_staff_admin.command(name="config", description="Configure quotas, tracked channels and stats reports")
    async def config(self, ctx: custom.ApplicationContext) -> None:
        assert ctx.guild is not None
        view = await ConfigPanelView.build(ctx.guild)
        await ctx.respond(view=view, ephemeral=True)

    @stats_staff_admin.command(
        name="preview-report",
        description="Preview what the weekly report would currently look like, without waiting for Sunday",
    )
    async def preview_report(self, ctx: custom.ApplicationContext) -> None:
        assert ctx.guild is not None
        settings = await get_or_create_settings(ctx.guild.id)
        now = datetime.now(tz=EUROPE_PARIS)
        view = await build_weekly_report_view(ctx.guild, settings, now)
        await ctx.respond(view=view, ephemeral=True)


__all__ = ("CommandsCog",)
