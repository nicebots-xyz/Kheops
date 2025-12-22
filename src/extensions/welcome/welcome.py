# Copyright (c) 2025 Bryan Thoury
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

from src import custom

from .storage import WelcomeStorage

if TYPE_CHECKING:
    from src import custom


default: dict[str, Any] = {
    "enabled": True,
    "channel_id": None,
    "message": "Bienvenue {mention} sur {server} !",
}


def tr(
    translations: dict[str, dict[str, str]] | None,
    key: str,
    locale: str | None,
    **fmt: Any,
) -> str:
    entry = (translations or {}).get(key, {})
    loc = locale or "fr"
    base = loc.split("-", 1)[0]

    text = entry.get(loc) or entry.get(base) or entry.get("en-US") or entry.get("fr") or ""
    if fmt:
        try:
            return text.format(**fmt)
        except (KeyError, ValueError):
            return text
    return text


def render_template(template: str, member: discord.Member) -> str:
    guild = member.guild

    class SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    vars_ = SafeDict(
        {
            "user": member.display_name,
            "mention": member.mention,
            "username": member.name,
            "server": guild.name,
            "member_count": guild.member_count or 0,
            "created_at": member.created_at.strftime("%Y-%m-%d"),
            "joined_at": member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "now",
        },
    )
    return str(template).format_map(vars_)


class WelcomeMessageModal(discord.ui.Modal):
    def __init__(
        self,
        storage: WelcomeStorage,
        channel_id: int,
        locale: str | None,
        translations: dict[str, dict[str, str]],
    ) -> None:
        super().__init__(title=tr(translations, "modal_title", locale))
        self.storage = storage
        self.channel_id = int(channel_id)
        self.locale = locale
        self.translations = translations

        self.message_input = discord.ui.InputText(
            label=tr(translations, "modal_label", locale),
            style=discord.InputTextStyle.long,
            placeholder=tr(translations, "modal_placeholder", locale),
            max_length=1800,
            required=True,
        )
        self.add_item(self.message_input)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                tr(self.translations, "only_guild", self.locale),
                ephemeral=True,
            )
            return

        msg = self.message_input.value.strip()
        await self.storage.set(
            interaction.guild.id,
            channel_id=self.channel_id,
            message=msg,
            enabled=True,
        )

        preview = msg
        if isinstance(interaction.user, discord.Member):
            preview = render_template(msg, interaction.user)

        await interaction.response.send_message(
            f"{tr(self.translations, 'configured', self.locale)}\n"
            f"{tr(self.translations, 'channel_line', self.locale, channel_id=self.channel_id)}\n\n"
            f"{tr(self.translations, 'preview_title', self.locale)}\n{preview}",
            ephemeral=True,
        )
        return


class WelcomeCog(commands.Cog):
    def __init__(self, bot: custom.Bot, translations: dict[str, dict[str, str]]) -> None:
        self.bot = bot
        self.translations = translations
        self.storage = WelcomeStorage("data/welcome.json")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        cfg = await self.storage.get(member.guild.id)
        if not cfg.get("enabled"):
            return

        channel_id = cfg.get("channel_id")
        template = cfg.get("message")
        if not channel_id or not template:
            return

        channel = member.guild.get_channel(int(channel_id))
        if channel is None:
            return

        content = render_template(str(template), member)

        allowed = discord.AllowedMentions(users=True, roles=False, everyone=False)
        try:
            await channel.send(content, allowed_mentions=allowed)
        except (discord.Forbidden, discord.HTTPException):
            return

    @discord.slash_command(name="bienvenue", description="Configurer le message de bienvenue.")
    @discord.default_permissions(manage_guild=True)
    async def bienvenue(self, ctx: discord.ApplicationContext, salon: discord.TextChannel) -> None:
        locale = getattr(ctx, "locale", None)
        modal = WelcomeMessageModal(self.storage, salon.id, locale, self.translations)
        await ctx.send_modal(modal)

    @discord.slash_command(name="bienvenue_off", description="Désactiver le message de bienvenue.")
    @discord.default_permissions(manage_guild=True)
    async def bienvenue_off(self, ctx: discord.ApplicationContext) -> None:
        if not ctx.guild:
            await ctx.respond(tr(self.translations, "only_guild", getattr(ctx, "locale", None)), ephemeral=True)
            return

        await self.storage.disable(ctx.guild.id)
        await ctx.respond(tr(self.translations, "disabled", getattr(ctx, "locale", None)), ephemeral=True)
        return

    @discord.slash_command(name="bienvenue_vars", description="Voir les variables disponibles.")
    async def bienvenue_vars(self, ctx: discord.ApplicationContext) -> None:
        locale = getattr(ctx, "locale", None)
        text = (
            f"{tr(self.translations, 'vars_title', locale)}\n\n"
            f"{tr(self.translations, 'vars_user', locale)}\n"
            f"{tr(self.translations, 'vars_mention', locale)}\n"
            f"{tr(self.translations, 'vars_username', locale)}\n"
            f"{tr(self.translations, 'vars_server', locale)}\n"
            f"{tr(self.translations, 'vars_member_count', locale)}\n"
            f"{tr(self.translations, 'vars_created_at', locale)}\n"
            f"{tr(self.translations, 'vars_joined_at', locale)}\n\n"
            f"{tr(self.translations, 'vars_example_title', locale)}\n"
            f"{tr(self.translations, 'vars_example', locale)}"
        )
        await ctx.respond(text, ephemeral=True)


def setup(bot: custom.Bot, config: dict[str, Any]) -> None:
    translations = config.get("translations") or {}
    bot.add_cog(WelcomeCog(bot, translations))
