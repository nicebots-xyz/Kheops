# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from .channel_note import (
    CONTENT_MAX_LENGTH as CONTENT_MAX_LENGTH_CHANNEL_NOTE,
)
from .channel_note import (
    FOOTER_MAX_LENGTH as FOOTER_MAX_LENGTH_CHANNEL_NOTE,
)
from .channel_note import (
    HEADER_MAX_LENGTH as HEADER_MAX_LENGTH_CHANNEL_NOTE,
)
from .channel_note import (
    SLOTS_PER_DAY as SLOTS_PER_DAY_CHANNEL_NOTE,
)
from .channel_note import (
    SLOTS_PER_WEEK as SLOTS_PER_WEEK_CHANNEL_NOTE,
)
from .channel_note import (
    ChannelNote,
    ChannelNoteEvery,
)
from .dormeur import Dormeur
from .guild import Guild
from .user import User

__all__ = [
    "CONTENT_MAX_LENGTH_CHANNEL_NOTE",
    "FOOTER_MAX_LENGTH_CHANNEL_NOTE",
    "HEADER_MAX_LENGTH_CHANNEL_NOTE",
    "SLOTS_PER_DAY_CHANNEL_NOTE",
    "SLOTS_PER_WEEK_CHANNEL_NOTE",
    "ChannelNote",
    "ChannelNoteEvery",
    "Dormeur",
    "Guild",
    "User",
]
