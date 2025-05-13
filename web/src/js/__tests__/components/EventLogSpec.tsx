import * as React from "react";
import EventLog from "../../components/EventLog";
import { fireEvent, render, screen } from "../test-utils";

test("EventLog", () => {
    const { asFragment, store } = render(<EventLog />);
    expect(asFragment()).toMatchSnapshot();

    expect(store.getState().eventLog.filters.debug).toBe(true);
    fireEvent.click(screen.getByText("debug"));
    expect(store.getState().eventLog.filters.debug).toBe(false);
});
