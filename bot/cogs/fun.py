import re
from typing import Optional
import random
import asyncio
import time
from io import BytesIO

import discord
from discord.ext import commands, tasks
from discord.ext.commands import BucketType, CommandOnCooldown, CooldownMapping

from bot.constants import Channels, Roles, Whitelists


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.change_role_color.start()

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        if not msg.guild:
            return

        role = msg.guild.get_role(1146271394280255498)
        if role in msg.author.roles:
            return

        try:
            await msg.author.add_roles(role)
            cat_emoji = self.bot.get_emoji(564512595445284875)
            await msg.add_reaction(cat_emoji)
        except discord.HTTPException as e:
            print(e)

    # every 2 mins change role color
    @tasks.loop(minutes=1)
    async def change_role_color(self):
        guild = self.bot.get_guild(444470893599784960)
        role = guild.get_role(1146271394280255498)
        colors = [
            discord.Color.red(),
            discord.Color.orange(),
            discord.Color.gold(),
            discord.Color.green(),
            discord.Color.blue(),
            discord.Color.purple(),
        ]

        # change role image to random cat emoji image
        cat_emojis = [e for e in self.bot.emojis if "cat" in e.name]

        cat_emoji = random.choice(cat_emojis)

        img_bytes = await cat_emoji.url.read()

        await role.edit(color=random.choice(colors), display_icon=img_bytes)


async def setup(bot):
    await bot.add_cog(Fun(bot))
