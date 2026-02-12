# Cursor IDE — Data Format Specification

## Storage Locations

Cursor stores data across **two locations:**

```
~/.cursor/                                          # Cursor-specific (1.4 GB)
├── ai-tracking/ai-code-tracking.db                 # SQLite: AI code attribution
├── projects/{project-name}/
│   ├── agent-transcripts/{uuid}.json               # Full agent conversation logs
│   ├── terminals/                                  # Terminal session logs
│   ├── mcps/                                       # MCP server metadata
│   └── agent-tools/                                # Tool output files
├── plans/{slug}_{hash}.plan.md                     # Implementation plans
├── hooks.json                                      # Pre/post prompt hooks
├── mcp.json                                        # MCP server configs
└── ide_state.json                                  # Recent files

~/Library/Application Support/Cursor/               # Electron app data (2.4 GB)
├── User/
│   ├── globalStorage/state.vscdb                   # THE MAIN DB (2.4 GB SQLite)
│   ├── workspaceStorage/{hash}/
│   │   ├── workspace.json                          # Maps hash → folder path
│   │   └── state.vscdb                             # Per-workspace state
│   ├── settings.json                               # User settings
│   └── History/{hash}/                             # File version history
└── logs/                                           # Application logs
```

**Project name format:** Same as Claude Code — filesystem path with `/` replaced by `-`.

---

## 1. Main State Database (state.vscdb)

**Path:** `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`
**Format:** SQLite 3.x with WAL
**Size:** ~2.4 GB

### Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `ItemTable` | ~3,161 | Settings, metadata, plan registry, auth |
| `cursorDiskKV` | ~141,851 | All conversation data, diffs, checkpoints |

### cursorDiskKV — Key Prefixes (The Conversation Store)

| Prefix | Count | Size | Description |
|--------|-------|------|-------------|
| `bubbleId:` | 66,620 | 904 MB | Individual messages ("bubbles") |
| `agentKv:blob:` | 42,987 | 718 MB | Agent context blobs (binary/protobuf) |
| `checkpointId:` | 11,973 | 476 MB | File undo/restore checkpoints |
| `codeBlockDiff:` | 10,361 | 130 MB | AI-generated code diffs |
| `composerData:` | 1,646 | 58 MB | Conversation session metadata |
| `messageRequestContext:` | 3,773 | 38 MB | Context sent per message |
| `codeBlockPartialInlineDiffFates:` | 4,017 | 20 MB | Diff accept/reject tracking |

### composerData:{uuid} — Conversation Session

```json
{
  "_v": 10,
  "composerId": "uuid",
  "richText": "...",
  "text": "",
  "fullConversationHeadersOnly": [
    {"bubbleId": "bubble-uuid-1", "type": 1},
    {"bubbleId": "bubble-uuid-2", "type": 2, "serverBubbleId": "server-uuid"}
  ],
  "conversationMap": {},
  "status": "none",
  "context": {
    "fileSelections": [],
    "selections": [],
    "terminalSelections": [],
    "cursorRules": [],
    "mentions": {}
  },
  "createdAt": 1762221631321,
  "modelConfig": {"modelName": "default", "maxMode": true},
  "unifiedMode": "chat",
  "forceMode": "chat",
  "totalLinesAdded": 0,
  "totalLinesRemoved": 0,
  "isArchived": false,
  "isDraft": false,
  "todos": []
}
```

| Field | Type | Description |
|-------|------|-------------|
| `composerId` | string (UUID) | Unique conversation ID |
| `fullConversationHeadersOnly` | array | Ordered list of message refs |
| `fullConversationHeadersOnly[].type` | int | `1` = user, `2` = assistant |
| `fullConversationHeadersOnly[].bubbleId` | string | Links to `bubbleId:` entry |
| `context.fileSelections` | array | Files attached to conversation |
| `context.cursorRules` | array | Active cursor rules |
| `modelConfig.modelName` | string | Model used (e.g., "default", "claude-3.5-sonnet") |
| `unifiedMode` | string | `"chat"`, `"composer"`, `"agent"` |
| `createdAt` | number | Epoch milliseconds |
| `totalLinesAdded` / `Removed` | number | Code change metrics |

### bubbleId:{composerId}:{bubbleId} — Individual Message

