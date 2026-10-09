# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from datetime import date, datetime

from src.database.models import StaffQuotaMode
from src.extensions.stats_staff.logic import (
    EUROPE_PARIS,
    StatsPeriod,
    completion_ratio,
    et_full_substitution,
    evaluate_quota,
    overlapping_minutes,
    period_start,
    previous_week_bounds,
    progress_bar,
    should_send_weekly_report,
    trend_arrow,
    week_start,
)


def test_week_start_on_monday() -> None:
    now = datetime(2026, 3, 16, 10, 0, tzinfo=EUROPE_PARIS)  # a Monday
    assert week_start(now) == datetime(2026, 3, 16, 0, 0, tzinfo=EUROPE_PARIS)


def test_week_start_on_sunday() -> None:
    now = datetime(2026, 3, 22, 23, 0, tzinfo=EUROPE_PARIS)  # a Sunday
    assert week_start(now) == datetime(2026, 3, 16, 0, 0, tzinfo=EUROPE_PARIS)


def test_should_send_weekly_report_before_sunday() -> None:
    now = datetime(2026, 3, 21, 23, 59, tzinfo=EUROPE_PARIS)  # Saturday
    assert should_send_weekly_report(now, None) is False


def test_should_send_weekly_report_sunday_before_time() -> None:
    now = datetime(2026, 3, 22, 23, 58, tzinfo=EUROPE_PARIS)
    assert should_send_weekly_report(now, None) is False


def test_should_send_weekly_report_sunday_at_time() -> None:
    now = datetime(2026, 3, 22, 23, 59, tzinfo=EUROPE_PARIS)
    assert should_send_weekly_report(now, None) is True


def test_should_send_weekly_report_already_sent_today() -> None:
    now = datetime(2026, 3, 22, 23, 59, tzinfo=EUROPE_PARIS)
    assert should_send_weekly_report(now, date(2026, 3, 22)) is False


def test_should_send_weekly_report_retried_same_sunday() -> None:
    now = datetime(2026, 3, 22, 23, 59, tzinfo=EUROPE_PARIS)  # Sunday, after a missed earlier tick
    assert should_send_weekly_report(now, date(2026, 3, 15)) is True


def test_should_send_weekly_report_monday_after_deadline_passed() -> None:
    now = datetime(2026, 3, 23, 0, 30, tzinfo=EUROPE_PARIS)  # Monday, Sunday's window is gone
    assert should_send_weekly_report(now, date(2026, 3, 15)) is False


def test_period_start_week() -> None:
    now = datetime(2026, 3, 19, 10, 0, tzinfo=EUROPE_PARIS)  # Thursday
    assert period_start(StatsPeriod.WEEK, now) == datetime(2026, 3, 16, 0, 0, tzinfo=EUROPE_PARIS)


def test_period_start_month() -> None:
    now = datetime(2026, 3, 19, 10, 0, tzinfo=EUROPE_PARIS)
    assert period_start(StatsPeriod.MONTH, now) == datetime(2026, 3, 1, 0, 0, tzinfo=EUROPE_PARIS)


def test_period_start_last_3_months_crosses_year() -> None:
    now = datetime(2026, 2, 10, 10, 0, tzinfo=EUROPE_PARIS)
    result = period_start(StatsPeriod.LAST_3_MONTHS, now)
    assert result is not None
    assert (result.year, result.month, result.day) == (2025, 11, 10)


def test_period_start_last_6_months() -> None:
    now = datetime(2026, 3, 19, 10, 0, tzinfo=EUROPE_PARIS)
    result = period_start(StatsPeriod.LAST_6_MONTHS, now)
    assert result is not None
    assert (result.year, result.month, result.day) == (2025, 9, 19)


def test_period_start_all_time() -> None:
    now = datetime(2026, 3, 19, 10, 0, tzinfo=EUROPE_PARIS)
    assert period_start(StatsPeriod.ALL_TIME, now) is None


