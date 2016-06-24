import React, { PropTypes } from 'react'
import Button from '../common/Button'
import { FlowActions } from '../../actions.js'
import { MessageUtils } from '../../flow/utils.js'
import { connect } from 'react-redux'

FlowMenu.title = 'Flow'

FlowMenu.propTypes = {
    flow: PropTypes.object.isRequired,
}

function FlowMenu({ flow }) {

    return (
        <div>
            <div className="menu-row">
                <Button disabled={!flow.intercepted} title="[a]ccept intercepted flow" text="Accept" icon="fa-play" onClick={() => FlowActions.accept(flow)} />
                <Button title="[r]eplay flow" text="Replay" icon="fa-repeat" onClick={FlowActions.replay.bind(null, flow)} />
                <Button title="[D]uplicate flow" text="Duplicate" icon="fa-copy" onClick={FlowActions.duplicate.bind(null, flow)} />
                <Button title="[d]elete flow" text="Delete" icon="fa-trash" onClick={FlowActions.delete.bind(null, flow)}/>
                <Button disabled={!flow.modified} title="revert changes to flow [V]" text="Revert" icon="fa-history" onClick={() => FlowActions.revert(flow)} />
                <Button title="download" text="Download" icon="fa-download" onClick={() => window.location = MessageUtils.getContentURL(flow, flow.response)}/>
            </div>
            <div className="clearfix"/>
        </div>
    )
}

export default connect(
    state => ({
        flow: state.flows.list.byId[state.flows.views.main.selected[0]],
    })
)(FlowMenu)
