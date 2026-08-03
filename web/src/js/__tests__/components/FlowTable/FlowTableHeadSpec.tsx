import * as React from "react";
import FlowTableHead from "../../../components/FlowTable/FlowTableHead";
import { Provider } from "react-redux";
import { TStore } from "../../ducks/tutils";
import { act, fireEvent, render, screen } from "@testing-library/react";

// jsdom implements neither pointer capture nor layout.
beforeAll(() => {
    Element.prototype.setPointerCapture = jest.fn();
});

const nextFrame = () =>
    act(() => new Promise((resolve) => requestAnimationFrame(resolve)));

test("FlowTableHead Component", async () => {
    const store = TStore();
    const noop = jest.fn();
    const { asFragment } = render(
        <Provider store={store}>
            <table>
                <thead>
                    <FlowTableHead onResize={noop} onResizeEnd={noop} />
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

test("FlowTableHead resize handle reports a new width and does not sort", async () => {
    const store = TStore();
    const onResize = jest.fn();
    const onResizeEnd = jest.fn();
    const { container } = render(
        <Provider store={store}>
            <table>
                <thead>
                    <FlowTableHead
                        onResize={onResize}
                        onResizeEnd={onResizeEnd}
                    />
                </thead>
            </table>
        </Provider>,
    );

    const handle = container.querySelector(
        ".col-size .col-resize-handle",
    ) as HTMLElement;
    expect(handle).not.toBeNull();

    fireEvent.pointerDown(handle, { clientX: 100 });

    // Every column but quickactions is pinned before the drag starts.
    expect(onResize).toHaveBeenCalledTimes(1);
    expect(Object.keys(onResize.mock.calls[0][0])).toEqual(
        store.getState().options.web_columns,
    );

    fireEvent.pointerMove(document, { clientX: 160 });
    fireEvent.pointerMove(document, { clientX: 170 });
    // Moves are coalesced into a single update per frame. The exact px is not
    // asserted because jsdom does not lay out.
    expect(onResize).toHaveBeenCalledTimes(1);
    await nextFrame();
    expect(onResize).toHaveBeenCalledTimes(2);
    expect(Object.keys(onResize.mock.calls[1][0])).toEqual(["size"]);

    // Dragging the handle must not have changed the sort column.
    expect(store.getState().flows.sort.column).toBe("path");

    expect(document.body.classList).toContain("resizing-columns");
    expect(onResizeEnd).not.toHaveBeenCalled();
    fireEvent.pointerUp(document);
    expect(onResizeEnd).toHaveBeenCalledTimes(1);
    expect(document.body.classList).not.toContain("resizing-columns");
});
