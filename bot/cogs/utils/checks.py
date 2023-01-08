import discord
from bot.constants import Roles


def is_patreon_t1(member: discord.Member):
    return Roles.patreon_t1 in [r.id for r in member.roles]

def is_patreon_t2(member: discord.Member):
    return Roles.patreon_t2 in [r.id for r in member.roles]

def is_lvl_60(member: discord.Member):    
    for r in member.roles:
        if r.name.startswith('lvl'):
            lvl_int = int(r.name.split(' ')[1])
            if lvl_int >= 60:
                return True

def is_lvl_60_or_patreon_t1(member: discord.Member):
    return is_lvl_60(member) or is_patreon_t1(member)

def is_lvl_60_or_patreon_t2(member: discord.Member):
    return is_lvl_60(member) or is_patreon_t2(member)

def is_lvl_60_or_patreon(member: discord.Member):
    return is_lvl_60(member) or is_patreon_t1(member) or is_patreon_t2(member)


def is_mod(member: discord.Member):
    return Roles.mod in [r.id for r in member.roles]
