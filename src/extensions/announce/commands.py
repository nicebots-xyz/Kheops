# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from typing import TYPE_CHECKING, final

import discord

from .logic import can_schedule
from .queries import get_or_create_settings
from .send import localize
from .views import AnnounceBuilderView, AnnounceListView, ConfigPanelView, PanelContext

if TYPE_CHECKING:
    from src import custom
    from src.i18n.classes import RawTranslation

    from .config import AnnounceConfig


@final
class AnnounceCommandsCog(discord.Cog):
    def __init__(self, bot: custom.Bot, config: AnnounceConfig, strings: dict[str, RawTranslation]) -> None:
        self.bot: custom.Bot = bot
        self.announce_config: AnnounceConfig = config
        self.strings: dict[str, RawTranslation] = strings

    async def _panel_context(self, ctx: custom.ApplicationContext) -> PanelContext | None:
        """Build the context of a panel opened by `ctx`'s author, if they can schedule announcements.

        Args:
            ctx: The invoking command's context.

        Returns:
            The panel's context, or `None` once the author was told they cannot schedule.

        """
        assert isinstance(ctx.author, discord.Member)
        assert ctx.guild is not None
        t = localize(self.strings, ctx.locale)
        is_admin = ctx.author.guild_permissions.administrator
        settings = await get_or_create_settings(ctx.guild.id)
        if not can_schedule((r.id for r in ctx.author.roles), is_admin=is_admin, settings=settings):
            await ctx.respond(t.no_permission, ephemeral=True)
            return None
        return PanelContext(
            bot=self.bot,
            guild_id=ctx.guild.id,
            member_id=ctx.author.id,
            is_admin=is_admin,
            tz=self.announce_config.tz,
            strings=self.strings,
            t=t,
            message_t=localize(self.strings, ctx.guild.preferred_locale),
        )

    announce = discord.SlashCommandGroup("announce", contexts={discord.InteractionContextType.guild})

    @announce.command()
    async def creer(self, ctx: custom.ApplicationContext) -> None:
        panel_ctx = await self._panel_context(ctx)
        if panel_ctx is None:
            return
        await ctx.respond(view=AnnounceBuilderView(panel_ctx, must_schedule=not panel_ctx.is_admin), ephemeral=True)

    @announce.command()
    async def historique(self, ctx: custom.ApplicationContext) -> None:
        panel_ctx = await self._panel_context(ctx)
        if panel_ctx is None:
            return
        view = await AnnounceListView.build(panel_ctx, must_schedule=not panel_ctx.is_admin)
        await ctx.respond(view=view, ephemeral=True)

    announce_admin = discord.SlashCommandGroup(
        "announce-admin",
        default_member_permissions=discord.Permissions(administrator=True),
        contexts={discord.InteractionContextType.guild},
    )

    @announce_admin.command()
    async def config(self, ctx: custom.ApplicationContext) -> None:
        assert ctx.guild is not None
        view = await ConfigPanelView.build(ctx.guild.id, localize(self.strings, ctx.locale))
        await ctx.respond(view=view, ephemeral=True)


__all__ = ("AnnounceCommandsCog",)
