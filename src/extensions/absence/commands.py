# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from typing import TYPE_CHECKING, final

import discord

from src.database.models import AbsenceSettings
from src.i18n.classes import apply_locale

from .logic import can_self_declare, is_responsible
from .views import AbsenceListView, AbsenceModal, ConfigPanelView

if TYPE_CHECKING:
    from src import custom
    from src.i18n.classes import RawTranslation

    from .views import Strings


@final
class AbsenceCommandsCog(discord.Cog):
    def __init__(self, bot: custom.Bot, strings: dict[str, RawTranslation]) -> None:
        self.bot: custom.Bot = bot
        self.strings: dict[str, RawTranslation] = strings

    def t(self, ctx: custom.ApplicationContext) -> Strings:
        return apply_locale(self.strings, ctx.locale)

    absence = discord.SlashCommandGroup(
        "absence", "Declare and manage staff absences", contexts={discord.InteractionContextType.guild}
    )

    @absence.command(name="declare", description="Declare an absence")
    @discord.option(
        "membre",
        discord.Member,
        description="Declare for this member instead of yourself (admins only)",
        required=False,
    )
    async def declare(self, ctx: custom.ApplicationContext, membre: discord.Member | None = None) -> None:
        assert isinstance(ctx.author, discord.Member)
        t = self.t(ctx)
        is_admin = ctx.author.guild_permissions.administrator

        if membre is not None:
            if not is_admin:
                await ctx.respond(t.no_permission_declare_other, ephemeral=True)
                return
            target = membre
        else:
            settings, _ = await AbsenceSettings.get_or_create(guild_id=ctx.author.guild.id)
            if not can_self_declare((r.id for r in ctx.author.roles), is_admin=is_admin, settings=settings):
                await ctx.respond(t.no_permission_declare_self, ephemeral=True)
                return
            target = ctx.author

        await ctx.send_modal(
            AbsenceModal(
                bot=self.bot,
                guild_id=ctx.author.guild.id,
                member_id=target.id,
                created_by_id=ctx.author.id,
                t=t,
            )
        )

    @absence.command(name="mine", description="View and manage my own absences")
    async def mine(self, ctx: custom.ApplicationContext) -> None:
        assert isinstance(ctx.author, discord.Member)
        t = self.t(ctx)
        is_admin = ctx.author.guild_permissions.administrator
        settings, _ = await AbsenceSettings.get_or_create(guild_id=ctx.author.guild.id)
        if not can_self_declare((r.id for r in ctx.author.roles), is_admin=is_admin, settings=settings):
            await ctx.respond(t.no_permission_declare_self, ephemeral=True)
            return
        can_delete = is_responsible((r.id for r in ctx.author.roles), is_admin=is_admin, settings=settings)
        view = await AbsenceListView.build(
            bot=self.bot,
            guild_id=ctx.author.guild.id,
            member_id=ctx.author.id,
            t=t,
            can_manage=True,
            can_delete=can_delete,
        )
        await ctx.respond(view=view, ephemeral=True)

    absence_admin = discord.SlashCommandGroup(
        "absence-admin",
        "Absence module administration",
        default_member_permissions=discord.Permissions(administrator=True),
        contexts={discord.InteractionContextType.guild},
    )

    @absence_admin.command(name="list", description="View and manage a member's absences")
    @discord.option("membre", discord.Member, description="Member to look up")
    async def admin_list(self, ctx: custom.ApplicationContext, membre: discord.Member) -> None:
        assert isinstance(ctx.author, discord.Member)
        assert ctx.guild is not None
        t = self.t(ctx)
        is_admin = ctx.author.guild_permissions.administrator
        settings, _ = await AbsenceSettings.get_or_create(guild_id=ctx.guild.id)
        can_delete = is_responsible((r.id for r in ctx.author.roles), is_admin=is_admin, settings=settings)
        view = await AbsenceListView.build(
            bot=self.bot, guild_id=ctx.guild.id, member_id=membre.id, t=t, can_manage=True, can_delete=can_delete
        )
        await ctx.respond(view=view, ephemeral=True)

    @absence_admin.command(
        name="config",
        description="Configure who can self-declare, the announcement channel, and the staff responsible role",
    )
    async def config(self, ctx: custom.ApplicationContext) -> None:
        assert ctx.guild is not None
        await ctx.respond(view=await ConfigPanelView.build(ctx.guild.id, self.t(ctx)), ephemeral=True)


__all__ = ("AbsenceCommandsCog",)