def test_evaluate_quota_any_passes_on_messages_only() -> None:
    assert evaluate_quota(
        StaffQuotaMode.ANY, messages=150, messages_required=100, voice_minutes=0, voice_minutes_required=240
    )


def test_evaluate_quota_any_passes_on_voice_only() -> None:
    assert evaluate_quota(
        StaffQuotaMode.ANY, messages=0, messages_required=100, voice_minutes=241, voice_minutes_required=240
    )


def test_evaluate_quota_any_fails_when_neither_met() -> None:
    assert not evaluate_quota(
        StaffQuotaMode.ANY, messages=10, messages_required=100, voice_minutes=10, voice_minutes_required=240
    )


def test_evaluate_quota_any_combines_partial_messages_and_voice() -> None:
    # half the required voice time (2h of 4h) plus half the required messages (50 of 100)
    assert evaluate_quota(
        StaffQuotaMode.ANY, messages=50, messages_required=100, voice_minutes=120, voice_minutes_required=240
    )


def test_evaluate_quota_any_combined_still_fails_below_100_percent() -> None:
    # a third of each: nowhere near enough combined
    assert not evaluate_quota(
        StaffQuotaMode.ANY, messages=30, messages_required=100, voice_minutes=60, voice_minutes_required=240
    )


def test_evaluate_quota_all_requires_both() -> None:
    assert not evaluate_quota(
        StaffQuotaMode.ALL, messages=150, messages_required=100, voice_minutes=10, voice_minutes_required=240
    )
    assert evaluate_quota(
        StaffQuotaMode.ALL, messages=150, messages_required=100, voice_minutes=241, voice_minutes_required=240
    )


def test_evaluate_quota_all_fails_when_both_fall_short() -> None:
    assert not evaluate_quota(
        StaffQuotaMode.ALL, messages=10, messages_required=100, voice_minutes=10, voice_minutes_required=240
    )


def test_evaluate_quota_all_zero_messages_needs_full_penalty_in_voice() -> None:
    # 6h required, skipping messages entirely needs 6h + 125% * 6h = 13.5h
    assert not evaluate_quota(
        StaffQuotaMode.ALL, messages=0, messages_required=100, voice_minutes=13 * 60, voice_minutes_required=6 * 60
    )
    assert evaluate_quota(
        StaffQuotaMode.ALL,
        messages=0,
        messages_required=100,
        voice_minutes=13.5 * 60,
        voice_minutes_required=6 * 60,
    )


def test_evaluate_quota_all_partial_shortfall_compensated_proportionally() -> None:
    # half the required voice (3h of 6h) -> deficit 0.5 -> needs messages_ratio >= 1 + 1.25*0.5 = 1.625
    assert not evaluate_quota(
        StaffQuotaMode.ALL, messages=162, messages_required=100, voice_minutes=3 * 60, voice_minutes_required=6 * 60
    )
    assert evaluate_quota(
        StaffQuotaMode.ALL, messages=163, messages_required=100, voice_minutes=3 * 60, voice_minutes_required=6 * 60
    )


def test_evaluate_quota_all_penalty_is_configurable() -> None:
    # with no penalty at all (1.0x), making up half a deficit on one side only needs equal excess
    assert evaluate_quota(
        StaffQuotaMode.ALL,
        messages=150,
        messages_required=100,
        voice_minutes=3 * 60,
        voice_minutes_required=6 * 60,
        et_penalty=1.0,
    )


def test_overlapping_minutes_closed_segment_fully_inside_range() -> None:
    started = datetime(2026, 3, 16, 10, 0, tzinfo=EUROPE_PARIS)
    ended = datetime(2026, 3, 16, 10, 30, tzinfo=EUROPE_PARIS)
    range_start = datetime(2026, 3, 16, 0, 0, tzinfo=EUROPE_PARIS)
    range_end = datetime(2026, 3, 23, 0, 0, tzinfo=EUROPE_PARIS)
    assert overlapping_minutes(started, ended, range_start, range_end) == 30


