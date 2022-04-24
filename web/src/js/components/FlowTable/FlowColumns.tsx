import React, {ReactElement, useState} from 'react'
import {useDispatch} from 'react-redux'
import classnames from 'classnames'
import {canReplay, endTime, getTotalSize, RequestUtils, ResponseUtils, startTime} from '../../flow/utils'
import {formatSize, formatTimeDelta, formatTimeStamp} from '../../utils'
import * as flowActions from "../../ducks/flows";
import {Flow} from "../../flow";


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
icon.sortKey = flow => getIcon(flow)

const getIcon = (flow: Flow): string => {
    if (flow.type === "tcp" || flow.type === "dns") {
        return `resource-icon-${flow.type}`
    }
    if (flow.websocket) {
        return 'resource-icon-websocket'
    }
    if (!flow.response) {
        return 'resource-icon-plain'
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

const mainPath = (flow: Flow): string => {
    switch (flow.type) {
        case "http":
            return RequestUtils.pretty_url(flow.request)
        case "tcp":
            return `${flow.client_conn.peername.join(':')} ↔ ${flow.server_conn?.address?.join(':')}`
        case "dns":
            return `${flow.request.questions.map(q => `${q.name} ${q.type}`).join(", ")} = ${(flow.response?.answers.map(q => q.data).join(", ") ?? "...") || "?"}`
    }
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
            {mainPath(flow)}
        </td>
    )
};
path.headerName = 'Path'
path.sortKey = flow => mainPath(flow)

export const method: FlowColumn = ({flow}) => <td className="col-method">{method.sortKey(flow)}</td>
method.headerName = 'Method'
method.sortKey = flow => {
    switch (flow.type) {
        case "http": return flow.websocket ? (flow.client_conn.tls_established ? "WSS" : "WS") : flow.request.method
        case "dns": return flow.request.op_code
        default: return flow.type.toUpperCase()
    }
}

export const status: FlowColumn = ({flow}) => {
    let color = 'darkred'

    if ((flow.type !== "http" && flow.type != "dns") || !flow.response)
        return <td className="col-status"/>

    if (100 <= flow.response.status_code && flow.response.status_code < 200) {
        color = 'green'
    } else if (200 <= flow.response.status_code && flow.response.status_code < 300) {
        color = 'darkgreen'
    } else if (300 <= flow.response.status_code && flow.response.status_code < 400) {
        color = 'lightblue'
    } else if (400 <= flow.response.status_code && flow.response.status_code < 500) {
        color = 'red'
    } else if (500 <= flow.response.status_code && flow.response.status_code < 600) {
        color = 'red'
    }

    return (
        <td className="col-status" style={{color: color}}>{status.sortKey(flow)}</td>
    )
}
status.headerName = 'Status'
status.sortKey = flow => {
    switch (flow.type) {
        case "http": return flow.response?.status_code
        case "dns": return flow.response?.response_code
        default: return undefined
    }
}

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
        <td className="col-timestamp">
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

    let resume_or_replay: ReactElement | null = null;
    if (flow.intercepted) {
        resume_or_replay = <a href="#" className="quickaction" onClick={() => dispatch(flowActions.resume(flow))}>
            <i className="fa fa-fw fa-play text-success"/>
        </a>;
    } else if (canReplay(flow)) {
        resume_or_replay = <a href="#" className="quickaction" onClick={() => dispatch(flowActions.replay(flow))}>
            <i className="fa fa-fw fa-repeat text-primary"/>
        </a>;
    }

    return (
        <td className={classnames("col-quickactions", {hover: open})} onClick={() => 0}>
            <div>
                {resume_or_replay}
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
