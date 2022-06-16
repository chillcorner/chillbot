import re
import discord
import openai
from discord.ext import commands
from utils.checks import is_mod
from bot.constants import Keys, Roles


class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label='Approve', style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_mod(interaction.user):
            return

        await interaction.response.send_message('Confirming', ephemeral=True)
        self.value = True
        self.stop()

        role = interaction.guild.get_role(Roles.verified)

    @discord.ui.button(label='Reject', style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_mod(interaction.user):
            return

        await interaction.response.send_message('Rejecting', ephemeral=True)
        self.value = False
        self.stop()


class Verification(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def verify(self, ctx):
        pass


async def setup(bot):
    await bot.add_cog(Verification(bot))
