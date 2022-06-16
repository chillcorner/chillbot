import discord
from bot.constants import Roles
from bot.constants import Channels
from discord.ext import commands


def is_mod(member: discord.Member):
    return Roles.mod in [r.id for r in member.roles]
