# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self, final, override

import discord
from discord.ext import tasks
from discord.utils import format_dt

from src.database.models import (
    StaffMemberRoleOverride,
    StaffMessageEvent,
    StaffQuotaMode,
    StaffRoleQuota,
    StaffStatsSettings,
    StaffVoiceSegment,
)
from src.log import logger as base_logger

from .logic import (
    EUROPE_PARIS,
    StatsPeriod,
    completion_ratio,
    et_full_substitution,
    evaluate_quota,
    overlapping_minutes,
    period_start,
    previous_week_bounds,
    progress_bar,
    should_send_weekly_report,
    trend_arrow,
    week_start,
)

if TYPE_CHECKING:
    from uuid import UUID

    from src import custom

logger = base_logger.getChild("stats_staff")

PERIOD_CHOICES = [
    discord.OptionChoice("Semaine en cours", StatsPeriod.WEEK.value),
    discord.OptionChoice("Mois en cours", StatsPeriod.MONTH.value),
    discord.OptionChoice("3 derniers mois", StatsPeriod.LAST_3_MONTHS.value),
    discord.OptionChoice("6 derniers mois", StatsPeriod.LAST_6_MONTHS.value),
    discord.OptionChoice("Depuis toujours", StatsPeriod.ALL_TIME.value),
]
PERIOD_LABELS = {StatsPeriod(choice.value): choice.name for choice in PERIOD_CHOICES}

MODE_CHOICES = [
    discord.OptionChoice("OU (vocal OU messages)", StaffQuotaMode.ANY.value),
    discord.OptionChoice("ET (vocal ET messages)", StaffQuotaMode.ALL.value),
]


async def _compute_stats_range(
    guild_id: int, member_id: int, start: datetime | None, end: datetime
) -> tuple[int, float]:
    messages_query = StaffMessageEvent.filter(guild_id=guild_id, member_id=member_id, created_at__lt=end)
    if start is not None:
        messages_query = messages_query.filter(created_at__gte=start)
    messages = await messages_query.count()

    segments = await StaffVoiceSegment.filter(guild_id=guild_id, member_id=member_id, started_at__lt=end)
    voice_minutes = sum(overlapping_minutes(s.started_at, s.ended_at, start, end) for s in segments)
    return messages, voice_minutes


async def _compute_stats(guild_id: int, member_id: int, period: StatsPeriod, now: datetime) -> tuple[int, float]:
    start = period_start(period, now)
    return await _compute_stats_range(guild_id, member_id, start, now)


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
        if hours < 0 or messages_required < 0:
            await interaction.respond("Les valeurs doivent être positives.", ephemeral=True)
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
        if percent < 0:
            await interaction.respond("La pénalité doit être positive ou nulle.", ephemeral=True)
            return

        self.settings.et_substitution_penalty = percent / 100
        await self.settings.save()
        await interaction.respond(f"Pénalité de substitution mise à jour : {percent:g}%.", ephemeral=True)


