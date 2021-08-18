import * as React from "react";
import Button from "../common/Button"
import {MessageUtils} from "../../flow/utils.js"
import HideInStatic from "../common/HideInStatic";
import {useAppDispatch, useAppSelector} from "../../ducks";
import {
    duplicate as duplicateFlow,
    kill as killFlow,
    remove as removeFlow,
    replay as replayFlow,
    resume as resumeFlow,
    revert as revertFlow
} from "../../ducks/flows"
import Dropdown, {MenuItem} from "../common/Dropdown";
import {copy} from "../../flow/export";
import {Flow} from "../../flow";

FlowMenu.title = 'Flow'

export default function FlowMenu(): JSX.Element {
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
                                onClick={() => dispatch(replayFlow(flow))}
                                disabled={!(flow.type === "http" && !flow.websocket)}
                        >
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
                    <DownloadButton flow={flow}/>
                    <Dropdown className="" text={
                        <Button title="Export flow." icon="fa-clone" onClick={() => 1}>Export▾</Button>
                    } options={{"placement": "bottom-start"}}>
                        <MenuItem onClick={() => copy(flow, "raw_request")}>Copy raw request</MenuItem>
                        <MenuItem onClick={() => copy(flow, "raw_response")}>Copy raw response</MenuItem>
                        <MenuItem onClick={() => copy(flow, "raw")}>Copy raw request and response</MenuItem>
                        <MenuItem onClick={() => copy(flow, "curl")}>Copy as cURL</MenuItem>
                        <MenuItem onClick={() => copy(flow, "httpie")}>Copy as HTTPie</MenuItem>
                    </Dropdown>


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


function DownloadButton({flow}: { flow: Flow }) {
    if (flow.type !== "http")
        return null;

    if (flow.request.contentLength && !flow.response?.contentLength) {
        return <Button icon="fa-download"
                       onClick={() => window.location.href = MessageUtils.getContentURL(flow, flow.request)}
        >Download</Button>
    }
    if (flow.response) {
        const response = flow.response;
        if (!flow.request.contentLength && flow.response.contentLength) {
            return <Button icon="fa-download"
                           onClick={() => window.location.href = MessageUtils.getContentURL(flow, response)}
            >Download</Button>
        }
        if (flow.request.contentLength && flow.response.contentLength) {
            return <Dropdown text={
                <Button icon="fa-download" onClick={() => 1}>Download▾</Button>
            } options={{"placement": "bottom-start"}}>
                <MenuItem onClick={() => window.location.href = MessageUtils.getContentURL(flow, flow.request)}>Download
                    request</MenuItem>
                <MenuItem onClick={() => window.location.href = MessageUtils.getContentURL(flow, response)}>Download
                    response</MenuItem>
            </Dropdown>
        }
    }

    return null;
}
