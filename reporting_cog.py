from asyncore import write
import discord
from discord.ext import commands
from discord import app_commands
import json
import time
import csv
from datetime import datetime, timedelta
import pytz

with open("json/config.json", "r") as read_file:
    config = json.load(read_file)

GUILD_ID = config["GUILD_ID"]
ELO_GAIN = config["ELO_GAIN"]
POINTS_FOR_WIN = config["POINTS_FOR_WIN"]


def log_event(event):
    with open("logs/live_logs.csv", "a", newline="") as write_file:
        writer = csv.writer(write_file)
        writer.writerow(event)


class reporting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Ping cog command
    @app_commands.command(description="Ping the reporting cog.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ping_reporting(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!", ephemeral=True)

    @app_commands.command(description="Report a win.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def win(self, interaction: discord.Interaction, game_id: str):
        with open("json/game_log.json", "r") as read_file:
            game_log = json.load(read_file)

        if game_id in game_log["live"]:
            await self.report_win(interaction, game_id)
        else:
            await interaction.response.send_message(
                f"Could not find {game_id}. Ensure you are selecting one of the autocompleted options.",
                ephemeral=True,
            )

    @win.autocomplete("game_id")
    async def autocomplete_callback(
        self, interaction: discord.Interaction, current: str
    ):
        with open("json/game_log.json") as read_file:
            game_log = json.load(read_file)

        choices = []
        for game_id in list(game_log["live"].keys()):
            if len(choices) > 23:
                break
            else:
                minutes_since_created = round(
                    (time.time() - game_log["live"][game_id]["created"]) / 60
                )
                tier = game_log["live"][game_id]["tier"].capitalize()
                formatted_game_id = game_id.split("-")[0]
                choices.append(
                    app_commands.Choice(
                        name=f"{formatted_game_id} ({tier}, {minutes_since_created} minutes ago)",
                        value=game_id,
                    )
                )

        return choices

    async def report_win(self, interaction, game_id):
        await interaction.response.send_message(f"Reporting {game_id}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(reporting(bot))
