import json

import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_llm import _build_chat_from_response
from mitmproxy.contentviews._view_llm import _build_chat_message
from mitmproxy.contentviews._view_llm import _build_reconstructed_json_anthropic
from mitmproxy.contentviews._view_llm import _build_reconstructed_json_openai
from mitmproxy.contentviews._view_llm import _build_request_data
from mitmproxy.contentviews._view_llm import _detect_provider
from mitmproxy.contentviews._view_llm import _detect_provider_from_body
from mitmproxy.contentviews._view_llm import _detect_provider_from_sse
from mitmproxy.contentviews._view_llm import _format_request_anthropic
from mitmproxy.contentviews._view_llm import _format_request_openai
from mitmproxy.contentviews._view_llm import _format_response_anthropic
from mitmproxy.contentviews._view_llm import _format_response_openai
from mitmproxy.contentviews._view_llm import _parse_json_response
from mitmproxy.contentviews._view_llm import _reconstruct_anthropic
from mitmproxy.contentviews._view_llm import _reconstruct_openai
from mitmproxy.contentviews._view_llm import detect_provider_from_path
from mitmproxy.contentviews._view_llm import get_llm_data
from mitmproxy.contentviews._view_llm import is_llm_api_path
from mitmproxy.contentviews._view_llm import llm_request
from mitmproxy.contentviews._view_llm import llm_response
from mitmproxy.contentviews._view_llm import parse_sse_events
from mitmproxy.test import tflow

# --- SSE Parsing ---


def test_parse_sse_events_basic():
    raw = b'event: message_start\ndata: {"type": "message_start"}\n\n'
    events = parse_sse_events(raw)
    assert len(events) == 1
    assert events[0]["event"] == "message_start"
    assert events[0]["parsedData"]["type"] == "message_start"


def test_parse_sse_events_multiline_data():
    raw = b"data: line1\ndata: line2\n\n"
    events = parse_sse_events(raw)
    assert len(events) == 1
    assert events[0]["data"] == "line1\nline2"


def test_parse_sse_events_comment():
    raw = b": this is a comment\ndata: hello\n\n"
    events = parse_sse_events(raw)
    assert len(events) == 1
    assert events[0]["data"] == "hello"


def test_parse_sse_events_empty_data():
    raw = b""
    events = parse_sse_events(raw)
    assert len(events) == 0


def test_parse_sse_events_multiple():
    raw = (
        b'event: message_start\ndata: {"type": "message_start"}\n\n'
        b'event: content_block_start\ndata: {"type": "content_block_start"}\n\n'
    )
    events = parse_sse_events(raw)
    assert len(events) == 2


def test_parse_sse_events_with_id():
    raw = b"id: 42\nevent: ping\ndata: {}\n\n"
    events = parse_sse_events(raw)
    assert len(events) == 1
    assert events[0]["id"] == "42"


def test_parse_sse_events_no_trailing_newline():
    raw = b'data: {"hello": true}'
    events = parse_sse_events(raw)
    assert len(events) == 1
    assert events[0]["parsedData"] == {"hello": True}


def test_parse_sse_events_non_json_data():
    raw = b"data: [DONE]\n\n"
    events = parse_sse_events(raw)
    assert len(events) == 1
    assert events[0]["parsedData"] == "[DONE]"
    assert events[0]["data"] == "[DONE]"


def test_parse_sse_events_openai_format():
    """OpenAI uses 'data: ' with no event: field."""
    raw = (
        b'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"delta":{"content":"Hi"}}]}\n\n'
        b"data: [DONE]\n\n"
    )
    events = parse_sse_events(raw)
    assert len(events) == 2
    assert events[0]["event"] == "message"
    assert events[0]["parsedData"]["choices"][0]["delta"]["content"] == "Hi"


# --- Provider Detection ---


def _make_metadata_with_path(path: str) -> Metadata:
    f = tflow.tflow(resp=True)
    f.request.path = path.encode()
    return Metadata(flow=f)


def test_detect_provider_anthropic():
    meta = _make_metadata_with_path("/v1/messages")
    assert _detect_provider(meta) == "anthropic"


def test_detect_provider_openai():
    meta = _make_metadata_with_path("/v1/chat/completions")
    assert _detect_provider(meta) == "openai"


def test_detect_provider_unknown():
    meta = _make_metadata_with_path("/api/something")
    assert _detect_provider(meta) is None


def test_detect_provider_no_flow():
    assert _detect_provider(Metadata()) is None


def test_detect_provider_from_sse_anthropic():
    events = [{"event": "message_start", "parsedData": {"type": "message_start"}}]
    assert _detect_provider_from_sse(events) == "anthropic"


def test_detect_provider_from_sse_openai():
    events = [
        {
            "event": "message",
            "parsedData": {"object": "chat.completion.chunk", "choices": []},
        }
    ]
    assert _detect_provider_from_sse(events) == "openai"


def test_detect_provider_from_sse_unknown():
    events = [{"event": "message", "parsedData": {"foo": "bar"}}]
    assert _detect_provider_from_sse(events) is None


# --- Anthropic Message Reconstruction ---


def test_reconstruct_anthropic_text():
    events = [
        {
            "event": "message_start",
            "parsedData": {
                "type": "message_start",
                "message": {
                    "model": "claude-sonnet-4-20250514",
                    "role": "assistant",
                    "usage": {"input_tokens": 10},
                },
            },
        },
        {
            "event": "content_block_start",
            "parsedData": {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text"},
            },
        },
        {
            "event": "content_block_delta",
            "parsedData": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "Hello"},
            },
        },
        {
            "event": "content_block_delta",
            "parsedData": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": " world"},
            },
        },
        {
            "event": "content_block_stop",
            "parsedData": {"type": "content_block_stop", "index": 0},
        },
        {
            "event": "message_delta",
            "parsedData": {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn"},
                "usage": {"output_tokens": 5},
            },
        },
    ]
    msg = _reconstruct_anthropic(events)
    assert msg["model"] == "claude-sonnet-4-20250514"
    assert msg["stop_reason"] == "end_turn"
    assert len(msg["blocks"]) == 1
    assert msg["blocks"][0]["type"] == "text"
    assert msg["blocks"][0]["content"] == "Hello world"
    assert msg["usage"]["output_tokens"] == 5


def test_reconstruct_anthropic_thinking():
    events = [
        {
            "event": "content_block_start",
            "parsedData": {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "thinking"},
            },
        },
        {
            "event": "content_block_delta",
            "parsedData": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "thinking_delta", "thinking": "Let me think..."},
            },
        },
        {
            "event": "content_block_stop",
            "parsedData": {"type": "content_block_stop", "index": 0},
        },
    ]
    msg = _reconstruct_anthropic(events)
    assert msg["blocks"][0]["type"] == "thinking"
    assert msg["blocks"][0]["content"] == "Let me think..."


