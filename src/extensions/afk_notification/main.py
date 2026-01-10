# Copyright (c) Communauté Les Frères Poulain
# SPDX-License-Identifier: MIT

import asyncio
from datetime import datetime, time, timedelta
from logging import getLogger
from typing import Self, final, override

import discord
from discord.ext import tasks
from discord.utils import format_dt

from src import custom
from src.database.models import Dormeur

from .config import EUROPE_PARIS, AfkNotifConfig

logger = getLogger("bot").getChild("afk_notification")


def is_time_between(start: time, end: time, current: datetime) -> bool:
    """Check if a given time is between start and end times.

    Handles ranges that cross midnight (e.g., 22:00 to 02:00).

    Args:
        start (time): The start time of the range.
        end (time): The end time of the range.
        current (datetime): The current datetime to check.

    """
    current_time = current.timetz()

    if start <= end:
        # Normal case: 09:00 to 17:00
        return start <= current_time <= end
    # Crosses midnight: 22:00 to 02:00
    return current_time >= start or current_time <= end


class NotifyView(discord.ui.DesignerView):
    @override
    def __init__(self, member: discord.Member, config: "AfkNotifConfig") -> None:
        self.member: discord.Member = member
        self.config: AfkNotifConfig = config
        super().__init__(timeout=self.config.afk_reminder_timeout, disable_on_timeout=True)

        button: discord.ui.Button[Self] = discord.ui.Button(
            label="Je suis réveillé(e) !", style=discord.ButtonStyle.success
        )
        button.callback = self.button_callback

        self.datetime_timeout: datetime = datetime.now(tz=EUROPE_PARIS) + timedelta(
            seconds=self.config.afk_reminder_timeout
        )

        container: discord.ui.Container[Self] = discord.ui.Container(
            discord.ui.TextDisplay(
                f"## {member.mention} Est-tu réveillé(e) ?\n"
                + f"Tu as {format_dt(self.datetime_timeout, style='R')} pour cliquer sur le bouton ci-dessous "
                + "et éviter d'être déconnecté(e) !"
            ),
            discord.ui.ActionRow(button),
        )
        self.add_item(container)
        self.task: asyncio.Task[None] = asyncio.create_task(self.disconnect_member())

    async def disconnect_member(self) -> None:
        await asyncio.sleep(self.config.afk_reminder_timeout)
        if self.member.voice and self.member.voice.channel:
            logger.info(f"Disconnecting AFK member: {self.member} ({self.member.id})")
            try:
                await self.member.edit(voice_channel=None)
            except discord.Forbidden:
                logger.warning(f"Missing permission to disconnect {self.member} ({self.member.id})")
            except Exception:
                logger.exception(f"Error disconnecting {self.member} ({self.member.id})")
            else:
                if self.message:
                    await self.message.reply(
                        f"{self.member.mention}, tu as été AFK pendant trop longtemps."
                        + " Je t'ai déconnecté du salon vocal."
                    )
        else:
            logger.debug(f"Member {self.member} ({self.member.id}) already left voice, skipping disconnect")

    async def button_callback(self, interaction: discord.Interaction) -> None:
        if interaction.user != self.member:
            logger.debug(f"Wrong user {interaction.user} clicked button for {self.member}")
            await interaction.response.send_message("Ce bouton n'est pas pour toi !", ephemeral=True)
            return
        logger.info(f"Member {self.member} ({self.member.id}) confirmed they are awake")
        try:
            await interaction.response.defer()
        except discord.HTTPException:
            logger.exception(f"Failed to defer interaction for {self.member} ({self.member.id})")
        self.task.cancel()
        await self.on_timeout()
        self.stop()


