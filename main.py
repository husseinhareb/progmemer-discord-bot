import os
import discord
from discord.ext import commands
from discord import app_commands 

from src.dice import roll_dice
from src.jokes import get_jokes
from src.memes import register_memes

TOKEN = os.getenv('TOKEN')

if not TOKEN:
    raise ValueError("No token provided. Please set the TOKEN environment variable.")

intents = discord.Intents.default()
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("Bot is Up and Ready!")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@bot.tree.command(name="hello")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hey {interaction.user.mention}! This is a slash command!")

@bot.tree.command(name="say")
@app_commands.describe(something="What should I say?")
async def say(interaction: discord.Interaction, something: str):
    await interaction.response.send_message(f"{something}")

# Register the commands from jokes.py, dice.py, and memes.py
get_jokes(bot)
roll_dice(bot)
register_memes(bot)

bot.run(TOKEN)
