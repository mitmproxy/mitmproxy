import * as React from "react";
import classnames from "classnames";

type BadgeProps = {
    className?: string;
    children: React.ReactNode;
    title?: string;
};

export default function Badge({ className, children, title }: BadgeProps) {
    return (
        <span className={classnames("badge", className)} title={title}>
            {children}
        </span>
    );
}
