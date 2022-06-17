import discord
from bot.constants import Roles



def is_mod(member: discord.Member):
    return Roles.mod in [r.id for r in member.roles]
