import * as React from "react";

interface PopoverProps {
    children: React.ReactNode;
    iconClass: string;
    classname?: string;
    isVisible?: boolean; //used only for local mode
}

export function Popover({
    children,
    iconClass,
    classname,
    isVisible,
}: PopoverProps) {
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

    //trick to open the popover even when clicking on an input field (local mode)
    React.useEffect(() => {
        if (isVisible === true) {
            document.getElementById(id)?.showPopover();
        }
    }, [isVisible]);

    return (
        <div
            className={classname ? `mode-popover ${classname}` : "mode-popover"}
        >
            {/* @ts-expect-error no popover support yet */}
            <button popoverTarget={id} ref={buttonRef}>
                <i className={iconClass} aria-hidden="true"></i>
            </button>
            {/* @ts-expect-error no popover support yet */}
            <div id={id} popover="auto" ref={popoverRef}>
                {children}
            </div>
        </div>
    );
}
