import * as React from "react";
import { render, screen, act, fireEvent, rtlRender } from "../test-utils";
import { useTheme } from "../../components/ThemeHandler";

const TestComponent = () => {
    const { theme, setTheme } = useTheme();
    return (
        <div>
            <div data-testid="theme">{theme}</div>
            <button onClick={() => setTheme("dark")}>Set Dark</button>
            <button onClick={() => setTheme("light")}>Set Light</button>
            <button onClick={() => setTheme("system")}>Set System</button>
        </div>
    );
};

describe("ThemeHandler", () => {
    beforeEach(() => {
        localStorage.clear();
        document.documentElement.removeAttribute("data-theme");
    });

    it("should provide default theme", () => {
        render(<TestComponent />);
        expect(screen.getByTestId("theme")).toHaveTextContent("system");
    });

    it("should allow changing theme", () => {
        render(<TestComponent />);
        fireEvent.click(screen.getByText("Set Dark"));
        expect(screen.getByTestId("theme")).toHaveTextContent("dark");
        expect(localStorage.getItem("mitmproxy-theme")).toBe("dark");
        expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    });

    it("should persist theme to localStorage", () => {
        localStorage.setItem("mitmproxy-theme", "dark");
        render(<TestComponent />);
        expect(screen.getByTestId("theme")).toHaveTextContent("dark");
    });

    it("should handle system theme and media query changes", () => {
        let changeListener: any = null;
        const mediaQueryMock = {
            matches: false,
            addEventListener: jest.fn((event, listener) => {
                if (event === "change") changeListener = listener;
            }),
            removeEventListener: jest.fn(),
        };
        window.matchMedia = jest.fn().mockReturnValue(mediaQueryMock);

        render(<TestComponent />);
        fireEvent.click(screen.getByText("Set System"));
        
        expect(mediaQueryMock.addEventListener).toHaveBeenCalledWith("change", expect.any(Function));
        expect(document.documentElement.getAttribute("data-theme")).toBe("light");

        // Simulate media query change
        act(() => {
            mediaQueryMock.matches = true;
            changeListener();
        });
        expect(document.documentElement.getAttribute("data-theme")).toBe("dark");

        // Test cleanup
        const { unmount } = render(<TestComponent />);
        unmount();
        expect(mediaQueryMock.removeEventListener).toHaveBeenCalledWith("change", expect.any(Function));
    });

    it("should throw error if used outside ThemeHandler", () => {
        const consoleSpy = jest.spyOn(console, "error").mockImplementation(() => {});
        const BuggyComponent = () => {
            useTheme();
            return null;
        };
        expect(() => rtlRender(<BuggyComponent />)).toThrow("useTheme must be used within a ThemeHandler");
        consoleSpy.mockRestore();
    });
});
