# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from collections.abc import Iterable
from datetime import date, datetime
from enum import StrEnum

from src.database.models import Absence, AbsenceSettings

DATE_FORMAT = "%d/%m/%Y"


class AbsenceStatus(StrEnum):
    CANCELLED = "cancelled"
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    PAST = "past"


def parse_date(value: str) -> date:
    """Parse a "JJ/MM/AAAA" string.

    Raises:
        ValueError: If `value` is not in "JJ/MM/AAAA" format.

    """
    try:
        return datetime.strptime(value.strip(), DATE_FORMAT).date()  # noqa: DTZ007 - .date() discards the naive time
    except ValueError as e:
        raise ValueError('Le format attendu est "JJ/MM/AAAA", par exemple "24/12/2026".') from e


def duration_days(start: date, end: date) -> int:
    """Count the days an absence spans, both ends included (same day = 1)."""
    return (end - start).days + 1


def is_backdated(start: date, today: date) -> bool:
    """Whether a *new* declaration's start date would be in the past.

    Only meant to gate creating absences — editing an existing one (already ongoing or past) must
    stay possible, so this is not applied there.
    """
    return start < today


def dates_overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    """Whether two inclusive date ranges share at least one day."""
    return a_start <= b_end and b_start <= a_end


def absence_status(absence: Absence, today: date) -> AbsenceStatus:
    """Derive an absence's status from its dates and cancellation — never stored directly."""
    if absence.cancelled_at is not None:
        return AbsenceStatus.CANCELLED
    if today < absence.start_date:
        return AbsenceStatus.UPCOMING
    if today > absence.end_date:
        return AbsenceStatus.PAST
    return AbsenceStatus.ONGOING


def can_self_declare(member_role_ids: Iterable[int], *, is_admin: bool, settings: AbsenceSettings) -> bool:
    """Whether a member can declare their own absence."""
    if is_admin:
        return True
    allowed = set(settings.allowed_role_ids)
    return bool(allowed.intersection(member_role_ids))


def is_responsible(member_role_ids: Iterable[int], *, settings: AbsenceSettings) -> bool:
    """Whether a member can permanently delete any absence.

    Deliberately not granted to admins automatically — only the specific role configured as
    "staff responsible" gets this, unlike every other permission check in this extension.
    """
    return settings.responsible_role_id is not None and settings.responsible_role_id in set(member_role_ids)


__all__ = (
    "DATE_FORMAT",
    "AbsenceStatus",
    "absence_status",
    "can_self_declare",
    "dates_overlap",
    "duration_days",
    "is_backdated",
    "is_responsible",
    "parse_date",
)
