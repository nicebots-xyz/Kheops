# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from datetime import UTC, datetime
from enum import StrEnum
from typing import final, override

import discord
from discord.ext import tasks
from discord.ui import CheckboxGroup, Container, DesignerView, Label, StringSelect, TextDisplay, TextInput

from src import custom
from src.database.models import (
    CONTENT_MAX_LENGTH_CHANNEL_NOTE,
    FOOTER_MAX_LENGTH_CHANNEL_NOTE,
    HEADER_MAX_LENGTH_CHANNEL_NOTE,
    SLOTS_PER_WEEK_CHANNEL_NOTE,
    ChannelNote,
    ChannelNoteEvery,
)
from src.i18n.classes import RawTranslation, TranslationWrapper
from src.log import logger as base_logger

from .config import ChannelNoteConfig

logger = base_logger.getChild("channel_note")


HISTORY_NOSEND_LIMIT = 12


class NoteFlag(StrEnum):
    ENABLED = "enabled"
    FORCE_RESEND = "force_resend"


def _is_note_message(message: discord.Message, note: ChannelNote) -> bool:
    """Check whether a message is this specific note's own previously-sent message.

    Matches on the note's header text inside the message's Components V2 tree, since
    a channel can contain other bot messages with components (other notes, other
    features) that must not be mistaken for this note already having been sent.
    """
    expected_header = f"## {note.header}"
    for component in message.components:
        if not isinstance(component, discord.Container):
            continue
        for child in component.components:
            if isinstance(child, discord.TextDisplay) and child.content == expected_header:
                return True
    return False


@final
class ChannelNoteConfigModal(discord.ui.DesignerModal):
    def __init__(
        self,
        bot: custom.Bot,
        translations: TranslationWrapper[dict[str, RawTranslation]],
        note: ChannelNote | None = None,
    ) -> None:
        self.translations = translations
        self.bot = bot
        self.note = note
        super().__init__(title=self.translations.modal_title)

        self.content_input = TextInput(
            required=True,
            style=discord.InputTextStyle.paragraph,
            min_length=1,
            max_length=CONTENT_MAX_LENGTH_CHANNEL_NOTE,
            value=self.note.content if self.note else "",
        )
        self.add_item(
            Label(
                label=self.translations.content_input_box,
                description=self.translations.content_input_description,
                item=self.content_input,
            )
        )

        self.header_input = TextInput(
            required=True,
            style=discord.InputTextStyle.short,
            min_length=1,
            max_length=HEADER_MAX_LENGTH_CHANNEL_NOTE,
            value=self.note.header if self.note else "",
        )
        self.add_item(
            Label(
                label=self.translations.header_input_box,
                description=self.translations.header_input_description,
                item=self.header_input,
            )
        )

        self.footer_input = TextInput(
            required=False,
            style=discord.InputTextStyle.short,
            min_length=0,
            max_length=FOOTER_MAX_LENGTH_CHANNEL_NOTE,
            value=self.note.footer if self.note else "",
        )
        self.add_item(
            Label(
                label=self.translations.footer_input_box,
                description=self.translations.footer_input_description,
                item=self.footer_input,
            )
        )

        self.every_select = StringSelect(
            required=True,
            options=[
                discord.SelectOption(
                    label=self.translations[f"every_select_option_{i.value}"],
                    value=i.value,
                    default=i == (self.note.every if self.note else ChannelNoteEvery.H_1),
                )
                for i in ChannelNoteEvery
            ],
            min_values=1,
            max_values=1,
        )
        self.add_item(
            Label(
                label=self.translations.every_select_box,
                description=self.translations.every_select_description,
                item=self.every_select,
            )
        )

        # Discord caps modals at 5 items; both flags share a single CheckboxGroup slot.
        self.flags_group = CheckboxGroup(
            required=False,
            min_values=0,
            max_values=2,
            options=[
                discord.CheckboxGroupOption(
                    label=self.translations.enabled_checkbox,
                    description=self.translations.enabled_checkbox_description,
                    value=NoteFlag.ENABLED,
                    default=self.note.enabled if self.note else True,
                ),
                discord.CheckboxGroupOption(
                    label=self.translations.force_resend_checkbox,
                    description=self.translations.force_resend_checkbox_description,
                    value=NoteFlag.FORCE_RESEND,
                    default=self.note.force_resend if self.note else False,
                ),
            ],
        )
        self.add_item(
            Label(
                label=self.translations.flags_group_box,
                item=self.flags_group,
            )
        )

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        assert interaction.channel is not None
        assert self.flags_group.values is not None
        assert self.content_input.value is not None
        assert self.header_input.value is not None
        assert self.footer_input.value is not None
        assert self.every_select.values is not None
        assert len(self.every_select.values) == 1

        enabled = NoteFlag.ENABLED in self.flags_group.values
        force_resend = NoteFlag.FORCE_RESEND in self.flags_group.values

        if self.note is None:
            self.note = ChannelNote(
                discord_id=interaction.channel.id,
                enabled=enabled,
                force_resend=force_resend,
                content=self.content_input.value,
                header=self.header_input.value,
                footer=self.footer_input.value,
                every=ChannelNoteEvery(self.every_select.values[0]),
            )
            await self.note.save()
            await interaction.respond(self.translations.note_created, ephemeral=True)
        else:
            modified: bool = False
            if self.note.enabled != enabled:
                self.note.enabled = enabled
                modified = True
            if self.note.force_resend != force_resend:
                self.note.force_resend = force_resend
                modified = True
            if self.note.content != self.content_input.value:
                self.note.content = self.content_input.value
                modified = True
            if self.note.header != self.header_input.value:
                self.note.header = self.header_input.value
                modified = True
            if self.note.footer != self.footer_input.value:
                self.note.footer = self.footer_input.value
                modified = True
            if self.note.every != ChannelNoteEvery(self.every_select.values[0]):
                self.note.every = ChannelNoteEvery(self.every_select.values[0])
                modified = True

            if modified:
                await self.note.save()
                await interaction.respond(self.translations.note_modified, ephemeral=True)
            else:
                await interaction.respond(self.translations.note_not_modified, ephemeral=True)


