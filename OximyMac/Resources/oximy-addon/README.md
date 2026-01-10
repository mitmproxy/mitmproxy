# Oximy - AI Traffic Capture Addon for mitmproxy

Captures AI API traffic based on the [OISP bundle](https://oisp.dev) whitelist, normalizes events, and writes to rotating JSONL files.

## Quick Start

```bash
# Start the proxy on port 8088 (avoiding common port 8080)
uv run mitmdump -s mitmproxy/addons/oximy/addon.py \
  --set oximy_enabled=true \
  --mode regular@8088

# In another terminal, test with curl
curl -x http://localhost:8088 -k \
  -X POST https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"Hello"}]}'

# Check captured events
cat ~/.oximy/traces/traces_$(date +%Y-%m-%d).jsonl | jq .
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `oximy_enabled` | `false` | Enable/disable capture |
| `oximy_output_dir` | `~/.oximy/traces` | Directory for JSONL files |
| `oximy_bundle_url` | `https://oisp.dev/spec/v0.1/oisp-spec-bundle.json` | OISP bundle URL |
| `oximy_bundle_refresh_hours` | `24` | Cache refresh interval |
| `oximy_include_raw` | `true` | Include raw request/response bodies |

## Supported Providers

Traffic is captured for any domain in the OISP bundle, including:

- **OpenAI**: `api.openai.com`
- **Anthropic**: `api.anthropic.com`
- **Google AI**: `generativelanguage.googleapis.com`
- **Perplexity**: `api.perplexity.ai` (used by Comet app)
- **Azure OpenAI**: `*.openai.azure.com`
- **AWS Bedrock**: `bedrock-runtime.*.amazonaws.com`
- **And 60+ more providers**

## Supported Apps

The OISP bundle includes app signatures for process attribution:

| App | Vendor | Bundle ID |
|-----|--------|-----------|
| Comet | Perplexity AI | `ai.perplexity.comet` |
| Granola | Granola | `com.granola.app` |
| Cursor | Cursor | (varies) |
| And more... | | |

## Using with Apps (Comet, Granola, etc.)

For desktop apps, use `--mode local` to capture traffic from specific processes:

```bash
# Capture all traffic from your machine (requires sudo on macOS)
sudo uv run mitmdump -s mitmproxy/addons/oximy/addon.py \
  --set oximy_enabled=true \
  --mode local

# Or set system proxy manually and run on port 8088
uv run mitmdump -s mitmproxy/addons/oximy/addon.py \
  --set oximy_enabled=true \
  --mode regular@8088
```

Then configure your system proxy to `localhost:8088`.

## Output Format

Events are written to daily JSONL files (`traces_YYYY-MM-DD.jsonl`):

```json
{
  "event_id": "019ba454-e7b4-7600-9e5e-376227eb454e",
  "timestamp": "2026-01-09T19:56:26.420Z",
  "source": {
    "type": "api",
    "id": "openai",
    "endpoint": null
  },
  "trace_level": "full",
  "timing": {
    "duration_ms": 1234,
    "ttfb_ms": 456
  },
  "interaction": {
    "model": "gpt-4",
    "provider": "openai",
    "request": {
      "messages": [{"role": "user", "content": "Hello"}],
      "model": "gpt-4"
    },
    "response": {
      "content": "Hi there!",
      "model": "gpt-4",
      "usage": {"input_tokens": 5, "output_tokens": 3}
    }
  }
}
```

## Traffic Classification

| Classification | Description | What's Logged |
|----------------|-------------|---------------|
| `full_trace` | Known AI API with parser | Full request/response |
| `identifiable` | Known domain, no parser | Metadata only |
| `drop` | Unknown domain | Nothing (silently dropped) |

## Programmatic Usage

```python
from mitmproxy.addons.oximy import OximyAddon

# Add to your mitmproxy script
addons = [OximyAddon()]
```

## Example Scripts

See `example.py` for a demo that:
1. Starts mitmproxy programmatically
2. Makes test requests to OpenAI
3. Shows captured events

```bash
# Run the example (requires OPENAI_API_KEY)
uv run python mitmproxy/addons/oximy/example.py
```

## Files

- `addon.py` - Main addon entry point
- `bundle.py` - OISP bundle loading with caching
- `matcher.py` - Traffic classification logic
- `parser.py` - Request/response parsing (JSONPath extraction)
- `writer.py` - JSONL file writer with daily rotation
- `sse.py` - SSE streaming response handler
- `types.py` - Data structures
