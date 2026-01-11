import os
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands


async def fetch_weather(city):
    api_key = os.getenv('WEATHER_API')
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    weather_description = data['weather'][0]['description']
                    temperature = data['main']['temp']
                    humidity = data['main']['humidity']
                    return weather_description, temperature, humidity
                else:
                    return None, None, None
    except aiohttp.ClientError:
        return None, None, None


def get_weather(bot: commands.Bot):
    @bot.tree.command(name="weather", description="Get weather details for a city")
    @app_commands.describe(city="City name")
    async def weather(interaction: discord.Interaction, city: str):
        weather_description, temperature, humidity = await fetch_weather(city)
        if weather_description is not None:
            weather_details = f"Weather Information for **{city}**:\n\n**Temperature:** {temperature}°C\n**Description:** {weather_description}\n**Humidity:** {humidity}%"
            await interaction.response.send_message(weather_details)
        else:
            await interaction.response.send_message("Failed to fetch weather data. Please ensure the city name is correct and try again.")
