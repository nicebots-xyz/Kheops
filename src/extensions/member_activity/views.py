# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from __future__ import annotations

from typing import TYPE_CHECKING, Never, final, override

import discord
from discord.ui import ActionRow, Container, DesignerView, TextDisplay

from .stats import get_or_create_settings

if TYPE_CHECKING:
    from src.database.models import MemberActivitySettings

    from .tracking import TrackingCog
    from .translations import ExtensionStrings as Strings


def _text(content: str) -> Container[DesignerView]:
    return Container[DesignerView](TextDisplay[DesignerView, Never](content))


@final
class _SettingsSelect(discord.ui.Select[DesignerView]):
    """Edits one settings field (always a list of channel/category ids here).

    Only that field is saved, so two open panels can't overwrite each other — same pattern as
    stats_staff's `_SettingsSelect`, trimmed to this extension's channel-only fields.
    """

    def __init__(self, panel: ConfigPanelView, field: str, channel_type: discord.ChannelType) -> None:
        ids: list[int] = getattr(panel.settings, field)
        placeholder: str = getattr(panel.t, f"placeholder_{field}")
        super().__init__(
            discord.ComponentType.channel_select,
            placeholder=placeholder,
            channel_types=[channel_type],
            min_values=0,
            max_values=25,
            default_values=[discord.Object(id=i, type=discord.abc.GuildChannel) for i in ids],
        )
        self.panel = panel
        self.field = field

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        ids = [value.id for value in self.values or []]
        setattr(self.panel.settings, self.field, ids)
        await self.panel.settings.save(update_fields=[self.field])
        await self.panel.saved(interaction)


@final
class ConfigPanelView(DesignerView):
    def __init__(
        self, guild: discord.Guild, tracking: TrackingCog, t: Strings, settings: MemberActivitySettings
    ) -> None:
        super().__init__(timeout=300)
        self.guild = guild
        self.tracking = tracking
        self.t = t
        self.settings = settings
        self.render()

    @classmethod
    async def build(cls, guild: discord.Guild, tracking: TrackingCog, t: Strings) -> ConfigPanelView:
        return cls(guild, tracking, t, await get_or_create_settings(guild.id))

    async def saved(self, interaction: discord.Interaction) -> None:
        """Refresh this panel after a change and let tracking pick it up right away."""
        await self.tracking.reload_config(self.guild.id)
        self.render()
        await interaction.response.edit_message(view=self)

    def render(self) -> None:
        s, t = self.settings, self.t
        self.clear_items()
        self.add_item(
            _text(
                t.config_summary.format(
                    message_channels=", ".join(f"<#{c}>" for c in s.message_channel_ids) or t.none,
                    voice_channels=", ".join(f"<#{c}>" for c in s.voice_channel_ids) or t.none,
                    categories=", ".join(f"<#{c}>" for c in s.tracked_category_ids) or t.none,
                )
            )
        )
        for item in (
            _SettingsSelect(self, "message_channel_ids", discord.ChannelType.text),
            _SettingsSelect(self, "voice_channel_ids", discord.ChannelType.voice),
            _SettingsSelect(self, "tracked_category_ids", discord.ChannelType.category),
        ):
            self.add_item(ActionRow[DesignerView](item))


__all__ = ("ConfigPanelView",)
