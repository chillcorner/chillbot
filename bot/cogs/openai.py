import functools
import re
from typing import Optional
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

    return clean if clean else False


class OpenAI(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def get_openapi_response(self, *, prompt, stop, tokens, temperature=0.7, frequency_penalty=0, presence_penalty=0):
        """
        Returns a response from OpenAI.ai.
        """

        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=prompt,
            temperature=temperature,
            max_tokens=tokens,
            top_p=1,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=[stop]
        )

        return response["choices"][0]["text"]

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def explain(self, ctx):
        """Explain a text for you"""
        clean_text = is_clean_with_ref(ctx)
        if not clean_text:
            return

        res = self.get_openapi_response(prompt=f"Explain the meaning of this text from {ctx.message.reference.cached_message.author.display_name.title()}:\n{clean_text}\nExplanation:",
                                        stop="Explanation:", tokens=256)
        ref = ctx.message.reference.cached_message.to_reference()
        await ctx.send(content=res, reference=ref)

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def answer(self, ctx):
        """Answers a question for you"""
        clean_text = is_clean_with_ref(ctx)
        if not clean_text:
            return

        res = self.get_openapi_response(prompt=f"Generate a quick response for this question:\n{clean_text}\nresponse:",
                                        stop="Response:", tokens=256)

        ref = ctx.message.reference.cached_message.to_reference()
        await ctx.send(content=res, reference=ref)

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def tldr(self, ctx):
        """Summarizes a long text for you"""
        clean_text = is_clean_with_ref(ctx)
        if not clean_text:
            return

        res = self.get_openapi_response(prompt=f"Summarize this for a second-grade student:\n{clean_text}\nsummary:",
                                        stop="Response:", tokens=75)
        ref = ctx.message.reference.cached_message.to_reference()
        await ctx.send(content=res, reference=ref)

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def english(self, ctx):
        """Corrects grammar and spelling errors in a text for you"""
        clean_text = is_clean_with_ref(ctx)
        if not clean_text:
            return

        res = self.get_openapi_response(prompt=f"Correct this to standard English:\n{clean_text}\ncorrection:",
                                        stop="Correction:", tokens=60)
        ref = ctx.message.reference.cached_message.to_reference()
        await ctx.send(content=res, reference=ref)

    @commands.command()
    @commands.cooldown(1, 15, commands.BucketType.channel)
    async def fact(self, ctx, *, topic=None):
        """Tells you a random fact about given topic."""
        if topic:
            prompt = clean_message(topic)

        prompt = "Tell me a random fact" if not topic else f"Tell me a fact about {topic}."

        async with ctx.channel.typing():
            func = functools.partial(self.get_openapi_response,
                                     prompt=f"{prompt}\nfact:",
                                     stop="Fact:", tokens=60)
            res = await self.bot.loop.run_in_executor(None, func)

            await ctx.reply(res)

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def ask(self, ctx, *, question: str):
        """Ask any question to bot"""

        question = clean_message(question)
        if not question:
            return

        async with ctx.channel.typing():
            response = openai.Completion.create(
                engine="text-davinci-002",
                prompt=question,
                temperature=0.7,
                max_tokens=256,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,

            )

        res = response["choices"][0]["text"]
        await ctx.send(content=res.strip().replace("\n", ""))

    @commands.command()
    @commands.cooldown(1, 20, commands.BucketType.member)
    async def topic(self, ctx, *, category: Optional[str]):
        """Generates a question for you to talk about based on the topic category provided. Leave topic empty for a random question"""

        if not category:
            prompt = "Generate a random thought-provoking question to talk about:"
        else:
            cat_clean = clean_message(category)
            if not cat_clean:
                return

            prompt = f"Generate a thought-provoking question about {cat_clean.title()}:"

        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=f"{prompt}\nQuestion:",
            temperature=1,
            max_tokens=256,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=["Question:"]
        )

        r = response["choices"][0]["text"]
        await ctx.send(content=r, reference=ctx.message.to_reference())

    @commands.command(enabled=False)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def story(self, ctx, *, members: str):
        """Generates a story based on names provided"""
        if not members:
            return

        names = ', '.join(f"{m.strip()}" for m in members.split())

        prompt = f'Create a fake story between {names}.'

        async with ctx.channel.typing():
            func = functools.partial(self.get_openapi_response,
                                     prompt=f"{prompt}\nStory:",
                                     stop="Story:", tokens=120)
            res = await self.bot.loop.run_in_executor(None, func)

            await ctx.send(content=res)


async def setup(bot):
    await bot.add_cog(OpenAI(bot))