def test_overlapping_minutes_open_segment_clamped_to_range_end() -> None:
    started = datetime(2026, 3, 16, 23, 45, tzinfo=EUROPE_PARIS)
    range_start = datetime(2026, 3, 16, 0, 0, tzinfo=EUROPE_PARIS)
    range_end = datetime(2026, 3, 17, 0, 0, tzinfo=EUROPE_PARIS)
    assert overlapping_minutes(started, None, range_start, range_end) == 15


def test_overlapping_minutes_segment_before_range_is_zero() -> None:
    started = datetime(2026, 3, 1, 10, 0, tzinfo=EUROPE_PARIS)
    ended = datetime(2026, 3, 1, 10, 30, tzinfo=EUROPE_PARIS)
    range_start = datetime(2026, 3, 16, 0, 0, tzinfo=EUROPE_PARIS)
    range_end = datetime(2026, 3, 23, 0, 0, tzinfo=EUROPE_PARIS)
    assert overlapping_minutes(started, ended, range_start, range_end) == 0


def test_overlapping_minutes_no_lower_bound() -> None:
    started = datetime(2020, 1, 1, 0, 0, tzinfo=EUROPE_PARIS)
    ended = datetime(2020, 1, 1, 1, 0, tzinfo=EUROPE_PARIS)
    range_end = datetime(2026, 3, 23, 0, 0, tzinfo=EUROPE_PARIS)
    assert overlapping_minutes(started, ended, None, range_end) == 60


def test_completion_ratio_any_sums_both_ratios() -> None:
    ratio = completion_ratio(
        StaffQuotaMode.ANY, messages=50, messages_required=100, voice_minutes=120, voice_minutes_required=240
    )
    assert ratio == 1.0


def test_completion_ratio_all_averages_both_ratios() -> None:
    ratio = completion_ratio(
        StaffQuotaMode.ALL, messages=100, messages_required=100, voice_minutes=0, voice_minutes_required=240
    )
    assert ratio == 0.5


def test_progress_bar_zero() -> None:
    assert progress_bar(0.0, width=10) == "▱▱▱▱▱▱▱▱▱▱ 0%"


def test_progress_bar_full() -> None:
    assert progress_bar(1.0, width=10) == "▰▰▰▰▰▰▰▰▰▰ 100%"


def test_progress_bar_half() -> None:
    assert progress_bar(0.5, width=10) == "▰▰▰▰▰▱▱▱▱▱ 50%"


def test_progress_bar_clamps_over_100_percent() -> None:
    assert progress_bar(1.5, width=10) == "▰▰▰▰▰▰▰▰▰▰ 150%"


def test_trend_arrow_up() -> None:
    assert trend_arrow(0.8, 0.5) == "▲ +30%"


def test_trend_arrow_down() -> None:
    assert trend_arrow(0.3, 0.6) == "▼ -30%"


def test_trend_arrow_stable_within_threshold() -> None:
    assert trend_arrow(0.51, 0.50) == "▬ stable"


def test_previous_week_bounds_mid_week() -> None:
    now = datetime(2026, 3, 17, 14, 0, tzinfo=EUROPE_PARIS)  # Tuesday 14:00
    start, end = previous_week_bounds(now)
    assert start == datetime(2026, 3, 9, 0, 0, tzinfo=EUROPE_PARIS)  # last Monday 00:00
    assert end == datetime(2026, 3, 10, 14, 0, tzinfo=EUROPE_PARIS)  # last Tuesday 14:00


def test_previous_week_bounds_end_of_week_matches_full_week() -> None:
    now = datetime(2026, 3, 22, 23, 59, tzinfo=EUROPE_PARIS)  # Sunday, just before the report fires
    start, end = previous_week_bounds(now)
    assert start == datetime(2026, 3, 9, 0, 0, tzinfo=EUROPE_PARIS)
    assert end == datetime(2026, 3, 15, 23, 59, tzinfo=EUROPE_PARIS)


def test_et_full_substitution_default_penalty() -> None:
    assert et_full_substitution(6, 1.25) == 13.5


def test_et_full_substitution_no_penalty() -> None:
    assert et_full_substitution(100, 0.0) == 100
