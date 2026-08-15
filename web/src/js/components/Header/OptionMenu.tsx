import * as React from "react";
import { useEffect, useRef, useState } from "react";
import { CommandBarToggle, EventlogToggle, OptionsToggle } from "./MenuToggle";
import Button from "../common/Button";
import DocsLink from "../common/DocsLink";
import HideInStatic from "../common/HideInStatic";
import FlowColumns from "../FlowTable/FlowColumns";
import * as modalActions from "../../ducks/ui/modal";
import * as optionsActions from "../../ducks/options";
import { resetColumnWidths } from "../../ducks/ui/columnWidths";
import { sortFunctions } from "../../flow/utils";
import { useAppDispatch, useAppSelector } from "../../ducks";

const TOGGLEABLE_COLUMNS = (
    Object.keys(sortFunctions) as (keyof typeof sortFunctions)[]
).filter((col) => col !== "quickactions");

// The table always shows these blank in the header; a text label is more useful here than an empty one.
const COLUMN_LABELS: Partial<Record<keyof typeof sortFunctions, string>> = {
    tls: "TLS",
    icon: "Resource Type",
};

OptionMenu.title = "Options";

function ThemeSelect() {
    const dispatch = useAppDispatch();
    const value = useAppSelector((state) => state.options.web_theme);
    const choices = useAppSelector(
        (state) => state.options_meta.web_theme?.choices,
    ) ?? ["system", "dark", "light"];

    return (
        <div className="menu-entry">
            <label>
                Theme
                <select
                    className="theme-select"
                    value={value}
                    onChange={(e) =>
                        dispatch(
                            optionsActions.update("web_theme", e.target.value),
                        )
                    }
                >
                    {choices.map((choice) => (
                        <option key={choice} value={choice}>
                            {choice}
                        </option>
                    ))}
                </select>
            </label>
        </div>
    );
}

export default function OptionMenu() {
    const dispatch = useAppDispatch();
    const openOptions = () => modalActions.setActiveModal("OptionModal");

    return (
        <div>
            <HideInStatic>
                <div className="menu-group">
                    <div className="menu-content">
                        <Button
                            title="Open Options"
                            icon="settings"
                            iconClassName="text-primary"
                            onClick={() => dispatch(openOptions())}
                        >
                            Edit Options
                        </Button>
                    </div>
                    <div className="menu-legend">Options Editor</div>
                </div>

                <div className="menu-group">
                    <div className="menu-content">
                        <OptionsToggle name="anticache">
                            Strip cache headers{" "}
                            <DocsLink resource="overview/features/#anticache" />
                        </OptionsToggle>
                        <OptionsToggle name="showhost">
                            Use host header for display{" "}
                            <DocsLink resource="concepts/options/#showhost" />
                        </OptionsToggle>
                        <OptionsToggle name="ssl_insecure">
                            Don&apos;t verify server certificates{" "}
                            <DocsLink resource="concepts/options/#ssl_insecure" />
                        </OptionsToggle>
                    </div>
                    <div className="menu-legend">Quick Options</div>
                </div>
            </HideInStatic>

            <div className="menu-group">
                <div className="menu-content">
                    <EventlogToggle />
                    <CommandBarToggle />
                </div>
                <div className="menu-legend">View Options</div>
            </div>

            <HideInStatic>
                <div className="menu-group">
                    <div className="menu-content">
                        <ThemeSelect />
                        <ColumnVisibility />
                        <ResetColumnWidths />
                    </div>
                    <div className="menu-legend">Appearance</div>
                </div>
            </HideInStatic>
        </div>
    );
}

function ColumnVisibility() {
    const dispatch = useAppDispatch();
    const visibleColumns = useAppSelector(
        (state) => state.options.web_columns,
    );
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!open) return;
        // A multi-select dropdown needs to survive clicks on its own checkboxes, so only a click elsewhere closes it.
        const onClickOutside = (e: MouseEvent) => {
            if (!ref.current?.contains(e.target as Node)) setOpen(false);
        };
        document.addEventListener("mousedown", onClickOutside);
        return () => document.removeEventListener("mousedown", onClickOutside);
    }, [open]);

    const toggle = (col: string) => {
        const next = visibleColumns.includes(col)
            ? visibleColumns.filter((c) => c !== col)
            : TOGGLEABLE_COLUMNS.filter(
                  (c) => c === col || visibleColumns.includes(c),
              );
        dispatch(optionsActions.update("web_columns", next));
    };

    return (
        <div className="column-visibility" ref={ref}>
            <Button
                className="btn-sm"
                icon="columns"
                onClick={() => setOpen(!open)}
            >
                Columns
            </Button>
            {open && (
                <ul className="dropdown-menu is-open">
                    {TOGGLEABLE_COLUMNS.map((col) => {
                        const checked = visibleColumns.includes(col);
                        return (
                            <li className="menu-entry" key={col}>
                                <label>
                                    <input
                                        type="checkbox"
                                        checked={checked}
                                        disabled={
                                            checked &&
                                            visibleColumns.length === 1
                                        }
                                        onChange={() => toggle(col)}
                                    />
                                    {COLUMN_LABELS[col] ??
                                        FlowColumns[col].headerName}
                                </label>
                            </li>
                        );
                    })}
                </ul>
            )}
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
