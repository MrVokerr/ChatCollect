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
- GitHub Actions workflow: `.github/workflows/release.yml` (manual-only fallback; uses Actions minutes, run only with the owner's OK)
- Local checks: `bash scripts/test-local.sh` (also the pre-push hook in `.githooks/`)

## User Data Protection
Never suggest editing these files (they're in .gitignore):
- `chatcollect_config.json`
- `chatcollect_data.txt`
- `backups/`
- `overlay/*.png` (except defaults)

## Update Workflow (local-first, no automatic GitHub Actions)
When user wants to release:
1. Sync version in code with `version.txt`; `bash scripts/test-local.sh` must pass
2. Build exe locally with `build_exe.bat` and test it
3. Commit, then push once
4. Create and push git tag: `git tag v1.x.x && git push origin v1.x.x` (pushing a tag no longer builds anything)
5. Create the GitHub release for that tag and attach the locally built `build/dist/ChatCollect.exe`
6. Users get auto-update via in-app button

## Manual Release (Fallback)
If automation fails:
1. Build locally with `build_exe.bat`
2. Go to GitHub → Releases → New Release
3. Tag must match version (e.g., `v1.2.7`)
4. Upload only `ChatCollect.exe`
