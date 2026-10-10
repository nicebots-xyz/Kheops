# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord
from tortoise.functions import Count

from src.database.models import Guild, StaffMessageEvent, StaffStatsSettings, StaffVoiceSession

from .logic import StatsPeriod

if TYPE_CHECKING:
    from src.i18n.classes import RawTranslation, TranslationWrapper

    type Strings = TranslationWrapper[dict[str, RawTranslation]]

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
FROM staffvoicesession
WHERE guild_id = $1 AND started_at < $3 AND ended_at > $2
GROUP BY member_id
"""


async def get_or_create_settings(guild_id: int) -> StaffStatsSettings:
    """Fetch a guild's stats settings, creating them (and the `Guild` row they point to) if needed."""
    await Guild.get_or_create(id=guild_id)
    settings, _ = await StaffStatsSettings.get_or_create(guild_id=guild_id)
    return settings


async def get_stats(guild_id: int, start: datetime | None, end: datetime) -> dict[int, tuple[int, float]]:
    """Count every member's messages and voice minutes between `start` and `end`.

    Args:
        guild_id: The guild.
        start: The start of the range, or None for no lower bound.
        end: The end of the range (excluded).

    Returns:
        `(messages, voice_minutes)` per member id. Members with no activity are missing.

    """
    start = start or datetime.min.replace(tzinfo=UTC)
    message_rows = (
        await StaffMessageEvent.filter(guild_id=guild_id, created_at__gte=start, created_at__lt=end)
        .annotate(count=Count("id"))
        .group_by("member_id")
        .values_list("member_id", "count")
    )
    voice_rows = await StaffVoiceSession._meta.db.execute_query_dict(VOICE_SECONDS_SQL, [guild_id, start, end])  # noqa: SLF001
    messages: dict[int, int] = {int(member_id): int(count) for member_id, count in message_rows}
    voice: dict[int, float] = {int(row["member_id"]): float(row["seconds"]) / 60 for row in voice_rows}
    return {member_id: (messages.get(member_id, 0), voice.get(member_id, 0.0)) for member_id in messages | voice}


__all__ = ("PERIOD_CHOICES", "PERIOD_LABELS", "get_or_create_settings", "get_stats")
