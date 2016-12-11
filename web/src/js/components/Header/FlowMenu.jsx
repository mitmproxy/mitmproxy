import React, { PropTypes } from "react"
import { connect } from "react-redux"
import Button from "../common/Button"
import { MessageUtils } from "../../flow/utils.js"
import * as flowsActions from "../../ducks/flows"

FlowMenu.title = 'Flow'

FlowMenu.propTypes = {
    flow: PropTypes.object,
    acceptFlow: PropTypes.func.isRequired,
    replayFlow: PropTypes.func.isRequired,
    duplicateFlow: PropTypes.func.isRequired,
    removeFlow: PropTypes.func.isRequired,
    revertFlow: PropTypes.func.isRequired
}

function FlowMenu({ flow, acceptFlow, replayFlow, duplicateFlow, removeFlow, revertFlow }) {
    if (!flow)
        return <div/>
    return (
        <div>
            <div className="menu-group">
                <div className="menu-content">
                    <Button title="[r]eplay flow" icon="fa-repeat text-primary" onClick={() => replayFlow(flow)}>
                        Replay
                    </Button>
                    <Button title="[D]uplicate flow" icon="fa-copy text-info"
                            onClick={() => duplicateFlow(flow)}>
                        Duplicate
                    </Button>
                    <Button disabled={!flow || !flow.modified} title="revert changes to flow [V]"
                            icon="fa-history text-warning" onClick={() => revertFlow(flow)}>
                        Revert
                    </Button>
                    <Button title="[d]elete flow" icon="fa-trash text-danger" onClick={() => removeFlow(flow)}>
                        Delete
                    </Button>
                </div>
                <div className="menu-legend">Flow Modification</div>
            </div>
            <div className="menu-group">
                <div className="menu-content">
                    <Button title="download" icon="fa-download"
                            onClick={() => window.location = MessageUtils.getContentURL(flow, flow.response)}>
                        Download
                    </Button>
                </div>
                <div className="menu-legend">Export</div>
            </div>
            <div className="menu-group">
                <div className="menu-content">
                    <Button disabled={!flow || !flow.intercepted} title="[a]ccept intercepted flow"
                    icon="fa-play text-success" onClick={() => acceptFlow(flow)}
                    >
                Resume
            </Button>

                </div>
                <div className="menu-legend">Interception</div>
            </div>



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
