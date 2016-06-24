import React, { PropTypes } from 'react'
import { connect } from 'react-redux'
import Button from '../common/Button'
import { MessageUtils } from '../../flow/utils.js'
import * as flowsActions from '../../ducks/flows'

FlowMenu.title = 'Flow'

FlowMenu.propTypes = {
    flow: PropTypes.object.isRequired,
}

function FlowMenu({ flow, onAccept, onReplay, onDuplicate, onRemove, onRevert }) {

    return (
        <div>
            <div className="menu-row">
                <Button disabled={!flow.intercepted} title="[a]ccept intercepted flow" text="Accept" icon="fa-play" onClick={() => onAccept(flow)} />
                <Button title="[r]eplay flow" text="Replay" icon="fa-repeat" onClick={() => onReplay(flow)} />
                <Button title="[D]uplicate flow" text="Duplicate" icon="fa-copy" onClick={() => onDuplicate(flow)} />
                <Button title="[d]elete flow" text="Delete" icon="fa-trash" onClick={() => onRemove(flow)}/>
                <Button disabled={!flow.modified} title="revert changes to flow [V]" text="Revert" icon="fa-history" onClick={() => onRevert(flow)} />
                <Button title="download" text="Download" icon="fa-download" onClick={() => window.location = MessageUtils.getContentURL(flow, flow.response)}/>
            </div>
            <div className="clearfix"/>
        </div>
    )
}

export default connect(
    state => ({
        flow: state.flows.list.byId[state.flows.views.main.selected[0]],
    }),
    {
        onAccept: flowsActions.accept,
        onReplay: flowsActions.replay,
        onDuplicate: flowsActions.duplicate,
        onRemove: flowsActions.remove,
        onRevert: flowsActions.revert,
    }
)(FlowMenu)
