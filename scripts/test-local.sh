#!/usr/bin/env bash
# Local checks (replaces GitHub Actions). Run from anywhere: bash scripts/test-local.sh
# Release builds happen locally too: build\build_exe.bat on Windows, then upload the exe to a GitHub release.
set -euo pipefail
cd "$(dirname "$0")/.."
# Finds a Python 3.10+ (python3 on Linux/macOS, python or py on Windows Git Bash).
PY=""
for c in python3 python py; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "test-local: no Python 3.10+ found" >&2; exit 1; }
echo "== syntax check build/*.py"
"$PY" -c "import pathlib; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in pathlib.Path('build').glob('*.py')]"
echo "== version.txt matches CURRENT_VERSION in chatcollect_gui.py"
file_ver="$(tr -d '[:space:]' < version.txt)"
code_ver="$(sed -n 's/^CURRENT_VERSION *= *"\([^"]*\)".*/\1/p' build/chatcollect_gui.py | head -1)"
echo "version.txt=$file_ver  code=$code_ver"
[ -n "$file_ver" ] && [ "$file_ver" = "$code_ver" ] || { echo "test-local: version.txt and CURRENT_VERSION differ" >&2; exit 1; }
echo "test-local: all checks passed"
