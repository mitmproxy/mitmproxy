import React  from "react"
import Button from "../common/Button"
import { MessageUtils } from "../../flow/utils.js"
import HideInStatic from "../common/HideInStatic";
import { useAppDispatch, useAppSelector } from "../../ducks";
import {
    resume as resumeFlow,
    replay as replayFlow,
    duplicate as duplicateFlow,
    revert as revertFlow,
    remove as removeFlow,
    kill as killFlow
} from "../../ducks/flows"

FlowMenu.title = 'Flow'

export default function FlowMenu() {
    const dispatch = useAppDispatch(),
    flow = useAppSelector(state => state.flows.byId[state.flows.selected[0]])

    if (!flow)
        return <div/>
    return (
        <div className="flow-menu">
            <HideInStatic>
            <div className="menu-group">
                <div className="menu-content">
                    <Button title="[r]eplay flow" icon="fa-repeat text-primary"
                            onClick={() => dispatch(replayFlow(flow))}>
                        Replay
                    </Button>
                    <Button title="[D]uplicate flow" icon="fa-copy text-info"
                            onClick={() => dispatch(duplicateFlow(flow))}>
                        Duplicate
                    </Button>
                    <Button disabled={!flow || !flow.modified} title="revert changes to flow [V]"
                            icon="fa-history text-warning" onClick={() => dispatch(revertFlow(flow))}>
                        Revert
                    </Button>
                    <Button title="[d]elete flow" icon="fa-trash text-danger"
                            onClick={() => dispatch(removeFlow(flow))}>
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
                            icon="fa-play text-success" onClick={() => dispatch(resumeFlow(flow))}>
                        Resume
                    </Button>
                    <Button disabled={!flow || !flow.intercepted} title="kill intercepted flow [x]"
                            icon="fa-times text-danger" onClick={() => dispatch(killFlow(flow))}>
                        Abort
                    </Button>
                </div>
                <div className="menu-legend">Interception</div>
            </div>
            </HideInStatic>
        </div>
    )
}
