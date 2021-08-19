import * as React from "react"
import {render, screen, waitFor} from "../test-utils";
import FlowView from "../../components/FlowView";
import fetchMock, {enableFetchMocks} from "jest-fetch-mock";
import {fireEvent} from "@testing-library/react";

enableFetchMocks();

test("FlowView", async () => {
    fetchMock.mockReject(new Error("backend missing"));

    const {asFragment} = render(<FlowView/>);
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
});
