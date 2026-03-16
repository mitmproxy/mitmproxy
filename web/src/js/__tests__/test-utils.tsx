import * as React from "react";
import { render as rtlRender } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { Provider } from "react-redux";
import { TStore } from "./ducks/tutils";
import { ThemeHandler } from "../components/ThemeHandler";

// re-export everything
export { waitFor, fireEvent, act, screen } from "@testing-library/react";
export { userEvent };

export function render(ui, { store = TStore(), ...renderOptions } = {}) {
    function Wrapper({ children }: { children: React.ReactNode }) {
        return (
            <Provider store={store}>
                <ThemeHandler>{children}</ThemeHandler>
            </Provider>
        );
    }

    const ret = rtlRender(ui, { wrapper: Wrapper, ...renderOptions });
    return { ...ret, store };
}
