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
- GitHub Actions workflow: `.github/workflows/release.yml`

## User Data Protection
Never suggest editing these files (they're in .gitignore):
- `chatcollect_config.json`
- `chatcollect_data.txt`
- `backups/`
- `overlay/*.png` (except defaults)

## Update Workflow (Automated)
When user wants to release:
1. Auto-sync version in code with `version.txt`
2. Build exe locally with `build_exe.bat` for testing
3. Commit and push changes
4. Create and push git tag: `git tag v1.x.x && git push origin v1.x.x`
5. GitHub Actions automatically builds exe and creates release
6. Users get auto-update via in-app button

## Manual Release (Fallback)
If automation fails:
1. Build locally with `build_exe.bat`
2. Go to GitHub → Releases → New Release
3. Tag must match version (e.g., `v1.2.7`)
4. Upload only `ChatCollect.exe`
