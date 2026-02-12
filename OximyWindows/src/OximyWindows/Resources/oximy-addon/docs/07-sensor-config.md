# Sensor Config Extension & Collection Architecture

## 1. Sensor Config Extension

Add a `localDataSources` field to the existing sensor-config API response. The sensor is a **dumb pipe** — config tells it **what files to read**, not how to parse them.

### Extended Sensor Config Response

```json
{
  "data": {
    "whitelistedDomains": ["...existing..."],
    "blacklistedWords": ["...existing..."],
    "passthroughDomains": ["...existing..."],
    "allowed_host_origins": ["...existing..."],
    "allowed_app_origins": {"...existing..."},
    "commands": {"...existing..."},
    "appConfig": {"...existing..."},

    "localDataSources": {
      "enabled": true,
      "poll_interval_seconds": 30,
      "upload_endpoint": "/api/v1/ingest/local-sessions",
      "max_batch_size_mb": 5,
      "max_events_per_batch": 200,

      "sources": [
        {
          "name": "claude_code",
          "enabled": true,
          "globs": [
            {
              "pattern": "~/.claude/projects/*/*.jsonl",
              "file_type": "session_transcript"
            },
            {
              "pattern": "~/.claude/projects/*/*/subagents/agent-*.jsonl",
              "file_type": "subagent_transcript"
            },
            {
              "pattern": "~/.claude/projects/*/sessions-index.json",
              "file_type": "session_index",
              "read_mode": "full"
            },
            {
              "pattern": "~/.claude/history.jsonl",
              "file_type": "prompt_history"
            },
            {
              "pattern": "~/.claude/stats-cache.json",
              "file_type": "stats",
              "read_mode": "full"
            }
          ],
          "detect_path": "~/.claude/projects/"
        },
        {
          "name": "cursor",
          "enabled": true,
          "globs": [
            {
              "pattern": "~/.cursor/projects/*/agent-transcripts/*.json",
              "file_type": "agent_transcript",
              "read_mode": "full"
            }
          ],
          "sqlite": [
            {
              "db_path": "~/Library/Application Support/Cursor/User/globalStorage/state.vscdb",
              "queries": [
                {
                  "file_type": "sqlite_composer",
                  "sql": "SELECT key, value, json_extract(value, '$.createdAt') as _ts FROM cursorDiskKV WHERE key LIKE 'composerData:%' AND json_extract(value, '$.createdAt') > ? ORDER BY json_extract(value, '$.createdAt')",
                  "incremental_field": "_ts"
                },
                {
                  "file_type": "sqlite_bubble",
                  "sql": "SELECT rowid, key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%' AND rowid > ? ORDER BY rowid",
                  "incremental_field": "rowid",
                  "depends_on": "sqlite_composer"
                }
              ]
            },
            {
              "db_path": "~/.cursor/ai-tracking/ai-code-tracking.db",
              "queries": [
                {
                  "file_type": "sqlite_code_tracking",
                  "sql": "SELECT * FROM ai_code_hashes WHERE createdAt > ?",
                  "incremental_field": "createdAt"
                }
              ]
            }
          ],
          "detect_path": "~/.cursor/"
        },
        {
          "name": "codex",
          "enabled": true,
          "globs": [
            {
              "pattern": "~/.codex/sessions/**/*.jsonl",
              "file_type": "session_transcript"
            },
            {
              "pattern": "~/.codex/history.jsonl",
              "file_type": "prompt_history"
            },
            {
              "pattern": "~/.codex/config.toml",
              "file_type": "config",
              "read_mode": "full"
            }
          ],
          "detect_path": "~/.codex/sessions/"
        },
        {
          "name": "openclaw",
          "enabled": true,
          "globs": [
            {
              "pattern": "~/.openclaw/agents/main/sessions/*.jsonl",
              "file_type": "session_transcript",
              "skip_patterns": ["*.deleted.*"]
            },
            {
              "pattern": "~/.openclaw/agents/main/sessions/sessions.json",
              "file_type": "session_index",
              "read_mode": "full"
            },
            {
              "pattern": "~/.openclaw/cron/runs/*.jsonl",
              "file_type": "cron_run"
            },
            {
              "pattern": "~/.openclaw/workspace/MEMORY.md",
              "file_type": "memory",
              "read_mode": "full"
            }
          ],
          "detect_path": "~/.openclaw/agents/"
        }
      ],

      "redact_patterns": [
        "sk-[a-zA-Z0-9]{20,}",
        "anthropic-[a-zA-Z0-9]{20,}",
        "ghp_[a-zA-Z0-9]{36,}",
        "Bearer\\s+[a-zA-Z0-9._-]{20,}",
        "ya29\\.[a-zA-Z0-9._-]+",
        "eyJ[a-zA-Z0-9._-]{40,}"
      ],
      "skip_files": [
        "*auth*", "*token*", "*credential*", "*secret*",
        "*.pem", "*.p12", "*.key"
      ],
      "max_event_size_bytes": 1048576
    }
  }
}
```

