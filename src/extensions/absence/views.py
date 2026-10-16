# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Never, final, override

import discord
from discord.ui import ActionRow, Container, DesignerModal, DesignerView, Separator, TextDisplay

from src.database.models import Absence, AbsenceSettings

from .announce import remove_announcement, sync_announcement
from .logic import AbsenceStatus, absence_status, duration_days, is_backdated, parse_date
from .queries import (
    CancelledError,
    OverlapError,
    cancel_absence,
    create_absence,
    get_or_create_settings,
    restore_absence,
    update_absence_dates,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from src.i18n.classes import RawTranslation, TranslationWrapper

    type Strings = TranslationWrapper[dict[str, RawTranslation]]
    type _Action = Callable[[discord.Interaction], Awaitable[None]]


def _text(content: str) -> Container[DesignerView]:
    return Container[DesignerView](TextDisplay[DesignerView, Never](content))


@final
class _CallbackButton(discord.ui.Button[DesignerView]):
    """A button that runs `action(interaction)`; avoids one subclass per button."""

    def __init__(
        self, label: str, action: "_Action", style: discord.ButtonStyle = discord.ButtonStyle.secondary
    ) -> None:
        super().__init__(label=label, style=style)
        self.action = action

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        await self.action(interaction)


@final
class AbsenceModal(DesignerModal):
    """Creates or edits one absence. Opened either standalone or from an `AbsenceListView`."""

    def __init__(
        self,
        *,
        bot: discord.Client,
        guild_id: int,
        member_id: int,
        created_by_id: int,
        t: "Strings",
        absence: Absence | None = None,
        panel: "AbsenceListView | None" = None,
    ) -> None:
        self.bot = bot
        self.guild_id = guild_id
        self.member_id = member_id
        self.created_by_id = created_by_id
        self.t = t
        self.absence = absence
        self.panel = panel
        super().__init__(title=t.edit_modal_title if absence else t.declare_modal_title)

        self.start_input = discord.ui.TextInput(
            style=discord.InputTextStyle.short,
            placeholder="01/01/2026",
            value=absence.start_date.strftime("%d/%m/%Y") if absence else "",
        )
        self.end_input = discord.ui.TextInput(
            style=discord.InputTextStyle.short,
            placeholder="01/01/2026",
            value=absence.end_date.strftime("%d/%m/%Y") if absence else "",
        )
        self.reason_input = discord.ui.TextInput(
            style=discord.InputTextStyle.paragraph,
            required=True,
            max_length=500,
            value=absence.reason if absence else "",
        )
        self.add_item(discord.ui.Label(label=t.modal_start_date, item=self.start_input))
        self.add_item(discord.ui.Label(label=t.modal_end_date, item=self.end_input))
        self.add_item(
            discord.ui.Label(label=t.modal_reason, description=t.modal_reason_description, item=self.reason_input)
        )

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            start = parse_date(self.start_input.value or "")
            end = parse_date(self.end_input.value or "")
        except ValueError as e:
            await interaction.respond(str(e), ephemeral=True)
            return
        if end < start:
            await interaction.respond(self.t.invalid_range, ephemeral=True)
            return
        if self.absence is None and is_backdated(start, datetime.now(tz=UTC).date()):
            await interaction.respond(self.t.invalid_past, ephemeral=True)
            return

        reason = (self.reason_input.value or "").strip()
        if not reason:
            await interaction.respond(self.t.invalid_blank_reason, ephemeral=True)
            return

        try:
            if self.absence is None:
                absence = await create_absence(
                    guild_id=self.guild_id,
                    member_id=self.member_id,
                    start=start,
                    end=end,
                    reason=reason,
                    created_by_id=self.created_by_id,
                )
            else:
                absence = self.absence
                await update_absence_dates(absence, start=start, end=end, reason=reason)
        except OverlapError as e:
            await interaction.respond(
                self.t.invalid_overlap.format(
                    start=e.conflicting.start_date.strftime("%d/%m/%Y"),
                    end=e.conflicting.end_date.strftime("%d/%m/%Y"),
                ),
                ephemeral=True,
            )
            return
        except CancelledError:
            await interaction.respond(self.t.invalid_cancelled, ephemeral=True)
            return

        settings = await get_or_create_settings(self.guild_id)
        await sync_announcement(self.bot, absence, settings)

        if self.panel is not None:
            await self.panel.refresh(interaction)
        else:
            days = duration_days(start, end)
            await interaction.respond(self.t.saved.format(days=days, plural="" if days == 1 else "s"), ephemeral=True)


#: Upcoming/ongoing absences are the ones that matter most, so they're never cut off — but capped
#: defensively since Discord messages can't hold unlimited components either way.
MAX_ACTIVE_DISPLAYED = 15
#: Past/cancelled absences pile up over months of use — only the most recent few are shown.
MAX_HISTORY_DISPLAYED = 5


@final
class AbsenceListView(DesignerView):
    """Lists one member's absences, with inline edit/cancel for whoever is allowed to manage them.

    To stay readable after months of use, this only shows every upcoming/ongoing absence plus the
    most recent few past/cancelled ones — not the member's full history.
    """

    def __init__(
        self,
        *,
        bot: discord.Client,
        guild_id: int,
        member_id: int,
        t: "Strings",
        absences: list[Absence],
        hidden_history_count: int,
        can_manage: bool,
        can_delete: bool,
    ) -> None:
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.member_id = member_id
        self.t = t
        self.absences = absences
        self.hidden_history_count = hidden_history_count
        self.can_manage = can_manage
        self.can_delete = can_delete
        self.render()

    @classmethod
    async def build(
        cls, *, bot: discord.Client, guild_id: int, member_id: int, t: "Strings", can_manage: bool, can_delete: bool
    ) -> "AbsenceListView":
        absences, hidden = await _load_absences(guild_id, member_id)
        return cls(
            bot=bot,
            guild_id=guild_id,
            member_id=member_id,
            t=t,
            absences=absences,
            hidden_history_count=hidden,
            can_manage=can_manage,
            can_delete=can_delete,
        )

    def render(self) -> None:
        t = self.t
        self.clear_items()
        if not self.absences:
            self.add_item(_text(t.no_absences))
            return

        today = datetime.now(tz=UTC).date()
        by_status: dict[AbsenceStatus, list[Absence]] = {status: [] for status in AbsenceStatus}
        for absence in self.absences:
            by_status[absence_status(absence, today)].append(absence)

        sections = (
            (t.section_active, [*by_status[AbsenceStatus.ONGOING], *by_status[AbsenceStatus.UPCOMING]], "active"),
            (t.section_past, by_status[AbsenceStatus.PAST], "past"),
            (t.section_cancelled, by_status[AbsenceStatus.CANCELLED], "cancelled"),
        )

        items: list[discord.ui.ViewItem[DesignerView]] = []
        for title, group, kind in sections:
            if not group:
                continue
            if items:
                items.append(Separator[DesignerView]())
            items.append(TextDisplay[DesignerView, Never](f"### {title}"))
            for absence in group:
                items.extend(self._absence_items(absence, kind=kind))

        if self.hidden_history_count:
            items.append(Separator[DesignerView]())
            items.append(TextDisplay[DesignerView, Never](t.hidden_history.format(count=self.hidden_history_count)))

        self.add_item(Container[DesignerView](*items))

    def _absence_items(self, absence: Absence, *, kind: str) -> list[discord.ui.ViewItem[DesignerView]]:
        t = self.t
        days = duration_days(absence.start_date, absence.end_date)
        items: list[discord.ui.ViewItem[DesignerView]] = [
            TextDisplay[DesignerView, Never](
                t.absence_line.format(
                    start=absence.start_date.strftime("%d/%m/%Y"),
                    end=absence.end_date.strftime("%d/%m/%Y"),
                    days=days,
                    plural="" if days == 1 else "s",
                    reason=absence.reason or t.no_reason,
                )
            )
        ]
        buttons: list[discord.ui.Button[DesignerView]] = []
        if self.can_manage and kind == "active":
            buttons.append(_CallbackButton(t.edit, self._edit(absence)))
            buttons.append(_CallbackButton(t.cancel, self._cancel(absence), discord.ButtonStyle.danger))
        if self.can_manage and kind == "cancelled":
            buttons.append(_CallbackButton(t.restore, self._restore(absence)))
        if self.can_delete:
            buttons.append(_CallbackButton(t.delete, self._delete(absence), discord.ButtonStyle.danger))
        if buttons:
            items.append(ActionRow[DesignerView](*buttons))
        return items

    def _edit(self, absence: Absence) -> "_Action":
        async def action(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(
                AbsenceModal(
                    bot=self.bot,
                    guild_id=self.guild_id,
                    member_id=self.member_id,
                    created_by_id=absence.created_by_id,
                    t=self.t,
                    absence=absence,
                    panel=self,
                )
            )

        return action

    def _cancel(self, absence: Absence) -> "_Action":
        async def action(interaction: discord.Interaction) -> None:
            await cancel_absence(absence)
            await remove_announcement(self.bot, absence)
            await self.refresh(interaction)

        return action

    def _restore(self, absence: Absence) -> "_Action":
        async def action(interaction: discord.Interaction) -> None:
            try:
                await restore_absence(absence)
            except OverlapError as e:
                await interaction.response.send_message(
                    self.t.invalid_overlap.format(
                        start=e.conflicting.start_date.strftime("%d/%m/%Y"),
                        end=e.conflicting.end_date.strftime("%d/%m/%Y"),
                    ),
                    ephemeral=True,
                )
                return
            settings = await get_or_create_settings(self.guild_id)
            await sync_announcement(self.bot, absence, settings)
            await self.refresh(interaction)

        return action

    def _delete(self, absence: Absence) -> "_Action":
        async def action(interaction: discord.Interaction) -> None:
            await remove_announcement(self.bot, absence)
            await absence.delete()
            await self.refresh(interaction)

        return action

    async def refresh(self, interaction: discord.Interaction) -> None:
        self.absences, self.hidden_history_count = await _load_absences(self.guild_id, self.member_id)
        self.render()
        await interaction.response.edit_message(view=self)


async def _load_absences(guild_id: int, member_id: int) -> tuple[list[Absence], int]:
    """Load the absences shown in `AbsenceListView`.

    Every upcoming/ongoing absence (soonest first), plus the most recent few past/cancelled ones
    (most recent first). Returns the absences to display and how many older past/cancelled
    entries were left out.
    """
    today = datetime.now(tz=UTC).date()
    active = await (
        Absence.filter(guild_id=guild_id, member_id=member_id, cancelled_at__isnull=True, end_date__gte=today)
        .order_by("start_date", "end_date")
        .limit(MAX_ACTIVE_DISPLAYED)
    )
    # Everything that isn't active (past or cancelled) — filtered directly by status, not by
    # excluding the (possibly truncated) `active` id list, so overflow active rows never leak in.
    history_query = Absence.filter(guild_id=guild_id, member_id=member_id).exclude(
        cancelled_at__isnull=True, end_date__gte=today
    )
    history_total = await history_query.count()
    history = await history_query.order_by("-start_date", "-end_date").limit(MAX_HISTORY_DISPLAYED)
    hidden = max(history_total - len(history), 0)
    return [*active, *history], hidden


@final
class _SettingsSelect(discord.ui.Select[DesignerView]):
    """Edits one `AbsenceSettings` field. Only that field is saved on change."""

    def __init__(self, panel: "ConfigPanelView", field: str, channel_type: discord.ChannelType | None = None) -> None:
        current: int | list[int] | None = getattr(panel.settings, field)
        self.many = isinstance(current, list)
        ids = current if isinstance(current, list) else [current] if current else []
        placeholder = panel.t[f"placeholder_{field}"]
        if channel_type is None:
            defaults = [discord.Object(id=i, type=discord.Role) for i in ids]
            super().__init__(
                discord.ComponentType.role_select,
                placeholder=placeholder,
                min_values=0,
                max_values=25 if self.many else 1,
                default_values=defaults,
            )
        else:
            super().__init__(
                discord.ComponentType.channel_select,
                placeholder=placeholder,
                channel_types=[channel_type],
                min_values=0,
                max_values=1,
                default_values=[discord.Object(id=i, type=discord.abc.GuildChannel) for i in ids],
            )
        self.panel = panel
        self.field = field

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        ids = [value.id for value in self.values or []]
        setattr(self.panel.settings, self.field, ids if self.many else next(iter(ids), None))
        await self.panel.settings.save(update_fields=[self.field])
        self.panel.render()
        await interaction.response.edit_message(view=self.panel)


@final
class ConfigPanelView(DesignerView):
    """Admin panel: who can self-declare, and where absences get announced."""

    def __init__(self, guild_id: int, t: "Strings", settings: AbsenceSettings) -> None:
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.t = t
        self.settings = settings
        self.render()

    @classmethod
    async def build(cls, guild_id: int, t: "Strings") -> "ConfigPanelView":
        settings = await get_or_create_settings(guild_id)
        return cls(guild_id, t, settings)

    def render(self) -> None:
        s, t = self.settings, self.t
        self.clear_items()
        self.add_item(
            _text(
                t.config_summary.format(
                    allowed_roles=", ".join(f"<@&{r}>" for r in s.allowed_role_ids) or t.none,
                    announce_channel=f"<#{s.announce_channel_id}>" if s.announce_channel_id else t.not_set,
                    responsible_role=f"<@&{s.responsible_role_id}>" if s.responsible_role_id else t.not_set,
                )
            )
        )
        self.add_item(ActionRow[DesignerView](_SettingsSelect(self, "allowed_role_ids")))
        self.add_item(ActionRow[DesignerView](_SettingsSelect(self, "announce_channel_id", discord.ChannelType.text)))
        self.add_item(ActionRow[DesignerView](_SettingsSelect(self, "responsible_role_id")))


__all__ = ("AbsenceListView", "AbsenceModal", "ConfigPanelView")
