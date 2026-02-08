# API Parsing Guide — Server-Side Processing

## Codebase Context

The API lives at `primary-oximy/api/` — a **Turborepo monorepo** with:

```
apps/
  api/          ← Express HTTP server (@oximy/api)
  worker/       ← BullMQ worker process (@oximy/worker)
packages/
  db/           ← MongoDB models + ClickHouse schemas + Redis (@oximy/db)
  queue/        ← BullMQ queue definitions (@oximy/queue)
  services/     ← Shared services (policy matcher, alerts, etc.)
  types/        ← Zod schemas + TypeScript interfaces (@oximy/types)
  utils/        ← Logger, encryption, error classes
```

**Stack:** TypeScript, Express, MongoDB (Mongoose), ClickHouse, BullMQ + Redis, Clerk (dashboard) + device tokens (sensors).

---

## How Network Traces Already Work (Follow This Pattern)

The existing `POST /api/v1/ingest/network-traces` pipeline:

```
Sensor → POST gzipped JSONL → authenticateDevice middleware
  → Read raw body (50MB limit)
  → Base64-encode gzipped payload
  → enqueueNetworkTraces() → BullMQ "network-traces" queue
  → Return 202 Accepted

Worker picks up job:
  → Decompress, split lines, parse JSONL
  → For each trace: resolve device → buildContext → parserRegistry.parse()
  → Batch insert to ClickHouse (network_traces, parsed_events, parse_failures)
  → Queue for analytics-enrichment (LLM classification)
```

**Key files in the existing pipeline:**

| File | What It Does |
|------|-------------|
| `apps/api/src/routes/ingest.routes.ts` | Route definition, body handling, queue dispatch |
| `packages/queue/src/queues.ts` | Queue definitions (6 queues), job data types, enqueue helpers |
| `apps/worker/src/processors/network-trace.processor.ts` | **The big one** (~1189 lines) — decompression, parsing, ClickHouse batch insert |
| `apps/worker/src/parsers/index.ts` | `ParserRegistry` — routes traces to app-specific parsers |
| `apps/worker/src/parsers/base.parser.ts` | Abstract base parser with event building helpers |
| `apps/worker/src/parsers/types.ts` | `ParseContext`, `ParsedEvent`, `ParseResult`, `IParser` |
| `packages/db/src/clickhouse/schemas.ts` | ClickHouse table definitions (`network_traces`, `parsed_events`, etc.) |
| `apps/api/src/routes/device.routes.ts` | `authenticateDevice` middleware (Bearer `dev_tk_xxx`) |
| `apps/api/src/routes/sensor-config.routes.ts` | `GET /api/v1/sensor-config` — serves config to sensors |

---

## What Needs to Be Built

### Files to Create/Modify

| # | File | Action | Description |
|---|------|--------|-------------|
| 1 | `apps/api/src/routes/ingest.routes.ts` | **Modify** | Add `POST /api/v1/ingest/local-sessions` route |
| 2 | `packages/queue/src/queues.ts` | **Modify** | Add `localSessionsQueue`, `LocalSessionJobData`, `enqueueLocalSessions()` |
| 3 | `packages/queue/src/index.ts` | **Modify** | Export new queue |
| 4 | `apps/worker/src/processors/local-session.processor.ts` | **Create** | New processor with source-specific parsers |
| 5 | `apps/worker/src/index.ts` | **Modify** | Register `localSessionWorker` |
| 6 | `packages/db/src/clickhouse/schemas.ts` | **Modify** | Add `local_session_events` table (or extend `parsed_events`) |
| 7 | `apps/api/src/routes/sensor-config.routes.ts` | **Modify** | Add `localDataSources` to response |

---

## 1. Ingest Route

**File:** `apps/api/src/routes/ingest.routes.ts`

Follow the exact same pattern as network-traces:

