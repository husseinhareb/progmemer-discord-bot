# Progmemer
Progmemer is a Discord bot written in Python oriented for programmers.

It has the capabilities of sending jokes, memes, and playing music.

![progmemer-pfp](https://github.com/husseinhareb/progmemer-discord-bot/assets/88323940/b35c3141-dd31-462d-80e4-b87fdcea90d8)

## Commands 
The bot is still under development, more commands will be added..

### General (Slash Commands)
```
/say - Say something.
/hello - Greet the bot.
/roll - Rolls the dice.
/weather - Get weather details for a certain city.
/joke - Get a random joke. (Default category: Any, Optional: Programming, Dark, Misc)
/meme - Get a random post from any subreddit. (Default: r/ProgrammerHumor, Optional: funny, memes, dankmemes, wholesomememes...)
```
### Music (Slash & Prefix Commands)
```
/play - Plays a selected song from YouTube.
/pause - Pause the current song being played.
/resume - Resume the current song being paused.
/skip - Skips the current song being played.
/queue - Displays the current songs in the queue.
/stop - Stops playing music, clears the queue, and disconnects.
/lyrics - Shows lyrics for the current song.
```
### To-Do Tasks (Slash Commands)
```
/add - Add a task for today. The task will be assigned a default status of 'to-do'.
/list - List tasks for a specific date or today's tasks if no date is provided.
/update - Update the status of a task. Options include 'to-do', 'working on it', and 'completed'.
/remove - Remove a to-do task for today.
/edit - Edit a task description for today.
```
### Utility (Prefix Commands)
```
!help - Displays all available commands.
!prefix <new_prefix> - Changes the command prefix for this server (requires Manage Server permission).
!send_to_all <message> - Sends a message to all text channels in the server (Admin only).
```

## Getting Started
### Prerequisites
Create a `.env` file in the project root with the following variables:
```
TOKEN=your_discord_bot_token
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
USER_AGENT=your_reddit_username
WEATHER_API=your_openweathermap_api_key
```
You can obtain these from:
- Discord bot token: [Discord Developer Portal](https://discord.com/developers/applications)
- Reddit API credentials: [Reddit Apps](https://www.reddit.com/prefs/apps)
- Weather API key: [OpenWeatherMap](https://openweathermap.org/api)

### Running the bot
You can run the bot locally by:
```shell
  git clone https://github.com/husseinhareb/progmemer-discord-bot/

  cd progmemer-discord-bot

  pip install -r requirements.txt

  python3 main.py
```  
## Contributing

Contributions are welcome! If you'd like to contribute:

    Fork the repository.
    Create your branch: git checkout -b feature/YourFeature.
    Commit your changes: git commit -m 'Add some feature'.
    Push to the branch: git push origin feature/YourFeature.
    Submit a pull request.

## Licence

This project is licensed under the [MIT License](https://github.com/husseinhareb/progmemer-discord-bot/blob/main/LICENSE).

