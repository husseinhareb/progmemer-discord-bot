# Progmemer
Progmemer is a Discord bot written in Python oriented for programmers.

It has the capabilities of sending jokes, memes, and playing music.

![progmemer-pfp](https://github.com/husseinhareb/progmemer-discord-bot/assets/88323940/b35c3141-dd31-462d-80e4-b87fdcea90d8)

## Commands 
The bot is still under development, more commands will be addded..

### General
```
/say - Say something.
/hello - Greet the bot.
/roll - Rolls the dice.
/weather - Get weather details for a certain city.
/joke - Get a random joke. (Default category: Programming, Optional types: Dark, Any, Misc)
/meme - Get a programming-related meme. (Default subreddit: r/ProgrammerHumor, Optional subreddits: funny, memes, dankmemes, wholesomemes...)
```
### Music
```
/play - Plays a selected song from youtube.
/pause - Pause the current song being played.
/resume - Resume the current song being paused.
/skip - Skips teh current song being played.
/queue - Displays the current songs in the queue.
/remove - Removes the last song added to the queue.
/clear - Stops the music and clears the queue.
/stop - Kicks the bot from the voice channel.
```

## Getting Started
### Running the bot
You can run the bot localy by 
```shell
  git clone https://github.com/husseinhareb/progmemer-discord-bot/

  cd progmemer-discord-bot

  pip install -r requirements.txt

  python3 main.py
```
Adding to that you have to create your own bot [here](https://discord.com/developers/applications) and pass the correct bot TOKEN and other tokens as well([reddit](https://www.reddit.com/dev/api),[openweather](https://openweathermap.org/api]))  
## Contributing

Contributions are welcome! If you'd like to contribute:

    Fork the repository.
    Create your branch: git checkout -b feature/YourFeature.
    Commit your changes: git commit -m 'Add some feature'.
    Push to the branch: git push origin feature/YourFeature.
    Submit a pull request.

## Licence

This project is licensed under the [MIT License](https://github.com/husseinhareb/progmemer-discord-bot/blob/main/LICENSE).

