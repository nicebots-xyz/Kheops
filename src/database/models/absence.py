# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from datetime import date, datetime
from uuid import UUID

from tortoise import fields
from tortoise.models import Model

REASON_MAX_LENGTH = 500


class AbsenceSettings(Model):
    guild_id: fields.Field[int] = fields.BigIntField(pk=True)

    allowed_role_ids: fields.Field[list[int]] = fields.JSONField(default=list)
    announce_channel_id: fields.Field[int | None] = fields.BigIntField(null=True)  # pyright: ignore[reportAssignmentType]

    # Can permanently delete any absence, on top of the admin-always-can baseline.
    responsible_role_id: fields.Field[int | None] = fields.BigIntField(null=True)  # pyright: ignore[reportAssignmentType]


class Absence(Model):
    id: fields.Field[UUID] = fields.UUIDField(pk=True)

    guild_id: fields.Field[int] = fields.BigIntField(index=True)
    member_id: fields.Field[int] = fields.BigIntField()

    start_date: fields.Field[date] = fields.DateField()
    end_date: fields.Field[date] = fields.DateField()
    reason: fields.Field[str] = fields.CharField(max_length=REASON_MAX_LENGTH, default="")

    # Self-declared, or the admin who declared it on the member's behalf.
    created_by_id: fields.Field[int] = fields.BigIntField()

    # The public announcement message (name + dates only), kept in sync on edit/cancel.
    announce_channel_id: fields.Field[int | None] = fields.BigIntField(null=True)  # pyright: ignore[reportAssignmentType]
    announce_message_id: fields.Field[int | None] = fields.BigIntField(null=True)  # pyright: ignore[reportAssignmentType]

    # Set on cancellation; the row is kept for history rather than deleted.
    cancelled_at: fields.Field[datetime | None] = fields.DatetimeField(null=True)  # pyright: ignore[reportAssignmentType]

    created_at: fields.Field[datetime] = fields.DatetimeField(auto_now_add=True)
    updated_at: fields.Field[datetime] = fields.DatetimeField(auto_now=True)

    class Meta(Model.Meta):
        indexes: tuple[tuple[str, ...], ...] = (("guild_id", "member_id"),)


__all__ = ("REASON_MAX_LENGTH", "Absence", "AbsenceSettings")
