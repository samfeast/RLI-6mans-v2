from discord.ext import commands

import discord


queue = ["Tomster", "Shallow", "Llama", "DLynch"]


class CounterBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=commands.when_mentioned_or("$"), intents=intents
        )

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")


# Define a simple View that gives us a counter button
class Counter(discord.ui.View):
    def __init__(self, ctx, label: list, queue_id: str):
        super().__init__(timeout=2)
        self.player_1.label = label[0]
        self.player_2.label = label[1]
        self.player_3.label = label[2]
        self.player_4.label = label[3]

        self.queue_id = queue_id

        self.ctx = ctx

    async def on_timeout(self):
        await self.ctx.send("Test")

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


class Voting(discord.ui.View):
    # Define the actual button
    # When pressed, this increments the number displayed until it hits 5.
    # When it hits 5, the counter button is disabled and it turns green.
    # note: The name of the function does not matter to the library
    @discord.ui.button(label="Captains (0)", style=discord.ButtonStyle.red)
    async def count(self, interaction: discord.Interaction, button: discord.ui.Button):
        number = int(button.label[-2])
        button.label = f"Captains ({number + 1})"

        # Make sure to update the message with our updated selves
        await interaction.response.edit_message(view=self)


bot = CounterBot()


@bot.command()
async def counter(ctx: commands.Context, id: str):
    """Starts a counter for pressing."""
    await ctx.send("Press!", view=Counter(ctx, queue, id))


@bot.command()
async def vote(ctx: commands.Context):
    """Starts a counter for pressing."""
    await ctx.send("Press!", view=Voting())


@bot.command()
async def a(ctx: commands.Context):
    queue.pop(0)
    await ctx.send(queue)


bot.run("THIS TOKEN IS NOT HERE")
