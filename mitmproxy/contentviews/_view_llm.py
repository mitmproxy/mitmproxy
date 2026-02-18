"""
Content viewers for LLM API requests and responses.

Supports Anthropic Claude and OpenAI (including compatible endpoints) protocols.
- LLM Request: Formats JSON request bodies showing model/system/messages/tools
- LLM Response: Parses SSE streaming responses, reconstructs complete messages
"""

from __future__ import annotations

import json
import re
from typing import Any

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.http import HTTPFlow

# URL patterns for known LLM API endpoints
_ANTHROPIC_PATTERNS = [
    re.compile(r"/v1/messages"),
]
_OPENAI_PATTERNS = [
    re.compile(r"/v1/chat/completions"),
]
_LLM_PATH_PATTERNS = _ANTHROPIC_PATTERNS + _OPENAI_PATTERNS


def _get_request_path(metadata: Metadata) -> str | None:
    if isinstance(metadata.flow, HTTPFlow):
        return metadata.flow.request.path
    return None


def is_llm_api_path(path: str) -> bool:
    """Check if the given URL path matches any known LLM API endpoint pattern."""
    return any(p.search(path) for p in _LLM_PATH_PATTERNS)


def detect_provider_from_path(path: str) -> str | None:
    """Detect the LLM provider ("anthropic" or "openai") from the URL path.

    Returns None if the path matches both or neither provider.
    """
    if any(p.search(path) for p in _ANTHROPIC_PATTERNS):
        if any(p.search(path) for p in _OPENAI_PATTERNS):
            return None
        return "anthropic"
    if any(p.search(path) for p in _OPENAI_PATTERNS):
        return "openai"
    return None


def _detect_provider(metadata: Metadata) -> str | None:
    """Detect the LLM provider from the flow's request path in metadata."""
    path = _get_request_path(metadata)
    if path is None:
        return None
    return detect_provider_from_path(path)


def _detect_provider_from_body(data: dict[str, Any]) -> str | None:
    """Infer the LLM provider by inspecting the request body structure and model name."""
    if "messages" not in data:
        return None
    messages = data.get("messages", [])
    if isinstance(messages, list) and messages:
        first = messages[0]
        if isinstance(first, dict):
            content = first.get("content")
            if isinstance(content, list):
                return "anthropic"
    if "model" in data:
        model = data["model"]
        if isinstance(model, str):
            if "claude" in model.lower():
                return "anthropic"
            if any(
                k in model.lower()
                for k in ("gpt", "o1", "o3", "o4", "chatgpt", "davinci")
            ):
                return "openai"
    return None


def _detect_provider_from_sse(events: list[dict[str, Any]]) -> str | None:
    """Infer the LLM provider from SSE event types and payload structure."""
    for ev in events:
        event_type = ev.get("event")
        parsed = ev.get("parsedData")
        if event_type in (
            "message_start",
            "content_block_start",
            "content_block_delta",
            "content_block_stop",
            "message_delta",
            "message_stop",
        ):
            return "anthropic"
        if isinstance(parsed, dict):
            if parsed.get("object") in ("chat.completion", "chat.completion.chunk"):
                return "openai"
            if "choices" in parsed:
                return "openai"
    return None


# --- SSE Parsing ---


def parse_sse_events(data: bytes) -> list[dict[str, Any]]:
    """Parse raw SSE (Server-Sent Events) bytes into a list of event dicts.

    Each event dict contains keys: "event", "data", "parsedData", "id".
    JSON data fields are automatically parsed into Python objects.
    """
    text = data.decode("utf-8", errors="replace")
    lines = text.split("\n")
    events: list[dict[str, Any]] = []

    current_event: str | None = None
    current_data_parts: list[str] = []
    current_id: str | None = None
    has_content = False

    for line in lines:
        if line.startswith(":"):
            continue

        if line == "" or line == "\r":
            if has_content:
                data_str = "\n".join(current_data_parts)
                parsed_data: Any = None
                if data_str:
                    try:
                        parsed_data = json.loads(data_str)
                    except (json.JSONDecodeError, ValueError):
                        parsed_data = data_str
                events.append(
                    {
                        "event": current_event or "message",
                        "data": data_str,
                        "parsedData": parsed_data,
                        "id": current_id,
                    }
                )
                current_event = None
                current_data_parts = []
                current_id = None
                has_content = False
            continue

        line = line.rstrip("\r")

        if line.startswith("event:"):
            current_event = line[6:].strip()
            has_content = True
        elif line.startswith("data:"):
            data_part = line[5:]
            if data_part.startswith(" "):
                data_part = data_part[1:]
            current_data_parts.append(data_part)
            has_content = True
        elif line.startswith("id:"):
            current_id = line[3:].strip()
            has_content = True

    if has_content:
        data_str = "\n".join(current_data_parts)
        parsed_data = None
        if data_str:
            try:
                parsed_data = json.loads(data_str)
            except (json.JSONDecodeError, ValueError):
                parsed_data = data_str
        events.append(
            {
                "event": current_event or "message",
                "data": data_str,
                "parsedData": parsed_data,
                "id": current_id,
            }
        )

    return events


