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


def log_event(event):
    with open("logs/live_logs.csv", "a", newline="") as write_file:
        writer = csv.writer(write_file)
        writer.writerow(event)


queue = {"elite": {}, "premier": {}, "championship": {}, "casual": {}}


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
        queue[tier][user.id] = round(time.time())

        if added:
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Queue",
                    f"{user.name} [{user.id}] has been added to the {queue_channel.name[:-6]} queue ({len(queue[tier])} in queue)",
                ]
            )
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
            else:
                embed = discord.Embed(
                    title=f"{len(queue[tier])} players are in the queue!"
                )
                embed.set_footer(
                    text=f"{str(6-len(queue[tier]))} more needed!",
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
                    f"{user.name} [{user.id}] has joined the {queue_channel.name[:-6]} queue ({len(queue[tier])} in queue)",
                ]
            )

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
            embed.color = 0xFF8B00
            embed.description = f"{user.mention} has joined the queue."
            await interaction.response.send_message(embed=embed)

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
            if removed:
                log_event(
                    [
                        round(time.time(), 2),
                        time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                        "Queue",
                        f"{user.name} [{user.id}] has been removed from the {queue_channel.name[:-6]} queue ({len(queue[tier])} in queue)",
                    ]
                )
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
                log_event(
                    [
                        round(time.time(), 2),
                        time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                        "Queue",
                        f"{user.name} [{user.id}] has left the {queue_channel.name[:-6]} queue ({len(queue[tier])} in queue)",
                    ]
                )
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


async def setup(bot):
    await bot.add_cog(queue_handler(bot))
