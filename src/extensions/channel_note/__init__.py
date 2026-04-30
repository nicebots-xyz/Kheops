from typing import Any

from src import custom

from .channel_note import ChannelNoteCog
from .config import ChannelNoteConfig

default = {"enabled": False}


def setup(bot: custom.Bot, config: dict[str, Any]) -> None:
    _config = ChannelNoteConfig.model_validate(config)

    bot.add_cog(ChannelNoteCog(bot, _config))
