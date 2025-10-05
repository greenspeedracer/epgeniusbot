
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
import json
from typing import List
from urllib.parse import quote
from datetime import datetime
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
REPO_URL = "http://repo-server.site"
CHECK_INTERVAL = 60
TIMEOUT = 10
CACHED_PLAYLISTS = None
PLAYLIST_CACHE_FILE = "playlists_cache.json"
PLAYLIST_URL = "http://repo-server.site/playlists"

FILEID_PATTERN = re.compile(r"/file/d/([a-zA-Z0-9_-]+)")

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


logo_cache = []
cache_timestamp = 0

class LogoSelectView(View):
    def __init__(self, logos):
        super().__init__(timeout=60)
        
        options = [
            discord.SelectOption(label=logo['name'], value=logo['name'])
            for logo in logos[:25] 
        ]
        
        select = Select(placeholder="Choose a logo...", options=options)
        select.callback = self.select_callback
        self.add_item(select)
        self.logos = {logo['name']: logo for logo in logos}
    
    async def select_callback(self, interaction: discord.Interaction):
        selected_name = interaction.data['values'][0]
        logo = self.logos[selected_name]
        
        embed = discord.Embed(
            title=f"Logo: {logo['name']}",
            color=discord.Color.blue(),
            description=f"[Direct Link]({logo['url']})"
        )
        embed.set_image(url=logo['url'])
        embed.set_footer(text="Source: K-yzu/Logos")
        
        await interaction.response.send_message(embed=embed)

async def fetch_logos_from_github() -> List[dict]:
    url = "https://api.github.com/repos/K-yzu/Logos/git/trees/main?recursive=1"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                logos = [
                    {
                        'name': item['path'].split('/')[-1].replace('.png', ''),
                        'path': item['path'],
                        'url': f"https://raw.githubusercontent.com/K-yzu/Logos/main/{quote(item['path'])}" 
                    }
                    for item in data.get('tree', [])
                    if item['type'] == 'blob' and item['path'].lower().endswith('.png')
                ]
                return logos
            return []

async def get_logo_list() -> List[dict]:
    global logo_cache, cache_timestamp
    import time
    current_time = time.time()
    
    if not logo_cache or (current_time - cache_timestamp) > 3600:
        logo_cache = await fetch_logos_from_github()
        cache_timestamp = current_time
    
    return logo_cache

async def logo_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    logos = await get_logo_list()
    
    matching = [
        logo for logo in logos
        if current.lower() in logo['name'].lower()
    ]
    
    return [
        app_commands.Choice(name=logo['name'], value=logo['name'])
        for logo in matching[:25]
    ]

@bot.tree.command(name="logo", description="Search K-yzu's GitHub Repo for a Channel Logo")
@app_commands.autocomplete(channel=logo_autocomplete)
async def logo_search(interaction: discord.Interaction, channel: str):
    await interaction.response.defer()
    
    logos = await get_logo_list()
    
    exact_match = next((logo for logo in logos if logo['name'].lower() == channel.lower()), None)
    
    if exact_match:
        embed = discord.Embed(
            title=f"Logo: {exact_match['name']}",
            color=discord.Color.blue(),
            description=f"[Direct Link]({exact_match['url']})"
            )
        embed.set_image(url=exact_match['url'])
        embed.add_field(name="Source", value="[📂 K-yzu's Logo Repository](https://github.com/K-yzu/Logos)", inline=False)
        
        await interaction.followup.send(embed=embed)
    else:
        partial_matches = [
            logo for logo in logos
            if channel.lower() in logo['name'].lower()
        ]
        
        if partial_matches:
            view = LogoSelectView(partial_matches)
            await interaction.followup.send("Select a logo:", view=view)
        else:
            await interaction.followup.send(
                f"No logos found matching '{channel}'"
            )

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
        main_error = error_type.replace('_', ' ').title()
        details = error_msg
    else:
        status_display = str(status_code)
        main_error = f"HTTP {status_code}"
        details = None if error_type == f"HTTP_{status_code}" else error_msg

    embed = discord.Embed(
        title="🚨 EPGenius Server Down Alert",
        description=f"{REPO_URL}",
        color=discord.Color.red()
    )
    embed.add_field(name="Status Code", value=status_display, inline=True)
    embed.add_field(name="Error", value=main_error, inline=True)
    if details:
        embed.add_field(name="Details", value=details, inline=False)

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

