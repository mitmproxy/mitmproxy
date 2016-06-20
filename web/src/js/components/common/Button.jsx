import React, { PropTypes } from 'react'

Button.propTypes = {
    onClick: PropTypes.func.isRequired,
    text: PropTypes.string.isRequired
}

export default function Button({ onClick, text, icon, disabled }) {
    return (
        <div className={"btn btn-default"}
             onClick={onClick}
             disabled={disabled}>
            <i className={"fa fa-fw " + icon}/>
            &nbsp;
            {text}
        </div>
    )
}