# --- Anthropic Message Reconstruction ---


def _reconstruct_anthropic(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Reconstruct a complete Anthropic message from streaming SSE events."""
    state: dict[str, Any] = {
        "blocks": [],
        "usage": None,
        "model": None,
        "stop_reason": None,
        "role": None,
    }

    for ev in events:
        parsed = ev.get("parsedData")
        if not isinstance(parsed, dict):
            continue

        event_type = parsed.get("type") or ev.get("event")

        if event_type == "message_start":
            msg = parsed.get("message", {})
            state["model"] = msg.get("model")
            state["role"] = msg.get("role")
            state["usage"] = msg.get("usage")

        elif event_type == "content_block_start":
            idx = parsed.get("index", len(state["blocks"]))
            block_info = parsed.get("content_block", {})
            block: dict[str, Any] = {
                "type": block_info.get("type", "text"),
                "content": "",
                "id": block_info.get("id"),
                "name": block_info.get("name"),
                "input": "",
                "signature": "",
                "tool_use_id": block_info.get("tool_use_id"),
                "caller": block_info.get("caller"),
                "block_content": block_info.get("content"),
                "citations": block_info.get("citations"),
            }
            while len(state["blocks"]) <= idx:
                state["blocks"].append(None)
            state["blocks"][idx] = block

        elif event_type == "content_block_delta":
            idx = parsed.get("index", 0)
            if idx < len(state["blocks"]) and state["blocks"][idx] is not None:
                block = state["blocks"][idx]
                delta = parsed.get("delta", {})
                delta_type = delta.get("type", "")
                if delta_type == "thinking_delta":
                    block["content"] += delta.get("thinking", "")
                elif delta_type == "text_delta":
                    block["content"] += delta.get("text", "")
                elif delta_type == "input_json_delta":
                    block["input"] += delta.get("partial_json", "")
                elif delta_type == "signature_delta":
                    block["signature"] = delta.get("signature", "")
                elif delta_type == "citations_delta":
                    citation = delta.get("citation")
                    if citation and isinstance(block.get("citations"), list):
                        block["citations"].append(citation)

        elif event_type == "content_block_stop":
            idx = parsed.get("index", 0)
            if idx < len(state["blocks"]) and state["blocks"][idx] is not None:
                block = state["blocks"][idx]
                if block["type"] in ("tool_use", "server_tool_use") and block["input"]:
                    try:
                        block["input"] = json.loads(block["input"])
                    except (json.JSONDecodeError, ValueError):
                        pass

        elif event_type == "message_delta":
            delta = parsed.get("delta", {})
            if "stop_reason" in delta:
                state["stop_reason"] = delta["stop_reason"]
            if parsed.get("usage"):
                if state["usage"] is None:
                    state["usage"] = {}
                state["usage"].update(parsed["usage"])

    state["blocks"] = [b for b in state["blocks"] if b is not None]
    return state


# --- OpenAI Message Reconstruction ---


def _reconstruct_openai(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Reconstruct a complete OpenAI message from streaming SSE events."""
    state: dict[str, Any] = {
        "content": "",
        "tool_calls": [],
        "model": None,
        "finish_reason": None,
        "usage": None,
        "role": None,
    }

    tool_call_map: dict[int, dict[str, Any]] = {}

    for ev in events:
        parsed = ev.get("parsedData")
        if not isinstance(parsed, dict):
            continue

        if parsed.get("model"):
            state["model"] = parsed["model"]

        if parsed.get("usage"):
            state["usage"] = parsed["usage"]

        choices = parsed.get("choices", [])
        for choice in choices:
            if not isinstance(choice, dict):
                continue

            if choice.get("finish_reason"):
                state["finish_reason"] = choice["finish_reason"]

            delta = choice.get("delta", {})
            if not isinstance(delta, dict):
                continue

            if delta.get("role"):
                state["role"] = delta["role"]

            if delta.get("content"):
                state["content"] += delta["content"]

            for tc in delta.get("tool_calls", []):
                if not isinstance(tc, dict):
                    continue
                idx = tc.get("index", 0)
                if idx not in tool_call_map:
                    tool_call_map[idx] = {
                        "id": tc.get("id", ""),
                        "type": tc.get("type", "function"),
                        "function": {
                            "name": "",
                            "arguments": "",
                        },
                    }
                entry = tool_call_map[idx]
                if tc.get("id"):
                    entry["id"] = tc["id"]
                func = tc.get("function", {})
                if isinstance(func, dict):
                    if func.get("name"):
                        entry["function"]["name"] = func["name"]
                    if func.get("arguments"):
                        entry["function"]["arguments"] += func["arguments"]

    state["tool_calls"] = [tool_call_map[k] for k in sorted(tool_call_map)]
    for tc in state["tool_calls"]:
        args_str = tc["function"]["arguments"]
        if args_str:
            try:
                tc["function"]["arguments"] = json.loads(args_str)
            except (json.JSONDecodeError, ValueError):
                pass

    return state


# --- Request Formatting ---


def _format_request_anthropic(data: dict[str, Any]) -> str:
    """Format an Anthropic request body into a human-readable text view."""
    lines: list[str] = []

    model = data.get("model", "unknown")
    lines.append(f"[LLM Request] Anthropic {model}")
    lines.append("")

    system = data.get("system")
    if system:
        lines.append("System:")
        if isinstance(system, str):
            lines.append(f"  {system}")
        elif isinstance(system, list):
            for block in system:
                if isinstance(block, dict):
                    text = block.get("text", "")
                    block_type = block.get("type", "text")
                    if block_type == "text":
                        lines.append(f"  {text}")
                    else:
                        lines.append(f"  [{block_type}] {text}")
        lines.append("")

    messages = data.get("messages", [])
    if messages:
        lines.append("Messages:")
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"  [{i + 1}] {role}:")
            if isinstance(content, str):
                for cline in content.split("\n"):
                    lines.append(f"      {cline}")
            elif isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    ptype = part.get("type", "text")
                    if ptype == "text":
                        text = part.get("text", "")
                        for cline in text.split("\n"):
                            lines.append(f"      {cline}")
                    elif ptype == "tool_use":
                        lines.append(
                            f"      [tool_use] {part.get('name', '')} ({part.get('id', '')})"
                        )
                        inp = part.get("input", {})
                        lines.append(f"        {json.dumps(inp, ensure_ascii=False)}")
                    elif ptype == "tool_result":
                        lines.append(
                            f"      [tool_result] tool_use_id={part.get('tool_use_id', '')}"
                        )
                        result_content = part.get("content", "")
                        if isinstance(result_content, str):
                            lines.append(f"        {result_content}")
                        elif isinstance(result_content, list):
                            for rc in result_content:
                                if isinstance(rc, dict):
                                    lines.append(
                                        f"        [{rc.get('type', '')}] {rc.get('text', '')}"
                                    )
                    elif ptype == "image":
                        lines.append("      [image]")
                    else:
                        text = str(part.get("text", part.get("thinking", "")))
                        lines.append(f"      [{ptype}] {text[:100]}")
        lines.append("")

    tools = data.get("tools", [])
    if tools:
        lines.append("Tools:")
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            name = tool.get("name", "")
            desc = tool.get("description", "")
            lines.append(f"  - {name}: {desc}")
        lines.append("")

    lines.append("Parameters:")
    for key in (
        "max_tokens",
        "temperature",
        "top_p",
        "top_k",
        "stop_sequences",
        "stream",
    ):
        if key in data:
            lines.append(f"  {key}: {data[key]}")

    return "\n".join(lines)


