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
race_condition_queue_lock = {
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

        if race_condition_queue_lock[tier] == True:
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
            race_condition_queue_lock[tier] = True

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

            race_condition_queue_lock[tier] = False

            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"{user.name} [{user.id}] has been added to the {queue_channel.name[:-6]} queue ({len(queue[tier])} in queue)",
                ]
            )

            if len(queue[tier]) == 6:
                # Crude method of picking a game id which isn't already the id of another active queue
                game_id = "RLI" + str(random.randint(1, 10))

                while game_id in active_queues:
                    game_id = "RLI" + str(random.randint(1, 10))

                active_queues[game_id] = {
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
                    " ".join(mention_players), embed=embed, view=Team_Picker(game_id)
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
                embed.description = f"{user.mention} has left the queue."
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


class Team_Picker(discord.ui.View):
    def __init__(self, game_id: str):
        super().__init__(timeout=10)
        self.game_id = game_id

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
    async def make_teams(self, game_id, team_type):
        queue = active_queues[game_id]["players"]
        if team_type == "random":
            random.shuffle(queue)
            team1 = [queue[0], queue[1], queue[2]]
            team2 = [queue[3], queue[4], queue[5]]
        elif team_type == "captains":
            team1 = []
            team2 = []
        elif team_type == "balanced":
            team1 = []
            team2 = []

        return team1, team2

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
                    team1, team2 = await self.make_teams(self.game_id, team_type)
                    print(team1)
                    print(team2)
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
                    team1, team2 = await self.make_teams(self.game_id, team_type)
                    print(team1)
                    print(team2)
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
                    team1, team2 = await self.make_teams(self.game_id, team_type)
                    print(team1)
                    print(team2)
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
