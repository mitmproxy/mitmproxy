# Claude Code — Data Format Specification

## Storage Location

```
~/.claude/
├── projects/                          # Per-project session data (2.3 GB)
│   ├── {project-key}/                 # e.g. -Users-name-Desktop-project
│   │   ├── sessions-index.json        # Session index (metadata for all sessions)
│   │   ├── memory/MEMORY.md           # Persistent cross-session memory
│   │   ├── {sessionId}.jsonl          # Main session transcript
│   │   └── {sessionId}/
│   │       ├── subagents/
│   │       │   └── agent-{agentId}.jsonl  # Subagent transcripts
│   │       └── tool-results/
│   │           └── toolu_{id}.txt     # Large tool output overflow
├── history.jsonl                      # Global prompt history (all sessions)
├── todos/                             # TodoWrite state per session
├── plans/                             # Markdown plan documents
├── settings.json                      # User config, permissions, hooks
└── stats-cache.json                   # Aggregated usage statistics
```

**Project key format:** Filesystem path with `/` replaced by `-` and leading `-`.
Example: `/Users/naman/Desktop/project` → `-Users-naman-Desktop-project`

---

## 1. sessions-index.json

**Path:** `~/.claude/projects/{project-key}/sessions-index.json`
**Format:** JSON
**Purpose:** Index of all sessions in a project. START HERE for discovery.

