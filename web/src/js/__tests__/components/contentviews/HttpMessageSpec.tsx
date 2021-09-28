import {TFlow} from "../../ducks/tutils";
import * as React from 'react';
import HttpMessage, {ViewImage} from '../../../components/contentviews/HttpMessage'
import {fireEvent, render, screen, waitFor} from "../../test-utils"
import fetchMock, {enableFetchMocks} from "jest-fetch-mock";
import {SHOW_MAX_LINES} from "../../../components/contentviews/useContent";

jest.mock("../../../contrib/CodeMirror")

enableFetchMocks();

test("HttpMessage", async () => {
    const lines = Array(SHOW_MAX_LINES).fill([["text", "data"]]).concat(
        Array(SHOW_MAX_LINES).fill([["text", "additional"]])
    );

    fetchMock.mockResponses(
        JSON.stringify({
            lines: lines.slice(0, SHOW_MAX_LINES + 1),
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
        })
    );

    const tflow = TFlow();
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
});

test("ViewImage", async () => {
    const flow = TFlow();
    const {asFragment} = render(<ViewImage flow={flow} message={flow.request}/>)
    expect(asFragment()).toMatchSnapshot();
});
