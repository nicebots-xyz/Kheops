# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from typing import TYPE_CHECKING, final

import discord

from src import i18n

from .logic import StatsPeriod
from .render import render_activity
from .stats import PERIOD_CHOICES
from .translations import ExtensionStrings
from .views import ConfigPanelView

if TYPE_CHECKING:
    from src import custom
    from src.i18n.classes import RawTranslation

    from .tracking import TrackingCog


@final
class CommandsCog(discord.Cog):
    def __init__(self, bot: custom.Bot, tracking: TrackingCog, strings: dict[str, RawTranslation]) -> None:
        self.bot: custom.Bot = bot
        self.tracking: TrackingCog = tracking
        self.strings: dict[str, RawTranslation] = strings

    def t(self, ctx: custom.ApplicationContext) -> ExtensionStrings:
        return i18n.typed(i18n.apply_locale(self.strings, ctx.locale), ExtensionStrings)

    member_activity = discord.SlashCommandGroup(
        "member-activity", "Member activity (messages, voice)", contexts={discord.InteractionContextType.guild}
    )

    @member_activity.command(name="me", description="View my own activity")
    async def me(
        self,
        ctx: custom.ApplicationContext,
        periode: str = discord.Option(str, "Période", choices=PERIOD_CHOICES, default=StatsPeriod.WEEK.value),  # pyright: ignore[reportArgumentType, reportCallInDefaultInitializer]
    ) -> None:
        assert isinstance(ctx.author, discord.Member)
        await self.show_activity(ctx, ctx.author, StatsPeriod(periode))

    @member_activity.command(name="view", description="View a member's activity")
    @discord.option("membre", discord.Member, description="Membre")  # pyright: ignore[reportUntypedFunctionDecorator]
    async def view(
        self,
        ctx: custom.ApplicationContext,
        membre: discord.Member,
        periode: str = discord.Option(str, "Période", choices=PERIOD_CHOICES, default=StatsPeriod.WEEK.value),  # pyright: ignore[reportArgumentType, reportCallInDefaultInitializer]
    ) -> None:
        await self.show_activity(ctx, membre, StatsPeriod(periode))

    async def show_activity(self, ctx: custom.ApplicationContext, member: discord.Member, period: StatsPeriod) -> None:
        await self.tracking.flush()
        await ctx.respond(embed=await render_activity(member, period, self.t(ctx)), ephemeral=True)

    member_activity_admin = discord.SlashCommandGroup(
        "member-activity-admin",
        "Member activity administration",
        default_member_permissions=discord.Permissions(administrator=True),
        contexts={discord.InteractionContextType.guild},
    )

    @member_activity_admin.command(name="config", description="Configure which channels are tracked")
    async def config(self, ctx: custom.ApplicationContext) -> None:
        assert ctx.guild is not None
        await ctx.respond(view=await ConfigPanelView.build(ctx.guild, self.tracking, self.t(ctx)), ephemeral=True)


__all__ = ("CommandsCog",)
