import asyncio
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands


def get_jokes(bot: commands.Bot):
    @bot.tree.command(name="joke", description="Get a random joke (default: Any)")
    @app_commands.describe(category="Choose a joke category (optional)")
    @app_commands.choices(category=[
        app_commands.Choice(name="Programming", value="Programming"),
        app_commands.Choice(name="Misc", value="Misc"),
        app_commands.Choice(name="Dark", value="Dark"),
        app_commands.Choice(name="Any", value="Any")
    ])
    async def joke(interaction: discord.Interaction, category: str = "Any"):
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f'https://v2.jokeapi.dev/joke/{category}') as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data.get('error'):
                        joke_message = "Failed to retrieve joke. Please try again later."
                    elif data['type'] == 'single':
                        joke_message = data['joke']
                    else:
                        joke_message = f"{data['setup']} - **{data['delivery']}**"
        except (aiohttp.ClientError, aiohttp.ClientResponseError, KeyError, asyncio.TimeoutError):
            joke_message = "Failed to retrieve joke. Please try again later."

        await interaction.followup.send(joke_message)
