
import discord
from discord import app_commands, Permissions
from discord.ext import commands, tasks
from discord.ui import View, Select, Modal, TextInput, Button
from discord.app_commands import MissingAnyRole
import re
import os
import sys
import asyncio
import aiohttp
import json
import time
import requests
from typing import List
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from thefuzz import fuzz, process
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# VARIABLES
# ============================================================================ 

TOKEN = os.getenv("EPGENIUSBOT_TOKEN")
MOD_ROLE_IDS = list(map(int, os.getenv("MOD_ROLE_IDS", "").split(",")))
GSR_GUILD_ID = int(os.getenv("GSR_GUILD_ID"))
EPGENIUS_GUILD_ID = int(os.getenv("EPGENIUS_GUILD_ID"))
GSR_GUILD = discord.Object(id=int(os.getenv("GSR_GUILD_ID")))
EPGENIUS_GUILD = discord.Object(id=int(os.getenv("EPGENIUS_GUILD_ID")))
ALL_GUILDS = [GSR_GUILD, EPGENIUS_GUILD]
BOTLOGCHANNEL_ID = int(os.getenv("BOTLOGCHANNEL_ID"))
BOTLOGCHANNEL = None
MODCHANNEL_ID = int(os.getenv("MODCHANNEL_ID"))
MODCHANNEL = None
SC_UPDATES_CHANNEL_ID = int(os.getenv("SC_UPDATES_CHANNEL_ID"))
SC_UPDATES_CHANNEL = None
MOD_MENTIONS = " ".join([f"<@&{role_id}>" for role_id in MOD_ROLE_IDS])
GSR_ID = int(os.getenv("GSR_ID", ""))
GSR_MENTION = f"<@{GSR_ID}>"
REPO_URL = "https://epgenius.org"
SC_URL = "https://streamcheck.pro"
CHECK_INTERVAL = 60
TIMEOUT = 30
CACHED_PLAYLISTS = None
PLAYLIST_CACHE_FILE = "playlists_cache.json"
PLAYLISTS_URL = "https://epgenius.org/playlists"
BOT_API_TOKEN = os.getenv("BOT_API_TOKEN")
GET_API_URL = os.getenv("GET_API_URL")
POST_API_URL = os.getenv("POST_API_URL")
FILEID_PATTERN = re.compile(r"/file/d/([a-zA-Z0-9_-]+)")
FILEID_REGEX = re.compile(r"(?:/file/d/|id=)([a-zA-Z0-9_-]+)|^([a-zA-Z0-9_-]+)$")

# ============================================================================
# COMMAND ERROR MESSAGES
# ============================================================================ 

MESSAGES = {
    "FREE_DISABLED_MSG": "❌ There may be an issue with your playlist's free updates. Please open a File ID Support [#🎟️〢ticket](https://discord.com/channels/1382432361840509039/1400145242606534710) with your Playlist Key and the error code `Free Update Disabled`",

    "FREE_24_MSG": "⚠️ Please wait 24 hours from playlist creation. Check again after {check_after}.",

    "FREE_MISS_MSG": "❌ There may be an issue with your playlist's free updates. Please open a File ID Support [#🎟️〢ticket](https://discord.com/channels/1382432361840509039/1400145242606534710) with your Playlist Key and the error code `Missing Free Update Sync Timestamp(s): \"{missing_sync}\"`",
    
    "FREE_SYNCLAG_MSG": "❌ There may be an issue with your playlist's free updates. Please open a File ID Support [#🎟️〢ticket](https://discord.com/channels/1382432361840509039/1400145242606534710) with your Playlist Key and the error code `Free Update Sync > 5 Hours`",
    
    "FREE_SYNC_MSG": "⚠️ Your playlist is still syncing. Check again after {check_after}.",
    
    "SUPPORTER_DONATION_MSG": "🦥 To enable supporter updates, please consider [donating to {pl_owner}]({donation_url}). After donating, please open an Unlock Supporter Features [#🎟️〢ticket](https://discord.com/channels/1382432361840509039/1400145242606534710) to activate supporter updates.",

    "SUPPORTER_MISS_MSG": "❌ There may be an issue with your playlist's supporter updates. If it has been more than 24 hours since your Unlock Supporter Features ticket was closed, please open an Unlock Supporter Features [#🎟️〢ticket](https://discord.com/channels/1382432361840509039/1400145242606534710) with your Playlist Key and the error code `Missing Supporter Update Sync Timestamp`",
    
    "SUPPORTER_SYNCLAG_MSG": "❌ There may be an issue with your playlist's supporter updates. Please open an Unlock Supporter Features [#🎟️〢ticket](https://discord.com/channels/1382432361840509039/1400145242606534710) with your Playlist Key and the error code `Supporter Update Sync > 36 Hours`",
    
    "SUPPORTER_THANK_MSG_GENERIC": "🔥 Thank you for your donation! Your support helps keep EPGenius running.",
    
    "USER_LOOKUP_ERROR_MSG": "❌ No matching playlist(s) found. Please ensure you have registered your playlists with the `/playlistregister` command. If you still need help, please visit [#🚑〢help](https://discord.com/channels/1382432361840509039/1383563895913844786).",
    
    "USER_LOOKUP_TIMEOUT_MSG": "⏱️ The lookup failed. Please try again later. If this error persists, please notify a mod in [#🚑〢help](https://discord.com/channels/1382432361840509039/1383563895913844786).",
}