```typescript
// Add alongside existing network-traces route
router.post(
  "/local-sessions",
  authenticateDevice,
  async (req: AuthenticatedDeviceRequest, res) => {
    try {
      const chunks: Buffer[] = [];
      req.on("data", (chunk) => chunks.push(chunk));
      req.on("end", async () => {
        const raw = Buffer.concat(chunks);

        // Decompress if gzipped
        const isGzip = req.headers["content-encoding"] === "gzip";
        const data = isGzip ? zlib.gunzipSync(raw) : raw;
        const lines = data.toString("utf-8").split("\n").filter(Boolean);

        // Re-compress for queue storage efficiency
        const compressed = zlib.gzipSync(data);
        const payload = compressed.toString("base64");

        await enqueueLocalSessions({
          payload,
          count: lines.length,
          deviceContext: {
            deviceId: req.device._id.toString(),
            workspaceId: req.device.workspaceId.toString(),
            ownerId: req.device.employeeId?.toString() || req.device.ownerId.toString(),
          },
        });

        res.status(202).json({ status: "accepted", count: lines.length });
      });
    } catch (err) {
      logger.error("local-sessions ingest error", err);
      res.status(500).json({ error: "Internal error" });
    }
  }
);
```

---

## 2. Queue Definition

**File:** `packages/queue/src/queues.ts`

```typescript
// Add alongside existing queue definitions
export interface LocalSessionJobData {
  payload: string;        // base64-encoded gzipped JSONL
  count: number;
  deviceContext: {
    deviceId: string;
    workspaceId: string;
    ownerId: string;
  };
}

export const localSessionsQueue = new Queue<LocalSessionJobData>(
  "local-sessions",
  {
    connection: redis,
    defaultJobOptions: {
      attempts: 3,
      backoff: { type: "exponential", delay: 1000 },
      removeOnComplete: { count: 1000 },
      removeOnFail: { count: 5000 },
    },
  }
);

export async function enqueueLocalSessions(data: LocalSessionJobData) {
  await localSessionsQueue.add("process", data);
}
```

---

## 3. Processor (The Main Parsing Logic)

**File:** `apps/worker/src/processors/local-session.processor.ts`

This is where all source-specific parsing lives. Follow the `network-trace.processor.ts` pattern but simpler — no parser registry needed initially.

```typescript
import { Worker, Job } from "bullmq";
import { redis } from "@oximy/queue";
import { clickhouse } from "@oximy/db";
import { logger } from "@oximy/utils";
import zlib from "zlib";

interface LocalSessionEnvelope {
  event_id: string;
  timestamp: string;
  type: "local_session";
  device_id: string;
  source: "claude_code" | "cursor" | "codex" | "openclaw";
  source_file: string;
  file_type: string;
  project_key?: string;
  session_id?: string;
  line_number?: number;
  raw: Record<string, unknown>;
}

// ── Parser routing ──────────────────────────────────

function parseEvent(envelope: LocalSessionEnvelope, workspaceId: string) {
  const { source, file_type, raw } = envelope;

  switch (source) {
    case "claude_code":
      return parseClaudeCode(envelope, workspaceId);
    case "cursor":
      return parseCursor(envelope, workspaceId);
    case "codex":
      return parseCodex(envelope, workspaceId);
    case "openclaw":
      return parseOpenClaw(envelope, workspaceId);
    default:
      logger.warn(`Unknown local session source: ${source}`);
      return null;
  }
}
```

### Claude Code Parser

Reference: [01-claude-code.md](01-claude-code.md)

