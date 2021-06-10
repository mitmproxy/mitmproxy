import React from "react"
import PropTypes from 'prop-types'
import classnames from "classnames"

Button.propTypes = {
    onClick: PropTypes.func.isRequired,
    children: PropTypes.node,
    icon: PropTypes.string,
    title: PropTypes.string,
}

export default function Button({ onClick, children, icon, disabled, className, title }) {
    return (
        <button className={classnames(className, 'btn btn-default')}
             onClick={disabled ? undefined : onClick}
             disabled={disabled}
             title={title}>
            {icon && (<i className={"fa fa-fw " + icon}/> )}
            {children}
        </button>
    )
}
