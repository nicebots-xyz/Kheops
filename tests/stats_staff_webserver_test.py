# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Tests for the `/stats_staff/v1/guilds/{guild_id}/config` validation logic.

There's no DB- or HTTP-level test harness in this repo yet (see `absence/webserver.py`, which
has none either), so these exercise `validate_settings_update` directly — the same pure-logic
style as `stats_staff_logic_test.py` — with fake Discord objects standing in for a real guild.
"""

from typing import cast, final

import discord
import pytest
from fastapi import HTTPException

from src.extensions.stats_staff.schemas import StaffStatsSettingsUpdateRequest
from src.extensions.stats_staff.webserver import validate_settings_update

ROLE_ID = 1
TEXT_CHANNEL_ID = 2
VOICE_CHANNEL_ID = 3
CATEGORY_ID = 4
OTHER_GUILD_ID = 99


@final
class _FakeGuild:
    def __init__(self) -> None:
        self._roles: dict[int, discord.Role] = {ROLE_ID: discord.Role.__new__(discord.Role)}
        self._channels: dict[int, object] = {
            TEXT_CHANNEL_ID: discord.TextChannel.__new__(discord.TextChannel),
            VOICE_CHANNEL_ID: discord.VoiceChannel.__new__(discord.VoiceChannel),
            CATEGORY_ID: discord.CategoryChannel.__new__(discord.CategoryChannel),
        }

    def get_role(self, role_id: int) -> discord.Role | None:
        return self._roles.get(role_id)

    def get_channel(self, channel_id: int) -> object | None:
        return self._channels.get(channel_id)


def _guild() -> discord.Guild:
    return cast("discord.Guild", cast("object", _FakeGuild()))


def _payload(
    *,
    responsible_role_id: int | None = ROLE_ID,
    report_channel_id: int | None = TEXT_CHANNEL_ID,
    message_channel_ids: list[int] | None = None,
    voice_channel_ids: list[int] | None = None,
    tracked_category_ids: list[int] | None = None,
    et_substitution_penalty: float = 1.25,
) -> StaffStatsSettingsUpdateRequest:
    return StaffStatsSettingsUpdateRequest(
        responsible_role_id=responsible_role_id,
        report_channel_id=report_channel_id,
        message_channel_ids=message_channel_ids if message_channel_ids is not None else [TEXT_CHANNEL_ID],
        voice_channel_ids=voice_channel_ids if voice_channel_ids is not None else [VOICE_CHANNEL_ID],
        tracked_category_ids=tracked_category_ids if tracked_category_ids is not None else [CATEGORY_ID],
        et_substitution_penalty=et_substitution_penalty,
    )


def test_valid_payload_passes() -> None:
    validate_settings_update(_guild(), _payload())


def test_null_role_and_channel_are_allowed() -> None:
    validate_settings_update(_guild(), _payload(responsible_role_id=None, report_channel_id=None))


def test_responsible_role_must_be_in_guild() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_settings_update(_guild(), _payload(responsible_role_id=OTHER_GUILD_ID))
    assert exc_info.value.status_code == 400
    assert "responsible_role_id" in exc_info.value.detail


def test_report_channel_must_be_a_text_channel_in_guild() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_settings_update(_guild(), _payload(report_channel_id=VOICE_CHANNEL_ID))
    assert exc_info.value.status_code == 400
    assert "report_channel_id" in exc_info.value.detail


def test_message_channel_ids_must_be_text_channels_in_guild() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_settings_update(_guild(), _payload(message_channel_ids=[VOICE_CHANNEL_ID]))
    assert "message_channel_ids" in exc_info.value.detail


def test_voice_channel_ids_must_be_voice_channels_in_guild() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_settings_update(_guild(), _payload(voice_channel_ids=[TEXT_CHANNEL_ID]))
    assert "voice_channel_ids" in exc_info.value.detail


def test_tracked_category_ids_must_be_categories_in_guild() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_settings_update(_guild(), _payload(tracked_category_ids=[TEXT_CHANNEL_ID]))
    assert "tracked_category_ids" in exc_info.value.detail


def test_et_substitution_penalty_must_be_at_least_100_percent() -> None:
    """Below 100% makes no sense for how this is actually used (125%, 130%, 127%...)."""
    with pytest.raises(HTTPException) as exc_info:
        validate_settings_update(_guild(), _payload(et_substitution_penalty=0.5))
    assert "et_substitution_penalty" in exc_info.value.detail


def test_et_substitution_penalty_of_exactly_100_percent_is_allowed() -> None:
    validate_settings_update(_guild(), _payload(et_substitution_penalty=1.0))
