# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from typing import TYPE_CHECKING

from src.database.models import StaffMemberRoleOverride, StaffRoleQuota

from .logic import resolve_quota_for_member

if TYPE_CHECKING:
    from uuid import UUID

    import discord


async def find_quota_role(member: discord.Member) -> StaffRoleQuota | None:
    quotas = await StaffRoleQuota.filter(guild_id=member.guild.id)
    override = await StaffMemberRoleOverride.get_or_none(guild_id=member.guild.id, member_id=member.id)
    member_role_ids = {role.id for role in member.roles}
    return resolve_quota_for_member(member_role_ids, quotas, override.role_id if override else None)


async def resolve_members_by_quota(
    guild: discord.Guild, quotas: list[StaffRoleQuota]
) -> dict[UUID, list[discord.Member]]:
    """Group every staff member under the single quota that applies to them.

    A member matching more than one configured role is resolved via their
    `StaffMemberRoleOverride` if set, so they are never counted under more than one role.
    Fetches every role override once up front instead of once per member.
    """
    overrides = await StaffMemberRoleOverride.filter(guild_id=guild.id)
    overrides_by_member_id = {override.member_id: override.role_id for override in overrides}

    members_by_quota_id: dict[UUID, list[discord.Member]] = {}
    seen_member_ids: set[int] = set()
    for quota in quotas:
        role = guild.get_role(quota.role_id)
        if role is None:
            continue
        for member in role.members:
            if member.bot or member.id in seen_member_ids:
                continue
            seen_member_ids.add(member.id)
            member_role_ids = {r.id for r in member.roles}
            resolved = resolve_quota_for_member(member_role_ids, quotas, overrides_by_member_id.get(member.id))
            if resolved is not None:
                members_by_quota_id.setdefault(resolved.id, []).append(member)
    return members_by_quota_id


__all__ = ("find_quota_role", "resolve_members_by_quota")
