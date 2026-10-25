import * as React from "react";
import { act, fireEvent, render, screen } from "../test-utils";
import FlowView, { splitTabsForFlow } from "../../components/FlowView";
import * as flowActions from "../../ducks/flows";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";
import { TFlow, TStore, testState } from "../ducks/tutils";

enableFetchMocks();

test("FlowView", async () => {
    fetchMock.mockReject(new Error("backend missing"));

    const { asFragment, getByTestId, store } = render(<FlowView />, {
        store: TStore({
            ...testState,
            options: { ...testState.options, web_split_flowview: true },
        }),
    });
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Response"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("WebSocket"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Connection"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Timing"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Comment"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Error"));
    expect(asFragment()).toMatchSnapshot();

    act(() =>
        store.dispatch(flowActions.select([store.getState().flows.list[2]])),
    );

    fireEvent.click(screen.getByText("Stream Data"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Error"));
    expect(asFragment()).toMatchSnapshot();

    act(() =>
        store.dispatch(flowActions.select([store.getState().flows.list[3]])),
    );

    fireEvent.click(screen.getByText("Request"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Response"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Error"));
    expect(asFragment()).toMatchSnapshot();

    act(() =>
        store.dispatch(flowActions.select([store.getState().flows.list[4]])),
    );

    fireEvent.click(screen.getByText("Datagrams"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Error"));
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(getByTestId("close-button-id"));
    expect(store.getState().flows.selected).toEqual([]);
});

test("FlowView shows HTTP flows in a single column by default", async () => {
    fetchMock.mockReject(new Error("backend missing"));
    const { container } = render(<FlowView />);

    expect(container.querySelector(".flow-detail-split")).toBeNull();
    expect(container.querySelectorAll("nav.nav-tabs")).toHaveLength(1);
    expect(screen.getByText("Request")).toBeInTheDocument();
    expect(screen.getByText("Response")).toBeInTheDocument();
    await screen.findByText(/Error getting content/);
});

test("splitTabsForFlow partitions the HTTP tabs by side", () => {
    expect(splitTabsForFlow(TFlow())).toEqual({
        request: ["request", "error", "connection", "timing", "comment"],
        response: ["response", "websocket"],
    });
});
