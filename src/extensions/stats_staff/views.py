# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Never, final, override

import discord
from discord.ui import ActionRow, Container, DesignerModal, DesignerView, TextDisplay

from src.database.models import StaffMemberRoleOverride, StaffQuotaMode, StaffRoleQuota, StaffStatsSettings

from .stats import get_or_create_settings

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from .stats import Strings
    from .tracking import TrackingCog

    type _Action = Callable[[discord.Interaction], Awaitable[None]]


def _text(content: str) -> Container[DesignerView]:
    return Container[DesignerView](TextDisplay[DesignerView, Never](content))


def _mode_label(mode: StaffQuotaMode) -> str:
    return "ET" if mode == StaffQuotaMode.ALL else "OU"


def _parse_number(raw: str | None) -> float | None:
    try:
        value = float((raw or "").replace(",", "."))
    except ValueError:
        return None
    return value if math.isfinite(value) and value >= 0 else None


@final
class QuotaModal(DesignerModal):
    def __init__(self, panel: QuotaPanelView, role: discord.Role) -> None:
        self.panel = panel
        self.role = role
        t = panel.t
        quota = next((q for q in panel.quotas if q.role_id == role.id), None)
        super().__init__(title=t.quota_modal_title.format(role=role.name)[:45])
        self.hours_input = discord.ui.TextInput(
            style=discord.InputTextStyle.short, value=f"{quota.voice_minutes_required / 60:g}" if quota else "0"
        )
        self.messages_input = discord.ui.TextInput(
            style=discord.InputTextStyle.short, value=str(quota.messages_required) if quota else "0"
        )
        self.mode_select = discord.ui.StringSelect(
            options=[
                discord.SelectOption(
                    label=t[f"mode_{mode.value}"], value=mode.value, default=quota is not None and quota.mode == mode
                )
                for mode in StaffQuotaMode
            ]
        )
        self.add_item(discord.ui.Label(label=t.quota_modal_hours, item=self.hours_input))
        self.add_item(discord.ui.Label(label=t.quota_modal_messages, item=self.messages_input))
        self.add_item(discord.ui.Label(label=t.quota_modal_mode, item=self.mode_select))

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        hours = _parse_number(self.hours_input.value)
        messages = _parse_number(self.messages_input.value)
        if hours is None or messages is None or not self.mode_select.values:
            await interaction.respond(self.panel.t.invalid_number, ephemeral=True)
            return
        quota, _ = await StaffRoleQuota.update_or_create(
            guild_id=self.panel.guild.id,
            role_id=self.role.id,
            defaults={
                "voice_minutes_required": round(hours * 60),
                "messages_required": int(messages),
                "mode": StaffQuotaMode(self.mode_select.values[0]),
            },
        )
        self.panel.quotas = [q for q in self.panel.quotas if q.role_id != self.role.id] + [quota]
        await self.panel.saved(interaction)


@final
class PenaltyModal(DesignerModal):
    def __init__(self, panel: ConfigPanelView) -> None:
        self.panel = panel
        super().__init__(title=panel.t.penalty_modal_title)
        self.penalty_input = discord.ui.TextInput(
            style=discord.InputTextStyle.short, value=f"{panel.settings.et_substitution_penalty * 100:g}"
        )
        self.add_item(
            discord.ui.Label(
                label=panel.t.penalty_modal_label,
                description=panel.t.penalty_modal_description,
                item=self.penalty_input,
            )
        )

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        percent = _parse_number(self.penalty_input.value)
        if percent is None:
            await interaction.respond(self.panel.t.invalid_number, ephemeral=True)
            return
        self.panel.settings.et_substitution_penalty = percent / 100
        await self.panel.settings.save(update_fields=["et_substitution_penalty"])
        await self.panel.saved(interaction)


@final
class _SettingsSelect(discord.ui.Select[DesignerView]):
    """Edits one settings field. Only that field is saved, so two open panels can't overwrite each other."""

    def __init__(self, panel: ConfigPanelView, field: str, channel_type: discord.ChannelType | None = None) -> None:
        current: int | list[int] | None = getattr(panel.settings, field)
        self.many = isinstance(current, list)
        ids = current if isinstance(current, list) else [current] if current else []
        placeholder = panel.t[f"placeholder_{field}"]
        if channel_type is None:
            defaults = [discord.Object(id=i, type=discord.Role) for i in ids]
            super().__init__(discord.ComponentType.role_select, placeholder=placeholder, default_values=defaults)
        else:
            super().__init__(
                discord.ComponentType.channel_select,
                placeholder=placeholder,
                channel_types=[channel_type],
                min_values=0 if self.many else 1,
                max_values=25 if self.many else 1,
                default_values=[discord.Object(id=i, type=discord.abc.GuildChannel) for i in ids],
            )
        self.panel = panel
        self.field = field

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        ids = [value.id for value in self.values or []]
        setattr(self.panel.settings, self.field, ids if self.many else next(iter(ids), None))
        await self.panel.settings.save(update_fields=[self.field])
        await self.panel.saved(interaction)


