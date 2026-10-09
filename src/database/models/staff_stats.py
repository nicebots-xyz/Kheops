# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from tortoise import fields
from tortoise.models import Model

from .guild import Guild


class StaffQuotaMode(StrEnum):
    ANY = "any"
    ALL = "all"


class StaffStatsSettings(Model):
    id: fields.Field[UUID] = fields.UUIDField(pk=True)
    guild: fields.OneToOneRelation[Guild] = fields.OneToOneField("models.Guild", related_name="staff_stats_settings")
    # Bare type-only annotation (no Field assignment): documents the shadow `guild_id` column
    # Tortoise generates for the relation above, so code can read/filter/create by it directly
    # without awaiting `.guild`, and pyright knows the attribute exists.
    guild_id: int

    responsible_role_id: fields.Field[int | None] = fields.BigIntField(null=True)  # pyright: ignore[reportAssignmentType]
    report_channel_id: fields.Field[int | None] = fields.BigIntField(null=True)  # pyright: ignore[reportAssignmentType]

    message_channel_ids: fields.Field[list[int]] = fields.JSONField(default=list)
    voice_channel_ids: fields.Field[list[int]] = fields.JSONField(default=list)

    # Applies to every role whose quota uses StaffQuotaMode.ALL: when one side (messages or
    # voice) falls short, the other side can compensate, but only at this penalty rate — e.g.
    # 1.25 means fully skipping one side requires 125% extra on the other, on top of its own
    # full requirement. See evaluate_quota() in logic.py.
    et_substitution_penalty: fields.Field[float] = fields.FloatField(default=1.25)

    last_report_sent_date: fields.Field[date | None] = fields.DateField(null=True)  # pyright: ignore[reportAssignmentType]


class StaffRoleQuota(Model):
    id: fields.Field[UUID] = fields.UUIDField(pk=True)

    guild_id: fields.Field[int] = fields.BigIntField(index=True)
    role_id: fields.Field[int] = fields.BigIntField()

    voice_minutes_required: fields.Field[int] = fields.IntField()
    messages_required: fields.Field[int] = fields.IntField()
    mode: StaffQuotaMode = fields.CharEnumField(enum_type=StaffQuotaMode)

    class Meta(Model.Meta):
        unique_together: tuple[tuple[str, ...], ...] = (("guild_id", "role_id"),)


class StaffMemberRoleOverride(Model):
    """Pins a member with several configured quota roles to the one that should apply to them.

    Without this, a member matching more than one `StaffRoleQuota` would be resolved
    arbitrarily (and counted under every matching role in the weekly report).
    """

    id: fields.Field[UUID] = fields.UUIDField(pk=True)

    guild_id: fields.Field[int] = fields.BigIntField(index=True)
    member_id: fields.Field[int] = fields.BigIntField()
    role_id: fields.Field[int] = fields.BigIntField()

    class Meta(Model.Meta):
        unique_together: tuple[tuple[str, ...], ...] = (("guild_id", "member_id"),)


class StaffMessageEvent(Model):
    id: fields.Field[UUID] = fields.UUIDField(pk=True)

    guild_id: fields.Field[int] = fields.BigIntField()
    member_id: fields.Field[int] = fields.BigIntField()
    channel_id: fields.Field[int] = fields.BigIntField()

    created_at: fields.Field[datetime] = fields.DatetimeField(auto_now_add=True)

    class Meta(Model.Meta):
        indexes: tuple[tuple[str, ...], ...] = (("guild_id", "member_id", "created_at"),)


class StaffVoiceSegment(Model):
    id: fields.Field[UUID] = fields.UUIDField(pk=True)

    guild_id: fields.Field[int] = fields.BigIntField()
    member_id: fields.Field[int] = fields.BigIntField()
    channel_id: fields.Field[int] = fields.BigIntField()

    started_at: fields.Field[datetime] = fields.DatetimeField()
    ended_at: fields.Field[datetime | None] = fields.DatetimeField(null=True)  # pyright: ignore[reportAssignmentType]

    class Meta(Model.Meta):
        indexes: tuple[tuple[str, ...], ...] = (("guild_id", "member_id", "started_at"),)


__all__ = (
    "StaffMemberRoleOverride",
    "StaffMessageEvent",
    "StaffQuotaMode",
    "StaffRoleQuota",
    "StaffStatsSettings",
    "StaffVoiceSegment",
)