def test_reconstruct_anthropic_tool_use():
    events = [
        {
            "event": "content_block_start",
            "parsedData": {
                "type": "content_block_start",
                "index": 0,
                "content_block": {
                    "type": "tool_use",
                    "id": "toolu_123",
                    "name": "get_weather",
                },
            },
        },
        {
            "event": "content_block_delta",
            "parsedData": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "input_json_delta", "partial_json": '{"loc'},
            },
        },
        {
            "event": "content_block_delta",
            "parsedData": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "input_json_delta",
                    "partial_json": 'ation": "Tokyo"}',
                },
            },
        },
        {
            "event": "content_block_stop",
            "parsedData": {"type": "content_block_stop", "index": 0},
        },
    ]
    msg = _reconstruct_anthropic(events)
    assert msg["blocks"][0]["type"] == "tool_use"
    assert msg["blocks"][0]["name"] == "get_weather"
    assert msg["blocks"][0]["id"] == "toolu_123"
    assert msg["blocks"][0]["input"] == {"location": "Tokyo"}


def test_reconstruct_anthropic_server_tool_use():
    events = [
        {
            "event": "content_block_start",
            "parsedData": {
                "type": "content_block_start",
                "index": 0,
                "content_block": {
                    "type": "server_tool_use",
                    "id": "srvtoolu_123",
                    "name": "web_search",
                    "input": {},
                    "caller": {"type": "direct"},
                },
            },
        },
        {
            "event": "content_block_delta",
            "parsedData": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "input_json_delta", "partial_json": ""},
            },
        },
        {
            "event": "content_block_delta",
            "parsedData": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "input_json_delta", "partial_json": '{"que'},
            },
        },
        {
            "event": "content_block_delta",
            "parsedData": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "input_json_delta", "partial_json": 'ry": "test"}'},
            },
        },
        {
            "event": "content_block_stop",
            "parsedData": {"type": "content_block_stop", "index": 0},
        },
    ]
    msg = _reconstruct_anthropic(events)
    assert msg["blocks"][0]["type"] == "server_tool_use"
    assert msg["blocks"][0]["name"] == "web_search"
    assert msg["blocks"][0]["id"] == "srvtoolu_123"
    assert msg["blocks"][0]["input"] == {"query": "test"}
    assert msg["blocks"][0]["caller"] == {"type": "direct"}


def test_reconstruct_anthropic_web_search_tool_result():
    events = [
        {
            "event": "content_block_start",
            "parsedData": {
                "type": "content_block_start",
                "index": 0,
                "content_block": {
                    "type": "web_search_tool_result",
                    "tool_use_id": "srvtoolu_123",
                    "content": [
                        {
                            "type": "web_search_result",
                            "title": "Example Page",
                            "url": "https://example.com",
                            "encrypted_content": "abc123",
                        }
                    ],
                },
            },
        },
        {
            "event": "content_block_stop",
            "parsedData": {"type": "content_block_stop", "index": 0},
        },
    ]
    msg = _reconstruct_anthropic(events)
    assert msg["blocks"][0]["type"] == "web_search_tool_result"
    assert msg["blocks"][0]["tool_use_id"] == "srvtoolu_123"
    assert len(msg["blocks"][0]["block_content"]) == 1
    assert msg["blocks"][0]["block_content"][0]["title"] == "Example Page"


# --- OpenAI Message Reconstruction ---


def test_reconstruct_openai_content():
    events = [
        {
            "event": "message",
            "parsedData": {
                "model": "gpt-4",
                "choices": [{"delta": {"role": "assistant", "content": "Hello"}}],
            },
        },
        {
            "event": "message",
            "parsedData": {
                "model": "gpt-4",
                "choices": [{"delta": {"content": " there"}}],
            },
        },
        {
            "event": "message",
            "parsedData": {
                "model": "gpt-4",
                "choices": [{"finish_reason": "stop", "delta": {}}],
            },
        },
    ]
    msg = _reconstruct_openai(events)
    assert msg["model"] == "gpt-4"
    assert msg["content"] == "Hello there"
    assert msg["finish_reason"] == "stop"


def test_reconstruct_openai_tool_calls():
    events = [
        {
            "event": "message",
            "parsedData": {
                "model": "gpt-4",
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call_123",
                                    "type": "function",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"lo',
                                    },
                                }
                            ]
                        }
                    }
                ],
            },
        },
        {
            "event": "message",
            "parsedData": {
                "model": "gpt-4",
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "function": {"arguments": 'cation":"NYC"}'},
                                }
                            ]
                        }
                    }
                ],
            },
        },
    ]
    msg = _reconstruct_openai(events)
    assert len(msg["tool_calls"]) == 1
    assert msg["tool_calls"][0]["function"]["name"] == "get_weather"
    assert msg["tool_calls"][0]["function"]["arguments"] == {"location": "NYC"}


