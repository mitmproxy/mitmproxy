import * as React from "react";

type ModeToggleProps = {
    value: boolean;
    onChange: (e: React.ChangeEvent) => void;
    children: React.ReactNode;
};

export function ModeToggle({ value, onChange, children }: ModeToggleProps) {
    return (
        <div className="mode-entry">
            <input type="checkbox" checked={value} onChange={onChange} />
            {children}
        </div>
    );
}
