import { TFlow } from "../../ducks/tutils";
import * as React from "react";
import HttpMessage from "../../../components/contentviews/HttpMessage";
import { act, fireEvent, render, screen, waitFor } from "../../test-utils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

enableFetchMocks();

// Mock CodeEditor to control onChange directly — CodeMirror is not drivable in jsdom.
let capturedOnChange: ((content: string) => void) | null = null;

jest.mock("../../../components/contentviews/CodeEditor", () => ({
    __esModule: true,
    default: ({
        initialContent,
        onChange,
    }: {
        initialContent: string;
        onChange: (c: string) => void;
    }) => {
        capturedOnChange = onChange;
        return (
            <textarea data-testid="mock-editor" defaultValue={initialContent} />
        );
    },
}));

beforeEach(() => {
    fetchMock.resetMocks();
    capturedOnChange = null;
});

const CVD = { view_name: "Raw", description: "", syntax_highlight: "none" };

test("saving empty body sends empty string, not original content", async () => {
    fetchMock.mockResponses(
        JSON.stringify({ text: "original body", ...CVD }),
        "original body",
        JSON.stringify({}),
    );

    const tflow = TFlow();
    render(<HttpMessage flow={tflow} message={tflow.request} />);
    await waitFor(() => screen.getAllByText("original body"));

    fireEvent.click(screen.getByText("Edit"));
    await waitFor(() => screen.getByText("Done"));

    // Simulate user clearing body — onChange fires with ""
    expect(capturedOnChange).not.toBeNull();
    act(() => capturedOnChange!(""));

    fireEvent.click(screen.getByText("Done"));

    await waitFor(() => {
        const putCall = fetchMock.mock.calls.find(
            ([, opts]) => opts && (opts as RequestInit).method === "PUT",
        );
        expect(putCall).toBeDefined();
        const body = JSON.parse(putCall![1]!.body as string);
        expect(body.request.content).toBe("");
    });
});

test("saving unedited body sends original content", async () => {
    fetchMock.mockResponses(
        JSON.stringify({ text: "original body", ...CVD }),
        "original body",
        JSON.stringify({}),
    );

    const tflow = TFlow();
    render(<HttpMessage flow={tflow} message={tflow.request} />);
    await waitFor(() => screen.getAllByText("original body"));

    // Don't call onChange — editedContent stays undefined
    fireEvent.click(screen.getByText("Edit"));
    // Wait for content to load in editor (useContent fetches asynchronously)
    await waitFor(() => {
        const editor = screen.getByTestId("mock-editor") as HTMLTextAreaElement;
        expect(editor.defaultValue).toBe("original body");
    });
    fireEvent.click(screen.getByText("Done"));

    await waitFor(() => {
        const putCall = fetchMock.mock.calls.find(
            ([, opts]) => opts && (opts as RequestInit).method === "PUT",
        );
        expect(putCall).toBeDefined();
        const body = JSON.parse(putCall![1]!.body as string);
        expect(body.request.content).toBe("original body");
    });
});
