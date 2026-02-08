# OpenClaw — Data Format Specification

## Storage Location

```
~/.openclaw/
├── openclaw.json                   # Master config (LLM provider, channels, gateway)
├── openclaw.json.bak[.1-4]        # Rolling config backups
├── update-check.json               # Version check
├── agents/main/
│   ├── sessions/
│   │   ├── sessions.json           # Session index + metadata
│   │   ├── {uuid}.jsonl            # Active session transcripts
│   │   └── {uuid}.jsonl.deleted.{ts}  # Soft-deleted sessions
│   └── agent/
│       └── auth-profiles.json      # LLM API key profiles
├── workspace/                      # Agent's working directory
│   ├── AGENTS.md                   # Operating instructions (injected to system prompt)
│   ├── SOUL.md                     # Personality definition
│   ├── USER.md                     # User profile
│   ├── MEMORY.md                   # Long-term curated memories
│   ├── IDENTITY.md                 # Agent identity
│   ├── HEARTBEAT.md                # Periodic task config
│   ├── TOOLS.md                    # Local environment notes
│   └── memory/YYYY-MM-DD.md        # Daily memory logs
├── memory/main.sqlite              # Semantic memory DB (FTS5 + embeddings)
├── skills/                         # User-created skills
├── subagents/runs.json             # Sub-agent run tracking
├── cron/
│   ├── jobs.json                   # Scheduled job definitions
│   └── runs/{jobId}.jsonl          # Job execution logs
├── credentials/                    # Channel auth (Telegram pairing)
├── devices/paired.json             # Paired device registry
├── identity/device.json            # Device keypair
├── logs/                           # Gateway logs
├── media/inbound/                  # Received files
├── browser/                        # Chrome extension
├── canvas/                         # Web UI
└── telegram/                       # Telegram bot state
```

---

## 1. Session Index

**Path:** `~/.openclaw/agents/main/sessions/sessions.json`
**Format:** JSON

```json
{
  "version": 2,
  "agents": {
    "agent:main:main": {
      "activeSessionId": "1906e15d-...",
      "model": {"provider": "anthropic", "model": "claude-opus-4-5"},
      "tokenCounts": {
        "inputTokens": 45000,
        "outputTokens": 12000,
        "totalTokens": 57000
      },
      "deliveryContext": {
        "channel": "telegram",
        "to": "1078321387"
      },
      "skills": [
        {"name": "apple-notes", "filePath": "/path/to/SKILL.md", "description": "..."},
        ...
      ],
      "systemPromptReport": {
        "injectedWorkspaceFiles": ["AGENTS.md", "SOUL.md", "USER.md"],
        "toolSchemas": 18,
        "totalSize": 45000
      }
    }
  }
}
```

---

## 2. Session Transcripts

**Path:** `~/.openclaw/agents/main/sessions/{uuid}.jsonl`
**Format:** JSONL
**Size range:** 6 KB to 16 MB

### Record Types

| Type | Description |
|------|-------------|
| `session` | Session initialization header (first line) |
| `message` | User messages, assistant responses, tool results |
| `compaction` | Context compression summary |
| `model_change` | Model switch event |
| `thinking_level_change` | Thinking level adjustment |
| `custom:openclaw.cache-ttl` | Cache TTL events |
| `custom:model-snapshot` | Model state capture |

### Common Fields (all records)

