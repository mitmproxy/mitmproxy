import * as React from "react";
import OptionInput, {
    ChoicesOption,
    Options,
} from "../../../components/Modal/OptionInput";
import { OPTIONS_UPDATE } from "../../../ducks/options";
import { fireEvent, render, screen, userEvent } from "../../test-utils";
import { TStore } from "../../ducks/tutils";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

enableFetchMocks();

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

    it("should only commit on blur or enter", async () => {
        const onChangeFn = jest.fn();
        render(<StringOption value="" onChange={onChangeFn} />);
        const input = screen.getByRole("textbox");

        await userEvent.type(input, "/tmp/foo");
        expect(input).toHaveValue("/tmp/foo");
        expect(onChangeFn).not.toHaveBeenCalled();

        await userEvent.tab();
        expect(onChangeFn).toHaveBeenCalledTimes(1);
        expect(onChangeFn).toHaveBeenLastCalledWith("/tmp/foo");

        await userEvent.type(input, "bar{enter}");
        expect(onChangeFn).toHaveBeenCalledTimes(2);
        expect(onChangeFn).toHaveBeenLastCalledWith("/tmp/foobar");
    });

    it("should not commit an unchanged value", async () => {
        const onChangeFn = jest.fn();
        render(<StringOption value="foo" onChange={onChangeFn} />);
        await userEvent.click(screen.getByRole("textbox"));
        await userEvent.tab();
        expect(onChangeFn).not.toHaveBeenCalled();
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

    it("should parse ints on enter", async () => {
        const onChange = jest.fn();
        render(<NumberOption value={8080} onChange={onChange} />);
        const input = screen.getByRole("spinbutton");
        await userEvent.clear(input);
        await userEvent.type(input, "9090");
        expect(onChange).not.toHaveBeenCalled();
        await userEvent.type(input, "{enter}");
        expect(onChange).toHaveBeenCalledWith(9090);
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
        fireEvent.blur(input);
        expect(onChangeFn).toHaveBeenLastCalledWith(1.5);

        fireEvent.change(input, { target: { value: "not-a-number" } });
        fireEvent.blur(input);
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

describe("StringSequenceOption Component", () => {
    const StringSequenceOption = Options["sequence of str"];

    it("should only commit non-empty lines on blur", () => {
        const onChangeFn = jest.fn();
        render(<StringSequenceOption value={["a"]} onChange={onChangeFn} />);
        const textarea = screen.getByRole("textbox");

        fireEvent.change(textarea, { target: { value: "a\nb\n\nc\n" } });
        expect(onChangeFn).not.toHaveBeenCalled();

        fireEvent.blur(textarea);
        expect(onChangeFn).toHaveBeenCalledWith(["a", "b", "c"]);
    });
});

describe("OptionInput Component", () => {
    it("should send one update for a typed path", async () => {
        fetchMock.resetMocks();
        fetchMock.mockResponse("");
        const store = TStore();
        store.dispatch(
            OPTIONS_UPDATE({
                save_stream_file: {
                    type: "optional str",
                    default: undefined,
                    value: undefined,
                    help: "Stream flows to file as they arrive.",
                },
            }),
        );
        render(<OptionInput name="save_stream_file" />, { store });
        const input = screen.getByRole("textbox");

        await userEvent.type(input, "/tmp/flows.mitm");
        expect(fetchMock).not.toHaveBeenCalled();

        await userEvent.tab();
        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(fetchMock.mock.calls[0][1]?.body).toEqual(
            '{"save_stream_file":"/tmp/flows.mitm"}',
        );
    });
});
