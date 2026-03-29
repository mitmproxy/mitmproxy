"""
Real-time detection of API keys, tokens, credentials in live traffic
with context-aware scoring, JSON-aware scanning, masking, and optional blocking.
"""

import json
import math
import re
from collections import Counter
from threading import Lock
from weakref import WeakKeyDictionary

from mitmproxy import ctx
from mitmproxy import http


class SecretLeakDetector:
    def __init__(self) -> None:
        self.secrets_found = 0
        self.lock = Lock()
        self.safe_paths = {"/health", "/metrics", "/static", "/favicon", "/robots.txt"}
        # Per-flow dedup tracked on the addon, not on the flow object (mypy-safe)
        self._seen: WeakKeyDictionary[http.HTTPFlow, set[tuple[str, str]]] = WeakKeyDictionary()

        # Updated patterns
        self.patterns = [
            (re.compile(r"sk-ant-api\d{2}-[a-zA-Z0-9_-]{86}"), "Anthropic API Key", 92),
            (re.compile(r"sk-proj-[a-zA-Z0-9_-]{48,}"), "OpenAI API Key (project)", 90),
            (re.compile(r"sk-[a-zA-Z0-9]{48}"), "OpenAI API Key (legacy)", 85),
            (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID", 85),
            (
                re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])"),
                "AWS Secret Access Key",
                65,
            ),
            (
                re.compile(
                    r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"
                ),
                "JWT Token",
                80,
            ),
            (re.compile(r"Bearer [a-zA-Z0-9_.-]{20,}"), "Bearer Token", 75),
            (re.compile(r"AIza[0-9A-Za-z_-]{35}"), "Google API Key", 70),
            (re.compile(r"ghp_[a-zA-Z0-9]{36,}"), "GitHub PAT", 70),
            (
                re.compile(r"github_pat_[a-zA-Z0-9_]{82,}"),
                "GitHub PAT (fine-grained)",
                88,
            ),
        ]

    def load(self, loader) -> None:
        loader.add_option(
            "secretleakdetector_block",
            bool,
            False,
            "Block high-confidence secret leaks",
        )
        loader.add_option(
            "secretleakdetector_threshold",
            str,
            "medium",
            "Minimum confidence to report (low/medium/high)",
        )

    def _calculate_entropy(self, s: str) -> float:
        if not s or len(s) < 8:
            return 0.0
        freq = Counter(s)
        return -sum(
            (count / len(s)) * math.log2(count / len(s))
            for count in freq.values()
            if count > 0
        )

    def _get_confidence(
        self, base_score: int, value: str, location: str, path: str
    ) -> int:
        score = base_score

        if any(
            x in location.lower()
            for x in ["authorization", "api-key", "token", "secret"]
        ):
            score += 15
        if any(x in path.lower() for x in ["/auth", "/api", "/login", "/token"]):
            score += 10
        if self._calculate_entropy(value) > 4.5:
            score += 10

        return min(score, 100)

    def _is_json(self, text: str) -> bool:
        text = text.strip()
        return (text.startswith("{") and text.endswith("}")) or (
            text.startswith("[") and text.endswith("]")
        )

    def _scan_json(
        self, data: dict | list, location_prefix: str, flow: http.HTTPFlow
    ) -> None:
        if isinstance(data, dict):
            for k, v in data.items():
                loc = f"{location_prefix} → {k}"
                if isinstance(v, (str, int, float)):
                    self._scan_value(str(v), loc, flow)
                elif isinstance(v, (dict, list)):
                    self._scan_json(v, loc, flow)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                loc = f"{location_prefix}[{i}]"
                if isinstance(item, (str, int, float)):
                    self._scan_value(str(item), loc, flow)
                else:
                    self._scan_json(item, loc, flow)

    def _scan_value(self, value: str, location: str, flow: http.HTTPFlow) -> None:
        if not value or len(value) < 8:
            return

        threshold = ctx.options.secretleakdetector_threshold
        block_enabled = ctx.options.secretleakdetector_block
        path = flow.request.path

        # JSON-aware scanning
        if self._is_json(value):
            try:
                parsed = json.loads(value)
                self._scan_json(parsed, f"{location} (JSON)", flow)
                return
            except json.JSONDecodeError:
                pass

        # Initialise per-flow seen set on the addon (mypy-safe, no monkey-patching)
        if flow not in self._seen:
            self._seen[flow] = set()
        seen = self._seen[flow]

        # Normal + multi-line scan
        for line in value.splitlines():
            line = line.strip()
            if not line:
                continue

            for pattern, name, base_score in self.patterns:
                match = pattern.search(line)
                if match:
                    full_match = match.group(0)
                    masked = full_match[:8] + "..." + full_match[-4:]

                    dedup_key = (name, masked)
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)

                    confidence = self._get_confidence(
                        base_score, full_match, location, path
                    )

                    if (threshold == "high" and confidence < 75) or (
                        threshold == "medium" and confidence < 60
                    ):
                        continue

                    with self.lock:
                        self.secrets_found += 1

                    # Structured logging
                    log_data = {
                        "event": "secret_leak_detected",
                        "secret_type": name,
                        "confidence": confidence,
                        "location": location,
                        "url": flow.request.pretty_url,
                        "masked_value": masked,
                    }
                    ctx.log.warn(json.dumps(log_data))

                    # Masking
                    if "request" in location.lower():
                        self._apply_mask(flow.request, location, full_match, masked)
                    elif flow.response is not None:
                        self._apply_mask(flow.response, location, full_match, masked)

                    # Blocking
                    if block_enabled and confidence >= 75:
                        if path in self.safe_paths:
                            ctx.log.info(f"[SAFE PATH] Skipped blocking for {path}")
                            continue

                        ctx.log.error(
                            json.dumps(
                                {
                                    "event": "secret_leak_blocked",
                                    "reason": "high-confidence leak",
                                    "url": flow.request.pretty_url,
                                }
                            )
                        )
                        flow.response = http.Response.make(
                            403, b"Secret leak detected and blocked by mitmproxy addon"
                        )
                        return

    def _apply_mask(
        self,
        obj: http.Request | http.Response,
        location: str,
        original: str,
        masked: str,
    ) -> None:
        if hasattr(obj, "headers") and "Header" in location:
            header_name = location.split(": ", 1)[1]
            if header_name in obj.headers:
                obj.headers[header_name] = obj.headers[header_name].replace(
                    original, masked
                )
        elif hasattr(obj, "content") and obj.content:
            try:
                text = obj.content.decode("utf-8", errors="ignore")
                text = text.replace(original, masked)
                obj.content = text.encode("utf-8")
            except Exception:
                pass

    def request(self, flow: http.HTTPFlow) -> None:
        for name, value in list(flow.request.headers.items()):
            self._scan_value(value, f"Request Header: {name}", flow)
        for name, value in flow.request.query.items():
            self._scan_value(value, f"Query: {name}", flow)
        if flow.request.content:
            if len(flow.request.content) >= 200_000:
                ctx.log.info(
                    f"[SKIPPED] Large request body ({len(flow.request.content)} bytes)"
                )
            else:
                self._scan_value(
                    flow.request.content.decode("utf-8", errors="ignore"),
                    "Request Body",
                    flow,
                )

    def response(self, flow: http.HTTPFlow) -> None:
        if flow.response is None:
            return
        for name, value in list(flow.response.headers.items()):
            self._scan_value(value, f"Response Header: {name}", flow)
        if flow.response.content:
            if len(flow.response.content) >= 200_000:
                ctx.log.info(
                    f"[SKIPPED] Large response body ({len(flow.response.content)} bytes)"
                )
            else:
                self._scan_value(
                    flow.response.content.decode("utf-8", errors="ignore"),
                    "Response Body",
                    flow,
                )


addons = [SecretLeakDetector()]
