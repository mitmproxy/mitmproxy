import * as React from "react";
import classnames from "classnames";

export interface ButtonProps {
    onClick: () => void;
    children?: React.ReactNode;
    icon?: string;
    disabled?: boolean;
    className?: string;
    title?: string;
}

export default function Button({
    onClick,
    children,
    icon,
    disabled,
    className,
    title,
}: ButtonProps) {
    const classes = className?.split(" ") || [];
    const isExtraSmall = classes.includes("m-btn-xs");
    const isSmall = classes.includes("m-btn-sm");

    return (
        <button
            className={classnames(className, "m-btn m-btn-default", {
                "m-btn-xs": isExtraSmall,
                "m-btn-sm": isSmall,
            })}
            onClick={disabled ? undefined : onClick}
            disabled={disabled}
            title={title}
        >
            {icon && (
                <>
                    <i className={"fa " + icon} />
                    &nbsp;
                </>
            )}
            {children}
        </button>
    );
}
