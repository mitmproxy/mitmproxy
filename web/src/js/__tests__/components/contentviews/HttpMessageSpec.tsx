import { TFlow } from "../../ducks/tutils";
import * as React from "react";
import HttpMessage, {
    ViewImage,
} from "../../../components/contentviews/HttpMessage";
import { fireEvent, render, screen, waitFor } from "../../test-utils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

const setClipboardMocks = () => {
    const clipboard = {
        write: jest
            .fn()
            .mockRejectedValue(new Error("clipboard.write not available")),
        writeText: jest.fn().mockResolvedValue(undefined),
    };
    Object.defineProperty(navigator, "clipboard", {
        value: clipboard,
        configurable: true,
    });
    return clipboard;
};

enableFetchMocks();

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

describe("HttpMessage Format toggle", () => {
    beforeEach(() => {
        fetchMock.resetMocks();
        jest.clearAllMocks();
        jest.spyOn(console, "warn").mockImplementation(() => {});
    });

    test("toggles Format button label", async () => {
        fetchMock.mockResponseOnce(
            JSON.stringify({
                text: "some content\n",
                view_name: "Raw",
                description: "",
                syntax_highlight: "none",
            }),
        );

        const tflow = TFlow();
        render(<HttpMessage flow={tflow} message={tflow.request} />);

        await waitFor(() => screen.getByText("Copy"));

        fireEvent.click(screen.getByText("Format"));
        await waitFor(() => screen.getByText("Formatted"));

        fireEvent.click(screen.getByText("Formatted"));
        await waitFor(() => screen.getByText("Format"));
    });

    test("Copy uses raw content.data when Format is off", async () => {
        const clipboard = setClipboardMocks();

        fetchMock.mockResponses(
            JSON.stringify({
                text: "some content\n",
                view_name: "Raw",
                description: "",
                syntax_highlight: "none",
            }),
            "raw content",
        );

        const tflow = TFlow();
        render(<HttpMessage flow={tflow} message={tflow.request} />);

        await waitFor(() => screen.getByText("Copy"));
        fireEvent.click(screen.getByText("Copy"));

        await waitFor(() =>
            expect(clipboard.writeText).toHaveBeenCalledWith("raw content"),
        );

        expect(
            fetchMock.mock.calls.some(([url]) =>
                String(url).endsWith("/request/content.data"),
            ),
        ).toBe(true);
    });

    test("Copy uses prettified content view JSON when Format is on", async () => {
        const clipboard = setClipboardMocks();

        fetchMock.mockResponses(
            JSON.stringify({
                text: "some content\n",
                view_name: "Raw",
                description: "",
                syntax_highlight: "none",
            }),
            JSON.stringify({
                text: "pretty content\n",
                view_name: "Auto",
                description: "",
                syntax_highlight: "none",
            }),
        );

        const tflow = TFlow();
        render(<HttpMessage flow={tflow} message={tflow.request} />);

        await waitFor(() => screen.getByText("Copy"));
        fireEvent.click(screen.getByText("Format"));
        await waitFor(() => screen.getByText("Formatted"));

        fireEvent.click(screen.getByText("Copy"));
        await waitFor(() =>
            expect(clipboard.writeText).toHaveBeenCalledWith(
                "pretty content\n",
            ),
        );

        expect(
            fetchMock.mock.calls.some(([url]) =>
                /\/request\/content\/Auto\.json(\?|$)/.test(String(url)),
            ),
        ).toBe(true);
        expect(
            fetchMock.mock.calls.some(([url]) =>
                String(url).endsWith("/request/content.data"),
            ),
        ).toBe(false);
    });

    test("Edit fetches prettified content view when Format is on", async () => {
        fetchMock.mockResponses(
            JSON.stringify({
                text: "some content\n",
                view_name: "Raw",
                description: "",
                syntax_highlight: "none",
            }),
            JSON.stringify({
                text: "pretty content\n",
                view_name: "Auto",
                description: "",
                syntax_highlight: "none",
            }),
        );

        const tflow = TFlow();
        render(<HttpMessage flow={tflow} message={tflow.request} />);

        await waitFor(() => screen.getByText("Copy"));
        fireEvent.click(screen.getByText("Format"));
        await waitFor(() => screen.getByText("Formatted"));

        fireEvent.click(screen.getByText("Edit"));
        await waitFor(() => screen.getByText("[Editing]"));

        expect(
            fetchMock.mock.calls.some(([url]) =>
                /\/request\/content\/Auto\.json(\?|$)/.test(String(url)),
            ),
        ).toBe(true);
        expect(
            fetchMock.mock.calls.some(([url]) =>
                String(url).endsWith("/request/content.data"),
            ),
        ).toBe(false);
    });
});
