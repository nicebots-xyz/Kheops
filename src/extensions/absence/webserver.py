# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""HTTP API routes for absence, exposed to the dashboard backend.

Mounted under `/absence/v1` and protected by the shared
`src.extensions.dashboard_api.auth.require_api_key` dependency — same convention as
`stats_staff`. A write here must also keep the Discord-side announcement message in sync, so the
dashboard and the bot always show the same thing (see `announce.py`).
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status

from src.database.models import Absence
from src.extensions.dashboard_api.auth import require_api_key

from .announce import remove_announcement, sync_announcement
from .logic import is_backdated
from .queries import OverlapError, create_absence, get_or_create_settings, restore_absence, update_absence_dates
from .schemas import (
    AbsenceCreateRequest,
    AbsenceResponse,
    AbsenceSettingsResponse,
    AbsenceSettingsUpdateRequest,
    AbsenceUpdateRequest,
)

if TYPE_CHECKING:
    import discord


def _to_response(absence: Absence) -> AbsenceResponse:
    return AbsenceResponse(
        id=absence.id,
        member_id=absence.member_id,
        start_date=absence.start_date,
        end_date=absence.end_date,
        reason=absence.reason,
        created_by_id=absence.created_by_id,
        cancelled=absence.cancelled_at is not None,
    )


def _conflict(e: OverlapError) -> HTTPException:
    period = f"{e.conflicting.start_date.isoformat()} -> {e.conflicting.end_date.isoformat()}"
    return HTTPException(status.HTTP_409_CONFLICT, f"Overlaps with absence {e.conflicting.id} ({period})")


def setup_webserver(app: FastAPI, bot: "discord.Client") -> None:  # noqa: PLR0915 - one router, each route is a few lines
    router = APIRouter(prefix="/absence/v1", dependencies=[Depends(require_api_key)])

    @router.get("/guilds/{guild_id}/absences")
    async def list_absences(guild_id: int, member_id: int | None = None) -> list[AbsenceResponse]:
        query = Absence.filter(guild_id=guild_id)
        if member_id is not None:
            query = query.filter(member_id=member_id)
        absences = await query.order_by("-start_date")
        return [_to_response(absence) for absence in absences]

    @router.post("/guilds/{guild_id}/absences", status_code=status.HTTP_201_CREATED)
    async def create_absence_route(guild_id: int, payload: AbsenceCreateRequest) -> AbsenceResponse:
        if payload.end_date < payload.start_date:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "end_date must not be before start_date")
        if is_backdated(payload.start_date, datetime.now(tz=UTC).date()):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "start_date must not be in the past")
        try:
            absence = await create_absence(
                guild_id=guild_id,
                member_id=payload.member_id,
                start=payload.start_date,
                end=payload.end_date,
                reason=payload.reason,
                created_by_id=payload.created_by_id,
            )
        except OverlapError as e:
            raise _conflict(e) from e
        settings = await get_or_create_settings(guild_id)
        await sync_announcement(bot, absence, settings)
        return _to_response(absence)

    @router.put("/guilds/{guild_id}/absences/{absence_id}")
    async def update_absence_route(guild_id: int, absence_id: UUID, payload: AbsenceUpdateRequest) -> AbsenceResponse:
        if payload.end_date < payload.start_date:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "end_date must not be before start_date")
        absence = await Absence.get_or_none(id=absence_id, guild_id=guild_id)
        if absence is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Absence not found")
        if absence.cancelled_at is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Absence is cancelled — restore it before editing")
        try:
            await update_absence_dates(absence, start=payload.start_date, end=payload.end_date, reason=payload.reason)
        except OverlapError as e:
            raise _conflict(e) from e
        settings = await get_or_create_settings(guild_id)
        await sync_announcement(bot, absence, settings)
        return _to_response(absence)

    @router.delete("/guilds/{guild_id}/absences/{absence_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def cancel_absence(guild_id: int, absence_id: UUID) -> None:
        absence = await Absence.get_or_none(id=absence_id, guild_id=guild_id)
        if absence is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Absence not found")
        absence.cancelled_at = datetime.now(tz=UTC)
        await absence.save(update_fields=["cancelled_at"])
        await remove_announcement(bot, absence)

    @router.post("/guilds/{guild_id}/absences/{absence_id}/restore")
    async def restore_absence_route(guild_id: int, absence_id: UUID) -> AbsenceResponse:
        absence = await Absence.get_or_none(id=absence_id, guild_id=guild_id)
        if absence is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Absence not found")
        if absence.cancelled_at is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Absence is not cancelled")
        try:
            await restore_absence(absence)
        except OverlapError as e:
            raise _conflict(e) from e
        settings = await get_or_create_settings(guild_id)
        await sync_announcement(bot, absence, settings)
        return _to_response(absence)

    @router.delete("/guilds/{guild_id}/absences/{absence_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_absence(guild_id: int, absence_id: UUID) -> None:
        """Permanently remove an absence — the "staff responsible" capability, not a regular cancel."""
        absence = await Absence.get_or_none(id=absence_id, guild_id=guild_id)
        if absence is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Absence not found")
        await remove_announcement(bot, absence)
        await absence.delete()

    @router.get("/guilds/{guild_id}/settings")
    async def get_settings(guild_id: int) -> AbsenceSettingsResponse:
        settings = await get_or_create_settings(guild_id)
        return AbsenceSettingsResponse(
            allowed_role_ids=settings.allowed_role_ids,
            announce_channel_id=settings.announce_channel_id,
            responsible_role_id=settings.responsible_role_id,
        )

    @router.put("/guilds/{guild_id}/settings")
    async def update_settings(guild_id: int, payload: AbsenceSettingsUpdateRequest) -> AbsenceSettingsResponse:
        settings = await get_or_create_settings(guild_id)
        settings.allowed_role_ids = payload.allowed_role_ids
        settings.announce_channel_id = payload.announce_channel_id
        settings.responsible_role_id = payload.responsible_role_id
        await settings.save(update_fields=["allowed_role_ids", "announce_channel_id", "responsible_role_id"])
        return AbsenceSettingsResponse(
            allowed_role_ids=settings.allowed_role_ids,
            announce_channel_id=settings.announce_channel_id,
            responsible_role_id=settings.responsible_role_id,
        )

    app.include_router(router)


__all__ = ("setup_webserver",)
