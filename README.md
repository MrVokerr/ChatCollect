# ChatCollect - Streamer Edition 🎒

## 🎮 What is ChatCollect?
An interactive Twitch stream game where viewers "loot" virtual items, climb ranks, and trigger animations on your stream overlay! 

**Optimized for Streamers:** Designed to run lightly in the background without affecting your gaming performance. Fully customizable via the included GUI.

---

## 📥 Installation & Updates

### First Time Setup
1. **Download ONLY:** `ChatCollect.exe` from the [latest release](https://github.com/MrVokerr/ChatCollect/releases/latest)
2. Place it in a folder (e.g., `C:\ChatCollect\`)
3. Run `ChatCollect.exe` - it will auto-create:
   - `chatcollect_config.json` (your settings)
   - `chatcollect_data.txt` (player scores)
   - `overlay/` folder with `overlay.html`
   - `overlay/legendary/` folder for legendary items
   - `backups/` folder for automatic backups

### 🔄 Updating to New Versions
**Easy Method (Recommended):**
1. Open ChatCollect
2. Go to **Settings** tab
3. Click **"🔄 Check for Updates"**
4. Click **Yes** to auto-update (your config/data/images are preserved!)

**Manual Method:**
- Just download the new `ChatCollect.exe` and replace the old one
- Your `chatcollect_config.json`, `chatcollect_data.txt`, and `overlay/` images are never touched!

### ✅ What You Keep Between Updates
- ✅ All your settings (`chatcollect_config.json`)
- ✅ Player scores/data (`chatcollect_data.txt`)
- ✅ Custom item images in `overlay/` folder
- ✅ Legendary items in `overlay/legendary/`
- ✅ All backups

### ❌ What Gets Updated
- ❌ Only `ChatCollect.exe` (the program itself)
- ❌ Only `overlay.html` (the browser source file)

> **💡 Pro Tip:** You only need ONE file to get started: `ChatCollect.exe`. Everything else is created automatically!

---

## 🚀 Quick Start

### 1. Configuration (First Time Setup)
1. Run **`ChatCollect.exe`**.
2. Go to the **Setup** tab. You will see several sub-tabs:
   - **💬 Commands**: Customize your chat commands (Default: `!loot`, `!leaderboard`, etc.).
   - **📢 Messages**: Customize the bot's responses. Use the **"❓ Syntax Help"** button to see available placeholders.
   - **🎉 Events**: Rename events to fit your theme (e.g., rename "Loot Drive" to "Raid").
   - **🏆 Ranks**: Create your own custom ranks and score thresholds.
   - **⚖️ Balance**: Adjust cooldowns and drop rates (Shiny/Legendary chances).
3. Click **"💾 Save Configuration"**.

### 📂 Loading & Switching Profiles
You can switch between different game modes (e.g., "Loot Mode" vs "Bake Mode") by loading different configuration files.
1. Go to the **Setup** tab.
2. Click **"📂 Load Config File"**.
3. Select a `.json` file (e.g., `chatcollect_config_bakerank.json`).
4. The application will instantly update all commands, messages, ranks, and settings to match the loaded file.
   *   *Note:* This does not delete your player data! The database (`chatcollect_data.txt`) is universal and compatible with any config. "Loot Points" simply become "Bake Points".

> **📝 Note on Saving:** 
> *   **Live Updates:** Most settings (Messages, Ranks, Balance, Theme) update immediately when you click Save.
> *   **Restart Required:** If you change **Command Names** (e.g., `!loot` -> `!dig`) or **Twitch Credentials**, you must **Stop** and **Start** the bot again for changes to take effect. You do *not* need to close the application.

### 2. Launching the Bot
1. Go to the **Collection** tab.
2. Enter your credentials:
   - **OAuth Token**: Get from [TwitchTokenGenerator](https://twitchtokengenerator.com/) (Select 'Custom Scope' -> enable `chat:read` and `chat:edit`).
   - **Channel Name**: Your Twitch username.
3. Click **"▶ Start Bot"**.

### 3. Overlay Setup (OBS/Streamlabs)
1. Add a **Browser Source**.
2. Check **"Local File"** and browse to select `overlay/overlay.html` inside the ChatCollect folder.
3. Set Width/Height to your canvas size (e.g., 1920x1080).
4. Check "Shutdown source when not visible" and "Refresh browser when scene becomes active".

---

## 🎛️ GUI Controls (ChatCollect.exe)

The main interface gives you full control over the game while live:

### **Testing Tools**
Located in the **Collection** tab, these tools let you verify your overlay is working without spamming chat:
*   **Test Explosion/Legendary**: Triggers the animation on the overlay immediately.
*   **Custom Test**: Select a specific item and rarity (e.g., "Golden Donut") from the dropdowns to preview exactly how it looks.

### **Events Control Panel**
Trigger special events to boost engagement. You can set custom durations (in minutes) for each event!

*   **🚀 Rush Hour**: Reduces loot cooldowns to **10 seconds** (normally 60s).
    *   *Action:* Click **Start** to begin, **Stop** to end early.
*   **🎒 Loot Drive**: Community challenge to collect **150 items** total.
    *   *Reward:* All participants get a **Prestige Star ⭐** if the goal is met.
    *   *Progress:* The current progress (e.g., `45/150`) is automatically attached to every `!loot` message while active.
*   **🧐 Bounty Hunter**: An NPC arrives craving a specific item (e.g., "Donut").
    *   *Action:* First person to loot that specific item gets a **+50 Point Bonus**.
*   **⚔️ Contest**: A PvP tournament!
    *   *Action:* Viewers type `!contest` to join (Cost: 10 pts). Winner takes the entire pot!
    *   *Note:* A reminder is sent to chat halfway through the joining period.

### **Overlay Settings**
*   **Show Banner**: Toggles the notification banner on the overlay.
*   **Show Leaderboard**: Toggles a live Top 10 Leaderboard on the overlay.

### **Game Balance (Setup Tab)**
Adjust the core mechanics of the game in the **Setup > Balance** tab:
*   **Cooldown**: Set how often users can loot (Default: 60s).
*   **Shiny Chance**: Set the rarity of Shiny items (Default: 1 in 10,000).
*   **Legendary Chance**: Set the rarity of Legendary items (Default: 1 in 1,000).
*   **Steal Chance**: Set the chance for a viewer to steal loot from another player (Default: 1%).

### **Appearance & Settings**
Customize the look of the application in the **Settings** tab:
*   **Theme**: Choose between **Dark Mode**, **Light Mode**, or **System Default**.
*   **Font**: Adjust the font family and size for the GUI.

### **Backup & Restore**
Never lose your settings!
*   **Auto-Backups**: The system automatically creates backups (`config_auto_...`) when updating.
*   **Backup Config**: Manually save a timestamped copy of your settings to the `backups/` folder.
*   **Restore Config**: Load a previous configuration file.

---

## 🎨 Customizing Loot Items

1. Open the `overlay` folder.
2. **Normal Items**: Add any `.png` image (e.g., `sword.png`, `potion.png`) directly in the `overlay` folder.
3. **Legendary Items**: 
    *   Place images in the `overlay/legendary/` subfolder.
    *   *Chance:* Viewers have a configurable chance to loot these (triggers a massive explosion).

### 💎 Shiny & Golden Logic
*   **Shiny** (Base Chance + Luck): Color-shifting glow + badge + explosion.
*   **Golden** (5% + Luck): Golden glow + 3x points.
*   **Ruined** (5%): Item is destroyed + 0 points.

### 😈 Steal Mechanic
*   **The Heist**: There is a small chance (configurable) that when a player loots an item, a random *other* player will swoop in and steal it!
*   **The Result**: 
    *   **Thief**: Gets the points for the item.
    *   **Victim**: Gets nothing... and still has to wait for their cooldown!
*   **Config**: Adjust the **Steal Chance** (0-100%) in the **Balance** tab and customize the message in the **Messages** tab.

---

## 🎮 Twitch Commands for Viewers

*Default commands (can be changed in Setup tab):*

- **!loot** - Try to find an item! Cooldown: 60s (10s during Rush Hour).
- **!use [amount]** - Consume points to gain **Luck**.
    *   *1 Point = 5% Luck*.
    *   Higher luck increases chances for **Shiny** and **Golden** items on the *next* loot.
- **!leaderboard** - Displays the top 5 collectors in chat.
- **!contest** - Join an active Contest tournament (Cost: 10 pts).

---

## 📊 Default Ranks

| Points | Rank |
|--------|------|
| 0 | Novice Collector |
| 50 | Rookie Scavenger |
| 250 | Apprentice Hunter |
| 750 | Loot Specialist |
| 2000 | Treasure Expert |
| 5000 | Hoard Master |
| 10000 | Legendary Collector |
| 25000 | Artifact Hunter |
| 50000 | Celestial Hoarder |
| 100000 | God of Loot |

*(You can edit these in the Setup tab)*

---

## 🛠️ For Developers / Building from Source

If you want to modify the code and rebuild the EXE:

1. **Install Python 3.10+**.
2. **Install Dependencies**:
   ```bat
   cd build
   install_requirements.bat
   ```
3. **Build EXE**:
   ```bat
   cd build
   build_exe.bat
   ```
   *   This will compile `ChatCollect.exe`.
   *   It automatically cleans up build artifacts and moves the EXE to the root folder.

---

## 📂 File Structure
*   `ChatCollect.exe` - The main application (Bot + Setup + Overlay Server).
*   `chatcollect_config.json` - Stores your settings.
*   `chatcollect_data.txt` - Player database (Do not edit while bot is running).
*   `overlay/` - Folder for your images and the HTML overlay.
*   `backups/` - Folder where configuration backups are stored.

---

## 🐛 Troubleshooting

### "Bot is already running"
Close all Python windows or run in PowerShell:
```powershell
taskkill /F /IM ChatCollect.exe
```

### .exe closes immediately
Make sure the `overlay` folder is in the same directory as the .exe.

### Overlay not connecting
Ensure `ChatCollect.exe` is running. The overlay connects via WebSocket to port `8765`.

---

## 📝 License

Free to use and modify for personal and commercial streaming!
