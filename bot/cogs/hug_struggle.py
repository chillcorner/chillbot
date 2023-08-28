import discord
from discord.ext import commands


class LockChannelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lock_emoji_id = 1062941796881154128
        self.target_emoji_id = 564512560355737600
        self.target_count = 5
        self.locked_channels = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if (
            str(self.lock_emoji_id) in message.content
            and message.author.id == 982097011434201108
        ):
            await message.channel.set_permissions(
                message.guild.default_role, send_messages=False
            )
            self.locked_channels[message.channel.id] = message.id
            lock_emoji = self.bot.get_emoji(self.lock_emoji_id)
            target_emoji = self.bot.get_emoji(self.target_emoji_id)
            await message.add_reaction(target_emoji)

            msg = await message.channel.send(
                f"||Channel has been locked! Add {self.target_count} {target_emoji} reactions to unlock.||",
                delete_after=100,
            )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if (
            payload.emoji.id == self.target_emoji_id
            and payload.channel_id in self.locked_channels
        ):

            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                return

            message = await channel.fetch_message(self.locked_channels[channel.id])
            if not message:
                return

            reactions = [
                reaction
                for reaction in message.reactions
                if reaction.emoji.id == self.target_emoji_id
            ]

            if reactions:
                if reactions[0].count > self.target_count:
                    await channel.set_permissions(
                        channel.guild.default_role, send_messages=True,
                        embed_links=False,
                        attach_files=False,
                    )
                    await channel.send(f"Channel has been unlocked!")
                    del self.locked_channels[payload.channel_id]


async def setup(bot):
    await bot.add_cog(LockChannelCog(bot))
