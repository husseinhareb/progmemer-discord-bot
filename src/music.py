import discord
from discord.ext import commands
from discord import app_commands
from youtubesearchpython import VideosSearch
from yt_dlp import YoutubeDL
import asyncio

class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.is_playing = False
        self.is_paused = False
        self.music_queue = []
        self.YDL_OPTIONS = {'format': 'bestaudio/best'}
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        self.vc = None
        self.ytdl = YoutubeDL(self.YDL_OPTIONS)

    async def send_embed(self, ctx_or_interaction, description, title=None, color=discord.Color.purple()):
        embed = discord.Embed(description=description, color=color)
        if title:
            embed.title = title
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed)
        else:
            await ctx_or_interaction.response.send_message(embed=embed)

    def search_yt(self, item):
        search = VideosSearch(item, limit=1)
        result = search.result()["result"][0]
        return {'source': result["link"], 'title': result["title"]}

    async def play_next(self):
        if len(self.music_queue) > 0:
            self.is_playing = True
            m_url = self.music_queue[0][0]['source']
            self.music_queue.pop(0)
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
            song = data['url']
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song, **self.FFMPEG_OPTIONS))
            self.vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))
        else:
            self.is_playing = False

    async def play_music(self, ctx_or_interaction):
        if len(self.music_queue) > 0:
            self.is_playing = True
            m_url = self.music_queue[0][0]['source']
            voice_channel = self.music_queue[0][1]
            if self.vc is None or not self.vc.is_connected():
                self.vc = await voice_channel.connect()
                if self.vc is None:
                    await self.send_embed(ctx_or_interaction, "Could not connect to the voice channel", title="Error", color=discord.Color.red())
                    return
            else:
                await self.vc.move_to(voice_channel)

            self.music_queue.pop(0)
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
            song = data['url']
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song, **self.FFMPEG_OPTIONS))
            self.vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))
        else:
            self.is_playing = False

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
                if self.is_playing:
                    await self.send_embed(ctx_or_interaction, f"**#{len(self.music_queue) + 1} - '{song['title']}'** added to the queue", color=discord.Color.green())
                else:
                    await self.send_embed(ctx_or_interaction, f"**{song['title']}**", color=discord.Color.green())
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
            await self.send_embed(ctx_or_interaction, "Paused the current song", color=discord.Color.orange())

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
            await self.send_embed(ctx_or_interaction, "Resumed the current song", color=discord.Color.green())

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
        await self.send_embed(ctx_or_interaction, "Music queue cleared", color=discord.Color.green())

    @commands.command(name="stop", help="Kick the bot from VC")
    async def dc(self, ctx):
        await self._dc(ctx)

    @app_commands.command(name="stop", description="Kick the bot from VC")
    async def slash_dc(self, interaction: discord.Interaction):
        await self._dc(interaction)

    async def _dc(self, ctx_or_interaction):
        self.is_playing = False
        self.is_paused = False
        if self.vc is not None:
            await self.vc.disconnect()
            self.vc = None
        await self.send_embed(ctx_or_interaction, "Disconnected from the voice channel", color=discord.Color.red())

    @commands.command(name="remove", help="Removes last song added to queue")
    async def re(self, ctx):
        await self._re(ctx)

    @app_commands.command(name="remove", description="Removes last song added to queue")
    async def slash_re(self, interaction: discord.Interaction):
        await self._re(interaction)

    async def _re(self, ctx_or_interaction):
        if len(self.music_queue) > 0:
            removed_song = self.music_queue.pop()
            await self.send_embed(ctx_or_interaction, f"Removed {removed_song[0]['title']} from the queue", color=discord.Color.green())
        else:
            await self.send_embed(ctx_or_interaction, "No songs in queue to remove", title="Remove", color=discord.Color.red())

async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot))

