import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { update as updateOptions } from '../../ducks/options'

PureBooleanOption.PropTypes = {
    value: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureBooleanOption({ value, onChange, name, help}) {
        return (
            <div className="menu-entry">
                <label>
                    <input type="checkbox"
                            checked={value}
                            onChange={onChange}
                            title={help}
                    />
                    { name }
                </label>
            </div>
        )
}

PureStringOption.PropTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureStringOption( { value, onChange, name, help }) {
    let onKeyDown = (e) => {e.stopPropagation()}
    return (
        <div className="menu-entry">
            <label>
                { name }
                <input type="text"
                        value={value}
                        onChange={onChange}
                        title={help}
                        onKeyDown={onKeyDown}
                />
            </label>
        </div>
    )
}

PureNumberOption.PropTypes = {
    value: PropTypes.number.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureNumberOption( {value, onChange, name, help }) {
    let onKeyDown = (e) => {e.stopPropagation()}
    return (
        <div className="menu-entry">
            <label>
                { name }
                <input type="number"
                        value={value}
                        onChange={onChange}
                        title={help}
                        onKeyDown={onKeyDown}
                />
            </label>
        </div>
    )
}

PureChoicesOption.PropTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureChoicesOption( { value, onChange, name, help, choices }) {
    return (
        <div className="menu-entry">
            <label htmlFor="">
                { name }
                <select name={name} onChange={onChange} title={help} selected={value}>
                    { choices.map(choice => (
                        <option value={choice}> {choice} </option>
                    ))}
                </select>
            </label>
        </div>
    )
}

const OptionTypes = {
    bool: PureBooleanOption,
    str: PureStringOption,
    int: PureNumberOption,
    "optional str": PureStringOption,
    "sequence of str": PureStringOption,
}

Wrapper.displayName = 'OptionWrapper'


function Wrapper({option, options, updateOptions, ...props}) {
    let optionObj = options[option],
        WrappedComponent = null
    if (optionObj.choices) {
        WrappedComponent = PureChoicesOption
    } else {
        WrappedComponent = OptionTypes[optionObj.type]
    }

    let onChange = (e) => {
        switch (optionObj.type) {
            case 'bool' :
                updateOptions({[option]: !optionObj.value})
                break
            case 'int':
                updateOptions({[option]: parseInt(e.target.value)})
                break
            default:
                updateOptions({[option]: e.target.value})
        }
    }
    return <WrappedComponent
        children={props.children}
        value={optionObj.value}
        onChange={onChange}
        name={option}
        help={optionObj.help}
        choices={optionObj.choices}
    />
}

export default connect(
    state => ({
        options: state.options,
    }),
    {
        updateOptions,
    }
)(Wrapper)
