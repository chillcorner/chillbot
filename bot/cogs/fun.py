import re
from typing import Optional
import random
import asyncio 

import discord
from discord.ext import commands
from discord.ext.commands import BucketType, CommandOnCooldown, CooldownMapping

from bot.cogs.utils import time
from bot.constants import Channels, Roles, Whitelists

fixed_nicks = {999177926903869520: "killjoy", 982097011434201108: "bharat"}


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if after.id in fixed_nicks:
            fixed_nick = fixed_nicks.get(after.id)
            if not after.display_name.lower().startswith(fixed_nick.lower()):
                try:
                    await after.send(f"You aren't allowed to change your nickname.")
                except Exception as e:
                    raise e

                try:
                    await after.edit(nick=fixed_nick)
                except Exception as e:
                    raise e

    @commands.command()
    @commands.is_owner()
    async def sn(self, ctx, minutes: int):
        if not ctx.guild:
            await ctx.send("This command can only be used in a server!")
            return

        # Ensure the user has permission to change nicknames
        if not ctx.author.guild_permissions.manage_nicknames:
            await ctx.send("You do not have permission to change nicknames!")
            return

        # Fetch the last 25 messages
        messages = [msg async for msg in ctx.channel.history(limit=25)]

        # Get unique authors (excluding the bot)
        authors = list(
            {message.author for message in messages if not message.author.bot}
        )

        if len(authors) < 2:  # We need at least two members to shuffle
            await ctx.send("Not enough unique members to shuffle!")
            return

        # Backup their nicknames and shuffle
        original_nicks = {}
        for author in authors:
            original_nicks[author.id] = author.nick

        shuffled_nicks = list(original_nicks.values())
        random.shuffle(shuffled_nicks)

        for author, new_nick in zip(authors, shuffled_nicks):
            try:
                await author.edit(nick=new_nick)
            except discord.Forbidden:
                print(
                    f"Couldn't change the nickname for {author.name} due to missing permissions."
                )
            except discord.HTTPException as e:
                print(f"Error while changing the nickname for {author.name}: {e}")

        # Wait for the specified time, then revert the nicknames
        await asyncio.sleep(minutes * 60)

        for author in authors:
            try:
                await author.edit(nick=original_nicks[author.id])
            except discord.Forbidden:
                pass  # Silently pass if there's a permission issue upon reverting
            except discord.HTTPException:
                pass


async def setup(bot):
    await bot.add_cog(Fun(bot))
