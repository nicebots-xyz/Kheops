# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from src import custom

from .main import StatsStaffCog

default = {"enabled": False}


def setup(bot: custom.Bot) -> None:
    bot.add_cog(StatsStaffCog(bot))
