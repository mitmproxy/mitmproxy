import * as React from "react";
import renderer from "react-test-renderer";
import FilterInput from "../../../components/Header/FilterInput";
import FilterDocs from "../../../components/Header/FilterDocs";
import { render } from "../../test-utils";

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
        render(<FilterInput
            type="foo"
            color="red"
            placeholder="bar"
            value="wat"
            onChange={jest.fn()}
            ref={ref}
        />);
        return ref.current!;
    }

    it("should handle componentWillReceiveProps", () => {
        const filterInput = dummyInput();
        filterInput.UNSAFE_componentWillReceiveProps({ value: "foo" });
        expect(filterInput.state.value).toEqual("foo");
    });

    it("should handle isValid", () => {
        const filterInput = dummyInput();
        // valid
        expect(filterInput.isValid("~u foo")).toBeTruthy();
        expect(filterInput.isValid("~foo bar")).toBeFalsy();
    });

    it("should handle getDesc", () => {
        const filterInput = dummyInput();
        
        filterInput.setState({value: ""});
        expect(filterInput.getDesc().type).toEqual(FilterDocs);

        filterInput.setState({value: "~u foo"});
        expect(filterInput.getDesc()).toEqual("url matches /foo/i");

        filterInput.setState({value: "~foo bar"});
        expect(filterInput.getDesc()).toEqual(
            'SyntaxError: Expected filter expression but "~" found.',
        );
    });

    it("should handle change", () => {
        const filterInput = dummyInput();
        const mockEvent = { target: { value: "~a bar" } };
        filterInput.onChange(mockEvent);
        expect(filterInput.state.value).toEqual("~a bar");
        expect(filterInput.props.onChange).toBeCalledWith("~a bar");
    });

    it("should handle focus", () => {
        const filterInput = dummyInput();
        filterInput.onFocus();
        expect(filterInput.state.focus).toBeTruthy();
    });

    it("should handle blur", () => {
        const filterInput = dummyInput();
        filterInput.onBlur();
        expect(filterInput.state.focus).toBeFalsy();
    });

    it("should handle mouseEnter", () => {
        const filterInput = dummyInput();
        filterInput.onMouseEnter();
        expect(filterInput.state.mousefocus).toBeTruthy();
    });

    it("should handle mouseLeave", () => {
        const filterInput = dummyInput();
        filterInput.onMouseLeave();
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
        filterInput.onKeyDown(mockEvent);
        expect(input.blur).toBeCalled();
        expect(filterInput.state.mousefocus).toBeFalsy();
        expect(mockEvent.stopPropagation).toBeCalled();
    });

    it("should handle selectFilter", () => {
        const filterInput = dummyInput();
        const input = filterInput.inputRef.current!;
        input.focus = jest.fn();
        filterInput.selectFilter("bar");
        expect(filterInput.state.value).toEqual("bar");
        expect(input.focus).toBeCalled();
    });

    it("should handle select", () => {
        const filterInput = dummyInput();
        const input = filterInput.inputRef.current!;
        input.select = jest.fn();
        filterInput.select();
        expect(input.select).toBeCalled();
    });
});
