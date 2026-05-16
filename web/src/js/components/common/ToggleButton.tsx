import React from "react";
import classnames from "classnames";
import Icon from "./Icon";

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
            className={classnames("btn toggle", {
                "btn-primary toggle-on": checked,
                "btn-default toggle-off": !checked,
            })}
            onClick={onToggle}
        >
            <Icon name={checked ? "confirmSquare" : "square"} />
            &nbsp;
            {text}
        </div>
    );
}
