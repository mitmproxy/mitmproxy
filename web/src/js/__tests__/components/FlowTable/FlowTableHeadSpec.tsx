import * as React from "react";
import FlowTableHead from "../../../components/FlowTable/FlowTableHead";
import { Provider } from "react-redux";
import { TStore } from "../../ducks/tutils";
import { fireEvent, render, screen } from "@testing-library/react";

test("FlowTableHead Component", async () => {
    const store = TStore();
    const onResize = jest.fn();
    const { asFragment } = render(
        <Provider store={store}>
            <table>
                <thead>
                    <FlowTableHead columnWidths={{}} onResize={onResize} />
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
    fireEvent.click(screen.getByText("Size"));
    expect(store.getState().flows.sort).toEqual({
        column: undefined,
        desc: false,
    });
});

test("FlowTableHead resize handle reports a new width and does not sort", () => {
    const store = TStore();
    const onResize = jest.fn();
    const { container } = render(
        <Provider store={store}>
            <table>
                <thead>
                    <FlowTableHead columnWidths={{}} onResize={onResize} />
                </thead>
            </table>
        </Provider>,
    );

    const handle = container.querySelector(
        ".col-size .col-resize-handle",
    ) as HTMLElement;
    expect(handle).not.toBeNull();

    fireEvent.pointerDown(handle, { clientX: 100 });
    fireEvent.pointerMove(document, { clientX: 160 });
    // The move reports a new width for the size column (exact px is not
    // asserted because jsdom does not lay out / populate clientX reliably).
    expect(onResize).toHaveBeenCalled();
    expect(onResize.mock.calls.at(-1)?.[0]).toBe("size");

    // Dragging the handle must not have changed the sort column.
    expect(store.getState().flows.sort.column).toBe("path");

    fireEvent.pointerUp(document);
});
