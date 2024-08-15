import * as React from "react";

interface PopoverProps {
    children: React.ReactNode;
}

export function Popover({ children }: PopoverProps) {

    // Popovers are positioned relatively to an element using `position-anchor: --name-of-anchor`.
    // As of 2024, Chrome only supports `anchor-name` for the anchor (and not `anchor-scope`), 
    // which is tree-scoped: Names must be unique across the page. So we do this rather annoying 
    // workaround here to generate a unique (hexadecimal) ID for each anchor and assign it with 
    // useEffect, because React 18 does not support `anchorName` in the style attribute.
    
    const id = React.useId();
    // ensure id is hexadecimal, 
    // https://github.com/facebook/react/issues/26839
    // https://drafts.csswg.org/css-syntax-3/#ident-token-diagram
    const cssId =
        "--" + [...id].map((c) => c.charCodeAt(0).toString(16)).join("");
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
