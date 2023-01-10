from typing import Union

import discord
from discord.ext import commands, tasks
from discord.ext.commands import Greedy

from bot.constants import Categories, Guilds, Roles


def is_modmail_category(ctx):
    """Check if the command is being run in a modmail channel."""
    return ctx.channel.category_id == Categories.modmail


def ticket_close_check(ctx):
    """Check if the same member or mod is running the command."""
    if not is_modmail_category(ctx):
        return False

    if ctx.channel.id == ctx.cog._cache.get(ctx.author.id):
        return True

    # has roles "Mod" or "Staff"
    return any(role.id in (Roles.mod, Roles.staff) for role in ctx.author.roles)


class TicketsCache:
    """A cache for tickets."""

    def __init__(self):
        self.tickets = {}

    def add(self, member_id: int, channel_id: int):
        """Add a ticket to the cache."""
        self.tickets[member_id] = channel_id

    def remove(self, member_id: int):
        """Remove a ticket from the cache."""
        del self.tickets[member_id]

    def remove_many(self, member_ids: list):
        """Remove multiple tickets from the cache."""
        for member_id in member_ids:
            del self.tickets[member_id]

    def get(self, member_id: int) -> Union[int, None]:
        """Get a ticket from the cache."""
        return self.tickets.get(member_id)

    def get_all(self) -> dict:
        """Get all tickets from the cache."""
        return self.tickets

    def get_members_by_ticket(self, channel_id: int) -> Union[int, None]:
        """Get a member from a ticket."""
        ret = []
        for member_id, channel in self.tickets.items():
            if channel == channel_id:
                ret.append(member_id)
        return ret

    def clear(self):
        """Clear the cache."""
        self.tickets.clear()

    # persistence methods
    async def save(self, collection):
        """Save the cache to the database."""
        for member_id, channel_id in self.tickets.items():
            await collection.update_one(
                {"member_id": member_id},
                {"$set": {"channel_id": channel_id}},
                upsert=True,
            )

    async def load(self, collection):
        """Load the cache from the database."""
        for d in await collection.find({}):
            self.tickets[d["member_id"]] = d["channel_id"]

    async def invalidate(self, collection):
        """Invalidate the cache by removing all tickets from the database."""
        await collection.delete_many({})
        self.clear()

    # magic methods

    def __getitem__(self, member_id: int):
        """Get a ticket from the cache."""
        return self.tickets[member_id]

    def __setitem__(self, member_id: int, channel_id: int):
        """Add a ticket to the cache."""
        self.tickets[member_id] = channel_id

    def __delitem__(self, member_id: int):
        """Remove a ticket from the cache."""
        del self.tickets[member_id]

    def __contains__(self, member_id: int):
        """Check if a ticket is in the cache."""
        return member_id in self.tickets

    def __len__(self):
        """Get the length of the cache."""
        return len(self.tickets)

    def __iter__(self):
        """Iterate over the cache."""
        return iter(self.tickets)

    def __repr__(self):
        return f"<TicketsCache tickets={self.tickets}>"


