import asyncio
import io
import json
import re

from typing import List, Literal, Optional, Union
import discord
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import Context, Greedy

from bot.constants import Guilds, Roles

# # MONGO SCHEMA
# {
#     "user_id": 123456789,
#     "role_id": 123456789,
#     "name": "role name",
#     "color": "#ffffff",
#     "icon_url": "https://example.com/icon.png",
#     "mentionable": True
# }


def is_lvl_50(i: discord.Interaction):
    for r in i.user.roles:
        if r.name.startswith('lvl'):
            lvl_int = int(r.name.split(' ')[1])
            if lvl_int >= 50:
                return True


def is_lvl_50_or_patreon(self, interaction: discord.Interaction):
    if any(r.id in Guilds.patreon_role_ids for r in interaction.user.roles):
        return is_lvl_50(interaction)

    return False


def is_patreon_t2(i: discord.Interaction):
    for r in i.user.roles:
        if r.id == Roles.patreon_t2:
            return True
    return False


def check_role_name(name: str, roles: List[discord.Role]) -> str:
    if len(name) > 32:
        raise ValueError("Role names must be less than 32 characters.")
    if name.lower() in [role.name.lower() for role in roles]:
        raise ValueError("Role name must be unique.")
    return name


def check_role_color(color: str) -> str:
    if len(color) > 7:
        raise ValueError("Role color must be less than 7 characters.")
    if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", color):
        raise ValueError("Role color must be a valid hex color.")
    return color


def check_role_icon_url(url: str) -> str:
    if len(url) > 1024:
        raise ValueError("Role icon URL must be less than 1024 characters.")
    # TODO: check if it's a unicode emoji character

    if not re.match(r"^(http|https)://.*\.(?:png|jpg|jpeg)$", url):
        raise ValueError("Role icon must be a valid image url.")

    return url


async def create_role(interaction, name, color, icon_url, mentionable, bot) -> discord.Role:
    """Create a role with the given name, color, and icon url"""
    role_name = check_role_name(name, interaction.user.roles)
    if color:
        role_color = check_role_color(color)
    if icon_url:
        role_icon_url = check_role_icon_url(icon_url)
        # make sure it's patreon T2 or lvl 50+
        if not (is_patreon_t2(interaction) or is_lvl_50(interaction)):
            await interaction.followup.send(
                "You must be a Patreon T2 or level 50+ to use custom role icons.",
                ephemeral=True
            )
            return
        # turn the role_icon_url to bytes
        async with bot.session.get(role_icon_url) as resp:
            role_icon_bytes = await resp.read()

    # create the role with the validated name, color, and icon url

    if color:
        role_color = discord.Color(int(role_color[1:], 16))
    else:
        role_color = discord.Color.default()

    if icon_url:
        try:
            display_icon = role_icon_bytes
        except Exception as e:
            print("Error, couldn't decode image: ", e)
            return
    else:
        display_icon = None

    try:
        role = await interaction.guild.create_role(
            name=role_name,
            color=role_color,
            reason=f"Created by {interaction.user} ({interaction.user.id})",
            display_icon=display_icon,
            mentionable=mentionable,

        )
    except Exception as e:
        print("Error, couldn't create role: ", e)

    await asyncio.sleep(2)

    if role:
        top_pos = interaction.guild.me.top_role.position
        await role.edit(position=top_pos - 25)

        await bot.custom_roles.insert_one({
            "user_id": interaction.user.id,
            "role_id": role.id,
            "name": name,
            "color": color,
            "icon_url": icon_url,
            "mentionable": True
        })

    return role


class MyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.roles_being_created = set()

    # async def cog_check(self, ctx) -> bool:
    #     return ctx.user.id == 982097011434201108

    @app_commands.command(name="sync")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync(self, interaction: discord.Interaction) -> None:
        """Sync slash commands"""
        await interaction.response.defer()
        await interaction.client.tree.sync(guild=interaction.guild)
        await interaction.followup.send("Synced slash commands.")

    cr = app_commands.Group(
        name="cr", description="Custom roles related commands")

    group_cooldown = app_commands.checks.cooldown(
        1, 60, key=lambda i: i.user.id)

    @cr.command(name="create")
    @group_cooldown
    @app_commands.describe(name="Your role name", color="Your role color in hex", icon_url="Your role icon URL in PNG/JPG format")
    async def create(self, interaction: discord.Interaction,
                     name: str,
                     color: Optional[str] = None,
                     icon_url: Optional[str] = None) -> None:
        """Create your own custom role"""

        await interaction.response.defer()

        if interaction.user.id in self.roles_being_created:
            await interaction.followup.send("You already have a role being created!", ephemeral=True)
            return

        # check if user already has a custom role
        document = await self.bot.custom_roles.find_one({"user_id": interaction.user.id})
        if document:
            await interaction.followup.send("You already have a custom role!", ephemeral=True)
            return

        # create the role

        role = await create_role(interaction, name, color, icon_url, mentionable=True, bot=self.bot)

        await interaction.user.add_roles(role)

        await interaction.followup.send(f"Created and assigned role {role.mention}!", ephemeral=True)

        self.roles_being_created.remove(interaction.user.id)

    @cr.command(name="delete")
    async def delete(self, interaction: discord.Interaction) -> None:
        """Delete your custom role"""

        await interaction.response.defer()

        # get role ID
        document = await self.bot.custom_roles.find_one({"user_id": interaction.user.id}, {"role_id": 1})

        if not document:
            await interaction.followup.send("You don't have a custom role!", ephemeral=True)
            return

        role_id = document["role_id"]

        # delete all documents with the user ID
        await self.bot.custom_roles.delete_many({"user_id": interaction.user.id})

        # get role object
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.followup.send("Role not found!", ephemeral=True)
            return

        # delete role
        await role.delete(reason=f"Deleted by {interaction.user} ({interaction.user.id})")
        await interaction.followup.send(f"Deleted your custom role", ephemeral=True)

    @cr.command(name="color")
    async def color(self, interaction: discord.Interaction, color: str) -> None:
        """Change your custom role's color"""

        await interaction.response.defer()

        # get the role ID
        document = await self.bot.custom_roles.find_one({"user_id": interaction.user.id}, {"role_id": 1})
        role_id = document["role_id"]

        # get the role object
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.followup.send("Role not found!", ephemeral=True)
            return

        # change the role's color
        await role.edit(color=discord.Color(int(color[1:], 16)))

        await self.bot.custom_roles.update_one({"user_id": interaction.user.id}, {"$set": {"color": color}})

        await interaction.followup.send(f"Changed the role color to **{color}**", ephemeral=True)

    @cr.command(name="name")
    @group_cooldown
    async def name(self, interaction: discord.Interaction, name: str) -> None:
        """Change your custom role's name"""
        # TODO: make sure it doesn't match with any of the existing roles except their own(i.e. case changes)

        await interaction.response.defer()

        # get the role ID
        document = await self.bot.custom_roles.find_one({"user_id": interaction.user.id}, {"role_id": 1})
        role_id = document["role_id"]

        # get the role object
        role = interaction.guild.get_role(role_id)

        if not role:
            await interaction.followup.send("You don't have a custom role", ephemeral=True)
            return

        # make sure the name doesn't conflict with any of the existing roles
        for r in interaction.guild.roles:
            if r.id == role_id:
                continue
            if r.name.lower() in name.lower():
                await interaction.followup.send("This role already exists!", ephemeral=True)
                return

        # change the role's name
        await role.edit(name=name)

        await self.bot.custom_roles.update_one({"user_id": interaction.user.id}, {"$set": {"name": name}})
        await interaction.followup.send(f"Changed your name to {role.mention}", ephemeral=True)

    @cr.command(name="icon")
    @group_cooldown
    async def icon(self, interaction: discord.Interaction, icon_url: str) -> None:
        """Change your custom role's icon"""

        await interaction.response.defer()

        # TODO: image validation(only JPG/PNG)

        # get the role ID
        document = await self.bot.custom_roles.find_one({"user_id": interaction.user.id}, {"role_id": 1})
        role_id = document["role_id"]

        # get the role object
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.followup.send("Role not found!", ephemeral=True)
            return

        # change the role's icon
        async with self.bot.session.get(icon_url) as resp:
            resp = await resp.read()
            await role.edit(display_icon=resp)

        try:
            await self.bot.custom_roles.update_one({"user_id": interaction.user.id}, {"$set": {"icon_url": icon_url}})
        except Exception as e:
            print('exception', e)
        await interaction.followup.send(f"Changed icon to the URL provided!", ephemeral=True)

    @cr.command(name="status")
    async def status(self, interaction: discord.Interaction) -> None:
        """Check your custom role's status"""

        await interaction.response.defer()

        # get the role ID
        document = await self.bot.custom_roles.find_one({"user_id": interaction.user.id}, {"role_id": 1})
        if not document:
            await interaction.followup.send("You don't have any custom role", ephemeral=True)
            return
        role_id = document["role_id"]

        # get the role object
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.followup.send("You don't have any custom role", ephemeral=True)
            return

        # get the role's status
        doc = await self.bot.custom_roles.find_one({"user_id": interaction.user.id}, {"name": 1, "color": 1, "icon_url": 1, "mentionable": 1})

        if doc["color"]:
            color = discord.Color(int(doc["color"][1:], 16))
        else:
            color = discord.Color.default()
        embed = discord.Embed(color=color)
        embed.set_author(name=f"{interaction.user.display_name}'s custom role", icon_url=str(
            interaction.user.display_avatar.url))
        embed.add_field(name="Name", value=f"{role.mention}")
        if doc["icon_url"]:
            embed.set_thumbnail(url=doc["icon_url"])
        embed.add_field(name="Mentionable", value=doc["mentionable"])

        await interaction.followup.send(embed=embed, ephemeral=True)

    @cr.command(name="mentionable")
    @group_cooldown
    async def mentionable(self, interaction: discord.Interaction) -> None:
        """Toggle your custom role's mentionability"""

        await interaction.response.defer()

        doc = await self.bot.custom_roles.find_one({"user_id": interaction.user.id}, {"mentionable": 1, "role_id": 1})
        is_mentionable = doc["mentionable"]

        # edit the role
        role_id = doc["role_id"]
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.followup.send("Role not found!", ephemeral=True)
            return

        await role.edit(mentionable=not is_mentionable)

        await self.bot.custom_roles.update_one({"user_id": interaction.user.id}, {"$set": {"mentionable": not is_mentionable}})

        clause = "un" if is_mentionable else ""
        await interaction.followup.send(f"Made role {clause}mentionable!", ephemeral=True)

    @create.error
    async def on_cr_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(str(error), ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.command.parent.name == "cr":

            if is_lvl_50_or_patreon(interaction):
                return True
            await interaction.response.send_message("You need to be level 50+ or a patron to use this command", ephemeral=True)
            return False


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MyCog(bot), guilds=[discord.Object(id=Guilds.cc)])
