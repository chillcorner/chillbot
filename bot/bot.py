import asyncio
import datetime as dt
import logging
import sys
import traceback
import asyncpg
import aiohttp

import discord

from discord.ext import commands
from discord.utils import get

from bot.constants import Bot, Database


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.messages = True
intents.typing = True
intents.presences = True

# extensions to load
bot_extensions = [
    'cogs.raids',
    'cogs.openai',
    'cogs.verification',
    'cogs.moderation',
    'cogs.snippets',

]

# logging stuff
logging.getLogger(__name__).setLevel(logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s: %(message)s')

handler = logging.FileHandler(
    filename='chillbot.log', encoding='utf-8', mode='a')
handler.setFormatter(formatter)

stream = logging.StreamHandler(stream=sys.stdout)
stream.setFormatter(formatter)

logging.getLogger().addHandler(handler)
logging.getLogger().addHandler(stream)


def get_prefix(bot, message):
    """A callable Prefix for our bot."""

    prefixes = ["!"]
    return commands.when_mentioned_or(*prefixes)(bot, message)


async def run_bot():
    description = Bot.description

    # bot params
    allowed_mentions = discord.AllowedMentions(
        everyone=False,
        users=True,
        roles=False

    )

    default_status = discord.Status.dnd

    default_activity = discord.Activity(
        type=discord.ActivityType.listening,
        name="mods"
    )

    bot = ChillBot(
        intents=intents,
        command_prefix="!",
        description=description,
        heartbeat_timeout=150.0,
        case_insensitive=True,
        allowed_mentions=allowed_mentions,
        status=default_status,
        activity=default_activity

    )

    try:

        async with bot:
            for n, ext in enumerate(bot_extensions):
                await bot.load_extension(f"bot.{ext}")
                print(f"{n + 1}. Loaded extension: [{ext}]")

            pool = await asyncpg.create_pool(Database.pgsql_string)
            bot.pool = pool

            await bot.start(Bot.token, reconnect=True)

    except KeyboardInterrupt:
        await bot.logout()


class ChillBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = dt.datetime.now()

    async def on_command_error(self, ctx, exception):
        if isinstance(exception, commands.CommandNotFound):
            return

        elif isinstance(exception, commands.BadArgument):
            await ctx.send(exception)

        elif isinstance(exception, commands.UserInputError):
            ctx.command.reset_cooldown(ctx)

        elif isinstance(exception, commands.CommandOnCooldown):
            await ctx.send(exception)

        elif isinstance(exception, asyncio.TimeoutError):
            return

        elif isinstance(exception, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')

        elif isinstance(exception, commands.DisabledCommand):
            await ctx.author.send('Sorry. This command is disabled and cannot be used.')

        elif isinstance(exception, commands.CommandInvokeError):
            original = exception.original
            if not isinstance(original, discord.HTTPException):
                print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
                traceback.print_tb(original.__traceback__)
                print(f'{original.__class__.__name__}: {original}',
                      file=sys.stderr)
            else:
                if isinstance(original, discord.NotFound):
                    print(f'{original.__class__.__name__}: {original}',
                          file=sys.stderr)
        elif isinstance(exception, commands.ArgumentParsingError):
            await ctx.send(exception)

        elif isinstance(exception, discord.Forbidden):
            print(exception, exception.original.__traceback__)

        else:
            raise exception
