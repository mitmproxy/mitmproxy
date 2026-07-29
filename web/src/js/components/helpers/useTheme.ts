import { useEffect, useState } from "react";
import { useAppSelector } from "../../ducks/hooks";

export type Theme = "system" | "dark" | "light";
export type ResolvedTheme = "dark" | "light";

function systemTheme(): ResolvedTheme {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
}

/**
 * Resolves the `web_theme` option to a concrete "dark" or "light" value,
 * following the OS preference (and its live changes) while set to "system".
 */
export function useResolvedTheme(): ResolvedTheme {
    const theme = useAppSelector(
        (state) => state.options.web_theme as Theme | undefined,
    );
    const [resolved, setResolved] = useState<ResolvedTheme>(() =>
        !theme || theme === "system" ? systemTheme() : theme,
    );

    useEffect(() => {
        if (theme && theme !== "system") {
            setResolved(theme);
            return;
        }
        const mql = window.matchMedia("(prefers-color-scheme: dark)");
        const update = () => setResolved(mql.matches ? "dark" : "light");
        update();
        mql.addEventListener("change", update);
        return () => mql.removeEventListener("change", update);
    }, [theme]);

    return resolved;
}
