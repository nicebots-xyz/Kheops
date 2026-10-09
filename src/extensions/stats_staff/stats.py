# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING

import discord
from tortoise.expressions import Q

from src.database.models import Guild, StaffMessageEvent, StaffStatsSettings, StaffVoiceSegment

from .logic import EUROPE_PARIS, StatsPeriod, overlapping_minutes, period_start, week_start

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date

PERIOD_CHOICES = [
    discord.OptionChoice("Semaine en cours", StatsPeriod.WEEK.value),
    discord.OptionChoice("Mois en cours", StatsPeriod.MONTH.value),
    discord.OptionChoice("3 derniers mois", StatsPeriod.LAST_3_MONTHS.value),
    discord.OptionChoice("6 derniers mois", StatsPeriod.LAST_6_MONTHS.value),
    discord.OptionChoice("Depuis toujours", StatsPeriod.ALL_TIME.value),
]
PERIOD_LABELS = {StatsPeriod(choice.value): choice.name for choice in PERIOD_CHOICES}


async def get_or_create_settings(guild_id: int) -> StaffStatsSettings:
    """Fetch this guild's stats settings, creating them (and the `Guild` row they require) if needed.

    `StaffStatsSettings.guild` is a real foreign key to `Guild`, so the referenced row must exist
    first — unlike the other `guild_id` columns in this module, which are plain integers with no
    constraint.
    """
    await Guild.get_or_create(id=guild_id)
    settings, _ = await StaffStatsSettings.get_or_create(guild_id=guild_id)
    return settings


async def compute_stats_range(
    guild_id: int, member_id: int, start: datetime | None, end: datetime
) -> tuple[int, float]:
    messages_query = StaffMessageEvent.filter(guild_id=guild_id, member_id=member_id, created_at__lt=end)
    if start is not None:
        messages_query = messages_query.filter(created_at__gte=start)
    messages = await messages_query.count()

    segments = await StaffVoiceSegment.filter(guild_id=guild_id, member_id=member_id, started_at__lt=end)
    voice_minutes = sum(overlapping_minutes(s.started_at, s.ended_at, start, end) for s in segments)
    return messages, voice_minutes


async def compute_stats(guild_id: int, member_id: int, period: StatsPeriod, now: datetime) -> tuple[int, float]:
    start = period_start(period, now)
    return await compute_stats_range(guild_id, member_id, start, now)


async def bulk_compute_stats(
    guild_id: int,
    member_ids: Sequence[int],
    now: datetime,
    last_week_start: datetime,
    last_week_end: datetime,
) -> dict[int, tuple[int, float, int, float]]:
    """Fetch this-week and last-week (messages, voice_minutes) for many members in a few queries.

    Replaces what would otherwise be 4 queries per member (used by the weekly report and its
    preview, where that N+1 pattern risked slow responses or interaction timeouts on a large
    staff list).
    """
    if not member_ids:
        return {}
    this_week_start = week_start(now)

    messages_this: dict[int, int] = defaultdict(int)
    messages_last: dict[int, int] = defaultdict(int)
    message_rows = await StaffMessageEvent.filter(
        guild_id=guild_id, member_id__in=member_ids, created_at__gte=last_week_start, created_at__lt=now
    ).values_list("member_id", "created_at")
    for member_id, created_at in message_rows:
        if created_at >= this_week_start:
            messages_this[member_id] += 1
        else:
            messages_last[member_id] += 1

    voice_this: dict[int, float] = defaultdict(float)
    voice_last: dict[int, float] = defaultdict(float)
    segments = await StaffVoiceSegment.filter(guild_id=guild_id, member_id__in=member_ids, started_at__lt=now).filter(
        Q(ended_at__isnull=True) | Q(ended_at__gt=last_week_start)
    )
    for segment in segments:
        voice_this[segment.member_id] += overlapping_minutes(segment.started_at, segment.ended_at, this_week_start, now)
        voice_last[segment.member_id] += overlapping_minutes(
            segment.started_at, segment.ended_at, last_week_start, last_week_end
        )

    return {
        member_id: (
            messages_this.get(member_id, 0),
            voice_this.get(member_id, 0.0),
            messages_last.get(member_id, 0),
            voice_last.get(member_id, 0.0),
        )
        for member_id in member_ids
    }


async def compute_daily_history(guild_id: int, member_id: int, start: date, end: date) -> list[tuple[date, int, float]]:
    """Return `(day, messages, voice_minutes)` for each day in `[start, end]` (inclusive).

    Used by the dashboard API for per-day history charts, where `compute_stats_range`'s single
    aggregate total isn't granular enough.
    """
    range_start = datetime.combine(start, time.min, tzinfo=EUROPE_PARIS)
    range_end = datetime.combine(end, time.max, tzinfo=EUROPE_PARIS)

    messages_by_day: dict[date, int] = defaultdict(int)
    message_dates = await StaffMessageEvent.filter(
        guild_id=guild_id, member_id=member_id, created_at__gte=range_start, created_at__lte=range_end
    ).values_list("created_at", flat=True)
    for created_at in message_dates:
        messages_by_day[created_at.astimezone(EUROPE_PARIS).date()] += 1

    segments = await StaffVoiceSegment.filter(
        guild_id=guild_id, member_id=member_id, started_at__lte=range_end
    ).filter(Q(ended_at__isnull=True) | Q(ended_at__gte=range_start))

    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    voice_by_day: dict[date, float] = defaultdict(float)
    for day in days:
        day_start = datetime.combine(day, time.min, tzinfo=EUROPE_PARIS)
        day_end = datetime.combine(day, time.max, tzinfo=EUROPE_PARIS)
        for segment in segments:
            voice_by_day[day] += overlapping_minutes(segment.started_at, segment.ended_at, day_start, day_end)

    return [(day, messages_by_day.get(day, 0), voice_by_day.get(day, 0.0)) for day in days]


__all__ = (
    "PERIOD_CHOICES",
    "PERIOD_LABELS",
    "bulk_compute_stats",
    "compute_daily_history",
    "compute_stats",
    "compute_stats_range",
    "get_or_create_settings",
)
