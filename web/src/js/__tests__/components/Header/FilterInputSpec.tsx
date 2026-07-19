import * as React from "react";
import { enableFetchMocks } from "jest-fetch-mock";
import FilterInput, {
    FilterIcon,
    validateFilter,
} from "../../../components/Header/FilterInput";
import FilterDocs from "../../../components/Header/FilterDocs";
import { act, fireEvent, render, waitFor } from "../../test-utils";

enableFetchMocks();

const validResponse = JSON.stringify({
    valid: true,
    description: "url matches /foo/i",
});

describe("FilterInput Component", () => {
    beforeEach(() => {
        fetchMock.resetMocks();
        fetchMock.mockResponse(validResponse);
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    it("should render correctly", () => {
        const { asFragment } = render(
            <FilterInput
                icon={FilterIcon.SEARCH}
                color="red"
                placeholder="bar"
                onChange={() => undefined}
                value="42"
            />,
        );
        expect(asFragment()).toMatchSnapshot();
    });

    it("should reject unsuccessful validation responses", async () => {
        fetchMock.mockReset();
        fetchMock.mockResponseOnce("Validation unavailable", { status: 503 });

        await expect(validateFilter("~u foo")).rejects.toThrow(
            "Validation unavailable",
        );
    });

    function dummyInput(value = "wat"): FilterInput {
        const ref = React.createRef<FilterInput>();
        render(
            <FilterInput
                icon={FilterIcon.SEARCH}
                color="red"
                placeholder="bar"
                value={value}
                onChange={jest.fn()}
                ref={ref}
            />,
        );
        return ref.current!;
    }

    it("should handle componentWillReceiveProps", () => {
        const { rerender, getByDisplayValue } = render(
            <FilterInput
                icon={FilterIcon.SEARCH}
                color="red"
                value="foo"
                placeholder=""
                onChange={() => null}
            />,
        );
        rerender(
            <FilterInput
                icon={FilterIcon.SEARCH}
                color="red"
                value="bar"
                placeholder=""
                onChange={() => null}
            />,
        );
        expect(getByDisplayValue("bar")).toBeInTheDocument();
    });

    it("preserves user-typed text when the parent re-renders with an unchanged value prop", () => {
        jest.useFakeTimers();
        const onChange = jest.fn();
        const props = {
            icon: FilterIcon.SEARCH,
            color: "red",
            placeholder: "Filter",
            value: "",
            onChange,
        };
        const { rerender, getByPlaceholderText } = render(
            <FilterInput {...props} />,
        );
        const input = getByPlaceholderText("Filter") as HTMLInputElement;

        fireEvent.change(input, { target: { value: "~foo bar" } });
        expect(input.value).toBe("~foo bar");
        expect(onChange).not.toHaveBeenCalled();

        rerender(<FilterInput {...props} />);
        expect(input.value).toBe("~foo bar");
    });

    it("should show filter docs, descriptions, and validation errors", () => {
        const filterInput = dummyInput();

        act(() => filterInput.setState({ value: "" }));
        const docs = filterInput.getDesc();
        expect(React.isValidElement(docs) && docs.type).toEqual(FilterDocs);

        act(() =>
            filterInput.setState({
                value: "~u foo",
                validation: {
                    status: "valid",
                    description: "url matches /foo/i",
                },
            }),
        );
        expect(filterInput.getDesc()).toEqual("url matches /foo/i");

        act(() =>
            filterInput.setState({
                validation: {
                    status: "invalid",
                    error: "Invalid filter expression",
                },
            }),
        );
        expect(filterInput.getDesc()).toEqual("Invalid filter expression");
    });

    it("should debounce and propagate valid filters", async () => {
        jest.useFakeTimers();
        const filterInput = dummyInput();

        act(() =>
            filterInput.onChange({
                target: { value: "~u f" },
            } as React.ChangeEvent<HTMLInputElement>),
        );
        act(() =>
            filterInput.onChange({
                target: { value: "~u foo" },
            } as React.ChangeEvent<HTMLInputElement>),
        );

        expect(fetchMock).not.toHaveBeenCalled();
        expect(filterInput.props.onChange).not.toHaveBeenCalled();

        await act(async () => jest.advanceTimersByTimeAsync(300));

        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(fetchMock).toHaveBeenCalledWith(
            "./filter/validate?expression=%7Eu+foo",
            expect.objectContaining({
                signal: expect.any(AbortSignal),
            }),
        );
        expect(filterInput.props.onChange).toHaveBeenCalledWith("~u foo");
        expect(filterInput.state.validation).toEqual({
            status: "valid",
            description: "url matches /foo/i",
        });
    });

    it("should not propagate invalid filters", async () => {
        jest.useFakeTimers();
        fetchMock.mockReset();
        fetchMock.mockResponseOnce(
            JSON.stringify({
                valid: false,
                error: "Invalid filter expression",
            }),
        );
        const filterInput = dummyInput();

        act(() =>
            filterInput.onChange({
                target: { value: "~invalid" },
            } as React.ChangeEvent<HTMLInputElement>),
        );
        await act(async () => jest.advanceTimersByTimeAsync(300));

        expect(filterInput.props.onChange).not.toHaveBeenCalled();
        expect(filterInput.state.validation).toEqual({
            status: "invalid",
            error: "Invalid filter expression",
        });
    });

    it("should commit an empty filter immediately", () => {
        jest.useFakeTimers();
        const filterInput = dummyInput("~u foo");

        act(() =>
            filterInput.onChange({
                target: { value: "" },
            } as React.ChangeEvent<HTMLInputElement>),
        );

        expect(fetchMock).not.toHaveBeenCalled();
        expect(filterInput.props.onChange).toHaveBeenCalledWith("");
        expect(filterInput.state.validation).toEqual({
            status: "valid",
            description: "",
        });
    });

    it("should surface request failures without propagating the filter", async () => {
        jest.useFakeTimers();
        fetchMock.mockReset();
        fetchMock.mockRejectOnce(new Error("connection failed"));
        const filterInput = dummyInput();

        act(() =>
            filterInput.onChange({
                target: { value: "~u foo" },
            } as React.ChangeEvent<HTMLInputElement>),
        );
        await act(async () => jest.advanceTimersByTimeAsync(300));

        expect(filterInput.props.onChange).not.toHaveBeenCalled();
        expect(filterInput.state.validation).toEqual({
            status: "error",
            error: "Error: connection failed",
        });
    });

    it("should abort obsolete requests and ignore their responses", async () => {
        jest.useFakeTimers();
        fetchMock.mockReset();
        let resolveFirstResponse: (body: string) => void;
        fetchMock.mockResponseOnce(
            () =>
                new Promise((resolve) => {
                    resolveFirstResponse = resolve;
                }),
        );
        fetchMock.mockResponseOnce(validResponse);
        const filterInput = dummyInput();

        act(() =>
            filterInput.onChange({
                target: { value: "~u first" },
            } as React.ChangeEvent<HTMLInputElement>),
        );
        await act(async () => jest.advanceTimersByTimeAsync(300));
        const firstSignal = fetchMock.mock.calls[0][1]?.signal;

        act(() =>
            filterInput.onChange({
                target: { value: "~u second" },
            } as React.ChangeEvent<HTMLInputElement>),
        );
        expect(firstSignal?.aborted).toBe(true);
        await act(async () => jest.advanceTimersByTimeAsync(300));
        expect(filterInput.props.onChange).toHaveBeenCalledWith("~u second");

        await act(async () => resolveFirstResponse(validResponse));
        expect(filterInput.props.onChange).not.toHaveBeenCalledWith("~u first");
    });

    it("should ignore a response that no longer matches the input value", async () => {
        fetchMock.mockReset();
        let resolveResponse: (body: string) => void;
        fetchMock.mockResponseOnce(
            () =>
                new Promise((resolve) => {
                    resolveResponse = resolve;
                }),
        );
        const filterInput = dummyInput("~u first");
        let validation: Promise<void>;

        act(() => {
            validation = filterInput.validate("~u first", true);
        });
        act(() => filterInput.setState({ value: "~u second" }));
        await act(async () => {
            resolveResponse(validResponse);
            await validation;
        });

        expect(filterInput.props.onChange).not.toHaveBeenCalled();
    });

    it("should validate an existing filter on focus without propagating it", async () => {
        const filterInput = dummyInput("~u foo");

        act(() => filterInput.onFocus());

        expect(filterInput.state.focus).toBeTruthy();
        await waitFor(() =>
            expect(filterInput.state.validation.status).toEqual("valid"),
        );
        expect(filterInput.props.onChange).not.toHaveBeenCalled();
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
        const mockEvent: Partial<React.KeyboardEvent<HTMLInputElement>> = {
            key: "Escape",
            stopPropagation: jest.fn(),
        };
        act(() =>
            filterInput.onKeyDown(
                mockEvent as React.KeyboardEvent<HTMLInputElement>,
            ),
        );
        expect(input.blur).toHaveBeenCalled();
        expect(filterInput.state.mousefocus).toBeFalsy();
        expect(mockEvent.stopPropagation).toHaveBeenCalled();
    });

    it("should validate filters selected from the documentation", async () => {
        const filterInput = dummyInput();
        const input = filterInput.inputRef.current!;
        input.focus = jest.fn();

        act(() => filterInput.selectFilter("bar"));

        expect(filterInput.state.value).toEqual("bar");
        expect(input.focus).toHaveBeenCalled();
        await waitFor(() =>
            expect(filterInput.props.onChange).toHaveBeenCalledWith("bar"),
        );
    });

    it("should cancel validation when unmounted", async () => {
        jest.useFakeTimers();
        fetchMock.mockReset();
        fetchMock.mockResponseOnce(() => new Promise(() => {}));
        const ref = React.createRef<FilterInput>();
        const { getByPlaceholderText, unmount } = render(
            <FilterInput
                icon={FilterIcon.SEARCH}
                color="red"
                placeholder="Filter"
                value=""
                onChange={jest.fn()}
                ref={ref}
            />,
        );

        fireEvent.change(getByPlaceholderText("Filter"), {
            target: { value: "~u foo" },
        });
        await act(async () => jest.advanceTimersByTimeAsync(300));
        const signal = fetchMock.mock.calls[0][1]?.signal;

        unmount();

        expect(signal?.aborted).toBe(true);
    });

    it("should handle select", () => {
        const filterInput = dummyInput();
        const input = filterInput.inputRef.current!;
        input.select = jest.fn();
        act(() => filterInput.select());
        expect(input.select).toHaveBeenCalled();
    });
});
