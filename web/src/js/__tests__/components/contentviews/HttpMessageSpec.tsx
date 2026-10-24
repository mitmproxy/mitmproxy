import { TFlow } from "../../ducks/tutils";
import * as React from "react";
import HttpMessage, {
    ViewImage,
} from "../../../components/contentviews/HttpMessage";
import { act, fireEvent, render, screen, waitFor } from "../../test-utils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

enableFetchMocks();

// When mockUseCodeEditor is true, CodeEditor becomes a plain textarea and the
// latest onChange/onSave are captured so tests can drive edits and saves.
let mockUseCodeEditor = false,
    mockCapturedOnChange: ((content: string) => void) | null = null,
    mockCapturedOnSave: (() => void) | null = null;

jest.mock("../../../components/contentviews/CodeEditor", () => {
    const actual = jest.requireActual(
        "../../../components/contentviews/CodeEditor",
    );
    return {
        __esModule: true,
        default: (props: {
            content: string;
            onChange?: (c: string) => void;
            onSave?: () => void;
        }) => {
            if (!mockUseCodeEditor) {
                return actual.default(props);
            }
            mockCapturedOnChange = props.onChange ?? null;
            mockCapturedOnSave = props.onSave ?? null;
            return (
                <textarea
                    data-testid="mock-editor"
                    value={props.content}
                    readOnly
                />
            );
        },
    };
});

beforeEach(() => {
    mockUseCodeEditor = false;
    mockCapturedOnChange = null;
    mockCapturedOnSave = null;
    fetchMock.resetMocks();
});

const cvd = { view_name: "Raw", description: "", syntax_highlight: "none" };

test("HttpMessage renders full content inline and switches views", async () => {
    mockUseCodeEditor = true;

    fetchMock.mockResponses(
        JSON.stringify({ text: "data\nadditional\n", ...cvd }),
        JSON.stringify({ text: "rawdata\n".repeat(5), ...cvd }),
    );

    const tflow = TFlow();
    render(<HttpMessage flow={tflow} message={tflow.request} />);

    await waitFor(() => {
        const editor = screen.getByTestId("mock-editor") as HTMLTextAreaElement;
        expect(editor.value).toContain("additional");
    });
    expect(screen.queryByText("Show more")).toBeNull();

    fireEvent.click(screen.getByText("auto"));
    fireEvent.click(screen.getByText("raw"));
    await waitFor(() => {
        const editor = screen.getByTestId("mock-editor") as HTMLTextAreaElement;
        expect(editor.value).toContain("rawdata");
    });

    // No edit/view toggle, and Save is hidden until edited.
    expect(screen.queryByText("Edit")).toBeNull();
    expect(screen.queryByText("Save")).toBeNull();
});

