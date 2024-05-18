import os
import random
import praw
import discord
from discord import app_commands
from discord.ext import commands

# Fetching Reddit API credentials from environment variables
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
USER_AGENT = os.getenv('USER_AGENT') 
REDDIT_USER_AGENT = f'MyDiscordBot/1.0 (by /u/{USER_AGENT})'

# Initialize the Reddit instance
reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID,
                     client_secret=REDDIT_CLIENT_SECRET,
                     user_agent=REDDIT_USER_AGENT)

def fetch_top_posts(subreddit_name):
    subreddit = reddit.subreddit(subreddit_name)
    # Get top 30 posts from the last week
    top_posts = list(subreddit.top(time_filter='week', limit=30))
    return top_posts

def get_random_post_info(posts):
    random_post = random.choice(posts)
    post_info = {
        "title": random_post.title,
        "score": random_post.score,
        "url": random_post.url,
        "subreddit": random_post.subreddit.display_name,
        "author": str(random_post.author),
        "created_utc": random_post.created_utc,
    }
    return post_info

# Function to register the meme command with the bot
def register_memes(bot: commands.Bot):
    @bot.tree.command(name="meme", description="Programming related memes (default: r/ProgrammerHumor)")
    @app_commands.describe(subreddit="Choose a subreddit (optional)")
    @app_commands.choices(subreddit=[
        app_commands.Choice(name="funny", value="funny"),
        app_commands.Choice(name="memes", value="memes"),
        app_commands.Choice(name="dankmemes", value="dankmemes"),
        app_commands.Choice(name="wholesomememes", value="wholesomememes"),
        app_commands.Choice(name="ProgrammerHumor", value="ProgrammerHumor"),
    ])
    async def meme(interaction: discord.Interaction, subreddit: str = "ProgrammerHumor"):
        try:
            posts = fetch_top_posts(subreddit)
            post_info = get_random_post_info(posts)

            embed = discord.Embed(title=post_info['title'], url=post_info['url'])
            embed.add_field(name="Score", value=post_info['score'])
            embed.add_field(name="Subreddit", value=post_info['subreddit'])
            embed.add_field(name="Author", value=post_info['author'])

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}")
