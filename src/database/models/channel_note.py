# Copyright Communauté Les Frères Poulain 2025, 2026
# SPDX-License-Identifier: MIT

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from tortoise import fields
from tortoise.models import Model

CONTENT_MAX_LENGTH = 1024
HEADER_MAX_LENGTH = 128
FOOTER_MAX_LENGTH = 128

SLOTS_PER_DAY = 24
SLOTS_PER_WEEK = 7 * SLOTS_PER_DAY


class ChannelNoteEvery(StrEnum):
    H_1 = "h_1"
    H_6 = "h_6"
    H_12 = "h_12"
    D_1 = "d_1"
    D_7 = "d_7"


class ChannelNote(Model):
    id: fields.Field[UUID] = fields.UUIDField(pk=True)

    discord_id: fields.Field[int] = fields.BigIntField(unique=True)
    enabled: fields.Field[bool] = fields.BooleanField(default=True)
    content: fields.Field[str] = fields.CharField(max_length=CONTENT_MAX_LENGTH)
    header: fields.Field[str] = fields.CharField(max_length=HEADER_MAX_LENGTH)
    footer: fields.Field[str] = fields.CharField(max_length=FOOTER_MAX_LENGTH)
    every: ChannelNoteEvery = fields.CharEnumField(enum_type=ChannelNoteEvery)

    created_at: fields.Field[datetime] = fields.DatetimeField(auto_now_add=True)
    updated_at: fields.Field[datetime] = fields.DatetimeField(auto_now=True)

    @property
    def slots(self) -> set[int]:
        """Get the slots for the channel note.

        This divides a week into slots of the given every hour, and returns the slots
        for which this channel note should be sent.

        The slots are 0-indexed. The first slot is representative of 00:00 on monday,
        and the last slot is representative of 23:00 on sunday.

        Returns:
            set[int]: The slots for which this channel note should be sent.

        """
        match self.every:
            case ChannelNoteEvery.H_1:
                return set(range(SLOTS_PER_WEEK))
            case ChannelNoteEvery.H_6:
                return set(range(0, SLOTS_PER_WEEK, 6))
            case ChannelNoteEvery.H_12:
                return set(range(0, SLOTS_PER_WEEK, 12))
            case ChannelNoteEvery.D_1:
                return set(range(0, SLOTS_PER_WEEK, 24))
            case ChannelNoteEvery.D_7:
                return {0}


__all__ = ("CONTENT_MAX_LENGTH", "FOOTER_MAX_LENGTH", "HEADER_MAX_LENGTH", "ChannelNote", "ChannelNoteEvery")
