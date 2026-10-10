# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from typing import Any

from src import custom

from .commands import CommandsCog
from .report import ReportCog
from .tracking import TrackingCog
from .webserver import setup_webserver

default = {"enabled": False}


def setup(bot: custom.Bot, config: dict[str, Any]) -> None:  # pyright: ignore[reportExplicitAny]
    # Reports and the assignment screen list role members, and voice tracking reads members already
    # in voice at startup: both need the member cache.
    bot.intents.members = True
    tracking = TrackingCog(bot)
    strings = config.get("translations") or {}
    bot.add_cog(tracking)
    bot.add_cog(ReportCog(bot, tracking, strings))
    bot.add_cog(CommandsCog(bot, tracking, strings))


__all__ = ("default", "setup", "setup_webserver")
