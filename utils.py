import re
from typing import Optional

import discord
import langcodes
from discord import Message, Interaction
from googletrans.models import Translated


DISCORD_SYNTAX_REGEX = re.compile(r"<(a?:.+?:(\d+))>")


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
