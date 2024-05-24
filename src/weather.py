import os
import requests
import discord
from discord.ext import commands
from discord import app_commands

def fetch_weather(city):
    api_key = os.getenv('WEATHER_API_KEY')
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        weather_description = data['weather'][0]['description']
        temperature = data['main']['temp']
        humidity = data['main']['humidity']
        return weather_description, temperature, humidity
    else:
        return None, None, None

def get_weather(bot: commands.Bot):
    @bot.tree.command(name="weather", description="Get weather details for a city")
    @app_commands.describe(city="City name")
    async def weather(interaction: discord.Interaction, city: str):
        weather_description, temperature, humidity = fetch_weather(city)
        if weather_description is not None:
            weather_details = f"Weather Information for **{city}**:\n\n**Temperature:** {temperature}°C\n**Description:** {weather_description}\n**Humidity:** {humidity}%"
            await interaction.response.send_message(weather_details)
        else:
            await interaction.response.send_message("Failed to fetch weather data. Please ensure the city name is correct and try again.")
