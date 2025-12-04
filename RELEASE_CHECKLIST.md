# Release Checklist for ChatCollect

## Before Each Release:

### 1. Update Version Number
- [ ] Update `CURRENT_VERSION` in `build/chatcollect_gui.py` (line ~25)
- [ ] Update `version.txt` in root folder
- [ ] Both should match (e.g., `v1.1.0`)

### 2. Build the Executable
```bash
cd build
python -m PyInstaller --onefile --windowed --icon=exe_icon.ico --name=ChatCollect chatcollect_gui.py
```
- [ ] Test the exe in `build/dist/ChatCollect.exe`
- [ ] Move it to root if desired

### 3. Create GitHub Release
- [ ] Go to: https://github.com/MrVokerr/ChatCollect/releases/new
- [ ] Tag: Must match version (e.g., `v1.1.0`)
- [ ] Title: `ChatCollect v1.1.0`
- [ ] Description: Add changelog/features
- [ ] Upload: **Only `ChatCollect.exe`**
- [ ] Mark as "Latest Release"

### 4. Verify Auto-Update Works
- [ ] `version.txt` is committed and pushed
- [ ] GitHub release has the exe attached
- [ ] Tag matches the version in code

---

## What Users Need to Download:

### First Time Users:
✅ **ONLY:** `ChatCollect.exe` from the latest release

### Existing Users (Updating):
✅ **Option 1 (Recommended):** Use in-app "Check for Updates" button
✅ **Option 2:** Download new `ChatCollect.exe` and replace old one

### What NOT to Include in Release:
❌ `chatcollect_config.json` (user-specific)
❌ `chatcollect_data.txt` (user data)
❌ `overlay/` images (user customizations)
❌ Python source files (unless they want to build from source)

---

## File Structure for Users:

```
ChatCollect/
├── ChatCollect.exe                    ← Only file they download!
├── chatcollect_config.json            ← Auto-created on first run
├── chatcollect_data.txt               ← Auto-created on first use
├── overlay/
│   ├── overlay.html                   ← Auto-created
│   ├── default_item.png               ← Auto-created if empty
│   ├── [user's custom images]         ← User adds these
│   └── legendary/
│       ├── default_legendary.png      ← Auto-created if empty
│       └── [user's legendaries]       ← User adds these
└── backups/                           ← Auto-created
    └── [automatic backups]
```

---

## Testing Update Process:

1. **Test old version → new version:**
   - [ ] Run old exe, create config & data
   - [ ] Click "Check for Updates"
   - [ ] Verify config/data preserved
   - [ ] Verify new features work

2. **Test manual update:**
   - [ ] Replace exe manually
   - [ ] Verify config/data still work
   - [ ] Verify no errors

---

## Common Issues:

### "Update button does nothing"
- Check `version.txt` is pushed to GitHub
- Check GitHub release has correct tag

### "Auto-update downloads but won't restart"
- Antivirus may block `.bat` file
- User should manually run new exe

### "Lost my settings after update"
- Should never happen (update only touches exe)
- Restore from `backups/` folder

---

## Release Notes Template:

```markdown
# ChatCollect v1.1.0

## 🆕 New Features
- Added X feature
- Added Y option to GUI

## 🐛 Bug Fixes
- Fixed Z issue
- Improved performance

## 📝 Notes
- All settings and data preserved during update
- Use in-app update button or download ChatCollect.exe

## 📥 Installation
First time? Just download `ChatCollect.exe` and run it!
Updating? Click "Check for Updates" in Settings tab.

Full guide: [README.md](https://github.com/MrVokerr/ChatCollect/blob/main/README.md)
```
