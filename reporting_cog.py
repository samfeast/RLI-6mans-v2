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

        # Check if the game ID exists in its current form
        if game_id in game_log["live"]:
            winner, loser = await self.get_result(interaction, game_log, game_id)
            await self.report_win(interaction, game_id, winner, loser)
        # If the user manually entered a game ID (e.g RLI123), check if the ID + "-(todays_date)" exists
        elif (
            f"{game_id.upper()}-{str(datetime.now(pytz.timezone('Europe/Dublin')).strftime('%d%m%y'))}"
            in game_log["live"]
        ):
            game_id = f"{game_id.upper()}-{str(datetime.now(pytz.timezone('Europe/Dublin')).strftime('%d%m%y'))}"

            winner, loser = await self.get_result(interaction, game_log, game_id)
            await self.report_win(interaction, game_id, winner, loser)
        # Same as above, but for yesterdays date - this happens when a match is being reported the day after it was created
        elif (
            f"{game_id.upper()}-{str((datetime.now(pytz.timezone('Europe/Dublin')) - timedelta(days=1)).strftime('%d%m%y'))}"
            in game_log["live"]
        ):
            game_id = f"{game_id.upper()}-{str((datetime.now(pytz.timezone('Europe/Dublin')) - timedelta(days=1)).strftime('%d%m%y'))}"

            winner, loser = await self.get_result(interaction, game_log, game_id)
            await self.report_win(interaction, game_id, winner, loser)

        else:
            await interaction.response.send_message(
                f"{game_id} does not exist",
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

    async def get_result(self, interaction, game_log, game_id):
        if interaction.user.id in game_log["live"][game_id]["team1"]:
            return "team1", "team2"
        elif interaction.user.id in game_log["live"][game_id]["team2"]:
            return "team2", "team1"
        else:
            return None, None

    async def report_win(self, interaction, game_id, winner, loser):
        if winner == None and loser == None:
            await interaction.response.send_message(
                f"You do not have permission to report {game_id.split('-')[0]}",
                ephemeral=True,
            )
        else:
            with open("json/game_log.json", "r") as read_file:
                game_log = json.load(read_file)

            game_dict = game_log["live"][game_id]

            if winner == "team1":
                elo_swing = ELO_GAIN * (1 - game_dict["p1_win"])
            elif winner == "team2":
                elo_swing = ELO_GAIN * (1 - game_dict["p2_win"])

            game_dict["reported"] = round(time.time())
            game_dict["winner"] = winner
            game_dict["loser"] = loser
            game_dict["elo_swing"] = elo_swing

            game_log["complete"][game_id] = game_dict
            del game_log["live"][game_id]

            with open("json/game_log.json", "w") as write_file:
                json.dump(game_log, write_file, indent=2)

            winning_players = []
            losing_players = []
            for player in game_dict[winner]:
                winning_players.append(self.bot.get_user(player).name)
            for player in game_dict[loser]:
                losing_players.append(self.bot.get_user(player).name)

            embed = discord.Embed(
                title=f"{game_dict['tier'].capitalize()} Game: {game_id.split('-')[0]}",
                color=0x83FF00,
            )
            embed.add_field(
                name="Winning Team",
                value=", ".join(player for player in winning_players),
                inline=False,
            )
            embed.add_field(
                name="Losing Team",
                value=", ".join(player for player in losing_players),
                inline=False,
            )
            embed.set_footer(
                text=f"Powered by RLI, for RLI",
                icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
            )
            await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(reporting(bot))
