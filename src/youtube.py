import os
import random
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as youtube_dl



# Initialize the bot

def register_play_command(bot: commands.Bot):
    @bot.tree.command(name="play", description="Plays audio from a YouTube URL")
    @app_commands.describe(url="The YouTube URL of the video to play")
    async def play(interaction: discord.Interaction, url: str):
        # Check if the user is in a voice channel
        if interaction.user.voice is None:
            await interaction.response.send_message("You are not connected to a voice channel")
            return

        voice_channel = interaction.user.voice.channel

        # Connect to the voice channel if not already connected
        if interaction.guild.voice_client is None:
            await voice_channel.connect()
        else:
            await interaction.guild.voice_client.move_to(voice_channel)

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True
        }

        # Use youtube_dl to extract audio source
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['formats'][0]['url']
            source = await discord.FFmpegOpusAudio.from_probe(audio_url, method='fallback')

        # Play the audio
        interaction.guild.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)
        await interaction.response.send_message(f'Now playing: {info["title"]}')

def register_stop_command(bot: commands.Bot):
    @bot.tree.command(name="stop", help='Stops and disconnects the bot from the voice channel')
    async def stop(interaction: discord.Interaction):
        if interaction.guild.voice_client is not None:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Disconnected from the voice channel")
        else:
            await interaction.response.send_message("I am not connected to a voice channel")