```typescript
function parseClaudeCode(env: LocalSessionEnvelope, workspaceId: string) {
  const raw = env.raw as any;

  // Route by raw.type field (see 01-claude-code.md §2)
  switch (raw.type) {
    case "user":
      return parseCCUser(env, raw, workspaceId);
    case "assistant":
      return parseCCAssistant(env, raw, workspaceId);
    case "system":
      return parseCCSystem(env, raw, workspaceId);
    case "queue-operation":
    case "file-history-snapshot":
      return null; // Low-value, skip
    default:
      return null;
  }
}

function parseCCUser(env: LocalSessionEnvelope, raw: any, workspaceId: string) {
  const msg = raw.message;
  const isToolResult = Array.isArray(msg?.content)
    && msg.content[0]?.type === "tool_result";

  return {
    event_id: env.event_id,
    workspace_id: workspaceId,
    device_id: env.device_id,
    source: "claude_code",
    session_id: env.session_id ?? raw.sessionId,
    record_type: isToolResult ? "tool_result" : "user_message",
    role: "user",
    message_id: raw.uuid,
    parent_id: raw.parentUuid,
    timestamp: env.timestamp,

    // Content
    content_text: typeof msg?.content === "string" ? msg.content : null,

    // Tool result details (see 01-claude-code.md §2.1 toolUseResult schemas)
    tool_name: isToolResult ? extractToolName(raw) : null,
    tool_result_meta: raw.toolUseResult
      ? JSON.stringify(summarizeToolResult(raw.toolUseResult))
      : null,
    source_tool_id: raw.sourceToolAssistantUUID,

    // Context
    model: null,
    provider: "anthropic",
    cwd: raw.cwd,
    git_branch: raw.gitBranch,
    tool_version: raw.version,
    is_subagent: raw.isSidechain ?? false,
    subagent_id: raw.agentId ?? null,

    // Usage (user messages don't have token data)
    input_tokens: 0,
    output_tokens: 0,
    cache_read_tokens: 0,
    cache_write_tokens: 0,

    // Raw preserved
    raw_json: JSON.stringify(raw),
  };
}

function parseCCAssistant(env: LocalSessionEnvelope, raw: any, workspaceId: string) {
  const msg = raw.message;

  // Extract content blocks (see 01-claude-code.md §2.2)
  // IMPORTANT: Multiple JSONL lines share same requestId — each has 1 content block
  const blocks = msg?.content ?? [];
  const textBlocks = blocks.filter((b: any) => b.type === "text");
  const toolBlocks = blocks.filter((b: any) => b.type === "tool_use");

  return {
    event_id: env.event_id,
    workspace_id: workspaceId,
    device_id: env.device_id,
    source: "claude_code",
    session_id: env.session_id ?? raw.sessionId,
    record_type: toolBlocks.length > 0 ? "tool_call" : "assistant_message",
    role: "assistant",
    message_id: raw.uuid,
    parent_id: raw.parentUuid,
    timestamp: env.timestamp,

    // Content
    content_text: textBlocks.map((b: any) => b.text).join("") || null,

    // Tool call details
    tool_name: toolBlocks[0]?.name ?? null,
    tool_input: toolBlocks[0] ? JSON.stringify({
      name: toolBlocks[0].name,
      id: toolBlocks[0].id,
      // For Edit: contains file_path, old_string, new_string (file diffs!)
      // For Write: contains file_path, content
      // For Bash: contains command
      // For Task: contains subagent_type, prompt
      input: toolBlocks[0].input,
    }) : null,

    // Model & usage
    model: msg?.model,
    provider: "anthropic",
    stop_reason: msg?.stop_reason,
    request_id: raw.requestId,
    input_tokens: msg?.usage?.input_tokens ?? 0,
    output_tokens: msg?.usage?.output_tokens ?? 0,
    cache_read_tokens: msg?.usage?.cache_read_input_tokens ?? 0,
    cache_write_tokens: msg?.usage?.cache_creation_input_tokens ?? 0,

    // Context
    cwd: raw.cwd,
    git_branch: raw.gitBranch,
    tool_version: raw.version,
    is_subagent: raw.isSidechain ?? false,
    subagent_id: raw.agentId ?? null,

    raw_json: JSON.stringify(raw),
  };
}

// Summarize toolUseResult without large content (see 01-claude-code.md §2.1)
function summarizeToolResult(tur: any) {
  if (typeof tur === "string") return { type: "error", message: tur };
  if ("stdout" in tur) return { type: "bash", interrupted: tur.interrupted, has_stderr: !!tur.stderr };
  if ("file" in tur) return { type: "file_read", path: tur.file?.filePath, lines: tur.file?.numLines };
  if ("filenames" in tur && "durationMs" in tur) return { type: "glob", count: tur.numFiles };
  if ("mode" in tur && "numFiles" in tur) return { type: "grep", count: tur.numFiles };
  if ("agentId" in tur) return {
    type: "subagent", agent_id: tur.agentId, status: tur.status,
    duration_ms: tur.totalDurationMs, tokens: tur.totalTokens, tool_uses: tur.totalToolUseCount
  };
  if (tur.type === "create" || tur.type === "update") return { type: "file_write", write_type: tur.type };
  return { type: "unknown" };
}

function extractToolName(raw: any): string | null {
  // tool_result messages don't directly carry the tool name
  // The tool name is in the assistant message that invoked it
  // We can infer from toolUseResult shape
  const tur = raw.toolUseResult;
  if (!tur) return null;
  if (typeof tur === "string") return null;
  if ("stdout" in tur) return "Bash";
  if ("file" in tur) return "Read";
  if ("filenames" in tur && "durationMs" in tur) return "Glob";
  if ("mode" in tur) return "Grep";
  if ("agentId" in tur) return "Task";
  if (tur.type === "create") return "Write";
  if (tur.type === "update") return "Edit";
  return null;
}
```