### Config Field Reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | false | Global kill switch |
| `poll_interval_seconds` | int | 30 | How often to scan for changes |
| `upload_endpoint` | string | — | API path for uploads |
| `max_batch_size_mb` | int | 5 | Max compressed batch size |
| `max_events_per_batch` | int | 200 | Max events per upload |
| `sources[].name` | string | — | Source identifier (matches `source` in envelope) |
| `sources[].enabled` | bool | true | Per-source toggle |
| `sources[].globs[]` | array | — | File patterns to scan |
| `sources[].globs[].pattern` | string | — | Glob pattern (`~` expanded at runtime) |
| `sources[].globs[].file_type` | string | — | Value set in envelope's `file_type` |
| `sources[].globs[].read_mode` | string | `incremental` | `incremental` (byte offset) or `full` (re-read entire file) |
| `sources[].globs[].skip_patterns` | array | [] | Sub-patterns to exclude |
| `sources[].sqlite[]` | array | — | SQLite databases to query |
| `sources[].sqlite[].db_path` | string | — | Path to SQLite file |
| `sources[].sqlite[].queries[]` | array | — | Queries to run |
| `sources[].sqlite[].queries[].sql` | string | — | SQL query (? = incremental marker) |
| `sources[].sqlite[].queries[].incremental_field` | string | null | Column for incremental reads |
| `sources[].detect_path` | string | — | Path to check if tool is installed |
| `redact_patterns` | array | — | Regex patterns to strip from raw data |
| `skip_files` | array | — | Filename patterns to never read |
| `max_event_size_bytes` | int | 1MB | Skip records larger than this |

---

## 2. Sensor Implementation (The Dumb Pipe)

### What the Sensor Does

```
Every poll_interval_seconds:
  1. For each enabled source:
     a. Check detect_path exists → skip if tool not installed
     b. Expand each glob pattern → list of files
     c. Filter out skip_files matches
     d. For each file:
        - Check mtime → skip if unchanged
        - If read_mode=incremental: seek to saved offset, read new lines
        - If read_mode=full: read entire file (only if mtime changed)
        - For each record (line for JSONL, row for SQLite):
          i.   Apply redact_patterns (regex on raw string)
          ii.  Skip if size > max_event_size_bytes
          iii. Wrap in envelope {event_id, source, file_type, raw, ...}
          iv.  Push to MemoryTraceBuffer
        - Save new offset/mtime to state file
  2. Buffer triggers upload when batch is ready
```

### Total Sensor Code (~100 lines of logic)

The sensor needs exactly these capabilities:
- `glob.glob()` with `~` expansion
- `open()` + `seek()` + `readline()` for JSONL
- `sqlite3.connect()` + `cursor.execute()` for SQLite
- `re.sub()` for redaction
- `json.loads()` to parse each line (only to wrap in envelope, not to understand it)
- `uuid7()` for event_id generation
- File mtime checking via `os.stat()`
- State persistence to `~/.oximy/local-scan-state.json`

**No tool-specific parsing logic. No schema knowledge. No normalization.**

### Integration Point

```python
# In addon.py — OximyAddon.configure()
local_config = sensor_config.get("localDataSources", {})
if local_config.get("enabled"):
    if not self._local_collector:
        self._local_collector = LocalDataCollector(
            config=local_config,
            buffer=self._buffer,       # existing MemoryTraceBuffer
            device_id=self._device_id
        )
        self._local_collector.start()
    else:
        self._local_collector.update_config(local_config)
```

---

## 3. Scan State Persistence

**Path:** `~/.oximy/local-scan-state.json`

```json
{
  "version": 1,
  "sources": {
    "claude_code": {
      "files": {
        "~/.claude/projects/-Users-.../abc.jsonl": {
          "offset": 456789,
          "mtime": 1768263841.305
        }
      }
    },
    "cursor": {
      "sqlite": {
        "state.vscdb": {
          "mtime": 1768263841.305,
          "incremental": {
            "sqlite_composer": {"last_value": 1762221631321},
            "sqlite_code_tracking": {"last_value": 1768000000000}
          }
        }
      },
      "files": {
        "~/.cursor/projects/.../transcript.json": {
          "mtime": 1768000000.000
        }
      }
    }
  }
}
```

### Edge Cases

| Situation | Handling |
|-----------|----------|
| File doesn't exist | Skip silently |
| File is empty | Skip silently |
| File is locked | Retry next cycle |
| File shrank (offset > size) | Reset offset to 0, re-read |
| JSON parse error on a line | Skip line, continue to next |
| SQLite locked | Retry with 5s timeout |
| SQLite corrupted | Log error, skip until mtime changes |
| Upload fails | Events return to buffer front (existing retry logic) |
| Device token expired | Stop collector (existing 401 handler) |
| Directory deleted mid-scan | Catch OSError, skip |
| Thread crash | Log, auto-restart after 60s |
| Config changes mid-run | `update_config()` hot-reloads |
| Single event > max_event_size | Skip with warning |

---

## 4. Detection & Heartbeat

The sensor reports which tools are installed via the existing heartbeat mechanism:

```json
{
  "installed_tools": {
    "claude_code": true,
    "cursor": true,
    "codex": true,
    "openclaw": false,
    "antigravity": false
  }
}
```

This lets the server:
- Know which parsers to expect data from
- Enable/disable sources per-device
- Dashboard shows which tools each user has

---

## 5. Phased Rollout

### Phase 1 — Claude Code (JSONL only)
- Implement `LocalDataCollector` (~100 lines)
- JSONL reader (incremental byte offset)
- `localDataSources` in sensor-config
- `POST /api/v1/ingest/local-sessions` endpoint
- Server parser for Claude Code
- **One macOS app update**

### Phase 2 — Cursor (adds SQLite)
- Add SQLite reader to collector
- Server parser for Cursor data
- **No app update** (SQLite reader deployed in Phase 1)

### Phase 3 — Codex + OpenClaw
- Server parsers only
- **No app update** (JSONL reader already deployed)

### After Phase 1 — All Future Changes Are Server-Side
- New tool? → Add `sources[]` entry to sensor-config + server parser
- New file type? → Add glob pattern to sensor-config + server parser
- Schema change? → Update server parser only
- Redaction rule? → Update `redact_patterns` in sensor-config
