var TLSColumn = React.createClass({
    statics: {
        renderTitle: function () {
            return <th key="tls" className="col-tls"></th>;
        }
    },
    render: function () {
        var flow = this.props.flow;
        var ssl = (flow.request.scheme == "https");
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
        renderTitle: function () {
            return <th key="icon" className="col-icon"></th>;
        }
    },
    render: function () {
        var flow = this.props.flow;

        var icon;
        if (flow.response) {
            var contentType = ResponseUtils.getContentType(flow.response);

            //TODO: We should assign a type to the flow somewhere else.
            if (flow.response.code == 304) {
                icon = "resource-icon-not-modified";
            } else if (300 <= flow.response.code && flow.response.code < 400) {
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
        renderTitle: function () {
            return <th key="path" className="col-path">Path</th>;
        }
    },
    render: function () {
        var flow = this.props.flow;
        return <td className="col-path">
            {flow.request.is_replay ? <i className="fa fa-fw fa-repeat pull-right"></i> : null}
            {flow.intercepted ? <i className="fa fa-fw fa-pause pull-right"></i> : null}
            {flow.request.scheme + "://" + flow.request.host + flow.request.path}
        </td>;
    }
});


var MethodColumn = React.createClass({
    statics: {
        renderTitle: function () {
            return <th key="method" className="col-method">Method</th>;
        }
    },
    render: function () {
        var flow = this.props.flow;
        return <td className="col-method">{flow.request.method}</td>;
    }
});


var StatusColumn = React.createClass({
    statics: {
        renderTitle: function () {
            return <th key="status" className="col-status">Status</th>;
        }
    },
    render: function () {
        var flow = this.props.flow;
        var status;
        if (flow.response) {
            status = flow.response.code;
        } else {
            status = null;
        }
        return <td className="col-status">{status}</td>;
    }
});


var SizeColumn = React.createClass({
    statics: {
        renderTitle: function () {
            return <th key="size" className="col-size">Size</th>;
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
        renderTitle: function () {
            return <th key="time" className="col-time">Time</th>;
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
    TimeColumn];

