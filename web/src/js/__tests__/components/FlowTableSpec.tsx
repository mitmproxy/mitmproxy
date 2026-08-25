import * as React from "react";
import FlowTable, { PureFlowTable } from "../../components/FlowTable";

import { act, render } from "../test-utils";
import { FLOWS_REMOVE, select } from "../../ducks/flows";

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

        act(() => store.dispatch(select([store.getState().flows.view[3]])));
        expect(asFragment()).toMatchSnapshot();
    });

    it("does not call onViewportUpdate when flowView and rowHeight are unchanged", () => {
        // Regression guard for an infinite componentDidUpdate -> setState
        // cycle. Before the FlowTableProps-comparison gate in
        // componentDidUpdate, onViewportUpdate was called on EVERY update —
        // including the setState the previous call itself produced — so
        // setState could feed itself indefinitely when state.viewportTop
        // and viewport.scrollTop never converged.
        const spy = jest.spyOn(PureFlowTable.prototype, "onViewportUpdate");
        const { store } = render(<FlowTable />);
        spy.mockClear(); // ignore the componentDidMount call

        // A `select` dispatch changes connect-mapped props that reach
        // FlowTable (onlySelectedId, firstSelectedIndex) and triggers
        // componentDidUpdate, but does NOT change flowView or rowHeight —
        // so onViewportUpdate must not run.
        act(() => store.dispatch(select([store.getState().flows.view[0]])));
        expect(spy).not.toHaveBeenCalled();

        spy.mockRestore();
    });

    it("calls onViewportUpdate when flowView changes", () => {
        // Complement of the previous test: removing a flow changes
        // `state.flows.view`, so the connect-mapped `flowView` prop differs
        // from `prevProps.flowView` on the resulting componentDidUpdate.
        // The gate must let onViewportUpdate run in this branch — otherwise
        // adding/removing flows would not refresh the virtual-scroll window.
        const spy = jest.spyOn(PureFlowTable.prototype, "onViewportUpdate");
        const { store } = render(<FlowTable />);
        spy.mockClear();

        const firstFlowId = store.getState().flows.view[0].id;
        act(() => store.dispatch(FLOWS_REMOVE(firstFlowId)));
        expect(spy).toHaveBeenCalled();

        spy.mockRestore();
    });
});
