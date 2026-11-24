# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Never, final, override

import discord
from discord.ui import ActionRow, Container, DesignerModal, DesignerView, Label, Separator, TextDisplay, TextInput

from src.database.models import (
    CONTENT_MAX_LENGTH_ANNOUNCEMENT,
    FOOTER_MAX_LENGTH_ANNOUNCEMENT,
    IMAGE_MAX_SIZE_ANNOUNCEMENT,
    MAX_ALLOWED_ROLES_ANNOUNCEMENT,
    MAX_ROLES_TO_MENTION_ANNOUNCEMENT,
    MESSAGE_TEXT_MAX_LENGTH_ANNOUNCEMENT,
    TITLE_MAX_LENGTH_ANNOUNCEMENT,
    Announcement,
    AnnouncementStatus,
    AnnounceSettings,
)

from .logic import DATE_FORMAT, TIME_FORMAT, parse_date, parse_time, sanitize_image_filename
from .queries import (
    cancel_announcement,
    create_announcement,
    get_or_create_settings,
    list_announcements,
    update_announcement,
)
from .send import build_view, image_file, send_claimed, send_scheduled, text_length

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from zoneinfo import ZoneInfo

    from src.i18n.classes import RawTranslation

    from .translations import ExtensionStrings

    type _Action = Callable[[discord.Interaction], Awaitable[None]]

BUILDER_TIMEOUT = 15 * 60
LIST_TIMEOUT = 5 * 60
_MIB = 1024 * 1024


def _text(content: str) -> TextDisplay[DesignerView, Never]:
    return TextDisplay[DesignerView, Never](content)


@dataclass(frozen=True, slots=True, kw_only=True)
class PanelContext:
    """What every announce panel opened by one member needs.

    Attributes:
        bot: The bot.
        guild_id: The guild the panel is used in.
        member_id: The member using the panel, credited as the author of what they create.
        is_admin: Whether that member is an administrator.
        tz: The timezone dates and times are typed in.
        strings: The extension's raw strings, to localize the sent message for its guild.
        t: The panel's strings, localized for the member.
        message_t: The announcement message's strings, localized for the guild.

    """

    bot: discord.Client
    guild_id: int
    member_id: int
    is_admin: bool
    tz: ZoneInfo
    strings: dict[str, RawTranslation]
    t: ExtensionStrings
    message_t: ExtensionStrings


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
class _ChannelPick(discord.ui.Select[DesignerView]):
    """Picks the single channel the announcement will be posted in."""

    def __init__(self, panel: AnnounceBuilderView) -> None:
        defaults = [discord.Object(id=panel.channel_id, type=discord.abc.GuildChannel)] if panel.channel_id else []
        super().__init__(
            discord.ComponentType.channel_select,
            placeholder=panel.ctx.t.channel_placeholder,
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
            default_values=defaults,
        )
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        self.panel.channel_id = self.values[0].id if self.values else None
        self.panel.error = None
        await self.panel.refresh(interaction)


@final
class _RoleMentionPick(discord.ui.Select[DesignerView]):
    """Picks which roles get pinged when the announcement is sent."""

    def __init__(self, panel: AnnounceBuilderView) -> None:
        defaults = [discord.Object(id=role_id, type=discord.Role) for role_id in panel.role_ids]
        super().__init__(
            discord.ComponentType.role_select,
            placeholder=panel.ctx.t.roles_placeholder,
            min_values=0,
            max_values=MAX_ROLES_TO_MENTION_ANNOUNCEMENT,
            default_values=defaults,
        )
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        self.panel.role_ids = [value.id for value in self.values or []]
        await self.panel.refresh(interaction)


