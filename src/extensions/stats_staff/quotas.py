# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from typing import TYPE_CHECKING

from src.database.models import StaffMemberRoleOverride, StaffRoleQuota

from .logic import resolve_quota_for_member

if TYPE_CHECKING:
    from uuid import UUID

    import discord


def role_positions(member: discord.Member) -> dict[int, int]:
    return {role.id: role.position for role in member.roles}


async def find_quota(member: discord.Member) -> StaffRoleQuota | None:
    quotas = await StaffRoleQuota.filter(guild_id=member.guild.id)
    override = await StaffMemberRoleOverride.get_or_none(guild_id=member.guild.id, member_id=member.id)
    return resolve_quota_for_member(role_positions(member), quotas, override.role_id if override else None)


async def members_by_quota(guild: discord.Guild, quotas: list[StaffRoleQuota]) -> dict[UUID, list[discord.Member]]:
    """Group every staff member under the single quota that applies to them."""
    overrides = dict(await StaffMemberRoleOverride.filter(guild_id=guild.id).values_list("member_id", "role_id"))
    quota_role_ids = {quota.role_id for quota in quotas}
    grouped: dict[UUID, list[discord.Member]] = {}
    for member in guild.members:
        if member.bot or not any(role.id in quota_role_ids for role in member.roles):
            continue
        quota = resolve_quota_for_member(role_positions(member), quotas, overrides.get(member.id))
        if quota is not None:
            grouped.setdefault(quota.id, []).append(member)
    return grouped


__all__ = ("find_quota", "members_by_quota", "role_positions")
