# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from datetime import UTC, datetime, timedelta

from src.extensions.stats_staff.tracking import PendingMessage, VoiceTracker

T0 = datetime(2026, 10, 5, 20, 0, tzinfo=UTC)
GUILD, MEMBER = 1, 7


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def test_continuous_session_keeps_its_id_across_flushes() -> None:
    tracker = VoiceTracker()
    tracker.sync(GUILD, MEMBER, 100, at(0))
    _, first, _ = tracker.take(at(120))
    tracker.sync(GUILD, MEMBER, 100, at(130))  # nothing changed
    _, second, _ = tracker.take(at(240))
    assert first[0].id == second[0].id
    assert (first[0].ended_at, second[0].ended_at) == (at(120), at(240))


def test_any_gap_or_channel_switch_starts_a_new_session() -> None:
    tracker = VoiceTracker()
    tracker.sync(GUILD, MEMBER, 100, at(0))
    tracker.sync(GUILD, MEMBER, None, at(10))  # muted for one second
    tracker.sync(GUILD, MEMBER, 100, at(11))
    tracker.sync(GUILD, MEMBER, 200, at(20))  # switched channel
    finished, ongoing, _ = tracker.take(at(30))
    rows = [(s.channel_id, s.started_at, s.ended_at) for s in (*finished, *ongoing)]
    assert rows == [(100, at(0), at(10)), (100, at(11), at(20)), (200, at(20), at(30))]
    assert len({s.id for s in (*finished, *ongoing)}) == 3


def test_take_forgets_finished_sessions_and_messages() -> None:
    tracker = VoiceTracker()
    tracker.sync(GUILD, MEMBER, 100, at(0))
    tracker.sync(GUILD, MEMBER, None, at(10))
    tracker.messages.append(PendingMessage(GUILD, MEMBER, 300, at(5)))
    finished, ongoing, messages = tracker.take(at(20))
    assert (len(finished), len(ongoing), len(messages)) == (1, 0, 1)
    assert tracker.take(at(30)) == ([], [], [])


def test_restore_after_a_failed_write_loses_nothing() -> None:
    tracker = VoiceTracker()
    tracker.sync(GUILD, MEMBER, 100, at(0))
    tracker.sync(GUILD, MEMBER, None, at(10))
    tracker.messages.append(PendingMessage(GUILD, MEMBER, 300, at(5)))
    finished, _, messages = tracker.take(at(20))
    tracker.messages.append(PendingMessage(GUILD, MEMBER, 300, at(25)))  # arrived during the failed write
    tracker.restore(finished, messages)
    finished_again, _, messages_again = tracker.take(at(30))
    assert finished_again == finished
    assert [m.created_at for m in messages_again] == [at(5), at(25)]


def test_open_session_snapshot_does_not_close_the_live_session() -> None:
    tracker = VoiceTracker()
    tracker.sync(GUILD, MEMBER, 100, at(0))
    tracker.take(at(60))
    assert tracker.open[GUILD, MEMBER].ended_at is None