class Modmail(commands.Cog):
    """Modmail commands that don't involve DMs."""

    def __init__(self, bot):
        self.bot = bot
        self.tickets = {}
        self._cache = TicketsCache()

    async def send_new_ticket_message(
        self, ticket: discord.TextChannel, members: Greedy[discord.Member]
    ):
        """Send a new ticket message to the modmail channel."""

        main_member = members[0]
        mentions = [m.mention for m in members]

        embed = discord.Embed(color=discord.Color.blurple())
        embed.set_author(
            name=f"New ticket from {main_member}", icon_url=main_member.avatar_url
        )
        embed.add_field(
            name="Roles",
            value=", ".join(role.mention for role in main_member.roles),
            inline=False,
        )
        embed.add_field(
            name="Member since",
            value=main_member.joined_at.strftime("%d %B %Y"),
            inline=True,
        )
        embed.add_field(
            name="Discord User since",
            value=main_member.created_at.strftime("%d %B %Y"),
            inline=True,
        )
        if len(mentions) > 1:
            embed.add_field(
                name="Other participants", value=", ".join(mentions[1:]), inline=False
            )

        embed.set_footer(text=f"Ticket ID: {ticket.id}")

        await ticket.send(content=", ".join(mentions), embed=embed)

    async def toggle_channel_access(
        self,
        channel: discord.TextChannel,
        members: Greedy[discord.Member],
        *,
        allow: bool = True,
    ):
        """Toggle channel access for members."""
        for member in members:
            await channel.set_permissions(
                member, send_messages=allow, read_messages=allow, add_reactions=allow
            )

        clause = "granted" if allow else "revoked"

        await channel.send(
            f"Access {clause} for {', '.join(member.mention for member in members)}"
        )

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Add member to guild_members list."""
        # if member.id not in self.guild_members:
        #     self.guild_members.append(member.id)
        pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Remove member from guild_members list."""
        # if member.id in self.guild_members:
        #     self.guild_members.remove(member.id)

        # remove the ticket from the cache if the member leaves the guild
        if member.id in self._cache:
            del self._cache[member.id]

        # send a message to the ticket about the user leaving the guild
        ticket = self.bot.get_channel(self._cache[member.id])

        if ticket is not None:
            await ticket.send(f"{member} left the server.")

    @commands.Cog.listener()
    async def on_message(self, message):
        pass
        # # only dm messages
        # if not isinstance(message.channel, discord.DMChannel):
        #     return

        # if message.author.bot:
        #     return

        # # check if the message author is a member of the guild
        # if message.author.id not in self.guild_members:
        #     return

        # # check if the message author has a ticket
        # # if not, create one
        # if message.author.id not in self.tickets:
        #     # create a ticket
        #     category = self.bot.get_channel(Categories.modmail)
        #     ticket = await category.create_text_channel(
        #         name=f"{message.author.name}-{message.author.discriminator}",
        #         topic=f"Ticket for {message.author.mention}"
        #     )
        #     self.tickets[message.author.id] = ticket.id

        #     # send a message to the ticket
        #     await ticket.send(f"Ticket created for {message.author.mention}.")

        # else:
        #     # get the ticket
        #     ticket = self.bot.get_channel(self.tickets[message.author.id])

        #     # send the message to the ticket
        #     embed = discord.Embed(
        #         description=message.content,
        #         color=discord.Color.blurple()
        #     )

        #     embed.set_author(name=message.author, icon_url=message.author.avatar_url)
        #     await ticket.send(embed=embed)

    # delete the ticket when the user leaves the guild or channel is deleted

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if channel.id in self.tickets.values():
            for member_id, channel_id in self.tickets.items():
                if channel_id == channel.id:
                    del self.tickets[member_id]
                    break

    @commands.group(invoke_without_command=True, aliases=["t"])
    async def ticket(self, ctx):
        """Create a ticket to contact the staff.""" ""
        await self.create_ticket(ctx, ctx.author)

    @ticket.command()
    @commands.has_any_role("Mod", "Staff")
    async def create(self, ctx, members: Greedy[Union[discord.Member, discord.User]]):
        """Create a ticket."""

        # check if any member has any ticket open
        # if yes, send a message to the channel

        for member in members:
            if member.id in self._cache:
                ticket = self.bot.get_channel(self._cache.get(member.id))
                if not ticket:
                    continue
                await ctx.send(
                    f"There is already a ticket open for {member.display_name}: {ticket.mention}",
                    reference=ctx.message,
                )
                return

        category = self.bot.get_channel(Categories.modmail)

        main_member = members[0]
        ticket_name = f"{main_member.name}-{main_member.discriminator}"

        ticket = await category.create_text_channel(
            name=ticket_name,
            topic=f"Ticket for {main_member.mention}",
            reason=f"Ticket created by {ctx.author}",
        )

        # add the ticket to the cache
        for member in members:
            self._cache.add(member.id, ticket.id)

        # add members to the ticket
        await self.toggle_channel_access(ticket, members)

        # send a message to the ticket
        await self.send_new_ticket_message(ticket, members)

    @ticket.command()
    @commands.check(ticket_close_check)
    async def close(self, ctx):
        """Close a ticket."""
        for member_id, channel_id in self._cache.items():
            if channel_id == ctx.channel.id:
                del self._cache[member_id]

        await ctx.channel.delete(reason=f"Ticket closed by {ctx.author}.")

    @ticket.command()
    @commands.has_any_role("Mod", "Staff")
    @commands.check(is_modmail_category)
    async def add(self, ctx, members: Greedy[Union[discord.Member, discord.User]]):
        """Add a member to the ticket."""
        for m in members:
            self._cache.add(m.id, ctx.channel.id)

        await self.toggle_channel_access(ctx.channel, members, allow=False)

    @ticket.command()
    @commands.has_any_role("Mod", "Staff")
    @commands.check(is_modmail_category)
    async def remove(self, ctx, members: Greedy[Union[discord.Member, discord.User]]):
        """Remove a member from the ticket."""
        for m in members:
            self._cache.remove(m.id)

        await self.toggle_channel_access(ctx.channel, members, allow=False)

    # tasks

    @tasks.loop(minutes=5)
    async def sync_tickets_with_db(self):
        """Sync tickets with the mongodb database"""
        # create a collection if not exists

        self.bot.db.create_collection("tickets", exist_ok=True)

        collection = self.bot.db.tickets

        # get all tickets from the database
        tickets = await collection.find().to_list(length=None)

        # update missing local tickets to remote cache and local cache
        all_local_tickets = self.bot.get_channel(Categories.modmail).text_channels
        for ticket in all_local_tickets:
            if ticket.id not in [t["channel_id"] for t in tickets]:
                # grab from local cache
                member_ids = self._cache.get_members_by_ticket(ticket.id)
                for member_id in member_ids:
                    if not member_id:
                        self._cache.remove(member_id)
                        continue

                    # add to remote cache matching member
                    await collection.update_one(
                        {"member_id": member_id},
                        {"$set": {"channel_id": ticket.id}},
                        upsert=True,
                    )


def setup(bot):
    bot.add_cog(Modmail(bot))
