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
                "Main",
                f"'ping_queue' used by {interaction.user.name} [{interaction.user.id}]",
            ]
        )
        await interaction.response.send_message("Pong!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(queue(bot))
