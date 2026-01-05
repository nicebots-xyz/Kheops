# Copyright (c) Communauté Les Frères Poulain
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any

import discord
from discord.ext import commands

default: dict[str, Any] = {
    "enabled": True,
    "channel_id": None,
    "message": "Bienvenue {mention} sur {server} !",
}


def tr(
    translations: dict[str, dict[str, str]],
    key: str,
    locale: str | None,
    **fmt: Any,
) -> str:
    entry = translations.get(key, {})
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
        }
    )
    return str(template).format_map(vars_)


class WelcomeCog(commands.Cog):
    def __init__(self, bot: discord.Bot, config: dict[str, Any]) -> None:
        self.bot = bot

        self.enabled: bool = bool(config.get("enabled", default["enabled"]))
        self.channel_id: int | None = config.get("channel_id", default["channel_id"])
        self.message: str = str(config.get("message") or default["message"])

        self.translations: dict[str, dict[str, str]] = config.get("translations") or {}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if not self.enabled or not self.channel_id or not self.message:
            return

        channel = member.guild.get_channel(int(self.channel_id))
        if channel is None:
            return

        content = render_template(self.message, member)
        allowed = discord.AllowedMentions(users=True, roles=False, everyone=False)

        try:
            await channel.send(content, allowed_mentions=allowed)
        except (discord.Forbidden, discord.HTTPException):
            return

    @discord.slash_command(name="bienvenue", description="Afficher la configuration du welcome.")
    @discord.default_permissions(manage_guild=True)
    async def bienvenue(self, ctx: discord.ApplicationContext) -> None:
        locale = getattr(ctx, "locale", None)

        if not ctx.guild:
            await ctx.respond(tr(self.translations, "only_guild", locale), ephemeral=True)
            return

        if not self.channel_id:
            await ctx.respond(tr(self.translations, "not_configured", locale), ephemeral=True)
            return

        preview = self.message
        if isinstance(ctx.user, discord.Member):
            preview = render_template(self.message, ctx.user)

        await ctx.respond(
            tr(
                self.translations,
                "status",
                locale,
                enabled=self.enabled,
                channel_id=int(self.channel_id),
                message=self.message,
                preview=preview,
            ),
            ephemeral=True,
        )

    @discord.slash_command(
        name="bienvenue_vars",
        description="Variables utilisables dans le message de bienvenue.",
    )
    async def bienvenue_vars(self, ctx: discord.ApplicationContext) -> None:
        locale = getattr(ctx, "locale", None)
        await ctx.respond(tr(self.translations, "vars", locale), ephemeral=True)


def setup(bot: discord.Bot, config: dict[str, Any]) -> None:
    bot.add_cog(WelcomeCog(bot, config))
