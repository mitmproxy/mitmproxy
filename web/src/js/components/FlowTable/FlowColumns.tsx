import React, {useState} from 'react'
import {useDispatch} from 'react-redux'
import classnames from 'classnames'
import {endTime, getTotalSize, RequestUtils, ResponseUtils, startTime} from '../../flow/utils'
import {formatSize, formatTimeDelta, formatTimeStamp} from '../../utils'
import * as flowActions from "../../ducks/flows";
import {addInterceptFilter} from "../../ducks/options"
import Dropdown, {MenuItem, SubMenu} from "../common/Dropdown";
import {Flow} from "../../flow";
import {copy} from "../../flow/export";


type FlowColumnProps = {
    flow: Flow
}

interface FlowColumn {
    (props: FlowColumnProps): JSX.Element;

    headerName: string; // Shown in the UI
    sortKey: (flow: Flow) => any;
}

export const tls: FlowColumn = ({flow}) => {
    return (
        <td className={classnames('col-tls', flow.client_conn.tls_established ? 'col-tls-https' : 'col-tls-http')}/>
    )
}
tls.headerName = ''
tls.sortKey = flow => flow.type === "http" && flow.request.scheme

export const icon: FlowColumn = ({flow}) => {
    return (
        <td className="col-icon">
            <div className={classnames('resource-icon', getIcon(flow))}/>
        </td>
    )
}
icon.headerName = ''
icon.sortKey = flow => 0

const getIcon = (flow: Flow): string => {
    if (flow.type !== "http" || !flow.response) {
        return 'resource-icon-plain'
    }
    if (flow.websocket) {
        return 'resource-icon-websocket'
    }

    var contentType = ResponseUtils.getContentType(flow.response) || ''

    if (flow.response.status_code === 304) {
        return 'resource-icon-not-modified'
    }
    if (300 <= flow.response.status_code && flow.response.status_code < 400) {
        return 'resource-icon-redirect'
    }
    if (contentType.indexOf('image') >= 0) {
        return 'resource-icon-image'
    }
    if (contentType.indexOf('javascript') >= 0) {
        return 'resource-icon-js'
    }
    if (contentType.indexOf('css') >= 0) {
        return 'resource-icon-css'
    }
    if (contentType.indexOf('html') >= 0) {
        return 'resource-icon-document'
    }

    return 'resource-icon-plain'
}

export const path: FlowColumn = ({flow}) => {
    let err;
    if (flow.error) {
        if (flow.error.msg === "Connection killed.") {
            err = <i className="fa fa-fw fa-times pull-right"/>
        } else {
            err = <i className="fa fa-fw fa-exclamation pull-right"/>
        }
    }
    return (
        <td className="col-path">
            {flow.is_replay === "request" && (
                <i className="fa fa-fw fa-repeat pull-right"/>
            )}
            {flow.intercepted && (
                <i className="fa fa-fw fa-pause pull-right"/>
            )}
            {err}
            <span className="marker pull-right">{flow.marked}</span>
            {flow.type === "http" ? RequestUtils.pretty_url(flow.request) : null}
        </td>
    )
};
path.headerName = 'Path'
path.sortKey = flow => flow.type === "http" && RequestUtils.pretty_url(flow.request)

export const method: FlowColumn = ({flow}) => {
    return (
        <td className="col-method">{flow.type === "http" ? flow.request.method : flow.type.toLowerCase()}</td>
    )
};
method.headerName = 'Method'
method.sortKey = flow => flow.type === "http" && flow.request.method

export const status: FlowColumn = ({flow}) => {
    let color = 'darkred';

    if (flow.type !== "http" || !flow.response)
        return <td className="col-status"/>

    if (100 <= flow.response.status_code && flow.response.status_code < 200) {
        color = 'green'
    } else if (200 <= flow.response.status_code && flow.response.status_code < 300) {
        color = 'darkgreen'
    } else if (300 <= flow.response.status_code && flow.response.status_code < 400) {
        color = 'lightblue'
    } else if (400 <= flow.response.status_code && flow.response.status_code < 500) {
        color = 'lightred'
    } else if (500 <= flow.response.status_code && flow.response.status_code < 600) {
        color = 'lightred'
    }

    return (
        <td className="col-status" style={{color: color}}>{flow.response.status_code}</td>
    )
}
status.headerName = 'Status'
status.sortKey = flow => flow.type === "http" && flow.response && flow.response.status_code

export const size: FlowColumn = ({flow}) => {
    return (
        <td className="col-size">{formatSize(getTotalSize(flow))}</td>
    )
};
size.headerName = 'Size'
size.sortKey = flow => getTotalSize(flow)


