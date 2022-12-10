import asyncio

import discord
from discord.ext import commands
from discord.utils import get
from discord.ext import tasks


from bot.constants import Channels, Guilds


class Onboarding(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.new_members_queue = []
        self.join_watcher.start()

    def cog_unload(self):
        self.join_watcher.cancel()

    async def send_welcome_message(self, member: discord.Member):
        system_channel = member.guild.system_channel
        await system_channel.send(f"Welcome {member.mention}!")
        


    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != Guilds.cc:
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
        new_members = self.new_members_queue.copy()
        self.new_members_queue.clear()

        if not len(new_members) >= 5:
            for member in new_members:
                if not isinstance(member, discord.Member):                    
                    continue 
                await self.send_welcome_message(member)
                
            return

        for member in new_members:
            try:
                await member.ban(reason="Potential raid")
            except discord.HTTPException as e:
                print("Failed to ban user:", e)

        staff_room = self.bot.get_channel(Channels.staff_room)

        if not staff_room:
            return

        await staff_room.send(f"Potential raid detected. Banned {len(new_members)} accounts.")


async def setup(bot):
    await bot.add_cog(Onboarding(bot))
