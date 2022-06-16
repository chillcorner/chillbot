import re
import openai
from discord.ext import commands

from bot.constants import Keys

openai.api_key = Keys.openai_key

EMOJI_RE = re.compile(r'<(a?):([A-Za-z0-9_]+):([0-9]+)>')
MENTION_RE = re.compile(r'<@?(!?)(#?)(&?)([0-9]*)>')


def clean_message(msg):
    """Removes emojis, mentions, and links from a message."""

    msg = re.sub(MENTION_RE, '', msg)
    new_msg = re.sub(EMOJI_RE, '', msg)

    return new_msg.strip()


def is_clean_with_ref(ctx):
    """Checks if the message is clean and has a reference."""
    ref = ctx.message.reference
    if not ref:
        return

    clean = clean_message(ref.cached_message.content)

    return True if clean else False


class OpenAI(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def get_openapi_response(self, *, prompt, stop, tokens, temperature=0.7):
        """
        Returns a response from OpenAI.ai.
        """

        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=prompt,
            temperature=temperature,
            max_tokens=tokens,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=[stop]
        )

        return response["choices"][0]["text"]

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.member)
    async def explain(self, ctx):
        """Explain a text for you"""
        if not is_clean_with_ref(ctx):
            return

        res = self.get_openapi_response(prompt=f"Explain the meaning of this text from {ref.cached_message.author.display_name.title()}:\n{clean}\nExplanation:",
                                        stop="Explanation:", tokens=256)
        await ctx.send(content=res, reference=ref.cached_message.to_reference())

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.member)
    async def english(self, ctx):
        """Corrects grammar and spelling errors in a text for you"""
        if not is_clean_with_ref(ctx):
            return

        res = self.get_openapi_response(prompt=f"Correct this to standard English:\n{clean}\ncorrection:",
                                        stop="Correction:", tokens=60)
        await ctx.send(content=res, reference=ref.cached_message.to_reference())

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.member)
    async def fact(self, ctx, *, topic=None):
        """Tells you a random fact about given topic."""
        if topic:
            prompt = clean_message(topic)

        prompt = "Tell me a random fact" if not topic else f"Tell me a fact about {topic}."

        res = self.get_openapi_response(prompt=f"{prompt}\nfact:",
                                        stop="Fact:", tokens=60)
        await ctx.send(content=res)


async def setup(bot):
    await bot.add_cog(OpenAI(bot))
