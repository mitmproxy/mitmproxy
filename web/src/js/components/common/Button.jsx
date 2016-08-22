import React, { PropTypes } from 'react'
import classnames from 'classnames'

Button.propTypes = {
    onClick: PropTypes.func.isRequired,
    text: PropTypes.string,
    icon: PropTypes.string
}

export default function Button({ onClick, text, icon, disabled, className }) {
    return (
        <div className={classnames(className, 'btn btn-default')}
             onClick={onClick}
             disabled={disabled}>
            {icon && (<i className={"fa fa-fw " + icon}/> )}
            {text && text}
        </div>
    )
}
