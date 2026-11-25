# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

import discord
from tortoise.functions import Count
from tortoise.transactions import in_transaction

from src.database.models import Guild, MemberActivityMessageEvent, MemberActivitySettings, MemberActivityVoiceSession

from .logic import StatsPeriod

if TYPE_CHECKING:
    from tortoise.backends.base.client import BaseDBAsyncClient

PERIOD_CHOICES = [
    discord.OptionChoice("Semaine en cours", StatsPeriod.WEEK.value),
    discord.OptionChoice("Mois en cours", StatsPeriod.MONTH.value),
    discord.OptionChoice("3 derniers mois", StatsPeriod.LAST_3_MONTHS.value),
    discord.OptionChoice("6 derniers mois", StatsPeriod.LAST_6_MONTHS.value),
    discord.OptionChoice("Depuis toujours", StatsPeriod.ALL_TIME.value),
]
PERIOD_LABELS = {StatsPeriod(choice.value): choice.name for choice in PERIOD_CHOICES}

# Each session only counts for the part that falls inside [$2, $3).
VOICE_SECONDS_SQL = """
SELECT member_id, SUM(EXTRACT(EPOCH FROM LEAST(ended_at, $3) - GREATEST(started_at, $2))) AS seconds
FROM memberactivityvoicesession
WHERE guild_id = $1 AND started_at < $3 AND ended_at > $2
GROUP BY member_id
"""

# One row per Europe/Paris day in [$3, $4]; sessions and messages are cut at the day boundaries.
DAILY_HISTORY_SQL = """
WITH days AS (
    SELECT d::date AS day,
           d::date::timestamp AT TIME ZONE 'Europe/Paris' AS day_start,
           (d::date + 1)::timestamp AT TIME ZONE 'Europe/Paris' AS day_end
    FROM generate_series($3::date, $4::date, interval '1 day') AS d
)
SELECT days.day,
       (SELECT COUNT(*) FROM memberactivitymessageevent m
        WHERE m.guild_id = $1 AND m.member_id = $2
          AND m.created_at >= days.day_start AND m.created_at < days.day_end) AS messages,
       (SELECT COALESCE(SUM(EXTRACT(EPOCH FROM
                    LEAST(s.ended_at, days.day_end) - GREATEST(s.started_at, days.day_start))), 0)
        FROM memberactivityvoicesession s
        WHERE s.guild_id = $1 AND s.member_id = $2
          AND s.started_at < days.day_end AND s.ended_at > days.day_start) AS seconds
FROM days
ORDER BY days.day
"""


async def get_or_create_settings(guild_id: int) -> MemberActivitySettings:
    """Fetch a guild's activity settings, creating them (and the `Guild` row they point to) if needed."""
    await Guild.get_or_create(id=guild_id)
    settings, _ = await MemberActivitySettings.get_or_create(guild_id=guild_id)
    return settings


async def _lock_guild_settings(conn: BaseDBAsyncClient, guild_id: int) -> None:
    """Postgres advisory lock scoped to one guild's activity settings.

    Same technique as stats_staff's `_lock_guild_settings`, prevents a read-modify-write race
    between two concurrent writers (e.g. two dashboard requests).
    """
    await conn.execute_query(
        "SELECT pg_advisory_xact_lock(hashtextextended($1, 0))", [f"member_activity_settings:{guild_id}"]
    )


async def update_settings(
    guild_id: int,
    *,
    message_channel_ids: list[int],
    voice_channel_ids: list[int],
    tracked_category_ids: list[int],
) -> MemberActivitySettings:
    """Atomically replace a guild's activity settings under the per-guild lock (see `_lock_guild_settings`)."""
    async with in_transaction() as conn:
        await Guild.get_or_create(id=guild_id, using_db=conn)
        await _lock_guild_settings(conn, guild_id)
        settings, _ = await MemberActivitySettings.get_or_create(guild_id=guild_id, using_db=conn)
        settings.message_channel_ids = message_channel_ids
        settings.voice_channel_ids = voice_channel_ids
        settings.tracked_category_ids = tracked_category_ids
        await settings.save(
            using_db=conn,
            update_fields=["message_channel_ids", "voice_channel_ids", "tracked_category_ids"],
        )
        return settings


async def get_stats(guild_id: int, start: datetime | None, end: datetime) -> dict[int, tuple[int, float]]:
    """Count every member's messages and voice minutes between `start` and `end`.

    Returns:
        `(messages, voice_minutes)` per member id. Members with no activity are missing.

    """
    start = start or datetime.min.replace(tzinfo=UTC)
    message_rows = (
        await MemberActivityMessageEvent.filter(guild_id=guild_id, created_at__gte=start, created_at__lt=end)
        .annotate(count=Count("id"))
        .group_by("member_id")
        .values_list("member_id", "count")
    )
    voice_rows = await MemberActivityVoiceSession._meta.db.execute_query_dict(VOICE_SECONDS_SQL, [guild_id, start, end])  # noqa: SLF001
    messages: dict[int, int] = {int(member_id): int(count) for member_id, count in message_rows}
    voice: dict[int, float] = {int(row["member_id"]): float(row["seconds"]) / 60 for row in voice_rows}
    return {member_id: (messages.get(member_id, 0), voice.get(member_id, 0.0)) for member_id in messages | voice}


async def get_daily_history(guild_id: int, member_id: int, start: date, end: date) -> list[tuple[date, int, float]]:
    """Count a member's messages and voice minutes for each day (Europe/Paris) from `start` to `end`.

    Returns:
        `(day, messages, voice_minutes)` for every day of the range, in order.

    """
    rows = await MemberActivityVoiceSession._meta.db.execute_query_dict(  # noqa: SLF001
        DAILY_HISTORY_SQL, [guild_id, member_id, start, end]
    )
    return [(row["day"], int(row["messages"]), float(row["seconds"]) / 60) for row in rows]


__all__ = (
    "PERIOD_CHOICES",
    "PERIOD_LABELS",
    "get_daily_history",
    "get_or_create_settings",
    "get_stats",
    "update_settings",
)