### Cursor Parser

Reference: [02-cursor.md](02-cursor.md)

```typescript
function parseCursor(env: LocalSessionEnvelope, workspaceId: string) {
  const raw = env.raw as any;

  switch (env.file_type) {
    case "agent_transcript":
      return parseCursorTranscript(env, raw, workspaceId);
    case "sqlite_composer":
      return parseCursorComposer(env, raw, workspaceId);
    case "sqlite_bubble":
      return parseCursorBubble(env, raw, workspaceId);
    case "sqlite_code_tracking":
      return parseCursorTracking(env, raw, workspaceId);
    case "sqlite_daily_stats":
      return parseCursorDailyStats(env, raw, workspaceId);
    default:
      return null;
  }
}

function parseCursorComposer(env: LocalSessionEnvelope, raw: any, workspaceId: string) {
  // raw = { key: "composerData:uuid", value: "JSON string" }
  const data = JSON.parse(raw.value);
  return {
    event_id: env.event_id,
    workspace_id: workspaceId,
    device_id: env.device_id,
    source: "cursor",
    session_id: data.composerId,
    record_type: "session_meta",
    role: null,
    timestamp: new Date(data.createdAt).toISOString(),
    content_text: null,
    model: data.modelConfig?.modelName,
    provider: "cursor",
    // Conversation metadata
    metadata: JSON.stringify({
      mode: data.unifiedMode,         // "chat", "composer", "agent"
      message_count: data.fullConversationHeadersOnly?.length ?? 0,
      lines_added: data.totalLinesAdded,
      lines_removed: data.totalLinesRemoved,
      is_archived: data.isArchived,
      message_refs: data.fullConversationHeadersOnly?.map((h: any) => ({
        bubble_id: h.bubbleId,
        type: h.type,  // 1=user, 2=assistant
      })),
    }),
    raw_json: JSON.stringify(raw),
  };
}

function parseCursorBubble(env: LocalSessionEnvelope, raw: any, workspaceId: string) {
  // raw = { key: "bubbleId:composerId:bubbleId", value: "JSON string" }
  const data = JSON.parse(raw.value);
  const [_, composerId, bubbleId] = raw.key.split(":");
  return {
    event_id: env.event_id,
    workspace_id: workspaceId,
    device_id: env.device_id,
    source: "cursor",
    session_id: composerId,
    record_type: data.type === 1 ? "user_message" : "assistant_message",
    role: data.type === 1 ? "user" : "assistant",
    message_id: bubbleId,
    timestamp: env.timestamp,
    content_text: data.text,
    tool_name: data.toolResults?.[0]?.toolName ?? null,
    metadata: JSON.stringify({
      code_blocks: data.suggestedCodeBlocks?.map((cb: any) => ({
        file: cb.filePath, lang: cb.language, lines: `${cb.startLine}-${cb.endLine}`
      })),
      diffs: data.assistantSuggestedDiffs?.map((d: any) => ({ file: d.filePath })),
      relevant_files: data.relevantFiles,
      images_count: data.images?.length ?? 0,
    }),
    raw_json: JSON.stringify(raw),
  };
}

function parseCursorTranscript(env: LocalSessionEnvelope, raw: any, workspaceId: string) {
  // raw = entire JSON array from agent-transcripts/{uuid}.json
  // Emit one record per message in the transcript
  if (!Array.isArray(raw)) return null;
  return raw.map((msg: any, idx: number) => ({
    event_id: `${env.event_id}-${idx}`,
    workspace_id: workspaceId,
    device_id: env.device_id,
    source: "cursor",
    session_id: env.session_id,
    record_type: msg.role === "tool" ? "tool_result" : `${msg.role}_message`,
    role: msg.role,
    message_id: `${env.session_id}-${idx}`,
    timestamp: env.timestamp,
    content_text: msg.text?.replace(/<\/?user_query>\n?/g, "") || null,
    tool_name: msg.toolCalls?.[0]?.toolName ?? msg.toolResult?.toolName ?? null,
    tool_input: msg.toolCalls ? JSON.stringify(msg.toolCalls) : null,
    raw_json: JSON.stringify(msg),
  }));
}

function parseCursorTracking(env: LocalSessionEnvelope, raw: any, workspaceId: string) {
  return {
    event_id: env.event_id,
    workspace_id: workspaceId,
    device_id: env.device_id,
    source: "cursor",
    record_type: "ai_code_tracking",
    timestamp: new Date(raw.createdAt).toISOString(),
    metadata: JSON.stringify({
      hash: raw.hash,
      tracking_source: raw.source,  // "tab" or "composer"
      file_extension: raw.fileExtension,
      file_name: raw.fileName,
      conversation_id: raw.conversationId,
      model: raw.model,
    }),
    raw_json: JSON.stringify(raw),
  };
}

function parseCursorDailyStats(env: LocalSessionEnvelope, raw: any, workspaceId: string) {
  // raw = { key: "aiCodeTracking.dailyStats.v1.5.2026-02-07", value: "JSON" }
  const data = JSON.parse(raw.value);
  return {
    event_id: env.event_id,
    workspace_id: workspaceId,
    device_id: env.device_id,
    source: "cursor",
    record_type: "daily_stats",
    timestamp: env.timestamp,
    metadata: JSON.stringify({
      date: raw.key.split(".").pop(),
      tab_suggested: data.tabSuggestedLines,
      tab_accepted: data.tabAcceptedLines,
      composer_suggested: data.composerSuggestedLines,
      composer_accepted: data.composerAcceptedLines,
    }),
    raw_json: JSON.stringify(raw),
  };
}
```

