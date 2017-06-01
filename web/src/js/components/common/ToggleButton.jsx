import React  from 'react'
import PropTypes from 'prop-types'

ToggleButton.propTypes = {
    checked: PropTypes.bool.isRequired,
    onToggle: PropTypes.func.isRequired,
    text: PropTypes.string.isRequired
}

export default function ToggleButton({ checked, onToggle, text }) {
    return (
        <div className={"btn btn-toggle " + (checked ? "btn-primary" : "btn-default")} onClick={onToggle}>
            <i className={"fa fa-fw " + (checked ? "fa-check-square-o" : "fa-square-o")}/>
            &nbsp;
            {text}
        </div>
    )
}
