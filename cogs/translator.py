from typing import Optional

import discord
import langcodes
from discord import app_commands, Interaction, Message
from discord.ext import commands
from googletrans.models import Translated

from bot import TranslatorBot
from utils import create_translate_embed


class TranslatorCog(commands.Cog, name="Translator"):
    def __init__(self, bot: TranslatorBot) -> None:
        self.bot = bot
    
    @app_commands.command()
    @app_commands.rename(from_lang="from")
    @app_commands.describe(
        text="The text to translate",
        to="The language to translate to",
        from_lang="The language to translate from (defaults to auto-detect)",
    )
    async def translate(
        self, interaction: Interaction, text: str, to: str, from_lang: str = "auto"
    ):
        translated = self.bot.translator.translate(text, dest=to, src=from_lang)
        await interaction.response.send_message(
            embed=create_translate_embed(translated, interaction=interaction)
        )


async def setup(bot: TranslatorBot):
    await bot.add_cog(TranslatorCog(bot))
    
    