def test_reconstruct_openai_with_usage():
    events = [
        {
            "event": "message",
            "parsedData": {
                "model": "gpt-4",
                "choices": [{"delta": {"content": "Hi"}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
        },
    ]
    msg = _reconstruct_openai(events)
    assert msg["usage"]["prompt_tokens"] == 10
    assert msg["usage"]["total_tokens"] == 15


def test_reconstruct_openai_done_event():
    """data: [DONE] events should not cause errors."""
    events = [
        {
            "event": "message",
            "parsedData": {
                "model": "gpt-4",
                "choices": [{"delta": {"content": "Hi"}}],
            },
        },
        {"event": "message", "parsedData": "[DONE]"},
    ]
    msg = _reconstruct_openai(events)
    assert msg["content"] == "Hi"


# --- Render Priority ---
# Both viewers return 0 (never auto-select), user manually switches.


def _make_request_metadata(
    path: str, content_type: str = "application/json"
) -> Metadata:
    f = tflow.tflow()
    f.request.path = path.encode()
    f.request.headers["content-type"] = content_type
    return Metadata(flow=f, content_type=content_type, http_message=f.request)


def test_render_priority_request_always_zero():
    """LLM Request viewer never auto-selects."""
    body = json.dumps(
        {
            "model": "claude-sonnet-4-20250514",
            "messages": [{"role": "user", "content": "Hi"}],
        }
    ).encode()
    meta = _make_request_metadata("/v1/messages")
    assert llm_request.render_priority(body, meta) == 0


def test_render_priority_request_openai_zero():
    body = json.dumps(
        {"model": "gpt-4", "messages": [{"role": "user", "content": "Hi"}]}
    ).encode()
    meta = _make_request_metadata("/v1/chat/completions")
    assert llm_request.render_priority(body, meta) == 0


def _make_response_metadata(
    path: str, content_type: str = "text/event-stream"
) -> Metadata:
    f = tflow.tflow(resp=True)
    f.request.path = path.encode()
    f.response.headers["content-type"] = content_type
    return Metadata(flow=f, content_type=content_type, http_message=f.response)


def test_render_priority_response_always_zero():
    """LLM Response viewer never auto-selects."""
    data = b'event: message_start\ndata: {"type": "message_start"}\n\n'
    meta = _make_response_metadata("/v1/messages")
    assert llm_response.render_priority(data, meta) == 0


def test_render_priority_response_json_zero():
    body = json.dumps(
        {
            "type": "message",
            "model": "claude-sonnet-4-20250514",
            "content": [{"type": "text", "text": "Hi"}],
        }
    ).encode()
    meta = _make_response_metadata("/v1/messages", content_type="application/json")
    assert llm_response.render_priority(body, meta) == 0


# --- Prettify Request: both parsed view + raw JSON ---


def test_prettify_request_anthropic():
    body_dict = {
        "model": "claude-sonnet-4-20250514",
        "system": "You are helpful.",
        "messages": [{"role": "user", "content": "What is weather?"}],
        "tools": [{"name": "get_weather", "description": "Get current weather"}],
        "max_tokens": 4096,
        "stream": True,
    }
    body = json.dumps(body_dict).encode()
    meta = _make_request_metadata("/v1/messages")
    result = llm_request.prettify(body, meta)
    # Parsed section
    assert "[LLM Request] Anthropic claude-sonnet-4-20250514" in result
    assert "System:" in result
    assert "You are helpful." in result
    assert "Messages:" in result
    assert "user:" in result
    assert "What is weather?" in result
    assert "Tools:" in result
    assert "get_weather" in result
    assert "max_tokens: 4096" in result
    assert "stream: True" in result
    # Separator
    assert "====" in result
    # Raw JSON section
    assert "Raw JSON:" in result
    assert '"model": "claude-sonnet-4-20250514"' in result


def test_prettify_request_openai():
    body_dict = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ],
        "temperature": 0.7,
        "stream": True,
    }
    body = json.dumps(body_dict).encode()
    meta = _make_request_metadata("/v1/chat/completions")
    result = llm_request.prettify(body, meta)
    # Parsed section
    assert "[LLM Request] OpenAI gpt-4" in result
    assert "Messages:" in result
    assert "system:" in result
    assert "user:" in result
    # Raw JSON section
    assert "Raw JSON:" in result
    assert '"model": "gpt-4"' in result


def test_prettify_request_anthropic_system_blocks():
    body = json.dumps(
        {
            "model": "claude-sonnet-4-20250514",
            "system": [{"type": "text", "text": "System prompt here"}],
            "messages": [{"role": "user", "content": "Hi"}],
        }
    ).encode()
    meta = _make_request_metadata("/v1/messages")
    result = llm_request.prettify(body, meta)
    assert "System prompt here" in result
    assert "Raw JSON:" in result


def test_prettify_request_anthropic_content_blocks():
    body = json.dumps(
        {
            "model": "claude-sonnet-4-20250514",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Look at this"},
                        {"type": "image", "source": {"type": "base64"}},
                    ],
                }
            ],
        }
    ).encode()
    meta = _make_request_metadata("/v1/messages")
    result = llm_request.prettify(body, meta)
    assert "Look at this" in result
    assert "[image]" in result
    assert "Raw JSON:" in result


# --- Prettify Response: both parsed view + reconstructed/raw JSON ---


def test_prettify_response_anthropic_sse():
    raw_sse = (
        b'event: message_start\ndata: {"type":"message_start","message":{"model":"claude-sonnet-4-20250514","role":"assistant","usage":{"input_tokens":100}}}\n\n'
        b'event: content_block_start\ndata: {"type":"content_block_start","index":0,"content_block":{"type":"text"}}\n\n'
        b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello!"}}\n\n'
        b'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n'
        b'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":5}}\n\n'
    )
    meta = _make_response_metadata("/v1/messages")
    result = llm_response.prettify(raw_sse, meta)
    # Parsed section
    assert "[LLM Response] Anthropic claude-sonnet-4-20250514" in result
    assert "[text]" in result
    assert "Hello!" in result
    assert "Stop Reason: end_turn" in result
    assert "output_tokens: 5" in result
    # Separator + Reconstructed JSON
    assert "====" in result
    assert "Reconstructed JSON:" in result
    assert '"text": "Hello!"' in result


def test_prettify_response_openai_sse():
    raw_sse = (
        b'data: {"model":"gpt-4","choices":[{"delta":{"role":"assistant","content":"Hi "}}]}\n\n'
        b'data: {"model":"gpt-4","choices":[{"delta":{"content":"there"}}]}\n\n'
        b'data: {"model":"gpt-4","choices":[{"finish_reason":"stop","delta":{}}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}\n\n'
        b"data: [DONE]\n\n"
    )
    meta = _make_response_metadata("/v1/chat/completions")
    result = llm_response.prettify(raw_sse, meta)
    # Parsed section
    assert "[LLM Response] OpenAI gpt-4" in result
    assert "Hi there" in result
    assert "Finish Reason: stop" in result
    assert "prompt_tokens: 10" in result
    # Reconstructed JSON
    assert "Reconstructed JSON:" in result
    assert '"content": "Hi there"' in result


