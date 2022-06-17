# Chill Bot

It was originally called "Chill Corner" bot just like any generic branded custom bot. It had basic moderation, fun and utlity commands that helped run our server. Many members of our community prefer to call it "Chill bot" so I renamed it

It always used to be a private bot and I could never make it open-source due to ugly and unreadable code that had more runtime errors than comments. Now I'm starting over from the scratch and making it public on github so others can contribute. 

I plan to make this bot public one day or at least some parts of it. It's still a private bot with custom functionalities suited to only our server but I may include some features that can be used by other server owners.


# Running your own instance
You can currently add this bot to your server but it's recommended to run your own instance.
## Requirements:
1. Python 3.7 or earlier
2. Discord.py 2.0+
3. OpenAI token 

## Configuration
Navigate `config.yml` and replace any values as per your requirements. i.e. if you need to setup the verification system to your server, you need to replace category ID, role ID, server ID etc with your own IDs.

Don't put tokens in config.yml. Set them as environment variables.

## Deployment
You can use Heroku and it works fine with it. The bot doesn't require any external database or storage to function. It completely runs on the RAM as of now. You can host it on your local machine as well but you need to install Python 3.7+ and dependencies from requirements.txt file.

Use `pip install -r requirements.txt` command to install the dependencies.

## Starting the bot
Open your terminal/command prompt and use `python -m bot` in the main bot directory to run the bot. On successful startup, it'll show login confirmation.

## Disclaimer
You must read the ToS of OpenAI and not run bot publically without supervision. It's against their ToS to run the bot on chat platforms like discord where anyone can interact with the bot and potentially prompt it to generate dangerous/harmful content.
