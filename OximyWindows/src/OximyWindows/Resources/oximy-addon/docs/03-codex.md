# OpenAI Codex CLI — Data Format Specification

## Storage Location

```
~/.codex/
├── config.toml                     # User config (model, personality, trust levels)
├── version.json                    # Version tracking
├── .codex-global-state.json        # Desktop app UI state + prompt history
├── history.jsonl                   # Cross-session prompt index
├── models_cache.json               # Available models catalog (163 KB)
├── auth.json                       # OAuth tokens (SENSITIVE — DO NOT COLLECT)
├── sessions/                       # Session transcripts
│   └── YYYY/MM/DD/
│       └── rollout-{timestamp}-{uuid}.jsonl
├── skills/                         # Skill definitions
│   └── .system/                    # Built-in skills
├── sqlite/codex-dev.db             # Automations DB (currently empty)
├── log/codex-tui.log               # TUI debug logs
├── vendor_imports/skills/          # Curated skill marketplace (Git repo)
└── tmp/                            # Transient execution data
```

---

## 1. Session Transcripts

**Path:** `~/.codex/sessions/YYYY/MM/DD/rollout-{ISO-timestamp}-{UUIDv7}.jsonl`
**Format:** JSONL
**Naming:** `rollout-2026-02-07T17-55-35-{uuid}.jsonl`

### Record Types

Each line has a `type` field:

| Type | Description |
|------|-------------|
| `session_meta` | Session initialization (1 per file, always first line) |
| `turn_context` | Full context snapshot for each turn |
| `response_item` | Messages, tool calls, reasoning blocks |
| `event_msg` | Token counts, agent reasoning, abort events |

### 1.1 `type: "session_meta"`

```json
{
  "type": "session_meta",
  "timestamp": "2026-02-07T17:55:35.123Z",
  "session_meta": {
    "id": "019c3af6-...",
    "cwd": "/Users/name/project",
    "originator": "Codex Desktop",
    "cli_version": "0.98.0",
    "source": "vscode",
    "model_provider": "openai",
    "base_instructions": "Full system prompt text... (~5KB)",
    "git": {}
  }
}
```

| Field | Description |
|-------|-------------|
| `originator` | `"codex_cli_rs"` (CLI) or `"Codex Desktop"` (Electron) |
| `cli_version` | e.g., `"0.42.0"`, `"0.98.0"` |
| `source` | `"vscode"` when launched from desktop app |
| `base_instructions` | Complete system prompt (very large, ~5KB) |

### 1.2 `type: "turn_context"`

Full snapshot of config for each conversational turn:

```json
{
  "type": "turn_context",
  "timestamp": "...",
  "turn_context": {
    "cwd": "/Users/name/project",
    "approval_policy": "on-request",
    "sandbox_policy": {
      "mode": "sandbox",
      "writable_roots": ["/path"],
      "network_access": true
    },
    "model": "gpt-5-codex",
    "personality": "pragmatic",
    "collaboration_mode": {
      "name": "Default",
      "settings": {},
      "developer_instructions": "..."
    },
    "effort": "medium",
    "summary": "auto",
    "truncation_policy": {"mode": "tokens", "limit": 10000},
    "user_instructions": "...",
    "developer_instructions": "..."
  }
}
```

### 1.3 `type: "response_item"` — Messages & Tool Calls

**User message:**
```json
{
  "type": "response_item",
  "timestamp": "...",
  "response_item": {
    "type": "message",
    "role": "user",
    "id": "msg_...",
    "content": [
      {"type": "input_text", "text": "Make a simple game for me"}
    ]
  }
}
```

**Assistant text response:**
```json
{
  "type": "response_item",
  "timestamp": "...",
  "response_item": {
    "type": "message",
    "role": "assistant",
    "id": "msg_...",
    "content": [
      {"type": "output_text", "text": "I'll create a simple game..."}
    ]
  }
}
```

**Reasoning block (chain-of-thought):**
```json
{
  "type": "response_item",
  "timestamp": "...",
  "response_item": {
    "type": "reasoning",
    "id": "rs_...",
    "summary": [
      {"type": "summary_text", "text": "**Planning game implementation**"}
    ],
    "encrypted_content": "base64-encrypted-reasoning..."
  }
}
```

