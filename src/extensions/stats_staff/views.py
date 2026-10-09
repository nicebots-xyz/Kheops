# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

import math
from typing import final, override

import discord

from src.database.models import StaffMemberRoleOverride, StaffQuotaMode, StaffRoleQuota, StaffStatsSettings

from .stats import get_or_create_settings

MODE_CHOICES = [
    discord.OptionChoice("OU (vocal OU messages)", StaffQuotaMode.ANY.value),
    discord.OptionChoice("ET (vocal ET messages)", StaffQuotaMode.ALL.value),
]


@final
class QuotaModal(discord.ui.DesignerModal):
    def __init__(self, role: discord.Role, quota: StaffRoleQuota | None) -> None:
        self.role = role
        self.quota = quota
        super().__init__(title=f"Quota pour {role.name}"[:45])

        self.hours_input = discord.ui.TextInput(
            required=True,
            style=discord.InputTextStyle.short,
            value=f"{quota.voice_minutes_required / 60:g}" if quota else "0",
        )
        self.add_item(
            discord.ui.Label(label="Heures de vocal requises / semaine", item=self.hours_input),
        )

        self.messages_input = discord.ui.TextInput(
            required=True,
            style=discord.InputTextStyle.short,
            value=str(quota.messages_required) if quota else "0",
        )
        self.add_item(
            discord.ui.Label(label="Messages requis / semaine", item=self.messages_input),
        )

        self.mode_select = discord.ui.StringSelect(
            required=True,
            options=[
                discord.SelectOption(
                    label=choice.name,
                    value=str(choice.value),
                    default=quota is not None and quota.mode.value == str(choice.value),
                )
                for choice in MODE_CHOICES
            ],
            min_values=1,
            max_values=1,
        )
        self.add_item(discord.ui.Label(label="Condition", item=self.mode_select))

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        assert self.hours_input.value is not None
        assert self.messages_input.value is not None
        assert self.mode_select.values is not None

        try:
            hours = float(self.hours_input.value.replace(",", "."))
            messages_required = int(self.messages_input.value)
        except ValueError:
            await interaction.respond("Les heures et messages doivent être des nombres.", ephemeral=True)
            return
        if not math.isfinite(hours) or hours < 0 or messages_required < 0:
            await interaction.respond("Les valeurs doivent être des nombres positifs et finis.", ephemeral=True)
            return

        mode = StaffQuotaMode(self.mode_select.values[0])
        voice_minutes_required = round(hours * 60)

        quota, _ = await StaffRoleQuota.get_or_create(
            guild_id=interaction.guild.id,
            role_id=self.role.id,
            defaults={
                "voice_minutes_required": voice_minutes_required,
                "messages_required": messages_required,
                "mode": mode,
            },
        )
        quota.voice_minutes_required = voice_minutes_required
        quota.messages_required = messages_required
        quota.mode = mode
        await quota.save()

        await interaction.respond(f"Quota enregistré pour {self.role.mention}.", ephemeral=True)


@final
class PenaltyModal(discord.ui.DesignerModal):
    def __init__(self, settings: StaffStatsSettings) -> None:
        self.settings = settings
        super().__init__(title="Pénalité de substitution (ET)")

        self.penalty_input = discord.ui.TextInput(
            required=True,
            style=discord.InputTextStyle.short,
            value=f"{settings.et_substitution_penalty * 100:g}",
        )
        self.add_item(
            discord.ui.Label(
                label="Surcoût (%) de substitution",
                description="Ex: 125 veut dire que sauter un critère demande 125% de plus sur l'autre.",
                item=self.penalty_input,
            ),
        )

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.penalty_input.value is not None
        try:
            percent = float(self.penalty_input.value.replace(",", "."))
        except ValueError:
            await interaction.respond("La pénalité doit être un nombre.", ephemeral=True)
            return
        if not math.isfinite(percent) or percent < 0:
            await interaction.respond("La pénalité doit être un nombre positif ou nul, et fini.", ephemeral=True)
            return

        self.settings.et_substitution_penalty = percent / 100
        await self.settings.save()
        await interaction.respond(f"Pénalité de substitution mise à jour : {percent:g}%.", ephemeral=True)


@final
class _AddOrEditQuotaSelect(discord.ui.Select):
    def __init__(self, panel: QuotaPanelView) -> None:
        super().__init__(
            select_type=discord.ComponentType.role_select,
            placeholder="Ajouter ou modifier un quota pour un rôle…",
        )
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.values is not None
        role = self.values[0]
        assert isinstance(role, discord.Role)
        existing = next((q for q in self.panel.quotas if q.role_id == role.id), None)
        await interaction.response.send_modal(QuotaModal(role, existing))


