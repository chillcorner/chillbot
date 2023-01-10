from discord.ext.commands import CommandError


class SnippetDoesNotExist(CommandError):
    pass


class SnippetExists(CommandError):
    pass
