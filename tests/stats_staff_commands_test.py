# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.database.models import StaffStatsSettings
from src.extensions.stats_staff.commands import CommandsCog
from src.extensions.stats_staff.logic import EUROPE_PARIS, last_completed_week_bounds


@pytest.mark.parametrize("configuration", ["missing", "unset", "configured"])
def test_resend_last_week_uses_configured_channel(monkeypatch: pytest.MonkeyPatch, configuration: str) -> None:
    settings = (
        None
        if configuration == "missing"
        else StaffStatsSettings(guild_id=42, report_channel_id=123 if configuration == "configured" else None)
    )
    get_settings = AsyncMock(return_value=settings)
    monkeypatch.setattr(StaffStatsSettings, "get_or_none", get_settings)
    tracking = SimpleNamespace(flush=AsyncMock())
    report = SimpleNamespace(send_report=AsyncMock())
    strings = SimpleNamespace(
        report_channel_not_set="Configure a report channel.",
        report_resent="Sent to {channel}.",
    )
    cog = SimpleNamespace(tracking=tracking, report=report, t=MagicMock(return_value=strings))
    ctx = SimpleNamespace(guild=SimpleNamespace(id=42), defer=AsyncMock(), respond=AsyncMock())

    asyncio.run(CommandsCog.resend_last_week.callback(cog, ctx))  # pyright: ignore[reportArgumentType, reportUnknownArgumentType]

    get_settings.assert_awaited_once_with(guild_id=42)
    ctx.defer.assert_awaited_once_with(ephemeral=True)
    if configuration != "configured":
        tracking.flush.assert_not_awaited()
        report.send_report.assert_not_awaited()
        ctx.respond.assert_awaited_once_with("Configure a report channel.", ephemeral=True)
    else:
        tracking.flush.assert_awaited_once_with()
        report.send_report.assert_awaited_once()
        sent_settings, period, comparison = report.send_report.await_args.args
        assert sent_settings is settings
        assert (period, comparison) == last_completed_week_bounds(datetime.now(tz=EUROPE_PARIS))
        ctx.respond.assert_awaited_once_with("Sent to <#123>.", ephemeral=True)
