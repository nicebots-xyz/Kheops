# Copyright (c) bryan1993-HA
# SPDX-License-Identifier: MIT

from __future__ import annotations

import discord
from discord.ext import commands

from src import custom
from .storage import WelcomeStorage

from pathlib import Path
from typing import Any, Dict, Optional


default = {
    "enabled": True,
    "channel_id": None,  # id du salon
    "message": "Bienvenue {mention} sur {server} !",
}


# -----------------------------
# i18n runtime (strings)
# -----------------------------

_TRANSLATIONS_CACHE: Optional[dict] = None


def _load_translations_file() -> dict:
    """
    Charge src/extensions/welcome/translations.yml si possible.
    Format attendu (comme ping):
      strings:
        key:
          fr: ...
          en-US: ...
    """
    global _TRANSLATIONS_CACHE
    if _TRANSLATIONS_CACHE is not None:
        return _TRANSLATIONS_CACHE

    # Fichier translations.yml à côté de ce fichier
    translations_path = Path(__file__).with_name("translations.yml")

    # Fallback minimal (si YAML non dispo)
    fallback = {
        "strings": {
            "modal_title": {"fr": "Configurer le message de bienvenue"},
            "modal_label": {"fr": "Message de bienvenue"},
            "modal_placeholder": {"fr": "Ex: Bienvenue {mention} sur {server} !"},
            "only_guild": {"fr": "Commande serveur uniquement."},
            "configured": {"fr": "✅ Bienvenue configuré !"},
            "disabled": {"fr": "✅ Message de bienvenue désactivé."},
            "vars_title": {"fr": "**Variables :**"},
            "vars_body": {
                "fr": "- `{user}`\n- `{mention}`\n- `{username}`\n- `{server}`\n- `{member_count}`\n- `{created_at}`\n- `{joined_at}`\n"
            },
            "preview_title": {"fr": "🧪 Aperçu :"},
            "channel_line": {"fr": "📌 Salon : <#{channel_id}>"},
        }
    }

    if not translations_path.exists():
        _TRANSLATIONS_CACHE = fallback
        return _TRANSLATIONS_CACHE

    # On tente PyYAML (souvent présent). Sinon fallback.
    try:
        import yaml  # type: ignore
    except Exception:
        _TRANSLATIONS_CACHE = fallback
        return _TRANSLATIONS_CACHE

    try:
        data = yaml.safe_load(translations_path.read_text(encoding="utf-8")) or {}
        # on merge fallback pour garantir la présence des clés minimales
        strings = fallback.get("strings", {})
        strings.update((data.get("strings") or {}))
        _TRANSLATIONS_CACHE = {"strings": strings}
        return _TRANSLATIONS_CACHE
    except Exception:
        _TRANSLATIONS_CACHE = fallback
        return _TRANSLATIONS_CACHE


def _normalize_locale(locale: Optional[str]) -> str:
    """
    Discord peut renvoyer 'fr', 'en-US', 'en-GB', etc.
    On tente dans l'ordre:
      - locale exacte
      - base (ex: 'en' si 'en-US')
      - fallback 'en-US'
      - fallback 'fr'
    """
    if not locale:
        return "fr"
    return str(locale)


def t(key: str, locale: Optional[str] = None, **fmt: Any) -> str:
    """
    Récupère strings.<key> depuis translations.yml (format ping).
    """
    data = _load_translations_file()
    strings: Dict[str, Dict[str, str]] = data.get("strings", {})

    loc = _normalize_locale(locale)
    base = loc.split("-")[0] if "-" in loc else loc

    entry = strings.get(key, {})
    # ordre de résolution
    text = (
        entry.get(loc)
        or entry.get(base)
        or entry.get("en-US")
        or entry.get("fr")
        or ""
    )

    if fmt:
        try:
            return text.format(**fmt)
        except Exception:
            return text
    return text


# -----------------------------
# Template message welcome
# -----------------------------

