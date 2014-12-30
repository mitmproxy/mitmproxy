(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
var ActionTypes = {
    // Connection
    CONNECTION_OPEN: "connection_open",
    CONNECTION_CLOSE: "connection_close",
    CONNECTION_ERROR: "connection_error",

    // Stores
    SETTINGS_STORE: "settings",
    EVENT_STORE: "events",
    FLOW_STORE: "flows",
};

var StoreCmds = {
    ADD: "add",
    UPDATE: "update",
    REMOVE: "remove",
    RESET: "reset"
};

var ConnectionActions = {
    open: function () {
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.CONNECTION_OPEN
        });
    },
    close: function () {
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.CONNECTION_CLOSE
        });
    },
    error: function () {
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.CONNECTION_ERROR
        });
    }
};

var SettingsActions = {
    update: function (settings) {

        jQuery.ajax({
            type: "PUT",
            url: "/settings",
            data: settings
        });

        /*
        //Facebook Flux: We do an optimistic update on the client already.
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.SETTINGS_STORE,
            cmd: StoreCmds.UPDATE,
            data: settings
        });
        */
    }
};

var EventLogActions_event_id = 0;
var EventLogActions = {
    add_event: function (message) {
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.EVENT_STORE,
            cmd: StoreCmds.ADD,
            data: {
                message: message,
                level: "web",
                id: "viewAction-" + EventLogActions_event_id++
            }
        });
    }
};

var FlowActions = {
    accept: function (flow) {
        jQuery.post("/flows/" + flow.id + "/accept");
    },
    accept_all: function(){
        jQuery.post("/flows/accept");
    },
    "delete": function(flow){
        jQuery.ajax({
            type:"DELETE",
            url: "/flows/" + flow.id
        });
    },
    duplicate: function(flow){
        jQuery.post("/flows/" + flow.id + "/duplicate");
    },
    replay: function(flow){
        jQuery.post("/flows/" + flow.id + "/replay");
    },
    revert: function(flow){
        jQuery.post("/flows/" + flow.id + "/revert");
    },
    update: function (flow) {
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.FLOW_STORE,
            cmd: StoreCmds.UPDATE,
            data: flow
        });
    },
    clear: function(){
        jQuery.post("/clear");
    }
};

Query = {
    FILTER: "f",
    HIGHLIGHT: "h",
    SHOW_EVENTLOG: "e"
};

module.exports = {
    ActionTypes: ActionTypes,
    ConnectionActions: ConnectionActions,
    FlowActions: FlowActions,
    StoreCmds: StoreCmds


};
},{}],2:[function(require,module,exports){

var React = require("react");
var ReactRouter = require("react-router");
var $ = require("jquery");

var Connection = require("./connection");
var proxyapp = require("./components/proxyapp.jsx.js");

$(function () {
    window.ws = new Connection("/updates");

    ReactRouter.run(proxyapp.routes, function (Handler) {
        React.render(React.createElement(Handler, null), document.body);
    });
});
},{"./components/proxyapp.jsx.js":9,"./connection":12,"jquery":"jquery","react":"react","react-router":"react-router"}],3:[function(require,module,exports){
var React = require("react");
var _ = require("lodash");

var utils = require("./utils.jsx.js");
var actions = require("../actions.js");
var flowutils = require("../flow/utils.js");
var toputils = require("../utils.js");

var NavAction = React.createClass({displayName: "NavAction",
    onClick: function (e) {
        e.preventDefault();
        this.props.onClick();
    },
    render: function () {
        return (
            React.createElement("a", {title: this.props.title, 
                href: "#", 
                className: "nav-action", 
                onClick: this.onClick}, 
                React.createElement("i", {className: "fa fa-fw " + this.props.icon})
            )
        );
    }
});

var FlowDetailNav = React.createClass({displayName: "FlowDetailNav",
    render: function () {
        var flow = this.props.flow;

        var tabs = this.props.tabs.map(function (e) {
            var str = e.charAt(0).toUpperCase() + e.slice(1);
            var className = this.props.active === e ? "active" : "";
            var onClick = function (event) {
                this.props.selectTab(e);
                event.preventDefault();
            }.bind(this);
            return React.createElement("a", {key: e, 
                href: "#", 
                className: className, 
                onClick: onClick}, str);
        }.bind(this));

        var acceptButton = null;
        if(flow.intercepted){
            acceptButton = React.createElement(NavAction, {title: "[a]ccept intercepted flow", icon: "fa-play", onClick: actions.FlowActions.accept.bind(null, flow)});
        }
        var revertButton = null;
        if(flow.modified){
            revertButton = React.createElement(NavAction, {title: "revert changes to flow [V]", icon: "fa-history", onClick: actions.FlowActions.revert.bind(null, flow)});
        }

        return (
            React.createElement("nav", {ref: "head", className: "nav-tabs nav-tabs-sm"}, 
                tabs, 
                React.createElement(NavAction, {title: "[d]elete flow", icon: "fa-trash", onClick: actions.FlowActions.delete.bind(null, flow)}), 
                React.createElement(NavAction, {title: "[D]uplicate flow", icon: "fa-copy", onClick: actions.FlowActions.duplicate.bind(null, flow)}), 
                React.createElement(NavAction, {disabled: true, title: "[r]eplay flow", icon: "fa-repeat", onClick: actions.FlowActions.replay.bind(null, flow)}), 
                acceptButton, 
                revertButton
            )
        );
    }
});

var Headers = React.createClass({displayName: "Headers",
    render: function () {
        var rows = this.props.message.headers.map(function (header, i) {
            return (
                React.createElement("tr", {key: i}, 
                    React.createElement("td", {className: "header-name"}, header[0] + ":"), 
                    React.createElement("td", {className: "header-value"}, header[1])
                )
            );
        });
        return (
            React.createElement("table", {className: "header-table"}, 
                React.createElement("tbody", null, 
                    rows
                )
            )
        );
    }
});

var FlowDetailRequest = React.createClass({displayName: "FlowDetailRequest",
    render: function () {
        var flow = this.props.flow;
        var first_line = [
            flow.request.method,
            flowutils.RequestUtils.pretty_url(flow.request),
            "HTTP/" + flow.request.httpversion.join(".")
        ].join(" ");
        var content = null;
        if (flow.request.contentLength > 0) {
            content = "Request Content Size: " + toputils.formatSize(flow.request.contentLength);
        } else {
            content = React.createElement("div", {className: "alert alert-info"}, "No Content");
        }

        //TODO: Styling

        return (
            React.createElement("section", null, 
                React.createElement("div", {className: "first-line"}, first_line ), 
                React.createElement(Headers, {message: flow.request}), 
                React.createElement("hr", null), 
                content
            )
        );
    }
});

var FlowDetailResponse = React.createClass({displayName: "FlowDetailResponse",
    render: function () {
        var flow = this.props.flow;
        var first_line = [
            "HTTP/" + flow.response.httpversion.join("."),
            flow.response.code,
            flow.response.msg
        ].join(" ");
        var content = null;
        if (flow.response.contentLength > 0) {
            content = "Response Content Size: " + toputils.formatSize(flow.response.contentLength);
        } else {
            content = React.createElement("div", {className: "alert alert-info"}, "No Content");
        }

        //TODO: Styling

        return (
            React.createElement("section", null, 
                React.createElement("div", {className: "first-line"}, first_line ), 
                React.createElement(Headers, {message: flow.response}), 
                React.createElement("hr", null), 
                content
            )
        );
    }
});

var FlowDetailError = React.createClass({displayName: "FlowDetailError",
    render: function () {
        var flow = this.props.flow;
        return (
            React.createElement("section", null, 
                React.createElement("div", {className: "alert alert-warning"}, 
                flow.error.msg, 
                    React.createElement("div", null, 
                        React.createElement("small", null,  toputils.formatTimeStamp(flow.error.timestamp) )
                    )
                )
            )
        );
    }
});

var TimeStamp = React.createClass({displayName: "TimeStamp",
    render: function () {

        if (!this.props.t) {
            //should be return null, but that triggers a React bug.
            return React.createElement("tr", null);
        }

        var ts = toputils.formatTimeStamp(this.props.t);

        var delta;
        if (this.props.deltaTo) {
            delta = toputils.formatTimeDelta(1000 * (this.props.t - this.props.deltaTo));
            delta = React.createElement("span", {className: "text-muted"}, "(" + delta + ")");
        } else {
            delta = null;
        }

        return React.createElement("tr", null, 
            React.createElement("td", null, this.props.title + ":"), 
            React.createElement("td", null, ts, " ", delta)
        );
    }
});

var ConnectionInfo = React.createClass({displayName: "ConnectionInfo",

    render: function () {
        var conn = this.props.conn;
        var address = conn.address.address.join(":");

        var sni = React.createElement("tr", {key: "sni"}); //should be null, but that triggers a React bug.
        if (conn.sni) {
            sni = React.createElement("tr", {key: "sni"}, 
                React.createElement("td", null, 
                    React.createElement("abbr", {title: "TLS Server Name Indication"}, "TLS SNI:")
                ), 
                React.createElement("td", null, conn.sni)
            );
        }
        return (
            React.createElement("table", {className: "connection-table"}, 
                React.createElement("tbody", null, 
                    React.createElement("tr", {key: "address"}, 
                        React.createElement("td", null, "Address:"), 
                        React.createElement("td", null, address)
                    ), 
                    sni
                )
            )
        );
    }
});

var CertificateInfo = React.createClass({displayName: "CertificateInfo",
    render: function () {
        //TODO: We should fetch human-readable certificate representation
        // from the server
        var flow = this.props.flow;
        var client_conn = flow.client_conn;
        var server_conn = flow.server_conn;

        var preStyle = {maxHeight: 100};
        return (
            React.createElement("div", null, 
            client_conn.cert ? React.createElement("h4", null, "Client Certificate") : null, 
            client_conn.cert ? React.createElement("pre", {style: preStyle}, client_conn.cert) : null, 

            server_conn.cert ? React.createElement("h4", null, "Server Certificate") : null, 
            server_conn.cert ? React.createElement("pre", {style: preStyle}, server_conn.cert) : null
            )
        );
    }
});

var Timing = React.createClass({displayName: "Timing",
    render: function () {
        var flow = this.props.flow;
        var sc = flow.server_conn;
        var cc = flow.client_conn;
        var req = flow.request;
        var resp = flow.response;

        var timestamps = [
            {
                title: "Server conn. initiated",
                t: sc.timestamp_start,
                deltaTo: req.timestamp_start
            }, {
                title: "Server conn. TCP handshake",
                t: sc.timestamp_tcp_setup,
                deltaTo: req.timestamp_start
            }, {
                title: "Server conn. SSL handshake",
                t: sc.timestamp_ssl_setup,
                deltaTo: req.timestamp_start
            }, {
                title: "Client conn. established",
                t: cc.timestamp_start,
                deltaTo: req.timestamp_start
            }, {
                title: "Client conn. SSL handshake",
                t: cc.timestamp_ssl_setup,
                deltaTo: req.timestamp_start
            }, {
                title: "First request byte",
                t: req.timestamp_start,
            }, {
                title: "Request complete",
                t: req.timestamp_end,
                deltaTo: req.timestamp_start
            }
        ];

        if (flow.response) {
            timestamps.push(
                {
                    title: "First response byte",
                    t: resp.timestamp_start,
                    deltaTo: req.timestamp_start
                }, {
                    title: "Response complete",
                    t: resp.timestamp_end,
                    deltaTo: req.timestamp_start
                }
            );
        }

        //Add unique key for each row.
        timestamps.forEach(function (e) {
            e.key = e.title;
        });

        timestamps = _.sortBy(timestamps, 't');

        var rows = timestamps.map(function (e) {
            return React.createElement(TimeStamp, React.__spread({},  e));
        });

        return (
            React.createElement("div", null, 
                React.createElement("h4", null, "Timing"), 
                React.createElement("table", {className: "timing-table"}, 
                    React.createElement("tbody", null, 
                    rows
                    )
                )
            )
        );
    }
});

var FlowDetailConnectionInfo = React.createClass({displayName: "FlowDetailConnectionInfo",
    render: function () {
        var flow = this.props.flow;
        var client_conn = flow.client_conn;
        var server_conn = flow.server_conn;
        return (
            React.createElement("section", null, 

                React.createElement("h4", null, "Client Connection"), 
                React.createElement(ConnectionInfo, {conn: client_conn}), 

                React.createElement("h4", null, "Server Connection"), 
                React.createElement(ConnectionInfo, {conn: server_conn}), 

                React.createElement(CertificateInfo, {flow: flow}), 

                React.createElement(Timing, {flow: flow})

            )
        );
    }
});

var allTabs = {
    request: FlowDetailRequest,
    response: FlowDetailResponse,
    error: FlowDetailError,
    details: FlowDetailConnectionInfo
};

var FlowDetail = React.createClass({displayName: "FlowDetail",
    mixins: [utils.StickyHeadMixin, utils.Navigation, utils.State],
    getTabs: function (flow) {
        var tabs = [];
        ["request", "response", "error"].forEach(function (e) {
            if (flow[e]) {
                tabs.push(e);
            }
        });
        tabs.push("details");
        return tabs;
    },
    nextTab: function (i) {
        var tabs = this.getTabs(this.props.flow);
        var currentIndex = tabs.indexOf(this.getParams().detailTab);
        // JS modulo operator doesn't correct negative numbers, make sure that we are positive.
        var nextIndex = (currentIndex + i + tabs.length) % tabs.length;
        this.selectTab(tabs[nextIndex]);
    },
    selectTab: function (panel) {
        this.replaceWith(
            "flow",
            {
                flowId: this.getParams().flowId,
                detailTab: panel
            }
        );
    },
    render: function () {
        var flow = this.props.flow;
        var tabs = this.getTabs(flow);
        var active = this.getParams().detailTab;

        if (!_.contains(tabs, active)) {
            if (active === "response" && flow.error) {
                active = "error";
            } else if (active === "error" && flow.response) {
                active = "response";
            } else {
                active = tabs[0];
            }
            this.selectTab(active);
        }

        var Tab = allTabs[active];
        return (
            React.createElement("div", {className: "flow-detail", onScroll: this.adjustHead}, 
                React.createElement(FlowDetailNav, {ref: "head", 
                    flow: flow, 
                    tabs: tabs, 
                    active: active, 
                    selectTab: this.selectTab}), 
                React.createElement(Tab, {flow: flow})
            )
        );
    }
});

module.exports = {
    FlowDetail: FlowDetail
};
},{"../actions.js":1,"../flow/utils.js":15,"../utils.js":18,"./utils.jsx.js":10,"lodash":"lodash","react":"react"}],4:[function(require,module,exports){
var React = require("react");
var flowutils = require("../flow/utils.js");
var utils = require("../utils.js");

var TLSColumn = React.createClass({displayName: "TLSColumn",
    statics: {
        renderTitle: function () {
            return React.createElement("th", {key: "tls", className: "col-tls"});
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
        return React.createElement("td", {className: classes});
    }
});


var IconColumn = React.createClass({displayName: "IconColumn",
    statics: {
        renderTitle: function () {
            return React.createElement("th", {key: "icon", className: "col-icon"});
        }
    },
    render: function () {
        var flow = this.props.flow;

        var icon;
        if (flow.response) {
            var contentType = flowutils.ResponseUtils.getContentType(flow.response);

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
        return React.createElement("td", {className: "col-icon"}, 
            React.createElement("div", {className: icon})
        );
    }
});

var PathColumn = React.createClass({displayName: "PathColumn",
    statics: {
        renderTitle: function () {
            return React.createElement("th", {key: "path", className: "col-path"}, "Path");
        }
    },
    render: function () {
        var flow = this.props.flow;
        return React.createElement("td", {className: "col-path"}, 
            flow.request.is_replay ? React.createElement("i", {className: "fa fa-fw fa-repeat pull-right"}) : null, 
            flow.intercepted ? React.createElement("i", {className: "fa fa-fw fa-pause pull-right"}) : null, 
            flow.request.scheme + "://" + flow.request.host + flow.request.path
        );
    }
});


var MethodColumn = React.createClass({displayName: "MethodColumn",
    statics: {
        renderTitle: function () {
            return React.createElement("th", {key: "method", className: "col-method"}, "Method");
        }
    },
    render: function () {
        var flow = this.props.flow;
        return React.createElement("td", {className: "col-method"}, flow.request.method);
    }
});


var StatusColumn = React.createClass({displayName: "StatusColumn",
    statics: {
        renderTitle: function () {
            return React.createElement("th", {key: "status", className: "col-status"}, "Status");
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
        return React.createElement("td", {className: "col-status"}, status);
    }
});


var SizeColumn = React.createClass({displayName: "SizeColumn",
    statics: {
        renderTitle: function () {
            return React.createElement("th", {key: "size", className: "col-size"}, "Size");
        }
    },
    render: function () {
        var flow = this.props.flow;

        var total = flow.request.contentLength;
        if (flow.response) {
            total += flow.response.contentLength || 0;
        }
        var size = utils.formatSize(total);
        return React.createElement("td", {className: "col-size"}, size);
    }
});


var TimeColumn = React.createClass({displayName: "TimeColumn",
    statics: {
        renderTitle: function () {
            return React.createElement("th", {key: "time", className: "col-time"}, "Time");
        }
    },
    render: function () {
        var flow = this.props.flow;
        var time;
        if (flow.response) {
            time = utils.formatTimeDelta(1000 * (flow.response.timestamp_end - flow.request.timestamp_start));
        } else {
            time = "...";
        }
        return React.createElement("td", {className: "col-time"}, time);
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


module.exports = all_columns;



},{"../flow/utils.js":15,"../utils.js":18,"react":"react"}],5:[function(require,module,exports){
var React = require("react");
var utils = require("./utils.jsx.js");
var VirtualScrollMixin = require("./virtualscroll.jsx.js");
var flowtable_columns = require("./flowtable-columns.jsx.js");

var FlowRow = React.createClass({displayName: "FlowRow",
    render: function () {
        var flow = this.props.flow;
        var columns = this.props.columns.map(function (Column) {
            return React.createElement(Column, {key: Column.displayName, flow: flow});
        }.bind(this));
        var className = "";
        if (this.props.selected) {
            className += " selected";
        }
        if (this.props.highlighted) {
            className += " highlighted";
        }
        if (flow.intercepted) {
            className += " intercepted";
        }
        if (flow.request) {
            className += " has-request";
        }
        if (flow.response) {
            className += " has-response";
        }

        return (
            React.createElement("tr", {className: className, onClick: this.props.selectFlow.bind(null, flow)}, 
                columns
            ));
    },
    shouldComponentUpdate: function (nextProps) {
        return true;
        // Further optimization could be done here
        // by calling forceUpdate on flow updates, selection changes and column changes.
        //return (
        //(this.props.columns.length !== nextProps.columns.length) ||
        //(this.props.selected !== nextProps.selected)
        //);
    }
});

var FlowTableHead = React.createClass({displayName: "FlowTableHead",
    render: function () {
        var columns = this.props.columns.map(function (column) {
            return column.renderTitle();
        }.bind(this));
        return React.createElement("thead", null, 
            React.createElement("tr", null, columns)
        );
    }
});


var ROW_HEIGHT = 32;

var FlowTable = React.createClass({displayName: "FlowTable",
    mixins: [utils.StickyHeadMixin, utils.AutoScrollMixin, VirtualScrollMixin],
    getInitialState: function () {
        return {
            columns: flowtable_columns
        };
    },
    componentWillMount: function () {
        if (this.props.view) {
            this.props.view.addListener("add update remove recalculate", this.onChange);
        }
    },
    componentWillReceiveProps: function (nextProps) {
        if (nextProps.view !== this.props.view) {
            if (this.props.view) {
                this.props.view.removeListener("add update remove recalculate");
            }
            nextProps.view.addListener("add update remove recalculate", this.onChange);
        }
    },
    getDefaultProps: function () {
        return {
            rowHeight: ROW_HEIGHT
        };
    },
    onScrollFlowTable: function () {
        this.adjustHead();
        this.onScroll();
    },
    onChange: function () {
        this.forceUpdate();
    },
    scrollIntoView: function (flow) {
        this.scrollRowIntoView(
            this.props.view.index(flow),
            this.refs.body.getDOMNode().offsetTop
        );
    },
    renderRow: function (flow) {
        var selected = (flow === this.props.selected);
        var highlighted =
            (
            this.props.view._highlight &&
            this.props.view._highlight[flow.id]
            );

        return React.createElement(FlowRow, {key: flow.id, 
            ref: flow.id, 
            flow: flow, 
            columns: this.state.columns, 
            selected: selected, 
            highlighted: highlighted, 
            selectFlow: this.props.selectFlow}
        );
    },
    render: function () {
        //console.log("render flowtable", this.state.start, this.state.stop, this.props.selected);
        var flows = this.props.view ? this.props.view.list : [];

        var rows = this.renderRows(flows);

        return (
            React.createElement("div", {className: "flow-table", onScroll: this.onScrollFlowTable}, 
                React.createElement("table", null, 
                    React.createElement(FlowTableHead, {ref: "head", 
                        columns: this.state.columns}), 
                    React.createElement("tbody", {ref: "body"}, 
                         this.getPlaceholderTop(flows.length), 
                        rows, 
                         this.getPlaceholderBottom(flows.length) 
                    )
                )
            )
        );
    }
});

module.exports = FlowTable;

},{"./flowtable-columns.jsx.js":4,"./utils.jsx.js":10,"./virtualscroll.jsx.js":11,"react":"react"}],6:[function(require,module,exports){
var React = require("react");

var Footer = React.createClass({displayName: "Footer",
    render: function () {
        var mode = this.props.settings.mode;
        var intercept = this.props.settings.intercept;
        return (
            React.createElement("footer", null, 
                mode != "regular" ? React.createElement("span", {className: "label label-success"}, mode, " mode") : null, 
                " ", 
                intercept ? React.createElement("span", {className: "label label-success"}, "Intercept: ", intercept) : null
            )
        );
    }
});

module.exports = Footer;
},{"react":"react"}],7:[function(require,module,exports){
var React = require("react");
var $ = require("jquery");

var utils = require("./utils.jsx.js");

var FilterDocs = React.createClass({displayName: "FilterDocs",
    statics: {
        xhr: false,
        doc: false
    },
    componentWillMount: function () {
        if (!FilterDocs.doc) {
            FilterDocs.xhr = $.getJSON("/filter-help").done(function (doc) {
                FilterDocs.doc = doc;
                FilterDocs.xhr = false;
            });
        }
        if (FilterDocs.xhr) {
            FilterDocs.xhr.done(function () {
                this.forceUpdate();
            }.bind(this));
        }
    },
    render: function () {
        if (!FilterDocs.doc) {
            return React.createElement("i", {className: "fa fa-spinner fa-spin"});
        } else {
            var commands = FilterDocs.doc.commands.map(function (c) {
                return React.createElement("tr", null, 
                    React.createElement("td", null, c[0].replace(" ", '\u00a0')), 
                    React.createElement("td", null, c[1])
                );
            });
            commands.push(React.createElement("tr", null, 
                React.createElement("td", {colSpan: "2"}, 
                    React.createElement("a", {href: "https://mitmproxy.org/doc/features/filters.html", 
                        target: "_blank"}, 
                        React.createElement("i", {className: "fa fa-external-link"}), 
                    "  mitmproxy docs")
                )
            ));
            return React.createElement("table", {className: "table table-condensed"}, 
                React.createElement("tbody", null, commands)
            );
        }
    }
});
var FilterInput = React.createClass({displayName: "FilterInput",
    getInitialState: function () {
        // Consider both focus and mouseover for showing/hiding the tooltip,
        // because onBlur of the input is triggered before the click on the tooltip
        // finalized, hiding the tooltip just as the user clicks on it.
        return {
            value: this.props.value,
            focus: false,
            mousefocus: false
        };
    },
    componentWillReceiveProps: function (nextProps) {
        this.setState({value: nextProps.value});
    },
    onChange: function (e) {
        var nextValue = e.target.value;
        this.setState({
            value: nextValue
        });
        // Only propagate valid filters upwards.
        if (this.isValid(nextValue)) {
            this.props.onChange(nextValue);
        }
    },
    isValid: function (filt) {
        try {
            Filt.parse(filt || this.state.value);
            return true;
        } catch (e) {
            return false;
        }
    },
    getDesc: function () {
        var desc;
        try {
            desc = Filt.parse(this.state.value).desc;
        } catch (e) {
            desc = "" + e;
        }
        if (desc !== "true") {
            return desc;
        } else {
            return (
                React.createElement(FilterDocs, null)
            );
        }
    },
    onFocus: function () {
        this.setState({focus: true});
    },
    onBlur: function () {
        this.setState({focus: false});
    },
    onMouseEnter: function () {
        this.setState({mousefocus: true});
    },
    onMouseLeave: function () {
        this.setState({mousefocus: false});
    },
    onKeyDown: function (e) {
        if (e.keyCode === Key.ESC || e.keyCode === Key.ENTER) {
            this.blur();
            // If closed using ESC/ENTER, hide the tooltip.
            this.setState({mousefocus: false});
        }
    },
    blur: function () {
        this.refs.input.getDOMNode().blur();
    },
    focus: function () {
        this.refs.input.getDOMNode().select();
    },
    render: function () {
        var isValid = this.isValid();
        var icon = "fa fa-fw fa-" + this.props.type;
        var groupClassName = "filter-input input-group" + (isValid ? "" : " has-error");

        var popover;
        if (this.state.focus || this.state.mousefocus) {
            popover = (
                React.createElement("div", {className: "popover bottom", onMouseEnter: this.onMouseEnter, onMouseLeave: this.onMouseLeave}, 
                    React.createElement("div", {className: "arrow"}), 
                    React.createElement("div", {className: "popover-content"}, 
                    this.getDesc()
                    )
                )
            );
        }

        return (
            React.createElement("div", {className: groupClassName}, 
                React.createElement("span", {className: "input-group-addon"}, 
                    React.createElement("i", {className: icon, style: {color: this.props.color}})
                ), 
                React.createElement("input", {type: "text", placeholder: this.props.placeholder, className: "form-control", 
                    ref: "input", 
                    onChange: this.onChange, 
                    onFocus: this.onFocus, 
                    onBlur: this.onBlur, 
                    onKeyDown: this.onKeyDown, 
                    value: this.state.value}), 
                popover
            )
        );
    }
});

var MainMenu = React.createClass({displayName: "MainMenu",
    mixins: [utils.Navigation, utils.State],
    statics: {
        title: "Start",
        route: "flows"
    },
    onFilterChange: function (val) {
        var d = {};
        d[Query.FILTER] = val;
        this.setQuery(d);
    },
    onHighlightChange: function (val) {
        var d = {};
        d[Query.HIGHLIGHT] = val;
        this.setQuery(d);
    },
    onInterceptChange: function (val) {
        SettingsActions.update({intercept: val});
    },
    render: function () {
        var filter = this.getQuery()[Query.FILTER] || "";
        var highlight = this.getQuery()[Query.HIGHLIGHT] || "";
        var intercept = this.props.settings.intercept || "";

        return (
            React.createElement("div", null, 
                React.createElement("div", {className: "menu-row"}, 
                    React.createElement(FilterInput, {
                        placeholder: "Filter", 
                        type: "filter", 
                        color: "black", 
                        value: filter, 
                        onChange: this.onFilterChange}), 
                    React.createElement(FilterInput, {
                        placeholder: "Highlight", 
                        type: "tag", 
                        color: "hsl(48, 100%, 50%)", 
                        value: highlight, 
                        onChange: this.onHighlightChange}), 
                    React.createElement(FilterInput, {
                        placeholder: "Intercept", 
                        type: "pause", 
                        color: "hsl(208, 56%, 53%)", 
                        value: intercept, 
                        onChange: this.onInterceptChange})
                ), 
                React.createElement("div", {className: "clearfix"})
            )
        );
    }
});


var ViewMenu = React.createClass({displayName: "ViewMenu",
    statics: {
        title: "View",
        route: "flows"
    },
    mixins: [utils.Navigation, utils.State],
    toggleEventLog: function () {
        var d = {};

        if (this.getQuery()[Query.SHOW_EVENTLOG]) {
            d[Query.SHOW_EVENTLOG] = undefined;
        } else {
            d[Query.SHOW_EVENTLOG] = "t"; // any non-false value will do it, keep it short
        }

        this.setQuery(d);
    },
    render: function () {
        var showEventLog = this.getQuery()[Query.SHOW_EVENTLOG];
        return (
            React.createElement("div", null, 
                React.createElement("button", {
                    className: "btn " + (showEventLog ? "btn-primary" : "btn-default"), 
                    onClick: this.toggleEventLog}, 
                    React.createElement("i", {className: "fa fa-database"}), 
                " Show Eventlog"
                ), 
                React.createElement("span", null, " ")
            )
        );
    }
});


var ReportsMenu = React.createClass({displayName: "ReportsMenu",
    statics: {
        title: "Visualization",
        route: "reports"
    },
    render: function () {
        return React.createElement("div", null, "Reports Menu");
    }
});

var FileMenu = React.createClass({displayName: "FileMenu",
    getInitialState: function () {
        return {
            showFileMenu: false
        };
    },
    handleFileClick: function (e) {
        e.preventDefault();
        if (!this.state.showFileMenu) {
            var close = function () {
                this.setState({showFileMenu: false});
                document.removeEventListener("click", close);
            }.bind(this);
            document.addEventListener("click", close);

            this.setState({
                showFileMenu: true
            });
        }
    },
    handleNewClick: function (e) {
        e.preventDefault();
        if (confirm("Delete all flows?")) {
            FlowActions.clear();
        }
    },
    handleOpenClick: function (e) {
        e.preventDefault();
        console.error("unimplemented: handleOpenClick");
    },
    handleSaveClick: function (e) {
        e.preventDefault();
        console.error("unimplemented: handleSaveClick");
    },
    handleShutdownClick: function (e) {
        e.preventDefault();
        console.error("unimplemented: handleShutdownClick");
    },
    render: function () {
        var fileMenuClass = "dropdown pull-left" + (this.state.showFileMenu ? " open" : "");

        return (
            React.createElement("div", {className: fileMenuClass}, 
                React.createElement("a", {href: "#", className: "special", onClick: this.handleFileClick}, " File "), 
                React.createElement("ul", {className: "dropdown-menu", role: "menu"}, 
                    React.createElement("li", null, 
                        React.createElement("a", {href: "#", onClick: this.handleNewClick}, 
                            React.createElement("i", {className: "fa fa-fw fa-file"}), 
                            "New"
                        )
                    ), 
                    React.createElement("li", {role: "presentation", className: "divider"}), 
                    React.createElement("li", null, 
                        React.createElement("a", {href: "http://mitm.it/", target: "_blank"}, 
                            React.createElement("i", {className: "fa fa-fw fa-external-link"}), 
                            "Install Certificates..."
                        )
                    )
                /*
                 <li>
                 <a href="#" onClick={this.handleOpenClick}>
                 <i className="fa fa-fw fa-folder-open"></i>
                 Open
                 </a>
                 </li>
                 <li>
                 <a href="#" onClick={this.handleSaveClick}>
                 <i className="fa fa-fw fa-save"></i>
                 Save
                 </a>
                 </li>
                 <li role="presentation" className="divider"></li>
                 <li>
                 <a href="#" onClick={this.handleShutdownClick}>
                 <i className="fa fa-fw fa-plug"></i>
                 Shutdown
                 </a>
                 </li>
                 */
                )
            )
        );
    }
});


var header_entries = [MainMenu, ViewMenu /*, ReportsMenu */];


var Header = React.createClass({displayName: "Header",
    mixins: [utils.Navigation],
    getInitialState: function () {
        return {
            active: header_entries[0]
        };
    },
    handleClick: function (active, e) {
        e.preventDefault();
        this.replaceWith(active.route);
        this.setState({active: active});
    },
    render: function () {
        var header = header_entries.map(function (entry, i) {
            var classes = React.addons.classSet({
                active: entry == this.state.active
            });
            return (
                React.createElement("a", {key: i, 
                    href: "#", 
                    className: classes, 
                    onClick: this.handleClick.bind(this, entry)
                }, 
                     entry.title
                )
            );
        }.bind(this));

        return (
            React.createElement("header", null, 
                React.createElement("div", {className: "title-bar"}, 
                    "mitmproxy ",  this.props.settings.version
                ), 
                React.createElement("nav", {className: "nav-tabs nav-tabs-lg"}, 
                    React.createElement(FileMenu, null), 
                    header
                ), 
                React.createElement("div", {className: "menu"}, 
                    React.createElement(this.state.active, {settings: this.props.settings})
                )
            )
        );
    }
});


module.exports = {
    Header: Header
}
},{"./utils.jsx.js":10,"jquery":"jquery","react":"react"}],8:[function(require,module,exports){
var React = require("react");

var utils = require("./utils.jsx.js");
var views = require("../store/view.js");
var Filt = require("../filt/filt.js");
FlowTable = require("./flowtable.jsx.js");
var flowdetail = require("./flowdetail.jsx.js");


var MainView = React.createClass({displayName: "MainView",
    mixins: [utils.Navigation, utils.State],
    getInitialState: function () {
        this.onQueryChange(Query.FILTER, function () {
            this.state.view.recalculate(this.getViewFilt(), this.getViewSort());
        }.bind(this));
        this.onQueryChange(Query.HIGHLIGHT, function () {
            this.state.view.recalculate(this.getViewFilt(), this.getViewSort());
        }.bind(this));
        return {
            flows: []
        };
    },
    getViewFilt: function () {
        try {
            var filt = Filt.parse(this.getQuery()[Query.FILTER] || "");
            var highlightStr = this.getQuery()[Query.HIGHLIGHT];
            var highlight = highlightStr ? Filt.parse(highlightStr) : false;
        } catch (e) {
            console.error("Error when processing filter: " + e);
        }

        return function filter_and_highlight(flow) {
            if (!this._highlight) {
                this._highlight = {};
            }
            this._highlight[flow.id] = highlight && highlight(flow);
            return filt(flow);
        };
    },
    getViewSort: function () {
    },
    componentWillReceiveProps: function (nextProps) {
        if (nextProps.flowStore !== this.props.flowStore) {
            this.closeView();
            this.openView(nextProps.flowStore);
        }
    },
    openView: function (store) {
        var view = new views.StoreView(store, this.getViewFilt(), this.getViewSort());
        this.setState({
            view: view
        });

        view.addListener("recalculate", this.onRecalculate);
        view.addListener("add update remove", this.onUpdate);
        view.addListener("remove", this.onRemove);
    },
    onRecalculate: function () {
        this.forceUpdate();
        var selected = this.getSelected();
        if (selected) {
            this.refs.flowTable.scrollIntoView(selected);
        }
    },
    onUpdate: function (flow) {
        if (flow.id === this.getParams().flowId) {
            this.forceUpdate();
        }
    },
    onRemove: function (flow_id, index) {
        if (flow_id === this.getParams().flowId) {
            var flow_to_select = this.state.view.list[Math.min(index, this.state.view.list.length -1)];
            this.selectFlow(flow_to_select);
        }
    },
    closeView: function () {
        this.state.view.close();
    },
    componentWillMount: function () {
        this.openView(this.props.flowStore);
    },
    componentWillUnmount: function () {
        this.closeView();
    },
    selectFlow: function (flow) {
        if (flow) {
            this.replaceWith(
                "flow",
                {
                    flowId: flow.id,
                    detailTab: this.getParams().detailTab || "request"
                }
            );
            this.refs.flowTable.scrollIntoView(flow);
        } else {
            this.replaceWith("flows", {});
        }
    },
    selectFlowRelative: function (shift) {
        var flows = this.state.view.list;
        var index;
        if (!this.getParams().flowId) {
            if (shift > 0) {
                index = flows.length - 1;
            } else {
                index = 0;
            }
        } else {
            var currFlowId = this.getParams().flowId;
            var i = flows.length;
            while (i--) {
                if (flows[i].id === currFlowId) {
                    index = i;
                    break;
                }
            }
            index = Math.min(
                Math.max(0, index + shift),
                flows.length - 1);
        }
        this.selectFlow(flows[index]);
    },
    onKeyDown: function (e) {
        var flow = this.getSelected();
        if (e.ctrlKey) {
            return;
        }
        switch (e.keyCode) {
            case Key.K:
            case Key.UP:
                this.selectFlowRelative(-1);
                break;
            case Key.J:
            case Key.DOWN:
                this.selectFlowRelative(+1);
                break;
            case Key.SPACE:
            case Key.PAGE_DOWN:
                this.selectFlowRelative(+10);
                break;
            case Key.PAGE_UP:
                this.selectFlowRelative(-10);
                break;
            case Key.END:
                this.selectFlowRelative(+1e10);
                break;
            case Key.HOME:
                this.selectFlowRelative(-1e10);
                break;
            case Key.ESC:
                this.selectFlow(null);
                break;
            case Key.H:
            case Key.LEFT:
                if (this.refs.flowDetails) {
                    this.refs.flowDetails.nextTab(-1);
                }
                break;
            case Key.L:
            case Key.TAB:
            case Key.RIGHT:
                if (this.refs.flowDetails) {
                    this.refs.flowDetails.nextTab(+1);
                }
                break;
            case Key.C:
                if (e.shiftKey) {
                    FlowActions.clear();
                }
                break;
            case Key.D:
                if (flow) {
                    if (e.shiftKey) {
                        FlowActions.duplicate(flow);
                    } else {
                        FlowActions.delete(flow);
                    }
                }
                break;
            case Key.A:
                if (e.shiftKey) {
                    FlowActions.accept_all();
                } else if (flow && flow.intercepted) {
                    FlowActions.accept(flow);
                }
                break;
            case Key.R:
                if (!e.shiftKey && flow) {
                    FlowActions.replay(flow);
                }
                break;
            case Key.V:
                if(e.shiftKey && flow && flow.modified) {
                    FlowActions.revert(flow);
                }
                break;
            default:
                console.debug("keydown", e.keyCode);
                return;
        }
        e.preventDefault();
    },
    getSelected: function () {
        return this.props.flowStore.get(this.getParams().flowId);
    },
    render: function () {
        var selected = this.getSelected();

        var details;
        if (selected) {
            details = [
                React.createElement(utils.Splitter, {key: "splitter"}),
                React.createElement(flowdetail.FlowDetail, {key: "flowDetails", ref: "flowDetails", flow: selected})
            ];
        } else {
            details = null;
        }

        return (
            React.createElement("div", {className: "main-view", onKeyDown: this.onKeyDown, tabIndex: "0"}, 
                React.createElement(FlowTable, {ref: "flowTable", 
                    view: this.state.view, 
                    selectFlow: this.selectFlow, 
                    selected: selected}), 
                details
            )
        );
    }
});

module.exports = MainView;

},{"../filt/filt.js":14,"../store/view.js":17,"./flowdetail.jsx.js":3,"./flowtable.jsx.js":5,"./utils.jsx.js":10,"react":"react"}],9:[function(require,module,exports){
var React = require("react");
var ReactRouter = require("react-router");
var _ = require("lodash");

var utils = require("./utils.jsx.js");
var MainView = require("./mainview.jsx.js");
var Footer = require("./footer.jsx.js");
var header = require("./header.jsx.js");
var store = require("../store/store.js");


//TODO: Move out of here, just a stub.
var Reports = React.createClass({displayName: "Reports",
    render: function () {
        return React.createElement("div", null, "ReportEditor");
    }
});


var ProxyAppMain = React.createClass({displayName: "ProxyAppMain",
    mixins: [utils.State],
    getInitialState: function () {
        var eventStore = new store.EventLogStore();
        var flowStore = new store.FlowStore();
        var settings = new store.SettingsStore();

        // Default Settings before fetch
        _.extend(settings.dict,{
        });
        return {
            settings: settings,
            flowStore: flowStore,
            eventStore: eventStore
        };
    },
    componentDidMount: function () {
        this.state.settings.addListener("recalculate", this.onSettingsChange);
        window.app = this;
    },
    componentWillUnmount: function () {
        this.state.settings.removeListener("recalculate", this.onSettingsChange);
    },
    onSettingsChange: function(){
        this.setState({
            settings: this.state.settings
        });
    },
    render: function () {

        var eventlog;
        if (this.getQuery()[Query.SHOW_EVENTLOG]) {
            eventlog = [
                React.createElement(Splitter, {key: "splitter", axis: "y"}),
                React.createElement(EventLog, {key: "eventlog", eventStore: this.state.eventStore})
            ];
        } else {
            eventlog = null;
        }

        return (
            React.createElement("div", {id: "container"}, 
                React.createElement(header.Header, {settings: this.state.settings.dict}), 
                React.createElement(RouteHandler, {settings: this.state.settings.dict, flowStore: this.state.flowStore}), 
                eventlog, 
                React.createElement(Footer, {settings: this.state.settings.dict})
            )
        );
    }
});


var Route = ReactRouter.Route;
var RouteHandler = ReactRouter.RouteHandler;
var Redirect = ReactRouter.Redirect;
var DefaultRoute = ReactRouter.DefaultRoute;
var NotFoundRoute = ReactRouter.NotFoundRoute;


var routes = (
    React.createElement(Route, {path: "/", handler: ProxyAppMain}, 
        React.createElement(Route, {name: "flows", path: "flows", handler: MainView}), 
        React.createElement(Route, {name: "flow", path: "flows/:flowId/:detailTab", handler: MainView}), 
        React.createElement(Route, {name: "reports", handler: Reports}), 
        React.createElement(Redirect, {path: "/", to: "flows"})
    )
);

module.exports = {
    routes: routes
};


},{"../store/store.js":16,"./footer.jsx.js":6,"./header.jsx.js":7,"./mainview.jsx.js":8,"./utils.jsx.js":10,"lodash":"lodash","react":"react","react-router":"react-router"}],10:[function(require,module,exports){
var React = require("react");
var ReactRouter = require("react-router");
var _ = require("lodash");

//React utils. For other utilities, see ../utils.js

// http://blog.vjeux.com/2013/javascript/scroll-position-with-react.html (also contains inverse example)
var AutoScrollMixin = {
    componentWillUpdate: function () {
        var node = this.getDOMNode();
        this._shouldScrollBottom = (
            node.scrollTop !== 0 &&
            node.scrollTop + node.clientHeight === node.scrollHeight
        );
    },
    componentDidUpdate: function () {
        if (this._shouldScrollBottom) {
            var node = this.getDOMNode();
            node.scrollTop = node.scrollHeight;
        }
    },
};


var StickyHeadMixin = {
    adjustHead: function () {
        // Abusing CSS transforms to set the element
        // referenced as head into some kind of position:sticky.
        var head = this.refs.head.getDOMNode();
        head.style.transform = "translate(0," + this.getDOMNode().scrollTop + "px)";
    }
};


var Navigation = _.extend({}, ReactRouter.Navigation, {
    setQuery: function (dict) {
        var q = this.context.getCurrentQuery();
        for(var i in dict){
            if(dict.hasOwnProperty(i)){
                q[i] = dict[i] || undefined; //falsey values shall be removed.
            }
        }
        q._ = "_"; // workaround for https://github.com/rackt/react-router/pull/599
        this.replaceWith(this.context.getCurrentPath(), this.context.getCurrentParams(), q);
    },
    replaceWith: function(routeNameOrPath, params, query) {
        if(routeNameOrPath === undefined){
            routeNameOrPath = this.context.getCurrentPath();
        }
        if(params === undefined){
            params = this.context.getCurrentParams();
        }
        if(query === undefined){
            query = this.context.getCurrentQuery();
        }
        ReactRouter.Navigation.replaceWith.call(this, routeNameOrPath, params, query);
    }
});
_.extend(Navigation.contextTypes, ReactRouter.State.contextTypes);

var State = _.extend({}, ReactRouter.State, {
    getInitialState: function () {
        this._query = this.context.getCurrentQuery();
        this._queryWatches = [];
        return null;
    },
    onQueryChange: function (key, callback) {
        this._queryWatches.push({
            key: key,
            callback: callback
        });
    },
    componentWillReceiveProps: function (nextProps, nextState) {
        var q = this.context.getCurrentQuery();
        for (var i = 0; i < this._queryWatches.length; i++) {
            var watch = this._queryWatches[i];
            if (this._query[watch.key] !== q[watch.key]) {
                watch.callback(this._query[watch.key], q[watch.key], watch.key);
            }
        }
        this._query = q;
    }
});

var Splitter = React.createClass({displayName: "Splitter",
    getDefaultProps: function () {
        return {
            axis: "x"
        };
    },
    getInitialState: function () {
        return {
            applied: false,
            startX: false,
            startY: false
        };
    },
    onMouseDown: function (e) {
        this.setState({
            startX: e.pageX,
            startY: e.pageY
        });
        window.addEventListener("mousemove", this.onMouseMove);
        window.addEventListener("mouseup", this.onMouseUp);
        // Occasionally, only a dragEnd event is triggered, but no mouseUp.
        window.addEventListener("dragend", this.onDragEnd);
    },
    onDragEnd: function () {
        this.getDOMNode().style.transform = "";
        window.removeEventListener("dragend", this.onDragEnd);
        window.removeEventListener("mouseup", this.onMouseUp);
        window.removeEventListener("mousemove", this.onMouseMove);
    },
    onMouseUp: function (e) {
        this.onDragEnd();

        var node = this.getDOMNode();
        var prev = node.previousElementSibling;
        var next = node.nextElementSibling;

        var dX = e.pageX - this.state.startX;
        var dY = e.pageY - this.state.startY;
        var flexBasis;
        if (this.props.axis === "x") {
            flexBasis = prev.offsetWidth + dX;
        } else {
            flexBasis = prev.offsetHeight + dY;
        }

        prev.style.flex = "0 0 " + Math.max(0, flexBasis) + "px";
        next.style.flex = "1 1 auto";

        this.setState({
            applied: true
        });
        this.onResize();
    },
    onMouseMove: function (e) {
        var dX = 0, dY = 0;
        if (this.props.axis === "x") {
            dX = e.pageX - this.state.startX;
        } else {
            dY = e.pageY - this.state.startY;
        }
        this.getDOMNode().style.transform = "translate(" + dX + "px," + dY + "px)";
    },
    onResize: function () {
        // Trigger a global resize event. This notifies components that employ virtual scrolling
        // that their viewport may have changed.
        window.setTimeout(function () {
            window.dispatchEvent(new CustomEvent("resize"));
        }, 1);
    },
    reset: function (willUnmount) {
        if (!this.state.applied) {
            return;
        }
        var node = this.getDOMNode();
        var prev = node.previousElementSibling;
        var next = node.nextElementSibling;

        prev.style.flex = "";
        next.style.flex = "";

        if (!willUnmount) {
            this.setState({
                applied: false
            });
        }
        this.onResize();
    },
    componentWillUnmount: function () {
        this.reset(true);
    },
    render: function () {
        var className = "splitter";
        if (this.props.axis === "x") {
            className += " splitter-x";
        } else {
            className += " splitter-y";
        }
        return (
            React.createElement("div", {className: className}, 
                React.createElement("div", {onMouseDown: this.onMouseDown, draggable: "true"})
            )
        );
    }
});

module.exports = {
    State: State,
    Navigation: Navigation,
    StickyHeadMixin: StickyHeadMixin,
    AutoScrollMixin: AutoScrollMixin,
    Splitter: Splitter
}
},{"lodash":"lodash","react":"react","react-router":"react-router"}],11:[function(require,module,exports){
var React = require("react");

var VirtualScrollMixin = {
    getInitialState: function () {
        return {
            start: 0,
            stop: 0
        };
    },
    componentWillMount: function () {
        if (!this.props.rowHeight) {
            console.warn("VirtualScrollMixin: No rowHeight specified", this);
        }
    },
    getPlaceholderTop: function (total) {
        var Tag = this.props.placeholderTagName || "tr";
        // When a large trunk of elements is removed from the button, start may be far off the viewport.
        // To make this issue less severe, limit the top placeholder to the total number of rows.
        var style = {
            height: Math.min(this.state.start, total) * this.props.rowHeight
        };
        var spacer = React.createElement(Tag, {key: "placeholder-top", style: style});

        if (this.state.start % 2 === 1) {
            // fix even/odd rows
            return [spacer, React.createElement(Tag, {key: "placeholder-top-2"})];
        } else {
            return spacer;
        }
    },
    getPlaceholderBottom: function (total) {
        var Tag = this.props.placeholderTagName || "tr";
        var style = {
            height: Math.max(0, total - this.state.stop) * this.props.rowHeight
        };
        return React.createElement(Tag, {key: "placeholder-bottom", style: style});
    },
    componentDidMount: function () {
        this.onScroll();
        window.addEventListener('resize', this.onScroll);
    },
    componentWillUnmount: function(){
        window.removeEventListener('resize', this.onScroll);
    },
    onScroll: function () {
        var viewport = this.getDOMNode();
        var top = viewport.scrollTop;
        var height = viewport.offsetHeight;
        var start = Math.floor(top / this.props.rowHeight);
        var stop = start + Math.ceil(height / (this.props.rowHeightMin || this.props.rowHeight));

        this.setState({
            start: start,
            stop: stop
        });
    },
    renderRows: function (elems) {
        var rows = [];
        var max = Math.min(elems.length, this.state.stop);

        for (var i = this.state.start; i < max; i++) {
            var elem = elems[i];
            rows.push(this.renderRow(elem));
        }
        return rows;
    },
    scrollRowIntoView: function (index, head_height) {

        var row_top = (index * this.props.rowHeight) + head_height;
        var row_bottom = row_top + this.props.rowHeight;

        var viewport = this.getDOMNode();
        var viewport_top = viewport.scrollTop;
        var viewport_bottom = viewport_top + viewport.offsetHeight;

        // Account for pinned thead
        if (row_top - head_height < viewport_top) {
            viewport.scrollTop = row_top - head_height;
        } else if (row_bottom > viewport_bottom) {
            viewport.scrollTop = row_bottom - viewport.offsetHeight;
        }
    },
};

module.exports  = VirtualScrollMixin;
},{"react":"react"}],12:[function(require,module,exports){

var actions = require("./actions.js");

function Connection(url) {
    if (url[0] === "/") {
        url = location.origin.replace("http", "ws") + url;
    }

    var ws = new WebSocket(url);
    ws.onopen = function () {
        actions.ConnectionActions.open();
    };
    ws.onmessage = function (message) {
        var m = JSON.parse(message.data);
        AppDispatcher.dispatchServerAction(m);
    };
    ws.onerror = function () {
        actions.ConnectionActions.error();
        EventLogActions.add_event("WebSocket connection error.");
    };
    ws.onclose = function () {
        actions.ConnectionActions.close();
        EventLogActions.add_event("WebSocket connection closed.");
    };
    return ws;
}

module.exports = Connection;
},{"./actions.js":1}],13:[function(require,module,exports){
const PayloadSources = {
    VIEW: "view",
    SERVER: "server"
};


function Dispatcher() {
    this.callbacks = [];
}
Dispatcher.prototype.register = function (callback) {
    this.callbacks.push(callback);
};
Dispatcher.prototype.unregister = function (callback) {
    var index = this.callbacks.indexOf(callback);
    if (index >= 0) {
        this.callbacks.splice(index, 1);
    }
};
Dispatcher.prototype.dispatch = function (payload) {
    console.debug("dispatch", payload);
    for (var i = 0; i < this.callbacks.length; i++) {
        this.callbacks[i](payload);
    }
};


AppDispatcher = new Dispatcher();
AppDispatcher.dispatchViewAction = function (action) {
    action.source = PayloadSources.VIEW;
    this.dispatch(action);
};
AppDispatcher.dispatchServerAction = function (action) {
    action.source = PayloadSources.SERVER;
    this.dispatch(action);
};

module.exports = {
    AppDispatcher: AppDispatcher
};
},{}],14:[function(require,module,exports){
/* jshint ignore:start */
Filt = (function() {
  /*
   * Generated by PEG.js 0.8.0.
   *
   * http://pegjs.majda.cz/
   */

  function peg$subclass(child, parent) {
    function ctor() { this.constructor = child; }
    ctor.prototype = parent.prototype;
    child.prototype = new ctor();
  }

  function SyntaxError(message, expected, found, offset, line, column) {
    this.message  = message;
    this.expected = expected;
    this.found    = found;
    this.offset   = offset;
    this.line     = line;
    this.column   = column;

    this.name     = "SyntaxError";
  }

  peg$subclass(SyntaxError, Error);

  function parse(input) {
    var options = arguments.length > 1 ? arguments[1] : {},

        peg$FAILED = {},

        peg$startRuleFunctions = { start: peg$parsestart },
        peg$startRuleFunction  = peg$parsestart,

        peg$c0 = { type: "other", description: "filter expression" },
        peg$c1 = peg$FAILED,
        peg$c2 = function(orExpr) { return orExpr; },
        peg$c3 = [],
        peg$c4 = function() {return trueFilter; },
        peg$c5 = { type: "other", description: "whitespace" },
        peg$c6 = /^[ \t\n\r]/,
        peg$c7 = { type: "class", value: "[ \\t\\n\\r]", description: "[ \\t\\n\\r]" },
        peg$c8 = { type: "other", description: "control character" },
        peg$c9 = /^[|&!()~"]/,
        peg$c10 = { type: "class", value: "[|&!()~\"]", description: "[|&!()~\"]" },
        peg$c11 = { type: "other", description: "optional whitespace" },
        peg$c12 = "|",
        peg$c13 = { type: "literal", value: "|", description: "\"|\"" },
        peg$c14 = function(first, second) { return or(first, second); },
        peg$c15 = "&",
        peg$c16 = { type: "literal", value: "&", description: "\"&\"" },
        peg$c17 = function(first, second) { return and(first, second); },
        peg$c18 = "!",
        peg$c19 = { type: "literal", value: "!", description: "\"!\"" },
        peg$c20 = function(expr) { return not(expr); },
        peg$c21 = "(",
        peg$c22 = { type: "literal", value: "(", description: "\"(\"" },
        peg$c23 = ")",
        peg$c24 = { type: "literal", value: ")", description: "\")\"" },
        peg$c25 = function(expr) { return binding(expr); },
        peg$c26 = "~a",
        peg$c27 = { type: "literal", value: "~a", description: "\"~a\"" },
        peg$c28 = function() { return assetFilter; },
        peg$c29 = "~e",
        peg$c30 = { type: "literal", value: "~e", description: "\"~e\"" },
        peg$c31 = function() { return errorFilter; },
        peg$c32 = "~q",
        peg$c33 = { type: "literal", value: "~q", description: "\"~q\"" },
        peg$c34 = function() { return noResponseFilter; },
        peg$c35 = "~s",
        peg$c36 = { type: "literal", value: "~s", description: "\"~s\"" },
        peg$c37 = function() { return responseFilter; },
        peg$c38 = "true",
        peg$c39 = { type: "literal", value: "true", description: "\"true\"" },
        peg$c40 = function() { return trueFilter; },
        peg$c41 = "false",
        peg$c42 = { type: "literal", value: "false", description: "\"false\"" },
        peg$c43 = function() { return falseFilter; },
        peg$c44 = "~c",
        peg$c45 = { type: "literal", value: "~c", description: "\"~c\"" },
        peg$c46 = function(s) { return responseCode(s); },
        peg$c47 = "~d",
        peg$c48 = { type: "literal", value: "~d", description: "\"~d\"" },
        peg$c49 = function(s) { return domain(s); },
        peg$c50 = "~h",
        peg$c51 = { type: "literal", value: "~h", description: "\"~h\"" },
        peg$c52 = function(s) { return header(s); },
        peg$c53 = "~hq",
        peg$c54 = { type: "literal", value: "~hq", description: "\"~hq\"" },
        peg$c55 = function(s) { return requestHeader(s); },
        peg$c56 = "~hs",
        peg$c57 = { type: "literal", value: "~hs", description: "\"~hs\"" },
        peg$c58 = function(s) { return responseHeader(s); },
        peg$c59 = "~m",
        peg$c60 = { type: "literal", value: "~m", description: "\"~m\"" },
        peg$c61 = function(s) { return method(s); },
        peg$c62 = "~t",
        peg$c63 = { type: "literal", value: "~t", description: "\"~t\"" },
        peg$c64 = function(s) { return contentType(s); },
        peg$c65 = "~tq",
        peg$c66 = { type: "literal", value: "~tq", description: "\"~tq\"" },
        peg$c67 = function(s) { return requestContentType(s); },
        peg$c68 = "~ts",
        peg$c69 = { type: "literal", value: "~ts", description: "\"~ts\"" },
        peg$c70 = function(s) { return responseContentType(s); },
        peg$c71 = "~u",
        peg$c72 = { type: "literal", value: "~u", description: "\"~u\"" },
        peg$c73 = function(s) { return url(s); },
        peg$c74 = { type: "other", description: "integer" },
        peg$c75 = null,
        peg$c76 = /^['"]/,
        peg$c77 = { type: "class", value: "['\"]", description: "['\"]" },
        peg$c78 = /^[0-9]/,
        peg$c79 = { type: "class", value: "[0-9]", description: "[0-9]" },
        peg$c80 = function(digits) { return parseInt(digits.join(""), 10); },
        peg$c81 = { type: "other", description: "string" },
        peg$c82 = "\"",
        peg$c83 = { type: "literal", value: "\"", description: "\"\\\"\"" },
        peg$c84 = function(chars) { return chars.join(""); },
        peg$c85 = "'",
        peg$c86 = { type: "literal", value: "'", description: "\"'\"" },
        peg$c87 = void 0,
        peg$c88 = /^["\\]/,
        peg$c89 = { type: "class", value: "[\"\\\\]", description: "[\"\\\\]" },
        peg$c90 = { type: "any", description: "any character" },
        peg$c91 = function(char) { return char; },
        peg$c92 = "\\",
        peg$c93 = { type: "literal", value: "\\", description: "\"\\\\\"" },
        peg$c94 = /^['\\]/,
        peg$c95 = { type: "class", value: "['\\\\]", description: "['\\\\]" },
        peg$c96 = /^['"\\]/,
        peg$c97 = { type: "class", value: "['\"\\\\]", description: "['\"\\\\]" },
        peg$c98 = "n",
        peg$c99 = { type: "literal", value: "n", description: "\"n\"" },
        peg$c100 = function() { return "\n"; },
        peg$c101 = "r",
        peg$c102 = { type: "literal", value: "r", description: "\"r\"" },
        peg$c103 = function() { return "\r"; },
        peg$c104 = "t",
        peg$c105 = { type: "literal", value: "t", description: "\"t\"" },
        peg$c106 = function() { return "\t"; },

        peg$currPos          = 0,
        peg$reportedPos      = 0,
        peg$cachedPos        = 0,
        peg$cachedPosDetails = { line: 1, column: 1, seenCR: false },
        peg$maxFailPos       = 0,
        peg$maxFailExpected  = [],
        peg$silentFails      = 0,

        peg$result;

    if ("startRule" in options) {
      if (!(options.startRule in peg$startRuleFunctions)) {
        throw new Error("Can't start parsing from rule \"" + options.startRule + "\".");
      }

      peg$startRuleFunction = peg$startRuleFunctions[options.startRule];
    }

    function text() {
      return input.substring(peg$reportedPos, peg$currPos);
    }

    function offset() {
      return peg$reportedPos;
    }

    function line() {
      return peg$computePosDetails(peg$reportedPos).line;
    }

    function column() {
      return peg$computePosDetails(peg$reportedPos).column;
    }

    function expected(description) {
      throw peg$buildException(
        null,
        [{ type: "other", description: description }],
        peg$reportedPos
      );
    }

    function error(message) {
      throw peg$buildException(message, null, peg$reportedPos);
    }

    function peg$computePosDetails(pos) {
      function advance(details, startPos, endPos) {
        var p, ch;

        for (p = startPos; p < endPos; p++) {
          ch = input.charAt(p);
          if (ch === "\n") {
            if (!details.seenCR) { details.line++; }
            details.column = 1;
            details.seenCR = false;
          } else if (ch === "\r" || ch === "\u2028" || ch === "\u2029") {
            details.line++;
            details.column = 1;
            details.seenCR = true;
          } else {
            details.column++;
            details.seenCR = false;
          }
        }
      }

      if (peg$cachedPos !== pos) {
        if (peg$cachedPos > pos) {
          peg$cachedPos = 0;
          peg$cachedPosDetails = { line: 1, column: 1, seenCR: false };
        }
        advance(peg$cachedPosDetails, peg$cachedPos, pos);
        peg$cachedPos = pos;
      }

      return peg$cachedPosDetails;
    }

    function peg$fail(expected) {
      if (peg$currPos < peg$maxFailPos) { return; }

      if (peg$currPos > peg$maxFailPos) {
        peg$maxFailPos = peg$currPos;
        peg$maxFailExpected = [];
      }

      peg$maxFailExpected.push(expected);
    }

    function peg$buildException(message, expected, pos) {
      function cleanupExpected(expected) {
        var i = 1;

        expected.sort(function(a, b) {
          if (a.description < b.description) {
            return -1;
          } else if (a.description > b.description) {
            return 1;
          } else {
            return 0;
          }
        });

        while (i < expected.length) {
          if (expected[i - 1] === expected[i]) {
            expected.splice(i, 1);
          } else {
            i++;
          }
        }
      }

      function buildMessage(expected, found) {
        function stringEscape(s) {
          function hex(ch) { return ch.charCodeAt(0).toString(16).toUpperCase(); }

          return s
            .replace(/\\/g,   '\\\\')
            .replace(/"/g,    '\\"')
            .replace(/\x08/g, '\\b')
            .replace(/\t/g,   '\\t')
            .replace(/\n/g,   '\\n')
            .replace(/\f/g,   '\\f')
            .replace(/\r/g,   '\\r')
            .replace(/[\x00-\x07\x0B\x0E\x0F]/g, function(ch) { return '\\x0' + hex(ch); })
            .replace(/[\x10-\x1F\x80-\xFF]/g,    function(ch) { return '\\x'  + hex(ch); })
            .replace(/[\u0180-\u0FFF]/g,         function(ch) { return '\\u0' + hex(ch); })
            .replace(/[\u1080-\uFFFF]/g,         function(ch) { return '\\u'  + hex(ch); });
        }

        var expectedDescs = new Array(expected.length),
            expectedDesc, foundDesc, i;

        for (i = 0; i < expected.length; i++) {
          expectedDescs[i] = expected[i].description;
        }

        expectedDesc = expected.length > 1
          ? expectedDescs.slice(0, -1).join(", ")
              + " or "
              + expectedDescs[expected.length - 1]
          : expectedDescs[0];

        foundDesc = found ? "\"" + stringEscape(found) + "\"" : "end of input";

        return "Expected " + expectedDesc + " but " + foundDesc + " found.";
      }

      var posDetails = peg$computePosDetails(pos),
          found      = pos < input.length ? input.charAt(pos) : null;

      if (expected !== null) {
        cleanupExpected(expected);
      }

      return new SyntaxError(
        message !== null ? message : buildMessage(expected, found),
        expected,
        found,
        pos,
        posDetails.line,
        posDetails.column
      );
    }

    function peg$parsestart() {
      var s0, s1, s2, s3;

      peg$silentFails++;
      s0 = peg$currPos;
      s1 = peg$parse__();
      if (s1 !== peg$FAILED) {
        s2 = peg$parseOrExpr();
        if (s2 !== peg$FAILED) {
          s3 = peg$parse__();
          if (s3 !== peg$FAILED) {
            peg$reportedPos = s0;
            s1 = peg$c2(s2);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$c1;
      }
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        s1 = [];
        if (s1 !== peg$FAILED) {
          peg$reportedPos = s0;
          s1 = peg$c4();
        }
        s0 = s1;
      }
      peg$silentFails--;
      if (s0 === peg$FAILED) {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c0); }
      }

      return s0;
    }

    function peg$parsews() {
      var s0, s1;

      peg$silentFails++;
      if (peg$c6.test(input.charAt(peg$currPos))) {
        s0 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s0 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c7); }
      }
      peg$silentFails--;
      if (s0 === peg$FAILED) {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c5); }
      }

      return s0;
    }

    function peg$parsecc() {
      var s0, s1;

      peg$silentFails++;
      if (peg$c9.test(input.charAt(peg$currPos))) {
        s0 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s0 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c10); }
      }
      peg$silentFails--;
      if (s0 === peg$FAILED) {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c8); }
      }

      return s0;
    }

    function peg$parse__() {
      var s0, s1;

      peg$silentFails++;
      s0 = [];
      s1 = peg$parsews();
      while (s1 !== peg$FAILED) {
        s0.push(s1);
        s1 = peg$parsews();
      }
      peg$silentFails--;
      if (s0 === peg$FAILED) {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c11); }
      }

      return s0;
    }

    function peg$parseOrExpr() {
      var s0, s1, s2, s3, s4, s5;

      s0 = peg$currPos;
      s1 = peg$parseAndExpr();
      if (s1 !== peg$FAILED) {
        s2 = peg$parse__();
        if (s2 !== peg$FAILED) {
          if (input.charCodeAt(peg$currPos) === 124) {
            s3 = peg$c12;
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) { peg$fail(peg$c13); }
          }
          if (s3 !== peg$FAILED) {
            s4 = peg$parse__();
            if (s4 !== peg$FAILED) {
              s5 = peg$parseOrExpr();
              if (s5 !== peg$FAILED) {
                peg$reportedPos = s0;
                s1 = peg$c14(s1, s5);
                s0 = s1;
              } else {
                peg$currPos = s0;
                s0 = peg$c1;
              }
            } else {
              peg$currPos = s0;
              s0 = peg$c1;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$c1;
      }
      if (s0 === peg$FAILED) {
        s0 = peg$parseAndExpr();
      }

      return s0;
    }

    function peg$parseAndExpr() {
      var s0, s1, s2, s3, s4, s5;

      s0 = peg$currPos;
      s1 = peg$parseNotExpr();
      if (s1 !== peg$FAILED) {
        s2 = peg$parse__();
        if (s2 !== peg$FAILED) {
          if (input.charCodeAt(peg$currPos) === 38) {
            s3 = peg$c15;
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) { peg$fail(peg$c16); }
          }
          if (s3 !== peg$FAILED) {
            s4 = peg$parse__();
            if (s4 !== peg$FAILED) {
              s5 = peg$parseAndExpr();
              if (s5 !== peg$FAILED) {
                peg$reportedPos = s0;
                s1 = peg$c17(s1, s5);
                s0 = s1;
              } else {
                peg$currPos = s0;
                s0 = peg$c1;
              }
            } else {
              peg$currPos = s0;
              s0 = peg$c1;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$c1;
      }
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        s1 = peg$parseNotExpr();
        if (s1 !== peg$FAILED) {
          s2 = [];
          s3 = peg$parsews();
          if (s3 !== peg$FAILED) {
            while (s3 !== peg$FAILED) {
              s2.push(s3);
              s3 = peg$parsews();
            }
          } else {
            s2 = peg$c1;
          }
          if (s2 !== peg$FAILED) {
            s3 = peg$parseAndExpr();
            if (s3 !== peg$FAILED) {
              peg$reportedPos = s0;
              s1 = peg$c17(s1, s3);
              s0 = s1;
            } else {
              peg$currPos = s0;
              s0 = peg$c1;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
        if (s0 === peg$FAILED) {
          s0 = peg$parseNotExpr();
        }
      }

      return s0;
    }

    function peg$parseNotExpr() {
      var s0, s1, s2, s3;

      s0 = peg$currPos;
      if (input.charCodeAt(peg$currPos) === 33) {
        s1 = peg$c18;
        peg$currPos++;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c19); }
      }
      if (s1 !== peg$FAILED) {
        s2 = peg$parse__();
        if (s2 !== peg$FAILED) {
          s3 = peg$parseNotExpr();
          if (s3 !== peg$FAILED) {
            peg$reportedPos = s0;
            s1 = peg$c20(s3);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$c1;
      }
      if (s0 === peg$FAILED) {
        s0 = peg$parseBindingExpr();
      }

      return s0;
    }

    function peg$parseBindingExpr() {
      var s0, s1, s2, s3, s4, s5;

      s0 = peg$currPos;
      if (input.charCodeAt(peg$currPos) === 40) {
        s1 = peg$c21;
        peg$currPos++;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c22); }
      }
      if (s1 !== peg$FAILED) {
        s2 = peg$parse__();
        if (s2 !== peg$FAILED) {
          s3 = peg$parseOrExpr();
          if (s3 !== peg$FAILED) {
            s4 = peg$parse__();
            if (s4 !== peg$FAILED) {
              if (input.charCodeAt(peg$currPos) === 41) {
                s5 = peg$c23;
                peg$currPos++;
              } else {
                s5 = peg$FAILED;
                if (peg$silentFails === 0) { peg$fail(peg$c24); }
              }
              if (s5 !== peg$FAILED) {
                peg$reportedPos = s0;
                s1 = peg$c25(s3);
                s0 = s1;
              } else {
                peg$currPos = s0;
                s0 = peg$c1;
              }
            } else {
              peg$currPos = s0;
              s0 = peg$c1;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$c1;
      }
      if (s0 === peg$FAILED) {
        s0 = peg$parseExpr();
      }

      return s0;
    }

    function peg$parseExpr() {
      var s0;

      s0 = peg$parseNullaryExpr();
      if (s0 === peg$FAILED) {
        s0 = peg$parseUnaryExpr();
      }

      return s0;
    }

    function peg$parseNullaryExpr() {
      var s0, s1;

      s0 = peg$parseBooleanLiteral();
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.substr(peg$currPos, 2) === peg$c26) {
          s1 = peg$c26;
          peg$currPos += 2;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) { peg$fail(peg$c27); }
        }
        if (s1 !== peg$FAILED) {
          peg$reportedPos = s0;
          s1 = peg$c28();
        }
        s0 = s1;
        if (s0 === peg$FAILED) {
          s0 = peg$currPos;
          if (input.substr(peg$currPos, 2) === peg$c29) {
            s1 = peg$c29;
            peg$currPos += 2;
          } else {
            s1 = peg$FAILED;
            if (peg$silentFails === 0) { peg$fail(peg$c30); }
          }
          if (s1 !== peg$FAILED) {
            peg$reportedPos = s0;
            s1 = peg$c31();
          }
          s0 = s1;
          if (s0 === peg$FAILED) {
            s0 = peg$currPos;
            if (input.substr(peg$currPos, 2) === peg$c32) {
              s1 = peg$c32;
              peg$currPos += 2;
            } else {
              s1 = peg$FAILED;
              if (peg$silentFails === 0) { peg$fail(peg$c33); }
            }
            if (s1 !== peg$FAILED) {
              peg$reportedPos = s0;
              s1 = peg$c34();
            }
            s0 = s1;
            if (s0 === peg$FAILED) {
              s0 = peg$currPos;
              if (input.substr(peg$currPos, 2) === peg$c35) {
                s1 = peg$c35;
                peg$currPos += 2;
              } else {
                s1 = peg$FAILED;
                if (peg$silentFails === 0) { peg$fail(peg$c36); }
              }
              if (s1 !== peg$FAILED) {
                peg$reportedPos = s0;
                s1 = peg$c37();
              }
              s0 = s1;
            }
          }
        }
      }

      return s0;
    }

    function peg$parseBooleanLiteral() {
      var s0, s1;

      s0 = peg$currPos;
      if (input.substr(peg$currPos, 4) === peg$c38) {
        s1 = peg$c38;
        peg$currPos += 4;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c39); }
      }
      if (s1 !== peg$FAILED) {
        peg$reportedPos = s0;
        s1 = peg$c40();
      }
      s0 = s1;
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.substr(peg$currPos, 5) === peg$c41) {
          s1 = peg$c41;
          peg$currPos += 5;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) { peg$fail(peg$c42); }
        }
        if (s1 !== peg$FAILED) {
          peg$reportedPos = s0;
          s1 = peg$c43();
        }
        s0 = s1;
      }

      return s0;
    }

    function peg$parseUnaryExpr() {
      var s0, s1, s2, s3;

      s0 = peg$currPos;
      if (input.substr(peg$currPos, 2) === peg$c44) {
        s1 = peg$c44;
        peg$currPos += 2;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c45); }
      }
      if (s1 !== peg$FAILED) {
        s2 = [];
        s3 = peg$parsews();
        if (s3 !== peg$FAILED) {
          while (s3 !== peg$FAILED) {
            s2.push(s3);
            s3 = peg$parsews();
          }
        } else {
          s2 = peg$c1;
        }
        if (s2 !== peg$FAILED) {
          s3 = peg$parseIntegerLiteral();
          if (s3 !== peg$FAILED) {
            peg$reportedPos = s0;
            s1 = peg$c46(s3);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$c1;
      }
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.substr(peg$currPos, 2) === peg$c47) {
          s1 = peg$c47;
          peg$currPos += 2;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) { peg$fail(peg$c48); }
        }
        if (s1 !== peg$FAILED) {
          s2 = [];
          s3 = peg$parsews();
          if (s3 !== peg$FAILED) {
            while (s3 !== peg$FAILED) {
              s2.push(s3);
              s3 = peg$parsews();
            }
          } else {
            s2 = peg$c1;
          }
          if (s2 !== peg$FAILED) {
            s3 = peg$parseStringLiteral();
            if (s3 !== peg$FAILED) {
              peg$reportedPos = s0;
              s1 = peg$c49(s3);
              s0 = s1;
            } else {
              peg$currPos = s0;
              s0 = peg$c1;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
        if (s0 === peg$FAILED) {
          s0 = peg$currPos;
          if (input.substr(peg$currPos, 2) === peg$c50) {
            s1 = peg$c50;
            peg$currPos += 2;
          } else {
            s1 = peg$FAILED;
            if (peg$silentFails === 0) { peg$fail(peg$c51); }
          }
          if (s1 !== peg$FAILED) {
            s2 = [];
            s3 = peg$parsews();
            if (s3 !== peg$FAILED) {
              while (s3 !== peg$FAILED) {
                s2.push(s3);
                s3 = peg$parsews();
              }
            } else {
              s2 = peg$c1;
            }
            if (s2 !== peg$FAILED) {
              s3 = peg$parseStringLiteral();
              if (s3 !== peg$FAILED) {
                peg$reportedPos = s0;
                s1 = peg$c52(s3);
                s0 = s1;
              } else {
                peg$currPos = s0;
                s0 = peg$c1;
              }
            } else {
              peg$currPos = s0;
              s0 = peg$c1;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
          if (s0 === peg$FAILED) {
            s0 = peg$currPos;
            if (input.substr(peg$currPos, 3) === peg$c53) {
              s1 = peg$c53;
              peg$currPos += 3;
            } else {
              s1 = peg$FAILED;
              if (peg$silentFails === 0) { peg$fail(peg$c54); }
            }
            if (s1 !== peg$FAILED) {
              s2 = [];
              s3 = peg$parsews();
              if (s3 !== peg$FAILED) {
                while (s3 !== peg$FAILED) {
                  s2.push(s3);
                  s3 = peg$parsews();
                }
              } else {
                s2 = peg$c1;
              }
              if (s2 !== peg$FAILED) {
                s3 = peg$parseStringLiteral();
                if (s3 !== peg$FAILED) {
                  peg$reportedPos = s0;
                  s1 = peg$c55(s3);
                  s0 = s1;
                } else {
                  peg$currPos = s0;
                  s0 = peg$c1;
                }
              } else {
                peg$currPos = s0;
                s0 = peg$c1;
              }
            } else {
              peg$currPos = s0;
              s0 = peg$c1;
            }
            if (s0 === peg$FAILED) {
              s0 = peg$currPos;
              if (input.substr(peg$currPos, 3) === peg$c56) {
                s1 = peg$c56;
                peg$currPos += 3;
              } else {
                s1 = peg$FAILED;
                if (peg$silentFails === 0) { peg$fail(peg$c57); }
              }
              if (s1 !== peg$FAILED) {
                s2 = [];
                s3 = peg$parsews();
                if (s3 !== peg$FAILED) {
                  while (s3 !== peg$FAILED) {
                    s2.push(s3);
                    s3 = peg$parsews();
                  }
                } else {
                  s2 = peg$c1;
                }
                if (s2 !== peg$FAILED) {
                  s3 = peg$parseStringLiteral();
                  if (s3 !== peg$FAILED) {
                    peg$reportedPos = s0;
                    s1 = peg$c58(s3);
                    s0 = s1;
                  } else {
                    peg$currPos = s0;
                    s0 = peg$c1;
                  }
                } else {
                  peg$currPos = s0;
                  s0 = peg$c1;
                }
              } else {
                peg$currPos = s0;
                s0 = peg$c1;
              }
              if (s0 === peg$FAILED) {
                s0 = peg$currPos;
                if (input.substr(peg$currPos, 2) === peg$c59) {
                  s1 = peg$c59;
                  peg$currPos += 2;
                } else {
                  s1 = peg$FAILED;
                  if (peg$silentFails === 0) { peg$fail(peg$c60); }
                }
                if (s1 !== peg$FAILED) {
                  s2 = [];
                  s3 = peg$parsews();
                  if (s3 !== peg$FAILED) {
                    while (s3 !== peg$FAILED) {
                      s2.push(s3);
                      s3 = peg$parsews();
                    }
                  } else {
                    s2 = peg$c1;
                  }
                  if (s2 !== peg$FAILED) {
                    s3 = peg$parseStringLiteral();
                    if (s3 !== peg$FAILED) {
                      peg$reportedPos = s0;
                      s1 = peg$c61(s3);
                      s0 = s1;
                    } else {
                      peg$currPos = s0;
                      s0 = peg$c1;
                    }
                  } else {
                    peg$currPos = s0;
                    s0 = peg$c1;
                  }
                } else {
                  peg$currPos = s0;
                  s0 = peg$c1;
                }
                if (s0 === peg$FAILED) {
                  s0 = peg$currPos;
                  if (input.substr(peg$currPos, 2) === peg$c62) {
                    s1 = peg$c62;
                    peg$currPos += 2;
                  } else {
                    s1 = peg$FAILED;
                    if (peg$silentFails === 0) { peg$fail(peg$c63); }
                  }
                  if (s1 !== peg$FAILED) {
                    s2 = [];
                    s3 = peg$parsews();
                    if (s3 !== peg$FAILED) {
                      while (s3 !== peg$FAILED) {
                        s2.push(s3);
                        s3 = peg$parsews();
                      }
                    } else {
                      s2 = peg$c1;
                    }
                    if (s2 !== peg$FAILED) {
                      s3 = peg$parseStringLiteral();
                      if (s3 !== peg$FAILED) {
                        peg$reportedPos = s0;
                        s1 = peg$c64(s3);
                        s0 = s1;
                      } else {
                        peg$currPos = s0;
                        s0 = peg$c1;
                      }
                    } else {
                      peg$currPos = s0;
                      s0 = peg$c1;
                    }
                  } else {
                    peg$currPos = s0;
                    s0 = peg$c1;
                  }
                  if (s0 === peg$FAILED) {
                    s0 = peg$currPos;
                    if (input.substr(peg$currPos, 3) === peg$c65) {
                      s1 = peg$c65;
                      peg$currPos += 3;
                    } else {
                      s1 = peg$FAILED;
                      if (peg$silentFails === 0) { peg$fail(peg$c66); }
                    }
                    if (s1 !== peg$FAILED) {
                      s2 = [];
                      s3 = peg$parsews();
                      if (s3 !== peg$FAILED) {
                        while (s3 !== peg$FAILED) {
                          s2.push(s3);
                          s3 = peg$parsews();
                        }
                      } else {
                        s2 = peg$c1;
                      }
                      if (s2 !== peg$FAILED) {
                        s3 = peg$parseStringLiteral();
                        if (s3 !== peg$FAILED) {
                          peg$reportedPos = s0;
                          s1 = peg$c67(s3);
                          s0 = s1;
                        } else {
                          peg$currPos = s0;
                          s0 = peg$c1;
                        }
                      } else {
                        peg$currPos = s0;
                        s0 = peg$c1;
                      }
                    } else {
                      peg$currPos = s0;
                      s0 = peg$c1;
                    }
                    if (s0 === peg$FAILED) {
                      s0 = peg$currPos;
                      if (input.substr(peg$currPos, 3) === peg$c68) {
                        s1 = peg$c68;
                        peg$currPos += 3;
                      } else {
                        s1 = peg$FAILED;
                        if (peg$silentFails === 0) { peg$fail(peg$c69); }
                      }
                      if (s1 !== peg$FAILED) {
                        s2 = [];
                        s3 = peg$parsews();
                        if (s3 !== peg$FAILED) {
                          while (s3 !== peg$FAILED) {
                            s2.push(s3);
                            s3 = peg$parsews();
                          }
                        } else {
                          s2 = peg$c1;
                        }
                        if (s2 !== peg$FAILED) {
                          s3 = peg$parseStringLiteral();
                          if (s3 !== peg$FAILED) {
                            peg$reportedPos = s0;
                            s1 = peg$c70(s3);
                            s0 = s1;
                          } else {
                            peg$currPos = s0;
                            s0 = peg$c1;
                          }
                        } else {
                          peg$currPos = s0;
                          s0 = peg$c1;
                        }
                      } else {
                        peg$currPos = s0;
                        s0 = peg$c1;
                      }
                      if (s0 === peg$FAILED) {
                        s0 = peg$currPos;
                        if (input.substr(peg$currPos, 2) === peg$c71) {
                          s1 = peg$c71;
                          peg$currPos += 2;
                        } else {
                          s1 = peg$FAILED;
                          if (peg$silentFails === 0) { peg$fail(peg$c72); }
                        }
                        if (s1 !== peg$FAILED) {
                          s2 = [];
                          s3 = peg$parsews();
                          if (s3 !== peg$FAILED) {
                            while (s3 !== peg$FAILED) {
                              s2.push(s3);
                              s3 = peg$parsews();
                            }
                          } else {
                            s2 = peg$c1;
                          }
                          if (s2 !== peg$FAILED) {
                            s3 = peg$parseStringLiteral();
                            if (s3 !== peg$FAILED) {
                              peg$reportedPos = s0;
                              s1 = peg$c73(s3);
                              s0 = s1;
                            } else {
                              peg$currPos = s0;
                              s0 = peg$c1;
                            }
                          } else {
                            peg$currPos = s0;
                            s0 = peg$c1;
                          }
                        } else {
                          peg$currPos = s0;
                          s0 = peg$c1;
                        }
                        if (s0 === peg$FAILED) {
                          s0 = peg$currPos;
                          s1 = peg$parseStringLiteral();
                          if (s1 !== peg$FAILED) {
                            peg$reportedPos = s0;
                            s1 = peg$c73(s1);
                          }
                          s0 = s1;
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }

      return s0;
    }

    function peg$parseIntegerLiteral() {
      var s0, s1, s2, s3;

      peg$silentFails++;
      s0 = peg$currPos;
      if (peg$c76.test(input.charAt(peg$currPos))) {
        s1 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c77); }
      }
      if (s1 === peg$FAILED) {
        s1 = peg$c75;
      }
      if (s1 !== peg$FAILED) {
        s2 = [];
        if (peg$c78.test(input.charAt(peg$currPos))) {
          s3 = input.charAt(peg$currPos);
          peg$currPos++;
        } else {
          s3 = peg$FAILED;
          if (peg$silentFails === 0) { peg$fail(peg$c79); }
        }
        if (s3 !== peg$FAILED) {
          while (s3 !== peg$FAILED) {
            s2.push(s3);
            if (peg$c78.test(input.charAt(peg$currPos))) {
              s3 = input.charAt(peg$currPos);
              peg$currPos++;
            } else {
              s3 = peg$FAILED;
              if (peg$silentFails === 0) { peg$fail(peg$c79); }
            }
          }
        } else {
          s2 = peg$c1;
        }
        if (s2 !== peg$FAILED) {
          if (peg$c76.test(input.charAt(peg$currPos))) {
            s3 = input.charAt(peg$currPos);
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) { peg$fail(peg$c77); }
          }
          if (s3 === peg$FAILED) {
            s3 = peg$c75;
          }
          if (s3 !== peg$FAILED) {
            peg$reportedPos = s0;
            s1 = peg$c80(s2);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$c1;
      }
      peg$silentFails--;
      if (s0 === peg$FAILED) {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c74); }
      }

      return s0;
    }

    function peg$parseStringLiteral() {
      var s0, s1, s2, s3;

      peg$silentFails++;
      s0 = peg$currPos;
      if (input.charCodeAt(peg$currPos) === 34) {
        s1 = peg$c82;
        peg$currPos++;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c83); }
      }
      if (s1 !== peg$FAILED) {
        s2 = [];
        s3 = peg$parseDoubleStringChar();
        while (s3 !== peg$FAILED) {
          s2.push(s3);
          s3 = peg$parseDoubleStringChar();
        }
        if (s2 !== peg$FAILED) {
          if (input.charCodeAt(peg$currPos) === 34) {
            s3 = peg$c82;
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) { peg$fail(peg$c83); }
          }
          if (s3 !== peg$FAILED) {
            peg$reportedPos = s0;
            s1 = peg$c84(s2);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$c1;
      }
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 39) {
          s1 = peg$c85;
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) { peg$fail(peg$c86); }
        }
        if (s1 !== peg$FAILED) {
          s2 = [];
          s3 = peg$parseSingleStringChar();
          while (s3 !== peg$FAILED) {
            s2.push(s3);
            s3 = peg$parseSingleStringChar();
          }
          if (s2 !== peg$FAILED) {
            if (input.charCodeAt(peg$currPos) === 39) {
              s3 = peg$c85;
              peg$currPos++;
            } else {
              s3 = peg$FAILED;
              if (peg$silentFails === 0) { peg$fail(peg$c86); }
            }
            if (s3 !== peg$FAILED) {
              peg$reportedPos = s0;
              s1 = peg$c84(s2);
              s0 = s1;
            } else {
              peg$currPos = s0;
              s0 = peg$c1;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
        if (s0 === peg$FAILED) {
          s0 = peg$currPos;
          s1 = peg$currPos;
          peg$silentFails++;
          s2 = peg$parsecc();
          peg$silentFails--;
          if (s2 === peg$FAILED) {
            s1 = peg$c87;
          } else {
            peg$currPos = s1;
            s1 = peg$c1;
          }
          if (s1 !== peg$FAILED) {
            s2 = [];
            s3 = peg$parseUnquotedStringChar();
            if (s3 !== peg$FAILED) {
              while (s3 !== peg$FAILED) {
                s2.push(s3);
                s3 = peg$parseUnquotedStringChar();
              }
            } else {
              s2 = peg$c1;
            }
            if (s2 !== peg$FAILED) {
              peg$reportedPos = s0;
              s1 = peg$c84(s2);
              s0 = s1;
            } else {
              peg$currPos = s0;
              s0 = peg$c1;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        }
      }
      peg$silentFails--;
      if (s0 === peg$FAILED) {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c81); }
      }

      return s0;
    }

    function peg$parseDoubleStringChar() {
      var s0, s1, s2;

      s0 = peg$currPos;
      s1 = peg$currPos;
      peg$silentFails++;
      if (peg$c88.test(input.charAt(peg$currPos))) {
        s2 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s2 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c89); }
      }
      peg$silentFails--;
      if (s2 === peg$FAILED) {
        s1 = peg$c87;
      } else {
        peg$currPos = s1;
        s1 = peg$c1;
      }
      if (s1 !== peg$FAILED) {
        if (input.length > peg$currPos) {
          s2 = input.charAt(peg$currPos);
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) { peg$fail(peg$c90); }
        }
        if (s2 !== peg$FAILED) {
          peg$reportedPos = s0;
          s1 = peg$c91(s2);
          s0 = s1;
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$c1;
      }
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 92) {
          s1 = peg$c92;
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) { peg$fail(peg$c93); }
        }
        if (s1 !== peg$FAILED) {
          s2 = peg$parseEscapeSequence();
          if (s2 !== peg$FAILED) {
            peg$reportedPos = s0;
            s1 = peg$c91(s2);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
      }

      return s0;
    }

    function peg$parseSingleStringChar() {
      var s0, s1, s2;

      s0 = peg$currPos;
      s1 = peg$currPos;
      peg$silentFails++;
      if (peg$c94.test(input.charAt(peg$currPos))) {
        s2 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s2 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c95); }
      }
      peg$silentFails--;
      if (s2 === peg$FAILED) {
        s1 = peg$c87;
      } else {
        peg$currPos = s1;
        s1 = peg$c1;
      }
      if (s1 !== peg$FAILED) {
        if (input.length > peg$currPos) {
          s2 = input.charAt(peg$currPos);
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) { peg$fail(peg$c90); }
        }
        if (s2 !== peg$FAILED) {
          peg$reportedPos = s0;
          s1 = peg$c91(s2);
          s0 = s1;
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$c1;
      }
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 92) {
          s1 = peg$c92;
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) { peg$fail(peg$c93); }
        }
        if (s1 !== peg$FAILED) {
          s2 = peg$parseEscapeSequence();
          if (s2 !== peg$FAILED) {
            peg$reportedPos = s0;
            s1 = peg$c91(s2);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$c1;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
      }

      return s0;
    }

    function peg$parseUnquotedStringChar() {
      var s0, s1, s2;

      s0 = peg$currPos;
      s1 = peg$currPos;
      peg$silentFails++;
      s2 = peg$parsews();
      peg$silentFails--;
      if (s2 === peg$FAILED) {
        s1 = peg$c87;
      } else {
        peg$currPos = s1;
        s1 = peg$c1;
      }
      if (s1 !== peg$FAILED) {
        if (input.length > peg$currPos) {
          s2 = input.charAt(peg$currPos);
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) { peg$fail(peg$c90); }
        }
        if (s2 !== peg$FAILED) {
          peg$reportedPos = s0;
          s1 = peg$c91(s2);
          s0 = s1;
        } else {
          peg$currPos = s0;
          s0 = peg$c1;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$c1;
      }

      return s0;
    }

    function peg$parseEscapeSequence() {
      var s0, s1;

      if (peg$c96.test(input.charAt(peg$currPos))) {
        s0 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s0 = peg$FAILED;
        if (peg$silentFails === 0) { peg$fail(peg$c97); }
      }
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 110) {
          s1 = peg$c98;
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) { peg$fail(peg$c99); }
        }
        if (s1 !== peg$FAILED) {
          peg$reportedPos = s0;
          s1 = peg$c100();
        }
        s0 = s1;
        if (s0 === peg$FAILED) {
          s0 = peg$currPos;
          if (input.charCodeAt(peg$currPos) === 114) {
            s1 = peg$c101;
            peg$currPos++;
          } else {
            s1 = peg$FAILED;
            if (peg$silentFails === 0) { peg$fail(peg$c102); }
          }
          if (s1 !== peg$FAILED) {
            peg$reportedPos = s0;
            s1 = peg$c103();
          }
          s0 = s1;
          if (s0 === peg$FAILED) {
            s0 = peg$currPos;
            if (input.charCodeAt(peg$currPos) === 116) {
              s1 = peg$c104;
              peg$currPos++;
            } else {
              s1 = peg$FAILED;
              if (peg$silentFails === 0) { peg$fail(peg$c105); }
            }
            if (s1 !== peg$FAILED) {
              peg$reportedPos = s0;
              s1 = peg$c106();
            }
            s0 = s1;
          }
        }
      }

      return s0;
    }


    function or(first, second) {
        // Add explicit function names to ease debugging.
        function orFilter() {
            return first.apply(this, arguments) || second.apply(this, arguments);
        }
        orFilter.desc = first.desc + " or " + second.desc;
        return orFilter;
    }
    function and(first, second) {
        function andFilter() {
            return first.apply(this, arguments) && second.apply(this, arguments);
        }
        andFilter.desc = first.desc + " and " + second.desc;
        return andFilter;
    }
    function not(expr) {
        function notFilter() {
            return !expr.apply(this, arguments);
        }
        notFilter.desc = "not " + expr.desc;
        return notFilter;
    }
    function binding(expr) {
        function bindingFilter() {
            return expr.apply(this, arguments);
        }
        bindingFilter.desc = "(" + expr.desc + ")";
        return bindingFilter;
    }
    function trueFilter(flow) {
        return true;
    }
    trueFilter.desc = "true";
    function falseFilter(flow) {
        return false;
    }
    falseFilter.desc = "false";

    var ASSET_TYPES = [
        new RegExp("text/javascript"),
        new RegExp("application/x-javascript"),
        new RegExp("application/javascript"),
        new RegExp("text/css"),
        new RegExp("image/.*"),
        new RegExp("application/x-shockwave-flash")
    ];
    function assetFilter(flow) {
        if (flow.response) {
            var ct = ResponseUtils.getContentType(flow.response);
            var i = ASSET_TYPES.length;
            while (i--) {
                if (ASSET_TYPES[i].test(ct)) {
                    return true;
                }
            }
        }
        return false;
    }
    assetFilter.desc = "is asset";
    function responseCode(code){
        function responseCodeFilter(flow){
            return flow.response && flow.response.code === code;
        }
        responseCodeFilter.desc = "resp. code is " + code;
        return responseCodeFilter;
    }
    function domain(regex){
        regex = new RegExp(regex, "i");
        function domainFilter(flow){
            return flow.request && regex.test(flow.request.host);
        }
        domainFilter.desc = "domain matches " + regex;
        return domainFilter;
    }
    function errorFilter(flow){
        return !!flow.error;
    }
    errorFilter.desc = "has error";
    function header(regex){
        regex = new RegExp(regex, "i");
        function headerFilter(flow){
            return (
                (flow.request && RequestUtils.match_header(flow.request, regex))
                ||
                (flow.response && ResponseUtils.match_header(flow.response, regex))
            );
        }
        headerFilter.desc = "header matches " + regex;
        return headerFilter;
    }
    function requestHeader(regex){
        regex = new RegExp(regex, "i");
        function requestHeaderFilter(flow){
            return (flow.request && RequestUtils.match_header(flow.request, regex));
        }
        requestHeaderFilter.desc = "req. header matches " + regex;
        return requestHeaderFilter;
    }
    function responseHeader(regex){
        regex = new RegExp(regex, "i");
        function responseHeaderFilter(flow){
            return (flow.response && ResponseUtils.match_header(flow.response, regex));
        }
        responseHeaderFilter.desc = "resp. header matches " + regex;
        return responseHeaderFilter;
    }
    function method(regex){
        regex = new RegExp(regex, "i");
        function methodFilter(flow){
            return flow.request && regex.test(flow.request.method);
        }
        methodFilter.desc = "method matches " + regex;
        return methodFilter;
    }
    function noResponseFilter(flow){
        return flow.request && !flow.response;
    }
    noResponseFilter.desc = "has no response";
    function responseFilter(flow){
        return !!flow.response;
    }
    responseFilter.desc = "has response";

    function contentType(regex){
        regex = new RegExp(regex, "i");
        function contentTypeFilter(flow){
            return (
                (flow.request && regex.test(RequestUtils.getContentType(flow.request)))
                ||
                (flow.response && regex.test(ResponseUtils.getContentType(flow.response)))
            );
        }
        contentTypeFilter.desc = "content type matches " + regex;
        return contentTypeFilter;
    }
    function requestContentType(regex){
        regex = new RegExp(regex, "i");
        function requestContentTypeFilter(flow){
            return flow.request && regex.test(RequestUtils.getContentType(flow.request));
        }
        requestContentTypeFilter.desc = "req. content type matches " + regex;
        return requestContentTypeFilter;
    }
    function responseContentType(regex){
        regex = new RegExp(regex, "i");
        function responseContentTypeFilter(flow){
            return flow.response && regex.test(ResponseUtils.getContentType(flow.response));
        }
        responseContentTypeFilter.desc = "resp. content type matches " + regex;
        return responseContentTypeFilter;
    }
    function url(regex){
        regex = new RegExp(regex, "i");
        function urlFilter(flow){
            return flow.request && regex.test(RequestUtils.pretty_url(flow.request));
        }
        urlFilter.desc = "url matches " + regex;
        return urlFilter;
    }


    peg$result = peg$startRuleFunction();

    if (peg$result !== peg$FAILED && peg$currPos === input.length) {
      return peg$result;
    } else {
      if (peg$result !== peg$FAILED && peg$currPos < input.length) {
        peg$fail({ type: "end", description: "end of input" });
      }

      throw peg$buildException(null, peg$maxFailExpected, peg$maxFailPos);
    }
  }

  return {
    SyntaxError: SyntaxError,
    parse:       parse
  };
})();
/* jshint ignore:end */

module.exports = Filt;

},{}],15:[function(require,module,exports){
var _ = require("lodash");

var _MessageUtils = {
    getContentType: function (message) {
        return this.get_first_header(message, /^Content-Type$/i);
    },
    get_first_header: function (message, regex) {
        //FIXME: Cache Invalidation.
        if (!message._headerLookups)
            Object.defineProperty(message, "_headerLookups", {
                value: {},
                configurable: false,
                enumerable: false,
                writable: false
            });
        if (!(regex in message._headerLookups)) {
            var header;
            for (var i = 0; i < message.headers.length; i++) {
                if (!!message.headers[i][0].match(regex)) {
                    header = message.headers[i];
                    break;
                }
            }
            message._headerLookups[regex] = header ? header[1] : undefined;
        }
        return message._headerLookups[regex];
    },
    match_header: function (message, regex) {
        var headers = message.headers;
        var i = headers.length;
        while (i--) {
            if (regex.test(headers[i].join(" "))) {
                return headers[i];
            }
        }
        return false;
    }
};

var defaultPorts = {
    "http": 80,
    "https": 443
};

var RequestUtils = _.extend(_MessageUtils, {
    pretty_host: function (request) {
        //FIXME: Add hostheader
        return request.host;
    },
    pretty_url: function (request) {
        var port = "";
        if (defaultPorts[request.scheme] !== request.port) {
            port = ":" + request.port;
        }
        return request.scheme + "://" + this.pretty_host(request) + port + request.path;
    }
});

var ResponseUtils = _.extend(_MessageUtils, {});


module.exports = {
    ResponseUtils: ResponseUtils,
    RequestUtils: RequestUtils

}
},{"lodash":"lodash"}],16:[function(require,module,exports){

var _ = require("lodash");
var $ = require("jquery");

var utils = require("../utils.js");
var actions = require("../actions.js");
var dispatcher = require("../dispatcher.js");


function ListStore() {
    utils.EventEmitter.call(this);
    this.reset();
}
_.extend(ListStore.prototype, utils.EventEmitter.prototype, {
    add: function (elem) {
        if (elem.id in this._pos_map) {
            return;
        }
        this._pos_map[elem.id] = this.list.length;
        this.list.push(elem);
        this.emit("add", elem);
    },
    update: function (elem) {
        if (!(elem.id in this._pos_map)) {
            return;
        }
        this.list[this._pos_map[elem.id]] = elem;
        this.emit("update", elem);
    },
    remove: function (elem_id) {
        if (!(elem_id in this._pos_map)) {
            return;
        }
        this.list.splice(this._pos_map[elem_id], 1);
        this._build_map();
        this.emit("remove", elem_id);
    },
    reset: function (elems) {
        this.list = elems || [];
        this._build_map();
        this.emit("recalculate");
    },
    _build_map: function () {
        this._pos_map = {};
        for (var i = 0; i < this.list.length; i++) {
            var elem = this.list[i];
            this._pos_map[elem.id] = i;
        }
    },
    get: function (elem_id) {
        return this.list[this._pos_map[elem_id]];
    },
    index: function (elem_id) {
        return this._pos_map[elem_id];
    }
});


function DictStore() {
    utils.EventEmitter.call(this);
    this.reset();
}
_.extend(DictStore.prototype, utils.EventEmitter.prototype, {
    update: function (dict) {
        _.merge(this.dict, dict);
        this.emit("recalculate");
    },
    reset: function (dict) {
        this.dict = dict || {};
        this.emit("recalculate");
    }
});

function LiveStoreMixin(type) {
    this.type = type;

    this._updates_before_fetch = undefined;
    this._fetchxhr = false;

    this.handle = this.handle.bind(this);
    dispatcher.AppDispatcher.register(this.handle);

    // Avoid double-fetch on startup.
    if (!(window.ws && window.ws.readyState === WebSocket.CONNECTING)) {
        this.fetch();
    }
}
_.extend(LiveStoreMixin.prototype, {
    handle: function (event) {
        if (event.type === actions.ActionTypes.CONNECTION_OPEN) {
            return this.fetch();
        }
        if (event.type === this.type) {
            if (event.cmd === actions.StoreCmds.RESET) {
                this.fetch(event.data);
            } else if (this._updates_before_fetch) {
                console.log("defer update", event);
                this._updates_before_fetch.push(event);
            } else {
                this[event.cmd](event.data);
            }
        }
    },
    close: function () {
        dispatcher.AppDispatcher.unregister(this.handle);
    },
    fetch: function (data) {
        console.log("fetch " + this.type);
        if (this._fetchxhr) {
            this._fetchxhr.abort();
        }
        this._updates_before_fetch = []; // (JS: empty array is true)
        if (data) {
            this.handle_fetch(data);
        } else {
            this._fetchxhr = $.getJSON("/" + this.type)
                .done(function (message) {
                    this.handle_fetch(message.data);
                }.bind(this))
                .fail(function () {
                    EventLogActions.add_event("Could not fetch " + this.type);
                }.bind(this));
        }
    },
    handle_fetch: function (data) {
        this._fetchxhr = false;
        console.log(this.type + " fetched.", this._updates_before_fetch);
        this.reset(data);
        var updates = this._updates_before_fetch;
        this._updates_before_fetch = false;
        for (var i = 0; i < updates.length; i++) {
            this.handle(updates[i]);
        }
    },
});

function LiveListStore(type) {
    ListStore.call(this);
    LiveStoreMixin.call(this, type);
}
_.extend(LiveListStore.prototype, ListStore.prototype, LiveStoreMixin.prototype);

function LiveDictStore(type) {
    DictStore.call(this);
    LiveStoreMixin.call(this, type);
}
_.extend(LiveDictStore.prototype, DictStore.prototype, LiveStoreMixin.prototype);


function FlowStore() {
    return new LiveListStore(actions.ActionTypes.FLOW_STORE);
}

function SettingsStore() {
    return new LiveDictStore(actions.ActionTypes.SETTINGS_STORE);
}

function EventLogStore() {
    LiveListStore.call(this, actions.ActionTypes.EVENT_STORE);
}
_.extend(EventLogStore.prototype, LiveListStore.prototype, {
    fetch: function(){
        LiveListStore.prototype.fetch.apply(this, arguments);

        // Make sure to display updates even if fetching all events failed.
        // This way, we can send "fetch failed" log messages to the log.
        if(this._fetchxhr){
            this._fetchxhr.fail(function(){
                this.handle_fetch(null);
            }.bind(this));
        }
    }
});


module.exports = {
    EventLogStore: EventLogStore,
    SettingsStore: SettingsStore,
    FlowStore: FlowStore
};
},{"../actions.js":1,"../dispatcher.js":13,"../utils.js":18,"jquery":"jquery","lodash":"lodash"}],17:[function(require,module,exports){
var _ = require("lodash");

var utils = require("../utils.js");

function SortByStoreOrder(elem) {
    return this.store.index(elem.id);
}

var default_sort = SortByStoreOrder;
var default_filt = function(elem){
    return true;
};

function StoreView(store, filt, sortfun) {
    utils.EventEmitter.call(this);
    filt = filt || default_filt;
    sortfun = sortfun || default_sort;

    this.store = store;

    this.add = this.add.bind(this);
    this.update = this.update.bind(this);
    this.remove = this.remove.bind(this);
    this.recalculate = this.recalculate.bind(this);
    this.store.addListener("add", this.add);
    this.store.addListener("update", this.update);
    this.store.addListener("remove", this.remove);
    this.store.addListener("recalculate", this.recalculate);

    this.recalculate(filt, sortfun);
}

_.extend(StoreView.prototype, utils.EventEmitter.prototype, {
    close: function () {
        this.store.removeListener("add", this.add);
        this.store.removeListener("update", this.update);
        this.store.removeListener("remove", this.remove);
        this.store.removeListener("recalculate", this.recalculate);
        },
        recalculate: function (filt, sortfun) {
        if (filt) {
            this.filt = filt.bind(this);
        }
        if (sortfun) {
            this.sortfun = sortfun.bind(this);
        }

        this.list = this.store.list.filter(this.filt);
        this.list.sort(function (a, b) {
            return this.sortfun(a) - this.sortfun(b);
        }.bind(this));
        this.emit("recalculate");
    },
    index: function (elem) {
        return _.sortedIndex(this.list, elem, this.sortfun);
    },
    add: function (elem) {
        if (this.filt(elem)) {
            var idx = this.index(elem);
            if (idx === this.list.length) { //happens often, .push is way faster.
                this.list.push(elem);
            } else {
                this.list.splice(idx, 0, elem);
            }
            this.emit("add", elem, idx);
        }
    },
    update: function (elem) {
        var idx;
        var i = this.list.length;
        // Search from the back, we usually update the latest entries.
        while (i--) {
            if (this.list[i].id === elem.id) {
                idx = i;
                break;
            }
        }

        if (idx === -1) { //not contained in list
            this.add(elem);
        } else if (!this.filt(elem)) {
            this.remove(elem.id);
        } else {
            if (this.sortfun(this.list[idx]) !== this.sortfun(elem)) { //sortpos has changed
                this.remove(this.list[idx]);
                this.add(elem);
            } else {
                this.list[idx] = elem;
                this.emit("update", elem, idx);
            }
        }
    },
    remove: function (elem_id) {
        var idx = this.list.length;
        while (idx--) {
            if (this.list[idx].id === elem_id) {
                this.list.splice(idx, 1);
                this.emit("remove", elem_id, idx);
                break;
            }
        }
    }
});

module.exports = {
    StoreView: StoreView
};
},{"../utils.js":18,"lodash":"lodash"}],18:[function(require,module,exports){
var $ = require("jquery");


var Key = {
    UP: 38,
    DOWN: 40,
    PAGE_UP: 33,
    PAGE_DOWN: 34,
    HOME: 36,
    END: 35,
    LEFT: 37,
    RIGHT: 39,
    ENTER: 13,
    ESC: 27,
    TAB: 9,
    SPACE: 32,
    BACKSPACE: 8,
};
// Add A-Z
for (var i = 65; i <= 90; i++) {
    Key[String.fromCharCode(i)] = i;
}


var formatSize = function (bytes) {
    var size = bytes;
    var prefix = ["B", "KB", "MB", "GB", "TB"];
    var i = 0;
    while (Math.abs(size) >= 1024 && i < prefix.length - 1) {
        i++;
        size = size / 1024;
    }
    return (Math.floor(size * 100) / 100.0).toFixed(2) + prefix[i];
};


var formatTimeDelta = function (milliseconds) {
    var time = milliseconds;
    var prefix = ["ms", "s", "min", "h"];
    var div = [1000, 60, 60];
    var i = 0;
    while (Math.abs(time) >= div[i] && i < div.length) {
        time = time / div[i];
        i++;
    }
    return Math.round(time) + prefix[i];
};


var formatTimeStamp = function (seconds) {
    var ts = (new Date(seconds * 1000)).toISOString();
    return ts.replace("T", " ").replace("Z", "");
};


function EventEmitter() {
    this.listeners = {};
}
EventEmitter.prototype.emit = function (event) {
    if (!(event in this.listeners)) {
        return;
    }
    var args = Array.prototype.slice.call(arguments, 1);
    this.listeners[event].forEach(function (listener) {
        listener.apply(this, args);
    }.bind(this));
};
EventEmitter.prototype.addListener = function (events, f) {
    events.split(" ").forEach(function (event) {
        this.listeners[event] = this.listeners[event] || [];
        this.listeners[event].push(f);
    }.bind(this));
};
EventEmitter.prototype.removeListener = function (events, f) {
    if (!(events in this.listeners)) {
        return false;
    }
    events.split(" ").forEach(function (event) {
        var index = this.listeners[event].indexOf(f);
        if (index >= 0) {
            this.listeners[event].splice(index, 1);
        }
    }.bind(this));
};


function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}
var xsrf = $.param({_xsrf: getCookie("_xsrf")});

//Tornado XSRF Protection.
$.ajaxPrefilter(function (options) {
    if (["post", "put", "delete"].indexOf(options.type.toLowerCase()) >= 0 && options.url[0] === "/") {
        if (options.data) {
            options.data += ("&" + xsrf);
        } else {
            options.data = xsrf;
        }
    }
});
// Log AJAX Errors
$(document).ajaxError(function (event, jqXHR, ajaxSettings, thrownError) {
    var message = jqXHR.responseText;
    console.error(message, arguments);
    EventLogActions.add_event(thrownError + ": " + message);
    window.alert(message);
});

module.exports = {
    EventEmitter: EventEmitter,
    formatSize: formatSize,
    formatTimeDelta: formatTimeDelta,
    formatTimeStamp: formatTimeStamp
};
},{"jquery":"jquery"}]},{},[2])
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIm5vZGVfbW9kdWxlcy9icm93c2VyaWZ5L25vZGVfbW9kdWxlcy9icm93c2VyLXBhY2svX3ByZWx1ZGUuanMiLCJzcmMvanMvYWN0aW9ucy5qcyIsInNyYy9qcy9hcHAuanMiLCJzcmMvanMvY29tcG9uZW50cy9mbG93ZGV0YWlsLmpzeC5qcyIsInNyYy9qcy9jb21wb25lbnRzL2Zsb3d0YWJsZS1jb2x1bW5zLmpzeC5qcyIsInNyYy9qcy9jb21wb25lbnRzL2Zsb3d0YWJsZS5qc3guanMiLCJzcmMvanMvY29tcG9uZW50cy9mb290ZXIuanN4LmpzIiwic3JjL2pzL2NvbXBvbmVudHMvaGVhZGVyLmpzeC5qcyIsInNyYy9qcy9jb21wb25lbnRzL21haW52aWV3LmpzeC5qcyIsInNyYy9qcy9jb21wb25lbnRzL3Byb3h5YXBwLmpzeC5qcyIsInNyYy9qcy9jb21wb25lbnRzL3V0aWxzLmpzeC5qcyIsInNyYy9qcy9jb21wb25lbnRzL3ZpcnR1YWxzY3JvbGwuanN4LmpzIiwic3JjL2pzL2Nvbm5lY3Rpb24uanMiLCJzcmMvanMvZGlzcGF0Y2hlci5qcyIsInNyYy9qcy9maWx0L2ZpbHQuanMiLCJzcmMvanMvZmxvdy91dGlscy5qcyIsInNyYy9qcy9zdG9yZS9zdG9yZS5qcyIsInNyYy9qcy9zdG9yZS92aWV3LmpzIiwic3JjL2pzL3V0aWxzLmpzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBO0FDQUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ3ZIQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDZEE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQzlZQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDcEtBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDeElBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDaEJBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDcFlBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ3ZPQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQzNGQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUNuTUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDcEZBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQzNCQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDdENBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ2h2REE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ2pFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDbkxBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDMUdBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EiLCJmaWxlIjoiZ2VuZXJhdGVkLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXNDb250ZW50IjpbIihmdW5jdGlvbiBlKHQsbixyKXtmdW5jdGlvbiBzKG8sdSl7aWYoIW5bb10pe2lmKCF0W29dKXt2YXIgYT10eXBlb2YgcmVxdWlyZT09XCJmdW5jdGlvblwiJiZyZXF1aXJlO2lmKCF1JiZhKXJldHVybiBhKG8sITApO2lmKGkpcmV0dXJuIGkobywhMCk7dmFyIGY9bmV3IEVycm9yKFwiQ2Fubm90IGZpbmQgbW9kdWxlICdcIitvK1wiJ1wiKTt0aHJvdyBmLmNvZGU9XCJNT0RVTEVfTk9UX0ZPVU5EXCIsZn12YXIgbD1uW29dPXtleHBvcnRzOnt9fTt0W29dWzBdLmNhbGwobC5leHBvcnRzLGZ1bmN0aW9uKGUpe3ZhciBuPXRbb11bMV1bZV07cmV0dXJuIHMobj9uOmUpfSxsLGwuZXhwb3J0cyxlLHQsbixyKX1yZXR1cm4gbltvXS5leHBvcnRzfXZhciBpPXR5cGVvZiByZXF1aXJlPT1cImZ1bmN0aW9uXCImJnJlcXVpcmU7Zm9yKHZhciBvPTA7bzxyLmxlbmd0aDtvKyspcyhyW29dKTtyZXR1cm4gc30pIiwidmFyIEFjdGlvblR5cGVzID0ge1xuICAgIC8vIENvbm5lY3Rpb25cbiAgICBDT05ORUNUSU9OX09QRU46IFwiY29ubmVjdGlvbl9vcGVuXCIsXG4gICAgQ09OTkVDVElPTl9DTE9TRTogXCJjb25uZWN0aW9uX2Nsb3NlXCIsXG4gICAgQ09OTkVDVElPTl9FUlJPUjogXCJjb25uZWN0aW9uX2Vycm9yXCIsXG5cbiAgICAvLyBTdG9yZXNcbiAgICBTRVRUSU5HU19TVE9SRTogXCJzZXR0aW5nc1wiLFxuICAgIEVWRU5UX1NUT1JFOiBcImV2ZW50c1wiLFxuICAgIEZMT1dfU1RPUkU6IFwiZmxvd3NcIixcbn07XG5cbnZhciBTdG9yZUNtZHMgPSB7XG4gICAgQUREOiBcImFkZFwiLFxuICAgIFVQREFURTogXCJ1cGRhdGVcIixcbiAgICBSRU1PVkU6IFwicmVtb3ZlXCIsXG4gICAgUkVTRVQ6IFwicmVzZXRcIlxufTtcblxudmFyIENvbm5lY3Rpb25BY3Rpb25zID0ge1xuICAgIG9wZW46IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFZpZXdBY3Rpb24oe1xuICAgICAgICAgICAgdHlwZTogQWN0aW9uVHlwZXMuQ09OTkVDVElPTl9PUEVOXG4gICAgICAgIH0pO1xuICAgIH0sXG4gICAgY2xvc2U6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFZpZXdBY3Rpb24oe1xuICAgICAgICAgICAgdHlwZTogQWN0aW9uVHlwZXMuQ09OTkVDVElPTl9DTE9TRVxuICAgICAgICB9KTtcbiAgICB9LFxuICAgIGVycm9yOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIEFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uKHtcbiAgICAgICAgICAgIHR5cGU6IEFjdGlvblR5cGVzLkNPTk5FQ1RJT05fRVJST1JcbiAgICAgICAgfSk7XG4gICAgfVxufTtcblxudmFyIFNldHRpbmdzQWN0aW9ucyA9IHtcbiAgICB1cGRhdGU6IGZ1bmN0aW9uIChzZXR0aW5ncykge1xuXG4gICAgICAgIGpRdWVyeS5hamF4KHtcbiAgICAgICAgICAgIHR5cGU6IFwiUFVUXCIsXG4gICAgICAgICAgICB1cmw6IFwiL3NldHRpbmdzXCIsXG4gICAgICAgICAgICBkYXRhOiBzZXR0aW5nc1xuICAgICAgICB9KTtcblxuICAgICAgICAvKlxuICAgICAgICAvL0ZhY2Vib29rIEZsdXg6IFdlIGRvIGFuIG9wdGltaXN0aWMgdXBkYXRlIG9uIHRoZSBjbGllbnQgYWxyZWFkeS5cbiAgICAgICAgQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFZpZXdBY3Rpb24oe1xuICAgICAgICAgICAgdHlwZTogQWN0aW9uVHlwZXMuU0VUVElOR1NfU1RPUkUsXG4gICAgICAgICAgICBjbWQ6IFN0b3JlQ21kcy5VUERBVEUsXG4gICAgICAgICAgICBkYXRhOiBzZXR0aW5nc1xuICAgICAgICB9KTtcbiAgICAgICAgKi9cbiAgICB9XG59O1xuXG52YXIgRXZlbnRMb2dBY3Rpb25zX2V2ZW50X2lkID0gMDtcbnZhciBFdmVudExvZ0FjdGlvbnMgPSB7XG4gICAgYWRkX2V2ZW50OiBmdW5jdGlvbiAobWVzc2FnZSkge1xuICAgICAgICBBcHBEaXNwYXRjaGVyLmRpc3BhdGNoVmlld0FjdGlvbih7XG4gICAgICAgICAgICB0eXBlOiBBY3Rpb25UeXBlcy5FVkVOVF9TVE9SRSxcbiAgICAgICAgICAgIGNtZDogU3RvcmVDbWRzLkFERCxcbiAgICAgICAgICAgIGRhdGE6IHtcbiAgICAgICAgICAgICAgICBtZXNzYWdlOiBtZXNzYWdlLFxuICAgICAgICAgICAgICAgIGxldmVsOiBcIndlYlwiLFxuICAgICAgICAgICAgICAgIGlkOiBcInZpZXdBY3Rpb24tXCIgKyBFdmVudExvZ0FjdGlvbnNfZXZlbnRfaWQrK1xuICAgICAgICAgICAgfVxuICAgICAgICB9KTtcbiAgICB9XG59O1xuXG52YXIgRmxvd0FjdGlvbnMgPSB7XG4gICAgYWNjZXB0OiBmdW5jdGlvbiAoZmxvdykge1xuICAgICAgICBqUXVlcnkucG9zdChcIi9mbG93cy9cIiArIGZsb3cuaWQgKyBcIi9hY2NlcHRcIik7XG4gICAgfSxcbiAgICBhY2NlcHRfYWxsOiBmdW5jdGlvbigpe1xuICAgICAgICBqUXVlcnkucG9zdChcIi9mbG93cy9hY2NlcHRcIik7XG4gICAgfSxcbiAgICBcImRlbGV0ZVwiOiBmdW5jdGlvbihmbG93KXtcbiAgICAgICAgalF1ZXJ5LmFqYXgoe1xuICAgICAgICAgICAgdHlwZTpcIkRFTEVURVwiLFxuICAgICAgICAgICAgdXJsOiBcIi9mbG93cy9cIiArIGZsb3cuaWRcbiAgICAgICAgfSk7XG4gICAgfSxcbiAgICBkdXBsaWNhdGU6IGZ1bmN0aW9uKGZsb3cpe1xuICAgICAgICBqUXVlcnkucG9zdChcIi9mbG93cy9cIiArIGZsb3cuaWQgKyBcIi9kdXBsaWNhdGVcIik7XG4gICAgfSxcbiAgICByZXBsYXk6IGZ1bmN0aW9uKGZsb3cpe1xuICAgICAgICBqUXVlcnkucG9zdChcIi9mbG93cy9cIiArIGZsb3cuaWQgKyBcIi9yZXBsYXlcIik7XG4gICAgfSxcbiAgICByZXZlcnQ6IGZ1bmN0aW9uKGZsb3cpe1xuICAgICAgICBqUXVlcnkucG9zdChcIi9mbG93cy9cIiArIGZsb3cuaWQgKyBcIi9yZXZlcnRcIik7XG4gICAgfSxcbiAgICB1cGRhdGU6IGZ1bmN0aW9uIChmbG93KSB7XG4gICAgICAgIEFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uKHtcbiAgICAgICAgICAgIHR5cGU6IEFjdGlvblR5cGVzLkZMT1dfU1RPUkUsXG4gICAgICAgICAgICBjbWQ6IFN0b3JlQ21kcy5VUERBVEUsXG4gICAgICAgICAgICBkYXRhOiBmbG93XG4gICAgICAgIH0pO1xuICAgIH0sXG4gICAgY2xlYXI6IGZ1bmN0aW9uKCl7XG4gICAgICAgIGpRdWVyeS5wb3N0KFwiL2NsZWFyXCIpO1xuICAgIH1cbn07XG5cblF1ZXJ5ID0ge1xuICAgIEZJTFRFUjogXCJmXCIsXG4gICAgSElHSExJR0hUOiBcImhcIixcbiAgICBTSE9XX0VWRU5UTE9HOiBcImVcIlxufTtcblxubW9kdWxlLmV4cG9ydHMgPSB7XG4gICAgQWN0aW9uVHlwZXM6IEFjdGlvblR5cGVzLFxuICAgIENvbm5lY3Rpb25BY3Rpb25zOiBDb25uZWN0aW9uQWN0aW9ucyxcbiAgICBGbG93QWN0aW9uczogRmxvd0FjdGlvbnMsXG4gICAgU3RvcmVDbWRzOiBTdG9yZUNtZHNcblxuXG59OyIsIlxudmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xudmFyIFJlYWN0Um91dGVyID0gcmVxdWlyZShcInJlYWN0LXJvdXRlclwiKTtcbnZhciAkID0gcmVxdWlyZShcImpxdWVyeVwiKTtcblxudmFyIENvbm5lY3Rpb24gPSByZXF1aXJlKFwiLi9jb25uZWN0aW9uXCIpO1xudmFyIHByb3h5YXBwID0gcmVxdWlyZShcIi4vY29tcG9uZW50cy9wcm94eWFwcC5qc3guanNcIik7XG5cbiQoZnVuY3Rpb24gKCkge1xuICAgIHdpbmRvdy53cyA9IG5ldyBDb25uZWN0aW9uKFwiL3VwZGF0ZXNcIik7XG5cbiAgICBSZWFjdFJvdXRlci5ydW4ocHJveHlhcHAucm91dGVzLCBmdW5jdGlvbiAoSGFuZGxlcikge1xuICAgICAgICBSZWFjdC5yZW5kZXIoUmVhY3QuY3JlYXRlRWxlbWVudChIYW5kbGVyLCBudWxsKSwgZG9jdW1lbnQuYm9keSk7XG4gICAgfSk7XG59KTsiLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XG52YXIgXyA9IHJlcXVpcmUoXCJsb2Rhc2hcIik7XG5cbnZhciB1dGlscyA9IHJlcXVpcmUoXCIuL3V0aWxzLmpzeC5qc1wiKTtcbnZhciBhY3Rpb25zID0gcmVxdWlyZShcIi4uL2FjdGlvbnMuanNcIik7XG52YXIgZmxvd3V0aWxzID0gcmVxdWlyZShcIi4uL2Zsb3cvdXRpbHMuanNcIik7XG52YXIgdG9wdXRpbHMgPSByZXF1aXJlKFwiLi4vdXRpbHMuanNcIik7XG5cbnZhciBOYXZBY3Rpb24gPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiTmF2QWN0aW9uXCIsXG4gICAgb25DbGljazogZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICB0aGlzLnByb3BzLm9uQ2xpY2soKTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImFcIiwge3RpdGxlOiB0aGlzLnByb3BzLnRpdGxlLCBcbiAgICAgICAgICAgICAgICBocmVmOiBcIiNcIiwgXG4gICAgICAgICAgICAgICAgY2xhc3NOYW1lOiBcIm5hdi1hY3Rpb25cIiwgXG4gICAgICAgICAgICAgICAgb25DbGljazogdGhpcy5vbkNsaWNrfSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge2NsYXNzTmFtZTogXCJmYSBmYS1mdyBcIiArIHRoaXMucHJvcHMuaWNvbn0pXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBGbG93RGV0YWlsTmF2ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZsb3dEZXRhaWxOYXZcIixcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG5cbiAgICAgICAgdmFyIHRhYnMgPSB0aGlzLnByb3BzLnRhYnMubWFwKGZ1bmN0aW9uIChlKSB7XG4gICAgICAgICAgICB2YXIgc3RyID0gZS5jaGFyQXQoMCkudG9VcHBlckNhc2UoKSArIGUuc2xpY2UoMSk7XG4gICAgICAgICAgICB2YXIgY2xhc3NOYW1lID0gdGhpcy5wcm9wcy5hY3RpdmUgPT09IGUgPyBcImFjdGl2ZVwiIDogXCJcIjtcbiAgICAgICAgICAgIHZhciBvbkNsaWNrID0gZnVuY3Rpb24gKGV2ZW50KSB7XG4gICAgICAgICAgICAgICAgdGhpcy5wcm9wcy5zZWxlY3RUYWIoZSk7XG4gICAgICAgICAgICAgICAgZXZlbnQucHJldmVudERlZmF1bHQoKTtcbiAgICAgICAgICAgIH0uYmluZCh0aGlzKTtcbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwiYVwiLCB7a2V5OiBlLCBcbiAgICAgICAgICAgICAgICBocmVmOiBcIiNcIiwgXG4gICAgICAgICAgICAgICAgY2xhc3NOYW1lOiBjbGFzc05hbWUsIFxuICAgICAgICAgICAgICAgIG9uQ2xpY2s6IG9uQ2xpY2t9LCBzdHIpO1xuICAgICAgICB9LmJpbmQodGhpcykpO1xuXG4gICAgICAgIHZhciBhY2NlcHRCdXR0b24gPSBudWxsO1xuICAgICAgICBpZihmbG93LmludGVyY2VwdGVkKXtcbiAgICAgICAgICAgIGFjY2VwdEJ1dHRvbiA9IFJlYWN0LmNyZWF0ZUVsZW1lbnQoTmF2QWN0aW9uLCB7dGl0bGU6IFwiW2FdY2NlcHQgaW50ZXJjZXB0ZWQgZmxvd1wiLCBpY29uOiBcImZhLXBsYXlcIiwgb25DbGljazogYWN0aW9ucy5GbG93QWN0aW9ucy5hY2NlcHQuYmluZChudWxsLCBmbG93KX0pO1xuICAgICAgICB9XG4gICAgICAgIHZhciByZXZlcnRCdXR0b24gPSBudWxsO1xuICAgICAgICBpZihmbG93Lm1vZGlmaWVkKXtcbiAgICAgICAgICAgIHJldmVydEJ1dHRvbiA9IFJlYWN0LmNyZWF0ZUVsZW1lbnQoTmF2QWN0aW9uLCB7dGl0bGU6IFwicmV2ZXJ0IGNoYW5nZXMgdG8gZmxvdyBbVl1cIiwgaWNvbjogXCJmYS1oaXN0b3J5XCIsIG9uQ2xpY2s6IGFjdGlvbnMuRmxvd0FjdGlvbnMucmV2ZXJ0LmJpbmQobnVsbCwgZmxvdyl9KTtcbiAgICAgICAgfVxuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwibmF2XCIsIHtyZWY6IFwiaGVhZFwiLCBjbGFzc05hbWU6IFwibmF2LXRhYnMgbmF2LXRhYnMtc21cIn0sIFxuICAgICAgICAgICAgICAgIHRhYnMsIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoTmF2QWN0aW9uLCB7dGl0bGU6IFwiW2RdZWxldGUgZmxvd1wiLCBpY29uOiBcImZhLXRyYXNoXCIsIG9uQ2xpY2s6IGFjdGlvbnMuRmxvd0FjdGlvbnMuZGVsZXRlLmJpbmQobnVsbCwgZmxvdyl9KSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChOYXZBY3Rpb24sIHt0aXRsZTogXCJbRF11cGxpY2F0ZSBmbG93XCIsIGljb246IFwiZmEtY29weVwiLCBvbkNsaWNrOiBhY3Rpb25zLkZsb3dBY3Rpb25zLmR1cGxpY2F0ZS5iaW5kKG51bGwsIGZsb3cpfSksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoTmF2QWN0aW9uLCB7ZGlzYWJsZWQ6IHRydWUsIHRpdGxlOiBcIltyXWVwbGF5IGZsb3dcIiwgaWNvbjogXCJmYS1yZXBlYXRcIiwgb25DbGljazogYWN0aW9ucy5GbG93QWN0aW9ucy5yZXBsYXkuYmluZChudWxsLCBmbG93KX0pLCBcbiAgICAgICAgICAgICAgICBhY2NlcHRCdXR0b24sIFxuICAgICAgICAgICAgICAgIHJldmVydEJ1dHRvblxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgSGVhZGVycyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJIZWFkZXJzXCIsXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciByb3dzID0gdGhpcy5wcm9wcy5tZXNzYWdlLmhlYWRlcnMubWFwKGZ1bmN0aW9uIChoZWFkZXIsIGkpIHtcbiAgICAgICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRyXCIsIHtrZXk6IGl9LCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIHtjbGFzc05hbWU6IFwiaGVhZGVyLW5hbWVcIn0sIGhlYWRlclswXSArIFwiOlwiKSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCB7Y2xhc3NOYW1lOiBcImhlYWRlci12YWx1ZVwifSwgaGVhZGVyWzFdKVxuICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgICk7XG4gICAgICAgIH0pO1xuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRhYmxlXCIsIHtjbGFzc05hbWU6IFwiaGVhZGVyLXRhYmxlXCJ9LCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGJvZHlcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgICAgIHJvd3NcbiAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBGbG93RGV0YWlsUmVxdWVzdCA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGbG93RGV0YWlsUmVxdWVzdFwiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgdmFyIGZpcnN0X2xpbmUgPSBbXG4gICAgICAgICAgICBmbG93LnJlcXVlc3QubWV0aG9kLFxuICAgICAgICAgICAgZmxvd3V0aWxzLlJlcXVlc3RVdGlscy5wcmV0dHlfdXJsKGZsb3cucmVxdWVzdCksXG4gICAgICAgICAgICBcIkhUVFAvXCIgKyBmbG93LnJlcXVlc3QuaHR0cHZlcnNpb24uam9pbihcIi5cIilcbiAgICAgICAgXS5qb2luKFwiIFwiKTtcbiAgICAgICAgdmFyIGNvbnRlbnQgPSBudWxsO1xuICAgICAgICBpZiAoZmxvdy5yZXF1ZXN0LmNvbnRlbnRMZW5ndGggPiAwKSB7XG4gICAgICAgICAgICBjb250ZW50ID0gXCJSZXF1ZXN0IENvbnRlbnQgU2l6ZTogXCIgKyB0b3B1dGlscy5mb3JtYXRTaXplKGZsb3cucmVxdWVzdC5jb250ZW50TGVuZ3RoKTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGNvbnRlbnQgPSBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwiYWxlcnQgYWxlcnQtaW5mb1wifSwgXCJObyBDb250ZW50XCIpO1xuICAgICAgICB9XG5cbiAgICAgICAgLy9UT0RPOiBTdHlsaW5nXG5cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJzZWN0aW9uXCIsIG51bGwsIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJmaXJzdC1saW5lXCJ9LCBmaXJzdF9saW5lICksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoSGVhZGVycywge21lc3NhZ2U6IGZsb3cucmVxdWVzdH0pLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaHJcIiwgbnVsbCksIFxuICAgICAgICAgICAgICAgIGNvbnRlbnRcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxudmFyIEZsb3dEZXRhaWxSZXNwb25zZSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGbG93RGV0YWlsUmVzcG9uc2VcIixcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG4gICAgICAgIHZhciBmaXJzdF9saW5lID0gW1xuICAgICAgICAgICAgXCJIVFRQL1wiICsgZmxvdy5yZXNwb25zZS5odHRwdmVyc2lvbi5qb2luKFwiLlwiKSxcbiAgICAgICAgICAgIGZsb3cucmVzcG9uc2UuY29kZSxcbiAgICAgICAgICAgIGZsb3cucmVzcG9uc2UubXNnXG4gICAgICAgIF0uam9pbihcIiBcIik7XG4gICAgICAgIHZhciBjb250ZW50ID0gbnVsbDtcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UuY29udGVudExlbmd0aCA+IDApIHtcbiAgICAgICAgICAgIGNvbnRlbnQgPSBcIlJlc3BvbnNlIENvbnRlbnQgU2l6ZTogXCIgKyB0b3B1dGlscy5mb3JtYXRTaXplKGZsb3cucmVzcG9uc2UuY29udGVudExlbmd0aCk7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBjb250ZW50ID0gUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcImFsZXJ0IGFsZXJ0LWluZm9cIn0sIFwiTm8gQ29udGVudFwiKTtcbiAgICAgICAgfVxuXG4gICAgICAgIC8vVE9ETzogU3R5bGluZ1xuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwic2VjdGlvblwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwiZmlyc3QtbGluZVwifSwgZmlyc3RfbGluZSApLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KEhlYWRlcnMsIHttZXNzYWdlOiBmbG93LnJlc3BvbnNlfSksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJoclwiLCBudWxsKSwgXG4gICAgICAgICAgICAgICAgY29udGVudFxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgRmxvd0RldGFpbEVycm9yID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZsb3dEZXRhaWxFcnJvclwiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJzZWN0aW9uXCIsIG51bGwsIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJhbGVydCBhbGVydC13YXJuaW5nXCJ9LCBcbiAgICAgICAgICAgICAgICBmbG93LmVycm9yLm1zZywgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwic21hbGxcIiwgbnVsbCwgIHRvcHV0aWxzLmZvcm1hdFRpbWVTdGFtcChmbG93LmVycm9yLnRpbWVzdGFtcCkgKVxuICAgICAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgVGltZVN0YW1wID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlRpbWVTdGFtcFwiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuXG4gICAgICAgIGlmICghdGhpcy5wcm9wcy50KSB7XG4gICAgICAgICAgICAvL3Nob3VsZCBiZSByZXR1cm4gbnVsbCwgYnV0IHRoYXQgdHJpZ2dlcnMgYSBSZWFjdCBidWcuXG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRyXCIsIG51bGwpO1xuICAgICAgICB9XG5cbiAgICAgICAgdmFyIHRzID0gdG9wdXRpbHMuZm9ybWF0VGltZVN0YW1wKHRoaXMucHJvcHMudCk7XG5cbiAgICAgICAgdmFyIGRlbHRhO1xuICAgICAgICBpZiAodGhpcy5wcm9wcy5kZWx0YVRvKSB7XG4gICAgICAgICAgICBkZWx0YSA9IHRvcHV0aWxzLmZvcm1hdFRpbWVEZWx0YSgxMDAwICogKHRoaXMucHJvcHMudCAtIHRoaXMucHJvcHMuZGVsdGFUbykpO1xuICAgICAgICAgICAgZGVsdGEgPSBSZWFjdC5jcmVhdGVFbGVtZW50KFwic3BhblwiLCB7Y2xhc3NOYW1lOiBcInRleHQtbXV0ZWRcIn0sIFwiKFwiICsgZGVsdGEgKyBcIilcIik7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBkZWx0YSA9IG51bGw7XG4gICAgICAgIH1cblxuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRyXCIsIG51bGwsIFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIG51bGwsIHRoaXMucHJvcHMudGl0bGUgKyBcIjpcIiksIFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIG51bGwsIHRzLCBcIiBcIiwgZGVsdGEpXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBDb25uZWN0aW9uSW5mbyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJDb25uZWN0aW9uSW5mb1wiLFxuXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBjb25uID0gdGhpcy5wcm9wcy5jb25uO1xuICAgICAgICB2YXIgYWRkcmVzcyA9IGNvbm4uYWRkcmVzcy5hZGRyZXNzLmpvaW4oXCI6XCIpO1xuXG4gICAgICAgIHZhciBzbmkgPSBSZWFjdC5jcmVhdGVFbGVtZW50KFwidHJcIiwge2tleTogXCJzbmlcIn0pOyAvL3Nob3VsZCBiZSBudWxsLCBidXQgdGhhdCB0cmlnZ2VycyBhIFJlYWN0IGJ1Zy5cbiAgICAgICAgaWYgKGNvbm4uc25pKSB7XG4gICAgICAgICAgICBzbmkgPSBSZWFjdC5jcmVhdGVFbGVtZW50KFwidHJcIiwge2tleTogXCJzbmlcIn0sIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImFiYnJcIiwge3RpdGxlOiBcIlRMUyBTZXJ2ZXIgTmFtZSBJbmRpY2F0aW9uXCJ9LCBcIlRMUyBTTkk6XCIpXG4gICAgICAgICAgICAgICAgKSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIG51bGwsIGNvbm4uc25pKVxuICAgICAgICAgICAgKTtcbiAgICAgICAgfVxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRhYmxlXCIsIHtjbGFzc05hbWU6IFwiY29ubmVjdGlvbi10YWJsZVwifSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRib2R5XCIsIG51bGwsIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidHJcIiwge2tleTogXCJhZGRyZXNzXCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCBudWxsLCBcIkFkZHJlc3M6XCIpLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCBudWxsLCBhZGRyZXNzKVxuICAgICAgICAgICAgICAgICAgICApLCBcbiAgICAgICAgICAgICAgICAgICAgc25pXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgQ2VydGlmaWNhdGVJbmZvID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkNlcnRpZmljYXRlSW5mb1wiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICAvL1RPRE86IFdlIHNob3VsZCBmZXRjaCBodW1hbi1yZWFkYWJsZSBjZXJ0aWZpY2F0ZSByZXByZXNlbnRhdGlvblxuICAgICAgICAvLyBmcm9tIHRoZSBzZXJ2ZXJcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG4gICAgICAgIHZhciBjbGllbnRfY29ubiA9IGZsb3cuY2xpZW50X2Nvbm47XG4gICAgICAgIHZhciBzZXJ2ZXJfY29ubiA9IGZsb3cuc2VydmVyX2Nvbm47XG5cbiAgICAgICAgdmFyIHByZVN0eWxlID0ge21heEhlaWdodDogMTAwfTtcbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwgbnVsbCwgXG4gICAgICAgICAgICBjbGllbnRfY29ubi5jZXJ0ID8gUmVhY3QuY3JlYXRlRWxlbWVudChcImg0XCIsIG51bGwsIFwiQ2xpZW50IENlcnRpZmljYXRlXCIpIDogbnVsbCwgXG4gICAgICAgICAgICBjbGllbnRfY29ubi5jZXJ0ID8gUmVhY3QuY3JlYXRlRWxlbWVudChcInByZVwiLCB7c3R5bGU6IHByZVN0eWxlfSwgY2xpZW50X2Nvbm4uY2VydCkgOiBudWxsLCBcblxuICAgICAgICAgICAgc2VydmVyX2Nvbm4uY2VydCA/IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJoNFwiLCBudWxsLCBcIlNlcnZlciBDZXJ0aWZpY2F0ZVwiKSA6IG51bGwsIFxuICAgICAgICAgICAgc2VydmVyX2Nvbm4uY2VydCA/IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJwcmVcIiwge3N0eWxlOiBwcmVTdHlsZX0sIHNlcnZlcl9jb25uLmNlcnQpIDogbnVsbFxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgVGltaW5nID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlRpbWluZ1wiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgdmFyIHNjID0gZmxvdy5zZXJ2ZXJfY29ubjtcbiAgICAgICAgdmFyIGNjID0gZmxvdy5jbGllbnRfY29ubjtcbiAgICAgICAgdmFyIHJlcSA9IGZsb3cucmVxdWVzdDtcbiAgICAgICAgdmFyIHJlc3AgPSBmbG93LnJlc3BvbnNlO1xuXG4gICAgICAgIHZhciB0aW1lc3RhbXBzID0gW1xuICAgICAgICAgICAge1xuICAgICAgICAgICAgICAgIHRpdGxlOiBcIlNlcnZlciBjb25uLiBpbml0aWF0ZWRcIixcbiAgICAgICAgICAgICAgICB0OiBzYy50aW1lc3RhbXBfc3RhcnQsXG4gICAgICAgICAgICAgICAgZGVsdGFUbzogcmVxLnRpbWVzdGFtcF9zdGFydFxuICAgICAgICAgICAgfSwge1xuICAgICAgICAgICAgICAgIHRpdGxlOiBcIlNlcnZlciBjb25uLiBUQ1AgaGFuZHNoYWtlXCIsXG4gICAgICAgICAgICAgICAgdDogc2MudGltZXN0YW1wX3RjcF9zZXR1cCxcbiAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XG4gICAgICAgICAgICB9LCB7XG4gICAgICAgICAgICAgICAgdGl0bGU6IFwiU2VydmVyIGNvbm4uIFNTTCBoYW5kc2hha2VcIixcbiAgICAgICAgICAgICAgICB0OiBzYy50aW1lc3RhbXBfc3NsX3NldHVwLFxuICAgICAgICAgICAgICAgIGRlbHRhVG86IHJlcS50aW1lc3RhbXBfc3RhcnRcbiAgICAgICAgICAgIH0sIHtcbiAgICAgICAgICAgICAgICB0aXRsZTogXCJDbGllbnQgY29ubi4gZXN0YWJsaXNoZWRcIixcbiAgICAgICAgICAgICAgICB0OiBjYy50aW1lc3RhbXBfc3RhcnQsXG4gICAgICAgICAgICAgICAgZGVsdGFUbzogcmVxLnRpbWVzdGFtcF9zdGFydFxuICAgICAgICAgICAgfSwge1xuICAgICAgICAgICAgICAgIHRpdGxlOiBcIkNsaWVudCBjb25uLiBTU0wgaGFuZHNoYWtlXCIsXG4gICAgICAgICAgICAgICAgdDogY2MudGltZXN0YW1wX3NzbF9zZXR1cCxcbiAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XG4gICAgICAgICAgICB9LCB7XG4gICAgICAgICAgICAgICAgdGl0bGU6IFwiRmlyc3QgcmVxdWVzdCBieXRlXCIsXG4gICAgICAgICAgICAgICAgdDogcmVxLnRpbWVzdGFtcF9zdGFydCxcbiAgICAgICAgICAgIH0sIHtcbiAgICAgICAgICAgICAgICB0aXRsZTogXCJSZXF1ZXN0IGNvbXBsZXRlXCIsXG4gICAgICAgICAgICAgICAgdDogcmVxLnRpbWVzdGFtcF9lbmQsXG4gICAgICAgICAgICAgICAgZGVsdGFUbzogcmVxLnRpbWVzdGFtcF9zdGFydFxuICAgICAgICAgICAgfVxuICAgICAgICBdO1xuXG4gICAgICAgIGlmIChmbG93LnJlc3BvbnNlKSB7XG4gICAgICAgICAgICB0aW1lc3RhbXBzLnB1c2goXG4gICAgICAgICAgICAgICAge1xuICAgICAgICAgICAgICAgICAgICB0aXRsZTogXCJGaXJzdCByZXNwb25zZSBieXRlXCIsXG4gICAgICAgICAgICAgICAgICAgIHQ6IHJlc3AudGltZXN0YW1wX3N0YXJ0LFxuICAgICAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XG4gICAgICAgICAgICAgICAgfSwge1xuICAgICAgICAgICAgICAgICAgICB0aXRsZTogXCJSZXNwb25zZSBjb21wbGV0ZVwiLFxuICAgICAgICAgICAgICAgICAgICB0OiByZXNwLnRpbWVzdGFtcF9lbmQsXG4gICAgICAgICAgICAgICAgICAgIGRlbHRhVG86IHJlcS50aW1lc3RhbXBfc3RhcnRcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICApO1xuICAgICAgICB9XG5cbiAgICAgICAgLy9BZGQgdW5pcXVlIGtleSBmb3IgZWFjaCByb3cuXG4gICAgICAgIHRpbWVzdGFtcHMuZm9yRWFjaChmdW5jdGlvbiAoZSkge1xuICAgICAgICAgICAgZS5rZXkgPSBlLnRpdGxlO1xuICAgICAgICB9KTtcblxuICAgICAgICB0aW1lc3RhbXBzID0gXy5zb3J0QnkodGltZXN0YW1wcywgJ3QnKTtcblxuICAgICAgICB2YXIgcm93cyA9IHRpbWVzdGFtcHMubWFwKGZ1bmN0aW9uIChlKSB7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChUaW1lU3RhbXAsIFJlYWN0Ll9fc3ByZWFkKHt9LCAgZSkpO1xuICAgICAgICB9KTtcblxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaDRcIiwgbnVsbCwgXCJUaW1pbmdcIiksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0YWJsZVwiLCB7Y2xhc3NOYW1lOiBcInRpbWluZy10YWJsZVwifSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0Ym9keVwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICAgICAgcm93c1xuICAgICAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgRmxvd0RldGFpbENvbm5lY3Rpb25JbmZvID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZsb3dEZXRhaWxDb25uZWN0aW9uSW5mb1wiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgdmFyIGNsaWVudF9jb25uID0gZmxvdy5jbGllbnRfY29ubjtcbiAgICAgICAgdmFyIHNlcnZlcl9jb25uID0gZmxvdy5zZXJ2ZXJfY29ubjtcbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJzZWN0aW9uXCIsIG51bGwsIFxuXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImg0XCIsIG51bGwsIFwiQ2xpZW50IENvbm5lY3Rpb25cIiksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoQ29ubmVjdGlvbkluZm8sIHtjb25uOiBjbGllbnRfY29ubn0pLCBcblxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJoNFwiLCBudWxsLCBcIlNlcnZlciBDb25uZWN0aW9uXCIpLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KENvbm5lY3Rpb25JbmZvLCB7Y29ubjogc2VydmVyX2Nvbm59KSwgXG5cbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KENlcnRpZmljYXRlSW5mbywge2Zsb3c6IGZsb3d9KSwgXG5cbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFRpbWluZywge2Zsb3c6IGZsb3d9KVxuXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBhbGxUYWJzID0ge1xuICAgIHJlcXVlc3Q6IEZsb3dEZXRhaWxSZXF1ZXN0LFxuICAgIHJlc3BvbnNlOiBGbG93RGV0YWlsUmVzcG9uc2UsXG4gICAgZXJyb3I6IEZsb3dEZXRhaWxFcnJvcixcbiAgICBkZXRhaWxzOiBGbG93RGV0YWlsQ29ubmVjdGlvbkluZm9cbn07XG5cbnZhciBGbG93RGV0YWlsID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZsb3dEZXRhaWxcIixcbiAgICBtaXhpbnM6IFt1dGlscy5TdGlja3lIZWFkTWl4aW4sIHV0aWxzLk5hdmlnYXRpb24sIHV0aWxzLlN0YXRlXSxcbiAgICBnZXRUYWJzOiBmdW5jdGlvbiAoZmxvdykge1xuICAgICAgICB2YXIgdGFicyA9IFtdO1xuICAgICAgICBbXCJyZXF1ZXN0XCIsIFwicmVzcG9uc2VcIiwgXCJlcnJvclwiXS5mb3JFYWNoKGZ1bmN0aW9uIChlKSB7XG4gICAgICAgICAgICBpZiAoZmxvd1tlXSkge1xuICAgICAgICAgICAgICAgIHRhYnMucHVzaChlKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgfSk7XG4gICAgICAgIHRhYnMucHVzaChcImRldGFpbHNcIik7XG4gICAgICAgIHJldHVybiB0YWJzO1xuICAgIH0sXG4gICAgbmV4dFRhYjogZnVuY3Rpb24gKGkpIHtcbiAgICAgICAgdmFyIHRhYnMgPSB0aGlzLmdldFRhYnModGhpcy5wcm9wcy5mbG93KTtcbiAgICAgICAgdmFyIGN1cnJlbnRJbmRleCA9IHRhYnMuaW5kZXhPZih0aGlzLmdldFBhcmFtcygpLmRldGFpbFRhYik7XG4gICAgICAgIC8vIEpTIG1vZHVsbyBvcGVyYXRvciBkb2Vzbid0IGNvcnJlY3QgbmVnYXRpdmUgbnVtYmVycywgbWFrZSBzdXJlIHRoYXQgd2UgYXJlIHBvc2l0aXZlLlxuICAgICAgICB2YXIgbmV4dEluZGV4ID0gKGN1cnJlbnRJbmRleCArIGkgKyB0YWJzLmxlbmd0aCkgJSB0YWJzLmxlbmd0aDtcbiAgICAgICAgdGhpcy5zZWxlY3RUYWIodGFic1tuZXh0SW5kZXhdKTtcbiAgICB9LFxuICAgIHNlbGVjdFRhYjogZnVuY3Rpb24gKHBhbmVsKSB7XG4gICAgICAgIHRoaXMucmVwbGFjZVdpdGgoXG4gICAgICAgICAgICBcImZsb3dcIixcbiAgICAgICAgICAgIHtcbiAgICAgICAgICAgICAgICBmbG93SWQ6IHRoaXMuZ2V0UGFyYW1zKCkuZmxvd0lkLFxuICAgICAgICAgICAgICAgIGRldGFpbFRhYjogcGFuZWxcbiAgICAgICAgICAgIH1cbiAgICAgICAgKTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgdmFyIHRhYnMgPSB0aGlzLmdldFRhYnMoZmxvdyk7XG4gICAgICAgIHZhciBhY3RpdmUgPSB0aGlzLmdldFBhcmFtcygpLmRldGFpbFRhYjtcblxuICAgICAgICBpZiAoIV8uY29udGFpbnModGFicywgYWN0aXZlKSkge1xuICAgICAgICAgICAgaWYgKGFjdGl2ZSA9PT0gXCJyZXNwb25zZVwiICYmIGZsb3cuZXJyb3IpIHtcbiAgICAgICAgICAgICAgICBhY3RpdmUgPSBcImVycm9yXCI7XG4gICAgICAgICAgICB9IGVsc2UgaWYgKGFjdGl2ZSA9PT0gXCJlcnJvclwiICYmIGZsb3cucmVzcG9uc2UpIHtcbiAgICAgICAgICAgICAgICBhY3RpdmUgPSBcInJlc3BvbnNlXCI7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIGFjdGl2ZSA9IHRhYnNbMF07XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICB0aGlzLnNlbGVjdFRhYihhY3RpdmUpO1xuICAgICAgICB9XG5cbiAgICAgICAgdmFyIFRhYiA9IGFsbFRhYnNbYWN0aXZlXTtcbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJmbG93LWRldGFpbFwiLCBvblNjcm9sbDogdGhpcy5hZGp1c3RIZWFkfSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChGbG93RGV0YWlsTmF2LCB7cmVmOiBcImhlYWRcIiwgXG4gICAgICAgICAgICAgICAgICAgIGZsb3c6IGZsb3csIFxuICAgICAgICAgICAgICAgICAgICB0YWJzOiB0YWJzLCBcbiAgICAgICAgICAgICAgICAgICAgYWN0aXZlOiBhY3RpdmUsIFxuICAgICAgICAgICAgICAgICAgICBzZWxlY3RUYWI6IHRoaXMuc2VsZWN0VGFifSksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoVGFiLCB7ZmxvdzogZmxvd30pXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbm1vZHVsZS5leHBvcnRzID0ge1xuICAgIEZsb3dEZXRhaWw6IEZsb3dEZXRhaWxcbn07IiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xudmFyIGZsb3d1dGlscyA9IHJlcXVpcmUoXCIuLi9mbG93L3V0aWxzLmpzXCIpO1xudmFyIHV0aWxzID0gcmVxdWlyZShcIi4uL3V0aWxzLmpzXCIpO1xuXG52YXIgVExTQ29sdW1uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlRMU0NvbHVtblwiLFxuICAgIHN0YXRpY3M6IHtcbiAgICAgICAgcmVuZGVyVGl0bGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGhcIiwge2tleTogXCJ0bHNcIiwgY2xhc3NOYW1lOiBcImNvbC10bHNcIn0pO1xuICAgICAgICB9XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG4gICAgICAgIHZhciBzc2wgPSAoZmxvdy5yZXF1ZXN0LnNjaGVtZSA9PSBcImh0dHBzXCIpO1xuICAgICAgICB2YXIgY2xhc3NlcztcbiAgICAgICAgaWYgKHNzbCkge1xuICAgICAgICAgICAgY2xhc3NlcyA9IFwiY29sLXRscyBjb2wtdGxzLWh0dHBzXCI7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBjbGFzc2VzID0gXCJjb2wtdGxzIGNvbC10bHMtaHR0cFwiO1xuICAgICAgICB9XG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwge2NsYXNzTmFtZTogY2xhc3Nlc30pO1xuICAgIH1cbn0pO1xuXG5cbnZhciBJY29uQ29sdW1uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkljb25Db2x1bW5cIixcbiAgICBzdGF0aWNzOiB7XG4gICAgICAgIHJlbmRlclRpdGxlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRoXCIsIHtrZXk6IFwiaWNvblwiLCBjbGFzc05hbWU6IFwiY29sLWljb25cIn0pO1xuICAgICAgICB9XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG5cbiAgICAgICAgdmFyIGljb247XG4gICAgICAgIGlmIChmbG93LnJlc3BvbnNlKSB7XG4gICAgICAgICAgICB2YXIgY29udGVudFR5cGUgPSBmbG93dXRpbHMuUmVzcG9uc2VVdGlscy5nZXRDb250ZW50VHlwZShmbG93LnJlc3BvbnNlKTtcblxuICAgICAgICAgICAgLy9UT0RPOiBXZSBzaG91bGQgYXNzaWduIGEgdHlwZSB0byB0aGUgZmxvdyBzb21ld2hlcmUgZWxzZS5cbiAgICAgICAgICAgIGlmIChmbG93LnJlc3BvbnNlLmNvZGUgPT0gMzA0KSB7XG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1ub3QtbW9kaWZpZWRcIjtcbiAgICAgICAgICAgIH0gZWxzZSBpZiAoMzAwIDw9IGZsb3cucmVzcG9uc2UuY29kZSAmJiBmbG93LnJlc3BvbnNlLmNvZGUgPCA0MDApIHtcbiAgICAgICAgICAgICAgICBpY29uID0gXCJyZXNvdXJjZS1pY29uLXJlZGlyZWN0XCI7XG4gICAgICAgICAgICB9IGVsc2UgaWYgKGNvbnRlbnRUeXBlICYmIGNvbnRlbnRUeXBlLmluZGV4T2YoXCJpbWFnZVwiKSA+PSAwKSB7XG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1pbWFnZVwiO1xuICAgICAgICAgICAgfSBlbHNlIGlmIChjb250ZW50VHlwZSAmJiBjb250ZW50VHlwZS5pbmRleE9mKFwiamF2YXNjcmlwdFwiKSA+PSAwKSB7XG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1qc1wiO1xuICAgICAgICAgICAgfSBlbHNlIGlmIChjb250ZW50VHlwZSAmJiBjb250ZW50VHlwZS5pbmRleE9mKFwiY3NzXCIpID49IDApIHtcbiAgICAgICAgICAgICAgICBpY29uID0gXCJyZXNvdXJjZS1pY29uLWNzc1wiO1xuICAgICAgICAgICAgfSBlbHNlIGlmIChjb250ZW50VHlwZSAmJiBjb250ZW50VHlwZS5pbmRleE9mKFwiaHRtbFwiKSA+PSAwKSB7XG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1kb2N1bWVudFwiO1xuICAgICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICAgIGlmICghaWNvbikge1xuICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1wbGFpblwiO1xuICAgICAgICB9XG5cblxuICAgICAgICBpY29uICs9IFwiIHJlc291cmNlLWljb25cIjtcbiAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCB7Y2xhc3NOYW1lOiBcImNvbC1pY29uXCJ9LCBcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogaWNvbn0pXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBQYXRoQ29sdW1uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlBhdGhDb2x1bW5cIixcbiAgICBzdGF0aWNzOiB7XG4gICAgICAgIHJlbmRlclRpdGxlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRoXCIsIHtrZXk6IFwicGF0aFwiLCBjbGFzc05hbWU6IFwiY29sLXBhdGhcIn0sIFwiUGF0aFwiKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIHtjbGFzc05hbWU6IFwiY29sLXBhdGhcIn0sIFxuICAgICAgICAgICAgZmxvdy5yZXF1ZXN0LmlzX3JlcGxheSA/IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJpXCIsIHtjbGFzc05hbWU6IFwiZmEgZmEtZncgZmEtcmVwZWF0IHB1bGwtcmlnaHRcIn0pIDogbnVsbCwgXG4gICAgICAgICAgICBmbG93LmludGVyY2VwdGVkID8gUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge2NsYXNzTmFtZTogXCJmYSBmYS1mdyBmYS1wYXVzZSBwdWxsLXJpZ2h0XCJ9KSA6IG51bGwsIFxuICAgICAgICAgICAgZmxvdy5yZXF1ZXN0LnNjaGVtZSArIFwiOi8vXCIgKyBmbG93LnJlcXVlc3QuaG9zdCArIGZsb3cucmVxdWVzdC5wYXRoXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cblxudmFyIE1ldGhvZENvbHVtbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJNZXRob2RDb2x1bW5cIixcbiAgICBzdGF0aWNzOiB7XG4gICAgICAgIHJlbmRlclRpdGxlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRoXCIsIHtrZXk6IFwibWV0aG9kXCIsIGNsYXNzTmFtZTogXCJjb2wtbWV0aG9kXCJ9LCBcIk1ldGhvZFwiKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIHtjbGFzc05hbWU6IFwiY29sLW1ldGhvZFwifSwgZmxvdy5yZXF1ZXN0Lm1ldGhvZCk7XG4gICAgfVxufSk7XG5cblxudmFyIFN0YXR1c0NvbHVtbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJTdGF0dXNDb2x1bW5cIixcbiAgICBzdGF0aWNzOiB7XG4gICAgICAgIHJlbmRlclRpdGxlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRoXCIsIHtrZXk6IFwic3RhdHVzXCIsIGNsYXNzTmFtZTogXCJjb2wtc3RhdHVzXCJ9LCBcIlN0YXR1c1wiKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuICAgICAgICB2YXIgc3RhdHVzO1xuICAgICAgICBpZiAoZmxvdy5yZXNwb25zZSkge1xuICAgICAgICAgICAgc3RhdHVzID0gZmxvdy5yZXNwb25zZS5jb2RlO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgc3RhdHVzID0gbnVsbDtcbiAgICAgICAgfVxuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIHtjbGFzc05hbWU6IFwiY29sLXN0YXR1c1wifSwgc3RhdHVzKTtcbiAgICB9XG59KTtcblxuXG52YXIgU2l6ZUNvbHVtbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJTaXplQ29sdW1uXCIsXG4gICAgc3RhdGljczoge1xuICAgICAgICByZW5kZXJUaXRsZTogZnVuY3Rpb24gKCkge1xuICAgICAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0aFwiLCB7a2V5OiBcInNpemVcIiwgY2xhc3NOYW1lOiBcImNvbC1zaXplXCJ9LCBcIlNpemVcIik7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcblxuICAgICAgICB2YXIgdG90YWwgPSBmbG93LnJlcXVlc3QuY29udGVudExlbmd0aDtcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UpIHtcbiAgICAgICAgICAgIHRvdGFsICs9IGZsb3cucmVzcG9uc2UuY29udGVudExlbmd0aCB8fCAwO1xuICAgICAgICB9XG4gICAgICAgIHZhciBzaXplID0gdXRpbHMuZm9ybWF0U2l6ZSh0b3RhbCk7XG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwge2NsYXNzTmFtZTogXCJjb2wtc2l6ZVwifSwgc2l6ZSk7XG4gICAgfVxufSk7XG5cblxudmFyIFRpbWVDb2x1bW4gPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiVGltZUNvbHVtblwiLFxuICAgIHN0YXRpY3M6IHtcbiAgICAgICAgcmVuZGVyVGl0bGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGhcIiwge2tleTogXCJ0aW1lXCIsIGNsYXNzTmFtZTogXCJjb2wtdGltZVwifSwgXCJUaW1lXCIpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG4gICAgICAgIHZhciB0aW1lO1xuICAgICAgICBpZiAoZmxvdy5yZXNwb25zZSkge1xuICAgICAgICAgICAgdGltZSA9IHV0aWxzLmZvcm1hdFRpbWVEZWx0YSgxMDAwICogKGZsb3cucmVzcG9uc2UudGltZXN0YW1wX2VuZCAtIGZsb3cucmVxdWVzdC50aW1lc3RhbXBfc3RhcnQpKTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHRpbWUgPSBcIi4uLlwiO1xuICAgICAgICB9XG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwge2NsYXNzTmFtZTogXCJjb2wtdGltZVwifSwgdGltZSk7XG4gICAgfVxufSk7XG5cblxudmFyIGFsbF9jb2x1bW5zID0gW1xuICAgIFRMU0NvbHVtbixcbiAgICBJY29uQ29sdW1uLFxuICAgIFBhdGhDb2x1bW4sXG4gICAgTWV0aG9kQ29sdW1uLFxuICAgIFN0YXR1c0NvbHVtbixcbiAgICBTaXplQ29sdW1uLFxuICAgIFRpbWVDb2x1bW5dO1xuXG5cbm1vZHVsZS5leHBvcnRzID0gYWxsX2NvbHVtbnM7XG5cblxuIiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xudmFyIHV0aWxzID0gcmVxdWlyZShcIi4vdXRpbHMuanN4LmpzXCIpO1xudmFyIFZpcnR1YWxTY3JvbGxNaXhpbiA9IHJlcXVpcmUoXCIuL3ZpcnR1YWxzY3JvbGwuanN4LmpzXCIpO1xudmFyIGZsb3d0YWJsZV9jb2x1bW5zID0gcmVxdWlyZShcIi4vZmxvd3RhYmxlLWNvbHVtbnMuanN4LmpzXCIpO1xuXG52YXIgRmxvd1JvdyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGbG93Um93XCIsXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuICAgICAgICB2YXIgY29sdW1ucyA9IHRoaXMucHJvcHMuY29sdW1ucy5tYXAoZnVuY3Rpb24gKENvbHVtbikge1xuICAgICAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoQ29sdW1uLCB7a2V5OiBDb2x1bW4uZGlzcGxheU5hbWUsIGZsb3c6IGZsb3d9KTtcbiAgICAgICAgfS5iaW5kKHRoaXMpKTtcbiAgICAgICAgdmFyIGNsYXNzTmFtZSA9IFwiXCI7XG4gICAgICAgIGlmICh0aGlzLnByb3BzLnNlbGVjdGVkKSB7XG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCIgc2VsZWN0ZWRcIjtcbiAgICAgICAgfVxuICAgICAgICBpZiAodGhpcy5wcm9wcy5oaWdobGlnaHRlZCkge1xuICAgICAgICAgICAgY2xhc3NOYW1lICs9IFwiIGhpZ2hsaWdodGVkXCI7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKGZsb3cuaW50ZXJjZXB0ZWQpIHtcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcIiBpbnRlcmNlcHRlZFwiO1xuICAgICAgICB9XG4gICAgICAgIGlmIChmbG93LnJlcXVlc3QpIHtcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcIiBoYXMtcmVxdWVzdFwiO1xuICAgICAgICB9XG4gICAgICAgIGlmIChmbG93LnJlc3BvbnNlKSB7XG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCIgaGFzLXJlc3BvbnNlXCI7XG4gICAgICAgIH1cblxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRyXCIsIHtjbGFzc05hbWU6IGNsYXNzTmFtZSwgb25DbGljazogdGhpcy5wcm9wcy5zZWxlY3RGbG93LmJpbmQobnVsbCwgZmxvdyl9LCBcbiAgICAgICAgICAgICAgICBjb2x1bW5zXG4gICAgICAgICAgICApKTtcbiAgICB9LFxuICAgIHNob3VsZENvbXBvbmVudFVwZGF0ZTogZnVuY3Rpb24gKG5leHRQcm9wcykge1xuICAgICAgICByZXR1cm4gdHJ1ZTtcbiAgICAgICAgLy8gRnVydGhlciBvcHRpbWl6YXRpb24gY291bGQgYmUgZG9uZSBoZXJlXG4gICAgICAgIC8vIGJ5IGNhbGxpbmcgZm9yY2VVcGRhdGUgb24gZmxvdyB1cGRhdGVzLCBzZWxlY3Rpb24gY2hhbmdlcyBhbmQgY29sdW1uIGNoYW5nZXMuXG4gICAgICAgIC8vcmV0dXJuIChcbiAgICAgICAgLy8odGhpcy5wcm9wcy5jb2x1bW5zLmxlbmd0aCAhPT0gbmV4dFByb3BzLmNvbHVtbnMubGVuZ3RoKSB8fFxuICAgICAgICAvLyh0aGlzLnByb3BzLnNlbGVjdGVkICE9PSBuZXh0UHJvcHMuc2VsZWN0ZWQpXG4gICAgICAgIC8vKTtcbiAgICB9XG59KTtcblxudmFyIEZsb3dUYWJsZUhlYWQgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiRmxvd1RhYmxlSGVhZFwiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgY29sdW1ucyA9IHRoaXMucHJvcHMuY29sdW1ucy5tYXAoZnVuY3Rpb24gKGNvbHVtbikge1xuICAgICAgICAgICAgcmV0dXJuIGNvbHVtbi5yZW5kZXJUaXRsZSgpO1xuICAgICAgICB9LmJpbmQodGhpcykpO1xuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRoZWFkXCIsIG51bGwsIFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRyXCIsIG51bGwsIGNvbHVtbnMpXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cblxudmFyIFJPV19IRUlHSFQgPSAzMjtcblxudmFyIEZsb3dUYWJsZSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGbG93VGFibGVcIixcbiAgICBtaXhpbnM6IFt1dGlscy5TdGlja3lIZWFkTWl4aW4sIHV0aWxzLkF1dG9TY3JvbGxNaXhpbiwgVmlydHVhbFNjcm9sbE1peGluXSxcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgIGNvbHVtbnM6IGZsb3d0YWJsZV9jb2x1bW5zXG4gICAgICAgIH07XG4gICAgfSxcbiAgICBjb21wb25lbnRXaWxsTW91bnQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgaWYgKHRoaXMucHJvcHMudmlldykge1xuICAgICAgICAgICAgdGhpcy5wcm9wcy52aWV3LmFkZExpc3RlbmVyKFwiYWRkIHVwZGF0ZSByZW1vdmUgcmVjYWxjdWxhdGVcIiwgdGhpcy5vbkNoYW5nZSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxSZWNlaXZlUHJvcHM6IGZ1bmN0aW9uIChuZXh0UHJvcHMpIHtcbiAgICAgICAgaWYgKG5leHRQcm9wcy52aWV3ICE9PSB0aGlzLnByb3BzLnZpZXcpIHtcbiAgICAgICAgICAgIGlmICh0aGlzLnByb3BzLnZpZXcpIHtcbiAgICAgICAgICAgICAgICB0aGlzLnByb3BzLnZpZXcucmVtb3ZlTGlzdGVuZXIoXCJhZGQgdXBkYXRlIHJlbW92ZSByZWNhbGN1bGF0ZVwiKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIG5leHRQcm9wcy52aWV3LmFkZExpc3RlbmVyKFwiYWRkIHVwZGF0ZSByZW1vdmUgcmVjYWxjdWxhdGVcIiwgdGhpcy5vbkNoYW5nZSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGdldERlZmF1bHRQcm9wczogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgcm93SGVpZ2h0OiBST1dfSEVJR0hUXG4gICAgICAgIH07XG4gICAgfSxcbiAgICBvblNjcm9sbEZsb3dUYWJsZTogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLmFkanVzdEhlYWQoKTtcbiAgICAgICAgdGhpcy5vblNjcm9sbCgpO1xuICAgIH0sXG4gICAgb25DaGFuZ2U6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5mb3JjZVVwZGF0ZSgpO1xuICAgIH0sXG4gICAgc2Nyb2xsSW50b1ZpZXc6IGZ1bmN0aW9uIChmbG93KSB7XG4gICAgICAgIHRoaXMuc2Nyb2xsUm93SW50b1ZpZXcoXG4gICAgICAgICAgICB0aGlzLnByb3BzLnZpZXcuaW5kZXgoZmxvdyksXG4gICAgICAgICAgICB0aGlzLnJlZnMuYm9keS5nZXRET01Ob2RlKCkub2Zmc2V0VG9wXG4gICAgICAgICk7XG4gICAgfSxcbiAgICByZW5kZXJSb3c6IGZ1bmN0aW9uIChmbG93KSB7XG4gICAgICAgIHZhciBzZWxlY3RlZCA9IChmbG93ID09PSB0aGlzLnByb3BzLnNlbGVjdGVkKTtcbiAgICAgICAgdmFyIGhpZ2hsaWdodGVkID1cbiAgICAgICAgICAgIChcbiAgICAgICAgICAgIHRoaXMucHJvcHMudmlldy5faGlnaGxpZ2h0ICYmXG4gICAgICAgICAgICB0aGlzLnByb3BzLnZpZXcuX2hpZ2hsaWdodFtmbG93LmlkXVxuICAgICAgICAgICAgKTtcblxuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChGbG93Um93LCB7a2V5OiBmbG93LmlkLCBcbiAgICAgICAgICAgIHJlZjogZmxvdy5pZCwgXG4gICAgICAgICAgICBmbG93OiBmbG93LCBcbiAgICAgICAgICAgIGNvbHVtbnM6IHRoaXMuc3RhdGUuY29sdW1ucywgXG4gICAgICAgICAgICBzZWxlY3RlZDogc2VsZWN0ZWQsIFxuICAgICAgICAgICAgaGlnaGxpZ2h0ZWQ6IGhpZ2hsaWdodGVkLCBcbiAgICAgICAgICAgIHNlbGVjdEZsb3c6IHRoaXMucHJvcHMuc2VsZWN0Rmxvd31cbiAgICAgICAgKTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICAvL2NvbnNvbGUubG9nKFwicmVuZGVyIGZsb3d0YWJsZVwiLCB0aGlzLnN0YXRlLnN0YXJ0LCB0aGlzLnN0YXRlLnN0b3AsIHRoaXMucHJvcHMuc2VsZWN0ZWQpO1xuICAgICAgICB2YXIgZmxvd3MgPSB0aGlzLnByb3BzLnZpZXcgPyB0aGlzLnByb3BzLnZpZXcubGlzdCA6IFtdO1xuXG4gICAgICAgIHZhciByb3dzID0gdGhpcy5yZW5kZXJSb3dzKGZsb3dzKTtcblxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcImZsb3ctdGFibGVcIiwgb25TY3JvbGw6IHRoaXMub25TY3JvbGxGbG93VGFibGV9LCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGFibGVcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoRmxvd1RhYmxlSGVhZCwge3JlZjogXCJoZWFkXCIsIFxuICAgICAgICAgICAgICAgICAgICAgICAgY29sdW1uczogdGhpcy5zdGF0ZS5jb2x1bW5zfSksIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGJvZHlcIiwge3JlZjogXCJib2R5XCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmdldFBsYWNlaG9sZGVyVG9wKGZsb3dzLmxlbmd0aCksIFxuICAgICAgICAgICAgICAgICAgICAgICAgcm93cywgXG4gICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5nZXRQbGFjZWhvbGRlckJvdHRvbShmbG93cy5sZW5ndGgpIFxuICAgICAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG5tb2R1bGUuZXhwb3J0cyA9IEZsb3dUYWJsZTtcbiIsInZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcblxudmFyIEZvb3RlciA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGb290ZXJcIixcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIG1vZGUgPSB0aGlzLnByb3BzLnNldHRpbmdzLm1vZGU7XG4gICAgICAgIHZhciBpbnRlcmNlcHQgPSB0aGlzLnByb3BzLnNldHRpbmdzLmludGVyY2VwdDtcbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJmb290ZXJcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgbW9kZSAhPSBcInJlZ3VsYXJcIiA/IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIsIHtjbGFzc05hbWU6IFwibGFiZWwgbGFiZWwtc3VjY2Vzc1wifSwgbW9kZSwgXCIgbW9kZVwiKSA6IG51bGwsIFxuICAgICAgICAgICAgICAgIFwiwqBcIiwgXG4gICAgICAgICAgICAgICAgaW50ZXJjZXB0ID8gUmVhY3QuY3JlYXRlRWxlbWVudChcInNwYW5cIiwge2NsYXNzTmFtZTogXCJsYWJlbCBsYWJlbC1zdWNjZXNzXCJ9LCBcIkludGVyY2VwdDogXCIsIGludGVyY2VwdCkgOiBudWxsXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbm1vZHVsZS5leHBvcnRzID0gRm9vdGVyOyIsInZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcbnZhciAkID0gcmVxdWlyZShcImpxdWVyeVwiKTtcblxudmFyIHV0aWxzID0gcmVxdWlyZShcIi4vdXRpbHMuanN4LmpzXCIpO1xuXG52YXIgRmlsdGVyRG9jcyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGaWx0ZXJEb2NzXCIsXG4gICAgc3RhdGljczoge1xuICAgICAgICB4aHI6IGZhbHNlLFxuICAgICAgICBkb2M6IGZhbHNlXG4gICAgfSxcbiAgICBjb21wb25lbnRXaWxsTW91bnQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgaWYgKCFGaWx0ZXJEb2NzLmRvYykge1xuICAgICAgICAgICAgRmlsdGVyRG9jcy54aHIgPSAkLmdldEpTT04oXCIvZmlsdGVyLWhlbHBcIikuZG9uZShmdW5jdGlvbiAoZG9jKSB7XG4gICAgICAgICAgICAgICAgRmlsdGVyRG9jcy5kb2MgPSBkb2M7XG4gICAgICAgICAgICAgICAgRmlsdGVyRG9jcy54aHIgPSBmYWxzZTtcbiAgICAgICAgICAgIH0pO1xuICAgICAgICB9XG4gICAgICAgIGlmIChGaWx0ZXJEb2NzLnhocikge1xuICAgICAgICAgICAgRmlsdGVyRG9jcy54aHIuZG9uZShmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICAgICAgdGhpcy5mb3JjZVVwZGF0ZSgpO1xuICAgICAgICAgICAgfS5iaW5kKHRoaXMpKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIGlmICghRmlsdGVyRG9jcy5kb2MpIHtcbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaVwiLCB7Y2xhc3NOYW1lOiBcImZhIGZhLXNwaW5uZXIgZmEtc3BpblwifSk7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICB2YXIgY29tbWFuZHMgPSBGaWx0ZXJEb2NzLmRvYy5jb21tYW5kcy5tYXAoZnVuY3Rpb24gKGMpIHtcbiAgICAgICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRyXCIsIG51bGwsIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwgbnVsbCwgY1swXS5yZXBsYWNlKFwiIFwiLCAnXFx1MDBhMCcpKSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCBudWxsLCBjWzFdKVxuICAgICAgICAgICAgICAgICk7XG4gICAgICAgICAgICB9KTtcbiAgICAgICAgICAgIGNvbW1hbmRzLnB1c2goUmVhY3QuY3JlYXRlRWxlbWVudChcInRyXCIsIG51bGwsIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCB7Y29sU3BhbjogXCIyXCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImFcIiwge2hyZWY6IFwiaHR0cHM6Ly9taXRtcHJveHkub3JnL2RvYy9mZWF0dXJlcy9maWx0ZXJzLmh0bWxcIiwgXG4gICAgICAgICAgICAgICAgICAgICAgICB0YXJnZXQ6IFwiX2JsYW5rXCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJpXCIsIHtjbGFzc05hbWU6IFwiZmEgZmEtZXh0ZXJuYWwtbGlua1wifSksIFxuICAgICAgICAgICAgICAgICAgICBcIsKgIG1pdG1wcm94eSBkb2NzXCIpXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKSk7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRhYmxlXCIsIHtjbGFzc05hbWU6IFwidGFibGUgdGFibGUtY29uZGVuc2VkXCJ9LCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGJvZHlcIiwgbnVsbCwgY29tbWFuZHMpXG4gICAgICAgICAgICApO1xuICAgICAgICB9XG4gICAgfVxufSk7XG52YXIgRmlsdGVySW5wdXQgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiRmlsdGVySW5wdXRcIixcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgLy8gQ29uc2lkZXIgYm90aCBmb2N1cyBhbmQgbW91c2VvdmVyIGZvciBzaG93aW5nL2hpZGluZyB0aGUgdG9vbHRpcCxcbiAgICAgICAgLy8gYmVjYXVzZSBvbkJsdXIgb2YgdGhlIGlucHV0IGlzIHRyaWdnZXJlZCBiZWZvcmUgdGhlIGNsaWNrIG9uIHRoZSB0b29sdGlwXG4gICAgICAgIC8vIGZpbmFsaXplZCwgaGlkaW5nIHRoZSB0b29sdGlwIGp1c3QgYXMgdGhlIHVzZXIgY2xpY2tzIG9uIGl0LlxuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgdmFsdWU6IHRoaXMucHJvcHMudmFsdWUsXG4gICAgICAgICAgICBmb2N1czogZmFsc2UsXG4gICAgICAgICAgICBtb3VzZWZvY3VzOiBmYWxzZVxuICAgICAgICB9O1xuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbFJlY2VpdmVQcm9wczogZnVuY3Rpb24gKG5leHRQcm9wcykge1xuICAgICAgICB0aGlzLnNldFN0YXRlKHt2YWx1ZTogbmV4dFByb3BzLnZhbHVlfSk7XG4gICAgfSxcbiAgICBvbkNoYW5nZTogZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgdmFyIG5leHRWYWx1ZSA9IGUudGFyZ2V0LnZhbHVlO1xuICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgIHZhbHVlOiBuZXh0VmFsdWVcbiAgICAgICAgfSk7XG4gICAgICAgIC8vIE9ubHkgcHJvcGFnYXRlIHZhbGlkIGZpbHRlcnMgdXB3YXJkcy5cbiAgICAgICAgaWYgKHRoaXMuaXNWYWxpZChuZXh0VmFsdWUpKSB7XG4gICAgICAgICAgICB0aGlzLnByb3BzLm9uQ2hhbmdlKG5leHRWYWx1ZSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGlzVmFsaWQ6IGZ1bmN0aW9uIChmaWx0KSB7XG4gICAgICAgIHRyeSB7XG4gICAgICAgICAgICBGaWx0LnBhcnNlKGZpbHQgfHwgdGhpcy5zdGF0ZS52YWx1ZSk7XG4gICAgICAgICAgICByZXR1cm4gdHJ1ZTtcbiAgICAgICAgfSBjYXRjaCAoZSkge1xuICAgICAgICAgICAgcmV0dXJuIGZhbHNlO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBnZXREZXNjOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBkZXNjO1xuICAgICAgICB0cnkge1xuICAgICAgICAgICAgZGVzYyA9IEZpbHQucGFyc2UodGhpcy5zdGF0ZS52YWx1ZSkuZGVzYztcbiAgICAgICAgfSBjYXRjaCAoZSkge1xuICAgICAgICAgICAgZGVzYyA9IFwiXCIgKyBlO1xuICAgICAgICB9XG4gICAgICAgIGlmIChkZXNjICE9PSBcInRydWVcIikge1xuICAgICAgICAgICAgcmV0dXJuIGRlc2M7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoRmlsdGVyRG9jcywgbnVsbClcbiAgICAgICAgICAgICk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIG9uRm9jdXM6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7Zm9jdXM6IHRydWV9KTtcbiAgICB9LFxuICAgIG9uQmx1cjogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLnNldFN0YXRlKHtmb2N1czogZmFsc2V9KTtcbiAgICB9LFxuICAgIG9uTW91c2VFbnRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLnNldFN0YXRlKHttb3VzZWZvY3VzOiB0cnVlfSk7XG4gICAgfSxcbiAgICBvbk1vdXNlTGVhdmU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7bW91c2Vmb2N1czogZmFsc2V9KTtcbiAgICB9LFxuICAgIG9uS2V5RG93bjogZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgaWYgKGUua2V5Q29kZSA9PT0gS2V5LkVTQyB8fCBlLmtleUNvZGUgPT09IEtleS5FTlRFUikge1xuICAgICAgICAgICAgdGhpcy5ibHVyKCk7XG4gICAgICAgICAgICAvLyBJZiBjbG9zZWQgdXNpbmcgRVNDL0VOVEVSLCBoaWRlIHRoZSB0b29sdGlwLlxuICAgICAgICAgICAgdGhpcy5zZXRTdGF0ZSh7bW91c2Vmb2N1czogZmFsc2V9KTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgYmx1cjogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLnJlZnMuaW5wdXQuZ2V0RE9NTm9kZSgpLmJsdXIoKTtcbiAgICB9LFxuICAgIGZvY3VzOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMucmVmcy5pbnB1dC5nZXRET01Ob2RlKCkuc2VsZWN0KCk7XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGlzVmFsaWQgPSB0aGlzLmlzVmFsaWQoKTtcbiAgICAgICAgdmFyIGljb24gPSBcImZhIGZhLWZ3IGZhLVwiICsgdGhpcy5wcm9wcy50eXBlO1xuICAgICAgICB2YXIgZ3JvdXBDbGFzc05hbWUgPSBcImZpbHRlci1pbnB1dCBpbnB1dC1ncm91cFwiICsgKGlzVmFsaWQgPyBcIlwiIDogXCIgaGFzLWVycm9yXCIpO1xuXG4gICAgICAgIHZhciBwb3BvdmVyO1xuICAgICAgICBpZiAodGhpcy5zdGF0ZS5mb2N1cyB8fCB0aGlzLnN0YXRlLm1vdXNlZm9jdXMpIHtcbiAgICAgICAgICAgIHBvcG92ZXIgPSAoXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcInBvcG92ZXIgYm90dG9tXCIsIG9uTW91c2VFbnRlcjogdGhpcy5vbk1vdXNlRW50ZXIsIG9uTW91c2VMZWF2ZTogdGhpcy5vbk1vdXNlTGVhdmV9LCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcImFycm93XCJ9KSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJwb3BvdmVyLWNvbnRlbnRcIn0sIFxuICAgICAgICAgICAgICAgICAgICB0aGlzLmdldERlc2MoKVxuICAgICAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKTtcbiAgICAgICAgfVxuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IGdyb3VwQ2xhc3NOYW1lfSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInNwYW5cIiwge2NsYXNzTmFtZTogXCJpbnB1dC1ncm91cC1hZGRvblwifSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJpXCIsIHtjbGFzc05hbWU6IGljb24sIHN0eWxlOiB7Y29sb3I6IHRoaXMucHJvcHMuY29sb3J9fSlcbiAgICAgICAgICAgICAgICApLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaW5wdXRcIiwge3R5cGU6IFwidGV4dFwiLCBwbGFjZWhvbGRlcjogdGhpcy5wcm9wcy5wbGFjZWhvbGRlciwgY2xhc3NOYW1lOiBcImZvcm0tY29udHJvbFwiLCBcbiAgICAgICAgICAgICAgICAgICAgcmVmOiBcImlucHV0XCIsIFxuICAgICAgICAgICAgICAgICAgICBvbkNoYW5nZTogdGhpcy5vbkNoYW5nZSwgXG4gICAgICAgICAgICAgICAgICAgIG9uRm9jdXM6IHRoaXMub25Gb2N1cywgXG4gICAgICAgICAgICAgICAgICAgIG9uQmx1cjogdGhpcy5vbkJsdXIsIFxuICAgICAgICAgICAgICAgICAgICBvbktleURvd246IHRoaXMub25LZXlEb3duLCBcbiAgICAgICAgICAgICAgICAgICAgdmFsdWU6IHRoaXMuc3RhdGUudmFsdWV9KSwgXG4gICAgICAgICAgICAgICAgcG9wb3ZlclxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgTWFpbk1lbnUgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiTWFpbk1lbnVcIixcbiAgICBtaXhpbnM6IFt1dGlscy5OYXZpZ2F0aW9uLCB1dGlscy5TdGF0ZV0sXG4gICAgc3RhdGljczoge1xuICAgICAgICB0aXRsZTogXCJTdGFydFwiLFxuICAgICAgICByb3V0ZTogXCJmbG93c1wiXG4gICAgfSxcbiAgICBvbkZpbHRlckNoYW5nZTogZnVuY3Rpb24gKHZhbCkge1xuICAgICAgICB2YXIgZCA9IHt9O1xuICAgICAgICBkW1F1ZXJ5LkZJTFRFUl0gPSB2YWw7XG4gICAgICAgIHRoaXMuc2V0UXVlcnkoZCk7XG4gICAgfSxcbiAgICBvbkhpZ2hsaWdodENoYW5nZTogZnVuY3Rpb24gKHZhbCkge1xuICAgICAgICB2YXIgZCA9IHt9O1xuICAgICAgICBkW1F1ZXJ5LkhJR0hMSUdIVF0gPSB2YWw7XG4gICAgICAgIHRoaXMuc2V0UXVlcnkoZCk7XG4gICAgfSxcbiAgICBvbkludGVyY2VwdENoYW5nZTogZnVuY3Rpb24gKHZhbCkge1xuICAgICAgICBTZXR0aW5nc0FjdGlvbnMudXBkYXRlKHtpbnRlcmNlcHQ6IHZhbH0pO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmaWx0ZXIgPSB0aGlzLmdldFF1ZXJ5KClbUXVlcnkuRklMVEVSXSB8fCBcIlwiO1xuICAgICAgICB2YXIgaGlnaGxpZ2h0ID0gdGhpcy5nZXRRdWVyeSgpW1F1ZXJ5LkhJR0hMSUdIVF0gfHwgXCJcIjtcbiAgICAgICAgdmFyIGludGVyY2VwdCA9IHRoaXMucHJvcHMuc2V0dGluZ3MuaW50ZXJjZXB0IHx8IFwiXCI7XG5cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcIm1lbnUtcm93XCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChGaWx0ZXJJbnB1dCwge1xuICAgICAgICAgICAgICAgICAgICAgICAgcGxhY2Vob2xkZXI6IFwiRmlsdGVyXCIsIFxuICAgICAgICAgICAgICAgICAgICAgICAgdHlwZTogXCJmaWx0ZXJcIiwgXG4gICAgICAgICAgICAgICAgICAgICAgICBjb2xvcjogXCJibGFja1wiLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIHZhbHVlOiBmaWx0ZXIsIFxuICAgICAgICAgICAgICAgICAgICAgICAgb25DaGFuZ2U6IHRoaXMub25GaWx0ZXJDaGFuZ2V9KSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoRmlsdGVySW5wdXQsIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHBsYWNlaG9sZGVyOiBcIkhpZ2hsaWdodFwiLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIHR5cGU6IFwidGFnXCIsIFxuICAgICAgICAgICAgICAgICAgICAgICAgY29sb3I6IFwiaHNsKDQ4LCAxMDAlLCA1MCUpXCIsIFxuICAgICAgICAgICAgICAgICAgICAgICAgdmFsdWU6IGhpZ2hsaWdodCwgXG4gICAgICAgICAgICAgICAgICAgICAgICBvbkNoYW5nZTogdGhpcy5vbkhpZ2hsaWdodENoYW5nZX0pLCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChGaWx0ZXJJbnB1dCwge1xuICAgICAgICAgICAgICAgICAgICAgICAgcGxhY2Vob2xkZXI6IFwiSW50ZXJjZXB0XCIsIFxuICAgICAgICAgICAgICAgICAgICAgICAgdHlwZTogXCJwYXVzZVwiLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIGNvbG9yOiBcImhzbCgyMDgsIDU2JSwgNTMlKVwiLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIHZhbHVlOiBpbnRlcmNlcHQsIFxuICAgICAgICAgICAgICAgICAgICAgICAgb25DaGFuZ2U6IHRoaXMub25JbnRlcmNlcHRDaGFuZ2V9KVxuICAgICAgICAgICAgICAgICksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJjbGVhcmZpeFwifSlcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxuXG52YXIgVmlld01lbnUgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiVmlld01lbnVcIixcbiAgICBzdGF0aWNzOiB7XG4gICAgICAgIHRpdGxlOiBcIlZpZXdcIixcbiAgICAgICAgcm91dGU6IFwiZmxvd3NcIlxuICAgIH0sXG4gICAgbWl4aW5zOiBbdXRpbHMuTmF2aWdhdGlvbiwgdXRpbHMuU3RhdGVdLFxuICAgIHRvZ2dsZUV2ZW50TG9nOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBkID0ge307XG5cbiAgICAgICAgaWYgKHRoaXMuZ2V0UXVlcnkoKVtRdWVyeS5TSE9XX0VWRU5UTE9HXSkge1xuICAgICAgICAgICAgZFtRdWVyeS5TSE9XX0VWRU5UTE9HXSA9IHVuZGVmaW5lZDtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGRbUXVlcnkuU0hPV19FVkVOVExPR10gPSBcInRcIjsgLy8gYW55IG5vbi1mYWxzZSB2YWx1ZSB3aWxsIGRvIGl0LCBrZWVwIGl0IHNob3J0XG4gICAgICAgIH1cblxuICAgICAgICB0aGlzLnNldFF1ZXJ5KGQpO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBzaG93RXZlbnRMb2cgPSB0aGlzLmdldFF1ZXJ5KClbUXVlcnkuU0hPV19FVkVOVExPR107XG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIG51bGwsIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJidXR0b25cIiwge1xuICAgICAgICAgICAgICAgICAgICBjbGFzc05hbWU6IFwiYnRuIFwiICsgKHNob3dFdmVudExvZyA/IFwiYnRuLXByaW1hcnlcIiA6IFwiYnRuLWRlZmF1bHRcIiksIFxuICAgICAgICAgICAgICAgICAgICBvbkNsaWNrOiB0aGlzLnRvZ2dsZUV2ZW50TG9nfSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJpXCIsIHtjbGFzc05hbWU6IFwiZmEgZmEtZGF0YWJhc2VcIn0pLCBcbiAgICAgICAgICAgICAgICBcIsKgU2hvdyBFdmVudGxvZ1wiXG4gICAgICAgICAgICAgICAgKSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInNwYW5cIiwgbnVsbCwgXCIgXCIpXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cblxudmFyIFJlcG9ydHNNZW51ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlJlcG9ydHNNZW51XCIsXG4gICAgc3RhdGljczoge1xuICAgICAgICB0aXRsZTogXCJWaXN1YWxpemF0aW9uXCIsXG4gICAgICAgIHJvdXRlOiBcInJlcG9ydHNcIlxuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIG51bGwsIFwiUmVwb3J0cyBNZW51XCIpO1xuICAgIH1cbn0pO1xuXG52YXIgRmlsZU1lbnUgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiRmlsZU1lbnVcIixcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgIHNob3dGaWxlTWVudTogZmFsc2VcbiAgICAgICAgfTtcbiAgICB9LFxuICAgIGhhbmRsZUZpbGVDbGljazogZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICBpZiAoIXRoaXMuc3RhdGUuc2hvd0ZpbGVNZW51KSB7XG4gICAgICAgICAgICB2YXIgY2xvc2UgPSBmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICAgICAgdGhpcy5zZXRTdGF0ZSh7c2hvd0ZpbGVNZW51OiBmYWxzZX0pO1xuICAgICAgICAgICAgICAgIGRvY3VtZW50LnJlbW92ZUV2ZW50TGlzdGVuZXIoXCJjbGlja1wiLCBjbG9zZSk7XG4gICAgICAgICAgICB9LmJpbmQodGhpcyk7XG4gICAgICAgICAgICBkb2N1bWVudC5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgY2xvc2UpO1xuXG4gICAgICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgICAgICBzaG93RmlsZU1lbnU6IHRydWVcbiAgICAgICAgICAgIH0pO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBoYW5kbGVOZXdDbGljazogZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICBpZiAoY29uZmlybShcIkRlbGV0ZSBhbGwgZmxvd3M/XCIpKSB7XG4gICAgICAgICAgICBGbG93QWN0aW9ucy5jbGVhcigpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBoYW5kbGVPcGVuQ2xpY2s6IGZ1bmN0aW9uIChlKSB7XG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcbiAgICAgICAgY29uc29sZS5lcnJvcihcInVuaW1wbGVtZW50ZWQ6IGhhbmRsZU9wZW5DbGlja1wiKTtcbiAgICB9LFxuICAgIGhhbmRsZVNhdmVDbGljazogZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICBjb25zb2xlLmVycm9yKFwidW5pbXBsZW1lbnRlZDogaGFuZGxlU2F2ZUNsaWNrXCIpO1xuICAgIH0sXG4gICAgaGFuZGxlU2h1dGRvd25DbGljazogZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICBjb25zb2xlLmVycm9yKFwidW5pbXBsZW1lbnRlZDogaGFuZGxlU2h1dGRvd25DbGlja1wiKTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmlsZU1lbnVDbGFzcyA9IFwiZHJvcGRvd24gcHVsbC1sZWZ0XCIgKyAodGhpcy5zdGF0ZS5zaG93RmlsZU1lbnUgPyBcIiBvcGVuXCIgOiBcIlwiKTtcblxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBmaWxlTWVudUNsYXNzfSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImFcIiwge2hyZWY6IFwiI1wiLCBjbGFzc05hbWU6IFwic3BlY2lhbFwiLCBvbkNsaWNrOiB0aGlzLmhhbmRsZUZpbGVDbGlja30sIFwiIEZpbGUgXCIpLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidWxcIiwge2NsYXNzTmFtZTogXCJkcm9wZG93bi1tZW51XCIsIHJvbGU6IFwibWVudVwifSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJsaVwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJhXCIsIHtocmVmOiBcIiNcIiwgb25DbGljazogdGhpcy5oYW5kbGVOZXdDbGlja30sIFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJpXCIsIHtjbGFzc05hbWU6IFwiZmEgZmEtZncgZmEtZmlsZVwifSksIFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwiTmV3XCJcbiAgICAgICAgICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgICAgICAgICAgKSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJsaVwiLCB7cm9sZTogXCJwcmVzZW50YXRpb25cIiwgY2xhc3NOYW1lOiBcImRpdmlkZXJcIn0pLCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImxpXCIsIG51bGwsIFxuICAgICAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImFcIiwge2hyZWY6IFwiaHR0cDovL21pdG0uaXQvXCIsIHRhcmdldDogXCJfYmxhbmtcIn0sIFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJpXCIsIHtjbGFzc05hbWU6IFwiZmEgZmEtZncgZmEtZXh0ZXJuYWwtbGlua1wifSksIFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIFwiSW5zdGFsbCBDZXJ0aWZpY2F0ZXMuLi5cIlxuICAgICAgICAgICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICAgICAgLypcbiAgICAgICAgICAgICAgICAgPGxpPlxuICAgICAgICAgICAgICAgICA8YSBocmVmPVwiI1wiIG9uQ2xpY2s9e3RoaXMuaGFuZGxlT3BlbkNsaWNrfT5cbiAgICAgICAgICAgICAgICAgPGkgY2xhc3NOYW1lPVwiZmEgZmEtZncgZmEtZm9sZGVyLW9wZW5cIj48L2k+XG4gICAgICAgICAgICAgICAgIE9wZW5cbiAgICAgICAgICAgICAgICAgPC9hPlxuICAgICAgICAgICAgICAgICA8L2xpPlxuICAgICAgICAgICAgICAgICA8bGk+XG4gICAgICAgICAgICAgICAgIDxhIGhyZWY9XCIjXCIgb25DbGljaz17dGhpcy5oYW5kbGVTYXZlQ2xpY2t9PlxuICAgICAgICAgICAgICAgICA8aSBjbGFzc05hbWU9XCJmYSBmYS1mdyBmYS1zYXZlXCI+PC9pPlxuICAgICAgICAgICAgICAgICBTYXZlXG4gICAgICAgICAgICAgICAgIDwvYT5cbiAgICAgICAgICAgICAgICAgPC9saT5cbiAgICAgICAgICAgICAgICAgPGxpIHJvbGU9XCJwcmVzZW50YXRpb25cIiBjbGFzc05hbWU9XCJkaXZpZGVyXCI+PC9saT5cbiAgICAgICAgICAgICAgICAgPGxpPlxuICAgICAgICAgICAgICAgICA8YSBocmVmPVwiI1wiIG9uQ2xpY2s9e3RoaXMuaGFuZGxlU2h1dGRvd25DbGlja30+XG4gICAgICAgICAgICAgICAgIDxpIGNsYXNzTmFtZT1cImZhIGZhLWZ3IGZhLXBsdWdcIj48L2k+XG4gICAgICAgICAgICAgICAgIFNodXRkb3duXG4gICAgICAgICAgICAgICAgIDwvYT5cbiAgICAgICAgICAgICAgICAgPC9saT5cbiAgICAgICAgICAgICAgICAgKi9cbiAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cblxudmFyIGhlYWRlcl9lbnRyaWVzID0gW01haW5NZW51LCBWaWV3TWVudSAvKiwgUmVwb3J0c01lbnUgKi9dO1xuXG5cbnZhciBIZWFkZXIgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiSGVhZGVyXCIsXG4gICAgbWl4aW5zOiBbdXRpbHMuTmF2aWdhdGlvbl0sXG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHJldHVybiB7XG4gICAgICAgICAgICBhY3RpdmU6IGhlYWRlcl9lbnRyaWVzWzBdXG4gICAgICAgIH07XG4gICAgfSxcbiAgICBoYW5kbGVDbGljazogZnVuY3Rpb24gKGFjdGl2ZSwgZSkge1xuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XG4gICAgICAgIHRoaXMucmVwbGFjZVdpdGgoYWN0aXZlLnJvdXRlKTtcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7YWN0aXZlOiBhY3RpdmV9KTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgaGVhZGVyID0gaGVhZGVyX2VudHJpZXMubWFwKGZ1bmN0aW9uIChlbnRyeSwgaSkge1xuICAgICAgICAgICAgdmFyIGNsYXNzZXMgPSBSZWFjdC5hZGRvbnMuY2xhc3NTZXQoe1xuICAgICAgICAgICAgICAgIGFjdGl2ZTogZW50cnkgPT0gdGhpcy5zdGF0ZS5hY3RpdmVcbiAgICAgICAgICAgIH0pO1xuICAgICAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiYVwiLCB7a2V5OiBpLCBcbiAgICAgICAgICAgICAgICAgICAgaHJlZjogXCIjXCIsIFxuICAgICAgICAgICAgICAgICAgICBjbGFzc05hbWU6IGNsYXNzZXMsIFxuICAgICAgICAgICAgICAgICAgICBvbkNsaWNrOiB0aGlzLmhhbmRsZUNsaWNrLmJpbmQodGhpcywgZW50cnkpXG4gICAgICAgICAgICAgICAgfSwgXG4gICAgICAgICAgICAgICAgICAgICBlbnRyeS50aXRsZVxuICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgICk7XG4gICAgICAgIH0uYmluZCh0aGlzKSk7XG5cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJoZWFkZXJcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcInRpdGxlLWJhclwifSwgXG4gICAgICAgICAgICAgICAgICAgIFwibWl0bXByb3h5IFwiLCAgdGhpcy5wcm9wcy5zZXR0aW5ncy52ZXJzaW9uXG4gICAgICAgICAgICAgICAgKSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcIm5hdlwiLCB7Y2xhc3NOYW1lOiBcIm5hdi10YWJzIG5hdi10YWJzLWxnXCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChGaWxlTWVudSwgbnVsbCksIFxuICAgICAgICAgICAgICAgICAgICBoZWFkZXJcbiAgICAgICAgICAgICAgICApLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwibWVudVwifSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQodGhpcy5zdGF0ZS5hY3RpdmUsIHtzZXR0aW5nczogdGhpcy5wcm9wcy5zZXR0aW5nc30pXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG5cbm1vZHVsZS5leHBvcnRzID0ge1xuICAgIEhlYWRlcjogSGVhZGVyXG59IiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xuXG52YXIgdXRpbHMgPSByZXF1aXJlKFwiLi91dGlscy5qc3guanNcIik7XG52YXIgdmlld3MgPSByZXF1aXJlKFwiLi4vc3RvcmUvdmlldy5qc1wiKTtcbnZhciBGaWx0ID0gcmVxdWlyZShcIi4uL2ZpbHQvZmlsdC5qc1wiKTtcbkZsb3dUYWJsZSA9IHJlcXVpcmUoXCIuL2Zsb3d0YWJsZS5qc3guanNcIik7XG52YXIgZmxvd2RldGFpbCA9IHJlcXVpcmUoXCIuL2Zsb3dkZXRhaWwuanN4LmpzXCIpO1xuXG5cbnZhciBNYWluVmlldyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJNYWluVmlld1wiLFxuICAgIG1peGluczogW3V0aWxzLk5hdmlnYXRpb24sIHV0aWxzLlN0YXRlXSxcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5vblF1ZXJ5Q2hhbmdlKFF1ZXJ5LkZJTFRFUiwgZnVuY3Rpb24gKCkge1xuICAgICAgICAgICAgdGhpcy5zdGF0ZS52aWV3LnJlY2FsY3VsYXRlKHRoaXMuZ2V0Vmlld0ZpbHQoKSwgdGhpcy5nZXRWaWV3U29ydCgpKTtcbiAgICAgICAgfS5iaW5kKHRoaXMpKTtcbiAgICAgICAgdGhpcy5vblF1ZXJ5Q2hhbmdlKFF1ZXJ5LkhJR0hMSUdIVCwgZnVuY3Rpb24gKCkge1xuICAgICAgICAgICAgdGhpcy5zdGF0ZS52aWV3LnJlY2FsY3VsYXRlKHRoaXMuZ2V0Vmlld0ZpbHQoKSwgdGhpcy5nZXRWaWV3U29ydCgpKTtcbiAgICAgICAgfS5iaW5kKHRoaXMpKTtcbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgIGZsb3dzOiBbXVxuICAgICAgICB9O1xuICAgIH0sXG4gICAgZ2V0Vmlld0ZpbHQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdHJ5IHtcbiAgICAgICAgICAgIHZhciBmaWx0ID0gRmlsdC5wYXJzZSh0aGlzLmdldFF1ZXJ5KClbUXVlcnkuRklMVEVSXSB8fCBcIlwiKTtcbiAgICAgICAgICAgIHZhciBoaWdobGlnaHRTdHIgPSB0aGlzLmdldFF1ZXJ5KClbUXVlcnkuSElHSExJR0hUXTtcbiAgICAgICAgICAgIHZhciBoaWdobGlnaHQgPSBoaWdobGlnaHRTdHIgPyBGaWx0LnBhcnNlKGhpZ2hsaWdodFN0cikgOiBmYWxzZTtcbiAgICAgICAgfSBjYXRjaCAoZSkge1xuICAgICAgICAgICAgY29uc29sZS5lcnJvcihcIkVycm9yIHdoZW4gcHJvY2Vzc2luZyBmaWx0ZXI6IFwiICsgZSk7XG4gICAgICAgIH1cblxuICAgICAgICByZXR1cm4gZnVuY3Rpb24gZmlsdGVyX2FuZF9oaWdobGlnaHQoZmxvdykge1xuICAgICAgICAgICAgaWYgKCF0aGlzLl9oaWdobGlnaHQpIHtcbiAgICAgICAgICAgICAgICB0aGlzLl9oaWdobGlnaHQgPSB7fTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIHRoaXMuX2hpZ2hsaWdodFtmbG93LmlkXSA9IGhpZ2hsaWdodCAmJiBoaWdobGlnaHQoZmxvdyk7XG4gICAgICAgICAgICByZXR1cm4gZmlsdChmbG93KTtcbiAgICAgICAgfTtcbiAgICB9LFxuICAgIGdldFZpZXdTb3J0OiBmdW5jdGlvbiAoKSB7XG4gICAgfSxcbiAgICBjb21wb25lbnRXaWxsUmVjZWl2ZVByb3BzOiBmdW5jdGlvbiAobmV4dFByb3BzKSB7XG4gICAgICAgIGlmIChuZXh0UHJvcHMuZmxvd1N0b3JlICE9PSB0aGlzLnByb3BzLmZsb3dTdG9yZSkge1xuICAgICAgICAgICAgdGhpcy5jbG9zZVZpZXcoKTtcbiAgICAgICAgICAgIHRoaXMub3BlblZpZXcobmV4dFByb3BzLmZsb3dTdG9yZSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIG9wZW5WaWV3OiBmdW5jdGlvbiAoc3RvcmUpIHtcbiAgICAgICAgdmFyIHZpZXcgPSBuZXcgdmlld3MuU3RvcmVWaWV3KHN0b3JlLCB0aGlzLmdldFZpZXdGaWx0KCksIHRoaXMuZ2V0Vmlld1NvcnQoKSk7XG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe1xuICAgICAgICAgICAgdmlldzogdmlld1xuICAgICAgICB9KTtcblxuICAgICAgICB2aWV3LmFkZExpc3RlbmVyKFwicmVjYWxjdWxhdGVcIiwgdGhpcy5vblJlY2FsY3VsYXRlKTtcbiAgICAgICAgdmlldy5hZGRMaXN0ZW5lcihcImFkZCB1cGRhdGUgcmVtb3ZlXCIsIHRoaXMub25VcGRhdGUpO1xuICAgICAgICB2aWV3LmFkZExpc3RlbmVyKFwicmVtb3ZlXCIsIHRoaXMub25SZW1vdmUpO1xuICAgIH0sXG4gICAgb25SZWNhbGN1bGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLmZvcmNlVXBkYXRlKCk7XG4gICAgICAgIHZhciBzZWxlY3RlZCA9IHRoaXMuZ2V0U2VsZWN0ZWQoKTtcbiAgICAgICAgaWYgKHNlbGVjdGVkKSB7XG4gICAgICAgICAgICB0aGlzLnJlZnMuZmxvd1RhYmxlLnNjcm9sbEludG9WaWV3KHNlbGVjdGVkKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgb25VcGRhdGU6IGZ1bmN0aW9uIChmbG93KSB7XG4gICAgICAgIGlmIChmbG93LmlkID09PSB0aGlzLmdldFBhcmFtcygpLmZsb3dJZCkge1xuICAgICAgICAgICAgdGhpcy5mb3JjZVVwZGF0ZSgpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBvblJlbW92ZTogZnVuY3Rpb24gKGZsb3dfaWQsIGluZGV4KSB7XG4gICAgICAgIGlmIChmbG93X2lkID09PSB0aGlzLmdldFBhcmFtcygpLmZsb3dJZCkge1xuICAgICAgICAgICAgdmFyIGZsb3dfdG9fc2VsZWN0ID0gdGhpcy5zdGF0ZS52aWV3Lmxpc3RbTWF0aC5taW4oaW5kZXgsIHRoaXMuc3RhdGUudmlldy5saXN0Lmxlbmd0aCAtMSldO1xuICAgICAgICAgICAgdGhpcy5zZWxlY3RGbG93KGZsb3dfdG9fc2VsZWN0KTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgY2xvc2VWaWV3OiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuc3RhdGUudmlldy5jbG9zZSgpO1xuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbE1vdW50OiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMub3BlblZpZXcodGhpcy5wcm9wcy5mbG93U3RvcmUpO1xuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbFVubW91bnQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5jbG9zZVZpZXcoKTtcbiAgICB9LFxuICAgIHNlbGVjdEZsb3c6IGZ1bmN0aW9uIChmbG93KSB7XG4gICAgICAgIGlmIChmbG93KSB7XG4gICAgICAgICAgICB0aGlzLnJlcGxhY2VXaXRoKFxuICAgICAgICAgICAgICAgIFwiZmxvd1wiLFxuICAgICAgICAgICAgICAgIHtcbiAgICAgICAgICAgICAgICAgICAgZmxvd0lkOiBmbG93LmlkLFxuICAgICAgICAgICAgICAgICAgICBkZXRhaWxUYWI6IHRoaXMuZ2V0UGFyYW1zKCkuZGV0YWlsVGFiIHx8IFwicmVxdWVzdFwiXG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgKTtcbiAgICAgICAgICAgIHRoaXMucmVmcy5mbG93VGFibGUuc2Nyb2xsSW50b1ZpZXcoZmxvdyk7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICB0aGlzLnJlcGxhY2VXaXRoKFwiZmxvd3NcIiwge30pO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBzZWxlY3RGbG93UmVsYXRpdmU6IGZ1bmN0aW9uIChzaGlmdCkge1xuICAgICAgICB2YXIgZmxvd3MgPSB0aGlzLnN0YXRlLnZpZXcubGlzdDtcbiAgICAgICAgdmFyIGluZGV4O1xuICAgICAgICBpZiAoIXRoaXMuZ2V0UGFyYW1zKCkuZmxvd0lkKSB7XG4gICAgICAgICAgICBpZiAoc2hpZnQgPiAwKSB7XG4gICAgICAgICAgICAgICAgaW5kZXggPSBmbG93cy5sZW5ndGggLSAxO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBpbmRleCA9IDA7XG4gICAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICB2YXIgY3VyckZsb3dJZCA9IHRoaXMuZ2V0UGFyYW1zKCkuZmxvd0lkO1xuICAgICAgICAgICAgdmFyIGkgPSBmbG93cy5sZW5ndGg7XG4gICAgICAgICAgICB3aGlsZSAoaS0tKSB7XG4gICAgICAgICAgICAgICAgaWYgKGZsb3dzW2ldLmlkID09PSBjdXJyRmxvd0lkKSB7XG4gICAgICAgICAgICAgICAgICAgIGluZGV4ID0gaTtcbiAgICAgICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaW5kZXggPSBNYXRoLm1pbihcbiAgICAgICAgICAgICAgICBNYXRoLm1heCgwLCBpbmRleCArIHNoaWZ0KSxcbiAgICAgICAgICAgICAgICBmbG93cy5sZW5ndGggLSAxKTtcbiAgICAgICAgfVxuICAgICAgICB0aGlzLnNlbGVjdEZsb3coZmxvd3NbaW5kZXhdKTtcbiAgICB9LFxuICAgIG9uS2V5RG93bjogZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLmdldFNlbGVjdGVkKCk7XG4gICAgICAgIGlmIChlLmN0cmxLZXkpIHtcbiAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgfVxuICAgICAgICBzd2l0Y2ggKGUua2V5Q29kZSkge1xuICAgICAgICAgICAgY2FzZSBLZXkuSzpcbiAgICAgICAgICAgIGNhc2UgS2V5LlVQOlxuICAgICAgICAgICAgICAgIHRoaXMuc2VsZWN0Rmxvd1JlbGF0aXZlKC0xKTtcbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgS2V5Lko6XG4gICAgICAgICAgICBjYXNlIEtleS5ET1dOOlxuICAgICAgICAgICAgICAgIHRoaXMuc2VsZWN0Rmxvd1JlbGF0aXZlKCsxKTtcbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgS2V5LlNQQUNFOlxuICAgICAgICAgICAgY2FzZSBLZXkuUEFHRV9ET1dOOlxuICAgICAgICAgICAgICAgIHRoaXMuc2VsZWN0Rmxvd1JlbGF0aXZlKCsxMCk7XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIEtleS5QQUdFX1VQOlxuICAgICAgICAgICAgICAgIHRoaXMuc2VsZWN0Rmxvd1JlbGF0aXZlKC0xMCk7XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIEtleS5FTkQ6XG4gICAgICAgICAgICAgICAgdGhpcy5zZWxlY3RGbG93UmVsYXRpdmUoKzFlMTApO1xuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgY2FzZSBLZXkuSE9NRTpcbiAgICAgICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3dSZWxhdGl2ZSgtMWUxMCk7XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIEtleS5FU0M6XG4gICAgICAgICAgICAgICAgdGhpcy5zZWxlY3RGbG93KG51bGwpO1xuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgY2FzZSBLZXkuSDpcbiAgICAgICAgICAgIGNhc2UgS2V5LkxFRlQ6XG4gICAgICAgICAgICAgICAgaWYgKHRoaXMucmVmcy5mbG93RGV0YWlscykge1xuICAgICAgICAgICAgICAgICAgICB0aGlzLnJlZnMuZmxvd0RldGFpbHMubmV4dFRhYigtMSk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgY2FzZSBLZXkuTDpcbiAgICAgICAgICAgIGNhc2UgS2V5LlRBQjpcbiAgICAgICAgICAgIGNhc2UgS2V5LlJJR0hUOlxuICAgICAgICAgICAgICAgIGlmICh0aGlzLnJlZnMuZmxvd0RldGFpbHMpIHtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5yZWZzLmZsb3dEZXRhaWxzLm5leHRUYWIoKzEpO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgS2V5LkM6XG4gICAgICAgICAgICAgICAgaWYgKGUuc2hpZnRLZXkpIHtcbiAgICAgICAgICAgICAgICAgICAgRmxvd0FjdGlvbnMuY2xlYXIoKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIEtleS5EOlxuICAgICAgICAgICAgICAgIGlmIChmbG93KSB7XG4gICAgICAgICAgICAgICAgICAgIGlmIChlLnNoaWZ0S2V5KSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBGbG93QWN0aW9ucy5kdXBsaWNhdGUoZmxvdyk7XG4gICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBGbG93QWN0aW9ucy5kZWxldGUoZmxvdyk7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIEtleS5BOlxuICAgICAgICAgICAgICAgIGlmIChlLnNoaWZ0S2V5KSB7XG4gICAgICAgICAgICAgICAgICAgIEZsb3dBY3Rpb25zLmFjY2VwdF9hbGwoKTtcbiAgICAgICAgICAgICAgICB9IGVsc2UgaWYgKGZsb3cgJiYgZmxvdy5pbnRlcmNlcHRlZCkge1xuICAgICAgICAgICAgICAgICAgICBGbG93QWN0aW9ucy5hY2NlcHQoZmxvdyk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgY2FzZSBLZXkuUjpcbiAgICAgICAgICAgICAgICBpZiAoIWUuc2hpZnRLZXkgJiYgZmxvdykge1xuICAgICAgICAgICAgICAgICAgICBGbG93QWN0aW9ucy5yZXBsYXkoZmxvdyk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgY2FzZSBLZXkuVjpcbiAgICAgICAgICAgICAgICBpZihlLnNoaWZ0S2V5ICYmIGZsb3cgJiYgZmxvdy5tb2RpZmllZCkge1xuICAgICAgICAgICAgICAgICAgICBGbG93QWN0aW9ucy5yZXZlcnQoZmxvdyk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgZGVmYXVsdDpcbiAgICAgICAgICAgICAgICBjb25zb2xlLmRlYnVnKFwia2V5ZG93blwiLCBlLmtleUNvZGUpO1xuICAgICAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgfVxuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XG4gICAgfSxcbiAgICBnZXRTZWxlY3RlZDogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4gdGhpcy5wcm9wcy5mbG93U3RvcmUuZ2V0KHRoaXMuZ2V0UGFyYW1zKCkuZmxvd0lkKTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgc2VsZWN0ZWQgPSB0aGlzLmdldFNlbGVjdGVkKCk7XG5cbiAgICAgICAgdmFyIGRldGFpbHM7XG4gICAgICAgIGlmIChzZWxlY3RlZCkge1xuICAgICAgICAgICAgZGV0YWlscyA9IFtcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KHV0aWxzLlNwbGl0dGVyLCB7a2V5OiBcInNwbGl0dGVyXCJ9KSxcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KGZsb3dkZXRhaWwuRmxvd0RldGFpbCwge2tleTogXCJmbG93RGV0YWlsc1wiLCByZWY6IFwiZmxvd0RldGFpbHNcIiwgZmxvdzogc2VsZWN0ZWR9KVxuICAgICAgICAgICAgXTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGRldGFpbHMgPSBudWxsO1xuICAgICAgICB9XG5cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJtYWluLXZpZXdcIiwgb25LZXlEb3duOiB0aGlzLm9uS2V5RG93biwgdGFiSW5kZXg6IFwiMFwifSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChGbG93VGFibGUsIHtyZWY6IFwiZmxvd1RhYmxlXCIsIFxuICAgICAgICAgICAgICAgICAgICB2aWV3OiB0aGlzLnN0YXRlLnZpZXcsIFxuICAgICAgICAgICAgICAgICAgICBzZWxlY3RGbG93OiB0aGlzLnNlbGVjdEZsb3csIFxuICAgICAgICAgICAgICAgICAgICBzZWxlY3RlZDogc2VsZWN0ZWR9KSwgXG4gICAgICAgICAgICAgICAgZGV0YWlsc1xuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG5tb2R1bGUuZXhwb3J0cyA9IE1haW5WaWV3O1xuIiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xudmFyIFJlYWN0Um91dGVyID0gcmVxdWlyZShcInJlYWN0LXJvdXRlclwiKTtcbnZhciBfID0gcmVxdWlyZShcImxvZGFzaFwiKTtcblxudmFyIHV0aWxzID0gcmVxdWlyZShcIi4vdXRpbHMuanN4LmpzXCIpO1xudmFyIE1haW5WaWV3ID0gcmVxdWlyZShcIi4vbWFpbnZpZXcuanN4LmpzXCIpO1xudmFyIEZvb3RlciA9IHJlcXVpcmUoXCIuL2Zvb3Rlci5qc3guanNcIik7XG52YXIgaGVhZGVyID0gcmVxdWlyZShcIi4vaGVhZGVyLmpzeC5qc1wiKTtcbnZhciBzdG9yZSA9IHJlcXVpcmUoXCIuLi9zdG9yZS9zdG9yZS5qc1wiKTtcblxuXG4vL1RPRE86IE1vdmUgb3V0IG9mIGhlcmUsIGp1c3QgYSBzdHViLlxudmFyIFJlcG9ydHMgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiUmVwb3J0c1wiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCBudWxsLCBcIlJlcG9ydEVkaXRvclwiKTtcbiAgICB9XG59KTtcblxuXG52YXIgUHJveHlBcHBNYWluID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlByb3h5QXBwTWFpblwiLFxuICAgIG1peGluczogW3V0aWxzLlN0YXRlXSxcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGV2ZW50U3RvcmUgPSBuZXcgc3RvcmUuRXZlbnRMb2dTdG9yZSgpO1xuICAgICAgICB2YXIgZmxvd1N0b3JlID0gbmV3IHN0b3JlLkZsb3dTdG9yZSgpO1xuICAgICAgICB2YXIgc2V0dGluZ3MgPSBuZXcgc3RvcmUuU2V0dGluZ3NTdG9yZSgpO1xuXG4gICAgICAgIC8vIERlZmF1bHQgU2V0dGluZ3MgYmVmb3JlIGZldGNoXG4gICAgICAgIF8uZXh0ZW5kKHNldHRpbmdzLmRpY3Qse1xuICAgICAgICB9KTtcbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgIHNldHRpbmdzOiBzZXR0aW5ncyxcbiAgICAgICAgICAgIGZsb3dTdG9yZTogZmxvd1N0b3JlLFxuICAgICAgICAgICAgZXZlbnRTdG9yZTogZXZlbnRTdG9yZVxuICAgICAgICB9O1xuICAgIH0sXG4gICAgY29tcG9uZW50RGlkTW91bnQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5zdGF0ZS5zZXR0aW5ncy5hZGRMaXN0ZW5lcihcInJlY2FsY3VsYXRlXCIsIHRoaXMub25TZXR0aW5nc0NoYW5nZSk7XG4gICAgICAgIHdpbmRvdy5hcHAgPSB0aGlzO1xuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbFVubW91bnQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5zdGF0ZS5zZXR0aW5ncy5yZW1vdmVMaXN0ZW5lcihcInJlY2FsY3VsYXRlXCIsIHRoaXMub25TZXR0aW5nc0NoYW5nZSk7XG4gICAgfSxcbiAgICBvblNldHRpbmdzQ2hhbmdlOiBmdW5jdGlvbigpe1xuICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgIHNldHRpbmdzOiB0aGlzLnN0YXRlLnNldHRpbmdzXG4gICAgICAgIH0pO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG5cbiAgICAgICAgdmFyIGV2ZW50bG9nO1xuICAgICAgICBpZiAodGhpcy5nZXRRdWVyeSgpW1F1ZXJ5LlNIT1dfRVZFTlRMT0ddKSB7XG4gICAgICAgICAgICBldmVudGxvZyA9IFtcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFNwbGl0dGVyLCB7a2V5OiBcInNwbGl0dGVyXCIsIGF4aXM6IFwieVwifSksXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChFdmVudExvZywge2tleTogXCJldmVudGxvZ1wiLCBldmVudFN0b3JlOiB0aGlzLnN0YXRlLmV2ZW50U3RvcmV9KVxuICAgICAgICAgICAgXTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGV2ZW50bG9nID0gbnVsbDtcbiAgICAgICAgfVxuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtpZDogXCJjb250YWluZXJcIn0sIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoaGVhZGVyLkhlYWRlciwge3NldHRpbmdzOiB0aGlzLnN0YXRlLnNldHRpbmdzLmRpY3R9KSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChSb3V0ZUhhbmRsZXIsIHtzZXR0aW5nczogdGhpcy5zdGF0ZS5zZXR0aW5ncy5kaWN0LCBmbG93U3RvcmU6IHRoaXMuc3RhdGUuZmxvd1N0b3JlfSksIFxuICAgICAgICAgICAgICAgIGV2ZW50bG9nLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KEZvb3Rlciwge3NldHRpbmdzOiB0aGlzLnN0YXRlLnNldHRpbmdzLmRpY3R9KVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG5cbnZhciBSb3V0ZSA9IFJlYWN0Um91dGVyLlJvdXRlO1xudmFyIFJvdXRlSGFuZGxlciA9IFJlYWN0Um91dGVyLlJvdXRlSGFuZGxlcjtcbnZhciBSZWRpcmVjdCA9IFJlYWN0Um91dGVyLlJlZGlyZWN0O1xudmFyIERlZmF1bHRSb3V0ZSA9IFJlYWN0Um91dGVyLkRlZmF1bHRSb3V0ZTtcbnZhciBOb3RGb3VuZFJvdXRlID0gUmVhY3RSb3V0ZXIuTm90Rm91bmRSb3V0ZTtcblxuXG52YXIgcm91dGVzID0gKFxuICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoUm91dGUsIHtwYXRoOiBcIi9cIiwgaGFuZGxlcjogUHJveHlBcHBNYWlufSwgXG4gICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoUm91dGUsIHtuYW1lOiBcImZsb3dzXCIsIHBhdGg6IFwiZmxvd3NcIiwgaGFuZGxlcjogTWFpblZpZXd9KSwgXG4gICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoUm91dGUsIHtuYW1lOiBcImZsb3dcIiwgcGF0aDogXCJmbG93cy86Zmxvd0lkLzpkZXRhaWxUYWJcIiwgaGFuZGxlcjogTWFpblZpZXd9KSwgXG4gICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoUm91dGUsIHtuYW1lOiBcInJlcG9ydHNcIiwgaGFuZGxlcjogUmVwb3J0c30pLCBcbiAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChSZWRpcmVjdCwge3BhdGg6IFwiL1wiLCB0bzogXCJmbG93c1wifSlcbiAgICApXG4pO1xuXG5tb2R1bGUuZXhwb3J0cyA9IHtcbiAgICByb3V0ZXM6IHJvdXRlc1xufTtcblxuIiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xudmFyIFJlYWN0Um91dGVyID0gcmVxdWlyZShcInJlYWN0LXJvdXRlclwiKTtcbnZhciBfID0gcmVxdWlyZShcImxvZGFzaFwiKTtcblxuLy9SZWFjdCB1dGlscy4gRm9yIG90aGVyIHV0aWxpdGllcywgc2VlIC4uL3V0aWxzLmpzXG5cbi8vIGh0dHA6Ly9ibG9nLnZqZXV4LmNvbS8yMDEzL2phdmFzY3JpcHQvc2Nyb2xsLXBvc2l0aW9uLXdpdGgtcmVhY3QuaHRtbCAoYWxzbyBjb250YWlucyBpbnZlcnNlIGV4YW1wbGUpXG52YXIgQXV0b1Njcm9sbE1peGluID0ge1xuICAgIGNvbXBvbmVudFdpbGxVcGRhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIG5vZGUgPSB0aGlzLmdldERPTU5vZGUoKTtcbiAgICAgICAgdGhpcy5fc2hvdWxkU2Nyb2xsQm90dG9tID0gKFxuICAgICAgICAgICAgbm9kZS5zY3JvbGxUb3AgIT09IDAgJiZcbiAgICAgICAgICAgIG5vZGUuc2Nyb2xsVG9wICsgbm9kZS5jbGllbnRIZWlnaHQgPT09IG5vZGUuc2Nyb2xsSGVpZ2h0XG4gICAgICAgICk7XG4gICAgfSxcbiAgICBjb21wb25lbnREaWRVcGRhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgaWYgKHRoaXMuX3Nob3VsZFNjcm9sbEJvdHRvbSkge1xuICAgICAgICAgICAgdmFyIG5vZGUgPSB0aGlzLmdldERPTU5vZGUoKTtcbiAgICAgICAgICAgIG5vZGUuc2Nyb2xsVG9wID0gbm9kZS5zY3JvbGxIZWlnaHQ7XG4gICAgICAgIH1cbiAgICB9LFxufTtcblxuXG52YXIgU3RpY2t5SGVhZE1peGluID0ge1xuICAgIGFkanVzdEhlYWQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgLy8gQWJ1c2luZyBDU1MgdHJhbnNmb3JtcyB0byBzZXQgdGhlIGVsZW1lbnRcbiAgICAgICAgLy8gcmVmZXJlbmNlZCBhcyBoZWFkIGludG8gc29tZSBraW5kIG9mIHBvc2l0aW9uOnN0aWNreS5cbiAgICAgICAgdmFyIGhlYWQgPSB0aGlzLnJlZnMuaGVhZC5nZXRET01Ob2RlKCk7XG4gICAgICAgIGhlYWQuc3R5bGUudHJhbnNmb3JtID0gXCJ0cmFuc2xhdGUoMCxcIiArIHRoaXMuZ2V0RE9NTm9kZSgpLnNjcm9sbFRvcCArIFwicHgpXCI7XG4gICAgfVxufTtcblxuXG52YXIgTmF2aWdhdGlvbiA9IF8uZXh0ZW5kKHt9LCBSZWFjdFJvdXRlci5OYXZpZ2F0aW9uLCB7XG4gICAgc2V0UXVlcnk6IGZ1bmN0aW9uIChkaWN0KSB7XG4gICAgICAgIHZhciBxID0gdGhpcy5jb250ZXh0LmdldEN1cnJlbnRRdWVyeSgpO1xuICAgICAgICBmb3IodmFyIGkgaW4gZGljdCl7XG4gICAgICAgICAgICBpZihkaWN0Lmhhc093blByb3BlcnR5KGkpKXtcbiAgICAgICAgICAgICAgICBxW2ldID0gZGljdFtpXSB8fCB1bmRlZmluZWQ7IC8vZmFsc2V5IHZhbHVlcyBzaGFsbCBiZSByZW1vdmVkLlxuICAgICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICAgIHEuXyA9IFwiX1wiOyAvLyB3b3JrYXJvdW5kIGZvciBodHRwczovL2dpdGh1Yi5jb20vcmFja3QvcmVhY3Qtcm91dGVyL3B1bGwvNTk5XG4gICAgICAgIHRoaXMucmVwbGFjZVdpdGgodGhpcy5jb250ZXh0LmdldEN1cnJlbnRQYXRoKCksIHRoaXMuY29udGV4dC5nZXRDdXJyZW50UGFyYW1zKCksIHEpO1xuICAgIH0sXG4gICAgcmVwbGFjZVdpdGg6IGZ1bmN0aW9uKHJvdXRlTmFtZU9yUGF0aCwgcGFyYW1zLCBxdWVyeSkge1xuICAgICAgICBpZihyb3V0ZU5hbWVPclBhdGggPT09IHVuZGVmaW5lZCl7XG4gICAgICAgICAgICByb3V0ZU5hbWVPclBhdGggPSB0aGlzLmNvbnRleHQuZ2V0Q3VycmVudFBhdGgoKTtcbiAgICAgICAgfVxuICAgICAgICBpZihwYXJhbXMgPT09IHVuZGVmaW5lZCl7XG4gICAgICAgICAgICBwYXJhbXMgPSB0aGlzLmNvbnRleHQuZ2V0Q3VycmVudFBhcmFtcygpO1xuICAgICAgICB9XG4gICAgICAgIGlmKHF1ZXJ5ID09PSB1bmRlZmluZWQpe1xuICAgICAgICAgICAgcXVlcnkgPSB0aGlzLmNvbnRleHQuZ2V0Q3VycmVudFF1ZXJ5KCk7XG4gICAgICAgIH1cbiAgICAgICAgUmVhY3RSb3V0ZXIuTmF2aWdhdGlvbi5yZXBsYWNlV2l0aC5jYWxsKHRoaXMsIHJvdXRlTmFtZU9yUGF0aCwgcGFyYW1zLCBxdWVyeSk7XG4gICAgfVxufSk7XG5fLmV4dGVuZChOYXZpZ2F0aW9uLmNvbnRleHRUeXBlcywgUmVhY3RSb3V0ZXIuU3RhdGUuY29udGV4dFR5cGVzKTtcblxudmFyIFN0YXRlID0gXy5leHRlbmQoe30sIFJlYWN0Um91dGVyLlN0YXRlLCB7XG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuX3F1ZXJ5ID0gdGhpcy5jb250ZXh0LmdldEN1cnJlbnRRdWVyeSgpO1xuICAgICAgICB0aGlzLl9xdWVyeVdhdGNoZXMgPSBbXTtcbiAgICAgICAgcmV0dXJuIG51bGw7XG4gICAgfSxcbiAgICBvblF1ZXJ5Q2hhbmdlOiBmdW5jdGlvbiAoa2V5LCBjYWxsYmFjaykge1xuICAgICAgICB0aGlzLl9xdWVyeVdhdGNoZXMucHVzaCh7XG4gICAgICAgICAgICBrZXk6IGtleSxcbiAgICAgICAgICAgIGNhbGxiYWNrOiBjYWxsYmFja1xuICAgICAgICB9KTtcbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxSZWNlaXZlUHJvcHM6IGZ1bmN0aW9uIChuZXh0UHJvcHMsIG5leHRTdGF0ZSkge1xuICAgICAgICB2YXIgcSA9IHRoaXMuY29udGV4dC5nZXRDdXJyZW50UXVlcnkoKTtcbiAgICAgICAgZm9yICh2YXIgaSA9IDA7IGkgPCB0aGlzLl9xdWVyeVdhdGNoZXMubGVuZ3RoOyBpKyspIHtcbiAgICAgICAgICAgIHZhciB3YXRjaCA9IHRoaXMuX3F1ZXJ5V2F0Y2hlc1tpXTtcbiAgICAgICAgICAgIGlmICh0aGlzLl9xdWVyeVt3YXRjaC5rZXldICE9PSBxW3dhdGNoLmtleV0pIHtcbiAgICAgICAgICAgICAgICB3YXRjaC5jYWxsYmFjayh0aGlzLl9xdWVyeVt3YXRjaC5rZXldLCBxW3dhdGNoLmtleV0sIHdhdGNoLmtleSk7XG4gICAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgICAgdGhpcy5fcXVlcnkgPSBxO1xuICAgIH1cbn0pO1xuXG52YXIgU3BsaXR0ZXIgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiU3BsaXR0ZXJcIixcbiAgICBnZXREZWZhdWx0UHJvcHM6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgIGF4aXM6IFwieFwiXG4gICAgICAgIH07XG4gICAgfSxcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgIGFwcGxpZWQ6IGZhbHNlLFxuICAgICAgICAgICAgc3RhcnRYOiBmYWxzZSxcbiAgICAgICAgICAgIHN0YXJ0WTogZmFsc2VcbiAgICAgICAgfTtcbiAgICB9LFxuICAgIG9uTW91c2VEb3duOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgIHN0YXJ0WDogZS5wYWdlWCxcbiAgICAgICAgICAgIHN0YXJ0WTogZS5wYWdlWVxuICAgICAgICB9KTtcbiAgICAgICAgd2luZG93LmFkZEV2ZW50TGlzdGVuZXIoXCJtb3VzZW1vdmVcIiwgdGhpcy5vbk1vdXNlTW92ZSk7XG4gICAgICAgIHdpbmRvdy5hZGRFdmVudExpc3RlbmVyKFwibW91c2V1cFwiLCB0aGlzLm9uTW91c2VVcCk7XG4gICAgICAgIC8vIE9jY2FzaW9uYWxseSwgb25seSBhIGRyYWdFbmQgZXZlbnQgaXMgdHJpZ2dlcmVkLCBidXQgbm8gbW91c2VVcC5cbiAgICAgICAgd2luZG93LmFkZEV2ZW50TGlzdGVuZXIoXCJkcmFnZW5kXCIsIHRoaXMub25EcmFnRW5kKTtcbiAgICB9LFxuICAgIG9uRHJhZ0VuZDogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLmdldERPTU5vZGUoKS5zdHlsZS50cmFuc2Zvcm0gPSBcIlwiO1xuICAgICAgICB3aW5kb3cucmVtb3ZlRXZlbnRMaXN0ZW5lcihcImRyYWdlbmRcIiwgdGhpcy5vbkRyYWdFbmQpO1xuICAgICAgICB3aW5kb3cucmVtb3ZlRXZlbnRMaXN0ZW5lcihcIm1vdXNldXBcIiwgdGhpcy5vbk1vdXNlVXApO1xuICAgICAgICB3aW5kb3cucmVtb3ZlRXZlbnRMaXN0ZW5lcihcIm1vdXNlbW92ZVwiLCB0aGlzLm9uTW91c2VNb3ZlKTtcbiAgICB9LFxuICAgIG9uTW91c2VVcDogZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgdGhpcy5vbkRyYWdFbmQoKTtcblxuICAgICAgICB2YXIgbm9kZSA9IHRoaXMuZ2V0RE9NTm9kZSgpO1xuICAgICAgICB2YXIgcHJldiA9IG5vZGUucHJldmlvdXNFbGVtZW50U2libGluZztcbiAgICAgICAgdmFyIG5leHQgPSBub2RlLm5leHRFbGVtZW50U2libGluZztcblxuICAgICAgICB2YXIgZFggPSBlLnBhZ2VYIC0gdGhpcy5zdGF0ZS5zdGFydFg7XG4gICAgICAgIHZhciBkWSA9IGUucGFnZVkgLSB0aGlzLnN0YXRlLnN0YXJ0WTtcbiAgICAgICAgdmFyIGZsZXhCYXNpcztcbiAgICAgICAgaWYgKHRoaXMucHJvcHMuYXhpcyA9PT0gXCJ4XCIpIHtcbiAgICAgICAgICAgIGZsZXhCYXNpcyA9IHByZXYub2Zmc2V0V2lkdGggKyBkWDtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGZsZXhCYXNpcyA9IHByZXYub2Zmc2V0SGVpZ2h0ICsgZFk7XG4gICAgICAgIH1cblxuICAgICAgICBwcmV2LnN0eWxlLmZsZXggPSBcIjAgMCBcIiArIE1hdGgubWF4KDAsIGZsZXhCYXNpcykgKyBcInB4XCI7XG4gICAgICAgIG5leHQuc3R5bGUuZmxleCA9IFwiMSAxIGF1dG9cIjtcblxuICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgIGFwcGxpZWQ6IHRydWVcbiAgICAgICAgfSk7XG4gICAgICAgIHRoaXMub25SZXNpemUoKTtcbiAgICB9LFxuICAgIG9uTW91c2VNb3ZlOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICB2YXIgZFggPSAwLCBkWSA9IDA7XG4gICAgICAgIGlmICh0aGlzLnByb3BzLmF4aXMgPT09IFwieFwiKSB7XG4gICAgICAgICAgICBkWCA9IGUucGFnZVggLSB0aGlzLnN0YXRlLnN0YXJ0WDtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGRZID0gZS5wYWdlWSAtIHRoaXMuc3RhdGUuc3RhcnRZO1xuICAgICAgICB9XG4gICAgICAgIHRoaXMuZ2V0RE9NTm9kZSgpLnN0eWxlLnRyYW5zZm9ybSA9IFwidHJhbnNsYXRlKFwiICsgZFggKyBcInB4LFwiICsgZFkgKyBcInB4KVwiO1xuICAgIH0sXG4gICAgb25SZXNpemU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgLy8gVHJpZ2dlciBhIGdsb2JhbCByZXNpemUgZXZlbnQuIFRoaXMgbm90aWZpZXMgY29tcG9uZW50cyB0aGF0IGVtcGxveSB2aXJ0dWFsIHNjcm9sbGluZ1xuICAgICAgICAvLyB0aGF0IHRoZWlyIHZpZXdwb3J0IG1heSBoYXZlIGNoYW5nZWQuXG4gICAgICAgIHdpbmRvdy5zZXRUaW1lb3V0KGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHdpbmRvdy5kaXNwYXRjaEV2ZW50KG5ldyBDdXN0b21FdmVudChcInJlc2l6ZVwiKSk7XG4gICAgICAgIH0sIDEpO1xuICAgIH0sXG4gICAgcmVzZXQ6IGZ1bmN0aW9uICh3aWxsVW5tb3VudCkge1xuICAgICAgICBpZiAoIXRoaXMuc3RhdGUuYXBwbGllZCkge1xuICAgICAgICAgICAgcmV0dXJuO1xuICAgICAgICB9XG4gICAgICAgIHZhciBub2RlID0gdGhpcy5nZXRET01Ob2RlKCk7XG4gICAgICAgIHZhciBwcmV2ID0gbm9kZS5wcmV2aW91c0VsZW1lbnRTaWJsaW5nO1xuICAgICAgICB2YXIgbmV4dCA9IG5vZGUubmV4dEVsZW1lbnRTaWJsaW5nO1xuXG4gICAgICAgIHByZXYuc3R5bGUuZmxleCA9IFwiXCI7XG4gICAgICAgIG5leHQuc3R5bGUuZmxleCA9IFwiXCI7XG5cbiAgICAgICAgaWYgKCF3aWxsVW5tb3VudCkge1xuICAgICAgICAgICAgdGhpcy5zZXRTdGF0ZSh7XG4gICAgICAgICAgICAgICAgYXBwbGllZDogZmFsc2VcbiAgICAgICAgICAgIH0pO1xuICAgICAgICB9XG4gICAgICAgIHRoaXMub25SZXNpemUoKTtcbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxVbm1vdW50OiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMucmVzZXQodHJ1ZSk7XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGNsYXNzTmFtZSA9IFwic3BsaXR0ZXJcIjtcbiAgICAgICAgaWYgKHRoaXMucHJvcHMuYXhpcyA9PT0gXCJ4XCIpIHtcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcIiBzcGxpdHRlci14XCI7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCIgc3BsaXR0ZXIteVwiO1xuICAgICAgICB9XG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IGNsYXNzTmFtZX0sIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge29uTW91c2VEb3duOiB0aGlzLm9uTW91c2VEb3duLCBkcmFnZ2FibGU6IFwidHJ1ZVwifSlcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxubW9kdWxlLmV4cG9ydHMgPSB7XG4gICAgU3RhdGU6IFN0YXRlLFxuICAgIE5hdmlnYXRpb246IE5hdmlnYXRpb24sXG4gICAgU3RpY2t5SGVhZE1peGluOiBTdGlja3lIZWFkTWl4aW4sXG4gICAgQXV0b1Njcm9sbE1peGluOiBBdXRvU2Nyb2xsTWl4aW4sXG4gICAgU3BsaXR0ZXI6IFNwbGl0dGVyXG59IiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xuXG52YXIgVmlydHVhbFNjcm9sbE1peGluID0ge1xuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgc3RhcnQ6IDAsXG4gICAgICAgICAgICBzdG9wOiAwXG4gICAgICAgIH07XG4gICAgfSxcbiAgICBjb21wb25lbnRXaWxsTW91bnQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgaWYgKCF0aGlzLnByb3BzLnJvd0hlaWdodCkge1xuICAgICAgICAgICAgY29uc29sZS53YXJuKFwiVmlydHVhbFNjcm9sbE1peGluOiBObyByb3dIZWlnaHQgc3BlY2lmaWVkXCIsIHRoaXMpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBnZXRQbGFjZWhvbGRlclRvcDogZnVuY3Rpb24gKHRvdGFsKSB7XG4gICAgICAgIHZhciBUYWcgPSB0aGlzLnByb3BzLnBsYWNlaG9sZGVyVGFnTmFtZSB8fCBcInRyXCI7XG4gICAgICAgIC8vIFdoZW4gYSBsYXJnZSB0cnVuayBvZiBlbGVtZW50cyBpcyByZW1vdmVkIGZyb20gdGhlIGJ1dHRvbiwgc3RhcnQgbWF5IGJlIGZhciBvZmYgdGhlIHZpZXdwb3J0LlxuICAgICAgICAvLyBUbyBtYWtlIHRoaXMgaXNzdWUgbGVzcyBzZXZlcmUsIGxpbWl0IHRoZSB0b3AgcGxhY2Vob2xkZXIgdG8gdGhlIHRvdGFsIG51bWJlciBvZiByb3dzLlxuICAgICAgICB2YXIgc3R5bGUgPSB7XG4gICAgICAgICAgICBoZWlnaHQ6IE1hdGgubWluKHRoaXMuc3RhdGUuc3RhcnQsIHRvdGFsKSAqIHRoaXMucHJvcHMucm93SGVpZ2h0XG4gICAgICAgIH07XG4gICAgICAgIHZhciBzcGFjZXIgPSBSZWFjdC5jcmVhdGVFbGVtZW50KFRhZywge2tleTogXCJwbGFjZWhvbGRlci10b3BcIiwgc3R5bGU6IHN0eWxlfSk7XG5cbiAgICAgICAgaWYgKHRoaXMuc3RhdGUuc3RhcnQgJSAyID09PSAxKSB7XG4gICAgICAgICAgICAvLyBmaXggZXZlbi9vZGQgcm93c1xuICAgICAgICAgICAgcmV0dXJuIFtzcGFjZXIsIFJlYWN0LmNyZWF0ZUVsZW1lbnQoVGFnLCB7a2V5OiBcInBsYWNlaG9sZGVyLXRvcC0yXCJ9KV07XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICByZXR1cm4gc3BhY2VyO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBnZXRQbGFjZWhvbGRlckJvdHRvbTogZnVuY3Rpb24gKHRvdGFsKSB7XG4gICAgICAgIHZhciBUYWcgPSB0aGlzLnByb3BzLnBsYWNlaG9sZGVyVGFnTmFtZSB8fCBcInRyXCI7XG4gICAgICAgIHZhciBzdHlsZSA9IHtcbiAgICAgICAgICAgIGhlaWdodDogTWF0aC5tYXgoMCwgdG90YWwgLSB0aGlzLnN0YXRlLnN0b3ApICogdGhpcy5wcm9wcy5yb3dIZWlnaHRcbiAgICAgICAgfTtcbiAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoVGFnLCB7a2V5OiBcInBsYWNlaG9sZGVyLWJvdHRvbVwiLCBzdHlsZTogc3R5bGV9KTtcbiAgICB9LFxuICAgIGNvbXBvbmVudERpZE1vdW50OiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMub25TY3JvbGwoKTtcbiAgICAgICAgd2luZG93LmFkZEV2ZW50TGlzdGVuZXIoJ3Jlc2l6ZScsIHRoaXMub25TY3JvbGwpO1xuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbFVubW91bnQ6IGZ1bmN0aW9uKCl7XG4gICAgICAgIHdpbmRvdy5yZW1vdmVFdmVudExpc3RlbmVyKCdyZXNpemUnLCB0aGlzLm9uU2Nyb2xsKTtcbiAgICB9LFxuICAgIG9uU2Nyb2xsOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciB2aWV3cG9ydCA9IHRoaXMuZ2V0RE9NTm9kZSgpO1xuICAgICAgICB2YXIgdG9wID0gdmlld3BvcnQuc2Nyb2xsVG9wO1xuICAgICAgICB2YXIgaGVpZ2h0ID0gdmlld3BvcnQub2Zmc2V0SGVpZ2h0O1xuICAgICAgICB2YXIgc3RhcnQgPSBNYXRoLmZsb29yKHRvcCAvIHRoaXMucHJvcHMucm93SGVpZ2h0KTtcbiAgICAgICAgdmFyIHN0b3AgPSBzdGFydCArIE1hdGguY2VpbChoZWlnaHQgLyAodGhpcy5wcm9wcy5yb3dIZWlnaHRNaW4gfHwgdGhpcy5wcm9wcy5yb3dIZWlnaHQpKTtcblxuICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgIHN0YXJ0OiBzdGFydCxcbiAgICAgICAgICAgIHN0b3A6IHN0b3BcbiAgICAgICAgfSk7XG4gICAgfSxcbiAgICByZW5kZXJSb3dzOiBmdW5jdGlvbiAoZWxlbXMpIHtcbiAgICAgICAgdmFyIHJvd3MgPSBbXTtcbiAgICAgICAgdmFyIG1heCA9IE1hdGgubWluKGVsZW1zLmxlbmd0aCwgdGhpcy5zdGF0ZS5zdG9wKTtcblxuICAgICAgICBmb3IgKHZhciBpID0gdGhpcy5zdGF0ZS5zdGFydDsgaSA8IG1heDsgaSsrKSB7XG4gICAgICAgICAgICB2YXIgZWxlbSA9IGVsZW1zW2ldO1xuICAgICAgICAgICAgcm93cy5wdXNoKHRoaXMucmVuZGVyUm93KGVsZW0pKTtcbiAgICAgICAgfVxuICAgICAgICByZXR1cm4gcm93cztcbiAgICB9LFxuICAgIHNjcm9sbFJvd0ludG9WaWV3OiBmdW5jdGlvbiAoaW5kZXgsIGhlYWRfaGVpZ2h0KSB7XG5cbiAgICAgICAgdmFyIHJvd190b3AgPSAoaW5kZXggKiB0aGlzLnByb3BzLnJvd0hlaWdodCkgKyBoZWFkX2hlaWdodDtcbiAgICAgICAgdmFyIHJvd19ib3R0b20gPSByb3dfdG9wICsgdGhpcy5wcm9wcy5yb3dIZWlnaHQ7XG5cbiAgICAgICAgdmFyIHZpZXdwb3J0ID0gdGhpcy5nZXRET01Ob2RlKCk7XG4gICAgICAgIHZhciB2aWV3cG9ydF90b3AgPSB2aWV3cG9ydC5zY3JvbGxUb3A7XG4gICAgICAgIHZhciB2aWV3cG9ydF9ib3R0b20gPSB2aWV3cG9ydF90b3AgKyB2aWV3cG9ydC5vZmZzZXRIZWlnaHQ7XG5cbiAgICAgICAgLy8gQWNjb3VudCBmb3IgcGlubmVkIHRoZWFkXG4gICAgICAgIGlmIChyb3dfdG9wIC0gaGVhZF9oZWlnaHQgPCB2aWV3cG9ydF90b3ApIHtcbiAgICAgICAgICAgIHZpZXdwb3J0LnNjcm9sbFRvcCA9IHJvd190b3AgLSBoZWFkX2hlaWdodDtcbiAgICAgICAgfSBlbHNlIGlmIChyb3dfYm90dG9tID4gdmlld3BvcnRfYm90dG9tKSB7XG4gICAgICAgICAgICB2aWV3cG9ydC5zY3JvbGxUb3AgPSByb3dfYm90dG9tIC0gdmlld3BvcnQub2Zmc2V0SGVpZ2h0O1xuICAgICAgICB9XG4gICAgfSxcbn07XG5cbm1vZHVsZS5leHBvcnRzICA9IFZpcnR1YWxTY3JvbGxNaXhpbjsiLCJcbnZhciBhY3Rpb25zID0gcmVxdWlyZShcIi4vYWN0aW9ucy5qc1wiKTtcblxuZnVuY3Rpb24gQ29ubmVjdGlvbih1cmwpIHtcbiAgICBpZiAodXJsWzBdID09PSBcIi9cIikge1xuICAgICAgICB1cmwgPSBsb2NhdGlvbi5vcmlnaW4ucmVwbGFjZShcImh0dHBcIiwgXCJ3c1wiKSArIHVybDtcbiAgICB9XG5cbiAgICB2YXIgd3MgPSBuZXcgV2ViU29ja2V0KHVybCk7XG4gICAgd3Mub25vcGVuID0gZnVuY3Rpb24gKCkge1xuICAgICAgICBhY3Rpb25zLkNvbm5lY3Rpb25BY3Rpb25zLm9wZW4oKTtcbiAgICB9O1xuICAgIHdzLm9ubWVzc2FnZSA9IGZ1bmN0aW9uIChtZXNzYWdlKSB7XG4gICAgICAgIHZhciBtID0gSlNPTi5wYXJzZShtZXNzYWdlLmRhdGEpO1xuICAgICAgICBBcHBEaXNwYXRjaGVyLmRpc3BhdGNoU2VydmVyQWN0aW9uKG0pO1xuICAgIH07XG4gICAgd3Mub25lcnJvciA9IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgYWN0aW9ucy5Db25uZWN0aW9uQWN0aW9ucy5lcnJvcigpO1xuICAgICAgICBFdmVudExvZ0FjdGlvbnMuYWRkX2V2ZW50KFwiV2ViU29ja2V0IGNvbm5lY3Rpb24gZXJyb3IuXCIpO1xuICAgIH07XG4gICAgd3Mub25jbG9zZSA9IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgYWN0aW9ucy5Db25uZWN0aW9uQWN0aW9ucy5jbG9zZSgpO1xuICAgICAgICBFdmVudExvZ0FjdGlvbnMuYWRkX2V2ZW50KFwiV2ViU29ja2V0IGNvbm5lY3Rpb24gY2xvc2VkLlwiKTtcbiAgICB9O1xuICAgIHJldHVybiB3cztcbn1cblxubW9kdWxlLmV4cG9ydHMgPSBDb25uZWN0aW9uOyIsImNvbnN0IFBheWxvYWRTb3VyY2VzID0ge1xuICAgIFZJRVc6IFwidmlld1wiLFxuICAgIFNFUlZFUjogXCJzZXJ2ZXJcIlxufTtcblxuXG5mdW5jdGlvbiBEaXNwYXRjaGVyKCkge1xuICAgIHRoaXMuY2FsbGJhY2tzID0gW107XG59XG5EaXNwYXRjaGVyLnByb3RvdHlwZS5yZWdpc3RlciA9IGZ1bmN0aW9uIChjYWxsYmFjaykge1xuICAgIHRoaXMuY2FsbGJhY2tzLnB1c2goY2FsbGJhY2spO1xufTtcbkRpc3BhdGNoZXIucHJvdG90eXBlLnVucmVnaXN0ZXIgPSBmdW5jdGlvbiAoY2FsbGJhY2spIHtcbiAgICB2YXIgaW5kZXggPSB0aGlzLmNhbGxiYWNrcy5pbmRleE9mKGNhbGxiYWNrKTtcbiAgICBpZiAoaW5kZXggPj0gMCkge1xuICAgICAgICB0aGlzLmNhbGxiYWNrcy5zcGxpY2UoaW5kZXgsIDEpO1xuICAgIH1cbn07XG5EaXNwYXRjaGVyLnByb3RvdHlwZS5kaXNwYXRjaCA9IGZ1bmN0aW9uIChwYXlsb2FkKSB7XG4gICAgY29uc29sZS5kZWJ1ZyhcImRpc3BhdGNoXCIsIHBheWxvYWQpO1xuICAgIGZvciAodmFyIGkgPSAwOyBpIDwgdGhpcy5jYWxsYmFja3MubGVuZ3RoOyBpKyspIHtcbiAgICAgICAgdGhpcy5jYWxsYmFja3NbaV0ocGF5bG9hZCk7XG4gICAgfVxufTtcblxuXG5BcHBEaXNwYXRjaGVyID0gbmV3IERpc3BhdGNoZXIoKTtcbkFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uID0gZnVuY3Rpb24gKGFjdGlvbikge1xuICAgIGFjdGlvbi5zb3VyY2UgPSBQYXlsb2FkU291cmNlcy5WSUVXO1xuICAgIHRoaXMuZGlzcGF0Y2goYWN0aW9uKTtcbn07XG5BcHBEaXNwYXRjaGVyLmRpc3BhdGNoU2VydmVyQWN0aW9uID0gZnVuY3Rpb24gKGFjdGlvbikge1xuICAgIGFjdGlvbi5zb3VyY2UgPSBQYXlsb2FkU291cmNlcy5TRVJWRVI7XG4gICAgdGhpcy5kaXNwYXRjaChhY3Rpb24pO1xufTtcblxubW9kdWxlLmV4cG9ydHMgPSB7XG4gICAgQXBwRGlzcGF0Y2hlcjogQXBwRGlzcGF0Y2hlclxufTsiLCIvKiBqc2hpbnQgaWdub3JlOnN0YXJ0ICovXG5GaWx0ID0gKGZ1bmN0aW9uKCkge1xuICAvKlxuICAgKiBHZW5lcmF0ZWQgYnkgUEVHLmpzIDAuOC4wLlxuICAgKlxuICAgKiBodHRwOi8vcGVnanMubWFqZGEuY3ovXG4gICAqL1xuXG4gIGZ1bmN0aW9uIHBlZyRzdWJjbGFzcyhjaGlsZCwgcGFyZW50KSB7XG4gICAgZnVuY3Rpb24gY3RvcigpIHsgdGhpcy5jb25zdHJ1Y3RvciA9IGNoaWxkOyB9XG4gICAgY3Rvci5wcm90b3R5cGUgPSBwYXJlbnQucHJvdG90eXBlO1xuICAgIGNoaWxkLnByb3RvdHlwZSA9IG5ldyBjdG9yKCk7XG4gIH1cblxuICBmdW5jdGlvbiBTeW50YXhFcnJvcihtZXNzYWdlLCBleHBlY3RlZCwgZm91bmQsIG9mZnNldCwgbGluZSwgY29sdW1uKSB7XG4gICAgdGhpcy5tZXNzYWdlICA9IG1lc3NhZ2U7XG4gICAgdGhpcy5leHBlY3RlZCA9IGV4cGVjdGVkO1xuICAgIHRoaXMuZm91bmQgICAgPSBmb3VuZDtcbiAgICB0aGlzLm9mZnNldCAgID0gb2Zmc2V0O1xuICAgIHRoaXMubGluZSAgICAgPSBsaW5lO1xuICAgIHRoaXMuY29sdW1uICAgPSBjb2x1bW47XG5cbiAgICB0aGlzLm5hbWUgICAgID0gXCJTeW50YXhFcnJvclwiO1xuICB9XG5cbiAgcGVnJHN1YmNsYXNzKFN5bnRheEVycm9yLCBFcnJvcik7XG5cbiAgZnVuY3Rpb24gcGFyc2UoaW5wdXQpIHtcbiAgICB2YXIgb3B0aW9ucyA9IGFyZ3VtZW50cy5sZW5ndGggPiAxID8gYXJndW1lbnRzWzFdIDoge30sXG5cbiAgICAgICAgcGVnJEZBSUxFRCA9IHt9LFxuXG4gICAgICAgIHBlZyRzdGFydFJ1bGVGdW5jdGlvbnMgPSB7IHN0YXJ0OiBwZWckcGFyc2VzdGFydCB9LFxuICAgICAgICBwZWckc3RhcnRSdWxlRnVuY3Rpb24gID0gcGVnJHBhcnNlc3RhcnQsXG5cbiAgICAgICAgcGVnJGMwID0geyB0eXBlOiBcIm90aGVyXCIsIGRlc2NyaXB0aW9uOiBcImZpbHRlciBleHByZXNzaW9uXCIgfSxcbiAgICAgICAgcGVnJGMxID0gcGVnJEZBSUxFRCxcbiAgICAgICAgcGVnJGMyID0gZnVuY3Rpb24ob3JFeHByKSB7IHJldHVybiBvckV4cHI7IH0sXG4gICAgICAgIHBlZyRjMyA9IFtdLFxuICAgICAgICBwZWckYzQgPSBmdW5jdGlvbigpIHtyZXR1cm4gdHJ1ZUZpbHRlcjsgfSxcbiAgICAgICAgcGVnJGM1ID0geyB0eXBlOiBcIm90aGVyXCIsIGRlc2NyaXB0aW9uOiBcIndoaXRlc3BhY2VcIiB9LFxuICAgICAgICBwZWckYzYgPSAvXlsgXFx0XFxuXFxyXS8sXG4gICAgICAgIHBlZyRjNyA9IHsgdHlwZTogXCJjbGFzc1wiLCB2YWx1ZTogXCJbIFxcXFx0XFxcXG5cXFxccl1cIiwgZGVzY3JpcHRpb246IFwiWyBcXFxcdFxcXFxuXFxcXHJdXCIgfSxcbiAgICAgICAgcGVnJGM4ID0geyB0eXBlOiBcIm90aGVyXCIsIGRlc2NyaXB0aW9uOiBcImNvbnRyb2wgY2hhcmFjdGVyXCIgfSxcbiAgICAgICAgcGVnJGM5ID0gL15bfCYhKCl+XCJdLyxcbiAgICAgICAgcGVnJGMxMCA9IHsgdHlwZTogXCJjbGFzc1wiLCB2YWx1ZTogXCJbfCYhKCl+XFxcIl1cIiwgZGVzY3JpcHRpb246IFwiW3wmISgpflxcXCJdXCIgfSxcbiAgICAgICAgcGVnJGMxMSA9IHsgdHlwZTogXCJvdGhlclwiLCBkZXNjcmlwdGlvbjogXCJvcHRpb25hbCB3aGl0ZXNwYWNlXCIgfSxcbiAgICAgICAgcGVnJGMxMiA9IFwifFwiLFxuICAgICAgICBwZWckYzEzID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifFwiLCBkZXNjcmlwdGlvbjogXCJcXFwifFxcXCJcIiB9LFxuICAgICAgICBwZWckYzE0ID0gZnVuY3Rpb24oZmlyc3QsIHNlY29uZCkgeyByZXR1cm4gb3IoZmlyc3QsIHNlY29uZCk7IH0sXG4gICAgICAgIHBlZyRjMTUgPSBcIiZcIixcbiAgICAgICAgcGVnJGMxNiA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIiZcIiwgZGVzY3JpcHRpb246IFwiXFxcIiZcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMxNyA9IGZ1bmN0aW9uKGZpcnN0LCBzZWNvbmQpIHsgcmV0dXJuIGFuZChmaXJzdCwgc2Vjb25kKTsgfSxcbiAgICAgICAgcGVnJGMxOCA9IFwiIVwiLFxuICAgICAgICBwZWckYzE5ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiIVwiLCBkZXNjcmlwdGlvbjogXCJcXFwiIVxcXCJcIiB9LFxuICAgICAgICBwZWckYzIwID0gZnVuY3Rpb24oZXhwcikgeyByZXR1cm4gbm90KGV4cHIpOyB9LFxuICAgICAgICBwZWckYzIxID0gXCIoXCIsXG4gICAgICAgIHBlZyRjMjIgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCIoXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCIoXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMjMgPSBcIilcIixcbiAgICAgICAgcGVnJGMyNCA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIilcIiwgZGVzY3JpcHRpb246IFwiXFxcIilcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMyNSA9IGZ1bmN0aW9uKGV4cHIpIHsgcmV0dXJuIGJpbmRpbmcoZXhwcik7IH0sXG4gICAgICAgIHBlZyRjMjYgPSBcIn5hXCIsXG4gICAgICAgIHBlZyRjMjcgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+YVwiLCBkZXNjcmlwdGlvbjogXCJcXFwifmFcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMyOCA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gYXNzZXRGaWx0ZXI7IH0sXG4gICAgICAgIHBlZyRjMjkgPSBcIn5lXCIsXG4gICAgICAgIHBlZyRjMzAgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+ZVwiLCBkZXNjcmlwdGlvbjogXCJcXFwifmVcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMzMSA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gZXJyb3JGaWx0ZXI7IH0sXG4gICAgICAgIHBlZyRjMzIgPSBcIn5xXCIsXG4gICAgICAgIHBlZyRjMzMgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+cVwiLCBkZXNjcmlwdGlvbjogXCJcXFwifnFcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMzNCA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gbm9SZXNwb25zZUZpbHRlcjsgfSxcbiAgICAgICAgcGVnJGMzNSA9IFwifnNcIixcbiAgICAgICAgcGVnJGMzNiA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5zXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+c1xcXCJcIiB9LFxuICAgICAgICBwZWckYzM3ID0gZnVuY3Rpb24oKSB7IHJldHVybiByZXNwb25zZUZpbHRlcjsgfSxcbiAgICAgICAgcGVnJGMzOCA9IFwidHJ1ZVwiLFxuICAgICAgICBwZWckYzM5ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwidHJ1ZVwiLCBkZXNjcmlwdGlvbjogXCJcXFwidHJ1ZVxcXCJcIiB9LFxuICAgICAgICBwZWckYzQwID0gZnVuY3Rpb24oKSB7IHJldHVybiB0cnVlRmlsdGVyOyB9LFxuICAgICAgICBwZWckYzQxID0gXCJmYWxzZVwiLFxuICAgICAgICBwZWckYzQyID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiZmFsc2VcIiwgZGVzY3JpcHRpb246IFwiXFxcImZhbHNlXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNDMgPSBmdW5jdGlvbigpIHsgcmV0dXJuIGZhbHNlRmlsdGVyOyB9LFxuICAgICAgICBwZWckYzQ0ID0gXCJ+Y1wiLFxuICAgICAgICBwZWckYzQ1ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifmNcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5jXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNDYgPSBmdW5jdGlvbihzKSB7IHJldHVybiByZXNwb25zZUNvZGUocyk7IH0sXG4gICAgICAgIHBlZyRjNDcgPSBcIn5kXCIsXG4gICAgICAgIHBlZyRjNDggPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+ZFwiLCBkZXNjcmlwdGlvbjogXCJcXFwifmRcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM0OSA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIGRvbWFpbihzKTsgfSxcbiAgICAgICAgcGVnJGM1MCA9IFwifmhcIixcbiAgICAgICAgcGVnJGM1MSA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5oXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+aFxcXCJcIiB9LFxuICAgICAgICBwZWckYzUyID0gZnVuY3Rpb24ocykgeyByZXR1cm4gaGVhZGVyKHMpOyB9LFxuICAgICAgICBwZWckYzUzID0gXCJ+aHFcIixcbiAgICAgICAgcGVnJGM1NCA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5ocVwiLCBkZXNjcmlwdGlvbjogXCJcXFwifmhxXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNTUgPSBmdW5jdGlvbihzKSB7IHJldHVybiByZXF1ZXN0SGVhZGVyKHMpOyB9LFxuICAgICAgICBwZWckYzU2ID0gXCJ+aHNcIixcbiAgICAgICAgcGVnJGM1NyA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5oc1wiLCBkZXNjcmlwdGlvbjogXCJcXFwifmhzXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNTggPSBmdW5jdGlvbihzKSB7IHJldHVybiByZXNwb25zZUhlYWRlcihzKTsgfSxcbiAgICAgICAgcGVnJGM1OSA9IFwifm1cIixcbiAgICAgICAgcGVnJGM2MCA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5tXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+bVxcXCJcIiB9LFxuICAgICAgICBwZWckYzYxID0gZnVuY3Rpb24ocykgeyByZXR1cm4gbWV0aG9kKHMpOyB9LFxuICAgICAgICBwZWckYzYyID0gXCJ+dFwiLFxuICAgICAgICBwZWckYzYzID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifnRcIiwgZGVzY3JpcHRpb246IFwiXFxcIn50XFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNjQgPSBmdW5jdGlvbihzKSB7IHJldHVybiBjb250ZW50VHlwZShzKTsgfSxcbiAgICAgICAgcGVnJGM2NSA9IFwifnRxXCIsXG4gICAgICAgIHBlZyRjNjYgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+dHFcIiwgZGVzY3JpcHRpb246IFwiXFxcIn50cVxcXCJcIiB9LFxuICAgICAgICBwZWckYzY3ID0gZnVuY3Rpb24ocykgeyByZXR1cm4gcmVxdWVzdENvbnRlbnRUeXBlKHMpOyB9LFxuICAgICAgICBwZWckYzY4ID0gXCJ+dHNcIixcbiAgICAgICAgcGVnJGM2OSA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn50c1wiLCBkZXNjcmlwdGlvbjogXCJcXFwifnRzXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNzAgPSBmdW5jdGlvbihzKSB7IHJldHVybiByZXNwb25zZUNvbnRlbnRUeXBlKHMpOyB9LFxuICAgICAgICBwZWckYzcxID0gXCJ+dVwiLFxuICAgICAgICBwZWckYzcyID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifnVcIiwgZGVzY3JpcHRpb246IFwiXFxcIn51XFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNzMgPSBmdW5jdGlvbihzKSB7IHJldHVybiB1cmwocyk7IH0sXG4gICAgICAgIHBlZyRjNzQgPSB7IHR5cGU6IFwib3RoZXJcIiwgZGVzY3JpcHRpb246IFwiaW50ZWdlclwiIH0sXG4gICAgICAgIHBlZyRjNzUgPSBudWxsLFxuICAgICAgICBwZWckYzc2ID0gL15bJ1wiXS8sXG4gICAgICAgIHBlZyRjNzcgPSB7IHR5cGU6IFwiY2xhc3NcIiwgdmFsdWU6IFwiWydcXFwiXVwiLCBkZXNjcmlwdGlvbjogXCJbJ1xcXCJdXCIgfSxcbiAgICAgICAgcGVnJGM3OCA9IC9eWzAtOV0vLFxuICAgICAgICBwZWckYzc5ID0geyB0eXBlOiBcImNsYXNzXCIsIHZhbHVlOiBcIlswLTldXCIsIGRlc2NyaXB0aW9uOiBcIlswLTldXCIgfSxcbiAgICAgICAgcGVnJGM4MCA9IGZ1bmN0aW9uKGRpZ2l0cykgeyByZXR1cm4gcGFyc2VJbnQoZGlnaXRzLmpvaW4oXCJcIiksIDEwKTsgfSxcbiAgICAgICAgcGVnJGM4MSA9IHsgdHlwZTogXCJvdGhlclwiLCBkZXNjcmlwdGlvbjogXCJzdHJpbmdcIiB9LFxuICAgICAgICBwZWckYzgyID0gXCJcXFwiXCIsXG4gICAgICAgIHBlZyRjODMgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJcXFwiXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJcXFxcXFxcIlxcXCJcIiB9LFxuICAgICAgICBwZWckYzg0ID0gZnVuY3Rpb24oY2hhcnMpIHsgcmV0dXJuIGNoYXJzLmpvaW4oXCJcIik7IH0sXG4gICAgICAgIHBlZyRjODUgPSBcIidcIixcbiAgICAgICAgcGVnJGM4NiA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIidcIiwgZGVzY3JpcHRpb246IFwiXFxcIidcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM4NyA9IHZvaWQgMCxcbiAgICAgICAgcGVnJGM4OCA9IC9eW1wiXFxcXF0vLFxuICAgICAgICBwZWckYzg5ID0geyB0eXBlOiBcImNsYXNzXCIsIHZhbHVlOiBcIltcXFwiXFxcXFxcXFxdXCIsIGRlc2NyaXB0aW9uOiBcIltcXFwiXFxcXFxcXFxdXCIgfSxcbiAgICAgICAgcGVnJGM5MCA9IHsgdHlwZTogXCJhbnlcIiwgZGVzY3JpcHRpb246IFwiYW55IGNoYXJhY3RlclwiIH0sXG4gICAgICAgIHBlZyRjOTEgPSBmdW5jdGlvbihjaGFyKSB7IHJldHVybiBjaGFyOyB9LFxuICAgICAgICBwZWckYzkyID0gXCJcXFxcXCIsXG4gICAgICAgIHBlZyRjOTMgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJcXFxcXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJcXFxcXFxcXFxcXCJcIiB9LFxuICAgICAgICBwZWckYzk0ID0gL15bJ1xcXFxdLyxcbiAgICAgICAgcGVnJGM5NSA9IHsgdHlwZTogXCJjbGFzc1wiLCB2YWx1ZTogXCJbJ1xcXFxcXFxcXVwiLCBkZXNjcmlwdGlvbjogXCJbJ1xcXFxcXFxcXVwiIH0sXG4gICAgICAgIHBlZyRjOTYgPSAvXlsnXCJcXFxcXS8sXG4gICAgICAgIHBlZyRjOTcgPSB7IHR5cGU6IFwiY2xhc3NcIiwgdmFsdWU6IFwiWydcXFwiXFxcXFxcXFxdXCIsIGRlc2NyaXB0aW9uOiBcIlsnXFxcIlxcXFxcXFxcXVwiIH0sXG4gICAgICAgIHBlZyRjOTggPSBcIm5cIixcbiAgICAgICAgcGVnJGM5OSA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIm5cIiwgZGVzY3JpcHRpb246IFwiXFxcIm5cXFwiXCIgfSxcbiAgICAgICAgcGVnJGMxMDAgPSBmdW5jdGlvbigpIHsgcmV0dXJuIFwiXFxuXCI7IH0sXG4gICAgICAgIHBlZyRjMTAxID0gXCJyXCIsXG4gICAgICAgIHBlZyRjMTAyID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiclwiLCBkZXNjcmlwdGlvbjogXCJcXFwiclxcXCJcIiB9LFxuICAgICAgICBwZWckYzEwMyA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gXCJcXHJcIjsgfSxcbiAgICAgICAgcGVnJGMxMDQgPSBcInRcIixcbiAgICAgICAgcGVnJGMxMDUgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ0XCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ0XFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMTA2ID0gZnVuY3Rpb24oKSB7IHJldHVybiBcIlxcdFwiOyB9LFxuXG4gICAgICAgIHBlZyRjdXJyUG9zICAgICAgICAgID0gMCxcbiAgICAgICAgcGVnJHJlcG9ydGVkUG9zICAgICAgPSAwLFxuICAgICAgICBwZWckY2FjaGVkUG9zICAgICAgICA9IDAsXG4gICAgICAgIHBlZyRjYWNoZWRQb3NEZXRhaWxzID0geyBsaW5lOiAxLCBjb2x1bW46IDEsIHNlZW5DUjogZmFsc2UgfSxcbiAgICAgICAgcGVnJG1heEZhaWxQb3MgICAgICAgPSAwLFxuICAgICAgICBwZWckbWF4RmFpbEV4cGVjdGVkICA9IFtdLFxuICAgICAgICBwZWckc2lsZW50RmFpbHMgICAgICA9IDAsXG5cbiAgICAgICAgcGVnJHJlc3VsdDtcblxuICAgIGlmIChcInN0YXJ0UnVsZVwiIGluIG9wdGlvbnMpIHtcbiAgICAgIGlmICghKG9wdGlvbnMuc3RhcnRSdWxlIGluIHBlZyRzdGFydFJ1bGVGdW5jdGlvbnMpKSB7XG4gICAgICAgIHRocm93IG5ldyBFcnJvcihcIkNhbid0IHN0YXJ0IHBhcnNpbmcgZnJvbSBydWxlIFxcXCJcIiArIG9wdGlvbnMuc3RhcnRSdWxlICsgXCJcXFwiLlwiKTtcbiAgICAgIH1cblxuICAgICAgcGVnJHN0YXJ0UnVsZUZ1bmN0aW9uID0gcGVnJHN0YXJ0UnVsZUZ1bmN0aW9uc1tvcHRpb25zLnN0YXJ0UnVsZV07XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gdGV4dCgpIHtcbiAgICAgIHJldHVybiBpbnB1dC5zdWJzdHJpbmcocGVnJHJlcG9ydGVkUG9zLCBwZWckY3VyclBvcyk7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gb2Zmc2V0KCkge1xuICAgICAgcmV0dXJuIHBlZyRyZXBvcnRlZFBvcztcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBsaW5lKCkge1xuICAgICAgcmV0dXJuIHBlZyRjb21wdXRlUG9zRGV0YWlscyhwZWckcmVwb3J0ZWRQb3MpLmxpbmU7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gY29sdW1uKCkge1xuICAgICAgcmV0dXJuIHBlZyRjb21wdXRlUG9zRGV0YWlscyhwZWckcmVwb3J0ZWRQb3MpLmNvbHVtbjtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBleHBlY3RlZChkZXNjcmlwdGlvbikge1xuICAgICAgdGhyb3cgcGVnJGJ1aWxkRXhjZXB0aW9uKFxuICAgICAgICBudWxsLFxuICAgICAgICBbeyB0eXBlOiBcIm90aGVyXCIsIGRlc2NyaXB0aW9uOiBkZXNjcmlwdGlvbiB9XSxcbiAgICAgICAgcGVnJHJlcG9ydGVkUG9zXG4gICAgICApO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIGVycm9yKG1lc3NhZ2UpIHtcbiAgICAgIHRocm93IHBlZyRidWlsZEV4Y2VwdGlvbihtZXNzYWdlLCBudWxsLCBwZWckcmVwb3J0ZWRQb3MpO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRjb21wdXRlUG9zRGV0YWlscyhwb3MpIHtcbiAgICAgIGZ1bmN0aW9uIGFkdmFuY2UoZGV0YWlscywgc3RhcnRQb3MsIGVuZFBvcykge1xuICAgICAgICB2YXIgcCwgY2g7XG5cbiAgICAgICAgZm9yIChwID0gc3RhcnRQb3M7IHAgPCBlbmRQb3M7IHArKykge1xuICAgICAgICAgIGNoID0gaW5wdXQuY2hhckF0KHApO1xuICAgICAgICAgIGlmIChjaCA9PT0gXCJcXG5cIikge1xuICAgICAgICAgICAgaWYgKCFkZXRhaWxzLnNlZW5DUikgeyBkZXRhaWxzLmxpbmUrKzsgfVxuICAgICAgICAgICAgZGV0YWlscy5jb2x1bW4gPSAxO1xuICAgICAgICAgICAgZGV0YWlscy5zZWVuQ1IgPSBmYWxzZTtcbiAgICAgICAgICB9IGVsc2UgaWYgKGNoID09PSBcIlxcclwiIHx8IGNoID09PSBcIlxcdTIwMjhcIiB8fCBjaCA9PT0gXCJcXHUyMDI5XCIpIHtcbiAgICAgICAgICAgIGRldGFpbHMubGluZSsrO1xuICAgICAgICAgICAgZGV0YWlscy5jb2x1bW4gPSAxO1xuICAgICAgICAgICAgZGV0YWlscy5zZWVuQ1IgPSB0cnVlO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBkZXRhaWxzLmNvbHVtbisrO1xuICAgICAgICAgICAgZGV0YWlscy5zZWVuQ1IgPSBmYWxzZTtcbiAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgIH1cblxuICAgICAgaWYgKHBlZyRjYWNoZWRQb3MgIT09IHBvcykge1xuICAgICAgICBpZiAocGVnJGNhY2hlZFBvcyA+IHBvcykge1xuICAgICAgICAgIHBlZyRjYWNoZWRQb3MgPSAwO1xuICAgICAgICAgIHBlZyRjYWNoZWRQb3NEZXRhaWxzID0geyBsaW5lOiAxLCBjb2x1bW46IDEsIHNlZW5DUjogZmFsc2UgfTtcbiAgICAgICAgfVxuICAgICAgICBhZHZhbmNlKHBlZyRjYWNoZWRQb3NEZXRhaWxzLCBwZWckY2FjaGVkUG9zLCBwb3MpO1xuICAgICAgICBwZWckY2FjaGVkUG9zID0gcG9zO1xuICAgICAgfVxuXG4gICAgICByZXR1cm4gcGVnJGNhY2hlZFBvc0RldGFpbHM7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJGZhaWwoZXhwZWN0ZWQpIHtcbiAgICAgIGlmIChwZWckY3VyclBvcyA8IHBlZyRtYXhGYWlsUG9zKSB7IHJldHVybjsgfVxuXG4gICAgICBpZiAocGVnJGN1cnJQb3MgPiBwZWckbWF4RmFpbFBvcykge1xuICAgICAgICBwZWckbWF4RmFpbFBvcyA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBwZWckbWF4RmFpbEV4cGVjdGVkID0gW107XG4gICAgICB9XG5cbiAgICAgIHBlZyRtYXhGYWlsRXhwZWN0ZWQucHVzaChleHBlY3RlZCk7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJGJ1aWxkRXhjZXB0aW9uKG1lc3NhZ2UsIGV4cGVjdGVkLCBwb3MpIHtcbiAgICAgIGZ1bmN0aW9uIGNsZWFudXBFeHBlY3RlZChleHBlY3RlZCkge1xuICAgICAgICB2YXIgaSA9IDE7XG5cbiAgICAgICAgZXhwZWN0ZWQuc29ydChmdW5jdGlvbihhLCBiKSB7XG4gICAgICAgICAgaWYgKGEuZGVzY3JpcHRpb24gPCBiLmRlc2NyaXB0aW9uKSB7XG4gICAgICAgICAgICByZXR1cm4gLTE7XG4gICAgICAgICAgfSBlbHNlIGlmIChhLmRlc2NyaXB0aW9uID4gYi5kZXNjcmlwdGlvbikge1xuICAgICAgICAgICAgcmV0dXJuIDE7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHJldHVybiAwO1xuICAgICAgICAgIH1cbiAgICAgICAgfSk7XG5cbiAgICAgICAgd2hpbGUgKGkgPCBleHBlY3RlZC5sZW5ndGgpIHtcbiAgICAgICAgICBpZiAoZXhwZWN0ZWRbaSAtIDFdID09PSBleHBlY3RlZFtpXSkge1xuICAgICAgICAgICAgZXhwZWN0ZWQuc3BsaWNlKGksIDEpO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBpKys7XG4gICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICB9XG5cbiAgICAgIGZ1bmN0aW9uIGJ1aWxkTWVzc2FnZShleHBlY3RlZCwgZm91bmQpIHtcbiAgICAgICAgZnVuY3Rpb24gc3RyaW5nRXNjYXBlKHMpIHtcbiAgICAgICAgICBmdW5jdGlvbiBoZXgoY2gpIHsgcmV0dXJuIGNoLmNoYXJDb2RlQXQoMCkudG9TdHJpbmcoMTYpLnRvVXBwZXJDYXNlKCk7IH1cblxuICAgICAgICAgIHJldHVybiBzXG4gICAgICAgICAgICAucmVwbGFjZSgvXFxcXC9nLCAgICdcXFxcXFxcXCcpXG4gICAgICAgICAgICAucmVwbGFjZSgvXCIvZywgICAgJ1xcXFxcIicpXG4gICAgICAgICAgICAucmVwbGFjZSgvXFx4MDgvZywgJ1xcXFxiJylcbiAgICAgICAgICAgIC5yZXBsYWNlKC9cXHQvZywgICAnXFxcXHQnKVxuICAgICAgICAgICAgLnJlcGxhY2UoL1xcbi9nLCAgICdcXFxcbicpXG4gICAgICAgICAgICAucmVwbGFjZSgvXFxmL2csICAgJ1xcXFxmJylcbiAgICAgICAgICAgIC5yZXBsYWNlKC9cXHIvZywgICAnXFxcXHInKVxuICAgICAgICAgICAgLnJlcGxhY2UoL1tcXHgwMC1cXHgwN1xceDBCXFx4MEVcXHgwRl0vZywgZnVuY3Rpb24oY2gpIHsgcmV0dXJuICdcXFxceDAnICsgaGV4KGNoKTsgfSlcbiAgICAgICAgICAgIC5yZXBsYWNlKC9bXFx4MTAtXFx4MUZcXHg4MC1cXHhGRl0vZywgICAgZnVuY3Rpb24oY2gpIHsgcmV0dXJuICdcXFxceCcgICsgaGV4KGNoKTsgfSlcbiAgICAgICAgICAgIC5yZXBsYWNlKC9bXFx1MDE4MC1cXHUwRkZGXS9nLCAgICAgICAgIGZ1bmN0aW9uKGNoKSB7IHJldHVybiAnXFxcXHUwJyArIGhleChjaCk7IH0pXG4gICAgICAgICAgICAucmVwbGFjZSgvW1xcdTEwODAtXFx1RkZGRl0vZywgICAgICAgICBmdW5jdGlvbihjaCkgeyByZXR1cm4gJ1xcXFx1JyAgKyBoZXgoY2gpOyB9KTtcbiAgICAgICAgfVxuXG4gICAgICAgIHZhciBleHBlY3RlZERlc2NzID0gbmV3IEFycmF5KGV4cGVjdGVkLmxlbmd0aCksXG4gICAgICAgICAgICBleHBlY3RlZERlc2MsIGZvdW5kRGVzYywgaTtcblxuICAgICAgICBmb3IgKGkgPSAwOyBpIDwgZXhwZWN0ZWQubGVuZ3RoOyBpKyspIHtcbiAgICAgICAgICBleHBlY3RlZERlc2NzW2ldID0gZXhwZWN0ZWRbaV0uZGVzY3JpcHRpb247XG4gICAgICAgIH1cblxuICAgICAgICBleHBlY3RlZERlc2MgPSBleHBlY3RlZC5sZW5ndGggPiAxXG4gICAgICAgICAgPyBleHBlY3RlZERlc2NzLnNsaWNlKDAsIC0xKS5qb2luKFwiLCBcIilcbiAgICAgICAgICAgICAgKyBcIiBvciBcIlxuICAgICAgICAgICAgICArIGV4cGVjdGVkRGVzY3NbZXhwZWN0ZWQubGVuZ3RoIC0gMV1cbiAgICAgICAgICA6IGV4cGVjdGVkRGVzY3NbMF07XG5cbiAgICAgICAgZm91bmREZXNjID0gZm91bmQgPyBcIlxcXCJcIiArIHN0cmluZ0VzY2FwZShmb3VuZCkgKyBcIlxcXCJcIiA6IFwiZW5kIG9mIGlucHV0XCI7XG5cbiAgICAgICAgcmV0dXJuIFwiRXhwZWN0ZWQgXCIgKyBleHBlY3RlZERlc2MgKyBcIiBidXQgXCIgKyBmb3VuZERlc2MgKyBcIiBmb3VuZC5cIjtcbiAgICAgIH1cblxuICAgICAgdmFyIHBvc0RldGFpbHMgPSBwZWckY29tcHV0ZVBvc0RldGFpbHMocG9zKSxcbiAgICAgICAgICBmb3VuZCAgICAgID0gcG9zIDwgaW5wdXQubGVuZ3RoID8gaW5wdXQuY2hhckF0KHBvcykgOiBudWxsO1xuXG4gICAgICBpZiAoZXhwZWN0ZWQgIT09IG51bGwpIHtcbiAgICAgICAgY2xlYW51cEV4cGVjdGVkKGV4cGVjdGVkKTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIG5ldyBTeW50YXhFcnJvcihcbiAgICAgICAgbWVzc2FnZSAhPT0gbnVsbCA/IG1lc3NhZ2UgOiBidWlsZE1lc3NhZ2UoZXhwZWN0ZWQsIGZvdW5kKSxcbiAgICAgICAgZXhwZWN0ZWQsXG4gICAgICAgIGZvdW5kLFxuICAgICAgICBwb3MsXG4gICAgICAgIHBvc0RldGFpbHMubGluZSxcbiAgICAgICAgcG9zRGV0YWlscy5jb2x1bW5cbiAgICAgICk7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlc3RhcnQoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczM7XG5cbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIHMxID0gcGVnJHBhcnNlX18oKTtcbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMiA9IHBlZyRwYXJzZU9yRXhwcigpO1xuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGMyKHMyKTtcbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgczEgPSBbXTtcbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgczEgPSBwZWckYzQoKTtcbiAgICAgICAgfVxuICAgICAgICBzMCA9IHMxO1xuICAgICAgfVxuICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMCk7IH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZXdzKCkge1xuICAgICAgdmFyIHMwLCBzMTtcblxuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBpZiAocGVnJGM2LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgczAgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczAgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNyk7IH1cbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzUpOyB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VjYygpIHtcbiAgICAgIHZhciBzMCwgczE7XG5cbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgaWYgKHBlZyRjOS50ZXN0KGlucHV0LmNoYXJBdChwZWckY3VyclBvcykpKSB7XG4gICAgICAgIHMwID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMwID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzEwKTsgfVxuICAgICAgfVxuICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOCk7IH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZV9fKCkge1xuICAgICAgdmFyIHMwLCBzMTtcblxuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBzMCA9IFtdO1xuICAgICAgczEgPSBwZWckcGFyc2V3cygpO1xuICAgICAgd2hpbGUgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwLnB1c2goczEpO1xuICAgICAgICBzMSA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMxMSk7IH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZU9yRXhwcigpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyLCBzMywgczQsIHM1O1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgczEgPSBwZWckcGFyc2VBbmRFeHByKCk7XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBwZWckcGFyc2VfXygpO1xuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDEyNCkge1xuICAgICAgICAgICAgczMgPSBwZWckYzEyO1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczMgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzEzKTsgfVxuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHM0ID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgICAgIGlmIChzNCAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBzNSA9IHBlZyRwYXJzZU9yRXhwcigpO1xuICAgICAgICAgICAgICBpZiAoczUgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMSA9IHBlZyRjMTQoczEsIHM1KTtcbiAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJHBhcnNlQW5kRXhwcigpO1xuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlQW5kRXhwcigpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyLCBzMywgczQsIHM1O1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgczEgPSBwZWckcGFyc2VOb3RFeHByKCk7XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBwZWckcGFyc2VfXygpO1xuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDM4KSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRjMTU7XG4gICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMTYpOyB9XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczQgPSBwZWckcGFyc2VfXygpO1xuICAgICAgICAgICAgaWYgKHM0ICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHM1ID0gcGVnJHBhcnNlQW5kRXhwcigpO1xuICAgICAgICAgICAgICBpZiAoczUgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMSA9IHBlZyRjMTcoczEsIHM1KTtcbiAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIHMxID0gcGVnJHBhcnNlTm90RXhwcigpO1xuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRwYXJzZUFuZEV4cHIoKTtcbiAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczEgPSBwZWckYzE3KHMxLCBzMyk7XG4gICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMwID0gcGVnJHBhcnNlTm90RXhwcigpO1xuICAgICAgICB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VOb3RFeHByKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczIsIHMzO1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAzMykge1xuICAgICAgICBzMSA9IHBlZyRjMTg7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMxOSk7IH1cbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMiA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMzID0gcGVnJHBhcnNlTm90RXhwcigpO1xuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICBzMSA9IHBlZyRjMjAoczMpO1xuICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRwYXJzZUJpbmRpbmdFeHByKCk7XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VCaW5kaW5nRXhwcigpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyLCBzMywgczQsIHM1O1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSA0MCkge1xuICAgICAgICBzMSA9IHBlZyRjMjE7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMyMik7IH1cbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMiA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMzID0gcGVnJHBhcnNlT3JFeHByKCk7XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzNCA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICAgICAgICBpZiAoczQgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSA0MSkge1xuICAgICAgICAgICAgICAgIHM1ID0gcGVnJGMyMztcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHM1ID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMjQpOyB9XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgaWYgKHM1ICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckYzI1KHMzKTtcbiAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJHBhcnNlRXhwcigpO1xuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlRXhwcigpIHtcbiAgICAgIHZhciBzMDtcblxuICAgICAgczAgPSBwZWckcGFyc2VOdWxsYXJ5RXhwcigpO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJHBhcnNlVW5hcnlFeHByKCk7XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VOdWxsYXJ5RXhwcigpIHtcbiAgICAgIHZhciBzMCwgczE7XG5cbiAgICAgIHMwID0gcGVnJHBhcnNlQm9vbGVhbkxpdGVyYWwoKTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGMyNikge1xuICAgICAgICAgIHMxID0gcGVnJGMyNjtcbiAgICAgICAgICBwZWckY3VyclBvcyArPSAyO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMjcpOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgczEgPSBwZWckYzI4KCk7XG4gICAgICAgIH1cbiAgICAgICAgczAgPSBzMTtcbiAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGMyOSkge1xuICAgICAgICAgICAgczEgPSBwZWckYzI5O1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzMwKTsgfVxuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzMxKCk7XG4gICAgICAgICAgfVxuICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjMzIpIHtcbiAgICAgICAgICAgICAgczEgPSBwZWckYzMyO1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyArPSAyO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMzMpOyB9XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGMzNCgpO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGMzNSkge1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJGMzNTtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyArPSAyO1xuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMzYpOyB9XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckYzM3KCk7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZUJvb2xlYW5MaXRlcmFsKCkge1xuICAgICAgdmFyIHMwLCBzMTtcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDQpID09PSBwZWckYzM4KSB7XG4gICAgICAgIHMxID0gcGVnJGMzODtcbiAgICAgICAgcGVnJGN1cnJQb3MgKz0gNDtcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzM5KTsgfVxuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICBzMSA9IHBlZyRjNDAoKTtcbiAgICAgIH1cbiAgICAgIHMwID0gczE7XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgNSkgPT09IHBlZyRjNDEpIHtcbiAgICAgICAgICBzMSA9IHBlZyRjNDE7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgKz0gNTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzQyKTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgIHMxID0gcGVnJGM0MygpO1xuICAgICAgICB9XG4gICAgICAgIHMwID0gczE7XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VVbmFyeUV4cHIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczM7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGM0NCkge1xuICAgICAgICBzMSA9IHBlZyRjNDQ7XG4gICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM0NSk7IH1cbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMiA9IFtdO1xuICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMzID0gcGVnJHBhcnNlSW50ZWdlckxpdGVyYWwoKTtcbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzQ2KHMzKTtcbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjNDcpIHtcbiAgICAgICAgICBzMSA9IHBlZyRjNDc7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzQ4KTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjNDkoczMpO1xuICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzUwKSB7XG4gICAgICAgICAgICBzMSA9IHBlZyRjNTA7XG4gICAgICAgICAgICBwZWckY3VyclBvcyArPSAyO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNTEpOyB9XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNTIoczMpO1xuICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMykgPT09IHBlZyRjNTMpIHtcbiAgICAgICAgICAgICAgczEgPSBwZWckYzUzO1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyArPSAzO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNTQpOyB9XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzU1KHMzKTtcbiAgICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMykgPT09IHBlZyRjNTYpIHtcbiAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNTY7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMztcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzU3KTsgfVxuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNTgoczMpO1xuICAgICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzU5KSB7XG4gICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNTk7XG4gICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyArPSAyO1xuICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNjApOyB9XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNjEoczMpO1xuICAgICAgICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjNjIpIHtcbiAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzYyO1xuICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyArPSAyO1xuICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNjMpOyB9XG4gICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzY0KHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMykgPT09IHBlZyRjNjUpIHtcbiAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNjU7XG4gICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMztcbiAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzY2KTsgfVxuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNjcoczMpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDMpID09PSBwZWckYzY4KSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNjg7XG4gICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyArPSAzO1xuICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNjkpOyB9XG4gICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNzAoczMpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjNzEpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzcxO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyArPSAyO1xuICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNzIpOyB9XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzczKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM3MyhzMSk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZUludGVnZXJMaXRlcmFsKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczIsIHMzO1xuXG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBpZiAocGVnJGM3Ni50ZXN0KGlucHV0LmNoYXJBdChwZWckY3VyclBvcykpKSB7XG4gICAgICAgIHMxID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzc3KTsgfVxuICAgICAgfVxuICAgICAgaWYgKHMxID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJGM3NTtcbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMiA9IFtdO1xuICAgICAgICBpZiAocGVnJGM3OC50ZXN0KGlucHV0LmNoYXJBdChwZWckY3VyclBvcykpKSB7XG4gICAgICAgICAgczMgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczMgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM3OSk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgaWYgKHBlZyRjNzgudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICAgICAgICBzMyA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBzMyA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM3OSk7IH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgaWYgKHBlZyRjNzYudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICAgICAgczMgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczMgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzc3KTsgfVxuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczMgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMzID0gcGVnJGM3NTtcbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGM4MChzMik7XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNzQpOyB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczIsIHMzO1xuXG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDM0KSB7XG4gICAgICAgIHMxID0gcGVnJGM4MjtcbiAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzgzKTsgfVxuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gW107XG4gICAgICAgIHMzID0gcGVnJHBhcnNlRG91YmxlU3RyaW5nQ2hhcigpO1xuICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZURvdWJsZVN0cmluZ0NoYXIoKTtcbiAgICAgICAgfVxuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDM0KSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRjODI7XG4gICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjODMpOyB9XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICBzMSA9IHBlZyRjODQoczIpO1xuICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDM5KSB7XG4gICAgICAgICAgczEgPSBwZWckYzg1O1xuICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM4Nik7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgIHMzID0gcGVnJHBhcnNlU2luZ2xlU3RyaW5nQ2hhcigpO1xuICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVNpbmdsZVN0cmluZ0NoYXIoKTtcbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDM5KSB7XG4gICAgICAgICAgICAgIHMzID0gcGVnJGM4NTtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHMzID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzg2KTsgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjODQoczIpO1xuICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgIHMxID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICAgICAgczIgPSBwZWckcGFyc2VjYygpO1xuICAgICAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgICAgIGlmIChzMiA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczEgPSBwZWckYzg3O1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMxO1xuICAgICAgICAgICAgczEgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlVW5xdW90ZWRTdHJpbmdDaGFyKCk7XG4gICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VVbnF1b3RlZFN0cmluZ0NoYXIoKTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGM4NChzMik7XG4gICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgfVxuICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjODEpOyB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VEb3VibGVTdHJpbmdDaGFyKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczI7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBzMSA9IHBlZyRjdXJyUG9zO1xuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBpZiAocGVnJGM4OC50ZXN0KGlucHV0LmNoYXJBdChwZWckY3VyclBvcykpKSB7XG4gICAgICAgIHMyID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMyID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzg5KTsgfVxuICAgICAgfVxuICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICBpZiAoczIgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckYzg3O1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMTtcbiAgICAgICAgczEgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgaWYgKGlucHV0Lmxlbmd0aCA+IHBlZyRjdXJyUG9zKSB7XG4gICAgICAgICAgczIgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczIgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM5MCk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICBzMSA9IHBlZyRjOTEoczIpO1xuICAgICAgICAgIHMwID0gczE7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSA5Mikge1xuICAgICAgICAgIHMxID0gcGVnJGM5MjtcbiAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOTMpOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczIgPSBwZWckcGFyc2VFc2NhcGVTZXF1ZW5jZSgpO1xuICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICBzMSA9IHBlZyRjOTEoczIpO1xuICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VTaW5nbGVTdHJpbmdDaGFyKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczI7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBzMSA9IHBlZyRjdXJyUG9zO1xuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBpZiAocGVnJGM5NC50ZXN0KGlucHV0LmNoYXJBdChwZWckY3VyclBvcykpKSB7XG4gICAgICAgIHMyID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMyID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzk1KTsgfVxuICAgICAgfVxuICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICBpZiAoczIgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckYzg3O1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMTtcbiAgICAgICAgczEgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgaWYgKGlucHV0Lmxlbmd0aCA+IHBlZyRjdXJyUG9zKSB7XG4gICAgICAgICAgczIgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczIgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM5MCk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICBzMSA9IHBlZyRjOTEoczIpO1xuICAgICAgICAgIHMwID0gczE7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSA5Mikge1xuICAgICAgICAgIHMxID0gcGVnJGM5MjtcbiAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOTMpOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczIgPSBwZWckcGFyc2VFc2NhcGVTZXF1ZW5jZSgpO1xuICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICBzMSA9IHBlZyRjOTEoczIpO1xuICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VVbnF1b3RlZFN0cmluZ0NoYXIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMjtcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIHMxID0gcGVnJGN1cnJQb3M7XG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIHMyID0gcGVnJHBhcnNld3MoKTtcbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMyID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJGM4NztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczE7XG4gICAgICAgIHMxID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIGlmIChpbnB1dC5sZW5ndGggPiBwZWckY3VyclBvcykge1xuICAgICAgICAgIHMyID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMyID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOTApOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgczEgPSBwZWckYzkxKHMyKTtcbiAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlRXNjYXBlU2VxdWVuY2UoKSB7XG4gICAgICB2YXIgczAsIHMxO1xuXG4gICAgICBpZiAocGVnJGM5Ni50ZXN0KGlucHV0LmNoYXJBdChwZWckY3VyclBvcykpKSB7XG4gICAgICAgIHMwID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMwID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzk3KTsgfVxuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMTEwKSB7XG4gICAgICAgICAgczEgPSBwZWckYzk4O1xuICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM5OSk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICBzMSA9IHBlZyRjMTAwKCk7XG4gICAgICAgIH1cbiAgICAgICAgczAgPSBzMTtcbiAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDExNCkge1xuICAgICAgICAgICAgczEgPSBwZWckYzEwMTtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMxMDIpOyB9XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICBzMSA9IHBlZyRjMTAzKCk7XG4gICAgICAgICAgfVxuICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAxMTYpIHtcbiAgICAgICAgICAgICAgczEgPSBwZWckYzEwNDtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzEwNSk7IH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczEgPSBwZWckYzEwNigpO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuXG4gICAgZnVuY3Rpb24gb3IoZmlyc3QsIHNlY29uZCkge1xuICAgICAgICAvLyBBZGQgZXhwbGljaXQgZnVuY3Rpb24gbmFtZXMgdG8gZWFzZSBkZWJ1Z2dpbmcuXG4gICAgICAgIGZ1bmN0aW9uIG9yRmlsdGVyKCkge1xuICAgICAgICAgICAgcmV0dXJuIGZpcnN0LmFwcGx5KHRoaXMsIGFyZ3VtZW50cykgfHwgc2Vjb25kLmFwcGx5KHRoaXMsIGFyZ3VtZW50cyk7XG4gICAgICAgIH1cbiAgICAgICAgb3JGaWx0ZXIuZGVzYyA9IGZpcnN0LmRlc2MgKyBcIiBvciBcIiArIHNlY29uZC5kZXNjO1xuICAgICAgICByZXR1cm4gb3JGaWx0ZXI7XG4gICAgfVxuICAgIGZ1bmN0aW9uIGFuZChmaXJzdCwgc2Vjb25kKSB7XG4gICAgICAgIGZ1bmN0aW9uIGFuZEZpbHRlcigpIHtcbiAgICAgICAgICAgIHJldHVybiBmaXJzdC5hcHBseSh0aGlzLCBhcmd1bWVudHMpICYmIHNlY29uZC5hcHBseSh0aGlzLCBhcmd1bWVudHMpO1xuICAgICAgICB9XG4gICAgICAgIGFuZEZpbHRlci5kZXNjID0gZmlyc3QuZGVzYyArIFwiIGFuZCBcIiArIHNlY29uZC5kZXNjO1xuICAgICAgICByZXR1cm4gYW5kRmlsdGVyO1xuICAgIH1cbiAgICBmdW5jdGlvbiBub3QoZXhwcikge1xuICAgICAgICBmdW5jdGlvbiBub3RGaWx0ZXIoKSB7XG4gICAgICAgICAgICByZXR1cm4gIWV4cHIuYXBwbHkodGhpcywgYXJndW1lbnRzKTtcbiAgICAgICAgfVxuICAgICAgICBub3RGaWx0ZXIuZGVzYyA9IFwibm90IFwiICsgZXhwci5kZXNjO1xuICAgICAgICByZXR1cm4gbm90RmlsdGVyO1xuICAgIH1cbiAgICBmdW5jdGlvbiBiaW5kaW5nKGV4cHIpIHtcbiAgICAgICAgZnVuY3Rpb24gYmluZGluZ0ZpbHRlcigpIHtcbiAgICAgICAgICAgIHJldHVybiBleHByLmFwcGx5KHRoaXMsIGFyZ3VtZW50cyk7XG4gICAgICAgIH1cbiAgICAgICAgYmluZGluZ0ZpbHRlci5kZXNjID0gXCIoXCIgKyBleHByLmRlc2MgKyBcIilcIjtcbiAgICAgICAgcmV0dXJuIGJpbmRpbmdGaWx0ZXI7XG4gICAgfVxuICAgIGZ1bmN0aW9uIHRydWVGaWx0ZXIoZmxvdykge1xuICAgICAgICByZXR1cm4gdHJ1ZTtcbiAgICB9XG4gICAgdHJ1ZUZpbHRlci5kZXNjID0gXCJ0cnVlXCI7XG4gICAgZnVuY3Rpb24gZmFsc2VGaWx0ZXIoZmxvdykge1xuICAgICAgICByZXR1cm4gZmFsc2U7XG4gICAgfVxuICAgIGZhbHNlRmlsdGVyLmRlc2MgPSBcImZhbHNlXCI7XG5cbiAgICB2YXIgQVNTRVRfVFlQRVMgPSBbXG4gICAgICAgIG5ldyBSZWdFeHAoXCJ0ZXh0L2phdmFzY3JpcHRcIiksXG4gICAgICAgIG5ldyBSZWdFeHAoXCJhcHBsaWNhdGlvbi94LWphdmFzY3JpcHRcIiksXG4gICAgICAgIG5ldyBSZWdFeHAoXCJhcHBsaWNhdGlvbi9qYXZhc2NyaXB0XCIpLFxuICAgICAgICBuZXcgUmVnRXhwKFwidGV4dC9jc3NcIiksXG4gICAgICAgIG5ldyBSZWdFeHAoXCJpbWFnZS8uKlwiKSxcbiAgICAgICAgbmV3IFJlZ0V4cChcImFwcGxpY2F0aW9uL3gtc2hvY2t3YXZlLWZsYXNoXCIpXG4gICAgXTtcbiAgICBmdW5jdGlvbiBhc3NldEZpbHRlcihmbG93KSB7XG4gICAgICAgIGlmIChmbG93LnJlc3BvbnNlKSB7XG4gICAgICAgICAgICB2YXIgY3QgPSBSZXNwb25zZVV0aWxzLmdldENvbnRlbnRUeXBlKGZsb3cucmVzcG9uc2UpO1xuICAgICAgICAgICAgdmFyIGkgPSBBU1NFVF9UWVBFUy5sZW5ndGg7XG4gICAgICAgICAgICB3aGlsZSAoaS0tKSB7XG4gICAgICAgICAgICAgICAgaWYgKEFTU0VUX1RZUEVTW2ldLnRlc3QoY3QpKSB7XG4gICAgICAgICAgICAgICAgICAgIHJldHVybiB0cnVlO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgICByZXR1cm4gZmFsc2U7XG4gICAgfVxuICAgIGFzc2V0RmlsdGVyLmRlc2MgPSBcImlzIGFzc2V0XCI7XG4gICAgZnVuY3Rpb24gcmVzcG9uc2VDb2RlKGNvZGUpe1xuICAgICAgICBmdW5jdGlvbiByZXNwb25zZUNvZGVGaWx0ZXIoZmxvdyl7XG4gICAgICAgICAgICByZXR1cm4gZmxvdy5yZXNwb25zZSAmJiBmbG93LnJlc3BvbnNlLmNvZGUgPT09IGNvZGU7XG4gICAgICAgIH1cbiAgICAgICAgcmVzcG9uc2VDb2RlRmlsdGVyLmRlc2MgPSBcInJlc3AuIGNvZGUgaXMgXCIgKyBjb2RlO1xuICAgICAgICByZXR1cm4gcmVzcG9uc2VDb2RlRmlsdGVyO1xuICAgIH1cbiAgICBmdW5jdGlvbiBkb21haW4ocmVnZXgpe1xuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcbiAgICAgICAgZnVuY3Rpb24gZG9tYWluRmlsdGVyKGZsb3cpe1xuICAgICAgICAgICAgcmV0dXJuIGZsb3cucmVxdWVzdCAmJiByZWdleC50ZXN0KGZsb3cucmVxdWVzdC5ob3N0KTtcbiAgICAgICAgfVxuICAgICAgICBkb21haW5GaWx0ZXIuZGVzYyA9IFwiZG9tYWluIG1hdGNoZXMgXCIgKyByZWdleDtcbiAgICAgICAgcmV0dXJuIGRvbWFpbkZpbHRlcjtcbiAgICB9XG4gICAgZnVuY3Rpb24gZXJyb3JGaWx0ZXIoZmxvdyl7XG4gICAgICAgIHJldHVybiAhIWZsb3cuZXJyb3I7XG4gICAgfVxuICAgIGVycm9yRmlsdGVyLmRlc2MgPSBcImhhcyBlcnJvclwiO1xuICAgIGZ1bmN0aW9uIGhlYWRlcihyZWdleCl7XG4gICAgICAgIHJlZ2V4ID0gbmV3IFJlZ0V4cChyZWdleCwgXCJpXCIpO1xuICAgICAgICBmdW5jdGlvbiBoZWFkZXJGaWx0ZXIoZmxvdyl7XG4gICAgICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgICAgIChmbG93LnJlcXVlc3QgJiYgUmVxdWVzdFV0aWxzLm1hdGNoX2hlYWRlcihmbG93LnJlcXVlc3QsIHJlZ2V4KSlcbiAgICAgICAgICAgICAgICB8fFxuICAgICAgICAgICAgICAgIChmbG93LnJlc3BvbnNlICYmIFJlc3BvbnNlVXRpbHMubWF0Y2hfaGVhZGVyKGZsb3cucmVzcG9uc2UsIHJlZ2V4KSlcbiAgICAgICAgICAgICk7XG4gICAgICAgIH1cbiAgICAgICAgaGVhZGVyRmlsdGVyLmRlc2MgPSBcImhlYWRlciBtYXRjaGVzIFwiICsgcmVnZXg7XG4gICAgICAgIHJldHVybiBoZWFkZXJGaWx0ZXI7XG4gICAgfVxuICAgIGZ1bmN0aW9uIHJlcXVlc3RIZWFkZXIocmVnZXgpe1xuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcbiAgICAgICAgZnVuY3Rpb24gcmVxdWVzdEhlYWRlckZpbHRlcihmbG93KXtcbiAgICAgICAgICAgIHJldHVybiAoZmxvdy5yZXF1ZXN0ICYmIFJlcXVlc3RVdGlscy5tYXRjaF9oZWFkZXIoZmxvdy5yZXF1ZXN0LCByZWdleCkpO1xuICAgICAgICB9XG4gICAgICAgIHJlcXVlc3RIZWFkZXJGaWx0ZXIuZGVzYyA9IFwicmVxLiBoZWFkZXIgbWF0Y2hlcyBcIiArIHJlZ2V4O1xuICAgICAgICByZXR1cm4gcmVxdWVzdEhlYWRlckZpbHRlcjtcbiAgICB9XG4gICAgZnVuY3Rpb24gcmVzcG9uc2VIZWFkZXIocmVnZXgpe1xuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcbiAgICAgICAgZnVuY3Rpb24gcmVzcG9uc2VIZWFkZXJGaWx0ZXIoZmxvdyl7XG4gICAgICAgICAgICByZXR1cm4gKGZsb3cucmVzcG9uc2UgJiYgUmVzcG9uc2VVdGlscy5tYXRjaF9oZWFkZXIoZmxvdy5yZXNwb25zZSwgcmVnZXgpKTtcbiAgICAgICAgfVxuICAgICAgICByZXNwb25zZUhlYWRlckZpbHRlci5kZXNjID0gXCJyZXNwLiBoZWFkZXIgbWF0Y2hlcyBcIiArIHJlZ2V4O1xuICAgICAgICByZXR1cm4gcmVzcG9uc2VIZWFkZXJGaWx0ZXI7XG4gICAgfVxuICAgIGZ1bmN0aW9uIG1ldGhvZChyZWdleCl7XG4gICAgICAgIHJlZ2V4ID0gbmV3IFJlZ0V4cChyZWdleCwgXCJpXCIpO1xuICAgICAgICBmdW5jdGlvbiBtZXRob2RGaWx0ZXIoZmxvdyl7XG4gICAgICAgICAgICByZXR1cm4gZmxvdy5yZXF1ZXN0ICYmIHJlZ2V4LnRlc3QoZmxvdy5yZXF1ZXN0Lm1ldGhvZCk7XG4gICAgICAgIH1cbiAgICAgICAgbWV0aG9kRmlsdGVyLmRlc2MgPSBcIm1ldGhvZCBtYXRjaGVzIFwiICsgcmVnZXg7XG4gICAgICAgIHJldHVybiBtZXRob2RGaWx0ZXI7XG4gICAgfVxuICAgIGZ1bmN0aW9uIG5vUmVzcG9uc2VGaWx0ZXIoZmxvdyl7XG4gICAgICAgIHJldHVybiBmbG93LnJlcXVlc3QgJiYgIWZsb3cucmVzcG9uc2U7XG4gICAgfVxuICAgIG5vUmVzcG9uc2VGaWx0ZXIuZGVzYyA9IFwiaGFzIG5vIHJlc3BvbnNlXCI7XG4gICAgZnVuY3Rpb24gcmVzcG9uc2VGaWx0ZXIoZmxvdyl7XG4gICAgICAgIHJldHVybiAhIWZsb3cucmVzcG9uc2U7XG4gICAgfVxuICAgIHJlc3BvbnNlRmlsdGVyLmRlc2MgPSBcImhhcyByZXNwb25zZVwiO1xuXG4gICAgZnVuY3Rpb24gY29udGVudFR5cGUocmVnZXgpe1xuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcbiAgICAgICAgZnVuY3Rpb24gY29udGVudFR5cGVGaWx0ZXIoZmxvdyl7XG4gICAgICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgICAgIChmbG93LnJlcXVlc3QgJiYgcmVnZXgudGVzdChSZXF1ZXN0VXRpbHMuZ2V0Q29udGVudFR5cGUoZmxvdy5yZXF1ZXN0KSkpXG4gICAgICAgICAgICAgICAgfHxcbiAgICAgICAgICAgICAgICAoZmxvdy5yZXNwb25zZSAmJiByZWdleC50ZXN0KFJlc3BvbnNlVXRpbHMuZ2V0Q29udGVudFR5cGUoZmxvdy5yZXNwb25zZSkpKVxuICAgICAgICAgICAgKTtcbiAgICAgICAgfVxuICAgICAgICBjb250ZW50VHlwZUZpbHRlci5kZXNjID0gXCJjb250ZW50IHR5cGUgbWF0Y2hlcyBcIiArIHJlZ2V4O1xuICAgICAgICByZXR1cm4gY29udGVudFR5cGVGaWx0ZXI7XG4gICAgfVxuICAgIGZ1bmN0aW9uIHJlcXVlc3RDb250ZW50VHlwZShyZWdleCl7XG4gICAgICAgIHJlZ2V4ID0gbmV3IFJlZ0V4cChyZWdleCwgXCJpXCIpO1xuICAgICAgICBmdW5jdGlvbiByZXF1ZXN0Q29udGVudFR5cGVGaWx0ZXIoZmxvdyl7XG4gICAgICAgICAgICByZXR1cm4gZmxvdy5yZXF1ZXN0ICYmIHJlZ2V4LnRlc3QoUmVxdWVzdFV0aWxzLmdldENvbnRlbnRUeXBlKGZsb3cucmVxdWVzdCkpO1xuICAgICAgICB9XG4gICAgICAgIHJlcXVlc3RDb250ZW50VHlwZUZpbHRlci5kZXNjID0gXCJyZXEuIGNvbnRlbnQgdHlwZSBtYXRjaGVzIFwiICsgcmVnZXg7XG4gICAgICAgIHJldHVybiByZXF1ZXN0Q29udGVudFR5cGVGaWx0ZXI7XG4gICAgfVxuICAgIGZ1bmN0aW9uIHJlc3BvbnNlQ29udGVudFR5cGUocmVnZXgpe1xuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcbiAgICAgICAgZnVuY3Rpb24gcmVzcG9uc2VDb250ZW50VHlwZUZpbHRlcihmbG93KXtcbiAgICAgICAgICAgIHJldHVybiBmbG93LnJlc3BvbnNlICYmIHJlZ2V4LnRlc3QoUmVzcG9uc2VVdGlscy5nZXRDb250ZW50VHlwZShmbG93LnJlc3BvbnNlKSk7XG4gICAgICAgIH1cbiAgICAgICAgcmVzcG9uc2VDb250ZW50VHlwZUZpbHRlci5kZXNjID0gXCJyZXNwLiBjb250ZW50IHR5cGUgbWF0Y2hlcyBcIiArIHJlZ2V4O1xuICAgICAgICByZXR1cm4gcmVzcG9uc2VDb250ZW50VHlwZUZpbHRlcjtcbiAgICB9XG4gICAgZnVuY3Rpb24gdXJsKHJlZ2V4KXtcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XG4gICAgICAgIGZ1bmN0aW9uIHVybEZpbHRlcihmbG93KXtcbiAgICAgICAgICAgIHJldHVybiBmbG93LnJlcXVlc3QgJiYgcmVnZXgudGVzdChSZXF1ZXN0VXRpbHMucHJldHR5X3VybChmbG93LnJlcXVlc3QpKTtcbiAgICAgICAgfVxuICAgICAgICB1cmxGaWx0ZXIuZGVzYyA9IFwidXJsIG1hdGNoZXMgXCIgKyByZWdleDtcbiAgICAgICAgcmV0dXJuIHVybEZpbHRlcjtcbiAgICB9XG5cblxuICAgIHBlZyRyZXN1bHQgPSBwZWckc3RhcnRSdWxlRnVuY3Rpb24oKTtcblxuICAgIGlmIChwZWckcmVzdWx0ICE9PSBwZWckRkFJTEVEICYmIHBlZyRjdXJyUG9zID09PSBpbnB1dC5sZW5ndGgpIHtcbiAgICAgIHJldHVybiBwZWckcmVzdWx0O1xuICAgIH0gZWxzZSB7XG4gICAgICBpZiAocGVnJHJlc3VsdCAhPT0gcGVnJEZBSUxFRCAmJiBwZWckY3VyclBvcyA8IGlucHV0Lmxlbmd0aCkge1xuICAgICAgICBwZWckZmFpbCh7IHR5cGU6IFwiZW5kXCIsIGRlc2NyaXB0aW9uOiBcImVuZCBvZiBpbnB1dFwiIH0pO1xuICAgICAgfVxuXG4gICAgICB0aHJvdyBwZWckYnVpbGRFeGNlcHRpb24obnVsbCwgcGVnJG1heEZhaWxFeHBlY3RlZCwgcGVnJG1heEZhaWxQb3MpO1xuICAgIH1cbiAgfVxuXG4gIHJldHVybiB7XG4gICAgU3ludGF4RXJyb3I6IFN5bnRheEVycm9yLFxuICAgIHBhcnNlOiAgICAgICBwYXJzZVxuICB9O1xufSkoKTtcbi8qIGpzaGludCBpZ25vcmU6ZW5kICovXG5cbm1vZHVsZS5leHBvcnRzID0gRmlsdDtcbiIsInZhciBfID0gcmVxdWlyZShcImxvZGFzaFwiKTtcblxudmFyIF9NZXNzYWdlVXRpbHMgPSB7XG4gICAgZ2V0Q29udGVudFR5cGU6IGZ1bmN0aW9uIChtZXNzYWdlKSB7XG4gICAgICAgIHJldHVybiB0aGlzLmdldF9maXJzdF9oZWFkZXIobWVzc2FnZSwgL15Db250ZW50LVR5cGUkL2kpO1xuICAgIH0sXG4gICAgZ2V0X2ZpcnN0X2hlYWRlcjogZnVuY3Rpb24gKG1lc3NhZ2UsIHJlZ2V4KSB7XG4gICAgICAgIC8vRklYTUU6IENhY2hlIEludmFsaWRhdGlvbi5cbiAgICAgICAgaWYgKCFtZXNzYWdlLl9oZWFkZXJMb29rdXBzKVxuICAgICAgICAgICAgT2JqZWN0LmRlZmluZVByb3BlcnR5KG1lc3NhZ2UsIFwiX2hlYWRlckxvb2t1cHNcIiwge1xuICAgICAgICAgICAgICAgIHZhbHVlOiB7fSxcbiAgICAgICAgICAgICAgICBjb25maWd1cmFibGU6IGZhbHNlLFxuICAgICAgICAgICAgICAgIGVudW1lcmFibGU6IGZhbHNlLFxuICAgICAgICAgICAgICAgIHdyaXRhYmxlOiBmYWxzZVxuICAgICAgICAgICAgfSk7XG4gICAgICAgIGlmICghKHJlZ2V4IGluIG1lc3NhZ2UuX2hlYWRlckxvb2t1cHMpKSB7XG4gICAgICAgICAgICB2YXIgaGVhZGVyO1xuICAgICAgICAgICAgZm9yICh2YXIgaSA9IDA7IGkgPCBtZXNzYWdlLmhlYWRlcnMubGVuZ3RoOyBpKyspIHtcbiAgICAgICAgICAgICAgICBpZiAoISFtZXNzYWdlLmhlYWRlcnNbaV1bMF0ubWF0Y2gocmVnZXgpKSB7XG4gICAgICAgICAgICAgICAgICAgIGhlYWRlciA9IG1lc3NhZ2UuaGVhZGVyc1tpXTtcbiAgICAgICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgICAgbWVzc2FnZS5faGVhZGVyTG9va3Vwc1tyZWdleF0gPSBoZWFkZXIgPyBoZWFkZXJbMV0gOiB1bmRlZmluZWQ7XG4gICAgICAgIH1cbiAgICAgICAgcmV0dXJuIG1lc3NhZ2UuX2hlYWRlckxvb2t1cHNbcmVnZXhdO1xuICAgIH0sXG4gICAgbWF0Y2hfaGVhZGVyOiBmdW5jdGlvbiAobWVzc2FnZSwgcmVnZXgpIHtcbiAgICAgICAgdmFyIGhlYWRlcnMgPSBtZXNzYWdlLmhlYWRlcnM7XG4gICAgICAgIHZhciBpID0gaGVhZGVycy5sZW5ndGg7XG4gICAgICAgIHdoaWxlIChpLS0pIHtcbiAgICAgICAgICAgIGlmIChyZWdleC50ZXN0KGhlYWRlcnNbaV0uam9pbihcIiBcIikpKSB7XG4gICAgICAgICAgICAgICAgcmV0dXJuIGhlYWRlcnNbaV07XG4gICAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgICAgcmV0dXJuIGZhbHNlO1xuICAgIH1cbn07XG5cbnZhciBkZWZhdWx0UG9ydHMgPSB7XG4gICAgXCJodHRwXCI6IDgwLFxuICAgIFwiaHR0cHNcIjogNDQzXG59O1xuXG52YXIgUmVxdWVzdFV0aWxzID0gXy5leHRlbmQoX01lc3NhZ2VVdGlscywge1xuICAgIHByZXR0eV9ob3N0OiBmdW5jdGlvbiAocmVxdWVzdCkge1xuICAgICAgICAvL0ZJWE1FOiBBZGQgaG9zdGhlYWRlclxuICAgICAgICByZXR1cm4gcmVxdWVzdC5ob3N0O1xuICAgIH0sXG4gICAgcHJldHR5X3VybDogZnVuY3Rpb24gKHJlcXVlc3QpIHtcbiAgICAgICAgdmFyIHBvcnQgPSBcIlwiO1xuICAgICAgICBpZiAoZGVmYXVsdFBvcnRzW3JlcXVlc3Quc2NoZW1lXSAhPT0gcmVxdWVzdC5wb3J0KSB7XG4gICAgICAgICAgICBwb3J0ID0gXCI6XCIgKyByZXF1ZXN0LnBvcnQ7XG4gICAgICAgIH1cbiAgICAgICAgcmV0dXJuIHJlcXVlc3Quc2NoZW1lICsgXCI6Ly9cIiArIHRoaXMucHJldHR5X2hvc3QocmVxdWVzdCkgKyBwb3J0ICsgcmVxdWVzdC5wYXRoO1xuICAgIH1cbn0pO1xuXG52YXIgUmVzcG9uc2VVdGlscyA9IF8uZXh0ZW5kKF9NZXNzYWdlVXRpbHMsIHt9KTtcblxuXG5tb2R1bGUuZXhwb3J0cyA9IHtcbiAgICBSZXNwb25zZVV0aWxzOiBSZXNwb25zZVV0aWxzLFxuICAgIFJlcXVlc3RVdGlsczogUmVxdWVzdFV0aWxzXG5cbn0iLCJcbnZhciBfID0gcmVxdWlyZShcImxvZGFzaFwiKTtcbnZhciAkID0gcmVxdWlyZShcImpxdWVyeVwiKTtcblxudmFyIHV0aWxzID0gcmVxdWlyZShcIi4uL3V0aWxzLmpzXCIpO1xudmFyIGFjdGlvbnMgPSByZXF1aXJlKFwiLi4vYWN0aW9ucy5qc1wiKTtcbnZhciBkaXNwYXRjaGVyID0gcmVxdWlyZShcIi4uL2Rpc3BhdGNoZXIuanNcIik7XG5cblxuZnVuY3Rpb24gTGlzdFN0b3JlKCkge1xuICAgIHV0aWxzLkV2ZW50RW1pdHRlci5jYWxsKHRoaXMpO1xuICAgIHRoaXMucmVzZXQoKTtcbn1cbl8uZXh0ZW5kKExpc3RTdG9yZS5wcm90b3R5cGUsIHV0aWxzLkV2ZW50RW1pdHRlci5wcm90b3R5cGUsIHtcbiAgICBhZGQ6IGZ1bmN0aW9uIChlbGVtKSB7XG4gICAgICAgIGlmIChlbGVtLmlkIGluIHRoaXMuX3Bvc19tYXApIHtcbiAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgfVxuICAgICAgICB0aGlzLl9wb3NfbWFwW2VsZW0uaWRdID0gdGhpcy5saXN0Lmxlbmd0aDtcbiAgICAgICAgdGhpcy5saXN0LnB1c2goZWxlbSk7XG4gICAgICAgIHRoaXMuZW1pdChcImFkZFwiLCBlbGVtKTtcbiAgICB9LFxuICAgIHVwZGF0ZTogZnVuY3Rpb24gKGVsZW0pIHtcbiAgICAgICAgaWYgKCEoZWxlbS5pZCBpbiB0aGlzLl9wb3NfbWFwKSkge1xuICAgICAgICAgICAgcmV0dXJuO1xuICAgICAgICB9XG4gICAgICAgIHRoaXMubGlzdFt0aGlzLl9wb3NfbWFwW2VsZW0uaWRdXSA9IGVsZW07XG4gICAgICAgIHRoaXMuZW1pdChcInVwZGF0ZVwiLCBlbGVtKTtcbiAgICB9LFxuICAgIHJlbW92ZTogZnVuY3Rpb24gKGVsZW1faWQpIHtcbiAgICAgICAgaWYgKCEoZWxlbV9pZCBpbiB0aGlzLl9wb3NfbWFwKSkge1xuICAgICAgICAgICAgcmV0dXJuO1xuICAgICAgICB9XG4gICAgICAgIHRoaXMubGlzdC5zcGxpY2UodGhpcy5fcG9zX21hcFtlbGVtX2lkXSwgMSk7XG4gICAgICAgIHRoaXMuX2J1aWxkX21hcCgpO1xuICAgICAgICB0aGlzLmVtaXQoXCJyZW1vdmVcIiwgZWxlbV9pZCk7XG4gICAgfSxcbiAgICByZXNldDogZnVuY3Rpb24gKGVsZW1zKSB7XG4gICAgICAgIHRoaXMubGlzdCA9IGVsZW1zIHx8IFtdO1xuICAgICAgICB0aGlzLl9idWlsZF9tYXAoKTtcbiAgICAgICAgdGhpcy5lbWl0KFwicmVjYWxjdWxhdGVcIik7XG4gICAgfSxcbiAgICBfYnVpbGRfbWFwOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuX3Bvc19tYXAgPSB7fTtcbiAgICAgICAgZm9yICh2YXIgaSA9IDA7IGkgPCB0aGlzLmxpc3QubGVuZ3RoOyBpKyspIHtcbiAgICAgICAgICAgIHZhciBlbGVtID0gdGhpcy5saXN0W2ldO1xuICAgICAgICAgICAgdGhpcy5fcG9zX21hcFtlbGVtLmlkXSA9IGk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGdldDogZnVuY3Rpb24gKGVsZW1faWQpIHtcbiAgICAgICAgcmV0dXJuIHRoaXMubGlzdFt0aGlzLl9wb3NfbWFwW2VsZW1faWRdXTtcbiAgICB9LFxuICAgIGluZGV4OiBmdW5jdGlvbiAoZWxlbV9pZCkge1xuICAgICAgICByZXR1cm4gdGhpcy5fcG9zX21hcFtlbGVtX2lkXTtcbiAgICB9XG59KTtcblxuXG5mdW5jdGlvbiBEaWN0U3RvcmUoKSB7XG4gICAgdXRpbHMuRXZlbnRFbWl0dGVyLmNhbGwodGhpcyk7XG4gICAgdGhpcy5yZXNldCgpO1xufVxuXy5leHRlbmQoRGljdFN0b3JlLnByb3RvdHlwZSwgdXRpbHMuRXZlbnRFbWl0dGVyLnByb3RvdHlwZSwge1xuICAgIHVwZGF0ZTogZnVuY3Rpb24gKGRpY3QpIHtcbiAgICAgICAgXy5tZXJnZSh0aGlzLmRpY3QsIGRpY3QpO1xuICAgICAgICB0aGlzLmVtaXQoXCJyZWNhbGN1bGF0ZVwiKTtcbiAgICB9LFxuICAgIHJlc2V0OiBmdW5jdGlvbiAoZGljdCkge1xuICAgICAgICB0aGlzLmRpY3QgPSBkaWN0IHx8IHt9O1xuICAgICAgICB0aGlzLmVtaXQoXCJyZWNhbGN1bGF0ZVwiKTtcbiAgICB9XG59KTtcblxuZnVuY3Rpb24gTGl2ZVN0b3JlTWl4aW4odHlwZSkge1xuICAgIHRoaXMudHlwZSA9IHR5cGU7XG5cbiAgICB0aGlzLl91cGRhdGVzX2JlZm9yZV9mZXRjaCA9IHVuZGVmaW5lZDtcbiAgICB0aGlzLl9mZXRjaHhociA9IGZhbHNlO1xuXG4gICAgdGhpcy5oYW5kbGUgPSB0aGlzLmhhbmRsZS5iaW5kKHRoaXMpO1xuICAgIGRpc3BhdGNoZXIuQXBwRGlzcGF0Y2hlci5yZWdpc3Rlcih0aGlzLmhhbmRsZSk7XG5cbiAgICAvLyBBdm9pZCBkb3VibGUtZmV0Y2ggb24gc3RhcnR1cC5cbiAgICBpZiAoISh3aW5kb3cud3MgJiYgd2luZG93LndzLnJlYWR5U3RhdGUgPT09IFdlYlNvY2tldC5DT05ORUNUSU5HKSkge1xuICAgICAgICB0aGlzLmZldGNoKCk7XG4gICAgfVxufVxuXy5leHRlbmQoTGl2ZVN0b3JlTWl4aW4ucHJvdG90eXBlLCB7XG4gICAgaGFuZGxlOiBmdW5jdGlvbiAoZXZlbnQpIHtcbiAgICAgICAgaWYgKGV2ZW50LnR5cGUgPT09IGFjdGlvbnMuQWN0aW9uVHlwZXMuQ09OTkVDVElPTl9PUEVOKSB7XG4gICAgICAgICAgICByZXR1cm4gdGhpcy5mZXRjaCgpO1xuICAgICAgICB9XG4gICAgICAgIGlmIChldmVudC50eXBlID09PSB0aGlzLnR5cGUpIHtcbiAgICAgICAgICAgIGlmIChldmVudC5jbWQgPT09IGFjdGlvbnMuU3RvcmVDbWRzLlJFU0VUKSB7XG4gICAgICAgICAgICAgICAgdGhpcy5mZXRjaChldmVudC5kYXRhKTtcbiAgICAgICAgICAgIH0gZWxzZSBpZiAodGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2gpIHtcbiAgICAgICAgICAgICAgICBjb25zb2xlLmxvZyhcImRlZmVyIHVwZGF0ZVwiLCBldmVudCk7XG4gICAgICAgICAgICAgICAgdGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2gucHVzaChldmVudCk7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHRoaXNbZXZlbnQuY21kXShldmVudC5kYXRhKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgIH0sXG4gICAgY2xvc2U6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgZGlzcGF0Y2hlci5BcHBEaXNwYXRjaGVyLnVucmVnaXN0ZXIodGhpcy5oYW5kbGUpO1xuICAgIH0sXG4gICAgZmV0Y2g6IGZ1bmN0aW9uIChkYXRhKSB7XG4gICAgICAgIGNvbnNvbGUubG9nKFwiZmV0Y2ggXCIgKyB0aGlzLnR5cGUpO1xuICAgICAgICBpZiAodGhpcy5fZmV0Y2h4aHIpIHtcbiAgICAgICAgICAgIHRoaXMuX2ZldGNoeGhyLmFib3J0KCk7XG4gICAgICAgIH1cbiAgICAgICAgdGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2ggPSBbXTsgLy8gKEpTOiBlbXB0eSBhcnJheSBpcyB0cnVlKVxuICAgICAgICBpZiAoZGF0YSkge1xuICAgICAgICAgICAgdGhpcy5oYW5kbGVfZmV0Y2goZGF0YSk7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICB0aGlzLl9mZXRjaHhociA9ICQuZ2V0SlNPTihcIi9cIiArIHRoaXMudHlwZSlcbiAgICAgICAgICAgICAgICAuZG9uZShmdW5jdGlvbiAobWVzc2FnZSkge1xuICAgICAgICAgICAgICAgICAgICB0aGlzLmhhbmRsZV9mZXRjaChtZXNzYWdlLmRhdGEpO1xuICAgICAgICAgICAgICAgIH0uYmluZCh0aGlzKSlcbiAgICAgICAgICAgICAgICAuZmFpbChmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICAgICAgICAgIEV2ZW50TG9nQWN0aW9ucy5hZGRfZXZlbnQoXCJDb3VsZCBub3QgZmV0Y2ggXCIgKyB0aGlzLnR5cGUpO1xuICAgICAgICAgICAgICAgIH0uYmluZCh0aGlzKSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGhhbmRsZV9mZXRjaDogZnVuY3Rpb24gKGRhdGEpIHtcbiAgICAgICAgdGhpcy5fZmV0Y2h4aHIgPSBmYWxzZTtcbiAgICAgICAgY29uc29sZS5sb2codGhpcy50eXBlICsgXCIgZmV0Y2hlZC5cIiwgdGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2gpO1xuICAgICAgICB0aGlzLnJlc2V0KGRhdGEpO1xuICAgICAgICB2YXIgdXBkYXRlcyA9IHRoaXMuX3VwZGF0ZXNfYmVmb3JlX2ZldGNoO1xuICAgICAgICB0aGlzLl91cGRhdGVzX2JlZm9yZV9mZXRjaCA9IGZhbHNlO1xuICAgICAgICBmb3IgKHZhciBpID0gMDsgaSA8IHVwZGF0ZXMubGVuZ3RoOyBpKyspIHtcbiAgICAgICAgICAgIHRoaXMuaGFuZGxlKHVwZGF0ZXNbaV0pO1xuICAgICAgICB9XG4gICAgfSxcbn0pO1xuXG5mdW5jdGlvbiBMaXZlTGlzdFN0b3JlKHR5cGUpIHtcbiAgICBMaXN0U3RvcmUuY2FsbCh0aGlzKTtcbiAgICBMaXZlU3RvcmVNaXhpbi5jYWxsKHRoaXMsIHR5cGUpO1xufVxuXy5leHRlbmQoTGl2ZUxpc3RTdG9yZS5wcm90b3R5cGUsIExpc3RTdG9yZS5wcm90b3R5cGUsIExpdmVTdG9yZU1peGluLnByb3RvdHlwZSk7XG5cbmZ1bmN0aW9uIExpdmVEaWN0U3RvcmUodHlwZSkge1xuICAgIERpY3RTdG9yZS5jYWxsKHRoaXMpO1xuICAgIExpdmVTdG9yZU1peGluLmNhbGwodGhpcywgdHlwZSk7XG59XG5fLmV4dGVuZChMaXZlRGljdFN0b3JlLnByb3RvdHlwZSwgRGljdFN0b3JlLnByb3RvdHlwZSwgTGl2ZVN0b3JlTWl4aW4ucHJvdG90eXBlKTtcblxuXG5mdW5jdGlvbiBGbG93U3RvcmUoKSB7XG4gICAgcmV0dXJuIG5ldyBMaXZlTGlzdFN0b3JlKGFjdGlvbnMuQWN0aW9uVHlwZXMuRkxPV19TVE9SRSk7XG59XG5cbmZ1bmN0aW9uIFNldHRpbmdzU3RvcmUoKSB7XG4gICAgcmV0dXJuIG5ldyBMaXZlRGljdFN0b3JlKGFjdGlvbnMuQWN0aW9uVHlwZXMuU0VUVElOR1NfU1RPUkUpO1xufVxuXG5mdW5jdGlvbiBFdmVudExvZ1N0b3JlKCkge1xuICAgIExpdmVMaXN0U3RvcmUuY2FsbCh0aGlzLCBhY3Rpb25zLkFjdGlvblR5cGVzLkVWRU5UX1NUT1JFKTtcbn1cbl8uZXh0ZW5kKEV2ZW50TG9nU3RvcmUucHJvdG90eXBlLCBMaXZlTGlzdFN0b3JlLnByb3RvdHlwZSwge1xuICAgIGZldGNoOiBmdW5jdGlvbigpe1xuICAgICAgICBMaXZlTGlzdFN0b3JlLnByb3RvdHlwZS5mZXRjaC5hcHBseSh0aGlzLCBhcmd1bWVudHMpO1xuXG4gICAgICAgIC8vIE1ha2Ugc3VyZSB0byBkaXNwbGF5IHVwZGF0ZXMgZXZlbiBpZiBmZXRjaGluZyBhbGwgZXZlbnRzIGZhaWxlZC5cbiAgICAgICAgLy8gVGhpcyB3YXksIHdlIGNhbiBzZW5kIFwiZmV0Y2ggZmFpbGVkXCIgbG9nIG1lc3NhZ2VzIHRvIHRoZSBsb2cuXG4gICAgICAgIGlmKHRoaXMuX2ZldGNoeGhyKXtcbiAgICAgICAgICAgIHRoaXMuX2ZldGNoeGhyLmZhaWwoZnVuY3Rpb24oKXtcbiAgICAgICAgICAgICAgICB0aGlzLmhhbmRsZV9mZXRjaChudWxsKTtcbiAgICAgICAgICAgIH0uYmluZCh0aGlzKSk7XG4gICAgICAgIH1cbiAgICB9XG59KTtcblxuXG5tb2R1bGUuZXhwb3J0cyA9IHtcbiAgICBFdmVudExvZ1N0b3JlOiBFdmVudExvZ1N0b3JlLFxuICAgIFNldHRpbmdzU3RvcmU6IFNldHRpbmdzU3RvcmUsXG4gICAgRmxvd1N0b3JlOiBGbG93U3RvcmVcbn07IiwidmFyIF8gPSByZXF1aXJlKFwibG9kYXNoXCIpO1xuXG52YXIgdXRpbHMgPSByZXF1aXJlKFwiLi4vdXRpbHMuanNcIik7XG5cbmZ1bmN0aW9uIFNvcnRCeVN0b3JlT3JkZXIoZWxlbSkge1xuICAgIHJldHVybiB0aGlzLnN0b3JlLmluZGV4KGVsZW0uaWQpO1xufVxuXG52YXIgZGVmYXVsdF9zb3J0ID0gU29ydEJ5U3RvcmVPcmRlcjtcbnZhciBkZWZhdWx0X2ZpbHQgPSBmdW5jdGlvbihlbGVtKXtcbiAgICByZXR1cm4gdHJ1ZTtcbn07XG5cbmZ1bmN0aW9uIFN0b3JlVmlldyhzdG9yZSwgZmlsdCwgc29ydGZ1bikge1xuICAgIHV0aWxzLkV2ZW50RW1pdHRlci5jYWxsKHRoaXMpO1xuICAgIGZpbHQgPSBmaWx0IHx8IGRlZmF1bHRfZmlsdDtcbiAgICBzb3J0ZnVuID0gc29ydGZ1biB8fCBkZWZhdWx0X3NvcnQ7XG5cbiAgICB0aGlzLnN0b3JlID0gc3RvcmU7XG5cbiAgICB0aGlzLmFkZCA9IHRoaXMuYWRkLmJpbmQodGhpcyk7XG4gICAgdGhpcy51cGRhdGUgPSB0aGlzLnVwZGF0ZS5iaW5kKHRoaXMpO1xuICAgIHRoaXMucmVtb3ZlID0gdGhpcy5yZW1vdmUuYmluZCh0aGlzKTtcbiAgICB0aGlzLnJlY2FsY3VsYXRlID0gdGhpcy5yZWNhbGN1bGF0ZS5iaW5kKHRoaXMpO1xuICAgIHRoaXMuc3RvcmUuYWRkTGlzdGVuZXIoXCJhZGRcIiwgdGhpcy5hZGQpO1xuICAgIHRoaXMuc3RvcmUuYWRkTGlzdGVuZXIoXCJ1cGRhdGVcIiwgdGhpcy51cGRhdGUpO1xuICAgIHRoaXMuc3RvcmUuYWRkTGlzdGVuZXIoXCJyZW1vdmVcIiwgdGhpcy5yZW1vdmUpO1xuICAgIHRoaXMuc3RvcmUuYWRkTGlzdGVuZXIoXCJyZWNhbGN1bGF0ZVwiLCB0aGlzLnJlY2FsY3VsYXRlKTtcblxuICAgIHRoaXMucmVjYWxjdWxhdGUoZmlsdCwgc29ydGZ1bik7XG59XG5cbl8uZXh0ZW5kKFN0b3JlVmlldy5wcm90b3R5cGUsIHV0aWxzLkV2ZW50RW1pdHRlci5wcm90b3R5cGUsIHtcbiAgICBjbG9zZTogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLnN0b3JlLnJlbW92ZUxpc3RlbmVyKFwiYWRkXCIsIHRoaXMuYWRkKTtcbiAgICAgICAgdGhpcy5zdG9yZS5yZW1vdmVMaXN0ZW5lcihcInVwZGF0ZVwiLCB0aGlzLnVwZGF0ZSk7XG4gICAgICAgIHRoaXMuc3RvcmUucmVtb3ZlTGlzdGVuZXIoXCJyZW1vdmVcIiwgdGhpcy5yZW1vdmUpO1xuICAgICAgICB0aGlzLnN0b3JlLnJlbW92ZUxpc3RlbmVyKFwicmVjYWxjdWxhdGVcIiwgdGhpcy5yZWNhbGN1bGF0ZSk7XG4gICAgICAgIH0sXG4gICAgICAgIHJlY2FsY3VsYXRlOiBmdW5jdGlvbiAoZmlsdCwgc29ydGZ1bikge1xuICAgICAgICBpZiAoZmlsdCkge1xuICAgICAgICAgICAgdGhpcy5maWx0ID0gZmlsdC5iaW5kKHRoaXMpO1xuICAgICAgICB9XG4gICAgICAgIGlmIChzb3J0ZnVuKSB7XG4gICAgICAgICAgICB0aGlzLnNvcnRmdW4gPSBzb3J0ZnVuLmJpbmQodGhpcyk7XG4gICAgICAgIH1cblxuICAgICAgICB0aGlzLmxpc3QgPSB0aGlzLnN0b3JlLmxpc3QuZmlsdGVyKHRoaXMuZmlsdCk7XG4gICAgICAgIHRoaXMubGlzdC5zb3J0KGZ1bmN0aW9uIChhLCBiKSB7XG4gICAgICAgICAgICByZXR1cm4gdGhpcy5zb3J0ZnVuKGEpIC0gdGhpcy5zb3J0ZnVuKGIpO1xuICAgICAgICB9LmJpbmQodGhpcykpO1xuICAgICAgICB0aGlzLmVtaXQoXCJyZWNhbGN1bGF0ZVwiKTtcbiAgICB9LFxuICAgIGluZGV4OiBmdW5jdGlvbiAoZWxlbSkge1xuICAgICAgICByZXR1cm4gXy5zb3J0ZWRJbmRleCh0aGlzLmxpc3QsIGVsZW0sIHRoaXMuc29ydGZ1bik7XG4gICAgfSxcbiAgICBhZGQ6IGZ1bmN0aW9uIChlbGVtKSB7XG4gICAgICAgIGlmICh0aGlzLmZpbHQoZWxlbSkpIHtcbiAgICAgICAgICAgIHZhciBpZHggPSB0aGlzLmluZGV4KGVsZW0pO1xuICAgICAgICAgICAgaWYgKGlkeCA9PT0gdGhpcy5saXN0Lmxlbmd0aCkgeyAvL2hhcHBlbnMgb2Z0ZW4sIC5wdXNoIGlzIHdheSBmYXN0ZXIuXG4gICAgICAgICAgICAgICAgdGhpcy5saXN0LnB1c2goZWxlbSk7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHRoaXMubGlzdC5zcGxpY2UoaWR4LCAwLCBlbGVtKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIHRoaXMuZW1pdChcImFkZFwiLCBlbGVtLCBpZHgpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICB1cGRhdGU6IGZ1bmN0aW9uIChlbGVtKSB7XG4gICAgICAgIHZhciBpZHg7XG4gICAgICAgIHZhciBpID0gdGhpcy5saXN0Lmxlbmd0aDtcbiAgICAgICAgLy8gU2VhcmNoIGZyb20gdGhlIGJhY2ssIHdlIHVzdWFsbHkgdXBkYXRlIHRoZSBsYXRlc3QgZW50cmllcy5cbiAgICAgICAgd2hpbGUgKGktLSkge1xuICAgICAgICAgICAgaWYgKHRoaXMubGlzdFtpXS5pZCA9PT0gZWxlbS5pZCkge1xuICAgICAgICAgICAgICAgIGlkeCA9IGk7XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICB9XG4gICAgICAgIH1cblxuICAgICAgICBpZiAoaWR4ID09PSAtMSkgeyAvL25vdCBjb250YWluZWQgaW4gbGlzdFxuICAgICAgICAgICAgdGhpcy5hZGQoZWxlbSk7XG4gICAgICAgIH0gZWxzZSBpZiAoIXRoaXMuZmlsdChlbGVtKSkge1xuICAgICAgICAgICAgdGhpcy5yZW1vdmUoZWxlbS5pZCk7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBpZiAodGhpcy5zb3J0ZnVuKHRoaXMubGlzdFtpZHhdKSAhPT0gdGhpcy5zb3J0ZnVuKGVsZW0pKSB7IC8vc29ydHBvcyBoYXMgY2hhbmdlZFxuICAgICAgICAgICAgICAgIHRoaXMucmVtb3ZlKHRoaXMubGlzdFtpZHhdKTtcbiAgICAgICAgICAgICAgICB0aGlzLmFkZChlbGVtKTtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgdGhpcy5saXN0W2lkeF0gPSBlbGVtO1xuICAgICAgICAgICAgICAgIHRoaXMuZW1pdChcInVwZGF0ZVwiLCBlbGVtLCBpZHgpO1xuICAgICAgICAgICAgfVxuICAgICAgICB9XG4gICAgfSxcbiAgICByZW1vdmU6IGZ1bmN0aW9uIChlbGVtX2lkKSB7XG4gICAgICAgIHZhciBpZHggPSB0aGlzLmxpc3QubGVuZ3RoO1xuICAgICAgICB3aGlsZSAoaWR4LS0pIHtcbiAgICAgICAgICAgIGlmICh0aGlzLmxpc3RbaWR4XS5pZCA9PT0gZWxlbV9pZCkge1xuICAgICAgICAgICAgICAgIHRoaXMubGlzdC5zcGxpY2UoaWR4LCAxKTtcbiAgICAgICAgICAgICAgICB0aGlzLmVtaXQoXCJyZW1vdmVcIiwgZWxlbV9pZCwgaWR4KTtcbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgIH1cbn0pO1xuXG5tb2R1bGUuZXhwb3J0cyA9IHtcbiAgICBTdG9yZVZpZXc6IFN0b3JlVmlld1xufTsiLCJ2YXIgJCA9IHJlcXVpcmUoXCJqcXVlcnlcIik7XG5cblxudmFyIEtleSA9IHtcbiAgICBVUDogMzgsXG4gICAgRE9XTjogNDAsXG4gICAgUEFHRV9VUDogMzMsXG4gICAgUEFHRV9ET1dOOiAzNCxcbiAgICBIT01FOiAzNixcbiAgICBFTkQ6IDM1LFxuICAgIExFRlQ6IDM3LFxuICAgIFJJR0hUOiAzOSxcbiAgICBFTlRFUjogMTMsXG4gICAgRVNDOiAyNyxcbiAgICBUQUI6IDksXG4gICAgU1BBQ0U6IDMyLFxuICAgIEJBQ0tTUEFDRTogOCxcbn07XG4vLyBBZGQgQS1aXG5mb3IgKHZhciBpID0gNjU7IGkgPD0gOTA7IGkrKykge1xuICAgIEtleVtTdHJpbmcuZnJvbUNoYXJDb2RlKGkpXSA9IGk7XG59XG5cblxudmFyIGZvcm1hdFNpemUgPSBmdW5jdGlvbiAoYnl0ZXMpIHtcbiAgICB2YXIgc2l6ZSA9IGJ5dGVzO1xuICAgIHZhciBwcmVmaXggPSBbXCJCXCIsIFwiS0JcIiwgXCJNQlwiLCBcIkdCXCIsIFwiVEJcIl07XG4gICAgdmFyIGkgPSAwO1xuICAgIHdoaWxlIChNYXRoLmFicyhzaXplKSA+PSAxMDI0ICYmIGkgPCBwcmVmaXgubGVuZ3RoIC0gMSkge1xuICAgICAgICBpKys7XG4gICAgICAgIHNpemUgPSBzaXplIC8gMTAyNDtcbiAgICB9XG4gICAgcmV0dXJuIChNYXRoLmZsb29yKHNpemUgKiAxMDApIC8gMTAwLjApLnRvRml4ZWQoMikgKyBwcmVmaXhbaV07XG59O1xuXG5cbnZhciBmb3JtYXRUaW1lRGVsdGEgPSBmdW5jdGlvbiAobWlsbGlzZWNvbmRzKSB7XG4gICAgdmFyIHRpbWUgPSBtaWxsaXNlY29uZHM7XG4gICAgdmFyIHByZWZpeCA9IFtcIm1zXCIsIFwic1wiLCBcIm1pblwiLCBcImhcIl07XG4gICAgdmFyIGRpdiA9IFsxMDAwLCA2MCwgNjBdO1xuICAgIHZhciBpID0gMDtcbiAgICB3aGlsZSAoTWF0aC5hYnModGltZSkgPj0gZGl2W2ldICYmIGkgPCBkaXYubGVuZ3RoKSB7XG4gICAgICAgIHRpbWUgPSB0aW1lIC8gZGl2W2ldO1xuICAgICAgICBpKys7XG4gICAgfVxuICAgIHJldHVybiBNYXRoLnJvdW5kKHRpbWUpICsgcHJlZml4W2ldO1xufTtcblxuXG52YXIgZm9ybWF0VGltZVN0YW1wID0gZnVuY3Rpb24gKHNlY29uZHMpIHtcbiAgICB2YXIgdHMgPSAobmV3IERhdGUoc2Vjb25kcyAqIDEwMDApKS50b0lTT1N0cmluZygpO1xuICAgIHJldHVybiB0cy5yZXBsYWNlKFwiVFwiLCBcIiBcIikucmVwbGFjZShcIlpcIiwgXCJcIik7XG59O1xuXG5cbmZ1bmN0aW9uIEV2ZW50RW1pdHRlcigpIHtcbiAgICB0aGlzLmxpc3RlbmVycyA9IHt9O1xufVxuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5lbWl0ID0gZnVuY3Rpb24gKGV2ZW50KSB7XG4gICAgaWYgKCEoZXZlbnQgaW4gdGhpcy5saXN0ZW5lcnMpKSB7XG4gICAgICAgIHJldHVybjtcbiAgICB9XG4gICAgdmFyIGFyZ3MgPSBBcnJheS5wcm90b3R5cGUuc2xpY2UuY2FsbChhcmd1bWVudHMsIDEpO1xuICAgIHRoaXMubGlzdGVuZXJzW2V2ZW50XS5mb3JFYWNoKGZ1bmN0aW9uIChsaXN0ZW5lcikge1xuICAgICAgICBsaXN0ZW5lci5hcHBseSh0aGlzLCBhcmdzKTtcbiAgICB9LmJpbmQodGhpcykpO1xufTtcbkV2ZW50RW1pdHRlci5wcm90b3R5cGUuYWRkTGlzdGVuZXIgPSBmdW5jdGlvbiAoZXZlbnRzLCBmKSB7XG4gICAgZXZlbnRzLnNwbGl0KFwiIFwiKS5mb3JFYWNoKGZ1bmN0aW9uIChldmVudCkge1xuICAgICAgICB0aGlzLmxpc3RlbmVyc1tldmVudF0gPSB0aGlzLmxpc3RlbmVyc1tldmVudF0gfHwgW107XG4gICAgICAgIHRoaXMubGlzdGVuZXJzW2V2ZW50XS5wdXNoKGYpO1xuICAgIH0uYmluZCh0aGlzKSk7XG59O1xuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5yZW1vdmVMaXN0ZW5lciA9IGZ1bmN0aW9uIChldmVudHMsIGYpIHtcbiAgICBpZiAoIShldmVudHMgaW4gdGhpcy5saXN0ZW5lcnMpKSB7XG4gICAgICAgIHJldHVybiBmYWxzZTtcbiAgICB9XG4gICAgZXZlbnRzLnNwbGl0KFwiIFwiKS5mb3JFYWNoKGZ1bmN0aW9uIChldmVudCkge1xuICAgICAgICB2YXIgaW5kZXggPSB0aGlzLmxpc3RlbmVyc1tldmVudF0uaW5kZXhPZihmKTtcbiAgICAgICAgaWYgKGluZGV4ID49IDApIHtcbiAgICAgICAgICAgIHRoaXMubGlzdGVuZXJzW2V2ZW50XS5zcGxpY2UoaW5kZXgsIDEpO1xuICAgICAgICB9XG4gICAgfS5iaW5kKHRoaXMpKTtcbn07XG5cblxuZnVuY3Rpb24gZ2V0Q29va2llKG5hbWUpIHtcbiAgICB2YXIgciA9IGRvY3VtZW50LmNvb2tpZS5tYXRjaChcIlxcXFxiXCIgKyBuYW1lICsgXCI9KFteO10qKVxcXFxiXCIpO1xuICAgIHJldHVybiByID8gclsxXSA6IHVuZGVmaW5lZDtcbn1cbnZhciB4c3JmID0gJC5wYXJhbSh7X3hzcmY6IGdldENvb2tpZShcIl94c3JmXCIpfSk7XG5cbi8vVG9ybmFkbyBYU1JGIFByb3RlY3Rpb24uXG4kLmFqYXhQcmVmaWx0ZXIoZnVuY3Rpb24gKG9wdGlvbnMpIHtcbiAgICBpZiAoW1wicG9zdFwiLCBcInB1dFwiLCBcImRlbGV0ZVwiXS5pbmRleE9mKG9wdGlvbnMudHlwZS50b0xvd2VyQ2FzZSgpKSA+PSAwICYmIG9wdGlvbnMudXJsWzBdID09PSBcIi9cIikge1xuICAgICAgICBpZiAob3B0aW9ucy5kYXRhKSB7XG4gICAgICAgICAgICBvcHRpb25zLmRhdGEgKz0gKFwiJlwiICsgeHNyZik7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBvcHRpb25zLmRhdGEgPSB4c3JmO1xuICAgICAgICB9XG4gICAgfVxufSk7XG4vLyBMb2cgQUpBWCBFcnJvcnNcbiQoZG9jdW1lbnQpLmFqYXhFcnJvcihmdW5jdGlvbiAoZXZlbnQsIGpxWEhSLCBhamF4U2V0dGluZ3MsIHRocm93bkVycm9yKSB7XG4gICAgdmFyIG1lc3NhZ2UgPSBqcVhIUi5yZXNwb25zZVRleHQ7XG4gICAgY29uc29sZS5lcnJvcihtZXNzYWdlLCBhcmd1bWVudHMpO1xuICAgIEV2ZW50TG9nQWN0aW9ucy5hZGRfZXZlbnQodGhyb3duRXJyb3IgKyBcIjogXCIgKyBtZXNzYWdlKTtcbiAgICB3aW5kb3cuYWxlcnQobWVzc2FnZSk7XG59KTtcblxubW9kdWxlLmV4cG9ydHMgPSB7XG4gICAgRXZlbnRFbWl0dGVyOiBFdmVudEVtaXR0ZXIsXG4gICAgZm9ybWF0U2l6ZTogZm9ybWF0U2l6ZSxcbiAgICBmb3JtYXRUaW1lRGVsdGE6IGZvcm1hdFRpbWVEZWx0YSxcbiAgICBmb3JtYXRUaW1lU3RhbXA6IGZvcm1hdFRpbWVTdGFtcFxufTsiXX0=
