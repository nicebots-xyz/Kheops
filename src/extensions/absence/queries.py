# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

"""Small DB queries shared between the Discord-side modal and the dashboard HTTP routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.database.models import Absence

from .logic import dates_overlap

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID


async def find_overlap(
    guild_id: int, member_id: int, start: date, end: date, *, exclude_id: UUID | None = None
) -> Absence | None:
    """Return an existing non-cancelled absence for this member overlapping [start, end], if any."""
    query = Absence.filter(guild_id=guild_id, member_id=member_id, cancelled_at__isnull=True)
    if exclude_id is not None:
        query = query.exclude(id=exclude_id)
    for absence in await query:
        if dates_overlap(absence.start_date, absence.end_date, start, end):
            return absence
    return None


__all__ = ("find_overlap",)