def render_template(template: str, member: discord.Member) -> str:
    guild = member.guild

    class SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    vars_ = SafeDict(
        {
            "user": member.display_name,
            "mention": member.mention,
            "username": member.name,
            "server": guild.name,
            "member_count": guild.member_count or 0,
            "created_at": member.created_at.strftime("%Y-%m-%d"),
            "joined_at": (member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "now"),
        }
    )
    return str(template).format_map(vars_)


# -----------------------------
# Modal
# -----------------------------

class WelcomeMessageModal(discord.ui.Modal):
    def __init__(self, storage: WelcomeStorage, channel_id: int, locale: Optional[str]):
        super().__init__(title=t("modal_title", locale))
        self.storage = storage
        self.channel_id = int(channel_id)
        self.locale = locale

        self.message_input = discord.ui.InputText(
            label=t("modal_label", locale),
            style=discord.InputTextStyle.long,
            placeholder=t("modal_placeholder", locale),
            max_length=1800,
            required=True,
        )
        self.add_item(self.message_input)

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message(t("only_guild", self.locale), ephemeral=True)

        msg = self.message_input.value.strip()
        await self.storage.set(interaction.guild.id, channel_id=self.channel_id, message=msg, enabled=True)

        preview = msg
        if isinstance(interaction.user, discord.Member):
            preview = render_template(msg, interaction.user)

        await interaction.response.send_message(
            f"{t('configured', self.locale)}\n"
            f"{t('channel_line', self.locale, channel_id=self.channel_id)}\n\n"
            f"{t('preview_title', self.locale)}\n{preview}",
            ephemeral=True,
        )


# -----------------------------
# Cog
# -----------------------------

class WelcomeCog(commands.Cog):
    def __init__(self, bot: custom.Bot):
        self.bot = bot
        self.storage = WelcomeStorage("data/welcome.json")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cfg = await self.storage.get(member.guild.id)
        if not cfg.get("enabled"):
            return

        channel_id = cfg.get("channel_id")
        template = cfg.get("message")
        if not channel_id or not template:
            return

        channel = member.guild.get_channel(int(channel_id))
        if channel is None:
            return

        content = render_template(str(template), member)

        # Sécurité mentions
        allowed = discord.AllowedMentions(users=True, roles=False, everyone=False)

        try:
            await channel.send(content, allowed_mentions=allowed)
        except (discord.Forbidden, discord.HTTPException):
            return

    @discord.slash_command(name="bienvenue", description="Configurer le message de bienvenue.")
    @discord.default_permissions(manage_guild=True)
    @discord.option(
        name="salon",
        description="Salon où envoyer le message",
        input_type=discord.TextChannel,
        required=True,
    )
    async def bienvenue(self, ctx: discord.ApplicationContext, salon: discord.TextChannel):
        locale = getattr(ctx, "locale", None)
        modal = WelcomeMessageModal(self.storage, salon.id, locale)
        await ctx.send_modal(modal)

    @discord.slash_command(name="bienvenue_off", description="Désactiver le message de bienvenue.")
    @discord.default_permissions(manage_guild=True)
    async def bienvenue_off(self, ctx: discord.ApplicationContext):
        if not ctx.guild:
            return await ctx.respond(t("only_guild", getattr(ctx, "locale", None)), ephemeral=True)
        await self.storage.disable(ctx.guild.id)
        await ctx.respond(t("disabled", getattr(ctx, "locale", None)), ephemeral=True)

    @discord.slash_command(name="bienvenue_vars", description="Voir les variables disponibles.")
    async def bienvenue_vars(self, ctx: discord.ApplicationContext):
        locale = getattr(ctx, "locale", None)

        text = (
            f"{t('vars_title', locale)}\n\n"
            f"{t('vars_user', locale)}\n"
            f"{t('vars_mention', locale)}\n"
            f"{t('vars_username', locale)}\n"
            f"{t('vars_server', locale)}\n"
            f"{t('vars_member_count', locale)}\n"
            f"{t('vars_created_at', locale)}\n"
            f"{t('vars_joined_at', locale)}\n\n"
            f"{t('vars_example_title', locale)}\n"
            f"{t('vars_example', locale)}"
        )

        await ctx.respond(text, ephemeral=True)

def setup(bot: custom.Bot, config: dict):
    bot.add_cog(WelcomeCog(bot))
