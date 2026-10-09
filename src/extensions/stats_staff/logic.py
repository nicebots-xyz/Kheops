# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from src.database.models import StaffQuotaMode, StaffRoleQuota

if TYPE_CHECKING:
    from collections.abc import Sequence

    import discord

EUROPE_PARIS = ZoneInfo("Europe/Paris")


class StatsPeriod(StrEnum):
    WEEK = "week"
    MONTH = "month"
    LAST_3_MONTHS = "last_3_months"
    LAST_6_MONTHS = "last_6_months"
    ALL_TIME = "all_time"


def is_valid_voice_state(voice_state: discord.VoiceState, *, other_humans: int) -> bool:
    """Whether a staff member's current voice state should count toward their quota.

    Requires the member to be neither muted nor deafened — self-imposed or server-imposed — and
    that at least one other human is present in the channel. `VoiceState.mute`/`.deaf` only
    reflect a server-imposed mute/deafen; `self_mute`/`self_deaf` must be checked separately.
    """
    if voice_state.mute or voice_state.deaf or voice_state.self_mute or voice_state.self_deaf:
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


def weekly_report_deadline(now: datetime) -> datetime:
    """Return the Sunday 23:59 Europe/Paris deadline that `now` should be checked against.

    Normally "this week's" deadline (today, if it's Sunday evening). In the first hour after
    midnight on Monday, resolves to *last* night's deadline instead — a safety grace window so a
    report loop whose tick phase lands a few minutes outside the narrow Sunday-23:59 instant still
    catches it, instead of permanently missing that week's report.
    """
    now = now.astimezone(EUROPE_PARIS)
    reference = now - timedelta(days=1) if now.weekday() == 0 and now.time() < time(1, 0) else now
    monday = reference.date() - timedelta(days=reference.weekday())
    sunday = monday + timedelta(days=6)
    return datetime.combine(sunday, time(23, 59), tzinfo=EUROPE_PARIS)


def should_send_weekly_report(now: datetime, last_sent: date | None) -> bool:
    """Whether the weekly staff report should fire now.

    Fires once the relevant Sunday 23:59 Europe/Paris deadline is reached (see
    `weekly_report_deadline`), and stays true on every subsequent check until a report is actually
    sent for that deadline (`last_sent` holds the deadline's date, not the send date) — so a
    missed tick is retried, within the grace window.
    """
    now = now.astimezone(EUROPE_PARIS)
    deadline = weekly_report_deadline(now)
    if now < deadline:
        return False
    return last_sent != deadline.date()


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
    last_day_of_month = calendar.monthrange(year, month)[1]
    day = min(now.day, last_day_of_month)
    return now.replace(year=year, month=month, day=day)


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


def resolve_quota_for_member(
    member_role_ids: set[int],
    quotas: Sequence[StaffRoleQuota],
    override_role_id: int | None,
) -> StaffRoleQuota | None:
    """Pick the single quota that applies to a member, from the roles they currently hold.

    A member matching more than one configured role is resolved via `override_role_id` (their
    `StaffMemberRoleOverride`, if set) so they are never counted under more than one role. Falls
    back to the first matching quota if no override is set or it no longer matches.
    """
    matching = [quota for quota in quotas if quota.role_id in member_role_ids]
    if not matching:
        return None
    if len(matching) == 1:
        return matching[0]
    if override_role_id is not None:
        picked = next((quota for quota in matching if quota.role_id == override_role_id), None)
        if picked is not None:
            return picked
    return matching[0]


def chunk_text_lines(items: Sequence[str], max_chars: int, *, sep: str = "\n") -> list[str]:
    """Group `items` into chunks joined by `sep`, each at most `max_chars` long.

    Used to stay under Discord's per-component text size limit (e.g. a Text Display is capped at
    4,000 characters) when rendering a list whose length depends on how many staff members exist.
    A single item longer than `max_chars` becomes its own oversized chunk rather than being split
    (splitting mid-item would produce broken output).
    """
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for item in items:
        added_len = len(item) + (len(sep) if current else 0)
        if current and current_len + added_len > max_chars:
            chunks.append(sep.join(current))
            current = []
            current_len = 0
            added_len = len(item)
        current.append(item)
        current_len += added_len
    if current:
        chunks.append(sep.join(current))
    return chunks


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
