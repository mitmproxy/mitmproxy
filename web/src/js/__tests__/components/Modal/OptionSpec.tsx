import * as React from "react";
import renderer, { act } from "react-test-renderer";
import { ChoicesOption, Options } from "../../../components/Modal/OptionInput";

describe("BooleanOption Component", () => {
    const BooleanOption = Options["bool"];
    const onChangeFn = jest.fn();
    const booleanOption = renderer.create(
        <BooleanOption value={true} onChange={onChangeFn} />,
    );
    const tree = booleanOption.toJSON();

    it("should render correctly", () => {
        expect(tree).toMatchSnapshot();
    });

    it("should handle onChange", () => {
        const input = tree.children[0].children[0];
        const mockEvent = { target: { checked: true } };
        input.props.onChange(mockEvent);
        expect(onChangeFn).toBeCalledWith(mockEvent.target.checked);
    });
});

describe("StringOption Component", () => {
    const StringOption = Options["str"];
    const onChangeFn = jest.fn();
    const stringOption = renderer.create(
        <StringOption value="foo" onChange={onChangeFn} />,
    );
    const tree = stringOption.toJSON();

    it("should render correctly", () => {
        expect(tree).toMatchSnapshot();
    });

    it("should handle onChange", () => {
        const mockEvent = { target: { value: "bar" } };
        tree.props.onChange(mockEvent);
        expect(onChangeFn).toBeCalledWith(mockEvent.target.value);
    });
});

describe("NumberOption Component", () => {
    const NumberOption = Options["int"];
    const onChangeFn = jest.fn();
    const numberOption = renderer.create(
        <NumberOption value={1} onChange={onChangeFn} />,
    );
    const tree = numberOption.toJSON();

    it("should render correctly", () => {
        expect(tree).toMatchSnapshot();
    });

    it("should handle onChange", () => {
        const mockEvent = { target: { value: "2" } };
        tree.props.onChange(mockEvent);
        expect(onChangeFn).toBeCalledWith(2);
    });
});

describe("ChoiceOption Component", () => {
    const onChangeFn = jest.fn();
    const choiceOption = renderer.create(
        <ChoicesOption
            value="a"
            choices={["a", "b", "c"]}
            onChange={onChangeFn}
        />,
    );
    const tree = choiceOption.toJSON();

    it("should render correctly", () => {
        expect(tree).toMatchSnapshot();
    });

    it("should handle onChange", () => {
        const mockEvent = { target: { value: "b" } };
        tree.props.onChange(mockEvent);
        expect(onChangeFn).toBeCalledWith(mockEvent.target.value);
    });
});

describe("StringOption Component", () => {
    const onChangeFn = jest.fn();
    const StringSequenceOption = Options["sequence of str"];
    const stringSequenceOption = renderer.create(
        <StringSequenceOption value={["a", "b"]} onChange={onChangeFn} />,
    );
    const tree = stringSequenceOption.toJSON();

    it("should render correctly", () => {
        expect(tree).toMatchSnapshot();
    });

    it("should handle onChange", () => {
        const mockEvent = { target: { value: "a\nb\nc\n" } };
        act(() => tree.props.onChange(mockEvent));
        expect(onChangeFn).toBeCalledWith(["a", "b", "c"]);
    });
});
