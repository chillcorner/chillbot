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


        # mongodb stuff
        collection = self.bot.db.snippets
        snippet = await collection.find_one({'name': cmd})
        if not snippet:
            return
        

        # check for cooldown
        on_cooldown = await self.is_on_snippet_cooldown(msg)
        
        if on_cooldown:
            error_msg = f"Please wait {on_cooldown:.2f}s before using this command again."   
            return await msg.channel.send(error_msg, reference=msg, delete_after=10.0)     

        approved = snippet.get('approved', False)
        title = snippet.get('title', None)
        content = snippet.get('content', None)
        footer = snippet.get('footer', None)
        snippet_type = snippet.get('type', None)
        

        if not approved:
            return await msg.channel.send("This snippet is not approved yet.")

        embed = discord.Embed(color=discord.Color.red())

        if snippet_type == 'image':
            embed.set_image(url=content)
            embed.title = title if title else None
        else:
            # textual snippet
            embed.title = title
            embed.description = content

        if footer:
            embed.set_footer(text=footer)

        ref = msg.reference if msg.reference else msg

        await msg.channel.send(content=mentions_str, reference=ref, embed=embed)


async def setup(bot):
    await bot.add_cog(Snippets(bot))