def test_prettify_response_json_anthropic():
    body = json.dumps(
        {
            "type": "message",
            "model": "claude-sonnet-4-20250514",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
    ).encode()
    meta = _make_response_metadata("/v1/messages", content_type="application/json")
    result = llm_response.prettify(body, meta)
    assert "[LLM Response] Anthropic" in result
    assert "Hello" in result
    # Raw JSON section for non-streaming response
    assert "Raw JSON:" in result
    assert '"type": "message"' in result


def test_prettify_response_json_openai():
    body = json.dumps(
        {
            "object": "chat.completion",
            "model": "gpt-4",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
    ).encode()
    meta = _make_response_metadata(
        "/v1/chat/completions", content_type="application/json"
    )
    result = llm_response.prettify(body, meta)
    assert "[LLM Response] OpenAI gpt-4" in result
    assert "Hello" in result
    assert "Raw JSON:" in result


# --- Reconstructed JSON for server_tool_use / web_search_tool_result ---


def test_reconstructed_json_server_tool_use():
    """server_tool_use blocks should include id, name, input in reconstructed JSON."""
    msg = {
        "model": "claude-haiku-4-5-20251001",
        "role": "assistant",
        "blocks": [
            {
                "type": "server_tool_use",
                "content": "",
                "id": "srvtoolu_123",
                "name": "web_search",
                "input": {"query": "test query"},
                "signature": "",
                "caller": {"type": "direct"},
            },
        ],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10},
    }
    result = _build_reconstructed_json_anthropic(msg)
    assert len(result["content"]) == 1
    block = result["content"][0]
    assert block["type"] == "server_tool_use"
    assert block["id"] == "srvtoolu_123"
    assert block["name"] == "web_search"
    assert block["input"] == {"query": "test query"}
    assert block["caller"] == {"type": "direct"}


def test_reconstructed_json_web_search_tool_result():
    """web_search_tool_result blocks should include tool_use_id and content in reconstructed JSON."""
    msg = {
        "model": "claude-haiku-4-5-20251001",
        "role": "assistant",
        "blocks": [
            {
                "type": "web_search_tool_result",
                "content": "",
                "id": None,
                "name": None,
                "input": "",
                "signature": "",
                "tool_use_id": "srvtoolu_123",
                "block_content": [
                    {
                        "type": "web_search_result",
                        "title": "Example Page",
                        "url": "https://example.com",
                        "encrypted_content": "abc",
                    }
                ],
            },
        ],
        "stop_reason": "end_turn",
        "usage": None,
    }
    result = _build_reconstructed_json_anthropic(msg)
    assert len(result["content"]) == 1
    block = result["content"][0]
    assert block["type"] == "web_search_tool_result"
    assert block["tool_use_id"] == "srvtoolu_123"
    assert len(block["content"]) == 1
    assert block["content"][0]["title"] == "Example Page"


# --- Prettify Invalid Data ---


def test_prettify_request_invalid():
    with pytest.raises(ValueError):
        llm_request.prettify(b'"not an object"', Metadata())


def test_prettify_request_no_messages():
    with pytest.raises(ValueError):
        llm_request.prettify(json.dumps({"model": "gpt-4"}).encode(), Metadata())


def test_prettify_response_invalid():
    with pytest.raises(ValueError):
        llm_response.prettify(
            b"not sse data at all", Metadata(content_type="text/event-stream")
        )


def test_prettify_response_empty():
    with pytest.raises(ValueError):
        llm_response.prettify(b"", Metadata(content_type="text/event-stream"))


# --- is_llm_api_path ---


def test_is_llm_api_path():
    assert is_llm_api_path("/v1/messages") is True
    assert is_llm_api_path("/v1/chat/completions") is True
    assert is_llm_api_path("/api/something") is False


# --- detect_provider_from_path ---


def test_detect_provider_from_path_both():
    assert detect_provider_from_path("/v1/messages/v1/chat/completions") is None


# --- _detect_provider_from_body ---


def test_detect_provider_from_body():
    assert _detect_provider_from_body({"model": "gpt-4"}) is None
    assert (
        _detect_provider_from_body(
            {"messages": [{"role": "user", "content": [{"type": "text"}]}]}
        )
        == "anthropic"
    )
    assert (
        _detect_provider_from_body(
            {"messages": [{"role": "user", "content": "Hi"}], "model": "claude-3"}
        )
        == "anthropic"
    )
    assert (
        _detect_provider_from_body(
            {"messages": [{"role": "user", "content": "Hi"}], "model": "gpt-4"}
        )
        == "openai"
    )
    assert (
        _detect_provider_from_body(
            {"messages": [{"role": "user", "content": "Hi"}], "model": "o1-preview"}
        )
        == "openai"
    )
    assert (
        _detect_provider_from_body(
            {"messages": [{"role": "user", "content": "Hi"}], "model": "llama-3"}
        )
        is None
    )
    assert _detect_provider_from_body({"messages": []}) is None


def test_detect_provider_from_sse_choices():
    events = [{"event": "message", "parsedData": {"choices": [{"delta": {}}]}}]
    assert _detect_provider_from_sse(events) == "openai"


# --- SSE parsing edge case ---


def test_parse_sse_events_trailing_non_json():
    raw = b"data: not valid json"
    events = parse_sse_events(raw)
    assert len(events) == 1
    assert events[0]["parsedData"] == "not valid json"


# --- Anthropic reconstruction edge cases ---


def test_reconstruct_anthropic_non_dict_parsed_data():
    events = [
        {"event": "message_start", "parsedData": "not a dict"},
        {
            "event": "message_start",
            "parsedData": {
                "type": "message_start",
                "message": {"model": "claude-3", "role": "assistant"},
            },
        },
    ]
    msg = _reconstruct_anthropic(events)
    assert msg["model"] == "claude-3"


def test_reconstruct_anthropic_signature_delta():
    events = [
        {
            "event": "content_block_start",
            "parsedData": {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "thinking"},
            },
        },
        {
            "event": "content_block_delta",
            "parsedData": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "signature_delta", "signature": "sig123"},
            },
        },
        {
            "event": "content_block_stop",
            "parsedData": {"type": "content_block_stop", "index": 0},
        },
    ]
    msg = _reconstruct_anthropic(events)
    assert msg["blocks"][0]["signature"] == "sig123"


def test_reconstruct_anthropic_citations_delta():
    events = [
        {
            "event": "content_block_start",
            "parsedData": {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "citations": []},
            },
        },
        {
            "event": "content_block_delta",
            "parsedData": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "citations_delta",
                    "citation": {"url": "https://example.com"},
                },
            },
        },
        {
            "event": "content_block_stop",
            "parsedData": {"type": "content_block_stop", "index": 0},
        },
    ]
    msg = _reconstruct_anthropic(events)
    assert len(msg["blocks"][0]["citations"]) == 1


def test_reconstruct_anthropic_invalid_tool_input():
    events = [
        {
            "event": "content_block_start",
            "parsedData": {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "tool_use", "id": "t1", "name": "test"},
            },
        },
        {
            "event": "content_block_delta",
            "parsedData": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "input_json_delta", "partial_json": "invalid{"},
            },
        },
        {
            "event": "content_block_stop",
            "parsedData": {"type": "content_block_stop", "index": 0},
        },
    ]
    msg = _reconstruct_anthropic(events)
    assert msg["blocks"][0]["input"] == "invalid{"


def test_reconstruct_anthropic_message_delta_null_usage():
    events = [
        {
            "event": "message_delta",
            "parsedData": {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn"},
                "usage": {"output_tokens": 10},
            },
        },
    ]
    msg = _reconstruct_anthropic(events)
    assert msg["usage"] == {"output_tokens": 10}


