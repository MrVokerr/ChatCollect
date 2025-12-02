import asyncio
import time
import json
import random
import os
import glob
import sys
import shutil
import ctypes
import urllib.request
import subprocess
from ctypes import windll, byref, c_int
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QGroupBox, QMessageBox, QComboBox, QGridLayout, QCheckBox, 
                             QTabWidget, QFileDialog, QSpinBox, QFontComboBox, QFormLayout, QScrollArea)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer, QPropertyAnimation, QRectF, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont, QIntValidator, QIcon, QPainter, QColor, QBrush, QPen
import websockets
from twitchio.ext import commands

# ============ VERSION & UPDATE CONFIG ============
CURRENT_VERSION = "1.0.7"
# REPLACE THESE WITH YOUR ACTUAL GITHUB URLs
UPDATE_VERSION_URL = "https://raw.githubusercontent.com/MrVokerr/ChatCollect/main/version.txt"
UPDATE_EXE_URL = "https://github.com/MrVokerr/ChatCollect/releases/latest/download/ChatCollect.exe"
REPO_RAW_URL = "https://raw.githubusercontent.com/MrVokerr/ChatCollect/main/"

# ============ PATH CONFIGURATION ============
if getattr(sys, 'frozen', False):
    # Running as compiled EXE
    BASE_PATH = os.path.dirname(sys.executable)
else:
    # Running as script
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    # If running from build/ folder, assets are in parent directory
    if os.path.basename(BASE_PATH).lower() == "build":
        BASE_PATH = os.path.dirname(BASE_PATH)

CONFIG_FILE = os.path.join(BASE_PATH, "chatcollect_config.json")
DB_PATH = os.path.join(BASE_PATH, "chatcollect_data.txt")
OVERLAY_FOLDER = os.path.join(BASE_PATH, "overlay")
COOLDOWN = 60

DEFAULT_CONFIG = {
    "commands": {
        "loot": "!loot",
        "leaderboard": "!leaderboard",
        "contest": "!contest",
        "use": "!use"
    },
    "messages": {
        "cooldown": "⏳ @{username}, resting...... wait {remaining}s.",
        "loot_success": "🍞 @{username} looted a {item}! (+{points} pts) ({rank}) | Score: {score}",
        "loot_legendary": "✨ @{username} looted a LEGENDARY {item}! ✨ (+{points} pts) ({rank}) | Score: {score}",
        "loot_ruined": "🔥 @{username} tried to loot a {item} but fell asleep! It's RUINED! (0 pts)",
        "loot_shiny": "💎✨ SHINY!! @{username} looted a SHINY {item}! Unlocked a Badge! (+{points} pts)",
        "loot_golden": "🌟 MASTERPIECE! @{username} looted a GOLDEN {item}! (+{points} pts)",
        "rank_up": "🎉 {username} ranked up to {rank}!",
        "contest_start": "⚔️ CONTEST STARTED! Type {command} to enter! (Entry: 50 pts)",
        "contest_winner": "🏆 {username} WON THE CONTEST! Prize: {prize} pts!",
        "rush_hour_start": "🚀 RUSH HOUR STARTED! 2x Points for 60 seconds!",
        "loot_drive_start": "🎒 LOOT DRIVE STARTED! Community Goal: {target} Items!",
        "bounty_hunter_spawn": "🧐 BOUNTY HUNTER ARRIVED! He wants a {item}!",
        "bounty_hunter_satisfied": "🧐 {username} satisfied the Bounty Hunter! (+{points} pts)"
    },
    "events": {
        "rush_hour_name": "Rush Hour",
        "loot_drive_name": "Loot Drive",
        "bounty_hunter_name": "Bounty Hunter",
        "contest_name": "Contest"
    },
    "points": {
        "shiny": 10,
        "golden": 3,
        "ruined": 0,
        "legendary": 5,
        "bounty_hunter": 50,
        "standard_min": 1,
        "standard_max": 1
    },
    "ranks": [
        {"score": 0, "title": "Novice Collector"},
        {"score": 50, "title": "Rookie Scavenger"},
        {"score": 250, "title": "Apprentice Hunter"},
        {"score": 750, "title": "Loot Specialist"},
        {"score": 2000, "title": "Treasure Expert"},
        {"score": 5000, "title": "Hoard Master"},
        {"score": 10000, "title": "Legendary Collector"},
        {"score": 25000, "title": "Artifact Hunter"},
        {"score": 50000, "title": "Celestial Hoarder"},
        {"score": 100000, "title": "God of Loot"}
    ]
}

# ============ OPTIMIZED MANAGERS ============
class AssetManager:
    def __init__(self, folder):
        self.folder = folder
        self._normal_items = []
        self._legendary_items = []
        self._last_scan = 0
        self._scan_interval = 60  # Cache for 60 seconds
        self.refresh()

    def _scan_if_needed(self):
        if time.time() - self._last_scan > self._scan_interval:
            self.refresh()

    def refresh(self):
        if not os.path.exists(self.folder):
            self._normal_items = ["croissant.png", "donut.png", "Pancakes.png"]
            self._legendary_items = []
            return

        # 1. Scan Root Folder (Normal Items + Old Legendary)
        root_files = glob.glob(os.path.join(self.folder, "*.png"))
        
        # 2. Scan 'legendary' Subfolder (New Legendary Items)
        legendary_folder = os.path.join(self.folder, "legendary")
        legendary_files = []
        if os.path.exists(legendary_folder):
            legendary_files = glob.glob(os.path.join(legendary_folder, "*.png"))

        self._legendary_items = []
        self._normal_items = []

        # Process Subfolder Legendaries (Preferred)
        for f in legendary_files:
            filename = os.path.basename(f)
            # Use forward slash for web compatibility
            self._legendary_items.append(f"legendary/{filename}")

        # Process Root Files
        for f in root_files:
            filename = os.path.basename(f)
            lower_name = filename.lower()
            
            # Backward compatibility for "Legendary-" prefix in root
            if lower_name.startswith("legendary-"):
                self._legendary_items.append(filename)
            else:
                self._normal_items.append(filename)
        
        # Fallback if no normal items found
        if not self._normal_items:
            self._normal_items = ["croissant.png", "donut.png", "Pancakes.png"]
        
        self._last_scan = time.time()

    @property
    def normal_items(self):
        self._scan_if_needed()
        return self._normal_items

    @property
    def legendary_items(self):
        self._scan_if_needed()
        return self._legendary_items