**NOTE:** `encrypted_content` contains the actual reasoning but is **encrypted** and not readable.

**Function call (tool use):**
```json
{
  "type": "response_item",
  "timestamp": "...",
  "response_item": {
    "type": "function_call",
    "id": "fc_...",
    "call_id": "call_...",
    "name": "shell",
    "arguments": "{\"command\":[\"npm\",\"init\",\"-y\"],\"workdir\":\"/path\"}",
    "status": "completed"
  }
}
```

**Function call output:**
```json
{
  "type": "response_item",
  "timestamp": "...",
  "response_item": {
    "type": "function_call_output",
    "call_id": "call_...",
    "output": "{\"stdout\":\"...\",\"stderr\":\"\",\"exit_code\":0}"
  }
}
```

#### Tool/Function Names

| Function | Description |
|----------|-------------|
| `shell` | Execute shell commands (args: `command[]`, `workdir`) |
| `apply_patch` | Apply code diffs (args: `patch` in unified diff format) |
| `update_plan` | Update the task plan (args: plan text) |
| `exec_command` | Execute a command with specific permissions |

### 1.4 `type: "event_msg"` — Events

**Token count:**
```json
{
  "type": "event_msg",
  "timestamp": "...",
  "event_msg": {
    "type": "token_count",
    "input_tokens": 5234,
    "input_tokens_cached": 4800,
    "output_tokens": 342,
    "reasoning_output_tokens": 128,
    "rate_limit_info": {
      "primary_window": {"remaining": 95, "limit": 100, "reset_seconds": 45},
      "secondary_window": {"remaining": 980, "limit": 1000, "reset_seconds": 3600},
      "credit_balance": 150.42
    }
  }
}
```

**Agent reasoning summary:**
```json
{
  "type": "event_msg",
  "event_msg": {
    "type": "agent_reasoning",
    "text": "**Planning AGENTS.md generation**"
  }
}
```

**Turn aborted:**
```json
{
  "type": "event_msg",
  "event_msg": {
    "type": "turn_aborted",
    "reason": "interrupted"
  }
}
```

---

## 2. Global Prompt History

**Path:** `~/.codex/history.jsonl`
**Format:** JSONL

```json
{"session_id": "019c3af6-...", "ts": 1759522892, "text": "Generate a file named AGENTS.md"}
```

Flat index of all prompts across sessions. `session_id` links to session JSONL files.

---

## 3. Config

**Path:** `~/.codex/config.toml`
**Format:** TOML

```toml
model = "gpt-5-codex"
personality = "pragmatic"

[projects."/Users/name/Desktop/project"]
trust_level = "trusted"
```

---

## 4. Global State (Desktop App)

**Path:** `~/.codex/.codex-global-state.json`
**Format:** JSON

```json
{
  "electron-saved-workspace-roots": ["/Users/name/Documents/project"],
  "electron-persisted-atom-state": {
    "prompt-history": ["Which folder are we in?", "Make a game please"],
    "codexCloudAccess": "enabled_needs_setup"
  },
  "thread-titles": {
    "titles": {"019c3af6-...": "Locate current working folder"},
    "order": ["019c3af6-..."]
  }
}
```

---

## 5. Collection Strategy for Codex

### What to Collect

| Priority | Data | Path | Method |
|----------|------|------|--------|
| P0 | Session transcripts | `sessions/YYYY/MM/DD/*.jsonl` | Incremental read (byte offset) |
| P1 | Prompt history | `history.jsonl` | Incremental read |
| P2 | Config | `config.toml` | Read full, track mtime |
| P2 | Global state | `.codex-global-state.json` | Read full, track mtime |
| Skip | Models cache | `models_cache.json` | Static catalog, not user data |
| Skip | Auth | `auth.json` | Sensitive |
| Skip | Skills | `skills/`, `vendor_imports/` | Static definitions |

### Discovery

Sessions are date-partitioned: `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`
Glob pattern: `~/.codex/sessions/**/*.jsonl`

### Incremental Reading

Same byte-offset approach as Claude Code — JSONL files are append-only.
