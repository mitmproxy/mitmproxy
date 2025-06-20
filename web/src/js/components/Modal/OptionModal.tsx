/* eslint-disable react/prop-types */
import React from "react";
import { connect, shallowEqual } from "react-redux";
import * as modalAction from "../../ducks/ui/modal";
import { Option } from "../../ducks/options";
import { compact, isEmpty } from "lodash";
import { RootState, useAppDispatch, useAppSelector } from "../../ducks";
import OptionInput from "./OptionInput";
import { setTimezoneDisplay } from "../../ducks/ui"; // Added this import
import { selectTimezoneDisplay } from "../../ducks/ui"; // Added this import

function OptionHelp({ name }: { name: Option }) {
    const help = useAppSelector((state) => state.options_meta[name]?.help);
    return <div className="help-block small">{help}</div>;
}

function OptionError({ name }) {
    const error = useAppSelector((state) => state.options_meta[name]?.error);
    if (!error) return null;
    return <div className="small text-danger">{error}</div>;
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
            <div className="small">
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

export default function OptionModal() {
    const dispatch = useAppDispatch();
    const options = useAppSelector(
        (state) => Object.keys(state.options_meta),
        shallowEqual,
    ).sort() as Option[];
    // Get current timezone setting
    const timezoneDisplay = useAppSelector(selectTimezoneDisplay);

    // Handle timezone change
    const handleTimezoneChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const value = e.target.value as "utc" | "local";
        dispatch(setTimezoneDisplay(value));
    };

    return (
        <div>
            <div className="modal-header">
                <button
                    type="button"
                    className="close"
                    data-dismiss="modal"
                    onClick={() => dispatch(modalAction.hideModal())}
                >
                    <i className="fa fa-fw fa-times"></i>
                </button>
                <div className="modal-title">
                    <h4>Options</h4>
                </div>
            </div>

            <div className="modal-body">
                {/* Add frontend preferences section */}
                <div className="form-group">
                    <div className="col-xs-6">
                        <label>Timestamp Display</label>
                        <div className="help-block small">
                            Choose between UTC or local time for timestamps
                        </div>
                    </div>
                    <div className="col-xs-6">
                        <select
                            value={timezoneDisplay}
                            onChange={handleTimezoneChange}
                            className="form-control"
                        >
                            <option value="utc">UTC</option>
                            <option value="local">Local Timezone</option>
                        </select>
                    </div>
                </div>

                <hr style={{ margin: "15px 0" }} />

                <div className="form-horizontal">
                    {options.map((name) => (
                        <div key={name} className="form-group">
                            <div className="col-xs-6">
                                <label htmlFor={name}>{name}</label>
                                <OptionHelp name={name} />
                            </div>
                            <div className="col-xs-6">
                                <OptionInput name={name} />
                                <OptionError name={name} />
                                <OptionDefault name={name} />
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="modal-footer"></div>
        </div>
    );
}