@final
class QuotaPanelView(discord.ui.DesignerView):
    def __init__(self, guild: discord.Guild, quotas: list[StaffRoleQuota]) -> None:
        super().__init__(timeout=300)
        self.guild = guild
        self.quotas = quotas
        self._render()

    def _render(self) -> None:
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

        add_select = discord.ui.RoleSelect(
            placeholder="Ajouter ou modifier un quota pour un rôle…",
        )

        async def on_add_or_edit(interaction: discord.Interaction) -> None:
            assert add_select.values is not None
            role = add_select.values[0]
            assert isinstance(role, discord.Role)
            existing = next((q for q in self.quotas if q.role_id == role.id), None)
            await interaction.response.send_modal(QuotaModal(role, existing))

        add_select.callback = on_add_or_edit
        self.add_item(discord.ui.ActionRow(add_select))  # pyright: ignore[reportUnknownArgumentType]

        configured_role_ids = {quota.role_id for quota in self.quotas}
        if configured_role_ids:
            remove_select = discord.ui.RoleSelect(
                placeholder="Retirer le quota d'un rôle…",
            )

            async def on_remove(interaction: discord.Interaction) -> None:
                assert remove_select.values is not None
                role = remove_select.values[0]
                assert isinstance(role, discord.Role)
                await StaffRoleQuota.filter(guild_id=self.guild.id, role_id=role.id).delete()
                self.quotas = [q for q in self.quotas if q.role_id != role.id]
                self._render()
                await interaction.response.edit_message(view=self)

            remove_select.callback = on_remove
            self.add_item(discord.ui.ActionRow(remove_select))  # pyright: ignore[reportUnknownArgumentType]

        back_button: discord.ui.Button[Self] = discord.ui.Button(label="Retour", style=discord.ButtonStyle.secondary)

        async def on_back(interaction: discord.Interaction) -> None:
            view = await ConfigPanelView.build(self.guild)
            await interaction.response.edit_message(view=view)

        back_button.callback = on_back
        self.add_item(discord.ui.ActionRow(back_button))  # pyright: ignore[reportUnknownArgumentType]

        assign_button: discord.ui.Button[Self] = discord.ui.Button(
            label="Assigner les membres à rôles multiples", style=discord.ButtonStyle.secondary
        )

        async def on_open_assign(interaction: discord.Interaction) -> None:
            view = await MemberRoleAssignView.build(self.guild, self.quotas)
            await interaction.response.edit_message(view=view)

        assign_button.callback = on_open_assign
        self.add_item(discord.ui.ActionRow(assign_button))  # pyright: ignore[reportUnknownArgumentType]


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
        self._render()

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

    def _render(self) -> None:
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

        member_default = (
            [discord.Object(id=self.pending_member_id, type=discord.Member)] if self.pending_member_id else []
        )
        member_select = discord.ui.UserSelect(
            placeholder="Choisir le membre à assigner…", default_values=member_default
        )

        async def on_member_select(interaction: discord.Interaction) -> None:
            assert member_select.values is not None
            self.pending_member_id = member_select.values[0].id if member_select.values else None
            await self._save_if_ready(interaction)

        member_select.callback = on_member_select
        self.add_item(discord.ui.ActionRow(member_select))  # pyright: ignore[reportUnknownArgumentType]

        role_default = [discord.Object(id=self.pending_role_id, type=discord.Role)] if self.pending_role_id else []
        role_select = discord.ui.RoleSelect(placeholder="Choisir son rôle quota…", default_values=role_default)
        quota_role_ids = {quota.role_id for quota in self.quotas}

        async def on_role_select(interaction: discord.Interaction) -> None:
            assert role_select.values is not None
            role_id = role_select.values[0].id if role_select.values else None
            if role_id is not None and role_id not in quota_role_ids:
                await interaction.response.send_message(
                    "Ce rôle n'a pas de quota configuré — choisis un rôle qui a un quota.", ephemeral=True
                )
                return
            self.pending_role_id = role_id
            await self._save_if_ready(interaction)

        role_select.callback = on_role_select
        self.add_item(discord.ui.ActionRow(role_select))  # pyright: ignore[reportUnknownArgumentType]

        back_button: discord.ui.Button[Self] = discord.ui.Button(label="Retour", style=discord.ButtonStyle.secondary)

        async def on_back(interaction: discord.Interaction) -> None:
            view = QuotaPanelView(self.guild, self.quotas)
            await interaction.response.edit_message(view=view)

        back_button.callback = on_back
        self.add_item(discord.ui.ActionRow(back_button))  # pyright: ignore[reportUnknownArgumentType]

    async def _save_if_ready(self, interaction: discord.Interaction) -> None:
        if self.pending_member_id is not None and self.pending_role_id is not None:
            await StaffMemberRoleOverride.update_or_create(
                guild_id=self.guild.id,
                member_id=self.pending_member_id,
                defaults={"role_id": self.pending_role_id},
            )
            self.overrides = await StaffMemberRoleOverride.filter(guild_id=self.guild.id)
            self.pending_member_id = None
            self.pending_role_id = None
        self._render()
        await interaction.response.edit_message(view=self)


