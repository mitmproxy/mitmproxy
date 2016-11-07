import { connect } from 'react-redux'
import { ContextMenu, MenuItem } from 'react-contextmenu'
import * as flowsActions from '../ducks/flows'
import { MessageUtils } from '../flow/utils.js'

function FlowContextMenu({ flow, accept, replay, duplicate, remove, revert }) {
    return (
        <ContextMenu identifier="flow-table-context-menu">
            <MenuItem disabled={!flow.intercepted} onClick={() => accept(flow)}>Accept</MenuItem>
            <MenuItem onClick={() => replay(flow)}>Replay</MenuItem>
            <MenuItem onClick={() => duplicate(flow)}>Duplicate</MenuItem>
            <MenuItem onClick={() => remove(flow)}>Delete</MenuItem>
            <MenuItem onClick={() => revert(flow)}>Revert</MenuItem>
            <MenuItem disabled={!flow.modified} onClick={() => window.location = MessageUtils.getContentURL(flow, flow.response)}>Download</MenuItem>
        </ContextMenu>
    )
}

export default connect(
    state => ({}),
    flowsActions
)(FlowContextMenu)
