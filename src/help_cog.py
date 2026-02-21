import sqlite3
import discord
from discord.ext import commands
from pathlib import Path

# Reuse the same DB path as notes
SCRIPT_DIR = Path(__file__).parent.parent.absolute()
DB_FOLDER = SCRIPT_DIR / 'db'
DB_FILE = DB_FOLDER / 'tasks.db'


def _ensure_prefix_table():
    """Create the guild_prefixes table if it doesn't exist."""
    if not DB_FOLDER.exists():
        DB_FOLDER.mkdir(parents=True)
    with sqlite3.connect(str(DB_FILE)) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS guild_prefixes (
                            guild_id INTEGER PRIMARY KEY,
                            prefix TEXT NOT NULL
                        )''')


def _load_prefixes() -> dict:
    """Load all guild prefixes from the database."""
    _ensure_prefix_table()
    with sqlite3.connect(str(DB_FILE)) as conn:
        rows = conn.execute("SELECT guild_id, prefix FROM guild_prefixes").fetchall()
    return {row[0]: row[1] for row in rows}


def _save_prefix(guild_id: int, prefix: str):
    """Save or update a guild's prefix in the database."""
    _ensure_prefix_table()
    with sqlite3.connect(str(DB_FILE)) as conn:
        conn.execute(
            "INSERT INTO guild_prefixes (guild_id, prefix) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET prefix = excluded.prefix",
            (guild_id, prefix)
        )


class HelpCog(commands.Cog):
    def __init__(self, bot, guild_prefixes=None):
        self.bot = bot
        self.help_message = ""
        self.guild_prefixes = guild_prefixes if guild_prefixes is not None else {}
        self.default_prefix = "!"
        # Load persisted prefixes into the shared dict
        saved = _load_prefixes()
        self.guild_prefixes.update(saved)

    def get_prefix(self, guild_id=None):
        """Get the prefix for a specific guild, or default."""
        if guild_id and guild_id in self.guild_prefixes:
            return self.guild_prefixes[guild_id]
        return self.default_prefix

    def _build_help_message(self, prefix=None):
        if prefix is None:
            prefix = self.default_prefix
        return f"""
**Music Commands:**
{prefix}play <song> - plays a song from YouTube
{prefix}pause - pauses the current song
{prefix}resume - resumes the paused song
{prefix}skip - skips the current song
{prefix}stop - stops playing and clears the queue
{prefix}queue - displays the current song queue
{prefix}lyrics - shows lyrics for the current song

**Bot Commands:**
{prefix}prefix <new_prefix> - changes the command prefix for this server
{prefix}help - displays this help message

**Slash Commands:**
Use `/` commands for more features: /hello, /say, /joke, /meme, /weather, /roll, /add, /list, /update, /remove, /edit, /nowplaying
"""

    @commands.Cog.listener()
    async def on_ready(self):
        # Use correct command name in presence
        await self.bot.change_presence(activity=discord.Game(f"type {self.default_prefix}help"))

    @commands.command(name="help", help="Displays all the available commands")
    async def help(self, ctx):
        # Generate help message with the current guild's prefix
        prefix = self.get_prefix(ctx.guild.id if ctx.guild else None)
        help_text = self._build_help_message(prefix)
        await ctx.send(help_text)

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.command(name="prefix", help="Change bot prefix for this server")
    async def prefix(self, ctx, *args):
        # Validate that a prefix was provided
        if not args:
            await ctx.send("Please provide a new prefix. Usage: `!prefix <new_prefix>`")
            return
        
        new_prefix = " ".join(args)
        
        # Prevent empty or whitespace-only prefix
        if not new_prefix.strip():
            await ctx.send("Prefix cannot be empty or whitespace only.")
            return
        
        # Store per-guild prefix (in memory and in database)
        self.guild_prefixes[ctx.guild.id] = new_prefix
        _save_prefix(ctx.guild.id, new_prefix)
        await ctx.send(f"Prefix for this server set to **'{new_prefix}'**")

    @prefix.error
    async def prefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Manage Server' permission to change the prefix.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ This command can only be used in a server.")

    @commands.has_permissions(administrator=True)
    @commands.command(name="send_to_all", help="Send a message to all text channels in this server (Admin only)")
    async def send_to_all(self, ctx, *, msg):
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return
        # Refresh channel list for the current guild only (use local variable to avoid race conditions)
        channels = [
            channel for channel in ctx.guild.text_channels 
            if channel.permissions_for(ctx.guild.me).send_messages
        ]
        
        if not channels:
            await ctx.send("No text channels available to send messages to.")
            return
            
        sent_count = 0
        for text_channel in channels:
            try:
                await text_channel.send(msg)
                sent_count += 1
            except discord.Forbidden:
                pass  # Skip channels where we lost permission
            except Exception as e:
                print(f"Error sending to {text_channel}: {e}")
        
        await ctx.send(f"Message sent to {sent_count} channels.")

    @send_to_all.error
    async def send_to_all_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need administrator permissions to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Please provide a message. Usage: `!send_to_all <message>`")


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
