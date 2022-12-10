import asyncio

import discord
from discord.ext import commands
from discord.utils import get
from discord.ext import tasks


from bot.constants import Channels, Guilds


class PreventRaids(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.new_members = []
        self.join_watcher.start()

    def cog_unload(self):
        self.join_watcher.cancel()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != Guilds.cc:
            # Only track CC members
            return
        self.new_members.append(member)

    @tasks.loop(seconds=3)
    async def join_watcher(self):
        await self.process_joins()

    @join_watcher.before_loop
    async def before_join_watcher(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

    async def process_joins(self):
        new_members_copy = self.new_members.copy()
        self.new_members.clear()

        if not len(new_members_copy) >= 5:
            # temporary welcome message
            if new_members_copy:
                cc = self.bot.get_guild(Guilds.cc)
                welcome_channel = cc.get_channel(636141709419479040)
                await welcome_channel.send(f"Welcome {', '.join([m.mention for m in new_members_copy])}")
            return

        for member in new_members_copy:
            try:
                await member.ban(reason="Potential raid")
            except discord.HTTPException as e:
                print("Failed to ban user:", e)

        staff_room = self.bot.get_channel(Channels.staff_room)
        if not staff_room:
            return
        await staff_room.send(f"Potential raid detected. Banned {len(new_members_copy)} accounts.")


async def setup(bot):
    await bot.add_cog(PreventRaids(bot))