@final
class _RemoveQuotaSelect(discord.ui.Select):
    def __init__(self, panel: QuotaPanelView) -> None:
        super().__init__(
            select_type=discord.ComponentType.role_select,
            placeholder="Retirer le quota d'un rôle…",
        )
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.values is not None
        role = self.values[0]
        assert isinstance(role, discord.Role)
        await StaffRoleQuota.filter(guild_id=self.panel.guild.id, role_id=role.id).delete()
        self.panel.quotas = [q for q in self.panel.quotas if q.role_id != role.id]
        self.panel.render()
        await interaction.response.edit_message(view=self.panel)


@final
class _QuotaPanelBackButton(discord.ui.Button["QuotaPanelView"]):
    def __init__(self, panel: QuotaPanelView) -> None:
        super().__init__(label="Retour", style=discord.ButtonStyle.secondary)
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        view = await ConfigPanelView.build(self.panel.guild)
        await interaction.response.edit_message(view=view)


@final
class _OpenAssignButton(discord.ui.Button["QuotaPanelView"]):
    def __init__(self, panel: QuotaPanelView) -> None:
        super().__init__(label="Assigner les membres à rôles multiples", style=discord.ButtonStyle.secondary)
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        view = await MemberRoleAssignView.build(self.panel.guild, self.panel.quotas)
        await interaction.response.edit_message(view=view)


@final
class QuotaPanelView(discord.ui.DesignerView):
    def __init__(self, guild: discord.Guild, quotas: list[StaffRoleQuota]) -> None:
        super().__init__(timeout=300)
        self.guild = guild
        self.quotas = quotas
        self.render()

    def render(self) -> None:
        self.clear_items()
        lines = ["## Quotas par rôle"]
        if self.quotas:
            for quota in self.quotas:
                mode_label = "ET" if quota.mode == StaffQuotaMode.ALL else "OU"
                lines.append(
                    f"- <@&{quota.role_id}> : {quota.voice_minutes_required / 60:g}h vocal **{mode_label}** "
                    + f"{quota.messages_required} messages / semaine"
                )
        else:
            lines.append("- Aucun quota configuré pour le moment.")
        self.add_item(discord.ui.Container(discord.ui.TextDisplay("\n".join(lines))))  # pyright: ignore[reportUnknownArgumentType]
        self.add_item(discord.ui.ActionRow(_AddOrEditQuotaSelect(self)))  # pyright: ignore[reportUnknownArgumentType]

        if {quota.role_id for quota in self.quotas}:
            self.add_item(discord.ui.ActionRow(_RemoveQuotaSelect(self)))  # pyright: ignore[reportUnknownArgumentType]

        self.add_item(discord.ui.ActionRow(_QuotaPanelBackButton(self)))  # pyright: ignore[reportUnknownArgumentType]
        self.add_item(discord.ui.ActionRow(_OpenAssignButton(self)))  # pyright: ignore[reportUnknownArgumentType]


@final
class _MemberAssignSelect(discord.ui.Select):
    def __init__(self, panel: MemberRoleAssignView) -> None:
        default = [discord.Object(id=panel.pending_member_id, type=discord.Member)] if panel.pending_member_id else []
        super().__init__(
            select_type=discord.ComponentType.user_select,
            placeholder="Choisir le membre à assigner…",
            default_values=default,
        )
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.values is not None
        self.panel.pending_member_id = self.values[0].id if self.values else None
        await self.panel.save_if_ready(interaction)


@final
class _RoleAssignSelect(discord.ui.Select):
    def __init__(self, panel: MemberRoleAssignView) -> None:
        default = [discord.Object(id=panel.pending_role_id, type=discord.Role)] if panel.pending_role_id else []
        super().__init__(
            select_type=discord.ComponentType.role_select,
            placeholder="Choisir son rôle quota…",
            default_values=default,
        )
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.values is not None
        role_id = self.values[0].id if self.values else None
        quota_role_ids = {quota.role_id for quota in self.panel.quotas}
        if role_id is not None and role_id not in quota_role_ids:
            await interaction.response.send_message(
                "Ce rôle n'a pas de quota configuré — choisis un rôle qui a un quota.", ephemeral=True
            )
            return
        self.panel.pending_role_id = role_id
        await self.panel.save_if_ready(interaction)


