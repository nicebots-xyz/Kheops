# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

import calendar
from datetime import datetime, time, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from src.database.models import StaffQuotaMode, StaffRoleQuota

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

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

    Args:
        voice_state: The member's current voice state.
        other_humans: How many other non-bot members are in the same channel.

    Returns:
        True if this voice time should count toward the quota.

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
    member: discord.Member,
    voice_channel_ids: Collection[int],
    category_ids: Collection[int],
    quota_role_ids: Collection[int],
) -> int | None:
    """Return the tracked voice channel this member is counting in right now, if any.

    Args:
        member: The member, as currently cached.
        voice_channel_ids: The tracked voice channels.
        category_ids: The categories tracked in full.
        quota_role_ids: The roles that have a quota.

    Returns:
        The channel id while the member's voice time counts, otherwise None.

    """
    if member.bot or not any(role.id in quota_role_ids for role in member.roles):
        return None
    voice = member.voice
    if voice is None or voice.channel is None or not is_tracked_channel(voice.channel, voice_channel_ids, category_ids):
        return None
    other_humans = sum(1 for other in voice.channel.members if not other.bot and other.id != member.id)
    return voice.channel.id if is_valid_voice_state(voice, other_humans=other_humans) else None


def week_start(now: datetime) -> datetime:
    """Return Monday 00:00 Europe/Paris of the week containing `now`."""
    today = now.astimezone(EUROPE_PARIS).date()
    return datetime.combine(today - timedelta(days=today.weekday()), time.min, tzinfo=EUROPE_PARIS)


def previous_week_bounds(now: datetime) -> tuple[datetime, datetime]:
    """Return last week's start and the same elapsed point in it.

    On Tuesday 14:00 this gives last Monday 00:00 to last Tuesday 14:00, so a week in progress is
    compared with the same amount of time, not with a full week.

    Args:
        now: The current time.

    Returns:
        The `(start, end)` of the comparable part of last week.

    """
    this_week_start = week_start(now)
    last_week_start = this_week_start - timedelta(days=7)
    return last_week_start, last_week_start + (now - this_week_start)


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


def quota_score(
    mode: StaffQuotaMode,
    *,
    messages: int,
    messages_required: int,
    voice_minutes: float,
    voice_minutes_required: int,
    penalty: float,
) -> float:
    """Return how much of a quota is done. 1.0 or more means the quota is met.

    ANY ("OU") adds the two ratios: half the messages plus half the voice time is 100%. A side with a
    requirement of 0 adds nothing.

    ALL ("ET") needs both sides. A shortfall on one side can be made up with extra on the other, at
    `penalty` extra cost: skipping messages entirely on "6h ET 100 messages" with a 1.25 penalty needs
    6h + 125% of 6h = 13.5h. A side with a requirement of 0 counts as met. With a penalty of 0, one full
    side is enough.

    A quota with both requirements at 0 is always met.

    Args:
        mode: How the two sides combine.
        messages: Messages sent.
        messages_required: Messages required.
        voice_minutes: Valid voice minutes.
        voice_minutes_required: Voice minutes required.
        penalty: The ALL substitution penalty (1.25 means 125%).

    Returns:
        The completion score; also what the progress bars show.

    """
    if messages_required <= 0 and voice_minutes_required <= 0:
        return 1.0
    if mode == StaffQuotaMode.ANY:
        m = messages / messages_required if messages_required > 0 else 0.0
        v = voice_minutes / voice_minutes_required if voice_minutes_required > 0 else 0.0
        return m + v
    m = messages / messages_required if messages_required > 0 else 1.0
    v = voice_minutes / voice_minutes_required if voice_minutes_required > 0 else 1.0
    low, high = min(m, v), max(m, v)
    if high < 1:
        return low
    return low + ((high - 1) / penalty if penalty > 0 else 1.0)


def progress_bar(ratio: float, *, width: int = 10) -> str:
    """Render `ratio` as a block bar with a percentage, e.g. "▰▰▰▰▰▱▱▱▱▱ 50%"."""
    filled = max(0, min(width, round(ratio * width)))
    return "▰" * filled + "▱" * (width - filled) + f" {round(ratio * 100)}%"


def trend_arrow(current_ratio: float, previous_ratio: float, *, threshold: float = 0.02) -> str:
    """Render the change between two scores as an up/down/stable indicator."""
    diff = current_ratio - previous_ratio
    if diff > threshold:
        return f"▲ +{diff * 100:.0f}%"
    if diff < -threshold:
        return f"▼ {diff * 100:.0f}%"
    return "▬ stable"


def resolve_quota_for_member(
    member_role_positions: Mapping[int, int],
    quotas: Sequence[StaffRoleQuota],
    override_role_id: int | None,
) -> StaffRoleQuota | None:
    """Pick the one quota that applies to a member.

    Args:
        member_role_positions: The member's roles, as role id to Discord role position.
        quotas: The guild's quotas.
        override_role_id: The role an admin pinned this member to, if any.

    Returns:
        The override if it still matches, else the quota of the member's highest quota role, else None.

    """
    matching = [quota for quota in quotas if quota.role_id in member_role_positions]
    override = next((quota for quota in matching if quota.role_id == override_role_id), None)
    if override is not None or not matching:
        return override
    return max(matching, key=lambda quota: member_role_positions[quota.role_id])


def chunk_text_lines(items: Sequence[str], max_chars: int, *, sep: str = "\n") -> list[str]:
    """Group `items` into chunks joined by `sep`, each at most `max_chars` long.

    A single item longer than `max_chars` becomes its own oversized chunk instead of being cut.

    Args:
        items: The lines to group.
        max_chars: The maximum length of a chunk.
        sep: What joins the items of a chunk.

    Returns:
        The chunks, in order.

    """
    chunks: list[str] = []
    current: list[str] = []
    for item in items:
        if current and len(sep.join([*current, item])) > max_chars:
            chunks.append(sep.join(current))
            current = []
        current.append(item)
    if current:
        chunks.append(sep.join(current))
    return chunks
