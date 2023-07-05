from asyncore import write
import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import time
import config
import csv

GUILD_ID = config.GUILD_ID

ELITE = config.ELITE
PREMIER = config.PREMIER
CHAMPIONSHIP = config.CHAMPIONSHIP
CASUAL = config.CASUAL

ELITE_LOGS = config.ELITE_LOGS
PREMIER_LOGS = config.PREMIER_LOGS
CHAMPIONSHIP_LOGS = config.CHAMPIONSHIP_LOGS
CASUAL_LOGS = config.CASUAL_LOGS

elite_queue = []
premier_queue = []
championship_queue = []
casual_queue = []


def log_event(event):
    with open("logs/live_logs.csv", "a", newline="") as write_file:
        writer = csv.writer(write_file)
        writer.writerow(event)


class queue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Ping cog command
    @app_commands.command(description="Ping the queue cog.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ping_queue(self, interaction: discord.Interaction):
        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Queue",
                f"'ping_queue' used by {interaction.user.name} [{interaction.user.id}]",
            ]
        )
        await interaction.response.send_message("Pong!", ephemeral=True)

    # Join queue
    @app_commands.command(description="Join the queue.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def q(self, interaction: discord.Interaction):
        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Queue",
                f"'q' used by {interaction.user.name} [{interaction.user.id}] in {interaction.channel.name} [{interaction.channel.id}]",
            ]
        )
        if interaction.channel.id == ELITE:
            if interaction.user.id in elite_queue:
                await interaction.response.send_message(
                    "You are already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    interaction.user,
                    elite_queue,
                    ELITE,
                    False,
                )
        elif interaction.channel.id == PREMIER:
            if interaction.user.id in premier_queue:
                await interaction.response.send_message(
                    "You are already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    interaction.user,
                    premier_queue,
                    PREMIER,
                    False,
                )
        elif interaction.channel.id == CHAMPIONSHIP:
            if interaction.user.id in championship_queue:
                await interaction.response.send_message(
                    "You are already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    interaction.user,
                    championship_queue,
                    CHAMPIONSHIP,
                    False,
                )
        elif interaction.channel.id == CASUAL:
            if interaction.user.id in casual_queue:
                await interaction.response.send_message(
                    "You are already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    interaction.user,
                    casual_queue,
                    CASUAL,
                    False,
                )
        else:
            await interaction.response.send_message(
                "Queuing is not enabled in this channel.", ephemeral=True
            )

        # Join queue

    @app_commands.command(description="Add a user to the queue.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def add(self, interaction: discord.Interaction, user: discord.User):
        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Queue",
                f"'add' used by {interaction.user.name} [{interaction.user.id}] in {interaction.channel.name} [{interaction.channel.id}] on {user.name} [{user.id}]",
            ]
        )
        if interaction.channel.id == ELITE_LOGS:
            if user.id in elite_queue:
                await interaction.response.send_message(
                    "User is already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    user,
                    elite_queue,
                    ELITE,
                    True,
                )
        elif interaction.channel.id == PREMIER_LOGS:
            if user.id in premier_queue:
                await interaction.response.send_message(
                    "User is already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    user,
                    premier_queue,
                    PREMIER,
                    True,
                )
        elif interaction.channel.id == CHAMPIONSHIP_LOGS:
            if user.id in championship_queue:
                await interaction.response.send_message(
                    "User is already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    user,
                    championship_queue,
                    CHAMPIONSHIP,
                    True,
                )
        elif interaction.channel.id == CASUAL_LOGS:
            if user.id in casual_queue:
                await interaction.response.send_message(
                    "User is already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    user,
                    casual_queue,
                    CASUAL,
                    True,
                )
        else:
            await interaction.response.send_message(
                "This command must be used in the corresponding logs channel.",
                ephemeral=True,
            )

    async def add_to_queue(self, interaction, user, queue, queue_channel_id, added):
        queue_channel = self.bot.get_channel(queue_channel_id)
        queue.append(user.id)

        if added:
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"{user.name} [{user.id}] has been added to the {queue_channel.name[:-6]} queue ({len(queue)} in queue)",
                ]
            )
            embed = discord.Embed(
                title="Player Added",
                description=f"{user.mention} has been added to the <#{queue_channel_id}> queue",
                color=0x83FF00,
            )
            await interaction.response.send_message(embed=embed)

            if len(queue) == 1:
                embed = discord.Embed(title="1 player is in the queue!")
                embed.set_footer(
                    text="5 more needed!",
                    icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                )
            else:
                embed = discord.Embed(title=f"{len(queue)} players are in the queue!")
                embed.set_footer(
                    text=f"{str(6-len(queue))} more needed!",
                    icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                )
            embed.color = 0xFF8B00
            embed.description = f"{user.mention} has been added to the queue."
            await queue_channel.send(embed=embed)
        else:
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"{user.name} [{user.id}] has joined the {queue_channel.name[:-6]} queue ({len(queue)} in queue)",
                ]
            )

            if len(queue) == 1:
                embed = discord.Embed(title="1 player is in the queue!")
                embed.set_footer(
                    text="5 more needed!",
                    icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                )
            else:
                embed = discord.Embed(title=f"{len(queue)} players are in the queue!")
                embed.set_footer(
                    text=f"{str(6-len(queue))} more needed!",
                    icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                )
            embed.color = 0xFF8B00
            embed.description = f"{user.mention} has joined the queue."
            await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(queue(bot))
