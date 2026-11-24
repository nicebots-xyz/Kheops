# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from dataclasses import dataclass
from datetime import date, time

import pytest

from src.database.models import TITLE_MAX_LENGTH_ANNOUNCEMENT
from src.extensions.announce.logic import can_schedule, parse_date, parse_time, sanitize_image_filename
from src.extensions.announce.send import localize, text_length
from src.i18n.classes import RawTranslation


@dataclass
class _FakeSettings:
    allowed_role_ids: list[int]


def test_parse_date_valid() -> None:
    assert parse_date("24/12/2026") == date(2026, 12, 24)


def test_parse_date_invalid_format() -> None:
    with pytest.raises(ValueError, match="does not match format"):
        parse_date("not a date")


def test_parse_time_valid() -> None:
    assert parse_time("18:30") == time(18, 30)


def test_parse_time_invalid_format() -> None:
    with pytest.raises(ValueError, match="does not match format"):
        parse_time("not a time")


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


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("photo.PNG", "photo.png"),
        ("mon image (1).jpeg", "mon_image_1.jpeg"),
        ("../../etc/passwd.png", "passwd.png"),
        ("C:\\Users\\me\\été.webp", "t.webp"),
        ("???.gif", "image.gif"),
        ("x" * 200 + ".jpg", "x" * 60 + ".jpg"),
    ],
)
def test_sanitize_image_filename(filename: str, expected: str) -> None:
    assert sanitize_image_filename(filename) == expected


@pytest.mark.parametrize("filename", ["script.svg", "archive.zip", "no_extension", "image.png.exe"])
def test_sanitize_image_filename_rejects_non_images(filename: str) -> None:
    assert sanitize_image_filename(filename) is None


def test_text_length_counts_every_text_display() -> None:
    t = localize({"signature": RawTranslation({"en-US": "by {author}"})}, None)
    length = text_length(
        t=t,
        title="T" * TITLE_MAX_LENGTH_ANNOUNCEMENT,
        content="c" * 10,
        footer="f",
        role_ids_to_mention=[1, 22],
        created_by_id=333,
    )
    rendered = ["<@&1> <@&22>", "# " + "T" * TITLE_MAX_LENGTH_ANNOUNCEMENT, "c" * 10, "-# f", "by <@333>"]
    assert length == sum(len(text) for text in rendered)
