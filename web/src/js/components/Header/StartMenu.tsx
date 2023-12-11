import * as React from "react";
import FilterInput from "./FilterInput";
import * as flowsActions from "../../ducks/flows";
import { setFilter, setHighlight } from "../../ducks/flows";
import Button from "../common/Button";
import { update as updateOptions } from "../../ducks/options";
import { useAppDispatch, useAppSelector } from "../../ducks";

StartMenu.title = "Start";

export default function StartMenu() {
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
        </div>
    );
}

function InterceptInput() {
    const dispatch = useAppDispatch(),
        value = useAppSelector((state) => state.options.intercept);
    return (
        <FilterInput
            value={value || ""}
            placeholder="Intercept"
            type="pause"
            color="hsl(208, 56%, 53%)"
            onChange={(val) => dispatch(updateOptions("intercept", val))}
        />
    );
}

function FlowFilterInput() {
    const dispatch = useAppDispatch(),
        value = useAppSelector((state) => state.flows.filter);
    return (
        <FilterInput
            value={value || ""}
            placeholder="Search"
            type="search"
            color="black"
            onChange={(value) => dispatch(setFilter(value))}
        />
    );
}

function HighlightInput() {
    const dispatch = useAppDispatch(),
        value = useAppSelector((state) => state.flows.highlight);
    return (
        <FilterInput
            value={value || ""}
            placeholder="Highlight"
            type="tag"
            color="hsl(48, 100%, 50%)"
            onChange={(value) => dispatch(setHighlight(value))}
        />
    );
}

export function ResumeAll() {
    const dispatch = useAppDispatch();
    return (
        <Button
            className="btn-sm"
            title="[a]ccept all"
            icon="fa-forward text-success"
            onClick={() => dispatch(flowsActions.resumeAll())}
        >
            Resume All
        </Button>
    );
}
