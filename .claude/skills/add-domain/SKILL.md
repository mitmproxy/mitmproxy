---
name: add-domain
description: End-to-end domain onboarding — HAR analysis, sensor config update, trace conversion, parser generation, refinement, and linking
disable-model-invocation: false
argument-hint: [domain.com] [path/to/file.har]
allowed-tools: Bash, Read, Grep, WebFetch, Task
---

# for your 

# Add Domain — End-to-End Onboarding Pipeline

Onboard a new AI domain from a HAR capture file all the way to a production-ready parser linked in the database.

**Arguments:**
- `$0` — the domain (e.g. `suno.com`)
- `$1` — path to a HAR file containing recorded API traffic

Derive a **slug** from `$0` (e.g. `suno.com` → `suno`, `gemini.google.com` → `gemini`). Use this slug for filenames, parser names, and catalog entries throughout.

---

## Step 0: Parse the HAR File

Read the HAR file at `$1` and extract all unique API endpoints for domain `$0`:

1. Read the file (it's JSON with a `log.entries[]` array)
2. Filter entries where the request URL host matches `$0` (or its subdomains)
3. For each entry, extract: `method`, `url` (path + query), `status`, `mimeType`
4. Ignore static assets (`.js`, `.css`, `.png`, `.jpg`, `.svg`, `.woff`, fonts, images)
5. Ignore common noise: analytics, tracking, sentry, healthcheck URLs
6. **Only keep endpoints related to:** AI/ML generation (prompts, completions, model calls), user account info, and subscription/billing data. Drop everything else (notifications, play counts, video status polling, gamification, config checks, attribution metadata, etc.)
7. Group remaining endpoints by path pattern — collapse path segments that look like IDs (UUIDs, numeric IDs) into `*` or `**` wildcards
8. Also collect any **external domains** referenced (CDNs, media servers, etc.)

Output a summary table of discovered API endpoints before proceeding.

---

## Step 1: Update Sensor Config via API

Fetch the current sensor config:

```json
curl --location 'https://api.oximy.com/api/v1/sensor-config' \
--header 'Accept: application/json' \
--header 'User-Agent: Oximy-Sensor/1.0' \
--header 'Authorization: Bearer [get this from "/Users/hirakdesai/.oximy"]'
```


### 1a. Check Existing Config

- Search `whitelistedDomains` and `allowed_host_origins` for `$0`
- If already present, report what exists and only create missing entries

### 1b. Create Whitelisted Domains

Convert discovered API endpoints to whitelist patterns using existing conventions:

| Convention | Example |
|---|---|
| Exact path | `domain.com/api/v1/chat/completions` |
| Single segment wildcard | `domain.com/api/*/status` |
| Multi-segment wildcard | `domain.com/api/**/conversation` |
| Trailing wildcard | `domain.com/api/feed/v2*` (for query params) |

Prefer specific patterns over broad ones.

**Scope:** Only AI/ML generation endpoints, user account endpoints, and subscription/billing endpoints. Exclude noise.

**Before each POST, ask the user for explicit permission.** Show the payload and endpoint, then wait for confirmation.

```bash
curl -X POST https://api.oximy.com/api/v1/internal/whitelisted-domains \
  -H "Content-Type: application/json" \
  -d '{"domain": "<pattern>", "note": "Added via add-domain skill for $0", "enabled": true}'
```

### 1c. Create Passthrough Domains

Identify CDN, media, or static asset domains from the HAR that should bypass TLS interception.

**Ask user permission before each POST.**

```bash
curl -X POST https://api.oximy.com/api/v1/internal/passthrough-domains \
  -H "Content-Type: application/json" \
  -d '{"pattern": "^cdn.example.com$", "note": "CDN for $0", "enabled": true}'
```

### 1d. Create / Update Website Catalog Entry

Check if a catalog entry already exists:

```bash
curl -s https://api.oximy.com/api/v1/internal/website-catalog/by-slug/<slug> | jq
```

**Ask user permission before creating or updating.**

If it does not exist:
```bash
curl -X POST https://api.oximy.com/api/v1/internal/website-catalog \
  -H "Content-Type: application/json" \
  -d '{"slug": "<slug>", "name": "<Name>", "domains": ["$0"], "category": "ai_chat", "toolType": "ai_tool", "verified": false, "needsReview": true}'
```

If it exists, PATCH with any new data:
```bash
curl -X PATCH https://api.oximy.com/api/v1/internal/website-catalog/by-slug/<slug> \
  -H "Content-Type: application/json" \
  -d '{ ... updated fields ... }'
```

### 1e. Review Blacklisted Words

Check if any endpoints would be blocked by existing blacklisted words. Flag conflicts.

---

## Step 2: Convert HAR to JSONL

Convert the HAR file into Oximy's JSONL trace format and save to the traces directory.

For each relevant HAR entry in `log.entries[]`, produce a JSON object per line with this structure:

```json
{
  "event_id": "<uuid>",
  "timestamp": "<ISO 8601 from HAR startedDateTime>",
  "type": "http",
  "device_id": "<single uuid for entire session>",
  "client": {
    "pid": 0,
    "bundle_id": "company.thebrowser.Browser",
    "name": "Browser",
    "app_type": "host",
    "host_origin": "<domain from URL>",
    "referrer_origin": "<from Referer header or empty>"
  },
  "request": {
    "method": "<method>",
    "host": "<host>",
    "path": "<path + query>",
    "headers": { "<key>": "<value>", ... },
    "body": "<postData.text or null>"
  },
  "response": {
    "status_code": <status>,
    "headers": { "<key>": "<value>", ... },
    "body": "<content.text or null>"
  },
  "timing": {
    "duration_ms": <time from HAR timings>,
    "ttfb_ms": <wait from HAR timings>
  }
}
```

Write the output to:

```
/Users/hirakdesai/Developer/Oximy/api/traces/<slug>-1.jsonl
```

Only include entries that match the domain and are relevant (same filters as Step 0).

---

## Step 3: Generate Parser

From the API repo root, generate a parser from the traces:

```bash
cd /Users/hirakdesai/Developer/Oximy/api
npx tsx scripts/parsers/generate-parser.ts ./traces/<slug>-1.jsonl --name <slug>
```

This creates: `apps/worker/src/parsers/apps/<slug>.parser.ts`

Show the output to the user, including any registration instructions.

---

## Step 4: Register Parser

Show the user the manual registration step:

> Open `/Users/hirakdesai/Developer/Oximy/api/apps/worker/src/parsers/index.ts` and:
> 1. Import the parser: `import { <SlugPascalCase>Parser } from "./apps/<slug>.parser.js";`
> 2. Add to the `PARSERS` array: `new <SlugPascalCase>Parser(),`

Wait for user confirmation before proceeding.

---

## Step 5: Build and Test

```bash
cd /Users/hirakdesai/Developer/Oximy/api
pnpm --filter @oximy/worker build
npx tsx scripts/parsers/test-parser.ts ./traces/<slug>-1.jsonl --parser <slug>
```

This writes parsed events to:
```
/Users/hirakdesai/Developer/Oximy/api/parsed_events/<slug>-1.jsonl
```

Show the test summary to the user. If the success rate is below 50%, note issues before proceeding to refinement.

---

## Step 6: AI-Guided Parser Refinement

Use the `Task` tool to spawn a sub-agent with the following prompt. Provide it the paths to:
- Raw traces: `traces/<slug>-1.jsonl`
- Parser: `apps/worker/src/parsers/apps/<slug>.parser.ts`
- Parsed output: `parsed_events/<slug>-1.jsonl`
- Base class: `apps/worker/src/parsers/base.parser.ts`
- Types: `apps/worker/src/parsers/types.ts`
- Reference parsers in `apps/worker/src/parsers/apps/` for comparison

**Sub-agent prompt (AI Chat Parser Development Guide):**

```
# AI Chat Parser Development Guide

## Context

You are creating a parser for **<slug>** to extract AI chat interactions from network traces.

### Files Provided
- `traces/<slug>-1.jsonl` - Raw network traces (one JSON object per line)
- `apps/worker/src/parsers/base.parser.ts` - Base class you extend
- `apps/worker/src/parsers/types.ts` - ParseContext, ParseResult, InteractionType definitions
- Existing parsers in `apps/worker/src/parsers/apps/` for reference

### Your Task
Create/fix `<slug>.parser.ts` that extracts:
1. User input text
2. AI response text
3. Conversation ID
4. Response/message ID
5. Thinking mode (if applicable)
6. Generated images/artifacts (if applicable)

---

## CRITICAL PRINCIPLE: Structural Extraction > Heuristics

**NEVER** use recursive content search or scoring heuristics. These fail because:
- AI services embed grounding data (reviews, citations, search results) in responses
- System prompts/custom instructions appear in response payloads
- Session tokens look like encoded user input
- "Longest text" selection grabs reviews instead of AI responses

**ALWAYS** extract from documented structural positions after mapping the format.

---

## Phase 1: Trace Analysis (80% of the work)

Before writing ANY code, analyze 3-5 traces and document the structure.

### 1.1 Analyze Request Structure
- Content-Type? (JSON, form-urlencoded, protobuf, nested JSON strings?)
- User message location? (exact path)
- Conversation ID location? (exact path)
- Session/continuation tokens? (identify to EXCLUDE from user input)
- Multimodal input? (images, files - where?)

### 1.2 Analyze Response Structure
- Streaming or single response?
- Chunk format? (newline-delimited JSON, SSE data: lines, custom?)
- AI response text location? (exact path - NOT "somewhere nested")
- Grounding/citation location? (this is NOT the AI response)
- System prompt location? (this is NOT the AI response)
- Generated images? (URLs, base64, references?)
- Thinking mode indicator? (specific field or structure?)
- Response ID format? (prefix pattern like r_, msg_?)

### 1.3 Document Structure Map
Document the exact structural positions for all fields before writing code.

## Phase 2: Implementation Rules

1. **Structural Extraction, Not Recursive Search** — extract from known paths only
2. **Validate Structure Before Trusting Indices** — check array/type at each level
3. **Validate User Input** — reject encoded tokens, session IDs, garbage strings
4. **Separate Grounding From Response** — never mix citations with AI response text
5. **Handle Streaming Responses** — process chunks properly (last chunk or accumulate)
6. **Fallback With Warning Logging** — if structural extraction fails, log a warning

## Phase 3: Validation

After making changes:
- Rebuild: `pnpm --filter @oximy/worker build`
- Retest: `npx tsx scripts/parsers/test-parser.ts ./traces/<slug>-1.jsonl --parser <slug>`
- Verify all user inputs are readable text, not encoded tokens
- Verify all outputs are AI-generated content, not reviews/grounding
- No system prompts in output
- Conversation IDs are consistent within sessions

## Final Checklist
- [ ] Structure map documented in file header
- [ ] Request structure: exact path for user input
- [ ] Session tokens identified and excluded
- [ ] Response structure: exact path for AI response
- [ ] Grounding/citations separated
- [ ] No recursive "find longest text"
- [ ] Structural markers validated
- [ ] isValidUserInput rejects garbage
- [ ] Streaming handled (if applicable)
- [ ] Images extracted to artifacts array
- [ ] Thinking mode detected (if applicable)
- [ ] TypeScript compiles without errors
```

After the sub-agent completes, rebuild and retest (repeat Step 5). Iterate up to 3 times until quality is acceptable.

---

## Step 7: Parser Analysis and Improvement

Use the `Task` tool to spawn another sub-agent with this analysis prompt:

```
# AI Chat Network Trace Parser Analysis

Review the parser at `apps/worker/src/parsers/apps/<slug>.parser.ts` and its output at `parsed_events/<slug>-1.jsonl`.

## Analysis Checklist

### Streaming Response Splitting
- Naive split("}{") or proper brace counting? Naive = P0 bug.

### Structural Extraction
- Known paths or heuristics ("longest text wins")?
- Hardcoded array indices without validation? Flag these.
- Fallback behavior that could pick wrong content?

### Input Validation
- Rejects encoded tokens?
- Space ratio check for garbage?
- Minimum length filtering?

### Missing Extractions
- Model name
- Thinking mode / extended thinking
- Tool use / artifacts
- Citations / sources
- Error responses (rate limits, content policy)
- Token usage
- File attachments

### Confidence Scoring
- Differentiated by extraction quality?
- Preview/prepare endpoints scored lower?

### Parsed Output Verification
- Clean inputs (no garbage tokens)
- Complete outputs (full AI response, not truncated)
- Proper metadata (conversation_id, message_id, model)
- No duplicates at high confidence
- Correct interaction type

## Output Format
Prioritized issue list (P0/P1/P2) with code references and specific fixes.
Apply all fixes to the parser file, then rebuild and retest.
```

After the sub-agent completes, rebuild and retest (Step 5 again).

---

## Step 8: Verify Output Schema

Read the parsed output at `parsed_events/<slug>-1.jsonl` and compare against multiple reference files in:

```
/Users/hirakdesai/Developer/Oximy/api/parsed_events/
```

Pick 2-3 reference files that are closest in nature to the new parser (e.g. streaming chat → compare with `chatgpt`, `claude`; search-augmented → compare with `perplexity`, `copilot`; multimodal → compare with `gemini`, `canva`).

Verify:
- Same top-level structure (`generated_at`, `source_file`, `stats`, `events`)
- Each event has proper `interaction.type` (`chat`, `codegen`, `asset_creation`)
- Required fields present: `conversation_id`, `input.text`, `output.text`
- Optional fields populated when applicable: `model`, `citations`, `artifacts`, `capabilities`
- Confidence scores appropriate (0.95 for full extraction)
- No `null` where `undefined`/omitted is expected

Report any schema mismatches to the user.

---

## Step 9: Link Parser to Website

```bash
cd /Users/hirakdesai/Developer/Oximy/api
npx tsx scripts/parsers/link-parser.ts --website $0 --parser <slug> --create
```

This sets `parserConfig.parserName` and `parserConfig.enabled` on the WebsiteCatalog entry.

---

## Step 10: Final Summary

Report to the user:

```
Domain Onboarding Complete: $0

Sensor Config:
  - N whitelisted domains added
  - N passthrough domains added
  - Website catalog entry: <slug>

Parser:
  - File: apps/worker/src/parsers/apps/<slug>.parser.ts
  - Test results: X% success, avg confidence Y
  - Linked to $0 in production

Files:
  - Traces: traces/<slug>-1.jsonl
  - Parsed events: parsed_events/<slug>-1.jsonl
```
