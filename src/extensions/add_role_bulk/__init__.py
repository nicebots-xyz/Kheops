# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
import discord

from src import custom

default = {
    "enabled": True,
}


class AddRoleBulkCog(discord.Cog):
    def __init__(self, bot: custom.Bot) -> None:
        self.bot: custom.Bot = bot

    @discord.slash_command(
        name="add_role_bulk",
        default_member_permissions=discord.Permissions(administrator=True),
        contexts={discord.InteractionContextType.guild},
    )
    async def add_role_bulk(
        self,
        ctx: custom.ApplicationContext,
        role: discord.Role,
        users: discord.Attachment,
    ) -> None:
        if ctx.guild is None:
            return

        await ctx.defer(ephemeral=True)

        bt = await users.read()
        user_ids: set[int] = {int(line.strip()) for line in bt.decode("utf-8").splitlines() if line.strip().isdigit()}

        if not user_ids:
            await ctx.respond(ctx.translations.no_valid_user_ids, ephemeral=True)
            return

        added_count = 0
        for user_id in user_ids:
            member = await ctx.guild.get_or_fetch(discord.Member, user_id)
            if member is not None:
                try:
                    await member.add_roles(role, reason=f"Bulk role addition by {ctx.author}")
                    added_count += 1
                except discord.Forbidden:
                    pass  # Skip members we can't modify

        await ctx.respond(ctx.translations.role_added_bulk.format(count=added_count), ephemeral=True)

    @discord.slash_command(
        name="add_role_sync",
        default_member_permissions=discord.Permissions(administrator=True),
        contexts={discord.InteractionContextType.guild},
    )
    async def add_role_sync(
        self,
        ctx: custom.ApplicationContext,
        source: discord.Role,
        target: discord.Role,
    ) -> None:
        if ctx.guild is None:
            return

        await ctx.defer(ephemeral=True)

        source_members = set(source.members)
        already_members = set(target.members)

        failures: int = 0
        for member in source_members - already_members:
            try:
                await member.add_roles(target, reason=f"Syncing role {target} with {source} by {ctx.author}")
            except discord.Forbidden:
                failures += 1

        await ctx.respond(
            ctx.translations.role_synced.format(source=source.name, target=target.name, failures=failures),
            ephemeral=True,
        )


def setup(bot: custom.Bot) -> None:
    bot.add_cog(AddRoleBulkCog(bot=bot))
