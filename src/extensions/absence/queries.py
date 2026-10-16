# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""DB queries shared between the Discord-side modal and the dashboard HTTP routes.

Create/update go through a Postgres advisory lock scoped to (guild_id, member_id) so two
concurrent writers (e.g. a Discord declaration and a dashboard API call landing at the same time)
can't both pass the overlap check before either one commits — a plain Python-side precheck alone
is vulnerable to that race, including the "member has zero rows yet" case where `select_for_update`
would have nothing to lock onto.
"""

from datetime import UTC, date, datetime
from uuid import UUID

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.transactions import in_transaction

from src.database.models import Absence, AbsenceSettings, Guild

from .logic import dates_overlap


async def get_or_create_settings(guild_id: int) -> AbsenceSettings:
    """Fetch (or create) a guild's absence settings, ensuring the `Guild` row they FK to exists."""
    await Guild.get_or_create(id=guild_id)
    settings, _ = await AbsenceSettings.get_or_create(guild_id=guild_id)
    return settings


class OverlapError(Exception):
    """Raised when a create/update would overlap an existing non-cancelled absence."""

    conflicting: Absence

    def __init__(self, conflicting: Absence) -> None:
        super().__init__(f"Overlaps with absence {conflicting.id}")
        self.conflicting = conflicting


class CancelledError(Exception):
    """Raised when trying to edit an absence that turned out to be cancelled."""


async def find_overlap(
    guild_id: int,
    member_id: int,
    start: date,
    end: date,
    *,
    exclude_id: UUID | None = None,
    using_db: BaseDBAsyncClient | None = None,
) -> Absence | None:
    """Return an existing non-cancelled absence for this member overlapping [start, end], if any."""
    query = Absence.filter(guild_id=guild_id, member_id=member_id, cancelled_at__isnull=True)
    if exclude_id is not None:
        query = query.exclude(id=exclude_id)
    if using_db is not None:
        query = query.using_db(using_db)
    for absence in await query:
        if dates_overlap(absence.start_date, absence.end_date, start, end):
            return absence
    return None


async def _lock_member(conn: BaseDBAsyncClient, guild_id: int, member_id: int) -> None:
    """Serialize concurrent writers for this member for the rest of the transaction.

    hashtextextended folds the key into a bigint server-side, so there's no risk of overflowing
    Postgres's int4 advisory-lock overload with a 64-bit Discord snowflake.
    """
    await conn.execute_query("SELECT pg_advisory_xact_lock(hashtextextended($1, 0))", [f"{guild_id}:{member_id}"])


async def create_absence(
    *, guild_id: int, member_id: int, start: date, end: date, reason: str, created_by_id: int
) -> Absence:
    """Create an absence, atomically rejecting overlaps even under concurrent writers.

    Raises:
        OverlapError: If this would overlap an existing non-cancelled absence for this member.

    """
    async with in_transaction() as conn:
        await Guild.get_or_create(id=guild_id, using_db=conn)
        await _lock_member(conn, guild_id, member_id)
        conflict = await find_overlap(guild_id, member_id, start, end, using_db=conn)
        if conflict is not None:
            raise OverlapError(conflict)
        return await Absence.create(
            guild_id=guild_id,
            member_id=member_id,
            start_date=start,
            end_date=end,
            reason=reason,
            created_by_id=created_by_id,
            using_db=conn,
        )


async def update_absence_dates(absence: Absence, *, start: date, end: date, reason: str) -> None:
    """Update an absence's dates/reason, atomically rejecting overlaps.

    Re-checks `cancelled_at` under the same lock (not just whatever the caller fetched earlier),
    so a concurrent cancellation can't be silently overwritten by a stale edit.

    Raises:
        OverlapError: If this would overlap another existing non-cancelled absence for this member.
        CancelledError: If the absence was cancelled since the caller last read it.

    """
    async with in_transaction() as conn:
        await _lock_member(conn, absence.guild_id, absence.member_id)
        await absence.refresh_from_db(using_db=conn, fields=["cancelled_at"])
        if absence.cancelled_at is not None:
            raise CancelledError
        conflict = await find_overlap(
            absence.guild_id, absence.member_id, start, end, exclude_id=absence.id, using_db=conn
        )
        if conflict is not None:
            raise OverlapError(conflict)
        absence.start_date = start
        absence.end_date = end
        absence.reason = reason
        await absence.save(using_db=conn, update_fields=["start_date", "end_date", "reason"])


async def cancel_absence(absence: Absence) -> None:
    """Cancel an absence under the same per-member lock as create/update/restore.

    Without the lock, a concurrent update/restore could commit and re-sync the public
    announcement right after this removes it, effectively undoing the cancellation.
    """
    async with in_transaction() as conn:
        await _lock_member(conn, absence.guild_id, absence.member_id)
        absence.cancelled_at = datetime.now(tz=UTC)
        await absence.save(using_db=conn, update_fields=["cancelled_at"])


async def restore_absence(absence: Absence) -> None:
    """Un-cancel an absence, atomically rejecting it if that would now overlap another one.

    Raises:
        OverlapError: If this would overlap another existing non-cancelled absence for this member.

    """
    async with in_transaction() as conn:
        await _lock_member(conn, absence.guild_id, absence.member_id)
        conflict = await find_overlap(
            absence.guild_id,
            absence.member_id,
            absence.start_date,
            absence.end_date,
            exclude_id=absence.id,
            using_db=conn,
        )
        if conflict is not None:
            raise OverlapError(conflict)
        absence.cancelled_at = None
        await absence.save(using_db=conn, update_fields=["cancelled_at"])


__all__ = (
    "CancelledError",
    "OverlapError",
    "cancel_absence",
    "create_absence",
    "find_overlap",
    "get_or_create_settings",
    "restore_absence",
    "update_absence_dates",
)
