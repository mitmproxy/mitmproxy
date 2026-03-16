import * as React from "react";
import * as eventLogActions from "../../ducks/eventLog";
import * as commandBarActions from "../../ducks/commandBar";
import { useAppDispatch, useAppSelector } from "../../ducks";
import * as optionsActions from "../../ducks/options";

type MenuToggleProps = {
    value: boolean;
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    children?: React.ReactNode;
};

export function MenuToggle({ value, onChange, children }: MenuToggleProps) {
    return (
        <div className="menu-entry">
            <label>
                <input type="checkbox" checked={value} onChange={onChange} />
                {children}
            </label>
        </div>
    );
}

type OptionsToggleProps = {
    name: optionsActions.Option;
    children?: React.ReactNode;
};

export function OptionsToggle({ name, children }: OptionsToggleProps) {
    const dispatch = useAppDispatch();
    const value = useAppSelector((state) => state.options[name]);

    return (
        <MenuToggle
            value={!!value}
            onChange={() => dispatch(optionsActions.update(name, !value))}
        >
            {children}
        </MenuToggle>
    );
}

export function EventlogToggle() {
    const dispatch = useAppDispatch();
    const visible = useAppSelector((state) => state.eventLog.visible);

    return (
        <MenuToggle
            value={visible}
            onChange={() => dispatch(eventLogActions.toggleVisibility())}
        >
            Display Event Log
        </MenuToggle>
    );
}

export function CommandBarToggle() {
    const dispatch = useAppDispatch();
    const visible = useAppSelector((state) => state.commandBar.visible);

    return (
        <MenuToggle
            value={visible}
            onChange={() => dispatch(commandBarActions.toggleVisibility())}
        >
            Display Command Bar
        </MenuToggle>
    );
}

export function ThemeToggle() {
    const [theme, setTheme] = React.useState<"light" | "dark" | "system">(
        () => {
            return (
                (localStorage.getItem("mitmproxy-theme") as
                    | "light"
                    | "dark"
                    | "system") || "system"
            );
        },
    );

    React.useEffect(() => {
        localStorage.setItem("mitmproxy-theme", theme);

        const applyTheme = (t: "light" | "dark" | "system") => {
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
        <div className="menu-entry">
            <label style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                Theme:
                <select
                    value={theme}
                    onChange={(e) =>
                        setTheme(e.target.value as "light" | "dark" | "system")
                    }
                    style={{
                        padding: "2px 4px",
                        background: "inherit",
                        color: "inherit",
                        border: "1px solid currentColor",
                        borderRadius: "3px",
                    }}
                >
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                    <option value="system">System</option>
                </select>
            </label>
        </div>
    );
}
