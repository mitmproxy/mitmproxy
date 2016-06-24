import React, { PropTypes } from 'react'
import { connect } from 'react-redux'
import classnames from 'classnames'
import * as flowsActions from '../../ducks/flows'

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
    onRemove: PropTypes.func.isRequired,
    onDuplicate: PropTypes.func.isRequired,
    onReplay: PropTypes.func.isRequired,
    onAccept: PropTypes.func.isRequired,
    onRevert: PropTypes.func.isRequired,
}

function Nav({ flow, active, tabs, onSelectTab, onRemove, onDuplicate, onReplay, onAccept, onRevert }) {
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
            <NavAction title="[d]elete flow" icon="fa-trash" onClick={() => onRemove(flow)} />
            <NavAction title="[D]uplicate flow" icon="fa-copy" onClick={() => onDuplicate(flow)} />
            <NavAction disabled title="[r]eplay flow" icon="fa-repeat" onClick={() => onReplay(flow)} />
            {flow.intercepted && (
                <NavAction title="[a]ccept intercepted flow" icon="fa-play" onClick={() => onAccept(flow)} />
            )}
            {flow.modified && (
                <NavAction title="revert changes to flow [V]" icon="fa-history" onClick={() => onRevert(flow)} />
            )}
        </nav>
    )
}

export default connect(
    null,
    {
        onRemove: flowsActions.remove,
        onDuplicate: flowsActions.duplicate,
        onReplay: flowsActions.replay,
        onAccept: flowsActions.accept,
        onRevert: flowsActions.revert,
    }
)(Nav)
