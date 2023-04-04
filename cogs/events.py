from discord import Message
from discord.ext import commands
from lingua import Language, LanguageDetectorBuilder

from bot import TranslatorBot
from utils import create_translate_embed, DISCORD_SYNTAX_REGEX


class EventsCog(commands.Cog, name="Events"):
    def __init__(self, bot: TranslatorBot) -> None:
        self.bot = bot

        languages = [Language.ENGLISH, Language.CHINESE, Language.VIETNAMESE, Language.MALAY, Language.TAGALOG, Language.FRENCH, Language.SPANISH, Language.INDONESIAN, Language.JAPANESE]
        self.detector = LanguageDetectorBuilder.from_languages(*languages).build()
    
    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author == self.bot.user:
            return

        if (
            self.bot.cfg["AUTO_TRANSLATE_CATEGORY"]
            and hasattr(message.channel, "category_id")
            and str(message.channel.category_id) not in self.bot.cfg["AUTO_TRANSLATE_CATEGORY"]
        ):
            return

        emotes = DISCORD_SYNTAX_REGEX.findall(message.content)
        sanitized_message = DISCORD_SYNTAX_REGEX.sub(r"<\2>", message.content)

        language = self.detector.detect_language_of(sanitized_message)
        if language is None:
            return
        confidence = self.detector.compute_language_confidence(sanitized_message, language)
        if language != Language.ENGLISH and confidence >= 0.7:
            translated = self.bot.translator.translate(sanitized_message, dest="en")
            if translated.text.lower() != sanitized_message.lower() and translated.src != translated.dest:
                for emote in emotes:
                    translated.text = translated.text.replace(f"<{emote[1]}>", f"<{emote[0]}>")
                await message.reply(
                    embed=create_translate_embed(translated, message=message),
                    mention_author=False,
                )


async def setup(bot: TranslatorBot):
    await bot.add_cog(EventsCog(bot))
