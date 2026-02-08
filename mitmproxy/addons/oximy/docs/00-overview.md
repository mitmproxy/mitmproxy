# Local AI Tool Session Collection — Overview

## Purpose

Collect session data (prompts, responses, tool calls, file diffs, tokens, subagents) from AI coding tools installed on user machines and send it to Oximy servers for analysis. This complements the existing network-traffic capture with local file-based data that never hits the network.

## Supported Tools

| Tool | Storage Format | Location | Data Richness | Priority |
|------|---------------|----------|---------------|----------|
| Claude Code | JSONL files | `~/.claude/` | Very High (427 sessions, 2.3GB) | P0 |
| Cursor IDE | SQLite + JSON | `~/.cursor/` + `~/Library/Application Support/Cursor/` | Very High (1,646 conversations, 2.4GB) | P0 |
| OpenAI Codex CLI | JSONL files | `~/.codex/` | Medium (4 sessions, 6.5MB) | P1 |
| OpenClaw | JSONL files | `~/.openclaw/` | Medium (9 sessions, 24MB useful) | P2 |
| Antigravity | SQLite (protobuf) | `~/.antigravity/` | Low (no chat data) | P3 |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  User's Machine (macOS App)                             │
│                                                         │
│  ┌──────────────┐    ┌──────────────────────────────┐   │
│  │ mitmproxy     │    │ LocalDataCollector (new)      │   │
│  │ addon.py      │    │                              │   │
│  │               │    │  Polls local files every Ns  │   │
│  │ (network      │    │  Reads JSONL / SQLite        │   │
│  │  capture)     │    │  Tracks offsets in state file │   │
│  └──────┬───────┘    └──────────┬───────────────────┘   │
│         │                       │                       │
│         ▼                       ▼                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │         MemoryTraceBuffer (existing)              │   │
│  │         Bounded, thread-safe, 20-200MB            │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                               │
│                         ▼                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │  DirectTraceUploader (existing)                   │   │
│  │  Batches → gzip → POST to API                    │   │
│  │  Retries 3x with backoff                         │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                               │
└─────────────────────────┼───────────────────────────────┘
                          │ HTTPS (Bearer token auth)
                          ▼
              ┌───────────────────────┐
              │  api.oximy.com        │
              │  POST /api/v1/ingest/ │
              │  local-sessions       │
              └───────────────────────┘
```

## Key Design Principles

1. **Raw pipe** — The sensor is a dumb pipe. It reads files, wraps raw JSON in a thin envelope, and POSTs to the API. **All parsing and normalization happens server-side.** This means no app updates when tool schemas change.
2. **Server-driven config** — What to scan, polling intervals, enabled sources, redaction rules all come from `sensor-config` API. No app updates needed to add new sources.
3. **Incremental reads** — Track byte offsets (JSONL) and timestamps (SQLite) to only read new data.
4. **Reuse existing infra** — Same buffer, uploader, auth, and error handling as network traces.
5. **Fail-silent** — If a tool isn't installed (dir doesn't exist), skip. If a file is locked, retry next cycle.
6. **No new dependencies** — `json`, `sqlite3`, `glob`, `os` are all Python stdlib.

## File Index

| File | Audience | Contents |
|------|----------|----------|
| [01-claude-code.md](01-claude-code.md) | API team | Claude Code full data format spec |
| [02-cursor.md](02-cursor.md) | API team | Cursor IDE full data format spec |
| [03-codex.md](03-codex.md) | API team | OpenAI Codex CLI full data format spec |
| [04-openclaw.md](04-openclaw.md) | API team | OpenClaw full data format spec |
| [05-antigravity.md](05-antigravity.md) | API team | Antigravity (Google Gemini) data format spec |
| [06-unified-model.md](06-unified-model.md) | Both | Wire format (sensor → API), envelope schema, batching |
| [07-sensor-config.md](07-sensor-config.md) | Sensor team | Sensor config extension, collection architecture, state management |
| [08-api-parsing-guide.md](08-api-parsing-guide.md) | API team | **How to parse each source**, routing logic, JS parser code, DB schema, re-processing |
