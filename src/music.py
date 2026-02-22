import discord
from discord.ext import commands
from discord import app_commands
from youtubesearchpython import VideosSearch
from yt_dlp import YoutubeDL
import aiohttp
import asyncio
import re
import logging

# Setup logging
logger = logging.getLogger(__name__)


def extract_artist_and_song(title):
    logger.debug(f"extract_artist_and_song: Original Title: {title}")
    
    # Define regex patterns for common YouTube title formats
    patterns = [
        r'^(.*?)\s*-\s*(.*?)$',  # "Artist - Song"
        r'^(.*?)\s*–\s*(.*?)$',  # "Artist – Song" (different dash)
        r'^(.*?)\s*:\s*(.*?)$',  # "Artist : Song"
        r'\"(.*?)\"\s*by\s*(.*?)$',  # '"Song" by Artist' -> swap: artist=group2, song=group1
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
    logger.debug(f"extract_artist_and_song: Cleaned Title: {clean_title}")

    # Try each pattern
    for pattern in patterns:
        match = re.match(pattern, clean_title)
        if match:
            first, second = match.groups()
            # Handle special case: '"Song" by Artist' pattern returns (song, artist)
            # Need to swap them - detect by checking if 'by' is in the pattern
            if 'by' in pattern:
                logger.debug(f"extract_artist_and_song: 'by' pattern matched, swapping: artist={second.strip()}, song={first.strip()}")
                return second.strip(), first.strip()
            logger.debug(f"extract_artist_and_song: Matched pattern '{pattern}', artist={first.strip()}, song={second.strip()}")
            return first.strip(), second.strip()

    logger.debug("extract_artist_and_song: No pattern matched, returning None, None")
    return None, None


class GuildMusicState:
    """Per-guild music state to handle multiple servers properly."""
    def __init__(self):
        self.is_playing = False
        self.is_paused = False
        self.music_queue = []
        self.current_song = None
        self.vc = None


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_states = {}  # Dictionary to store per-guild state
        self.YDL_OPTIONS = {'format': 'bestaudio/best'}
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        self.ytdl = YoutubeDL(self.YDL_OPTIONS)
        logger.info("MusicCog initialized")

    def get_guild_state(self, guild_id: int) -> GuildMusicState:
        """Get or create the music state for a guild."""
        if guild_id not in self.guild_states:
            self.guild_states[guild_id] = GuildMusicState()
        return self.guild_states[guild_id]

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Clean up guild state when bot leaves a server."""
        if guild.id in self.guild_states:
            state = self.guild_states[guild.id]
            if state.vc and state.vc.is_connected():
                await state.vc.disconnect()
            del self.guild_states[guild.id]
            logger.info(f"Cleaned up music state for guild {guild.id}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Reset music state when the bot is disconnected from voice externally."""
        if member.id != self.bot.user.id:
            return
        # Bot left a voice channel (kicked, moved out, or disconnected)
        if before.channel is not None and after.channel is None:
            guild_id = before.channel.guild.id
            if guild_id in self.guild_states:
                state = self.guild_states[guild_id]
                state.is_playing = False
                state.is_paused = False
                state.music_queue.clear()
                state.current_song = None
                state.vc = None
                logger.info(f"Bot was disconnected from voice in guild {guild_id}, state reset.")

    async def send_embed(self, ctx_or_interaction, description, title=None, color=discord.Color.purple(), thumbnail=None, view=None):
        logger.debug(f"send_embed: Sending Embed -> Title: {title}, Description: {description[:60]}...")
        embed = discord.Embed(description=description, color=color)
        if title:
            embed.title = title
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        msg = None
        if isinstance(ctx_or_interaction, commands.Context):
            msg = await ctx_or_interaction.send(embed=embed, view=view)
        else:
            # Handle interaction - check if already responded or deferred
            try:
                if ctx_or_interaction.response.is_done():
                    # Already responded, use followup
                    msg = await ctx_or_interaction.followup.send(embed=embed, view=view)
                else:
                    await ctx_or_interaction.response.send_message(embed=embed, view=view)
                    # interaction.response.send_message returns None;
                    # fetch the actual message so the view can edit it on timeout
                    msg = await ctx_or_interaction.original_response()
            except discord.errors.InteractionResponded:
                msg = await ctx_or_interaction.followup.send(embed=embed, view=view)
        
        # Store message reference on the view so on_timeout can disable buttons
        if view is not None and msg is not None:
            view.message = msg

    def search_yt(self, item):
        logger.debug(f"search_yt: Searching YouTube for '{item}'")
        try:
            search = VideosSearch(item, limit=1)
            results = search.result()["result"]
            if not results:
                logger.warning("search_yt: No results found")
                return None
            result = results[0]
            logger.debug(f"search_yt: Found video -> Title: {result['title']}, Link: {result['link']}")
            thumbnails = result.get("thumbnails")
            thumbnail_url = None
            if thumbnails and len(thumbnails) > 0:
                thumbnail_url = thumbnails[0].get("url")
            return {
                'source': result["link"],
                'title': result["title"],
                'duration': result["duration"],
                'thumbnail': thumbnail_url
            }
        except Exception as e:
            logger.error(f"search_yt: Failed to find or parse results. Error: {e}")
            return None

    async def play_next(self, guild_id: int):
        logger.debug("play_next: Checking queue to play next song...")
        state = self.get_guild_state(guild_id)
        
        if len(state.music_queue) > 0:
            state.is_playing = True
            state.current_song = state.music_queue.pop(0)
            m_url = state.current_song[0]['source']
            logger.debug(f"play_next: Next song URL -> {m_url}")
            
            loop = asyncio.get_running_loop()
            try:
                data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
                logger.debug(f"play_next: Received data from ytdl -> {data.get('url', 'No URL')}")
                song = data['url']
            except Exception as e:
                logger.error(f"play_next: Error extracting info with yt-dlp -> {e}")
                state.current_song = None
                # Skip to the next song iteratively to avoid deep recursion
                while len(state.music_queue) > 0:
                    state.current_song = state.music_queue.pop(0)
                    try:
                        next_url = state.current_song[0]['source']
                        data = await loop.run_in_executor(None, lambda u=next_url: self.ytdl.extract_info(u, download=False))
                        song = data['url']
                        break
                    except Exception as e2:
                        logger.error(f"play_next: Skipping failed song -> {e2}")
                        state.current_song = None
                        continue
                else:
                    # All remaining songs failed or queue empty
                    state.is_playing = False
                    state.current_song = None
                    return
            
            if state.vc is None or not state.vc.is_connected():
                logger.warning("play_next: Voice client disconnected, cannot play next song.")
                state.is_playing = False
                state.current_song = None
                return

            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song, **self.FFMPEG_OPTIONS))
            logger.debug("play_next: Attempting to play the next song.")
            
            def _after_play(error):
                if error:
                    logger.error(f"play_next: Playback error -> {error}")
                asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop)

            state.vc.play(source, after=_after_play)
        else:
            logger.debug("play_next: Queue is empty, stopping playback.")
            state.is_playing = False
            state.current_song = None

    async def play_music(self, ctx_or_interaction, guild_id: int):
        logger.debug("play_music: Checking if queue has songs...")
        state = self.get_guild_state(guild_id)
        
        if len(state.music_queue) > 0:
            state.is_playing = True
            state.current_song = state.music_queue.pop(0)
            m_url = state.current_song[0]['source']
            voice_channel = state.current_song[1]
            song_title = state.current_song[0]['title']
            song_duration = state.current_song[0]['duration']

            logger.debug(f"play_music: Song title -> {song_title}, URL -> {m_url}")

            try:
                if state.vc is None or not state.vc.is_connected():
                    logger.debug("play_music: Connecting to voice channel.")
                    state.vc = await voice_channel.connect()
                else:
                    logger.debug("play_music: Moving bot to the new voice channel.")
                    await state.vc.move_to(voice_channel)
            except Exception as e:
                logger.error(f"play_music: Could not connect to or move to voice channel -> {e}")
                state.is_playing = False
                state.current_song = None
                await self.send_embed(ctx_or_interaction, f"Could not connect to the voice channel: {str(e)}", title="Error", color=discord.Color.red())
                return

            loop = asyncio.get_running_loop()
            try:
                data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
                logger.debug(f"play_music: Extracted data from ytdl -> {data.get('url', 'No URL')}")
                song = data['url']
            except Exception as e:
                logger.error(f"play_music: Error extracting info with yt-dlp -> {e}")
                state.is_playing = False
                state.current_song = None
                await self.send_embed(ctx_or_interaction, f"Error extracting info: {str(e)}", title="Error", color=discord.Color.red())
                return

            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song, **self.FFMPEG_OPTIONS))

            logger.debug("play_music: Attempting to play the current song.")

            def _after_play(error):
                if error:
                    logger.error(f"play_music: Playback error -> {error}")
                asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop)

            state.vc.play(source, after=_after_play)
        else:
            logger.debug("play_music: Queue is empty, no song to play.")
            state.is_playing = False
            state.current_song = None

    async def play_autocomplete(self, interaction: discord.Interaction, current: str):
        logger.debug(f"play_autocomplete: Autocomplete triggered with input '{current}'")
        if not current:
            return []
        try:
            loop = asyncio.get_running_loop()
            def _search():
                search = VideosSearch(current, limit=5)
                return search.result()["result"]
            results = await loop.run_in_executor(None, _search)
            return [
                app_commands.Choice(name=f"{video['title'][:80]} - {video['duration']}", value=video["link"])
                for video in results
            ]
        except Exception as e:
            logger.error(f"play_autocomplete: Error during autocomplete: {e}")
            return []

    @commands.command(name="play", help="Plays a selected song from YouTube")
    async def play(self, ctx, *, query: str):
        logger.info(f"command:play: Called with query -> {query}")
        await self._play(ctx, query)

    @app_commands.command(name="play", description="Plays a selected song from YouTube")
    @app_commands.autocomplete(query=play_autocomplete)
    async def slash_play(self, interaction: discord.Interaction, query: str):
        logger.info(f"slash command:play: Called with query -> {query}")
        await self._play(interaction, query)

    async def _play(self, ctx_or_interaction, query):
        logger.debug(f"_play: Attempting to play -> {query}")
        if isinstance(ctx_or_interaction, commands.Context):
            if ctx_or_interaction.guild is None:
                await ctx_or_interaction.send("Music commands can only be used in a server.")
                return
            author = ctx_or_interaction.author
            guild_id = ctx_or_interaction.guild.id
        else:
            if ctx_or_interaction.guild_id is None:
                await ctx_or_interaction.response.send_message("Music commands can only be used in a server.")
                return
            author = ctx_or_interaction.user
            guild_id = ctx_or_interaction.guild_id
            # Defer slash command response to avoid 3-second interaction timeout
            if not ctx_or_interaction.response.is_done():
                await ctx_or_interaction.response.defer()

        state = self.get_guild_state(guild_id)

        try:
            voice_channel = author.voice.channel
            logger.debug(f"_play: Found voice channel -> {voice_channel}")
        except AttributeError:
            logger.warning("_play: User not in a voice channel.")
            await self.send_embed(ctx_or_interaction, "You need to connect to a voice channel first!", title="Error", color=discord.Color.red())
            return

        loop = asyncio.get_running_loop()
        song = await loop.run_in_executor(None, self.search_yt, query)
        if song is None:
            logger.warning("_play: search_yt returned None.")
            await self.send_embed(ctx_or_interaction, "Could not download the song. Incorrect format or unsupported type. Please try another keyword.", title="Error", color=discord.Color.red())
            return

        state.music_queue.append([song, voice_channel])
        logger.info(f"_play: Added song '{song['title']}' to queue. Queue length is now {len(state.music_queue)}")

        view = MusicControlView(self, guild_id)
        if state.is_paused:
            logger.debug("_play: Bot is paused, resuming and queuing new song.")
            state.vc.resume()
            state.is_paused = False
            state.is_playing = True
            await self.send_embed(
                ctx_or_interaction,
                f"Resumed playback and added **'{song['title']}'** (Duration: {song['duration']}) to the queue",
                color=discord.Color.green(),
                thumbnail=song['thumbnail'],
                view=view
            )
        elif state.is_playing:
            logger.debug("_play: Already playing, just adding to queue.")
            await self.send_embed(
                ctx_or_interaction, 
                f"**#{len(state.music_queue)} - '{song['title']}'** (Duration: {song['duration']}) added to the queue", 
                color=discord.Color.green(), 
                thumbnail=song['thumbnail'], 
                view=view
            )
        else:
            logger.debug("_play: Not playing, will start now.")
            await self.send_embed(
                ctx_or_interaction, 
                f"**{song['title']}** (Duration: {song['duration']})", 
                color=discord.Color.green(), 
                thumbnail=song['thumbnail'], 
                view=view
            )
            await self.play_music(ctx_or_interaction, guild_id)

    @commands.command(name="pause", help="Pauses the current song being played")
    async def pause(self, ctx):
        logger.info("command:pause called.")
        await self._pause(ctx)

    @app_commands.command(name="pause", description="Pauses the current song being played")
    async def slash_pause(self, interaction: discord.Interaction):
        logger.info("slash command:pause called.")
        await self._pause(interaction)

    async def _pause(self, ctx_or_interaction):
        logger.debug("_pause: Attempting to pause.")
        if isinstance(ctx_or_interaction, commands.Context):
            if ctx_or_interaction.guild is None:
                await ctx_or_interaction.send("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild.id
        else:
            if ctx_or_interaction.guild_id is None:
                await ctx_or_interaction.response.send_message("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild_id
        
        state = self.get_guild_state(guild_id)
        
        if state.is_playing and state.vc is not None:
            state.is_playing = False
            state.is_paused = True
            state.vc.pause()
            view = MusicControlView(self, guild_id)
            await self.send_embed(ctx_or_interaction, "Paused the current song", color=discord.Color.orange(), view=view)
        else:
            logger.warning("_pause: No song is currently playing.")
            await self.send_embed(ctx_or_interaction, "No song is currently playing.", color=discord.Color.red())

    @commands.command(name="resume", help="Resumes playing with the Discord bot")
    async def resume(self, ctx):
        logger.info("command:resume called.")
        await self._resume(ctx)

    @app_commands.command(name="resume", description="Resumes playing with the Discord bot")
    async def slash_resume(self, interaction: discord.Interaction):
        logger.info("slash command:resume called.")
        await self._resume(interaction)

    async def _resume(self, ctx_or_interaction):
        logger.debug("_resume: Attempting to resume.")
        if isinstance(ctx_or_interaction, commands.Context):
            if ctx_or_interaction.guild is None:
                await ctx_or_interaction.send("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild.id
        else:
            if ctx_or_interaction.guild_id is None:
                await ctx_or_interaction.response.send_message("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild_id
        
        state = self.get_guild_state(guild_id)
        
        if state.is_paused and state.vc is not None:
            state.is_paused = False
            state.is_playing = True
            state.vc.resume()
            view = MusicControlView(self, guild_id)
            await self.send_embed(ctx_or_interaction, "Resumed the current song", color=discord.Color.green(), view=view)
        else:
            logger.warning("_resume: Bot is not paused, cannot resume.")
            await self.send_embed(ctx_or_interaction, "No song is paused.", color=discord.Color.red())

    @commands.command(name="skip", help="Skips the current song being played")
    async def skip(self, ctx):
        logger.info("command:skip called.")
        await self._skip(ctx)

    @app_commands.command(name="skip", description="Skips the current song being played")
    async def slash_skip(self, interaction: discord.Interaction):
        logger.info("slash command:skip called.")
        await self._skip(interaction)

    async def _skip(self, ctx_or_interaction):
        logger.debug("_skip: Attempting to skip current song.")
        if isinstance(ctx_or_interaction, commands.Context):
            if ctx_or_interaction.guild is None:
                await ctx_or_interaction.send("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild.id
        else:
            if ctx_or_interaction.guild_id is None:
                await ctx_or_interaction.response.send_message("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild_id
        
        state = self.get_guild_state(guild_id)
        
        if state.vc is not None and (state.vc.is_playing() or state.is_paused):
            state.vc.stop()
            # play_next is triggered automatically by the after callback
            await self.send_embed(ctx_or_interaction, "Skipped the current song", color=discord.Color.green())
        else:
            logger.warning("_skip: There is no current song playing to skip.")
            await self.send_embed(ctx_or_interaction, "No song is currently playing.", color=discord.Color.red())

    # Lyrics
    @commands.command(name="lyrics", help="Prints the lyrics of the current song being played")
    async def lyrics(self, ctx):
        logger.info("command:lyrics called.")
        await self._lyrics(ctx)

    @app_commands.command(name="lyrics", description="Prints the lyrics of the current song being played")
    async def slash_lyrics(self, interaction: discord.Interaction):
        logger.info("slash command:lyrics called.")
        await self._lyrics(interaction)

    async def _lyrics(self, ctx_or_interaction):
        logger.debug("_lyrics: Attempting to fetch lyrics.")
        if isinstance(ctx_or_interaction, commands.Context):
            if ctx_or_interaction.guild is None:
                await ctx_or_interaction.send("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild.id
        else:
            if ctx_or_interaction.guild_id is None:
                await ctx_or_interaction.response.send_message("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild_id
            # Defer slash command response to avoid 3-second interaction timeout
            if not ctx_or_interaction.response.is_done():
                await ctx_or_interaction.response.defer()
        
        state = self.get_guild_state(guild_id)
        
        if state.vc is None or (not state.vc.is_playing() and not state.is_paused):
            logger.warning("_lyrics: No song is currently playing or paused.")
            await self.send_embed(ctx_or_interaction, "No song is currently playing.", title="Error", color=discord.Color.red())
            return

        # Check if current_song exists
        if state.current_song is None:
            logger.warning("_lyrics: current_song is None.")
            await self.send_embed(ctx_or_interaction, "No song information available.", title="Error", color=discord.Color.red())
            return

        logger.debug(f"_lyrics: Current song title -> {state.current_song[0]['title']}")
        artist, song_title = extract_artist_and_song(state.current_song[0]['title'])
        logger.debug(f"_lyrics: Extracted -> Artist: {artist}, Title: {song_title}")

        if not artist or not song_title:
            logger.warning("_lyrics: Could not extract artist/song from the title, skipping lyrics fetch.")
            await self.send_embed(ctx_or_interaction, "Could not determine artist and song title for lyrics.", title="Error", color=discord.Color.red())
            return

        lyrics_url = f"https://api.lyrics.ovh/v1/{artist}/{song_title}"
        logger.debug(f"_lyrics: Lyrics URL -> {lyrics_url}")

        # Use async HTTP request instead of blocking requests
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(lyrics_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        lyrics = data.get('lyrics', None)
                        if lyrics:
                            # Truncate lyrics if too long for Discord embed
                            if len(lyrics) > 4000:
                                lyrics = lyrics[:4000] + "\n\n...(lyrics truncated)"
                            logger.info("_lyrics: Lyrics found, sending embed.")
                            await self.send_embed(ctx_or_interaction, f"**Lyrics for '{song_title}':**\n\n{lyrics}", color=discord.Color.green())
                        else:
                            logger.warning("_lyrics: Lyrics not found in API response.")
                            await self.send_embed(ctx_or_interaction, "Lyrics not found.", title="Error", color=discord.Color.red())
                    else:
                        logger.warning("_lyrics: Failed to fetch lyrics from API.")
                        await self.send_embed(ctx_or_interaction, "Could not fetch lyrics.", title="Error", color=discord.Color.red())
        except aiohttp.ClientError as e:
            logger.error(f"_lyrics: HTTP error fetching lyrics: {e}")
            await self.send_embed(ctx_or_interaction, "Could not fetch lyrics.", title="Error", color=discord.Color.red())

    # Queue
    @commands.command(name="queue", help="Displays the current song queue")
    async def queue(self, ctx):
        logger.info("command:queue called.")
        await self._queue(ctx)

    @app_commands.command(name="queue", description="Displays the current song queue")
    async def slash_queue(self, interaction: discord.Interaction):
        logger.info("slash command:queue called.")
        await self._queue(interaction)

    async def _queue(self, ctx_or_interaction):
        logger.debug("_queue: Attempting to display queue.")
        if isinstance(ctx_or_interaction, commands.Context):
            if ctx_or_interaction.guild is None:
                await ctx_or_interaction.send("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild.id
        else:
            if ctx_or_interaction.guild_id is None:
                await ctx_or_interaction.response.send_message("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild_id
        
        state = self.get_guild_state(guild_id)
        
        retval = ""
        for i in range(len(state.music_queue)):
            song_title = state.music_queue[i][0]['title']
            song_duration = state.music_queue[i][0]['duration']
            retval += f"#{i + 1} - {song_title} ({song_duration})\n"

        if retval:
            logger.debug("_queue: Queue contents found.")
            await self.send_embed(ctx_or_interaction, f"**Queue:**\n{retval}", color=discord.Color.orange())
        else:
            logger.debug("_queue: Queue is empty.")
            await self.send_embed(ctx_or_interaction, "No music in queue", title="Queue", color=discord.Color.red())

    @commands.command(name="stop", help="Stops playing music and clears the queue")
    async def stop(self, ctx):
        logger.info("command:stop called.")
        await self._stop(ctx)

    @app_commands.command(name="stop", description="Stops playing music and clears the queue")
    async def slash_stop(self, interaction: discord.Interaction):
        logger.info("slash command:stop called.")
        await self._stop(interaction)

    async def _stop(self, ctx_or_interaction):
        logger.debug("_stop: Attempting to stop and clear queue.")
        if isinstance(ctx_or_interaction, commands.Context):
            if ctx_or_interaction.guild is None:
                await ctx_or_interaction.send("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild.id
        else:
            if ctx_or_interaction.guild_id is None:
                await ctx_or_interaction.response.send_message("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild_id
        
        state = self.get_guild_state(guild_id)
        
        if state.vc is not None:
            await state.vc.disconnect()
        state.is_playing = False
        state.is_paused = False
        state.music_queue.clear()
        state.current_song = None
        state.vc = None
        await self.send_embed(ctx_or_interaction, "Stopped playing music and cleared the queue.", color=discord.Color.red())

    # Now Playing
    @app_commands.command(name="nowplaying", description="Shows the currently playing song")
    async def slash_nowplaying(self, interaction: discord.Interaction):
        logger.info("slash command:nowplaying called.")
        await self._nowplaying(interaction)

    @commands.command(name="nowplaying", aliases=["np"], help="Shows the currently playing song")
    async def nowplaying(self, ctx):
        logger.info("command:nowplaying called.")
        await self._nowplaying(ctx)

    async def _nowplaying(self, ctx_or_interaction):
        logger.debug("_nowplaying: Attempting to show current song.")
        if isinstance(ctx_or_interaction, commands.Context):
            if ctx_or_interaction.guild is None:
                await ctx_or_interaction.send("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild.id
        else:
            if ctx_or_interaction.guild_id is None:
                await ctx_or_interaction.response.send_message("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild_id

        state = self.get_guild_state(guild_id)

        if state.current_song is not None and (state.is_playing or state.is_paused):
            song = state.current_song[0]
            status = "⏸️ Paused" if state.is_paused else "▶️ Playing"
            view = MusicControlView(self, guild_id)
            await self.send_embed(
                ctx_or_interaction,
                f"{status}: **{song['title']}**\nDuration: {song['duration']}",
                title="Now Playing",
                color=discord.Color.green(),
                thumbnail=song.get('thumbnail'),
                view=view
            )
        else:
            await self.send_embed(ctx_or_interaction, "No song is currently playing.", color=discord.Color.red())

    # Remove from queue
    @app_commands.command(name="removequeue", description="Remove a song from the queue by position")
    @app_commands.describe(position="Position in queue (1, 2, 3...)")
    async def slash_removequeue(self, interaction: discord.Interaction, position: int):
        logger.info(f"slash command:removequeue called with position {position}.")
        await self._removequeue(interaction, position)

    @commands.command(name="removequeue", aliases=["rq"], help="Remove a song from the queue by position")
    async def removequeue(self, ctx, position: int):
        logger.info(f"command:removequeue called with position {position}.")
        await self._removequeue(ctx, position)

    async def _removequeue(self, ctx_or_interaction, position: int):
        logger.debug(f"_removequeue: Removing position {position} from queue.")
        if isinstance(ctx_or_interaction, commands.Context):
            if ctx_or_interaction.guild is None:
                await ctx_or_interaction.send("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild.id
        else:
            if ctx_or_interaction.guild_id is None:
                await ctx_or_interaction.response.send_message("Music commands can only be used in a server.")
                return
            guild_id = ctx_or_interaction.guild_id

        state = self.get_guild_state(guild_id)
        index = position - 1

        if index < 0 or index >= len(state.music_queue):
            await self.send_embed(
                ctx_or_interaction,
                f"Invalid position. Queue has {len(state.music_queue)} song(s).",
                title="Error",
                color=discord.Color.red()
            )
            return

        removed = state.music_queue.pop(index)
        removed_title = removed[0]['title']
        await self.send_embed(
            ctx_or_interaction,
            f"Removed **{removed_title}** from position #{position} in the queue.",
            color=discord.Color.green()
        )


class MusicControlView(discord.ui.View):
    def __init__(self, cog: MusicCog, guild_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.guild_id = guild_id

    async def on_timeout(self):
        """Disable all buttons when the view times out."""
        for item in self.children:
            item.disabled = True
        # Try to edit the message to show disabled buttons
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.primary)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info("MusicControlView: Pause button clicked.")
        await self.cog._pause(interaction)

    @discord.ui.button(label="Resume", style=discord.ButtonStyle.success)
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info("MusicControlView: Resume button clicked.")
        await self.cog._resume(interaction)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.danger)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info("MusicControlView: Skip button clicked.")
        await self.cog._skip(interaction)


async def setup(bot: commands.Bot):
    logger.info("setup: Adding MusicCog to bot.")
    await bot.add_cog(MusicCog(bot))
