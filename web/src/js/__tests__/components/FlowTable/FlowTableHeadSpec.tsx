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

const stubViewportWidth = (px: number) =>
    jest.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(px);

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

    // Every column is pinned before the drag starts, bar the collapsed quickactions column.
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

    // It stays collapsed with its buttons showing on hover, so it has no label, no width to drag and no order to sort by.
    const actions = container.querySelector(".col-quickactions") as HTMLElement;
    expect(actions.textContent).toBe("");
    expect(actions.querySelector(".col-resize-handle")).toBeNull();

    fireEvent.click(actions);
    expect(store.getState().flows.sort.column).toBe("path");
});
test("FlowTableHead does not sort on a click that lands on a resize handle", () => {
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

    const handle = container.querySelector(
        ".col-size .col-resize-handle",
    ) as HTMLElement;
    fireEvent.click(handle);

    expect(store.getState().flows.sort.column).toBe("path");
});

test("FlowTableHead does not resize a column the pointer never dragged", () => {
    const offsetWidth = stubColumnWidth(10);
    const store = TStore();
    const onResizeEnd = jest.fn();
    const { container } = render(
        <Provider store={store}>
            <table>
                <thead>
                    <FlowTableHead
                        onResize={jest.fn()}
                        onResizeEnd={onResizeEnd}
                    />
                </thead>
            </table>
        </Provider>,
    );

    const handle = container.querySelector(
        ".col-tls .col-resize-handle",
    ) as HTMLElement;
    firePointer(handle, "pointerdown", 40);
    firePointer(document, "pointerup", 40);

    expect(onResizeEnd).toHaveBeenCalledWith({});
    offsetWidth.mockRestore();
});

test("FlowTableHead reports the width a drag returning to its origin ended on", async () => {
    const offsetWidth = stubColumnWidth(70);
    const store = TStore();
    const onResizeEnd = jest.fn();
    const { container } = render(
        <Provider store={store}>
            <table>
                <thead>
                    <FlowTableHead
                        onResize={jest.fn()}
                        onResizeEnd={onResizeEnd}
                    />
                </thead>
            </table>
        </Provider>,
    );

    const handle = container.querySelector(
        ".col-size .col-resize-handle",
    ) as HTMLElement;
    firePointer(handle, "pointerdown", 100);
    firePointer(document, "pointermove", 160);
    await nextFrame();
    // Back to the pixel it started from, which is a drag that happened, not a click.
    firePointer(document, "pointermove", 100);
    firePointer(document, "pointerup", 100);

    expect(onResizeEnd).toHaveBeenCalledWith({ size: 70 });
    offsetWidth.mockRestore();
});

test("FlowTableHead keeps a column narrower than the minimum at its own width", async () => {
    // The TLS column ships at 10px, below the 20px a drag is otherwise floored at.
    const offsetWidth = stubColumnWidth(10);
    const store = TStore();
    const onResize = jest.fn();
    const { container } = render(
        <Provider store={store}>
            <table>
                <thead>
                    <FlowTableHead
                        onResize={onResize}
                        onResizeEnd={jest.fn()}
                    />
                </thead>
            </table>
        </Provider>,
    );

    const handle = container.querySelector(
        ".col-tls .col-resize-handle",
    ) as HTMLElement;
    firePointer(handle, "pointerdown", 40);
    firePointer(document, "pointermove", 20);
    await nextFrame();

    expect(onResize).toHaveBeenLastCalledWith({ tls: 10 });
    // The drag is still live otherwise, and its document listeners would outlive the test.
    firePointer(document, "pointerup", 20);
    offsetWidth.mockRestore();
});

test("FlowTableHead stops a column at the width of the visible table", async () => {
    const offsetWidth = stubColumnWidth(70);
    const clientWidth = stubViewportWidth(300);
    const store = TStore();
    const onResize = jest.fn();
    const onResizeEnd = jest.fn();
    const { container } = render(
        <Provider store={store}>
            <div className="flow-table">
                <table>
                    <thead>
                        <FlowTableHead
                            onResize={onResize}
                            onResizeEnd={onResizeEnd}
                        />
                    </thead>
                </table>
            </div>
        </Provider>,
    );

    const handle = container.querySelector(
        ".col-size .col-resize-handle",
    ) as HTMLElement;
    firePointer(handle, "pointerdown", 100);
    firePointer(document, "pointermove", 2000);
    await nextFrame();

    expect(onResize).toHaveBeenLastCalledWith({ size: 300 });

    firePointer(document, "pointerup", 2000);
    expect(onResizeEnd).toHaveBeenCalledWith({ size: 300 });
    clientWidth.mockRestore();
    offsetWidth.mockRestore();
});

// jsdom lays nothing out, so an element only has the natural width it is given here.
// The fit reads it while the element is unconstrained, so the stub hands it out only then.
const stubNaturalWidth = (el: Element, px: number) =>
    jest.spyOn(el, "getBoundingClientRect").mockImplementation(
        () =>
            ({
                width: (el as HTMLElement).style.display === "block" ? px : 999,
            }) as DOMRect,
    );