# --- OpenAI reconstruction edge cases ---


def test_reconstruct_openai_non_dict_choice():
    events = [
        {
            "event": "message",
            "parsedData": {
                "model": "gpt-4",
                "choices": ["not a dict", {"delta": {"content": "Hi"}}],
            },
        },
    ]
    msg = _reconstruct_openai(events)
    assert msg["content"] == "Hi"


def test_reconstruct_openai_non_dict_delta():
    events = [
        {
            "event": "message",
            "parsedData": {"model": "gpt-4", "choices": [{"delta": "not a dict"}]},
        },
    ]
    msg = _reconstruct_openai(events)
    assert msg["content"] == ""


def test_reconstruct_openai_non_dict_tool_call():
    events = [
        {
            "event": "message",
            "parsedData": {
                "model": "gpt-4",
                "choices": [{"delta": {"tool_calls": ["not a dict"]}}],
            },
        },
    ]
    msg = _reconstruct_openai(events)
    assert msg["tool_calls"] == []


def test_reconstruct_openai_invalid_tool_args():
    events = [
        {
            "event": "message",
            "parsedData": {
                "model": "gpt-4",
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call_1",
                                    "function": {
                                        "name": "test",
                                        "arguments": "invalid{",
                                    },
                                }
                            ]
                        }
                    }
                ],
            },
        },
    ]
    msg = _reconstruct_openai(events)
    assert msg["tool_calls"][0]["function"]["arguments"] == "invalid{"


# --- Format request edge cases ---


def test_format_request_anthropic_system_non_text_block():
    data = {
        "model": "claude-3",
        "system": [{"type": "cache_control", "text": "cached"}],
        "messages": [],
    }
    result = _format_request_anthropic(data)
    assert "[cache_control]" in result


def test_format_request_anthropic_non_dict_message():
    data = {
        "model": "claude-3",
        "messages": ["not a dict", {"role": "user", "content": "Hi"}],
    }
    result = _format_request_anthropic(data)
    assert "user:" in result


def test_format_request_anthropic_non_dict_part():
    data = {
        "model": "claude-3",
        "messages": [
            {"role": "user", "content": ["not a dict", {"type": "text", "text": "Hi"}]}
        ],
    }
    result = _format_request_anthropic(data)
    assert "Hi" in result


def test_format_request_anthropic_tool_use_content():
    data = {
        "model": "claude-3",
        "messages": [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "get_weather",
                        "id": "toolu_1",
                        "input": {"location": "Tokyo"},
                    }
                ],
            }
        ],
    }
    result = _format_request_anthropic(data)
    assert "[tool_use] get_weather (toolu_1)" in result
    assert "Tokyo" in result


def test_format_request_anthropic_tool_result_content():
    data = {
        "model": "claude-3",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_1",
                        "content": "sunny",
                    }
                ],
            }
        ],
    }
    result = _format_request_anthropic(data)
    assert "[tool_result] tool_use_id=toolu_1" in result
    assert "sunny" in result


def test_format_request_anthropic_tool_result_list_content():
    data = {
        "model": "claude-3",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t1",
                        "content": [{"type": "text", "text": "result text"}],
                    }
                ],
            }
        ],
    }
    result = _format_request_anthropic(data)
    assert "[text] result text" in result


def test_format_request_anthropic_thinking_type():
    data = {
        "model": "claude-3",
        "messages": [
            {
                "role": "assistant",
                "content": [{"type": "thinking", "thinking": "deep thought"}],
            }
        ],
    }
    result = _format_request_anthropic(data)
    assert "[thinking]" in result


def test_format_request_anthropic_non_dict_tool():
    data = {
        "model": "claude-3",
        "messages": [],
        "tools": ["not a dict", {"name": "tool1", "description": "desc1"}],
    }
    result = _format_request_anthropic(data)
    assert "tool1" in result


def test_format_request_openai_non_dict_message():
    data = {
        "model": "gpt-4",
        "messages": ["not a dict", {"role": "user", "content": "Hi"}],
    }
    result = _format_request_openai(data)
    assert "user:" in result


def test_format_request_openai_content_list():
    data = {
        "model": "gpt-4",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Look"},
                    {"type": "image_url", "image_url": {"url": "http://x.com/i.png"}},
                    {"type": "audio"},
                    "not a dict",
                ],
            }
        ],
    }
    result = _format_request_openai(data)
    assert "Look" in result
    assert "[image_url]" in result
    assert "[audio]" in result


def test_format_request_openai_tool_calls():
    data = {
        "model": "gpt-4",
        "messages": [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"loc": "NYC"}',
                        },
                    }
                ],
            }
        ],
    }
    result = _format_request_openai(data)
    assert "[tool_call] get_weather (call_1)" in result


def test_format_request_openai_tool_calls_dict_args():
    data = {
        "model": "gpt-4",
        "messages": [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "c1",
                        "function": {"name": "t", "arguments": {"key": "val"}},
                    }
                ],
            }
        ],
    }
    result = _format_request_openai(data)
    assert '"key": "val"' in result


def test_format_request_openai_tools():
    data = {
        "model": "gpt-4",
        "messages": [],
        "tools": [
            {"function": {"name": "get_weather", "description": "Get weather"}},
            "not a dict",
        ],
    }
    result = _format_request_openai(data)
    assert "get_weather" in result


# --- Format response edge cases ---


def test_format_response_anthropic_thinking():
    msg = {
        "model": "claude-3",
        "blocks": [
            "not a dict",
            {"type": "thinking", "content": "Let me think..."},
        ],
    }
    result = _format_response_anthropic(msg)
    assert "[thinking]" in result
    assert "Let me think..." in result


def test_format_response_anthropic_tool_use():
    msg = {
        "model": "claude-3",
        "blocks": [
            {
                "type": "tool_use",
                "name": "get_weather",
                "id": "t1",
                "input": {"location": "Tokyo"},
            }
        ],
    }
    result = _format_response_anthropic(msg)
    assert "[tool_use] get_weather (t1)" in result


def test_format_response_anthropic_tool_use_str_input():
    msg = {
        "model": "claude-3",
        "blocks": [{"type": "tool_use", "name": "t", "id": "t1", "input": "raw input"}],
    }
    result = _format_response_anthropic(msg)
    assert "raw input" in result


def test_format_response_anthropic_server_tool_use():
    msg = {
        "model": "claude-3",
        "blocks": [
            {
                "type": "server_tool_use",
                "name": "web_search",
                "id": "s1",
                "input": {"query": "test"},
            }
        ],
    }
    result = _format_response_anthropic(msg)
    assert "[server_tool_use] web_search (s1)" in result


