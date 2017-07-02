import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { update as updateOptions } from '../../ducks/options'

MenuToggle.propTypes = {
    value: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired,
    children: PropTypes.node.isRequired,
}

export function MenuToggle({ value, onChange, children }) {
    return (
        <div className="menu-entry">
            <label>
                <input type="checkbox"
                        checked={value}
                        onChange={onChange}/>
                {children}
            </label>
        </div>
    )
}

OptionsToggle.propTypes = {
    option: PropTypes.string.isRequired,
    children: PropTypes.node.isRequired,
}

export function OptionsToggle({ option, children, options, updateOptions }) {
    return (
        <MenuToggle
            value={ options[option].value }
            onChange={() => {console.log(options[option]);
                updateOptions({ [option]: !(options[option].value)}) }}
        >
            {children}
        </MenuToggle>
    )
}

OptionsToggle = connect(
    state => ({
        options: state.options,
    }),
    {
        updateOptions,
    }
)(OptionsToggle)
