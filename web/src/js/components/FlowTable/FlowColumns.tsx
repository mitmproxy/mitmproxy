import React, {useState} from 'react'
import {useDispatch} from 'react-redux'
import classnames from 'classnames'
import {RequestUtils, ResponseUtils} from '../../flow/utils.js'
import {formatSize, formatTimeDelta, formatTimeStamp} from '../../utils.js'
import * as flowActions from "../../ducks/flows";
import {addInterceptFilter} from "../../ducks/settings"
import Dropdown, {MenuItem, SubMenu} from "../common/Dropdown";
import {fetchApi} from "../../utils"
import {Flow} from "../../flow";

export const defaultColumnNames = ["tls", "icon", "path", "method", "status", "size", "time"]

type FlowColumnProps = {
    flow: Flow
}

interface FlowColumn {
    (props: FlowColumnProps): JSX.Element;

    headerClass: string;
    headerName: string;
}

export const TLSColumn: FlowColumn = ({flow}) => {
    return (
        <td className={classnames('col-tls', flow.client_conn.tls_established ? 'col-tls-https' : 'col-tls-http')}/>
    )
}

TLSColumn.headerClass = 'col-tls'
TLSColumn.headerName = ''

export const IconColumn: FlowColumn = ({flow}) => {
    return (
        <td className="col-icon">
            <div className={classnames('resource-icon', getIcon(flow))}/>
        </td>
    )
}

IconColumn.headerClass = 'col-icon'
IconColumn.headerName = ''

const getIcon = (flow: Flow): string => {
    if (flow.type !== "http" || !flow.response) {
        return 'resource-icon-plain'
    }

    var contentType = ResponseUtils.getContentType(flow.response) || ''

    // @todo We should assign a type to the flow somewhere else.
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

export const PathColumn: FlowColumn = ({flow}) => {
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
            {flow.type === "http" ? RequestUtils.pretty_url(flow.request) : null}
        </td>
    )
};

PathColumn.headerClass = 'col-path'
PathColumn.headerName = 'Path'

export const MethodColumn: FlowColumn = ({flow}) => {
    return (
        <td className="col-method">{flow.type === "http" ? flow.request.method : flow.type.toLowerCase()}</td>
    )
};

MethodColumn.headerClass = 'col-method'
MethodColumn.headerName = 'Method'

export const StatusColumn: FlowColumn = ({flow}) => {
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

StatusColumn.headerClass = 'col-status'
StatusColumn.headerName = 'Status'

export const SizeColumn: FlowColumn = ({flow}) => {
    return (
        <td className="col-size">{formatSize(getTotalSize(flow))}</td>
    )
};

const getTotalSize = (flow: Flow): number => {
    if (flow.type !== "http")
        return 0
    let total = flow.request.contentLength
    if (flow.response) {
        total += flow.response.contentLength || 0
    }
    return total
}

SizeColumn.headerClass = 'col-size'
SizeColumn.headerName = 'Size'

export const TimeColumn: FlowColumn = ({flow}) => {
    return (
        <td className="col-time">
            {flow.type === "http" && flow.response ? (
                formatTimeDelta(1000 * (flow.response.timestamp_end - flow.request.timestamp_start))
            ) : (
                '...'
            )}
        </td>
    )
}

TimeColumn.headerClass = 'col-time'
TimeColumn.headerName = 'Time'

export const TimeStampColumn: FlowColumn = ({flow}) => {
    return (
        <td className="col-start">
            {flow.type === "http" && flow.request.timestamp_start ? (
                formatTimeStamp(flow.request.timestamp_start)
            ) : (
                '...'
            )}
        </td>
    )
}

TimeStampColumn.headerClass = 'col-timestamp'
TimeStampColumn.headerName = 'TimeStamp'

export const QuickActionsColumn: FlowColumn = ({flow}) => {
    const dispatch = useDispatch()
    let [open, setOpen] = useState(false)

    const copy = (format: string) => {
        if (!flow) {
            return
        }

        fetchApi(`/flows/${flow.id}/export/${format}.json`, {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                navigator.clipboard.writeText(data.export)
            })
    }

    let resume_or_replay = null;
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
        <td className={classnames("col-quickactions", {hover: open})} onClick={(e) => e.stopPropagation()}>
            <div>
                {resume_or_replay}
                <Dropdown text={<i className="fa fa-fw fa-ellipsis-h text-muted"/>} className="quickaction"
                          onOpen={setOpen}
                          options={{placement: "bottom-end"}}>
                    <SubMenu title="Copy...">
                        <MenuItem onClick={() => copy("raw_request")}>Copy raw request</MenuItem>
                        <MenuItem onClick={() => copy("raw_response")}>Copy raw response</MenuItem>
                        <MenuItem onClick={() => copy("raw")}>Copy raw request and response</MenuItem>
                        <MenuItem onClick={() => copy("curl")}>Copy as cURL</MenuItem>
                        <MenuItem onClick={() => copy("httpie")}>Copy as HTTPie</MenuItem>
                    </SubMenu>
                    <SubMenu title="Intercept requests like this">
                        <MenuItem onClick={() => filt(`~q ${flow.request.host}`)}>
                            Requests to {flow.request.host}
                        </MenuItem>w
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

QuickActionsColumn.headerClass = 'col-quickactions'
QuickActionsColumn.headerName = ''


export const columns: { [key: string]: FlowColumn } = {};
for (let col of [
    TLSColumn,
    IconColumn,
    PathColumn,
    MethodColumn,
    StatusColumn,
    TimeStampColumn,
    SizeColumn,
    TimeColumn,
    QuickActionsColumn,
]) {
    columns[col.name.replace(/Column$/, "").toLowerCase()] = col;
}