@final
class AfkNotif(discord.Cog):
    def __init__(self, bot: custom.Bot, config: "AfkNotifConfig") -> None:
        self.bot = bot
        self.config = config

        self.tasks: dict[int, asyncio.Task[None]] = {}
        self.loop = tasks.loop(time=self.config.start_time)(self.register_all)

    async def notify_member(self, member: discord.Member) -> None:
        try:
            while True:
                logger.debug(f"Starting {self.config.afk_reminder_every}s sleep for {member} ({member.id})")
                await asyncio.sleep(self.config.afk_reminder_every)

                if not member.voice or not member.voice.channel:
                    logger.debug(f"Member {member} ({member.id}) no longer in voice, stopping notifications")
                    return

                if not is_time_between(self.config.start_time, self.config.stop_time, datetime.now(tz=EUROPE_PARIS)):
                    logger.debug(f"Outside time window for {member} ({member.id}), stopping notifications")
                    return

                logger.info(f"Sending AFK notification to {member} ({member.id}) in {member.voice.channel}")
                view = NotifyView(member, self.config)
                try:
                    await member.voice.channel.send(view=view)
                except discord.Forbidden:
                    logger.exception(f"Missing permission to send message in {member.voice.channel}")
                    view.task.cancel()
                    return
                except discord.HTTPException:
                    view.task.cancel()
                    logger.exception(f"Failed to send AFK notification to {member} ({member.id})")
                except Exception:
                    view.task.cancel()
                    raise

        except asyncio.CancelledError:
            logger.debug(f"Notification task cancelled for {member} ({member.id})")
            raise
        except Exception:
            logger.exception(f"Error in notify_member for {member} ({member.id})")
        finally:
            logger.debug(f"Cleaning up task for {member} ({member.id})")
            self.tasks.pop(member.id, None)

    async def register_all(self) -> None:
        logger.info("Registering all members in voice channels")
        guild = self.bot.get_guild(self.config.guild_id)
        if not guild:
            logger.warning(f"Guild {self.config.guild_id} not found")
            return

        count = 0
        for channel in guild.voice_channels:
            for member in channel.members:
                if member.id not in self.tasks:
                    await self.register_new_member(member)
                    count += 1

        logger.info(f"Registered {count} member(s) for AFK notifications")

    async def register_new_member(self, member: discord.Member) -> None:
        if member.bot:
            return
        if self.config.role_id and self.config.role_id not in [role.id for role in member.roles]:
            logger.debug(f"Member {member} ({member.id}) does not have required role {self.config.role_id}")
            return

        if not await Dormeur.filter(discord_id=member.id).exists():
            logger.debug(f"Member {member} ({member.id}) is not a dormeur")
            return

        logger.info(f"Registering new member for AFK notifications: {member} ({member.id})")
        self.tasks[member.id] = asyncio.create_task(self.notify_member(member))

    @discord.Cog.listener("on_ready", once=True)
    async def on_ready(self) -> None:
        logger.info("AfkNotif cog ready, starting daily registration loop")
        self.loop.start()

    @discord.Cog.listener("on_voice_state_update")
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,  # noqa: ARG002
        after: discord.VoiceState,
    ) -> None:
        if not is_time_between(self.config.start_time, self.config.stop_time, datetime.now(tz=EUROPE_PARIS)):
            logger.debug(f"Voice state update for {member} ({member.id}) outside time window, ignoring")
            return

        if member.bot:
            return

        if after.channel is None:
            logger.debug(f"Member {member} ({member.id}) left voice channel")
            if task := self.tasks.get(member.id):
                logger.debug(f"Cancelling notification task for {member} ({member.id})")
                task.cancel()
                self.tasks.pop(member.id)
        elif member.id not in self.tasks:
            logger.debug(f"Member {member} ({member.id}) joined voice channel: {after.channel}")
            await self.register_new_member(member)

    dormeurs = discord.SlashCommandGroup(
        "dormeurs",
        "Commandes concernant les dormeurs",
        default_member_permissions=discord.Permissions(administrator=True),
    )

    @dormeurs.command(name="ajouter", description="Ajouter un dormeur")
    async def ajouter(self, ctx: custom.ApplicationContext, member: discord.Member) -> None:
        if await Dormeur.filter(discord_id=member.id).exists():
            await ctx.respond(f"{member.mention} est déjà un dormeur.", ephemeral=True)
            return
        await Dormeur.create(discord_id=member.id)
        if is_time_between(self.config.start_time, self.config.stop_time, datetime.now(tz=EUROPE_PARIS)):
            await self.register_new_member(member)
            logger.debug(f"Registered new member {member} ({member.id}) for AFK notifications")

        await ctx.respond(f"{member.mention} a été ajouté en tant que dormeur.", ephemeral=True)

    @dormeurs.command(name="supprimer", description="Supprimer un dormeur")
    async def supprimer(self, ctx: custom.ApplicationContext, member: discord.Member) -> None:
        if not await Dormeur.filter(discord_id=member.id).exists():
            await ctx.respond(f"{member.mention} n'est pas un dormeur.", ephemeral=True)
            return
        await Dormeur.filter(discord_id=member.id).delete()
        if task := self.tasks.get(member.id):
            logger.debug(f"Cancelling notification task for removed dormeur {member} ({member.id})")
            task.cancel()
            self.tasks.pop(member.id)

        await ctx.respond(f"{member.mention} a été supprimé en tant que dormeur.", ephemeral=True)

    @dormeurs.command(name="lister", description="Lister les dormeurs")
    async def lister(self, ctx: custom.ApplicationContext) -> None:
        dormeurs = await Dormeur.all()
        if not dormeurs:
            await ctx.respond("Aucun dormeur enregistré.", ephemeral=True)
            return
        dormeurs_str = "\n".join(f"- <@{dormeur.discord_id}>" for dormeur in dormeurs)
        await ctx.respond(
            view=discord.ui.DesignerView(
                discord.ui.Container(discord.ui.TextDisplay(f"## Liste des dormeurs\n{dormeurs_str}"))  # pyright: ignore[reportUnknownArgumentType]
            )
        )
