import React from 'react'
import {useDispatch} from 'react-redux'
import classnames from 'classnames'
import {RequestUtils, ResponseUtils} from '../../flow/utils.js'
import {formatSize, formatTimeDelta, formatTimeStamp} from '../../utils.js'
import * as flowActions from "../../ducks/flows";

export const defaultColumnNames = ["tls", "icon", "path", "method", "status", "size", "time"]

export function TLSColumn({flow}) {
    return (
        <td className={classnames('col-tls', flow.request.scheme === 'https' ? 'col-tls-https' : 'col-tls-http')}/>
    )
}

TLSColumn.headerClass = 'col-tls'
TLSColumn.headerName = ''

export function IconColumn({flow}) {
    return (
        <td className="col-icon">
            <div className={classnames('resource-icon', IconColumn.getIcon(flow))}/>
        </td>
    )
}

IconColumn.headerClass = 'col-icon'
IconColumn.headerName = ''

IconColumn.getIcon = flow => {
    if (!flow.response) {
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

export function PathColumn({flow}) {

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
            {flow.request.is_replay && (
                <i className="fa fa-fw fa-repeat pull-right"/>
            )}
            {flow.intercepted && (
                <i className="fa fa-fw fa-pause pull-right"/>
            )}
            {err}
            {RequestUtils.pretty_url(flow.request)}
        </td>
    )
}

PathColumn.headerClass = 'col-path'
PathColumn.headerName = 'Path'

export function MethodColumn({flow}) {
    return (
        <td className="col-method">{flow.request.method}</td>
    )
}

MethodColumn.headerClass = 'col-method'
MethodColumn.headerName = 'Method'

export function StatusColumn({flow}) {
    let color = 'darkred';

    if (flow.response && 100 <= flow.response.status_code && flow.response.status_code < 200) {
        color = 'green'
    } else if (flow.response && 200 <= flow.response.status_code && flow.response.status_code < 300) {
        color = 'darkgreen'
    } else if (flow.response && 300 <= flow.response.status_code && flow.response.status_code < 400) {
        color = 'lightblue'
    } else if (flow.response && 400 <= flow.response.status_code && flow.response.status_code < 500) {
        color = 'lightred'
    } else if (flow.response && 500 <= flow.response.status_code && flow.response.status_code < 600) {
        color = 'lightred'
    }

    return (
        <td className="col-status" style={{color: color}}>{flow.response && flow.response.status_code}</td>
    )
}

StatusColumn.headerClass = 'col-status'
StatusColumn.headerName = 'Status'

export function SizeColumn({flow}) {
    return (
        <td className="col-size">{formatSize(SizeColumn.getTotalSize(flow))}</td>
    )
}

SizeColumn.getTotalSize = flow => {
    let total = flow.request.contentLength
    if (flow.response) {
        total += flow.response.contentLength || 0
    }
    return total
}

SizeColumn.headerClass = 'col-size'
SizeColumn.headerName = 'Size'

export function TimeColumn({flow}) {
    return (
        <td className="col-time">
            {flow.response ? (
                formatTimeDelta(1000 * (flow.response.timestamp_end - flow.request.timestamp_start))
            ) : (
                '...'
            )}
        </td>
    )
}

TimeColumn.headerClass = 'col-time'
TimeColumn.headerName = 'Time'

export function TimeStampColumn({flow}) {
    return (
        <td className="col-start">
            {flow.request.timestamp_start ? (
                formatTimeStamp(flow.request.timestamp_start)
            ) : (
                '...'
            )}
        </td>
    )
}

TimeStampColumn.headerClass = 'col-timestamp'
TimeStampColumn.headerName = 'TimeStamp'

export function QuickActionsColumn({flow}) {
    const dispatch = useDispatch()

    function resume(e) {
        dispatch(flowActions.resume(flow))
        e.preventDefault()
        e.stopPropagation()
    }

    return (
        <td className="col-quickactions">
            <div>
                <div className="quickaction"><i className="fa fa-fw fa-ellipsis-h"/></div>
                {flow.intercepted
                    ? <div className="quickaction" onClick={resume}><i className="fa fa-fw fa-play text-success"/></div>
                    : null}
            </div>
        </td>
    )
}

QuickActionsColumn.headerClass = 'col-quickactions'
QuickActionsColumn.headerName = ''


export const columns = {};
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
