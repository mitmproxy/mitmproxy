import * as React from "react";
import { act, fireEvent, render, screen } from "../../test-utils";
import {
    LLMRequest,
    LLMResponse,
    LLMRequestJSON,
    LLMResponseJSON,
} from "../../../components/FlowView/LLM";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

enableFetchMocks();

const anthropicLLMData = {
    provider: "anthropic",
    request: {
        model: "claude-sonnet-4-20250514",
        system: "You are helpful.",
        messages: [
            { role: "user", content: "Hello" },
            {
                role: "assistant",
                content: [
                    { type: "text", text: "I can help!" },
                    { type: "thinking", thinking: "Let me think..." },
                    {
                        type: "tool_use",
                        name: "get_weather",
                        id: "t1",
                        input: { location: "NYC" },
                    },
                    {
                        type: "tool_result",
                        tool_use_id: "t1",
                        content: "Sunny",
                    },
                    { type: "image" },
                ],
            },
        ],
        tools: [
            {
                name: "get_weather",
                description: "Get weather",
                input_schema: { type: "object" },
            },
        ],
        parameters: { max_tokens: 4096, stream: true },
    },
    request_json: {
        model: "claude-sonnet-4-20250514",
        messages: [{ role: "user", content: "Hello" }],
    },
    response: {
        model: "claude-sonnet-4-20250514",
        role: "assistant",
        blocks: [
            { type: "text", content: "Hello!", id: null, name: null },
            {
                type: "tool_use",
                content: "",
                id: "toolu_1",
                name: "get_weather",
                input: { location: "NYC" },
            },
            {
                type: "web_search_tool_result",
                content: "",
                tool_use_id: "srv_1",
                block_content: [
                    { title: "Result", url: "https://example.com" },
                ],
            },
        ],
        stop_reason: "end_turn",
        usage: { input_tokens: 100, output_tokens: 50 },
    },
    response_json: {
        role: "assistant",
        model: "claude-sonnet-4-20250514",
        content: [{ type: "text", text: "Hello!" }],
    },
    chat_messages: [],
};

const openaiLLMData = {
    provider: "openai",
    request: {
        model: "gpt-4",
        system: null,
        messages: [{ role: "user", content: "Hello" }],
        tools: [],
        parameters: { temperature: 0.7 },
    },
    request_json: {
        model: "gpt-4",
        messages: [{ role: "user", content: "Hello" }],
    },
    response: {
        model: "gpt-4",
        role: "assistant",
        content: "Hi there!",
        tool_calls: [
            {
                id: "call_1",
                function: {
                    name: "get_weather",
                    arguments: { location: "NYC" },
                },
            },
        ],
        finish_reason: "stop",
        usage: { prompt_tokens: 10, completion_tokens: 5 },
    },
    response_json: {
        role: "assistant",
        model: "gpt-4",
        content: "Hi there!",
    },
    chat_messages: [],
};

// Data with various JSON value types and edge-case message content
const richLLMData = {
    provider: "anthropic",
    request: {
        model: "claude-3",
        system: { type: "text", text: "Be helpful" },
        messages: [
            { role: "user", content: { key: "value" } },
            { role: "user", content: 42 },
            {
                role: "assistant",
                content: [{ type: "custom_block", text: "Custom" }],
            },
        ],
        tools: [],
        parameters: {},
    },
    request_json: {
        count: 42,
        active: true,
        metadata: null,
        tags: ["a", "b"],
    },
    response: null,
    response_json: null,
    chat_messages: [],
};

beforeEach(() => {
    fetchMock.resetMocks();
});

