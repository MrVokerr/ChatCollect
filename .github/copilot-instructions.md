# ChatCollect Project Instructions for GitHub Copilot

## Version Management
When the user updates `version.txt`, ALWAYS automatically update `CURRENT_VERSION` in `build/chatcollect_gui.py` to match.

Example:
- If `version.txt` says `v1.3.0`
- Update line ~25 in `build/chatcollect_gui.py` to: `CURRENT_VERSION = "v1.3.0"`

## Code Style
- Use semantic versioning format: `v1.2.3`
- All versions must include the `v` prefix
- Keep `version.txt` and code version synchronized

## File Locations
- Version in code: `build/chatcollect_gui.py` line ~25
- Version file: `version.txt` (root)
- Main source: `build/chatcollect_gui.py`

## User Data Protection
Never suggest editing these files (they're in .gitignore):
- `chatcollect_config.json`
- `chatcollect_data.txt`
- `backups/`
- `overlay/*.png` (except defaults)

## Update Workflow
When user wants to release:
1. Auto-sync version in code with `version.txt`
2. Remind them to build exe
3. Remind them to create GitHub release with matching tag
4. Upload only `ChatCollect.exe` to release