def _format_request_openai(data: dict[str, Any]) -> str:
    """Format an OpenAI request body into a human-readable text view."""
    lines: list[str] = []

    model = data.get("model", "unknown")
    lines.append(f"[LLM Request] OpenAI {model}")
    lines.append("")

    messages = data.get("messages", [])
    if messages:
        lines.append("Messages:")
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"  [{i + 1}] {role}:")
            if isinstance(content, str):
                for cline in content.split("\n"):
                    lines.append(f"      {cline}")
            elif isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    ptype = part.get("type", "text")
                    if ptype == "text":
                        for cline in part.get("text", "").split("\n"):
                            lines.append(f"      {cline}")
                    elif ptype == "image_url":
                        lines.append("      [image_url]")
                    else:
                        lines.append(f"      [{ptype}]")

            tool_calls = msg.get("tool_calls", [])
            for tc in tool_calls:
                if isinstance(tc, dict):
                    func = tc.get("function", {})
                    lines.append(
                        f"      [tool_call] {func.get('name', '')} ({tc.get('id', '')})"
                    )
                    args = func.get("arguments", "")
                    if isinstance(args, str) and args:
                        lines.append(f"        {args}")
                    elif isinstance(args, dict):
                        lines.append(f"        {json.dumps(args, ensure_ascii=False)}")
        lines.append("")

    tools = data.get("tools", [])
    if tools:
        lines.append("Tools:")
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            func = tool.get("function", {})
            if isinstance(func, dict):
                name = func.get("name", "")
                desc = func.get("description", "")
                lines.append(f"  - {name}: {desc}")
        lines.append("")

    lines.append("Parameters:")
    for key in (
        "max_tokens",
        "max_completion_tokens",
        "temperature",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "stop",
        "stream",
    ):
        if key in data:
            lines.append(f"  {key}: {data[key]}")

    return "\n".join(lines)