test("FlowTableHead double-click fits a column to its widest visible cell", () => {
    const offsetWidth = stubColumnWidth(70);
    const store = TStore();
    const onResizeEnd = jest.fn();
    const { container } = render(
        <Provider store={store}>
            <table>
                <thead>
                    <FlowTableHead
                        onResize={jest.fn()}
                        onResizeEnd={onResizeEnd}
                    />
                </thead>
                <tbody>
                    <tr>
                        <td className="col-size">1kb</td>
                    </tr>
                    <tr>
                        <td className="col-size">123.4kb</td>
                    </tr>
                </tbody>
            </table>
        </Provider>,
    );

    const cells = container.querySelectorAll("tbody td.col-size");
    stubNaturalWidth(cells[0], 40);
    stubNaturalWidth(cells[1], 89.5);
    stubNaturalWidth(container.querySelector(".col-size .th-content")!, 30);

    const handle = container.querySelector(
        ".col-size .col-resize-handle",
    ) as HTMLElement;
    fireEvent.doubleClick(handle);

    // The widest of the two visible cells wins, rounded up so it isn't clipped - and the double-click must not sort the column either.
    expect(onResizeEnd).toHaveBeenCalledWith(
        expect.objectContaining({ size: 90 }),
    );
    expect(store.getState().flows.sort.column).toBe("path");
    // The cells go back to the table layout once measured.
    expect(cells[1].getAttribute("style")).toBeFalsy();
    offsetWidth.mockRestore();
});

test("FlowTableHead double-click shrinks a column wider than its content, and again leaves it be", () => {
    const offsetWidth = stubColumnWidth(200);
    const store = TStore();
    const onResizeEnd = jest.fn();
    const { container } = render(
        <Provider store={store}>
            <table>
                <thead>
                    <FlowTableHead
                        onResize={jest.fn()}
                        onResizeEnd={onResizeEnd}
                    />
                </thead>
                <tbody>
                    <tr>
                        <td className="col-size">1kb</td>
                    </tr>
                </tbody>
            </table>
        </Provider>,
    );

    // A cell fills its column, so its rendered width says nothing about its content.
    const cell = container.querySelector("tbody td.col-size")!;
    Object.defineProperty(cell, "scrollWidth", { value: 200 });
    stubNaturalWidth(cell, 40);

    const handle = container.querySelector(
        ".col-size .col-resize-handle",
    ) as HTMLElement;
    fireEvent.doubleClick(handle);
    fireEvent.doubleClick(handle);

    expect(onResizeEnd).toHaveBeenNthCalledWith(
        1,
        expect.objectContaining({ size: 40 }),
    );
    expect(onResizeEnd).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({ size: 40 }),
    );
    offsetWidth.mockRestore();
});

test("FlowTableHead double-click leaves a sorted column room for its sort indicator", () => {
    const offsetWidth = stubColumnWidth(200);
    const store = TStore();
    const onResizeEnd = jest.fn();
    const { container } = render(
        <Provider store={store}>
            <table>
                <thead>
                    <FlowTableHead
                        onResize={jest.fn()}
                        onResizeEnd={onResizeEnd}
                    />
                </thead>
            </table>
        </Provider>,
    );

    const th = container.querySelector("th.col-size") as HTMLElement;
    th.style.paddingRight = "18px";
    stubNaturalWidth(th.querySelector(".th-content")!, 40);

    fireEvent.doubleClick(th.querySelector(".col-resize-handle")!);

    expect(onResizeEnd).toHaveBeenCalledWith(
        expect.objectContaining({ size: 58 }),
    );
    offsetWidth.mockRestore();
});

test("FlowTableHead double-click does nothing when no rows are rendered to measure", () => {
    const offsetWidth = stubColumnWidth(70);
    const store = TStore();
    const onResizeEnd = jest.fn();
    const { container } = render(
        <Provider store={store}>
            <table>
                <thead>
                    <FlowTableHead
                        onResize={jest.fn()}
                        onResizeEnd={onResizeEnd}
                    />
                </thead>
                <tbody />
            </table>
        </Provider>,
    );

    const handle = container.querySelector(
        ".col-size .col-resize-handle",
    ) as HTMLElement;
    fireEvent.doubleClick(handle);

    expect(onResizeEnd).not.toHaveBeenCalled();
    offsetWidth.mockRestore();
});

test("FlowTableHead lets a column wider than the visible table only shrink", async () => {
    const offsetWidth = stubColumnWidth(500);
    const clientWidth = stubViewportWidth(300);
    const store = TStore();
    const onResize = jest.fn();
    const { container } = render(
        <Provider store={store}>
            <div className="flow-table">
                <table>
                    <thead>
                        <FlowTableHead
                            onResize={onResize}
                            onResizeEnd={jest.fn()}
                        />
                    </thead>
                </table>
            </div>
        </Provider>,
    );

    const handle = container.querySelector(
        ".col-size .col-resize-handle",
    ) as HTMLElement;
    firePointer(handle, "pointerdown", 100);
    // A width restored from a wider window is not snapped down to the ceiling, but must not grow past it either.
    firePointer(document, "pointermove", 200);
    await nextFrame();
    expect(onResize).toHaveBeenLastCalledWith({ size: 500 });

    firePointer(document, "pointermove", 40);
    await nextFrame();
    expect(onResize).toHaveBeenLastCalledWith({ size: 440 });

    firePointer(document, "pointerup", 40);
    clientWidth.mockRestore();
    offsetWidth.mockRestore();
});
