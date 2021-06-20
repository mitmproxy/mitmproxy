import React, {useEffect, useState} from 'react'
import {usePopper} from "react-popper";
import * as PopperJS from "@popperjs/core";
import classnames from "classnames";

export const Divider = () => <li role="separator" className="divider"/>;


type MenuItemProps = {
    onClick: () => void,
    children: React.ReactNode
}

export function MenuItem({onClick, children, ...attrs}: MenuItemProps) {

    const click = (e) => {
        e.preventDefault();
        onClick();
    }

    return <li>
        <a
            href="#"
            onClick={click}
            {...attrs}>
            {children}
        </a>
    </li>
}

type SubMenuProps = {
    title: string,
    children: React.ReactNode,
}

export function SubMenu({title, children}: SubMenuProps) {
    const [open, setOpen] = useState(false);
    const [referenceElement, setReferenceElement] = useState(null);
    const [popperElement, setPopperElement] = useState(null);
    const {styles, attributes} = usePopper(referenceElement, popperElement, {placement: "right-start"});

    let submenu = null;
    if (open) {
        submenu = <ul className="dropdown-menu show" ref={setPopperElement}
                      style={styles.popper} {...attributes.popper}>{children}</ul>;
    }

    return (
        <li
            ref={setReferenceElement}
            onMouseEnter={() => setOpen(true)}
            onMouseLeave={() => setOpen(false)}
        >
            <a><i className="fa fa-caret-right pull-right" aria-hidden="true"/> {title}</a>
            {submenu}
        </li>
    )
}

type DropdownProps = {
    text: React.ReactNode,
    children: React.ReactNode,
    options?: Partial<PopperJS.Options>,
    className?: string,
    onOpen?: (boolean) => void
}
export default React.memo(function Dropdown({text, children, options, className, onOpen, ...attrs}: DropdownProps) {

    const [refElement, setRefElement] = useState(null);
    const [open, _setOpen] = useState(false);
    const [popperElement, setPopperElement] = useState(null);
    const {styles, attributes} = usePopper(refElement, popperElement, {...options});

    let setOpen = (b: boolean) => {
        _setOpen(b);
        onOpen && onOpen(b);
    };

    useEffect(() => {
        if (!open)
            return
        document.addEventListener("click", () => {
            // a bit tricky: we need to wait here for a bit so that we don't double-toggle
            // when clicking the dropdown button.
            setTimeout(() => setOpen(false));
        }, {capture: true, once: true});
    }, [open]);

    let contents;
    if (open) {
        contents = <ul
            className="dropdown-menu show"
            ref={setPopperElement}
            style={styles.popper}
            {...attributes.popper}>
            {children}
        </ul>
    } else {
        contents = null;
    }

    return <>
        <a href="#"
           ref={setRefElement}
           className={classnames(className, {"open": open})}
           onClick={() => setOpen(true)}
           {...attrs}>
            {text}
        </a>
        {contents}
    </>;
});
