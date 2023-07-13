from asyncore import write
import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import time
import config
import csv
from datetime import datetime

GUILD_ID = config.GUILD_ID

queue = ["Tomster", "Shallow", "Llama", "DLynch"]

global messages
messages = []

class Test_Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Ping cog command
    @app_commands.command(description="Ping the test cog.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ping_test(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!", ephemeral=True)

    @app_commands.command(description="alpha")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def alpha(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send("1")
        await interaction.followup.send("2")
        await interaction.response.send_message("Pong!", ephemeral=True)


    @app_commands.command(description="test view")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def view(self, interaction: discord.Interaction, id: str):
        await interaction.response.send_message(time.time(), view=Counter(queue, id))
        Counter.response = await interaction.original_response()

    @app_commands.command(description="Test View")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def test(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"View Created: {datetime.utcnow().strftime('%H:%M:%S')}",
            view=Test_View(),
        )
        message = await interaction.original_response()
        messages.append(message)


# This is a functional, but UNDESIRABLE solution. It uses a global variable ('messages') which is bad practice
class Test_View(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=45)

    async def on_timeout(self):
        await messages[0].edit(
            content=f"View Expired: {datetime.utcnow().strftime('%H:%M:%S')}", view=None
        )
        messages.pop(0)

    @discord.ui.button(label="off", style=discord.ButtonStyle.red)
    async def test_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        #button.disabled = True
        print(f"Pressed at {datetime.utcnow().strftime('%H:%M:%S')}")
        if button.label == "off":
            button.label = "on"
            button.style = discord.ButtonStyle.green
        else:
            button.label = "off"
            button.style = discord.ButtonStyle.red
        await interaction.response.edit_message(view=self)
        message = await interaction.original_response()
        messages.remove(message)
        messages.append(message)
        


# Define a simple View that gives us a counter button
class Counter(discord.ui.View):
    def __init__(self, label: list, queue_id: str):
        super().__init__(timeout=30)
        self.player_1.label = label[0]
        self.player_2.label = label[1]
        self.player_3.label = label[2]
        self.player_4.label = label[3]

        self.queue_id = queue_id

    async def on_timeout(self):
        await self.response.edit(content=time.time(), view=None)

    @discord.ui.button(label="placeholder", style=discord.ButtonStyle.red)
    async def player_1(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        button.disabled = True
        print(self.player_1.label, self.queue_id)

        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="placeholder", style=discord.ButtonStyle.red)
    async def player_2(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        button.disabled = True
        print(self.player_2.label, self.queue_id)

        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="placeholder", style=discord.ButtonStyle.red)
    async def player_3(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        button.disabled = True
        print(self.player_3.label, self.queue_id)

        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="placeholder", style=discord.ButtonStyle.red)
    async def player_4(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        button.disabled = True
        print(self.player_4.label, self.queue_id)

        await interaction.response.edit_message(view=self)


async def setup(bot):
    await bot.add_cog(Test_Commands(bot))