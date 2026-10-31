import * as React from "react";
import classnames from "classnames";

type BadgeProps = React.ComponentPropsWithoutRef<"span">;

export default function Badge({ className, ...props }: BadgeProps) {
    return <span {...props} className={classnames("badge", className)} />;
}