REGISTER_MESSAGES = {
    "PL_REG_THANK_MSG": "✅ Thanks for registering your **{pl_owner}** **#{list_id}** **{provider}** playlist.",
    
    "CREDENTIALS_UPDATE_SUCCESS_MSG": "✅ Credentials for your **{pl_owner}** **#{list_id}** **{provider}** playlist have been updated. Changes will take place on the next automatic update.",
    
    "PL_REG_ERROR_MSG": "❌ The registration failed. Please try again later. If this error persists, please notify a mod in [#🚑〢help](https://discord.com/channels/1382432361840509039/1383563895913844786).",
    
    "PL_REG_DUP_MSG": "ℹ️ This playlist is already registered to you.",
    
    "PL_REG_MISMATCH_MSG": "⚠️ This playlist is already registered to another user. If you believe this is an error, please open a File ID Support [#🎟️〢ticket](https://discord.com/channels/1382432361840509039/1400145242606534710).",
    
    "PL_REG_MISSING_MSG": "❌ Playlist not found. Please check the File ID, Share URL, or Export URL and try again.",
    
    "INVALID_INPUT_MSG": "❌ Invalid input. Please provide a valid File ID, Share URL, or Export URL.",
}

# ============================================================================
# PLAYLIST CACHE SETTINGS
# ============================================================================ 

playlist_cache = {
    "data": None,
    "timestamp": None,
    "ttl": 300
}

# ============================================================================
# DISCORD BOT INTENTS
# ============================================================================ 

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ============================================================================
# EPGENIUS PLAYLIST INFO API CALLS
# ============================================================================ 

async def get_all_user_playlists(duid):
    """Fetch all playlists for a user by DUID"""
    headers = {
        "Authorization": BOT_API_TOKEN,
        "Content-Type": "application/json"
    }
    
    json_data = {
        "duid": duid
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                GET_API_URL, 
                headers=headers, 
                json=json_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 404:
                    return []  # Empty list for 404
                elif response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    print(f"Error: {response.status} - {text}")
                    return None
        except asyncio.TimeoutError:
            print(f"Request timed out for user {duid}")
            return None
        except Exception as e:
            print(f"Request failed: {e}")
            return None

class PlaylistPaginationView(View):
    def __init__(self, records, playlists_data, is_mod=False):
        super().__init__(timeout=180)
        self.records = records
        self.playlists_data = playlists_data
        self.is_mod = is_mod
        self.current_page = 0
        self.max_page = len(records) - 1
        self.message = None

    async def on_timeout(self):
        """Called when the view times out"""
        if self.message:
            try:
                await self.message.edit(view=None)
            except:
                pass  
    
    def get_embed(self):
        """Generate embed for current page"""
        record = self.records[self.current_page]
        list_id = record.get('list_id')
        playlist_details = get_playlist_details(list_id, self.playlists_data)
        
        embed = create_file_info_embed(record, playlist_details, is_mod=self.is_mod)
        
        if self.max_page > 0:
            embed.set_footer(text=f"Playlist {self.current_page + 1} of {self.max_page + 1}")
        
        return embed
    
    def update_buttons(self):
        """Update button states based on current page"""
        for item in self.children:
            if isinstance(item, Button):
                if "Previous" in item.label:
                    item.disabled = (self.current_page == 0)
                elif "Next" in item.label:
                    item.disabled = (self.current_page == self.max_page)
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.max_page:
            self.current_page += 1
            self.update_buttons()
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)


