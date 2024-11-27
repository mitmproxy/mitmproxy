/* eslint-disable react/prop-types */
import React from "react";
import { connect, shallowEqual } from "react-redux";
import * as modalAction from "../../ducks/ui/modal";
import { Option } from "../../ducks/options";
import { compact, isEmpty } from "lodash";
import { RootState, useAppDispatch, useAppSelector } from "../../ducks";
import OptionInput from "./OptionInput";

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
