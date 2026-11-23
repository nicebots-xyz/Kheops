# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from src import custom

from .commands import AnnounceCommandsCog
from .config import AnnounceConfig
from .scheduler import AnnounceSchedulerCog
from .webserver import setup_webserver

default: dict[str, str | bool] = {"enabled": True, "timezone": "Europe/Paris"}


def setup(bot: custom.Bot, config: dict[str, object]) -> None:
    announce_config = AnnounceConfig.model_validate(config)
    bot.add_cog(AnnounceCommandsCog(bot, announce_config))
    bot.add_cog(AnnounceSchedulerCog(bot))


__all__ = ("default", "setup", "setup_webserver")
