import * as React from "react";

interface PopoverProps {
    children: React.ReactNode;
    mode: string;
}

export function Popover({ children, mode }: PopoverProps) {
    return (
        <div className="mode-popover-container">
            <button id={`button-config-${mode}`} popovertarget={`popover-${mode}`} className="mode-popover-icon">
                <i
                    className="fa fa-cog"
                    aria-hidden="true"
                ></i>
            </button>
            <div
                id={`popover-${mode}`}
                popover="auto"
            >
                <div className="mode-popover-header">
                    <label className="mode-popover-title">
                        Advanced Configuration
                    </label>
                </div>
                <div className="mode-popover-content">{children}</div>
            </div>
        </div>
    );
}