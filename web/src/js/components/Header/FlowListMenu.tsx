import * as React from "react";
import { useTranslation } from "react-i18next";
import FilterInput, { FilterIcon } from "./FilterInput";
import * as flowsActions from "../../ducks/flows";
import Button from "../common/Button";
import { update as updateOptions } from "../../ducks/options";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { FilterName, setFilter, setHighlight } from "../../ducks/ui/filter";

FlowListMenu.title = "Flow List";

export default function FlowListMenu() {
    return (
        <div className="main-menu">
            <div className="menu-group">
                <div className="menu-content">
                    <FlowFilterInput />
                    <HighlightInput />
                </div>
                <div className="menu-legend"><FlowListMenuSectionLegend /></div>
            </div>

            <div className="menu-group">
                <div className="menu-content">
                    <InterceptInput />
                    <ResumeAll />
                </div>
                <div className="menu-legend"><InterceptSectionLegend /></div>
            </div>
        </div>
    );
}

function FlowListMenuSectionLegend() {
    const { t } = useTranslation();
    return <>{t("header.flowListMenu.find")}</>;
}

function InterceptSectionLegend() {
    const { t } = useTranslation();
    return <>{t("header.flowListMenu.intercept")}</>;
}

function InterceptInput() {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();
    const value = useAppSelector((state) => state.options.intercept);
    return (
        <FilterInput
            value={value || ""}
            placeholder={t("header.flowListMenu.interceptPlaceholder")}
            icon={FilterIcon.INTERCEPT}
            color="hsl(208, 56%, 53%)"
            onChange={(val) => dispatch(updateOptions("intercept", val))}
        />
    );
}

function FlowFilterInput() {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();
    const value = useAppSelector((state) => state.ui.filter[FilterName.Search]);
    return (
        <FilterInput
            value={value}
            placeholder={t("header.flowListMenu.searchPlaceholder")}
            icon={FilterIcon.SEARCH}
            color="black"
            onChange={(expr) => dispatch(setFilter(expr))}
        />
    );
}

function HighlightInput() {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();
    const value = useAppSelector(
        (state) => state.ui.filter[FilterName.Highlight],
    );
    return (
        <FilterInput
            value={value}
            placeholder={t("header.flowListMenu.highlightPlaceholder")}
            icon={FilterIcon.HIGHLIGHT}
            color="hsl(48, 100%, 50%)"
            onChange={(expr) => dispatch(setHighlight(expr))}
        />
    );
}

export function ResumeAll() {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();
    return (
        <Button
            className="btn-sm"
            title={t("header.flowListMenu.resumeAllTitle")}
            icon="fa-forward text-success"
            onClick={() => dispatch(flowsActions.resumeAll())}
        >
            {t("header.flowListMenu.resumeAll")}
        </Button>
    );
}
