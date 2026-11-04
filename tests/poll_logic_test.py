# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.extensions.poll.logic import (
    MAX_DURATION_HOURS,
    EndInPastError,
    EndTooFarError,
    InvalidEmojiError,
    InvalidEndFormatError,
    duration_hours,
    effective_end,
    emoji_input_value,
    parse_emoji,
    parse_end,
)

PARIS = ZoneInfo("Europe/Paris")
NOW = datetime(2026, 11, 4, 17, 0, tzinfo=UTC)


def test_parse_end_valid() -> None:
    assert parse_end("24/12/2026", "18:30", PARIS) == datetime(2026, 12, 24, 18, 30, tzinfo=PARIS)


@pytest.mark.parametrize(("date_raw", "time_raw"), [("24-12-2026", "18h30"), (" 24.12.2026 ", "18 : 30")])
def test_parse_end_alternative_separators(date_raw: str, time_raw: str) -> None:
    assert parse_end(date_raw, time_raw, PARIS) == datetime(2026, 12, 24, 18, 30, tzinfo=PARIS)


@pytest.mark.parametrize(
    ("date_raw", "time_raw"),
    [("2026/12/24", "18:30"), ("24/12/2026", "1830"), ("31/02/2026", "10:00"), ("24/12/2026", "25:00"), ("", "")],
)
def test_parse_end_invalid(date_raw: str, time_raw: str) -> None:
    with pytest.raises(InvalidEndFormatError):
        parse_end(date_raw, time_raw, PARIS)


def test_duration_rounds_up_to_overshoot() -> None:
    assert duration_hours(NOW + timedelta(hours=2, minutes=1), NOW) == 3
    assert duration_hours(NOW + timedelta(minutes=59, seconds=59), NOW) == 1
    assert duration_hours(NOW + timedelta(seconds=1), NOW) == 1


def test_duration_exact_hours_are_kept() -> None:
    assert duration_hours(NOW + timedelta(hours=5), NOW) == 5


def test_duration_effective_end_never_before_requested() -> None:
    end = NOW + timedelta(days=3, minutes=17)
    assert effective_end(NOW, duration_hours(end, NOW)) >= end


def test_duration_across_timezones() -> None:
    # 18:30 Paris (UTC+1 in November) is 17:30 UTC, half an hour after NOW.
    assert duration_hours(parse_end("04/11/2026", "18:30", PARIS), NOW) == 1


def test_duration_max() -> None:
    assert duration_hours(NOW + timedelta(hours=MAX_DURATION_HOURS), NOW) == MAX_DURATION_HOURS
    with pytest.raises(EndTooFarError):
        duration_hours(NOW + timedelta(hours=MAX_DURATION_HOURS, seconds=1), NOW)


@pytest.mark.parametrize("delta", [timedelta(0), timedelta(minutes=-5)])
def test_duration_past(delta: timedelta) -> None:
    with pytest.raises(EndInPastError):
        duration_hours(NOW + delta, NOW)


def test_parse_emoji_empty() -> None:
    assert parse_emoji(None) is None
    assert parse_emoji("   ") is None


def test_parse_emoji_id() -> None:
    emoji = parse_emoji(" 123456789012345678 ")
    assert emoji is not None
    assert emoji.id == 123456789012345678
    assert emoji_input_value(emoji) == "123456789012345678"


@pytest.mark.parametrize(
    ("raw", "animated"), [("<:kheops:123456789012345678>", False), ("<a:kheops:123456789012345678>", True)]
)
def test_parse_emoji_custom_mention(raw: str, animated: bool) -> None:
    emoji = parse_emoji(raw)
    assert emoji is not None
    assert (emoji.name, emoji.id, emoji.animated) == ("kheops", 123456789012345678, animated)


@pytest.mark.parametrize("raw", ["🎃", "1️⃣", "👍🏽"])
def test_parse_emoji_unicode(raw: str) -> None:
    emoji = parse_emoji(raw)
    assert emoji is not None
    assert emoji.id is None
    assert emoji.name == raw
    assert emoji_input_value(emoji) == raw


def test_parse_emoji_alias() -> None:
    emoji = parse_emoji(":jack_o_lantern:")
    assert emoji is not None
    assert emoji.name == "🎃"


@pytest.mark.parametrize("raw", ["hello", "12", ":not_a_real_emoji_alias:"])
def test_parse_emoji_invalid(raw: str) -> None:
    with pytest.raises(InvalidEmojiError):
        parse_emoji(raw)
