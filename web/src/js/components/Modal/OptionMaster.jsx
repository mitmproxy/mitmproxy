import React, { Component } from 'react'
import PropTypes from 'prop-types'

PureBooleanOption.PropTypes = {
    value: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureBooleanOption({ value, onChange, help}) {
        return (
                <input type="checkbox"
                        checked={value}
                        onChange={onChange}
                        title={help}
                />
        )
}

PureStringOption.PropTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureStringOption( { value, onChange, help }) {
    let onKeyDown = (e) => {e.stopPropagation()}
    return (
            <input type="text"
                    value={value}
                    onChange={onChange}
                    title={help}
                    onKeyDown={onKeyDown}
            />
    )
}

PureNumberOption.PropTypes = {
    value: PropTypes.number.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureNumberOption( {value, onChange, help }) {
    let onKeyDown = (e) => {e.stopPropagation()}
    return (
            <input type="number"
                    value={value}
                    onChange={onChange}
                    title={help}
                    onKeyDown={onKeyDown}
            />
    )
}

PureChoicesOption.PropTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureChoicesOption( { value, onChange, name, help, choices }) {
    return (
            <select name={name} onChange={onChange} title={help} selected={value}>
                { choices.map((choice, index) => (
                    <option key={index} value={choice}> {choice} </option>
                ))}
            </select>
    )
}

class PureStringSequenceOption extends Component {
    constructor(props, context) {
        super(props, context)
        this.state = { height: 1, focus: false }

        this.onFocus = this.onFocus.bind(this)
        this.onBlur = this.onBlur.bind(this)
        this.onKeyDown = this.onKeyDown.bind(this)
    }

    onFocus() {
        this.setState( {focus: true, height: 3 })
    }

    onBlur() {
        this.setState( {focus: false, height: 1})
    }

    onKeyDown(e) {
        e.stopPropagation()
    }

    render() {
        const {value, onChange, help} = this.props
        const {height, focus} = this.state
        return (
            <textarea
                rows={height}
                value={value}
                onChange={onChange}
                title={help}
                onKeyDown={this.onKeyDown}
                onFocus={this.onFocus}
                onBlur={this.onBlur}
            />
        )
    }
}

const OptionTypes = {
    bool: PureBooleanOption,
    str: PureStringOption,
    int: PureNumberOption,
    "optional str": PureStringOption,
    "sequence of str": PureStringSequenceOption,
}

export default function OptionMaster({option, name, updateOptions, ...props}) {
    let WrappedComponent = null
    if (option.choices) {
        WrappedComponent = PureChoicesOption
    } else {
        WrappedComponent = OptionTypes[option.type]
    }

    let onChange = (e) => {
        switch (option.type) {
            case 'bool' :
                updateOptions({[name]: !option.value})
                break
            case 'int':
                updateOptions({[name]: parseInt(e.target.value)})
                break
            default:
                updateOptions({[name]: e.target.value})
        }
    }
    return (
        <div className="row">
            <div className="col-sm-8">
                {name}
            </div>
            <div className="col-sm-4">
                <WrappedComponent
                    children={props.children}
                    value={option.value}
                    onChange={onChange}
                    name={name}
                    help={option.help}
                    choices={option.choices}
                />
            </div>
        </div>
    )
}
