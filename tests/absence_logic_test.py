# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest

from src.extensions.absence.logic import (
    AbsenceStatus,
    absence_status,
    can_self_declare,
    dates_overlap,
    duration_days,
    is_backdated,
    is_responsible,
    parse_date,
)


@dataclass
class _FakeSettings:
    allowed_role_ids: list[int]
    responsible_role_id: int | None = None


@dataclass
class _FakeAbsence:
    start_date: date
    end_date: date
    cancelled_at: datetime | None = None


def test_parse_date_valid() -> None:
    assert parse_date("24/12/2026") == date(2026, 12, 24)


def test_parse_date_invalid_format() -> None:
    with pytest.raises(ValueError, match="JJ/MM/AAAA"):
        parse_date("not a date")


def test_parse_date_out_of_range() -> None:
    with pytest.raises(ValueError, match="JJ/MM/AAAA"):
        parse_date("32/13/2026")


def test_duration_days_same_day() -> None:
    assert duration_days(date(2026, 3, 20), date(2026, 3, 20)) == 1


def test_duration_days_multiple_days() -> None:
    assert duration_days(date(2026, 3, 20), date(2026, 3, 25)) == 6


def test_is_backdated_past_start() -> None:
    assert is_backdated(date(2026, 3, 19), date(2026, 3, 20)) is True


def test_is_backdated_today_is_not_backdated() -> None:
    assert is_backdated(date(2026, 3, 20), date(2026, 3, 20)) is False


def test_is_backdated_future_is_not_backdated() -> None:
    assert is_backdated(date(2026, 3, 21), date(2026, 3, 20)) is False


def test_dates_overlap_identical_ranges() -> None:
    assert dates_overlap(date(2026, 3, 20), date(2026, 3, 25), date(2026, 3, 20), date(2026, 3, 25)) is True


def test_dates_overlap_partial() -> None:
    assert dates_overlap(date(2026, 3, 20), date(2026, 3, 25), date(2026, 3, 24), date(2026, 3, 30)) is True


def test_dates_overlap_touching_single_day() -> None:
    assert dates_overlap(date(2026, 3, 20), date(2026, 3, 25), date(2026, 3, 25), date(2026, 3, 30)) is True


def test_dates_overlap_disjoint() -> None:
    assert dates_overlap(date(2026, 3, 20), date(2026, 3, 25), date(2026, 3, 26), date(2026, 3, 30)) is False


def test_absence_status_upcoming() -> None:
    absence = _FakeAbsence(start_date=date(2026, 3, 20), end_date=date(2026, 3, 25))
    assert absence_status(absence, date(2026, 3, 19)) == AbsenceStatus.UPCOMING  # pyright: ignore[reportArgumentType]


def test_absence_status_ongoing_on_start_day() -> None:
    absence = _FakeAbsence(start_date=date(2026, 3, 20), end_date=date(2026, 3, 25))
    assert absence_status(absence, date(2026, 3, 20)) == AbsenceStatus.ONGOING  # pyright: ignore[reportArgumentType]


def test_absence_status_ongoing_on_end_day() -> None:
    absence = _FakeAbsence(start_date=date(2026, 3, 20), end_date=date(2026, 3, 25))
    assert absence_status(absence, date(2026, 3, 25)) == AbsenceStatus.ONGOING  # pyright: ignore[reportArgumentType]


def test_absence_status_past() -> None:
    absence = _FakeAbsence(start_date=date(2026, 3, 20), end_date=date(2026, 3, 25))
    assert absence_status(absence, date(2026, 3, 26)) == AbsenceStatus.PAST  # pyright: ignore[reportArgumentType]


def test_absence_status_cancelled_overrides_dates() -> None:
    absence = _FakeAbsence(
        start_date=date(2026, 3, 20), end_date=date(2026, 3, 25), cancelled_at=datetime(2026, 3, 21, tzinfo=UTC)
    )
    assert absence_status(absence, date(2026, 3, 22)) == AbsenceStatus.CANCELLED  # pyright: ignore[reportArgumentType]


def test_can_self_declare_admin_always_true() -> None:
    settings = _FakeSettings(allowed_role_ids=[])
    assert can_self_declare([], is_admin=True, settings=settings) is True  # pyright: ignore[reportArgumentType]


def test_can_self_declare_no_matching_role() -> None:
    settings = _FakeSettings(allowed_role_ids=[1, 2])
    assert can_self_declare([3, 4], is_admin=False, settings=settings) is False  # pyright: ignore[reportArgumentType]


def test_can_self_declare_matching_role() -> None:
    settings = _FakeSettings(allowed_role_ids=[1, 2])
    assert can_self_declare([2, 4], is_admin=False, settings=settings) is True  # pyright: ignore[reportArgumentType]


def test_is_responsible_admin_always_true() -> None:
    settings = _FakeSettings(allowed_role_ids=[], responsible_role_id=None)
    assert is_responsible([], is_admin=True, settings=settings) is True  # pyright: ignore[reportArgumentType]


def test_is_responsible_no_role_configured() -> None:
    settings = _FakeSettings(allowed_role_ids=[], responsible_role_id=None)
    assert is_responsible([1, 2], is_admin=False, settings=settings) is False  # pyright: ignore[reportArgumentType]


def test_is_responsible_matching_role() -> None:
    settings = _FakeSettings(allowed_role_ids=[], responsible_role_id=5)
    assert is_responsible([5, 6], is_admin=False, settings=settings) is True  # pyright: ignore[reportArgumentType]


def test_is_responsible_non_matching_role() -> None:
    settings = _FakeSettings(allowed_role_ids=[], responsible_role_id=5)
    assert is_responsible([6, 7], is_admin=False, settings=settings) is False  # pyright: ignore[reportArgumentType]
