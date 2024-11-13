import os
import discord
import asyncio

from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

from src.dice import roll_dice
from src.jokes import get_jokes
from src.memes import register_memes
from src.weather import get_weather
from src.music import MusicCog
from src.help_cog import HelpCog
from src.notes import add_note
from src.notes import get_note
from src.notes import update_status
from src.notes import remove_task
from src.notes import edit_task
load_dotenv()
TOKEN = os.getenv('TOKEN')

if not TOKEN:
    raise ValueError("No token provided. Please set the TOKEN environment variable.")

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.guild_messages = True
intents.guild_reactions = True
intents.reactions = True
intents.message_content = True
intents.voice_states = True 

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("Bot is Up and Ready!")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@bot.tree.command(name="hello", description="Greet the bot.")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hey {interaction.user.mention}! How are you?")

@bot.tree.command(name="say", description="Say something!")
@app_commands.describe(something="What should I say?")
async def say(interaction: discord.Interaction, something: str):
    await interaction.response.send_message(f"{something}")

# Register commands
get_jokes(bot)
roll_dice(bot)
register_memes(bot)
get_weather(bot)
add_note(bot)
get_note(bot)
update_status(bot)
remove_task(bot)
edit_task(bot)
async def main():
    async with bot:
        await bot.add_cog(HelpCog(bot))  
        await bot.add_cog(MusicCog(bot)) 
        await bot.start(TOKEN)

asyncio.run(main())


