import * as React from "react";

interface PopoverProps {
    children: React.ReactNode;
}

export function Popover({ children }: PopoverProps) {
    const [isVisible, setIsVisible] = React.useState(false);
    const popoverRef = React.useRef<HTMLDivElement>(null);

    const handleClickOutside = (event: MouseEvent) => {
        if (
            popoverRef.current &&
            !popoverRef.current.contains(event.target as Node)
        ) {
            setIsVisible(false);
        }
    };

    React.useEffect(() => {
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    return (
        <div className="mode-popover-container" ref={popoverRef}>
            <i
                className="fa fa-cog mode-popover-icon"
                aria-hidden="true"
                onClick={() => setIsVisible(!isVisible)}
            ></i>
            {isVisible && (
                <div className="mode-popover-content">
                    <div className="mode-popover-header">
                        <label className="mode-popover-title">
                            Advanced Configuration
                        </label>
                    </div>
                    <div className="mode-popover-body">{children}</div>
                </div>
            )}
        </div>
    );
}