### Codex Parser

Reference: [03-codex.md](03-codex.md)

```typescript
function parseCodex(env: LocalSessionEnvelope, workspaceId: string) {
  const raw = env.raw as any;

  switch (raw.type) {
    case "session_meta":
      return {
        event_id: env.event_id,
        workspace_id: workspaceId,
        device_id: env.device_id,
        source: "codex",
        session_id: raw.session_meta?.id ?? env.session_id,
        record_type: "session_meta",
        timestamp: env.timestamp,
        metadata: JSON.stringify({
          cwd: raw.session_meta?.cwd,
          originator: raw.session_meta?.originator,
          cli_version: raw.session_meta?.cli_version,
          model_provider: raw.session_meta?.model_provider,
        }),
        raw_json: JSON.stringify(raw),
      };

    case "response_item":
      return parseCodexResponseItem(env, raw.response_item, workspaceId);

    case "event_msg":
      return parseCodexEventMsg(env, raw.event_msg, workspaceId);

    case "turn_context":
      return {
        event_id: env.event_id,
        workspace_id: workspaceId,
        device_id: env.device_id,
        source: "codex",
        session_id: env.session_id,
        record_type: "turn_context",
        timestamp: env.timestamp,
        model: raw.turn_context?.model,
        metadata: JSON.stringify({
          personality: raw.turn_context?.personality,
          effort: raw.turn_context?.effort,
          sandbox_mode: raw.turn_context?.sandbox_policy?.mode,
        }),
        raw_json: JSON.stringify(raw),
      };

    default:
      return null;
  }
}

function parseCodexResponseItem(env: LocalSessionEnvelope, item: any, workspaceId: string) {
  if (!item) return null;

  const base = {
    event_id: env.event_id,
    workspace_id: workspaceId,
    device_id: env.device_id,
    source: "codex",
    session_id: env.session_id,
    timestamp: env.timestamp,
    provider: "openai",
  };

  switch (item.type) {
    case "message":
      const textContent = item.content
        ?.filter((c: any) => c.type === "input_text" || c.type === "output_text")
        .map((c: any) => c.text)
        .join("");
      return {
        ...base,
        record_type: `${item.role}_message`,
        role: item.role,
        message_id: item.id,
        content_text: textContent || null,
        raw_json: JSON.stringify(item),
      };

    case "reasoning":
      // NOTE: encrypted_content is encrypted — don't store it
      return {
        ...base,
        record_type: "reasoning",
        message_id: item.id,
        content_text: item.summary?.map((s: any) => s.text).join("") || null,
        raw_json: JSON.stringify({ ...item, encrypted_content: "[REDACTED]" }),
      };

    case "function_call":
      let args: any = null;
      try { args = JSON.parse(item.arguments); } catch {}
      return {
        ...base,
        record_type: "tool_call",
        message_id: item.id,
        tool_name: item.name,  // "shell", "apply_patch", "update_plan"
        tool_input: JSON.stringify(args),
        metadata: JSON.stringify({ call_id: item.call_id, status: item.status }),
        raw_json: JSON.stringify(item),
      };

    case "function_call_output":
      let output: any = null;
      try { output = JSON.parse(item.output); } catch {}
      return {
        ...base,
        record_type: "tool_result",
        tool_result_meta: JSON.stringify(output),
        metadata: JSON.stringify({ call_id: item.call_id }),
        raw_json: JSON.stringify(item),
      };

    default:
      return null;
  }
}

function parseCodexEventMsg(env: LocalSessionEnvelope, msg: any, workspaceId: string) {
  if (!msg) return null;

  if (msg.type === "token_count") {
    return {
      event_id: env.event_id,
      workspace_id: workspaceId,
      device_id: env.device_id,
      source: "codex",
      session_id: env.session_id,
      record_type: "token_usage",
      timestamp: env.timestamp,
      input_tokens: msg.input_tokens ?? 0,
      output_tokens: msg.output_tokens ?? 0,
      metadata: JSON.stringify({
        cached: msg.input_tokens_cached,
        reasoning: msg.reasoning_output_tokens,
        rate_limit: msg.rate_limit_info,
      }),
      raw_json: JSON.stringify(msg),
    };
  }

  // agent_reasoning, turn_aborted — low volume, store as metadata
  return {
    event_id: env.event_id,
    workspace_id: workspaceId,
    device_id: env.device_id,
    source: "codex",
    session_id: env.session_id,
    record_type: msg.type,
    timestamp: env.timestamp,
    content_text: msg.text ?? msg.reason ?? null,
    raw_json: JSON.stringify(msg),
  };
}
```

