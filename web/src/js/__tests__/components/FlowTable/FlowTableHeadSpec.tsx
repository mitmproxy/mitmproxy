import * as React from "react";
import FlowTableHead from "../../../components/FlowTable/FlowTableHead";
import { Provider } from "react-redux";
import { TStore } from "../../ducks/tutils";
import { fireEvent, render, screen } from "@testing-library/react";

test("FlowTableHead Component", async () => {
    const store = TStore();
    const { asFragment } = render(
        <Provider store={store}>
            <table>
                <thead>
                    <FlowTableHead />
                </thead>
            </table>
        </Provider>,
    );
    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Size"));
    expect(store.getState().flows.sort).toEqual({
        column: "size",
        desc: false,
    });
    fireEvent.click(screen.getByText("Size"));
    expect(store.getState().flows.sort).toEqual({ column: "size", desc: true });
});
