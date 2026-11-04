# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Never, final, override

import discord
from discord.ui import ActionRow, Container, DesignerModal, DesignerView, Label, Separator, TextDisplay, TextInput

from .logic import (
    ANSWER_MAX_LENGTH,
    MAX_ANSWERS,
    MAX_DURATION_HOURS,
    QUESTION_MAX_LENGTH,
    DraftAnswer,
    EndInPastError,
    EndTooFarError,
    InvalidEmojiError,
    InvalidEndFormatError,
    duration_hours,
    effective_end,
    emoji_input_value,
    format_emoji,
    parse_emoji,
    parse_end,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from zoneinfo import ZoneInfo

    from src import custom
    from src.i18n.classes import RawTranslation, TranslationWrapper

    type Strings = TranslationWrapper[dict[str, RawTranslation]]
    type _Action = Callable[[discord.Interaction], Awaitable[None]]

BUILDER_TIMEOUT = 15 * 60
DATE_FORMAT = "%d/%m/%Y"
TIME_FORMAT = "%H:%M"


def _text(content: str) -> TextDisplay[DesignerView, Never]:
    return TextDisplay[DesignerView, Never](content)


@final
class _CallbackButton(discord.ui.Button[DesignerView]):
    """A button that runs `action(interaction)`; avoids one subclass per button."""

    def __init__(
        self,
        label: str,
        action: _Action,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        *,
        disabled: bool = False,
    ) -> None:
        super().__init__(label=label, style=style, disabled=disabled)
        self.action = action

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        await self.action(interaction)


@final
class PollSettingsModal(DesignerModal):
    """Edits the poll question, its end date and whether several answers can be picked."""

    def __init__(self, panel: PollBuilderView) -> None:
        self.panel = panel
        t = panel.t
        super().__init__(title=t.settings_modal_title)
        local_end = panel.end.astimezone(panel.tz) if panel.end else None

        self.question_input = TextInput(
            style=discord.InputTextStyle.paragraph,
            max_length=QUESTION_MAX_LENGTH,
            value=panel.question or None,
        )
        self.date_input = TextInput(
            style=discord.InputTextStyle.short,
            placeholder=t.date_placeholder,
            min_length=8,
            max_length=10,
            value=local_end.strftime(DATE_FORMAT) if local_end else None,
        )
        self.time_input = TextInput(
            style=discord.InputTextStyle.short,
            placeholder=t.time_placeholder,
            min_length=4,
            max_length=5,
            value=local_end.strftime(TIME_FORMAT) if local_end else None,
        )
        self.multiselect_checkbox = discord.ui.Checkbox(default=panel.multiselect)

        self.add_item(Label(label=t.question_label, item=self.question_input))
        self.add_item(
            Label(
                label=t.date_label,
                description=t.date_description.format(timezone=panel.tz.key),
                item=self.date_input,
            )
        )
        self.add_item(Label(label=t.time_label, description=t.time_description, item=self.time_input))
        self.add_item(
            Label(
                label=t.multiselect_label,
                description=t.multiselect_description,
                item=self.multiselect_checkbox,
            )
        )

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        panel = self.panel
        panel.question = (self.question_input.value or "").strip()
        panel.multiselect = bool(self.multiselect_checkbox.value)
        panel.error = None
        try:
            panel.end = parse_end(self.date_input.value or "", self.time_input.value or "", panel.tz)
        except InvalidEndFormatError:
            panel.error = panel.t.invalid_end_format
        await panel.refresh(interaction)


@final
class PollAnswerModal(DesignerModal):
    """Adds a new answer, or edits the answer at `index`."""

    def __init__(self, panel: PollBuilderView, index: int | None = None) -> None:
        self.panel = panel
        self.index = index
        t = panel.t
        answer = panel.answers[index] if index is not None else None
        super().__init__(title=t.answer_modal_edit_title if answer else t.answer_modal_add_title)

        self.emoji_input = TextInput(
            style=discord.InputTextStyle.short,
            required=False,
            max_length=100,
            placeholder=t.emoji_placeholder,
            value=emoji_input_value(answer.emoji) if answer else None,
        )
        self.text_input = TextInput(
            style=discord.InputTextStyle.short,
            max_length=ANSWER_MAX_LENGTH,
            value=answer.text if answer else None,
        )
        self.add_item(Label(label=t.emoji_label, description=t.emoji_description, item=self.emoji_input))
        self.add_item(Label(label=t.answer_label, item=self.text_input))

    def _resolve(self, emoji: discord.PartialEmoji | None) -> discord.PartialEmoji | None:
        """Fill in the name of a custom emoji given by ID, so the preview shows it properly."""
        if emoji is None or emoji.id is None:
            return emoji
        known = self.panel.bot.get_emoji(emoji.id)
        if known is None:
            return emoji
        return discord.PartialEmoji(name=known.name, id=known.id, animated=known.animated)

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        panel = self.panel
        panel.error = None
        try:
            emoji = self._resolve(parse_emoji(self.emoji_input.value))
        except InvalidEmojiError:
            panel.error = panel.t.invalid_emoji
            await panel.refresh(interaction)
            return

        answer = DraftAnswer(text=(self.text_input.value or "").strip(), emoji=emoji)
        if self.index is not None and self.index < len(panel.answers):
            panel.answers[self.index] = answer
        elif len(panel.answers) < MAX_ANSWERS:
            panel.answers.append(answer)
        else:
            panel.error = panel.t.too_many_answers.format(max=MAX_ANSWERS)
        await panel.refresh(interaction)


@final
class _AnswerSelect(discord.ui.Select[DesignerView]):
    """Picks one answer to edit (opens the answer modal) or to remove."""

    def __init__(self, panel: PollBuilderView, *, remove: bool) -> None:
        t = panel.t
        super().__init__(
            placeholder=t.remove_answer_placeholder if remove else t.edit_answer_placeholder,
            options=[
                discord.SelectOption(label=f"{i + 1}. {answer.text}"[:100], value=str(i))
                for i, answer in enumerate(panel.answers)
            ],
        )
        self.panel = panel
        self.remove = remove

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.values:
            return
        index = int(str(self.values[0]))
        if not self.remove:
            await interaction.response.send_modal(PollAnswerModal(self.panel, index))
            return
        if index < len(self.panel.answers):
            self.panel.answers.pop(index)
        self.panel.error = None
        await self.panel.refresh(interaction)


@final
class PollBuilderView(DesignerView):
    """Ephemeral panel used to build a native poll before sending it in the channel."""

    def __init__(self, bot: custom.Bot, t: Strings, tz: ZoneInfo) -> None:
        super().__init__(timeout=BUILDER_TIMEOUT, disable_on_timeout=True)
        self.bot: custom.Bot = bot
        self.t: Strings = t
        self.tz: ZoneInfo = tz
        self.question: str = ""
        self.end: datetime | None = None
        self.multiselect: bool = False
        self.answers: list[DraftAnswer] = []
        self.error: str | None = None
        self.render()

    def _end_summary(self, now: datetime) -> tuple[str, bool]:
        """Describe the end of the poll and tell whether it can be sent as is."""
        t = self.t
        if self.end is None:
            return t.end_not_set, False
        local_end = self.end.astimezone(self.tz)
        requested = t.end_requested.format(
            date=local_end.strftime(DATE_FORMAT), time=local_end.strftime(TIME_FORMAT), timezone=self.tz.key
        )
        try:
            hours = duration_hours(self.end, now)
        except EndInPastError:
            return requested + "\n" + t.end_in_past, False
        except EndTooFarError:
            return requested + "\n" + t.end_too_far.format(max=MAX_DURATION_HOURS, days=MAX_DURATION_HOURS // 24), False
        timestamp = int(effective_end(now, hours).timestamp())
        return requested + "\n" + t.end_effective.format(hours=hours, timestamp=timestamp), True

    def render(self) -> None:
        """Rebuild every component from the current draft."""
        t = self.t
        self.clear_items()
        now = datetime.now(UTC)

        question = f"## {self.question}" if self.question else t.no_question
        answers = (
            "\n".join(
                f"{i + 1}. " + (f"{format_emoji(answer.emoji)} " if answer.emoji else "") + answer.text
                for i, answer in enumerate(self.answers)
            )
            if self.answers
            else t.no_answers
        )
        end_summary, end_ok = self._end_summary(now)
        mode = t.mode_multiple if self.multiselect else t.mode_single

        preview: list[discord.ui.ViewItem[DesignerView]] = [
            _text(t.panel_title),
            _text(question),
            Separator[DesignerView](),
            _text(t.answers_title.format(count=len(self.answers), max=MAX_ANSWERS) + "\n" + answers),
            Separator[DesignerView](),
            _text(t.end_title + "\n" + end_summary + "\n" + mode),
        ]
        if self.error:
            preview += [Separator[DesignerView](), _text(self.error)]
        self.add_item(Container[DesignerView](*preview))

        self.add_item(
            ActionRow[DesignerView](
                _CallbackButton(t.edit_settings, self.open_settings, discord.ButtonStyle.primary),
                _CallbackButton(t.add_answer, self.open_add_answer, disabled=len(self.answers) >= MAX_ANSWERS),
            )
        )
        if self.answers:
            self.add_item(ActionRow[DesignerView](_AnswerSelect(self, remove=False)))
            self.add_item(ActionRow[DesignerView](_AnswerSelect(self, remove=True)))
        ready = bool(self.question) and bool(self.answers) and end_ok
        self.add_item(
            ActionRow[DesignerView](
                _CallbackButton(t.send, self.send, discord.ButtonStyle.success, disabled=not ready),
                _CallbackButton(t.cancel, self.cancel, discord.ButtonStyle.danger),
            )
        )

    async def refresh(self, interaction: discord.Interaction) -> None:
        """Re-render the panel in place after a change."""
        self.render()
        await interaction.response.edit_message(view=self)

    async def open_settings(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(PollSettingsModal(self))

    async def open_add_answer(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(PollAnswerModal(self))

    async def cancel(self, interaction: discord.Interaction) -> None:
        self.stop()
        self.clear_items()
        self.add_item(Container[DesignerView](_text(self.t.cancelled)))
        await interaction.response.edit_message(view=self)

    async def send(self, interaction: discord.Interaction) -> None:
        channel = interaction.channel
        if self.end is None or not isinstance(channel, discord.abc.Messageable):
            await self.refresh(interaction)
            return

        # The duration is computed again now: time went by while the poll was being built.
        now = datetime.now(UTC)
        try:
            hours = duration_hours(self.end, now)
        except (EndInPastError, EndTooFarError):
            self.error = None
            await self.refresh(interaction)
            return

        poll = discord.Poll(
            question=self.question,
            answers=[discord.PollAnswer(answer.text, answer.emoji) for answer in self.answers],
            duration=hours,
            allow_multiselect=self.multiselect,
        )
        await interaction.response.defer()
        try:
            message = await channel.send(poll=poll)
        except discord.HTTPException as e:
            self.error = self.t.send_failed.format(error=e.text or e.status)
            self.render()
            await interaction.edit_original_response(view=self)
            return

        self.stop()
        self.clear_items()
        timestamp = int(effective_end(now, hours).timestamp())
        self.add_item(
            Container[DesignerView](
                _text(self.t.sent.format(url=message.jump_url, hours=hours, timestamp=timestamp)),
            )
        )
        await interaction.edit_original_response(view=self)


__all__ = ("PollBuilderView",)