@final
class ConfigPanelView(discord.ui.DesignerView):
    def __init__(self, guild: discord.Guild, settings: StaffStatsSettings, quotas: list[StaffRoleQuota]) -> None:
        super().__init__(timeout=300)
        self.guild = guild
        self.settings = settings
        self.quotas = quotas
        self._render()

    @classmethod
    async def build(cls, guild: discord.Guild) -> ConfigPanelView:
        settings, _ = await StaffStatsSettings.get_or_create(guild_id=guild.id)
        quotas = await StaffRoleQuota.filter(guild_id=guild.id)
        return cls(guild, settings, quotas)

    def _render(self) -> None:
        self.clear_items()
        self.add_item(discord.ui.Container(discord.ui.TextDisplay(self._summary())))  # pyright: ignore[reportUnknownArgumentType]
        self._add_responsible_role_row()
        self._add_report_channel_row()
        self._add_message_channels_row()
        self._add_voice_channels_row()
        self._add_quotas_row()
        self._add_penalty_row()

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

    def _add_responsible_role_row(self) -> None:
        s = self.settings
        default = [discord.Object(id=s.responsible_role_id, type=discord.Role)] if s.responsible_role_id else []
        role_select = discord.ui.RoleSelect(placeholder="Changer le rôle responsable…", default_values=default)

        async def on_responsible_role(interaction: discord.Interaction) -> None:
            assert role_select.values is not None
            self.settings.responsible_role_id = role_select.values[0].id if role_select.values else None
            await self.settings.save()
            self._render()
            await interaction.response.edit_message(view=self)

        role_select.callback = on_responsible_role
        self.add_item(discord.ui.ActionRow(role_select))  # pyright: ignore[reportUnknownArgumentType]

    def _add_report_channel_row(self) -> None:
        s = self.settings
        default = [discord.Object(id=s.report_channel_id, type=discord.abc.GuildChannel)] if s.report_channel_id else []
        report_select = discord.ui.ChannelSelect(
            placeholder="Changer le salon de rapport hebdo…",
            channel_types=[discord.ChannelType.text],
            default_values=default,
        )

        async def on_report_channel(interaction: discord.Interaction) -> None:
            assert report_select.values is not None
            self.settings.report_channel_id = report_select.values[0].id if report_select.values else None
            await self.settings.save()
            self._render()
            await interaction.response.edit_message(view=self)

        report_select.callback = on_report_channel
        self.add_item(discord.ui.ActionRow(report_select))  # pyright: ignore[reportUnknownArgumentType]

    def _add_message_channels_row(self) -> None:
        s = self.settings
        default = [discord.Object(id=c, type=discord.abc.GuildChannel) for c in s.message_channel_ids]
        message_select = discord.ui.ChannelSelect(
            placeholder="Changer les salons suivis (messages)…",
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=25,
            default_values=default,
        )

        async def on_message_channels(interaction: discord.Interaction) -> None:
            assert message_select.values is not None
            self.settings.message_channel_ids = [c.id for c in message_select.values]
            await self.settings.save()
            self._render()
            await interaction.response.edit_message(view=self)

        message_select.callback = on_message_channels
        self.add_item(discord.ui.ActionRow(message_select))  # pyright: ignore[reportUnknownArgumentType]

    def _add_voice_channels_row(self) -> None:
        s = self.settings
        default = [discord.Object(id=c, type=discord.abc.GuildChannel) for c in s.voice_channel_ids]
        voice_select = discord.ui.ChannelSelect(
            placeholder="Changer les salons suivis (vocal)…",
            channel_types=[discord.ChannelType.voice],
            min_values=0,
            max_values=25,
            default_values=default,
        )

        async def on_voice_channels(interaction: discord.Interaction) -> None:
            assert voice_select.values is not None
            self.settings.voice_channel_ids = [c.id for c in voice_select.values]
            await self.settings.save()
            self._render()
            await interaction.response.edit_message(view=self)

        voice_select.callback = on_voice_channels
        self.add_item(discord.ui.ActionRow(voice_select))  # pyright: ignore[reportUnknownArgumentType]

    def _add_quotas_row(self) -> None:
        quotas_button: discord.ui.Button[Self] = discord.ui.Button(
            label="Gérer les quotas par rôle", style=discord.ButtonStyle.primary
        )

        async def on_open_quotas(interaction: discord.Interaction) -> None:
            view = QuotaPanelView(self.guild, self.quotas)
            await interaction.response.edit_message(view=view)

        quotas_button.callback = on_open_quotas
        self.add_item(discord.ui.ActionRow(quotas_button))  # pyright: ignore[reportUnknownArgumentType]

    def _add_penalty_row(self) -> None:
        penalty_button: discord.ui.Button[Self] = discord.ui.Button(
            label="Pénalité de substitution (ET)", style=discord.ButtonStyle.secondary
        )

        async def on_edit_penalty(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(PenaltyModal(self.settings))

        penalty_button.callback = on_edit_penalty
        self.add_item(discord.ui.ActionRow(penalty_button))  # pyright: ignore[reportUnknownArgumentType]


@final
class StatsStaffCog(discord.Cog):
    def __init__(self, bot: custom.Bot) -> None:
        self.bot: custom.Bot = bot
        self.open_segments: dict[tuple[int, int], StaffVoiceSegment] = {}
        self.report_loop: tasks.Loop = tasks.loop(minutes=5)(self.report_loop_meth)  # pyright: ignore [reportMissingTypeArgument]
        self.checkpoint_loop: tasks.Loop = tasks.loop(minutes=1)(self.checkpoint_loop_meth)  # pyright: ignore [reportMissingTypeArgument]

    @discord.Cog.listener("on_ready", once=True)
    async def on_ready(self) -> None:
        logger.info("Stats staff cog ready, reconciling voice segments")
        await self._reconcile_voice_segments()
        self.report_loop.start()
        self.checkpoint_loop.start()

    async def checkpoint_loop_meth(self) -> None:
        """Roll every open voice segment over into a fresh one, closing the old one in place.

        Bounds how much voice time a crash or hard restart can over-credit (the reconciliation
        on the next startup closes whatever is still open at the restart time) to at most one
        checkpoint interval, instead of the full downtime.
        """
        now = datetime.now(tz=UTC)
        for key, segment in list(self.open_segments.items()):
            guild_id, member_id = key
            segment.ended_at = now
            await segment.save()
            new_segment = await StaffVoiceSegment.create(
                guild_id=guild_id, member_id=member_id, channel_id=segment.channel_id, started_at=now
            )
            self.open_segments[key] = new_segment

    async def _reconcile_voice_segments(self) -> None:
        now = datetime.now(tz=UTC)
        stale = await StaffVoiceSegment.filter(ended_at__isnull=True)
        for segment in stale:
            segment.ended_at = now
            await segment.save()

        all_settings = await StaffStatsSettings.all()
        for settings in all_settings:
            if not settings.voice_channel_ids:
                continue
            guild = self.bot.get_guild(settings.guild_id)
            if guild is None:
                continue
            quota_role_ids = {q.role_id for q in await StaffRoleQuota.filter(guild_id=guild.id)}
            for channel_id in settings.voice_channel_ids:
                channel = guild.get_channel(channel_id)
                if not isinstance(channel, discord.VoiceChannel):
                    continue
                for member in channel.members:
                    await self._recompute_validity(member, channel, quota_role_ids)

    def _has_quota_role(self, member: discord.Member, quota_role_ids: set[int]) -> bool:
        return not member.bot and any(role.id in quota_role_ids for role in member.roles)

    async def _recompute_validity(
        self, member: discord.Member, channel: discord.VoiceChannel, quota_role_ids: set[int]
    ) -> None:
        if not self._has_quota_role(member, quota_role_ids):
            return

        other_humans = sum(1 for m in channel.members if not m.bot and m.id != member.id)
        voice_state = member.voice
        valid = (
            voice_state is not None
            and voice_state.channel is not None
            and voice_state.channel.id == channel.id
            and not voice_state.mute
            and not voice_state.deaf
            and other_humans > 0
        )

        key = (channel.guild.id, member.id)
        open_segment = self.open_segments.get(key)
        now = datetime.now(tz=UTC)
        if valid and open_segment is None:
            segment = await StaffVoiceSegment.create(
                guild_id=channel.guild.id, member_id=member.id, channel_id=channel.id, started_at=now
            )
            self.open_segments[key] = segment
        elif not valid and open_segment is not None:
            open_segment.ended_at = now
            await open_segment.save()
            del self.open_segments[key]

    @discord.Cog.listener("on_voice_state_update")
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if member.bot:
            return
        settings = await StaffStatsSettings.get_or_none(guild_id=member.guild.id)
        if settings is None or not settings.voice_channel_ids:
            return
        quota_role_ids = {q.role_id for q in await StaffRoleQuota.filter(guild_id=member.guild.id)}
        if not quota_role_ids:
            return

        channels: set[discord.VoiceChannel] = set()
        for state in (before, after):
            if state.channel is not None and state.channel.id in settings.voice_channel_ids:
                channels.add(state.channel)  # pyright: ignore[reportArgumentType]

        for channel in channels:
            for other in channel.members:
                await self._recompute_validity(other, channel, quota_role_ids)

        if after.channel is None or after.channel.id not in settings.voice_channel_ids:
            key = (member.guild.id, member.id)
            open_segment = self.open_segments.get(key)
            if open_segment is not None:
                open_segment.ended_at = datetime.now(tz=UTC)
                await open_segment.save()
                del self.open_segments[key]

    @discord.Cog.listener("on_message")
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None or not isinstance(message.author, discord.Member):
            return
        settings = await StaffStatsSettings.get_or_none(guild_id=message.guild.id)
        if settings is None or message.channel.id not in settings.message_channel_ids:
            return
        quota_role_ids = {q.role_id for q in await StaffRoleQuota.filter(guild_id=message.guild.id)}
        if not any(role.id in quota_role_ids for role in message.author.roles):
            return
        await StaffMessageEvent.create(
            guild_id=message.guild.id, member_id=message.author.id, channel_id=message.channel.id
        )

    async def report_loop_meth(self) -> None:
        now = datetime.now(tz=EUROPE_PARIS)
        all_settings = await StaffStatsSettings.filter(report_channel_id__isnull=False)
        for settings in all_settings:
            if not should_send_weekly_report(now, settings.last_report_sent_date):
                continue
            try:
                await self._send_weekly_report(settings, now)
            except Exception:
                logger.exception(f"Failed to send weekly staff report for guild {settings.guild_id}")

    async def _build_role_report_block(
        self,
        guild: discord.Guild,
        settings: StaffStatsSettings,
        quota: StaffRoleQuota,
        role: discord.Role,
        members: list[discord.Member],
        now: datetime,
    ) -> tuple[discord.ui.Container[discord.ui.DesignerView], int, int, list[discord.Member]]:
        mode_label = "ET" if quota.mode == StaffQuotaMode.ALL else "OU"
        lines = [
            f"### {role.mention}",
            f"-# Quota : {quota.voice_minutes_required / 60:g}h vocal **{mode_label}** "
            + f"{quota.messages_required} messages",
        ]

        last_week_start, last_week_end = previous_week_bounds(now)

        passed_count = 0
        zero_activity_members: list[discord.Member] = []
        for member in sorted(members, key=lambda m: m.display_name.lower()):
            messages, voice_minutes = await _compute_stats(guild.id, member.id, StatsPeriod.WEEK, now)
            passed = evaluate_quota(
                quota.mode,
                messages=messages,
                messages_required=quota.messages_required,
                voice_minutes=voice_minutes,
                voice_minutes_required=quota.voice_minutes_required,
                et_penalty=settings.et_substitution_penalty,
            )
            passed_count += passed
            ratio = completion_ratio(
                quota.mode,
                messages=messages,
                messages_required=quota.messages_required,
                voice_minutes=voice_minutes,
                voice_minutes_required=quota.voice_minutes_required,
            )

            last_messages, last_voice_minutes = await _compute_stats_range(
                guild.id, member.id, last_week_start, last_week_end
            )
            last_ratio = completion_ratio(
                quota.mode,
                messages=last_messages,
                messages_required=quota.messages_required,
                voice_minutes=last_voice_minutes,
                voice_minutes_required=quota.voice_minutes_required,
            )

            if messages == 0 and voice_minutes == 0:
                zero_activity_members.append(member)
                emoji = "🚨"
            else:
                emoji = "✅" if passed else "❌"
            lines.append(
                f"{emoji} **{member.display_name}** — {voice_minutes / 60:.1f}h vocal · {messages} messages\n"
                + f"-# {progress_bar(ratio)} · {trend_arrow(ratio, last_ratio)} vs semaine dernière"
            )

        if not members:
            lines.append("-# Aucun membre.")
            colour = discord.Colour.light_grey()
        elif passed_count == len(members):
            colour = discord.Colour.green()
        elif passed_count == 0:
            colour = discord.Colour.red()
        else:
            colour = discord.Colour.gold()

        container = discord.ui.Container[discord.ui.DesignerView](
            discord.ui.TextDisplay("\n".join(lines)),
            colour=colour,
        )
        return container, passed_count, len(members), zero_activity_members

    async def _build_weekly_report_view(
        self, guild: discord.Guild, settings: StaffStatsSettings, now: datetime
    ) -> discord.ui.DesignerView:
        quotas = await StaffRoleQuota.filter(guild_id=guild.id)
        members_by_quota_id = await self._resolve_members_by_quota(guild, quotas)

        role_blocks: list[discord.ui.Container[discord.ui.DesignerView]] = []
        total_passed = 0
        total_members = 0
        all_zero_activity: list[discord.Member] = []
        for quota in quotas:
            role = guild.get_role(quota.role_id)
            if role is None:
                continue
            members = members_by_quota_id.get(quota.id, [])
            block, passed_count, member_count, zero_activity_members = await self._build_role_report_block(
                guild, settings, quota, role, members, now
            )
            role_blocks.append(block)
            total_passed += passed_count
            total_members += member_count
            all_zero_activity.extend(zero_activity_members)

        start = week_start(now)
        header_lines = [
            "## 📊 Rapport hebdomadaire des quotas staff",
            f"-# Semaine du {format_dt(start, style='D')} — {total_passed}/{total_members} quota(s) atteint(s)",
        ]
        items: list[discord.ui.ViewItem[discord.ui.DesignerView]] = [
            discord.ui.Container[discord.ui.DesignerView](discord.ui.TextDisplay("\n".join(header_lines)))
        ]

        if all_zero_activity and settings.responsible_role_id is not None:
            mentions = ", ".join(member.mention for member in all_zero_activity)
            alert_lines = [
                f"## 🚨 <@&{settings.responsible_role_id}> — aucune activité cette semaine",
                f"{len(all_zero_activity)} membre(s) n'ont fait ni message ni vocal cette semaine : {mentions}",
            ]
            items.append(
                discord.ui.Container[discord.ui.DesignerView](
                    discord.ui.TextDisplay("\n".join(alert_lines)),
                    colour=discord.Colour.dark_red(),
                )
            )

        items.extend(role_blocks)
        return discord.ui.DesignerView(*items)

    async def _send_weekly_report(self, settings: StaffStatsSettings, now: datetime) -> None:
        assert settings.report_channel_id is not None
        guild = self.bot.get_guild(settings.guild_id)
        if guild is None:
            logger.warning(f"Guild {settings.guild_id} not found, skipping weekly staff report")
            return

        view = await self._build_weekly_report_view(guild, settings, now)
        channel = self.bot.get_partial_messageable(settings.report_channel_id)
        try:
            await channel.send(view=view)
        except (discord.Forbidden, discord.HTTPException):
            logger.exception(f"Failed to post weekly staff report in channel {settings.report_channel_id}")
            return

        settings.last_report_sent_date = now.date()
        await settings.save()

    async def _is_responsible_or_admin(self, ctx: custom.ApplicationContext) -> bool:
        assert isinstance(ctx.author, discord.Member)
        if ctx.author.guild_permissions.administrator:
            return True
        settings = await StaffStatsSettings.get_or_none(guild_id=ctx.author.guild.id)
        if settings is None or settings.responsible_role_id is None:
            return False
        return settings.responsible_role_id in (role.id for role in ctx.author.roles)

    async def _resolve_members_by_quota(
        self, guild: discord.Guild, quotas: list[StaffRoleQuota]
    ) -> dict[UUID, list[discord.Member]]:
        """Group every staff member under the single quota that applies to them.

        A member matching more than one configured role is resolved via their
        `StaffMemberRoleOverride` if set, so they are never counted under more than one role.
        """
        members_by_quota_id: dict[UUID, list[discord.Member]] = {}
        seen_member_ids: set[int] = set()
        for quota in quotas:
            role = guild.get_role(quota.role_id)
            if role is None:
                continue
            for member in role.members:
                if member.bot or member.id in seen_member_ids:
                    continue
                seen_member_ids.add(member.id)
                resolved = await self._find_quota_role(member)
                if resolved is not None:
                    members_by_quota_id.setdefault(resolved.id, []).append(member)
        return members_by_quota_id

    async def _find_quota_role(self, member: discord.Member) -> StaffRoleQuota | None:
        quotas = await StaffRoleQuota.filter(guild_id=member.guild.id)
        member_role_ids = {role.id for role in member.roles}
        matching = [q for q in quotas if q.role_id in member_role_ids]
        if not matching:
            return None
        if len(matching) == 1:
            return matching[0]

        override = await StaffMemberRoleOverride.get_or_none(guild_id=member.guild.id, member_id=member.id)
        if override is not None:
            picked = next((q for q in matching if q.role_id == override.role_id), None)
            if picked is not None:
                return picked
        return matching[0]

    async def _render_stats(self, member: discord.Member, period: StatsPeriod) -> discord.ui.DesignerView:
        quota = await self._find_quota_role(member)
        now = datetime.now(tz=EUROPE_PARIS)
        messages, voice_minutes = await _compute_stats(member.guild.id, member.id, period, now)
        period_label = PERIOD_LABELS[period]

        header = discord.ui.Section[discord.ui.DesignerView](
            discord.ui.TextDisplay(f"## {member.display_name}\n-# {period_label}"),
            accessory=discord.ui.Thumbnail(member.display_avatar.url),
        )
        activity_block = discord.ui.TextDisplay(  # pyright: ignore[reportUnknownVariableType]
            f"### 📈 Activité\n**{messages}** messages · **{voice_minutes / 60:.1f}h** de vocal"
        )

        if quota is None:
            container = discord.ui.Container[discord.ui.DesignerView](
                header,
                discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large),
                activity_block,
                discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large),
                discord.ui.TextDisplay("-# Ce membre n'a pas de rôle avec quota configuré."),
                colour=discord.Colour.light_grey(),
            )
            return discord.ui.DesignerView(container)

        settings = await StaffStatsSettings.get_or_none(guild_id=member.guild.id)
        et_penalty = settings.et_substitution_penalty if settings is not None else 1.25
        passed = evaluate_quota(
            quota.mode,
            messages=messages,
            messages_required=quota.messages_required,
            voice_minutes=voice_minutes,
            voice_minutes_required=quota.voice_minutes_required,
            et_penalty=et_penalty,
        )
        ratio = completion_ratio(
            quota.mode,
            messages=messages,
            messages_required=quota.messages_required,
            voice_minutes=voice_minutes,
            voice_minutes_required=quota.voice_minutes_required,
        )
        mode_label = "ET" if quota.mode == StaffQuotaMode.ALL else "OU"
        status_label = "Quota atteint" if passed else "Quota non atteint"
        status_emoji = "✅" if passed else "❌"

        quota_block = discord.ui.TextDisplay(  # pyright: ignore[reportUnknownVariableType]
            f"### 🎯 Quota ({mode_label})\n"
            + f"{quota.voice_minutes_required / 60:g}h vocal **{mode_label}** {quota.messages_required} messages\n"
            + f"{progress_bar(ratio)}\n"
            + f"{status_emoji} **{status_label}**"
        )

        items: list[discord.ui.ViewItem[discord.ui.DesignerView]] = [
            header,
            discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large),
            activity_block,
            discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large),
            quota_block,
        ]

        if period == StatsPeriod.WEEK:
            last_week_start, last_week_end = previous_week_bounds(now)
            last_messages, last_voice_minutes = await _compute_stats_range(
                member.guild.id, member.id, last_week_start, last_week_end
            )
            last_ratio = completion_ratio(
                quota.mode,
                messages=last_messages,
                messages_required=quota.messages_required,
                voice_minutes=last_voice_minutes,
                voice_minutes_required=quota.voice_minutes_required,
            )
            items.append(discord.ui.Separator(spacing=discord.SeparatorSpacingSize.large))
            items.append(
                discord.ui.TextDisplay(  # pyright: ignore[reportUnknownArgumentType]
                    f"### 📊 Tendance\n{trend_arrow(ratio, last_ratio)} vs semaine dernière"
                )
            )

        container = discord.ui.Container[discord.ui.DesignerView](
            *items,
            colour=discord.Colour.green() if passed else discord.Colour.red(),
        )
        return discord.ui.DesignerView(container)

    stats_staff = discord.SlashCommandGroup("stats-staff", "Statistiques d'activité du staff")

    @stats_staff.command(name="aide", description="Comprendre comment sont calculés les quotas (OU / ET)")
    async def aide(self, ctx: custom.ApplicationContext) -> None:
        assert ctx.guild is not None
        assert isinstance(ctx.author, discord.Member)

        settings = await StaffStatsSettings.get_or_none(guild_id=ctx.guild.id)
        et_penalty = settings.et_substitution_penalty if settings is not None else 1.25
        penalty_percent = et_penalty * 100

        lines = [
            "## 📖 Comment fonctionnent les quotas",
            "### 🔀 Mode OU",
            "Le vocal et les messages se combinent proportionnellement : chaque activité compte "
            + "pour le pourcentage de son propre seuil atteint, et la somme doit atteindre 100%. "
            + 'Ex: sur un quota "4h vocal OU 100 messages", faire 2h de vocal (50%) et 50 messages '
            + "(50%) remplit le quota, même si aucun des deux seuils n'est atteint seul.",
            f"### 🧩 Mode ET (pénalité actuelle : {penalty_percent:g}%)",
            "Les deux seuils sont normalement requis en entier, mais un manque sur l'un peut être "
            + f"compensé par un surplus sur l'autre, à {penalty_percent:g}% du manque. Sauter "
            + "entièrement un des deux critères demande donc l'équivalent du seuil habituel "
            + f"+ {penalty_percent:g}% sur l'autre. Si les deux critères sont en dessous de leur "
            + "seuil, le quota échoue dans tous les cas, peu importe le surplus ailleurs.",
        ]

        quota = await self._find_quota_role(ctx.author)
        if quota is not None:
            role = ctx.guild.get_role(quota.role_id)
            role_label = role.mention if role is not None else "ton rôle"
            hours_required = quota.voice_minutes_required / 60
            lines.append(f"### 🎯 Ton quota ({role_label})")
            if quota.mode == StaffQuotaMode.ANY:
                lines.append(
                    f"**{hours_required:g}h** de vocal OU **{quota.messages_required}** messages — ou un "
                    + "mélange des deux qui totalise 100% (ex: la moitié de chaque)."
                )
            else:
                voice_substitute = et_full_substitution(hours_required, et_penalty)
                messages_substitute = round(et_full_substitution(quota.messages_required, et_penalty))
                lines.append(
                    f"**{hours_required:g}h** de vocal ET **{quota.messages_required}** messages.\n"
                    + f"- Si tu ne fais aucun message, il te faut **{voice_substitute:g}h** de vocal.\n"
                    + f"- Si tu ne fais aucun vocal, il te faut **{messages_substitute}** messages."
                )

        await ctx.respond(
            view=discord.ui.DesignerView(discord.ui.Container(discord.ui.TextDisplay("\n\n".join(lines)))),  # pyright: ignore[reportUnknownArgumentType]
            ephemeral=True,
        )

    @stats_staff.command(name="moi", description="Voir mes propres statistiques de staff")
    async def moi(
        self,
        ctx: custom.ApplicationContext,
        periode: str = discord.Option(str, "Période", choices=PERIOD_CHOICES, default=StatsPeriod.WEEK.value),  # pyright: ignore[reportArgumentType, reportCallInDefaultInitializer]
    ) -> None:
        assert isinstance(ctx.author, discord.Member)
        if await self._find_quota_role(ctx.author) is None:
            await ctx.respond("Tu n'as pas de rôle avec un quota configuré.", ephemeral=True)
            return
        view = await self._render_stats(ctx.author, StatsPeriod(periode))
        await ctx.respond(view=view, ephemeral=True)

    @stats_staff.command(name="voir", description="Voir les statistiques d'un membre du staff")
    async def voir(
        self,
        ctx: custom.ApplicationContext,
        membre: discord.Member,
        periode: str = discord.Option(str, "Période", choices=PERIOD_CHOICES, default=StatsPeriod.WEEK.value),  # pyright: ignore[reportArgumentType, reportCallInDefaultInitializer]
    ) -> None:
        if not await self._is_responsible_or_admin(ctx):
            await ctx.respond("Tu n'as pas la permission de voir les statistiques d'un autre membre.", ephemeral=True)
            return
        view = await self._render_stats(membre, StatsPeriod(periode))
        await ctx.respond(view=view, ephemeral=True)

    stats_staff_admin = discord.SlashCommandGroup(
        "stats-staff-admin",
        "Administration des statistiques de staff",
        default_member_permissions=discord.Permissions(administrator=True),
    )

    @stats_staff_admin.command(name="config", description="Configurer les quotas, salons suivis et rapports de stats")
    async def config(self, ctx: custom.ApplicationContext) -> None:
        assert ctx.guild is not None
        view = await ConfigPanelView.build(ctx.guild)
        await ctx.respond(view=view, ephemeral=True)

    @stats_staff_admin.command(
        name="apercu-rapport",
        description="Voir à quoi ressemblerait le rapport hebdomadaire maintenant, sans attendre dimanche",
    )
    async def apercu_rapport(self, ctx: custom.ApplicationContext) -> None:
        assert ctx.guild is not None
        settings, _ = await StaffStatsSettings.get_or_create(guild_id=ctx.guild.id)
        now = datetime.now(tz=EUROPE_PARIS)
        view = await self._build_weekly_report_view(ctx.guild, settings, now)
        await ctx.respond(view=view, ephemeral=True)


__all__ = ("StatsStaffCog",)
