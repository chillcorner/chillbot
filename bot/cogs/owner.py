import asyncio
import importlib
import os
import re
import subprocess
import sys
from discord.ext import commands



class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run_process(self, command: str) -> list[str]:
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    _GIT_PULL_REGEX = re.compile(r'\s*(?P<filename>.+?)\s*\|\s*[0-9]+\s*[+-]+')
    
    def find_modules_from_git(self, output: str) -> list[tuple[int, str]]:
        files = self._GIT_PULL_REGEX.findall(output)
        ret: list[tuple[int, str]] = []
        for file in files:
            root, ext = os.path.splitext(file)
            if ext != '.py':
                continue

            if root.startswith('bot/cogs/'):
                # A submodule is a directory inside the main cog directory for
                # my purposes
                ret.append((root.count('/') - 2, root.replace('/', '.')))

        # For reload order, the submodules should be reloaded first
        ret.sort(reverse=True)
        return ret

    @commands.command()
    @commands.is_owner()
    async def pull(self, ctx):
        """Pulls the latest changes from the repo."""
        async with ctx.typing():
            stdout, stderr = await self.run_process('git pull')

        # progress and stuff is redirected to stderr in git pull
        # however, things like "fast forward" and files
        # along with the text "already up-to-date" are in stdout

        if stdout.startswith('Already up-to-date.'):
            return await ctx.send(stdout)

        modules = self.find_modules_from_git(stdout)        

        statuses = []
        for is_submodule, module in modules:
            if is_submodule:
                try:
                    actual_module = sys.modules[module]
                except KeyError:
                    statuses.append((ctx.tick(None), module))
                else:
                    try:
                        importlib.reload(actual_module)
                    except Exception as e:
                        statuses.append((ctx.tick(False), module))
                    else:
                        statuses.append((ctx.tick(True), module))
            else:
                try:
                    await self.reload_or_load_extension(module)
                except commands.ExtensionError:
                    statuses.append((ctx.tick(False), module))
                else:
                    statuses.append((ctx.tick(True), module))

        await ctx.send('\n'.join(f'{status}: `{module}`' for status, module in statuses))




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


        