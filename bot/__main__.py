import asyncio
from dotenv import load_dotenv


from bot.bot import run_bot

load_dotenv()

asyncio.run(run_bot())
