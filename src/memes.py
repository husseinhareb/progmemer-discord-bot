import os
import random
import praw
import discord
from discord import app_commands
from discord.ext import commands
from collections import deque

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
USER_AGENT = os.getenv('USER_AGENT')
REDDIT_USER_AGENT = f'MyDiscordBot/1.0 (by /u/{USER_AGENT})'

reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID,
                     client_secret=REDDIT_CLIENT_SECRET,
                     user_agent=REDDIT_USER_AGENT)

sent_posts = deque(maxlen=1000)  # Use deque with max length for automatic cleanup

def fetch_top_posts(subreddit_name):
    subreddit = reddit.subreddit(subreddit_name)
    top_posts = list(subreddit.top(time_filter='month', limit=100))
    return top_posts

def get_unique_random_post_info(posts):
    unsent_posts = [post for post in posts if post.id not in sent_posts]
    if not unsent_posts:
        return None
    random_post = random.choice(unsent_posts)
    
    # Determine image URL - handle various Reddit image formats
    image_url = None
    if random_post.url.endswith(('jpg', 'jpeg', 'png', 'gif')):
        image_url = random_post.url
    elif hasattr(random_post, 'preview') and 'images' in random_post.preview:
        # Get the highest quality preview image
        image_url = random_post.preview['images'][0]['source']['url'].replace('&amp;', '&')
    
    post_info = {
        "id": random_post.id,
        "title": random_post.title,
        "score": random_post.score,
        "url": random_post.url,
        "subreddit": random_post.subreddit.display_name,
        "author": str(random_post.author),
        "created_utc": random_post.created_utc,
        "image_url": image_url,
        "nsfw": random_post.over_18
    }
    return post_info

# Popular subreddits for autocomplete suggestions
POPULAR_SUBREDDITS = [
    "ProgrammerHumor", "funny", "memes", "dankmemes", "wholesomememes",
    "aww", "pics", "gaming", "technews", "todayilearned",
    "Showerthoughts", "science", "technology", "EarthPorn", "space",
    "movies", "music", "books", "AskReddit", "explainlikeimfive"
]

def register_memes(bot: commands.Bot):
    async def subreddit_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocomplete function to suggest popular subreddits"""
        current_lower = current.lower().replace('r/', '')
        # Filter subreddits that match the current input
        matches = [sub for sub in POPULAR_SUBREDDITS if current_lower in sub.lower()]
        # Return up to 25 matches (Discord limit)
        return [app_commands.Choice(name=f"r/{sub}", value=sub) for sub in matches[:25]]
    
    @bot.tree.command(name="meme", description="Get a random post from any subreddit (default: r/ProgrammerHumor)")
    @app_commands.describe(subreddit="Type any subreddit name (e.g., 'funny', 'memes', 'aww')")
    @app_commands.autocomplete(subreddit=subreddit_autocomplete)
    async def meme(interaction: discord.Interaction, subreddit: str = "ProgrammerHumor"):
        # Clean the subreddit name (remove r/ prefix if present)
        subreddit = subreddit.strip().replace('r/', '')
        
        try:
            # Defer the response to prevent timeout for slow requests
            await interaction.response.defer()
            
            posts = await bot.loop.run_in_executor(None, fetch_top_posts, subreddit)
            
            if not posts:
                await interaction.followup.send(f"Could not find any posts in r/{subreddit}. Please check the subreddit name and try again.")
                return
                
            post_info = get_unique_random_post_info(posts)

            if post_info is None:
                await interaction.followup.send("No new posts available at the moment. Please try again later.")
                return

            # Set embed color based on NSFW status
            embed_color = discord.Color.red() if post_info.get('nsfw', False) else discord.Color.blue()
            embed = discord.Embed(title=post_info['title'], url=post_info['url'], color=embed_color)
            
            # Add NSFW warning if applicable
            if post_info.get('nsfw', False):
                embed.add_field(name="⚠️ NSFW", value="This post is marked as NSFW", inline=False)
            
            embed.add_field(name="Score", value=f"⬆️ {post_info['score']}", inline=True)
            embed.add_field(name="Subreddit", value=f"r/{post_info['subreddit']}", inline=True)
            embed.add_field(name="Author", value=f"u/{post_info['author']}", inline=True)

            if post_info['image_url']:
                embed.set_image(url=post_info['image_url'])

            # Mark the message as NSFW if the post is NSFW
            await interaction.followup.send(embed=embed)

            # Add post to deque (automatically removes oldest if at max capacity)
            sent_posts.append(post_info['id'])

        except Exception as e:
            error_message = str(e).lower()
            if 'redirect' in error_message or 'not found' in error_message or '404' in error_message:
                await interaction.followup.send(f"❌ Subreddit r/{subreddit} not found. Please check the spelling and try again.", ephemeral=True)
            elif 'private' in error_message or 'forbidden' in error_message:
                await interaction.followup.send(f"❌ r/{subreddit} is private or restricted. Try a different subreddit.", ephemeral=True)
            else:
                print(f"Error fetching from r/{subreddit}: {e}")
                await interaction.followup.send(f"❌ An error occurred while fetching from r/{subreddit}. Please try again.", ephemeral=True)