describe("LLMRequest", () => {
    it("should render loading state", () => {
        fetchMock.mockResponseOnce(
            () => new Promise((resolve) => setTimeout(resolve, 10000)),
        );
        const { asFragment } = render(<LLMRequest />);
        expect(asFragment()).toMatchSnapshot();
        expect(screen.getByText("Loading...")).toBeTruthy();
    });

    it("should render error state", async () => {
        fetchMock.mockResponseOnce("", { status: 500 });
        const warnSpy = jest
            .spyOn(console, "warn")
            .mockImplementation(() => {});
        await act(async () => {
            render(<LLMRequest />);
        });
        expect(screen.getByText("Failed to load LLM data.")).toBeTruthy();
        warnSpy.mockRestore();
    });

    it("should render anthropic request", async () => {
        fetchMock.mockResponseOnce(JSON.stringify(anthropicLLMData));
        await act(async () => {
            render(<LLMRequest />);
        });
        expect(screen.getByText("anthropic")).toBeTruthy();
        expect(screen.getByText("claude-sonnet-4-20250514")).toBeTruthy();
    });

    it("should render openai request", async () => {
        fetchMock.mockResponseOnce(JSON.stringify(openaiLLMData));
        await act(async () => {
            render(<LLMRequest />);
        });
        expect(screen.getByText("openai")).toBeTruthy();
        expect(screen.getByText("gpt-4")).toBeTruthy();
    });

    it("should render messages with object and primitive content", async () => {
        fetchMock.mockResponseOnce(JSON.stringify(richLLMData));
        await act(async () => {
            render(<LLMRequest />);
        });
        // Object content renders as collapsed InlineJSON with "1 key" hint
        const container = document.querySelector(".llm-inline-json");
        expect(container).toBeTruthy();
        // Numeric content renders as String(42)
        expect(screen.getByText("42")).toBeTruthy();
        // Custom block type triggers MessagePart default case
        expect(screen.getByText("custom_block")).toBeTruthy();
        expect(screen.getByText("Custom")).toBeTruthy();
    });
});

describe("LLMResponse", () => {
    it("should render loading state", () => {
        fetchMock.mockResponseOnce(
            () => new Promise((resolve) => setTimeout(resolve, 10000)),
        );
        const { asFragment } = render(<LLMResponse />);
        expect(asFragment()).toMatchSnapshot();
        expect(screen.getByText("Loading...")).toBeTruthy();
    });

    it("should render error state", async () => {
        fetchMock.mockResponseOnce("", { status: 500 });
        const warnSpy = jest
            .spyOn(console, "warn")
            .mockImplementation(() => {});
        await act(async () => {
            render(<LLMResponse />);
        });
        expect(screen.getByText("Failed to load LLM data.")).toBeTruthy();
        warnSpy.mockRestore();
    });

    it("should render no response data", async () => {
        fetchMock.mockResponseOnce(
            JSON.stringify({ ...anthropicLLMData, response: null }),
        );
        await act(async () => {
            render(<LLMResponse />);
        });
        expect(screen.getByText("No LLM response data.")).toBeTruthy();
    });

    it("should render anthropic response with blocks", async () => {
        fetchMock.mockResponseOnce(JSON.stringify(anthropicLLMData));
        await act(async () => {
            render(<LLMResponse />);
        });
        expect(screen.getByText("anthropic")).toBeTruthy();
        expect(screen.getByText(/Content Blocks/)).toBeTruthy();
        expect(screen.getByText("Stop Reason")).toBeTruthy();
    });

    it("should render openai response with content and tool calls", async () => {
        fetchMock.mockResponseOnce(JSON.stringify(openaiLLMData));
        await act(async () => {
            render(<LLMResponse />);
        });
        expect(screen.getByText("openai")).toBeTruthy();
        expect(screen.getByText("Hi there!")).toBeTruthy();
        expect(screen.getByText(/Tool Calls/)).toBeTruthy();
        expect(screen.getByText("Finish Reason")).toBeTruthy();
    });
});

