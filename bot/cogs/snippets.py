import re
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

    @snippet.command(name="add")
    @commands.is_owner()
    async def snippet_add(self, ctx, *, unique_name: str):
        """Add a snippet"""
        ref = ctx.message.reference
        if not ref:
            return
        if not ref.cached_message:
            return await ctx.send("No message found in bot cache")
        if not ref.attachments:
            return await ctx.send("No image attached.")

        url = ref.attachments[0].url
        if re.match(IMAGE_URL_PATTERN, url):
            storage_channel = self.bot.get_channel(Channels.storage)
            msg = await storage_channel.send(url)

            if msg.attachments:
                url = msg.attachments[0].url
            else:
                return await ctx.send(f"Couldn't upload the file.")

            try:
                await self.bot.pool.execute("""INSERT INTO snippets(name, approved, title, description, footer, owner_id, storage_id)
                                        VALUES($1, $2, $3, $4, $5, $6, $7)""",
                                            unique_name, True, None, url, None, ctx.author.id, msg.id)
            except Exception as e:
                return await ctx.send(f"I couldn't add the snippet: {e}")

            await ctx.send(f"Snippet {unique_name} added.")


async def setup(bot):
    await bot.add_cog(Snippets(bot))
