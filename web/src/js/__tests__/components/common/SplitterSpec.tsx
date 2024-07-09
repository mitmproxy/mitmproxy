import * as React from "react";
import renderer from "react-test-renderer";
import Splitter from "../../../components/common/Splitter";
import TestUtils from "react-dom/test-utils";

describe.each([
    ["", ""],
    ["x", "X"],
    ["y", "Y"],
])("Splitter Component", (axisLower, axisUpper) => {
    if (axisLower === "") {
        it("should render correctly with default (x) axis", () => {
            const splitter = renderer.create(<Splitter />);
            const tree = splitter.toJSON();
            expect(tree).toMatchInlineSnapshot(`
<div
  className="splitter splitter-x"
>
  <div
    onLostPointerCapture={[Function]}
    onPointerDown={[Function]}
    onPointerMove={[Function]}
  />
</div>
`);
        });
        return;
    }

    it("should render correctly with specified axis", () => {
        const splitter = renderer.create(<Splitter axis={axisLower} />);
        const tree = splitter.toJSON();
        expect(tree).toMatchInlineSnapshot(`
<div
  className="splitter splitter-${axisLower}"
>
  <div
    onLostPointerCapture={[Function]}
    onPointerDown={[Function]}
    onPointerMove={[Function]}
  />
</div>
`);
    });

    const splitter = TestUtils.renderIntoDocument(
        <Splitter axis={axisLower} />,
    );
    const dom = splitter.node.current;
    const previousElementSibling = document.createElement("div");
    const nextElementSibling = document.createElement("div");

    Object.defineProperties(previousElementSibling, {
        offsetWidth: { value: 300 },
        offsetHeight: { value: 500 },
    });
    previousElementSibling.style.flex = "";
    nextElementSibling.style.flex = "";

    Object.defineProperties(dom, {
        previousElementSibling: { value: previousElementSibling },
        nextElementSibling: { value: nextElementSibling },
    });
    dom.firstElementChild.setPointerCapture = jest.fn();

    it("should handle pointerdown", () => {
        const e = {
            pageX: 13,
            pageY: 22,
            pointerId: -4618,
            target: dom.firstElementChild,
        };
        expect(splitter.state.dragPointer).toEqual(0.1);
        splitter.onPointerDown(e);
        expect(e.target.setPointerCapture).toBeCalledWith(-4618);
        expect(splitter.state.dragPointer).toEqual(-4618);
        expect(splitter.state.startPos).toEqual(e[`page${axisUpper}`]);
    });

    it("should handle pointermove", () => {
        const e = {
            pageX: 62,
            pageY: 21,
            pointerId: -4618,
            target: dom.firstElementChild,
        };
        splitter.onPointerMove(e);
        expect(dom.style.transform).toEqual(
            axisLower === "x"
                ? `translateX(${62 - 13}px)`
                : `translateY(${21 - 22}px)`,
        );
    });

    it("should handle lostpointercapture", () => {
        const e = {
            pageX: 56,
            pageY: 82,
            pointerId: -4618,
            target: dom.firstElementChild,
        };
        splitter.onLostPointerCapture(e);
        expect(splitter.state.dragPointer).toEqual(0.1);
        expect(dom.style.transform).toEqual("");
        expect(previousElementSibling.style.flex).toEqual(
            `0 0 ${axisLower === "x" ? 300 + 56 - 13 : 500 + 82 - 22}px`,
        );
        expect(nextElementSibling.style.flex).toEqual("1 1 auto");
    });

    it("should not resize previousElementSibling negative", () => {
        const e = {
            pageX: 56,
            pageY: 82,
            pointerId: 47,
            target: dom.firstElementChild,
        };
        splitter.onPointerDown(e);
        e[`page${axisUpper}`] = -1234;
        splitter.onLostPointerCapture(e);
        expect(previousElementSibling.style.flex).toEqual("0 0 0px");
    });

    it("should ignore other pointers", () => {
        splitter.onPointerDown({
            pageX: 70,
            pageY: 60,
            pointerId: 47,
            target: dom.firstElementChild,
        });
        splitter.onPointerDown({
            pageX: 70,
            pageY: 60,
            pointerId: 46,
            target: dom.firstElementChild,
        });
        expect(splitter.state.dragPointer).toEqual(47);
        splitter.onPointerMove({ pageX: 75, pageY: 55, pointerId: 46 });
        expect(dom.style.transform).toEqual("");
        splitter.onPointerMove({
            pageX: 74,
            pageY: 54,
            pointerId: 47,
            target: dom.firstElementChild,
        });
        splitter.onLostPointerCapture({ pageX: 76, pageY: 56, pointerId: 46 });
        expect(dom.style.transform).toEqual(
            axisLower === "x"
                ? `translateX(${74 - 70}px)`
                : `translateY(${54 - 60}px)`,
        );
    });

    it("should handle resize", () => {
        const x = jest.spyOn(window, "setTimeout");
        splitter.onResize();
        expect(x).toHaveBeenCalled();
    });

    it("should handle componentWillUnmount", () => {
        splitter.componentWillUnmount();
        expect(previousElementSibling.style.flex).toEqual("");
        expect(nextElementSibling.style.flex).toEqual("");
        expect(splitter.state.applied).toBeTruthy();
    });

    it("should handle reset", () => {
        splitter.reset(false);
        expect(splitter.state.applied).toBeFalsy();
        expect(splitter.reset(true)).toEqual(undefined);
    });
});
