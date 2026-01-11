# Oximy Addon Architecture

> Comprehensive documentation for the Oximy mitmproxy addon that captures AI API traffic using the OISP (Open Intelligence & Services Protocol) specification.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Module Reference](#module-reference)
5. [Data Flow](#data-flow)
6. [OISP Bundle Format](#oisp-bundle-format)
7. [Configuration Options](#configuration-options)
8. [Output Format](#output-format)
9. [Adding New Providers](#adding-new-providers)
10. [Common Edge Cases](#common-edge-cases)
11. [Debugging & Troubleshooting](#debugging--troubleshooting)
12. [Investigation Mode](#investigation-mode)

---

## Overview

Oximy is a mitmproxy addon that:
- **Captures** AI API traffic (OpenAI, Anthropic, Google, etc.)
- **Classifies** traffic against the OISP bundle registry
- **Parses** requests/responses into normalized format
- **Handles** Server-Sent Events (SSE) streaming
- **Attributes** traffic to client processes (which app made the request)
- **Writes** events to rotating JSONL files

### Key Design Principles

1. **Privacy Tiers**: Full trace (parsed content) vs identifiable (metadata only) vs drop
2. **Registry-Driven**: All classification/parsing rules come from the OISP bundle
3. **Process Attribution**: Captures which application made each request
4. **TLS Passthrough**: Auto-learns certificate-pinned hosts
5. **Stream Handling**: Accumulates SSE chunks while passing data through unchanged

---

## Quick Start

### Running the Addon

```bash
# Basic usage - start mitmproxy with Oximy enabled
mitmdump -s mitmproxy/addons/oximy/addon.py \
         --set oximy_enabled=true \
         --listen-port 8088

# With custom output directory
mitmdump -s mitmproxy/addons/oximy/addon.py \
         --set oximy_enabled=true \
         --set oximy_output_dir=~/my-traces \
         --listen-port 8088

# Without raw request/response bodies (smaller output)
mitmdump -s mitmproxy/addons/oximy/addon.py \
         --set oximy_enabled=true \
         --set oximy_include_raw=false \
         --listen-port 8088

# Force bundle refresh from URL
mitmdump -s mitmproxy/addons/oximy/addon.py \
         --set oximy_enabled=true \
         --set oximy_bundle_refresh_hours=0 \
         --listen-port 8088
```

### Using with mitmweb (GUI)

```bash
mitmweb -s mitmproxy/addons/oximy/addon.py \
        --set oximy_enabled=true \
        --listen-port 8088
```

### Configure System Proxy (macOS)

The addon can auto-configure macOS system proxy (development convenience):

```python
# In addon.py, set:
OXIMY_AUTO_PROXY_ENABLED = True  # Auto-enable proxy on start
OXIMY_PROXY_PORT = "8088"        # Match your --listen-port
```

Or manually:
```bash
# Enable proxy
networksetup -setwebproxy Wi-Fi 127.0.0.1 8088
networksetup -setsecurewebproxy Wi-Fi 127.0.0.1 8088

# Disable proxy
networksetup -setwebproxystate Wi-Fi off
networksetup -setsecurewebproxystate Wi-Fi off
```

### Installing mitmproxy CA Certificate

For HTTPS interception, install the mitmproxy CA:

```bash
# Generate cert (run mitmproxy once first)
mitmproxy  # Then quit

# Install on macOS
sudo security add-trusted-cert -d -r trustRoot \
     -k /Library/Keychains/System.keychain \
     ~/.mitmproxy/mitmproxy-ca-cert.pem
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HTTP Request arrives                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     OximyAddon.request() hook                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  TrafficMatcher.match()                                      │    │
│  │  ├─ domain_lookup (exact match)  → full_trace               │    │
│  │  ├─ domain_patterns (regex)      → full_trace               │    │
│  │  ├─ websites (endpoint patterns) → full_trace               │    │
│  │  └─ unknown                      → drop                      │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  ProcessResolver.get_process_for_port()                      │    │
│  │  └─ Captures client process info IMMEDIATELY                 │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  Store MatchResult + ClientProcess in flow.metadata                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 OximyAddon.responseheaders() hook                    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  If content-type: text/event-stream                          │    │
│  │  └─ Create SSEBuffer and set flow.response.stream handler    │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    (SSE chunks processed in stream handler)
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   OximyAddon.response() hook                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  RequestParser.parse()                                       │    │
│  │  └─ Extract messages, model, temperature, etc.               │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  ResponseParser.parse() OR SSEBuffer.finalize()              │    │
│  │  └─ Extract content, model, usage, finish_reason             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Build OximyEvent                                            │    │
│  │  └─ Combine source, timing, client, interaction              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  EventWriter.write()                                         │    │
│  │  └─ Append to traces_YYYY-MM-DD.jsonl                        │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Module Reference

### `addon.py` - Main Entry Point

The core addon class that hooks into mitmproxy's lifecycle.

```python
class OximyAddon:
    # Hooks implemented:
    def load(self, loader)           # Register configuration options
    def configure(self, updated)     # Initialize/teardown based on settings
    def request(self, flow)          # Classify traffic, capture process info
    def responseheaders(self, flow)  # Set up SSE streaming
    def response(self, flow)         # Build and write events
    def tls_clienthello(self, data)  # Check TLS passthrough
    def tls_failed_client(self, data) # Learn certificate-pinned hosts
    def done(self)                   # Cleanup on shutdown
```

**Key metadata stored on flows:**
- `flow.metadata["oximy_match"]` - MatchResult from classification
- `flow.metadata["oximy_client"]` - ClientProcess info

### `types.py` - Data Structures

All data classes for the addon:

| Type | Purpose |
|------|---------|
| `MatchResult` | Classification result (full_trace/identifiable/drop) |
| `EventSource` | Source info (type: api/app/website, id, endpoint) |
| `InteractionRequest` | Parsed request (messages, model, temperature, etc.) |
| `InteractionResponse` | Parsed response (content, model, usage, etc.) |
| `Interaction` | Combined request + response |
| `EventTiming` | Timing metrics (duration_ms, ttfb_ms) |
| `OximyEvent` | Final output event with all fields |
| `DomainPattern` | Compiled regex for dynamic domain matching |

**UUID v7 Generation:**
The addon generates time-sortable UUIDs (v7) for event IDs, making them naturally chronological.

### `matcher.py` - Traffic Classification

Classifies HTTP traffic against the OISP bundle.

```python
class TrafficMatcher:
    def match(self, flow: HTTPFlow) -> MatchResult:
        # Priority order:
        # 1. domain_lookup - exact domain match (api.openai.com → openai)
        # 2. domain_patterns - regex match (*.openai.azure.com → azure_openai)
        # 3. websites - known AI websites with endpoint patterns
        # 4. Unknown → drop
```

**Classification Levels:**
- `full_trace` - Parse and capture full interaction content
- `identifiable` - Capture metadata only (method, path, status)
- `drop` - Silently ignore (unknown traffic)

### `parser.py` - Request/Response Parsing

JSONPath-based extraction of structured data.

```python
class JSONPathExtractor:
    # Supports:
    # $.field - Top level
    # $.field.nested - Nested
    # $.field[0] - Array index
    # $.field[*].nested - All elements

class RequestParser:
    def parse(self, body, api_format, include_raw) -> InteractionRequest
    # Special handling for ChatGPT web format

class ResponseParser:
    def parse(self, body, api_format, include_raw) -> InteractionResponse
    # Handles Anthropic content blocks, usage normalization
```

### `sse.py` - Server-Sent Events Handler

Accumulates streaming response chunks.

```python
class SSEBuffer:
    def process_chunk(self, chunk: bytes) -> bytes:
        # Parse SSE events while passing data through unchanged
        # Accumulates: content, model, finish_reason, usage

    def finalize(self) -> dict:
        # Returns accumulated data after stream ends

# SSE Format Detection:
# - OpenAI: data: {"choices":[{"delta":{"content":"..."}}]}
# - Anthropic: data: {"delta":{"text":"..."}}
# - ChatGPT Web: data: {"v":"text"} or {"o":"append","v":"text","p":"/message/..."}
```

**ChatGPT Web SSE Formats:**
1. Simple continuation: `{"v": "text"}` - just append
2. JSON patch append: `{"o": "append", "v": "text", "p": "/message/content/parts/0"}`
3. Nested patches: `{"o": "patch", "v": [{"o": "append", ...}]}`

### `bundle.py` - OISP Bundle Loading

Manages bundle fetching, caching, and parsing.

```python
class BundleLoader:
    def load(self, force_refresh=False) -> OISPBundle:
        # Priority:
        # 1. Local bundle (registry/dist/oximy-bundle.json) - development
        # 2. Cached bundle (if < 24 hours old)
        # 3. Remote URL (https://oisp.dev/spec/...)
        # 4. Stale cache (fallback)

class OISPBundle:
    domain_lookup: dict[str, str]        # hostname → provider_id
    domain_patterns: list[CompiledDomainPattern]  # regex patterns
    providers: dict[str, dict]           # provider metadata
    parsers: dict[str, dict]             # api_format → {request, response}
    models: dict[str, dict]              # model definitions
    apps: dict[str, dict]                # app signatures
    websites: dict[str, dict]            # website definitions
```

**Cache Location:** `~/.oximy/bundle_cache.json`

### `writer.py` - JSONL Output

Writes events to rotating daily files.

```python
class EventWriter:
    def write(self, event: OximyEvent) -> None:
        # Appends to ~/.oximy/traces/traces_YYYY-MM-DD.jsonl
        # Auto-rotates at midnight
        # Atomic append with flush
```

### `process.py` - Process Attribution

Maps network connections to originating processes.

```python
class ProcessResolver:
    def get_process_for_port(self, port: int) -> ClientProcess:
        # 1. Find PID via lsof (port must be SOURCE, not DEST)
        # 2. Get process info via ps
        # 3. Get parent process info
        # Returns: pid, name, path, ppid, parent_name, user

class ClientProcess:
    pid: int | None
    name: str | None          # e.g., "Cursor Helper"
    path: str | None          # e.g., "/Applications/Cursor.app/..."
    ppid: int | None
    parent_name: str | None   # e.g., "Cursor"
    user: str | None
    port: int
```

**Why capture in request() hook?**
Process info must be captured immediately when the request arrives. By the time the response completes, the client process may have exited.

### `passthrough.py` - TLS Certificate Pinning

Handles hosts that use certificate pinning.

```python
class TLSPassthrough:
    # Known pinned hosts (regex patterns):
    # - *.apple.com, *.icloud.com
    # - *.googleapis.com, accounts.google.com

    def should_passthrough(self, host) -> (bool, reason)
    def record_tls_failure(self, host, error, client_process)

    # Hooks:
    def tls_clienthello(self, data)    # Skip known pinned hosts
    def tls_failed_client(self, data)  # Learn new pinned hosts
```

**Auto-Learning:**
When TLS handshake fails with pinning-related errors, the host is added to the passthrough list and persisted to `~/.oximy/traces/pinned_hosts.json`.

---

## Data Flow

### Complete Request/Response Lifecycle

```
1. Client (e.g., Cursor) makes HTTPS request to api.openai.com
2. mitmproxy intercepts (TLS termination)
3. OximyAddon.request():
   - TrafficMatcher classifies: api.openai.com → openai (full_trace)
   - ProcessResolver captures: PID 1234, "Cursor Helper", parent "Cursor"
   - Store in flow.metadata
4. Request forwarded to api.openai.com
5. Response headers arrive
6. OximyAddon.responseheaders():
   - Detects text/event-stream
   - Creates SSEBuffer
   - Sets flow.response.stream = handler
7. SSE chunks arrive:
   - data: {"choices":[{"delta":{"content":"Hello"}}]}
   - data: {"choices":[{"delta":{"content":" world"}}]}
   - data: [DONE]
   - SSEBuffer accumulates: "Hello world"
8. Response complete
9. OximyAddon.response():
   - RequestParser extracts messages, model from request
   - SSEBuffer.finalize() returns accumulated content
   - Build OximyEvent
   - EventWriter appends to JSONL
```

### Timing Calculation

```python
timing = EventTiming(
    duration_ms = (response.timestamp_end - request.timestamp_start) * 1000,
    ttfb_ms = (response.timestamp_start - request.timestamp_start) * 1000,
)
```

---

## OISP Bundle Format

The OISP bundle is a JSON file containing all classification and parsing rules.

### Top-Level Structure

```json
{
  "$schema": "https://oisp.dev/schema/v0.1/bundle.schema.json",
  "bundle_version": "2.1.0",
  "generated_at": "2026-01-10T03:49:50.425563+00:00",

  "domain_lookup": { ... },
  "domain_patterns": [ ... ],
  "providers": { ... },
  "parsers": { ... },
  "models": { ... },
  "registry": {
    "apps": { ... },
    "websites": { ... }
  }
}
```

### domain_lookup

Direct hostname to provider ID mapping.

```json
{
  "api.openai.com": "openai",
  "api.anthropic.com": "anthropic",
  "api.groq.com": "groq",
  "generativelanguage.googleapis.com": "google"
}
```

### domain_patterns

Regex patterns for dynamic domains (Azure, AWS Bedrock).

```json
[
  {
    "pattern": ".*\\.openai\\.azure\\.com$",
    "provider": "azure_openai"
  },
  {
    "pattern": "bedrock-runtime\\..*\\.amazonaws\\.com$",
    "provider": "aws_bedrock"
  }
]
```

### providers

Metadata about each AI provider.

```json
{
  "openai": {
    "name": "OpenAI",
    "api_format": "openai",
    "website": "https://openai.com"
  },
  "anthropic": {
    "name": "Anthropic",
    "api_format": "anthropic",
    "website": "https://anthropic.com"
  }
}
```

### parsers

JSONPath extraction rules for each API format.

```json
{
  "openai": {
    "request": {
      "messages": "$.messages",
      "model": "$.model",
      "temperature": "$.temperature",
      "max_tokens": "$.max_tokens",
      "tools": "$.tools"
    },
    "response": {
      "content": "$.choices[0].message.content",
      "model": "$.model",
      "finish_reason": "$.choices[0].finish_reason",
      "usage": "$.usage"
    }
  },
  "anthropic": {
    "request": {
      "messages": "$.messages",
      "model": "$.model",
      "temperature": "$.temperature",
      "max_tokens": "$.max_tokens"
    },
    "response": {
      "content": "$.content",
      "model": "$.model",
      "stop_reason": "$.stop_reason",
      "usage": "$.usage"
    }
  }
}
```

### registry.websites

Website definitions with endpoint patterns.

```json
{
  "chatgpt": {
    "name": "ChatGPT",
    "domains": ["chatgpt.com", "chat.openai.com"],
    "api_format": "chatgpt_web",
    "features": {
      "chat": {
        "patterns": [
          {"url": "**/backend-api/conversation", "method": "POST"}
        ]
      },
      "voice": {
        "patterns": [
          {"url": "**/backend-api/voice/**", "method": "POST"}
        ]
      }
    }
  }
}
```

---

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `oximy_enabled` | bool | false | Enable/disable the addon |
| `oximy_output_dir` | str | ~/.oximy/traces | Output directory for JSONL files |
| `oximy_bundle_url` | str | https://oisp.dev/... | URL to fetch OISP bundle |
| `oximy_bundle_refresh_hours` | int | 24 | Hours before bundle refresh |
| `oximy_include_raw` | bool | true | Include raw request/response bodies |

### Setting Options

```bash
# Command line
mitmdump --set oximy_enabled=true --set oximy_output_dir=/tmp/traces

# Or in mitmproxy config file (~/.mitmproxy/config.yaml)
oximy_enabled: true
oximy_output_dir: /tmp/traces
```

---

## Output Format

Events are written to `~/.oximy/traces/traces_YYYY-MM-DD.jsonl` in JSONL format (one JSON object per line).

### Full Trace Event

```json
{
  "event_id": "019ba938-c2c4-7edc-9674-7bedb7631751",
  "timestamp": "2026-01-10T18:43:48.036Z",
  "source": {
    "type": "website",
    "id": "chatgpt",
    "endpoint": "chat"
  },
  "trace_level": "full",
  "timing": {
    "duration_ms": 2706,
    "ttfb_ms": 1091
  },
  "client": {
    "port": 58634,
    "pid": 89299,
    "name": "Comet Helper",
    "path": "/Applications/Comet.app/.../Comet Helper",
    "ppid": 4928,
    "parent_name": "Comet",
    "user": "namanambavi"
  },
  "interaction": {
    "request": {
      "messages": [{"role": "user", "content": "Hello!"}],
      "model": "gpt-4",
      "_raw": { ... }
    },
    "response": {
      "content": "Hello! How can I help you?",
      "model": "gpt-4",
      "finish_reason": "stop",
      "usage": {
        "input_tokens": 10,
        "output_tokens": 8,
        "total_tokens": 18
      }
    },
    "model": "gpt-4"
  }
}
```

### Identifiable Event (Metadata Only)

```json
{
  "event_id": "019ba938-d1e5-7abc-8901-234567890abc",
  "timestamp": "2026-01-10T18:45:12.123Z",
  "source": {
    "type": "api",
    "id": "openai",
    "endpoint": null
  },
  "trace_level": "identifiable",
  "timing": {
    "duration_ms": 150,
    "ttfb_ms": 50
  },
  "client": { ... },
  "metadata": {
    "request_method": "GET",
    "request_path": "/v1/models",
    "response_status": 200,
    "content_length": 4523
  }
}
```

---

## Adding New Providers

### Step 1: Add to domain_lookup

In the OISP bundle (or local override):

```json
{
  "domain_lookup": {
    "api.newprovider.com": "newprovider"
  }
}
```

### Step 2: Add Provider Definition

```json
{
  "providers": {
    "newprovider": {
      "name": "New Provider",
      "api_format": "openai",  // or custom format
      "website": "https://newprovider.com"
    }
  }
}
```

### Step 3: Add Parser (if custom format)

```json
{
  "parsers": {
    "newprovider": {
      "request": {
        "messages": "$.messages",
        "model": "$.model"
      },
      "response": {
        "content": "$.result.text",
        "model": "$.result.model_used"
      }
    }
  }
}
```

### Step 4: For Websites (AI web interfaces)

```json
{
  "registry": {
    "websites": {
      "newsite": {
        "name": "New AI Site",
        "domains": ["newsite.ai", "app.newsite.ai"],
        "api_format": "newsite_web",
        "features": {
          "chat": {
            "patterns": [
              {"url": "**/api/chat", "method": "POST"}
            ]
          }
        }
      }
    }
  }
}
```

---

## Common Edge Cases

### SSE Streaming Formats

**OpenAI API:**
```
data: {"id":"...","choices":[{"delta":{"content":"Hello"}}]}
data: {"id":"...","choices":[{"delta":{"content":" world"}}]}
data: [DONE]
```

**Anthropic API:**
```
data: {"type":"content_block_delta","delta":{"text":"Hello"}}
data: {"type":"content_block_delta","delta":{"text":" world"}}
data: {"type":"message_stop"}
```

**ChatGPT Web (complex):**
```
data: v1
data: {"type":"server_ste_metadata","metadata":{"model_slug":"gpt-5-2"}}
data: {"v":"Hello"}
data: {"v":" world"}
data: {"o":"append","v":"!","p":"/message/content/parts/0"}
data: {"o":"patch","v":[{"o":"append","v":"...","p":"/..."}]}
```

### Process Attribution Edge Cases

1. **Helper processes**: Many apps use helper processes (e.g., "Cursor Helper"). We capture both the actual process and parent.

2. **Quick exits**: Some CLI tools exit immediately after request. Capture in `request()` hook, not `response()`.

3. **Port reuse**: Use LRU cache by PID, not port, since ports are reused.

### Certificate Pinning

Some hosts will never work with MITM:
- Apple services (*.apple.com)
- Some banking apps
- Apps with custom certificate validation

The addon auto-learns these and adds to passthrough list.

---

## Debugging & Troubleshooting

### Enable Debug Logging

```bash
mitmdump -s mitmproxy/addons/oximy/addon.py \
         --set oximy_enabled=true \
         -v  # Verbose logging
```

### Check What's Being Captured

```bash
# Watch the output file
tail -f ~/.oximy/traces/traces_$(date +%Y-%m-%d).jsonl | jq .

# Filter by source
tail -f ~/.oximy/traces/traces_*.jsonl | jq 'select(.source.id == "openai")'
```

### Common Issues

**"No bundle available"**
- Check internet connectivity
- Check if local bundle exists: `ls registry/dist/oximy-bundle.json`
- Check cache: `cat ~/.oximy/bundle_cache.json | jq .bundle_version`

**Traffic not being captured**
- Verify proxy is configured: `networksetup -getwebproxy Wi-Fi`
- Verify CA is trusted: Check Keychain Access
- Check if domain is in bundle: `jq '.domain_lookup["api.openai.com"]' registry/dist/oximy-bundle.json`

**SSE content missing/incomplete**
- Check if SSEBuffer is created (look for "Setting up SSE buffer" log)
- Check raw chunks in debug logs
- Verify api_format matches expected SSE format

**Process attribution showing "Unknown"**
- Process may have exited before lookup
- Check if running as root (required for some process lookups)
- Try running: `lsof -i TCP:${PORT} -n -P`

### Inspecting Raw Traffic

```bash
# Use mitmweb for visual inspection
mitmweb -s mitmproxy/addons/oximy/addon.py \
        --set oximy_enabled=true \
        --listen-port 8088

# Then open http://127.0.0.1:8081 in browser
```

---

## Investigation Mode

Investigation Mode is a separate addon for raw traffic capture when analyzing new AI services, debugging parsing issues, or understanding how apps communicate with AI APIs.

### When to Use Investigation Mode

- **New service analysis**: Understanding how a new AI API or website works
- **Debugging**: When SSE parsing fails or content is missing
- **App discovery**: Seeing what AI calls apps like Cursor, Granola, or Slack make
- **Edge case hunting**: Finding unusual formats or patterns

### Quick Start

```bash
# Investigate ChatGPT traffic
mitmdump -s mitmproxy/addons/oximy/investigator.py \
         --set investigate_enabled=true \
         --set investigate_domains="chatgpt.com" \
         --listen-port 8088

# Investigate traffic from Cursor app
mitmdump -s mitmproxy/addons/oximy/investigator.py \
         --set investigate_enabled=true \
         --set investigate_apps="Cursor" \
         --listen-port 8088

# Investigate multiple apps
mitmdump -s mitmproxy/addons/oximy/investigator.py \
         --set investigate_enabled=true \
         --set investigate_apps="Cursor,Granola,Slack" \
         --listen-port 8088

# Capture ALL traffic (use with caution - high volume)
mitmdump -s mitmproxy/addons/oximy/investigator.py \
         --set investigate_enabled=true \
         --set investigate_capture_all=true \
         --listen-port 8088

# Custom output file
mitmdump -s mitmproxy/addons/oximy/investigator.py \
         --set investigate_enabled=true \
         --set investigate_domains="api.openai.com" \
         --set investigate_output="~/my-investigation.jsonl" \
         --listen-port 8088

# With session description (for notes)
mitmdump -s mitmproxy/addons/oximy/investigator.py \
         --set investigate_enabled=true \
         --set investigate_apps="Cursor" \
         --set investigate_description="Testing Cursor autocomplete feature" \
         --listen-port 8088
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `investigate_enabled` | bool | false | Enable investigation mode |
| `investigate_output` | str | auto | Output file (default: `~/.oximy/investigations/session_TIMESTAMP.jsonl`) |
| `investigate_domains` | str | "" | Comma-separated domains to capture |
| `investigate_apps` | str | "" | Comma-separated app names to capture |
| `investigate_capture_all` | bool | false | Capture all traffic (ignore filters) |
| `investigate_description` | str | "" | Description for this session |
| `investigate_include_matcher` | bool | true | Include production matcher results |

### Output Format

Investigation events preserve raw data that the production addon normalizes:

```json
{
  "event_id": "019ba940-1234-7abc-9012-345678901234",
  "timestamp": "2026-01-10T19:30:00.000Z",
  "session_id": "019ba940-0000-7abc-0000-000000000000",
  "flow_id": "abc123",

  "connection": {
    "host": "chatgpt.com",
    "url": "https://chatgpt.com/backend-api/conversation",
    "path": "/backend-api/conversation",
    "method": "POST",
    "scheme": "https"
  },

  "timing": {
    "duration_ms": 2500,
    "ttfb_ms": 800
  },

  "client": {
    "port": 54321,
    "pid": 12345,
    "name": "Comet Helper",
    "path": "/Applications/Comet.app/.../Comet Helper",
    "ppid": 1234,
    "parent_name": "Comet",
    "user": "username"
  },

  "request": {
    "headers": {
      "content-type": "application/json",
      "authorization": "Bearer ..."
    },
    "content_type": "application/json",
    "body_size": 1234,
    "body_truncated": false,
    "body_raw": "{\"action\":\"next\",\"messages\":[...]}",
    "body_parsed": {
      "action": "next",
      "messages": [...]
    }
  },

  "response": {
    "status": 200,
    "headers": {
      "content-type": "text/event-stream"
    },
    "content_type": "text/event-stream",
    "body_size": 5678,
    "body_truncated": false
  },

  "sse": {
    "is_sse": true,
    "chunk_count": 45,
    "chunks": [
      {
        "index": 0,
        "timestamp": "2026-01-10T19:30:00.800Z",
        "data_raw": "v1",
        "data_parsed": null,
        "delta_ms": 0,
        "size_bytes": 4
      },
      {
        "index": 1,
        "timestamp": "2026-01-10T19:30:00.815Z",
        "data_raw": "{\"v\":\"Hello\"}",
        "data_parsed": {"v": "Hello"},
        "delta_ms": 15,
        "size_bytes": 25
      },
      {
        "index": 2,
        "timestamp": "2026-01-10T19:30:00.830Z",
        "data_raw": "{\"v\":\" world\"}",
        "data_parsed": {"v": " world"},
        "delta_ms": 15,
        "size_bytes": 27
      }
    ],
    "reconstructed_content": "Hello world"
  },

  "match_attempt": {
    "classification": "full_trace",
    "source_type": "website",
    "source_id": "chatgpt",
    "api_format": "chatgpt_web",
    "endpoint": "chat",
    "match_reason": "website"
  },

  "parse_attempt": {
    "api_format": "chatgpt_web",
    "request_extracted": {
      "messages": [{"role": "user", "content": "Hello!"}],
      "model": "gpt-4"
    },
    "response_extracted": {
      "content": "Hello world"
    },
    "errors": []
  }
}
```

### Session Metadata

Each investigation session starts with a session metadata event:

```json
{
  "type": "session_start",
  "session_id": "019ba940-0000-7abc-0000-000000000000",
  "started_at": "2026-01-10T19:30:00.000Z",
  "description": "Testing Cursor autocomplete feature",
  "filters": {
    "domains": [],
    "apps": ["Cursor"],
    "capture_all": false
  }
}
```

### Analyzing Investigation Output

```bash
# View all events
cat ~/.oximy/investigations/session_*.jsonl | jq .

# View just SSE chunks
cat session_*.jsonl | jq 'select(.sse.is_sse == true) | .sse.chunks'

# Find events where parsing failed
cat session_*.jsonl | jq 'select(.parse_attempt.errors | length > 0)'

# See unique hosts captured
cat session_*.jsonl | jq -r '.connection.host' | sort | uniq -c

# Filter by app
cat session_*.jsonl | jq 'select(.client.parent_name == "Cursor")'

# View SSE chunk timing
cat session_*.jsonl | jq '.sse.chunks[] | {index, delta_ms, data_raw}'

# Find unmatched traffic (potential new providers)
cat session_*.jsonl | jq 'select(.match_attempt.classification == "drop") | .connection.host' | sort | uniq
```

### Investigation Workflow

#### 1. Start Investigation

```bash
# For a specific app
mitmdump -s investigator.py \
         --set investigate_enabled=true \
         --set investigate_apps="Cursor" \
         --set investigate_description="Investigating Cursor AI features"
```

#### 2. Use the App

- Open the app
- Trigger AI features (autocomplete, chat, etc.)
- Try different scenarios (short/long responses, errors, etc.)

#### 3. Stop and Analyze

```bash
# Stop mitmproxy (Ctrl+C)

# Look at the output
cat ~/.oximy/investigations/session_*.jsonl | jq .
```

#### 4. Identify Patterns

Look for:
- **Endpoints**: What URLs does the app call?
- **Request format**: How are messages structured?
- **Response format**: How is content returned?
- **SSE patterns**: What do the streaming chunks look like?

#### 5. Build Parser (if needed)

Based on observed patterns, create parser rules:

```json
{
  "cursor_api": {
    "request": {
      "messages": "$.messages",
      "model": "$.model"
    },
    "response": {
      "content": "$.choices[0].message.content",
      "model": "$.model"
    }
  }
}
```

#### 6. Add to Registry

Update the OISP bundle with new domain/parser definitions.

### Common Investigation Scenarios

#### Scenario: ChatGPT SSE Not Parsing

```bash
# Investigate ChatGPT
mitmdump -s investigator.py \
         --set investigate_enabled=true \
         --set investigate_domains="chatgpt.com"

# Look at SSE chunks
cat session_*.jsonl | jq '.sse.chunks[] | {index, data_raw, data_parsed}'

# Find chunks that didn't parse
cat session_*.jsonl | jq '.sse.chunks[] | select(.data_parsed == null)'
```

#### Scenario: Unknown App Making AI Calls

```bash
# Capture all traffic briefly
mitmdump -s investigator.py \
         --set investigate_enabled=true \
         --set investigate_capture_all=true

# Find AI-related hosts
cat session_*.jsonl | jq -r '.connection.host' | sort | uniq | grep -i ai

# Filter to specific host
cat session_*.jsonl | jq 'select(.connection.host | contains("api.")) | .connection'
```

#### Scenario: Process Attribution Not Working

```bash
# Check client info in captured events
cat session_*.jsonl | jq '{host: .connection.host, client: .client}'

# Find events with missing process info
cat session_*.jsonl | jq 'select(.client.name == null or .client.name == "Unknown (exited)")'
```

### Differences from Production Addon

| Feature | Production (`addon.py`) | Investigation (`investigator.py`) |
|---------|------------------------|-----------------------------------|
| Filtering | Registry-based | Domain/app configurable |
| Body storage | Parsed only | Raw + parsed |
| SSE handling | Reconstructed content | Individual chunks preserved |
| Headers | Not stored | Full headers stored |
| Parse errors | Silent | Logged with details |
| Output | Normalized events | Raw debug events |
| Use case | Production capture | Analysis & debugging |

### Module Files

| File | Purpose |
|------|---------|
| `investigator.py` | Main investigation addon |
| `investigator_types.py` | Data types (InvestigationEvent, SSEChunk, etc.) |

---

## File Locations

| File | Purpose |
|------|---------|
| `~/.oximy/traces/traces_YYYY-MM-DD.jsonl` | Captured events |
| `~/.oximy/bundle_cache.json` | Cached OISP bundle |
| `~/.oximy/traces/pinned_hosts.json` | Learned certificate-pinned hosts |
| `registry/dist/oximy-bundle.json` | Local bundle (development) |

---

## Development Tips

### Testing Changes

```bash
# Run with a specific test request
curl -x http://127.0.0.1:8088 https://api.openai.com/v1/chat/completions \
     -H "Authorization: Bearer $OPENAI_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"gpt-4","messages":[{"role":"user","content":"Hi"}]}'
```

### Reloading Addon

mitmproxy doesn't hot-reload addons. Restart the proxy to pick up changes.

### Local Bundle Development

1. Edit files in `registry/` directory
2. Build bundle: `cd registry && npm run build`
3. Restart mitmproxy (picks up local bundle automatically)

---

## Contributing

When adding new features:
1. Follow existing patterns (dataclasses, type hints)
2. Add logging at appropriate levels (debug for details, info for major events)
3. Update this documentation
4. Test with real traffic before submitting
