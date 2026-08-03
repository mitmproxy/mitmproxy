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

// jsdom has no PointerEvent, so fireEvent's pointer helpers dispatch a bare Event with no clientX for the drag to measure from.
// A MouseEvent under the same type carries one.
const firePointer = (
    target: Element | Document,
    type: "pointerdown" | "pointermove" | "pointerup",
    clientX: number,
) => fireEvent(target, new MouseEvent(type, { bubbles: true, clientX }));

// Nothing has a width until one is faked, and the drag starts from the rendered widths.
const stubColumnWidth = (px: number) =>
    jest.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(px);

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
    const offsetWidth = stubColumnWidth(70);
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

    firePointer(handle, "pointerdown", 100);

    // Every column is pinned before the drag starts, bar the quickactions column that takes the slack.
    expect(onResize).toHaveBeenCalledTimes(1);
    expect(Object.keys(onResize.mock.calls[0][0])).toEqual(
        store.getState().options.web_columns,
    );

    firePointer(document, "pointermove", 160);
    firePointer(document, "pointermove", 170);
    // Moves are coalesced into a single update per frame, so only the last one lands.
    expect(onResize).toHaveBeenCalledTimes(1);
    await nextFrame();
    expect(onResize).toHaveBeenLastCalledWith({ size: 140 });

    // Dragging the handle must not have changed the sort column.
    expect(store.getState().flows.sort.column).toBe("path");

    expect(document.body.classList).toContain("resizing-columns");
    expect(onResizeEnd).not.toHaveBeenCalled();
    firePointer(document, "pointermove", 180);
    firePointer(document, "pointerup", 180);
    // The width the drag ended on rides along, so nothing has to wait a frame for it.
    expect(onResizeEnd).toHaveBeenCalledWith({ size: 150 });
    expect(onResize).toHaveBeenCalledTimes(2);
    expect(document.body.classList).not.toContain("resizing-columns");
    offsetWidth.mockRestore();
});

test("FlowTableHead leaves the actions column to the browser", () => {
    const store = TStore();
    const { container } = render(
        <Provider store={store}>
            <table>
                <thead>
                    <FlowTableHead
                        onResize={jest.fn()}
                        onResizeEnd={jest.fn()}
                    />
                </thead>
            </table>
        </Provider>,
    );

    // It takes the width the other columns leave over, so it has neither a width to drag nor an order to sort by.
    const actions = container.querySelector(".col-quickactions") as HTMLElement;
    expect(actions.querySelector(".col-resize-handle")).toBeNull();

    fireEvent.click(screen.getByText("Actions"));
    expect(store.getState().flows.sort.column).toBe("path");
});