```json
{
  "_v": 3,
  "type": 2,
  "bubbleId": "uuid",
  "text": "I'll fix the authentication...",
  "suggestedCodeBlocks": [
    {
      "filePath": "/path/to/file.ts",
      "language": "typescript",
      "code": "const auth = ...",
      "startLine": 42,
      "endLine": 55
    }
  ],
  "toolResults": [
    {
      "toolName": "Read",
      "result": "file contents..."
    }
  ],
  "capabilities": [],
  "diffHistories": [],
  "assistantSuggestedDiffs": [
    {
      "filePath": "/path/to/file.ts",
      "oldContent": "...",
      "newContent": "..."
    }
  ],
  "images": [],
  "attachedFolders": [],
  "relevantFiles": ["src/auth.ts", "src/login.tsx"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | int | `1` = user, `2` = assistant |
| `text` | string | Message text content |
| `suggestedCodeBlocks` | array | Code suggestions with file/line info |
| `toolResults` | array | Tool execution results |
| `assistantSuggestedDiffs` | array | File diffs (old → new content) |
| `relevantFiles` | array | Files referenced in context |
| `images` | array | Attached images/screenshots |

---

## 2. Agent Transcripts

**Path:** `~/.cursor/projects/{project-name}/agent-transcripts/{uuid}.json`
**Format:** JSON array
**Total:** 68 files across 8 projects, 7.26 MB

```json
[
  {
    "role": "user",
    "text": "<user_query>\nSolve build errors please\n</user_query>"
  },
  {
    "role": "assistant",
    "text": "",
    "toolCalls": [
      {
        "toolName": "Read",
        "args": {"path": "/src/app.tsx"}
      }
    ]
  },
  {
    "role": "tool",
    "text": "",
    "toolResult": {
      "toolName": "Read",
      "result": "file contents..."
    }
  },
  {
    "role": "assistant",
    "text": "I can see the build error. Let me fix it...",
    "toolCalls": [
      {
        "toolName": "Edit",
        "args": {"path": "/src/app.tsx", "content": "..."}
      }
    ]
  }
]
```

| Role | Description |
|------|-------------|
| `user` | Human prompt (wrapped in `<user_query>` tags) |
| `assistant` | Claude/model response with optional `toolCalls` |
| `tool` | Tool execution result |

**Tool names observed:** `Read`, `Edit`, `Terminal`, `Grep`, `Glob`, `Write`

---

## 3. AI Code Tracking Database

**Path:** `~/.cursor/ai-tracking/ai-code-tracking.db`
**Format:** SQLite (26 MB)

### Tables

#### `ai_code_hashes` (220 rows)
```sql
CREATE TABLE ai_code_hashes (
    hash TEXT,
    source TEXT,           -- "tab" (autocomplete) or "composer" (agent/chat)
    fileExtension TEXT,    -- ".tsx", ".py", etc.
    fileName TEXT,
    requestId TEXT,
    conversationId TEXT,
    timestamp INTEGER,
    createdAt INTEGER,
    model TEXT             -- "default" or specific model name
);
```

#### `scored_commits` (773 rows)
```sql
CREATE TABLE scored_commits (
    commitHash TEXT,
    branchName TEXT,
    scoredAt INTEGER
);
```

#### `conversation_summaries` (0 rows — schema only)
```sql
CREATE TABLE conversation_summaries (
    conversationId TEXT,
    title TEXT,
    tldr TEXT,
    overview TEXT,
    summaryBullets TEXT,
    model TEXT,
    mode TEXT,
    updatedAt INTEGER
);
```

#### `tracking_state` (1 row)
```sql
CREATE TABLE tracking_state (key TEXT, value TEXT);
-- Contains: tracking_start_time
```

---

## 4. ItemTable Keys of Interest

| Key | Contents |
|-----|----------|
| `composer.planRegistry` | JSON: all plan files with IDs, names, URIs, timestamps |
| `aiCodeTracking.dailyStats.v1.5.{date}` | JSON: `{tabSuggestedLines, tabAcceptedLines, composerSuggestedLines, composerAcceptedLines}` |
| `cursor/memoriesEnabled` | boolean |
| `cursorAuth/*` | Auth tokens (DO NOT COLLECT) |

---

## 5. Plans

**Path:** `~/.cursor/plans/{slug}_{hash}.plan.md`
**Format:** Markdown with YAML frontmatter

```markdown
---
name: "Fix authentication flow"
overview: "Update the login component to use OAuth2"
todos:
  - title: "Update auth service"
    done: true
  - title: "Add token refresh"
    done: false
---

## Implementation Plan

### Phase 1: Auth Service
...
```

---

## 6. Collection Strategy for Cursor

### What to Collect

| Priority | Data | Path | Method |
|----------|------|------|--------|
| P0 | Agent transcripts | `.cursor/projects/*/agent-transcripts/*.json` | Read full files, track mtime |
| P0 | Conversation list | `state.vscdb` → `composerData:*` | SQLite query |
| P0 | Message bubbles | `state.vscdb` → `bubbleId:*` | SQLite query (batched) |
| P1 | AI code tracking | `.cursor/ai-tracking/ai-code-tracking.db` | SQLite query |
| P1 | Daily stats | `state.vscdb` → `aiCodeTracking.dailyStats.*` | SQLite query |
| P2 | Plans | `.cursor/plans/*.plan.md` | Read full files |
| Skip | Checkpoints | `checkpointId:*` | Too large, file snapshots |
| Skip | Agent blobs | `agentKv:blob:*` | Binary/protobuf, hard to parse |
| Skip | Auth tokens | `cursorAuth/*` | Sensitive |

### SQLite Reading

```sql
-- Get all conversations (composerData)
SELECT key, value FROM cursorDiskKV
WHERE key LIKE 'composerData:%'
ORDER BY json_extract(value, '$.createdAt') DESC;

-- Get messages for a conversation
SELECT key, value FROM cursorDiskKV
WHERE key LIKE 'bubbleId:{composerId}:%';

-- Get AI code tracking
SELECT * FROM ai_code_hashes
WHERE createdAt > ? ORDER BY createdAt;

-- Get daily stats
SELECT key, value FROM ItemTable
WHERE key LIKE 'aiCodeTracking.dailyStats%';
```

### Incremental Strategy

- Track last-seen `createdAt` timestamp for composerData entries
- For bubbleId, only fetch bubbles belonging to new/updated conversations
- For ai_code_hashes, track max `createdAt` value
- WAL mode means reads won't block Cursor's writes
