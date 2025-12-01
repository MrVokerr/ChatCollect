import asyncio
import time
import json
import random
import os
import glob
import sys
import ctypes
from ctypes import windll, byref, c_int
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QGroupBox, QMessageBox, QComboBox, QGridLayout, QCheckBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QIntValidator, QIcon
import websockets
from twitchio.ext import commands

CONFIG_FILE = "chatcollect_config.json"
DB_PATH = "chatcollect_data.txt"
OVERLAY_FOLDER = "overlay"
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
        self.load()

    def load(self):
        if not os.path.exists(self.filepath):
            return
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('|')
                    if len(parts) >= 3:
                        username = parts[0].strip()
                        try:
                            self.players[username] = {
                                'loot_score': int(parts[1].strip()),
                                'last_loot_time': float(parts[2].strip()),
                                'luck': float(parts[3].strip()) if len(parts) >= 4 else 0.0,
                                'last_use_time': float(parts[4].strip()) if len(parts) >= 5 else 0.0,
                                'prestige_stars': int(parts[5].strip()) if len(parts) >= 6 else 0,
                                'shinies': int(parts[6].strip()) if len(parts) >= 7 else 0
                            }
                        except ValueError:
                            continue
        except Exception as e:
            print(f"⚠️ Warning: Could not load database: {e}")

    def save_blocking(self):
        """Blocking save for use in executor"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write("# ChatCollect Player Database - Edit with Notepad\n")
                f.write("# Format: username | loot_score | last_loot_time | luck | last_use_time | prestige_stars | shinies\n")
                f.write("# WARNING: Keep the | separators intact!\n\n")
                
                sorted_players = sorted(self.players.items(), key=lambda x: x[1]['loot_score'], reverse=True)
                for username, data in sorted_players:
                    f.write(f"{username} | {data['loot_score']} | {data['last_loot_time']} | "
                            f"{data.get('luck', 0.0)} | {data.get('last_use_time', 0.0)} | "
                            f"{data.get('prestige_stars', 0)} | {data.get('shinies', 0)}\n")
                
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
def choose_loot_item(rarity="standard"):
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

    # Standard/Golden/Ruined: 0.1% chance of Legendary, else Normal
    if legendary and random.random() < 0.001:
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
        cooldown_time = COOLDOWN
        
        # Check Rush Hour
        if self.rush_hour_active:
            cooldown_time = 10 # Reduced cooldown
        
        if now - last_bake_time < cooldown_time:
            remaining = int(cooldown_time - (now - last_bake_time))
            msg = msgs.get("cooldown", DEFAULT_CONFIG["messages"]["cooldown"])
            await ctx.send(msg.format(username=username, remaining=remaining))
            return

        old_rank_title = self.get_rank_title(bake_score)
        
        # Rarity Logic
        shiny_prob = 0.0001 + (luck / 1000.0)
        golden_prob = 0.05 + (luck / 200.0)
        ruined_prob = 0.05
        
        rand_val = random.random()
        
        rarity = "standard"
        points_gained = 1
        
        if rand_val < shiny_prob:
            rarity = "shiny"
            points_gained = 10
            player_data[username]['shinies'] += 1
        elif rand_val < (shiny_prob + ruined_prob):
            rarity = "ruined"
            points_gained = 0
        elif rand_val < (shiny_prob + ruined_prob + golden_prob):
            rarity = "golden"
            points_gained = 3
        else:
            rarity = "standard"
            points_gained = 1
            
        # Reset luck
        player_data[username]['luck'] = 0.0
        
        # Choose item
        loot_item, is_legendary_item = choose_loot_item(rarity)
        item_display_name = format_item_name(loot_item)
        
        # Legendary Bonus (Override points if legendary, unless already higher)
        if is_legendary_item:
            if points_gained < 5:
                points_gained = 5

        # Bounty Hunter Check
        critic_bonus = 0
        critic_msg = ""
        if self.bounty_hunter_active and self.bounty_hunter_craving == loot_item:
            critic_bonus = 50
            points_gained += critic_bonus
            self.bounty_hunter_active = False
            self.bounty_hunter_craving = None
            
            bh_msg = msgs.get("bounty_hunter_satisfied", DEFAULT_CONFIG["messages"]["bounty_hunter_satisfied"])
            critic_msg = f" {bh_msg.format(username=username, points=50)}"
            
            self.log_callback(f"🧐 {username} satisfied the {evts['bounty_hunter_name']}!")
            self._send_status_update()

        bake_score += points_gained
        new_rank_title = self.get_rank_title(bake_score)

        player_data[username]['loot_score'] = bake_score
        player_data[username]['last_loot_time'] = now
        await db.save()

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
            elif self.loot_drive_current % 10 == 0: # Notify every 10 items
                 loot_drive_msg = f" ({evts['loot_drive_name']}: {self.loot_drive_current}/{self.loot_drive_target})"
            self._send_status_update()

        # Construct Message
        msg = ""
        if rarity == "ruined":
            msg = f"🔥 @{username} tried to loot a {item_display_name} but fell asleep! It's RUINED! (0 pts)"
            self.log_callback(f"🔥 {username} ruined a {item_display_name}")
        elif rarity == "shiny":
            msg = f"💎✨ SHINY!! @{username} looted a SHINY {item_display_name}! Unlocked a Badge! (+{points_gained} pts){critic_msg}{loot_drive_msg}"
            self.log_callback(f"💎 {username} got a SHINY {item_display_name}")
        elif rarity == "golden":
            msg = f"🌟 MASTERPIECE! @{username} looted a GOLDEN {item_display_name}! (+{points_gained} pts){critic_msg}{loot_drive_msg}"
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
            
            self.loop.run_until_complete(asyncio.gather(overlay_task, bot_task))
        except Exception as e:
            self.error_signal.emit(str(e))
            
    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

# ============ MAIN GUI WINDOW ============
class ChatCollectGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bot_thread = None
        self.config = self.load_config()
        self.init_ui()

    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)
        
    def init_ui(self):
        self.setWindowTitle("ChatCollect")
        
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
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-size: 11pt;
            }
            QGroupBox {
                background-color: #252525;
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #e0e0e0;
                background-color: transparent;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px;
                color: #e0e0e0;
                selection-background-color: #4a4a4a;
            }
            QLineEdit:focus {
                border: 1px solid #0d7377;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 8px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #1d1d1d;
            }
            QTextEdit {
                background-color: #0d0d0d;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                color: #e0e0e0;
                selection-background-color: #4a4a4a;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
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
        self.save_config_btn.clicked.connect(self.save_configuration)
        config_layout.addWidget(self.save_config_btn)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Control Buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Start Bot")
        self.start_btn.clicked.connect(self.start_bot)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; border: none;")
        btn_layout.addWidget(self.start_btn)
        
        self.test_explosion_btn = QPushButton("💥 Test Explosion")
        self.test_explosion_btn.clicked.connect(self.test_explosion)
        self.test_explosion_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 10px; border: none;")
        btn_layout.addWidget(self.test_explosion_btn)
        
        self.test_legendary_btn = QPushButton("✨ Test Legendary")
        self.test_legendary_btn.clicked.connect(self.test_legendary)
        self.test_legendary_btn.setStyleSheet("background-color: #FFD700; color: black; font-weight: bold; padding: 10px; border: none;")
        btn_layout.addWidget(self.test_legendary_btn)
        
        layout.addLayout(btn_layout)

        # Test Controls Group
        test_group = QGroupBox("Test")
        test_layout = QHBoxLayout()

        # Rarity Dropdown
        test_layout.addWidget(QLabel("Rarity:"))
        self.rarity_combo = QComboBox()
        self.rarity_combo.addItems(["Standard", "Ruined", "Shiny", "Golden", "Legendary"])
        test_layout.addWidget(self.rarity_combo)

        # Item Dropdown
        test_layout.addWidget(QLabel("Item:"))
        self.item_combo = QComboBox()
        # Populate items
        all_items = asset_manager.normal_items + asset_manager.legendary_items
        for filename in all_items:
            display_name = format_item_name(filename)
            self.item_combo.addItem(display_name, filename) # Store filename as user data
        test_layout.addWidget(self.item_combo)

        # Test Button
        self.custom_test_btn = QPushButton("🧪 Test")
        self.custom_test_btn.clicked.connect(self.test_custom_bake)
        self.custom_test_btn.setStyleSheet("background-color: #00BCD4; color: white; font-weight: bold; padding: 8px;")
        test_layout.addWidget(self.custom_test_btn)

        test_group.setLayout(test_layout)
        layout.addWidget(test_group)

        # Overlay Settings (Between Test and Events)
        overlay_group = QGroupBox("Overlay Settings")
        overlay_layout = QHBoxLayout()
        self.show_banner_cb = QCheckBox("Show Banner in Overlay")
        self.show_banner_cb.setChecked(self.config.get('show_banner', True))
        self.show_banner_cb.stateChanged.connect(self.toggle_banner)
        overlay_layout.addWidget(self.show_banner_cb)
        overlay_group.setLayout(overlay_layout)
        layout.addWidget(overlay_group)

        # Events Group
        events_group = QGroupBox("Events")
        events_layout = QGridLayout()
        
        # Validators
        int_validator = QIntValidator(1, 9999)

        # Rush Hour
        events_layout.addWidget(QLabel("🚀 Rush Hour"), 0, 0)
        self.rh_duration = QLineEdit("2")
        self.rh_duration.setValidator(int_validator)
        self.rh_duration.setFixedWidth(50)
        self.rh_duration.setPlaceholderText("Min")
        events_layout.addWidget(self.rh_duration, 0, 1)
        events_layout.addWidget(QLabel("minutes"), 0, 2)
        
        self.rush_hour_btn = QPushButton("Start")
        self.rush_hour_btn.clicked.connect(self.trigger_rush_hour)
        self.rush_hour_btn.setStyleSheet("background-color: #E91E63; color: white; font-weight: bold;")
        events_layout.addWidget(self.rush_hour_btn, 0, 3)

        self.stop_rh_btn = QPushButton("Stop")
        self.stop_rh_btn.clicked.connect(self.stop_rush_hour)
        self.stop_rh_btn.setStyleSheet("background-color: #555; color: white;")
        events_layout.addWidget(self.stop_rh_btn, 0, 4)
        
        # Loot Drive
        events_layout.addWidget(QLabel("🎒 Loot Drive"), 1, 0)
        self.bs_duration = QLineEdit("20")
        self.bs_duration.setValidator(int_validator)
        self.bs_duration.setFixedWidth(50)
        self.bs_duration.setPlaceholderText("Min")
        events_layout.addWidget(self.bs_duration, 1, 1)
        events_layout.addWidget(QLabel("minutes"), 1, 2)

        self.loot_drive_btn = QPushButton("Start")
        self.loot_drive_btn.clicked.connect(self.trigger_loot_drive)
        self.loot_drive_btn.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold;")
        events_layout.addWidget(self.loot_drive_btn, 1, 3)

        self.stop_bs_btn = QPushButton("Stop")
        self.stop_bs_btn.clicked.connect(self.stop_loot_drive)
        self.stop_bs_btn.setStyleSheet("background-color: #555; color: white;")
        events_layout.addWidget(self.stop_bs_btn, 1, 4)
        
        # Bounty Hunter
        events_layout.addWidget(QLabel("🧐 Bounty Hunter"), 2, 0)
        self.fc_duration = QLineEdit("10")
        self.fc_duration.setValidator(int_validator)
        self.fc_duration.setFixedWidth(50)
        self.fc_duration.setPlaceholderText("Min")
        events_layout.addWidget(self.fc_duration, 2, 1)
        events_layout.addWidget(QLabel("minutes"), 2, 2)

        self.bounty_hunter_btn = QPushButton("Start")
        self.bounty_hunter_btn.clicked.connect(self.trigger_bounty_hunter)
        self.bounty_hunter_btn.setStyleSheet("background-color: #607D8B; color: white; font-weight: bold;")
        events_layout.addWidget(self.bounty_hunter_btn, 2, 3)

        self.stop_fc_btn = QPushButton("Stop")
        self.stop_fc_btn.clicked.connect(self.stop_bounty_hunter)
        self.stop_fc_btn.setStyleSheet("background-color: #555; color: white;")
        events_layout.addWidget(self.stop_fc_btn, 2, 4)
        
        # Contest
        events_layout.addWidget(QLabel("⚔️ Contest"), 3, 0)
        self.bo_duration = QLineEdit("2")
        self.bo_duration.setValidator(int_validator)
        self.bo_duration.setFixedWidth(50)
        self.bo_duration.setPlaceholderText("Min")
        events_layout.addWidget(self.bo_duration, 3, 1)
        events_layout.addWidget(QLabel("minutes"), 3, 2)

        self.contest_btn = QPushButton("Start")
        self.contest_btn.clicked.connect(self.trigger_contest)
        self.contest_btn.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold;")
        events_layout.addWidget(self.contest_btn, 3, 3)

        self.stop_bo_btn = QPushButton("Stop")
        self.stop_bo_btn.clicked.connect(self.stop_contest)
        self.stop_bo_btn.setStyleSheet("background-color: #555; color: white;")
        events_layout.addWidget(self.stop_bo_btn, 3, 4)
        
        events_group.setLayout(events_layout)
        layout.addWidget(events_group)

        # Active Events Status Group
        status_group = QGroupBox("Active Events Status")
        status_layout = QHBoxLayout()

        # Rush Hour Status
        rh_layout = QVBoxLayout()
        rh_layout.addWidget(QLabel("🚀 Rush Hour"))
        self.rh_status_label = QLabel("Inactive")
        self.rh_status_label.setStyleSheet("color: #888;")
        rh_layout.addWidget(self.rh_status_label)
        status_layout.addLayout(rh_layout)

        # Loot Drive Status
        bs_layout = QVBoxLayout()
        bs_layout.addWidget(QLabel("🎒 Loot Drive"))
        self.bs_status_label = QLabel("Inactive")
        self.bs_status_label.setStyleSheet("color: #888;")
        bs_layout.addWidget(self.bs_status_label)
        status_layout.addLayout(bs_layout)

        # Bounty Hunter Status
        fc_layout = QVBoxLayout()
        fc_layout.addWidget(QLabel("🧐 Bounty Hunter"))
        self.fc_status_label = QLabel("Inactive")
        self.fc_status_label.setStyleSheet("color: #888;")
        fc_layout.addWidget(self.fc_status_label)
        status_layout.addLayout(fc_layout)

        # Contest Status
        bo_layout = QVBoxLayout()
        bo_layout.addWidget(QLabel("⚔️ Contest"))
        self.bo_status_label = QLabel("Inactive")
        self.bo_status_label.setStyleSheet("color: #888;")
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
        
        self.log("🍞 ChatCollect Bot GUI Ready")
        self.log("Configure your settings and click 'Start Bot'")
        
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with default to ensure all keys exist
                    config = DEFAULT_CONFIG.copy()
                    # Deep merge for nested dicts
                    for key in ["commands", "messages", "events"]:
                        if key in loaded:
                            config[key].update(loaded[key])
                    # Merge top level keys (token, channel)
                    for key in loaded:
                        if key not in ["commands", "messages", "events"]:
                            config[key] = loaded[key]
                    return config
            except Exception as e:
                print(f"Error loading config: {e}")
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()
    
    def save_configuration(self):
        # Update current config with UI values
        self.config['token'] = self.token_input.text()
        self.config['channel'] = self.channel_input.text()
        self.config['show_banner'] = self.show_banner_cb.isChecked()
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            self.log("✅ Configuration saved successfully")
            QMessageBox.information(self, "Success", "Configuration saved!")
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
        loot_item, is_legendary = choose_loot_item()
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
