# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from typing import TYPE_CHECKING, cast

from src import custom

from .commands import AnnounceCommandsCog
from .config import AnnounceConfig
from .scheduler import AnnounceSchedulerCog
from .webserver import setup_webserver

if TYPE_CHECKING:
    from src.i18n.classes import RawTranslation
    from src.startup.types import ExtensionConfig

default: dict[str, str | bool] = {"enabled": True, "timezone": "Europe/Paris"}


def setup(bot: custom.Bot, config: "ExtensionConfig") -> None:
    announce_config = AnnounceConfig.model_validate(config)
    strings = cast("dict[str, RawTranslation]", config.get("translations") or {})
    bot.add_cog(AnnounceCommandsCog(bot, announce_config, strings))
    bot.add_cog(AnnounceSchedulerCog(bot, strings))


__all__ = ("default", "setup", "setup_webserver")