test("HttpMessage shows Save/dirty only after editing and PUTs the edit", async () => {
    mockUseCodeEditor = true;

    fetchMock.mockResponses(
        JSON.stringify({ text: "original body", ...cvd }),
        JSON.stringify({}),
    );

    const tflow = TFlow();
    render(<HttpMessage flow={tflow} message={tflow.request} />);
    await waitFor(() => screen.getByTestId("mock-editor"));

    expect(screen.queryByText("Save")).toBeNull();
    expect(screen.queryByTitle("Unsaved changes")).toBeNull();

    act(() => mockCapturedOnChange!("edited body"));

    await screen.findByText("Save");
    expect(screen.getByTitle("Unsaved changes")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Save"));

    await waitFor(() => {
        const putCall = fetchMock.mock.calls.find(
            ([, opts]) => opts && (opts as RequestInit).method === "PUT",
        );
        expect(putCall).toBeDefined();
        const body = JSON.parse(putCall![1]!.body as string);
        expect(body.request.content).toBe("edited body");
    });
});

test("HttpMessage saves an empty body as an empty string", async () => {
    mockUseCodeEditor = true;

    fetchMock.mockResponses(
        JSON.stringify({ text: "original body", ...cvd }),
        JSON.stringify({}),
    );

    const tflow = TFlow();
    render(<HttpMessage flow={tflow} message={tflow.request} />);
    await waitFor(() => screen.getByTestId("mock-editor"));

    act(() => mockCapturedOnChange!(""));
    fireEvent.click(await screen.findByText("Save"));

    await waitFor(() => {
        const putCall = fetchMock.mock.calls.find(
            ([, opts]) => opts && (opts as RequestInit).method === "PUT",
        );
        expect(putCall).toBeDefined();
        const body = JSON.parse(putCall![1]!.body as string);
        expect(body.request.content).toBe("");
    });
});

test("HttpMessage re-typing the original content hides Save", async () => {
    mockUseCodeEditor = true;

    fetchMock.mockResponses(JSON.stringify({ text: "original body", ...cvd }));

    const tflow = TFlow();
    render(<HttpMessage flow={tflow} message={tflow.request} />);
    await waitFor(() => screen.getByTestId("mock-editor"));

    act(() => mockCapturedOnChange!("edited body"));
    await screen.findByText("Save");

    act(() => mockCapturedOnChange!("original body"));
    await waitFor(() => expect(screen.queryByText("Save")).toBeNull());
});

test("HttpMessage wires the editor's onSave callback to the content PUT", async () => {
    // The keystroke -> onSave binding itself is covered in CodeEditorSpec.
    mockUseCodeEditor = true;

    fetchMock.mockResponses(
        JSON.stringify({ text: "original body", ...cvd }),
        JSON.stringify({}),
    );

    const tflow = TFlow();
    render(<HttpMessage flow={tflow} message={tflow.request} />);
    await waitFor(() => screen.getByTestId("mock-editor"));

    act(() => mockCapturedOnChange!("edited via onSave"));
    await screen.findByText("Save");

    act(() => mockCapturedOnSave!());

    await waitFor(() => {
        const putCall = fetchMock.mock.calls.find(
            ([, opts]) => opts && (opts as RequestInit).method === "PUT",
        );
        expect(putCall).toBeDefined();
        const body = JSON.parse(putCall![1]!.body as string);
        expect(body.request.content).toBe("edited via onSave");
    });
});

test("HttpMessage shows 'No content' and an editable editor for an empty body", async () => {
    mockUseCodeEditor = true;

    fetchMock.mockResponse(JSON.stringify({ text: "", ...cvd }));

    const tflow = TFlow();
    tflow.request.contentLength = 0;
    render(<HttpMessage flow={tflow} message={tflow.request} />);

    expect(await screen.findByText("No content")).toBeInTheDocument();
    const editor = (await screen.findByTestId(
        "mock-editor",
    )) as HTMLTextAreaElement;
    expect(editor.value).toBe("");
});

test("HttpMessage uploads a replacement via the Replace file chooser", async () => {
    fetchMock.mockResponse(JSON.stringify({ text: "original", ...cvd }));

    const tflow = TFlow();
    const { container } = render(
        <HttpMessage flow={tflow} message={tflow.request} />,
    );
    await waitFor(() => screen.getByText("Replace"));

    const fileInput = container.querySelector(
        "input[type=file]",
    ) as HTMLInputElement;
    const file = new File(["replacement"], "body.txt", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
        const postCall = fetchMock.mock.calls.find(
            ([url, opts]) =>
                typeof url === "string" &&
                url.includes("/request/content.data") &&
                opts &&
                (opts as RequestInit).method === "POST",
        );
        expect(postCall).toBeDefined();
    });
});

test("ViewImage", async () => {
    const flow = TFlow();
    const { asFragment } = render(
        <ViewImage flow={flow} message={flow.request} />,
    );
    expect(asFragment()).toMatchSnapshot();
});

test("ViewImage.matches", () => {
    const flow = TFlow();
    const matches = (contentType: string) => {
        flow.response.headers = [["Content-Type", contentType]];
        return ViewImage.matches(flow.response);
    };
    expect(matches("image/png")).toBe(true);
    expect(matches("image/jpeg")).toBe(true);
    expect(matches("image/jpg")).toBe(true);
    expect(matches("image/gif")).toBe(true);
    expect(matches("image/webp")).toBe(true);
    expect(matches("image/avif")).toBe(true);
    expect(matches("image/svg+xml")).toBe(true);
    expect(matches("image/vnd.microsoft.icon")).toBe(true);
    expect(matches("image/x-icon")).toBe(true);
    expect(matches("IMAGE/AVIF")).toBe(true);
    expect(matches("image/heic")).toBe(false);
    expect(matches("application/json")).toBe(false);
    expect(matches("video/mp4")).toBe(false);
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
