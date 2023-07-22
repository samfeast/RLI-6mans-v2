from asyncore import write
import discord
from discord.ext import commands
from discord import app_commands
import json
import time
import csv

with open("json/config.json", "r") as read_file:
    config = json.load(read_file)

GUILD_ID = config["GUILD_ID"]
ELO_GAIN = config["ELO_GAIN"]


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
        await interaction.response.send_message(
            f"{game_id} has been reported", ephemeral=True
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
                        value=game_id.split("-")[0],
                    )
                )

        return choices


async def setup(bot):
    await bot.add_cog(reporting(bot))
