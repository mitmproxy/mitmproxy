import * as React from "react";

interface PopoverProps {
    children: React.ReactNode;
}

export function Popover({ children }: PopoverProps) {
    const id = React.useId();

    // Rather annoying workaround to make popover anchors work with current React.
    // Ideally this can go away once browsers have anchor-scope.
    // https://github.com/facebook/react/issues/26839
    const cssId = "--" + [...id].map(c => c.charCodeAt(0).toString(16)).join("");
    const buttonRef = React.useRef<HTMLButtonElement>(null);
    const popoverRef = React.useRef<HTMLDivElement>(null);
    React.useEffect(() => {
        // @ts-expect-error no anchor support yet
        buttonRef.current!.style.anchorName = cssId;
        // @ts-expect-error no anchor support yet
        popoverRef.current!.style.positionAnchor = cssId;
    }, []);

    return (
        <div className="mode-popover">
            {/* @ts-expect-error no popover support yet */}
            <button popovertarget={id} ref={buttonRef}>
                <i className="fa fa-cog" aria-hidden="true"></i>
            </button>
            {/* @ts-expect-error no popover support yet */}
            <div id={id} popover="auto" ref={popoverRef}>
                <h4>Advanced Configuration</h4>
                {children}
            </div>
        </div>
    );
}
