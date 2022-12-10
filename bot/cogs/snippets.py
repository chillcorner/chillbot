import re
import discord
from discord.ext import commands
from discord.ext.commands import BucketType, CooldownMapping, CommandOnCooldown

from bot.constants import Channels, Guilds

IMAGE_URL_PATTERN = re.compile(
    r'(http(s?):)([/|.|\w|\s|-])*\.(?:jpg|jpeg|gif|png|svg)', re.IGNORECASE)

DEFAULT_COOLDOWN = CooldownMapping.from_cooldown(1, 30, BucketType.channel)

class Snippets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot        

    async def is_on_snippet_cooldown(self, msg: discord.Message):        
        bucket = DEFAULT_COOLDOWN.get_bucket(msg)
        return bucket.update_rate_limit()

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        # ignore dms
        if not msg.guild:
            return
        
        # chill corner only
        if msg.guild.id != Guilds.cc:
            return
        

        if not msg.content.startswith(';'):
            return

        title = msg.content[1:].strip()
        if not title:
            return

        # extract mentions and clean the command
        mentions_str = " ".join([m.mention for m in msg.mentions])
        cmd = re.sub(r'<@(!?)([0-9]*)>', '', title).strip()


        query = """SELECT * FROM snippets WHERE name = $1"""
        row = await self.bot.pool.fetchrow(query, cmd)

        if not row:
            return

        # check for cooldown
        on_cooldown = await self.is_on_snippet_cooldown(msg)
        
        if on_cooldown:
            error_msg = f"Please wait {on_cooldown:.2f}s before using this command again."   
            return await msg.channel.send(error_msg, reference=msg, delete_after=10.0)     

        approved = row.get('approved', False)
        title = row.get('title', None)
        description = row.get('description', None)
        footer = row.get('footer', None)

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

        ref = msg.reference if msg.reference else msg

        await msg.channel.send(content=mentions_str, reference=ref, embed=embed)


async def setup(bot):
    await bot.add_cog(Snippets(bot))
