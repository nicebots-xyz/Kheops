# Copyright Communauté Les Frères Poulain 2025, 2026
# SPDX-License-Identifier: MIT

from logging import getLogger
from typing import Any

from src import custom

from .config import AfkNotifConfig
from .main import AfkNotif

logger = getLogger("bot").getChild("afk_notification")

default = {
    "enabled": False,
}


def setup(bot: custom.Bot, config: dict[Any, Any]) -> None:
    bot.intents.members = True

    bot.add_cog(AfkNotif(bot, AfkNotifConfig.model_validate(config)))
    logger.info("Loaded afk_notification extension")
