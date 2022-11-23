import {TFlow} from "../../ducks/tutils";
import * as React from 'react';
import HttpMessage, {ViewImage} from '../../../components/contentviews/HttpMessage'
import {fireEvent, render, screen, waitFor} from "../../test-utils"
import fetchMock, {enableFetchMocks} from "jest-fetch-mock";

jest.mock("../../../contrib/CodeMirror", () => {
    const React = require("react");
    return {
        __esModule: true,
        default: React.forwardRef((props, ref) => {
            React.useImperativeHandle(ref, () => ({
                codeMirror: {
                    getValue: () => props.value
                }
            }));
            return <div>{props.value}</div>
        })
    }
})

enableFetchMocks();

test("HttpMessage", async () => {
    const lines = Array(512).fill([["text", "data"]]).concat(
        Array(512).fill([["text", "additional"]])
    );

    fetchMock.mockResponses(
        JSON.stringify({
            lines: lines.slice(0, 512 + 1),
            description: "Auto"
        }), JSON.stringify({
            lines,
            description: "Auto"
        }), JSON.stringify({
            lines: Array(5).fill([["text", "rawdata"]]),
            description: "Raw",
        }),
        "raw content",
        JSON.stringify({
            lines: Array(5).fill([["text", "rawdata"]]),
            description: "Raw",
        }),
        "",
        JSON.stringify({
            lines: Array(5).fill([["text", "rawdata"]]),
            description: "Raw",
        })
    );

    const tflow = TFlow();
    tflow.request.method = "POST";
    const {asFragment} = render(<HttpMessage flow={tflow} message={tflow.request}/>);
    await waitFor(() => screen.getAllByText("data"));
    expect(screen.queryByText('additional')).toBeNull();

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

    fireEvent.click(screen.getByText("Edit"));
    fireEvent.click(screen.getByText("Done"));
    await waitFor(() => screen.getAllByText("rawdata"));
    expect(asFragment()).toMatchSnapshot();
});

test("HttpMessage edit query string", async () => {
    const lines = [
        [
            ["header", "foo"],
            ["text", "1"],
        ],
        [
            ["header", "bar"],
            ["text", "2"],
        ],
    ];

    fetchMock.mockResponses(
        JSON.stringify({
            lines: lines,
            description: "Query",
        }),
        "foo=1\nbar=2",
        '',
        JSON.stringify({
            lines,
            description: "Query",
        })
    );

    const tflow = TFlow();
    tflow.request.path = "/path?foo=1&bar=2";
    const { asFragment, debug } = render(
        <HttpMessage flow={tflow} message={tflow.request} />
    );
    fireEvent.click(screen.getByText("Edit"));
    await waitFor(() => screen.getAllByText(/foo/));
    expect(asFragment()).toMatchSnapshot();
    fireEvent.click(screen.getByText("Done"));

    await waitFor(() => screen.getAllByText("foo"));
    expect(asFragment()).toMatchSnapshot();
});

test("ViewImage", async () => {
    const flow = TFlow();
    const {asFragment} = render(<ViewImage flow={flow} message={flow.request}/>)
    expect(asFragment()).toMatchSnapshot();
});
