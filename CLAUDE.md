## Project Structure

All addon changes go in `mitmproxy/addons/oximy/` — this is the **source of truth**. Desktop app bundles are synced copies with converted imports.

```
mitmproxy/addons/oximy/
  addon.py       ← Main addon logic (~4000+ lines)
  normalize.py   ← gRPC, SSE, msgpack decoding
  process.py     ← Process resolution (PID → bundle ID)
  collector.py   ← Event collection
  config.json    ← Default config
  tests/         ← Unit tests (pytest)
```

## Testing

Run tests before committing or building:

```bash
python -m pytest mitmproxy/addons/oximy/tests/ -v --tb=short
```

Expected: `271 passed`. Run specific files or patterns with `-k`:

```bash
python -m pytest mitmproxy/addons/oximy/tests/test_addon.py -v
python -m pytest mitmproxy/addons/oximy/tests/ -k "grpc" -v
```

## Building Desktop Apps

Always make changes in `mitmproxy/addons/oximy/` first, then sync to the platform app.

**macOS:**
```bash
cd OximyMac && make build        # sync + build (debug)
cd OximyMac && make run          # sync + build + run
cd OximyMac && make dmg          # release DMG for distribution
```

**Windows:**
```powershell
cd OximyWindows/scripts && .\build.ps1                              # debug build
cd OximyWindows/scripts && .\build.ps1 -Release -CreateVelopack -Version "1.0.0"  # release
```

Both build systems auto-sync the addon and convert imports (`from mitmproxy.addons.oximy.X` → `from X`).

## Git Workflow

### Branching

**Never commit directly to `main`** for feature work. Always use a branch:

```bash
# Feature branch
git checkout -b feat/add-grpc-support

# Bug fix branch
git checkout -b fix/missing-bundle-id

# Chore / CI / docs
git checkout -b chore/update-release-workflow
```

Branch naming: `<type>/<short-kebab-description>` — matches the commit type.

When the feature is done: push the branch, open a PR against `main`, then merge.

```bash
git push -u origin feat/add-grpc-support
gh pr create --title "feat: Add gRPC support" --body "Description of changes"
```

### Worktrees (Parallel Sessions)

When multiple Claude Code sessions or tasks need to run simultaneously on different branches, use **git worktrees** instead of stashing or switching branches:

```bash
# Create a worktree for a feature branch (from the repo root)
git worktree add ../sensor-feat-grpc feat/add-grpc-support

# Create a worktree with a new branch
git worktree add ../sensor-fix-logging -b fix/logging-issue

# List active worktrees
git worktree list

# Remove when done (after merging)
git worktree remove ../sensor-feat-grpc
```

Each worktree is a full working copy at a separate path — independent builds, independent test runs, no conflicts. Name worktree directories `sensor-<branch-slug>` to keep them identifiable.

**When to use worktrees:**
- User has multiple Claude sessions working on different features
- A hotfix is needed while a feature branch is mid-work
- Running long builds on one branch while coding on another

### Commit Messages

Use **Conventional Commits** format:

```
<type>: <Imperative description>
```

| Type | Use for | Example |
|------|---------|---------|
| `feat` | New feature | `feat: Add MDM configuration service` |
| `fix` | Bug fix | `fix: Handle missing bundle IDs in client logging` |
| `refactor` | Code restructuring, no behavior change | `refactor: Improve LocalDataCollector startup` |
| `chore` | CI, build scripts, deps | `chore: Update release workflow` |
| `docs` | Documentation only | `docs: Add testing section to CLAUDE.md` |

Rules:
- Imperative mood ("Add X", not "Added X")
- Under 72 characters, no trailing period
- Multi-area changes: summarize primary intent

### Pushing Code & Opening PRs

When the user asks to push, commit, or ship changes, **always follow this full workflow** — push + PR is the standard, not just push:

1. **Ensure you're on a feature branch** — not `main` (unless explicitly told otherwise):
   ```bash
   git branch --show-current  # verify — if on main, create a branch first
   ```
2. **Run tests** — never push broken code:
   ```bash
   python -m pytest mitmproxy/addons/oximy/tests/ -v --tb=short
   ```
3. **Stage specific files** — never use `git add .` or `git add -A`:
   ```bash
   git add path/to/file.py path/to/other.py
   ```
4. **Commit with conventional format**:
   ```bash
   git commit -m "feat: Description here"
   ```
5. **Push** (use `-u` on first push to set upstream):
   ```bash
   git push -u origin <branch>
   ```
6. **Open a PR** — always create a PR after pushing:
   ```bash
   gh pr create --title "feat: Short description" --body "## Summary
   - What changed and why

   ## Test plan
   - [ ] Tests pass locally
   - [ ] Manually verified"
   ```

Never force-push to `main` without explicit user approval. Never skip pre-commit hooks.

### Notifications

Two Slack notifications are configured:
- **Push to main** (`oximy-push-notify.yml`): fires on every push/merge to `main` — blue notification with commit info and author
- **Release** (`oximy-release.yml`): fires when a release completes or fails — green/red notification with version and download links

