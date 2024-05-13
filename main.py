import discord
from discord import message

client = discord.Client()

@client.event
async def on_ready():
  print("We have logged in as {0.user}".format(client))

@client.event
async def on_message(message):
  if message.author == client.user:
    return

  if message.content.startswith("!hello"):
    await message.channel.send("Hello!")

  if message.content.startswith("!help"):
    await message.channel.send("This is a bot made")