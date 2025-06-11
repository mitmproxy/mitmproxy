import { TFlow } from "../../ducks/tutils";
import * as React from "react";
import HttpMessage, {
    ViewImage,
} from "../../../components/contentviews/HttpMessage";
import { fireEvent, render, screen, waitFor } from "../../test-utils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";
import { SyntaxHighlight } from "../../../backends/consts";

jest.mock("@uiw/react-codemirror", () => {
    return {
        __esModule: true,
        default: ({ value }: { value: string }) => (
            <pre data-testid="mock-editor">{value}</pre>
        ),
    };
});

enableFetchMocks();

test("HttpMessage", async () => {
    const cvd = {
        view_name: "Raw",
        description: "",
        syntax_highlight: SyntaxHighlight.NONE,
    };

    fetchMock.mockResponses(
        JSON.stringify({
            text: "data\n".repeat(10) + "additional\n",
            ...cvd,
        }),
        JSON.stringify({
            text: "rawdata\n".repeat(5),
            ...cvd,
        }),
    );

    const tflow = TFlow();
    const { asFragment } = render(
        <HttpMessage flow={tflow} message={tflow.request} />,
    );
    await waitFor(() =>
        expect(screen.getByTestId("mock-editor").textContent).toContain("data"),
    );
    await waitFor(() =>
        expect(screen.getByTestId("mock-editor").textContent).toContain(
            "additional",
        ),
    );

    fireEvent.click(screen.getByText("auto"));
    fireEvent.click(screen.getByText("raw"));
    await waitFor(() =>
        expect(screen.getByTestId("mock-editor").textContent).toContain(
            "rawdata",
        ),
    );
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