export const time: FlowColumn = ({flow}) => {
    const start = startTime(flow), end = endTime(flow);
    return (
        <td className="col-time">
            {start && end ? (
                formatTimeDelta(1000 * (end - start))
            ) : (
                '...'
            )}
        </td>
    )
}
time.headerName = 'Time'
time.sortKey = flow => {
    const start = startTime(flow), end = endTime(flow);
    return start && end && end - start;
}

export const timestamp: FlowColumn = ({flow}) => {
    const start = startTime(flow);
    return (
        <td className="col-start">
            {start ? (
                formatTimeStamp(start)
            ) : (
                '...'
            )}
        </td>
    )
}
timestamp.headerName = 'Start time'
timestamp.sortKey = flow => startTime(flow)

const markers = {
    ":red_circle:": "🔴",
    ":orange_circle:": "🟠",
    ":yellow_circle:": "🟡",
    ":green_circle:": "🟢",
    ":large_blue_circle:": "🔵",
    ":purple_circle:": "🟣",
    ":brown_circle:": "🟤",
}

export const quickactions: FlowColumn = ({flow}) => {
    const dispatch = useDispatch()
    let [open, setOpen] = useState(false)

    let resume_or_replay: React.ReactNode | null = null;
    if (flow.intercepted) {
        resume_or_replay = <a href="#" className="quickaction" onClick={() => dispatch(flowActions.resume(flow))}>
            <i className="fa fa-fw fa-play text-success"/>
        </a>;
    } else {
        resume_or_replay = <a href="#" className="quickaction" onClick={() => dispatch(flowActions.replay(flow))}>
            <i className="fa fa-fw fa-repeat text-primary"/>
        </a>;
    }

    if (flow.type !== "http")
        return <td className="col-quickactions"/>

    const filt = (x) => dispatch(addInterceptFilter(x));
    const ct = flow.response && ResponseUtils.getContentType(flow.response);

    return (
        <td className={classnames("col-quickactions", {hover: open})} onClick={() => 0}>
            <div>
                {resume_or_replay}
                <Dropdown text={<i className="fa fa-fw fa-ellipsis-h text-muted"/>} className="quickaction"
                          onOpen={setOpen}
                          options={{placement: "bottom-end"}}>
                    <SubMenu title="Copy...">
                        <MenuItem onClick={() => copy(flow, "raw_request")}>Copy raw request</MenuItem>
                        <MenuItem onClick={() => copy(flow, "raw_response")}>Copy raw response</MenuItem>
                        <MenuItem onClick={() => copy(flow, "raw")}>Copy raw request and response</MenuItem>
                        <MenuItem onClick={() => copy(flow, "curl")}>Copy as cURL</MenuItem>
                        <MenuItem onClick={() => copy(flow, "httpie")}>Copy as HTTPie</MenuItem>
                    </SubMenu>
                    <SubMenu title="Mark..." className="markers-menu">
                        <MenuItem onClick={() => dispatch(flowActions.update(flow, {marked: ""}))}>⚪ (no marker)</MenuItem>
                        {Object.entries(markers).map(([name, sym]) =>
                            <MenuItem
                                key={name}
                                onClick={() => dispatch(flowActions.update(flow, {marked: name}))}>
                                {sym} {name.replace(/[:_]/g, " ")}
                            </MenuItem>
                        )}
                    </SubMenu>
                    <SubMenu title="Intercept requests like this">
                        <MenuItem onClick={() => filt(`~q ${flow.request.host}`)}>
                            Requests to {flow.request.host}
                        </MenuItem>
                        {flow.request.path !== "/" &&
                        <MenuItem onClick={() => filt(`~q ${flow.request.host}${flow.request.path}`)}>
                            Requests to {flow.request.host + flow.request.path}
                        </MenuItem>}
                        {flow.request.method !== "GET" &&
                        <MenuItem onClick={() => filt(`~q ~m ${flow.request.method} ${flow.request.host}`)}>
                            {flow.request.method} requests to {flow.request.host}
                        </MenuItem>}
                    </SubMenu>
                    <SubMenu title="Intercept responses like this">
                        <MenuItem onClick={() => filt(`~s ${flow.request.host}`)}>
                            Responses from {flow.request.host}
                        </MenuItem>
                        {flow.request.path !== "/" &&
                        <MenuItem onClick={() => filt(`~s ${flow.request.host}${flow.request.path}`)}>
                            Responses from {flow.request.host + flow.request.path}
                        </MenuItem>}
                        {!!ct &&
                        <MenuItem onClick={() => filt(`~ts ${ct}`)}>
                            Responses with a {ct} content type.
                        </MenuItem>}
                    </SubMenu>
                </Dropdown>
            </div>

        </td>
    )
}

quickactions.headerName = ''
quickactions.sortKey = flow => 0;

export default {
    icon,
    method,
    path,
    quickactions,
    size,
    status,
    time,
    timestamp,
    tls
};