@final
class ChannelNoteCog(discord.Cog):
    def __init__(self, bot: custom.Bot, config: ChannelNoteConfig) -> None:
        self.bot = bot
        self.last_slot: int | None = None
        self.config = config

    @discord.Cog.listener(once=True)
    async def on_ready(self) -> None:
        self.channel_note_task.start()
        logger.info("Channel note task started")

    @discord.slash_command(default_member_permissions=discord.Permissions(administrator=True))  # pyright: ignore[reportUntypedFunctionDecorator]
    async def channel_note(self, ctx: custom.ApplicationContext) -> None:
        assert ctx.channel is not None
        note = await ChannelNote.get_or_none(discord_id=ctx.channel.id)
        await ctx.send_modal(ChannelNoteConfigModal(self.bot, ctx.translations, note=note))

    def get_current_slot(self) -> int:
        """Get the current slot for the channel note.

        This divides a week into slots of the given every hour, and returns the slots
        for which this channel note should be sent.

        The slots are 0-indexed. The first slot is representative of 00:00 on monday,
        and the last slot is representative of 23:00 on sunday.

        Returns:
            int: The current slot.

        """
        now = datetime.now(tz=UTC)
        return now.weekday() * 24 + now.hour

    @tasks.loop(hours=1)
    async def channel_note_task(self) -> None:  # noqa: PLR0912
        current_slot = self.get_current_slot()
        logger.info(f"Current slot: {current_slot}")
        if self.last_slot == current_slot:
            logger.info("Current slot is the same as the last slot, skipping")
            return
        if self.last_slot is None:
            self.last_slot = current_slot
            if not self.config.send_on_start:
                logger.info("Send on start is disabled, skipping")
                return
            logger.info("Last slot is None, setting last slot to current slot")
            slots_to_handle = {current_slot}
        else:
            slots_to_handle = (
                set(range(self.last_slot + 1, current_slot + 1))
                if self.last_slot < current_slot
                else set(range(self.last_slot + 1, SLOTS_PER_WEEK_CHANNEL_NOTE)) | set(range(current_slot + 1))
            )
        notes = await ChannelNote.all()
        for note in notes:
            logger.info(f"Checking note: {note.id}")
            if not note.enabled:
                logger.info(f"Note {note} is not enabled, skipping")
                continue
            if not len(note.slots & slots_to_handle) > 0:
                logger.info(
                    f"Note {note} does not match the current slot, it has slots {note.slots}"
                    + f"and the current slots are {slots_to_handle}, skipping"
                )
                continue
            if channel := self.bot.get_channel(note.discord_id):
                skip = False
                if not note.force_resend:
                    async for message in channel.history(limit=HISTORY_NOSEND_LIMIT):  # pyright: ignore[reportAttributeAccessIssue]
                        if message.author.id == self.bot.user.id and _is_note_message(message, note):
                            logger.info(f"Message {message.id} is this note's own message, skipping")
                            skip = True
                            break
                if skip:
                    continue
                logger.info(f"Note {note} matches the current slot, sending to channel {channel.id}")
                container = Container[DesignerView](
                    TextDisplay(
                        content=f"## {note.header}",
                    ),
                    TextDisplay(
                        content=note.content,
                    ),
                )
                if note.footer:
                    container.add_item(
                        TextDisplay(
                            content=note.footer,
                        ),
                    )
                await channel.send(view=DesignerView(container))  # pyright: ignore[reportAttributeAccessIssue]
            else:
                logger.info(f"Channel {note.discord_id} for note {note} not found or not cached, skipping")
        self.last_slot = current_slot


__all__ = ("ChannelNoteCog",)
