import discord
from discord.ext import commands
from discord import app_commands
from youtubesearchpython import VideosSearch
from yt_dlp import YoutubeDL
from bs4 import BeautifulSoup
import asyncio
import requests
import re

def extract_artist_and_song(title):
    print(f"[DEBUG] extract_artist_and_song: Original Title: {title}")
    
    # Define regex patterns for common YouTube title formats
    patterns = [
        r'^(.*?)\s*-\s*(.*?)$',  # "Artist - Song"
        r'^(.*?)\s*–\s*(.*?)$',  # "Artist – Song" (different dash)
        r'^(.*?)\s*:\s*(.*?)$',  # "Artist : Song"
        r'\"(.*?)\"\s*by\s*(.*?)$',  # '"Song" by Artist'
        r'^(.*?)\s*\"(.*?)\"$',  # 'Artist "Song"'
        r'^(.*?)\s*\((.*?)\)$',  # "Artist (Song)"
    ]
    
    # Words to ignore in the title
    ignore_words = [
        "slowed", "sped up", "lyrics", "official", "audio", "video", "music video",
        "remix", "cover", "live", "HD", "HQ"
    ]
    
    # Remove ignore words from the title
    clean_title = title
    for word in ignore_words:
        clean_title = re.sub(rf'\b{word}\b', '', clean_title, flags=re.IGNORECASE)
    
    clean_title = ' '.join(clean_title.split())  # Trim extra spaces
    print(f"[DEBUG] extract_artist_and_song: Cleaned Title: {clean_title}")

    # Try each pattern
    for pattern in patterns:
        match = re.match(pattern, clean_title)
        if match:
            artist, song = match.groups()
            print(f"[DEBUG] extract_artist_and_song: Matched pattern '{pattern}', artist={artist.strip()}, song={song.strip()}")
            return artist.strip(), song.strip()

    print("[DEBUG] extract_artist_and_song: No pattern matched, returning None, None")
    return None, None

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
        print("[DEBUG] MusicCog initialized")

    async def send_embed(self, ctx_or_interaction, description, title=None, color=discord.Color.purple(), thumbnail=None, view=None):
        print(f"[DEBUG] send_embed: Sending Embed -> Title: {title}, Description: {description[:60]}...")
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
        print(f"[DEBUG] search_yt: Searching YouTube for '{item}'")
        try:
            search = VideosSearch(item, limit=1)
            result = search.result()["result"][0]
            print(f"[DEBUG] search_yt: Found video -> Title: {result['title']}, Link: {result['link']}")
            return {
                'source': result["link"],
                'title': result["title"],
                'duration': result["duration"],
                'thumbnail': result["thumbnails"][0]["url"]
            }
        except Exception as e:
            print(f"[DEBUG] search_yt: Failed to find or parse results. Error: {e}")
            return None

    async def play_next(self):
        print("[DEBUG] play_next: Checking queue to play next song...")
        if len(self.music_queue) > 0:
            self.is_playing = True
            self.current_song = self.music_queue.pop(0)
            m_url = self.current_song[0]['source']
            print(f"[DEBUG] play_next: Next song URL -> {m_url}")
            
            loop = asyncio.get_running_loop()
            try:
                data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
                print(f"[DEBUG] play_next: Received data from ytdl -> {data.get('url', 'No URL')}")
            except Exception as e:
                print(f"[DEBUG] play_next: Error extracting info with yt-dlp -> {e}")
                self.is_playing = False
                self.current_song = None
                return
            
            song = data['url']
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song, **self.FFMPEG_OPTIONS))
            print("[DEBUG] play_next: Attempting to play the next song.")
            
            self.vc.play(
                source, 
                after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop)
            )
        else:
            print("[DEBUG] play_next: Queue is empty, stopping playback.")
            self.is_playing = False
            self.current_song = None

    async def play_music(self, ctx_or_interaction):
        print("[DEBUG] play_music: Checking if queue has songs...")
        if len(self.music_queue) > 0:
            self.is_playing = True
            self.current_song = self.music_queue.pop(0)
            m_url = self.current_song[0]['source']
            voice_channel = self.current_song[1]
            song_title = self.current_song[0]['title']
            song_duration = self.current_song[0]['duration']

            print(f"[DEBUG] play_music: Song title -> {song_title}, URL -> {m_url}")

            try:
                if self.vc is None or not self.vc.is_connected():
                    print("[DEBUG] play_music: Connecting to voice channel.")
                    self.vc = await voice_channel.connect()
                else:
                    print("[DEBUG] play_music: Moving bot to the new voice channel.")
                    await self.vc.move_to(voice_channel)
            except Exception as e:
                print(f"[DEBUG] play_music: Could not connect to or move to voice channel -> {e}")
                await self.send_embed(ctx_or_interaction, f"Could not connect to the voice channel: {str(e)}", title="Error", color=discord.Color.red())
                return

            loop = asyncio.get_running_loop()
            try:
                data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
                print(f"[DEBUG] play_music: Extracted data from ytdl -> {data.get('url', 'No URL')}")
            except Exception as e:
                print(f"[DEBUG] play_music: Error extracting info with yt-dlp -> {e}")
                await self.send_embed(ctx_or_interaction, f"Error extracting info: {str(e)}", title="Error", color=discord.Color.red())
                return

            song = data['url']
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song, **self.FFMPEG_OPTIONS))

            print("[DEBUG] play_music: Attempting to play the current song.")
            self.vc.play(
                source, 
                after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop)
            )
            
            # Send embed showing the song title and duration
            await self.send_embed(
                ctx_or_interaction, 
                f"**{song_title}**\nDuration: {song_duration}", 
                color=discord.Color.green(), 
                thumbnail=self.current_song[0]['thumbnail']
            )
        else:
            print("[DEBUG] play_music: Queue is empty, no song to play.")
            self.is_playing = False
            self.current_song = None

    async def play_autocomplete(self, interaction: discord.Interaction, current: str):
        print(f"[DEBUG] play_autocomplete: Autocomplete triggered with input '{current}'")
        search = VideosSearch(current, limit=5)
        results = search.result()["result"]
        return [
            app_commands.Choice(name=f"{video['title']} - {video['duration']}", value=video["link"])
            for video in results
        ]

    @commands.command(name="play", help="Plays a selected song from YouTube")
    async def play(self, ctx, *, query: str):
        print(f"[DEBUG] command:play: Called with query -> {query}")
        await self._play(ctx, query)

    @app_commands.command(name="play", description="Plays a selected song from YouTube")
    @app_commands.autocomplete(query=play_autocomplete)
    async def slash_play(self, interaction: discord.Interaction, query: str):
        print(f"[DEBUG] slash command:play: Called with query -> {query}")
        await self._play(interaction, query)

    async def _play(self, ctx_or_interaction, query):
        print(f"[DEBUG] _play: Attempting to play -> {query}")
        if isinstance(ctx_or_interaction, commands.Context):
            author = ctx_or_interaction.author
        else:
            author = ctx_or_interaction.user

        try:
            voice_channel = author.voice.channel
            print(f"[DEBUG] _play: Found voice channel -> {voice_channel}")
        except AttributeError:
            print("[DEBUG] _play: User not in a voice channel.")
            await self.send_embed(ctx_or_interaction, "You need to connect to a voice channel first!", title="Error", color=discord.Color.red())
            return

        if self.is_paused:
            print("[DEBUG] _play: Bot is paused, resuming.")
            self.vc.resume()
            self.is_paused = False
            self.is_playing = True
        else:
            song = self.search_yt(query)
            if song is None:
                print("[DEBUG] _play: search_yt returned None.")
                await self.send_embed(ctx_or_interaction, "Could not download the song. Incorrect format or unsupported type. Please try another keyword.", title="Error", color=discord.Color.red())
            else:
                self.music_queue.append([song, voice_channel])
                print(f"[DEBUG] _play: Added song '{song['title']}' to queue. Queue length is now {len(self.music_queue)}")

                view = MusicControlView(self)
                if self.is_playing:
                    print("[DEBUG] _play: Already playing, just adding to queue.")
                    await self.send_embed(
                        ctx_or_interaction, 
                        f"**#{len(self.music_queue) + 1} - '{song['title']}'** (Duration: {song['duration']}) added to the queue", 
                        color=discord.Color.green(), 
                        thumbnail=song['thumbnail'], 
                        view=view
                    )
                else:
                    print("[DEBUG] _play: Not playing, will start now.")
                    await self.send_embed(
                        ctx_or_interaction, 
                        f"**{song['title']}** (Duration: {song['duration']})", 
                        color=discord.Color.green(), 
                        thumbnail=song['thumbnail'], 
                        view=view
                    )
                    await self.play_music(ctx_or_interaction)

    @commands.command(name="pause", help="Pauses the current song being played")
    async def pause(self, ctx):
        print("[DEBUG] command:pause called.")
        await self._pause(ctx)

    @app_commands.command(name="pause", description="Pauses the current song being played")
    async def slash_pause(self, interaction: discord.Interaction):
        print("[DEBUG] slash command:pause called.")
        await self._pause(interaction)

    async def _pause(self, ctx_or_interaction):
        print("[DEBUG] _pause: Attempting to pause.")
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
            view = MusicControlView(self)
            await self.update_button_state(view, play=True)
            await self.send_embed(ctx_or_interaction, "Paused the current song", color=discord.Color.orange(), view=view)
        else:
            print("[DEBUG] _pause: No song is currently playing.")

    @commands.command(name="resume", help="Resumes playing with the Discord bot")
    async def resume(self, ctx):
        print("[DEBUG] command:resume called.")
        await self._resume(ctx)

    @app_commands.command(name="resume", description="Resumes playing with the Discord bot")
    async def slash_resume(self, interaction: discord.Interaction):
        print("[DEBUG] slash command:resume called.")
        await self._resume(interaction)

    async def _resume(self, ctx_or_interaction):
        print("[DEBUG] _resume: Attempting to resume.")
        if self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()
            view = MusicControlView(self)
            await self.update_button_state(view, play=False)
            await self.send_embed(ctx_or_interaction, "Resumed the current song", color=discord.Color.green(), view=view)
        else:
            print("[DEBUG] _resume: Bot is not paused, cannot resume.")

    @commands.command(name="skip", help="Skips the current song being played")
    async def skip(self, ctx):
        print("[DEBUG] command:skip called.")
        await self._skip(ctx)

    @app_commands.command(name="skip", description="Skips the current song being played")
    async def slash_skip(self, interaction: discord.Interaction):
        print("[DEBUG] slash command:skip called.")
        await self._skip(interaction)

    async def _skip(self, ctx_or_interaction):
        print("[DEBUG] _skip: Attempting to skip current song.")
        if self.vc is not None and self.vc.is_playing():
            self.vc.stop()
            await self.play_music(ctx_or_interaction)
            await self.send_embed(ctx_or_interaction, "Skipped the current song", color=discord.Color.green())
        else:
            print("[DEBUG] _skip: There is no current song playing to skip.")

    # Lyrics
    @commands.command(name="lyrics", help="Prints the lyrics of the current song being played")
    async def lyrics(self, ctx):
        print("[DEBUG] command:lyrics called.")
        await self._lyrics(ctx)

    @app_commands.command(name="lyrics", description="Prints the lyrics of the current song being played")
    async def slash_lyrics(self, interaction: discord.Interaction):
        print("[DEBUG] slash command:lyrics called.")
        await self._lyrics(interaction)

    async def _lyrics(self, ctx_or_interaction):
        print("[DEBUG] _lyrics: Attempting to fetch lyrics.")
        if self.vc is None or not self.vc.is_playing():
            print("[DEBUG] _lyrics: No song is currently playing.")
            await self.send_embed(ctx_or_interaction, "No song is currently playing.", title="Error", color=discord.Color.red())
            return

        print(f"[DEBUG] _lyrics: Current song title -> {self.current_song[0]['title']}")
        artist, song_title = extract_artist_and_song(self.current_song[0]['title'])
        print(f"[DEBUG] _lyrics: Extracted -> Artist: {artist}, Title: {song_title}")

        if not artist or not song_title:
            print("[DEBUG] _lyrics: Could not extract artist/song from the title, skipping lyrics fetch.")
            await self.send_embed(ctx_or_interaction, "Could not determine artist and song title for lyrics.", title="Error", color=discord.Color.red())
            return

        lyrics_url = f"https://api.lyrics.ovh/v1/{artist}/{song_title}"
        print(f"[DEBUG] _lyrics: Lyrics URL -> {lyrics_url}")

        response = requests.get(lyrics_url)
        if response.status_code == 200:
            data = response.json()
            lyrics = data.get('lyrics', None)
            if lyrics:
                # Send the lyrics in an embed
                print("[DEBUG] _lyrics: Lyrics found, sending embed.")
                await self.send_embed(ctx_or_interaction, f"**Lyrics for '{song_title}':**\n\n{lyrics}", color=discord.Color.green())
            else:
                print("[DEBUG] _lyrics: Lyrics not found in API response.")
                await self.send_embed(ctx_or_interaction, "Lyrics not found.", title="Error", color=discord.Color.red())
        else:
            print("[DEBUG] _lyrics: Failed to fetch lyrics from API.")
            await self.send_embed(ctx_or_interaction, "Could not fetch lyrics.", title="Error", color=discord.Color.red())

    # Queue
    @commands.command(name="queue", help="Displays the current song queue")
    async def queue(self, ctx):
        print("[DEBUG] command:queue called.")
        await self._queue(ctx)

    @app_commands.command(name="queue", description="Displays the current song queue")
    async def slash_queue(self, interaction: discord.Interaction):
        print("[DEBUG] slash command:queue called.")
        await self._queue(interaction)

    async def _queue(self, ctx_or_interaction):
        print("[DEBUG] _queue: Attempting to display queue.")
        retval = ""
        for i in range(len(self.music_queue)):
            song_title = self.music_queue[i][0]['title']
            song_duration = self.music_queue[i][0]['duration']
            retval += f"#{i + 1} - {song_title} ({song_duration})\n"

        if retval:
            print("[DEBUG] _queue: Queue contents found.")
            await self.send_embed(ctx_or_interaction, f"**Queue:**\n{retval}", color=discord.Color.orange())
        else:
            print("[DEBUG] _queue: Queue is empty.")
            await self.send_embed(ctx_or_interaction, "No music in queue", title="Queue", color=discord.Color.red())

    @commands.command(name="stop", help="Stops playing music and clears the queue")
    async def stop(self, ctx):
        print("[DEBUG] command:stop called.")
        await self._stop(ctx)

    @app_commands.command(name="stop", description="Stops playing music and clears the queue")
    async def slash_stop(self, interaction: discord.Interaction):
        print("[DEBUG] slash command:stop called.")
        await self._stop(interaction)

    async def _stop(self, ctx_or_interaction):
        print("[DEBUG] _stop: Attempting to stop and clear queue.")
        if self.vc is not None:
            await self.vc.disconnect()
        self.is_playing = False
        self.is_paused = False
        self.music_queue.clear()
        self.current_song = None
        await self.send_embed(ctx_or_interaction, "Stopped playing music and cleared the queue.", color=discord.Color.red())

class MusicControlView(discord.ui.View):
    def __init__(self, bot: MusicCog):
        super().__init__()
        self.bot = bot

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.primary)
    async def pause_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        print("[DEBUG] MusicControlView: Pause button clicked.")
        await self.bot._pause(interaction)

    @discord.ui.button(label="Resume", style=discord.ButtonStyle.success)
    async def resume_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        print("[DEBUG] MusicControlView: Resume button clicked.")
        await self.bot._resume(interaction)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.danger)
    async def skip_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        print("[DEBUG] MusicControlView: Skip button clicked.")
        await self.bot._skip(interaction)

    async def update_button_state(self, view, play):
        print(f"[DEBUG] MusicControlView: update_button_state called with play={play}")
        if play:
            view.pause_button.disabled = True
            view.resume_button.disabled = False
        else:
            view.pause_button.disabled = False
            view.resume_button.disabled = True

async def setup(bot: commands.Bot):
    print("[DEBUG] setup: Adding MusicCog to bot.")
    await bot.add_cog(MusicCog(bot))
