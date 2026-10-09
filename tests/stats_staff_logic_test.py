# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

import random
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, cast

import pytest

from src.database.models import StaffQuotaMode, StaffRoleQuota
from src.extensions.stats_staff.logic import (
    EUROPE_PARIS,
    StatsPeriod,
    chunk_text_lines,
    is_valid_voice_state,
    period_start,
    previous_week_bounds,
    progress_bar,
    quota_score,
    resolve_quota_for_member,
    trend_arrow,
    week_start,
)

if TYPE_CHECKING:
    import discord

ANY, ALL = StaffQuotaMode.ANY, StaffQuotaMode.ALL


def paris(*args: int) -> datetime:
    return datetime(*args, tzinfo=EUROPE_PARIS)  # pyright: ignore[reportArgumentType]


@dataclass
class _FakeVoiceState:
    mute: bool = False
    deaf: bool = False
    self_mute: bool = False
    self_deaf: bool = False


def score(mode: StaffQuotaMode, messages: int, messages_required: int, voice: float, voice_required: int) -> float:
    return quota_score(
        mode,
        messages=messages,
        messages_required=messages_required,
        voice_minutes=voice,
        voice_minutes_required=voice_required,
        penalty=1.25,
    )


@pytest.mark.parametrize("now", [paris(2026, 3, 16, 10, 0), paris(2026, 3, 22, 23, 0)])
def test_week_start(now: datetime) -> None:
    assert week_start(now) == paris(2026, 3, 16, 0, 0)


@pytest.mark.parametrize(
    ("period", "now", "expected"),
    [
        (StatsPeriod.WEEK, paris(2026, 3, 18, 12, 0), paris(2026, 3, 16, 0, 0)),
        (StatsPeriod.MONTH, paris(2026, 3, 18, 12, 0), paris(2026, 3, 1, 0, 0)),
        (StatsPeriod.LAST_3_MONTHS, paris(2026, 2, 10, 12, 0), paris(2025, 11, 10, 12, 0)),
        (StatsPeriod.LAST_6_MONTHS, paris(2026, 3, 18, 12, 0), paris(2025, 9, 18, 12, 0)),
        (StatsPeriod.LAST_3_MONTHS, paris(2026, 5, 31, 12, 0), paris(2026, 2, 28, 12, 0)),
        (StatsPeriod.LAST_6_MONTHS, paris(2025, 12, 31, 12, 0), paris(2025, 6, 30, 12, 0)),
        (StatsPeriod.ALL_TIME, paris(2026, 3, 18, 12, 0), None),
    ],
)
def test_period_start(period: StatsPeriod, now: datetime, expected: datetime | None) -> None:
    assert period_start(period, now) == expected


def test_previous_week_bounds_cuts_last_week_at_the_same_point() -> None:
    assert previous_week_bounds(paris(2026, 3, 17, 14, 0)) == (paris(2026, 3, 9, 0, 0), paris(2026, 3, 10, 14, 0))


@pytest.mark.parametrize(
    ("state", "other_humans", "expected"),
    [
        (_FakeVoiceState(), 1, True),
        (_FakeVoiceState(), 0, False),
        (_FakeVoiceState(mute=True), 1, False),
        (_FakeVoiceState(deaf=True), 1, False),
        (_FakeVoiceState(self_mute=True), 1, False),
        (_FakeVoiceState(self_deaf=True), 1, False),
    ],
)
def test_is_valid_voice_state(state: _FakeVoiceState, other_humans: int, expected: bool) -> None:
    voice_state = cast("discord.VoiceState", cast("object", state))
    assert is_valid_voice_state(voice_state, other_humans=other_humans) is expected


def _old_evaluate_quota(mode: StaffQuotaMode, m: float, v: float, penalty: float) -> bool:
    """Apply the previous pass/fail rule (on ratios), kept to prove quota_score agrees with it."""
    if mode == ANY:
        return m + v >= 1.0
    if m >= 1.0 and v >= 1.0:
        return True
    if m < 1.0 and v < 1.0:
        return False
    if m < 1.0:
        return v >= 1.0 + penalty * (1.0 - m)
    return m >= 1.0 + penalty * (1.0 - v)


