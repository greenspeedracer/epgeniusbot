
import discord
from discord import app_commands, Permissions
from discord.ext import commands, tasks
from discord.ui import View, Select
from discord.app_commands import MissingAnyRole
import re
import os
import sys
import asyncio
import aiohttp
from thefuzz import fuzz, process
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("EPGENIUSBOT_TOKEN")
MOD_ROLE_IDS = list(map(int, os.getenv("MOD_ROLE_IDS", "").split(",")))
GSR_GUILD_ID = int(os.getenv("GSR_GUILD_ID"))
EPGENIUS_GUILD_ID = int(os.getenv("EPGENIUS_GUILD_ID"))
GSR_GUILD = discord.Object(id=int(os.getenv("GSR_GUILD_ID")))
EPGENIUS_GUILD = discord.Object(id=int(os.getenv("EPGENIUS_GUILD_ID")))
ALL_GUILDS = [GSR_GUILD, EPGENIUS_GUILD]
MODCHANNEL_ID = int(os.getenv("MODCHANNEL_ID"))
MODCHANNEL = None
MOD_MENTIONS = " ".join([f"<@&{role_id}>" for role_id in MOD_ROLE_IDS])
REPO_URL = "http://httpbin.org/status/500"
CHECK_INTERVAL = 60
TIMEOUT = 10

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
    {"number": 18, "owner": "CorB3n", "provider": "Trex", "epg_url": "https://xmltvfr.fr/xmltv/xmltv_fr.xml.gz"},
    {"number": 19, "owner": "AMMAR", "provider": "Strong", "epg_url": "https://raw.githubusercontent.com/ammartaha/EPG/refs/heads/master/Guide.xml"},
    {"number": 20, "owner": "GanjaRelease", "provider": "Strong", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg6.xml.gz"},
    {"number": 21, "owner": "NewEraSCTV", "provider": "Strong", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg21.xml.gz"},
    {"number": 23, "owner": "JayNowa", "provider": "Trex", "epg_url": "https://github.com/ferteque/Curated-M3U-Repository/raw/refs/heads/main/epg23.xml.gz"},
]

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

bot.last_repo_status = None

@tasks.loop(seconds=CHECK_INTERVAL)
async def check_repo_status():
    status_code, error_type, error_msg = await check_site_status(REPO_URL, TIMEOUT)
    current_status = f"{status_code}:{error_type}"
    
    if current_status != bot.last_repo_status:
        if status_code != 200:
            await send_repo_alert(status_code, error_type, error_msg)
        elif bot.last_repo_status is not None:
            await send_repo_recovery_alert()
        bot.last_repo_status = current_status

@check_repo_status.before_loop
async def before_check_repo_status():
    await bot.wait_until_ready()

async def check_site_status(url, timeout):
    try:
        timeout_config = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async with session.get(url) as response:
                status = response.status
                if status == 200:
                    return (200, "OK", "")
                else:
                    return (status, f"HTTP_{status}", f"HTTP {status}")
    except asyncio.TimeoutError:
        return (0, "TIMEOUT", f"Request timed out after {timeout} seconds")
    except aiohttp.ClientConnectorError as e:
        return (0, "CONNECTION_ERROR", f"Connection failed: {str(e)}")
    except aiohttp.ClientSSLError as e:
        return (0, "SSL_ERROR", f"SSL/TLS error: {str(e)}")
    except aiohttp.InvalidURL as e:
        return (0, "INVALID_URL", f"Invalid URL: {str(e)}")
    except aiohttp.ClientError as e:
        return (0, "CLIENT_ERROR", f"Client error: {str(e)}")
    except Exception as e:
        return (0, "UNKNOWN_ERROR", f"Unexpected error: {type(e).__name__} - {str(e)}")

async def send_repo_alert(status_code, error_type, error_msg):
    if MODCHANNEL is None:
        print(f"MODCHANNEL not initialized")
        return
    
    if status_code == 0:
        status_display = "N/A (Connection Failed)"
    else:
        status_display = str(status_code)
    
    embed = discord.Embed(
        title="🚨 EPGenius Server Down Alert",
        description=f"{MOD_MENTIONS}",
        color=discord.Color.red()
    )
    embed.add_field(name="URL", value=REPO_URL, inline=False)
    embed.add_field(name="Status Code", value=status_display, inline=True)
    embed.add_field(name="Error Type", value=error_type, inline=True)
    if error_msg:
        embed.add_field(name="Error Details", value=error_msg, inline=False)
    
    await MODCHANNEL.send(content=MOD_MENTIONS, embed=embed)

async def send_repo_recovery_alert():
    if MODCHANNEL is None:
        return
    
    embed = discord.Embed(
        title="✅ EPGenius Server Recovered",
        description=f"EPGenius server {REPO_URL} is back online",
        color=discord.Color.green()
    )
    embed.add_field(name="Status", value="200 OK", inline=False)
    
    await MODCHANNEL.send(content=MOD_MENTIONS, embed=embed)

# For sending alerts
# await MODCHANNEL.send(f"{MOD_MENTIONS} Something needs attention!")

# Or in an interaction response
# await interaction.response.send_message(f"{MOD_MENTIONS} Alert sent!")

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

@bot.tree.command(name="killepgbot", description="Kill EPGeniusBot")
@app_commands.default_permissions(manage_messages=True) 
@app_commands.checks.has_any_role(*MOD_ROLE_IDS)
async def killepgbot(interaction: discord.Interaction):
    await interaction.response.send_message("Killing EPGeniusBot", ephemeral=True)
    await bot.close()

@bot.tree.error
async def on_app_command_error(interaction, error):
    if isinstance(error, MissingAnyRole):
        await interaction.response.send_message(
            "You don't have the required role(s) to run this command.",
            ephemeral=True
        )
    else:
        print(f"Unhandled error: {error}")

class OwnerSelect(Select):
    def __init__(self, owners, playlists):
        options = [discord.SelectOption(label=owner) for owner in owners]
        super().__init__(placeholder="Choose an owner...", min_values=1, max_values=1, options=options)
        self.playlists = playlists

    async def callback(self, interaction: discord.Interaction):
        selected_owner = self.values[0]
        matched_playlists = [p for p in self.playlists if p.get("owner") == selected_owner]

        embed = discord.Embed(title=f"Playlists for owner '{selected_owner}'", color=discord.Color.blue())
        for p in matched_playlists:
            epg_url = p.get("epg_url", "No EPG URL")
            embed.add_field(
                name=f"#{p['number']} - {selected_owner}",
                value=f"Provider: {p.get('provider', 'N/A')}\nEPG: {epg_url}",
                inline=False,
            )
        await interaction.response.edit_message(embed=embed, view=None)

class OwnerSelectView(View):
    def __init__(self, owners, playlists):
        super().__init__(timeout=60)
        self.add_item(OwnerSelect(owners, playlists))

@bot.tree.command(name="epg", description="Lookup EPG URL by Number or Owner. Type `List` to See All. Type `Owner` to Select from Owners.")
@app_commands.describe(query="Playlist number, owner name, `list`, or `owner`.")
async def epglookup(interaction: discord.Interaction, query: str):

    playlists = PLAYLISTS

    if query.lower() == "list":
        embed = discord.Embed(title="All Playlists", color=discord.Color.blue())
        for p in playlists:
            epg_display = p['epg_url'] if p['epg_url'] and p['epg_url'].lower() not in ["n/a", "use provider’s epg"] else "No EPG URL"
            owner_display = p['owner'] or "N/A"
            embed.add_field(
                name=f"#{p['number']} - {owner_display}",
                value=f"Provider: {p['provider']}\nEPG: {epg_display}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if query.lower() == "owner":
        owners = sorted({p['owner'] for p in playlists if p.get("owner")})
        if not owners:
            await interaction.response.send_message("No owners found.", ephemeral=True)
            return
        view = OwnerSelectView(owners, playlists)
        await interaction.response.send_message("Select an owner:", view=view, ephemeral=True)
        return

    try:
        number_query = int(query)
        playlist = next((p for p in playlists if p["number"] == number_query), None)
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
        owners = [p["owner"] for p in playlists if p.get("owner")]
        matches = process.extract(query, owners, scorer=fuzz.WRatio)
        filtered_matches = [m for m in matches if m[1] >= 80]

        if not filtered_matches:
            owners = sorted(set(owners))
            view = OwnerSelectView(owners, playlists)
            await interaction.response.send_message(f"No close matches found for '{query}'. Please select an owner:", view=view, ephemeral=True)
            return

        embed = discord.Embed(title=f"Playlists matching '{query}'", color=discord.Color.blue())
        seen_owners = set()

        for match_name, score in filtered_matches:
            if match_name in seen_owners:
                continue
            seen_owners.add(match_name)

            matched_playlists = [p for p in playlists if p["owner"] == match_name]
            for p in matched_playlists:
                epg_display = p['epg_url'] if p['epg_url'] and p['epg_url'].lower() not in ["n/a", "use provider’s epg"] else "No EPG URL"
                embed.add_field(
                    name=f"#{p['number']} - {p['owner']} (score {score})",
                    value=f"Provider: {p['provider']}\nEPG: {epg_display}",
                    inline=False
                )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    print(f"Mod Role IDs: {MOD_ROLE_IDS}")
    print(f"GSR Guild ID: {GSR_GUILD_ID}")
    print(f"EPGenius Guild ID: {EPGENIUS_GUILD_ID}")

    global MODCHANNEL
    MODCHANNEL = bot.get_channel(MODCHANNEL_ID)
    if MODCHANNEL:
        print(f"Mod channel found: {MODCHANNEL.name}")
    else:
        print(f"Warning: Could not find mod channel with ID {MODCHANNEL_ID}")
    
    if not check_repo_status.is_running():
        check_repo_status.start()
        print(f"EPGenius server status monitoring started for {REPO_URL}")

    synced_global = await bot.tree.sync()
    print(f"Synced {len(synced_global)} global commands: {[cmd.name for cmd in synced_global]}")

    for guild_obj in ALL_GUILDS:
        guild = bot.get_guild(guild_obj.id)
        guild_name = guild.name if guild else "Unknown"
        try:
            synced = await bot.tree.sync(guild=guild_obj)
            print(f"Synced {len(synced)} commands to guild {guild_name} ({guild_obj.id})")
        except Exception as e:
            print(f"Failed to sync to guild {guild_name} ({guild_obj.id}): {e}")

    print(f"{bot.user} is fully ready!")

bot.run(TOKEN)