```json
{
  "version": 1,
  "entries": [
    {
      "sessionId": "d389b24d-28dd-4e76-b01d-bb6aeb3f0f72",
      "fullPath": "/Users/name/.claude/projects/.../d389b24d-....jsonl",
      "fileMtime": 1768263841305,
      "firstPrompt": "Why is this coming for the DMGs...",
      "messageCount": 14,
      "created": "2026-01-13T00:20:06.190Z",
      "modified": "2026-01-13T00:24:01.280Z",
      "gitBranch": "main",
      "projectPath": "/Users/name/Desktop/project",
      "isSidechain": false
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `sessionId` | string (UUID) | Unique session identifier |
| `fullPath` | string | Absolute path to the JSONL transcript file |
| `fileMtime` | number | File modification time (epoch ms) |
| `firstPrompt` | string | First user message (may be truncated) |
| `messageCount` | number | Total messages in session |
| `created` | string (ISO 8601) | Session start time |
| `modified` | string (ISO 8601) | Last activity time |
| `gitBranch` | string | Git branch at time of session |
| `projectPath` | string | Absolute path to the project directory |
| `isSidechain` | boolean | Whether this is a sidechain session |

**Collection strategy:** Read this file to discover sessions. Use `fileMtime` to detect changes since last scan.

---

## 2. Session Transcript (main JSONL)

**Path:** `~/.claude/projects/{project-key}/{sessionId}.jsonl`
**Format:** JSONL (one JSON object per line)
**Size range:** 0 bytes (empty/abandoned) to 13.6 MB. ~38% of files are empty.

### Record Types

Every line has a `type` field. There are **5 record types:**

### 2.1 `type: "user"` — Human Prompts & Tool Results

```json
{
  "parentUuid": "abc123-...",
  "isSidechain": false,
  "userType": "external",
  "cwd": "/Users/name/project",
  "sessionId": "d389b24d-...",
  "version": "2.1.4",
  "gitBranch": "main",
  "slug": "linked-watching-shell",
  "type": "user",
  "message": {
    "role": "user",
    "content": "Fix the login bug"
  },
  "uuid": "unique-id",
  "timestamp": "2026-01-09T23:44:35.789Z"
}
```

**When content is a tool result:**
```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_01G8C1t6...",
        "content": "file contents here...",
        "is_error": false
      }
    ]
  },
  "toolUseResult": {
    "stdout": "Build successful",
    "stderr": "",
    "interrupted": false,
    "isImage": false
  },
  "sourceToolAssistantUUID": "uuid-of-assistant-that-called-tool",
  "todos": [
    {"content": "Fix login", "status": "completed", "activeForm": "Fixing login"}
  ]
}
```

**~80% of "user" lines are tool results**, not actual human input. Distinguish by checking if `content` is a string (human) or array with `tool_result` items.

#### toolUseResult Schemas (varies by tool)

| Tool | Schema |
|------|--------|
| **Bash** | `{stdout, stderr, interrupted, isImage}` |
| **Bash (error)** | `{stdout, stderr, interrupted, isImage, returnCodeInterpretation}` |
| **Read** | `{file: {filePath, content, numLines, startLine, totalLines}, type: "text"}` |
| **Write/Edit** | `{type: "create" \| "update"}` |
| **Glob** | `{filenames: [...], durationMs, numFiles, truncated}` |
| **Grep** | `{filenames: [...], mode, numFiles}` or `{filenames, appliedLimit, mode, numFiles}` |
| **Task (subagent)** | `{agentId, status, totalDurationMs, totalTokens, totalToolUseCount, prompt, content, usage}` |
| **Error** | Plain string: `"Error: File content exceeds maximum..."` |

### 2.2 `type: "assistant"` — Claude's Responses

```json
{
  "parentUuid": "prev-uuid",
  "isSidechain": false,
  "type": "assistant",
  "message": {
    "model": "claude-opus-4-5-20251101",
    "id": "msg_01ABC...",
    "type": "message",
    "role": "assistant",
    "content": [
      {"type": "text", "text": "I'll fix the login bug..."},
      {
        "type": "tool_use",
        "id": "toolu_01XYZ...",
        "name": "Edit",
        "input": {
          "file_path": "/path/to/file.py",
          "old_string": "broken code",
          "new_string": "fixed code"
        }
      }
    ],
    "stop_reason": "tool_use",
    "usage": {
      "input_tokens": 3,
      "cache_creation_input_tokens": 5423,
      "cache_read_input_tokens": 13001,
      "cache_creation": {
        "ephemeral_5m_input_tokens": 5423,
        "ephemeral_1h_input_tokens": 0
      },
      "output_tokens": 150,
      "service_tier": "standard"
    }
  },
  "requestId": "req_01ABC...",
  "uuid": "unique-id",
  "timestamp": "2026-01-09T23:45:00.123Z"
}
```

**CRITICAL:** Assistant messages are **streamed** — a single API call produces multiple JSONL lines sharing the same `requestId` and `message.id`. Each line contains one content item. `stop_reason` is `null` on intermediate lines.

#### Content Block Types

| `content[].type` | Fields | Description |
|------------------|--------|-------------|
| `text` | `text` | Assistant's text response |
| `tool_use` | `id`, `name`, `input` | Tool invocation with parameters |

#### Tool Names (observed)

`Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Task`, `TodoWrite`, `ExitPlanMode`, `TaskOutput`, `WebFetch`, `WebSearch`, `AskUserQuestion`, `NotebookEdit`, `EnterPlanMode`

#### Usage Object

| Field | Type | Description |
|-------|------|-------------|
| `input_tokens` | int | New (non-cached) input tokens |
| `output_tokens` | int | Generated output tokens |
| `cache_read_input_tokens` | int | Tokens read from cache (dominates — can be millions) |
| `cache_creation_input_tokens` | int | Tokens written to cache |
| `cache_creation.ephemeral_5m_input_tokens` | int | 5-minute cache tier |
| `cache_creation.ephemeral_1h_input_tokens` | int | 1-hour cache tier |
| `service_tier` | string | `"standard"` |

### 2.3 `type: "system"` — Conversation Compaction

```json
{
  "type": "system",
  "subtype": "compact_boundary",
  "content": "Conversation compacted",
  "isMeta": false,
  "level": "info",
  "compactMetadata": {
    "trigger": "context_limit",
    "preTokens": 180000
  },
  "uuid": "...",
  "timestamp": "..."
}
```

Rare (~0.2% of lines). Marks where conversation history was compressed.

### 2.4 `type: "file-history-snapshot"` — File Backups

```json
{
  "type": "file-history-snapshot",
  "messageId": "uuid",
  "snapshot": {
    "messageId": "uuid",
    "trackedFileBackups": {
      "/path/to/file.py": "original file contents..."
    },
    "timestamp": "2026-01-09T23:44:35.790Z"
  },
  "isSnapshotUpdate": false
}
```

Tracks file state before modifications for undo. `trackedFileBackups` maps file paths to their pre-edit content.

### 2.5 `type: "queue-operation"` — Message Queue Lifecycle

```json
{
  "type": "queue-operation",
  "operation": "dequeue",
  "timestamp": "2026-01-09T23:44:35.782Z",
  "sessionId": "d389b24d-..."
}
```

Operations: `enqueue`, `dequeue`, `remove`. Tracks user message processing flow.

---

## 3. UUID Threading Model

Messages form a **tree** (not a linear list):

```
user (parentUuid: null)          ← root
  └─ assistant (text)            ← uuid=A
       └─ assistant (tool_use)   ← uuid=B
            ├─ assistant (tool_use)  ← uuid=C (next tool in same call)
            └─ user (tool_result)    ← uuid=D (result for B's tool)
                 └─ assistant (text) ← uuid=E (continues after result)
```

- `parentUuid: null` = conversation root
- Branching occurs at parallel tool calls
- `sourceToolAssistantUUID` links tool results to their invoking assistant message (separate from `parentUuid`)
- All UUIDs are self-contained within one file

---

## 4. Subagent Transcripts

**Path:** `~/.claude/projects/{project-key}/{sessionId}/subagents/agent-{agentId}.jsonl`
**Format:** Same JSONL as main sessions, but only `user` and `assistant` record types.

### Key Differences from Main Sessions

| Field | Main Session | Subagent |
|-------|-------------|----------|
| `isSidechain` | `false` | Always `true` |
| `agentId` | Absent | Present (7-char hex, matches filename) |
| Record types | All 5 | Only `user` + `assistant` |
| Model | Opus/Sonnet | Typically Haiku (cheaper) |

### Warmup Stubs

**38% of subagent files** (296/773) are 369-byte stubs containing only:
```json
{"message": {"role": "user", "content": "Warmup"}, "type": "user", ...}
```

These are pre-allocated but never used. **Skip files where line 1 content = "Warmup" AND file has only 1 line.**

### Linking Subagents to Parent Session

In the parent session JSONL, a `Task` tool_use creates the subagent:
```json
{"type": "tool_use", "name": "Task", "input": {"subagent_type": "Explore", "prompt": "..."}}
```

The corresponding tool_result contains:
```json
{"toolUseResult": {"agentId": "aff2f18", "status": "completed", "totalDurationMs": 107544, "totalTokens": 79900, "totalToolUseCount": 49}}
```

`agentId` → filename `agent-aff2f18.jsonl`.

---

## 5. Tool Result Overflow

**Path:** `~/.claude/projects/{project-key}/{sessionId}/tool-results/toolu_{toolUseId}.txt`
**Format:** Plain text (ASCII or binary)
**Purpose:** Stores tool outputs that exceeded inline size limits (up to 1.7 MB).

The `toolUseId` matches the `id` field from a `tool_use` content block. Both main session and subagent tool outputs share the same directory.

---

## 6. Global Prompt History

**Path:** `~/.claude/history.jsonl`
**Format:** JSONL

```json
{
  "display": "Fix the login bug",
  "pastedContents": {},
  "timestamp": 1766607244547,
  "project": "/Users/name/Desktop/project",
  "sessionId": "d389b24d-..."
}
```

Lightweight cross-session prompt index. Every user prompt across all projects.

---

## 7. Stats Cache

**Path:** `~/.claude/stats-cache.json`
**Format:** JSON

Contains aggregated usage: total sessions, messages, tool calls, per-model token counts, hourly/daily breakdowns. Useful for high-level telemetry without parsing all sessions.

---

## 8. Collection Strategy for Claude Code

### What to Collect

| Priority | Data | Path | Method |
|----------|------|------|--------|
| P0 | Session index | `projects/*/sessions-index.json` | Read full file, compare mtime |
| P0 | Session transcripts | `projects/*/*.jsonl` | Incremental read (byte offset) |
| P1 | Subagent transcripts | `projects/*/*/subagents/agent-*.jsonl` | Incremental read |
| P2 | Global history | `history.jsonl` | Incremental read |
| P3 | Stats cache | `stats-cache.json` | Read full file |
| Skip | Tool overflow files | `tool-results/*.txt` | Too large, low value |
| Skip | File history snapshots | `file-history/` | Raw file backups, not conversations |
| Skip | Shell snapshots | `shell-snapshots/` | Environment captures, not useful |

### Incremental Reading (JSONL)

```
State file: ~/.oximy/local-scan-state.json
{
  "claude_code": {
    "files": {
      "~/.claude/projects/-Users-.../abc123.jsonl": {
        "offset": 45678,
        "mtime": 1768263841305
      }
    }
  }
}
```

1. Check file mtime — skip if unchanged
2. Seek to saved byte offset
3. Read new lines from offset
4. Update offset after successful upload
