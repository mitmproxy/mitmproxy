import * as React from "react";
import renderer, { act } from "react-test-renderer";
import { ChoicesOption, Options } from "../../../components/Modal/Option";

describe("BooleanOption Component", () => {
    const BooleanOption = Options["bool"],
        onChangeFn = jest.fn(),
        booleanOption = renderer.create(
            <BooleanOption value={true} onChange={onChangeFn} />,
        ),
        tree = booleanOption.toJSON();

    it("should render correctly", () => {
        expect(tree).toMatchSnapshot();
    });

    it("should handle onChange", () => {
        const input = tree.children[0].children[0],
            mockEvent = { target: { checked: true } };
        input.props.onChange(mockEvent);
        expect(onChangeFn).toBeCalledWith(mockEvent.target.checked);
    });
});

describe("StringOption Component", () => {
    const StringOption = Options["str"],
        onChangeFn = jest.fn(),
        stringOption = renderer.create(
            <StringOption value="foo" onChange={onChangeFn} />,
        ),
        tree = stringOption.toJSON();

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
    const NumberOption = Options["int"],
        onChangeFn = jest.fn(),
        numberOption = renderer.create(
            <NumberOption value={1} onChange={onChangeFn} />,
        ),
        tree = numberOption.toJSON();

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
    const onChangeFn = jest.fn(),
        choiceOption = renderer.create(
            <ChoicesOption
                value="a"
                choices={["a", "b", "c"]}
                onChange={onChangeFn}
            />,
        ),
        tree = choiceOption.toJSON();

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
    const onChangeFn = jest.fn(),
        StringSequenceOption = Options["sequence of str"],
        stringSequenceOption = renderer.create(
            <StringSequenceOption value={["a", "b"]} onChange={onChangeFn} />,
        ),
        tree = stringSequenceOption.toJSON();

    it("should render correctly", () => {
        expect(tree).toMatchSnapshot();
    });

    it("should handle onChange", () => {
        const mockEvent = { target: { value: "a\nb\nc\n" } };
        act(() => tree.props.onChange(mockEvent));
        expect(onChangeFn).toBeCalledWith(["a", "b", "c"]);
    });
});
