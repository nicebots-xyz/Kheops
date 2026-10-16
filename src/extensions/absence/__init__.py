# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from src import custom

from .commands import AbsenceCommandsCog
from .webserver import setup_webserver

default = {"enabled": False}


def setup(bot: custom.Bot) -> None:
    bot.add_cog(AbsenceCommandsCog(bot))


__all__ = ("default", "setup", "setup_webserver")