def test_quota_score_passes_exactly_when_the_old_rule_did() -> None:
    rng = random.Random(42)  # noqa: S311
    for _ in range(20_000):
        mode = rng.choice([ANY, ALL])
        messages_required, voice_required = rng.randint(1, 200), rng.randint(1, 1200)
        messages, voice = rng.randint(0, 600), rng.uniform(0, 4000)
        penalty = rng.choice([0.25, 0.5, 1.0, 1.25, 2.0])
        new = quota_score(
            mode,
            messages=messages,
            messages_required=messages_required,
            voice_minutes=voice,
            voice_minutes_required=voice_required,
            penalty=penalty,
        )
        old = _old_evaluate_quota(mode, messages / messages_required, voice / voice_required, penalty)
        assert (new >= 1) is old


@pytest.mark.parametrize(
    ("mode", "messages", "messages_required", "voice", "voice_required", "expected"),
    [
        (ANY, 50, 100, 120, 240, 1.0),  # half + half
        (ANY, 0, 100, 240, 240, 1.0),
        (ALL, 100, 100, 360, 360, 1.0),
        (ALL, 0, 100, 360 * 2.25, 360, 1.0),  # skipping messages needs 6h + 125% of 6h
        (ALL, 50, 100, 180, 360, 0.5),  # both short: the lower side
        (ANY, 0, 0, 0, 240, 0.0),  # lenient: in OU a 0 requirement adds nothing
        (ALL, 0, 0, 240, 240, 1.0),  # lenient: in ET a 0 requirement is already met
        (ALL, 0, 0, 0, 0, 1.0),  # nothing required
        (ANY, 0, 0, 0, 0, 1.0),
    ],
)
def test_quota_score(
    mode: StaffQuotaMode, messages: int, messages_required: int, voice: float, voice_required: int, expected: float
) -> None:
    assert score(mode, messages, messages_required, voice, voice_required) == pytest.approx(expected)


def test_quota_score_zero_penalty_means_one_full_side_is_enough() -> None:
    kwargs = {"messages": 0, "messages_required": 100, "voice_minutes_required": 360, "penalty": 0.0}
    assert quota_score(ALL, voice_minutes=360, **kwargs) >= 1  # pyright: ignore[reportArgumentType]
    assert quota_score(ALL, voice_minutes=359, **kwargs) < 1  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [(0, "▱▱▱▱▱▱▱▱▱▱ 0%"), (1, "▰▰▰▰▰▰▰▰▰▰ 100%"), (0.5, "▰▰▰▰▰▱▱▱▱▱ 50%"), (1.5, "▰▰▰▰▰▰▰▰▰▰ 150%")],
)
def test_progress_bar(ratio: float, expected: str) -> None:
    assert progress_bar(ratio) == expected


@pytest.mark.parametrize(
    ("current", "previous", "expected"), [(0.8, 0.5, "▲ +30%"), (0.3, 0.5, "▼ -20%"), (0.5, 0.51, "▬ stable")]
)
def test_trend_arrow(current: float, previous: float, expected: str) -> None:
    assert trend_arrow(current, previous) == expected


def _quota(role_id: int) -> StaffRoleQuota:
    return StaffRoleQuota(
        guild_id=1, role_id=role_id, voice_minutes_required=60, messages_required=10, mode=StaffQuotaMode.ANY
    )


@pytest.mark.parametrize(
    ("member_roles", "override", "expected_role"),
    [
        ({99: 1}, None, None),  # no quota role
        ({10: 1}, None, 10),
        ({10: 1, 20: 5}, 10, 10),  # override wins
        ({10: 1, 20: 5}, None, 20),  # otherwise the highest role
        ({10: 7, 20: 5}, None, 10),
        ({10: 1, 20: 5}, 30, 20),  # stale override is ignored
    ],
)
def test_resolve_quota_for_member(
    member_roles: dict[int, int], override: int | None, expected_role: int | None
) -> None:
    resolved = resolve_quota_for_member(member_roles, [_quota(10), _quota(20), _quota(30)], override)
    assert (resolved.role_id if resolved else None) == expected_role


@pytest.mark.parametrize(
    ("items", "max_chars", "expected"),
    [
        (["a", "b"], 100, ["a\nb"]),
        (["aaaa", "bbbb", "cccc"], 9, ["aaaa\nbbbb", "cccc"]),
        (["x" * 20, "y"], 10, ["x" * 20, "y"]),
        ([], 10, []),
    ],
)
def test_chunk_text_lines(items: list[str], max_chars: int, expected: list[str]) -> None:
    assert chunk_text_lines(items, max_chars) == expected
