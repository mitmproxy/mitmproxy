import React from "react";
import { useTranslation } from "react-i18next";
import { useAppSelector } from "../../ducks";
import Dropdown, { MenuItem } from "../common/Dropdown";

type ViewSelectorProps = {
    value: string;
    onChange: (string) => void;
};

export default function ViewSelector({ value, onChange }: ViewSelectorProps) {
    const { t } = useTranslation();
    const contentViews = useAppSelector(
        (state) => state.backendState.contentViews || [],
    );

    const inner = (
        <span>
            <i className="fa fa-fw fa-files-o" />
            &nbsp;<b>{t("contentview.view")}:</b> {value.toLowerCase()}{" "}
            <span className="caret" />
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
