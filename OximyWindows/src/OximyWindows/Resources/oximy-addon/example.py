#!/usr/bin/env python3
"""
Oximy Example - Demonstrates AI traffic capture with mitmproxy.

This script:
1. Starts mitmproxy in a background thread
2. Makes test requests to OpenAI through the proxy
3. Displays the captured events

Usage:
    # Set your API key first
    export OPENAI_API_KEY=sk-...

    # Run the example
    uv run python mitmproxy/addons/oximy/example.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

# Add parent paths for imports when running standalone
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def run_proxy(output_dir: Path, port: int = 8088, ready_event: threading.Event | None = None):
    """Run mitmproxy in a new event loop (for threading)."""
    import asyncio

    from mitmproxy import options
    from mitmproxy.tools import dump

    from mitmproxy.addons.oximy import OximyAddon

    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    opts = options.Options(
        listen_port=port,
        ssl_insecure=True,  # Don't verify upstream certs for demo
    )

    master = dump.DumpMaster(
        opts,
        loop=loop,
        with_termlog=False,  # Quiet mode
    )

    # Add our addon
    addon = OximyAddon()
    master.addons.add(addon)

    # Configure options
    opts.update(
        oximy_enabled=True,
        oximy_output_dir=str(output_dir),
        oximy_include_raw=True,
    )

    if ready_event:
        # Signal that proxy is ready after a short delay
        def signal_ready():
            time.sleep(1)
            ready_event.set()
        threading.Thread(target=signal_ready, daemon=True).start()

    try:
        loop.run_until_complete(master.run())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


def make_openai_request(api_key: str, proxy_port: int = 8088) -> dict:
    """Make a test request to OpenAI through the proxy."""
    import ssl
    import urllib.error
    import urllib.request

    # Create proxy handler
    proxy_handler = urllib.request.ProxyHandler({
        'http': f'http://localhost:{proxy_port}',
        'https': f'http://localhost:{proxy_port}',
    })

    # Create SSL context that doesn't verify (for mitmproxy)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    https_handler = urllib.request.HTTPSHandler(context=ssl_context)
    opener = urllib.request.build_opener(proxy_handler, https_handler)

    # Build request
    url = "https://api.openai.com/v1/chat/completions"
    data = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": "Say 'Hello from Oximy!' in exactly 5 words."}
        ],
        "max_tokens": 50,
    }).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with opener.open(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode('utf-8'), "status": e.code}
    except Exception as e:
        return {"error": str(e)}


def read_captured_events(output_dir: Path) -> list[dict]:
    """Read all captured events from JSONL files."""
    events = []
    for jsonl_file in output_dir.glob("*.jsonl"):
        with open(jsonl_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return events


def main():
    print("=" * 60)
    print("Oximy Example - AI Traffic Capture Demo")
    print("=" * 60)
    print()

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print()
        print("To run this example:")
        print("  export OPENAI_API_KEY=sk-...")
        print("  uv run python mitmproxy/addons/oximy/example.py")
        sys.exit(1)

    # Create temp directory for output
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        port = 8088

        print(f"[1/4] Starting mitmproxy on port {port}...")

        # Start proxy in background thread
        ready_event = threading.Event()
        proxy_thread = threading.Thread(
            target=run_proxy,
            args=(output_dir, port, ready_event),
            daemon=True,
        )
        proxy_thread.start()

        # Wait for proxy to be ready
        if not ready_event.wait(timeout=10):
            print("ERROR: Proxy failed to start")
            sys.exit(1)

        print(f"    Proxy running at http://localhost:{port}")
        print()

        print("[2/4] Making request to OpenAI...")
        print("    POST https://api.openai.com/v1/chat/completions")
        print("    Model: gpt-4o-mini")
        print("    Prompt: \"Say 'Hello from Oximy!' in exactly 5 words.\"")
        print()

        response = make_openai_request(api_key, port)

        if "error" in response:
            print(f"    Response: ERROR - {response}")
        else:
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            model = response.get("model", "unknown")
            usage = response.get("usage", {})
            print(f"    Response: \"{content}\"")
            print(f"    Model: {model}")
            print(f"    Tokens: {usage.get('prompt_tokens', '?')} in, {usage.get('completion_tokens', '?')} out")
        print()

        # Give writer time to flush
        time.sleep(0.5)

        print("[3/4] Reading captured events...")
        events = read_captured_events(output_dir)
        print(f"    Found {len(events)} event(s)")
        print()

        print("[4/4] Captured Event Details:")
        print("-" * 60)

        for i, event in enumerate(events, 1):
            print(f"\nEvent #{i}:")
            print(f"  ID: {event.get('event_id', 'unknown')}")
            print(f"  Timestamp: {event.get('timestamp', 'unknown')}")
            print(f"  Source: {event.get('source', {}).get('id', 'unknown')}")
            print(f"  Trace Level: {event.get('trace_level', 'unknown')}")

            timing = event.get("timing", {})
            if timing.get("duration_ms"):
                print(f"  Duration: {timing['duration_ms']}ms")
            if timing.get("ttfb_ms"):
                print(f"  Time to First Byte: {timing['ttfb_ms']}ms")

            interaction = event.get("interaction", {})
            if interaction:
                print(f"  Provider: {interaction.get('provider', 'unknown')}")
                print(f"  Model: {interaction.get('model', 'unknown')}")

                req = interaction.get("request", {})
                if req.get("messages"):
                    msg = req["messages"][0] if req["messages"] else {}
                    content_text = msg.get('content', '')
                    if len(content_text) > 50:
                        print(f"  Request: \"{content_text[:50]}...\"")
                    else:
                        print(f"  Request: \"{content_text}\"")

                resp = interaction.get("response", {})
                resp_content = resp.get("content", "")
                if resp_content:
                    if len(resp_content) > 50:
                        print(f"  Response: \"{resp_content[:50]}...\"")
                    else:
                        print(f"  Response: \"{resp_content}\"")

                usage = resp.get("usage", {})
                if usage:
                    print(f"  Usage: {usage.get('input_tokens', '?')} input, {usage.get('output_tokens', '?')} output tokens")

        print()
        print("-" * 60)
        print()
        print("Full event JSON:")
        print()
        for event in events:
            print(json.dumps(event, indent=2))

        print()
        print("=" * 60)
        print("Demo complete!")
        print()
        print("To capture traffic from real apps like Comet or Granola:")
        print()
        print("  # Start proxy")
        print("  uv run mitmdump -s mitmproxy/addons/oximy/addon.py \\")
        print("    --set oximy_enabled=true --mode regular@8088")
        print()
        print("  # Set system proxy to localhost:8088")
        print("  # Then use your AI apps normally")
        print()
        print("  # View captured events")
        print("  cat ~/.oximy/traces/traces_$(date +%Y-%m-%d).jsonl | jq .")
        print("=" * 60)


if __name__ == "__main__":
    main()
