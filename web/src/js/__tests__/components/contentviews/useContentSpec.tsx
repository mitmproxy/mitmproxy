import * as React from "react";
import { render, screen, waitFor } from "../../test-utils";
import { useContent } from "../../../components/contentviews/useContent";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

enableFetchMocks();

function TComp({ url, hash }: { url: string; hash: string }) {
    const content = useContent(url, hash);
    return <div>{content}</div>;
}

test("caching", async () => {
    fetchMock.mockResponses("hello", "world");
    const { rerender } = render(<TComp url="/content" hash="hash" />);

    await waitFor(() => screen.getByText("hello"));
    rerender(<TComp url="/content" hash="hash" />);
    expect(fetchMock.mock.calls).toHaveLength(1);

    rerender(<TComp url="/content" hash="newhash" />);
    await waitFor(() => screen.getByText("world"));
    expect(fetchMock.mock.calls).toHaveLength(2);
});

test("network error", async () => {
    fetchMock.mockRejectOnce(new Error("I/O error"));
    render(<TComp url="/content" hash="hash" />);
    await waitFor(() =>
        screen.getByText("Error getting content: Error: I/O error."),
    );
});