@final
class _MemberAssignBackButton(discord.ui.Button["MemberRoleAssignView"]):
    def __init__(self, panel: MemberRoleAssignView) -> None:
        super().__init__(label="Retour", style=discord.ButtonStyle.secondary)
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        view = QuotaPanelView(self.panel.guild, self.panel.quotas)
        await interaction.response.edit_message(view=view)


@final
class MemberRoleAssignView(discord.ui.DesignerView):
    """Lets an admin pin which configured quota role applies to a member who has several."""

    def __init__(
        self,
        guild: discord.Guild,
        quotas: list[StaffRoleQuota],
        ambiguous_members: list[discord.Member],
        overrides: list[StaffMemberRoleOverride],
    ) -> None:
        super().__init__(timeout=300)
        self.guild = guild
        self.quotas = quotas
        self.ambiguous_members = ambiguous_members
        self.overrides = overrides
        self.pending_member_id: int | None = None
        self.pending_role_id: int | None = None
        self.render()

    @classmethod
    async def build(cls, guild: discord.Guild, quotas: list[StaffRoleQuota]) -> MemberRoleAssignView:
        quota_role_ids = {quota.role_id for quota in quotas}
        ambiguous_members = [
            member
            for member in guild.members
            if not member.bot and sum(1 for role in member.roles if role.id in quota_role_ids) > 1
        ]
        overrides = await StaffMemberRoleOverride.filter(guild_id=guild.id)
        return cls(guild, quotas, ambiguous_members, overrides)

    def render(self) -> None:
        self.clear_items()
        overrides_by_member_id = {override.member_id: override.role_id for override in self.overrides}
        lines = ["## Membres avec plusieurs rôles quota"]
        if self.ambiguous_members:
            for member in self.ambiguous_members:
                role_id = overrides_by_member_id.get(member.id)
                status = f"→ <@&{role_id}>" if role_id else "⚠️ à assigner"
                lines.append(f"- {member.mention} {status}")
        else:
            lines.append("- Aucun membre n'a actuellement plusieurs rôles avec quota configuré.")
        self.add_item(discord.ui.Container(discord.ui.TextDisplay("\n".join(lines))))  # pyright: ignore[reportUnknownArgumentType]
        self.add_item(discord.ui.ActionRow(_MemberAssignSelect(self)))  # pyright: ignore[reportUnknownArgumentType]
        self.add_item(discord.ui.ActionRow(_RoleAssignSelect(self)))  # pyright: ignore[reportUnknownArgumentType]
        self.add_item(discord.ui.ActionRow(_MemberAssignBackButton(self)))  # pyright: ignore[reportUnknownArgumentType]

    async def save_if_ready(self, interaction: discord.Interaction) -> None:
        if self.pending_member_id is not None and self.pending_role_id is not None:
            await StaffMemberRoleOverride.update_or_create(
                guild_id=self.guild.id,
                member_id=self.pending_member_id,
                defaults={"role_id": self.pending_role_id},
            )
            self.overrides = await StaffMemberRoleOverride.filter(guild_id=self.guild.id)
            self.pending_member_id = None
            self.pending_role_id = None
        self.render()
        await interaction.response.edit_message(view=self)


@final
class _ResponsibleRoleSelect(discord.ui.Select):
    def __init__(self, panel: ConfigPanelView) -> None:
        role_id = panel.settings.responsible_role_id
        default = [discord.Object(id=role_id, type=discord.Role)] if role_id else []
        super().__init__(
            select_type=discord.ComponentType.role_select,
            placeholder="Changer le rôle responsable…",
            default_values=default,
        )
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.values is not None
        self.panel.settings.responsible_role_id = self.values[0].id if self.values else None
        await self.panel.settings.save()
        self.panel.render()
        await interaction.response.edit_message(view=self.panel)


@final
class _ReportChannelSelect(discord.ui.Select):
    def __init__(self, panel: ConfigPanelView) -> None:
        channel_id = panel.settings.report_channel_id
        default = [discord.Object(id=channel_id, type=discord.abc.GuildChannel)] if channel_id else []
        super().__init__(
            select_type=discord.ComponentType.channel_select,
            placeholder="Changer le salon de rapport hebdo…",
            channel_types=[discord.ChannelType.text],
            default_values=default,
        )
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.values is not None
        self.panel.settings.report_channel_id = self.values[0].id if self.values else None
        await self.panel.settings.save()
        self.panel.render()
        await interaction.response.edit_message(view=self.panel)