# --- Response Formatting ---


def _format_response_anthropic(msg: dict[str, Any]) -> str:
    """Format a reconstructed Anthropic response into a human-readable text view."""
    lines: list[str] = []

    model = msg.get("model", "unknown")
    lines.append(f"[LLM Response] Anthropic {model}")
    lines.append("")

    blocks = msg.get("blocks", [])
    if blocks:
        lines.append("Content:")
        for block in blocks:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "text")
            content = block.get("content", "")

            if btype == "thinking":
                lines.append("  [thinking]")
                for cline in content.split("\n"):
                    lines.append(f"    {cline}")
            elif btype == "text":
                lines.append("  [text]")
                for cline in content.split("\n"):
                    lines.append(f"    {cline}")
            elif btype == "tool_use":
                name = block.get("name", "")
                block_id = block.get("id", "")
                lines.append(f"  [tool_use] {name} ({block_id})")
                inp = block.get("input", "")
                if isinstance(inp, dict):
                    lines.append(f"    {json.dumps(inp, ensure_ascii=False)}")
                elif isinstance(inp, str) and inp:
                    lines.append(f"    {inp}")
            elif btype == "server_tool_use":
                name = block.get("name", "")
                block_id = block.get("id", "")
                lines.append(f"  [server_tool_use] {name} ({block_id})")
                inp = block.get("input", "")
                if isinstance(inp, dict):
                    lines.append(f"    {json.dumps(inp, ensure_ascii=False)}")
                elif isinstance(inp, str) and inp:
                    lines.append(f"    {inp}")
            elif btype == "web_search_tool_result":
                tool_use_id = block.get("tool_use_id", "")
                lines.append(f"  [web_search_tool_result] tool_use_id={tool_use_id}")
                bc = block.get("block_content")
                if isinstance(bc, list):
                    for result in bc:
                        if isinstance(result, dict):
                            title = result.get("title", "")
                            url = result.get("url", "")
                            lines.append(f"    - {title}")
                            lines.append(f"      {url}")
            else:
                lines.append(f"  [{btype}]")
                if content:
                    lines.append(f"    {content}")
        lines.append("")

    stop_reason = msg.get("stop_reason")
    if stop_reason:
        lines.append(f"Stop Reason: {stop_reason}")
        lines.append("")

    usage = msg.get("usage")
    if isinstance(usage, dict) and usage:
        lines.append("Usage:")
        for key, value in usage.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


