import React from "react"
import classnames from "classnames"

type ButtonProps = {
    onClick: () => void,
    children?: React.ReactNode,
    icon?: string,
    disabled?: boolean,
    className?: string,
    title?: string,
}

export default function Button({ onClick, children, icon, disabled, className, title }: ButtonProps) {
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
