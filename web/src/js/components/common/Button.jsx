import React, { PropTypes } from 'react'

Button.propTypes = {
    onClick: PropTypes.func.isRequired,
    text: PropTypes.string,
    icon: PropTypes.string
}

export default function Button({ onClick, text, icon, disabled }) {
    return (
        <div className={"btn btn-default"}
             onClick={onClick}
             disabled={disabled}>
            {icon && (<i className={"fa fa-fw " + icon}/> )}
            {text && text}
        </div>
    )
}
