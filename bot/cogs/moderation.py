
import discord
from discord.ext import commands
from typing import Optional

from bot.cogs.utils import time
from bot.constants import Channels, Whitelists


async def handle_media_only_channel_content(msg):
    if msg.attachments:
        return
    if isinstance(msg.channel, discord.Thread):
        return

    # delete if message type is default or reply
    if any(isinstance(msg, _t) for _t in (discord.MessageType.default, discord.MessageType.reply):
        try:
            await msg.delete()
            await msg.author.send("Please create a thread and post your reply there instead of directly replying to this channel.")
        except discord.HTTPException:
            pass  # Ignore if user has DMs disabled or message is already gone


class Duration(time.ShortTime):
    def __init__(self, argument, *, now=None):
        super().__init__(argument, now=now)
        duration = self.dt - now
        if duration.days > 28:
            raise commands.BadArgument(
                "That's a lot of time! You can only set timeout for up to 28 days.")

        elif duration.days == 0 and duration.seconds < 300:
            raise commands.BadArgument(
                "You can only set timeout for at least 5 minutes.")


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        if msg.guild is None:
            return

        if msg.channel.id in Whitelists.media_channels:
            await handle_media_only_channel_content(msg)

            if msg.attachments:
                # auto add default comment thread
                await msg.channel.create_thread(name=f"💬 {msg.author.display_name}'s post comments", message=msg)

    @commands.command(aliases=['t'])
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, members: commands.Greedy[discord.Member], duration: Duration, *, reason: str):
        """Timeout a list of members for a certain amount of time. Example: !t @user1 @user2 1h spam"""
        for m in members:
            await m.timeout(duration.dt, reason=reason)

    @commands.command(aliases=['st'])
    async def self_timeout(self, ctx: commands.Context, duration: Duration, *, reason: Optional[str]):
        """Timeout yourself from 5 minutes to 28 days. Example: !st 2h study"""

        await ctx.author.timeout(duration.dt, reason=reason)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
