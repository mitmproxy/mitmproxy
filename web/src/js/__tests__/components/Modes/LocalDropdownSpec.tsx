import * as React from "react";
import { fireEvent, render, screen, waitFor } from "../../test-utils";
import LocalDropdown from "../../../components/Modes/LocalDropdown";
import { TStore } from "../../ducks/tutils";
import { Provider } from "react-redux";

test("LocalDropdown - initial render and filtering", async () => {
    const store = TStore();

    const server = store.getState().modes.local[0];

    const { asFragment } = render(
        <Provider store={store}>
            <LocalDropdown server={server} />
        </Provider>,
    );
    expect(asFragment()).toMatchSnapshot();

    const input = screen.getByPlaceholderText("(all applications)");
    expect(input).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "curl" } });

    await waitFor(() =>
        expect(screen.getByText("curl.exe")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByText("curl.exe"));

    expect(
        screen.getByText("curl.exe").parentElement?.parentElement,
    ).toHaveClass("selected");
});

test("LocalDropdown - no matching processes", async () => {
    const store = TStore();
    const server = store.getState().modes.local[0];

    render(
        <Provider store={store}>
            <LocalDropdown server={server} />
        </Provider>,
    );

    const input = screen.getByPlaceholderText("(all applications)");
    fireEvent.change(input, { target: { value: "nonexistent" } });

    await waitFor(() => {
        expect(screen.getByText(/Press/i)).toBeInTheDocument();
        expect(screen.getByText("Enter")).toBeInTheDocument();
        expect(screen.getByText("nonexistent")).toBeInTheDocument();
    });
});

test("LocalDropdown - toggle process selection", async () => {
    const store = TStore();
    const server = store.getState().modes.local[0];

    render(
        <Provider store={store}>
            <LocalDropdown server={server} />
        </Provider>,
    );

    const input = screen.getByPlaceholderText("(all applications)");
    fireEvent.change(input, { target: { value: "curl" } });

    await waitFor(() =>
        expect(screen.getByText("curl.exe")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByText("curl.exe"));

    expect(
        screen.getByText("curl.exe").parentElement?.parentElement,
    ).toHaveClass("selected");

    fireEvent.click(screen.getByText("curl.exe"));

    expect(
        screen.getByText("curl.exe").parentElement?.parentElement,
    ).not.toHaveClass("selected");
});
