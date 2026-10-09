# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from src import custom

from .commands import CommandsCog
from .report import ReportCog
from .tracking import TrackingCog

default = {"enabled": False}


def setup(bot: custom.Bot) -> None:
    bot.add_cog(TrackingCog(bot))
    bot.add_cog(ReportCog(bot))
    bot.add_cog(CommandsCog(bot))
