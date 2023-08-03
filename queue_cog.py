# TODO: Migrate to a sqlite database using either asqlite or aiosqlite
# This would replace all json records which are prone to data loss
# Look into connection pooling
# TODO: Come up with a naming system for variables and everything
# Standardise the meaning of everything to make code more readable
# TODO: Just import the config dictionary rather than using loads of different variables
# Also include things like timeout constants in config for more customisation

from asyncore import write
import discord
from discord.ext import commands, tasks
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

CHANNELS = {
    "elite": config["CHANNELS"]["ELITE"],
    "premier": config["CHANNELS"]["PREMIER"],
    "championship": config["CHANNELS"]["CHAMPIONSHIP"],
    "casual": config["CHANNELS"]["CASUAL"],
    "elite_logs": config["CHANNELS"]["ELITE_LOGS"],
    "premier_logs": config["CHANNELS"]["PREMIER_LOGS"],
    "championship_logs": config["CHANNELS"]["CHAMPIONSHIP_LOGS"],
    "casual_logs": config["CHANNELS"]["CASUAL_LOGS"],
}

ELO_SENSITIVITY = config["ELO_SENSITIVITY"]
TEAM_PICKER_COLOURS = {"random": 0xDA373C, "captains": 0x5865F2, "balanced": 0x248046}

