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
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    _GIT_PULL_REGEX = re.compile(r'\s*(?P<filename>.+?)\s*\|\s*[0-9]+\s*[+-]+')

    def find_modules_from_git(self, output):
        files = self._GIT_PULL_REGEX.findall(output)
        ret = []
        for file in files:
            root, ext = os.path.splitext(file)
            if ext != '.py':
                continue

            if root.startswith('bot/'):
                # A submodule is a directory inside the main cog directory for
                # my purposes.
                dir_count = root.count('/')
                if dir_count == 2 and "/cogs" in root:
                    _ret = 1
                elif dir_count - 1 == 0:
                    _ret = 0

                else:
                    _ret = 0
                ret.append((_ret, root.replace('/', '.')))

        # For reload order, the submodules should be reloaded first
        ret.sort(reverse=True)
        return ret

    @commands.command()
    @commands.is_owner()
    async def pull(self, ctx):        
        """Pulls the latest changes from the repo.""" 

        unused_var = 25
       
        async with ctx.typing():
            stdout, stderr = await self.run_process('git pull')
            print("stdout", stdout)

        # progress and stuff is redirected to stderr in git pull
        # however, things like "fast forward" and files
        # along with the text "already up-to-date" are in stdout

        if 'Already up to date.' in stdout:
            return await ctx.send(f"Already up to date.")

        print(stdout)
        print()

        modules = self.find_modules_from_git(stdout)
        # mods_text = '\n'.join(f'{index}. `{module}`' for index, (_, module) in enumerate(modules, start=1))

        # prompt_text = f'This will update the following modules, are you sure?\n{mods_text}'
        # confirm = await ctx.prompt(prompt_text, reacquire=False)
        # if not confirm:
        #     return await ctx.send('Aborting.')
        print("Modules", modules)

        statuses = []
        agree = '\u2705'
        disagree = '\u274c'
        
       

        for is_module, module in modules:
            if is_module == 1:
                try:
                    self.reload_or_load_extension(module)
                    print(f"Reloaded a cog module: {module}")
                except commands.ExtensionError:
                    statuses.append((disagree, module))
                else:
                    statuses.append((agree, module))

            else:
                try:
                    actual_module = sys.modules[module]
                except KeyError:
                    statuses.append((disagree, module))
                else:
                    try:
                        importlib.reload(actual_module)

                        print(f'Reloaded a non-cog module {actual_module}')
                    except Exception as e:
                        statuses.append((disagree, module))
                        raise e
                    else:
                        statuses.append((agree, module))

        modules_ = '\n'.join(
            f'{status}: `{module}`' for status, module in statuses)
        await ctx.send(f"Reloaded the following modules:\n{modules_}")




    @commands.command()
    @commands.is_owner()
    async def load(self, ctx, *, module: str):
        """Loads a module."""
        try:
            await self.bot.load_extension(module)
        except Exception as e:
            await ctx.send(f'```py {type(e).__name__}: {e}```')
        else:
            await ctx.send('\u2705')


    @commands.command()
    @commands.is_owner()
    async def unload(self, ctx, *, module: str):
        """Unloads a module."""
        try:
            await self.bot.unload_extension(module)
        except Exception as e:
            await ctx.send(f'```py {type(e).__name__}: {e}```')
        else:
            await ctx.send('\u2705')

        
    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx, *, module: str):
        """Reloads a module."""
        try:
            await self.bot.reload_extension(module)
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


        