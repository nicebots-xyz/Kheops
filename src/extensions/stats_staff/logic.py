# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from src.database.models import StaffQuotaMode

if TYPE_CHECKING:
    import discord

EUROPE_PARIS = ZoneInfo("Europe/Paris")

REPORT_TIME = time(hour=23, minute=59, tzinfo=EUROPE_PARIS)


class StatsPeriod(StrEnum):
    WEEK = "week"
    MONTH = "month"
    LAST_3_MONTHS = "last_3_months"
    LAST_6_MONTHS = "last_6_months"
    ALL_TIME = "all_time"


def is_valid_voice_state(voice_state: discord.VoiceState, *, other_humans: int) -> bool:
    """Whether a staff member's current voice state should count toward their quota.

    Requires the member to be neither muted nor deafened (self or server-imposed), and that at
    least one other human is present in the channel.
    """
    if voice_state.mute or voice_state.deaf:
        return False
    return other_humans > 0


def week_start(now: datetime) -> datetime:
    """Return midnight Europe/Paris on the Monday of `now`'s week."""
    monday = now.astimezone(EUROPE_PARIS).date() - timedelta(days=now.astimezone(EUROPE_PARIS).weekday())
    return datetime.combine(monday, time.min, tzinfo=EUROPE_PARIS)


def previous_week_bounds(now: datetime) -> tuple[datetime, datetime]:
    """Return `(start, end)` of last week, clipped to the same elapsed time as this week so far.

    E.g. if it's Tuesday 14:00 this week, returns last Monday 00:00 → last Tuesday 14:00 — an
    apples-to-apples comparison for `trend_arrow`, instead of comparing a partial current week to
    a full previous one (which would look like a decline early in the week purely from less time
    having passed). At the literal end of the week (Sunday 23:59), this naturally returns the
    full previous week, matching the weekly report's own comparison.
    """
    this_week_start = week_start(now)
    elapsed = now - this_week_start
    last_week_start = this_week_start - timedelta(days=7)
    return last_week_start, last_week_start + elapsed


def should_send_weekly_report(now: datetime, last_sent: date | None) -> bool:
    """Whether the weekly staff report should fire now.

    Fires once Sunday 23:59 Europe/Paris is reached, and stays true on every subsequent check
    until a report is actually sent (`last_sent` updated) — so a missed tick is retried.
    """
    now = now.astimezone(EUROPE_PARIS)
    if last_sent == now.date():
        return False
    return now.weekday() == 6 and now.timetz() >= REPORT_TIME


def period_start(period: StatsPeriod, now: datetime) -> datetime | None:
    """Return the lower bound of the given stats period, or `None` for no lower bound."""
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
    year = now.year
    month = now.month - months
    while month <= 0:
        month += 12
        year -= 1
    return now.replace(year=year, month=month)


def et_full_substitution(required: float, et_penalty: float) -> float:
    """Return the amount needed on one side of an ET quota to fully replace the other side, skipped entirely.

    E.g. with `et_penalty=1.25`, skipping a 6h vocal requirement entirely needs
    `et_full_substitution(6, 1.25) == 13.5` hours of extra voice instead.
    """
    return required * (1 + et_penalty)


def evaluate_quota(
    mode: StaffQuotaMode,
    *,
    messages: int,
    messages_required: int,
    voice_minutes: float,
    voice_minutes_required: int,
    et_penalty: float = 1.25,
) -> bool:
    """Whether a staff member's activity meets their role's quota for the mode.

    `ANY` lets messages and voice combine proportionally — e.g. half the required messages plus
    half the required voice time also meets a "4h vocal OU 100 messages" quota.

    `ALL` normally requires both thresholds met in full, but a shortfall on one side can be
    compensated by extra on the other side at `et_penalty` cost — e.g. with the default 1.25,
    skipping messages entirely on a "6h vocal ET 100 messages" quota requires 6h + 125% of 6h =
    13.5h of voice instead; doing half the required messages only needs half that penalty made up
    in extra voice. Falling short on *both* sides still fails outright.
    """
    messages_ratio = 1.0 if messages_required <= 0 else messages / messages_required
    voice_ratio = 1.0 if voice_minutes_required <= 0 else voice_minutes / voice_minutes_required

    if mode == StaffQuotaMode.ANY:
        return messages_ratio + voice_ratio >= 1.0

    if messages_ratio >= 1.0 and voice_ratio >= 1.0:
        return True
    if messages_ratio < 1.0 and voice_ratio < 1.0:
        return False
    if messages_ratio < 1.0:
        deficit = 1.0 - messages_ratio
        return voice_ratio >= 1.0 + et_penalty * deficit
    deficit = 1.0 - voice_ratio
    return messages_ratio >= 1.0 + et_penalty * deficit


def completion_ratio(
    mode: StaffQuotaMode,
    *,
    messages: int,
    messages_required: int,
    voice_minutes: float,
    voice_minutes_required: int,
) -> float:
    """Return a single 0..1+ progress score for a quota, for display (bars, trends) — not pass/fail.

    `ANY` sums the two ratios (matching how `evaluate_quota` combines them). `ALL` averages them
    — a simpler approximation than the exact substitution-penalty math in `evaluate_quota`, good
    enough for an at-a-glance progress indicator.
    """
    messages_ratio = 1.0 if messages_required <= 0 else messages / messages_required
    voice_ratio = 1.0 if voice_minutes_required <= 0 else voice_minutes / voice_minutes_required
    if mode == StaffQuotaMode.ANY:
        return messages_ratio + voice_ratio
    return (messages_ratio + voice_ratio) / 2


def progress_bar(ratio: float, *, width: int = 10) -> str:
    """Render `ratio` (0..1+) as a filled/empty block bar with a percentage, e.g. "▰▰▰▰▰▱▱▱▱▱ 50%"."""
    filled = max(0, min(width, round(ratio * width)))
    bar = "▰" * filled + "▱" * (width - filled)
    return f"{bar} {round(ratio * 100)}%"


def trend_arrow(current_ratio: float, previous_ratio: float, *, threshold: float = 0.02) -> str:
    """Compare two completion ratios and render an up/down/stable indicator with the delta."""
    diff = current_ratio - previous_ratio
    if diff > threshold:
        return f"▲ +{diff * 100:.0f}%"
    if diff < -threshold:
        return f"▼ {diff * 100:.0f}%"
    return "▬ stable"


def overlapping_minutes(
    started_at: datetime,
    ended_at: datetime | None,
    range_start: datetime | None,
    range_end: datetime,
) -> float:
    """Minutes of a (possibly still open) voice segment that fall within `[range_start, range_end]`."""
    segment_end = ended_at if ended_at is not None else range_end
    clamped_start = max(started_at, range_start) if range_start is not None else started_at
    clamped_end = min(segment_end, range_end)
    if clamped_end <= clamped_start:
        return 0.0
    return (clamped_end - clamped_start).total_seconds() / 60
