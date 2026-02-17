import discord
from discord.ext import commands


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_message = ""
        self.text_channel_list = []
        self.guild_prefixes = {}  # Per-guild prefix storage
        self.default_prefix = "!"
        self.set_message()

    def get_prefix(self, guild_id=None):
        """Get the prefix for a specific guild, or default."""
        if guild_id and guild_id in self.guild_prefixes:
            return self.guild_prefixes[guild_id]
        return self.default_prefix

    def set_message(self, prefix=None):
        if prefix is None:
            prefix = self.default_prefix
        self.help_message = f"""
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
{prefix}helppp - displays this help message

**Slash Commands:**
Use `/` commands for more features: /hello, /say, /joke, /meme, /weather, /roll, /add, /list, /update, /remove, /edit
"""

    @commands.Cog.listener()
    async def on_ready(self):
        # Populate text_channel_list with all text channels the bot has access to
        self.text_channel_list = [
            channel for guild in self.bot.guilds 
            for channel in guild.text_channels 
            if channel.permissions_for(guild.me).send_messages
        ]
        # Use correct command name in presence
        await self.bot.change_presence(activity=discord.Game(f"type {self.default_prefix}helppp"))

    @commands.command(name="helppp", help="Displays all the available commands")
    async def helppp(self, ctx):
        # Generate help message with the current guild's prefix
        prefix = self.get_prefix(ctx.guild.id if ctx.guild else None)
        self.set_message(prefix)
        await ctx.send(self.help_message)

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
        
        # Store per-guild prefix
        if ctx.guild:
            self.guild_prefixes[ctx.guild.id] = new_prefix
            await ctx.send(f"Prefix for this server set to **'{new_prefix}'**")
        else:
            # DM context - change default prefix
            self.default_prefix = new_prefix
            await ctx.send(f"Default prefix set to **'{new_prefix}'**")

    @prefix.error
    async def prefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Manage Server' permission to change the prefix.")

    @commands.has_permissions(administrator=True)
    @commands.command(name="send_to_all", help="Send a message to all text channels in this server (Admin only)")
    async def send_to_all(self, ctx, *, msg):
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return
        # Refresh channel list for the current guild only
        self.text_channel_list = [
            channel for channel in ctx.guild.text_channels 
            if channel.permissions_for(ctx.guild.me).send_messages
        ]
        
        if not self.text_channel_list:
            await ctx.send("No text channels available to send messages to.")
            return
            
        sent_count = 0
        for text_channel in self.text_channel_list:
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


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