@final
class _MessageChannelsSelect(discord.ui.Select):
    def __init__(self, panel: ConfigPanelView) -> None:
        default = [discord.Object(id=c, type=discord.abc.GuildChannel) for c in panel.settings.message_channel_ids]
        super().__init__(
            select_type=discord.ComponentType.channel_select,
            placeholder="Changer les salons suivis (messages)…",
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=25,
            default_values=default,
        )
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.values is not None
        self.panel.settings.message_channel_ids = [c.id for c in self.values]
        await self.panel.settings.save()
        self.panel.render()
        await interaction.response.edit_message(view=self.panel)


@final
class _VoiceChannelsSelect(discord.ui.Select):
    def __init__(self, panel: ConfigPanelView) -> None:
        default = [discord.Object(id=c, type=discord.abc.GuildChannel) for c in panel.settings.voice_channel_ids]
        super().__init__(
            select_type=discord.ComponentType.channel_select,
            placeholder="Changer les salons suivis (vocal)…",
            channel_types=[discord.ChannelType.voice],
            min_values=0,
            max_values=25,
            default_values=default,
        )
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.values is not None
        self.panel.settings.voice_channel_ids = [c.id for c in self.values]
        await self.panel.settings.save()
        self.panel.render()
        await interaction.response.edit_message(view=self.panel)


@final
class _OpenQuotasButton(discord.ui.Button["ConfigPanelView"]):
    def __init__(self, panel: ConfigPanelView) -> None:
        super().__init__(label="Gérer les quotas par rôle", style=discord.ButtonStyle.primary)
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        view = QuotaPanelView(self.panel.guild, self.panel.quotas)
        await interaction.response.edit_message(view=view)


@final
class _EditPenaltyButton(discord.ui.Button["ConfigPanelView"]):
    def __init__(self, panel: ConfigPanelView) -> None:
        super().__init__(label="Pénalité de substitution (ET)", style=discord.ButtonStyle.secondary)
        self.panel = panel

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(PenaltyModal(self.panel.settings))


@final
class ConfigPanelView(discord.ui.DesignerView):
    def __init__(self, guild: discord.Guild, settings: StaffStatsSettings, quotas: list[StaffRoleQuota]) -> None:
        super().__init__(timeout=300)
        self.guild = guild
        self.settings = settings
        self.quotas = quotas
        self.render()

    @classmethod
    async def build(cls, guild: discord.Guild) -> ConfigPanelView:
        settings = await get_or_create_settings(guild.id)
        quotas = await StaffRoleQuota.filter(guild_id=guild.id)
        return cls(guild, settings, quotas)

    def render(self) -> None:
        self.clear_items()
        self.add_item(discord.ui.Container(discord.ui.TextDisplay(self._summary())))  # pyright: ignore[reportUnknownArgumentType]
        self.add_item(discord.ui.ActionRow(_ResponsibleRoleSelect(self)))  # pyright: ignore[reportUnknownArgumentType]
        self.add_item(discord.ui.ActionRow(_ReportChannelSelect(self)))  # pyright: ignore[reportUnknownArgumentType]
        self.add_item(discord.ui.ActionRow(_MessageChannelsSelect(self)))  # pyright: ignore[reportUnknownArgumentType]
        self.add_item(discord.ui.ActionRow(_VoiceChannelsSelect(self)))  # pyright: ignore[reportUnknownArgumentType]
        self.add_item(discord.ui.ActionRow(_OpenQuotasButton(self)))  # pyright: ignore[reportUnknownArgumentType]
        self.add_item(discord.ui.ActionRow(_EditPenaltyButton(self)))  # pyright: ignore[reportUnknownArgumentType]

    def _summary(self) -> str:
        s = self.settings
        responsible = f"<@&{s.responsible_role_id}>" if s.responsible_role_id else "non défini"
        report_channel = f"<#{s.report_channel_id}>" if s.report_channel_id else "non défini"
        message_channels = ", ".join(f"<#{c}>" for c in s.message_channel_ids) or "aucun"
        voice_channels = ", ".join(f"<#{c}>" for c in s.voice_channel_ids) or "aucun"
        lines = [
            "## Configuration des stats staff",
            f"- Rôle responsable : {responsible}",
            f"- Salon de rapport hebdo : {report_channel}",
            f"- Salons suivis (messages) : {message_channels}",
            f"- Salons suivis (vocal) : {voice_channels}",
            f"- Rôles avec quota configuré : {len(self.quotas)}",
            f"- Pénalité de substitution (ET) : {s.et_substitution_penalty * 100:g}%",
        ]
        return "\n".join(lines)


__all__ = (
    "ConfigPanelView",
    "MemberRoleAssignView",
    "PenaltyModal",
    "QuotaModal",
    "QuotaPanelView",
)
