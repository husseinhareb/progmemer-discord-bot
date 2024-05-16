import requests
import discord
from discord import app_commands

valid_categories = ["Programming", "Misc", "Dark", "Any"]

def setup(bot: commands.Bot):
    @bot.tree.command(name="joke")
    @app_commands.describe(category="Choose a joke category: Programming, Misc, Dark, etc.")
    async def joke(interaction: discord.Interaction, category: str = "Any"):
        # Validate the category
        if category not in valid_categories:
            await interaction.response.send_message(f"Invalid category! Please choose from {valid_categories}")
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

        await interaction.response.send_message(joke_message)
