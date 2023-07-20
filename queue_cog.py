from asyncore import write
import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import time
import csv
from datetime import datetime
import pytz
import itertools

with open("json/config.json", "r") as read_file:
    config = json.load(read_file)

GUILD_ID = config["GUILD_ID"]

ELITE = config["CHANNELS"]["ELITE"]
PREMIER = config["CHANNELS"]["PREMIER"]
CHAMPIONSHIP = config["CHANNELS"]["CHAMPIONSHIP"]
CASUAL = config["CHANNELS"]["CASUAL"]

ELITE_LOGS = config["CHANNELS"]["ELITE_LOGS"]
PREMIER_LOGS = config["CHANNELS"]["PREMIER_LOGS"]
CHAMPIONSHIP_LOGS = config["CHANNELS"]["CHAMPIONSHIP_LOGS"]
CASUAL_LOGS = config["CHANNELS"]["CASUAL_LOGS"]

ELO_SENSITIVITY = 200

# 5/6 players queued for ease of testing
queue = {
    "elite": {
        935182920019234887: 1,
        1104162909120110603: 2,
        865798504714338324: 3,
        988906946725822484: 4,
        963466636059365476: 5,
    },
    "premier": {},
    "championship": {},
    "casual": {},
}
active_queues = {}
queue_lock = {
    "elite": False,
    "premier": False,
    "championship": False,
    "casual": False,
}
view_messages = []


def log_event(event):
    with open("logs/live_logs.csv", "a", newline="") as write_file:
        writer = csv.writer(write_file)
        writer.writerow(event)


