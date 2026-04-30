# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from pydantic import BaseModel


class ChannelNoteConfig(BaseModel):
    enabled: bool = True
    send_on_start: bool = True
