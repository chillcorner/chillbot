import asyncio
import random
import re
import string
import discord
import openai
from discord.ext import commands
from bot.constants import Guilds, Roles, Categories


def is_mod(member):
    return member.guild.get_role(Roles.mod) in member.roles


def get_random_code():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))


async def create_verification_channel(member: discord.Member, verification_type: str):
    cat = member.guild.get_channel(Categories.verification)

    mod_role = member.guild.get_role(Roles.mod)

    overwrites = {
        member.guild.default_role:
            discord.PermissionOverwrite(
                read_messages=False,
            ),
        member: discord.PermissionOverwrite(read_messages=True,
                                            add_reactions=False,
                                            embed_links=False,
                                            attach_files=True),

        mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    code = get_random_code()

    emoji = "🤳" if verification_type == "selfie" else "🎨"

    priv_channel = await member.guild.create_text_channel(
        name=f"{emoji} {verification_type}_{code}_{member.display_name}",
        category=cat,
        topic=f"{verification_type.title()} verification for {member.display_name}",
        slowmode_delay=5,
        overwrites=overwrites
    )

    # notify with an example
    embed = discord.Embed(color=discord.Color.red())
    embed.set_author(name="Follow these verification steps:",
                     icon_url=member.display_avatar.url)
    embed.add_field(name="Verification Code", value=f"{code}")

    if verification_type == "selfie":
        desc = f"1. Take a piece of paper.\n\n" \
               f"2. Write **{code}** on it.\n\n" \
               f"3. Hold it and take a selfie with it.\n\n" \
               f"4. Upload the selfie in this channel.\n\n" \
               f"5. Wait for mods to verify it.\n\n\n"
    else:
        desc = f"1. Take an existing artwork of yours or create a new disposable one.\n\n" \
               f"2. Write **{code}** at the upper corner of the artwork. " \
               f"You can use a separate sticky note or photoshop layer in case of digital art.\n\n" \
               f"3. Take a picture of it and make sure the code is clearly visible.\n\n" \
               f"4. Upload the picture in this channel.\n\n" \
               f"5. Wait for mods to verify it.\n\n\n"

    embed.description = desc
    embed.set_footer(text="Note: We will not keep your verification picture. "
                          "It would be permanently deleted as soon as the verification "
                          "has been marked complete"
                          " by one of the server moderators.",
                     icon_url="https://cdn0.iconfinder.com/data/icons/colorful-business-set-1/100/colour-39-512.png")

    # embed.set_image(url=)

    _msg = await priv_channel.send(embed=embed, content=member.mention, view=VerificationView(member, verification_type))

    # await asyncio.sleep(60*25)
    # if priv_channel:
    #     last_20 = await priv_channel.history(limit=20).flatten()
    #     for msg in last_20:
    #         if msg.author == member and len(msg.attachments) >= 1:
    #             return
    #     await priv_channel.delete()


class VerificationView(discord.ui.View):
    def __init__(self, member: discord.Member, verification_type: str):
        super().__init__()
        self.value = None
        self.member = member
        self.verification_type = verification_type

    @discord.ui.button(label='Approve', style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_mod(interaction.user):
            return

        await interaction.response.send_message(f'Verifying {self.member.display_name}', ephemeral=True)
        role_id = Roles.verified if self.verification_type == "selfie" else Roles.artist

        role = interaction.guild.get_role(role_id)

        await self.member.add_roles(role)

        self.value = True
        self.stop()

        await interaction.channel.delete(reason=f"Verfication successful")
        await self.member.send(f"We have verified your submission 🥳")

    @discord.ui.button(label='Reject', style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_mod(interaction.user):
            return

        await interaction.response.send_message(f"Rejecting {self.member.display_name}'s submission", ephemeral=True)
        self.value = False
        self.stop()

        await interaction.channel.delete(reason=f"Verfication failed")
        await self.member.send(f"We couldn't verify your submission")


class VerificationTypeView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label='Selfie verification', style=discord.ButtonStyle.green)
    async def selfie(self, interaction: discord.Interaction, button: discord.ui.Button):

        verified_role = interaction.guild.get_role(Roles.verified)
        if verified_role in interaction.user.roles:
            await interaction.response.send_message(f"You already have the {verified_role.name} role", ephemeral=True)
        else:
            await create_verification_channel(interaction.user, "selfie")
            await interaction.response.send_message('Please follow your recent ping.', ephemeral=True)

        self.value = True
        button.disabled = True
        self.stop()

    @discord.ui.button(label='Art verification', style=discord.ButtonStyle.blurple)
    async def art(self, interaction: discord.Interaction, button: discord.ui.Button):

        art_role = interaction.guild.get_role(Roles.artist)
        if art_role in interaction.user.roles:
            await interaction.response.send_message(f"You already have the {art_role.name} role", ephemeral=True)

        else:
            await create_verification_channel(interaction.user, "art")
            await interaction.response.send_message('Please follow your recent ping.', ephemeral=True)

        self.value = False
        button.disabled = True
        self.stop()


class Verification(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def verify(self, ctx):
        if ctx.guild.id != Guilds.cc:
            return
        await ctx.send("Please select the verification type", view=VerificationTypeView())


async def setup(bot):
    await bot.add_cog(Verification(bot))