def _format_response_openai(msg: dict[str, Any]) -> str:
    """Format a reconstructed OpenAI response into a human-readable text view."""
    lines: list[str] = []

    model = msg.get("model", "unknown")
    lines.append(f"[LLM Response] OpenAI {model}")
    lines.append("")

    content = msg.get("content", "")
    if content:
        lines.append("Content:")
        for cline in content.split("\n"):
            lines.append(f"  {cline}")
        lines.append("")

    tool_calls = msg.get("tool_calls", [])
    if tool_calls:
        lines.append("Tool Calls:")
        for tc in tool_calls:
            if not isinstance(tc, dict):
                continue
            func = tc.get("function", {})
            name = func.get("name", "")
            tc_id = tc.get("id", "")
            lines.append(f"  [{name}] ({tc_id})")
            args = func.get("arguments", "")
            if isinstance(args, dict):
                lines.append(f"    {json.dumps(args, ensure_ascii=False)}")
            elif isinstance(args, str) and args:
                lines.append(f"    {args}")
        lines.append("")

    finish_reason = msg.get("finish_reason")
    if finish_reason:
        lines.append(f"Finish Reason: {finish_reason}")
        lines.append("")

    usage = msg.get("usage")
    if isinstance(usage, dict) and usage:
        lines.append("Usage:")
        for key, value in usage.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


# --- Public API for structured LLM data ---


def get_llm_data(flow: HTTPFlow) -> dict[str, Any] | None:
    """
    Extract structured LLM data from an HTTPFlow.
    Returns a dict with keys: provider, request, response, chat_messages.
    Returns None if the flow is not an LLM API flow.
    """
    path = flow.request.path
    if not is_llm_api_path(path):
        return None

    provider = detect_provider_from_path(path)

    result: dict[str, Any] = {
        "provider": provider,
        "request": None,
        "request_json": None,
        "response": None,
        "response_json": None,
        "chat_messages": [],
    }

    # Parse request
    request_data = flow.request.get_content(strict=False)
    if request_data:
        try:
            body = json.loads(request_data)
            if isinstance(body, dict) and "messages" in body:
                if provider is None:
                    provider = _detect_provider_from_body(body)
                    result["provider"] = provider

                result["request"] = _build_request_data(body, provider)
                result["request_json"] = body

                # Build chat messages from request (exclude system messages)
                for msg in body.get("messages", []):
                    if isinstance(msg, dict) and msg.get("role") != "system":
                        result["chat_messages"].append(
                            _build_chat_message(msg, provider)
                        )
        except (json.JSONDecodeError, ValueError):
            pass

    # Parse response
    response_data = flow.response.get_content(strict=False) if flow.response else None
    if response_data and flow.response:
        content_type = flow.response.headers.get("content-type", "")

        if "text/event-stream" in content_type:
            events = parse_sse_events(response_data)
            if events:
                if provider is None:
                    provider = _detect_provider_from_sse(events)
                    result["provider"] = provider

                if provider == "anthropic":
                    msg = _reconstruct_anthropic(events)
                    result["response"] = msg
                    result["response_json"] = _build_reconstructed_json_anthropic(msg)
                    result["chat_messages"].append(
                        _build_chat_from_response(msg, "anthropic")
                    )
                elif provider == "openai":
                    msg = _reconstruct_openai(events)
                    result["response"] = msg
                    result["response_json"] = _build_reconstructed_json_openai(msg)
                    result["chat_messages"].append(
                        _build_chat_from_response(msg, "openai")
                    )
                else:
                    msg = _reconstruct_anthropic(events)
                    if msg.get("blocks") or msg.get("model"):
                        result["response"] = msg
                        result["response_json"] = _build_reconstructed_json_anthropic(
                            msg
                        )
                        result["chat_messages"].append(
                            _build_chat_from_response(msg, "anthropic")
                        )
                    else:
                        msg = _reconstruct_openai(events)
                        if msg.get("content") or msg.get("model"):
                            result["response"] = msg
                            result["response_json"] = _build_reconstructed_json_openai(
                                msg
                            )
                            result["chat_messages"].append(
                                _build_chat_from_response(msg, "openai")
                            )

        elif "application/json" in content_type:
            try:
                resp_body = json.loads(response_data)
                if isinstance(resp_body, dict):
                    parsed = _parse_json_response(resp_body, provider)
                    if parsed:
                        result["response"] = parsed["response"]
                        result["response_json"] = resp_body
                        result["chat_messages"].append(parsed["chat_message"])
            except (json.JSONDecodeError, ValueError):
                pass

    return result


