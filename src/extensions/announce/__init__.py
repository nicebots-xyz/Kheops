# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from os.path import splitext
from typing import Never, final, override

import discord
from discord import InputTextStyle, Interaction, MediaGalleryItem
from discord.ui import (
    DesignerModal,
    DesignerView,
    FileUpload,
    MediaGallery,
    RoleSelect,
    TextDisplay,
    TextInput,
    ViewItem,
)
from discord.ui.label import Label

from src import custom
from src.i18n.classes import RawTranslation, TranslationWrapper

default: dict[str, bool] = {"enabled": True}


@final
class AnnounceModal(DesignerModal):
    @override
    def __init__(self, bot: custom.Bot, translations: TranslationWrapper[dict[str, RawTranslation]]) -> None:
        self.translations = translations
        self.bot = bot
        super().__init__(title=self.translations.modal_title)

        self.role_select = RoleSelect(min_values=0, max_values=10, required=False)
        self.add_item(Label(label=self.translations.roles_to_mention, item=self.role_select))

        self.title_input = TextInput(required=True, style=InputTextStyle.short, max_length=256)
        self.add_item(Label(label=self.translations.announcement_title, item=self.title_input))

        self.content_input = TextInput(required=True, style=InputTextStyle.paragraph, max_length=2048)
        self.add_item(Label(label=self.translations.announcement_content, item=self.content_input))

        self.footer_input = TextInput(required=False, style=InputTextStyle.short, max_length=512)
        self.add_item(Label(label=self.translations.announcement_footer, item=self.footer_input))

        self.image_upload = FileUpload(
            required=False,
        )
        self.add_item(Label(label=self.translations.announcement_image, item=self.image_upload))

    @override
    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        if interaction.channel is None:
            return

        components: list[ViewItem[DesignerView]] = []

        if self.role_select.values is not None:
            components.append(
                TextDisplay[DesignerView, Never](" ".join(role.mention for role in self.role_select.values))
            )

        if self.title_input.value:
            components.append(TextDisplay[DesignerView, Never](f"# {self.title_input.value}"))

        if self.image_upload.values:
            image: discord.File | None = await self.image_upload.values[0].to_file()
            if image.filename is None:
                return
            image.filename = f"image.{splitext(image.filename)[1]}"
            components.append(MediaGallery[DesignerView](MediaGalleryItem(f"attachment://{image.filename}")))
        else:
            image = None

        if self.content_input.value:
            components.append(TextDisplay[DesignerView, Never](self.content_input.value))

        if self.footer_input.value:
            components.append(TextDisplay[DesignerView, Never](f"-# {self.footer_input.value}"))

        components.append(
            TextDisplay[DesignerView, Never](self.translations.announcement_signature.format(author=interaction.user))
        )
        await interaction.channel.send(view=DesignerView(*components), files=[image] if image is not None else [])  # pyright: ignore[reportAttributeAccessIssue]


@final
class AnnounceCog(discord.Cog):
    def __init__(self, bot: custom.Bot) -> None:
        self.bot = bot
        super().__init__()

    @discord.slash_command(default_member_permissions=discord.Permissions(administrator=True))
    async def announce(self, ctx: custom.ApplicationContext) -> None:
        if ctx.channel is None:
            return
        await ctx.send_modal(AnnounceModal(self.bot, ctx.translations))


def setup(bot: custom.Bot) -> None:
    bot.add_cog(AnnounceCog(bot))
