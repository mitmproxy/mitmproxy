import * as React from "react";
import { render, screen, waitFor } from "../test-utils";
import ProxyApp from "../../components/ProxyApp";
import { enableFetchMocks } from "jest-fetch-mock";
import { SyntaxHighlight } from "../../backends/consts";

jest.mock("@uiw/react-codemirror", () => {
    return {
        __esModule: true,
        default: ({ value }: { value: string }) => (
            <pre data-testid="mock-editor">{value}</pre>
        ),
    };
});

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
    expect(screen.getByTitle("Mitmproxy Version")).toBeDefined();
    await waitFor(() => screen.getByText("my data"));
});
