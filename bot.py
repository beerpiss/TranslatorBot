import re
from typing import Optional

import discord
import langcodes
import spacy
from discord import app_commands, Message, Interaction
from discord.ext.commands import Bot
from dotenv import dotenv_values
from googletrans import Translator
from googletrans.models import Translated
from spacy.language import Language
from spacy_langdetect import LanguageDetector


@Language.factory("language_detector")
def create_language_detector(nlp, name):
    return LanguageDetector()


class TranslatorBot(Bot):
    def __init__(self, *args, testing_guild_id: Optional[int] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.testing_guild_id = testing_guild_id

    async def setup_hook(self) -> None:
        if self.testing_guild_id:
            guild = discord.Object(id=self.testing_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)


DISCORD_SYNTAX_REGEX = re.compile(r"<(a?:.+?:(\d+))>")
cfg = dotenv_values(".env")

intents = discord.Intents.default()
intents.message_content = True

client = TranslatorBot(
    command_prefix=">",
    intents=intents,
    testing_guild_id=int(cfg["GUILD_ID"]) if cfg["GUILD_ID"] else None,
)
nlp = spacy.load("en_core_web_sm")
nlp.add_pipe("language_detector")
translator = Translator()


def create_translate_embed(
    translated: Translated,
    message: Optional[Message] = None,
    interaction: Optional[Interaction] = None,
) -> discord.Embed:
    if message is None and interaction is None:
        raise ValueError("Either message or interaction must be specified")

    name = None
    url = None
    icon_url = None
    color = None

    if message is not None:
        name = message.author.display_name
        url = message.jump_url
        icon_url = message.author.display_avatar.url
        color = message.author.roles[-1].color
    elif interaction is not None:
        name = interaction.user.display_name
        url = None
        icon_url = interaction.user.display_avatar.url
        color = interaction.user.roles[-1].color

    return (
        discord.Embed(
            description=translated.text,
            color=color,
        )
        .set_footer(text=f"Translated from {langcodes.Language.get(translated.src).language_name()}")
        .set_author(
            name=name,
            url=url,
            icon_url=icon_url,
        )
    )


@client.event
async def on_message(message: Message):
    if message.author == client.user:
        return

    if (
        cfg["AUTO_TRANSLATE_CATEGORY"]
        and hasattr(message.channel, "category_id")
        and str(message.channel.category_id) not in cfg["AUTO_TRANSLATE_CATEGORY"]
    ):
        return

    emotes = DISCORD_SYNTAX_REGEX.findall(message.content)
    sanitized_message = DISCORD_SYNTAX_REGEX.sub(r"<\2>", message.content)
    doc = nlp(message.content)
    detected_lang = doc._.language["language"]
    if detected_lang != "en":
        translated = translator.translate(sanitized_message, dest="en")
        if translated.text.lower() != sanitized_message.lower() and translated.src != translated.dest:
            for emote in emotes:
                translated.text = translated.text.replace(f"<{emote[1]}>", f"<{emote[0]}>")
            print(translated.text)
            await message.reply(
                embed=create_translate_embed(translated, message=message),
                mention_author=False,
            )


@client.tree.command()
@app_commands.rename(
    from_lang="from",
)
@app_commands.describe(
    text="The text to translate",
    to="The language to translate to",
    from_lang="The language to translate from (defaults to auto-detect)",
)
async def translate(
    interaction: Interaction, text: str, to: str, from_lang: str = "auto"
):
    translated = translator.translate(text, dest=to, src=from_lang)
    await interaction.response.send_message(
        embed=create_translate_embed(translated, interaction=interaction)
    )


client.run(cfg["TOKEN"])