async def fetch_playlists_data():
    """Fetch and cache playlist data from EPGenius API"""
    now = datetime.now(timezone.utc)
    
    if (playlist_cache["data"] is not None and 
        playlist_cache["timestamp"] is not None and 
        (now - playlist_cache["timestamp"]).total_seconds() < playlist_cache["ttl"]):
        return playlist_cache["data"]
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(PLAYLISTS_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    playlist_cache["data"] = data
                    playlist_cache["timestamp"] = now
                    return data
                else:
                    print(f"Failed to fetch playlists: {response.status}")
                    return None
        except Exception as e:
            print(f"Error fetching playlists: {e}")
            return None

def get_playlist_details(list_id, playlists_data):
    """Get additional playlist details from EPGenius playlists API"""
    if not playlists_data:
        return None
    
    for playlist in playlists_data:
        if playlist.get('id') == list_id:
            return {
                'provider': playlist.get('service_name'),
                'pl_owner': playlist.get('reddit_user'),
                'epg_url': playlist.get('github_epg_url'),
                'donation_url': playlist.get('donation_info'),
                'pl_owner_last_update': playlist.get('timestamp'),
                'thank_message': playlist.get('thank_message')
            }
    return None

def build_export_url(drive_file_id):
    """Build Google Drive export URL from file ID"""
    return f"https://drive.google.com/uc?export=download&id={drive_file_id}"

def parse_timestamp(timestamp_str):
    """Convert timestamp string to datetime object"""
    if not timestamp_str or timestamp_str == "NULL":
        return None
    
    formats = [
        '%a, %d %b %Y %H:%M:%S %Z',  
        '%d/%m/%Y',                   
        '%Y-%m-%dT%H:%M:%S.%fZ',    
        '%Y-%m-%dT%H:%M:%SZ',      
        '%Y-%m-%d %H:%M:%S',        
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(timestamp_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    
    print(f"Error parsing timestamp '{timestamp_str}': no matching format found")
    return None

def format_datetime(dt):
    """Format datetime to human-readable string"""
    if not dt:
        return None
    return dt.strftime("%b %d, %Y at %I:%M %p %Z")

def check_timestamp_age(timestamp_str, hours_threshold):
    """Check if timestamp is older than threshold in hours"""
    dt = parse_timestamp(timestamp_str)
    if not dt:
        return None
    
    now = datetime.now(timezone.utc)
    age_hours = (now - dt).total_seconds() / 3600
    return age_hours > hours_threshold

async def get_file_info_async(file_identifier, duid):
    """Fetch file info from API"""
    match = FILEID_REGEX.search(file_identifier)
    if not match:
        return None
    
    file_id = match.group(1) or match.group(2)
    if not file_id:
        return None
    
    headers = {
        "Authorization": BOT_API_TOKEN,
        "Content-Type": "application/json"
    }
    
    json_data = {
        "file_id": file_id,
        "duid": duid
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(GET_API_URL, headers=headers, json=json_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    print(f"Error: {response.status} - {text}")
                    return None
        except Exception as e:
            print(f"Request failed: {e}")
            return None

def create_file_info_embed(record, playlist_details, is_mod=False):
    """Create Discord embed for file info display"""
    embed = discord.Embed(
        title="📁 Playlist Information",
        color=discord.Color.blue()
    )
    
    info_messages = []
    
    playlist_creation_date = parse_timestamp(record.get('uploaded_at'))
    last_update_owner = parse_timestamp(record.get('last_update_owner'))
    pl_owner_last_update_str = playlist_details.get('pl_owner_last_update') if playlist_details else None
    pl_owner_last_update = parse_timestamp(pl_owner_last_update_str) if pl_owner_last_update_str else None
    valid = record.get('valid')
    auto_update = record.get('auto_update')
    now = datetime.now(timezone.utc)
    
    # Row 1: Playlist Owner, Playlist Number, Service Provider
    if playlist_details:
        embed.add_field(
            name="Playlist Owner",
            value=playlist_details['pl_owner'] or "N/A",
            inline=True
        )
    
    embed.add_field(
        name="Playlist Number",
        value=f"`{record.get('list_id')}`",
        inline=True
    )
    
    if playlist_details:
        embed.add_field(
            name="Service Provider",
            value=playlist_details['provider'] or "N/A",
            inline=True
        )
    
    # Row 2: Playlist Link, EPG Link + spacer
    export_url = build_export_url(record.get('drive_file_id'))
    embed.add_field(
        name="Playlist Link",
        value=f"[Download]({export_url})",
        inline=True
    )
    
    if playlist_details and playlist_details.get('epg_url'):
        embed.add_field(
            name="EPG Link",
            value=f"[Download]({playlist_details['epg_url']})",
            inline=True
        )
    
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    
    # Row 3: Free Updates, Last Free Update + spacer
    if not valid:
        embed.add_field(
            name="Free Updates",
            value="❌ Disabled",
            inline=True
        )
        info_messages.append(MESSAGES["FREE_DISABLED_MSG"])
    else:
        embed.add_field(
            name="Free Updates",
            value="✅ Enabled",
            inline=True
        )
        
        if not playlist_creation_date:
            info_messages.append("❌ Error: Missing playlist creation date.")
        else:
            playlist_age = (now - playlist_creation_date).total_seconds() / 3600
            
            if playlist_age <= 24:
                check_after = playlist_creation_date + timedelta(hours=24)
                info_messages.append(MESSAGES["FREE_24_MSG"].format(check_after=format_datetime(check_after)))
            else:
                if not last_update_owner or not pl_owner_last_update:
                    missing_fields = []
                    if not last_update_owner:
                        missing_fields.append("Last Free Update")
                    if not pl_owner_last_update:
                        pl_owner = playlist_details.get('pl_owner', 'Owner') if playlist_details else 'Owner'
                        missing_fields.append(f'Last "{pl_owner}" Update')
                    
                    info_messages.append(MESSAGES["FREE_MISS_MSG"].format(missing_sync=" and ".join(missing_fields)))
                else:
                    if last_update_owner < pl_owner_last_update:
                        owner_update_plus_5h = pl_owner_last_update + timedelta(hours=5)
                        
                        if owner_update_plus_5h < now:
                            info_messages.append(MESSAGES["FREE_SYNCLAG_MSG"])
                        else:
                            info_messages.append(MESSAGES["FREE_SYNC_MSG"].format(check_after=format_datetime(owner_update_plus_5h)))

    if last_update_owner:
        embed.add_field(
            name="Last Free Update",
            value=format_datetime(last_update_owner),
            inline=True
        )
    else:
        embed.add_field(
            name="Last Free Update",
            value="N/A",
            inline=True
        )
    
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    
    # Row 4: Supporter Updates, Last Supporter Update + spacer
    last_update_provider = record.get('last_update_provider')
    
    if auto_update:
        embed.add_field(
            name="Supporter Updates",
            value="✅ Enabled",
            inline=True
        )
        thank_msg = playlist_details.get('thank_message') if playlist_details else None
        if thank_msg:
            info_messages.append(thank_msg)
        else:
            info_messages.append(MESSAGES["SUPPORTER_THANK_MSG_GENERIC"])
        
        if not last_update_provider or last_update_provider == "NULL":
            info_messages.append(MESSAGES["SUPPORTER_MISS_MSG"])
        else:
            is_old = check_timestamp_age(last_update_provider, 36)
            if is_old:
                info_messages.append(MESSAGES["SUPPORTER_SYNCLAG_MSG"])
    else:
        embed.add_field(
            name="Supporter Updates",
            value="❌ Disabled",
            inline=True
        )
        
        donation_url = playlist_details.get('donation_url') if playlist_details else None
        pl_owner = playlist_details.get('pl_owner') if playlist_details else None
        if donation_url:
            donation_msg = MESSAGES["SUPPORTER_DONATION_MSG"].format(
                donation_url=donation_url,
                pl_owner=pl_owner or "the playlist owner"
            )
            info_messages.append(donation_msg)
        else:
            info_messages.append("⚠️ Supporter updates are currently unavailable for this playlist. Please check back later or contact a mod.")
    
    if last_update_provider and last_update_provider != "NULL":
        provider_dt = parse_timestamp(last_update_provider)
        if provider_dt:
            formatted = format_datetime(provider_dt)
            embed.add_field(
                name="Last Supporter Update",
                value=formatted if formatted else "N/A",
                inline=True
            )
        else:
            embed.add_field(
                name="Last Supporter Update",
                value="N/A",
                inline=True
            )
    else:
        embed.add_field(
            name="Last Supporter Update",
            value="N/A",
            inline=True
        )
    
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    
    # Row 5: Last Owner Update, Creation Date, Playlist Key
    pl_owner_name = playlist_details.get('pl_owner') if playlist_details else None
    if pl_owner_name and pl_owner_last_update_str:
        pl_owner_dt = parse_timestamp(pl_owner_last_update_str)
        if pl_owner_dt:
            formatted = format_datetime(pl_owner_dt)
            embed.add_field(
                name=f"Last {pl_owner_name} Update",
                value=formatted if formatted else "N/A",
                inline=True
            )
        else:
            embed.add_field(
                name=f"Last {pl_owner_name} Update",
                value="N/A",
                inline=True
            )
    else:
        embed.add_field(
            name="Last Owner Update",
            value="N/A",
            inline=True
        )
    
    if playlist_creation_date:
        formatted = format_datetime(playlist_creation_date)
        embed.add_field(
            name="Playlist Creation Date",
            value=formatted if formatted else "N/A",
            inline=True
        )
    else:
        embed.add_field(
            name="Playlist Creation Date",
            value="N/A",
            inline=True
        )
    
    embed.add_field(
        name="Playlist Key",
        value=f"`{record.get('id')}`",
        inline=True
    )
    
    # Row 6 (if mod): File ID, Discord User ID, File Owner
    if is_mod:
        embed.add_field(
            name="File ID",
            value=f"`{record.get('drive_file_id')}`",
            inline=True
        )
        
        embed.add_field(
            name="Discord User ID",
            value=f"`{record.get('discord_id')}`",
            inline=True
        )
        
        embed.add_field(
            name="File Owner",
            value=record.get('file_owner') or "N/A",
            inline=True
        )
    
    if info_messages:
        embed.description = "\n\n".join(info_messages)
    
    return embed

# ============================================================================
# EPGENIUS PLAYLIST REGISTRATION API CALLS
# ============================================================================  

async def register_file_async(file_identifier, duid):
    """Register a file with the API"""
    match = FILEID_REGEX.search(file_identifier)
    if not match:
        return {"error": "invalid_input"}
    
    file_id = match.group(1) or match.group(2)
    if not file_id:
        return {"error": "invalid_input"}
    
    headers = {
        "Authorization": BOT_API_TOKEN,
        "Content-Type": "application/json"
    }
    
    data = {
        "file_id": file_id,
        "duid": duid
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(POST_API_URL, headers=headers, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "error": "api_error",
                        "status": response.status,
                        "message": await response.text()
                    }
        except Exception as e:
            return {"error": "request_failed", "exception": str(e)}


def handle_registration_response(result, playlists_data=None):
    """Process registration API response and return appropriate message"""
    if not result:
        return REGISTER_MESSAGES["PL_REG_ERROR_MSG"], None
    
    if "error" in result:
        error_type = result.get("error")
        if error_type == "invalid_input":
            return REGISTER_MESSAGES["INVALID_INPUT_MSG"], None
        elif error_type in ("api_error", "request_failed"):
            return REGISTER_MESSAGES["PL_REG_ERROR_MSG"], None
    
    status = result.get("status")
    
    if status == "duplicate":
        return REGISTER_MESSAGES["PL_REG_DUP_MSG"], None
    if status == "mismatch":
        return REGISTER_MESSAGES["PL_REG_MISMATCH_MSG"], None
    if status == "not_found":
        return REGISTER_MESSAGES["PL_REG_MISSING_MSG"], None
    
    if status == "ok":
        record = result.get("file")
        
        if not record:
            return "✅ Registration successful! Your playlist has been registered.", None
        
        list_id = record.get("list_id")
        provider = "N/A"
        pl_owner = "N/A"
        
        if playlists_data and list_id:
            for playlist in playlists_data:
                if playlist.get("id") == list_id:
                    provider = playlist.get("service_name", "N/A")
                    pl_owner = playlist.get("reddit_user", "N/A")
                    break
        
        message = REGISTER_MESSAGES["PL_REG_THANK_MSG"].format(
            pl_owner=pl_owner,
            list_id=list_id,
            provider=provider
        )
        return message, record
    
    return REGISTER_MESSAGES["PL_REG_ERROR_MSG"], None

# ============================================================================
# PROVIDER SERVICEINFO API CALLS
# ============================================================================      

class ServiceInfoModal(Modal, title="Service Information"):  
    dns = TextInput(
        label="DNS/URL",
        placeholder="http://example.com",
        required=True,
        max_length=200
    )
    
    username = TextInput(
        label="Username",
        placeholder="Username",
        required=True,
        max_length=100
    )
    
    password = TextInput(
        label="Password",
        placeholder="Password",
        required=True,
        max_length=100,
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        url = f"{self.dns.value}/player_api.php?username={self.username.value}&password={self.password.value}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                user_info = data.get('user_info', {})
                server_info = data.get('server_info', {})

                cred_embed = discord.Embed(
                    title="🔐 Service Credentials",
                    color=discord.Color.blue()
                )
                cred_text = f"**DNS/URL:** ||{server_info.get('url', 'N/A')}||\n"
                cred_text += f"**Username:** ||{user_info.get('username', 'N/A')}||\n"
                cred_text += f"**Password:** ||{user_info.get('password', 'N/A')}||"
                cred_embed.description = cred_text

                await interaction.followup.send(embed=cred_embed, ephemeral=True)

                embed = discord.Embed(
                    title="📊 Service Information",
                    color=discord.Color.blue()
                )

                user_text = "__**👤 User Information**__\n\n"
                if user_info.get('message'):
                    user_text += f"**Message:** {user_info['message']}\n"
                if user_info.get('auth') is not None:
                    user_text += f"**Auth:** {'Yes' if user_info['auth'] == 1 else 'No'}\n"
                if user_info.get('status'):
                    user_text += f"**Status:** {user_info['status']}\n"
                if user_info.get('exp_date'):
                    exp_dt = datetime.fromtimestamp(int(user_info['exp_date']))
                    user_text += f"**Expiration:** {exp_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                if user_info.get('is_trial') is not None:
                    user_text += f"**Trial:** {'Yes' if user_info['is_trial'] == '1' else 'No'}\n"
                if user_info.get('active_cons') is not None:
                    user_text += f"**Active Connections:** {user_info['active_cons']}\n"
                if user_info.get('created_at'):
                    created_dt = datetime.fromtimestamp(int(user_info['created_at']))
                    user_text += f"**Created:** {created_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                if user_info.get('max_connections'):
                    user_text += f"**Max Connections:** {user_info['max_connections']}\n"
                if user_info.get('allowed_output_formats'):
                    formats = ', '.join(user_info['allowed_output_formats']) if isinstance(user_info['allowed_output_formats'], list) else user_info['allowed_output_formats']
                    user_text += f"**Output Formats:** {formats}"

                embed.add_field(name="\u200b", value=user_text, inline=False)

                server_text = "__**🖥️ Server Information**__\n\n"
                if server_info.get('port'):
                    server_text += f"**Port:** {server_info['port']}\n"
                if server_info.get('https_port'):
                    server_text += f"**HTTPS Port:** {server_info['https_port']}\n"
                if server_info.get('server_protocol'):
                    server_text += f"**Protocol:** {server_info['server_protocol']}\n"
                if server_info.get('rtmp_port'):
                    server_text += f"**RTMP Port:** {server_info['rtmp_port']}\n"
                if server_info.get('timezone'):
                    server_text += f"**Timezone:** {server_info['timezone']}\n"
                if server_info.get('time_now'):
                    server_text += f"**Server Time:** {server_info['time_now']}"

                embed.add_field(name="\u200b", value=server_text, inline=False)

                await interaction.followup.send(embed=embed, ephemeral=True)

            else:
                await interaction.followup.send(
                    "❌ Unable to retrieve service information. Please check your DNS and credentials and try again.",
                    ephemeral=True
                )

        except Exception:
            await interaction.followup.send(
                "❌ Unable to retrieve service information. Please check your DNS and credentials and try again.",
                ephemeral=True
            )        

# ============================================================================
# BOT /PLAYLISTREGISTER COMMAND
# ============================================================================  

@bot.tree.command(name="playlistregister", description="Register Your Playlists")
@app_commands.describe(playlist="Enter your File ID or Google Drive Share/Export URL")
async def playlistregister(interaction: discord.Interaction, playlist: str):
    await interaction.response.defer(ephemeral=True)
    
    duid = str(interaction.user.id)
    
    result = await register_file_async(playlist, duid)
    
    playlists_data = await fetch_playlists_data()
    
    message, record = handle_registration_response(result, playlists_data)
    
    await interaction.followup.send(message, ephemeral=True)

# ============================================================================
# BOT /PLAYLISTINFO COMMAND
# ============================================================================

@bot.tree.command(name="playlistinfo", description="View All Your Registered Playlists")
async def playlistinfo(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    duid = str(interaction.user.id)
    result = await get_all_user_playlists(duid)
    
    if not result:
        await interaction.followup.send(
            MESSAGES["USER_LOOKUP_TIMEOUT_MSG"],
            ephemeral=True
        )
        return
    
    if not isinstance(result, list) or len(result) == 0:
        await interaction.followup.send(
            MESSAGES["USER_LOOKUP_ERROR_MSG"],
            ephemeral=True
        )
        return
    
    playlists_data = await fetch_playlists_data()
    
    if len(result) == 1:
        record = result[0]
        list_id = record.get('list_id')
        playlist_details = get_playlist_details(list_id, playlists_data)
        embed = create_file_info_embed(record, playlist_details, is_mod=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        view = PlaylistPaginationView(result, playlists_data, is_mod=False)
        embed = view.get_embed()
        message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.message = message

# ============================================================================
# BOT /PLAYLISTINFOMOD COMMAND
# ============================================================================

@bot.tree.command(name="playlistinfomod", description="View All Registered Playlists for a Specified User")
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_any_role(*MOD_ROLE_IDS)
@app_commands.describe(duid="Discord User ID")
async def playlistinfomod(interaction: discord.Interaction, duid: str):
    if interaction.channel_id != MODCHANNEL_ID:
        await interaction.response.send_message("This command can only be used in [modlogs](https://discord.com/channels/1382432361840509039/1383551896354164800).", ephemeral=False)
        return
    
    await interaction.response.defer(ephemeral=False)
    
    duid = duid
    result = await get_all_user_playlists(duid)
    
    if not result:
        await interaction.followup.send(MESSAGES["USER_LOOKUP_TIMEOUT_MSG"], ephemeral=False)
        return
    
    if not isinstance(result, list) or len(result) == 0:
        await interaction.followup.send(MESSAGES["USER_LOOKUP_ERROR_MSG"], ephemeral=False)
        return
    
    playlists_data = await fetch_playlists_data()
    
    if len(result) == 1:
        record = result[0]
        list_id = record.get("list_id")
        playlist_details = get_playlist_details(list_id, playlists_data)
        embed = create_file_info_embed(record, playlist_details, is_mod=True)
        await interaction.followup.send(embed=embed, ephemeral=False)
    else:
        view = PlaylistPaginationView(result, playlists_data, is_mod=True)
        embed = view.get_embed()
        message = await interaction.followup.send(embed=embed, view=view, ephemeral=False)
        view.message = message

# ============================================================================
# BOT /PLAYLISTINFOID COMMAND
# ============================================================================

@bot.tree.command(name="playlistinfoid", description="View Specific Playlist by File ID/Playlist URL")
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_any_role(*MOD_ROLE_IDS)
@app_commands.describe(playlist="Enter your File ID or Google Drive Share/Export URL")
async def playlistinfoid(interaction: discord.Interaction, playlist: str):
    await interaction.response.defer(ephemeral=True)
    
    duid = str(interaction.user.id)
    
    result = await get_file_info_async(playlist, duid)
    
    if not result:
        await interaction.followup.send(
            MESSAGES["USER_LOOKUP_ERROR_MSG"],
            ephemeral=True
        )
        return
    
    if result.get('status') != 'ok':
        await interaction.followup.send(
            MESSAGES["USER_LOOKUP_TIMEOUT_MSG"],
            ephemeral=True
        )
        return
    
    record = result.get('file')
    if not record:
        await interaction.followup.send(
            MESSAGES["USER_LOOKUP_ERROR_MSG"],
            ephemeral=True
        )
        return
    
    playlists_data = await fetch_playlists_data()
    playlist_details = get_playlist_details(record.get('list_id'), playlists_data)
    
    embed = create_file_info_embed(record, playlist_details, is_mod=False)
    await interaction.followup.send(embed=embed, ephemeral=True)

# ============================================================================
# BOT /SERVICEINFO COMMAND
# ============================================================================  

@bot.tree.command(name="serviceinfo", description="Get Service Information")
async def serviceinfo(interaction: discord.Interaction):
    await interaction.response.send_modal(ServiceInfoModal())

# ============================================================================
# BOT /LOGOUPDATE COMMAND
# ============================================================================      

@bot.tree.command(name="logoupdate", description="Update the Logo Cache Immediately")
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_any_role(*MOD_ROLE_IDS)
async def logoupdate(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
        global logo_cache, cache_timestamp
        logo_cache = await fetch_logos_from_github()
        cache_timestamp = time.time()

        if logo_cache:
            await interaction.followup.send(
                f"Logo cache updated! Loaded {len(logo_cache)} logos.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "Failed to refresh logo cache. If this error persists, please notify @greenspeedracer.",
                ephemeral=True
            )
    except Exception as e:
        import traceback; traceback.print_exc()
        try:
            await interaction.followup.send(f"Error updating logo cache: {e}", ephemeral=True)
        except Exception:
            pass

# ============================================================================
# KYZU LOGO REPOSITORY CALLS
# ============================================================================              

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
        embed.add_field(name="Source", value="[📂 K-yzu's Logo Repository](https://github.com/K-yzu/Logos)", inline=False)
    
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def fetch_logos_from_github() -> List[dict]:
    url = "https://api.github.com/repos/K-yzu/Logos/git/trees/main?recursive=1"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                logos = [
                    {
                        'name': item['path'].split('/')[-1].replace('.png', '').replace('.gif', ''),
                        'path': item['path'],
                        'url': f"https://raw.githubusercontent.com/K-yzu/Logos/main/{quote(item['path'])}" 
                    }
                    for item in data.get('tree', [])
                    if item['type'] == 'blob' and (
                        item['path'].lower().endswith('.png') or item['path'].lower().endswith('.gif')
                    )
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

# ============================================================================
# BOT /LOGO COMMAND
# ============================================================================  

@bot.tree.command(name="logo", description="Search K-yzu's GitHub Repo for a Logo")
@app_commands.autocomplete(name=logo_autocomplete)
async def logo_search(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    
    logos = await get_logo_list()
    
    exact_match = next((logo for logo in logos if logo['name'].lower() == name.lower()), None)
    
    if exact_match:
        embed = discord.Embed(
            title=f"Logo: {exact_match['name']}",
            color=discord.Color.blue(),
            description=f"[Direct Link]({exact_match['url']})"
            )
        embed.set_image(url=exact_match['url'])
        embed.add_field(name="Source", value="[📂 K-yzu's Logo Repository](https://github.com/K-yzu/Logos)", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        partial_matches = [
            logo for logo in logos
            if name.lower() in logo['name'].lower()
        ]
        
        if partial_matches:
            view = LogoSelectView(partial_matches)
            await interaction.followup.send("Select a logo:", view=view, ephemeral=True)
        else:
            await interaction.followup.send(
                f"No logos found matching '{name}'", ephemeral=True)

# ============================================================================
# EPGENIUS.ORG DOWN DETECTOR
# ============================================================================

bot.last_repo_status = None

@tasks.loop(seconds=CHECK_INTERVAL)
async def check_repo_status():
    status_code, error_type, error_msg = await check_site_status(REPO_URL, TIMEOUT)
    current_status = "UP" if status_code == 200 else "DOWN"
    
    if current_status != bot.last_repo_status:
        if current_status == "DOWN":
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
    if BOTLOGCHANNEL is None:
        print(f"BOTLOGCHANNEL not initialized")
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

    await BOTLOGCHANNEL.send(content=MOD_MENTIONS, embed=embed)

async def send_repo_recovery_alert():
    if BOTLOGCHANNEL is None:
        return
    
    embed = discord.Embed(
        title="✅ EPGenius Server Recovered",
        description=f"EPGenius server {REPO_URL} is back online",
        color=discord.Color.green()
    )
    embed.add_field(name="Status", value="200 OK", inline=False)
    
    await BOTLOGCHANNEL.send(content=MOD_MENTIONS, embed=embed)

# ============================================================================
# STREAMCHECK.PRO DOWN DETECTOR
# ============================================================================

bot.last_sc_status = None

@tasks.loop(seconds=CHECK_INTERVAL)
async def check_sc_status():
    status_code, error_type, error_msg = await check_site_status(SC_URL, TIMEOUT)
    current_status = "UP" if status_code == 200 else "DOWN"
    
    if current_status != bot.last_sc_status:
        if current_status == "DOWN":
            await send_sc_alert(status_code, error_type, error_msg)
        elif bot.last_sc_status is not None:
            await send_sc_recovery_alert()
        
        bot.last_sc_status = current_status

@check_sc_status.before_loop
async def before_check_sc_status():
    await bot.wait_until_ready()

async def send_sc_alert(status_code, error_type, error_msg):
    if SC_UPDATES_CHANNEL is None:
        print(f"SC_UPDATES_CHANNEL not initialized")
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
        title="🚨 StreamCheck Server Down Alert",
        description=f"{SC_URL}",
        color=discord.Color.red()
    )
    embed.add_field(name="Status Code", value=status_display, inline=True)
    embed.add_field(name="Error", value=main_error, inline=True)
    if details:
        embed.add_field(name="Details", value=details, inline=False)

    await SC_UPDATES_CHANNEL.send(content=GSR_MENTION, embed=embed)

async def send_sc_recovery_alert():
    if SC_UPDATES_CHANNEL is None:
        return
    
    embed = discord.Embed(
        title="✅ StreamCheck Server Recovered",
        description=f"StreamCheck server {SC_URL} is back online",
        color=discord.Color.green()
    )
    embed.add_field(name="Status", value="200 OK", inline=False)
    
    await SC_UPDATES_CHANNEL.send(content=GSR_MENTION, embed=embed)

# ============================================================================
# EPGENIUS.ORG PLAYLIST API CALLS
# ============================================================================            

async def fetch_playlists():
    try:
        timeout_config = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async with session.get(PLAYLISTS_URL) as response:
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

# ============================================================================
# BOT /PLAYLIST COMMAND
# ============================================================================    

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

# ============================================================================
# BOT /KILLEPGBOT COMMAND
# ============================================================================     

@bot.tree.command(name="killepgbot", description="Kill EPGeniusBot")
@app_commands.default_permissions(manage_messages=True) 
@app_commands.checks.has_any_role(*MOD_ROLE_IDS)
async def killepgbot(interaction: discord.Interaction):
    await interaction.response.send_message("Killing EPGeniusBot")
    await bot.close()

@bot.tree.error
async def on_app_command_error(interaction, error):
    if isinstance(error, MissingAnyRole):
        await interaction.response.send_message(
            "You don't have the required role(s) to run this command.",
        )
    else:
        print(f"Unhandled error: {error}")

# ============================================================================
# BOT /EPG COMMAND
# ============================================================================         

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

# ============================================================================
# ONREADY
# ============================================================================ 

@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    print(f"Mod Role IDs: {MOD_ROLE_IDS}")
    print(f"GSR Guild ID: {GSR_GUILD_ID}")
    print(f"EPGenius Guild ID: {EPGENIUS_GUILD_ID}")

    global BOTLOGCHANNEL
    BOTLOGCHANNEL = bot.get_channel(BOTLOGCHANNEL_ID)
    if BOTLOGCHANNEL:
        print(f"Bot log channel found: {BOTLOGCHANNEL.name}")
    else:
        print(f"Warning: Could not find bot log channel with ID {BOTLOGCHANNEL_ID}")
    
    if not check_repo_status.is_running():
        check_repo_status.start()
        print(f"EPGenius server status monitoring started for {REPO_URL}")

    
    global MODCHANNEL
    MODCHANNEL = bot.get_channel(MODCHANNEL_ID)
    if MODCHANNEL:
        print(f"Mod channel found: {MODCHANNEL.name}")
    else:
        print(f"Warning: Could not find mod channel with ID {MODCHANNEL_ID}")    

    global SC_UPDATES_CHANNEL
    SC_UPDATES_CHANNEL = bot.get_channel(SC_UPDATES_CHANNEL_ID)
    if SC_UPDATES_CHANNEL:
        print(f"StreamCheck Updates channel found: {SC_UPDATES_CHANNEL.name}")
    else:
        print(f"Warning: Could not find StreamCheck Updates channel with ID {SC_UPDATES_CHANNEL_ID}")
    
    if not check_sc_status.is_running():
        check_sc_status.start()
        print(f"StreamCheck server status monitoring started for {SC_URL}")

    logos = await get_logo_list()
    if logos:
        print(f"Pre-cached {len(logos)} logos")
    else:
        print("Failed to pre-cache logos")    

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