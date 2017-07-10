import React, { Component } from 'react'
import PropTypes from 'prop-types'

PureBooleanOption.PropTypes = {
    value: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureBooleanOption({ value, onChange, ...props}) {
        let onFocus = () => { props.onFocus() },
            onBlur = () => { props.onBlur() },
            onMouseEnter = () => { props.onMouseEnter() },
            onMouseLeave = () => { props.onMouseLeave() }
        return (
                <input type="checkbox"
                        checked={value}
                        onChange={onChange}
                        onFocus={onFocus}
                        onBlur={onBlur}
                        onMouseOver={onMouseEnter}
                        onMouseLeave={onMouseLeave}
                />
        )
}

PureStringOption.PropTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureStringOption( { value, onChange, ...props }) {
    let onKeyDown = (e) => {e.stopPropagation()},
        onFocus = () => { props.onFocus() },
        onBlur = () => { props.onBlur() },
        onMouseEnter = () => { props.onMouseEnter() },
        onMouseLeave = () => { props.onMouseLeave() }
    return (
            <input type="text"
                    value={value}
                    onChange={onChange}
                    onKeyDown={onKeyDown}
                    onFocus={onFocus}
                    onBlur={onBlur}
                    onMouseOver={onMouseEnter}
                    onMouseLeave={onMouseLeave}
            />
    )
}

PureNumberOption.PropTypes = {
    value: PropTypes.number.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureNumberOption( {value, onChange, ...props }) {
    let onKeyDown = (e) => {e.stopPropagation()},
        onFocus = () => { props.onFocus() },
        onBlur = () => { props.onBlur() },
        onMouseEnter = () => { props.onMouseEnter() },
        onMouseLeave = () => { props.onMouseLeave() }

    return (
            <input type="number"
                    value={value}
                    onChange={onChange}
                    onKeyDown={onKeyDown}
                    onFocus={onFocus}
                    onBlur={onBlur}
                    onMouseOver={onMouseEnter}
                    onMouseLeave={onMouseLeave}
            />
    )
}

PureChoicesOption.PropTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureChoicesOption( { value, onChange, name, choices, ...props}) {
    let onFocus = () => { props.onFocus() },
        onBlur = () => { props.onBlur() },
        onMouseEnter = () => { props.onMouseEnter() },
        onMouseLeave = () => { props.onMouseLeave() }
    return (
            <select
                name={name}
                onChange={onChange}
                selected={value}
                onFocus={onFocus}
                onBlur={onBlur}
                onMouseOver={onMouseEnter}
                onMouseLeave={onMouseLeave}
            >
                { choices.map((choice, index) => (
                    <option key={index} value={choice}> {choice} </option>
                ))}
            </select>
    )
}

class PureStringSequenceOption extends Component {
    constructor(props, context) {
        super(props, context)
        this.state = { height: 1, focus: false, value: this.props.value}

        this.onFocus = this.onFocus.bind(this)
        this.onBlur = this.onBlur.bind(this)
        this.onKeyDown = this.onKeyDown.bind(this)
        this.onChange = this.onChange.bind(this)
    }

    onFocus() {
        this.setState( {focus: true, height: 3 })
        this.props.onFocus()
    }

    onBlur() {
        this.setState( {focus: false, height: 1})
        this.props.onBlur()
    }

    onKeyDown(e) {
        e.stopPropagation()
    }

    onChange(e) {
        const value = e.target.value.split("\n")
        console.log(value)
        this.props.onChange(e)
        this.setState({ value })
    }

    render() {
        const {height, value} = this.state
        return (
            <textarea
                rows={height}
                value={value}
                onChange={this.onChange}
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

export default class OptionMaster extends Component {

    constructor(props, context) {
        super(props, context)
        this.state = {
                updateOptions: this.props.updateOptions,
                option: this.props.option,
                name: this.props.name,
                mousefocus: false,
                focus: false,

        }
        if (props.option.choices) {
            this.WrappedComponent = PureChoicesOption
        } else {
            this.WrappedComponent = OptionTypes[props.option.type]
        }
        this.onChange = this.onChange.bind(this)
        this.onMouseEnter = this.onMouseEnter.bind(this)
        this.onMouseLeave = this.onMouseLeave.bind(this)
        this.onFocus = this.onFocus.bind(this)
        this.onBlur = this.onBlur.bind(this)
    }

    componentWillReceiveProps(nextProps) {
        this.setState({ option: nextProps.option })
    }

    onChange(e) {
        const { updateOptions, option, name } = this.state
        switch (option.type) {
            case 'bool' :
                updateOptions({[name]: !option.value})
                break
            case 'int':
                updateOptions({[name]: parseInt(e.target.value)})
                break
            case 'sequence of str':
                const value = e.target.value.split('\n')
                updateOptions({[name]: value})
                break
            default:
                updateOptions({[name]: e.target.value})
        }
    }

    onMouseEnter() {
        console.log(this.state)
        this.setState({ mousefocus: true })
    }

    onMouseLeave() {
        this.setState({ mousefocus: false })
    }

    onFocus() {
        console.log(this.state)
        this.setState({ focus: true })
    }

    onBlur() {
        this.setState({ focus: false })
    }

    render() {
        const { name, children } = this.props
        const { option, focus, mousefocus } = this.state
        const WrappedComponent = this.WrappedComponent
        return (
            <div className="row">
                <div className="col-sm-8">
                    {name}
                </div>
                <div className="col-sm-4">
                    <WrappedComponent
                        children={children}
                        value={option.value}
                        onChange={this.onChange}
                        name={name}
                        choices={option.choices}
                        onFocus={this.onFocus}
                        onBlur={this.onBlur}
                        onMouseEnter={this.onMouseEnter}
                        onMouseLeave={this.onMouseLeave}
                    />
                    {(focus || mousefocus) && (
                        <div className="tooltip tooltip-bottom" role="tooltip" style={{opacity: 1}}>
                        <div className="tooltip-inner">
                            {option.help}
                        </div>
                    </div>)}
                </div>
            </div>
        )
    }
}