def _build_request_data(body: dict[str, Any], provider: str | None) -> dict[str, Any]:
    """Extract structured request metadata."""
    data: dict[str, Any] = {
        "model": body.get("model"),
        "messages": body.get("messages", []),
        "parameters": {},
    }

    if provider == "anthropic":
        data["system"] = body.get("system")
        data["tools"] = body.get("tools", [])
        for key in (
            "max_tokens",
            "temperature",
            "top_p",
            "top_k",
            "stop_sequences",
            "stream",
        ):
            if key in body:
                data["parameters"][key] = body[key]
    else:
        data["system"] = None
        # Extract system message from messages for OpenAI
        sys_msgs = [
            m
            for m in body.get("messages", [])
            if isinstance(m, dict) and m.get("role") == "system"
        ]
        if sys_msgs:
            data["system"] = sys_msgs[0].get("content", "")

        tools = body.get("tools", [])
        data["tools"] = []
        for tool in tools:
            if isinstance(tool, dict) and "function" in tool:
                data["tools"].append(tool["function"])
            elif isinstance(tool, dict):
                data["tools"].append(tool)

        for key in (
            "max_tokens",
            "max_completion_tokens",
            "temperature",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
            "stream",
        ):
            if key in body:
                data["parameters"][key] = body[key]

    return data


def _build_chat_message(msg: dict[str, Any], provider: str | None) -> dict[str, Any]:
    """Build a chat message for the LLM Chat tab."""
    role = msg.get("role", "unknown")
    result: dict[str, Any] = {"role": role, "content_parts": []}

    content = msg.get("content", "")
    if isinstance(content, str):
        if content:
            result["content_parts"].append({"type": "text", "text": content})
    elif isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                ptype = part.get("type", "text")
                if ptype == "text":
                    result["content_parts"].append(
                        {"type": "text", "text": part.get("text", "")}
                    )
                elif ptype == "thinking":
                    result["content_parts"].append(
                        {"type": "thinking", "text": part.get("thinking", "")}
                    )
                elif ptype == "tool_use":
                    result["content_parts"].append(
                        {
                            "type": "tool_use",
                            "name": part.get("name", ""),
                            "id": part.get("id", ""),
                            "input": part.get("input", {}),
                        }
                    )
                elif ptype == "tool_result":
                    rc = part.get("content", "")
                    text = (
                        rc
                        if isinstance(rc, str)
                        else json.dumps(rc, ensure_ascii=False)
                    )
                    result["content_parts"].append(
                        {
                            "type": "tool_result",
                            "tool_use_id": part.get("tool_use_id", ""),
                            "text": text,
                        }
                    )
                elif ptype == "image" or ptype == "image_url":
                    result["content_parts"].append({"type": "image", "text": "[image]"})
                else:
                    result["content_parts"].append(
                        {"type": ptype, "text": str(part.get("text", ""))}
                    )

    # OpenAI tool_calls in message
    for tc in msg.get("tool_calls", []):
        if isinstance(tc, dict):
            func = tc.get("function", {})
            result["content_parts"].append(
                {
                    "type": "tool_use",
                    "name": func.get("name", ""),
                    "id": tc.get("id", ""),
                    "input": func.get("arguments", ""),
                }
            )

    return result


