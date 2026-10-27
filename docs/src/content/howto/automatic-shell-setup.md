---
title: "Automatic shell environment setup"
weight: 2
aliases:
  - /howto-automatic-shell-setup/
---

# Automatic Shell Environment Setup

Instead of manually configuring proxy settings in your shell, mitmproxy provides automatic setup endpoints that generate shell configuration scripts for different shells. These scripts configure environment variables for the proxy, certificates, and other tools.

## Quick Start

Replace `127.0.0.1:8080` with your actual mitmproxy address and port.

### Bash/Zsh/Ksh
```bash
eval "$(curl -sS http://127.0.0.1:8080/setup.sh)"
```

### Fish
```bash
source (curl -sS http://127.0.0.1:8080/setup.fish | psub)
```

### PowerShell
```powershell
. (curl -Uri http://127.0.0.1:8080/setup.ps1).Content
```

## Available Endpoints

The setup endpoints are available on any proxy address/port where mitmproxy is listening:

| Endpoint | Format | Shell | Description |
|----------|--------|-------|-------------|
| `/setup` | JSON | - | Returns proxy configuration and certificate paths as JSON |
| `/setup.sh` | Bash | bash/sh | Shell script with environment variables and winpty aliases |
| `/setup.fish` | Fish | fish | Fish shell script with environment variables and aliases |
| `/setup.ps1` | PowerShell | pwsh | PowerShell script with `Stop-Intercepting` function |

## What Gets Configured

These setup scripts automatically export environment variables for:

### Proxy Configuration
- Standard: `HTTP_PROXY`, `HTTPS_PROXY`, `http_proxy`, `https_proxy`
- WebSocket: `WS_PROXY`, `WSS_PROXY`
- Tool-specific: `npm_config_proxy`, `GLOBAL_AGENT_HTTP_PROXY`, `CGI_HTTP_PROXY`

### Certificate Trust
Paths are set for multiple tools to trust the mitmproxy CA certificate:
- `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`
- `NODE_EXTRA_CA_CERTS`, `DENO_CERT`
- `GIT_SSL_CAINFO`, `CARGO_HTTP_CAINFO`, `AWS_CA_BUNDLE`, `PERL_LWP_SSL_CA_FILE`

### Status Indicator
- `MITMPROXY_ACTIVE=true` indicates that mitmproxy interception is active

## Stopping Interception

### Bash/Fish
Close your shell or manually unset the environment variables:
```bash
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy WS_PROXY WSS_PROXY \
      npm_config_proxy GLOBAL_AGENT_HTTP_PROXY CGI_HTTP_PROXY \
      SSL_CERT_FILE REQUESTS_CA_BUNDLE CURL_CA_BUNDLE NODE_EXTRA_CA_CERTS \
      DENO_CERT GIT_SSL_CAINFO CARGO_HTTP_CAINFO AWS_CA_BUNDLE \
      PERL_LWP_SSL_CA_FILE MITMPROXY_ACTIVE
```

### PowerShell
Use the `Stop-Intercepting` function:
```powershell
Stop-Intercepting
```

## Programmatic Access

If you need to retrieve the configuration programmatically (e.g., in a script or application):

```bash
curl -sS http://127.0.0.1:8080/setup | jq
```

This returns a JSON object with:
```json
{
  "proxy_url": "127.0.0.1:8080",
  "proxy_host": "127.0.0.1",
  "proxy_port": 8080,
  "certificates": {
    "pem": "~/.mitmproxy/mitmproxy-ca-cert.pem",
    "p12": "~/.mitmproxy/mitmproxy-ca-cert.p12",
    "cer": "~/.mitmproxy/mitmproxy-ca-cert.cer"
  },
  "setup_scripts": {
    "sh": "http://127.0.0.1:8080/setup.sh",
    "bash": "http://127.0.0.1:8080/setup.sh",
    "zsh": "http://127.0.0.1:8080/setup.sh",
    "ksh": "http://127.0.0.1:8080/setup.sh",
    "fish": "http://127.0.0.1:8080/setup.fish",
    "powershell": "http://127.0.0.1:8080/setup.ps1",
    "pwsh": "http://127.0.0.1:8080/setup.ps1"
  }
}
```

## Configuration Requirements

For automatic setup to work:

1. **mitmproxy must be running** - Start mitmproxy with `mitmproxy`, `mitmweb`, or `mitmdump`
2. **Access the proxy directly** - Request the setup endpoints from the proxy's IP/port (e.g., `http://127.0.0.1:8080/setup.sh`)

For example, if mitmproxy is running on `127.0.0.1:8080`:
```bash
eval "$(curl -sS http://127.0.0.1:8080/setup.sh)"
```

Or if your mitmproxy instance is on a remote machine:
```bash
eval "$(curl -sS http://remote-proxy:8080/setup.sh)"
```