# 5/6 players queued for ease of testing
queue = {
    "elite": {
        935182920019234887: 2000000000,
        1104162909120110603: 2000000000,
        865798504714338324: 2000000000,
        988906946725822484: 2000000000,
        963466636059365476: 2000000000,
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
resolved_team_picker_messages = []


def log_event(event):
    with open("logs/live_logs.csv", "a", newline="") as write_file:
        writer = csv.writer(write_file)
        writer.writerow(event)


class queue_handler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue_reminder.start()
        self.cleaner.start()

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

    # Removes active queues and unreported games after 1 hour and 8 hours respectively
    @tasks.loop(minutes=2)
    async def cleaner(self):
        timestamp = round(time.time())

        active_queues_to_remove = []
        live_games_to_remove = []

        for active_queue in active_queues:
            if timestamp - active_queues[active_queue]["timestamp"] > 3600:
                active_queues_to_remove.append(active_queue)

        with open("json/game_log.json", "r") as read_file:
            game_log = json.load(read_file)

        for game in game_log["live"]:
            if (
                timestamp - game_log["live"][game]["created"] > 28800
                and game_log["live"][game]["timeout_immunity"] == False
            ):
                live_games_to_remove.append(game)

        for queue in active_queues_to_remove:
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"Deleting {queue} from active queues (>1 hour since creation)",
                ]
            )
            del active_queues[queue]
        for game in live_games_to_remove:
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"Deleting {game} from live game log (>8 hours since creation)",
                ]
            )
            del game_log["live"][game]

        if len(live_games_to_remove) > 0:
            with open("json/game_log.json", "w") as write_file:
                json.dump(game_log, write_file, indent=2)

    @cleaner.before_loop
    async def before_queue_reminder(self):
        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Queue",
                f"Cleaner task loop waiting for bot startup",
            ]
        )
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=2)
    async def queue_reminder(self):
        with open("json/member_info.json", "r") as read_file:
            member_info = json.load(read_file)

        dm_notices = {}
        ping_notices = {}
        removal_notices = {}

        for tier in list(queue.keys()):
            for player in queue[tier]:
                time_delta = time.time() - queue[tier][player]
                # Once 14400 seconds (4 hours) have elapsed players are forcibly removed from the queue - this value can be changed
                # NOTE: For users without /reminder set up, the 'elapsed' field must be greater than this 14400 value to avoid errors
                if time_delta > 14400:
                    if player in removal_notices:
                        removal_notices[player].append(tier)
                    else:
                        removal_notices[player] = [tier]
                else:
                    if str(player) in member_info:
                        player_reminder_settings = member_info[str(player)]["reminder"]
                        if time_delta > player_reminder_settings["interval"]:
                            if player_reminder_settings["message_type"] == "DM":
                                if player in dm_notices:
                                    dm_notices[player].append(tier)
                                else:
                                    dm_notices[player] = [tier]
                            elif player_reminder_settings["message_type"] == "Ping":
                                if player in ping_notices:
                                    ping_notices[player].append(tier)
                                else:
                                    ping_notices[player] = [tier]

        if len(dm_notices) + len(ping_notices) + len(removal_notices) == 0:
            pass
        else:
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"Reminder task loop run with {len(dm_notices)} DM notices, {len(ping_notices)} ping notices, and {len(removal_notices)} removal notices required",
                ]
            )
            await self.send_dm_notices(member_info, dm_notices)
            await self.send_ping_notices(member_info, ping_notices)
            await self.send_removal_notices(removal_notices)

    async def send_dm_notices(self, member_info, dm_notices):
        for player in dm_notices:
            player_user = self.bot.get_user(player)

            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"Processing DM notice for {player_user.name} [{player}] (Type: {member_info[str(player)]['reminder']['type']})",
                ]
            )

            embed = discord.Embed()
            embed.set_footer(
                text="Change behaviour with /reminder",
                icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
            )
            if member_info[str(player)]["reminder"]["type"] == "Reminder":
                embed.title = "Reminder!"
                embed.description = (
                    f"You are still in the {' and '.join(dm_notices[player])} queue"
                )
                embed.color = 0x0062FF
                for tier in dm_notices[player]:
                    queue[tier][player] = round(time.time())
            elif member_info[str(player)]["reminder"]["type"] == "Remove":
                embed.title = "Removed for inactivity"
                embed.description = f"You have been removed from the {' and '.join(dm_notices[player])} queue"
                embed.color = 0xFF0000
                for tier in dm_notices[player]:
                    await self.remove_from_queue(
                        None, player_user, tier, CHANNELS[tier], True
                    )

            try:
                await player_user.send(embed=embed)
            except Exception as e:
                log_event(
                    [
                        round(time.time(), 2),
                        time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                        "Queue",
                        f"Failed to DM {player_user.name} [{player}]: {e}",
                    ]
                )

    async def send_ping_notices(self, member_info, ping_notices):
        for player in ping_notices:
            player_user = self.bot.get_user(player)

            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"Processing ping notice for {player_user.name} [{player}] (Type: {member_info[str(player)]['reminder']['type']})",
                ]
            )

            embed = discord.Embed()
            embed.set_footer(
                text="Change behaviour with /reminder",
                icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
            )
            if member_info[str(player)]["reminder"]["type"] == "Reminder":
                embed.title = "Reminder!"
                embed.description = (
                    f"{player_user.mention} - you are still in the queue"
                )
                embed.color = 0x0062FF
                for tier in ping_notices[player]:
                    queue[tier][player] = round(time.time())
                    tier_channel = self.bot.get_channel(CHANNELS[tier])
                    await tier_channel.send(f"||{player_user.mention}||", embed=embed)

            elif member_info[str(player)]["reminder"]["type"] == "Remove":
                embed.title = "Removed for inactivity"
                embed.description = (
                    f"{player_user.mention} - you have been removed from the queue"
                )
                embed.color = 0xFF0000
                for tier in ping_notices[player]:
                    tier_channel = self.bot.get_channel(CHANNELS[tier])
                    await tier_channel.send(f"||{player_user.mention}||", embed=embed)
                    await self.remove_from_queue(
                        None, player_user, tier, CHANNELS[tier], True
                    )

    async def send_removal_notices(self, removal_notices):
        for player in removal_notices:
            player_user = self.bot.get_user(player)

            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"Processing removal notice for {player_user.name} [{player}] (Type: Forced Removal)",
                ]
            )

            embed = discord.Embed(
                title="Removed for inactivity",
                description=f"{player_user.mention} - you have been removed from the queue",
                color=0xFF0000,
            )
            embed.set_footer(
                text="Rejoin the queue if you still wish to play",
                icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
            )

            for tier in removal_notices[player]:
                tier_channel = self.bot.get_channel(CHANNELS[tier])
                await tier_channel.send(f"||{player_user.mention}||", embed=embed)
                await self.remove_from_queue(
                    None, player_user, tier, CHANNELS[tier], True
                )

    @queue_reminder.before_loop
    async def before_queue_reminder(self):
        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Queue",
                f"Reminder task loop waiting for bot startup",
            ]
        )
        await self.bot.wait_until_ready()

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

        tier = None
        if interaction.channel.id == CHANNELS["elite"]:
            tier = "elite"
        elif interaction.channel.id == CHANNELS["premier"]:
            tier = "premier"
        elif interaction.channel.id == CHANNELS["championship"]:
            tier = "championship"
        elif interaction.channel.id == CHANNELS["casual"]:
            tier = "casual"
        else:
            await interaction.response.send_message(
                "Queuing is not enabled in this channel.", ephemeral=True
            )

        if tier:
            if interaction.user.id in queue[tier]:
                await interaction.response.send_message(
                    "You are already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(
                    interaction, interaction.user, tier, CHANNELS[tier], False
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

        tier = None
        if interaction.channel.id == CHANNELS["elite_logs"]:
            tier = "elite"
        elif interaction.channel.id == CHANNELS["premier_logs"]:
            tier = "premier"
        elif interaction.channel.id == CHANNELS["championship_logs"]:
            tier = "championship"
        elif interaction.channel.id == CHANNELS["casual_logs"]:
            tier = "casual"
        else:
            await interaction.response.send_message(
                "This command must be used in the corresponding logs channel.",
                ephemeral=True,
            )

        if tier:
            if user.id in queue[tier]:
                await interaction.response.send_message(
                    "User is already in the queue.", ephemeral=True
                )
            else:
                await self.add_to_queue(interaction, user, tier, CHANNELS[tier], True)

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
                    game_id = "RLI" + str(random.randint(1, 999)) + "-" + date

                active_queues[game_id] = {
                    "timestamp": round(time.time()),
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

                # Could this be refactored to be nicer than this?
                mention_players = []
                for player in active_queues[game_id]["players"]:
                    player_user = self.bot.get_user(player)
                    mention_players.append(player_user.mention)
                    if player in queue["elite"] and tier != "elite":
                        await self.remove_from_queue(
                            None, player_user, "elite", CHANNELS["elite"], True
                        )
                    if player in queue["premier"] and tier != "premier":
                        await self.remove_from_queue(
                            None, player_user, "premier", CHANNELS["premier"], True
                        )
                    if player in queue["championship"] and tier != "championship":
                        await self.remove_from_queue(
                            None, player_user, "championship", CHANNELS["championship"], True
                        )
                    if player in queue["casual"] and tier != "casual":
                        await self.remove_from_queue(
                            None, player_user, "casual", CHANNELS["casual"], True
                        )

                queue[tier] = {}

                log_event(
                    [
                        round(time.time(), 2),
                        time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                        "Queue",
                        f"Launching team picker view for {game_id}",
                    ]
                )

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
        tier = None
        if interaction.channel_id == CHANNELS["elite"]:
            tier = "elite"
        elif interaction.channel_id == CHANNELS["premier"]:
            tier = "premier"
        elif interaction.channel_id == CHANNELS["championship"]:
            tier = "championship"
        elif interaction.channel_id == CHANNELS["casual"]:
            tier = "casual"
        else:
            await interaction.response.send_message(
                "Queuing is not enabled in this channel.", ephemeral=True
            )
        
        if tier:
            await self.remove_from_queue(interaction, interaction.user, tier, CHANNELS[tier], False)

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

        tier = None
        if interaction.channel_id == CHANNELS["elite_logs"]:
            tier = "elite"
        elif interaction.channel_id == CHANNELS["premier_logs"]:
            tier = "premier"
        elif interaction.channel_id == CHANNELS["championship_logs"]:
            tier = "championship"
        elif interaction.channel_id == CHANNELS["casual_logs"]:
            tier = "casual"
        else:
            await interaction.response.send_message(
                "This command must be used in the corresponding logs channel.", ephemeral=True
            )

        if tier:
            await self.remove_from_queue(interaction, user, tier, CHANNELS[tier], True)

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
                # When the task loop removes a user from the queue there is no interaction, so no response can/needs to be sent
                if interaction != None:
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
                if interaction != None:
                    await interaction.response.send_message("User is not in the queue.")
            else:
                await interaction.response.send_message(
                    "You are not in the queue.", ephemeral=True
                )

    # Status command
    @app_commands.command(description="Check how many players are in the queue.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def status(self, interaction: discord.Interaction):
        if interaction.channel_id == CHANNELS["elite"]:
            await self.show_status(interaction, queue["elite"])
        elif interaction.channel_id == CHANNELS["premier"]:
            await self.show_status(interaction, queue["premier"])
        elif interaction.channel_id == CHANNELS["championship"]:
            await self.show_status(interaction, queue["championship"])
        elif interaction.channel_id == CHANNELS["casual"]:
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
            with open("json/game_log.json", "r") as read_file:
                game_log = json.load(read_file)

            # Makes a list containing all the game IDs of completed series, and reverses it so that most recently reported series are at the front of the list
            game_log_keys = list(game_log["complete"].keys())
            game_log_keys.reverse()

            # Get a list of game IDs of series started within the last 10800 seconds (3 hours)
            current_timestamp = round(time.time())
            recent_matches = []
            for key in game_log_keys:
                if current_timestamp - game_log["complete"][key]["reported"] < 10800:
                    recent_matches.append(key)

            # Filter recent_matches to only contain matches containing the same 6 players as the current queue
            filtered_matches = list(
                (
                    key
                    for key in recent_matches
                    if sorted(current_queue)
                    == sorted(
                        game_log["complete"][key]["team1"]
                        + game_log["complete"][key]["team2"]
                    )
                )
            )

            if filtered_matches != []:
                log_event(
                    [
                        round(time.time(), 2),
                        time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                        "Queue",
                        f"{len(recent_matches)} recent matches found {recent_matches} with {len(filtered_matches)} {filtered_matches} containing the same players as the current queue {game_id}",
                    ]
                )

            # Keep randomising the teams until it finds a combination that hasn't been seen in any of the filtered matches
            # In theory (but likely never in reality) if all 10 team compositions have been played in the last 3 hours, this won't be able to find a new combination
            # If it fails to make unique teams 100 times in a row, it will still return teams that are repeats of a previous queue
            shuffle_attempts = 0
            while shuffle_attempts < 100:
                shuffle_attempts += 1

                random.shuffle(current_queue)
                team1 = [current_queue[0], current_queue[1], current_queue[2]]
                team2 = [current_queue[3], current_queue[4], current_queue[5]]

                count_unique = 0
                for key in filtered_matches:
                    # Check if team1 in the current queue is the same as EITHER team1 or team2 in a recent queue
                    # N.B: If team1 appears in a recent queue, team2 MUST as well, as we're only going through matches containing the same 6 players
                    if sorted(team1) == sorted(
                        game_log["complete"][key]["team1"]
                    ) or sorted(team1) == sorted(game_log["complete"][key]["team2"]):
                        break
                    else:
                        count_unique += 1
                # This condition is met when the current team1 and team2 are different to the team setups in ALL of the filtered matches
                # When this is met we know we have teams which have not been seen in the last 3 hours, so can stop shuffling
                if count_unique == len(filtered_matches):
                    break

            if shuffle_attempts == 100:
                log_event(
                    [
                        round(time.time(), 2),
                        time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                        "Queue",
                        f"ERROR: Failed to find non-repeated random teams in 100 shuffle attempts",
                    ]
                )
            elif shuffle_attempts > 1:
                log_event(
                    [
                        round(time.time(), 2),
                        time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                        "Queue",
                        f"Shuffled teams {shuffle_attempts-1} time(s) to find non-repeated random teams",
                    ]
                )

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
            # Technically only 10 of these are needed, as a team makeup of players (1,2,3) is a mirror of (4,5,6), but performance gains would be negligible
            team_combinations = list(itertools.combinations(current_queue, r=3))

            # Go through each team combination and find the absolute difference between that combinations elo and the target elo
            # The combination with the smallest difference represents the 'fairest' team makeup
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
            "created": round(time.time()),
            "reported": None,
            "tier": active_queues[game_id]["tier"],
            "team_type": team_type,
            "team1": team1,
            "team2": team2,
            "winner": None,
            "loser": None,
            "p1_win": p1_win,
            "p2_win": p2_win,
            "elo_swing": None,
            "timeout_immunity": False,
        }

        with open("json/game_log.json", "w") as write_file:
            json.dump(game_log, write_file, indent=2)

        match_creator = random.choice(current_queue)

        mention_players = []
        for player in current_queue:
            mention_players.append(self.bot.get_user(player).mention)

        embed = discord.Embed(title=f"The Teams!", color=0x83FF00)
        embed.add_field(
            name="**-Team 1-**",
            value=f"{self.bot.get_user(team1[0]).name}, {self.bot.get_user(team1[1]).name}, {self.bot.get_user(team1[2]).name}",
            inline=False,
        )
        embed.add_field(
            name="**-Team 2-**",
            value=f"{self.bot.get_user(team2[0]).name}, {self.bot.get_user(team2[1]).name}, {self.bot.get_user(team2[2]).name}",
            inline=False,
        )
        embed.add_field(
            name="**Match Creator:**",
            value=f"{self.bot.get_user(match_creator).name}",
            inline=False,
        )
        embed.set_footer(
            text=f"Powered by RLI",
            icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
        )
        await interaction.followup.send(" ".join(mention_players), embed=embed)

        for player in current_queue:
            player_user = self.bot.get_user(player)

            embed = discord.Embed(title=f"The Teams!", color=0x83FF00)
            embed.add_field(
                name="**-Team 1-**",
                value=f"{self.bot.get_user(team1[0]).name}, {self.bot.get_user(team1[1]).name}, {self.bot.get_user(team1[2]).name}",
                inline=False,
            )
            embed.add_field(
                name="**-Team 2-**",
                value=f"{self.bot.get_user(team2[0]).name}, {self.bot.get_user(team2[1]).name}, {self.bot.get_user(team2[2]).name}",
                inline=False,
            )
            embed.add_field(
                name="**Match Creator:**",
                value=f"{self.bot.get_user(match_creator).name}",
                inline=False,
            )

            embed.add_field(
                name="**Username:**", value=game_id.split("-")[0], inline=True
            )
            embed.add_field(
                name="**Password:**", value=game_id.split("-")[0], inline=True
            )
            try:
                await player_user.send(
                    "**You have 10 minutes to join the lobby.**", embed=embed
                )
            except Exception as e:
                log_event(
                    [
                        round(time.time(), 2),
                        time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                        "Queue",
                        f"Unable to DM teams to {player_user.name} [{player_user.id}]: {e}",
                    ]
                )

        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Queue",
                f"Teams created for {game_id}. Team1: {team1}, Team2: {team2}",
            ]
        )

        del active_queues[game_id]

    async def on_timeout(self):
        if view_messages[0].id not in resolved_team_picker_messages:
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
        else:
            resolved_team_picker_messages.remove(view_messages[0].id)
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
                        f"{interaction.user.name} [{interaction.user.id}] voted for random teams in {self.game_id} (R: {active_queues[self.game_id]['random']}, C: {active_queues[self.game_id]['captains']}, B: {active_queues[self.game_id]['balanced']})",
                    ]
                )
                button.label = f"Random ({active_queues[self.game_id]['random']})"

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
                    resolved_team_picker_messages.append(message.id)
                    embed = discord.Embed(
                        title=f"{team_type.capitalize()} teams have been chosen",
                    )
                    embed.color = TEAM_PICKER_COLOURS[team_type]
                    embed.set_footer(
                        text=f"GLHF",
                        icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                    )
                    await interaction.edit_original_response(
                        content="", embed=embed, view=None
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
                        f"{interaction.user.name} [{interaction.user.id}] voted for captains teams in {self.game_id} (R: {active_queues[self.game_id]['random']}, C: {active_queues[self.game_id]['captains']}, B: {active_queues[self.game_id]['balanced']})",
                    ]
                )
                button.label = f"Captains ({active_queues[self.game_id]['captains']})"

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
                    resolved_team_picker_messages.append(message.id)
                    embed = discord.Embed(
                        title=f"{team_type.capitalize()} teams have been chosen",
                    )
                    embed.color = TEAM_PICKER_COLOURS[team_type]
                    embed.set_footer(
                        text=f"GLHF",
                        icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                    )
                    await interaction.edit_original_response(
                        content="", embed=embed, view=None
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
                        f"{interaction.user.name} [{interaction.user.id}] voted for balanced teams in {self.game_id} (R: {active_queues[self.game_id]['random']}, C: {active_queues[self.game_id]['captains']}, B: {active_queues[self.game_id]['balanced']})",
                    ]
                )
                button.label = f"Balanced ({active_queues[self.game_id]['balanced']})"

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
                    resolved_team_picker_messages.append(message.id)
                    embed = discord.Embed(
                        title=f"{team_type.capitalize()} teams have been chosen",
                    )
                    embed.color = TEAM_PICKER_COLOURS[team_type]
                    embed.set_footer(
                        text=f"GLHF",
                        icon_url=f"https://cdn.discordapp.com/emojis/607596209254694913.png?v=1",
                    )
                    await interaction.edit_original_response(
                        content="", embed=embed, view=None
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
