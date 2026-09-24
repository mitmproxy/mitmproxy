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

describe("FloatOption Component", () => {
    const FloatOption = Options["float"];

    it("should render correctly", () => {
        const { asFragment } = render(
            <FloatOption value={0.42} onChange={() => 0} />,
        );
        expect(asFragment()).toMatchSnapshot();
    });

    it("should parse floats", () => {
        const onChangeFn = jest.fn();
        render(<FloatOption value={0.42} onChange={onChangeFn} />);
        const input = screen.getByRole("spinbutton");
        expect(input).toHaveAttribute("step", "any");

        fireEvent.change(input, { target: { value: "1.5" } });
        expect(onChangeFn).toHaveBeenLastCalledWith(1.5);

        fireEvent.change(input, { target: { value: "not-a-number" } });
        expect(onChangeFn).toHaveBeenLastCalledWith(NaN);
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