def _build_chat_from_response(msg: dict[str, Any], provider: str) -> dict[str, Any]:
    """Build chat message from a reconstructed response."""
    result: dict[str, Any] = {"role": msg.get("role", "assistant"), "content_parts": []}

    if provider == "anthropic":
        for block in msg.get("blocks", []):
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "text")
            if btype == "text":
                result["content_parts"].append(
                    {"type": "text", "text": block.get("content", "")}
                )
            elif btype == "thinking":
                result["content_parts"].append(
                    {"type": "thinking", "text": block.get("content", "")}
                )
            elif btype in ("tool_use", "server_tool_use"):
                result["content_parts"].append(
                    {
                        "type": btype,
                        "name": block.get("name", ""),
                        "id": block.get("id", ""),
                        "input": block.get("input", ""),
                    }
                )
            elif btype == "web_search_tool_result":
                result["content_parts"].append(
                    {
                        "type": "web_search_tool_result",
                        "tool_use_id": block.get("tool_use_id", ""),
                    }
                )
    else:
        if msg.get("content"):
            result["content_parts"].append({"type": "text", "text": msg["content"]})
        for tc in msg.get("tool_calls", []):
            if isinstance(tc, dict):
                func = tc.get("function", {})
                result["content_parts"].append(
                    {
                        "type": "tool_use",
                        "name": func.get("name", ""),
                        "id": tc.get("id", ""),
                        "input": func.get("arguments", ""),
                    }
                )

    return result


def _build_reconstructed_json_anthropic(msg: dict[str, Any]) -> dict[str, Any]:
    """Build the reconstructed JSON for Anthropic response."""
    content_blocks: list[dict[str, Any]] = []
    for b in msg.get("blocks", []):
        if not isinstance(b, dict):
            continue
        btype = b.get("type", "text")
        if btype == "text":
            block_json: dict[str, Any] = {"type": "text", "text": b.get("content", "")}
            if b.get("citations"):
                block_json["citations"] = b["citations"]
            content_blocks.append(block_json)
        elif btype == "thinking":
            block_json = {"type": "thinking", "thinking": b.get("content", "")}
            if b.get("signature"):
                block_json["signature"] = b["signature"]
            content_blocks.append(block_json)
        elif btype == "tool_use":
            content_blocks.append(
                {
                    "type": "tool_use",
                    "id": b.get("id", ""),
                    "name": b.get("name", ""),
                    "input": b.get("input", ""),
                }
            )
        elif btype == "server_tool_use":
            block_json = {
                "type": "server_tool_use",
                "id": b.get("id", ""),
                "name": b.get("name", ""),
                "input": b.get("input", ""),
            }
            if b.get("caller"):
                block_json["caller"] = b["caller"]
            content_blocks.append(block_json)
        elif btype == "web_search_tool_result":
            block_json = {
                "type": "web_search_tool_result",
                "tool_use_id": b.get("tool_use_id", ""),
            }
            if b.get("block_content") is not None:
                block_json["content"] = b["block_content"]
            content_blocks.append(block_json)
        else:
            content_blocks.append({"type": btype, "text": b.get("content", "")})
    result: dict[str, Any] = {"role": msg.get("role", "assistant")}
    if msg.get("model"):
        result["model"] = msg["model"]
    result["content"] = content_blocks
    if msg.get("stop_reason"):
        result["stop_reason"] = msg["stop_reason"]
    if msg.get("usage"):
        result["usage"] = msg["usage"]
    return result


def _build_reconstructed_json_openai(msg: dict[str, Any]) -> dict[str, Any]:
    """Build the reconstructed JSON for OpenAI response."""
    result: dict[str, Any] = {"role": msg.get("role", "assistant")}
    if msg.get("model"):
        result["model"] = msg["model"]
    if msg.get("content"):
        result["content"] = msg["content"]
    if msg.get("tool_calls"):
        result["tool_calls"] = msg["tool_calls"]
    if msg.get("finish_reason"):
        result["finish_reason"] = msg["finish_reason"]
    if msg.get("usage"):
        result["usage"] = msg["usage"]
    return result