class PlayerDatabase:
    def __init__(self, filepath):
        self.filepath = filepath
        self.players = {}
        self._last_mtime = 0
        self.load()

    def load(self):
        if not os.path.exists(self.filepath):
            return
        
        try:
            current_mtime = os.path.getmtime(self.filepath)
            self._last_mtime = current_mtime
            
            with open(self.filepath, 'r', encoding='utf-8') as f:
                loaded_players = {}
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('|')
                    if len(parts) >= 3:
                        username = parts[0].strip()
                        try:
                            loaded_players[username] = {
                                'loot_score': int(parts[1].strip()),
                                'last_loot_time': float(parts[2].strip()),
                                'luck': float(parts[3].strip()) if len(parts) >= 4 else 0.0,
                                'last_use_time': float(parts[4].strip()) if len(parts) >= 5 else 0.0,
                                'prestige_stars': int(parts[5].strip()) if len(parts) >= 6 else 0,
                                'shinies': int(parts[6].strip()) if len(parts) >= 7 else 0
                            }
                        except ValueError:
                            continue
                
                # Update existing dictionary to preserve references
                self.players.clear()
                self.players.update(loaded_players)
                print(f"✅ Database loaded. {len(self.players)} players.")
                
        except Exception as e:
            print(f"⚠️ Warning: Could not load database: {e}")
            try:
                shutil.copy2(self.filepath, self.filepath + ".corrupt_backup")
                print(f"⚠️ Created backup of corrupted database: {self.filepath}.corrupt_backup")
            except:
                pass

    def reload_if_needed(self):
        """Reloads the database if the file has changed on disk"""
        if not os.path.exists(self.filepath):
            return
        
        try:
            current_mtime = os.path.getmtime(self.filepath)
            if current_mtime > self._last_mtime:
                print("🔄 File changed externally, reloading database...")
                self.load()
        except Exception as e:
            print(f"⚠️ Error checking file update: {e}")

    def save_blocking(self):
        """Blocking save for use in executor"""
        try:
            # Write to temp file first to prevent corruption
            temp_file = self.filepath + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write("# ChatCollect Player Database - Edit with Notepad\n")
                f.write("# Format: username | loot_score | last_loot_time | luck | last_use_time | prestige_stars | shinies\n")
                f.write("# WARNING: Keep the | separators intact!\n\n")
                
                sorted_players = sorted(self.players.items(), key=lambda x: x[1]['loot_score'], reverse=True)
                for username, data in sorted_players:
                    f.write(f"{username} | {data['loot_score']} | {data['last_loot_time']} | "
                            f"{data.get('luck', 0.0)} | {data.get('last_use_time', 0.0)} | "
                            f"{data.get('prestige_stars', 0)} | {data.get('shinies', 0)}\n")
            
            # Atomic replace
            if os.path.exists(self.filepath):
                os.replace(temp_file, self.filepath)
            else:
                os.rename(temp_file, self.filepath)
            
            # Update mtime so we don't reload our own save
            self._last_mtime = os.path.getmtime(self.filepath)
                
        except Exception as e:
            print(f"❌ Error saving database: {e}")

    async def save(self):
        """Async save wrapper"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.save_blocking)

# Initialize Managers
asset_manager = AssetManager(OVERLAY_FOLDER)
db = PlayerDatabase(DB_PATH)
player_data = db.players

# ============ BAKED GOODS HELPERS ============
def choose_loot_item(rarity="standard", legendary_chance_1_in_x=1000):
    """Choose a baked good based on rarity"""
    legendary = asset_manager.legendary_items
    normal = asset_manager.normal_items
    
    # Shiny: Pull from BOTH pools
    if rarity == "shiny":
        pool = normal + legendary
        if not pool: 
            return "croissant.png", False
        
        choice = random.choice(pool)
        is_legendary = choice in legendary
        return choice, is_legendary

    # Standard/Golden/Ruined: Configurable chance of Legendary, else Normal
    chance = 1.0 / max(1, legendary_chance_1_in_x)
    
    if legendary and random.random() < chance:
        return random.choice(legendary), True
    else:
        return random.choice(normal), False

def format_item_name(filename):
    """Convert filename to display name"""
    # Handle paths like "legendary/cake.png" - get just the filename
    name = os.path.basename(filename)
    name = os.path.splitext(name)[0]
    
    # Case-insensitive removal of prefix
    lower_name = name.lower()
    if lower_name.startswith("legendary-") or lower_name.startswith("legendary_") or lower_name.startswith("legendary "):
        name = name[10:]
        
    return name.replace("_", " ").replace("-", " ").strip().title()

def get_leaderboard_message(show):
    sorted_players = sorted(player_data.items(), key=lambda x: x[1]['loot_score'], reverse=True)[:10]
    leaderboard_data = []
    for rank, (username, data) in enumerate(sorted_players, 1):
        leaderboard_data.append({
            "rank": rank,
            "username": username,
            "score": data['loot_score'],
            "shinies": data.get('shinies', 0)
        })
    
    return {
        "event": "leaderboard_update",
        "show": show,
        "data": leaderboard_data
    }

# ============ WEBSOCKET SERVER ============
overlay_clients = set()

async def handle_overlay_connection(websocket):
    """Handle incoming overlay connections"""
    overlay_clients.add(websocket)
    try:
        async for _ in websocket:
            pass
    finally:
        overlay_clients.remove(websocket)

async def broadcast_to_overlays(message):
    """Send message to all connected overlays"""
    if overlay_clients:
        data = json.dumps(message)
        await asyncio.gather(*[client.send(data) for client in overlay_clients], return_exceptions=True)

async def start_overlay_server():
    """Start WebSocket server"""
    async with websockets.serve(handle_overlay_connection, "0.0.0.0", 8765):
        await asyncio.Future()

# ============ TWITCH BOT ============
class ChatCollectBot(commands.Bot):
    def __init__(self, token, channel, log_callback, status_callback, config):
        super().__init__(token=token, prefix="!", initial_channels=[channel], case_insensitive=True)
        self.token = token
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.channel_name = channel
        self.config = config
        
        # Event States
        self.rush_hour_active = False
        self.rush_hour_end_time = 0
        
        self.loot_drive_active = False
        self.loot_drive_target = 0
        self.loot_drive_current = 0
        self.loot_drive_end_time = 0
        self.loot_drive_participants = set()
        
        self.bounty_hunter_active = False
        self.bounty_hunter_craving = None
        self.bounty_hunter_end_time = 0

        # Contest State
        self.contest_state = "inactive" # inactive, joining, resolving
        self.contest_join_end_time = 0
        self.contest_resolve_time = 0
        self.contest_participants = []
        self.contest_pool = 0
        self.contest_start_time = 0
        self.contest_reminder_sent = False
        
        # Settings
        self.show_banner = True

    def set_show_banner(self, enabled):
        self.show_banner = enabled

    def get_rank_title(self, score):
        ranks = self.config.get("ranks", DEFAULT_CONFIG["ranks"])
        # Ensure ranks are sorted by score descending for the check
        # The config might have them in any order, but usually ascending.
        # Let's sort them descending to find the highest threshold met.
        sorted_ranks = sorted(ranks, key=lambda x: x["score"], reverse=True)
        
        for r in sorted_ranks:
            if score >= r["score"]:
                return r["title"]
        # Fallback to lowest
        if sorted_ranks:
            return sorted_ranks[-1]["title"]
        return "Novice"

    async def event_ready(self):
        self.log_callback(f"✅ Bot logged in as {self.nick}")
        self.log_callback(f"📺 Connected to channel: {self.channel_name}")
        
        # Register Dynamic Commands
        cmds = self.config.get("commands", DEFAULT_CONFIG["commands"])
        
        # Helper to strip prefix for registration
        def get_cmd_name(cmd_str):
            return cmd_str.lstrip('!')

        self.add_command(commands.Command(name=get_cmd_name(cmds["loot"]), func=self.cmd_loot))
        self.add_command(commands.Command(name=get_cmd_name(cmds["leaderboard"]), func=self.cmd_leaderboard))
        self.add_command(commands.Command(name=get_cmd_name(cmds["contest"]), func=self.cmd_contest))
        self.add_command(commands.Command(name=get_cmd_name(cmds["use"]), func=self.cmd_use))

        self.log_callback(f"🎮 Commands: {cmds['loot']}, {cmds['leaderboard']}, {cmds['contest']}")
        self.log_callback("-" * 50)
        self.loop.create_task(self.game_loop())

    async def event_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        self.log_callback(f"❌ Command Error: {error}")

    def _send_status_update(self):
        """Helper to send current event status to GUI"""
        try:
            now = time.time()
            status = {
                "rush_hour_active": self.rush_hour_active,
                "rush_hour_remaining": int(max(0, self.rush_hour_end_time - now)) if self.rush_hour_active else 0,
                "loot_drive_active": self.loot_drive_active,
                "loot_drive_remaining": int(max(0, self.loot_drive_end_time - now)) if self.loot_drive_active else 0,
                "loot_drive_progress": f"{self.loot_drive_current}/{self.loot_drive_target}" if self.loot_drive_active else "Inactive",
                "bounty_hunter_active": self.bounty_hunter_active,
                "bounty_hunter_craving": format_item_name(self.bounty_hunter_craving) if self.bounty_hunter_active else "None",
                "bounty_hunter_remaining": int(max(0, self.bounty_hunter_end_time - now)) if self.bounty_hunter_active else 0,
                "contest_state": self.contest_state,
                "contest_pool": self.contest_pool,
                "contest_timer": int(max(0, self.contest_join_end_time - now)) if self.contest_state == "joining" else int(max(0, self.contest_resolve_time - now)) if self.contest_state == "resolving" else 0
            }
            if self.status_callback:
                self.status_callback(status)
        except Exception as e:
            print(f"Status Update Error: {e}")

    async def game_loop(self):
        """Background task to check event timers and update GUI"""
        while True:
            try:
                now = time.time()
                channel = self.get_channel(self.channel_name)
                
                msgs = self.config.get("messages", DEFAULT_CONFIG["messages"])
                evts = self.config.get("events", DEFAULT_CONFIG["events"])

                # Check Rush Hour Expiry
                if self.rush_hour_active and now > self.rush_hour_end_time:
                    self.rush_hour_active = False
                    self.log_callback(f"🛑 {evts['rush_hour_name']} ended!")
                    if channel:
                        await channel.send(f"🛑 The {evts['rush_hour_name']} has ended! Cooldowns are back to normal.")
                    self._send_status_update()

                # Check Loot Drive Expiry (Failure)
                if self.loot_drive_active and now > self.loot_drive_end_time:
                    self.loot_drive_active = False
                    self.log_callback(f"😞 {evts['loot_drive_name']} Failed (Time out)")
                    if channel:
                        await channel.send(f"😞 The {evts['loot_drive_name']} ended! We only collected {self.loot_drive_current}/{self.loot_drive_target}. No stars awarded.")
                    self._send_status_update()

                # Check Bounty Hunter Expiry
                if self.bounty_hunter_active and now > self.bounty_hunter_end_time:
                    self.bounty_hunter_active = False
                    self.bounty_hunter_craving = None
                    self.log_callback(f"😒 {evts['bounty_hunter_name']} left (Time out)")
                    if channel:
                        await channel.send(f"😒 The {evts['bounty_hunter_name']} got tired of waiting and left!")
                    self._send_status_update()

                # Contest Logic
                if self.contest_state == "joining":
                    # Reminder Logic (Halfway mark)
                    if not self.contest_reminder_sent:
                        total_duration = self.contest_join_end_time - self.contest_start_time
                        if (now - self.contest_start_time) >= (total_duration / 2):
                            self.contest_reminder_sent = True
                            remaining = int(self.contest_join_end_time - now)
                            time_str = f"{remaining // 60}m {remaining % 60}s" if remaining >= 60 else f"{remaining}s"
                            if channel:
                                await channel.send(f"⚠️ {evts['contest_name']} entries closing in {time_str}! Join now!")

                    if now > self.contest_join_end_time:
                        if not self.contest_participants:
                            self.contest_state = "inactive"
                            self.log_callback(f"😞 {evts['contest_name']} cancelled (No participants)")
                            if channel: await channel.send(f"😞 {evts['contest_name']} cancelled! No one joined.")
                        else:
                            self.contest_state = "resolving"
                            self.contest_resolve_time = now + 30
                            names = ", ".join(self.contest_participants)
                            self.log_callback(f"🥊 {evts['contest_name']} Entries Closed! ({len(self.contest_participants)} entries)")
                            if channel: await channel.send(f"🥊 {evts['contest_name']} Entries Closed! Participants: {names}. Winner chosen in 30s! Pool: {self.contest_pool} pts")
                        self._send_status_update()
                
                elif self.contest_state == "resolving":
                    if now > self.contest_resolve_time:
                        # Reload DB before awarding prize
                        db.reload_if_needed()
                        
                        winner = random.choice(self.contest_participants)
                        if winner in player_data:
                            player_data[winner]['loot_score'] += self.contest_pool
                            await db.save()
                        
                        self.log_callback(f"🏆 {evts['contest_name']} Winner: {winner} (+{self.contest_pool} pts)")
                        
                        win_msg = msgs.get("contest_winner", DEFAULT_CONFIG["messages"]["contest_winner"])
                        win_msg = win_msg.format(username=winner, prize=self.contest_pool)
                        
                        if channel: await channel.send(win_msg)
                        self.contest_state = "inactive"
                        self._send_status_update()

                # Send Status Update to GUI
                self._send_status_update()

                # Dynamic sleep: 1s if active, 5s if inactive to save resources
                if self.rush_hour_active or self.loot_drive_active or self.bounty_hunter_active:
                    await asyncio.sleep(1)
                else:
                    await asyncio.sleep(5)

            except Exception as e:
                print(f"Game Loop Error: {e}")
                await asyncio.sleep(5)

    async def cmd_use(self, ctx):
        # Reload DB if changed externally
        db.reload_if_needed()
        
        username = ctx.author.name.lower()
        parts = ctx.message.content.split()
        amount = 1
        if len(parts) > 1:
            try:
                amount = int(parts[1])
            except ValueError:
                pass
        
        if amount < 1:
            return

        if username not in player_data:
            await ctx.send(f"@{username}, you need to loot something first!")
            return

        now = time.time()
        last_eat = player_data[username].get('last_use_time', 0)
        
        # 5 minute cooldown (300 seconds)
        if now - last_eat < 300:
            remaining = int(300 - (now - last_eat))
            await ctx.send(f"⏳ @{username}, you're too full! Wait {remaining}s.")
            return

        current_score = player_data[username]['loot_score']
        if current_score < amount:
            await ctx.send(f"@{username}, you don't have enough points! (Current: {current_score})")
            return

        # Consume points
        player_data[username]['loot_score'] -= amount
        
        # Add luck (5% per point)
        current_luck = player_data[username].get('luck', 0.0)
        added_luck = amount * 5.0
        new_luck = current_luck + added_luck
        player_data[username]['luck'] = new_luck
        player_data[username]['last_use_time'] = now
        
        await db.save()
        
        await ctx.send(f"🍽️ @{username} used {amount} points! Luck increased by {int(added_luck)}% (Total: {int(new_luck)}%). Good luck on your next loot!")

    async def cmd_loot(self, ctx):
        # Reload DB if changed externally
        db.reload_if_needed()
        
        username = ctx.author.name.lower()
        now = time.time()
        
        msgs = self.config.get("messages", DEFAULT_CONFIG["messages"])
        evts = self.config.get("events", DEFAULT_CONFIG["events"])

        if username not in player_data:
            player_data[username] = {
                'loot_score': 0, 
                'last_loot_time': 0,
                'luck': 0.0,
                'last_use_time': 0.0,
                'prestige_stars': 0,
                'shinies': 0
            }
        
        # Ensure all fields exist
        if 'luck' not in player_data[username]: player_data[username]['luck'] = 0.0
        if 'shinies' not in player_data[username]: player_data[username]['shinies'] = 0
        if 'prestige_stars' not in player_data[username]: player_data[username]['prestige_stars'] = 0
        
        bake_score = player_data[username]['loot_score']
        last_bake_time = player_data[username]['last_loot_time']
        luck = player_data[username]['luck']

        # COOLDOWN CHECK
        cooldown_time = int(self.config.get("cooldown", COOLDOWN))
        
        # Check Rush Hour
        if self.rush_hour_active:
            cooldown_time = max(1, cooldown_time // 6) # Reduced cooldown
        
        if now - last_bake_time < cooldown_time:
            remaining = int(cooldown_time - (now - last_bake_time))
            msg = msgs.get("cooldown", DEFAULT_CONFIG["messages"]["cooldown"])
            await ctx.send(msg.format(username=username, remaining=remaining))
            return

        old_rank_title = self.get_rank_title(bake_score)
        
        # Rarity Logic
        shiny_chance_1_in_x = int(self.config.get("shiny_chance", 10000))
        legendary_chance_1_in_x = int(self.config.get("legendary_chance", 1000))
        
        base_shiny_prob = 1.0 / max(1, shiny_chance_1_in_x)
        shiny_prob = base_shiny_prob + (luck / 1000.0)
        
        golden_prob = 0.05 + (luck / 200.0)
        ruined_prob = 0.05
        
        rand_val = random.random()
        
        rarity = "standard"
        points_gained = 1
        
        # Loot Points Config
        pts_cfg = self.config.get("points", DEFAULT_CONFIG["points"])
        loot_min = int(pts_cfg.get("standard_min", 1))
        loot_max = int(pts_cfg.get("standard_max", 1))
        
        if rand_val < shiny_prob:
            rarity = "shiny"
            points_gained = int(pts_cfg.get("shiny", 10))
            player_data[username]['shinies'] += 1
        elif rand_val < (shiny_prob + ruined_prob):
            rarity = "ruined"
            points_gained = int(pts_cfg.get("ruined", 0))
        elif rand_val < (shiny_prob + ruined_prob + golden_prob):
            rarity = "golden"
            points_gained = int(pts_cfg.get("golden", 3))
        else:
            rarity = "standard"
            points_gained = random.randint(loot_min, loot_max)
            
        # Reset luck
        player_data[username]['luck'] = 0.0
        
        # Choose item
        loot_item, is_legendary_item = choose_loot_item(rarity, legendary_chance_1_in_x)
        item_display_name = format_item_name(loot_item)
        
        # Legendary Bonus (Override points if legendary, unless already higher)
        if is_legendary_item:
            leg_pts = int(pts_cfg.get("legendary", 5))
            if points_gained < leg_pts:
                points_gained = leg_pts

        # Bounty Hunter Check
        critic_bonus = 0
        critic_msg = ""
        if self.bounty_hunter_active and self.bounty_hunter_craving == loot_item:
            critic_bonus = int(pts_cfg.get("bounty_hunter", 50))
            points_gained += critic_bonus
            self.bounty_hunter_active = False
            self.bounty_hunter_craving = None
            
            bh_msg = msgs.get("bounty_hunter_satisfied", DEFAULT_CONFIG["messages"]["bounty_hunter_satisfied"])
            critic_msg = f" {bh_msg.format(username=username, points=critic_bonus)}"
            
            self.log_callback(f"🧐 {username} satisfied the {evts['bounty_hunter_name']}!")
            self._send_status_update()

        bake_score += points_gained
        new_rank_title = self.get_rank_title(bake_score)

        player_data[username]['loot_score'] = bake_score
        player_data[username]['last_loot_time'] = now
        await db.save()

        # Update Leaderboard if enabled
        if self.config.get('show_leaderboard', False):
            await broadcast_to_overlays(get_leaderboard_message(True))

        ranked_up = old_rank_title != new_rank_title
        
        trigger_explosion = ranked_up or (rarity == "shiny") or (rarity == "golden") or is_legendary_item or (critic_bonus > 0)
        
        # Loot Drive Logic
        loot_drive_msg = ""
        if self.loot_drive_active:
            self.loot_drive_current += 1
            self.loot_drive_participants.add(username)
            remaining_sale = self.loot_drive_target - self.loot_drive_current
            if remaining_sale <= 0:
                self.loot_drive_active = False
                loot_drive_msg = f" 🍪 {evts['loot_drive_name']} COMPLETE! All participants get a Prestige Star! ⭐"
                self.log_callback(f"🍪 {evts['loot_drive_name']} Completed!")
                # Award stars
                for participant in self.loot_drive_participants:
                    if participant in player_data:
                        player_data[participant]['prestige_stars'] = player_data[participant].get('prestige_stars', 0) + 1
                await db.save()
            else:
                 # Always show progress if active
                 loot_drive_msg = f" ({evts['loot_drive_name']}: {self.loot_drive_current}/{self.loot_drive_target})"
            self._send_status_update()

        # Construct Message
        msg = ""
        if rarity == "ruined":
            base_msg = msgs.get("loot_ruined", DEFAULT_CONFIG["messages"]["loot_ruined"])
            msg = base_msg.format(username=username, item=item_display_name)
            self.log_callback(f"🔥 {username} ruined a {item_display_name}")
        elif rarity == "shiny":
            base_msg = msgs.get("loot_shiny", DEFAULT_CONFIG["messages"]["loot_shiny"])
            msg = base_msg.format(username=username, item=item_display_name, points=points_gained)
            msg += f"{critic_msg}{loot_drive_msg}"
            self.log_callback(f"💎 {username} got a SHINY {item_display_name}")
        elif rarity == "golden":
            base_msg = msgs.get("loot_golden", DEFAULT_CONFIG["messages"]["loot_golden"])
            msg = base_msg.format(username=username, item=item_display_name, points=points_gained)
            msg += f"{critic_msg}{loot_drive_msg}"
            self.log_callback(f"🌟 {username} got a GOLDEN {item_display_name}")
        else:
            # Standard
            if is_legendary_item:
                base_msg = msgs.get("loot_legendary", DEFAULT_CONFIG["messages"]["loot_legendary"])
                msg = base_msg.format(username=username, item=item_display_name, points=points_gained, rank=new_rank_title, score=int(bake_score))
                msg += f"{critic_msg}{loot_drive_msg}"
                self.log_callback(f"✨ {username} looted a LEGENDARY {item_display_name}")
            else:
                base_msg = msgs.get("loot_success", DEFAULT_CONFIG["messages"]["loot_success"])
                msg = base_msg.format(username=username, item=item_display_name, points=points_gained, rank=new_rank_title, score=int(bake_score))
                msg += f"{critic_msg}{loot_drive_msg}"
                self.log_callback(f"🍞 {username} looted a {item_display_name}")
                
        await ctx.send(msg)

        message = {
            "event": "loot",
            "user": username,
            "rank": new_rank_title,
            "score": int(bake_score),
            "item": loot_item,
            "is_legendary": is_legendary_item,
            "rarity": rarity,
            "trigger_explosion": trigger_explosion,
            "ranked_up": ranked_up,
            "show_banner": self.show_banner
        }
        await broadcast_to_overlays(message)

    async def cmd_leaderboard(self, ctx):
        # Reload DB if changed externally
        db.reload_if_needed()
        self.log_callback(f"📊 Leaderboard requested by {ctx.author.name}")
        await self.send_leaderboard_to_chat(ctx)

    async def fetch_leaderboard(self):
        sorted_players = sorted(player_data.items(), key=lambda x: x[1]['loot_score'], reverse=True)[:5]
        board = []
        for username, data in sorted_players:
            board.append({
                "username": username,
                "score": int(data['loot_score']),
                "title": self.get_rank_title(data['loot_score'])
            })
        return board

    async def send_leaderboard_to_chat(self, ctx):
        board = await self.fetch_leaderboard()
        if not board:
            await ctx.send("No collectors yet.")
            return
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        
        msg_parts = []
        for i, b in enumerate(board):
            username = b['username']
            shinies = player_data[username].get('shinies', 0)
            badge = "💎" if shinies > 0 else ""
            msg_parts.append(f"{medals[i]} {username}{badge} ({b['title']}) - {b['score']}")
            
        msg = " | ".join(msg_parts)
        await ctx.send(msg)

    async def start_rush_hour(self, duration_minutes=2):
        if self.rush_hour_active:
            self.log_callback("⚠️ Rush Hour already active!")
            return
            
        self.rush_hour_active = True
        duration_seconds = duration_minutes * 60
        self.rush_hour_end_time = time.time() + duration_seconds
        
        evts = self.config.get("events", DEFAULT_CONFIG["events"])
        msgs = self.config.get("messages", DEFAULT_CONFIG["messages"])
        
        self.log_callback(f"🚀 {evts['rush_hour_name']} started! ({duration_minutes} mins)")
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            msg = msgs.get("rush_hour_start", DEFAULT_CONFIG["messages"]["rush_hour_start"])
            await channel.send(msg)

    async def stop_rush_hour(self):
        if not self.rush_hour_active:
            return
        self.rush_hour_active = False
        evts = self.config.get("events", DEFAULT_CONFIG["events"])
        self.log_callback(f"🛑 {evts['rush_hour_name']} stopped manually.")
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            await channel.send(f"🛑 The {evts['rush_hour_name']} has been stopped manually.")

    async def start_loot_drive(self, duration_minutes=20):
        if self.loot_drive_active:
            self.log_callback("⚠️ Loot Drive already active!")
            return

        self.loot_drive_active = True
        self.loot_drive_target = 150
        self.loot_drive_current = 0
        duration_seconds = duration_minutes * 60
        self.loot_drive_end_time = time.time() + duration_seconds
        self.loot_drive_participants = set()
        
        evts = self.config.get("events", DEFAULT_CONFIG["events"])
        msgs = self.config.get("messages", DEFAULT_CONFIG["messages"])
        
        self.log_callback(f"🎒 {evts['loot_drive_name']} started! Target: 150 Items ({duration_minutes} mins)")
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            msg = msgs.get("loot_drive_start", DEFAULT_CONFIG["messages"]["loot_drive_start"])
            await channel.send(msg.format(target=self.loot_drive_target))

    async def stop_loot_drive(self):
        if not self.loot_drive_active:
            return
        self.loot_drive_active = False
        evts = self.config.get("events", DEFAULT_CONFIG["events"])
        self.log_callback(f"🛑 {evts['loot_drive_name']} stopped manually.")
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            await channel.send(f"🛑 The {evts['loot_drive_name']} has been stopped manually.")

    async def spawn_bounty_hunter(self, duration_minutes=10):
        if self.bounty_hunter_active:
            self.log_callback("⚠️ Bounty Hunter already here!")
            return

        self.bounty_hunter_active = True
        duration_seconds = duration_minutes * 60
        self.bounty_hunter_end_time = time.time() + duration_seconds
        # Pick a random item
        items = asset_manager.normal_items
        self.bounty_hunter_craving = random.choice(items)
        craving_name = format_item_name(self.bounty_hunter_craving)
        
        evts = self.config.get("events", DEFAULT_CONFIG["events"])
        msgs = self.config.get("messages", DEFAULT_CONFIG["messages"])
        
        self.log_callback(f"🧐 {evts['bounty_hunter_name']} arrived! Craving: {craving_name} ({duration_minutes} mins)")
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            msg = msgs.get("bounty_hunter_spawn", DEFAULT_CONFIG["messages"]["bounty_hunter_spawn"])
            await channel.send(msg.format(item=craving_name))

    async def stop_bounty_hunter(self):
        if not self.bounty_hunter_active:
            return
        self.bounty_hunter_active = False
        self.bounty_hunter_craving = None
        evts = self.config.get("events", DEFAULT_CONFIG["events"])
        self.log_callback(f"🛑 {evts['bounty_hunter_name']} left manually.")
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            await channel.send(f"🛑 The {evts['bounty_hunter_name']} has left the chat.")

    async def cmd_contest(self, ctx):
        # Reload DB if changed externally
        db.reload_if_needed()

        if self.contest_state != "joining":
            return
        
        username = ctx.author.name.lower()
        if username in self.contest_participants:
            await ctx.send(f"@{username}, you are already in the Contest!")
            return
            
        if username not in player_data:
             await ctx.send(f"@{username}, you need to loot something first!")
             return

        if player_data[username]['loot_score'] < 10:
            await ctx.send(f"@{username}, you need 10 points to join!")
            return
            
        player_data[username]['loot_score'] -= 10
        self.contest_participants.append(username)
        self.contest_pool += 10
        await db.save()
        await ctx.send(f"⚔️ @{username} joined the Contest! (Pool: {self.contest_pool})")

    async def start_contest(self, duration_minutes=2):
        if self.contest_state != "inactive":
            self.log_callback("⚠️ Contest already active!")
            return

        self.contest_state = "joining"
        self.contest_join_end_time = time.time() + (duration_minutes * 60)
        self.contest_start_time = time.time()
        self.contest_reminder_sent = False
        self.contest_participants = []
        self.contest_pool = 0
        
        evts = self.config.get("events", DEFAULT_CONFIG["events"])
        msgs = self.config.get("messages", DEFAULT_CONFIG["messages"])
        cmds = self.config.get("commands", DEFAULT_CONFIG["commands"])
        
        self.log_callback(f"⚔️ {evts['contest_name']} started! ({duration_minutes} mins)")
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            msg = msgs.get("contest_start", DEFAULT_CONFIG["messages"]["contest_start"])
            await channel.send(msg.format(command=cmds['contest']))

    async def stop_contest(self):
        if self.contest_state == "inactive":
            return
        
        evts = self.config.get("events", DEFAULT_CONFIG["events"])
        
        # Refund participants if manually stopped
        if self.contest_pool > 0:
            for p in self.contest_participants:
                if p in player_data:
                    player_data[p]['loot_score'] += 10
            await db.save()
            self.log_callback(f"🛑 {evts['contest_name']} stopped manually. Points refunded.")
        else:
            self.log_callback(f"🛑 {evts['contest_name']} stopped manually.")

        self.contest_state = "inactive"
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            await channel.send(f"🛑 The {evts['contest_name']} has been stopped manually. Points refunded.")

# ============ BOT THREAD ============
class BotThread(QThread):
    log_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(dict)
    
    def __init__(self, token, channel, config, show_banner=True):
        super().__init__()
        self.token = token
        self.channel = channel
        self.config = config
        self.show_banner = show_banner
        self.bot = None
        self.loop = None
        
    def log(self, message):
        self.log_signal.emit(message)

    def update_status(self, status):
        self.status_signal.emit(status)

    def set_show_banner(self, enabled):
        if self.bot:
            self.bot.set_show_banner(enabled)

    def send_leaderboard_update(self, show_leaderboard):
        if not self.loop:
            return

        async def _send():
            message = get_leaderboard_message(show_leaderboard)
            await broadcast_to_overlays(message)

        self.loop.call_soon_threadsafe(lambda: self.loop.create_task(_send()))
        
    def run(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Start overlay server
            overlay_task = self.loop.create_task(start_overlay_server())
            self.log("🍞 Overlay server started on ws://localhost:8765")
            
            # Start bot
            self.bot = ChatCollectBot(self.token, self.channel, self.log, self.update_status, self.config)
            self.bot.set_show_banner(self.show_banner)
            bot_task = self.loop.create_task(self.bot.start())
            
            # Initial Leaderboard
            if self.config.get('show_leaderboard', False):
                 self.send_leaderboard_update(True)
            
            self.loop.run_until_complete(asyncio.gather(overlay_task, bot_task))
        except Exception as e:
            self.error_signal.emit(str(e))
            
    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

# ============ CUSTOM WIDGETS ============
class ToggleSwitch(QCheckBox):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self._bg_color = QColor("#444")
        self._circle_color = QColor("#DDD")
        self._active_color = QColor("#4CAF50")
        self._circle_position = 3
        self.animation = QPropertyAnimation(self, b"circle_position", self)
        self.animation.setEasingCurve(QEasingCurve.OutBounce)
        self.animation.setDuration(300)
        self.stateChanged.connect(self.start_transition)
        self.setFixedHeight(26)
        # Ensure width accommodates switch (50px) + padding (10px) + text
        self.setMinimumWidth(60 + self.fontMetrics().width(text))

    @pyqtProperty(float)
    def circle_position(self):
        return self._circle_position

    @circle_position.setter
    def circle_position(self, pos):
        self._circle_position = pos
        self.update()

    def start_transition(self, state):
        self.animation.stop()
        if state:
            self.animation.setEndValue(27) # 50 - 20 - 3
        else:
            self.animation.setEndValue(3)
        self.animation.start()

    def hitButton(self, pos):
        return self.contentsRect().contains(pos)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Switch Rect
        sw_width = 50
        sw_height = 26
        rect = QRectF(0, 0, sw_width, sw_height)
        
        if self.isChecked():
            p.setBrush(QBrush(self._active_color))
        else:
            p.setBrush(QBrush(self._bg_color))
        
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(rect, 13, 13)

        # Draw Circle
        p.setBrush(QBrush(self._circle_color))
        p.drawEllipse(QRectF(self._circle_position, 3, 20, 20))

        # Draw Text
        if self.text():
            p.setPen(self.palette().text().color())
            p.setFont(self.font())
            text_rect = QRectF(sw_width + 10, 0, self.width() - sw_width - 10, self.height())
            p.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, self.text())

class ToastNotification(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            background-color: #333; 
            color: white; 
            padding: 10px 20px; 
            border-radius: 5px; 
            font-weight: bold;
            border: 1px solid #555;
        """)
        self.setAlignment(Qt.AlignCenter)
        self.adjustSize()
        self.hide()
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)
        
        self.opacity_effect = None
        self.animation = None

    def show_message(self, text, duration=2000):
        self.setText(text)
        self.adjustSize()
        
        if self.parent():
            # Center horizontally, position near bottom
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = parent_rect.height() - self.height() - 50
            self.move(x, y)
            
        self.show()
        self.raise_()
        
        # Reset opacity
        # (Simple show for now, animation can be added if needed)
        self.timer.start(duration)

    def fade_out(self):
        self.hide()

