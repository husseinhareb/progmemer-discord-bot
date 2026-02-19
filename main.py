import os
import discord
import asyncio
import signal
import logging

from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

from src.dice import roll_dice
from src.jokes import get_jokes
from src.memes import register_memes
from src.weather import get_weather
from src.music import MusicCog
from src.help_cog import HelpCog
from src.notes import ensure_db_exists
from src.notes import add_note
from src.notes import get_note
from src.notes import update_status
from src.notes import remove_task
from src.notes import edit_task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

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

# Per-guild prefix storage (shared with HelpCog)
guild_prefixes = {}
DEFAULT_PREFIX = "!"

def get_prefix(bot, message):
    """Return the per-guild prefix, or the default for DMs."""
    if message.guild and message.guild.id in guild_prefixes:
        return guild_prefixes[message.guild.id]
    return DEFAULT_PREFIX

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)
_tree_synced = False

# Initialize database at startup
ensure_db_exists()

@bot.event
async def on_ready():
    global _tree_synced
    logger.info("Bot is Up and Ready!")

    # Warn if message_content intent might not be enabled on the portal
    if not bot.intents.message_content:
        logger.warning(
            "message_content intent is not enabled. "
            "Prefix commands will not work. Enable it in the Discord Developer Portal."
        )

    if not _tree_synced:
        try:
            synced = await bot.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
            _tree_synced = True
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

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
        await bot.add_cog(HelpCog(bot, guild_prefixes))  
        await bot.add_cog(MusicCog(bot))

        # Graceful shutdown on SIGINT/SIGTERM
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.ensure_future(shutdown(bot)))

        await bot.start(TOKEN)

async def shutdown(bot):
    """Gracefully disconnect voice clients and close the bot."""
    logger.info("Shutting down...")
    for vc in bot.voice_clients:
        try:
            await vc.disconnect(force=True)
        except Exception:
            pass
    await bot.close()

asyncio.run(main())