def test_format_response_anthropic_server_tool_use_str_input():
    msg = {
        "model": "claude-3",
        "blocks": [
            {"type": "server_tool_use", "name": "t", "id": "s1", "input": "raw"}
        ],
    }
    result = _format_response_anthropic(msg)
    assert "raw" in result


def test_format_response_anthropic_web_search_result():
    msg = {
        "model": "claude-3",
        "blocks": [
            {
                "type": "web_search_tool_result",
                "tool_use_id": "s1",
                "block_content": [
                    {"title": "Example", "url": "https://example.com"},
                ],
            }
        ],
    }
    result = _format_response_anthropic(msg)
    assert "[web_search_tool_result] tool_use_id=s1" in result
    assert "Example" in result


def test_format_response_anthropic_unknown_type():
    msg = {
        "model": "claude-3",
        "blocks": [{"type": "custom_type", "content": "custom content"}],
    }
    result = _format_response_anthropic(msg)
    assert "[custom_type]" in result
    assert "custom content" in result


def test_format_response_anthropic_unknown_type_empty():
    msg = {"model": "claude-3", "blocks": [{"type": "custom", "content": ""}]}
    result = _format_response_anthropic(msg)
    assert "[custom]" in result


def test_format_response_openai_tool_calls():
    msg = {
        "model": "gpt-4",
        "content": "",
        "tool_calls": [
            {
                "id": "call_1",
                "function": {"name": "get_weather", "arguments": {"loc": "NYC"}},
            },
            "not a dict",
        ],
    }
    result = _format_response_openai(msg)
    assert "Tool Calls:" in result
    assert "[get_weather] (call_1)" in result


def test_format_response_openai_tool_calls_str_args():
    msg = {
        "model": "gpt-4",
        "content": "",
        "tool_calls": [
            {"id": "c1", "function": {"name": "test", "arguments": "raw args"}}
        ],
    }
    result = _format_response_openai(msg)
    assert "raw args" in result


# --- _build_request_data ---


def test_build_request_data_anthropic():
    body = {
        "model": "claude-3",
        "messages": [{"role": "user", "content": "Hi"}],
        "system": "Be helpful",
        "tools": [{"name": "test", "description": "d"}],
        "max_tokens": 1024,
        "temperature": 0.7,
        "stream": True,
    }
    result = _build_request_data(body, "anthropic")
    assert result["model"] == "claude-3"
    assert result["system"] == "Be helpful"
    assert result["parameters"]["max_tokens"] == 1024
    assert result["parameters"]["stream"] is True


def test_build_request_data_openai():
    body = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hi"},
        ],
        "tools": [
            {"type": "function", "function": {"name": "t", "description": "d"}},
            {"name": "raw", "description": "d2"},
        ],
        "max_tokens": 1024,
        "stream": True,
    }
    result = _build_request_data(body, "openai")
    assert result["system"] == "Be helpful"
    assert len(result["tools"]) == 2
    assert result["tools"][0]["name"] == "t"
    assert result["parameters"]["max_tokens"] == 1024


def test_build_request_data_openai_no_system():
    body = {"model": "gpt-4", "messages": [{"role": "user", "content": "Hi"}]}
    result = _build_request_data(body, "openai")
    assert result["system"] is None


# --- _build_chat_message ---


def test_build_chat_message_string_content():
    msg = {"role": "user", "content": "Hello"}
    result = _build_chat_message(msg, "anthropic")
    assert result["role"] == "user"
    assert len(result["content_parts"]) == 1
    assert result["content_parts"][0] == {"type": "text", "text": "Hello"}


def test_build_chat_message_empty_string():
    msg = {"role": "user", "content": ""}
    result = _build_chat_message(msg, "anthropic")
    assert result["content_parts"] == []


def test_build_chat_message_list_content():
    msg = {
        "role": "user",
        "content": [
            {"type": "text", "text": "Hello"},
            {"type": "thinking", "thinking": "deep thought"},
            {"type": "tool_use", "name": "t", "id": "t1", "input": {}},
            {"type": "tool_result", "tool_use_id": "t1", "content": "result"},
            {
                "type": "tool_result",
                "tool_use_id": "t2",
                "content": [{"type": "text", "text": "list"}],
            },
            {"type": "image"},
            {"type": "image_url"},
            {"type": "custom", "text": "c"},
            "not a dict",
        ],
    }
    result = _build_chat_message(msg, "anthropic")
    parts = result["content_parts"]
    assert parts[0] == {"type": "text", "text": "Hello"}
    assert parts[1] == {"type": "thinking", "text": "deep thought"}
    assert parts[2]["type"] == "tool_use"
    assert parts[3]["type"] == "tool_result"
    assert parts[3]["text"] == "result"
    assert parts[4]["type"] == "tool_result"
    assert parts[5]["type"] == "image"
    assert parts[6]["type"] == "image"
    assert parts[7] == {"type": "custom", "text": "c"}


def test_build_chat_message_openai_tool_calls():
    msg = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": "c1", "function": {"name": "test", "arguments": "{}"}},
        ],
    }
    result = _build_chat_message(msg, "openai")
    assert len(result["content_parts"]) == 1
    assert result["content_parts"][0]["type"] == "tool_use"


# --- _build_chat_from_response ---


def test_build_chat_from_response_anthropic():
    msg = {
        "role": "assistant",
        "blocks": [
            {"type": "text", "content": "Hello"},
            {"type": "thinking", "content": "Thinking..."},
            {"type": "tool_use", "name": "t", "id": "t1", "input": {}},
            {"type": "server_tool_use", "name": "ws", "id": "s1", "input": {}},
            {"type": "web_search_tool_result", "tool_use_id": "s1"},
            "not a dict",
        ],
    }
    result = _build_chat_from_response(msg, "anthropic")
    parts = result["content_parts"]
    assert parts[0] == {"type": "text", "text": "Hello"}
    assert parts[1] == {"type": "thinking", "text": "Thinking..."}
    assert parts[2]["type"] == "tool_use"
    assert parts[3]["type"] == "server_tool_use"
    assert parts[4]["type"] == "web_search_tool_result"
    assert len(parts) == 5


def test_build_chat_from_response_openai():
    msg = {
        "role": "assistant",
        "content": "Hello",
        "tool_calls": [
            {"id": "c1", "function": {"name": "test", "arguments": "{}"}},
            "not a dict",
        ],
    }
    result = _build_chat_from_response(msg, "openai")
    parts = result["content_parts"]
    assert parts[0] == {"type": "text", "text": "Hello"}
    assert parts[1]["type"] == "tool_use"
    assert len(parts) == 2


