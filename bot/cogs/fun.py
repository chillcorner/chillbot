import re
from typing import Optional
import random
import asyncio
import time
from io import BytesIO
import aiohttp


import discord
from discord.ext import commands, tasks
from discord.ext.commands import BucketType, CommandOnCooldown, CooldownMapping

from bot.constants import Channels, Roles, Whitelists


SWITCHABLE_ROLES = {
    "Black Hole": {
        "color": discord.Color.from_rgb(8, 0, 13),
        "hoist": False,
        "mentionable": False,
        "icon": "https://cdn-icons-png.flaticon.com/512/1171/1171419.png",
    },
    "The North Star.": {
        "color": discord.Color.from_rgb(112, 0, 193),
        "hoist": False,
        "mentionable": False,
        "icon": "https://cdn.discordapp.com/role-icons/1173340939654287491/236b588ddef1bcdeaf4f99c4ad35e193.png",
    },
}


async def get_icon_bytes(icon_url: str) -> Optional[bytes]:
    async with aiohttp.ClientSession() as session:
        async with session.get(icon_url) as resp:
            if resp.status != 200:
                return None
            return await resp.read()


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.switch_roles_task = self.switch_roles.start()

    async def on_cog_unload(self):
        self.switch_roles_task.cancel()

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        if not msg.guild:
            return

    @tasks.loop(hours=2)
    async def switch_roles(self):
        guild = self.bot.get_guild(444470893599784960)
        role = guild.get_role(1173340939654287491)

        member = guild.get_member(1081727262191276044)

        while True:
            for role_name, role_data in SWITCHABLE_ROLES.items():
                # edit role
                icon_bytes = await get_icon_bytes(role_data["icon"])
                await role.edit(
                    name=role_name,
                    color=role_data["color"],
                    hoist=role_data["hoist"],
                    mentionable=role_data["mentionable"],
                    icon=icon_bytes,
                )

                # sleep for 2 mins
                await asyncio.sleep(60 * 2)


async def setup(bot):
    await bot.add_cog(Fun(bot))