# ============ MAIN GUI WINDOW ============
class ChatCollectGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bot_thread = None
        self.config = self.load_config()
        self.init_ui()
        
        # Toast
        self.toast = ToastNotification("", self)

    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)
        
    def get_dark_stylesheet(self):
        font_size = self.config.get('font_size', 10)
        return f"""
            QMainWindow {{
                background-color: #121212;
            }}
            QWidget {{
                background-color: #121212;
                color: #e0e0e0;
                font-family: 'Segoe UI', sans-serif;
                font-size: {font_size}pt;
            }}
            QGroupBox {{
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 0px;
                font-weight: bold;
                color: #ffffff;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                padding: 0 5px;
                background-color: #1e1e1e; 
            }}
            QLabel {{
                color: #b0b0b0;
                background-color: transparent;
            }}
            QLineEdit {{
                background-color: #252525;
                border: 1px solid #333;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                selection-background-color: #007acc;
                qproperty-alignment: 'AlignCenter';
            }}
            QLineEdit:focus {{
                border: 1px solid #007acc;
                background-color: #2d2d2d;
            }}
            QPushButton {{
                background-color: #007acc;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background-color: #0062a3;
                margin-top: 2px;
                border-bottom: 2px solid #004080;
            }}
            QPushButton:pressed {{
                background-color: #005a9e;
                margin-top: 4px;
                border-bottom: none;
            }}
            QPushButton:disabled {{
                background-color: #333;
                color: #777;
                border: none;
            }}
            QTextEdit {{
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 6px;
                color: #e0e0e0;
                selection-background-color: #007acc;
            }}
            QTabWidget::pane {{
                border: 1px solid #333;
                background: #1e1e1e;
                border-radius: 6px;
            }}
            QTabBar::tab {{
                background: #2d2d2d;
                color: #e0e0e0;
                padding: 10px 25px;
                border: 1px solid #333;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-width: 100px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: #1e1e1e;
                border-bottom: 2px solid #007acc;
                font-weight: bold;
                color: #ffffff;
            }}
            QComboBox {{
                background-color: #252525;
                border: 1px solid #333;
                border-radius: 6px;
                padding: 5px 10px;
                color: #ffffff;
                min-width: 6em;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 1px;
                border-left-color: #333;
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #2d2d2d;
            }}
            QComboBox::down-arrow {{
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #e0e0e0;
                margin-right: 2px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #252525;
                border: 1px solid #333;
                selection-background-color: #007acc;
                outline: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: #252525;
                border: 1px solid #333;
                selection-background-color: #007acc;
                outline: none;
            }}
            QPushButton#startBtn {{ background-color: #2ecc71; }}
            QPushButton#startBtn:hover {{ background-color: #27ae60; }}
            QPushButton#startBtn:pressed {{ background-color: #1e8449; }}

            QPushButton#stopBtn {{ background-color: #e74c3c; }}
            QPushButton#stopBtn:hover {{ background-color: #c0392b; }}
            QPushButton#stopBtn:pressed {{ background-color: #922b21; }}

            QPushButton#testExplosionBtn {{ background-color: #e67e22; }}
            QPushButton#testExplosionBtn:hover {{ background-color: #d35400; }}
            QPushButton#testExplosionBtn:pressed {{ background-color: #a04000; }}

            QPushButton#testLegendaryBtn {{ background-color: #f1c40f; color: #2c3e50; }}
            QPushButton#testLegendaryBtn:hover {{ background-color: #f39c12; }}
            QPushButton#testLegendaryBtn:pressed {{ background-color: #d68910; }}

            QPushButton#customTestBtn {{ background-color: #3498db; }}
            QPushButton#customTestBtn:hover {{ background-color: #2980b9; }}
            QPushButton#customTestBtn:pressed {{ background-color: #21618c; }}

            QPushButton#rushHourBtn {{ background-color: #e91e63; }}
            QPushButton#rushHourBtn:hover {{ background-color: #c2185b; }}
            QPushButton#rushHourBtn:pressed {{ background-color: #880e4f; }}

            QPushButton#lootDriveBtn {{ background-color: #9c27b0; }}
            QPushButton#lootDriveBtn:hover {{ background-color: #7b1fa2; }}
            QPushButton#lootDriveBtn:pressed {{ background-color: #4a148c; }}

            QPushButton#bountyHunterBtn {{ background-color: #607d8b; }}
            QPushButton#bountyHunterBtn:hover {{ background-color: #455a64; }}
            QPushButton#bountyHunterBtn:pressed {{ background-color: #263238; }}

            QPushButton#contestBtn {{ background-color: #ff5722; }}
            QPushButton#contestBtn:hover {{ background-color: #e64a19; }}
            QPushButton#contestBtn:pressed {{ background-color: #bf360c; }}

            QPushButton#backupBtn {{ background-color: #2196f3; }}
            QPushButton#backupBtn:hover {{ background-color: #1976d2; }}
            QPushButton#backupBtn:pressed {{ background-color: #0d47a1; }}

            QPushButton#restoreBtn {{ background-color: #ff9800; }}
            QPushButton#restoreBtn:hover {{ background-color: #f57c00; }}
            QPushButton#restoreBtn:pressed {{ background-color: #e65100; }}

            QPushButton#saveBtn {{ background-color: #4caf50; }}
            QPushButton#saveBtn:hover {{ background-color: #388e3c; }}
            QPushButton#saveBtn:pressed {{ background-color: #1b5e20; }}
            
            QPushButton#helpBtn {{ background-color: #00bcd4; }}
            QPushButton#helpBtn:hover {{ background-color: #0097a7; }}
            QPushButton#helpBtn:pressed {{ background-color: #006064; }}

            QPushButton#delBtn {{ background-color: #d32f2f; }}
            QPushButton#delBtn:hover {{ background-color: #b71c1c; }}
            QPushButton#delBtn:pressed {{ background-color: #c62828; }}
        """

    def get_light_stylesheet(self):
        font_size = self.config.get('font_size', 10)
        return f"""
            QMainWindow {{
                background-color: #f0f0f0;
            }}
            QWidget {{
                background-color: #f0f0f0;
                color: #333333;
                font-family: 'Segoe UI', sans-serif;
                font-size: {font_size}pt;
            }}
            QGroupBox {{
                background-color: #ffffff;
                border: 1px solid #ccc;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 0px;
                font-weight: bold;
                color: #333333;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                padding: 0 5px;
                background-color: #ffffff; 
            }}
            QLabel {{
                color: #333333;
                background-color: transparent;
            }}
            QLineEdit {{
                background-color: #ffffff;
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 8px;
                color: #333333;
                selection-background-color: #007acc;
                qproperty-alignment: 'AlignCenter';
            }}
            QLineEdit:focus {{
                border: 1px solid #007acc;
                background-color: #ffffff;
            }}
            QPushButton {{
                background-color: #007acc;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background-color: #0062a3;
                margin-top: 2px;
                border-bottom: 2px solid #004080;
            }}
            QPushButton:pressed {{
                background-color: #005a9e;
                margin-top: 4px;
                border-bottom: none;
            }}
            QPushButton:disabled {{
                background-color: #e0e0e0;
                color: #a0a0a0;
                border: none;
            }}
            QTextEdit {{
                background-color: #ffffff;
                border: 1px solid #ccc;
                border-radius: 6px;
                color: #333333;
                selection-background-color: #007acc;
            }}
            QTabWidget::pane {{
                border: 1px solid #ccc;
                background: #ffffff;
                border-radius: 6px;
            }}
            QTabBar::tab {{
                background: #e0e0e0;
                color: #333333;
                padding: 10px 25px;
                border: 1px solid #ccc;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-width: 100px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: #ffffff;
                border-bottom: 2px solid #007acc;
                font-weight: bold;
                color: #333333;
            }}
            QComboBox {{
                background-color: #ffffff;
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 5px 10px;
                color: #333333;
                min-width: 6em;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 1px;
                border-left-color: #ccc;
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #e0e0e0;
            }}
            QComboBox::down-arrow {{
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #333333;
                margin-right: 2px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #ffffff;
                border: 1px solid #ccc;
                selection-background-color: #007acc;
                outline: none;
                color: #333333;
            }}
            /* Keep colored buttons as they are, they work on light theme too */
            QPushButton#startBtn {{ background-color: #2ecc71; }}
            QPushButton#startBtn:hover {{ background-color: #27ae60; }}
            QPushButton#startBtn:pressed {{ background-color: #1e8449; }}

            QPushButton#stopBtn {{ background-color: #e74c3c; }}
            QPushButton#stopBtn:hover {{ background-color: #c0392b; }}
            QPushButton#stopBtn:pressed {{ background-color: #922b21; }}

            QPushButton#testExplosionBtn {{ background-color: #e67e22; }}
            QPushButton#testExplosionBtn:hover {{ background-color: #d35400; }}
            QPushButton#testExplosionBtn:pressed {{ background-color: #a04000; }}

            QPushButton#testLegendaryBtn {{ background-color: #f1c40f; color: #2c3e50; }}
            QPushButton#testLegendaryBtn:hover {{ background-color: #f39c12; }}
            QPushButton#testLegendaryBtn:pressed {{ background-color: #d68910; }}

            QPushButton#customTestBtn {{ background-color: #3498db; }}
            QPushButton#customTestBtn:hover {{ background-color: #2980b9; }}
            QPushButton#customTestBtn:pressed {{ background-color: #21618c; }}

            QPushButton#rushHourBtn {{ background-color: #e91e63; }}
            QPushButton#rushHourBtn:hover {{ background-color: #c2185b; }}
            QPushButton#rushHourBtn:pressed {{ background-color: #880e4f; }}

            QPushButton#lootDriveBtn {{ background-color: #9c27b0; }}
            QPushButton#lootDriveBtn:hover {{ background-color: #7b1fa2; }}
            QPushButton#lootDriveBtn:pressed {{ background-color: #4a148c; }}

            QPushButton#bountyHunterBtn {{ background-color: #607d8b; }}
            QPushButton#bountyHunterBtn:hover {{ background-color: #455a64; }}
            QPushButton#bountyHunterBtn:pressed {{ background-color: #263238; }}

            QPushButton#contestBtn {{ background-color: #ff5722; }}
            QPushButton#contestBtn:hover {{ background-color: #e64a19; }}
            QPushButton#contestBtn:pressed {{ background-color: #bf360c; }}

            QPushButton#backupBtn {{ background-color: #2196f3; }}
            QPushButton#backupBtn:hover {{ background-color: #1976d2; }}
            QPushButton#backupBtn:pressed {{ background-color: #0d47a1; }}

            QPushButton#restoreBtn {{ background-color: #ff9800; }}
            QPushButton#restoreBtn:hover {{ background-color: #f57c00; }}
            QPushButton#restoreBtn:pressed {{ background-color: #e65100; }}

            QPushButton#saveBtn {{ background-color: #4caf50; }}
            QPushButton#saveBtn:hover {{ background-color: #388e3c; }}
            QPushButton#saveBtn:pressed {{ background-color: #1b5e20; }}
            
            QPushButton#helpBtn {{ background-color: #00bcd4; }}
            QPushButton#helpBtn:hover {{ background-color: #0097a7; }}
            QPushButton#helpBtn:pressed {{ background-color: #006064; }}

            QPushButton#delBtn {{ background-color: #d32f2f; }}
            QPushButton#delBtn:hover {{ background-color: #b71c1c; }}
            QPushButton#delBtn:pressed {{ background-color: #c62828; }}
        """

    def init_ui(self):
        self.setWindowTitle(f"ChatCollect v{CURRENT_VERSION}")
        
        # Set Window Icon
        icon_path = self.resource_path("exe_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setGeometry(100, 100, 700, 600)
        
        # Enable Dark Title Bar (Windows 10/11)
        try:
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            hwnd = int(self.winId())
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), 4)
        except Exception:
            pass

        # Dark mode stylesheet
        self.setStyleSheet(self.get_dark_stylesheet())
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Check for updates
        QTimer.singleShot(2000, self.check_for_updates)
        
        # Create Tabs
        self.tabs = QTabWidget()
        self.tab_collection = QWidget()
        self.tab_setup = QWidget()
        self.tab_settings = QWidget()
        
        self.tabs.addTab(self.tab_collection, "Collection")
        self.tabs.addTab(self.tab_setup, "Setup")
        self.tabs.addTab(self.tab_settings, "Settings")
        
        main_layout.addWidget(self.tabs)
        
        # --- Tab 1: Collection (Existing UI) ---
        layout = QVBoxLayout(self.tab_collection)
        
        # Configuration Group
        config_group = QGroupBox("Bot Configuration")
        config_layout = QVBoxLayout()
        
        # Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("OAuth Token:"))
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setText(self.config.get('token', ''))
        token_layout.addWidget(self.token_input)
        config_layout.addLayout(token_layout)
        
        # Channel
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("Channel Name:"))
        self.channel_input = QLineEdit()
        self.channel_input.setText(self.config.get('channel', ''))
        channel_layout.addWidget(self.channel_input)
        config_layout.addLayout(channel_layout)

        # Save Config Button
        self.save_config_btn = QPushButton("💾 Save Configuration")
        self.save_config_btn.setObjectName("saveBtn")
        self.save_config_btn.clicked.connect(self.save_configuration)
        config_layout.addWidget(self.save_config_btn)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Control Buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Start Bot")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.clicked.connect(self.start_bot)
        btn_layout.addWidget(self.start_btn)
        
        self.test_explosion_btn = QPushButton("💥 Test Explosion")
        self.test_explosion_btn.setObjectName("testExplosionBtn")
        self.test_explosion_btn.clicked.connect(self.test_explosion)
        btn_layout.addWidget(self.test_explosion_btn)
        
        self.test_legendary_btn = QPushButton("✨ Test Legendary")
        self.test_legendary_btn.setObjectName("testLegendaryBtn")
        self.test_legendary_btn.clicked.connect(self.test_legendary)
        btn_layout.addWidget(self.test_legendary_btn)
        
        layout.addLayout(btn_layout)

        # Test Controls Group
        test_group = QGroupBox("Test")
        test_layout = QHBoxLayout()
        
        test_layout.addStretch()

        # Rarity Dropdown
        test_layout.addWidget(QLabel("Rarity:"))
        self.rarity_combo = QComboBox()
        self.rarity_combo.setEditable(True)
        self.rarity_combo.lineEdit().setReadOnly(True)
        self.rarity_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.rarity_combo.addItems(["Standard", "Ruined", "Shiny", "Golden", "Legendary"])
        self.rarity_combo.setFixedWidth(120)
        test_layout.addWidget(self.rarity_combo)
        
        test_layout.addSpacing(20)

        # Item Dropdown
        test_layout.addWidget(QLabel("Item:"))
        self.item_combo = QComboBox()
        self.item_combo.setEditable(True)
        self.item_combo.lineEdit().setReadOnly(True)
        self.item_combo.lineEdit().setAlignment(Qt.AlignCenter)
        # Populate items
        all_items = asset_manager.normal_items + asset_manager.legendary_items
        for filename in all_items:
            display_name = format_item_name(filename)
            self.item_combo.addItem(display_name, filename) # Store filename as user data
        self.item_combo.setFixedWidth(200)
        test_layout.addWidget(self.item_combo)
        
        test_layout.addStretch()

        # Test Button
        self.custom_test_btn = QPushButton("🧪 Test")
        self.custom_test_btn.setObjectName("customTestBtn")
        self.custom_test_btn.clicked.connect(self.test_custom_bake)
        test_layout.addWidget(self.custom_test_btn)

        test_group.setLayout(test_layout)
        layout.addWidget(test_group)

        # Overlay Settings (Between Test and Events)
        overlay_group = QGroupBox("Overlay Settings")
        overlay_layout = QHBoxLayout()
        
        self.show_banner_cb = ToggleSwitch("Show Banner")
        self.show_banner_cb.setChecked(self.config.get('show_banner', True))
        self.show_banner_cb.stateChanged.connect(self.toggle_banner)
        overlay_layout.addWidget(self.show_banner_cb)
        
        self.show_leaderboard_cb = ToggleSwitch("Show Leaderboard")
        self.show_leaderboard_cb.setChecked(self.config.get('show_leaderboard', False))
        self.show_leaderboard_cb.stateChanged.connect(self.toggle_leaderboard)
        overlay_layout.addWidget(self.show_leaderboard_cb)
        
        overlay_group.setLayout(overlay_layout)
        layout.addWidget(overlay_group)

        # Events Group
        events_group = QGroupBox("Events")
        events_layout = QGridLayout()
        
        # Validators
        int_validator = QIntValidator(1, 9999)

        # Rush Hour
        self.rh_label = QLabel("🚀 Rush Hour")
        events_layout.addWidget(self.rh_label, 0, 0)
        self.rh_duration = QLineEdit("2")
        self.rh_duration.setValidator(int_validator)
        self.rh_duration.setFixedWidth(50)
        self.rh_duration.setPlaceholderText("Min")
        events_layout.addWidget(self.rh_duration, 0, 1)
        events_layout.addWidget(QLabel("minutes"), 0, 2)
        
        self.rush_hour_btn = QPushButton("Start")
        self.rush_hour_btn.setObjectName("rushHourBtn")
        self.rush_hour_btn.clicked.connect(self.trigger_rush_hour)
        events_layout.addWidget(self.rush_hour_btn, 0, 3)

        self.stop_rh_btn = QPushButton("Stop")
        self.stop_rh_btn.setObjectName("stopBtn")
        self.stop_rh_btn.clicked.connect(self.stop_rush_hour)
        events_layout.addWidget(self.stop_rh_btn, 0, 4)
        
        # Loot Drive
        self.ld_label = QLabel("🎒 Loot Drive")
        events_layout.addWidget(self.ld_label, 1, 0)
        self.bs_duration = QLineEdit("20")
        self.bs_duration.setValidator(int_validator)
        self.bs_duration.setFixedWidth(50)
        self.bs_duration.setPlaceholderText("Min")
        events_layout.addWidget(self.bs_duration, 1, 1)
        events_layout.addWidget(QLabel("minutes"), 1, 2)

        self.loot_drive_btn = QPushButton("Start")
        self.loot_drive_btn.setObjectName("lootDriveBtn")
        self.loot_drive_btn.clicked.connect(self.trigger_loot_drive)
        events_layout.addWidget(self.loot_drive_btn, 1, 3)

        self.stop_bs_btn = QPushButton("Stop")
        self.stop_bs_btn.setObjectName("stopBtn")
        self.stop_bs_btn.clicked.connect(self.stop_loot_drive)
        events_layout.addWidget(self.stop_bs_btn, 1, 4)
        
        # Bounty Hunter
        self.bh_label = QLabel("🧐 Bounty Hunter")
        events_layout.addWidget(self.bh_label, 2, 0)
        self.fc_duration = QLineEdit("10")
        self.fc_duration.setValidator(int_validator)
        self.fc_duration.setFixedWidth(50)
        self.fc_duration.setPlaceholderText("Min")
        events_layout.addWidget(self.fc_duration, 2, 1)
        events_layout.addWidget(QLabel("minutes"), 2, 2)

        self.bounty_hunter_btn = QPushButton("Start")
        self.bounty_hunter_btn.setObjectName("bountyHunterBtn")
        self.bounty_hunter_btn.clicked.connect(self.trigger_bounty_hunter)
        events_layout.addWidget(self.bounty_hunter_btn, 2, 3)

        self.stop_fc_btn = QPushButton("Stop")
        self.stop_fc_btn.setObjectName("stopBtn")
        self.stop_fc_btn.clicked.connect(self.stop_bounty_hunter)
        events_layout.addWidget(self.stop_fc_btn, 2, 4)
        
        # Contest
        self.ct_label = QLabel("⚔️ Contest")
        events_layout.addWidget(self.ct_label, 3, 0)
        self.bo_duration = QLineEdit("2")
        self.bo_duration.setValidator(int_validator)
        self.bo_duration.setFixedWidth(50)
        self.bo_duration.setPlaceholderText("Min")
        events_layout.addWidget(self.bo_duration, 3, 1)
        events_layout.addWidget(QLabel("minutes"), 3, 2)

        self.contest_btn = QPushButton("Start")
        self.contest_btn.setObjectName("contestBtn")
        self.contest_btn.clicked.connect(self.trigger_contest)
        events_layout.addWidget(self.contest_btn, 3, 3)

        self.stop_bo_btn = QPushButton("Stop")
        self.stop_bo_btn.setObjectName("stopBtn")
        self.stop_bo_btn.clicked.connect(self.stop_contest)
        events_layout.addWidget(self.stop_bo_btn, 3, 4)
        
        events_group.setLayout(events_layout)
        layout.addWidget(events_group)

        # Active Events Status Group
        status_group = QGroupBox("Active Events Status")
        status_layout = QHBoxLayout()

        # Rush Hour Status
        rh_layout = QVBoxLayout()
        self.rh_status_header = QLabel("🚀 Rush Hour")
        rh_layout.addWidget(self.rh_status_header)
        self.rh_status_label = QLabel("Inactive")
        self.rh_status_label.setObjectName("statusLabel")
        rh_layout.addWidget(self.rh_status_label)
        status_layout.addLayout(rh_layout)

        # Loot Drive Status
        bs_layout = QVBoxLayout()
        self.ld_status_header = QLabel("🎒 Loot Drive")
        bs_layout.addWidget(self.ld_status_header)
        self.bs_status_label = QLabel("Inactive")
        self.bs_status_label.setObjectName("statusLabel")
        bs_layout.addWidget(self.bs_status_label)
        status_layout.addLayout(bs_layout)

        # Bounty Hunter Status
        fc_layout = QVBoxLayout()
        self.bh_status_header = QLabel("🧐 Bounty Hunter")
        fc_layout.addWidget(self.bh_status_header)
        self.fc_status_label = QLabel("Inactive")
        self.fc_status_label.setObjectName("statusLabel")
        fc_layout.addWidget(self.fc_status_label)
        status_layout.addLayout(fc_layout)

        # Contest Status
        bo_layout = QVBoxLayout()
        self.ct_status_header = QLabel("⚔️ Contest")
        bo_layout.addWidget(self.ct_status_header)
        self.bo_status_label = QLabel("Inactive")
        self.bo_status_label.setObjectName("statusLabel")
        bo_layout.addWidget(self.bo_status_label)
        status_layout.addLayout(bo_layout)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Log Display
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_display)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # --- Tab 2: Setup ---
        self.setup_setup_tab()

        # --- Tab 3: Settings ---
        self.setup_settings_tab()
        
        self.log("🍞 ChatCollect Bot GUI Ready")
        self.log("Configure your settings and click 'Start Bot'")
        
        # Initial Label Update
        self.update_event_labels()

    def setup_setup_tab(self):
        layout = QVBoxLayout(self.tab_setup)
        
        # Nested Tabs
        self.setup_tabs = QTabWidget()
        layout.addWidget(self.setup_tabs)
        
        self.setup_inputs = {}
        
        # --- Commands Tab ---
        cmd_tab = QWidget()
        cmd_layout = QFormLayout()
        self.add_config_input(cmd_layout, "commands", "loot", "Loot Command:")
        self.add_config_input(cmd_layout, "commands", "leaderboard", "Leaderboard Command:")
        self.add_config_input(cmd_layout, "commands", "contest", "Contest Command:")
        self.add_config_input(cmd_layout, "commands", "use", "Use Item Command:")
        cmd_tab.setLayout(cmd_layout)
        self.setup_tabs.addTab(cmd_tab, "💬 Commands")

        # --- Messages Tab ---
        msg_tab = QWidget()
        msg_layout = QVBoxLayout()
        
        # Syntax Help Button
        help_btn = QPushButton("❓ Syntax Help")
        help_btn.setObjectName("helpBtn")
        help_btn.clicked.connect(self.show_syntax_help)
        msg_layout.addWidget(help_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QFormLayout(scroll_content)
        
        self.add_config_input(scroll_layout, "messages", "cooldown", "Cooldown Message:")
        self.add_config_input(scroll_layout, "messages", "loot_success", "Loot Success:")
        self.add_config_input(scroll_layout, "messages", "loot_legendary", "Legendary Loot:")
        self.add_config_input(scroll_layout, "messages", "loot_ruined", "Loot Ruined:")
        self.add_config_input(scroll_layout, "messages", "loot_shiny", "Loot Shiny:")
        self.add_config_input(scroll_layout, "messages", "loot_golden", "Loot Golden (Masterpiece):")
        self.add_config_input(scroll_layout, "messages", "rank_up", "Rank Up:")
        self.add_config_input(scroll_layout, "messages", "contest_start", "Contest Start:")
        self.add_config_input(scroll_layout, "messages", "contest_winner", "Contest Winner:")
        self.add_config_input(scroll_layout, "messages", "rush_hour_start", "Rush Hour Start:")
        self.add_config_input(scroll_layout, "messages", "loot_drive_start", "Loot Drive Start:")
        self.add_config_input(scroll_layout, "messages", "bounty_hunter_spawn", "Bounty Hunter Spawn:")
        self.add_config_input(scroll_layout, "messages", "bounty_hunter_satisfied", "Bounty Hunter Satisfied:")
        
        scroll.setWidget(scroll_content)
        msg_layout.addWidget(scroll)
        msg_tab.setLayout(msg_layout)
        self.setup_tabs.addTab(msg_tab, "📢 Messages")

        # --- Events Tab ---
        evt_tab = QWidget()
        evt_layout = QFormLayout()
        self.add_config_input(evt_layout, "events", "rush_hour_name", "Rush Hour Name:")
        self.add_config_input(evt_layout, "events", "loot_drive_name", "Loot Drive Name:")
        self.add_config_input(evt_layout, "events", "bounty_hunter_name", "Bounty Hunter Name:")
        self.add_config_input(evt_layout, "events", "contest_name", "Contest Name:")
        evt_tab.setLayout(evt_layout)
        self.setup_tabs.addTab(evt_tab, "🎉 Events")

        # --- Ranks Tab ---
        ranks_tab = QWidget()
        ranks_layout = QVBoxLayout()
        
        # Scroll Area for Ranks
        rank_scroll = QScrollArea()
        rank_scroll.setWidgetResizable(True)
        rank_scroll_content = QWidget()
        self.ranks_layout = QVBoxLayout(rank_scroll_content)
        self.ranks_layout.setSpacing(2)
        self.ranks_layout.setContentsMargins(10, 10, 10, 10)
        
        # Load ranks
        self.rank_inputs = []
        current_ranks = self.config.get("ranks", DEFAULT_CONFIG["ranks"])
        current_ranks.sort(key=lambda x: x["score"])
        
        for r in current_ranks:
            self.add_rank_row(r["score"], r["title"])
            
        rank_scroll.setWidget(rank_scroll_content)
        ranks_layout.addWidget(rank_scroll)
        
        # Add Rank Button
        add_rank_btn = QPushButton("➕ Add Rank")
        add_rank_btn.clicked.connect(lambda: self.add_rank_row(0, "New Rank"))
        ranks_layout.addWidget(add_rank_btn)
        
        ranks_tab.setLayout(ranks_layout)
        self.setup_tabs.addTab(ranks_tab, "🏆 Ranks")
        
        # Save Button for Setup Tab
        btn_layout = QHBoxLayout()
        
        load_btn = QPushButton("📂 Load Config File")
        load_btn.clicked.connect(self.load_config_from_file)
        btn_layout.addWidget(load_btn)

        save_btn = QPushButton("💾 Save Configuration")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.save_configuration)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)

        # --- Balance Tab ---
        balance_tab = QWidget()
        balance_layout = QVBoxLayout()
        
        # Grid for inputs
        grid_layout = QGridLayout()
        
        # Cooldown
        grid_layout.addWidget(QLabel("Cooldown (seconds):"), 0, 0)
        self.cooldown_spin = QSpinBox()
        self.cooldown_spin.setRange(1, 3600)
        self.cooldown_spin.setValue(int(self.config.get('cooldown', 60)))
        self.cooldown_spin.valueChanged.connect(self.save_settings_change)
        grid_layout.addWidget(self.cooldown_spin, 0, 1)
        
        # Shiny Chance
        grid_layout.addWidget(QLabel("Shiny Chance (1 in X):"), 1, 0)
        self.shiny_chance_spin = QSpinBox()
        self.shiny_chance_spin.setRange(1, 1000000)
        self.shiny_chance_spin.setValue(int(self.config.get('shiny_chance', 10000)))
        self.shiny_chance_spin.valueChanged.connect(self.save_settings_change)
        grid_layout.addWidget(self.shiny_chance_spin, 1, 1)
        
        # Legendary Chance
        grid_layout.addWidget(QLabel("Legendary Chance (1 in X):"), 2, 0)
        self.legendary_chance_spin = QSpinBox()
        self.legendary_chance_spin.setRange(1, 1000000)
        self.legendary_chance_spin.setValue(int(self.config.get('legendary_chance', 1000)))
        self.legendary_chance_spin.valueChanged.connect(self.save_settings_change)
        grid_layout.addWidget(self.legendary_chance_spin, 2, 1)
        
        balance_layout.addLayout(grid_layout)
        
        # Points Configuration
        points_group = QGroupBox("Point Values")
        points_layout = QFormLayout()
        
        self.add_config_input(points_layout, "points", "standard_min", "Standard Min:")
        self.add_config_input(points_layout, "points", "standard_max", "Standard Max:")
        self.add_config_input(points_layout, "points", "shiny", "Shiny Points:")
        self.add_config_input(points_layout, "points", "golden", "Golden Points:")
        self.add_config_input(points_layout, "points", "legendary", "Legendary Min:")
        self.add_config_input(points_layout, "points", "ruined", "Ruined Points:")
        self.add_config_input(points_layout, "points", "bounty_hunter", "Bounty Hunter Bonus:")
        
        points_group.setLayout(points_layout)
        balance_layout.addWidget(points_group)
        
        balance_layout.addStretch()
        
        balance_tab.setLayout(balance_layout)
        self.setup_tabs.addTab(balance_tab, "⚖️ Balance")

    def add_config_input(self, layout, category, key, label_text):
        layout.addRow(QLabel(label_text))
        input_field = QLineEdit()
        # Get value safely
        val = self.config.get(category, {}).get(key, "")
        input_field.setText(str(val))
        layout.addRow(input_field)
        
        if category not in self.setup_inputs:
            self.setup_inputs[category] = {}
        self.setup_inputs[category][key] = input_field

    def add_rank_row(self, score, title):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        score_input = QLineEdit(str(score))
        score_input.setValidator(QIntValidator())
        score_input.setFixedWidth(80)
        score_input.setPlaceholderText("Score")
        
        title_input = QLineEdit(title)
        title_input.setPlaceholderText("Rank Title")
        
        del_btn = QPushButton("❌")
        del_btn.setObjectName("delBtn")
        del_btn.setFixedWidth(30)
        del_btn.clicked.connect(lambda: self.remove_rank_row(row_widget, score_input, title_input))
        
        row_layout.addWidget(QLabel("Score:"))
        row_layout.addWidget(score_input)
        row_layout.addWidget(QLabel("Title:"))
        row_layout.addWidget(title_input)
        row_layout.addWidget(del_btn)
        
        self.ranks_layout.addWidget(row_widget)
        self.rank_inputs.append((score_input, title_input))

    def remove_rank_row(self, widget, score_input, title_input):
        widget.deleteLater()
        if (score_input, title_input) in self.rank_inputs:
            self.rank_inputs.remove((score_input, title_input))

    def setup_settings_tab(self):
        layout = QVBoxLayout(self.tab_settings)
        
        # Appearance Group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QGridLayout()
        
        # Theme
        appearance_layout.addWidget(QLabel("Theme:"), 0, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.setEditable(True)
        self.theme_combo.lineEdit().setReadOnly(True)
        self.theme_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.theme_combo.addItems(["Dark Mode", "Light Mode", "System Default"])
        self.theme_combo.setCurrentText(self.config.get('theme', 'Dark Mode'))
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        appearance_layout.addWidget(self.theme_combo, 0, 1)
        
        # Font Family
        appearance_layout.addWidget(QLabel("Font Family:"), 1, 0)
        self.font_combo = QFontComboBox()
        self.font_combo.setEditable(True)
        self.font_combo.lineEdit().setReadOnly(True)
        self.font_combo.lineEdit().setAlignment(Qt.AlignCenter)
        current_font = self.config.get('font_family', 'Segoe UI')
        self.font_combo.setCurrentFont(QFont(current_font))
        self.font_combo.currentFontChanged.connect(self.apply_font)
        appearance_layout.addWidget(self.font_combo, 1, 1)
        
        # Font Size
        appearance_layout.addWidget(QLabel("Font Size:"), 2, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(self.config.get('font_size', 11))
        self.font_size_spin.valueChanged.connect(self.apply_font)
        appearance_layout.addWidget(self.font_size_spin, 2, 1)
        
        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)
        
        # Data Management Group
        data_group = QGroupBox("Data Management")
        data_layout = QGridLayout()
        
        # Output Directory
        data_layout.addWidget(QLabel("Output Directory:"), 0, 0)
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setText(self.config.get('output_dir', os.getcwd()))
        self.output_dir_input.setReadOnly(True)
        data_layout.addWidget(self.output_dir_input, 0, 1)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_output_dir)
        data_layout.addWidget(self.browse_btn, 0, 2)
        
        # Auto-Save Interval
        data_layout.addWidget(QLabel("Auto-Save Interval (min):"), 1, 0)
        self.autosave_spin = QSpinBox()
        self.autosave_spin.setRange(1, 60)
        self.autosave_spin.setValue(self.config.get('autosave_interval', 5))
        self.autosave_spin.valueChanged.connect(self.save_settings_change)
        data_layout.addWidget(self.autosave_spin, 1, 1)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # Backup & Restore Group
        backup_group = QGroupBox("Backup & Restore")
        backup_layout = QHBoxLayout()
        
        self.backup_btn = QPushButton("📂 Backup Config")
        self.backup_btn.setObjectName("backupBtn")
        self.backup_btn.clicked.connect(self.backup_config)
        backup_layout.addWidget(self.backup_btn)
        
        self.restore_btn = QPushButton("♻️ Restore Config")
        self.restore_btn.setObjectName("restoreBtn")
        self.restore_btn.clicked.connect(self.restore_config)
        backup_layout.addWidget(self.restore_btn)
        
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        layout.addStretch()

    def show_syntax_help(self):
        help_text = """
        <h3>Available Placeholders:</h3>
        <ul>
        <li><b>{username}</b>: The name of the user who triggered the event.</li>
        <li><b>{item}</b>: The name of the looted item.</li>
        <li><b>{points}</b>: The number of points gained.</li>
        <li><b>{rank}</b>: The user's current rank title.</li>
        <li><b>{score}</b>: The user's total score.</li>
        <li><b>{remaining}</b>: Seconds remaining for cooldowns.</li>
        <li><b>{target}</b>: The target goal for Loot Drive.</li>
        <li><b>{command}</b>: The command name (e.g., !contest).</li>
        <li><b>{prize}</b>: The prize amount for contests.</li>
        </ul>
        <br>
        <i>Note: Not all placeholders work for every message.</i>
        """
        QMessageBox.information(self, "Message Syntax Help", help_text)

    def backup_config(self):
        try:
            backup_dir = os.path.join(os.getcwd(), "backups")
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"config_backup_{timestamp}.json")
            
            shutil.copy2(CONFIG_FILE, backup_file)
            self.log(f"✅ Configuration backed up to: {backup_file}")
            QMessageBox.information(self, "Backup Successful", f"Backup created:\n{backup_file}")
        except Exception as e:
            self.log(f"❌ Backup failed: {e}")
            QMessageBox.critical(self, "Backup Failed", str(e))

    def restore_config(self):
        backup_dir = os.path.join(os.getcwd(), "backups")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Backup File", backup_dir, "JSON Files (*.json)")
        
        if file_path:
            try:
                shutil.copy2(file_path, CONFIG_FILE)
                self.config = self.load_config()
                
                self.log(f"✅ Configuration restored from: {file_path}")
                QMessageBox.information(self, "Restore Successful", "Configuration restored! Please restart the application to ensure all settings take effect.")
            except Exception as e:
                self.log(f"❌ Restore failed: {e}")
                QMessageBox.critical(self, "Restore Failed", str(e))

    def apply_theme(self, theme_name):
        self.config['theme'] = theme_name
        if theme_name == "Light Mode":
            self.setStyleSheet(self.get_light_stylesheet()) 
        elif theme_name == "Dark Mode":
            self.setStyleSheet(self.get_dark_stylesheet())
        elif theme_name == "System Default":
            self.setStyleSheet("") # Fallback to system
        self.save_configuration()

    def apply_font(self):
        font = self.font_combo.currentFont()
        size = self.font_size_spin.value()
        font.setPointSize(size)
        QApplication.setFont(font)
        self.config['font_family'] = font.family()
        self.config['font_size'] = size
        
        # Re-apply stylesheet to update font size
        current_theme = self.theme_combo.currentText()
        if current_theme == "Light Mode":
            self.setStyleSheet(self.get_light_stylesheet()) 
        elif current_theme == "Dark Mode":
            self.setStyleSheet(self.get_dark_stylesheet())
            
        self.save_configuration()

    def check_for_updates(self):
        """Check for updates in a separate thread"""
        def _check():
            try:
                with urllib.request.urlopen(UPDATE_VERSION_URL, timeout=5) as response:
                    remote_version = response.read().decode('utf-8').strip()
                
                if remote_version != CURRENT_VERSION:
                    # Signal main thread to prompt
                    QTimer.singleShot(0, lambda: self.prompt_update(remote_version))
            except Exception as e:
                print(f"Update check failed: {e}")

        import threading
        threading.Thread(target=_check, daemon=True).start()

    def prompt_update(self, remote_version):
        reply = QMessageBox.question(self, "Update Available", 
                                     f"A new version ({remote_version}) is available!\n\n"
                                     "Do you want to update now?\n"
                                     "(This will backup your settings, download the new version, and restart)",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.perform_update()

    def perform_update(self):
        self.log("🔄 Starting update process...")
        
        # 1. Create Backup (Keep max 2)
        self.manage_auto_backups()
        
        try:
            # 2. Download Additional Files (README, Overlay, Build folder)
            self.log("⬇️ Downloading updated files...")
            files_to_update = [
                "README.md",
                "overlay/overlay.html",
                "build/chatcollect_gui.py",
                "build/requirements.txt",
                "build/build_exe.bat",
                "build/install_requirements.bat",
                "build/exe_icon.ico"
            ]
            
            for file_path in files_to_update:
                url = REPO_RAW_URL + file_path
                local_path = os.path.join(BASE_PATH, file_path)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                try:
                    self.log(f"   Downloading {file_path}...")
                    with urllib.request.urlopen(url) as response, open(local_path, 'wb') as out_file:
                        shutil.copyfileobj(response, out_file)
                except Exception as e:
                    self.log(f"⚠️ Failed to update {file_path}: {e}")

            # 3. Download new EXE
            new_exe_name = "ChatCollect_new.exe"
            self.log("⬇️ Downloading new executable...")
            
            # Download with progress (blocking UI for simplicity, or use thread)
            # Using urllib for simplicity
            with urllib.request.urlopen(UPDATE_EXE_URL) as response, open(new_exe_name, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
                
            self.log("✅ Download complete.")
            
            # 4. Create Updater Script
            updater_bat = "update_restart.bat"
            current_exe = sys.executable
            
            with open(updater_bat, "w") as bat:
                bat.write("@echo off\n")
                bat.write("timeout /t 2 /nobreak >nul\n")
                bat.write(f'move /y "{new_exe_name}" "{current_exe}"\n')
                bat.write(f'start "" "{current_exe}"\n')
                bat.write(f'del "{updater_bat}"\n')
            
            self.log("🚀 Restarting to apply update...")
            
            # 5. Launch Updater and Exit
            subprocess.Popen([updater_bat], shell=True)
            QApplication.quit()
            
        except Exception as e:
            self.log(f"❌ Update failed: {e}")
            QMessageBox.critical(self, "Update Failed", f"Could not update: {e}")

    def manage_auto_backups(self):
        """Create backup and ensure only 2 newest exist"""
        try:
            backup_dir = os.path.join(os.getcwd(), "backups")
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            # Create new backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Backup Config
            shutil.copy2(CONFIG_FILE, os.path.join(backup_dir, f"config_auto_{timestamp}.json"))
            # Backup Data
            if os.path.exists(DB_PATH):
                shutil.copy2(DB_PATH, os.path.join(backup_dir, f"data_auto_{timestamp}.txt"))
            
            self.log("✅ Auto-backup created.")
            
            # Cleanup old backups (Keep newest 2 sets)
            # Filter for auto backups
            files = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith("config_auto_")], key=os.path.getmtime)
            
            while len(files) > 2:
                oldest_config = files.pop(0)
                # Try to find matching data file
                timestamp_part = oldest_config.split("_")[-1].replace(".json", "")
                oldest_data = os.path.join(backup_dir, f"data_auto_{timestamp_part}.txt")
                
                try:
                    os.remove(oldest_config)
                    if os.path.exists(oldest_data):
                        os.remove(oldest_data)
                    self.log(f"🗑️ Removed old backup: {os.path.basename(oldest_config)}")
                except Exception as e:
                    print(f"Failed to remove old backup: {e}")
                    
        except Exception as e:
            self.log(f"⚠️ Auto-backup warning: {e}")

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_dir_input.setText(directory)
            self.config['output_dir'] = directory
            self.save_configuration()

    def toggle_leaderboard(self, state):
        enabled = state == Qt.Checked
        self.config['show_leaderboard'] = enabled
        self.save_configuration()
        if self.bot_thread:
            self.bot_thread.send_leaderboard_update(enabled)

    def save_settings_change(self):
        self.save_configuration()
        
    def load_config(self):
        # Auto-restore from backup if config is missing
        if not os.path.exists(CONFIG_FILE):
            backup_dir = os.path.join(os.getcwd(), "backups")
            if os.path.exists(backup_dir):
                # Find latest auto-backup
                auto_backups = [f for f in os.listdir(backup_dir) if f.startswith("config_auto_") and f.endswith(".json")]
                if auto_backups:
                    auto_backups.sort(reverse=True) # Latest timestamp first
                    latest_backup = os.path.join(backup_dir, auto_backups[0])
                    try:
                        shutil.copy2(latest_backup, CONFIG_FILE)
                        print(f"Restored config from auto-backup: {latest_backup}")
                    except Exception as e:
                        print(f"Failed to restore auto-backup: {e}")

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with default to ensure all keys exist
                    config = DEFAULT_CONFIG.copy()
                    # Deep merge for nested dicts
                    for key in ["commands", "messages", "events", "points"]:
                        if key in loaded:
                            config[key].update(loaded[key])
                    # Merge top level keys (token, channel)
                    for key in loaded:
                        if key not in ["commands", "messages", "events", "points"]:
                            config[key] = loaded[key]
                    return config
            except Exception as e:
                print(f"Error loading config: {e}")
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()

    def load_config_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Config File", os.getcwd(), "JSON Files (*.json)")
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                new_config = json.load(f)
                
            # Update self.config
            self.config = DEFAULT_CONFIG.copy()
            # Deep merge logic
            for key in ["commands", "messages", "events", "points"]:
                if key in new_config:
                    self.config[key].update(new_config[key])
            for key in new_config:
                if key not in ["commands", "messages", "events", "points"]:
                    self.config[key] = new_config[key]
            
            # Refresh UI
            self.refresh_ui_from_config()
            
            self.log(f"✅ Configuration loaded from: {file_path}")
            self.toast.show_message("✅ Configuration Loaded!")
            
            QMessageBox.information(self, "Restart Required", 
                                    "Configuration loaded successfully!\n\n"
                                    "If you have changed Commands, Events, or other core settings, "
                                    "please restart the application for changes to take full effect.")
            
        except Exception as e:
            self.log(f"❌ Error loading config: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load config: {e}")

    def refresh_ui_from_config(self):
        # Tab 1: Collection
        self.token_input.setText(self.config.get('token', ''))
        self.channel_input.setText(self.config.get('channel', ''))
        self.show_banner_cb.setChecked(self.config.get('show_banner', True))
        self.show_leaderboard_cb.setChecked(self.config.get('show_leaderboard', False))
        
        # Tab 2: Setup (Dynamic Inputs)
        if hasattr(self, 'setup_inputs'):
            for category, inputs in self.setup_inputs.items():
                for key, input_field in inputs.items():
                    val = self.config.get(category, {}).get(key, "")
                    input_field.setText(str(val))
                    
        # Tab 2: Ranks
        # Clear existing ranks
        while self.ranks_layout.count():
            item = self.ranks_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.rank_inputs = []
        
        # Add new ranks
        current_ranks = self.config.get("ranks", DEFAULT_CONFIG["ranks"])
        current_ranks.sort(key=lambda x: x["score"])
        for r in current_ranks:
            self.add_rank_row(r["score"], r["title"])
            
        # Tab 2: Balance
        self.cooldown_spin.setValue(int(self.config.get('cooldown', 60)))
        self.shiny_chance_spin.setValue(int(self.config.get('shiny_chance', 10000)))
        self.legendary_chance_spin.setValue(int(self.config.get('legendary_chance', 1000)))

        # Tab 3: Settings
        self.theme_combo.setCurrentText(self.config.get('theme', 'Dark Mode'))
        self.font_combo.setCurrentFont(QFont(self.config.get('font_family', 'Segoe UI')))
        self.font_size_spin.setValue(self.config.get('font_size', 11))
        self.output_dir_input.setText(self.config.get('output_dir', os.getcwd()))
        self.autosave_spin.setValue(self.config.get('autosave_interval', 5))
        
        # Apply Theme/Font
        self.apply_theme(self.config.get('theme', 'Dark Mode'))
        self.apply_font()
    
    def update_event_labels(self):
        """Update event labels based on current config"""
        evts = self.config.get("events", DEFAULT_CONFIG["events"])
        
        # Update Collection Tab Labels
        self.rh_label.setText(f"🚀 {evts.get('rush_hour_name', 'Rush Hour')}")
        self.ld_label.setText(f"🎒 {evts.get('loot_drive_name', 'Loot Drive')}")
        self.bh_label.setText(f"🧐 {evts.get('bounty_hunter_name', 'Bounty Hunter')}")
        self.ct_label.setText(f"⚔️ {evts.get('contest_name', 'Contest')}")
        
        # Update Status Header Labels
        self.rh_status_header.setText(f"🚀 {evts.get('rush_hour_name', 'Rush Hour')}")
        self.ld_status_header.setText(f"🎒 {evts.get('loot_drive_name', 'Loot Drive')}")
        self.bh_status_header.setText(f"🧐 {evts.get('bounty_hunter_name', 'Bounty Hunter')}")
        self.ct_status_header.setText(f"⚔️ {evts.get('contest_name', 'Contest')}")

    def save_configuration(self):
        # Update current config with UI values
        self.config['token'] = self.token_input.text()
        self.config['channel'] = self.channel_input.text()
        self.config['show_banner'] = self.show_banner_cb.isChecked()
        
        # New Settings
        self.config['theme'] = self.theme_combo.currentText()
        self.config['font_family'] = self.font_combo.currentFont().family()
        self.config['font_size'] = self.font_size_spin.value()
        self.config['output_dir'] = self.output_dir_input.text()
        self.config['autosave_interval'] = self.autosave_spin.value()
        
        # Game Balance
        self.config['cooldown'] = self.cooldown_spin.value()
        self.config['shiny_chance'] = self.shiny_chance_spin.value()
        self.config['legendary_chance'] = self.legendary_chance_spin.value()
        # self.config['loot_min'] = self.loot_min_spin.value()
        # self.config['loot_max'] = self.loot_max_spin.value()

        # --- Save Setup Tab Inputs ---
        if hasattr(self, 'setup_inputs'):
            for category, inputs in self.setup_inputs.items():
                if category not in self.config:
                    self.config[category] = {}
                for key, input_field in inputs.items():
                    self.config[category][key] = input_field.text()

        # --- Save Ranks ---
        if hasattr(self, 'rank_inputs'):
            new_ranks = []
            for score_input, title_input in self.rank_inputs:
                try:
                    score = int(score_input.text())
                    title = title_input.text()
                    if title:
                        new_ranks.append({"score": score, "title": title})
                except ValueError:
                    continue
            self.config['ranks'] = new_ranks
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            self.log("✅ Configuration saved successfully")
            
            # Update running bot config
            if self.bot_thread and self.bot_thread.bot:
                self.bot_thread.bot.config = self.config
                self.log("🔄 Bot configuration updated live!")
            
            # Update UI Labels
            self.update_event_labels()

            # Only show message box if triggered manually (not by auto-save or spinbox change)
            if isinstance(self.sender(), QPushButton):
                # Use Toast instead of QMessageBox to avoid sound
                self.toast.show_message("✅ Configuration Saved!")
        except Exception as e:
            self.log(f"❌ Error saving config: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save config: {e}")
    
    def start_bot(self):
        token = self.token_input.text().strip()
        channel = self.channel_input.text().strip()
        
        if not token or not channel:
            QMessageBox.warning(self, "Missing Info", "Please enter Token and Channel Name!")
            return
        
        self.log("=" * 50)
        self.log("🍞 Starting ChatCollect Bot...")
        self.log("=" * 50)
        
        show_banner = self.show_banner_cb.isChecked()
        # Reload config to ensure latest messages/commands are used
        self.config = self.load_config()
        self.config['token'] = token
        self.config['channel'] = channel
        self.config['show_banner'] = show_banner
        
        self.bot_thread = BotThread(token, channel, self.config, show_banner)
        self.bot_thread.log_signal.connect(self.log)
        self.bot_thread.error_signal.connect(self.show_error)
        self.bot_thread.status_signal.connect(self.update_status_display)
        self.bot_thread.start()
        
        self.start_btn.setEnabled(False)

    def toggle_banner(self, state):
        if self.bot_thread:
            self.bot_thread.set_show_banner(self.show_banner_cb.isChecked())
        
    def stop_bot(self):
        if self.bot_thread:
            self.log("🛑 Stopping bot...")
            self.bot_thread.stop()
            self.bot_thread.wait()
            self.bot_thread = None
        
        self.log("✅ Bot stopped")
        self.start_btn.setEnabled(True)
        self.rh_status_label.setText("Inactive")
        self.bs_status_label.setText("Inactive")
        self.fc_status_label.setText("Inactive")
        self.bo_status_label.setText("Inactive")

    def update_status_display(self, status):
        # Rush Hour
        if status["rush_hour_active"]:
            self.rh_status_label.setText(f"ACTIVE\nTime: {status['rush_hour_remaining']}s")
            self.rh_status_label.setStyleSheet("color: #E91E63; font-weight: bold;")
        else:
            self.rh_status_label.setText("Inactive")
            self.rh_status_label.setStyleSheet("color: #888;")

        # Loot Drive
        if status["loot_drive_active"]:
            self.bs_status_label.setText(f"ACTIVE\nProgress: {status['loot_drive_progress']}\nTime: {status['loot_drive_remaining']}s")
            self.bs_status_label.setStyleSheet("color: #9C27B0; font-weight: bold;")
        else:
            self.bs_status_label.setText("Inactive")
            self.bs_status_label.setStyleSheet("color: #888;")

        # Bounty Hunter
        if status["bounty_hunter_active"]:
            self.fc_status_label.setText(f"ACTIVE\nCraving: {status['bounty_hunter_craving']}\nTime: {status['bounty_hunter_remaining']}s")
            self.fc_status_label.setStyleSheet("color: #607D8B; font-weight: bold;")
        else:
            self.fc_status_label.setText("Inactive")
            self.fc_status_label.setStyleSheet("color: #888;")

        # Contest
        if status.get("contest_state", "inactive") != "inactive":
            state = status["contest_state"].upper()
            pool = status.get("contest_pool", 0)
            timer = status.get("contest_timer", 0)
            self.bo_status_label.setText(f"{state}\nPool: {pool}\nTime: {timer}s")
            self.bo_status_label.setStyleSheet("color: #FF5722; font-weight: bold;")
        else:
            self.bo_status_label.setText("Inactive")
            self.bo_status_label.setStyleSheet("color: #888;")
        
    def test_custom_bake(self):
        rarity_text = self.rarity_combo.currentText().lower()
        item_filename = self.item_combo.currentData()
        
        if not item_filename:
            QMessageBox.warning(self, "No Item", "No baked goods found in overlay folder!")
            return

        is_legendary = False
        rarity = "standard"

        if rarity_text == "legendary":
            is_legendary = True
            rarity = "standard"
        else:
            rarity = rarity_text
        
        message = {
            "event": "loot",
            "user": "TEST_USER",
            "rank": "Test Rank",
            "score": 123,
            "item": item_filename,
            "is_legendary": is_legendary,
            "rarity": rarity,
            "trigger_explosion": True,
            "ranked_up": False,
            "show_banner": self.show_banner_cb.isChecked()
        }
        
        if rarity in ["shiny", "golden"] or is_legendary:
            message["trigger_explosion"] = True
        else:
             message["trigger_explosion"] = False

        asyncio.run(broadcast_to_overlays(message))
        self.log(f"🧪 Custom Test: {rarity_text.upper()} {format_item_name(item_filename)}")

    def test_explosion(self):
        """Send test explosion to overlay (doesn't count toward scores)"""
        legendary_chance = int(self.config.get("legendary_chance", 1000))
        loot_item, is_legendary = choose_loot_item(legendary_chance_1_in_x=legendary_chance)
        item_display_name = format_item_name(loot_item)
        
        message = {
            "event": "loot",
            "user": "TEST",
            "rank": "Test Mode",
            "score": 0,
            "item": loot_item,
            "is_legendary": is_legendary,
            "trigger_explosion": True,
            "ranked_up": False,
            "show_banner": self.show_banner_cb.isChecked()
        }
        
        asyncio.run(broadcast_to_overlays(message))
        self.log(f"💥 TEST EXPLOSION: {item_display_name}")
    
    def test_legendary(self):
        """Send test legendary bake to overlay (doesn't count toward scores)"""
        legendary_items = asset_manager.legendary_items
        
        if not legendary_items:
            self.log("⚠️ No legendary items found! Add Legendary-*.png files to overlay folder.")
            QMessageBox.warning(self, "No Legendaries", "No legendary items found!\n\nAdd PNG files starting with 'Legendary-' to the overlay folder.")
            return
        
        # Pick random legendary item
        loot_item = random.choice(legendary_items)
        item_display_name = format_item_name(loot_item)
        
        message = {
            "event": "loot",
            "user": "TEST",
            "rank": "Test Mode",
            "score": 0,
            "item": loot_item,
            "is_legendary": True,
            "trigger_explosion": True,
            "ranked_up": False,
            "show_banner": self.show_banner_cb.isChecked()
        }
        
        asyncio.run(broadcast_to_overlays(message))
        self.log(f"✨ TEST LEGENDARY: {item_display_name} ✨")
        
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_display.append(f"[{timestamp}] {message}")
        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        )
        
    def show_error(self, error):
        self.log(f"❌ ERROR: {error}")
        QMessageBox.critical(self, "Bot Error", f"An error occurred:\n{error}")
        self.stop_bot()
        
    def closeEvent(self, event):
        # Auto-stop bot when window closes
        if self.bot_thread and self.bot_thread.isRunning():
            self.log("🛑 Closing application - stopping bot...")
            self.stop_bot()
        event.accept()

    def trigger_rush_hour(self):
        if self.bot_thread and self.bot_thread.bot:
            try:
                duration = int(self.rh_duration.text())
            except ValueError:
                duration = 2
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.start_rush_hour(duration), self.bot_thread.loop)
            evts = self.config.get("events", DEFAULT_CONFIG["events"])
            self.log(f"🚀 Triggered {evts['rush_hour_name']} ({duration} mins)!")
        else:
            QMessageBox.warning(self, "Bot Not Running", "Please start the bot first!")

    def stop_rush_hour(self):
        if self.bot_thread and self.bot_thread.bot:
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.stop_rush_hour(), self.bot_thread.loop)
            evts = self.config.get("events", DEFAULT_CONFIG["events"])
            self.log(f"🛑 Stopped {evts['rush_hour_name']}!")

    def trigger_loot_drive(self):
        if self.bot_thread and self.bot_thread.bot:
            try:
                duration = int(self.bs_duration.text())
            except ValueError:
                duration = 20
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.start_loot_drive(duration), self.bot_thread.loop)
            evts = self.config.get("events", DEFAULT_CONFIG["events"])
            self.log(f"🍪 Triggered {evts['loot_drive_name']} ({duration} mins)!")
        else:
            QMessageBox.warning(self, "Bot Not Running", "Please start the bot first!")

    def stop_loot_drive(self):
        if self.bot_thread and self.bot_thread.bot:
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.stop_loot_drive(), self.bot_thread.loop)
            evts = self.config.get("events", DEFAULT_CONFIG["events"])
            self.log(f"🛑 Stopped {evts['loot_drive_name']}!")

    def trigger_bounty_hunter(self):
        if self.bot_thread and self.bot_thread.bot:
            try:
                duration = int(self.fc_duration.text())
            except ValueError:
                duration = 10
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.spawn_bounty_hunter(duration), self.bot_thread.loop)
            evts = self.config.get("events", DEFAULT_CONFIG["events"])
            self.log(f"🧐 Triggered {evts['bounty_hunter_name']} ({duration} mins)!")
        else:
            QMessageBox.warning(self, "Bot Not Running", "Please start the bot first!")

    def stop_bounty_hunter(self):
        if self.bot_thread and self.bot_thread.bot:
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.stop_bounty_hunter(), self.bot_thread.loop)
            evts = self.config.get("events", DEFAULT_CONFIG["events"])
            self.log(f"🛑 Stopped {evts['bounty_hunter_name']}!")

    def trigger_contest(self):
        if self.bot_thread and self.bot_thread.bot:
            try:
                duration = int(self.bo_duration.text())
            except ValueError:
                duration = 2
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.start_contest(duration), self.bot_thread.loop)
            evts = self.config.get("events", DEFAULT_CONFIG["events"])
            self.log(f"⚔️ Triggered {evts['contest_name']} ({duration} mins)!")
        else:
            QMessageBox.warning(self, "Bot Not Running", "Please start the bot first!")

    def stop_contest(self):
        if self.bot_thread and self.bot_thread.bot:
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.stop_contest(), self.bot_thread.loop)
            evts = self.config.get("events", DEFAULT_CONFIG["events"])
            self.log(f"🛑 Stopped {evts['contest_name']}!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatCollectGUI()
    window.show()
    sys.exit(app.exec_())
