# Windsurf (Codeium Cascade) — Data Format Specification

## Overview

Windsurf is a **Codeium-built VS Code fork** with Cascade AI integration. Cascade conversations are stored as **AES-GCM encrypted protobuf** files on disk — NOT accessible without the encryption key. However, the running language server exposes a **Connect-RPC API on localhost** that returns full conversation data in JSON.

**Priority: P1 (High)** — Requires Windsurf to be running (language server must be active).

## Architecture

```
Windsurf (Electron) ──Connect-RPC──▶ language_server_macos_arm (Go, localhost:{random_port})
                                        │
                                        ├──▶ ~/.codeium/windsurf/cascade/*.pb  (encrypted, AES-GCM)
                                        ├──▶ server.self-serve.windsurf.com    (gRPC, cert-pinned)
                                        └──▶ inference.codeium.com             (model inference)
```

The language server is a Go binary at:
```
/Applications/Windsurf.app/Contents/Resources/app/extensions/windsurf/bin/language_server_macos_arm
```

## Storage Locations

```
~/.codeium/windsurf/                             # Codeium integration data
├── cascade/                                     # Cascade conversations (ENCRYPTED)
│   ├── {uuid}.pb                                # AES-GCM encrypted protobuf per conversation
│   └── ...
├── implicit/                                    # Implicit context (ENCRYPTED)
│   └── {uuid}.pb
├── user_settings.pb                             # Plain protobuf (NOT encrypted)
├── installation_id                              # UUID string
├── brain/                                       # Cascade memories
├── code_tracker/                                # Code tracking
├── codemaps/                                    # Code map index
├── database/                                    # SQLite embedding DB
├── memories/                                    # User memories
└── recipes/                                     # Custom recipes

~/.windsurf/                                     # CLI config + extensions
├── argv.json                                    # CLI arguments
└── extensions/                                  # VS Code extensions

~/Library/Application Support/Windsurf/          # Electron app data
├── User/
│   ├── globalStorage/state.vscdb                # SQLite key-value store
│   ├── workspaceStorage/{hash}/state.vscdb      # Per-workspace state
│   └── settings.json                            # Editor settings
└── logs/                                        # Application logs
```

## Why Network Capture Doesn't Work

Windsurf's Cascade uses **gRPC with certificate pinning** to communicate with `server.self-serve.windsurf.com`. The `language_server_macos_arm` binary connects through the proxy but the TLS handshake fails silently because the native Go gRPC client pins certificates. Zero API traffic is captured.

The API server URL is configured in the vscdb:
```json
// key: codeium.windsurf
{"apiServerUrl": "https://server.self-serve.windsurf.com"}
```

## Collection Method: Language Server RPC API

### Discovery

1. **Find the language server process:**
   ```bash
   ps aux | grep "language_server_macos_arm.*--ide_name windsurf"
   ```

2. **Extract from command-line arguments:**
   - `--csrf_token {token}` — Required for authentication
   - `--extension_server_port {port}` — Extension server port (NOT the LS port)
   - `--codeium_dir .codeium/windsurf` — Data directory
   - `--workspace_id {id}` — Active workspace

3. **Find the language server listening port:**
   ```bash
   lsof -i -P -n -p {PID} | grep LISTEN
   ```
   The LS typically listens on 2-3 ports. The **lowest port** is the main RPC endpoint.

### Authentication

All requests require the CSRF token as a header:
```
x-codeium-csrf-token: {csrf_token_from_cmdline}
```

### API Endpoints

