import * as React from "react";
import { render } from "../../test-utils";
import { TStore } from "../../ducks/tutils";
import ThemeManager from "../../../components/helpers/ThemeManager";
import { defaultState as defaultOptions } from "../../../ducks/options";

function storeWithTheme(web_theme: string) {
    const state = TStore().getState();
    return TStore({
        ...state,
        options: { ...defaultOptions, web_theme },
    });
}

function mockMatchMedia(matches: boolean) {
    window.matchMedia = ((query: string) => ({
        matches,
        media: query,
        onchange: null,
        addEventListener: () => {},
        removeEventListener: () => {},
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
}

afterEach(() => {
    document.documentElement.removeAttribute("data-theme");
});

test("system theme follows OS preference (light)", () => {
    mockMatchMedia(false);
    render(<ThemeManager />, { store: storeWithTheme("system") });
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
});

test("system theme follows OS preference (dark)", () => {
    mockMatchMedia(true);
    render(<ThemeManager />, { store: storeWithTheme("system") });
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
});

test("explicit dark overrides OS preference", () => {
    mockMatchMedia(false);
    render(<ThemeManager />, { store: storeWithTheme("dark") });
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
});

test("explicit light overrides OS preference", () => {
    mockMatchMedia(true);
    render(<ThemeManager />, { store: storeWithTheme("light") });
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
});
