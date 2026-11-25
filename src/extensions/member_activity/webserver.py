# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""HTTP API routes for member_activity, exposed to the dashboard backend.

Mounted under `/member_activity/v1` and protected by the shared
`src.extensions.dashboard_api.auth.require_api_key` dependency — same pattern as stats_staff's
webserver.py. No route here assumes a Discord interaction context: authorization is the bearer
API key only, checked once per request by the router-level dependency below.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

import discord
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status

from src.extensions.dashboard_api.auth import require_api_key

from .logic import EUROPE_PARIS, StatsPeriod, period_start
from .schemas import (
    DailyHistoryEntry,
    MemberActivitySettingsResponse,
    MemberActivitySettingsUpdateRequest,
    MemberHistoryResponse,
    MemberStatsResponse,
)
from .stats import get_daily_history, get_or_create_settings, get_stats, update_settings
from .tracking import TrackingCog

if TYPE_CHECKING:
    from src.database.models import MemberActivitySettings

MAX_HISTORY_DAYS = 366


def _settings_response(settings: MemberActivitySettings) -> MemberActivitySettingsResponse:
    return MemberActivitySettingsResponse(
        message_channel_ids=settings.message_channel_ids,
        voice_channel_ids=settings.voice_channel_ids,
        tracked_category_ids=settings.tracked_category_ids,
    )


def validate_settings_update(guild: discord.Guild, payload: MemberActivitySettingsUpdateRequest) -> None:
    """Check a settings update against the real guild, raising HTTPException(400) on the first bad field."""
    bad_message = [c for c in payload.message_channel_ids if not isinstance(guild.get_channel(c), discord.TextChannel)]
    if bad_message:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"message_channel_ids not text channels in this guild: {bad_message}"
        )
    bad_voice = [c for c in payload.voice_channel_ids if not isinstance(guild.get_channel(c), discord.VoiceChannel)]
    if bad_voice:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"voice_channel_ids not voice channels in this guild: {bad_voice}"
        )
    bad_category = [
        c for c in payload.tracked_category_ids if not isinstance(guild.get_channel(c), discord.CategoryChannel)
    ]
    if bad_category:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"tracked_category_ids not categories in this guild: {bad_category}"
        )


def _tracking(bot: discord.Bot) -> TrackingCog | None:
    cog = bot.get_cog(TrackingCog.__name__)
    return cog if isinstance(cog, TrackingCog) else None


async def _flush(bot: discord.Bot) -> None:
    """Write the last ~2 minutes of activity still held in memory, so reads are up to date."""
    if (cog := _tracking(bot)) is not None:
        await cog.flush()


async def _config_changed(bot: discord.Bot, guild_id: int) -> None:
    """Let voice/message tracking pick up a config change right away."""
    if (cog := _tracking(bot)) is not None:
        await cog.reload_config(guild_id)


def setup_webserver(app: FastAPI, bot: discord.Bot) -> None:
    router = APIRouter(prefix="/member_activity/v1", dependencies=[Depends(require_api_key)])

    @router.get("/guilds/{guild_id}/members/{member_id}/stats", response_model=MemberStatsResponse)
    async def get_member_stats(
        guild_id: int, member_id: int, period: StatsPeriod = StatsPeriod.WEEK
    ) -> MemberStatsResponse:
        await _flush(bot)
        now = datetime.now(tz=EUROPE_PARIS)
        stats = await get_stats(guild_id, period_start(period, now), now)
        messages, voice_minutes = stats.get(member_id, (0, 0.0))
        return MemberStatsResponse(member_id=member_id, period=period, messages=messages, voice_minutes=voice_minutes)

    @router.get("/guilds/{guild_id}/members/{member_id}/history", response_model=MemberHistoryResponse)
    async def get_member_history(guild_id: int, member_id: int, start: date, end: date) -> MemberHistoryResponse:
        if end < start:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "end must not be before start")
        if (end - start).days + 1 > MAX_HISTORY_DAYS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"range too wide (max {MAX_HISTORY_DAYS} days)")
        await _flush(bot)
        days = await get_daily_history(guild_id, member_id, start, end)
        return MemberHistoryResponse(
            member_id=member_id,
            start=start,
            end=end,
            days=[
                DailyHistoryEntry(day=day, messages=messages, voice_minutes=voice_minutes)
                for day, messages, voice_minutes in days
            ],
        )

    @router.get("/guilds/{guild_id}/config", response_model=MemberActivitySettingsResponse)
    async def get_config(guild_id: int) -> MemberActivitySettingsResponse:
        return _settings_response(await get_or_create_settings(guild_id))

    @router.put("/guilds/{guild_id}/config", response_model=MemberActivitySettingsResponse)
    async def update_config(
        guild_id: int, payload: MemberActivitySettingsUpdateRequest
    ) -> MemberActivitySettingsResponse:
        guild = bot.get_guild(guild_id)
        if guild is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Guild not found")
        validate_settings_update(guild, payload)

        settings = await update_settings(
            guild_id,
            message_channel_ids=payload.message_channel_ids,
            voice_channel_ids=payload.voice_channel_ids,
            tracked_category_ids=payload.tracked_category_ids,
        )
        await _config_changed(bot, guild_id)
        return _settings_response(settings)

    app.include_router(router)


__all__ = ("setup_webserver",)
