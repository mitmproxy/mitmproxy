import React  from "react"
import PropTypes from 'prop-types'
import { connect } from "react-redux"
import Button from "../common/Button"
import { MessageUtils } from "../../flow/utils.js"
import * as flowsActions from "../../ducks/flows"
import HideInStatic from "../common/HideInStatic";

FlowMenu.title = 'Flow'

FlowMenu.propTypes = {
    flow: PropTypes.object,
    resumeFlow: PropTypes.func.isRequired,
    killFlow: PropTypes.func.isRequired,
    replayFlow: PropTypes.func.isRequired,
    duplicateFlow: PropTypes.func.isRequired,
    removeFlow: PropTypes.func.isRequired,
    revertFlow: PropTypes.func.isRequired
}

export function FlowMenu({ flow, resumeFlow, killFlow, replayFlow, duplicateFlow, removeFlow, revertFlow }) {
    if (!flow)
        return <div/>
    return (
        <div className="flow-menu">
            <HideInStatic>
            <div className="menu-group">
                <div className="menu-content">
                    <Button title="[r]eplay flow" icon="fa-repeat text-primary"
                            onClick={() => replayFlow(flow)}>
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
                    <Button title="[d]elete flow" icon="fa-trash text-danger"
                            onClick={() => removeFlow(flow)}>
                        Delete
                    </Button>
                </div>
                <div className="menu-legend">Flow Modification</div>
            </div>
            </HideInStatic>

            <div className="menu-group">
                <div className="menu-content">
                    <Button title="download" icon="fa-download"
                            onClick={() => window.location = MessageUtils.getContentURL(flow, flow.response)}>
                        Download
                    </Button>
                </div>
                <div className="menu-legend">Export</div>
            </div>

            <HideInStatic>
            <div className="menu-group">
                <div className="menu-content">
                    <Button disabled={!flow || !flow.intercepted} title="[a]ccept intercepted flow"
                            icon="fa-play text-success" onClick={() => resumeFlow(flow)}>
                        Resume
                    </Button>
                    <Button disabled={!flow || !flow.intercepted} title="kill intercepted flow [x]"
                            icon="fa-times text-danger" onClick={() => killFlow(flow)}>
                        Abort
                    </Button>
                </div>
                <div className="menu-legend">Interception</div>
            </div>
            </HideInStatic>
        </div>
    )
}

export default connect(
    state => ({
        flow: state.flows.byId[state.flows.selected[0]],
    }),
    {
        resumeFlow: flowsActions.resume,
        killFlow: flowsActions.kill,
        replayFlow: flowsActions.replay,
        duplicateFlow: flowsActions.duplicate,
        removeFlow: flowsActions.remove,
        revertFlow: flowsActions.revert,
    }
)(FlowMenu)
