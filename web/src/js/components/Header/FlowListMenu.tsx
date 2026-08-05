import * as React from "react";
import FilterInput, { FilterIcon } from "./FilterInput";
import * as flowsActions from "../../ducks/flows";
import Button from "../common/Button";
import { update as updateOptions } from "../../ducks/options";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { FilterName, setFilter, setHighlight } from "../../ducks/ui/filter";
import { resetColumnWidths } from "../../ducks/ui/columnWidths";

FlowListMenu.title = "Flow List";

export default function FlowListMenu() {
    return (
        <div className="main-menu">
            <div className="menu-group">
                <div className="menu-content">
                    <FlowFilterInput />
                    <HighlightInput />
                </div>
                <div className="menu-legend">Find</div>
            </div>

            <div className="menu-group">
                <div className="menu-content">
                    <InterceptInput />
                    <ResumeAll />
                </div>
                <div className="menu-legend">Intercept</div>
            </div>

            <div className="menu-group">
                <div className="menu-content">
                    <ResetColumnWidths />
                </div>
                <div className="menu-legend">Columns</div>
            </div>
        </div>
    );
}

export function ResetColumnWidths() {
    const dispatch = useAppDispatch();
    const resized = useAppSelector(
        (state) => Object.keys(state.ui.columnWidths).length > 0,
    );
    return (
        <Button
            className="btn-sm"
            title="Restore the flow table columns to their default widths"
            icon="revert"
            disabled={!resized}
            onClick={() => dispatch(resetColumnWidths())}
        >
            Reset Widths
        </Button>
    );
}

function InterceptInput() {
    const dispatch = useAppDispatch();
    const value = useAppSelector((state) => state.options.intercept);
    return (
        <FilterInput
            value={value || ""}
            placeholder="Intercept"
            icon={FilterIcon.INTERCEPT}
            color="hsl(208, 56%, 53%)"
            onChange={(val) => dispatch(updateOptions("intercept", val))}
        />
    );
}

function FlowFilterInput() {
    const dispatch = useAppDispatch();
    const value = useAppSelector((state) => state.ui.filter[FilterName.Search]);
    return (
        <FilterInput
            value={value}
            placeholder="Search"
            icon={FilterIcon.SEARCH}
            color="var(--mitmweb-fg)"
            onChange={(expr) => dispatch(setFilter(expr))}
        />
    );
}

function HighlightInput() {
    const dispatch = useAppDispatch();
    const value = useAppSelector(
        (state) => state.ui.filter[FilterName.Highlight],
    );
    return (
        <FilterInput
            value={value}
            placeholder="Highlight"
            icon={FilterIcon.HIGHLIGHT}
            color="hsl(48, 100%, 50%)"
            onChange={(expr) => dispatch(setHighlight(expr))}
        />
    );
}

export function ResumeAll() {
    const dispatch = useAppDispatch();
    return (
        <Button
            className="btn-sm"
            title="[a]ccept all"
            icon="resumeAll"
            iconClassName="text-success"
            onClick={() => dispatch(flowsActions.resumeAll())}
        >
            Resume All
        </Button>
    );
}
