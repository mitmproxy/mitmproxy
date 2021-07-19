import React  from 'react'
import classnames from 'classnames'
import _ from 'lodash'

type NavActionProps = {
    icon: string,
    title: string,
    onClick: (e: any) => void,
}

export function NavAction({ icon, title, onClick }: NavActionProps) {
    return (
        <a title={title}
            href="#"
            className="nav-action"
            onClick={event => {
                event.preventDefault()
                onClick(event)
            }}>
            <i className={`fa fa-fw ${icon}`}></i>
        </a>
    )
}

type NavProps = {
    active: string,
    tabs: string[],
    onSelectTab: (e: string) => void,
}

export default function Nav({ active, tabs, onSelectTab }: NavProps) {
    return (
        <nav className="nav-tabs nav-tabs-sm">
            {tabs.map(tab => (
                <a key={tab}
                    href="#"
                    className={classnames({ active: active === tab })}
                    onClick={event => {
                        event.preventDefault()
                        onSelectTab(tab)
                    }}>
                    {_.capitalize(tab)}
                </a>
            ))}
        </nav>
    )
}
