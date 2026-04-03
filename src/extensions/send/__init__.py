# Copyright Communauté Les Frères Poulain 2025, 2026
# SPDX-License-Identifier: MIT

from typing import final, override

import discord

from src import custom

default: dict[str, bool] = {"enabled": True}


@final
class SendModal(discord.ui.DesignerModal):
    def __init__(self) -> None:
        super().__init__(title="Envoyer un message")
        self.input = discord.ui.TextInput(max_length=4000)

        self.add_item(discord.ui.Label(label="Message", description="Le message à envoyer", item=self.input))

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        if self.input.value is None:
            await interaction.respond("Vous devez entrer un message !", ephemeral=True)
            return
        if not interaction.channel:
            await interaction.respond("Impossible d'envoyer le message : le canal est introuvable.", ephemeral=True)
            return
        await interaction.channel.send(view=discord.ui.DesignerView(discord.ui.TextDisplay(content=self.input.value)))
        await interaction.respond("Message envoyé !", ephemeral=True)


class SendCog(discord.Cog):
    @discord.slash_command(default_member_permissions=discord.Permissions(administrator=True))
    async def send(self, ctx: custom.ApplicationContext) -> None:
        await ctx.send_modal(SendModal())


def setup(bot: custom.Bot) -> None:
    bot.add_cog(SendCog())
