import asyncio
import datetime
import os
import re
from typing import Optional, Union

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import BucketType, CommandOnCooldown, CooldownMapping

from bot.constants import Channels, Guilds
from bot.exceptions import SnippetDoesNotExist, SnippetExists

IMAGE_URL_PATTERN = re.compile(
    r"(http(s?):)([/|.|\w|\s|-])*\.(?:jpg|jpeg|gif|png|svg)", re.IGNORECASE
)

DEFAULT_COOLDOWN = CooldownMapping.from_cooldown(1, 20, BucketType.channel)


class SnippetsGroup(app_commands.Group):
    """Group to manage all snippet commands"""

    @app_commands.command(name="create", description="Create a new snippet")
    async def create(
        self, interaction: discord.Integration, name: str, *, content: str
    ):
        pass

    @app_commands.command(name="delete", description="Delete a snippet by name or ID")
    async def delete(self, interaction: discord.Integration, name: str):
        pass

    @app_commands.command(name="edit", description="Edit a snippet by name or ID")
    async def edit(
        self, interaction: discord.Integration, new_name: Optional[str] = None
    ):
        pass

    @app_commands.command(name="list", description="List all snippets")
    async def list(self, interaction: discord.Integration):
        pass

    @app_commands.command(name="search", description="Search for a snippet by name")
    async def search(self, interaction: discord.Integration, name: str):
        pass

    @app_commands.command(name="info", description="Info about a snippet")
    async def info(self, interaction: discord.Integration, name: str):
        pass

    @app_commands.command(name="user", description="List all snippets by a user")
    async def user(self, interaction: discord.Integration, user: discord.User):
        pass

    @app_commands.command(name="leaderboard", description="Snippet leaderboard")
    async def leaderboard(self, interaction: discord.Integration):
        pass


