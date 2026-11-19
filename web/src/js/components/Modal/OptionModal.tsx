/* eslint-disable react/prop-types */
import React, { useRef, useState } from "react";
import { connect } from "react-redux";
import * as modalAction from "../../ducks/ui/modal";
import type { Option } from "../../ducks/options";
import { compact, isEmpty } from "lodash";
import type { RootState } from "../../ducks";
import { useAppDispatch, useAppSelector } from "../../ducks";
import OptionInput from "./OptionInput";
import Icon from "../common/Icon";

// The column picker in Options ▸ Appearance sets this one; a raw list of column names is a second, worse way to edit the same thing.
const HIDDEN_OPTIONS: Option[] = ["web_columns"];

function OptionHelp({ name }: { name: Option }) {
    const help = useAppSelector((state) => state.options_meta[name]?.help);
    return <div className="help-block text-small">{help}</div>;
}

function OptionError({ name }) {
    const error = useAppSelector((state) => state.options_meta[name]?.error);
    if (!error) return null;
    return <div className="text-small text-danger">{error}</div>;
}

export function PureOptionDefault({ value, defaultVal }) {
    if (value === defaultVal) {
        return null;
    } else {
        if (typeof defaultVal === "boolean") {
            defaultVal = defaultVal ? "true" : "false";
        } else if (Array.isArray(defaultVal)) {
            if (
                isEmpty(compact(value)) && // filter the empty string in array
                isEmpty(defaultVal)
            ) {
                return null;
            }
            defaultVal = "[ ]";
        } else if (defaultVal === "") {
            defaultVal = '""';
        } else if (defaultVal === null) {
            defaultVal = "null";
        }
        return (
            <div className="text-small">
                Default: <strong> {defaultVal} </strong>{" "}
            </div>
        );
    }
}

const OptionDefault = connect(
    (state: RootState, { name }: { name: Option }) => ({
        value: state.options[name],
        defaultVal: state.options_meta[name]?.default,
    }),
)(PureOptionDefault);

function matchesSearch(
    name: Option,
    help: string | undefined,
    terms: string[],
) {
    if (terms.length === 0) return true;
    const haystack = `${name} ${help ?? ""}`.toLowerCase();
    return terms.every((term) => haystack.includes(term));
}

type OptionSearchProps = {
    value: string;
    onChange: (value: string) => void;
};

function OptionSearch({ value, onChange }: OptionSearchProps) {
    const inputRef = useRef<HTMLInputElement>(null);

    const clear = () => {
        onChange("");
        inputRef.current?.focus();
    };

    const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
        // Clear an active search on Escape instead of closing the modal;
        // once empty, let Escape bubble up to the global handler to close it.
        if (e.key === "Escape") {
            if (value) {
                e.stopPropagation();
                clear();
            }
            return;
        }
        e.stopPropagation();
    };

    return (
        <div className="option-modal-search input-group" onKeyDown={onKeyDown}>
            <span className="input-group-addon">
                <Icon name="search" size={14} />
            </span>
            <input
                ref={inputRef}
                type="text"
                className="input"
                placeholder="Search options..."
                aria-label="Search options"
                value={value}
                autoFocus
                onChange={(e) => onChange(e.target.value)}
            />
            {value && (
                <button
                    type="button"
                    className="option-modal-search-clear"
                    aria-label="Clear search"
                    title="Clear search"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={clear}
                >
                    <Icon name="close" size={14} />
                </button>
            )}
        </div>
    );
}

export default function OptionModal() {
    const dispatch = useAppDispatch();
    const [query, setQuery] = useState("");
    const optionsMeta = useAppSelector((state) => state.options_meta);

    const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const options = (Object.keys(optionsMeta) as Option[])
        .filter(
            (name) =>
                !HIDDEN_OPTIONS.includes(name) &&
                matchesSearch(name, optionsMeta[name]?.help, terms),
        )
        .sort();

    return (
        <div>
            <div className="modal-header">
                <button
                    type="button"
                    className="close"
                    data-dismiss="modal"
                    onClick={() => dispatch(modalAction.hideModal())}
                >
                    <Icon name="close" />
                </button>
                <div className="modal-title">
                    <h4>Options</h4>
                </div>
                <OptionSearch value={query} onChange={setQuery} />
            </div>

            <div className="modal-body">
                {options.length > 0 ? (
                    <div className="form-horizontal">
                        {options.map((name) => (
                            <div key={name} className="form-row">
                                <div className="col-6">
                                    <label
                                        className="control-label"
                                        htmlFor={name}
                                    >
                                        {name}
                                    </label>
                                    <OptionHelp name={name} />
                                </div>
                                <div className="col-6">
                                    <OptionInput name={name} />
                                    <OptionError name={name} />
                                    <OptionDefault name={name} />
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="option-modal-empty text-muted">
                        No matching options.
                    </div>
                )}
            </div>

            <div className="modal-footer"></div>
        </div>
    );
}
