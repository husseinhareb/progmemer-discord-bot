import discord
from discord.ext import commands
from discord import app_commands
from youtubesearchpython import VideosSearch
from yt_dlp import YoutubeDL
from bs4 import BeautifulSoup
import asyncio
import os
import requests

class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.is_playing = False
        self.is_paused = False
        self.music_queue = []
        self.current_song = None
        self.YDL_OPTIONS = {'format': 'bestaudio/best'}
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        self.vc = None
        self.ytdl = YoutubeDL(self.YDL_OPTIONS)

    async def send_embed(self, ctx_or_interaction, description, title=None, color=discord.Color.purple(), thumbnail=None, view=None):
        embed = discord.Embed(description=description, color=color)
        if title:
            embed.title = title
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed, view=view)
        else:
            if view:
                await ctx_or_interaction.response.send_message(embed=embed, view=view)
            else:
                await ctx_or_interaction.response.send_message(embed=embed)

    def search_yt(self, item):
        search = VideosSearch(item, limit=1)
        result = search.result()["result"][0]
        return {'source': result["link"], 'title': result["title"], 'thumbnail': result["thumbnails"][0]["url"]}

    async def play_next(self):
        if len(self.music_queue) > 0:
            self.is_playing = True
            self.current_song = self.music_queue.pop(0)
            m_url = self.current_song[0]['source']
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
            song = data['url']
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song, **self.FFMPEG_OPTIONS))
            self.vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))
        else:
            self.is_playing = False
            self.current_song = None

    async def play_music(self, ctx_or_interaction):
        if len(self.music_queue) > 0:
            self.is_playing = True
            self.current_song = self.music_queue.pop(0)
            m_url = self.current_song[0]['source']
            voice_channel = self.current_song[1]
            try:
                if self.vc is None or not self.vc.is_connected():
                    self.vc = await voice_channel.connect()
                else:
                    await self.vc.move_to(voice_channel)
            except Exception as e:
                await self.send_embed(ctx_or_interaction, f"Could not connect to the voice channel: {str(e)}", title="Error", color=discord.Color.red())
                return

            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
            song = data['url']
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song, **self.FFMPEG_OPTIONS))
            self.vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))
        else:
            self.is_playing = False
            self.current_song = None

    async def play_autocomplete(self, interaction: discord.Interaction, current: str):
        search = VideosSearch(current, limit=5)
        results = search.result()["result"]
        return [
            app_commands.Choice(name=f"{video['title']} - {video['duration']}", value=video["link"])
            for video in results
        ]

    @commands.command(name="play", help="Plays a selected song from YouTube")
    async def play(self, ctx, *, query: str):
        await self._play(ctx, query)

    @app_commands.command(name="play", description="Plays a selected song from YouTube")
    @app_commands.autocomplete(query=play_autocomplete)
    async def slash_play(self, interaction: discord.Interaction, query: str):
        await self._play(interaction, query)

    async def _play(self, ctx_or_interaction, query):
        if isinstance(ctx_or_interaction, commands.Context):
            author = ctx_or_interaction.author
        else:
            author = ctx_or_interaction.user

        try:
            voice_channel = author.voice.channel
        except AttributeError:
            await self.send_embed(ctx_or_interaction, "You need to connect to a voice channel first!", title="Error", color=discord.Color.red())
            return

        if self.is_paused:
            self.vc.resume()
            self.is_paused = False
            self.is_playing = True
        else:
            song = self.search_yt(query)
            if song is None:
                await self.send_embed(ctx_or_interaction, "Could not download the song. Incorrect format or unsupported type. Please try another keyword.", title="Error", color=discord.Color.red())
            else:
                self.music_queue.append([song, voice_channel])
                view = MusicControlView(self)
                if self.is_playing:
                    await self.send_embed(ctx_or_interaction, f"**#{len(self.music_queue) + 1} - '{song['title']}'** added to the queue", color=discord.Color.green(), thumbnail=song['thumbnail'], view=view)
                else:
                    await self.send_embed(ctx_or_interaction, f"**{song['title']}**", color=discord.Color.green(), thumbnail=song['thumbnail'], view=view)
                    await self.play_music(ctx_or_interaction)

    @commands.command(name="pause", help="Pauses the current song being played")
    async def pause(self, ctx):
        await self._pause(ctx)

    @app_commands.command(name="pause", description="Pauses the current song being played")
    async def slash_pause(self, interaction: discord.Interaction):
        await self._pause(interaction)

    async def _pause(self, ctx_or_interaction):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
            view = MusicControlView(self)
            await self.update_button_state(view, play=True)
            await self.send_embed(ctx_or_interaction, "Paused the current song", color=discord.Color.orange(), view=view)

    @commands.command(name="resume", help="Resumes playing with the Discord bot")
    async def resume(self, ctx):
        await self._resume(ctx)

    @app_commands.command(name="resume", description="Resumes playing with the Discord bot")
    async def slash_resume(self, interaction: discord.Interaction):
        await self._resume(interaction)

    async def _resume(self, ctx_or_interaction):
        if self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()
            view = MusicControlView(self)
            await self.update_button_state(view, play=False)
            await self.send_embed(ctx_or_interaction, "Resumed the current song", color=discord.Color.green(), view=view)

    @commands.command(name="skip", help="Skips the current song being played")
    async def skip(self, ctx):
        await self._skip(ctx)

    @app_commands.command(name="skip", description="Skips the current song being played")
    async def slash_skip(self, interaction: discord.Interaction):
        await self._skip(interaction)

    async def _skip(self, ctx_or_interaction):
        if self.vc is not None and self.vc.is_playing():
            self.vc.stop()
            await self.play_music(ctx_or_interaction)
            await self.send_embed(ctx_or_interaction, "Skipped the current song", color=discord.Color.green())

    #Lyrics
    @commands.command(name="lyrics", help="Prints the lyrics of the current song being played")
    async def lyrics(self, ctx):
        await self._lyrics(ctx)

    @app_commands.command(name="lyrics", description="Prints the lyrics of the current song being played")
    async def slash_lyrics(self, interaction: discord.Interaction):
        await self._lyrics(interaction)


    async def _lyrics(self, ctx_or_interaction):
        # Check if there is a song currently being played
        if self.vc is None or not self.vc.is_playing():
            await self.send_embed(ctx_or_interaction, "No song is currently playing.", title="Error", color=discord.Color.red())
            return

        # Get the current song's title and artist from the currently playing song
        if self.current_song is None:
            await self.send_embed(ctx_or_interaction, "No song is currently playing.", title="Error", color=discord.Color.red())
            return

        song_title = self.current_song[0]['title']
        song_artist = self.current_song[0].get('artist', 'Unknown Artist')  # Adjust if artist information is available

        access_token = os.getenv('GENIUS_TOKEN')
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        search_url = 'https://api.genius.com/search'

        # Search for the song
        search_params = {
            'q': f'{song_title} {song_artist}'
        }
        search_response = requests.get(search_url, headers=headers, params=search_params)
        search_data = search_response.json()

        if search_data['response']['hits']:
            song_info = search_data['response']['hits'][0]['result']
            song_path = song_info['path']

            # Fetch the song page
            song_url = f'https://genius.com{song_path}'
            page_response = requests.get(song_url)

            # Parse the HTML to extract lyrics
            soup = BeautifulSoup(page_response.text, 'html.parser')
            lyrics_div = soup.find('div', class_='lyrics')
            if not lyrics_div:
                lyrics_div = soup.find('div', class_='Lyrics__Root-sc-1ynbvzw-0')

            if lyrics_div:
                lyrics = lyrics_div.get_text(strip=True)
                await self.send_embed(ctx_or_interaction, lyrics, title="Lyrics")
            else:
                await self.send_embed(ctx_or_interaction, "Lyrics not found.", title="Error", color=discord.Color.red())
        else:
            await self.send_embed(ctx_or_interaction, "Song not found.", title="Error", color=discord.Color.red())


    
    @commands.command(name="queue", help="Displays the current songs in queue")
    async def queue(self, ctx):
        await self._queue(ctx)

    @app_commands.command(name="queue", description="Displays the current songs in queue")
    async def slash_queue(self, interaction: discord.Interaction):
        await self._queue(interaction)

    async def _queue(self, ctx_or_interaction):
        retval = ""
        for i in range(len(self.music_queue)):
            retval += f"#{i + 1} - {self.music_queue[i][0]['title']}\n"

        if retval:
            await self.send_embed(ctx_or_interaction, f"**Queue:**\n{retval}", color=discord.Color.orange())
        else:
            await self.send_embed(ctx_or_interaction, "No music in queue", title="Queue", color=discord.Color.red())

    @commands.command(name="clear", help="Stops the music and clears the queue")
    async def clear(self, ctx):
        await self._clear(ctx)

    @app_commands.command(name="clear", description="Stops the music and clears the queue")
    async def slash_clear(self, interaction: discord.Interaction):
        await self._clear(interaction)

    async def _clear(self, ctx_or_interaction):
        if self.vc is not None and self.is_playing:
            self.vc.stop()
        self.music_queue = []
        self.is_playing = False
        self.is_paused = False
        self.current_song = None
        await self.send_embed(ctx_or_interaction, "Music queue cleared", color=discord.Color.green())

    @commands.command(name="stop", help="Stops the music and disconnects from the voice channel")
    async def stop(self, ctx):
        await self._stop(ctx)

    @app_commands.command(name="stop", description="Stops the music and disconnects from the voice channel")
    async def slash_stop(self, interaction: discord.Interaction):
        await self._stop(interaction)

    async def _stop(self, ctx_or_interaction):
        self.is_playing = False
        self.is_paused = False
        self.music_queue = []
        self.current_song = None
        if self.vc is not None:
            await self.vc.disconnect()
            self.vc = None
        await self.send_embed(ctx_or_interaction, "Stopped the music and disconnected from the voice channel", color=discord.Color.red())

    async def update_button_state(self, view, play):
        for item in view.children:
            if isinstance(item, discord.ui.Button):
                if play:
                    if item.emoji == "⏸️":
                        item.style = discord.ButtonStyle.primary
                        item.emoji = "▶️"
                else:
                    if item.emoji == "▶️":
                        item.style = discord.ButtonStyle.primary
                        item.emoji = "⏸️"

class MusicControlView(discord.ui.View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary)
    async def pause_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()  # Defer the interaction to prevent "interaction failed"
        await self.cog._pause(interaction)
        await interaction.edit_original_response(view=self)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary)
    async def skip_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()  # Defer the interaction to prevent "interaction failed"
        await self.cog._skip(interaction)
        await interaction.edit_original_response(view=self)

async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot))