async def fetch_playlists():
    try:
        timeout_config = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async with session.get(PLAYLIST_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    playlists = []
                    for item in data:
                        playlists.append({
                            "number": item["id"],
                            "owner": item["reddit_user"] if item["reddit_user"] != "N/A" else None,
                            "provider": item["service_name"],
                            "epg_url": item["github_epg_url"]
                        })
                    return playlists
                else:
                    print(f"Failed to fetch playlists: HTTP {response.status}")
                    return None
    except Exception as e:
        print(f"Error fetching playlists: {e}")
        return None

def save_playlist_cache(playlists):
    try:
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "playlists": playlists
        }
        with open(PLAYLIST_CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
        print(f"Playlist cache saved at {cache_data['timestamp']}")
    except Exception as e:
        print(f"Error saving playlist cache: {e}")

def load_playlist_cache():
    try:
        if not os.path.exists(PLAYLIST_CACHE_FILE):
            print("No cache file found")
            return None
        
        with open(PLAYLIST_CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
        
        cache_time = datetime.fromisoformat(cache_data['timestamp'])
        age = datetime.now() - cache_time
        
        print(f"Loading playlist cache from {cache_data['timestamp']} (age: {age})")
        return cache_data['playlists']
    except Exception as e:
        print(f"Error loading playlist cache: {e}")
        return None

async def get_playlists():
    global CACHED_PLAYLISTS
    
    print("Attempting to fetch live playlist data...")
    live_playlists = await fetch_playlists()
    
    if live_playlists:
        print(f"Successfully fetched {len(live_playlists)} playlists from server")
        CACHED_PLAYLISTS = live_playlists
        save_playlist_cache(live_playlists)
        return live_playlists
    
    print("Live fetch failed, attempting to load cache...")
    
    if CACHED_PLAYLISTS:
        print(f"Using in-memory cached playlists ({len(CACHED_PLAYLISTS)} playlists)")
        return CACHED_PLAYLISTS
    
    cached_playlists = load_playlist_cache()
    
    if cached_playlists:
        print(f"Using file cached playlists ({len(cached_playlists)} playlists)")
        CACHED_PLAYLISTS = cached_playlists
        return cached_playlists
    
    print("ERROR: No playlist data available (live fetch failed and no cache exists)")
    return None


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

    await interaction.response.defer(ephemeral=True)

    playlists = await get_playlists()
    
    if playlists is None:
        await interaction.followup.send(
            "Unable to fetch playlist data. The server is down and no cache is available. Please try again later.",
            ephemeral=True
        )
        return

    if query.lower() == "list":
        embeds = []
        current_embed = discord.Embed(title="All Playlists (Page 1)", color=discord.Color.blue())
        field_count = 0
        page_num = 1
        
        for p in playlists:
            epg_display = p['epg_url'] if p['epg_url'] and p['epg_url'].lower() not in ["n/a", "use provider's epg"] else "No EPG URL"
            owner_display = p['owner'] or "N/A"
            
            if field_count >= 25:
                embeds.append(current_embed)
                page_num += 1
                current_embed = discord.Embed(title=f"All Playlists (Page {page_num})", color=discord.Color.blue())
                field_count = 0
            
            current_embed.add_field(
                name=f"#{p['number']} - {owner_display}",
                value=f"Provider: {p['provider']}\nEPG: {epg_display}",
                inline=False
            )
            field_count += 1
        
        if field_count > 0:
            embeds.append(current_embed)
        
        if len(embeds) == 1:
            await interaction.followup.send(embed=embeds[0], ephemeral=True)
        else:
            await interaction.followup.send(embed=embeds[0], ephemeral=True)
            for embed in embeds[1:]:
                await interaction.followup.send(embed=embed, ephemeral=True)
        return

    if query.lower() == "owner":
        owners = sorted({p['owner'] for p in playlists if p.get("owner")})
        if not owners:
            await interaction.followup.send("No owners found.", ephemeral=True)
            return
        view = OwnerSelectView(owners, playlists)
        await interaction.followup.send("Select an owner:", view=view, ephemeral=True)
        return

    try:
        number_query = int(query)
        playlist = next((p for p in playlists if p["number"] == number_query), None)
        if not playlist:
            await interaction.followup.send(f"No playlist found for #{number_query}.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Playlist #{playlist['number']} EPG Info", color=discord.Color.blue())
        embed.add_field(name="Owner", value=playlist['owner'] or "N/A", inline=True)
        embed.add_field(name="Provider", value=playlist['provider'], inline=True)
        epg_url = playlist['epg_url'] or "No EPG URL available"
        embed.add_field(name="EPG URL", value=epg_url, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    except ValueError:
        owners = [p["owner"] for p in playlists if p.get("owner")]
        matches = process.extract(query, owners, scorer=fuzz.WRatio)
        filtered_matches = [m for m in matches if m[1] >= 80]

        if not filtered_matches:
            owners = sorted(set(owners))
            view = OwnerSelectView(owners, playlists)
            await interaction.followup.send(f"No close matches found for '{query}'. Please select an owner:", view=view, ephemeral=True)
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
        await interaction.followup.send(embed=embed, ephemeral=True)

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