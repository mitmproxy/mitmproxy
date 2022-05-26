import * as React from "react"
import {render, screen} from "../test-utils";
import FlowView from "../../components/FlowView";
import * as flowActions from "../../ducks/flows"
import fetchMock, {enableFetchMocks} from "jest-fetch-mock";
import {fireEvent} from "@testing-library/react";

enableFetchMocks();

test("FlowView", async () => {
    fetchMock.mockReject(new Error("backend missing"));

    const {asFragment, store} = render(<FlowView/>);
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Response"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("WebSocket"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Connection"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Timing"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Error"));
    expect(asFragment()).toMatchSnapshot();

    store.dispatch(flowActions.select(store.getState().flows.list[2].id));

    fireEvent.click(screen.getByText("TCP Messages"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Error"));
    expect(asFragment()).toMatchSnapshot();

    store.dispatch(flowActions.select(store.getState().flows.list[3].id));

    fireEvent.click(screen.getByText("Request"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Response"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Error"));
    expect(asFragment()).toMatchSnapshot();
});
