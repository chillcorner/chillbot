import asyncio
import io
import json
import re
from typing import List, Literal, Optional, Union

import aiohttp
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord.ext.commands import Context, Greedy

from bot.constants import Guilds, People, Roles

# # MONGO SCHEMA
# {
#     "user_id": 123456789,
#     "role_id": 123456789,
#     "name": "role name",
#     "color": "#ffffff",
#     "icon_url": "https://example.com/icon.png",
#     "mentionable": True
# }


MIN_LVL = 40
HEX_PATTERN = re.compile(r"^#?([0-9a-fA-F]{6})$")


class CustomCheckFailure(app_commands.AppCommandError):
    pass


def has_required_level(i: discord.Interaction):
    for r in i.user.roles:
        if r.name.startswith("lvl"):
            lvl_int = int(r.name.split(" ")[1])
            if lvl_int >= MIN_LVL:
                return True
    # allow mod
    return any(r.id == Roles.mod for r in i.user.roles)


def has_required_level_or_patreon(interaction: discord.Interaction):
    if any(r.id in Roles.patreon_role_ids for r in interaction.user.roles):
        return True

    return has_required_level(interaction)


def cooldown_check(interaction: discord.Interaction):
    """Owner bypasses cooldown"""
    if interaction.user.id == People.bharat:
        return None

    return app_commands.Cooldown(1, 60)


def is_patreon_t2(i: discord.Interaction):
    for r in i.user.roles:
        if r.id == Roles.patreon_t2:
            return True
    return False


def check_role_name(name: str, roles: List[discord.Role]) -> str:
    if len(name) > 32:
        raise CustomCheckFailure("Role names must be less than 32 characters.")
    if name.lower() in [role.name.lower() for role in roles]:
        raise CustomCheckFailure("Role name must be unique and not already in use.")
    return name


def check_role_color(color: str) -> str:
    if len(color) > 7:
        raise CustomCheckFailure("Role color must be less than 7 characters.")
    if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", color):
        raise CustomCheckFailure("Role color must be a valid hex color e.g. #FFFFFF")
    return color


def check_role_icon_url(url: str) -> str:
    if len(url) > 1024:
        raise CustomCheckFailure("Role icon URL must be less than 1024 characters.")
    # TODO: check if it's a unicode emoji character

    # remove query params
    url = url.split("?")[0].strip()

    if not re.match(r"^(http|https)://.*\.(?:png|jpg|jpeg)$", url):
        raise CustomCheckFailure(
            "Role icon must be a valid image url with a .png, .jpg, or .jpeg extension."
        )

    return url


def is_valid_hex(hex_code: str):
    m = HEX_PATTERN.match(hex_code)
    if not m:
        return False

    try:
        return int(m.group(1), 16)

    except ValueError:
        return False


async def get_icon(icon_url: str, session: aiohttp.ClientSession):
    async with session.get(icon_url) as resp:
        return await resp.read()


async def create_role(
    interaction, name, color, icon_url, mentionable, bot
) -> discord.Role:
    """Create a role with the given name, color, and icon url"""
    role_name = check_role_name(name, interaction.guild.roles)
    if color:
        role_color = is_valid_hex(color)
        if role_color is False:
            raise CustomCheckFailure(
                "Role color must be a valid hex color e.g. #FFFFFF"
            )
    if icon_url:
        role_icon_url = check_role_icon_url(icon_url)
        # make sure it's patreon T2 or min lvl +
        if not (is_patreon_t2(interaction) or has_required_level(interaction)):
            await interaction.followup.send(
                f"You must be a Patreon T2 or level {MIN_LVL}+ to use custom role icons.",
                ephemeral=True,
            )
            return
        # turn the role_icon_url to bytes

        role_icon_bytes = await get_icon(role_icon_url, bot.session)

    # create the role with the validated name, color, and icon url

    if color:
        role_color = discord.Color(role_color)
    else:
        role_color = discord.Color.default()  # default color

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

        await bot.custom_roles.insert_one(
            {
                "user_id": interaction.user.id,
                "role_id": role.id,
                "name": name,
                "color": color,
                "icon_url": icon_url,
                "mentionable": True,
            }
        )

    return role


blacklisted_users = [
    999177926903869520, #himby #test2
]


async def is_not_blacklisted(interaction):
    return interaction.user.id not in blacklisted_users


class MyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.roles_being_created = set()

    # async def cog_check(self, ctx) -> bool:
    #     return ctx.user.id == 982097011434201108

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync(self, ctx) -> None:
        """Sync slash commands"""

        await ctx.bot.tree.sync(guild=ctx.guild)
        await ctx.send("Synced slash commands.")

    cr = app_commands.Group(name="cr", description="Custom roles related commands")
    group_cooldown = app_commands.checks.dynamic_cooldown(cooldown_check)

    @cr.command(name="create")
    @group_cooldown
    @app_commands.check(is_not_blacklisted)
    @app_commands.describe(
        name="Your role name",
        color="Your role color in hex",
        icon_url="Your role icon URL in PNG/JPG format",
    )
    async def create(
        self,
        interaction: discord.Interaction,
        name: str,
        color: Optional[str] = None,
        icon_url: Optional[str] = None,
    ) -> None:
        """Create your own custom role"""

        await interaction.response.defer()

        if interaction.user.id in self.roles_being_created:
            await interaction.followup.send(
                "You already have a role being created!", ephemeral=True
            )
            return

        # check if user already has a custom role
        document = await self.bot.custom_roles.find_one(
            {"user_id": interaction.user.id}
        )
        if document:
            await interaction.followup.send(
                "You already have a custom role!", ephemeral=True
            )
            return

        # create the role

        role = await create_role(
            interaction, name, color, icon_url, mentionable=True, bot=self.bot
        )

        await interaction.user.add_roles(role)

        await interaction.followup.send(
            f"Created and assigned role {role.mention}!", ephemeral=True
        )

        self.roles_being_created.remove(interaction.user.id)

    @cr.command(name="update")
    @group_cooldown
    @app_commands.check(is_not_blacklisted)
    @app_commands.describe(
        name="Your new role name",
        color="Your new role color hex",
        icon_url="Your new role icon URL in PNG/JPG format",
    )
    async def update(
        self,
        interaction: discord.Interaction,
        name: Optional[str] = None,
        color: Optional[str] = None,
        icon_url: Optional[str] = None,
    ) -> None:
        """Update your custom role name, color, or icon"""

        if not any([name, color, icon_url]):
            await interaction.response.send_message(
                "You must provide a name, color, or icon URL!", ephemeral=True
            )
            return

        await interaction.response.defer()

        # get the document with all the info
        document = await self.bot.custom_roles.find_one(
            {"user_id": interaction.user.id}
        )

        if not document:
            await interaction.followup.send(
                "You don't have a custom role!", ephemeral=True
            )
            return

        role_id = document["role_id"]

        # get role object
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.followup.send(
                "Your custom role doesn't exist!", ephemeral=True
            )
            return

        # only update the fields that are provided in one go
        update = {}

        if name:
            # ok
            update["name"] = check_role_name(name, interaction.guild.roles)

        if color:
            _hex = is_valid_hex(color)
            if _hex is False:
                await interaction.followup.send(
                    "Please provide a valid hex e.g. #FFF000", ephemeral=True
                )
                return
            update["color"] = _hex

        if icon_url:
            update["icon_url"] = check_role_icon_url(icon_url)

        await self.bot.custom_roles.update_one(
            {"user_id": interaction.user.id, "role.id": role.id}, {"$set": update}
        )

        if "icon_url" in update:
            update["display_icon"] = await get_icon(
                update.pop("icon_url"), self.bot.session
            )

        if "color" in update:
            # convert hex to discord.Color
            update["color"] = discord.Color(update["color"])

        print(f"Updating role {role} with data:\n{update.keys()}")
        print(f"{update.get('name')}")
        # update the role
        await role.edit(**update)

        await interaction.followup.send("Updated your custom role!", ephemeral=True)

    @cr.command(name="delete")
    @app_commands.check(is_not_blacklisted)
    async def delete(self, interaction: discord.Interaction) -> None:
        """Delete your custom role"""

        await interaction.response.defer()

        # get role ID
        document = await self.bot.custom_roles.find_one(
            {"user_id": interaction.user.id}, {"role_id": 1}
        )

        if not document:
            await interaction.followup.send(
                "You don't have a custom role!", ephemeral=True
            )
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
        await role.delete(
            reason=f"Deleted by {interaction.user} ({interaction.user.id})"
        )
        await interaction.followup.send(f"Deleted your custom role", ephemeral=True)

    @cr.command(name="slots")
    @app_commands.default_permissions(administrator=True)
    async def slots(self, interaction: discord.Interaction) -> None:
        """Displays the number of custom role slots available"""

        resp = f"Custom role slots available: {(250 - len(interaction.guild.roles)) - 10}/250."
        await interaction.response.send_message(resp, ephemeral=True)

    @cr.command(name="patreon")
    async def patreon(self, interaction: discord.Interaction) -> None:
        """Patreon link to support the bot development"""
        await interaction.response.send_message(
            "https://www.patreon.com/chillcornerbot"
        )

    @cr.command(name="rules")
    async def rules(self, interaction: discord.Interaction) -> None:
        """Rules to follow while using custom roles"""
        embed = discord.Embed(title="Custom Role Rules", color=discord.Color.blurple())
        embed.add_field(
            name="1. No NSFW content",
            value="Your custom role should not contain any NSFW content. This includes any kind of sexual content, nudity, etc.",
            inline=False,
        )
        embed.add_field(
            name="2. No offensive content",
            value="Your custom role should not contain any offensive content. This includes any kind of hate speech, racism, etc.",
            inline=False,
        )
        embed.add_field(
            name="4. No impersonation",
            value="Your custom role should not imitate any other server member/role",
            inline=False,
        )
        embed.add_field(
            name="Conclusion",
            value="Your custom role name, icon image etc should comply with the server rules and discord community guidelines",
            inline=False,
        )

        embed.set_footer(
            text="If you break any of these rules, your custom role could be removed without any warning"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @create.error
    @update.error
    async def on_edit_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(str(error), ephemeral=True)

        elif isinstance(error, CustomCheckFailure):
            await interaction.followup.send(str(error), ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        cmd = interaction.command
        if cmd.parent.name == "cr":
            if cmd.name == "patreon":
                return True

            # staff members can use all commands
            if any(r.id == Roles.mod for r in interaction.user.roles):
                return True

            if has_required_level_or_patreon(interaction):
                return True

            await interaction.response.send_message(
                f"You need to be level {MIN_LVL}+ or a patron to use this command",
                ephemeral=True,
            )



async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MyCog(bot), guilds=[discord.Object(id=Guilds.cc)])
