import React, { PropTypes } from 'react'
import classnames from 'classnames'
import { FlowActions } from '../../actions.js'

NavAction.propTypes = {
    icon: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    onClick: PropTypes.func.isRequired,
}

function NavAction({ icon, title, onClick }) {
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
    flow: PropTypes.object.isRequired,
    active: PropTypes.string.isRequired,
    tabs: PropTypes.array.isRequired,
    onSelectTab: PropTypes.func.isRequired,
}

export default function Nav({ flow, active, tabs, onSelectTab }) {
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
            <NavAction title="[d]elete flow" icon="fa-trash" onClick={() => FlowActions.delete(flow)} />
            <NavAction title="[D]uplicate flow" icon="fa-copy" onClick={() => FlowActions.duplicate(flow)} />
            <NavAction disabled title="[r]eplay flow" icon="fa-repeat" onClick={() => FlowActions.replay(flow)} />
            {flow.intercepted && (
                <NavAction title="[a]ccept intercepted flow" icon="fa-play" onClick={() => FlowActions.accept(flow)} />
            )}
            {flow.modified && (
                <NavAction title="revert changes to flow [V]" icon="fa-history" onClick={() => FlowActions.revert(flow)} />
            )}
        </nav>
    )
}
