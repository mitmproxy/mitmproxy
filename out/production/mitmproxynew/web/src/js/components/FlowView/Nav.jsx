import React  from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import classnames from 'classnames'
import _ from 'lodash'

NavAction.propTypes = {
    icon: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    onClick: PropTypes.func.isRequired,
}

export function NavAction({ icon, title, onClick }) {
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

Nav.propTypes = {
    active: PropTypes.string.isRequired,
    tabs: PropTypes.array.isRequired,
    onSelectTab: PropTypes.func.isRequired,
}

export default function Nav({ active, tabs, onSelectTab }) {
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
