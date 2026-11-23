# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from dataclasses import dataclass
from datetime import date, time

import pytest

from src.extensions.announce.logic import can_schedule, can_send_instant, parse_date, parse_time


@dataclass
class _FakeSettings:
    allowed_role_ids: list[int]


def test_parse_date_valid() -> None:
    assert parse_date("24/12/2026") == date(2026, 12, 24)


def test_parse_date_invalid_format() -> None:
    with pytest.raises(ValueError, match="JJ/MM/AAAA"):
        parse_date("not a date")


def test_parse_time_valid() -> None:
    assert parse_time("18:30") == time(18, 30)


def test_parse_time_invalid_format() -> None:
    with pytest.raises(ValueError, match="HH:MM"):
        parse_time("not a time")


def test_can_send_instant_admin() -> None:
    assert can_send_instant(is_admin=True) is True


def test_can_send_instant_non_admin() -> None:
    assert can_send_instant(is_admin=False) is False


def test_can_schedule_admin_always() -> None:
    settings = _FakeSettings(allowed_role_ids=[])
    assert can_schedule([], is_admin=True, settings=settings) is True  # pyright: ignore[reportArgumentType]


def test_can_schedule_allowed_role() -> None:
    settings = _FakeSettings(allowed_role_ids=[1, 2])
    assert can_schedule([2, 3], is_admin=False, settings=settings) is True  # pyright: ignore[reportArgumentType]


def test_can_schedule_no_matching_role() -> None:
    settings = _FakeSettings(allowed_role_ids=[1, 2])
    assert can_schedule([3, 4], is_admin=False, settings=settings) is False  # pyright: ignore[reportArgumentType]


def test_can_schedule_no_roles_configured() -> None:
    settings = _FakeSettings(allowed_role_ids=[])
    assert can_schedule([1, 2], is_admin=False, settings=settings) is False  # pyright: ignore[reportArgumentType]
