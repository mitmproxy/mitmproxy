import * as React from "react";

type Theme = "light" | "dark" | "system";

interface ThemeContextType {
    theme: Theme;
    setTheme: (theme: Theme) => void;
}

const ThemeContext = React.createContext<ThemeContextType | undefined>(
    undefined,
);

export function ThemeHandler({ children }: { children: React.ReactNode }) {
    const [theme, setTheme] = React.useState<Theme>(() => {
        return (localStorage.getItem("mitmproxy-theme") as Theme) || "system";
    });

    React.useEffect(() => {
        localStorage.setItem("mitmproxy-theme", theme);

        const applyTheme = (t: Theme) => {
            let activeTheme = t;
            if (activeTheme === "system") {
                activeTheme =
                    window.matchMedia &&
                    window.matchMedia("(prefers-color-scheme: dark)").matches
                        ? "dark"
                        : "light";
            }
            document.documentElement.setAttribute("data-theme", activeTheme);
        };

        applyTheme(theme);

        if (theme === "system" && window.matchMedia) {
            const mediaQuery = window.matchMedia(
                "(prefers-color-scheme: dark)",
            );
            const handleChange = () => applyTheme("system");
            mediaQuery.addEventListener("change", handleChange);
            return () => mediaQuery.removeEventListener("change", handleChange);
        }
    }, [theme]);

    return (
        <ThemeContext.Provider value={{ theme, setTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

export function useTheme() {
    const context = React.useContext(ThemeContext);
    if (!context) {
        throw new Error("useTheme must be used within a ThemeHandler");
    }
    return context;
}
