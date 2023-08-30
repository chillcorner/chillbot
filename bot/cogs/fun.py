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

    async def on_cog_unload(self):
        self.change_role_color.cancel()

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

            # get random cat from https://cataas.com/cat and send it
            nick = msg.author.display_name
            async with self.bot.session.get(f"https://cataas.com/cat/cute/says/Hello {nick}") as r:
                if r.status == 200:
                    img_bytes = await r.read()
                    file = discord.File(BytesIO(img_bytes), filename="cat.png")
                    await msg.channel.send(file=file, reference=msg, mention_author=True, content="Hi", delete_after=8)
        except discord.HTTPException as e:
            print(e)

    # every 2 mins change role color
    @tasks.loop(minutes=5)
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
        cat_emojis = [e for e in guild.emojis if "cat" in e.name]

        cat_emoji = random.choice(cat_emojis)

        img_bytes = await cat_emoji.read()

        await role.edit(color=random.choice(colors), display_icon=img_bytes)


async def setup(bot):
    await bot.add_cog(Fun(bot))
