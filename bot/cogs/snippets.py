from io import BytesIO
import re
import aiohttp
import discord
from discord.ext import commands

from bot.constants import Channels

IMAGE_URL_PATTERN = re.compile(
    r'(http(s?):)([/|.|\w|\s|-])*\.(?:jpg|jpeg|gif|png|svg)', re.IGNORECASE)


class Snippets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.snippets_cd = commands.CooldownMapping.from_cooldown(
            1, 30, commands.BucketType.channel)

    async def is_on_snippet_cooldown(self, msg):
        # channel specific cooldown
        bucket = self.snippets_cd.get_bucket(msg)
        return bucket.update_rate_limit()

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        if not msg.content.startswith(';'):
            return

        title = msg.content[1:].strip()
        if not title:
            return

        # extract mentions and clean the command
        mentions_str = " ".join([m.mention for m in msg.mentions])
        cmd = re.sub(r'<@(!?)([0-9]*)>', '', title).strip()

        row = await self.bot.pool.fetchrow("""SELECT * FROM snippets WHERE name = $1""", cmd)
        if not row:
            return  # await msg.channel.send(f"Found nothing.")

        # check for cooldown
        on_cooldown = await self.is_on_snippet_cooldown(msg)
        if on_cooldown:
            cd_msg = f"This channel is on cooldown. Try again in {round(on_cooldown, 2)}s {msg.author.mention}"
            try:
                await msg.delete()
            except discord.NotFound:
                pass
            finally:
                return await msg.channel.send(cd_msg, delete_after=5.0)

        approved = row['approved']
        title = row['title']
        description = row['description']
        footer = row['footer']

        if not approved:
            return await msg.channel.send("This snippet is not approved yet.")

        embed = discord.Embed(color=discord.Color.red())
        if re.match(IMAGE_URL_PATTERN, description):
            embed.set_image(url=description)
            embed.title = title if title else None
        else:
            embed.title = title
            embed.description = description

        if footer:
            embed.set_footer(text=footer)

        # send snippet
        tmp_msg = await msg.channel.send(reference=msg, embed=embed)

    @commands.group(name="snippet", invoke_without_command=False)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def snippet(self, ctx):
        """Snippet commands"""
        pass


async def setup(bot):
    await bot.add_cog(Snippets(bot))
