import re
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import BucketType, CommandOnCooldown, CooldownMapping

from bot.cogs.utils import time
from bot.constants import Channels, Roles, Whitelists

DEFAULT_COOLDOWN = CooldownMapping.from_cooldown(1, 60, BucketType.member)
IMAGE_LINK_REGEX = re.compile(
    r"(http(s?):)([/|.|\w|\s|-])*\.(?:jpg|jpeg|gif|png|svg)", re.IGNORECASE
)


async def apply_general_cooldown(msg):

    # ignore rate limits for mods
    if Roles.moderators in [r.id for r in msg.author.roles]:
        return

    bucket = DEFAULT_COOLDOWN.get_bucket(msg)
    retry_after = bucket.update_rate_limit()
    if retry_after:
        try:
            await msg.delete(reason="On general image cooldown")
            await msg.author.send(
                f"Please wait {retry_after:.2f}s before posting another image in {msg.channel.mention}."
            )
        except discord.HTTPException:
            pass


async def delete_videos_in_general(msg):
    if msg.channel.id != Channels.general:
        return

    if msg.attachments:
        return

    if msg.content.startswith("https://"):
        await msg.delete()


async def handle_media_only_channel_content(msg):
    if msg.attachments:
        return
    if msg.channel.type == discord.Thread:
        return

    # delete if message type is default or reply
    if any(
        msg.type == t for t in (discord.MessageType.default, discord.MessageType.reply)
    ):
        try:
            await msg.delete()
            await msg.author.send(
                "Please create a thread and post your reply there instead of directly replying to this channel."
            )
        except discord.HTTPException:
            pass  # Ignore if user has DMs disabled or message is already gone


class Duration(time.ShortTime):
    def __init__(self, argument, *, now=None):
        super().__init__(argument, now=now)
        duration = self.dt - now
        if duration.days > 28:
            raise commands.BadArgument(
                "That's a lot of time! You can only set timeout for up to 28 days."
            )

        elif duration.days == 0 and duration.seconds < 300:
            raise commands.BadArgument(
                "You can only set timeout for at least 5 minutes."
            )


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        if msg.guild is None:
            return

        # check for cooldown
        if msg.channel.id == Channels.general:
            # check if msg has attachments or contains image link
            if msg.attachments or IMAGE_LINK_REGEX.search(msg.content):
                await apply_general_cooldown(msg)

        if msg.channel.id in Whitelists.media_channels:
            await handle_media_only_channel_content(msg)

            if msg.attachments:
                # auto add default comment thread
                await msg.channel.create_thread(
                    name=f"💬 {msg.author.display_name}'s post comments", message=msg
                )

    @commands.group(invoke_without_command=False, hidden=True)
    @commands.is_owner()
    async def ac(self, ctx):
        """Commands for managing private channel access."""
        pass

    @ac.command(name='add')
    async def add_to_ac(self, ctx, members: commands.Greedy[discord.Member]):
        """Assigns the special role to the given members, allowing them to access the private channel."""
        await ctx.message.delete()

        role = ctx.guild.get_role(Roles.adults_access)
        channel = ctx.guild.get_channel(Channels.adults_chat)

        assigned = []
        for m in members:
            if role in m.roles:
                continue

            await m.add_roles(role)
            assigned.append(m)

        await channel.send(f"You have been added to this channel, {', '.join(m.mention for m in assigned)}!")

    @ac.command(name='remove')
    async def remove_from_ac(self, ctx, members: commands.Greedy[discord.Member]):
        """Removes the special role from the given members, removing their access to the private channel."""
        await ctx.message.delete()

        role = ctx.guild.get_role(Roles.adults_access)
        channel = ctx.guild.get_channel(Channels.adults_chat)

        removed = []
        for m in members:
            if role not in m.roles:
                continue

            await m.remove_roles(role)
            removed.append(m)

        await channel.send(f"Removed {len(removed)} member(s) from this channel!")

    @commands.command(aliases=["t"])
    @commands.has_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: commands.Context,
        members: commands.Greedy[discord.Member],
        duration: Duration,
        *,
        reason: str,
    ):
        """Timeout a list of members for a certain amount of time. Example: !t @user1 @user2 1h spam"""
        for m in members:
            await m.timeout(duration.dt, reason=reason)

    @commands.command(aliases=["st"])
    async def self_timeout(
        self, ctx: commands.Context, duration: Duration, *, reason: Optional[str]
    ):
        """Timeout yourself from 5 minutes to 28 days. Example: !st 2h study"""

        await ctx.author.timeout(duration.dt, reason=reason)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
