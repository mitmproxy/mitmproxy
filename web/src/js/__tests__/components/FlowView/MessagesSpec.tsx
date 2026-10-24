import * as React from "react";
import { render, screen, waitFor } from "../../test-utils";
import Messages from "../../../components/FlowView/Messages";
import { TFlow } from "../../ducks/tutils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

enableFetchMocks();

// Render bodies through a plain marker instead of CodeMirror.
jest.mock("../../../components/contentviews/CodeEditor", () => ({
    __esModule: true,
    default: ({
        content,
        readonly,
    }: {
        content: string;
        readonly?: boolean;
    }) => (
        <pre data-testid="msg-editor" data-readonly={String(!!readonly)}>
            {content}
        </pre>
    ),
}));

beforeEach(() => {
    fetchMock.resetMocks();
});

test("Messages renders each message read-only with a direction icon", async () => {
    const messages = [
        {
            text: "client says hi",
            view_name: "Raw",
            description: "",
            syntax_highlight: "none",
            from_client: true,
            timestamp: 946681200,
        },
        {
            text: "server replies",
            view_name: "Raw",
            description: "",
            syntax_highlight: "none",
            from_client: false,
            timestamp: 946681201,
        },
    ];
    fetchMock.mockResponse(JSON.stringify(messages));

    const flow = TFlow();
    render(
        <Messages
            flow={flow}
            messages_meta={{ contentLength: 29, count: 2 }}
        />,
    );

    expect(screen.getByText("2 Messages")).toBeInTheDocument();

    await waitFor(() => {
        const editors = screen.getAllByTestId("msg-editor");
        expect(editors).toHaveLength(2);
    });

    const editors = screen.getAllByTestId("msg-editor");
    expect(editors[0]).toHaveTextContent("client says hi");
    expect(editors[1]).toHaveTextContent("server replies");
    editors.forEach((e) =>
        expect(e.getAttribute("data-readonly")).toBe("true"),
    );

    // Scoped per message so a swapped from_client -> icon mapping would fail.
    const clientMsg = editors[0].parentElement!;
    const serverMsg = editors[1].parentElement!;
    expect(clientMsg.querySelector(".icon-arrowRight")).toBeInTheDocument();
    expect(clientMsg.querySelector(".icon-arrowLeft")).toBeNull();
    expect(serverMsg.querySelector(".icon-arrowLeft")).toBeInTheDocument();
    expect(serverMsg.querySelector(".icon-arrowRight")).toBeNull();
});

test("Messages renders a single error entry for a non-JSON response", async () => {
    // Non-JSON makes useContentView fall back to one error entry.
    fetchMock.mockResponse("Error getting content: 500.");

    const flow = TFlow();
    render(
        <Messages flow={flow} messages_meta={{ contentLength: 0, count: 1 }} />,
    );

    await waitFor(() => {
        const editors = screen.getAllByTestId("msg-editor");
        expect(editors).toHaveLength(1);
        expect(editors[0]).toHaveTextContent("Error getting content: 500.");
    });
});
