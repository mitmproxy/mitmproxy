import * as React from "react";
import { render, screen, waitFor } from "../test-utils";
import ProxyApp from "../../components/ProxyApp";
import { enableFetchMocks } from "jest-fetch-mock";
import { SyntaxHighlight } from "../../backends/consts";

// Render content through a plain element instead of CodeMirror, whose
// async measuring throws in jsdom (textRange(...).getClientRects).
jest.mock("../../components/contentviews/CodeEditor", () => ({
    __esModule: true,
    default: ({ content }: { content: string }) => <pre>{content}</pre>,
}));

enableFetchMocks();

test("ProxyApp", async () => {
    const cv = {
        text: "my data",
        view_name: "raw",
        syntax_highlight: SyntaxHighlight.NONE,
        description: "",
    };
    fetchMock.doMockOnceIf(
        "./flows/flow2/request/content/Auto.json",
        JSON.stringify(cv),
    );
    render(<ProxyApp />);
    expect(screen.getByTitle("Mitmproxy Version")).toBeVisible();
    await waitFor(() => screen.getByText("my data"));
});
