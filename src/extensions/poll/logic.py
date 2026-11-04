# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
"""Pure helpers for the poll builder: no Discord I/O, so they can be unit tested."""

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo

import discord

# Limits enforced by the Discord API for native polls.
MAX_DURATION_HOURS = 768  # 32 days
MIN_DURATION_HOURS = 1
MAX_ANSWERS = 10
QUESTION_MAX_LENGTH = 300
ANSWER_MAX_LENGTH = 55

_DATE_RE = re.compile(r"^\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\s*$")
_TIME_RE = re.compile(r"^\s*(\d{1,2})\s*[:hH]\s*(\d{2})\s*$")
_CUSTOM_EMOJI_RE = re.compile(r"^<?(?P<animated>a)?:(?P<name>\w+):(?P<id>\d{15,25})>?$")
_EMOJI_ID_RE = re.compile(r"^\d{15,25}$")


class InvalidEmojiError(ValueError):
    """The emoji field contains something that can't be an emoji."""


class PollEndError(ValueError):
    """Base class for an end date that can't be turned into a poll duration."""


class InvalidEndFormatError(PollEndError):
    """The date or the time doesn't follow the expected format, or doesn't exist."""


class EndInPastError(PollEndError):
    """The end date is not in the future."""


class EndTooFarError(PollEndError):
    """The end date would need a duration longer than Discord allows."""


@dataclass(slots=True)
class DraftAnswer:
    """A poll answer being built, before it is sent to Discord.

    Attributes:
        text: The answer's label.
        emoji: The answer's emoji, if any.

    """

    text: str
    emoji: discord.PartialEmoji | None = None


def parse_end(date_raw: str, time_raw: str, tz: tzinfo) -> datetime:
    """Parse a `JJ/MM/AAAA` date and a `HH:MM` time into an aware datetime.

    Args:
        date_raw: The date, as `JJ/MM/AAAA` (`/`, `.` or `-` as separators).
        time_raw: The time, as `HH:MM` or `HHhMM`.
        tz: The timezone the date and time are expressed in.

    Returns:
        The aware datetime the user meant.

    Raises:
        InvalidEndFormatError: If either value is malformed or isn't a real date/time.

    """
    date_match = _DATE_RE.match(date_raw)
    time_match = _TIME_RE.match(time_raw)
    if date_match is None or time_match is None:
        raise InvalidEndFormatError("Expected JJ/MM/AAAA and HH:MM")
    day, month, year = (int(g) for g in date_match.groups())
    hour, minute = (int(g) for g in time_match.groups())
    try:
        return datetime(year, month, day, hour, minute, tzinfo=tz)
    except ValueError as e:
        raise InvalidEndFormatError(str(e)) from e


def duration_hours(end: datetime, now: datetime) -> int:
    """Compute the smallest whole number of hours that reaches or passes `end`.

    Discord polls only take a duration in hours, so the poll ends at the first hour mark
    that overshoots the requested date, never before it.

    Args:
        end: The requested end of the poll (aware).
        now: The current time (aware).

    Returns:
        The poll duration in hours.

    Raises:
        EndInPastError: If `end` isn't after `now`.
        EndTooFarError: If the duration would exceed `MAX_DURATION_HOURS`.

    """
    seconds = (end - now).total_seconds()
    if seconds <= 0:
        raise EndInPastError("The end date must be in the future")
    hours = max(MIN_DURATION_HOURS, math.ceil(seconds / 3600))
    if hours > MAX_DURATION_HOURS:
        raise EndTooFarError(f"A poll can't last more than {MAX_DURATION_HOURS} hours")
    return hours


def effective_end(now: datetime, hours: int) -> datetime:
    """Get when a poll created at `now` with a duration of `hours` actually closes.

    Args:
        now: When the poll is created.
        hours: The poll duration in hours.

    Returns:
        The real closing time of the poll.

    """
    return now + timedelta(hours=hours)


def parse_emoji(raw: str | None) -> discord.PartialEmoji | None:
    """Parse what a user typed in the emoji field.

    Accepts a bare custom emoji ID, a custom emoji mention (`<:name:id>`, `<a:name:id>`, `name:id`),
    a unicode emoji, or a `:alias:` known to py-cord.

    Args:
        raw: The raw user input.

    Returns:
        The parsed emoji, or `None` if the field was left empty.

    Raises:
        InvalidEmojiError: If the input is plain text rather than an emoji.

    """
    value = (raw or "").strip()
    if not value:
        return None
    if _EMOJI_ID_RE.match(value):
        return discord.PartialEmoji(name=None, id=int(value))
    if match := _CUSTOM_EMOJI_RE.match(value):
        return discord.PartialEmoji(name=match["name"], id=int(match["id"]), animated=match["animated"] is not None)
    emoji = discord.PartialEmoji.from_str(value)
    # Unicode emojis always contain non-ASCII code points (even keycaps like 1️⃣), plain words don't.
    if emoji.name is None or emoji.name.isascii():
        raise InvalidEmojiError(f"{value!r} is not an emoji")
    return emoji


def format_emoji(emoji: discord.PartialEmoji | None) -> str:
    """Render an emoji for the builder preview.

    Args:
        emoji: The emoji to render.

    Returns:
        A string that Discord renders as the emoji, or an empty string.

    """
    return "" if emoji is None else str(emoji)


def emoji_input_value(emoji: discord.PartialEmoji | None) -> str:
    """Turn an emoji back into what the user would type, to prefill the modal.

    Args:
        emoji: The emoji to convert.

    Returns:
        The custom emoji ID, the unicode emoji, or an empty string.

    """
    if emoji is None:
        return ""
    if emoji.id is not None:
        return str(emoji.id)
    return emoji.name or ""


__all__ = (
    "ANSWER_MAX_LENGTH",
    "MAX_ANSWERS",
    "MAX_DURATION_HOURS",
    "QUESTION_MAX_LENGTH",
    "DraftAnswer",
    "EndInPastError",
    "EndTooFarError",
    "InvalidEmojiError",
    "InvalidEndFormatError",
    "PollEndError",
    "duration_hours",
    "effective_end",
    "emoji_input_value",
    "format_emoji",
    "parse_emoji",
    "parse_end",
)