### OpenClaw Parser

Reference: [04-openclaw.md](04-openclaw.md)

```typescript
function parseOpenClaw(env: LocalSessionEnvelope, workspaceId: string) {
  const raw = env.raw as any;

  switch (raw.type) {
    case "message":
      return parseOpenClawMessage(env, raw, workspaceId);

    case "compaction":
      return {
        event_id: env.event_id,
        workspace_id: workspaceId,
        device_id: env.device_id,
        source: "openclaw",
        session_id: env.session_id,
        record_type: "compaction",
        message_id: raw.id,
        parent_id: raw.parentId,
        timestamp: env.timestamp,
        content_text: raw.summary,
        raw_json: JSON.stringify(raw),
      };

    case "session":
    case "model_change":
    case "thinking_level_change":
      return {
        event_id: env.event_id,
        workspace_id: workspaceId,
        device_id: env.device_id,
        source: "openclaw",
        session_id: env.session_id,
        record_type: raw.type,
        timestamp: env.timestamp,
        raw_json: JSON.stringify(raw),
      };

    default:
      // Skip custom:openclaw.* internal events
      return null;
  }
}

function parseOpenClawMessage(env: LocalSessionEnvelope, raw: any, workspaceId: string) {
  const msg = raw.message;
  if (!msg) return null;

  const isDeliveryMirror = msg.model === "delivery-mirror";
  const textContent = msg.content
    ?.filter((c: any) => c.type === "text" || c.type === "output_text")
    .map((c: any) => c.text)
    .join("");

  const toolCalls = msg.content
    ?.filter((c: any) => c.type === "tool_use")
    .map((c: any) => ({ id: c.id, name: c.name, input: c.input }));

  let recordType = `${msg.role}_message`;
  if (msg.role === "toolResult") recordType = "tool_result";
  if (toolCalls?.length) recordType = "tool_call";

  return {
    event_id: env.event_id,
    workspace_id: workspaceId,
    device_id: env.device_id,
    source: "openclaw",
    session_id: env.session_id,
    record_type: recordType,
    role: msg.role === "toolResult" ? "tool_result" : msg.role,
    message_id: raw.id,
    parent_id: raw.parentId,
    timestamp: env.timestamp,
    content_text: textContent || null,
    model: msg.model,
    provider: msg.provider === "anthropic-messages" ? "anthropic" : msg.provider,
    stop_reason: msg.stopReason,
    tool_name: toolCalls?.[0]?.name ?? (msg.role === "toolResult" ? msg.toolName : null),
    tool_input: toolCalls?.length ? JSON.stringify(toolCalls) : null,
    tool_result_meta: msg.role === "toolResult" ? JSON.stringify({
      tool_call_id: msg.toolCallId,
      is_error: msg.isError,
    }) : null,
    input_tokens: msg.usage?.inputTokens ?? 0,
    output_tokens: msg.usage?.outputTokens ?? 0,
    metadata: JSON.stringify({
      is_delivery_mirror: isDeliveryMirror,
    }),
    raw_json: JSON.stringify(raw),
  };
}
```

