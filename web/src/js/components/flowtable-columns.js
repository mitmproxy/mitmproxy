import React from "react";
import {RequestUtils, ResponseUtils} from "../flow/utils.js";
import {formatSize, formatTimeDelta} from "../utils.js";

var TLSColumn = React.createClass({
    statics: {
        Title: React.createClass({
            render: function(){
                return <th {...this.props} className={"col-tls " + (this.props.className || "") }></th>;
            }
        }),
        sortKeyFun: function(flow){
            return flow.request.scheme;
        }
    },
    render: function () {
        var flow = this.props.flow;
        var ssl = (flow.request.scheme === "https");
        var classes;
        if (ssl) {
            classes = "col-tls col-tls-https";
        } else {
            classes = "col-tls col-tls-http";
        }
        return <td className={classes}></td>;
    }
});


var IconColumn = React.createClass({
    statics: {
        Title: React.createClass({
            render: function(){
                return <th {...this.props} className={"col-icon " + (this.props.className || "") }></th>;
            }
        })
    },
    render: function () {
        var flow = this.props.flow;

        var icon;
        if (flow.response) {
            var contentType = ResponseUtils.getContentType(flow.response);

            //TODO: We should assign a type to the flow somewhere else.
            if (flow.response.status_code === 304) {
                icon = "resource-icon-not-modified";
            } else if (300 <= flow.response.status_code && flow.response.status_code < 400) {
                icon = "resource-icon-redirect";
            } else if (contentType && contentType.indexOf("image") >= 0) {
                icon = "resource-icon-image";
            } else if (contentType && contentType.indexOf("javascript") >= 0) {
                icon = "resource-icon-js";
            } else if (contentType && contentType.indexOf("css") >= 0) {
                icon = "resource-icon-css";
            } else if (contentType && contentType.indexOf("html") >= 0) {
                icon = "resource-icon-document";
            }
        }
        if (!icon) {
            icon = "resource-icon-plain";
        }


        icon += " resource-icon";
        return <td className="col-icon">
            <div className={icon}></div>
        </td>;
    }
});

var PathColumn = React.createClass({
    statics: {
        Title: React.createClass({
            render: function(){
                return <th {...this.props} className={"col-path " + (this.props.className || "") }>Path</th>;
            }
        }),
        sortKeyFun: function(flow){
            return RequestUtils.pretty_url(flow.request);
        }
    },
    render: function () {
        var flow = this.props.flow;
        return <td className="col-path">
            {flow.request.is_replay ? <i className="fa fa-fw fa-repeat pull-right"></i> : null}
            {flow.intercepted ? <i className="fa fa-fw fa-pause pull-right"></i> : null}
            { RequestUtils.pretty_url(flow.request) }
        </td>;
    }
});


var MethodColumn = React.createClass({
    statics: {
        Title: React.createClass({
            render: function(){
                return <th {...this.props} className={"col-method " + (this.props.className || "") }>Method</th>;
            }
        }),
        sortKeyFun: function(flow){
            return flow.request.method;
        }
    },
    render: function () {
        var flow = this.props.flow;
        return <td className="col-method">{flow.request.method}</td>;
    }
});


var StatusColumn = React.createClass({
    statics: {
        Title: React.createClass({
            render: function(){
                return <th {...this.props} className={"col-status " + (this.props.className || "") }>Status</th>;
            }
        }),
        sortKeyFun: function(flow){
            return flow.response ? flow.response.status_code : undefined;
        }
    },
    render: function () {
        var flow = this.props.flow;
        var status;
        if (flow.response) {
            status = flow.response.status_code;
        } else {
            status = null;
        }
        return <td className="col-status">{status}</td>;
    }
});


var SizeColumn = React.createClass({
    statics: {
        Title: React.createClass({
            render: function(){
                return <th {...this.props} className={"col-size " + (this.props.className || "") }>Size</th>;
            }
        }),
        sortKeyFun: function(flow){
            var total = flow.request.contentLength;
            if (flow.response) {
                total += flow.response.contentLength || 0;
            }
            return total;
        }
    },
    render: function () {
        var flow = this.props.flow;

        var total = flow.request.contentLength;
        if (flow.response) {
            total += flow.response.contentLength || 0;
        }
        var size = formatSize(total);
        return <td className="col-size">{size}</td>;
    }
});


var TimeColumn = React.createClass({
    statics: {
        Title: React.createClass({
            render: function(){
                return <th {...this.props} className={"col-time " + (this.props.className || "") }>Time</th>;
            }
        }),
        sortKeyFun: function(flow){
            if(flow.response) {
                return flow.response.timestamp_end - flow.request.timestamp_start;
            }
        }
    },
    render: function () {
        var flow = this.props.flow;
        var time;
        if (flow.response) {
            time = formatTimeDelta(1000 * (flow.response.timestamp_end - flow.request.timestamp_start));
        } else {
            time = "...";
        }
        return <td className="col-time">{time}</td>;
    }
});


var all_columns = [
    TLSColumn,
    IconColumn,
    PathColumn,
    MethodColumn,
    StatusColumn,
    SizeColumn,
    TimeColumn
];

export default all_columns;
