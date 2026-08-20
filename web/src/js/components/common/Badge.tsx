import * as React from "react";
import classnames from "classnames";

type BadgeProps = {
    className?: string;
    children: React.ReactNode;
};

export default function Badge({ className, children }: BadgeProps) {
    return <span className={classnames("badge", className)}>{children}</span>;
}
