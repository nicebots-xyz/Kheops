# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Never, final, override

import discord
from discord.ui import ActionRow, Container, DesignerModal, DesignerView, Label, Separator, TextDisplay, TextInput

from src.database.models import (
    CONTENT_MAX_LENGTH_ANNOUNCEMENT,
    FOOTER_MAX_LENGTH_ANNOUNCEMENT,
    TITLE_MAX_LENGTH_ANNOUNCEMENT,
    Announcement,
    AnnouncementStatus,
    AnnounceSettings,
)

from .logic import parse_date, parse_time
from .queries import cancel_announcement, create_announcement, get_or_create_settings, list_announcements
from .send import build_view, send_announcement

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from zoneinfo import ZoneInfo

    from src import custom
    from src.i18n.classes import RawTranslation, TranslationWrapper

    type Strings = TranslationWrapper[dict[str, RawTranslation]]
    type _Action = Callable[[discord.Interaction], Awaitable[None]]

BUILDER_TIMEOUT = 15 * 60
MAX_ROLES_TO_MENTION = 10
MAX_HISTORY_DISPLAYED = 10


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
class _ChannelPick(discord.ui.Select[DesignerView]):
    """Picks the single channel the announcement will be posted in."""

    def __init__(self, panel: AnnounceBuilderView) -> None:
        defaults = [discord.Object(id=panel.channel_id, type=discord.abc.GuildChannel)] if panel.channel_id else []
        super().__init__(
            discord.ComponentType.channel_select,
            placeholder=panel.t.channel_placeholder,
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
            placeholder=panel.t.roles_placeholder,
            min_values=0,
            max_values=MAX_ROLES_TO_MENTION,
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
        t = panel.t
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
        panel.title = (self.title_input.value or "").strip()
        panel.content = (self.content_input.value or "").strip()
        panel.footer = (self.footer_input.value or "").strip() or None
        if self.image_upload.values:
            attachment = self.image_upload.values[0]
            panel.image_data = await attachment.read()
            panel.image_filename = attachment.filename
        panel.error = None
        await panel.refresh(interaction)


@final
class AnnounceScheduleModal(DesignerModal):
    """Edits when the announcement should be sent — required unless the panel's owner is admin."""

    def __init__(self, panel: AnnounceBuilderView) -> None:
        self.panel = panel
        t = panel.t
        super().__init__(title=t.schedule_modal_title)
        local = panel.scheduled_for.astimezone(panel.tz) if panel.scheduled_for else None

        self.date_input = TextInput(
            style=discord.InputTextStyle.short,
            required=panel.must_schedule,
            placeholder="24/12/2026",
            value=local.strftime("%d/%m/%Y") if local else None,
        )
        self.time_input = TextInput(
            style=discord.InputTextStyle.short,
            required=panel.must_schedule,
            placeholder="18:30",
            value=local.strftime("%H:%M") if local else None,
        )
        self.add_item(
            Label(
                label=t.schedule_date,
                description=t.schedule_date_description.format(timezone=panel.tz.key),
                item=self.date_input,
            )
        )
        self.add_item(Label(label=t.schedule_time, item=self.time_input))

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        panel = self.panel
        panel.error = None
        date_raw, time_raw = (self.date_input.value or "").strip(), (self.time_input.value or "").strip()

        if not date_raw and not time_raw:
            if panel.must_schedule:
                panel.error = panel.t.schedule_required
            else:
                panel.scheduled_for = None
            await panel.refresh(interaction)
            return

        try:
            date = parse_date(date_raw)
            time = parse_time(time_raw)
        except ValueError as e:
            panel.error = str(e)
            await panel.refresh(interaction)
            return

        scheduled_for = datetime.combine(date, time, tzinfo=panel.tz).astimezone(UTC)
        if scheduled_for <= datetime.now(tz=UTC):
            panel.error = panel.t.schedule_in_past
            await panel.refresh(interaction)
            return

        panel.scheduled_for = scheduled_for
        await panel.refresh(interaction)


@final
class AnnounceBuilderView(DesignerView):
    """Ephemeral panel used to compose an announcement before sending or scheduling it."""

    def __init__(
        self,
        *,
        bot: custom.Bot,
        guild_id: int,
        created_by_id: int,
        t: Strings,
        tz: ZoneInfo,
        is_admin: bool,
        must_schedule: bool,
        prefill: Announcement | None = None,
    ) -> None:
        super().__init__(timeout=BUILDER_TIMEOUT, disable_on_timeout=True)
        self.bot = bot
        self.guild_id = guild_id
        self.created_by_id = created_by_id
        self.t = t
        self.tz = tz
        self.is_admin = is_admin
        #: Non-admins can never skip scheduling (see `logic.can_send_instant`) — enforced both
        #: here (so the send button stays disabled until a date is set) and in `AnnounceScheduleModal`.
        self.must_schedule = must_schedule
        self.error: str | None = None

        self.title = prefill.title if prefill else ""
        self.content = prefill.content if prefill else ""
        self.footer = prefill.footer if prefill else None
        self.channel_id = prefill.channel_id if prefill else None
        self.role_ids = list(prefill.role_ids_to_mention) if prefill else []
        self.image_data = prefill.image_data if prefill else None
        self.image_filename = prefill.image_filename if prefill else None
        #: A duplicate always starts as a fresh, unscheduled draft — reusing the source
        #: announcement's (likely already past) date would silently misfire.
        self.scheduled_for: datetime | None = None

        self.render()

    def render(self) -> None:
        t = self.t
        self.clear_items()

        title = f"# {self.title}" if self.title else t.no_title
        content = self.content or t.no_content
        channel = f"<#{self.channel_id}>" if self.channel_id else t.no_channel
        schedule = (
            t.schedule_summary.format(timestamp=int(self.scheduled_for.timestamp()))
            if self.scheduled_for
            else (t.schedule_required if self.must_schedule else t.schedule_not_set)
        )

        preview: list[discord.ui.ViewItem[DesignerView]] = [
            _text(t.panel_title),
            _text(f"{t.channel_label}: {channel}"),
            Separator[DesignerView](),
            _text(title),
            _text(content),
            Separator[DesignerView](),
            _text(f"{t.schedule_label}: {schedule}"),
        ]
        if self.error:
            preview += [Separator[DesignerView](), _text(self.error)]
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

        ready = bool(self.title) and bool(self.content) and self.channel_id is not None
        ready = ready and (self.scheduled_for is not None or not self.must_schedule)
        send_label = t.schedule_action if self.scheduled_for else t.send_now_action
        self.add_item(
            ActionRow[DesignerView](
                _CallbackButton(send_label, self.send, discord.ButtonStyle.success, disabled=not ready),
                _CallbackButton(t.cancel, self.cancel, discord.ButtonStyle.danger),
            )
        )

    async def refresh(self, interaction: discord.Interaction) -> None:
        self.render()
        await interaction.response.edit_message(view=self)

    async def open_content(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(AnnounceContentModal(self))

    async def open_schedule(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(AnnounceScheduleModal(self))

    async def preview(self, interaction: discord.Interaction) -> None:
        view = build_view(
            title=self.title,
            content=self.content,
            footer=self.footer,
            role_ids_to_mention=self.role_ids,
            created_by_id=self.created_by_id,
            image_filename=self.image_filename,
        )
        file = (
            discord.File(io.BytesIO(self.image_data), filename=self.image_filename)
            if self.image_data and self.image_filename
            else None
        )
        await interaction.response.send_message(
            content=self.t.preview_label, view=view, files=[file] if file else [], ephemeral=True
        )

    async def cancel(self, interaction: discord.Interaction) -> None:
        self.stop()
        self.clear_items()
        self.add_item(Container[DesignerView](_text(self.t.cancelled)))
        await interaction.response.edit_message(view=self)

    async def send(self, interaction: discord.Interaction) -> None:
        if self.channel_id is None or not self.title or not self.content:
            await self.refresh(interaction)
            return
        if self.must_schedule and self.scheduled_for is None:
            self.error = self.t.schedule_required
            await self.refresh(interaction)
            return

        await interaction.response.defer()
        announcement = await create_announcement(
            guild_id=self.guild_id,
            channel_id=self.channel_id,
            title=self.title,
            content=self.content,
            footer=self.footer,
            role_ids_to_mention=self.role_ids,
            image_data=self.image_data,
            image_filename=self.image_filename,
            scheduled_for=self.scheduled_for,
            created_by_id=self.created_by_id,
        )

        self.stop()
        self.clear_items()
        if self.scheduled_for is None:
            await send_announcement(self.bot, announcement)
            self.add_item(Container[DesignerView](_text(self.t.sent)))
        else:
            self.add_item(
                Container[DesignerView](_text(self.t.scheduled.format(timestamp=int(self.scheduled_for.timestamp()))))
            )
        await interaction.edit_original_response(view=self)


@final
class AnnounceListView(DesignerView):
    """Lists recent announcements for the guild, with cancel/duplicate/send-now actions."""

    def __init__(
        self,
        *,
        bot: custom.Bot,
        guild_id: int,
        created_by_id: int,
        t: Strings,
        tz: ZoneInfo,
        is_admin: bool,
        must_schedule: bool,
        announcements: list[Announcement],
    ) -> None:
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.created_by_id = created_by_id
        self.t = t
        self.tz = tz
        self.is_admin = is_admin
        self.must_schedule = must_schedule
        self.announcements = announcements
        self.render()

    @classmethod
    async def build(
        cls,
        *,
        bot: custom.Bot,
        guild_id: int,
        created_by_id: int,
        t: Strings,
        tz: ZoneInfo,
        is_admin: bool,
        must_schedule: bool,
    ) -> AnnounceListView:
        announcements = await list_announcements(guild_id, limit=MAX_HISTORY_DISPLAYED)
        return cls(
            bot=bot,
            guild_id=guild_id,
            created_by_id=created_by_id,
            t=t,
            tz=tz,
            is_admin=is_admin,
            must_schedule=must_schedule,
            announcements=announcements,
        )

    def render(self) -> None:
        t = self.t
        self.clear_items()
        if not self.announcements:
            self.add_item(_text(t.no_announcements))
            return

        items: list[discord.ui.ViewItem[DesignerView]] = []
        for announcement in self.announcements:
            items.extend(self._row(announcement))
        self.add_item(Container[DesignerView](*items))

    def _status_label(self, announcement: Announcement) -> str:
        t = self.t
        return {
            AnnouncementStatus.SCHEDULED: t.status_scheduled,
            AnnouncementStatus.SENT: t.status_sent,
            AnnouncementStatus.CANCELLED: t.status_cancelled,
            AnnouncementStatus.FAILED: t.status_failed,
        }[announcement.status]

    def _row(self, announcement: Announcement) -> list[discord.ui.ViewItem[DesignerView]]:
        t = self.t
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
            buttons.append(_CallbackButton(t.cancel_scheduled, self._cancel(announcement), discord.ButtonStyle.danger))
            if self.is_admin:
                buttons.append(
                    _CallbackButton(t.send_now_action, self._send_now(announcement), discord.ButtonStyle.success)
                )
        row.append(ActionRow[DesignerView](*buttons))
        return row

    def _duplicate(self, announcement: Announcement) -> _Action:
        async def action(interaction: discord.Interaction) -> None:
            panel = AnnounceBuilderView(
                bot=self.bot,
                guild_id=self.guild_id,
                created_by_id=self.created_by_id,
                t=self.t,
                tz=self.tz,
                is_admin=self.is_admin,
                must_schedule=self.must_schedule,
                prefill=announcement,
            )
            await interaction.response.send_message(view=panel, ephemeral=True)

        return action

    def _cancel(self, announcement: Announcement) -> _Action:
        async def action(interaction: discord.Interaction) -> None:
            await cancel_announcement(announcement)
            await self.refresh(interaction)

        return action

    def _send_now(self, announcement: Announcement) -> _Action:
        async def action(interaction: discord.Interaction) -> None:
            await send_announcement(self.bot, announcement)
            await self.refresh(interaction)

        return action

    async def refresh(self, interaction: discord.Interaction) -> None:
        self.announcements = await list_announcements(self.guild_id, limit=MAX_HISTORY_DISPLAYED)
        self.render()
        await interaction.response.edit_message(view=self)


@final
class _AllowedRolesPick(discord.ui.Select[DesignerView]):
    """Edits `AnnounceSettings.allowed_role_ids` — saved as soon as it changes."""

    def __init__(self, panel: ConfigPanelView) -> None:
        defaults = [discord.Object(id=role_id, type=discord.Role) for role_id in panel.settings.allowed_role_ids]
        super().__init__(
            discord.ComponentType.role_select,
            placeholder=panel.t.placeholder_allowed_role_ids,
            min_values=0,
            max_values=25,
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

    def __init__(self, guild_id: int, t: Strings, settings: AnnounceSettings) -> None:
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.t = t
        self.settings = settings
        self.render()

    @classmethod
    async def build(cls, guild_id: int, t: Strings) -> ConfigPanelView:
        settings = await get_or_create_settings(guild_id)
        return cls(guild_id, t, settings)

    def render(self) -> None:
        s, t = self.settings, self.t
        self.clear_items()
        self.add_item(
            _text(t.config_summary.format(allowed_roles=", ".join(f"<@&{r}>" for r in s.allowed_role_ids) or t.none))
        )
        self.add_item(ActionRow[DesignerView](_AllowedRolesPick(self)))


__all__ = ("AnnounceBuilderView", "AnnounceListView", "ConfigPanelView")