Every merge to `main` triggers a Slack ping so the team knows what landed, even without a release.

### Release Workflow

Releases are manual via GitHub Actions (`oximy-release.yml`). Go to Actions → "Oximy Release" → Run workflow → enter version.

```
Preflight (ubuntu)                     ← rejects duplicate versions, generates changelog
    ├── Build macOS (macos-14)         ← Xcode, code-sign, notarize → DMG
    └── Build Windows (windows-latest) ← .NET, Velopack, Inno Setup → EXE
            └── Create Release         ← GitHub release + latest tag + Slack
```

- **Version tags**: `oximy-v{VERSION}` (e.g., `oximy-v1.2.0`)
- **Duplicate guard**: Preflight fails immediately if the tag already exists
- **Changelog**: Auto-generated from commits since the previous `oximy-v*` tag
- **Latest tag**: Stable releases update the `latest` GitHub Release; pre-releases do not
- **Slack**: Posts success/failure notification with version and links

**Pre-release vs Release:**
- `prerelease: false` → tagged as `latest`, production rollout
- `prerelease: true` → "Pre-release" badge, no `latest` tag, for internal testing

Check current deployed version: `gh release view latest --json name,tagName`

## Sensor Configuration

The addon's filtering config comes from the API, not local files:

- **API**: `https://api.oximy.com/api/v1/sensor-config` (auth: bearer token from `~/.oximy/device-token`)
- **Local cache**: `~/.oximy/sensor-config.json` (fallback only, overwritten every 30 min)

**Do NOT edit the local cache** — it gets overwritten. To change config, update the API backend:
- New domains: add to `whitelistedDomains` and `allowed_host_origins`
- New blacklist words: add to `blacklistedWords`

### Whitelist Patterns

| Pattern | Matches |
|---------|---------|
| `api.openai.com` | Any request to api.openai.com |
| `*.openai.com` | Any subdomain of openai.com |
| `gemini.google.com/**/StreamGenerate*` | Only StreamGenerate calls |
| `api.openai.com/v1/chat/completions` | Only that exact path |

Wildcards: `**` = any depth, `*` = single segment.

### Request Pipeline

```
STEP 0 (app gating) → STEP 1 (whitelist) → STEP 2 (blacklist) →
STEP 3 (GraphQL blacklist) → STEP 4 (app origin) → STEP 6 (host origin) → capture
```

## App Configuration (Feature Flags)

Config flows through a 3-tier fallback: **MDM → API (remote-state) → defaults**.

```
Backend API (sensor-config)
    ↓ addon fetches every 3s
Python Addon → writes ~/.oximy/remote-state.json
    ↓ Swift polls every 2s
macOS App (RemoteStateService → MDMConfigService)
```

Key files:
- **Addon**: `addon.py` → `_parse_sensor_config()` extracts `appConfig`, writes `remote-state.json`
- **Swift**: `OximyMac/Services/RemoteStateService.swift` → `AppConfigFlags` struct
- **Fallback**: `OximyMac/Services/MDMConfigService.swift` → MDM > remote-state > defaults (per-field)

Available flags: `disableUserLogout`, `disableQuit`, `forceAutoStart`, `managedSetupComplete`, `managedEnrollmentComplete`, `managedCACertInstalled`, `managedDeviceToken`, `managedDeviceId`, `managedWorkspaceId`, `managedWorkspaceName`, `apiEndpoint`, `heartbeatInterval`.

To update flags for a workspace:
```
PATCH /api/v1/workspaces/{workspaceId}/app-config
```

## CA Certificate

Apps use `~/.mitmproxy/oximy-ca-cert.pem` (auto-generated on first run via `CONF_BASENAME = "oximy"` in `mitmproxy/options.py`). If browsers show cert errors, install and trust the cert, then restart the browser.

## Self-Learning

**Claude must continuously improve this file.** When you discover something important while working — a gotcha, a pattern, a file relationship, a debugging insight — add it to CLAUDE.md immediately. Don't wait to be asked.

**What to add:**
- Non-obvious patterns (e.g., "function X expects pre-lowercased input")
- File relationships that aren't obvious from the code structure
- Common pitfalls you hit and how you solved them
- New build commands or test patterns discovered during work
- Architecture decisions or constraints that affect future work

**What NOT to add:**
- Session-specific context or temporary debugging notes
- Anything already covered — check first, avoid duplication
- Verbose explanations — keep entries concise (1-2 lines)

**Where to add:**
- If it fits an existing section (e.g., a testing gotcha → add under Testing), put it there
- If it's a new topic, create a new `##` section
- Keep CLAUDE.md under ~200 lines — if a section grows too large, extract details to a separate file in the repo and link to it

**Format:** Add learnings as bullet points under the relevant section. Prefix with context:
```
- `addon.py`: `_state` is a module-level singleton — tests must save/restore `_state.sensor_active`
- `normalize.py`: `contains_blacklist_word()` expects pre-lowercased words
```
