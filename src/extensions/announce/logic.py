# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from collections.abc import Iterable
from datetime import date, datetime, time

from src.database.models import AnnounceSettings

DATE_FORMAT = "%d/%m/%Y"
TIME_FORMAT = "%H:%M"


def parse_date(value: str) -> date:
    """Parse a "JJ/MM/AAAA" string.

    Raises:
        ValueError: If `value` is not in "JJ/MM/AAAA" format.

    """
    try:
        return datetime.strptime(value.strip(), DATE_FORMAT).date()  # noqa: DTZ007 - .date() discards the naive time
    except ValueError as e:
        raise ValueError('Le format attendu est "JJ/MM/AAAA", par exemple "24/12/2026".') from e


def parse_time(value: str) -> time:
    """Parse a "HH:MM" (24h) string.

    Raises:
        ValueError: If `value` is not in "HH:MM" format.

    """
    try:
        return datetime.strptime(value.strip(), TIME_FORMAT).time()  # noqa: DTZ007 - .time() discards the naive date
    except ValueError as e:
        raise ValueError('Le format attendu est "HH:MM" (24h), par exemple "18:30".') from e


def can_send_instant(*, is_admin: bool) -> bool:
    """Whether a member can post an announcement right away, with no scheduling delay.

    Deliberately admin-only: everyone on staff can schedule an announcement (see
    `can_schedule`), but bypassing the delay entirely is kept to the people already trusted with
    every other admin-only action in this bot.
    """
    return is_admin


def can_schedule(member_role_ids: Iterable[int], *, is_admin: bool, settings: AnnounceSettings) -> bool:
    """Whether a member can schedule an announcement for later.

    Admins always can; everyone else needs one of the roles an admin configured via
    `/announce-admin config` (same pattern as `absence.logic.can_self_declare`).
    """
    if is_admin:
        return True
    allowed = set(settings.allowed_role_ids)
    return bool(allowed.intersection(member_role_ids))


__all__ = (
    "DATE_FORMAT",
    "TIME_FORMAT",
    "can_schedule",
    "can_send_instant",
    "parse_date",
    "parse_time",
)
