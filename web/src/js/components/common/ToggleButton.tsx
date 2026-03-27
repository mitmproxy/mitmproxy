import React from "react";
import classnames from "classnames";

type ToggleButtonProps = {
    checked: boolean;
    onToggle: () => any;
    text: string;
};

export default function ToggleButton({
    checked,
    onToggle,
    text,
}: ToggleButtonProps) {
    return (
        <div
            className={classnames("m-btn m-toggle", {
                "m-btn-primary m-toggle-on": checked,
                "m-btn-default m-toggle-off": !checked,
            })}
            onClick={onToggle}
        >
            <i
                className={
                    "fa fa-fw " +
                    (checked ? "fa-check-square-o" : "fa-square-o")
                }
            />
            &nbsp;
            {text}
        </div>
    );
}