@final
class AnnounceContentModal(DesignerModal):
    """Edits the title, content, footer and image of the draft."""

    def __init__(self, panel: AnnounceBuilderView) -> None:
        self.panel = panel
        t = panel.ctx.t
        super().__init__(title=t.content_modal_title)

        self.title_input = TextInput(
            style=discord.InputTextStyle.short, max_length=TITLE_MAX_LENGTH_ANNOUNCEMENT, value=panel.title or None
        )
        self.content_input = TextInput(
            style=discord.InputTextStyle.paragraph,
            max_length=CONTENT_MAX_LENGTH_ANNOUNCEMENT,
            value=panel.content or None,
        )
        self.footer_input = TextInput(
            style=discord.InputTextStyle.short,
            required=False,
            max_length=FOOTER_MAX_LENGTH_ANNOUNCEMENT,
            value=panel.footer or None,
        )
        self.image_upload = discord.ui.FileUpload(required=False)

        self.add_item(Label(label=t.announcement_title, item=self.title_input))
        self.add_item(Label(label=t.announcement_content, item=self.content_input))
        self.add_item(Label(label=t.announcement_footer, item=self.footer_input))
        self.add_item(
            Label(label=t.announcement_image, description=t.announcement_image_description, item=self.image_upload)
        )

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        panel = self.panel
        t = panel.ctx.t
        panel.title = (self.title_input.value or "").strip()
        panel.content = (self.content_input.value or "").strip()
        panel.footer = (self.footer_input.value or "").strip() or None
        panel.error = None
        if self.image_upload.values:
            attachment = self.image_upload.values[0]
            filename = sanitize_image_filename(attachment.filename)
            if filename is None:
                panel.error = t.invalid_image
            elif attachment.size > IMAGE_MAX_SIZE_ANNOUNCEMENT:
                panel.error = t.image_too_large.format(max_size=IMAGE_MAX_SIZE_ANNOUNCEMENT // _MIB)
            else:
                panel.new_image = await attachment.read()
                panel.image_filename = filename
        await panel.refresh(interaction)


@final
class AnnounceScheduleModal(DesignerModal):
    """Edits when the announcement should be sent, required unless the panel's owner is admin."""

    def __init__(self, panel: AnnounceBuilderView) -> None:
        self.panel = panel
        t = panel.ctx.t
        super().__init__(title=t.schedule_modal_title)
        local = panel.scheduled_for.astimezone(panel.ctx.tz) if panel.scheduled_for else None

        self.date_input = TextInput(
            style=discord.InputTextStyle.short,
            required=panel.must_schedule,
            placeholder=t.schedule_date_placeholder,
            value=local.strftime(DATE_FORMAT) if local else None,
        )
        self.time_input = TextInput(
            style=discord.InputTextStyle.short,
            required=panel.must_schedule,
            placeholder=t.schedule_time_placeholder,
            value=local.strftime(TIME_FORMAT) if local else None,
        )
        self.add_item(
            Label(
                label=t.schedule_date,
                description=t.schedule_date_description.format(timezone=panel.ctx.tz.key),
                item=self.date_input,
            )
        )
        self.add_item(Label(label=t.schedule_time, item=self.time_input))

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        panel = self.panel
        t = panel.ctx.t
        panel.error = None
        date_raw, time_raw = (self.date_input.value or "").strip(), (self.time_input.value or "").strip()

        if not date_raw and not time_raw:
            if panel.must_schedule:
                panel.error = t.schedule_required
            else:
                panel.scheduled_for = None
            await panel.refresh(interaction)
            return

        try:
            date = parse_date(date_raw)
        except ValueError:
            panel.error = t.invalid_date
            await panel.refresh(interaction)
            return
        try:
            time = parse_time(time_raw)
        except ValueError:
            panel.error = t.invalid_time
            await panel.refresh(interaction)
            return

        scheduled_for = datetime.combine(date, time, tzinfo=panel.ctx.tz).astimezone(UTC)
        if scheduled_for <= datetime.now(tz=UTC):
            panel.error = t.schedule_in_past
            await panel.refresh(interaction)
            return

        panel.scheduled_for = scheduled_for
        await panel.refresh(interaction)


@final
class AnnounceBuilderView(DesignerView):
    """Ephemeral panel used to compose an announcement before sending or scheduling it."""

    def __init__(
        self,
        ctx: PanelContext,
        *,
        must_schedule: bool,
        prefill: Announcement | None = None,
        prefill_image: bytes | None = None,
        editing: Announcement | None = None,
    ) -> None:
        """Open a panel on a new draft, a copy of `prefill`, or the scheduled `editing`.

        Args:
            ctx: The panel's context.
            must_schedule: Whether a date/time is required, always the case for non-admins.
            prefill: An announcement whose values a new draft starts from.
            prefill_image: The image of `prefill`, copied into the new draft.
            editing: A scheduled announcement edited in place, instead of creating one.

        """
        super().__init__(timeout=BUILDER_TIMEOUT, disable_on_timeout=True)
        self.ctx = ctx
        self.must_schedule = must_schedule
        self.error: str | None = None
        #: Set once sending starts, so a double click never creates the announcement twice.
        self.submitted = False

        self.editing = editing
        source = editing or prefill
        self.title = source.title if source else ""
        self.content = source.content if source else ""
        self.footer = source.footer if source else None
        self.channel_id = source.channel_id if source else None
        self.role_ids = list(source.role_ids_to_mention) if source else []
        #: An image picked in this panel, or copied from `prefill`. When editing, the stored image
        #: is only replaced if this is set.
        self.new_image = prefill_image if prefill else None
        self.image_filename = source.image_filename if source and (editing or prefill_image) else None
        #: Edits keep the original author, credited in the sent message.
        self.author_id = editing.created_by_id if editing else ctx.member_id
        #: Editing keeps the original date; a duplicate starts unscheduled, since the date of the
        #: announcement it copies may already be past.
        self.scheduled_for: datetime | None = editing.scheduled_for if editing else None

        self.render()

    @classmethod
    async def duplicate(cls, ctx: PanelContext, source: Announcement, *, must_schedule: bool) -> AnnounceBuilderView:
        """Open a panel on a new draft copying `source`, image included.

        Args:
            ctx: The panel's context.
            source: The announcement to copy.
            must_schedule: Whether a date/time is required.

        Returns:
            The panel.

        """
        try:
            image = await source.image.read()
        except FileNotFoundError:
            image = None
        return cls(ctx, must_schedule=must_schedule, prefill=source, prefill_image=image)

    def _text_length(self) -> int:
        """Count the text of the message the draft would send.

        Returns:
            The number of characters across its text displays.

        """
        return text_length(
            t=self.ctx.message_t,
            title=self.title,
            content=self.content,
            footer=self.footer,
            role_ids_to_mention=self.role_ids,
            created_by_id=self.author_id,
        )

    def render(self) -> None:
        t = self.ctx.t
        self.clear_items()

        title = f"# {self.title}" if self.title else t.no_title
        content = self.content or t.no_content
        channel = f"<#{self.channel_id}>" if self.channel_id else t.no_channel
        schedule = (
            t.schedule_summary.format(timestamp=int(self.scheduled_for.timestamp()))
            if self.scheduled_for
            else (t.schedule_required if self.must_schedule else t.schedule_not_set)
        )
        length = self._text_length()
        too_long = length > MESSAGE_TEXT_MAX_LENGTH_ANNOUNCEMENT

        preview: list[discord.ui.ViewItem[DesignerView]] = [
            _text(t.panel_title),
            _text(f"{t.channel_label}: {channel}"),
            Separator[DesignerView](),
            _text(title),
            _text(content),
            Separator[DesignerView](),
            _text(f"{t.schedule_label}: {schedule}"),
        ]
        errors = [error for error in (self.error,) if error]
        if too_long:
            errors.append(t.text_too_long.format(length=length, max_length=MESSAGE_TEXT_MAX_LENGTH_ANNOUNCEMENT))
        for error in errors:
            preview += [Separator[DesignerView](), _text(error)]
        self.add_item(Container[DesignerView](*preview))

        self.add_item(
            ActionRow[DesignerView](
                _CallbackButton(t.edit_content, self.open_content, discord.ButtonStyle.primary),
                _CallbackButton(t.edit_schedule, self.open_schedule, discord.ButtonStyle.primary),
                _CallbackButton(t.preview, self.preview, discord.ButtonStyle.secondary),
            )
        )
        self.add_item(ActionRow[DesignerView](_ChannelPick(self)))
        self.add_item(ActionRow[DesignerView](_RoleMentionPick(self)))

        send_label = (
            t.save_changes if self.editing else (t.schedule_action if self.scheduled_for else t.send_now_action)
        )
        self.add_item(
            ActionRow[DesignerView](
                _CallbackButton(send_label, self.send, discord.ButtonStyle.success, disabled=not self._ready()),
                _CallbackButton(t.cancel, self.cancel, discord.ButtonStyle.danger),
            )
        )

    def _ready(self) -> bool:
        """Tell whether the draft can be sent or scheduled.

        Returns:
            Whether every required field is set and the text fits in a message.

        """
        return (
            bool(self.title)
            and bool(self.content)
            and self.channel_id is not None
            and (self.scheduled_for is not None or not self.must_schedule)
            and self._text_length() <= MESSAGE_TEXT_MAX_LENGTH_ANNOUNCEMENT
        )

    async def refresh(self, interaction: discord.Interaction) -> None:
        self.render()
        await interaction.response.edit_message(view=self)

    async def open_content(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(AnnounceContentModal(self))

    async def open_schedule(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(AnnounceScheduleModal(self))

    async def preview(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        image = self.new_image
        if image is None and self.editing is not None:
            image = await self.editing.image.read()
        view = build_view(
            t=self.ctx.message_t,
            title=self.title,
            content=self.content,
            footer=self.footer,
            role_ids_to_mention=self.role_ids,
            created_by_id=self.author_id,
            image_filename=self.image_filename if image is not None else None,
        )
        await interaction.followup.send(self.ctx.t.preview_label, ephemeral=True)
        await interaction.followup.send(
            view=view,
            files=image_file(image, self.image_filename),
            ephemeral=True,
        )

    async def cancel(self, interaction: discord.Interaction) -> None:
        self.stop()
        self.clear_items()
        self.add_item(Container[DesignerView](_text(self.ctx.t.cancelled)))
        await interaction.response.edit_message(view=self)

    async def _finish(self, interaction: discord.Interaction, message: str) -> None:
        """Close the panel, replacing it with `message`.

        Args:
            interaction: The deferred interaction that closed it.
            message: The outcome shown instead of the panel.

        """
        self.stop()
        self.clear_items()
        self.add_item(Container[DesignerView](_text(message)))
        await interaction.edit_original_response(view=self)

    async def send(self, interaction: discord.Interaction) -> None:
        if self.submitted:
            await interaction.response.defer()
            return
        if self.channel_id is None or not self._ready():
            await self.refresh(interaction)
            return
        self.submitted = True
        await interaction.response.defer()
        t = self.ctx.t

        if self.editing is not None:
            assert self.scheduled_for is not None  # must_schedule=True whenever editing
            updated = await update_announcement(
                self.editing.id,
                self.ctx.guild_id,
                channel_id=self.channel_id,
                title=self.title,
                content=self.content,
                footer=self.footer,
                role_ids_to_mention=self.role_ids,
                scheduled_for=self.scheduled_for,
                image=self.new_image,
                image_filename=self.image_filename,
            )
            if updated is None:
                await self._finish(interaction, t.not_scheduled)
            else:
                await self._finish(interaction, t.changes_saved.format(timestamp=int(self.scheduled_for.timestamp())))
            return

        announcement = await create_announcement(
            guild_id=self.ctx.guild_id,
            channel_id=self.channel_id,
            title=self.title,
            content=self.content,
            footer=self.footer,
            role_ids_to_mention=self.role_ids,
            image=self.new_image,
            image_filename=self.image_filename,
            scheduled_for=self.scheduled_for,
            created_by_id=self.ctx.member_id,
        )
        if self.scheduled_for is not None:
            await self._finish(interaction, t.scheduled.format(timestamp=int(self.scheduled_for.timestamp())))
            return
        sent = await send_claimed(self.ctx.bot, announcement, self.ctx.strings)
        await self._finish(interaction, t.sent if sent else t.send_failed)


@final
class AnnounceListView(DesignerView):
    """Lists recent announcements for the guild, with cancel/duplicate/edit/send-now actions."""

    def __init__(self, ctx: PanelContext, *, must_schedule: bool, announcements: list[Announcement]) -> None:
        super().__init__(timeout=LIST_TIMEOUT)
        self.ctx = ctx
        self.must_schedule = must_schedule
        self.announcements = announcements
        self.error: str | None = None
        self.render()

    @classmethod
    async def build(cls, ctx: PanelContext, *, must_schedule: bool) -> AnnounceListView:
        """Open the history of `ctx`'s guild.

        Args:
            ctx: The panel's context.
            must_schedule: Whether announcements opened from it require a date/time.

        Returns:
            The panel.

        """
        return cls(ctx, must_schedule=must_schedule, announcements=await list_announcements(ctx.guild_id))

    def render(self) -> None:
        t = self.ctx.t
        self.clear_items()
        if self.error:
            self.add_item(_text(self.error))
        if not self.announcements:
            self.add_item(_text(t.no_announcements))
            return

        items: list[discord.ui.ViewItem[DesignerView]] = []
        for announcement in self.announcements:
            items.extend(self._row(announcement))
        self.add_item(Container[DesignerView](*items))

    def _status_label(self, announcement: Announcement) -> str:
        t = self.ctx.t
        return {
            AnnouncementStatus.SCHEDULED: t.status_scheduled,
            AnnouncementStatus.SENDING: t.status_sending,
            AnnouncementStatus.SENT: t.status_sent,
            AnnouncementStatus.CANCELLED: t.status_cancelled,
            AnnouncementStatus.FAILED: t.status_failed,
        }[announcement.status]

    def _row(self, announcement: Announcement) -> list[discord.ui.ViewItem[DesignerView]]:
        t = self.ctx.t
        when = announcement.scheduled_for or announcement.sent_at or announcement.created_at
        line = t.history_line.format(
            title=announcement.title,
            status=self._status_label(announcement),
            channel=f"<#{announcement.channel_id}>",
            timestamp=int(when.timestamp()),
        )
        row: list[discord.ui.ViewItem[DesignerView]] = [_text(line)]
        buttons: list[discord.ui.Button[DesignerView]] = [_CallbackButton(t.duplicate, self._duplicate(announcement))]
        if announcement.status == AnnouncementStatus.SCHEDULED:
            buttons.append(_CallbackButton(t.edit, self._edit(announcement), discord.ButtonStyle.primary))
            buttons.append(_CallbackButton(t.cancel_scheduled, self._cancel(announcement), discord.ButtonStyle.danger))
            if self.ctx.is_admin:
                buttons.append(
                    _CallbackButton(t.send_now_action, self._send_now(announcement), discord.ButtonStyle.success)
                )
        row.append(ActionRow[DesignerView](*buttons))
        return row

    def _duplicate(self, announcement: Announcement) -> _Action:
        async def action(interaction: discord.Interaction) -> None:
            await interaction.response.defer(ephemeral=True)
            panel = await AnnounceBuilderView.duplicate(self.ctx, announcement, must_schedule=self.must_schedule)
            await interaction.followup.send(view=panel, ephemeral=True)

        return action

    def _edit(self, announcement: Announcement) -> _Action:
        async def action(interaction: discord.Interaction) -> None:
            current = await Announcement.get_or_none(id=announcement.id, guild_id=self.ctx.guild_id)
            if current is None or current.status != AnnouncementStatus.SCHEDULED:
                await self.refresh(interaction, error=self.ctx.t.not_scheduled)
                return
            # Editing a scheduled announcement never turns it into an instant send, even for admins.
            panel = AnnounceBuilderView(self.ctx, must_schedule=True, editing=current)
            await interaction.response.send_message(view=panel, ephemeral=True)

        return action

    def _cancel(self, announcement: Announcement) -> _Action:
        async def action(interaction: discord.Interaction) -> None:
            cancelled = await cancel_announcement(announcement.id, self.ctx.guild_id)
            await self.refresh(interaction, error=None if cancelled else self.ctx.t.not_scheduled)

        return action

    def _send_now(self, announcement: Announcement) -> _Action:
        async def action(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            sent = await send_scheduled(self.ctx.bot, announcement.id, self.ctx.strings, self.ctx.guild_id)
            self.error = self.ctx.t.not_scheduled if sent is None else None
            self.announcements = await list_announcements(self.ctx.guild_id)
            self.render()
            await interaction.edit_original_response(view=self)

        return action

    async def refresh(self, interaction: discord.Interaction, *, error: str | None = None) -> None:
        self.error = error
        self.announcements = await list_announcements(self.ctx.guild_id)
        self.render()
        await interaction.response.edit_message(view=self)


@final
class _AllowedRolesPick(discord.ui.Select[DesignerView]):
    """Edits `AnnounceSettings.allowed_role_ids`, saved as soon as it changes."""

    def __init__(self, panel: ConfigPanelView) -> None:
        defaults = [discord.Object(id=role_id, type=discord.Role) for role_id in panel.settings.allowed_role_ids]
        super().__init__(
            discord.ComponentType.role_select,
            placeholder=panel.t.placeholder_allowed_role_ids,
            min_values=0,
            max_values=MAX_ALLOWED_ROLES_ANNOUNCEMENT,
            default_values=defaults,
        )
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        self.panel.settings.allowed_role_ids = [value.id for value in self.values or []]
        await self.panel.settings.save(update_fields=["allowed_role_ids"])
        self.panel.render()
        await interaction.response.edit_message(view=self.panel)


@final
class ConfigPanelView(DesignerView):
    """Admin panel: which roles (besides admins) can schedule an announcement."""

    def __init__(self, t: ExtensionStrings, settings: AnnounceSettings) -> None:
        super().__init__(timeout=LIST_TIMEOUT)
        self.t = t
        self.settings = settings
        self.render()

    @classmethod
    async def build(cls, guild_id: int, t: ExtensionStrings) -> ConfigPanelView:
        """Open the configuration panel of a guild.

        Args:
            guild_id: The guild's ID.
            t: The panel's strings.

        Returns:
            The panel.

        """
        return cls(t, await get_or_create_settings(guild_id))

    def render(self) -> None:
        s, t = self.settings, self.t
        self.clear_items()
        self.add_item(
            _text(t.config_summary.format(allowed_roles=", ".join(f"<@&{r}>" for r in s.allowed_role_ids) or t.none))
        )
        self.add_item(ActionRow[DesignerView](_AllowedRolesPick(self)))


__all__ = ("AnnounceBuilderView", "AnnounceListView", "ConfigPanelView", "PanelContext")
