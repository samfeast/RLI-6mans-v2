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
POINTS_FOR_LOSS = config["POINTS_FOR_LOSS"]


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
        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Reporting",
                f"'ping_reporting' used by {interaction.user.name} [{interaction.user.id}]",
            ]
        )
        await interaction.response.send_message("Pong!", ephemeral=True)

    @app_commands.command(description="Report a win.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def win(self, interaction: discord.Interaction, game_id: str):
        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Reporting",
                f"'win' used by {interaction.user.name} [{interaction.user.id}] for {game_id.upper()}",
            ]
        )
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
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Reporting",
                    f"{game_id.upper()} does not exist",
                ]
            )
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
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Reporting",
                    f"{interaction.user.name} [{interaction.user.id}] does not have permission to report {game_id}",
                ]
            )
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

            game_log["stats_queue"].append(game_id)

            with open("json/game_log.json", "w") as write_file:
                json.dump(game_log, write_file, indent=2)

            with open("json/player_data.json", "r") as read_file:
                player_data = json.load(read_file)

            mention_winning_players = []
            mention_losing_players = []
            for player in game_dict[winner]:
                mention_winning_players.append(self.bot.get_user(player).name)
                if str(player) in player_data[game_dict["tier"]]:
                    player_data[game_dict["tier"]][str(player)]["wins"] += 1
                    player_data[game_dict["tier"]][str(player)][
                        "points"
                    ] += POINTS_FOR_WIN
                    player_data[game_dict["tier"]][str(player)]["elo"] += elo_swing
                else:
                    player_data[game_dict["tier"]][str(player)] = {
                        "wins": 1,
                        "losses": 0,
                        "points": POINTS_FOR_WIN,
                        "elo": 1000 + elo_swing,
                    }
            for player in game_dict[loser]:
                mention_losing_players.append(self.bot.get_user(player).name)
                if str(player) in player_data[game_dict["tier"]]:
                    player_data[game_dict["tier"]][str(player)]["losses"] += 1
                    player_data[game_dict["tier"]][str(player)][
                        "points"
                    ] -= POINTS_FOR_LOSS
                    player_data[game_dict["tier"]][str(player)]["elo"] -= elo_swing
                else:
                    player_data[game_dict["tier"]][str(player)] = {
                        "wins": 0,
                        "losses": 1,
                        "points": -POINTS_FOR_LOSS,
                        "elo": 1000 - elo_swing,
                    }

            with open("json/player_data.json", "w") as write_file:
                json.dump(player_data, write_file, indent=2)

            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Reporting",
                    f"{game_id} reported by {interaction.user.name} [{interaction.user.id}] with ELO swing {round(elo_swing,1)}",
                ]
            )

            embed = discord.Embed(
                title=f"{game_dict['tier'].capitalize()} Game: {game_id.split('-')[0]}",
                color=0x83FF00,
            )
            embed.add_field(
                name=f"Winning Team\t(+{round(elo_swing,1)} ELO)",
                value=", ".join(player for player in mention_winning_players),
                inline=False,
            )
            embed.add_field(
                name=f"Losing Team\t(-{round(elo_swing,1)} ELO)",
                value=", ".join(player for player in mention_losing_players),
                inline=False,
            )
            embed.set_footer(
                text=f"Powered by RLI, for RLI",
                icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
            )
            await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Un-report a series.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def reverse_report(
        self, interaction: discord.Interaction, game_id: str, date: str
    ):
        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Reporting",
                f"'reverse_report' used by {interaction.user.name} [{interaction.user.id}] for {game_id.upper()} on {date}",
            ]
        )

        with open("json/game_log.json", "r") as read_file:
            game_log = json.load(read_file)

        full_game_id = game_id + "-" + date.replace(".", "")

        if full_game_id in game_log["complete"]:
            game_dict = game_log["complete"][full_game_id]

            winning_players = game_dict[game_dict["winner"]]
            losing_players = game_dict[game_dict["loser"]]

            mention_winning_players = []
            for player in winning_players:
                mention_winning_players.append(self.bot.get_user(player).name)

            mention_losing_players = []
            for player in losing_players:
                mention_losing_players.append(self.bot.get_user(player).name)

            embed = discord.Embed(
                title=f"{game_dict['tier'].capitalize()} Game: {game_id.split('-')[0]} ({date})",
                description="**Are you sure you wish to reverse this series result?**",
                color=0xFF8B00,
            )
            embed.add_field(
                name=f"Winning Team",
                value=", ".join(player for player in mention_winning_players),
                inline=False,
            )
            embed.add_field(
                name=f"Losing Team",
                value=", ".join(player for player in mention_losing_players),
                inline=False,
            )
            embed.set_footer(
                text=f"Powered by RLI, for RLI",
                icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
            )

            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Reporting",
                    f"{full_game_id} is valid - launching confirmation view",
                ]
            )

            await interaction.response.send_message(
                embed=embed,
                view=Verify_Reversal(self.bot, full_game_id, interaction.user.id),
            )
        else:
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Reporting",
                    f"{full_game_id} does not exist",
                ]
            )
            await interaction.response.send_message(
                f"No series with ID {game_id} could be found on {date}"
            )


class Verify_Reversal(discord.ui.View):
    def __init__(self, bot, game_id: str, user: int):
        super().__init__(timeout=300)
        self.game_id = game_id
        self.bot = bot
        self.user = user

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        message = await interaction.original_response()
        if interaction.user.id == self.user:
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Reporting",
                    f"Reversing {self.game_id}",
                ]
            )
            await interaction.followup.send(
                f"{self.game_id.split('-')[0]} has been reversed. It can now be reported by players on the winning team."
            )
            await interaction.followup.edit_message(message_id=message.id, view=None)

            with open("json/game_log.json", "r") as read_file:
                game_log = json.load(read_file)

            with open("json/player_data.json", "r") as read_file:
                player_data = json.load(read_file)

            game_dict = game_log["complete"][self.game_id]

            for player in game_dict[game_dict["winner"]]:
                player_data[game_dict["tier"]][str(player)]["wins"] -= 1
                player_data[game_dict["tier"]][str(player)]["points"] -= POINTS_FOR_WIN
                player_data[game_dict["tier"]][str(player)]["elo"] -= game_dict[
                    "elo_swing"
                ]

            for player in game_dict[game_dict["loser"]]:
                player_data[game_dict["tier"]][str(player)]["losses"] -= 1
                player_data[game_dict["tier"]][str(player)]["points"] += POINTS_FOR_LOSS
                player_data[game_dict["tier"]][str(player)]["elo"] += game_dict[
                    "elo_swing"
                ]

            game_dict["reported"] = None
            game_dict["winner"] = None
            game_dict["loser"] = None
            game_dict["elo_swing"] = None
            game_dict["timeout_immunity"] = True

            game_log["live"][self.game_id] = game_dict
            del game_log["complete"][self.game_id]

            with open("json/game_log.json", "w") as write_file:
                json.dump(game_log, write_file, indent=2)

            with open("json/player_data.json", "w") as write_file:
                json.dump(player_data, write_file, indent=2)

        else:
            await interaction.followup.send(
                "You do not have permission to respond to this", ephemeral=True
            )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        message = await interaction.original_response()
        if interaction.user.id == self.user:
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Reporting",
                    f"Cancelling reversal for {self.game_id}",
                ]
            )
            await interaction.followup.send(f"Cancelled. The series was not reversed.")
            await interaction.followup.edit_message(message_id=message.id, view=None)
        else:
            await interaction.followup.send(
                "You do not have permission to respond to this", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(reporting(bot))
