import React, { useEffect, useState } from "react";
import { useFloating, UseFloatingOptions } from "@floating-ui/react-dom";
import classnames from "classnames";

export const Divider = () => <li role="separator" className="divider" />;

type MenuItemProps = {
    onClick: () => void;
    children: React.ReactNode;
};

export function MenuItem({ onClick, children, ...attrs }: MenuItemProps) {
    const click = (e) => {
        e.preventDefault();
        onClick();
    };

    return (
        <li>
            <a href="#" onClick={click} {...attrs}>
                {children}
            </a>
        </li>
    );
}

type SubMenuProps = {
    title: string;
    children: React.ReactNode;
    className?: string;
};

export function SubMenu({ title, children, className }: SubMenuProps) {
    const [open, setOpen] = useState(false);
    const { refs, floatingStyles } = useFloating({
        placement: "right-start",
    });
    let submenu: React.ReactNode | null = null;
    if (open) {
        submenu = (
            <ul
                className={classnames("dropdown-menu show", className)}
                ref={refs.setFloating}
                style={floatingStyles}
            >
                {children}
            </ul>
        );
    }

    return (
        <li
            ref={refs.setReference}
            onMouseEnter={() => setOpen(true)}
            onMouseLeave={() => setOpen(false)}
        >
            <a>
                <i
                    className="fa fa-caret-right pull-right"
                    aria-hidden="true"
                />{" "}
                {title}
            </a>
            {submenu}
        </li>
    );
}

type DropdownProps = {
    text: React.ReactNode;
    children: React.ReactNode;
    options?: UseFloatingOptions;
    className?: string;
    onOpen?: (b: boolean) => void;
};
/*
 * When modifying this component, check that File -> Open and flow content upload work.
 */
export default React.memo(function Dropdown({
    text,
    children,
    options,
    className,
    onOpen,
    ...attrs
}: DropdownProps) {
    const [open, _setOpen] = useState(false);

    const { refs, floatingStyles } = useFloating(options);

    const setOpen = (b: boolean) => {
        _setOpen(b);
        if (onOpen) onOpen(b);
    };

    useEffect(() => {
        if (!refs.floating.current) return;
        document.addEventListener(
            "click",
            (e) => {
                if (!refs.floating.current?.contains(e.target as Node)) {
                    e.preventDefault();
                    e.stopPropagation();
                    setOpen(false);
                } else {
                    // We only want to call setOpen on the way out. This ensures the dropdown stays in DOM when clicked,
                    // which we need for file upload from Dropdowns.
                    document.addEventListener("click", () => setOpen(false), {
                        once: true,
                    });
                }
            },
            { once: true, capture: true },
        );
    }, [refs.floating.current]);

    let contents;
    if (open) {
        contents = (
            <ul
                className="dropdown-menu show"
                ref={refs.setFloating}
                style={floatingStyles}
            >
                {children}
            </ul>
        );
    } else {
        contents = null;
    }

    return (
        <>
            <a
                href="#"
                ref={refs.setReference}
                className={classnames(className, { open: open })}
                onClick={(e) => {
                    e.preventDefault();
                    setOpen(true);
                }}
                {...attrs}
            >
                {text}
            </a>
            {contents}
        </>
    );
});
