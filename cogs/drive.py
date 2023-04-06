from typing import Optional

import discord
import discord.ui
import io
import zipfile
from discord import app_commands, Interaction
from discord.ext import commands
from oauth2client.service_account import ServiceAccountCredentials  # type: ignore
from pydrive2.auth import GoogleAuth  # type: ignore
from pydrive2.drive import GoogleDrive  # type: ignore

from bot import TranslatorBot


async def zip_folder(drive: GoogleDrive, id: str, parent_folder: str, guild: Optional[discord.Guild] = None) -> tuple[io.BytesIO, bool]:
    filesize_limit = guild.filesize_limit if guild is not None else 25 * 1000 * 1000

    files = drive.ListFile({
        "q": f"'{id}' in parents"
    }).GetList()

    estimated_file_size = (30 + 16 + 46 + 52) * len(files) + 22
    for file in files:
        arcname = f"{parent_folder}/{file['title']}"
        estimated_file_size += 2 * len(arcname.encode("utf-8")) + int(file["fileSize"])
    exclude_pv = estimated_file_size > filesize_limit
    
    excluded_pv = False
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for file in files:
            if "pv" in file["title"] and exclude_pv:
                excluded_pv = True
                continue
            z.writestr(f"{parent_folder}/{file['title']}", file.GetContentIOBuffer().read())
    
    buf.seek(0)
    return buf, excluded_pv


class DriveSelectionView(discord.ui.View):
    def __init__(self, interaction: Interaction, drive: GoogleDrive, options: list[tuple[str, str]]):
        super().__init__(timeout=120)
        self.interaction = interaction
        self.drive = drive
        self.mapping = {x[1]: x[0] for x in options}
        self.dropdown.options = [discord.SelectOption(label=x[0], value=x[1]) for x in options]

    async def on_timeout(self) -> None:
        for child in self.children:
            if hasattr(child, "disabled"):
                child.disabled = True  # type: ignore
        await self.interaction.edit_original_response(view=self)
    
    @discord.ui.select(placeholder="Select a song...")
    async def dropdown(self, interaction: Interaction, select: discord.ui.Select):
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        await interaction.response.defer(thinking=True)

        id = select.values[0]
        title = self.mapping[id]
        
        buf, has_pv = await zip_folder(self.drive, id, title)

        content = f"PV not included due to Discord's 8MB limit." if has_pv else ""
        await interaction.followup.send(content=content, file=discord.File(fp=buf, filename=f"{title}.zip"))
        

class DriveCog(commands.GroupCog, name="Drive", group_name="unreleased", group_description="Unreleased charts"):
    minimum_download_role: Optional[int] = None
    
    def __init__(self, bot: TranslatorBot) -> None:
        self.bot = bot

        if (client_secret := bot.cfg.get("DRIVE_CLIENT_SECRET_PATH")) is None:
            raise RuntimeError("DRIVE_CLIENT_SECRET_PATH is not defined in .env")
        if (unreleased_folder_id := bot.cfg.get("UNRELEASED_FOLDER_ID")) is None:
            raise RuntimeError("UNRELEASED_FOLDER_ID is not defined in .env")

        self.unreleased_folder_id = unreleased_folder_id
        
        scope = ["https://www.googleapis.com/auth/drive"]
        gauth = GoogleAuth()
        gauth.auth_method = 'service'
        gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(client_secret, scope)
        
        self.drive = GoogleDrive(gauth)
        self.drive.GetAbout()
    
    @app_commands.command(description="List unreleased charts")
    async def list(self, interaction: Interaction):
        folders = self.drive.ListFile({
            "q": f"'{self.unreleased_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
        }).GetList()

        embed = discord.Embed(
            title="Unreleased Songs",
            description="\n".join([x["title"] for x in folders])
        )
        view = DriveSelectionView(interaction, self.drive, [(x["title"], x["id"]) for x in folders])
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(description="Download unreleased charts")
    async def download(self, interaction: Interaction, title: str):
        await interaction.response.defer(thinking=True)
        folders = self.drive.ListFile({
            "q": f"'{self.unreleased_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and title contains '{title}'"
        }).GetList()

        folder = folders[0]
        id = folder["id"]
        title = folder["title"]

        buf, excluded_pv = await zip_folder(self.drive, id, title, interaction.guild)

        content = f"PV not included due to Discord's 8MB limit." if excluded_pv else ""
        await interaction.followup.send(content=content, file=discord.File(fp=buf, filename=f"{title}.zip"))

        
async def setup(bot: TranslatorBot):
    await bot.add_cog(DriveCog(bot))
