# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from typing import Any

from src import custom

from .commands import AbsenceCommandsCog
from .webserver import setup_webserver

default = {"enabled": False}


def setup(bot: custom.Bot, config: dict[str, Any]) -> None:  # pyright: ignore[reportExplicitAny]
    strings = config.get("translations") or {}
    bot.add_cog(AbsenceCommandsCog(bot, strings))


__all__ = ("default", "setup", "setup_webserver")
