
import discord
from discord import app_commands
from discord.ext import commands
import re
import os
from thefuzz import process
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("EPGENIUSBOT_TOKEN")
ADMINS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
GSR_GUILD = discord.Object(id=int(os.getenv("GSR_GUILD_ID")))
EPGENIUS_GUILD = discord.Object(id=int(os.getenv("EPGENIUS_GUILD_ID")))
ALL_GUILDS = [GSR_GUILD, EPGENIUS_GUILD]

FILEID_PATTERN = re.compile(r"/file/d/([a-zA-Z0-9_-]+)")

PLAYLISTS = [
    {"number": 1, "owner": "ferteque", "provider": "Strong", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg1.xml.gz"},
    {"number": 2, "owner": "jams", "provider": "Strong", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg2.xml.gz"},
    {"number": 3, "owner": None, "provider": "France OTT", "epg_url": None},
    {"number": 4, "owner": "edsanchez", "provider": "Eagle", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg4.xml.gz"},
    {"number": 5, "owner": None, "provider": "Mega", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg5.xml.gz"},
    {"number": 6, "owner": "GanjaRelease", "provider": "Strong", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg6.xml.gz"},
    {"number": 7, "owner": "SouthwestBudz", "provider": "Trex", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg7.xml.gz"},
    {"number": 8, "owner": "GanjaRelease", "provider": "Lion", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg8.xml.gz"},
    {"number": 9, "owner": "GanjaRelease", "provider": "Trex", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg9.xml.gz"},
    {"number": 10, "owner": None, "provider": "Strong", "epg_url": "https://epg.722222227.xyz/epg/0/0_nodummy.xml.gz"},
    {"number": 11, "owner": "smauggmg", "provider": "Strong", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg11.xml.gz"},
    {"number": 12, "owner": "thedoobles", "provider": "Strong", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg12.xml.gz"},
    {"number": 13, "owner": "ferteque", "provider": "Strong", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg13.xml.gz"},
    {"number": 14, "owner": "tropaz", "provider": "Strong", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg14.xml.gz"},
    {"number": 15, "owner": "tropaz", "provider": "Trex", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg15.xml.gz"},
    {"number": 16, "owner": "CorB3n", "provider": "Eagle", "epg_url": "https://xmltvfr.fr/xmltv/xmltv_fr.xml.gz"},
    {"number": 17, "owner": "OldJob8069", "provider": "B1G", "epg_url": "Use Provider’s EPG"},
    {"number": 18, "owner": "Corb3n", "provider": "Trex", "epg_url": "https://xmltvfr.fr/xmltv/xmltv_fr.xml.gz"},
    {"number": 19, "owner": "AMMAR", "provider": "Strong", "epg_url": "https://raw.githubusercontent.com/ammartaha/EPG/refs/heads/master/Guide.xml"},
    {"number": 20, "owner": "GanjaRelease", "provider": "Strong", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg6.xml.gz"},
    {"number": 21, "owner": "NewEraSCTV", "provider": "Strong", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg21.xml.gz"},
    {"number": 23, "owner": "JayNowa", "provider": "Trex", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg23.xml.gz"},
]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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

@bot.tree.command(name="syncgsr", guild=GSR_GUILD, description="Sync Commands to the GSR Server")
async def syncgsr(interaction: discord.Interaction):
    if interaction.user.id not in ADMINS:
        await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    bot.tree.copy_global_to(guild=GSR_GUILD)
    synced = await interaction.client.tree.sync(guild=GSR_GUILD) 
    await interaction.followup.send(f"Commands synced to GSR guild {GSR_GUILD.id}. Synced {len(synced)} commands.", ephemeral=True)

@bot.tree.command(name="syncepgenius", guild=GSR_GUILD, description="Sync Commands to the EPGenius Server")
async def syncepgenius(interaction: discord.Interaction):
    if interaction.user.id not in ADMINS:
        await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    bot.tree.copy_global_to(guild=EPGENIUS_GUILD)
    synced = await interaction.client.tree.sync(guild=EPGENIUS_GUILD) 
    await interaction.followup.send(f"Commands synced to EPGenius guild {EPGENIUS_GUILD.id}. Synced {len(synced)} commands.", ephemeral=True)

@bot.tree.command(name="epg", description="Lookup EPG URL by Playlist Number or Owner. Type List to See All.")
@app_commands.describe(query="Playlist number, owner or 'list'")
async def epglookup(interaction: discord.Interaction, query: str):
    if query.lower() == "list":
        embed = discord.Embed(title="All Playlists", color=discord.Color.blue())
        for p in PLAYLISTS:
            epg_display = p['epg_url'] if p['epg_url'] and p['epg_url'].lower() not in ["n/a", "use provider’s epg"] else "No EPG URL"
            owner_display = p['owner'] or "N/A"
            embed.add_field(
                name=f"#{p['number']} - {owner_display}",
                value=f"Provider: {p['provider']}\nEPG: {epg_display}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        number_query = int(query)
        playlist = next((p for p in PLAYLISTS if p["number"] == number_query), None)
        if not playlist:
            await interaction.response.send_message(f"No playlist found for #{number_query}.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Playlist #{playlist['number']} EPG Info", color=discord.Color.blue())
        embed.add_field(name="Owner", value=playlist['owner'] or "N/A", inline=True)
        embed.add_field(name="Provider", value=playlist['provider'], inline=True)
        epg_url = playlist['epg_url'] or "No EPG URL available"
        embed.add_field(name="EPG URL", value=epg_url, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    except ValueError:
        owners = [p["owner"] for p in PLAYLISTS if p["owner"]]
        matches = process.extract(query, owners, scorer=process.fuzz.token_sort_ratio)
        filtered_matches = [m for m in matches if m[1] >= 60]

        if not filtered_matches:
            await interaction.response.send_message(f"No close matches found for '{query}'.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Playlists matching '{query}'", color=discord.Color.blue())
        seen_owners = set()

        for match_name, score in filtered_matches:
            if match_name in seen_owners:
                continue
            seen_owners.add(match_name)

            matched_playlists = [p for p in PLAYLISTS if p["owner"] == match_name]
            for p in matched_playlists:
                epg_display = p['epg_url'] if p['epg_url'] and p['epg_url'].lower() not in ["n/a", "use provider’s epg"] else "No EPG URL"
                embed.add_field(
                    name=f"#{p['number']} - {p['owner']}",
                    value=f"Provider: {p['provider']}\nEPG: {epg_display}",
                    inline=False
                )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync(guild=EPGENIUS_GUILD)
    print(f'{bot.user} is online!')
    print(f"GSR Guild: {GSR_GUILD.id}")
    print(f"EPGenius Guild: {EPGENIUS_GUILD.id}")
    print(f"Admins: {ADMINS}")
    
    for guild in ALL_GUILDS:
        guild_commands = [cmd.name for cmd in bot.tree.get_commands(guild=guild)]
        print(f"{guild.id}: {len(guild_commands)} commands - {guild_commands}")

bot.run(TOKEN)