def _parse_json_response(
    body: dict[str, Any], provider: str | None
) -> dict[str, Any] | None:
    """Parse a non-streaming JSON response body."""
    if body.get("type") == "message" or provider == "anthropic":
        msg: dict[str, Any] = {
            "blocks": [],
            "usage": body.get("usage"),
            "model": body.get("model"),
            "stop_reason": body.get("stop_reason"),
            "role": body.get("role"),
        }
        for block in body.get("content", []):
            if isinstance(block, dict):
                msg["blocks"].append(
                    {
                        "type": block.get("type", "text"),
                        "content": block.get("text", block.get("thinking", "")),
                        "id": block.get("id"),
                        "name": block.get("name"),
                        "input": block.get("input", ""),
                        "signature": block.get("signature", ""),
                    }
                )
        return {
            "response": msg,
            "chat_message": _build_chat_from_response(msg, "anthropic"),
        }

    if (
        body.get("object") in ("chat.completion", "chat.completion.chunk")
        or "choices" in body
        or provider == "openai"
    ):
        choices = body.get("choices", [])
        content = ""
        tool_calls: list[dict[str, Any]] = []
        finish_reason = None
        role = None
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message", {})
            if isinstance(message, dict):
                content += message.get("content", "") or ""
                role = message.get("role", role)
                tool_calls.extend(message.get("tool_calls", []))
            if choice.get("finish_reason"):
                finish_reason = choice["finish_reason"]

        msg_state: dict[str, Any] = {
            "content": content,
            "tool_calls": tool_calls,
            "model": body.get("model"),
            "finish_reason": finish_reason,
            "usage": body.get("usage"),
            "role": role,
        }
        return {
            "response": msg_state,
            "chat_message": _build_chat_from_response(msg_state, "openai"),
        }

    return None


# --- Contentview Classes ---


_SECTION_SEPARATOR = "\n\n" + "=" * 60 + "\n"


def _pretty_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


class LLMRequestContentview(Contentview):
    name = "LLM Request"
    syntax_highlight = "yaml"

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        # Never auto-select; user manually switches to this viewer.
        return 0

    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        body = json.loads(data)
        if not isinstance(body, dict) or "messages" not in body:
            raise ValueError("Not an LLM request.")

        provider = _detect_provider(metadata)
        if provider is None:
            provider = _detect_provider_from_body(body)

        if provider == "anthropic":
            parsed_view = _format_request_anthropic(body)
        else:
            parsed_view = _format_request_openai(body)

        raw_json = _pretty_json(body)
        return parsed_view + _SECTION_SEPARATOR + "Raw JSON:\n" + raw_json


class LLMResponseContentview(Contentview):
    name = "LLM Response"
    syntax_highlight = "yaml"

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        # Never auto-select; user manually switches to this viewer.
        return 0

    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        if metadata.content_type == "application/json":
            return self._prettify_json_response(data, metadata)

        events = parse_sse_events(data)
        if not events:
            raise ValueError("No SSE events found.")

        provider = _detect_provider(metadata)
        if provider is None:
            provider = _detect_provider_from_sse(events)

        if provider == "anthropic":
            msg = _reconstruct_anthropic(events)
            parsed_view = _format_response_anthropic(msg)
        elif provider == "openai":
            msg = _reconstruct_openai(events)
            parsed_view = _format_response_openai(msg)
        else:
            msg = _reconstruct_anthropic(events)
            if msg.get("blocks") or msg.get("model"):
                parsed_view = _format_response_anthropic(msg)
            else:
                msg = _reconstruct_openai(events)
                if msg.get("content") or msg.get("model"):
                    parsed_view = _format_response_openai(msg)
                else:
                    raise ValueError("Unable to detect LLM provider from SSE events.")

        if provider == "anthropic":
            reconstructed = _build_reconstructed_json_anthropic(msg)
        else:
            reconstructed = _build_reconstructed_json_openai(msg)
        return (
            parsed_view
            + _SECTION_SEPARATOR
            + "Reconstructed JSON:\n"
            + _pretty_json(reconstructed)
        )

    def _prettify_json_response(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        body = json.loads(data)
        if not isinstance(body, dict):
            raise ValueError("Not an LLM response.")

        provider = _detect_provider(metadata)
        raw_json = _pretty_json(body)

        parsed = _parse_json_response(body, provider)
        if parsed is None:
            raise ValueError("Not a recognized LLM response.")

        msg = parsed["response"]
        # Detect which format the response is in
        if "blocks" in msg:
            parsed_view = _format_response_anthropic(msg)
        else:
            parsed_view = _format_response_openai(msg)

        return parsed_view + _SECTION_SEPARATOR + "Raw JSON:\n" + raw_json


llm_request = LLMRequestContentview()
llm_response = LLMResponseContentview()
