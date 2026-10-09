# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""HTTP API routes for stats_staff, exposed to the dashboard backend.

Mounted under `/stats_staff/v1` and protected by the shared
`src.extensions.dashboard_api.auth.require_api_key` dependency. No route here assumes a Discord
interaction context (there isn't one over HTTP): the permission checks commands.py does via
`ctx.author` don't apply — authorization is the bearer API key only, checked once per request by
the router-level dependency below.
"""

from __future__ import annotations

from datetime import date, datetime

import discord
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status

from src.database.models import StaffRoleQuota
from src.extensions.dashboard_api.auth import require_api_key

from .logic import EUROPE_PARIS, StatsPeriod, period_start
from .schemas import (
    DailyHistoryEntry,
    MemberHistoryResponse,
    MemberStatsResponse,
    QuotaResponse,
    QuotaUpsertRequest,
)
from .stats import compute_daily_history, compute_stats_range

MAX_HISTORY_DAYS = 366


def setup_webserver(app: FastAPI, bot: discord.Bot) -> None:
    router = APIRouter(prefix="/stats_staff/v1", dependencies=[Depends(require_api_key)])

    @router.get("/guilds/{guild_id}/members/{member_id}/stats", response_model=MemberStatsResponse)
    async def get_member_stats(
        guild_id: int, member_id: int, period: StatsPeriod = StatsPeriod.WEEK
    ) -> MemberStatsResponse:
        now = datetime.now(tz=EUROPE_PARIS)
        start = period_start(period, now)
        messages, voice_minutes = await compute_stats_range(guild_id, member_id, start, now)
        return MemberStatsResponse(member_id=member_id, period=period, messages=messages, voice_minutes=voice_minutes)

    @router.get("/guilds/{guild_id}/members/{member_id}/history", response_model=MemberHistoryResponse)
    async def get_member_history(guild_id: int, member_id: int, start: date, end: date) -> MemberHistoryResponse:
        if end < start:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "end must not be before start")
        if (end - start).days + 1 > MAX_HISTORY_DAYS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"range too wide (max {MAX_HISTORY_DAYS} days)")
        days = await compute_daily_history(guild_id, member_id, start, end)
        return MemberHistoryResponse(
            member_id=member_id,
            start=start,
            end=end,
            days=[
                DailyHistoryEntry(day=day, messages=messages, voice_minutes=voice_minutes)
                for day, messages, voice_minutes in days
            ],
        )

    @router.get("/guilds/{guild_id}/quotas", response_model=list[QuotaResponse])
    async def list_quotas(guild_id: int) -> list[QuotaResponse]:
        quotas = await StaffRoleQuota.filter(guild_id=guild_id)
        return [QuotaResponse.model_validate(quota, from_attributes=True) for quota in quotas]

    @router.put("/guilds/{guild_id}/quotas/{role_id}", response_model=QuotaResponse)
    async def upsert_quota(guild_id: int, role_id: int, payload: QuotaUpsertRequest) -> QuotaResponse:
        guild = bot.get_guild(guild_id)
        if guild is None or guild.get_role(role_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found in this guild")
        quota, _ = await StaffRoleQuota.update_or_create(
            guild_id=guild_id,
            role_id=role_id,
            defaults={
                "voice_minutes_required": payload.voice_minutes_required,
                "messages_required": payload.messages_required,
                "mode": payload.mode,
            },
        )
        return QuotaResponse.model_validate(quota, from_attributes=True)

    @router.delete("/guilds/{guild_id}/quotas/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_quota(guild_id: int, role_id: int) -> None:
        deleted = await StaffRoleQuota.filter(guild_id=guild_id, role_id=role_id).delete()
        if not deleted:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Quota not found")

    app.include_router(router)


__all__ = ("setup_webserver",)
