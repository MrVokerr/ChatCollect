# ChatCollect - Streamer Edition 🎒

## 🎮 What is ChatCollect?
An interactive Twitch stream game where viewers "loot" virtual items, climb ranks, and trigger animations on your stream overlay! 

**Optimized for Streamers:** Designed to run lightly in the background without affecting your gaming performance. Fully customizable via the included Setup tool.

---

## 🚀 Quick Start

### 1. Configuration (First Time Setup)
1. Run **`Setup.exe`**.
2. **Commands Tab**: Customize your chat commands (Default: `!loot`, `!leaderboard`, etc.).
3. **Messages Tab**: Customize the bot's responses to chat.
4. **Events Tab**: Rename events to fit your theme (e.g., rename "Loot Drive" to "Raid").
5. **Ranks Tab**: Create your own custom ranks and score thresholds.
6. Click **"💾 Save Settings"**.

### 2. Launching the Bot
1. Run **`ChatCollect.exe`**.
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

### **Events Control Panel**
Trigger special events to boost engagement. You can set custom durations (in minutes) for each event!

*   **🚀 Rush Hour**: Reduces loot cooldowns to **10 seconds** (normally 60s).
    *   *Action:* Click **Start** to begin, **Stop** to end early.
*   **🎒 Loot Drive**: Community challenge to collect **150 items** total.
    *   *Reward:* All participants get a **Prestige Star ⭐** if the goal is met.
    *   *Icon:* Displays a Backpack 🎒 progress tracker.
*   **🧐 Bounty Hunter**: An NPC arrives craving a specific item (e.g., "Donut").
    *   *Action:* First person to loot that specific item gets a **+50 Point Bonus**.
*   **⚔️ Contest**: A PvP tournament!
    *   *Action:* Viewers type `!contest` to join (Cost: 10 pts). Winner takes the entire pot!
    *   *Note:* A reminder is sent to chat halfway through the joining period.

### **Test Lab**
Test your overlay alerts without affecting player scores.
*   **Rarity**: Choose from Standard, Ruined, Shiny, Golden, or Legendary.
*   **Item**: Select any image from your overlay folder.
*   **Test Button**: Triggers the alert on stream immediately.

---

## 🎨 Customizing Loot Items

1. Open the `overlay` folder.
2. **Normal Items**: Add any `.png` image (e.g., `sword.png`, `potion.png`) directly in the `overlay` folder.
3. **Legendary Items**: 
    *   Place images in the `overlay/legendary/` subfolder.
    *   *Chance:* Viewers have a base 0.1% chance to loot these (triggers a massive explosion).

### 💎 Shiny & Golden Logic
*   **Shiny** (0.1% + Luck): Color-shifting glow + badge + explosion.
*   **Golden** (5% + Luck): Golden glow + 3x points.
*   **Ruined** (5%): Item is destroyed + 0 points.

---

## 🎮 Twitch Commands for Viewers

*Default commands (can be changed in Setup.exe):*

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

*(You can edit these in Setup.exe)*

---

## 🛠️ For Developers / Building from Source

If you want to modify the code and rebuild the EXEs:

1. **Install Python 3.14+**.
2. **Install Dependencies**:
   ```bat
   install_requirements.bat
   ```
3. **Build EXEs**:
   ```bat
   build_exe.bat
   ```
   *   This will compile `ChatCollect.exe` and `Setup.exe`.
   *   It automatically cleans up build artifacts and moves the EXEs to the root folder.

---

## 📂 File Structure
*   `ChatCollect.exe` - The main bot application.
*   `Setup.exe` - The configuration tool.
*   `chatcollect_config.json` - Stores your settings (created by Setup.exe).
*   `chatcollect_data.txt` - Player database (Do not edit while bot is running).
*   `overlay/` - Folder for your images and the HTML overlay.

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
