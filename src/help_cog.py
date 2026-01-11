import discord
from discord.ext import commands


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_message = ""
        self.text_channel_list = []
        self.set_message()

    def set_message(self):
        self.help_message = f"""
**Music Commands:**
{self.bot.command_prefix}play <song> - plays a song from YouTube
{self.bot.command_prefix}pause - pauses the current song
{self.bot.command_prefix}resume - resumes the paused song
{self.bot.command_prefix}skip - skips the current song
{self.bot.command_prefix}stop - stops playing and clears the queue
{self.bot.command_prefix}queue - displays the current song queue
{self.bot.command_prefix}lyrics - shows lyrics for the current song

**Bot Commands:**
{self.bot.command_prefix}prefix <new_prefix> - changes the command prefix
{self.bot.command_prefix}helppp - displays this help message

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
        await self.bot.change_presence(activity=discord.Game(f"type {self.bot.command_prefix}helppp"))

    @commands.command(name="helppp", help="Displays all the available commands")
    async def helppp(self, ctx):
        await ctx.send(self.help_message)

    @commands.command(name="prefix", help="Change bot prefix")
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
            
        self.bot.command_prefix = new_prefix
        self.set_message()
        await ctx.send(f"prefix set to **'{self.bot.command_prefix}'**")
        await self.bot.change_presence(activity=discord.Game(f"type {self.bot.command_prefix}helppp"))

    @commands.command(name="send_to_all", help="Send a message to all text channels")
    async def send_to_all(self, ctx, *, msg):
        # Refresh channel list before sending
        self.text_channel_list = [
            channel for guild in self.bot.guilds 
            for channel in guild.text_channels 
            if channel.permissions_for(guild.me).send_messages
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


def setup(bot):
    bot.add_cog(HelpCog(bot))
