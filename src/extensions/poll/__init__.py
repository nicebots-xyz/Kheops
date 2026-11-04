# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from typing import final

import discord

from src import custom

from .config import PollConfig
from .views import PollBuilderView

default: dict[str, str | bool] = {"enabled": False, "timezone": "Europe/Paris"}


@final
class PollCog(discord.Cog):
    def __init__(self, bot: custom.Bot, config: PollConfig) -> None:
        self.bot: custom.Bot = bot
        self.config: PollConfig = config
        super().__init__()

    @discord.slash_command(
        name="poll",
        default_member_permissions=discord.Permissions(administrator=True),
        contexts={discord.InteractionContextType.guild},
    )
    async def poll(self, ctx: custom.ApplicationContext) -> None:
        await ctx.respond(view=PollBuilderView(self.bot, ctx.translations, self.config.tz), ephemeral=True)


def setup(bot: custom.Bot, config: dict[str, object]) -> None:
    bot.add_cog(PollCog(bot, PollConfig.model_validate(config)))