# --- _build_reconstructed_json edge cases ---


def test_reconstructed_json_anthropic_text_with_citations():
    msg = {
        "blocks": [
            {
                "type": "text",
                "content": "Hi",
                "citations": [{"url": "https://x.com"}],
            }
        ],
    }
    result = _build_reconstructed_json_anthropic(msg)
    assert result["content"][0]["citations"] == [{"url": "https://x.com"}]


def test_reconstructed_json_anthropic_thinking_with_signature():
    msg = {
        "blocks": [{"type": "thinking", "content": "Think...", "signature": "sig123"}],
    }
    result = _build_reconstructed_json_anthropic(msg)
    assert result["content"][0]["thinking"] == "Think..."
    assert result["content"][0]["signature"] == "sig123"


def test_reconstructed_json_anthropic_tool_use_block():
    msg = {
        "blocks": [
            {"type": "tool_use", "id": "t1", "name": "test", "input": {"k": "v"}}
        ],
    }
    result = _build_reconstructed_json_anthropic(msg)
    assert result["content"][0]["type"] == "tool_use"
    assert result["content"][0]["input"] == {"k": "v"}


def test_reconstructed_json_anthropic_non_dict_block():
    msg = {"blocks": ["not a dict", {"type": "text", "content": "Hi"}]}
    result = _build_reconstructed_json_anthropic(msg)
    assert len(result["content"]) == 1


def test_reconstructed_json_anthropic_unknown_type():
    msg = {"blocks": [{"type": "custom", "content": "text"}]}
    result = _build_reconstructed_json_anthropic(msg)
    assert result["content"][0] == {"type": "custom", "text": "text"}


def test_reconstructed_json_openai_tool_calls():
    msg = {
        "model": "gpt-4",
        "content": "",
        "tool_calls": [{"id": "c1", "function": {"name": "t", "arguments": "{}"}}],
        "finish_reason": "tool_calls",
    }
    result = _build_reconstructed_json_openai(msg)
    assert result["tool_calls"] == msg["tool_calls"]
    assert result["finish_reason"] == "tool_calls"


# --- _parse_json_response ---


def test_parse_json_response_non_dict_choice():
    body = {
        "choices": [
            "not a dict",
            {
                "message": {"role": "assistant", "content": "Hi"},
                "finish_reason": "stop",
            },
        ],
    }
    result = _parse_json_response(body, "openai")
    assert result is not None
    assert result["response"]["content"] == "Hi"


def test_parse_json_response_unrecognized():
    assert _parse_json_response({"foo": "bar"}, None) is None


# --- get_llm_data ---


def _make_flow_with_sse(path, request_body, response_sse):
    f = tflow.tflow(resp=True)
    f.request.path = path
    f.request.headers["content-type"] = "application/json"
    f.request.content = request_body
    f.response.headers["content-type"] = "text/event-stream"
    f.response.content = response_sse
    return f


def _make_flow_with_json_response(path, request_body, response_body):
    f = tflow.tflow(resp=True)
    f.request.path = path
    f.request.headers["content-type"] = "application/json"
    f.request.content = request_body
    f.response.headers["content-type"] = "application/json"
    f.response.content = response_body
    return f


def test_get_llm_data_not_llm():
    f = tflow.tflow(resp=True)
    f.request.path = "/api/something"
    assert get_llm_data(f) is None


def test_get_llm_data_anthropic_sse():
    request_body = json.dumps(
        {
            "model": "claude-3",
            "messages": [{"role": "user", "content": "Hi"}],
            "stream": True,
        }
    ).encode()
    response_sse = (
        b'event: message_start\ndata: {"type":"message_start","message":{"model":"claude-3","role":"assistant","usage":{"input_tokens":10}}}\n\n'
        b'event: content_block_start\ndata: {"type":"content_block_start","index":0,"content_block":{"type":"text"}}\n\n'
        b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}\n\n'
        b'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n'
        b'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":5}}\n\n'
    )
    f = _make_flow_with_sse("/v1/messages", request_body, response_sse)
    result = get_llm_data(f)
    assert result is not None
    assert result["provider"] == "anthropic"
    assert result["request"] is not None
    assert result["response"] is not None
    assert result["response_json"] is not None
    assert len(result["chat_messages"]) == 2


def test_get_llm_data_openai_sse():
    request_body = json.dumps(
        {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hi"}],
            "stream": True,
        }
    ).encode()
    response_sse = (
        b'data: {"model":"gpt-4","choices":[{"delta":{"role":"assistant","content":"Hello"}}]}\n\n'
        b'data: {"model":"gpt-4","choices":[{"finish_reason":"stop","delta":{}}]}\n\n'
        b"data: [DONE]\n\n"
    )
    f = _make_flow_with_sse("/v1/chat/completions", request_body, response_sse)
    result = get_llm_data(f)
    assert result is not None
    assert result["provider"] == "openai"
    assert result["response"]["content"] == "Hello"


def test_get_llm_data_json_response():
    request_body = json.dumps(
        {"model": "claude-3", "messages": [{"role": "user", "content": "Hi"}]}
    ).encode()
    response_body = json.dumps(
        {
            "type": "message",
            "model": "claude-3",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello"}],
            "stop_reason": "end_turn",
        }
    ).encode()
    f = _make_flow_with_json_response("/v1/messages", request_body, response_body)
    result = get_llm_data(f)
    assert result is not None
    assert result["response_json"] is not None


def test_get_llm_data_openai_json_response():
    request_body = json.dumps(
        {"model": "gpt-4", "messages": [{"role": "user", "content": "Hi"}]}
    ).encode()
    response_body = json.dumps(
        {
            "object": "chat.completion",
            "model": "gpt-4",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello"},
                    "finish_reason": "stop",
                }
            ],
        }
    ).encode()
    f = _make_flow_with_json_response(
        "/v1/chat/completions", request_body, response_body
    )
    result = get_llm_data(f)
    assert result is not None
    assert result["provider"] == "openai"
    assert result["response"]["content"] == "Hello"


def test_get_llm_data_no_response():
    f = tflow.tflow()
    f.request.path = "/v1/messages"
    f.request.content = json.dumps(
        {"model": "claude-3", "messages": [{"role": "user", "content": "Hi"}]}
    ).encode()
    result = get_llm_data(f)
    assert result is not None
    assert result["request"] is not None
    assert result["response"] is None


def test_get_llm_data_invalid_request():
    f = tflow.tflow(resp=True)
    f.request.path = "/v1/messages"
    f.request.content = b"not json"
    f.response.headers["content-type"] = "text/plain"
    f.response.content = b""
    result = get_llm_data(f)
    assert result is not None
    assert result["request"] is None


