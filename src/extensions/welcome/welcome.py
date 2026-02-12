# Copyright Communauté Les Frères Poulain 2025, 2026
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

from src.log import logger as base_logger

if TYPE_CHECKING:
    from src import custom

logger = base_logger.getChild("kheops.welcome")

default: dict[str, Any] = {
    "enabled": True,
    "channel_id": None,
    "message": "Bienvenue {mention} sur {server} !",
}


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

        channel = self.bot.get_partial_messageable(int(self.channel_id))

        content = render_template(self.message, member)
        allowed = discord.AllowedMentions(users=True, roles=False, everyone=False)

        try:
            await channel.send(content, allowed_mentions=allowed)
        except (discord.Forbidden, discord.HTTPException):
            logger.exception("Impossible d'envoyer un message dans le salon")


def setup(bot: custom.Bot, config: dict[str, Any]) -> None:
    bot.intents.members = True
    bot.add_cog(WelcomeCog(bot, config))