---

## 4. ClickHouse Table

**File:** `packages/db/src/clickhouse/schemas.ts`

Add alongside existing table definitions:

```sql
CREATE TABLE IF NOT EXISTS local_session_events (
  event_id          String,
  workspace_id      String,
  device_id         String,
  source            LowCardinality(String),   -- claude_code, cursor, codex, openclaw
  session_id        Nullable(String),
  record_type       LowCardinality(String),   -- user_message, assistant_message, tool_call, etc.
  role              Nullable(LowCardinality(String)),
  message_id        Nullable(String),
  parent_id         Nullable(String),
  timestamp         DateTime64(3),

  -- Content
  content_text      Nullable(String),
  tool_name         Nullable(LowCardinality(String)),
  tool_input        Nullable(String),         -- JSON string
  tool_result_meta  Nullable(String),         -- JSON string

  -- Model & usage
  model             Nullable(LowCardinality(String)),
  provider          Nullable(LowCardinality(String)),
  stop_reason       Nullable(String),
  request_id        Nullable(String),
  input_tokens      UInt32 DEFAULT 0,
  output_tokens     UInt32 DEFAULT 0,
  cache_read_tokens UInt32 DEFAULT 0,
  cache_write_tokens UInt32 DEFAULT 0,

  -- Context
  cwd               Nullable(String),
  git_branch        Nullable(String),
  tool_version      Nullable(String),
  is_subagent       Bool DEFAULT false,
  subagent_id       Nullable(String),

  -- Metadata & raw
  metadata          Nullable(String),         -- JSON string for extra fields
  raw_json          String,                   -- Full original record

  -- Internal
  created_at        DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (workspace_id, device_id, source, timestamp)
TTL toDateTime(timestamp) + INTERVAL 365 DAY
```

---

## 5. Processor Main Loop

