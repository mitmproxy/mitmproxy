import { TFlow } from "../../ducks/tutils";
import * as React from "react";
import HttpMessage, {
    ViewImage,
} from "../../../components/contentviews/HttpMessage";
import { fireEvent, render, screen, waitFor } from "../../test-utils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

jest.mock("../../../contrib/CodeMirror");

enableFetchMocks();

test("HttpMessage", async () => {
    const lines = Array(512)
        .fill([["text", "data"]])
        .concat(Array(512).fill([["text", "additional"]]));

    fetchMock.mockResponses(
        JSON.stringify({
            lines: lines.slice(0, 512 + 1),
            description: "Auto",
        }),
        JSON.stringify({
            lines,
            description: "Auto",
        }),
        JSON.stringify({
            lines: Array(5).fill([["text", "rawdata"]]),
            description: "Raw",
        }),
        "raw content",
        JSON.stringify({
            lines: Array(5).fill([["text", "rawdata"]]),
            description: "Raw",
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
        const lines = [[["text", "data"]], [["text", "additional"]]];
        fetchMock.mockResponse(JSON.stringify({ lines, description: "Auto" }));

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
