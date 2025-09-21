
import discord
from discord import app_commands
from discord.ext import commands
import re
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("EPGENIUSBOT_TOKEN")
ADMINS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
GSR_GUILD = discord.Object(id=int(os.getenv("GSR_GUILD_ID")))
EPGENIUS_GUILD = discord.Object(id=int(os.getenv("EPGENIUS_GUILD_ID")))

FILEID_PATTERN = re.compile(r"/file/d/([a-zA-Z0-9_-]+)")

intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync(guild=GSR_GUILD)
        print(f"Logged in as {self.user}. Commands synced to guild {GSR_GUILD.id} on startup.")

bot = MyBot()

@bot.tree.command(name="playlist", description="Convert Google Drive Playlist Share Link into Playlist Export Link")
@app_commands.describe(url="Google Drive Playlist Share Link")
async def gdrive(interaction: discord.Interaction, url: str):
    match = FILEID_PATTERN.search(url)
    if not match:
        await interaction.response.send_message(
            "The Google Drive playlist share link is invalid. Please log into your Google Drive, right click the EPGenius playlist, and choose `Share > Copy Link`.",
            ephemeral=True,
        )
        return
    file_id = match.group(1)
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=true"
    await interaction.response.send_message(f"Playlist Export Link:\n{download_url}", ephemeral=True)

@bot.tree.command(name="syncgsr", description="Sync Commands to GSR")
async def syncgsr(interaction: discord.Interaction):
    if interaction.user.id in ADMINS:
        await bot.tree.sync(guild=GSR_GUILD)
        await interaction.response.send_message(f"Commands synced to guild {GSR_GUILD.id}.", ephemeral=True)
    else:
        await interaction.response.send_message("You do not have permission to run this.", ephemeral=True)    


@bot.tree.command(name="syncepgenius", description="Sync Commands to EPGenius Server")
async def syncepgenius(interaction: discord.Interaction):
    if interaction.user.id in ADMINS:
        await bot.tree.sync(guild=EPGENIUS_GUILD)
        await interaction.response.send_message(f"Commands synced to guild {EPGENIUS_GUILD.id}.", ephemeral=True)
    else:
        await interaction.response.send_message("You do not have permission to run this.", ephemeral=True)

bot.run(TOKEN)
