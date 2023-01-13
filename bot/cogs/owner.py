from discord.ext import commands

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx, *, module: str):
        """Loads a module."""
        try:
            self.bot.load_extension(module)
        except Exception as e:
            await ctx.send(f'```py {type(e).__name__}: {e}```')
        else:
            await ctx.send('\u2705')


    @commands.command()
    @commands.is_owner()
    async def unload(self, ctx, *, module: str):
        """Unloads a module."""
        try:
            self.bot.unload_extension(module)
        except Exception as e:
            await ctx.send(f'```py {type(e).__name__}: {e}```')
        else:
            await ctx.send('\u2705')

        
    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx, *, module: str):
        """Reloads a module."""
        try:
            self.bot.reload_extension(module)
        except Exception as e:
            await ctx.send(f'```py {type(e).__name__}: {e}```')
        else:
            await ctx.send('\u2705')

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, ctx):
        """Shuts down the bot."""
        await ctx.send('Shutting down...')
        await self.bot.close()
        
        await self.bot.session.close()
        await self.bot.db.close()


async def setup(bot):
    await bot.add_cog(Owner(bot))


        