describe("LLMRequestJSON", () => {
    it("should render loading state", () => {
        fetchMock.mockResponseOnce(
            () => new Promise((resolve) => setTimeout(resolve, 10000)),
        );
        render(<LLMRequestJSON />);
        expect(screen.getByText("Loading...")).toBeTruthy();
    });

    it("should render no request JSON", async () => {
        fetchMock.mockResponseOnce(
            JSON.stringify({ ...anthropicLLMData, request_json: null }),
        );
        await act(async () => {
            render(<LLMRequestJSON />);
        });
        expect(screen.getByText("No LLM request JSON.")).toBeTruthy();
    });

    it("should render request JSON", async () => {
        fetchMock.mockResponseOnce(JSON.stringify(anthropicLLMData));
        await act(async () => {
            render(<LLMRequestJSON />);
        });
        expect(screen.getByText(/model/)).toBeTruthy();
    });

    it("should render JSON with null, boolean, and number values", async () => {
        fetchMock.mockResponseOnce(JSON.stringify(richLLMData));
        await act(async () => {
            render(<LLMRequestJSON />);
        });
        // Number value
        expect(screen.getByText("42")).toBeTruthy();
        // Boolean value
        expect(screen.getByText("true")).toBeTruthy();
        // Null value
        expect(screen.getByText("null")).toBeTruthy();
    });

    it("should expand collapsed JSON array on click", async () => {
        fetchMock.mockResponseOnce(JSON.stringify(richLLMData));
        await act(async () => {
            render(<LLMRequestJSON />);
        });
        // The "tags" array is nested so rendered collapsed with "2 items"
        const hint = screen.getByText(/2 items/);
        expect(hint).toBeTruthy();
        // Click the toggle to expand
        const toggle = hint.parentElement!.querySelector(".json-toggle")!;
        fireEvent.click(toggle);
        // After expanding, individual items are visible
        expect(screen.getByText(/"a"/)).toBeTruthy();
        expect(screen.getByText(/"b"/)).toBeTruthy();
    });

    it("should copy leaf value on click", async () => {
        const writeText = jest.fn().mockResolvedValue(undefined);
        Object.defineProperty(navigator, "clipboard", {
            value: { writeText },
            writable: true,
            configurable: true,
        });

        fetchMock.mockResponseOnce(JSON.stringify(richLLMData));
        await act(async () => {
            render(<LLMRequestJSON />);
        });
        // Click on the "42" number leaf
        const leaf = screen.getByText("42");
        await act(async () => {
            fireEvent.click(leaf);
        });
        expect(writeText).toHaveBeenCalledWith("42");
    });
});

describe("LLMResponseJSON", () => {
    it("should render loading state", () => {
        fetchMock.mockResponseOnce(
            () => new Promise((resolve) => setTimeout(resolve, 10000)),
        );
        render(<LLMResponseJSON />);
        expect(screen.getByText("Loading...")).toBeTruthy();
    });

    it("should render no response JSON", async () => {
        fetchMock.mockResponseOnce(
            JSON.stringify({ ...anthropicLLMData, response_json: null }),
        );
        await act(async () => {
            render(<LLMResponseJSON />);
        });
        expect(screen.getByText("No LLM response JSON.")).toBeTruthy();
    });

    it("should render response JSON", async () => {
        fetchMock.mockResponseOnce(JSON.stringify(anthropicLLMData));
        await act(async () => {
            render(<LLMResponseJSON />);
        });
        expect(screen.getByText(/role/)).toBeTruthy();
    });
});

describe("CopyButton", () => {
    it("should copy section content on click", async () => {
        const writeText = jest.fn().mockResolvedValue(undefined);
        Object.defineProperty(navigator, "clipboard", {
            value: { writeText },
            writable: true,
            configurable: true,
        });

        fetchMock.mockResponseOnce(JSON.stringify(openaiLLMData));
        await act(async () => {
            render(<LLMResponse />);
        });
        // Find a copy button by title
        const copyBtn = screen.getAllByTitle("Copy")[0];
        await act(async () => {
            fireEvent.click(copyBtn);
        });
        expect(writeText).toHaveBeenCalled();
    });
});
