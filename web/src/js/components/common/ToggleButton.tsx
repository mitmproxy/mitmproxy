import React from "react";

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
            className={
                "btn btn-toggle " + (checked ? "btn-primary" : "btn-default")
            }
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
