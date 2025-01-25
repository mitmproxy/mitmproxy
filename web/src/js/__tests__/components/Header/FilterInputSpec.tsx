import * as React from "react";
import renderer from "react-test-renderer";
import FilterInput from "../../../components/Header/FilterInput";
import FilterDocs from "../../../components/Header/FilterDocs";
import { act, render } from "../../test-utils";

describe("FilterInput Component", () => {
    it("should render correctly", () => {
        const filterInput = renderer.create(
            <FilterInput
                type="foo"
                color="red"
                placeholder="bar"
                onChange={() => undefined}
                value="42"
            />,
        );
        const tree = filterInput.toJSON();
        expect(tree).toMatchSnapshot();
    });

    function dummyInput(): FilterInput {
        const ref = React.createRef<FilterInput>();
        render(
            <FilterInput
                type="foo"
                color="red"
                placeholder="bar"
                value="wat"
                onChange={jest.fn()}
                ref={ref}
            />,
        );
        return ref.current!;
    }

    it("should handle componentWillReceiveProps", () => {
        const { rerender, getByDisplayValue } = render(
            <FilterInput
                type="typ"
                color="red"
                value="foo"
                placeholder=""
                onChange={() => null}
            />,
        );
        rerender(
            <FilterInput
                type="typ"
                color="red"
                value="bar"
                placeholder=""
                onChange={() => null}
            />,
        );
        expect(getByDisplayValue("bar")).toBeInTheDocument();
    });

    it("should handle isValid", () => {
        const filterInput = dummyInput();
        // valid
        expect(filterInput.isValid("~u foo")).toBeTruthy();
        expect(filterInput.isValid("~foo bar")).toBeFalsy();
    });

    it("should handle getDesc", () => {
        const filterInput = dummyInput();

        act(() => filterInput.setState({ value: "" }));
        expect(filterInput.getDesc().type).toEqual(FilterDocs);

        act(() => filterInput.setState({ value: "~u foo" }));
        expect(filterInput.getDesc()).toEqual("url matches /foo/i");

        act(() => filterInput.setState({ value: "~foo bar" }));
        expect(filterInput.getDesc()).toEqual(
            'SyntaxError: Expected filter expression but "~" found.',
        );
    });

    it("should handle change", () => {
        const filterInput = dummyInput();
        const mockEvent = {
            target: { value: "~a bar" },
        } as React.ChangeEvent<HTMLInputElement>;
        act(() => filterInput.onChange(mockEvent));
        expect(filterInput.state.value).toEqual("~a bar");
        expect(filterInput.props.onChange).toBeCalledWith("~a bar");
    });

    it("should handle focus", () => {
        const filterInput = dummyInput();
        act(() => filterInput.onFocus());
        expect(filterInput.state.focus).toBeTruthy();
    });

    it("should handle blur", () => {
        const filterInput = dummyInput();
        act(() => filterInput.onBlur());
        expect(filterInput.state.focus).toBeFalsy();
    });

    it("should handle mouseEnter", () => {
        const filterInput = dummyInput();
        act(() => filterInput.onMouseEnter());
        expect(filterInput.state.mousefocus).toBeTruthy();
    });

    it("should handle mouseLeave", () => {
        const filterInput = dummyInput();
        act(() => filterInput.onMouseLeave());
        expect(filterInput.state.mousefocus).toBeFalsy();
    });

    it("should handle keyDown", () => {
        const filterInput = dummyInput();
        const input = filterInput.inputRef.current!;
        input.blur = jest.fn();
        const mockEvent = {
            key: "Escape",
            stopPropagation: jest.fn(),
        };
        act(() => filterInput.onKeyDown(mockEvent));
        expect(input.blur).toBeCalled();
        expect(filterInput.state.mousefocus).toBeFalsy();
        expect(mockEvent.stopPropagation).toBeCalled();
    });

    it("should handle selectFilter", () => {
        const filterInput = dummyInput();
        const input = filterInput.inputRef.current!;
        input.focus = jest.fn();
        act(() => filterInput.selectFilter("bar"));
        expect(filterInput.state.value).toEqual("bar");
        expect(input.focus).toBeCalled();
    });

    it("should handle select", () => {
        const filterInput = dummyInput();
        const input = filterInput.inputRef.current!;
        input.select = jest.fn();
        act(() => filterInput.select());
        expect(input.select).toBeCalled();
    });
});
