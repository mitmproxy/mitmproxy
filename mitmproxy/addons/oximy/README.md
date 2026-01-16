# Oximy - AI Traffic Capture Addon for mitmproxy

Captures AI API traffic based on whitelist filtering, and writes to rotating JSONL files.

## Prerequisites: Certificate Setup (REQUIRED)

**IMPORTANT**: Before using Oximy, you MUST install and trust the CA certificate. Without this, HTTPS interception will fail.

### macOS

```bash
# 1. First, run mitmproxy once to generate the certificate
uv run mitmdump --mode regular@8080
# Press Ctrl+C after it starts

# 2. Install and trust the certificate (requires admin password)
sudo security add-trusted-cert -d -r trustRoot -p ssl \
  -k /Library/Keychains/System.keychain \
  ~/.mitmproxy/oximy-ca-cert.pem

# 3. Verify it worked
security verify-cert -c ~/.mitmproxy/oximy-ca-cert.pem
# Should output: "...certificate verification successful."
```

### Troubleshooting Certificate Issues

If you see `SSL certificate problem: unable to get local issuer certificate`:

1. **Check which CA is being used** - mitmproxy uses `oximy-ca-cert.pem`, NOT `mitmproxy-ca-cert.pem`
2. **Verify the cert is trusted with SSL policy**:
   ```bash
   security dump-trust-settings -d | grep -A5 oximy
   ```
3. **Re-install with `-p ssl` flag** (sets SSL trust policy):
   ```bash
   sudo security add-trusted-cert -d -r trustRoot -p ssl \
     -k /Library/Keychains/System.keychain \
     ~/.mitmproxy/oximy-ca-cert.pem
   ```

## Quick Start

```bash
# Start the proxy on port 8080
uv run mitmdump -s mitmproxy/addons/oximy/addon.py \
  --set oximy_enabled=true \
  --mode regular@8080

# In another terminal, test with curl (use system curl on macOS)
/usr/bin/curl -x http://localhost:8080 https://api.openai.com/v1/models

# Check captured events
cat ~/.oximy/traces/traces_$(date +%Y-%m-%d).jsonl | jq .
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `oximy_enabled` | `false` | Enable/disable capture |
| `oximy_output_dir` | `~/.oximy/traces` | Directory for JSONL files |
| `oximy_config` | `""` | Path to custom config.json |
| `oximy_verbose` | `false` | Enable debug logging |

## Viewing Logs

Logs are printed to stderr in real-time. You'll see:

```
[INFO] >>> POST api.openai.com/v1/chat/completions
[INFO] <<< CAPTURED: POST api.openai.com/v1/chat/completions [200]
```

For verbose logging:
```bash
uv run mitmdump -s mitmproxy/addons/oximy/addon.py \
  --set oximy_enabled=true \
  --set oximy_verbose=true \
  --mode regular@8080
```

## Supported Providers

Traffic is captured for domains in `whitelist.json`, including:

- **OpenAI**: `api.openai.com`, `chat.openai.com`, `chatgpt.com`
- **Anthropic**: `api.anthropic.com`, `claude.ai`
- **Google AI**: `generativelanguage.googleapis.com`, `gemini.google.com`
- **Perplexity**: `api.perplexity.ai`, `www.perplexity.ai`
- **Azure OpenAI**: `*.openai.azure.com`
- **AWS Bedrock**: `bedrock-runtime.*.amazonaws.com`
- **And more** (see `whitelist.json`)

## How It Works

1. **Startup**: Checks certificate trust, loads whitelist/blacklist, enables system proxy
2. **TLS Passthrough**: Certificate-pinned apps (Raycast, etc.) are auto-detected and bypassed
3. **Whitelist Filter**: Only captures traffic to known AI domains
4. **Blacklist Filter**: Drops requests/responses containing sensitive words
5. **Capture**: Writes HTTP and WebSocket traffic to JSONL files
6. **Cleanup**: Disables system proxy on shutdown

## Output Format

Events are written to daily JSONL files (`~/.oximy/traces/traces_YYYY-MM-DD.jsonl`):

```json
{
  "event_id": "019ba454-e7b4-7600-9e5e-376227eb454e",
  "timestamp": "2026-01-09T19:56:26.420Z",
  "type": "http",
  "request": {
    "method": "POST",
    "host": "api.openai.com",
    "path": "/v1/chat/completions",
    "headers": {...},
    "body": "{...}"
  },
  "response": {
    "status_code": 200,
    "headers": {...},
    "body": "{...}"
  },
  "timing": {
    "duration_ms": 1234,
    "ttfb_ms": 456
  }
}
```

## Files

- `addon.py` - Main addon with all logic
- `whitelist.json` - Domains to capture
- `blacklist.json` - Words to filter out
- `passthrough.json` - Certificate-pinned hosts (auto-populated)
- `config.json` - Output configuration

## Common Issues

### "Client does not trust the proxy's certificate"
The certificate isn't installed or trusted. See [Certificate Setup](#prerequisites-certificate-setup-required).

### Apps like Raycast/Apple services fail
These apps use certificate pinning. The addon auto-detects this and adds them to `passthrough.json` so they bypass interception.

### curl works with `-k` but not without
The certificate is installed but not trusted for SSL. Re-run with `-p ssl`:
```bash
sudo security add-trusted-cert -d -r trustRoot -p ssl \
  -k /Library/Keychains/System.keychain \
  ~/.mitmproxy/oximy-ca-cert.pem
```

### Homebrew/Anaconda curl fails but system curl works
Non-system curl uses OpenSSL which doesn't read macOS Keychain. Use `/usr/bin/curl` or add the cert to OpenSSL's trust store.
