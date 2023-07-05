import discord
from discord.ext import commands
import asyncio
from os import listdir
import config
import time
import csv

discord.utils.setup_logging()

PREFIX = ">"
TOKEN = config.TOKEN
GUILD_ID = config.GUILD_ID

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)
# Initialize slash command tree
tree = bot.tree


def log_event(event):
    with open("logs/live_logs.csv", "a", newline="") as write_file:
        writer = csv.writer(write_file)
        writer.writerow(event)


@bot.event
async def on_ready():

    print(f"Logged in as {bot.user.name} [{bot.user.id}]")
    print("Servers:")
    guilds = []
    for guild in bot.guilds:
        guilds.append(f"{guild.name} [{guild.id}]")

    print("\t" + "\n\t".join(guilds))

    log_event(
        [
            round(time.time(), 2),
            time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
            "Main",
            f"Connected as {bot.user.name} [{bot.user.id}] in servers: {', '.join(guilds)}",
        ]
    )


# Sync all slash commands in server where command is used - only use when a new command is added, or the name/description of an existing command is changed
@bot.command()
async def synclocal_6mans(ctx):
    log_event(
        [
            round(time.time(), 2),
            time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
            "Main",
            f"'synclocal_6mans' used by {ctx.author.name} [{ctx.author.id}]",
        ]
    )
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    await ctx.send("Slash commands synced.")
    log_event(
        [
            round(time.time(), 2),
            time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
            "Main",
            "Slash commands synced",
        ]
    )


# Reload a cog (cog argument does not need to contain _cog.py)
@bot.command()
async def reload_6mans(ctx, cog):
    log_event(
        [
            round(time.time(), 2),
            time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
            "Main",
            f"'reload_6mans' used to reload '{cog.lower()}' cog by {ctx.author.name} [{ctx.author.id}]",
        ]
    )
    try:
        await bot.reload_extension(f"{cog.lower()}_cog")
        await ctx.send(f"{cog.lower()}_cog reloaded successfully.")
        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Main",
                f"{cog.lower()}_cog.py reloaded successfully",
            ]
        )
    except Exception as e:
        await ctx.send(f"Failed to reload {cog.lower()}_cog.")
        log_event(
            [
                round(time.time(), 2),
                time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                "Main",
                f"Failed to reload {cog.lower()}_cog.py - '{type(e).__name__}: {str(e)[:-1]}'",
            ]
        )


# Reload all cogs
@bot.command()
async def reload_all_6mans(ctx):
    log_event(
        [
            round(time.time(), 2),
            time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
            "Main",
            f"'reload_all_6mans' used by {ctx.author.name} [{ctx.author.id}]",
        ]
    )
    cogs = [f[:-3] for f in listdir() if "cog" == f[-6:-3]]
    for cog in cogs:
        try:
            await bot.reload_extension(cog)
            await ctx.send(f"{cog.lower()} reloaded successfully.")
        except Exception as e:
            await ctx.send(f"Failed to reload {cog.lower()}_cog.")
            log_event(
                [
                    round(time.time(), 2),
                    time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
                    "Main",
                    f"Failed to reload {cog.lower()}_cog.py - '{type(e).__name__}: {str(e)[:-1]}'",
                ]
            )

    log_event(
        [
            round(time.time(), 2),
            time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
            "Main",
            f"Finished attempting to reload all cogs (Failures in separate log)",
        ]
    )


@bot.command()
async def ping_6mans(ctx):
    log_event(
        [
            round(time.time(), 2),
            time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
            "Main",
            f"'ping_6mans' used by {ctx.author.name} [{ctx.author.id}]",
        ]
    )
    await ctx.send("Pong!")


@tree.command(description="Ping main cog.", guild=discord.Object(id=GUILD_ID))
async def ping_main(interaction: discord.Interaction):
    log_event(
        [
            round(time.time(), 2),
            time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
            "Main",
            f"'ping_main' used by {interaction.user.name} [{interaction.user.id}]",
        ]
    )
    await interaction.response.send_message("Pong!", ephemeral=True)


# TODO: Add /export_logs (with a date parameter, uploading all logs on that date to a google sheet)
@tree.command(
    description="Show most recent logs (up to 2000 characters)",
    guild=discord.Object(id=GUILD_ID),
)
async def view_logs(interaction: discord.Interaction):

    log_event(
        [
            round(time.time(), 2),
            time.strftime("%d-%m-%y %H:%M:%S", time.localtime()),
            "Main",
            f"'view_logs' used by {interaction.user.name} [{interaction.user.id}]",
        ]
    )

    string = "Time\t    Cog\t      Output\n"
    with open("logs/live_logs.csv", "r") as read_file:
        reader = csv.reader(read_file, delimiter=",")

        event_list = []
        for row in reader:
            event_list.append(row)

        event_list.reverse()

        for event in event_list:
            if row != []:
                new_line = f"{event[1][-8:]}\t{event[2]}\t"

                for i in range(9 - len(event[2])):
                    new_line += " "

                new_line += event[3]
                new_line += "\n"

                if len(string) + len(new_line) <= 1994:
                    string += new_line
                else:
                    break

    await interaction.response.send_message(f"```{string}```")


# Run bot and load cogs
async def main():
    async with bot:
        cogs = [f[:-3] for f in listdir() if "cog" == f[-6:-3]]
        print("Cogs:")
        for cog in cogs:
            try:
                await bot.load_extension(cog)
                print(f"\t{cog}")
            except Exception as e:
                print(f"Failed to load {cog}")
                print(f"{type(e).__name__}: {e}")
        await bot.start(TOKEN)


asyncio.run(main())
