from pathlib import Path

from dotenv import dotenv_values

BOT_DIR = Path(__file__).absolute().parent
cfg = dotenv_values(BOT_DIR / ".env")

import asyncio
import logging
import logging.handlers
import sys
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import Bot
from dotenv import dotenv_values
from googletrans import Translator


class TranslatorBot(Bot):
    cfg: dict[str, str | None]
    translator: Translator

    def __init__(self, *args, testing_guild_id: Optional[int] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.testing_guild_id = testing_guild_id

    async def setup_hook(self) -> None:
        if self.testing_guild_id:
            guild = discord.Object(id=self.testing_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)


async def startup():
    logger = logging.getLogger("discord")
    logger.setLevel(logging.DEBUG)

    handler = logging.handlers.RotatingFileHandler(
        filename="discord.log",
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    (intents := discord.Intents.default()).message_content = True

    guild_id = cfg.get("GUILD_ID")
    bot = TranslatorBot(command_prefix=commands.when_mentioned_or(">"), intents=intents, testing_guild_id=int(guild_id) if guild_id else None)
    bot.cfg = cfg
    bot.translator = Translator()

    for file in (BOT_DIR / "cogs").glob("*.py"):
        if file.stem in ["__init__"]:
            continue
        try:
            await bot.load_extension(f"cogs.{file.stem}")
            print(f"Loaded cogs.{file.stem}")
        except Exception as e:
            print(f"Failed to load extension cogs.{file.stem}")
            print(f"{type(e).__name__}: {e}")

    if (token := cfg.get("TOKEN")) is None:
        sys.exit(
            "[ERROR] Token not found, make sure 'TOKEN' is set in the '.env' file. Exiting."
        )

    try:
        await bot.start(token)
    except discord.LoginFailure:
        sys.exit(
            "[ERROR] Token not found, make sure 'TOKEN' is set in the '.env' file. Exiting."
        )
    except discord.PrivilegedIntentsRequired:
        sys.exit(
            "[ERROR] Message Content Intent not enabled, go to 'https://discord.com/developers/applications' and enable the Message Content Intent. Exiting."
        )


if __name__ == "__main__":
    asyncio.run(startup())
