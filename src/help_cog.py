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
        await self.bot.change_presence(activity=discord.Game(f"type {self.bot.command_prefix}help"))

    @commands.command(name="helppp", help="Displays all the available commands")
    async def helppp(self, ctx):
        await ctx.send(self.help_message)

    @commands.command(name="prefix", help="Change bot prefix")
    async def prefix(self, ctx, *args):
        self.bot.command_prefix = " ".join(args)
        self.set_message()
        await ctx.send(f"prefix set to **'{self.bot.command_prefix}'**")
        await self.bot.change_presence(activity=discord.Game(f"type {self.bot.command_prefix}help"))

    @commands.command(name="send_to_all", help="Send a message to all members")
    async def send_to_all(self, ctx, *, msg):
        for text_channel in self.text_channel_list:
            await text_channel.send(msg)

def setup(bot):
    bot.add_cog(HelpCog(bot))
