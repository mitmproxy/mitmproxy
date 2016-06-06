import React from "react"
import {RequestUtils, ResponseUtils} from "../flow/utils.js"
import {formatSize, formatTimeDelta} from "../utils.js"


function TLSColumn({flow}) {
    let ssl = (flow.request.scheme === "https")
    let classes
    if (ssl) {
        classes = "col-tls col-tls-https"
    } else {
        classes = "col-tls col-tls-http"
    }
    return <td className={classes}></td>
}
TLSColumn.Title = ({className = "", ...props}) => <th {...props} className={"col-tls " + className }></th>
TLSColumn.sortKeyFun = flow => flow.request.scheme


function IconColumn({flow}) {
    let icon
    if (flow.response) {
        var contentType = ResponseUtils.getContentType(flow.response)

        //TODO: We should assign a type to the flow somewhere else.
        if (flow.response.status_code === 304) {
            icon = "resource-icon-not-modified"
        } else if (300 <= flow.response.status_code && flow.response.status_code < 400) {
            icon = "resource-icon-redirect"
        } else if (contentType && contentType.indexOf("image") >= 0) {
            icon = "resource-icon-image"
        } else if (contentType && contentType.indexOf("javascript") >= 0) {
            icon = "resource-icon-js"
        } else if (contentType && contentType.indexOf("css") >= 0) {
            icon = "resource-icon-css"
        } else if (contentType && contentType.indexOf("html") >= 0) {
            icon = "resource-icon-document"
        }
    }
    if (!icon) {
        icon = "resource-icon-plain"
    }

    icon += " resource-icon"
    return <td className="col-icon">
        <div className={icon}></div>
    </td>
}
IconColumn.Title = ({className = "", ...props}) => <th {...props} className={"col-icon " + className }></th>


function PathColumn({flow}) {
    return <td className="col-path">
        {flow.request.is_replay ? <i className="fa fa-fw fa-repeat pull-right"></i> : null}
        {flow.intercepted ? <i className="fa fa-fw fa-pause pull-right"></i> : null}
        { RequestUtils.pretty_url(flow.request) }
    </td>
}
PathColumn.Title = ({className = "", ...props}) =>
    <th {...props} className={"col-path " + className }>Path</th>
PathColumn.sortKeyFun = flow => RequestUtils.pretty_url(flow.request)


function MethodColumn({flow}) {
    return <td className="col-method">{flow.request.method}</td>
}
MethodColumn.Title = ({className = "", ...props}) =>
    <th {...props} className={"col-method " + className }>Method</th>
MethodColumn.sortKeyFun = flow => flow.request.method


function StatusColumn({flow}) {
    let status
    if (flow.response) {
        status = flow.response.status_code
    } else {
        status = null
    }
    return <td className="col-status">{status}</td>

}
StatusColumn.Title = ({className = "", ...props}) =>
    <th {...props} className={"col-status " + className }>Status</th>
StatusColumn.sortKeyFun = flow => flow.response ? flow.response.status_code : undefined


function SizeColumn({flow}) {
    let total = flow.request.contentLength
    if (flow.response) {
        total += flow.response.contentLength || 0
    }
    let size = formatSize(total)
    return <td className="col-size">{size}</td>

}
SizeColumn.Title = ({className = "", ...props}) =>
    <th {...props} className={"col-size " + className }>Size</th>
SizeColumn.sortKeyFun = flow => {
    let total = flow.request.contentLength
    if (flow.response) {
        total += flow.response.contentLength || 0
    }
    return total
}


function TimeColumn({flow}) {
    let time
    if (flow.response) {
        time = formatTimeDelta(1000 * (flow.response.timestamp_end - flow.request.timestamp_start))
    } else {
        time = "..."
    }
    return <td className="col-time">{time}</td>
}
TimeColumn.Title = ({className = "", ...props}) =>
    <th {...props} className={"col-time " + className }>Time</th>
TimeColumn.sortKeyFun = flow => flow.response.timestamp_end - flow.request.timestamp_start


var all_columns = [
    TLSColumn,
    IconColumn,
    PathColumn,
    MethodColumn,
    StatusColumn,
    SizeColumn,
    TimeColumn
]

export default all_columns
