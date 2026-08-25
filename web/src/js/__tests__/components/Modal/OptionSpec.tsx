import * as React from "react";
import { ChoicesOption, Options } from "../../../components/Modal/OptionInput";
import { fireEvent, render, screen } from "../../test-utils";

describe("BooleanOption Component", () => {
    const BooleanOption = Options["bool"];

    it("should handle onChange", () => {
        const onChangeFn = jest.fn();
        render(<BooleanOption value={true} onChange={onChangeFn} />);
        fireEvent.click(screen.getByText("Enable"));
        expect(onChangeFn).toBeCalled();
    });
});

describe("StringOption Component", () => {
    const StringOption = Options["str"];

    it("should render", async () => {
        render(<StringOption value="foo" onChange={() => 0} />);
    });
});

describe("NumberOption Component", () => {
    const NumberOption = Options["int"];
    const onChangeFn = jest.fn();
    const { asFragment } = render(
        <NumberOption value={1} onChange={onChangeFn} />,
    );

    it("should render correctly", () => {
        expect(asFragment()).toMatchSnapshot();
    });
});

describe("ChoiceOption Component", () => {
    const onChangeFn = jest.fn();
    const { asFragment } = render(
        <ChoicesOption
            value="a"
            choices={["a", "b", "c"]}
            onChange={onChangeFn}
        />,
    );

    it("should render correctly", () => {
        expect(asFragment()).toMatchSnapshot();
    });
});

describe("StringOption Component", () => {
    const onChangeFn = jest.fn();
    const StringSequenceOption = Options["sequence of str"];
    const { asFragment } = render(
        <StringSequenceOption value={["a", "b"]} onChange={onChangeFn} />,
    );

    it("should render correctly", () => {
        expect(asFragment()).toMatchSnapshot();
    });
});