Base URL: `http://127.0.0.1:{ls_port}`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/exa.language_server_pb.LanguageServerService/GetAllCascadeTrajectories` | List all conversations with summaries |
| POST | `/exa.language_server_pb.LanguageServerService/GetCascadeTrajectory` | Get full conversation with all steps |
| POST | `/exa.language_server_pb.LanguageServerService/GetCascadeMemories` | Get cascade memories |
| POST | `/exa.language_server_pb.LanguageServerService/GetConversationTags` | Get conversation tags |
| POST | `/exa.language_server_pb.LanguageServerService/GetCascadeAnalytics` | Get usage analytics |

All requests use `Content-Type: application/json` with an empty body `{}` or specific parameters.

---

## Data Formats

### GetAllCascadeTrajectories Response

```json
{
  "trajectorySummaries": {
    "{cascadeId}": {
      "summary": "Initiate Coding Task",
      "stepCount": 4,
      "lastModifiedTime": "2026-02-09T00:56:47.792166Z",
      "trajectoryId": "{uuid}",
      "status": "CASCADE_RUN_STATUS_IDLE",
      "createdTime": "2026-02-09T00:56:46.225925Z",
      "workspaces": [{
        "workspaceFolderAbsoluteUri": "file:///Users/.../project",
        "gitRootAbsoluteUri": "file:///Users/.../project",
        "repository": {
          "computedName": "OrgName/repo",
          "gitOriginUrl": "git@github.com:OrgName/repo.git"
        },
        "branchName": "main"
      }],
      "lastUserInputTime": "2026-02-09T00:56:46.267740Z",
      "trajectoryType": "CORTEX_TRAJECTORY_TYPE_CASCADE",
      "lastGeneratorModelUid": "MODEL_SWE_1_5_SLOW"
    }
  }
}
```

### GetCascadeTrajectory Request/Response

**Request:**
```json
{"cascadeId": "{cascadeId}"}
```

**Response — Trajectory Steps:**

Each conversation is a sequence of typed steps:

#### CORTEX_STEP_TYPE_USER_INPUT
```json
{
  "type": "CORTEX_STEP_TYPE_USER_INPUT",
  "status": "CORTEX_STEP_STATUS_DONE",
  "metadata": {
    "createdAt": "2026-02-09T00:56:46.267740Z",
    "source": "CORTEX_STEP_SOURCE_USER_EXPLICIT",
    "requestedModelUid": "MODEL_SWE_1_5_SLOW",
    "executionId": "{uuid}",
    "plannerMode": "CONVERSATIONAL_PLANNER_MODE_DEFAULT"
  },
  "userInput": {
    "userResponse": "Hey Windsurf!",
    "items": [{"text": "Hey Windsurf!"}],
    "activeUserState": {}
  }
}
```

#### CORTEX_STEP_TYPE_PLANNER_RESPONSE
```json
{
  "type": "CORTEX_STEP_TYPE_PLANNER_RESPONSE",
  "status": "CORTEX_STEP_STATUS_DONE",
  "metadata": {
    "createdAt": "2026-02-09T00:56:46.514067Z",
    "generatorModelUid": "MODEL_SWE_1_5_SLOW",
    "requestedModelUid": "MODEL_SWE_1_5_SLOW",
    "executionId": "{uuid}",
    "requestId": "{uuid}",
    "cumulativeTokensAtStep": "9984"
  },
  "plannerResponse": {
    "response": "\nHello! I'm here to help...",
    "modifiedResponse": "Hello! I'm here to help...",
    "messageId": "bot-{requestId}",
    "thinkingDuration": "0.000268292s"
  }
}
```

#### CORTEX_STEP_TYPE_CHECKPOINT
```json
{
  "type": "CORTEX_STEP_TYPE_CHECKPOINT",
  "metadata": {
    "modelUsage": {
      "model": "MODEL_GOOGLE_GEMINI_2_5_FLASH",
      "modelUid": "MODEL_GOOGLE_GEMINI_2_5_FLASH",
      "inputTokens": "1696",
      "outputTokens": "59",
      "apiProvider": "API_PROVIDER_GOOGLE_GENAI_VERTEX"
    },
    "modelCost": 0.00065630005
  },
  "checkpoint": {
    "userIntent": "Initiate Coding Task\nThe user wants me to...",
    "intentOnly": true
  }
}
```

#### Other Step Types
- `CORTEX_STEP_TYPE_RETRIEVE_MEMORY` — System retrieves cascade memories
- `CORTEX_STEP_TYPE_TOOL_CALL` — Tool execution (file edits, terminal commands, search)
- `CORTEX_STEP_TYPE_TOOL_RESULT` — Tool execution result

### Step Type → Interaction Mapping

| Cascade Step Type | Oximy Interaction Type | Notes |
|---|---|---|
| `CORTEX_STEP_TYPE_USER_INPUT` | `input` | `userInput.userResponse` = user message |
| `CORTEX_STEP_TYPE_PLANNER_RESPONSE` | `output` | `plannerResponse.modifiedResponse` = AI response |
| `CORTEX_STEP_TYPE_CHECKPOINT` | `metadata` | Token usage, cost, intent summary |
| `CORTEX_STEP_TYPE_TOOL_CALL` | `tool_call` | Tool name + arguments |
| `CORTEX_STEP_TYPE_TOOL_RESULT` | `tool_result` | Tool output |

### Model UID Mapping

| Windsurf Model UID | Actual Model |
|---|---|
| `MODEL_SWE_1_5_SLOW` | Cascade default (routes to various backends) |
| `MODEL_GOOGLE_GEMINI_2_5_FLASH` | Google Gemini 2.5 Flash |
| `MODEL_CHAT_GPT_5_LOW` | GPT-5 |
| `MODEL_CODEMAP_MEDIUM` | Code map model |
| `MODEL_QUERY_11791` | MQuery search model |

---

## Collection Strategy

### Recommended: LocalDataCollector RPC Polling

Since the `.pb` files are encrypted and network traffic is cert-pinned, the **only viable approach** is polling the language server's local RPC API.

**Detection:**
```python
# Check if Windsurf LS is running
ps_output = subprocess.run(["ps", "aux"], capture_output=True, text=True).stdout
is_running = "language_server_macos_arm" in ps_output and "--ide_name windsurf" in ps_output
```

**Polling approach:**
1. On startup and every `poll_interval_seconds`, check if the LS is running
2. Extract CSRF token and port from the process command line
3. Call `GetAllCascadeTrajectories` to get summaries with `lastModifiedTime`
4. For each trajectory modified since last poll, call `GetCascadeTrajectory`
5. Wrap each new/modified step as a `local_session` envelope and upload

**Envelope format:**
```json
{
  "event_id": "{uuid7}",
  "type": "local_session",
  "source": "windsurf",
  "timestamp": "{step.metadata.createdAt}",
  "source_file": "rpc://127.0.0.1:{port}/cascade/{cascadeId}",
  "raw": { /* full step JSON from GetCascadeTrajectory */ }
}
```

### Sensor Config Source Definition

```json
{
  "name": "windsurf",
  "enabled": true,
  "rpc": {
    "process_pattern": "language_server_macos_arm.*--ide_name windsurf",
    "csrf_token_arg": "--csrf_token",
    "service": "exa.language_server_pb.LanguageServerService",
    "list_method": "GetAllCascadeTrajectories",
    "get_method": "GetCascadeTrajectory",
    "id_field": "cascadeId",
    "summary_field": "trajectorySummaries",
    "timestamp_field": "lastModifiedTime"
  },
  "detect_path": "~/.codeium/windsurf/"
}
```

### Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| Requires Windsurf running | Cannot backfill when app is closed | Collect while running, cache last state |
| CSRF token changes on restart | Must re-discover on each LS restart | Poll process table periodically |
| Port is random | Must discover via lsof each time | Cache port, re-discover on connection error |
| Encrypted .pb files | Cannot read offline | Accept this limitation; RPC-only approach |
| One workspace per LS | Multi-workspace needs multiple LS processes | Scan all matching processes |

---

## Encryption Details (For Reference)

The `.pb` files use **AES-GCM** encryption via `github.com/Exafunction/Exafunction/exa/cortex/proto_saver.WithEncryptionKey`. The key is passed during language server initialization (`initServers.WithEncryptionKey`). The key source is internal to the Go binary and not exposed via command-line arguments or local files. Entropy of encrypted files is ~8.0 bits/byte (indistinguishable from random).

Non-encrypted protobuf files (`user_settings.pb`) have entropy ~6.3 bits/byte and decode normally with `protoc --decode_raw`.

## Quick Reference

| Item | Value |
|---|---|
| macOS Bundle ID | `com.exafunction.windsurf` (or `com.codeium.windsurf`) |
| Windows App ID | `Codeium.Windsurf` |
| Data Directory | `~/.codeium/windsurf/` |
| App Support | `~/Library/Application Support/Windsurf/` |
| API Server | `server.self-serve.windsurf.com` |
| Inference Server | `inference.codeium.com` |
| LS Binary | `Windsurf.app/.../extensions/windsurf/bin/language_server_macos_arm` |
| Auth Header | `x-codeium-csrf-token` |
| RPC Protocol | Connect-RPC (JSON over HTTP POST) |
| Cascade Storage | Encrypted AES-GCM protobuf (`.pb`) |
