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

        # If the game_id is longer than 6, we know they have either 1) selected one of the autocomplete choices, or 2) have entered an invalid ID
        if len(game_id) > 6:
            if game_id in game_log["live"]:
                await self.report_win(game_id)
            else:
                print(f"{game_id} does not exist")
        else:
            # Full game IDs include the date when the match was created
            # Users only see the shortened ID, so if a user reported without using an autocomplete option, the date needs to be added
            # This date could either be the day of the report, or the day previous - both must be checked
            # This whole ordeal could be circumvented entirely by rejecting any inputs which do not match the autocomplete options - CONSIDER THIS!
            game_id_1 = (
                game_id.upper()
                + "-"
                + str(datetime.now(pytz.timezone("Europe/Dublin")).strftime("%d%m%y"))
            )
            game_id_2 = (
                game_id.upper()
                + "-"
                + str(
                    (
                        datetime.now(pytz.timezone("Europe/Dublin")) - timedelta(days=1)
                    ).strftime("%d%m%y")
                )
            )
            if game_id_1 in game_log["live"]:
                await self.report_win(game_id_1)
            else:
                if game_id_2 in game_log["live"]:
                    await self.report_win(game_id_2)
                else:
                    print(f"{game_id} does not exist")

        await interaction.response.send_message("Pong!", ephemeral=True)

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

    async def report_win(interaction, game_id):
        print(f"Reporting {game_id}")


async def setup(bot):
    await bot.add_cog(reporting(bot))
