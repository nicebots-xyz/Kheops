# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, final

import discord

from src.database.models import StaffRoleQuota, StaffStatsSettings
from src.i18n.classes import apply_locale

from .logic import EUROPE_PARIS, StatsPeriod, last_completed_week_bounds, previous_week_bounds, week_start
from .quotas import find_quota
from .render import render_stats
from .report import ReportCog, build_report
from .stats import PERIOD_CHOICES, get_or_create_settings
from .views import ConfigPanelView

if TYPE_CHECKING:
    from src import custom
    from src.i18n.classes import RawTranslation

    from .stats import Strings
    from .tracking import TrackingCog


@final
class CommandsCog(discord.Cog):
    def __init__(
        self, bot: custom.Bot, tracking: TrackingCog, report: ReportCog, strings: dict[str, RawTranslation]
    ) -> None:
        self.bot: custom.Bot = bot
        self.tracking: TrackingCog = tracking
        self.report: ReportCog = report
        self.strings: dict[str, RawTranslation] = strings

    def t(self, ctx: custom.ApplicationContext) -> Strings:
        return apply_locale(self.strings, ctx.locale)

    stats_staff = discord.SlashCommandGroup(
        "stats-staff", "Staff activity statistics", contexts={discord.InteractionContextType.guild}
    )

    @stats_staff.command(name="me", description="View my own staff statistics")
    async def me(
        self,
        ctx: custom.ApplicationContext,
        periode: str = discord.Option(str, "Période", choices=PERIOD_CHOICES, default=StatsPeriod.WEEK.value),  # pyright: ignore[reportArgumentType, reportCallInDefaultInitializer]
    ) -> None:
        assert isinstance(ctx.author, discord.Member)
        quota = await find_quota(ctx.author)
        if quota is None:
            await ctx.respond(self.t(ctx).no_quota_self, ephemeral=True)
            return
        await self.show_stats(ctx, ctx.author, quota, StatsPeriod(periode))

    @stats_staff.command(name="view", description="View a staff member's statistics")
    @discord.option("membre", discord.Member, description="Membre")  # pyright: ignore[reportUntypedFunctionDecorator]
    async def view(
        self,
        ctx: custom.ApplicationContext,
        membre: discord.Member,
        periode: str = discord.Option(str, "Période", choices=PERIOD_CHOICES, default=StatsPeriod.WEEK.value),  # pyright: ignore[reportArgumentType, reportCallInDefaultInitializer]
    ) -> None:
        assert isinstance(ctx.author, discord.Member)
        settings = await StaffStatsSettings.get_or_none(guild_id=ctx.author.guild.id)
        responsible = settings is not None and settings.responsible_role_id in {role.id for role in ctx.author.roles}
        if not (ctx.author.guild_permissions.administrator or responsible):
            await ctx.respond(self.t(ctx).no_permission_view, ephemeral=True)
            return
        await self.show_stats(ctx, membre, await find_quota(membre), StatsPeriod(periode))

    async def show_stats(
        self, ctx: custom.ApplicationContext, member: discord.Member, quota: StaffRoleQuota | None, period: StatsPeriod
    ) -> None:
        await self.tracking.flush()
        await ctx.respond(embed=await render_stats(member, quota, period, self.t(ctx)), ephemeral=True)

    stats_staff_admin = discord.SlashCommandGroup(
        "stats-staff-admin",
        "Staff statistics administration",
        default_member_permissions=discord.Permissions(administrator=True),
        contexts={discord.InteractionContextType.guild},
    )

    @stats_staff_admin.command(name="config", description="Configure quotas, tracked channels and stats reports")
    async def config(self, ctx: custom.ApplicationContext) -> None:
        assert ctx.guild is not None
        await ctx.respond(view=await ConfigPanelView.build(ctx.guild, self.tracking, self.t(ctx)), ephemeral=True)

    @stats_staff_admin.command(
        name="preview-report",
        description="Preview what the weekly report would currently look like, without waiting for Monday",
    )
    async def preview_report(self, ctx: custom.ApplicationContext) -> None:
        assert ctx.guild is not None
        await ctx.defer(ephemeral=True)
        await self.tracking.flush()
        now = datetime.now(tz=EUROPE_PARIS)
        settings = await get_or_create_settings(ctx.guild.id)
        views = await build_report(ctx.guild, settings, self.t(ctx), (week_start(now), now), previous_week_bounds(now))
        for view in views:
            await ctx.respond(view=view, ephemeral=True)

    @stats_staff_admin.command(
        name="resend-last-week", description="Send last week's report again to the configured channel"
    )
    async def resend_last_week(self, ctx: custom.ApplicationContext) -> None:
        assert ctx.guild is not None
        await ctx.defer(ephemeral=True)
        settings = await StaffStatsSettings.get_or_none(guild_id=ctx.guild.id)
        if settings is None or settings.report_channel_id is None:
            await ctx.respond(self.t(ctx).report_channel_not_set, ephemeral=True)
            return
        await self.tracking.flush()
        period, comparison = last_completed_week_bounds(datetime.now(tz=EUROPE_PARIS))
        await self.report.send_report(settings, period, comparison)
        await ctx.respond(self.t(ctx).report_resent.format(channel=f"<#{settings.report_channel_id}>"), ephemeral=True)


__all__ = ("CommandsCog",)