```typescript
export function createLocalSessionWorker() {
  return new Worker<LocalSessionJobData>(
    "local-sessions",
    async (job: Job<LocalSessionJobData>) => {
      const { payload, count, deviceContext } = job.data;

      // Decompress
      const buf = Buffer.from(payload, "base64");
      const data = zlib.gunzipSync(buf).toString("utf-8");
      const lines = data.split("\n").filter(Boolean);

      const batch: any[] = [];

      for (const line of lines) {
        try {
          const envelope: LocalSessionEnvelope = JSON.parse(line);
          const parsed = parseEvent(envelope, deviceContext.workspaceId);

          if (!parsed) continue;

          // Handle array results (e.g., Cursor transcripts emit multiple records)
          const records = Array.isArray(parsed) ? parsed : [parsed];
          for (const record of records) {
            batch.push({
              ...record,
              workspace_id: deviceContext.workspaceId,
              device_id: deviceContext.deviceId,
            });
          }
        } catch (err) {
          logger.warn(`Failed to parse local session line: ${err}`);
        }
      }

      // Batch insert to ClickHouse
      if (batch.length > 0) {
        await clickhouse.insert({
          table: "local_session_events",
          values: batch,
          format: "JSONEachRow",
        });
      }

      logger.info(`Processed ${batch.length}/${count} local session events`);
    },
    {
      connection: redis,
      concurrency: 10,
    }
  );
}
```

---

## 6. Register Worker

**File:** `apps/worker/src/index.ts`

```typescript
import { createLocalSessionWorker } from "./processors/local-session.processor.js";

// Add alongside existing workers
const localSessionWorker = createLocalSessionWorker();

// Add to graceful shutdown
async function shutdown() {
  await localSessionWorker.close();
  // ... existing shutdown ...
}
```

---

## 7. Processing Flow Summary

```
Sensor (macOS app)
  │  POST /api/v1/ingest/local-sessions (gzipped JSONL)
  │  Auth: Bearer dev_tk_xxx
  ▼
Express Route (apps/api/)
  │  authenticateDevice → resolve device + workspace
  │  Base64 encode gzipped payload
  │  enqueueLocalSessions() → BullMQ
  │  Return 202
  ▼
BullMQ "local-sessions" queue (Redis)
  ▼
Worker Process (apps/worker/)
  │  Decompress, split lines
  │  For each envelope:
  │    Route by source → parseClaudeCode/Cursor/Codex/OpenClaw
  │    Parse raw → normalized flat record
  │  Batch insert → ClickHouse local_session_events
  ▼
ClickHouse
  │  Partitioned by day, ordered by (workspace, device, source, time)
  │  365-day TTL
  ▼
Dashboard queries ClickHouse
```

---

## 8. Schema Reference (Which Doc to Read)

| When parsing... | Reference |
|-----------------|-----------|
| Claude Code `raw.type` values, UUID threading, streaming lines | [01-claude-code.md](01-claude-code.md) |
| Claude Code `toolUseResult` variants (Bash/Read/Glob/Task) | [01-claude-code.md §2.1](01-claude-code.md) |
| Claude Code subagents (warmup stubs, agentId) | [01-claude-code.md §4](01-claude-code.md) |
| Cursor composerData / bubbleId (SQLite key format) | [02-cursor.md §1](02-cursor.md) |
| Cursor agent transcripts (JSON array structure) | [02-cursor.md §2](02-cursor.md) |
| Cursor AI code tracking (ai_code_hashes columns) | [02-cursor.md §3](02-cursor.md) |
| Codex session JSONL (4 record types) | [03-codex.md §1](03-codex.md) |
| Codex function calls (shell, apply_patch) | [03-codex.md §1.3](03-codex.md) |
| Codex token_count with rate limits | [03-codex.md §1.4](03-codex.md) |
| OpenClaw messages (multi-provider, delivery mirrors) | [04-openclaw.md §2](04-openclaw.md) |
| OpenClaw compaction summaries | [04-openclaw.md §2.2](04-openclaw.md) |
| Wire format (envelope fields the sensor sends) | [06-unified-model.md §1](06-unified-model.md) |
| Sensor config (what globs/queries the sensor uses) | [07-sensor-config.md §1](07-sensor-config.md) |
