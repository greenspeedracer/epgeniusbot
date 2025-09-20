import discord
from discord import app_commands
from discord.ext import commands
import re

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

file_id_pattern = re.compile(r"/file/d/([a-zA-Z0-9_-]+)")

@bot.tree.command(name="playlist", description="Convert Google Drive share link into playlist link")
@app_commands.describe(url="Google Drive share URL")
async def gdrive(interaction: discord.Interaction, url: str):
    match = file_id_pattern.search(url)
    if not match:
        await interaction.response.send_message("Invalid Google Drive file URL format.", ephemeral=True)
        return

    file_id = match.group(1)
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=true"
    await interaction.response.send_message(f"Direct download link:\n{download_url}", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} and commands synced to guild {GUILD_ID}!")

bot.run(os.environ["EPGBOT_TOKEN"])
