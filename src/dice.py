import random
import discord
from discord.ext import commands

def roll_dice(bot: commands.Bot):
    @bot.tree.command(name="roll", description="Roll the dice!")
    async def roll(interaction: discord.Interaction):
        rand_number = random.randint(1, 6)
        await interaction.response.send_message(f"You rolled a {rand_number}!")
