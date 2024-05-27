import discord
from discord.ext import commands
from discord import app_commands
from youtubesearchpython import VideosSearch
from yt_dlp import YoutubeDL
import asyncio
from discord.ui import Button, View

class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # all the music related stuff
        self.is_playing = False
        self.is_paused = False

        # 2d array containing [song, channel]
        self.music_queue = []
        self.YDL_OPTIONS = {'format': 'bestaudio/best'}
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        self.vc = None
        self.ytdl = YoutubeDL(self.YDL_OPTIONS)

    # Helper method to create and send embeds
    async def send_embed(self, ctx_or_interaction, description, title=None, color=discord.Color.purple()):
        embed = discord.Embed(description=description, color=color)
        if title:
            embed.title = title

        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed)
        else:
            await ctx_or_interaction.response.send_message(embed=embed)

    # searching the item on youtube
    def search_yt(self, item):
        if item.startswith("https://"):
            title = self.ytdl.extract_info(item, download=False)["title"]
            return {'source': item, 'title': title}
        search = VideosSearch(item, limit=1)
        return {
            'source': search.result()["result"][0]["link"],
            'title': search.result()["result"][0]["title"]
        }

    async def play_next(self):
        if len(self.music_queue) > 0:
            self.is_playing = True

            # get the first url
            m_url = self.music_queue[0][0]['source']

            # remove the first element as you are currently playing it
            self.music_queue.pop(0)
            loop = asyncio.get_running_loop()
            try:
                data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
                song = data['url']
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song, **self.FFMPEG_OPTIONS))
                self.vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))
            except Exception as e:
                print(f"Error playing song: {e}")
                self.is_playing = False
        else:
            self.is_playing = False

    # infinite loop checking 
    async def play_music(self, ctx):
        if len(self.music_queue) > 0:
            self.is_playing = True

            m_url = self.music_queue[0][0]['source']
            # try to connect to voice channel if you are not already connected
            if self.vc == None or not self.vc.is_connected():
                self.vc = await self.music_queue[0][1].connect()

                # in case we fail to connect
                if self.vc == None:
                    await ctx.send("```Could not connect to the voice channel```")
                    return
            else:
                await self.vc.move_to(self.music_queue[0][1])
            # remove the first element as you are currently playing it
            self.music_queue.pop(0)
            loop = asyncio.get_running_loop()
            try:
                data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
                song = data['url']
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song, **self.FFMPEG_OPTIONS))
                self.vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))
            except Exception as e:
                await ctx.send(f"Could not play the song. Error: {e}")
                print(f"Error playing song: {e}")
                self.is_playing = False
        else:
            self.is_playing = False

    @commands.command(name="play", aliases=["p", "playing"], help="Plays a selected song from youtube")
    async def play(self, ctx, *args):
        await self._play(ctx, " ".join(args))

    @app_commands.command(name="play", description="Plays a selected song from youtube")
    async def slash_play(self, interaction: discord.Interaction, *, query: str):
        await self._play(interaction, query)

    async def _play(self, ctx_or_interaction, query):
        if isinstance(ctx_or_interaction, commands.Context):
            send = ctx_or_interaction.send
            author = ctx_or_interaction.author
        else:
            send = ctx_or_interaction.response.send_message
            author = ctx_or_interaction.user

        try:
            voice_channel = author.voice.channel
        except AttributeError:
            await self.send_embed(ctx_or_interaction, "You need to connect to a voice channel first!", title="Error")
            return

        if self.is_paused:
            self.vc.resume()
        else:
            song = self.search_yt(query)
            if song is None:
                await self.send_embed(ctx_or_interaction, "Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format.", title="Error")
            else:
                if self.is_playing:
                    await self.send_embed(ctx_or_interaction, f"**#{len(self.music_queue) + 2} - '{song['title']}'** added to the queue")
                else:
                    await self.send_embed(ctx_or_interaction, f"**{song['title']}**")
                    self.music_queue.append([song, voice_channel])
                    if not self.is_playing:
                        await self.play_music(ctx_or_interaction)

    @commands.command(name="pause", help="Pauses the current song being played")
    async def pause(self, ctx, *args):
        await self._pause(ctx)

    @app_commands.command(name="pause", description="Pauses the current song being played")
    async def slash_pause(self, interaction: discord.Interaction):
        await self._pause(interaction)

    async def _pause(self, ctx_or_interaction):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
        elif self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()

    @commands.command(name="resume", aliases=["r"], help="Resumes playing with the discord bot")
    async def resume(self, ctx, *args):
        await self._resume(ctx)

    @app_commands.command(name="resume", description="Resumes playing with the discord bot")
    async def slash_resume(self, interaction: discord.Interaction):
        await self._resume(interaction)

    async def _resume(self, ctx_or_interaction):
        if self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()

    @commands.command(name="skip", aliases=["s"], help="Skips the current song being played")
    async def skip(self, ctx):
        await self._skip(ctx)

    @app_commands.command(name="skip", description="Skips the current song being played")
    async def slash_skip(self, interaction: discord.Interaction):
        await self._skip(interaction)

    async def _skip(self, ctx_or_interaction):
        if self.vc is not None and self.vc.is_playing():
            self.vc.stop()
            # try to play next in the queue if it exists
            await self.play_music(ctx_or_interaction)

    @commands.command(name="queue", aliases=["q"], help="Displays the current songs in queue")
    async def queue(self, ctx):
        await self._queue(ctx)

    @app_commands.command(name="queue", description="Displays the current songs in queue")
    async def slash_queue(self, interaction: discord.Interaction):
        await self._queue(interaction)

    async def _queue(self, ctx_or_interaction):
        retval = ""
        for i in range(len(self.music_queue)):
            retval += f"#{i + 1} - {self.music_queue[i][0]['title']}\n"

        if retval != "":
            await self.send_embed(ctx_or_interaction, f"**Queue:**\n{retval}")
        else:
            await self.send_embed(ctx_or_interaction, "No music in queue", title="Queue")

    @commands.command(name="clear", aliases=["c", "bin"], help="Stops the music and clears the queue")
    async def clear(self, ctx):
        await self._clear(ctx)

    @app_commands.command(name="clear", description="Stops the music and clears the queue")
    async def slash_clear(self, interaction: discord.Interaction):
        await self._clear(interaction)

    async def _clear(self, ctx_or_interaction):
        if self.vc is not None and self.is_playing:
            self.vc.stop()
        self.music_queue = []
        await self.send_embed(ctx_or_interaction, "Music queue cleared")

    @commands.command(name="stop", aliases=["disconnect", "l", "d"], help="Kick the bot from VC")
    async def dc(self, ctx):
        await self._dc(ctx)

    @app_commands.command(name="stop", description="Kick the bot from VC")
    async def slash_dc(self, interaction: discord.Interaction):
        await self._dc(interaction)

    async def _dc(self, ctx_or_interaction):
        self.is_playing = False
        self.is_paused = False
        await self.vc.disconnect()

    @commands.command(name="remove", help="Removes last song added to queue")
    async def re(self, ctx):
        await self._re(ctx)

    @app_commands.command(name="remove", description="Removes last song added to queue")
    async def slash_re(self, interaction: discord.Interaction):
        await self._re(interaction)

    async def _re(self, ctx_or_interaction):
        if len(self.music_queue) > 0:
            self.music_queue.pop()
            await self.send_embed(ctx_or_interaction, "Last song removed")
        else:
            await self.send_embed(ctx_or_interaction, "No songs in queue", title="Remove")

async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot))
