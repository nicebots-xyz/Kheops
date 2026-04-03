# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

import io
from pathlib import Path
from typing import Never

import aiofile
import discord
from discord.components import MediaGalleryItem
from discord.ui import DesignerView, MediaGallery, Separator, TextDisplay, ViewItem

from src import custom

default: dict[str, bool] = {"enabled": True}


class SendCog(discord.Cog):
    async def get_networks_image(self) -> discord.File:
        async with aiofile.AIOFile(Path(__file__).parent / "assets" / "networks.png", "rb") as file:
            return discord.File(io.BytesIO(await file.read()), filename="networks.png")  # pyright: ignore[reportArgumentType]

    async def build_message(
        self,
        ctx: custom.ApplicationContext,
        *,
        main: bool = True,
        networks: bool = True,
        tipeee_text: bool = True,
        level_roles: bool = True,
        vc_roles: bool = True,
        recruiting: bool = True,
        recruiting_num_mods: int = 5,
        recruiting_num_anim: int = 2,
        recruiting_num_happymanager: int = 3,
    ) -> tuple[list[discord.ui.ViewItem[discord.ui.DesignerView]], list[discord.File]]:
        blocks: list[list[ViewItem[DesignerView]]] = []
        files: list[discord.File] = []

        if main:
            blocks.append([TextDisplay[DesignerView, Never](ctx.translations.main_text)])

        if networks:
            networks_file = await self.get_networks_image()
            files.append(networks_file)
            blocks.append(
                [
                    TextDisplay[DesignerView, Never](ctx.translations.networks_heading),
                    MediaGallery[DesignerView](MediaGalleryItem(f"attachment://{networks_file.filename}")),
                    TextDisplay[DesignerView, Never](ctx.translations.networks_text),
                ]
            )

        if tipeee_text:
            blocks.append([TextDisplay[DesignerView, Never](ctx.translations.tipeee_text)])

        if level_roles:
            blocks.append([TextDisplay[DesignerView, Never](ctx.translations.leveled_roles_text)])

        if vc_roles:
            blocks.append([TextDisplay[DesignerView, Never](ctx.translations.activity_roles_voice)])

        if recruiting:
            blocks.append(
                [
                    TextDisplay[DesignerView, Never](
                        ctx.translations.recruiting_text.format(
                            mods=recruiting_num_mods, anim=recruiting_num_anim, happymanager=recruiting_num_happymanager
                        )
                    )
                ]
            )

        for i, block in enumerate(blocks):
            if i != len(blocks) - 1:
                block.append(Separator[DesignerView](divider=True, spacing=discord.SeparatorSpacingSize.large))

        return [block for sublist in blocks for block in sublist], files

    @discord.slash_command(default_member_permissions=discord.Permissions(administrator=True))
    async def informations_send(
        self,
        ctx: custom.ApplicationContext,
        main: bool = True,
        networks: bool = True,
        tipeee_text: bool = True,
        level_roles: bool = True,
        vc_roles: bool = True,
        recruiting: bool = True,
        recruiting_num_mods: int = 5,
        recruiting_num_anim: int = 2,
        recruiting_num_happymanager: int = 3,
    ) -> None:
        components, files = await self.build_message(
            ctx,
            main=main,
            networks=networks,
            tipeee_text=tipeee_text,
            level_roles=level_roles,
            vc_roles=vc_roles,
            recruiting=recruiting,
            recruiting_num_mods=recruiting_num_mods,
            recruiting_num_anim=recruiting_num_anim,
            recruiting_num_happymanager=recruiting_num_happymanager,
        )

        await ctx.channel.send(
            view=discord.ui.DesignerView(*components),
            files=files,
            allowed_mentions=discord.AllowedMentions.none(),
        )

        await ctx.respond(
            ctx.translations.message_sent,
            ephemeral=True,
        )


def setup(bot: custom.Bot) -> None:
    bot.add_cog(SendCog())
