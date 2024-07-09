import * as React from "react";
import FlowTable, { PureFlowTable } from "../../components/FlowTable";

import { act, render } from "../test-utils";
import { select } from "../../ducks/flows";

window.addEventListener = jest.fn();

describe("FlowTable Component", () => {
    it("should render correctly", () => {
        const { asFragment } = render(<FlowTable />);
        expect(asFragment()).toMatchSnapshot();
    });

    it("should scroll current selection into view", () => {
        const height = PureFlowTable.defaultProps.rowHeight;
        const { asFragment, store } = render(
            <div style={{ height, overflow: "hidden" }}>
                <FlowTable />
            </div>,
        );
        expect(asFragment()).toMatchSnapshot();

        act(() => store.dispatch(select(store.getState().flows.view[3].id)));
        expect(asFragment()).toMatchSnapshot();
    });
});
