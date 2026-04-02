import { TFlow } from "../../ducks/tutils";
import * as React from "react";
import HttpMessage, {
    ViewImage,
} from "../../../components/contentviews/HttpMessage";
import { act, fireEvent, render, screen, waitFor } from "../../test-utils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

enableFetchMocks();

let mockUseCodeEditor = false,
    mockCapturedOnChange: ((content: string) => void) | null = null;

jest.mock("../../../components/contentviews/CodeEditor", () => {
    const actual = jest.requireActual(
        "../../../components/contentviews/CodeEditor",
    );
    return {
        __esModule: true,
        default: ({
            initialContent,
            onChange,
        }: {
            initialContent: string;
            onChange: (c: string) => void;
        }) => {
            if (!mockUseCodeEditor) {
                return actual.default({ initialContent, onChange });
            }
            mockCapturedOnChange = onChange;
            return (
                <textarea data-testid="mock-editor" defaultValue={initialContent} />
            );
        },
    };
});

test("HttpMessage", async () => {
    const text = "data\n".repeat(512) + "additional\n".repeat(512);

    const cvd = {
        view_name: "Raw",
        description: "",
        syntax_highlight: "none",
    };

    fetchMock.mockResponses(
        JSON.stringify({
            text: "data\n".repeat(512) + "additional\n",
            ...cvd,
        }),
        JSON.stringify({
            text,
            ...cvd,
        }),
        JSON.stringify({
            text: "rawdata\n".repeat(5),
            ...cvd,
        }),
        "raw content",
        JSON.stringify({
            text: "rawdata\n".repeat(5),
            ...cvd,
        }),
    );

    const tflow = TFlow();
    const { asFragment } = render(
        <HttpMessage flow={tflow} message={tflow.request} />,
    );
    await waitFor(() => screen.getAllByText("data"));
    expect(screen.queryByText("additional")).toBeNull();

    fireEvent.click(screen.getByText("Show more"));
    await waitFor(() => screen.getAllByText("additional"));

    fireEvent.click(screen.getByText("auto"));
    fireEvent.click(screen.getByText("raw"));
    await waitFor(() => screen.getAllByText("rawdata"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Edit"));
    expect(asFragment()).toMatchSnapshot();
    fireEvent.click(screen.getByText("Cancel"));

    await waitFor(() => screen.getAllByText("rawdata"));
    expect(asFragment()).toMatchSnapshot();

    await waitFor(() => screen.getByText("Copy"));
    expect(asFragment()).toMatchSnapshot();
});

test("ViewImage", async () => {
    const flow = TFlow();
    const { asFragment } = render(
        <ViewImage flow={flow} message={flow.request} />,
    );
    expect(asFragment()).toMatchSnapshot();
});

/*
    This test differs from the one above because clicking the copy button triggers 'handleClickCopyButton'.
    In the previous test, the response contained "raw content," which caused an "invalid JSON response body" error
    when processing the following line:
    `const data: ContentViewData = await response.json()`
    since "raw content" is not valid JSON.
*/
describe("HttpMessage Copy Button", () => {
    beforeEach(() => {
        fetchMock.resetMocks();
        jest.spyOn(console, "error").mockImplementation(() => {});
    });

    test("handles successful copy action", async () => {
        jest.spyOn(console, "warn").mockImplementation(() => {});

        const text = "data\nadditional\n";
        fetchMock.mockResponse(JSON.stringify({ text, description: "Auto" }));

        const tflow = TFlow();
        render(<HttpMessage flow={tflow} message={tflow.request} />);

        await waitFor(() => screen.getByText("Copy"));

        fireEvent.click(screen.getByText("Copy"));
    });

    test("handles failed fetch with non-ok response", async () => {
        fetchMock.mockResponse("", {
            status: 500,
            statusText: "Internal Server Error",
        });

        const tflow = TFlow();
        render(<HttpMessage flow={tflow} message={tflow.request} />);

        await waitFor(() => screen.getByText("Copy"));
        fireEvent.click(screen.getByText("Copy"));

        await waitFor(() =>
            expect(console.error).toHaveBeenCalledWith(expect.any(Error)),
        );
    });
});

describe("HttpMessage body edit", () => {
    const cvd = { view_name: "Raw", description: "", syntax_highlight: "none" };

    beforeEach(() => {
        mockUseCodeEditor = true;
        mockCapturedOnChange = null;
        fetchMock.resetMocks();
    });

    afterEach(() => {
        mockUseCodeEditor = false;
        mockCapturedOnChange = null;
    });

    test("saving empty body sends empty string, not original content", async () => {
        fetchMock.mockResponses(
            JSON.stringify({ text: "original body", ...cvd }),
            "original body",
            JSON.stringify({}),
        );

        const tflow = TFlow();
        render(<HttpMessage flow={tflow} message={tflow.request} />);
        await waitFor(() => screen.getAllByText("original body"));

        fireEvent.click(screen.getByText("Edit"));
        await waitFor(() => screen.getByText("Done"));

        expect(mockCapturedOnChange).not.toBeNull();
        act(() => mockCapturedOnChange!(""));

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
            JSON.stringify({ text: "original body", ...cvd }),
            "original body",
            JSON.stringify({}),
        );

        const tflow = TFlow();
        render(<HttpMessage flow={tflow} message={tflow.request} />);
        await waitFor(() => screen.getAllByText("original body"));

        fireEvent.click(screen.getByText("Edit"));
        await waitFor(() => {
            const editor = screen.getByTestId(
                "mock-editor",
            ) as HTMLTextAreaElement;
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
});
