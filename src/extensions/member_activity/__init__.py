# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from typing import Any

from src import custom

from .commands import CommandsCog
from .tracking import TrackingCog
from .webserver import setup_webserver

default = {"enabled": False}


def setup(bot: custom.Bot, config: dict[str, Any]) -> None:  # pyright: ignore[reportExplicitAny]
    tracking = TrackingCog(bot)
    strings = config.get("translations") or {}
    bot.add_cog(tracking)
    bot.add_cog(CommandsCog(bot, tracking, strings))


__all__ = ("default", "setup", "setup_webserver")
