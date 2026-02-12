# Antigravity (Google Gemini IDE) — Data Format Specification

## Overview

Antigravity is a **Google-built VS Code fork** (v1.11.2) with Gemini AI integration. It uses the Open VSX marketplace and Google Cloud for auto-updates. **The app is no longer installed on this machine** but data directories remain.

**Priority: P3 (Low)** — Almost no conversation data found. Included for completeness.

## Storage Locations

```
~/.antigravity/                                     # CLI config + extensions (606 MB)
├── argv.json                                       # CLI arguments
├── antigravity/bin/                                # CLI symlinks (broken — app uninstalled)
├── extensions/                                     # VS Code extensions (606 MB)
└── extensions/extensions.json                      # Extension registry

~/Library/Application Support/Antigravity/          # Electron app data (121 MB)
├── User/
│   ├── settings.json                               # Editor settings
│   ├── keybindings.json                            # Keybindings (Cmd+I → composerMode.agent)
│   └── globalStorage/
│       ├── storage.json                            # Full app state
│       └── state.vscdb                             # SQLite key-value store (258 KB)
├── CachedData/                                     # V8 bytecode cache (32 MB)
└── CachedExtensionVSIXs/                           # Downloaded extensions (55 MB)

~/.gemini/antigravity/                              # Gemini integration data
├── installation_id                                 # UUID
├── browserAllowlist.txt                            # 77 allowed domains
├── mcp_config.json                                 # MCP config (empty)
├── user_settings.pb                                # Protobuf settings
├── brain/                                          # Empty (Gemini memory)
├── context_state/                                  # Empty
├── code_tracker/                                   # Empty (active + history)
├── implicit/{uuid}.pb                              # Protobuf context (319 bytes)
└── playground/perihelion-sagan/                     # Empty workspace
```

## State Database

**Path:** `~/Library/Application Support/Antigravity/User/globalStorage/state.vscdb`
**Format:** SQLite, single `ItemTable` (key-value)
**Size:** 258 KB

### Relevant Keys

| Key | Value | Notes |
|-----|-------|-------|
| `antigravityAuthStatus` | Google OAuth2 auth state | Authenticated as "Naman Ambavi" |
| `antigravity.profileUrl` | Base64 JPEG profile pic | |
| `antigravityChangelog/lastVersion` | `"1.11.2"` | |
| `antigravity_allowed_command_model_configs` | Base64 protobuf | Lists "Gemini 3 Flash" and "Gemini 3 Pro (Low)" |
| `chat.ChatSessionStore.index` | `{"version":1,"entries":{}}` | **EMPTY — no saved chats** |
| `jetskiStateSync.agentManagerInitState` | Protobuf | Agent manager state (codenamed "jetski") |
| `google.antigravity` | Codeium installation ID | |

## Chat Sessions

**No conversation data exists.** `chat.ChatSessionStore.index` is empty. The app was likely used briefly and uninstalled.

## Parsing Challenges

- Some values are **protobuf-encoded** (not JSON) — requires protobuf decoding
- Auth tokens are Google OAuth2 — do not collect
- Very little useful data to extract

## Collection Strategy

| Priority | Data | Method |
|----------|------|--------|
| P3 | Chat sessions | SQLite query on `chat.ChatSessionStore.index` — currently empty |
| Skip | Everything else | Low value, protobuf encoding, or sensitive |

**Recommendation:** Only implement if a user is actively using Antigravity. Detection: check if `~/.antigravity/` exists AND `state.vscdb` has non-empty chat sessions.
