import * as React from "react";
import Splitter from "../../../components/common/Splitter";
import { act, render } from "../../test-utils";

describe.each([["x"], ["y"]])("Splitter Component (%s axis)", (axis) => {
    const isX = axis === "x";
    // jsdom reports every element as 0x0, so fake a size for the two panels the
    // splitter sits between. Both start at 200px, giving a 400px total.
    let sizeSpy: jest.SpyInstance;
    beforeEach(() => {
        sizeSpy = jest
            .spyOn(
                HTMLElement.prototype,
                isX ? "offsetWidth" : "offsetHeight",
                "get",
            )
            .mockReturnValue(200);
    });
    afterEach(() => {
        sizeSpy.mockRestore();
        document.body.className = "";
    });

    it("should render correctly", () => {
        const ref = React.createRef<Splitter>();
        const { asFragment, container, unmount } = render(
            <>
                <div></div>
                <Splitter axis={axis} ref={ref} />
                <div></div>
            </>,
        );
        const splitter = ref.current!;
        const prev = container.firstChild as HTMLElement;

        expect(asFragment()).toMatchSnapshot();

        act(() => {
            splitter.onPointerDown({
                target: {
                    setPointerCapture: () => 0,
                } as unknown,
                pageX: 100,
                pageY: 100,
                pointerId: 42,
            } as React.PointerEvent<HTMLDivElement>);
        });
        expect(splitter.state.dragPointer).toBe(42);
        // The drag adds a body class so the resize cursor shows everywhere.
        expect(document.body.classList.contains("splitter-resizing")).toBe(
            true,
        );

        // The previous panel follows the pointer: starting at 200px, a +50
        // move sizes it to 250px.
        act(() => {
            splitter.onPointerMove({
                pageX: 150,
                pageY: 150,
                pointerId: 42,
            } as React.PointerEvent<HTMLDivElement>);
        });
        expect(prev.style.flex).toBe("0 0 250px");

        // Capture can be lost at coordinates that aren't meaningful (e.g.
        // pointercancel). The size must stay where the last move left it rather
        // than jump to these coordinates.
        act(() => {
            splitter.onLostPointerCapture({
                pageX: 999,
                pageY: 999,
                pointerId: 42,
            } as React.PointerEvent<HTMLDivElement>);
        });
        expect(prev.style.flex).toBe("0 0 250px");
        expect(splitter.state.dragPointer).toBe(0.1);
        expect(document.body.classList.contains("splitter-resizing")).toBe(
            false,
        );
        expect(asFragment()).toMatchSnapshot();

        unmount();
    });

    it("clamps the drag to the shared space", () => {
        const ref = React.createRef<Splitter>();
        const { container, unmount } = render(
            <>
                <div></div>
                <Splitter axis={axis} ref={ref} />
                <div></div>
            </>,
        );
        const splitter = ref.current!;
        const prev = container.firstChild as HTMLElement;

        act(() => {
            splitter.onPointerDown({
                target: { setPointerCapture: () => 0 } as unknown,
                pageX: 0,
                pageY: 0,
                pointerId: 7,
            } as React.PointerEvent<HTMLDivElement>);
        });

        // Drag far past the next panel; prev is capped at the 400px total.
        act(() => {
            splitter.onPointerMove({
                pageX: 10000,
                pageY: 10000,
                pointerId: 7,
            } as React.PointerEvent<HTMLDivElement>);
        });
        expect(prev.style.flex).toBe("0 0 400px");

        // Drag far the other way; prev collapses to 0.
        act(() => {
            splitter.onPointerMove({
                pageX: -10000,
                pageY: -10000,
                pointerId: 7,
            } as React.PointerEvent<HTMLDivElement>);
        });
        expect(prev.style.flex).toBe("0 0 0px");

        unmount();
    });
});
