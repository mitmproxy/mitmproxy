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
    const isSmall = className?.split(" ").includes("btn-sm");

    return (
        <button
            className={classnames(className, "btn btn-default m-btn m-btn-default", {
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
