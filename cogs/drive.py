from typing import Optional

import discord
import io
import zipfile
from discord import app_commands, Interaction, Role
from discord.ext import commands
from oauth2client.service_account import ServiceAccountCredentials  # type: ignore
from pydrive2.auth import GoogleAuth  # type: ignore
from pydrive2.drive import GoogleDrive  # type: ignore

from bot import TranslatorBot


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
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(description="Download unreleased charts")
    async def download(self, interaction: Interaction, title: str):
        await interaction.response.defer(thinking=True)
        folders = self.drive.ListFile({
            "q": f"'{self.unreleased_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
        }).GetList()

        folder = next((x for x in folders if x["title"] == title), None)
        if folder is None:
            await interaction.response.send_message("Chart not found")
            return
        
        files = self.drive.ListFile({
            "q": f"'{folder['id']}' in parents"
        }).GetList()

        has_pv = False
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for file in files:
                if "pv" in file["title"]:
                    has_pv = True
                    continue
                z.writestr(f"{title}/{file['title']}", file.GetContentIOBuffer().read())
        
        buf.seek(0)
        content = f"PV not included due to Discord's 8MB limit." if has_pv else ""
        await interaction.followup.send(content=content, file=discord.File(fp=buf, filename=f"{title}.zip"))

        
async def setup(bot: TranslatorBot):
    await bot.add_cog(DriveCog(bot))
