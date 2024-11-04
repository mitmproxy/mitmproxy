import * as React from "react";
import Splitter from "../../../components/common/Splitter";
import { act, render } from "../../test-utils";

describe.each([["x"], ["y"]])("Splitter Component", (axis) => {
    it(`should render correctly (${axis} axis)`, () => {
        const ref = React.createRef<Splitter>();
        const { asFragment, unmount } = render(
            <>
                <div></div>
                <Splitter axis={axis} ref={ref} />
                <div></div>
            </>,
        );
        const splitter = ref.current!;

        expect(asFragment()).toMatchSnapshot();

        act(() => {
            splitter.onPointerDown({
                target: {
                    setPointerCapture: () => 0,
                } as unknown,
                pageX: 100,
                pageY: 200,
                pointerId: 42,
            } as React.PointerEvent<HTMLDivElement>);
        });
        expect(splitter.state.startPos).toBe(axis === "x" ? 100 : 200);

        act(() => {
            splitter.onPointerMove({
                pageX: 300,
                pageY: 300,
                pointerId: 42,
            } as React.PointerEvent<HTMLDivElement>);
        });
        expect(splitter.node.current!.style.transform).toBeTruthy();

        act(() => {
            splitter.onLostPointerCapture({
                pageX: 400,
                pageY: 400,
                pointerId: 42,
            } as React.PointerEvent<HTMLDivElement>);
        });
        expect(asFragment()).toMatchSnapshot();

        unmount();
    });
});
