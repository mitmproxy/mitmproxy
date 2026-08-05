import * as React from "react";
import FlowListMenu from "../../../components/Header/FlowListMenu";
import { fireEvent, render, screen } from "../../test-utils";
import { TStore, testState } from "../../ducks/tutils";

const withColumnWidths = () =>
    TStore({
        ...testState,
        ui: { ...testState.ui, columnWidths: { size: 70 } },
    });

test("MainMenu", () => {
    const { asFragment } = render(<FlowListMenu />);
    expect(asFragment()).toMatchSnapshot();
});

test("MainMenu resets the flow table column widths", () => {
    const { store } = render(<FlowListMenu />, { store: withColumnWidths() });

    fireEvent.click(screen.getByText("Reset Widths"));

    expect(store.getState().ui.columnWidths).toEqual({});
});

test("MainMenu has nothing to reset until a column is resized", () => {
    render(<FlowListMenu />);

    expect(screen.getByText("Reset Widths").closest("button")).toBeDisabled();
});
