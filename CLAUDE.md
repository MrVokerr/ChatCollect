# ChatCollect

## Core rule: local-first, zero GitHub Actions minutes

- Never use GitHub Actions as a test runner. Run all tests, builds, lint, sims and checks locally (in the session's container or on the owner's own machines) before pushing.
- No workflow may run automatically: no `push`, `pull_request`, `schedule` or `workflow_run` triggers. Workflows are `workflow_dispatch` (manual) only, and only run with the owner's OK.
- If a workflow with an automatic trigger shows up, switch it to manual-only and make sure the local test script and pre-push hook cover what it checked.
- A PR is done when the local test suite passes (not "CI green"). Say in the PR which local commands you ran.
- Batch commits and push once per finished change. No push-to-iterate loops.
- Deploys go through the host's own Git integration (e.g. Vercel), never through Actions.
- If anything would use Actions minutes, Codespaces or other paid GitHub usage, ask the owner first.

### Local checks

- `bash scripts/test-local.sh` runs a syntax check of `build/*.py` and checks that `version.txt` matches `CURRENT_VERSION` in `build/chatcollect_gui.py`.
- Pre-push hook: `.githooks/pre-push` runs that script before every push. Turn it on once per clone with `git config core.hooksPath .githooks`.
- Releases: build locally with `build/build_exe.bat`, push the tag, then create the GitHub release with that exe. `.github/workflows/release.yml` is a manual-only fallback that needs the owner's OK.