@final
class _CallbackButton(discord.ui.Button[DesignerView]):
    """A button that runs `action(interaction)`; avoids one subclass per button."""

    def __init__(self, label: str, action: _Action, style: discord.ButtonStyle = discord.ButtonStyle.secondary) -> None:
        super().__init__(label=label, style=style)
        self.action = action

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        await self.action(interaction)


class _Panel(DesignerView):
    def __init__(self, guild: discord.Guild, tracking: TrackingCog, t: Strings) -> None:
        super().__init__(timeout=300)
        self.guild: discord.Guild = guild
        self.tracking: TrackingCog = tracking
        self.t: Strings = t

    def render(self) -> None:
        raise NotImplementedError

    async def saved(self, interaction: discord.Interaction) -> None:
        """Refresh this panel after a change and let tracking pick it up right away."""
        await self.tracking.reload_config(self.guild.id)
        self.render()
        await interaction.response.edit_message(view=self)

    async def show(self, interaction: discord.Interaction, view: DesignerView) -> None:
        await interaction.response.edit_message(view=view)


@final
class ConfigPanelView(_Panel):
    def __init__(
        self,
        guild: discord.Guild,
        tracking: TrackingCog,
        t: Strings,
        settings: StaffStatsSettings,
        quotas: list[StaffRoleQuota],
    ) -> None:
        super().__init__(guild, tracking, t)
        self.settings = settings
        self.quotas = quotas
        self.render()

    @classmethod
    async def build(cls, guild: discord.Guild, tracking: TrackingCog, t: Strings) -> ConfigPanelView:
        settings = await get_or_create_settings(guild.id)
        return cls(guild, tracking, t, settings, await StaffRoleQuota.filter(guild_id=guild.id))

    @override
    def render(self) -> None:
        s, t = self.settings, self.t
        self.clear_items()
        self.add_item(
            _text(
                t.config_summary.format(
                    responsible=f"<@&{s.responsible_role_id}>" if s.responsible_role_id else t.not_set,
                    report_channel=f"<#{s.report_channel_id}>" if s.report_channel_id else t.not_set,
                    message_channels=", ".join(f"<#{c}>" for c in s.message_channel_ids) or t.none,
                    voice_channels=", ".join(f"<#{c}>" for c in s.voice_channel_ids) or t.none,
                    categories=", ".join(f"<#{c}>" for c in s.tracked_category_ids) or t.none,
                    quotas=len(self.quotas),
                    penalty=f"{s.et_substitution_penalty * 100:g}",
                )
            )
        )
        for item in (
            _SettingsSelect(self, "responsible_role_id"),
            _SettingsSelect(self, "report_channel_id", discord.ChannelType.text),
            _SettingsSelect(self, "message_channel_ids", discord.ChannelType.text),
            _SettingsSelect(self, "voice_channel_ids", discord.ChannelType.voice),
            _SettingsSelect(self, "tracked_category_ids", discord.ChannelType.category),
            _CallbackButton(t.open_quotas, self.open_quotas, discord.ButtonStyle.primary),
            _CallbackButton(t.edit_penalty, self.edit_penalty),
        ):
            self.add_item(ActionRow[DesignerView](item))

    async def open_quotas(self, interaction: discord.Interaction) -> None:
        await self.show(interaction, QuotaPanelView(self.guild, self.tracking, self.t, self.quotas))

    async def edit_penalty(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(PenaltyModal(self))


@final
class _QuotaRoleSelect(discord.ui.Select[DesignerView]):
    def __init__(self, panel: QuotaPanelView, *, remove: bool) -> None:
        super().__init__(
            select_type=discord.ComponentType.role_select,
            placeholder=panel.t.remove_quota_placeholder if remove else panel.t.edit_quota_placeholder,
        )
        self.panel = panel
        self.remove = remove

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        role = (self.values or [None])[0]
        if not isinstance(role, discord.Role):
            return
        if not self.remove:
            await interaction.response.send_modal(QuotaModal(self.panel, role))
            return
        await StaffRoleQuota.filter(guild_id=self.panel.guild.id, role_id=role.id).delete()
        self.panel.quotas = [q for q in self.panel.quotas if q.role_id != role.id]
        await self.panel.saved(interaction)


@final
class QuotaPanelView(_Panel):
    def __init__(self, guild: discord.Guild, tracking: TrackingCog, t: Strings, quotas: list[StaffRoleQuota]) -> None:
        super().__init__(guild, tracking, t)
        self.quotas = quotas
        self.render()

    @override
    def render(self) -> None:
        t = self.t
        self.clear_items()
        lines = [t.quotas_title]
        lines += [
            t.quota_line.format(
                role=f"<@&{q.role_id}>",
                hours=f"{q.voice_minutes_required / 60:g}",
                mode=_mode_label(q.mode),
                messages=q.messages_required,
            )
            for q in self.quotas
        ] or [t.no_quotas]
        self.add_item(_text("\n".join(lines)))
        items: list[discord.ui.ViewItem[DesignerView]] = [_QuotaRoleSelect(self, remove=False)]
        if self.quotas:
            items.append(_QuotaRoleSelect(self, remove=True))
        items += [_CallbackButton(t.back, self.back), _CallbackButton(t.open_assign, self.open_assign)]
        for item in items:
            self.add_item(ActionRow[DesignerView](item))

    async def back(self, interaction: discord.Interaction) -> None:
        await self.show(interaction, await ConfigPanelView.build(self.guild, self.tracking, self.t))

    async def open_assign(self, interaction: discord.Interaction) -> None:
        await self.show(interaction, await MemberRoleAssignView.build(self.guild, self.tracking, self.t, self.quotas))


@final
class _AssignSelect(discord.ui.Select[DesignerView]):
    def __init__(self, panel: MemberRoleAssignView, *, pick_role: bool) -> None:
        pending = panel.pending_role_id if pick_role else panel.pending_member_id
        object_type = discord.Role if pick_role else discord.Member
        super().__init__(
            select_type=discord.ComponentType.role_select if pick_role else discord.ComponentType.user_select,
            placeholder=panel.t.assign_role_placeholder if pick_role else panel.t.assign_member_placeholder,
            default_values=[discord.Object(id=pending, type=object_type)] if pending else [],
        )
        self.panel = panel
        self.pick_role = pick_role

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        picked = self.values[0].id if self.values else None
        if not self.pick_role:
            self.panel.pending_member_id = picked
        elif picked is not None and picked not in {q.role_id for q in self.panel.quotas}:
            await interaction.respond(self.panel.t.role_without_quota, ephemeral=True)
            return
        else:
            self.panel.pending_role_id = picked
        await self.panel.save_if_ready(interaction)


@final
class MemberRoleAssignView(_Panel):
    """Lets an admin pin which quota role applies to a member who has several."""

    def __init__(
        self,
        guild: discord.Guild,
        tracking: TrackingCog,
        t: Strings,
        quotas: list[StaffRoleQuota],
        overrides: dict[int, int],
    ) -> None:
        super().__init__(guild, tracking, t)
        self.quotas = quotas
        self.overrides = overrides
        self.pending_member_id: int | None = None
        self.pending_role_id: int | None = None
        self.render()

    @classmethod
    async def build(
        cls, guild: discord.Guild, tracking: TrackingCog, t: Strings, quotas: list[StaffRoleQuota]
    ) -> MemberRoleAssignView:
        overrides = dict(await StaffMemberRoleOverride.filter(guild_id=guild.id).values_list("member_id", "role_id"))
        return cls(guild, tracking, t, quotas, overrides)

    @override
    def render(self) -> None:
        t = self.t
        self.clear_items()
        quota_role_ids = {q.role_id for q in self.quotas}
        ambiguous = [m for m in self.guild.members if not m.bot and sum(r.id in quota_role_ids for r in m.roles) > 1]
        lines = [t.assign_title]
        lines += [
            f"- {m.mention} " + (f"→ <@&{self.overrides[m.id]}>" if m.id in self.overrides else t.to_assign)
            for m in ambiguous
        ] or [t.no_ambiguous_members]
        self.add_item(_text("\n".join(lines)))
        for item in (
            _AssignSelect(self, pick_role=False),
            _AssignSelect(self, pick_role=True),
            _CallbackButton(t.back, self.back),
        ):
            self.add_item(ActionRow[DesignerView](item))

    async def back(self, interaction: discord.Interaction) -> None:
        await self.show(interaction, QuotaPanelView(self.guild, self.tracking, self.t, self.quotas))

    async def save_if_ready(self, interaction: discord.Interaction) -> None:
        if self.pending_member_id is not None and self.pending_role_id is not None:
            await StaffMemberRoleOverride.update_or_create(
                guild_id=self.guild.id, member_id=self.pending_member_id, defaults={"role_id": self.pending_role_id}
            )
            self.overrides[self.pending_member_id] = self.pending_role_id
            self.pending_member_id = self.pending_role_id = None
        self.render()
        await interaction.response.edit_message(view=self)


__all__ = ("ConfigPanelView",)
