# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from typing import TYPE_CHECKING, final

import discord

from .config import AnnounceConfig
from .logic import can_schedule
from .queries import get_or_create_settings
from .views import AnnounceBuilderView, AnnounceListView, ConfigPanelView

if TYPE_CHECKING:
    from src import custom


@final
class AnnounceCommandsCog(discord.Cog):
    def __init__(self, bot: "custom.Bot", config: AnnounceConfig) -> None:
        self.bot: custom.Bot = bot
        self.config: AnnounceConfig = config

    announce = discord.SlashCommandGroup(
        "announce", "Create and schedule announcements", contexts={discord.InteractionContextType.guild}
    )

    @announce.command(name="creer", description="Create or schedule an announcement")
    async def create(self, ctx: "custom.ApplicationContext") -> None:
        assert isinstance(ctx.author, discord.Member)
        assert ctx.guild is not None
        is_admin = ctx.author.guild_permissions.administrator
        settings = await get_or_create_settings(ctx.guild.id)
        if not can_schedule((r.id for r in ctx.author.roles), is_admin=is_admin, settings=settings):
            await ctx.respond(ctx.translations.no_permission, ephemeral=True)
            return

        panel = AnnounceBuilderView(
            bot=self.bot,
            guild_id=ctx.guild.id,
            created_by_id=ctx.author.id,
            t=ctx.translations,
            tz=self.config.tz,
            is_admin=is_admin,
            must_schedule=not is_admin,
        )
        await ctx.respond(view=panel, ephemeral=True)

    @announce.command(name="historique", description="View, cancel or duplicate recent announcements")
    async def history(self, ctx: "custom.ApplicationContext") -> None:
        assert isinstance(ctx.author, discord.Member)
        assert ctx.guild is not None
        is_admin = ctx.author.guild_permissions.administrator
        settings = await get_or_create_settings(ctx.guild.id)
        if not can_schedule((r.id for r in ctx.author.roles), is_admin=is_admin, settings=settings):
            await ctx.respond(ctx.translations.no_permission, ephemeral=True)
            return

        view = await AnnounceListView.build(
            bot=self.bot,
            guild_id=ctx.guild.id,
            created_by_id=ctx.author.id,
            t=ctx.translations,
            tz=self.config.tz,
            is_admin=is_admin,
            must_schedule=not is_admin,
        )
        await ctx.respond(view=view, ephemeral=True)

    announce_admin = discord.SlashCommandGroup(
        "announce-admin",
        "Announce module administration",
        default_member_permissions=discord.Permissions(administrator=True),
        contexts={discord.InteractionContextType.guild},
    )

    @announce_admin.command(name="config", description="Configure who can schedule announcements besides admins")
    async def config_command(self, ctx: "custom.ApplicationContext") -> None:
        assert ctx.guild is not None
        await ctx.respond(view=await ConfigPanelView.build(ctx.guild.id, ctx.translations), ephemeral=True)


__all__ = ("AnnounceCommandsCog",)
