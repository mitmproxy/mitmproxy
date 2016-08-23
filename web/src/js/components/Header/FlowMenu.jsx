import React, { PropTypes } from 'react'
import { connect } from 'react-redux'
import Button from '../common/Button'
import { MessageUtils } from '../../flow/utils.js'
import * as flowsActions from '../../ducks/flows'

FlowMenu.title = 'Flow'

FlowMenu.propTypes = {
    flow: PropTypes.object.isRequired,
    acceptFlow: PropTypes.func.isRequired,
    replayFlow: PropTypes.func.isRequired,
    duplicateFlow: PropTypes.func.isRequired,
    removeFlow: PropTypes.func.isRequired,
    revertFlow: PropTypes.func.isRequired
}

function FlowMenu({ flow, acceptFlow, replayFlow, duplicateFlow, removeFlow, revertFlow }) {
    return (
        <div>
            <div className="menu-row">
                <Button disabled={!flow || !flow.intercepted} title="[a]ccept intercepted flow" text="Accept" icon="fa-play" onClick={() => acceptFlow(flow)} />
                <Button title="[r]eplay flow" text="Replay" icon="fa-repeat" onClick={() => replayFlow(flow)} />
                <Button title="[D]uplicate flow" text="Duplicate" icon="fa-copy" onClick={() => duplicateFlow(flow)} />
                <Button title="[d]elete flow" text="Delete" icon="fa-trash" onClick={() => removeFlow(flow)}/>
                <Button disabled={!flow || !flow.modified} title="revert changes to flow [V]" text="Revert" icon="fa-history" onClick={() => revertFlow(flow)} />
                <Button title="download" text="Download" icon="fa-download" onClick={() => window.location = MessageUtils.getContentURL(flow, flow.response)}/>
            </div>
            <div className="clearfix"/>
        </div>
    )
}

export default connect(
    state => ({
        flow: state.flows.byId[state.flows.selected[0]],
    }),
    {
        acceptFlow: flowsActions.accept,
        replayFlow: flowsActions.replay,
        duplicateFlow: flowsActions.duplicate,
        removeFlow: flowsActions.remove,
        revertFlow: flowsActions.revert,
    }
)(FlowMenu)
