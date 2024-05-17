import requests
import random
import discord
from discord import app_commands
from discord.ext import commands

# Function to fetch top 100 posts from the past week
def fetch_top_posts(subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/top/.json?t=week&limit=100"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Error fetching data from Reddit: {response.status_code}")

    posts = response.json()['data']['children']
    return posts

# Function to get random post information
def get_random_post_info(posts, subreddit):
    random_post = random.choice(posts)['data']
    post_info = {
        "title": random_post['title'],
        "score": random_post['score'],
        "url": random_post['url'],
        "subreddit": subreddit,
        "author": random_post['author'],
        "created_utc": random_post['created_utc'],
    }
    return post_info

# Function to register the meme command with the bot
def register_memes(bot: commands.Bot):
    @bot.tree.command(name="meme")
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
            post_info = get_random_post_info(posts, subreddit)

            embed = discord.Embed(title=post_info['title'], url=post_info['url'])
            embed.add_field(name="Score", value=post_info['score'])
            embed.add_field(name="Subreddit", value=post_info['subreddit'])
            embed.add_field(name="Author", value=post_info['author'])

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}")

