import * as React from "react";
import { render, screen, waitFor } from "../test-utils";
import ProxyApp from "../../components/ProxyApp";
import { enableFetchMocks } from "jest-fetch-mock";
import { ContentViewData } from "../../components/contentviews/useContentView";
import { SyntaxHighlight } from "../../backends/consts";

enableFetchMocks();

test("ProxyApp", async () => {
    const cv: ContentViewData = {
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
