import re
from typing import Optional

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
    async def on_member_update(before, after):
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

async def setup(bot):
    await bot.add_cog(Fun(bot))