class queue_handler(commands.Cog):
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
            if interaction.user.id in queue["elite"]:
                await interaction.response.send_message(
                    "You are already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    interaction.user,
                    "elite",
                    ELITE,
                    False,
                )
        elif interaction.channel.id == PREMIER:
            if interaction.user.id in queue["premier"]:
                await interaction.response.send_message(
                    "You are already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    interaction.user,
                    "premier",
                    PREMIER,
                    False,
                )
        elif interaction.channel.id == CHAMPIONSHIP:
            if interaction.user.id in queue["championship"]:
                await interaction.response.send_message(
                    "You are already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    interaction.user,
                    "championship",
                    CHAMPIONSHIP,
                    False,
                )
        elif interaction.channel.id == CASUAL:
            if interaction.user.id in queue["casual"]:
                await interaction.response.send_message(
                    "You are already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    interaction.user,
                    "casual",
                    CASUAL,
                    False,
                )
        else:
            await interaction.response.send_message(
                "Queuing is not enabled in this channel.", ephemeral=True
            )

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
            if user.id in queue["elite"]:
                await interaction.response.send_message(
                    "User is already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    user,
                    "elite",
                    ELITE,
                    True,
                )
        elif interaction.channel.id == PREMIER_LOGS:
            if user.id in queue["premier"]:
                await interaction.response.send_message(
                    "User is already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    user,
                    "premier",
                    PREMIER,
                    True,
                )
        elif interaction.channel.id == CHAMPIONSHIP_LOGS:
            if user.id in queue["championship"]:
                await interaction.response.send_message(
                    "User is already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    user,
                    "championship",
                    CHAMPIONSHIP,
                    True,
                )
        elif interaction.channel.id == CASUAL_LOGS:
            if user.id in queue["casual"]:
                await interaction.response.send_message(
                    "User is already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction,
                    user,
                    "casual",
                    CASUAL,
                    True,
                )
        else:
            await interaction.response.send_message(
                "This command must be used in the corresponding logs channel.",
                ephemeral=True,
            )

    async def add_to_queue(self, interaction, user, tier, queue_channel_id, added):
        queue_channel = self.bot.get_channel(queue_channel_id)

        if queue_lock[tier] == True:
            await interaction.response.send_message(
                "Another user tried to join the queue at the same time, causing your command to fail. Please try again.",
                ephemeral=True,
            )

            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"{user.name} [{user.id}] was blocked from joining the {queue_channel.name[:-6]} queue to prevent a race condition",
                ]
            )

        else:
            queue_lock[tier] = True

            queue[tier][user.id] = round(time.time())

            if added:
                embed = discord.Embed(
                    title="Player Added",
                    description=f"{user.mention} has been added to the <#{queue_channel_id}> queue",
                    color=0x83FF00,
                )
                await interaction.response.send_message(embed=embed)

                if len(queue[tier]) == 1:
                    embed = discord.Embed(title="1 player is in the queue!")
                    embed.set_footer(
                        text="5 more needed!",
                        icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                    )
                    embed.color = 0xFF8B00
                elif len(queue[tier]) == 6:
                    embed = discord.Embed(title="6 players are in the queue!")
                    embed.set_footer(
                        text="LETS GOOOO!",
                        icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                    )
                    embed.color = 0x83FF00
                else:
                    embed = discord.Embed(
                        title=f"{len(queue[tier])} players are in the queue!"
                    )
                    embed.set_footer(
                        text=f"{6-len(queue[tier])} more needed!",
                        icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                    )
                    embed.color = 0xFF8B00
                embed.description = f"{user.mention} has been added to the queue."
                await queue_channel.send(embed=embed)
            else:
                if len(queue[tier]) == 1:
                    embed = discord.Embed(title="1 player is in the queue!")
                    embed.set_footer(
                        text="5 more needed!",
                        icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                    )
                    embed.color = 0xFF8B00

                elif len(queue[tier]) == 6:
                    embed = discord.Embed(title="6 players are in the queue!")
                    embed.set_footer(
                        text="LETS GOOOO!",
                        icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                    )
                    embed.color = 0x83FF00

                else:
                    embed = discord.Embed(
                        title=f"{len(queue[tier])} players are in the queue!"
                    )
                    embed.set_footer(
                        text=f"{6-len(queue[tier])} more needed!",
                        icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                    )
                    embed.color = 0xFF8B00
                embed.description = f"{user.mention} has joined the queue."
                await interaction.response.send_message(embed=embed)

            queue_lock[tier] = False

            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"{user.name} [{user.id}] has been added to the {tier} queue ({len(queue[tier])} in queue)",
                ]
            )

            if len(queue[tier]) == 6:
                with open("json/game_log.json", "r") as read_file:
                    game_log = json.load(read_file)

                # Crude method of picking a game id which hasn't been used before
                date = datetime.now(pytz.timezone("Europe/Dublin")).strftime("%d%m%y")
                game_id = "RLI" + str(random.randint(1, 999)) + "-" + date

                while (
                    game_id in active_queues
                    or game_id in game_log["live"]
                    or game_id in game_log["complete"]
                ):
                    game_id = "RLI" + str(random.randint(1, 10)) + "-" + date

                active_queues[game_id] = {
                    "tier": tier,
                    "players": list(queue[tier].keys()),
                    "voted": [],
                    "random": 0,
                    "captains": 0,
                    "balanced": 0,
                }

                log_event(
                    [
                        round(time.time(), 2),
                        time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                        "Queue",
                        f"Queue filled in {queue_channel.name[:-6]} containing {', '.join(map(str, active_queues[game_id]['players']))} ({game_id})",
                    ]
                )

                queue[tier] = {}

                embed = discord.Embed(title=f"Queue has been reset.", color=0xFF8B00)
                embed.set_footer(
                    text=f"When's the next one...?",
                    icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                )
                await queue_channel.send(embed=embed)

                log_event(
                    [
                        round(time.time(), 2),
                        time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                        "Queue",
                        f"Team Picker view launched for {game_id}",
                    ]
                )

                mention_players = []
                for player in active_queues[game_id]["players"]:
                    mention_players.append(self.bot.get_user(player).mention)

                embed = discord.Embed(title="Choose team type!", color=0xFFFFFF)
                embed.set_footer(
                    text="Powered by RLI",
                    icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                )

                message = await queue_channel.send(
                    " ".join(mention_players),
                    embed=embed,
                    view=Team_Picker(self.bot, game_id),
                )
                view_messages.append(message)

    # Leave command
    @app_commands.command(description="Leave the queue.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def l(self, interaction: discord.Interaction):
        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Queue",
                f"'l' used by {interaction.user.name} [{interaction.user.id}] in {interaction.channel.name} [{interaction.channel.id}]",
            ]
        )

        if interaction.channel_id == ELITE:
            await self.remove_from_queue(
                interaction,
                interaction.user,
                "elite",
                ELITE,
                False,
            )
        elif interaction.channel_id == PREMIER:
            await self.remove_from_queue(
                interaction,
                interaction.user,
                "premier",
                PREMIER,
                False,
            )
        elif interaction.channel_id == CHAMPIONSHIP:
            await self.remove_from_queue(
                interaction,
                interaction.user,
                "championship",
                CHAMPIONSHIP,
                False,
            )
        elif interaction.channel_id == CASUAL:
            await self.remove_from_queue(
                interaction,
                interaction.user,
                "casual",
                CASUAL,
                False,
            )
        else:
            await interaction.response.send_message(
                "Queuing is not enabled in this channel.", ephemeral=True
            )

    # Leave command
    @app_commands.command(description="Remove a user from the queue.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def remove(self, interaction: discord.Interaction, user: discord.User):
        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Queue",
                f"'remove' used by {interaction.user.name} [{interaction.user.id}] in {interaction.channel.name} [{interaction.channel.id}] on {user.name} [{user.id}]",
            ]
        )

        if interaction.channel_id == ELITE_LOGS:
            await self.remove_from_queue(
                interaction,
                user,
                "elite",
                ELITE,
                True,
            )
        elif interaction.channel_id == PREMIER_LOGS:
            await self.remove_from_queue(
                interaction,
                user,
                "premier",
                PREMIER,
                True,
            )
        elif interaction.channel_id == CHAMPIONSHIP_LOGS:
            await self.remove_from_queue(
                interaction,
                user,
                "championship",
                CHAMPIONSHIP,
                True,
            )
        elif interaction.channel_id == CASUAL_LOGS:
            await self.remove_from_queue(
                interaction,
                user,
                "casual",
                CASUAL,
                True,
            )
        else:
            await interaction.response.send_message(
                "Queuing is not enabled in this channel.", ephemeral=True
            )

    # Queue removal function
    async def remove_from_queue(
        self, interaction, user, tier, queue_channel_id, removed
    ):
        queue_channel = self.bot.get_channel(queue_channel_id)
        try:
            del queue[tier][user.id]
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"{user.name} [{user.id}] has been removed from the {queue_channel.name[:-6]} queue ({len(queue[tier])} in queue)",
                ]
            )
            if removed:
                embed = discord.Embed(
                    title="Player Removed",
                    description=f"{user.mention} has been removed from the <#{queue_channel_id}> queue",
                    color=0xFF0000,
                )
                await interaction.response.send_message(embed=embed)

                if len(queue[tier]) == 1:
                    embed = discord.Embed(title="1 player is in the queue!")
                    embed.set_footer(
                        text="5 more needed!",
                        icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                    )
                else:
                    embed = discord.Embed(
                        title=f"{len(queue[tier])} players are in the queue!"
                    )
                    embed.set_footer(
                        text=f"{str(6-len(queue[tier]))} more needed!",
                        icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                    )
                embed.color = 0xFFFFFF
                embed.description = f"{user.mention} has been removed from the queue."
                await queue_channel.send(embed=embed)
            else:
                if len(queue) == 1:
                    embed = discord.Embed(title="1 player is in the queue!")
                    embed.set_footer(
                        text="5 more needed!",
                        icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                    )
                else:
                    embed = discord.Embed(
                        title=f"{len(queue[tier])} players are in the queue!"
                    )
                    embed.set_footer(
                        text=f"{str(6-len(queue[tier]))} more needed!",
                        icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                    )
                embed.color = 0xFFFFFF
                embed.description = f"{user.mention} has left the queue."
                await interaction.response.send_message(embed=embed)
        except KeyError:
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"Unable to remove {user.name} [{user.id}] from the {queue_channel.name[:-6]} queue",
                ]
            )
            if removed:
                await interaction.response.send_message("User is not in the queue.")
            else:
                await interaction.response.send_message(
                    "You are not in the queue.", ephemeral=True
                )

    # Status command
    @app_commands.command(description="Check how many players are in the queue.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def status(self, interaction: discord.Interaction):
        if interaction.channel_id == ELITE:
            await self.show_status(interaction, queue["elite"])
        elif interaction.channel_id == PREMIER:
            await self.show_status(interaction, queue["premier"])
        elif interaction.channel_id == CHAMPIONSHIP:
            await self.show_status(interaction, queue["championship"])
        elif interaction.channel_id == CASUAL:
            await self.show_status(interaction, queue["casual"])
        else:
            await interaction.response.send_message(
                "There is no queue in this channel.", ephemeral=True
            )

    async def show_status(self, interaction, queue):
        players = []
        for player in list(queue.keys()):
            players.append(self.bot.get_user(player).mention)

        if len(queue) == 1:
            embed = discord.Embed(title="1 player is in the queue")
        else:
            embed = discord.Embed(title=f"{len(queue)} players are in the queue")
        embed.description = " ".join(players)
        embed.color = 0xFF8B00
        embed.set_footer(
            text=f"{str(6-len(queue))} more needed!",
            icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
        )
        await interaction.response.send_message(embed=embed)


class Team_Picker(discord.ui.View):
    def __init__(self, bot, game_id: str):
        super().__init__(timeout=300)
        self.game_id = game_id
        self.bot = bot

    # Check if any of the criteria needed for voting to be resolved have been met, if so return winning team type, else return unresovled
    def resolve_voting(self, game_id):
        random_votes = active_queues[game_id]["random"]
        captains_votes = active_queues[game_id]["captains"]
        balanced_votes = active_queues[game_id]["balanced"]

        if random_votes >= 4:
            return "random"
        elif captains_votes >= 3:
            return "captains"
        elif balanced_votes >= 4:
            return "balanced"
        elif random_votes + captains_votes + balanced_votes == 6:
            if random_votes > captains_votes and random_votes > balanced_votes:
                return "random"
            elif captains_votes > random_votes and captains_votes > balanced_votes:
                return "captains"
            elif balanced_votes > random_votes and balanced_votes > captains_votes:
                return "balanced"
            elif random_votes == 3 and balanced_votes == 3:
                return "balanced"
            else:
                return "captains"
        else:
            return "unresolved"

    # Generate two teams from a given queue and team type
    async def make_teams(self, interaction, game_id, team_type):
        tier = active_queues[game_id]["tier"]

        with open("json/player_data.json", "r") as read_file:
            player_data = json.load(read_file)

        current_queue = active_queues[game_id]["players"]
        if team_type == "random":
            # TODO: Current setup is 'simple random' - eventually this should ensure that the teams aren't identical to the previous match if the same players are in the queue
            random.shuffle(queue)
            team1 = [current_queue[0], current_queue[1], current_queue[2]]
            team2 = [current_queue[3], current_queue[4], current_queue[5]]
        elif team_type == "captains":
            team1 = []
            team2 = []

        elif team_type == "balanced":
            # Calculate the total elo of all the players in the lobby - half of this is the 'target elo' for each team
            total_elo = 0
            for player in current_queue:
                if str(player) in player_data[tier]:
                    total_elo += player_data[tier][str(player)]["elo"]
                else:
                    total_elo += 1000

            # Get all the possible 3 person teams from the 6 players - there are 20 such combinations (6C3)
            # Technically only 10 of these are needed, as team makeup of players (1,2,3) is a mirror of (4,5,6), but performance gains would be negligible
            team_combinations = list(itertools.combinations(current_queue, r=3))

            # Go through each team combination and find the absolute difference between that combinations elo and the target elo
            # The smallest difference represents the 'fairest' team makeup
            smallest_difference = 999999
            for team_combination in team_combinations:
                combination_elo = 0
                for i in range(3):
                    if str(team_combination[i]) in player_data[tier]:
                        combination_elo += player_data[tier][str(team_combination[i])][
                            "elo"
                        ]
                    else:
                        combination_elo += 1000

                if abs((total_elo / 2) - combination_elo) < smallest_difference:
                    smallest_difference = abs((total_elo / 2) - combination_elo)
                    team1 = list(team_combination)

            team2 = []
            for player in current_queue:
                if player not in team1:
                    team2.append(player)

        team1_elo = 0
        team2_elo = 0

        for team1_player, team2_player in zip(team1, team2):
            if str(team1_player) in player_data[tier]:
                team1_elo += player_data[tier][str(team1_player)]["elo"]
            else:
                team1_elo += 1000
            if str(team2_player) in player_data[tier]:
                team2_elo += player_data[tier][str(team2_player)]["elo"]
            else:
                team2_elo += 1000

        p1_win = 1 / (1 + 10 ** ((team2_elo - team1_elo) / ELO_SENSITIVITY))
        p2_win = 1 / (1 + 10 ** ((team1_elo - team2_elo) / ELO_SENSITIVITY))

        with open("json/game_log.json", "r") as read_file:
            game_log = json.load(read_file)

        game_log["live"][game_id] = {
            "timestamp": round(time.time()),
            "tier": active_queues[game_id]["tier"],
            "team1": team1,
            "team2": team2,
            "winner": None,
            "loser": None,
            "p1_win": p1_win,
            "p2_win": p2_win,
        }

        with open("json/game_log.json", "w") as write_file:
            json.dump(game_log, write_file, indent=2)

        mention_players = []
        for player in active_queues[game_id]["players"]:
            mention_players.append(self.bot.get_user(player).mention)

        teams_embed = discord.Embed(title=f"The Teams!", color=0x83FF00)
        teams_embed.add_field(
            name="**-Team 1-**",
            value=f"{self.bot.get_user(team1[0]).name}, {self.bot.get_user(team1[1]).name}, {self.bot.get_user(team1[2]).name}",
            inline=False,
        )
        teams_embed.add_field(
            name="**-Team 2-**",
            value=f"{self.bot.get_user(team2[0]).name}, {self.bot.get_user(team2[1]).name}, {self.bot.get_user(team2[2]).name}",
            inline=False,
        )
        teams_embed.add_field(
            name="**Match Creator:**",
            value=f"{self.bot.get_user(random.choice(current_queue)).name}",
            inline=False,
        )
        teams_embed.set_footer(
            text=f"Powered by RLI",
            icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
        )
        await interaction.followup.send(" ".join(mention_players), embed=teams_embed)

    async def on_timeout(self):
        embed = discord.Embed(
            title="Queue Timed Out",
            description="The queue has been voided due to inactivity.",
            color=0xFF0000,
        )
        embed.set_footer(
            text=f"Requeue if you still wish to play",
            icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
        )
        await view_messages[0].edit(content="", embed=embed, view=None)
        view_messages.pop(0)

    @discord.ui.button(label="Random (0)", style=discord.ButtonStyle.red)
    async def random_teams_vote(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        message = await interaction.original_response()
        view_messages.remove(message)
        view_messages.append(message)
        if interaction.user.id in active_queues[self.game_id]["players"]:
            if interaction.user.id not in active_queues[self.game_id]["voted"]:
                active_queues[self.game_id]["voted"].append(interaction.user.id)
                active_queues[self.game_id]["random"] += 1
                log_event(
                    [
                        round(time.time(), 2),
                        time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                        "Queue",
                        f"{interaction.user.name} [{interaction.user.id}] voted for random teams for {self.game_id} (R: {active_queues[self.game_id]['random']}, C: {active_queues[self.game_id]['captains']}, B: {active_queues[self.game_id]['balanced']})",
                    ]
                )
                button.label = f"Random ({active_queues[self.game_id]['random']})"

                await interaction.followup.send(
                    "You have voted for random teams.", ephemeral=True
                )
                await interaction.followup.edit_message(
                    message_id=message.id, view=self
                )

                team_type = self.resolve_voting(self.game_id)

                # Override for testing
                if interaction.user.name == "res43":
                    print(f"'resolve_voting' returned {team_type}, but overriding...")
                    team_type = "random"

                if team_type == "unresolved":
                    pass
                else:
                    log_event(
                        [
                            round(time.time(), 2),
                            time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                            "Queue",
                            f"Making {team_type} teams for {self.game_id}",
                        ]
                    )
                    await self.make_teams(interaction, self.game_id, team_type)

            else:
                await interaction.followup.send(
                    "You have already voted.", ephemeral=True
                )
        else:
            await interaction.followup.send(
                "You do not have permission to vote on this queue.", ephemeral=True
            )

    @discord.ui.button(label="Captains (0)", style=discord.ButtonStyle.blurple)
    async def captains_teams_vote(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        message = await interaction.original_response()
        if interaction.user.id in active_queues[self.game_id]["players"]:
            if interaction.user.id not in active_queues[self.game_id]["voted"]:
                active_queues[self.game_id]["voted"].append(interaction.user.id)
                active_queues[self.game_id]["captains"] += 1
                log_event(
                    [
                        round(time.time(), 2),
                        time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                        "Queue",
                        f"{interaction.user.name} [{interaction.user.id}] voted for captains teams for {self.game_id} (R: {active_queues[self.game_id]['random']}, C: {active_queues[self.game_id]['captains']}, B: {active_queues[self.game_id]['balanced']})",
                    ]
                )
                button.label = f"Captains ({active_queues[self.game_id]['captains']})"

                await interaction.followup.send(
                    "You have voted for captains teams.", ephemeral=True
                )
                await interaction.followup.edit_message(
                    message_id=message.id, view=self
                )

                team_type = self.resolve_voting(self.game_id)

                # Override for testing
                if interaction.user.name == "res43":
                    print(f"'resolve_voting' returned {team_type}, but overriding...")
                    team_type = "captains"

                if team_type == "unresolved":
                    pass
                else:
                    log_event(
                        [
                            round(time.time(), 2),
                            time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                            "Queue",
                            f"Making {team_type} teams for {self.game_id}",
                        ]
                    )
                    await self.make_teams(interaction, self.game_id, team_type)

            else:
                await interaction.followup.send(
                    "You have already voted.", ephemeral=True
                )
        else:
            await interaction.followup.send(
                "You do not have permission to vote on this queue.", ephemeral=True
            )

    @discord.ui.button(label="Balanced (0)", style=discord.ButtonStyle.green)
    async def balanced_teams_vote(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Queue",
                f"{interaction.user.name} [{interaction.user.id}] voted for balanced teams for {self.game_id}",
            ]
        )

        await interaction.response.defer()
        message = await interaction.original_response()
        if interaction.user.id in active_queues[self.game_id]["players"]:
            if interaction.user.id not in active_queues[self.game_id]["voted"]:
                active_queues[self.game_id]["voted"].append(interaction.user.id)
                active_queues[self.game_id]["balanced"] += 1
                log_event(
                    [
                        round(time.time(), 2),
                        time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                        "Queue",
                        f"{interaction.user.name} [{interaction.user.id}] voted for balanced teams for {self.game_id} (R: {active_queues[self.game_id]['random']}, C: {active_queues[self.game_id]['captains']}, B: {active_queues[self.game_id]['balanced']})",
                    ]
                )
                button.label = f"Balanced ({active_queues[self.game_id]['balanced']})"

                await interaction.followup.send(
                    "You have voted for balanced teams.", ephemeral=True
                )
                await interaction.followup.edit_message(
                    message_id=message.id, view=self
                )

                team_type = self.resolve_voting(self.game_id)

                # Override for testing
                if interaction.user.name == "res43":
                    print(f"'resolve_voting' returned {team_type}, but overriding...")
                    team_type = "balanced"

                if team_type == "unresolved":
                    pass
                else:
                    log_event(
                        [
                            round(time.time(), 2),
                            time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                            "Queue",
                            f"Making {team_type} teams for {self.game_id}",
                        ]
                    )
                    await self.make_teams(interaction, self.game_id, team_type)

            else:
                await interaction.followup.send(
                    "You have already voted.", ephemeral=True
                )
        else:
            await interaction.followup.send(
                "You do not have permission to vote on this queue.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(queue_handler(bot))
