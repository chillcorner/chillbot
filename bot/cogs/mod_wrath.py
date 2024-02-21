from discord.ext import tasks, commands
import matplotlib.pyplot as plt
import datetime

class ModWrath(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.update_graphs.start()

    def cog_unload(self):
        self.update_graphs.cancel()

    @tasks.loop(minutes=10)
    async def update_graphs(self):
        # Generate the graphs using the data from MongoDB
        # Send to Discord channel


async def setup(bot):
    await bot.add_cog(ModWrath(bot))