```json
{
  "type": "message",
  "id": "71443552",
  "parentId": "ccd6e3f9",
  "timestamp": "2026-01-31T07:26:10.958Z",
  ...
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Record type |
| `id` | string (8 hex chars) | Unique record ID |
| `parentId` | string \| null | Previous record (linked list) |
| `timestamp` | string (ISO 8601) | Event time |

### 2.1 `type: "message"` — Conversations

**User message:**
```json
{
  "type": "message",
  "id": "71443552",
  "parentId": "ccd6e3f9",
  "timestamp": "2026-01-31T07:26:10.958Z",
  "message": {
    "role": "user",
    "content": [{"type": "text", "text": "Check my calendar"}],
    "timestamp": 1769844370957
  }
}
```

**Assistant message:**
```json
{
  "type": "message",
  "message": {
    "role": "assistant",
    "provider": "anthropic-messages",
    "model": "claude-opus-4-5",
    "content": [
      {"type": "text", "text": "Let me check your calendar..."},
      {
        "type": "tool_use",
        "id": "toolu_016Gz8...",
        "name": "apple-calendar-list",
        "input": {"days": 1}
      }
    ],
    "stopReason": "tool_use",
    "usage": {
      "inputTokens": 5000,
      "outputTokens": 200
    }
  }
}
```

**Tool result:**
```json
{
  "type": "message",
  "message": {
    "role": "toolResult",
    "toolCallId": "toolu_016Gz8...",
    "toolName": "apple-calendar-list",
    "content": [{"type": "text", "text": "Meeting with John at 2pm..."}],
    "isError": false
  }
}
```

**Delivery mirror (forwarding to Telegram):**
```json
{
  "type": "message",
  "message": {
    "role": "assistant",
    "provider": "openai-responses",
    "model": "delivery-mirror",
    "content": [{"type": "output_text", "text": "You have a meeting..."}]
  }
}
```

#### Message Roles

| Role | Provider | Description |
|------|----------|-------------|
| `user` | — | Human input |
| `assistant` | `anthropic-messages` | Claude response |
| `assistant` | `openai-responses` / `delivery-mirror` | Forwarded to channel (Telegram) |
| `toolResult` | — | Tool execution output |

#### Tool Names (from bundled skills)

`apple-notes-*`, `apple-reminders-*`, `apple-calendar-*`, `read`, `write`, `shell`, `web-search`, `web-fetch`, `peekaboo-*` (UI automation), `bird-*` (Twitter), `github-*`, `himalaya-*` (email), `sessions_spawn` (sub-agent)

### 2.2 `type: "compaction"` — Context Compression

```json
{
  "type": "compaction",
  "id": "abc123",
  "parentId": "prev-id",
  "timestamp": "...",
  "summary": "The user asked about calendar events. I checked and found...\n<read-files>\n- AGENTS.md\n</read-files>\n<modified-files>\n- workspace/report.md\n</modified-files>"
}
```

Contains compressed summaries of earlier conversation, including lists of files read and modified.

### 2.3 Soft-Deleted Sessions

Deleted sessions are renamed to `{uuid}.jsonl.deleted.{ISO-timestamp}` (not removed). Parse the same way as active sessions.

---

## 3. Cron Jobs

**Path:** `~/.openclaw/cron/jobs.json`
**Format:** JSON

```json
{
  "jobs": [
    {
      "id": "5145dbcf-...",
      "name": "Meeting Intel",
      "prompt": "Check calendars for meetings starting in 30-45 minutes...",
      "schedule": {"kind": "interval", "everyMs": 900000},
      "enabled": true,
      "createdAt": "2026-01-31T..."
    }
  ]
}
```

**Run logs:** `~/.openclaw/cron/runs/{jobId}.jsonl`
```json
{"timestamp": "...", "jobId": "...", "action": "finished", "status": "ok", "summary": "No upcoming meetings", "durationMs": 12500, "nextRunAt": "..."}
```

---

## 4. Memory Files

### Daily Logs
**Path:** `~/.openclaw/workspace/memory/YYYY-MM-DD.md`
Markdown notes written by the agent at end of day.

### Curated Memory
**Path:** `~/.openclaw/workspace/MEMORY.md`
Long-term distilled facts (people, preferences, patterns).

### Semantic Memory (SQLite)
**Path:** `~/.openclaw/memory/main.sqlite`
Schema: `meta`, `files`, `chunks` (with embeddings), `embedding_cache`, `chunks_fts` (FTS5).
Currently empty — agent uses markdown files instead.

---

## 5. Collection Strategy for OpenClaw

### What to Collect

| Priority | Data | Path | Method |
|----------|------|------|--------|
| P0 | Session transcripts | `agents/main/sessions/*.jsonl` | Incremental read |
| P0 | Session index | `agents/main/sessions/sessions.json` | Read full, track mtime |
| P1 | Cron job logs | `cron/runs/*.jsonl` | Incremental read |
| P1 | Cron job defs | `cron/jobs.json` | Read full |
| P2 | Memory files | `workspace/MEMORY.md`, `workspace/memory/*.md` | Read full |
| P2 | Personality | `workspace/SOUL.md`, `IDENTITY.md`, `USER.md` | Read full |
| Skip | Auth profiles | `agents/main/agent/auth-profiles.json` | Sensitive |
| Skip | Credentials | `credentials/`, `identity/` | Sensitive |
| Skip | Workspace files | `workspace/reports/` | Generated artifacts, too large |
| Skip | Deleted sessions | `*.jsonl.deleted.*` | Historical, lower value |

### Incremental Reading

Same byte-offset approach. JSONL files are append-only. Track in `~/.oximy/local-scan-state.json`.
