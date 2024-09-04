import * as React from "react";

type ModeToggleProps = {
    value: boolean;
    label: string;
    onChange: (e: React.ChangeEvent) => void;
    children: React.ReactNode;
};

export function ModeToggle({
    value,
    onChange,
    children,
    label,
}: ModeToggleProps) {
    const id = React.useId();

    return (
        <div className="mode-entry">
            <input
                type="checkbox"
                name={`mode-checkbox-${id}`}
                id={`mode-checkbox-${id}`}
                checked={value}
                onChange={onChange}
            />
            <label
                htmlFor={`mode-checkbox-${id}`}
                style={{ marginBottom: 0, fontWeight: "normal" }}
            >
                {label}
            </label>
            {children}
        </div>
    );
}
