import React from "react";
import { useAppSelector } from "../../ducks";
import Dropdown, { MenuItem } from "../common/Dropdown";
import Icon from "../common/Icon";

type ViewSelectorProps = {
    value: string;
    onChange: (viewName: string) => void;
};

export default function ViewSelector({ value, onChange }: ViewSelectorProps) {
    const contentViews = useAppSelector(
        (state) => state.backendState.contentViews || [],
    );

    const inner = (
        <span>
            <Icon name="files" />
            &nbsp;<b>View:</b> {value.toLowerCase()} <span className="caret" />
        </span>
    );

    return (
        <Dropdown
            text={inner}
            className="btn btn-default btn-xs"
            options={{ placement: "top-end" }}
        >
            {contentViews.map((name) => (
                <MenuItem key={name} onClick={() => onChange(name)}>
                    {name.toLowerCase().replace("_", " ")}
                </MenuItem>
            ))}
        </Dropdown>
    );
}