def test_get_llm_data_invalid_json_response():
    f = tflow.tflow(resp=True)
    f.request.path = "/v1/messages"
    f.request.content = json.dumps(
        {"model": "claude-3", "messages": [{"role": "user", "content": "Hi"}]}
    ).encode()
    f.response.headers["content-type"] = "application/json"
    f.response.content = b"not json"
    result = get_llm_data(f)
    assert result is not None
    assert result["response"] is None


def test_get_llm_data_skips_system_messages():
    f = tflow.tflow(resp=True)
    f.request.path = "/v1/chat/completions"
    f.request.content = json.dumps(
        {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "Be helpful"},
                {"role": "user", "content": "Hi"},
            ],
        }
    ).encode()
    f.response.headers["content-type"] = "text/plain"
    f.response.content = b""
    result = get_llm_data(f)
    assert result is not None
    assert len(result["chat_messages"]) == 1
    assert result["chat_messages"][0]["role"] == "user"


def test_get_llm_data_detect_provider_from_body():
    request_body = json.dumps(
        {"model": "claude-3-opus", "messages": [{"role": "user", "content": "Hi"}]}
    ).encode()
    # Use a path that matches both patterns so path detection returns None
    f = tflow.tflow(resp=True)
    f.request.path = "/v1/messages/v1/chat/completions"
    f.request.content = request_body
    f.response.headers["content-type"] = "text/plain"
    f.response.content = b""
    result = get_llm_data(f)
    assert result is not None
    assert result["provider"] == "anthropic"


def test_get_llm_data_detect_provider_from_sse():
    request_body = json.dumps(
        {"model": "test", "messages": [{"role": "user", "content": "Hi"}]}
    ).encode()
    response_sse = (
        b'event: message_start\ndata: {"type":"message_start","message":{"model":"test","role":"assistant"}}\n\n'
        b'event: content_block_start\ndata: {"type":"content_block_start","index":0,"content_block":{"type":"text"}}\n\n'
        b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n\n'
        b'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n'
    )
    f = tflow.tflow(resp=True)
    f.request.path = "/v1/messages/v1/chat/completions"
    f.request.content = request_body
    f.response.headers["content-type"] = "text/event-stream"
    f.response.content = response_sse
    result = get_llm_data(f)
    assert result is not None
    assert result["provider"] == "anthropic"
    assert result["response"] is not None


def test_get_llm_data_unknown_provider_anthropic_fallback():
    request_body = json.dumps(
        {"model": "test", "messages": [{"role": "user", "content": "Hi"}]}
    ).encode()
    # SSE with no event: field, so _detect_provider_from_sse returns None.
    # But parsedData has "type":"message_start" so _reconstruct_anthropic works.
    response_sse = (
        b'data: {"type":"message_start","message":{"model":"test-model","role":"assistant"}}\n\n'
        b'data: {"type":"content_block_start","index":0,"content_block":{"type":"text"}}\n\n'
        b'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n\n'
        b'data: {"type":"content_block_stop","index":0}\n\n'
    )
    f = tflow.tflow(resp=True)
    f.request.path = "/v1/messages/v1/chat/completions"
    f.request.content = request_body
    f.response.headers["content-type"] = "text/event-stream"
    f.response.content = response_sse
    result = get_llm_data(f)
    assert result is not None
    assert result["response"] is not None


def test_get_llm_data_unknown_provider_openai_fallback():
    request_body = json.dumps(
        {"model": "test", "messages": [{"role": "user", "content": "Hi"}]}
    ).encode()
    # SSE events with model but no anthropic or openai structure for detection
    response_sse = b'data: {"model":"test-model","content":"hello"}\n\n'
    f = tflow.tflow(resp=True)
    f.request.path = "/v1/messages/v1/chat/completions"
    f.request.content = request_body
    f.response.headers["content-type"] = "text/event-stream"
    f.response.content = response_sse
    result = get_llm_data(f)
    assert result is not None
    assert result["response"] is not None


# --- Contentview prettify edge cases ---


def test_prettify_request_detect_from_body():
    body = json.dumps(
        {"model": "claude-3-opus", "messages": [{"role": "user", "content": "Hi"}]}
    ).encode()
    meta = Metadata()
    result = llm_request.prettify(body, meta)
    assert "[LLM Request] Anthropic claude-3-opus" in result


def test_prettify_response_sse_detect_from_sse():
    raw_sse = (
        b'event: message_start\ndata: {"type":"message_start","message":{"model":"claude-3"}}\n\n'
        b'event: content_block_start\ndata: {"type":"content_block_start","index":0,"content_block":{"type":"text"}}\n\n'
        b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n\n'
        b'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n'
    )
    meta = Metadata()
    result = llm_response.prettify(raw_sse, meta)
    assert "[LLM Response] Anthropic claude-3" in result


def test_prettify_response_sse_unknown_anthropic_fallback():
    # No event: field → _detect_provider_from_sse returns None
    # But parsedData type fields work for _reconstruct_anthropic
    raw_sse = (
        b'data: {"type":"message_start","message":{"model":"test"}}\n\n'
        b'data: {"type":"content_block_start","index":0,"content_block":{"type":"text"}}\n\n'
        b'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n\n'
        b'data: {"type":"content_block_stop","index":0}\n\n'
    )
    meta = Metadata()
    result = llm_response.prettify(raw_sse, meta)
    assert "[LLM Response] Anthropic test" in result


def test_prettify_response_sse_unknown_openai_fallback():
    # Events that produce empty anthropic reconstruction but have model for openai
    raw_sse = b'data: {"model":"test","content":"hello"}\n\n'
    meta = Metadata()
    result = llm_response.prettify(raw_sse, meta)
    assert "[LLM Response] OpenAI test" in result


def test_prettify_response_sse_unknown_provider_error():
    raw_sse = b'data: {"foo":"bar"}\n\n'
    meta = Metadata()
    with pytest.raises(ValueError, match="Unable to detect"):
        llm_response.prettify(raw_sse, meta)


def test_prettify_response_json_not_dict():
    body = json.dumps([1, 2, 3]).encode()
    meta = Metadata(content_type="application/json")
    with pytest.raises(ValueError, match="Not an LLM response"):
        llm_response.prettify(body, meta)


def test_prettify_response_json_unrecognized():
    body = json.dumps({"foo": "bar"}).encode()
    meta = Metadata(content_type="application/json")
    with pytest.raises(ValueError, match="Not a recognized"):
        llm_response.prettify(body, meta)
