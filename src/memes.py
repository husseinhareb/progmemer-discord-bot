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

# Initialize the Reddit instance using praw
reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID,
                     client_secret=REDDIT_CLIENT_SECRET,
                     user_agent=REDDIT_USER_AGENT)

sent_posts = set()  # Set to keep track of sent post IDs

def fetch_top_posts(subreddit_name):
    subreddit = reddit.subreddit(subreddit_name)
    # Get top 100 posts from the last week
    top_posts = list(subreddit.top(time_filter='week', limit=100))
    return top_posts

def get_unique_random_post_info(posts):
    # Filter out posts that have already been sent
    unsent_posts = [post for post in posts if post.id not in sent_posts]
    if not unsent_posts:
        return None  # If all posts have been sent, return None

    random_post = random.choice(unsent_posts)
    post_info = {
        "id": random_post.id,
        "title": random_post.title,
        "score": random_post.score,
        "url": random_post.url,
        "subreddit": random_post.subreddit.display_name,
        "author": str(random_post.author),
        "created_utc": random_post.created_utc,
        "image_url": random_post.url if random_post.url.endswith(('jpg', 'jpeg', 'png', 'gif')) else None
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
            posts = await bot.loop.run_in_executor(None, fetch_top_posts, subreddit)
            post_info = get_unique_random_post_info(posts)

            if post_info is None:
                await interaction.response.send_message("No new posts available at the moment. Please try again later.")
                return

            embed = discord.Embed(title=post_info['title'], url=post_info['url'])
            embed.add_field(name="Score", value=post_info['score'])
            embed.add_field(name="Subreddit", value=post_info['subreddit'])
            embed.add_field(name="Author", value=post_info['author'])

            if post_info['image_url']:
                embed.set_image(url=post_info['image_url'])

            await interaction.response.send_message(embed=embed)

            # Add the post ID to the set of sent posts
            sent_posts.add(post_info['id'])

        except discord.errors.NotFound:
            print(f"Failed to respond to interaction: {e}")
        except discord.errors.HTTPException as e:
            print(f"HTTP exception occurred: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)