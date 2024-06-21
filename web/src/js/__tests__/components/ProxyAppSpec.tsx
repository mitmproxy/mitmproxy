import * as React from "react";
import { render, screen, waitFor } from "../test-utils";
import ProxyApp from "../../components/ProxyApp";
import { enableFetchMocks } from "jest-fetch-mock";
import { ContentViewData } from "../../components/contentviews/useContent";

enableFetchMocks();

test("ProxyApp", async () => {
    const cv: ContentViewData = {
        lines: [[["text", "my data"]]],
        description: "",
    };
    fetchMock.doMockOnceIf(
        "./flows/flow2/request/content/Auto.json?lines=513",
        JSON.stringify(cv),
    );
    render(<ProxyApp />);
    expect(screen.getByTitle("Mitmproxy Version")).toBeDefined();
    await waitFor(() => screen.getByText("my data"));
});
