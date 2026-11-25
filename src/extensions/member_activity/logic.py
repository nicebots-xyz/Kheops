# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

import calendar
from datetime import datetime, time
from datetime import timedelta as _timedelta
from enum import StrEnum
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from collections.abc import Collection

    import discord

EUROPE_PARIS = ZoneInfo("Europe/Paris")


class StatsPeriod(StrEnum):
    WEEK = "week"
    MONTH = "month"
    LAST_3_MONTHS = "last_3_months"
    LAST_6_MONTHS = "last_6_months"
    ALL_TIME = "all_time"


def is_valid_voice_state(voice_state: discord.VoiceState, *, other_humans: int) -> bool:
    """Whether a voice state counts: not muted or deafened (self or server), and not alone.

    Same anti-AFK rule as stats_staff (see `StaffVoiceSession`/`is_valid_voice_state` there) —
    kept identical on purpose so voice time means the same thing across both extensions.
    """
    if voice_state.mute or voice_state.deaf or voice_state.self_mute or voice_state.self_deaf:
        return False
    return other_humans > 0


def is_tracked_channel(
    channel: discord.abc.GuildChannel | discord.Thread, channel_ids: Collection[int], category_ids: Collection[int]
) -> bool:
    """Whether a channel is tracked, by being listed itself or belonging to a tracked category."""
    return channel.id in channel_ids or channel.category_id in category_ids


def counting_channel_id(
    member: discord.Member, voice_channel_ids: Collection[int], category_ids: Collection[int]
) -> int | None:
    """Return the tracked voice channel this member is counting in right now, if any.

    Unlike stats_staff's `counting_channel_id`, there is no quota-role gate here: every human
    member in a tracked channel counts, regardless of their roles.

    Args:
        member: The member, as currently cached.
        voice_channel_ids: The tracked voice channels.
        category_ids: The categories tracked in full.

    Returns:
        The channel id while the member's voice time counts, otherwise None.

    """
    if member.bot:
        return None
    voice = member.voice
    if voice is None or voice.channel is None or not is_tracked_channel(voice.channel, voice_channel_ids, category_ids):
        return None
    other_humans = sum(1 for other in voice.channel.members if not other.bot and other.id != member.id)
    return voice.channel.id if is_valid_voice_state(voice, other_humans=other_humans) else None


def week_start(now: datetime) -> datetime:
    """Return Monday 00:00 Europe/Paris of the week containing `now`."""
    today = now.astimezone(EUROPE_PARIS).date()
    return datetime.combine(today - _timedelta(days=today.weekday()), time.min, tzinfo=EUROPE_PARIS)


def period_start(period: StatsPeriod, now: datetime) -> datetime | None:
    """Return the lower bound of `period`, or None for no lower bound."""
    now = now.astimezone(EUROPE_PARIS)
    match period:
        case StatsPeriod.WEEK:
            return week_start(now)
        case StatsPeriod.MONTH:
            return datetime.combine(now.date().replace(day=1), time.min, tzinfo=EUROPE_PARIS)
        case StatsPeriod.LAST_3_MONTHS:
            return _months_ago(now, 3)
        case StatsPeriod.LAST_6_MONTHS:
            return _months_ago(now, 6)
        case StatsPeriod.ALL_TIME:
            return None


def _months_ago(now: datetime, months: int) -> datetime:
    year, month = divmod(now.year * 12 + now.month - 1 - months, 12)
    month += 1
    day = min(now.day, calendar.monthrange(year, month)[1])
    return now.replace(year=year, month=month, day=day)


__all__ = (
    "EUROPE_PARIS",
    "StatsPeriod",
    "counting_channel_id",
    "is_tracked_channel",
    "is_valid_voice_state",
    "period_start",
    "week_start",
)
