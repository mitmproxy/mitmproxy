import React, { Component } from "react"
import PropTypes from "prop-types"
import { connect } from "react-redux"
import { update as updateOptions } from "../../ducks/options"
import { Key } from "../../utils"

const stopPropagation = e => {
    if (e.keyCode !== Key.ESC) {
        e.stopPropagation()
    }
}

BooleanOption.PropTypes = {
    value: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired,
}
function BooleanOption({ value, onChange, ...props }) {
    return (
        <input type="checkbox"
               checked={value}
               onChange={e => onChange(e.target.checked)}
               {...props}
        />
    )
}

StringOption.PropTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
}
function StringOption({ value, onChange, ...props }) {
    return (
        <input type="text"
               value={value || ""}
               onChange={e => onChange(e.target.value)}
               {...props}
        />
    )
}

NumberOption.PropTypes = {
    value: PropTypes.number.isRequired,
    onChange: PropTypes.func.isRequired,
}
function NumberOption({ value, onChange, ...props }) {
    return (
        <input type="number"
               value={value}
               onChange={(e) => onChange(parseInt(e.target.value))}
               {...props}
        />
    )
}

ChoicesOption.PropTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
}
function ChoicesOption({ value, onChange, choices, ...props }) {
    return (
        <select
            onChange={(e) => onChange(e.target.value)}
            selected={value}
            {...props}
        >
            { choices.map(
                choice => (
                    <option key={choice} value={choice}>{choice}</option>
                )
            )}
        </select>
    )
}

StringSequenceOption.PropTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
}
function StringSequenceOption({ value, onChange, ...props }) {
    const height = Math.max(value.length, 1)
    return <textarea
        rows={height}
        value={value.join("\n")}
        onChange={e => onChange(e.target.value.split("\n"))}
        {...props}
    />
}

const Options = {
    "bool": BooleanOption,
    "str": StringOption,
    "int": NumberOption,
    "optional str": StringOption,
    "sequence of str": StringSequenceOption,
}

function PureOption({ choices, type, value, onChange }) {
    if (choices) {
        return <ChoicesOption
            value={value}
            onChange={onChange}
            choices={choices}
            onKeyDown={stopPropagation}
        />
    }
    const Opt = Options[type]
    return <Opt
        value={value}
        onChange={onChange}
        onKeyDown={stopPropagation}
    />
}
export default connect(
    (state, { name }) => ({
        ...state.options[name],
        ...state.ui.optionsEditor[name]
    }),
    (dispatch, { name }) => ({
        onChange: value => dispatch(updateOptions(name, value))
    })
)(PureOption)
