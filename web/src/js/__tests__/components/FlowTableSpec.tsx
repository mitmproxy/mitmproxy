import * as React from "react";
import FlowTable, { PureFlowTable } from "../../components/FlowTable";

import { act, fireEvent, render } from "../test-utils";
import { FLOWS_REMOVE, select } from "../../ducks/flows";

window.addEventListener = jest.fn();

const COLUMN_WIDTHS_KEY = "mitmweb-column-widths";

// jsdom implements neither pointer capture nor layout.
beforeAll(() => {
    Element.prototype.setPointerCapture = jest.fn();
});

beforeEach(() => localStorage.clear());

const nextFrame = () =>
    act(() => new Promise((resolve) => requestAnimationFrame(resolve)));

// jsdom has no PointerEvent, so fireEvent's pointer helpers dispatch a bare Event with no clientX for the drag to measure from.
// A MouseEvent under the same type carries one.
const firePointer = (
    target: Element | Document,
    type: "pointerdown" | "pointermove" | "pointerup",
    clientX: number,
) => fireEvent(target, new MouseEvent(type, { bubbles: true, clientX }));

const colWidth = (container: HTMLElement, colName: string) =>
    (container.querySelector(`col.col-${colName}`) as HTMLElement).style.width;

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

    it("restores persisted column widths", () => {
        localStorage.setItem(
            COLUMN_WIDTHS_KEY,
            JSON.stringify({ size: 123, time: 45 }),
        );

        const { container } = render(<FlowTable />);

        expect(colWidth(container, "size")).toBe("123px");
        expect(colWidth(container, "time")).toBe("45px");
        // Only what the user dragged is pinned; the rest is left to the browser.
        expect(colWidth(container, "path")).toBe("");
    });

    it("starts from unsized columns when the persisted widths cannot be read", () => {
        localStorage.setItem(COLUMN_WIDTHS_KEY, "}{");

        const { container } = render(<FlowTable />);

        expect(colWidth(container, "size")).toBe("");
    });

    it("applies and persists the width a resize drag ends on", async () => {
        // Nothing has a width until one is faked, and the drag starts from the rendered widths.
        const offsetWidth = jest
            .spyOn(HTMLElement.prototype, "offsetWidth", "get")
            .mockReturnValue(70);
        const { container } = render(<FlowTable />);

        const handle = container.querySelector(
            "th.col-size .col-resize-handle",
        ) as HTMLElement;
        firePointer(handle, "pointerdown", 100);
        // Every other column is pinned at its rendered width the moment the drag starts.
        expect(colWidth(container, "path")).toBe("70px");

        firePointer(document, "pointermove", 160);
        await nextFrame();
        expect(colWidth(container, "size")).toBe("130px");
        // Nothing is written until the drag ends.
        expect(localStorage.getItem(COLUMN_WIDTHS_KEY)).toBeNull();

        firePointer(document, "pointermove", 180);
        act(() => {
            firePointer(document, "pointerup", 180);
        });

        expect(colWidth(container, "size")).toBe("150px");
        expect(JSON.parse(localStorage.getItem(COLUMN_WIDTHS_KEY)!)).toEqual({
            tls: 70,
            icon: 70,
            path: 70,
            method: 70,
            status: 70,
            size: 150,
            time: 70,
        });
        // With every other column pinned, the actions column is the one left to take the slack.
        expect(colWidth(container, "quickactions")).toBe("auto");
        offsetWidth.mockRestore();
    });

    it("keeps the resized column when it cannot be persisted", () => {
        const offsetWidth = jest
            .spyOn(HTMLElement.prototype, "offsetWidth", "get")
            .mockReturnValue(70);
        const setItem = jest
            .spyOn(Storage.prototype, "setItem")
            .mockImplementation(() => {
                throw new Error("quota exceeded");
            });
        const { container } = render(<FlowTable />);

        const handle = container.querySelector(
            "th.col-size .col-resize-handle",
        ) as HTMLElement;
        firePointer(handle, "pointerdown", 100);
        firePointer(document, "pointermove", 180);
        act(() => {
            firePointer(document, "pointerup", 180);
        });

        expect(colWidth(container, "size")).toBe("150px");
        setItem.mockRestore();
        offsetWidth.mockRestore();
    });
});
