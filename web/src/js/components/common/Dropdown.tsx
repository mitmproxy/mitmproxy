import React, { useEffect, useState } from "react";
import { usePopper } from "react-popper";
import * as PopperJS from "@popperjs/core";
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
    const [referenceElement, setReferenceElement] =
        useState<HTMLLIElement | null>(null);
    const [popperElement, setPopperElement] = useState<HTMLUListElement | null>(
        null,
    );
    const { styles, attributes } = usePopper(referenceElement, popperElement, {
        placement: "right-start",
    });

    let submenu: React.ReactNode | null = null;
    if (open) {
        submenu = (
            <ul
                className={classnames("dropdown-menu show", className)}
                ref={setPopperElement}
                style={styles.popper}
                {...attributes.popper}
            >
                {children}
            </ul>
        );
    }

    return (
        <li
            ref={setReferenceElement}
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
    options?: Partial<PopperJS.Options>;
    className?: string;
    onOpen?: (boolean) => void;
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
    const [refElement, setRefElement] = useState<HTMLAnchorElement | null>(
        null,
    );
    const [open, _setOpen] = useState(false);
    const [popperElement, setPopperElement] = useState<HTMLUListElement | null>(
        null,
    );
    const { styles, attributes } = usePopper(refElement, popperElement, {
        ...options,
    });

    const setOpen = (b: boolean) => {
        _setOpen(b);
        onOpen && onOpen(b);
    };

    useEffect(() => {
        if (!popperElement) return;
        document.addEventListener(
            "click",
            (e) => {
                if (!popperElement.contains(e.target as Node)) {
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
    }, [popperElement]);

    let contents;
    if (open) {
        contents = (
            <ul
                className="dropdown-menu show"
                ref={setPopperElement}
                style={styles.popper}
                {...attributes.popper}
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
                ref={setRefElement}
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