class Snippets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_on_snippet_cooldown(self, msg: discord.Message):
        bucket = DEFAULT_COOLDOWN.get_bucket(msg)
        return bucket.update_rate_limit()

    async def snippet_exists(self, name: str):
        return await self.bot.snippets.find_one(
            {"name": {"$regex": f"^{name}$", "$options": "i"}}
        )

    async def snippet_not_found(self, ctx):
        return await ctx.send(
            f"Snipppet with this name does not exist.", reference=ctx.message
        )

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

        if not msg.content.startswith(";"):
            return

        title = msg.content[1:].strip()
        if not title:
            return

        # extract mentions and clean the command
        mentions_str = " ".join([m.mention for m in msg.mentions])
        cmd = re.sub(r"<@(!?)([0-9]*)>", "", title).strip().lower()

        # mongodb stuff
        snippet = await self.snippet_exists(cmd)
        if not snippet:
            raise SnippetDoesNotExist()

        # check for cooldown
        on_cooldown = await self.is_on_snippet_cooldown(msg)

        if on_cooldown:
            error_msg = (
                f"Please wait {on_cooldown:.2f}s before using this command again."
            )
            return await msg.channel.send(error_msg, reference=msg, delete_after=10.0)

        approved = snippet.get("approved", False)
        title = snippet.get("title", None)
        content = snippet.get("content", None)
        footer = snippet.get("footer", None)
        snippet_type = snippet.get("type", None)

        if not approved:
            return await msg.channel.send(
                "This snippet is not approved yet.", reference=msg
            )

        embed = discord.Embed(color=discord.Color.red())

        if snippet_type == "link":
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

        # increment uses by one
        await self.bot.snippets.update_one({"name": cmd}, {"$inc": {"uses": 1}})

    @commands.group(name="snippet", aliases=["s"], invoke_without_command=False)
    async def snippet(self, ctx):
        pass

    @snippet.command(name="add", aliases=["create"])
    async def snippet_add(self, ctx, name, *, content: Optional[str] = None):
        """Adds a snippet to the database."""

        # check if either the content is a text or there's an attachment
        if not content and not ctx.message.attachments:
            return await ctx.send(
                "Please add a text or an attachment.", reference=ctx.message
            )

        attachments = ctx.message.attachments
        if attachments and content:
            name = f"{name} {content}"
        # check if snippet already exists

        snippet = await self.snippet_exists(name)

        if snippet:
            raise SnippetExists()

        # get the CDN link from the attachment
        if attachments:

            # get the image file extension from the URL
            ext = ctx.message.attachments[0].url.split(".")[-1]

            # create temp folder if it doesn't exist
            if not os.path.exists("./temp"):
                os.makedirs("./temp")

            await ctx.message.attachments[0].save(fp=f"./temp/{name}.{ext}")
            storage_msg = await self.bot.get_channel(Channels.storage).send(
                file=discord.File(f"./temp/{name}.{ext}")
            )
            storage_id = storage_msg.attachments[0].id

            content = storage_msg.attachments[0].url
            snippet_type = "link"

        else:
            content = content.strip()
            snippet_type = "text"
            storage_id = None

        # add the snippet
        await self.bot.snippets.insert_one(
            {
                "name": name.strip().lower(),
                "type": snippet_type,
                "content": content,
                "approved": True,
                "title": None,
                "footer": None,
                "created_at": datetime.datetime.utcnow(),
                "owner_id": ctx.author.id,
                "storage_id": storage_id,
            }
        )

        await ctx.send("Snippet added successfully.", reference=ctx.message)

    @snippet.command(name="info")
    async def snippet_info(self, ctx, *, name: str):
        """Shows information about a snippet."""

        snippet = await self.snippet_exists(name)
        if not snippet:
            raise SnippetDoesNotExist()

        snippet_type = snippet.get("type", None)

        embed = discord.Embed(color=discord.Color.red())
        embed.title = snippet.get("name")
        if snippet_type == "link":
            embed.set_image(url=snippet.get("content"))
        else:
            embed.description = snippet.get("content")

        # get member
        member = ctx.guild.get_member(snippet.get("owner_id"))
        if member:
            embed.add_field(name="Owner", value=member.mention)
        else:
            embed.add_field(name="Owner", value=snippet.get("owner_id"))

        # uses
        embed.add_field(name="Uses", value=snippet.get("uses", 0))

        embed.add_field(name="Approved", value=snippet.get("approved"))

        embed.add_field(
            name="Created at",
            value=snippet.get("created_at").strftime("%d/%m/%Y %H:%M:%S"),
        )

        footer = snippet.get("footer", None)
        if footer:
            embed.set_footer(text=footer)

        await ctx.send(embed=embed, reference=ctx.message)

    @snippet.command(name="leaderboard")
    async def snippet_leaderboard(self, ctx):
        """Shows the snippet leaderboard."""

        snippets = (
            await self.bot.snippets.find({}).sort("uses", -1).limit(10).to_list(None)
        )

        embed = discord.Embed(color=discord.Color.red())
        embed.title = "Snippet leaderboard"

        for i, snippet in enumerate(snippets):
            embed.add_field(
                name=f'{i + 1}. {snippet.get("name")}',
                value=f"Uses: {snippet.get('uses', 0)}",
            )

        await ctx.send(embed=embed, reference=ctx.message)

    @snippet.command(name="search", aliases=["find"])
    async def snippet_search(self, ctx, *, query: str):
        """Searches for a snippet."""

        # fuzzy search for the snippet
        snippets = await self.bot.snippets.find(
            {"name": {"$regex": query, "$options": "i"}}
        ).to_list(None)

        if not snippets:
            return await ctx.send("No snippets found.", reference=ctx.message)

        embed = discord.Embed(color=discord.Color.red())
        embed.title = "Search results"

        # send top 10 results
        for i, snippet in enumerate(snippets[:10]):
            embed.add_field(
                name=f'{i + 1}. {snippet.get("name")}',
                value=f"Uses: {snippet.get('uses', 0)}",
            )

        await ctx.send(embed=embed, reference=ctx.message)

    @snippet.command(name="user")
    async def snippet_user(self, ctx, *, user: Union[discord.Member, discord.User]):
        """Shows a user's snippets."""

        # top 10 results
        snippets = (
            await self.bot.snippets.find({"owner_id": user.id})
            .sort("uses", -1)
            .limit(10)
            .to_list(None)
        )

        if not snippets:
            return await ctx.send("No snippets found.", reference=ctx.message)

        embed = discord.Embed(color=discord.Color.red())
        embed.title = f"{user}'s snippets"

        for i, snippet in enumerate(snippets):
            embed.add_field(
                name=f'{i + 1}. {snippet.get("name")}',
                value=f"Uses: {snippet.get('uses', 0)}",
            )

        await ctx.send(embed=embed, reference=ctx.message)

    @snippet.command(name="approve")
    @commands.has_any_role("Mod", "Staff")
    async def snippet_approve(self, ctx, *, name: str):
        """Approves a snippet."""

        snippet = await self.snippet_exists(name)
        if not snippet:
            raise SnippetDoesNotExist()

        await self.bot.snippets.update_one({"name": name}, {"$set": {"approved": True}})
        await ctx.send("Snippet approved successfully.", reference=ctx.message)

    @snippet.command(name="unapprove")
    @commands.has_any_role("Mod", "Staff")
    async def snippet_unapprove(self, ctx, *, name: str):
        """Unapproves a snippet."""

        snippet = await self.snippet_exists(name)
        if not snippet:
            raise SnippetDoesNotExist()

        await self.bot.snippets.update_one(
            {"name": name}, {"$set": {"approved": False}}
        )
        await ctx.send("Snippet unapproved successfully.", reference=ctx.message)

    @snippet.command(name="delete", aliases=["remove"])
    @commands.has_any_role("Mod", "Staff")
    async def snippet_delete(self, ctx, *, name: str):
        """Deletes a snippet."""

        snippet = await self.snippet_exists(name)
        if not snippet:
            raise SnippetDoesNotExist()

        await self.bot.snippets.delete_one({"name": name})
        await ctx.send("Snippet deleted successfully.", reference=ctx.message)


async def setup(bot):
    await bot.add_cog(Snippets(bot))
