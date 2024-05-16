import discord
import os
import requests
from discord import app_commands
from discord.ext import commands

TOKEN = os.environ['TOKEN']

intents = discord.Intents.default()
intents.members = True

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
    await interaction.response.send_message(f"Hey {interaction.user.mention}! This is a slash command!", ephemeral=True)

@bot.tree.command(name="say")
@app_commands.describe(thing_to_say="What should I say?")
async def say(interaction: discord.Interaction, thing_to_say: str):
    await interaction.response.send_message(f"{thing_to_say}", ephemeral=True)

@bot.tree.command(name="joke")
@app_commands.describe(category="Choose a joke category: Programming, Misc, Dark, etc.")
async def joke(interaction: discord.Interaction, category: str = "Any"):
    # Validate the category
    valid_categories = ["Programming", "Misc", "Dark", "Any"]
    if category not in valid_categories:
        await interaction.response.send_message(f"Invalid category! Please choose from {valid_categories}", ephemeral=True)
        return

    # Fetch joke from the API
    response = requests.get(f'https://v2.jokeapi.dev/joke/{category}')
    if response.status_code == 200:
        joke = response.json()
        if joke['type'] == 'single':
            joke_message = joke['joke']
        else:
            joke_message = f"{joke['setup']} - {joke['delivery']}"
    else:
        joke_message = "Failed to retrieve joke"

    await interaction.response.send_message(joke_message, ephemeral=True)

bot.run(TOKEN)
