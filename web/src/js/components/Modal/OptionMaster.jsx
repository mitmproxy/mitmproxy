import PropTypes from 'prop-types'

PureBooleanOption.PropTypes = {
    value: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureBooleanOption({ value, onChange, name, help}) {
        return (
                <label>
                    { name }
                    <input type="checkbox"
                            checked={value}
                            onChange={onChange}
                            title={help}
                    />
                </label>
        )
}

PureStringOption.PropTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureStringOption( { value, onChange, name, help }) {
    let onKeyDown = (e) => {e.stopPropagation()}
    return (
            <label>
                { name }
                <input type="text"
                        value={value}
                        onChange={onChange}
                        title={help}
                        onKeyDown={onKeyDown}
                />
            </label>
    )
}

PureNumberOption.PropTypes = {
    value: PropTypes.number.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureNumberOption( {value, onChange, name, help }) {
    let onKeyDown = (e) => {e.stopPropagation()}
    return (
            <label>
                { name }
                <input type="number"
                        value={value}
                        onChange={onChange}
                        title={help}
                        onKeyDown={onKeyDown}
                />
            </label>
    )
}

PureChoicesOption.PropTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
}

function PureChoicesOption( { value, onChange, name, help, choices }) {
    return (
            <label htmlFor="">
                { name }
                <select name={name} onChange={onChange} title={help} selected={value}>
                    { choices.map((choice, index) => (
                        <option key={index} value={choice}> {choice} </option>
                    ))}
                </select>
            </label>
    )
}

const OptionTypes = {
    bool: PureBooleanOption,
    str: PureStringOption,
    int: PureNumberOption,
    "optional str": PureStringOption,
    "sequence of str": PureStringOption,
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
        <div className="menu-entry">
            <WrappedComponent
                children={props.children}
                value={option.value}
                onChange={onChange}
                name={name}
                help={option.help}
                choices={option.choices}
            />
        </div>
    )
}
