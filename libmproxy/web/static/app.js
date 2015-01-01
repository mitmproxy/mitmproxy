(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
// Copyright Joyent, Inc. and other Node contributors.
//
// Permission is hereby granted, free of charge, to any person obtaining a
// copy of this software and associated documentation files (the
// "Software"), to deal in the Software without restriction, including
// without limitation the rights to use, copy, modify, merge, publish,
// distribute, sublicense, and/or sell copies of the Software, and to permit
// persons to whom the Software is furnished to do so, subject to the
// following conditions:
//
// The above copyright notice and this permission notice shall be included
// in all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
// OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
// MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
// NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
// DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
// OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
// USE OR OTHER DEALINGS IN THE SOFTWARE.

function EventEmitter() {
  this._events = this._events || {};
  this._maxListeners = this._maxListeners || undefined;
}
module.exports = EventEmitter;

// Backwards-compat with node 0.10.x
EventEmitter.EventEmitter = EventEmitter;

EventEmitter.prototype._events = undefined;
EventEmitter.prototype._maxListeners = undefined;

// By default EventEmitters will print a warning if more than 10 listeners are
// added to it. This is a useful default which helps finding memory leaks.
EventEmitter.defaultMaxListeners = 10;

// Obviously not all Emitters should be limited to 10. This function allows
// that to be increased. Set to zero for unlimited.
EventEmitter.prototype.setMaxListeners = function(n) {
  if (!isNumber(n) || n < 0 || isNaN(n))
    throw TypeError('n must be a positive number');
  this._maxListeners = n;
  return this;
};

EventEmitter.prototype.emit = function(type) {
  var er, handler, len, args, i, listeners;

  if (!this._events)
    this._events = {};

  // If there is no 'error' event listener then throw.
  if (type === 'error') {
    if (!this._events.error ||
        (isObject(this._events.error) && !this._events.error.length)) {
      er = arguments[1];
      if (er instanceof Error) {
        throw er; // Unhandled 'error' event
      }
      throw TypeError('Uncaught, unspecified "error" event.');
    }
  }

  handler = this._events[type];

  if (isUndefined(handler))
    return false;

  if (isFunction(handler)) {
    switch (arguments.length) {
      // fast cases
      case 1:
        handler.call(this);
        break;
      case 2:
        handler.call(this, arguments[1]);
        break;
      case 3:
        handler.call(this, arguments[1], arguments[2]);
        break;
      // slower
      default:
        len = arguments.length;
        args = new Array(len - 1);
        for (i = 1; i < len; i++)
          args[i - 1] = arguments[i];
        handler.apply(this, args);
    }
  } else if (isObject(handler)) {
    len = arguments.length;
    args = new Array(len - 1);
    for (i = 1; i < len; i++)
      args[i - 1] = arguments[i];

    listeners = handler.slice();
    len = listeners.length;
    for (i = 0; i < len; i++)
      listeners[i].apply(this, args);
  }

  return true;
};

EventEmitter.prototype.addListener = function(type, listener) {
  var m;

  if (!isFunction(listener))
    throw TypeError('listener must be a function');

  if (!this._events)
    this._events = {};

  // To avoid recursion in the case that type === "newListener"! Before
  // adding it to the listeners, first emit "newListener".
  if (this._events.newListener)
    this.emit('newListener', type,
              isFunction(listener.listener) ?
              listener.listener : listener);

  if (!this._events[type])
    // Optimize the case of one listener. Don't need the extra array object.
    this._events[type] = listener;
  else if (isObject(this._events[type]))
    // If we've already got an array, just append.
    this._events[type].push(listener);
  else
    // Adding the second element, need to change to array.
    this._events[type] = [this._events[type], listener];

  // Check for listener leak
  if (isObject(this._events[type]) && !this._events[type].warned) {
    var m;
    if (!isUndefined(this._maxListeners)) {
      m = this._maxListeners;
    } else {
      m = EventEmitter.defaultMaxListeners;
    }

    if (m && m > 0 && this._events[type].length > m) {
      this._events[type].warned = true;
      console.error('(node) warning: possible EventEmitter memory ' +
                    'leak detected. %d listeners added. ' +
                    'Use emitter.setMaxListeners() to increase limit.',
                    this._events[type].length);
      if (typeof console.trace === 'function') {
        // not supported in IE 10
        console.trace();
      }
    }
  }

  return this;
};

EventEmitter.prototype.on = EventEmitter.prototype.addListener;

EventEmitter.prototype.once = function(type, listener) {
  if (!isFunction(listener))
    throw TypeError('listener must be a function');

  var fired = false;

  function g() {
    this.removeListener(type, g);

    if (!fired) {
      fired = true;
      listener.apply(this, arguments);
    }
  }

  g.listener = listener;
  this.on(type, g);

  return this;
};

// emits a 'removeListener' event iff the listener was removed
EventEmitter.prototype.removeListener = function(type, listener) {
  var list, position, length, i;

  if (!isFunction(listener))
    throw TypeError('listener must be a function');

  if (!this._events || !this._events[type])
    return this;

  list = this._events[type];
  length = list.length;
  position = -1;

  if (list === listener ||
      (isFunction(list.listener) && list.listener === listener)) {
    delete this._events[type];
    if (this._events.removeListener)
      this.emit('removeListener', type, listener);

  } else if (isObject(list)) {
    for (i = length; i-- > 0;) {
      if (list[i] === listener ||
          (list[i].listener && list[i].listener === listener)) {
        position = i;
        break;
      }
    }

    if (position < 0)
      return this;

    if (list.length === 1) {
      list.length = 0;
      delete this._events[type];
    } else {
      list.splice(position, 1);
    }

    if (this._events.removeListener)
      this.emit('removeListener', type, listener);
  }

  return this;
};

EventEmitter.prototype.removeAllListeners = function(type) {
  var key, listeners;

  if (!this._events)
    return this;

  // not listening for removeListener, no need to emit
  if (!this._events.removeListener) {
    if (arguments.length === 0)
      this._events = {};
    else if (this._events[type])
      delete this._events[type];
    return this;
  }

  // emit removeListener for all listeners on all events
  if (arguments.length === 0) {
    for (key in this._events) {
      if (key === 'removeListener') continue;
      this.removeAllListeners(key);
    }
    this.removeAllListeners('removeListener');
    this._events = {};
    return this;
  }

  listeners = this._events[type];

  if (isFunction(listeners)) {
    this.removeListener(type, listeners);
  } else {
    // LIFO order
    while (listeners.length)
      this.removeListener(type, listeners[listeners.length - 1]);
  }
  delete this._events[type];

  return this;
};

EventEmitter.prototype.listeners = function(type) {
  var ret;
  if (!this._events || !this._events[type])
    ret = [];
  else if (isFunction(this._events[type]))
    ret = [this._events[type]];
  else
    ret = this._events[type].slice();
  return ret;
};

EventEmitter.listenerCount = function(emitter, type) {
  var ret;
  if (!emitter._events || !emitter._events[type])
    ret = 0;
  else if (isFunction(emitter._events[type]))
    ret = 1;
  else
    ret = emitter._events[type].length;
  return ret;
};

function isFunction(arg) {
  return typeof arg === 'function';
}

function isNumber(arg) {
  return typeof arg === 'number';
}

function isObject(arg) {
  return typeof arg === 'object' && arg !== null;
}

function isUndefined(arg) {
  return arg === void 0;
}

},{}],2:[function(require,module,exports){
var $ = require("jquery");

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

        $.ajax({
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
        $.post("/flows/" + flow.id + "/accept");
    },
    accept_all: function(){
        $.post("/flows/accept");
    },
    "delete": function(flow){
        $.ajax({
            type:"DELETE",
            url: "/flows/" + flow.id
        });
    },
    duplicate: function(flow){
        $.post("/flows/" + flow.id + "/duplicate");
    },
    replay: function(flow){
        $.post("/flows/" + flow.id + "/replay");
    },
    revert: function(flow){
        $.post("/flows/" + flow.id + "/revert");
    },
    update: function (flow) {
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.FLOW_STORE,
            cmd: StoreCmds.UPDATE,
            data: flow
        });
    },
    clear: function(){
        $.post("/clear");
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
},{"jquery":"jquery"}],3:[function(require,module,exports){

var React = require("react");
var ReactRouter = require("react-router");
var $ = require("jquery");

var Connection = require("./connection");
var proxyapp = require("./components/proxyapp.js");

$(function () {
    window.ws = new Connection("/updates");

    ReactRouter.run(proxyapp.routes, function (Handler) {
        React.render(React.createElement(Handler, null), document.body);
    });
});
},{"./components/proxyapp.js":11,"./connection":14,"jquery":"jquery","react":"react","react-router":"react-router"}],4:[function(require,module,exports){
var React = require("react");
var utils = require("./utils.js");
var VirtualScrollMixin = require("./virtualscroll.js");
var views = require("../store/view.js");

var LogMessage = React.createClass({displayName: "LogMessage",
    render: function () {
        var entry = this.props.entry;
        var indicator;
        switch (entry.level) {
            case "web":
                indicator = React.createElement("i", {className: "fa fa-fw fa-html5"});
                break;
            case "debug":
                indicator = React.createElement("i", {className: "fa fa-fw fa-bug"});
                break;
            default:
                indicator = React.createElement("i", {className: "fa fa-fw fa-info"});
        }
        return (
            React.createElement("div", null, 
                indicator, " ", entry.message
            )
        );
    },
    shouldComponentUpdate: function () {
        return false; // log entries are immutable.
    }
});

var EventLogContents = React.createClass({displayName: "EventLogContents",
    mixins: [utils.AutoScrollMixin, VirtualScrollMixin],
    getInitialState: function () {
        return {
            log: []
        };
    },
    componentWillMount: function () {
        this.openView(this.props.eventStore);
    },
    componentWillUnmount: function () {
        this.closeView();
    },
    openView: function (store) {
        var view = new views.StoreView(store, function (entry) {
            return this.props.filter[entry.level];
        }.bind(this));
        this.setState({
            view: view
        });

        view.addListener("add recalculate", this.onEventLogChange);
    },
    closeView: function () {
        this.state.view.close();
    },
    onEventLogChange: function () {
        this.setState({
            log: this.state.view.list
        });
    },
    componentWillReceiveProps: function (nextProps) {
        if (nextProps.filter !== this.props.filter) {
            this.props.filter = nextProps.filter; // Dirty: Make sure that view filter sees the update.
            this.state.view.recalculate();
        }
        if (nextProps.eventStore !== this.props.eventStore) {
            this.closeView();
            this.openView(nextProps.eventStore);
        }
    },
    getDefaultProps: function () {
        return {
            rowHeight: 45,
            rowHeightMin: 15,
            placeholderTagName: "div"
        };
    },
    renderRow: function (elem) {
        return React.createElement(LogMessage, {key: elem.id, entry: elem});
    },
    render: function () {
        var rows = this.renderRows(this.state.log);

        return React.createElement("pre", {onScroll: this.onScroll}, 
             this.getPlaceholderTop(this.state.log.length), 
            rows, 
             this.getPlaceholderBottom(this.state.log.length) 
        );
    }
});

var ToggleFilter = React.createClass({displayName: "ToggleFilter",
    toggle: function (e) {
        e.preventDefault();
        return this.props.toggleLevel(this.props.name);
    },
    render: function () {
        var className = "label ";
        if (this.props.active) {
            className += "label-primary";
        } else {
            className += "label-default";
        }
        return (
            React.createElement("a", {
                href: "#", 
                className: className, 
                onClick: this.toggle}, 
                this.props.name
            )
        );
    }
});

var EventLog = React.createClass({displayName: "EventLog",
    getInitialState: function () {
        return {
            filter: {
                "debug": false,
                "info": true,
                "web": true
            }
        };
    },
    close: function () {
        var d = {};
        d[Query.SHOW_EVENTLOG] = undefined;
        this.setQuery(d);
    },
    toggleLevel: function (level) {
        var filter = _.extend({}, this.state.filter);
        filter[level] = !filter[level];
        this.setState({filter: filter});
    },
    render: function () {
        return (
            React.createElement("div", {className: "eventlog"}, 
                React.createElement("div", null, 
                    "Eventlog", 
                    React.createElement("div", {className: "pull-right"}, 
                        React.createElement(ToggleFilter, {name: "debug", active: this.state.filter.debug, toggleLevel: this.toggleLevel}), 
                        React.createElement(ToggleFilter, {name: "info", active: this.state.filter.info, toggleLevel: this.toggleLevel}), 
                        React.createElement(ToggleFilter, {name: "web", active: this.state.filter.web, toggleLevel: this.toggleLevel}), 
                        React.createElement("i", {onClick: this.close, className: "fa fa-close"})
                    )

                ), 
                React.createElement(EventLogContents, {filter: this.state.filter, eventStore: this.props.eventStore})
            )
        );
    }
});

module.exports = EventLog;
},{"../store/view.js":19,"./utils.js":12,"./virtualscroll.js":13,"react":"react"}],5:[function(require,module,exports){
var React = require("react");
var _ = require("lodash");

var utils = require("./utils.js");
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
},{"../actions.js":2,"../flow/utils.js":17,"../utils.js":20,"./utils.js":12,"lodash":"lodash","react":"react"}],6:[function(require,module,exports){
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



},{"../flow/utils.js":17,"../utils.js":20,"react":"react"}],7:[function(require,module,exports){
var React = require("react");
var utils = require("./utils.js");
var VirtualScrollMixin = require("./virtualscroll.js");
var flowtable_columns = require("./flowtable-columns.js");

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

},{"./flowtable-columns.js":6,"./utils.js":12,"./virtualscroll.js":13,"react":"react"}],8:[function(require,module,exports){
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
},{"react":"react"}],9:[function(require,module,exports){
var React = require("react");
var $ = require("jquery");

var utils = require("./utils.js");

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
},{"./utils.js":12,"jquery":"jquery","react":"react"}],10:[function(require,module,exports){
var React = require("react");

var utils = require("./utils.js");
var toputils = require("../utils.js");
var views = require("../store/view.js");
var Filt = require("../filt/filt.js");
FlowTable = require("./flowtable.js");
var flowdetail = require("./flowdetail.js");


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
            case toputils.Key.K:
            case toputils.Key.UP:
                this.selectFlowRelative(-1);
                break;
            case toputils.Key.J:
            case toputils.Key.DOWN:
                this.selectFlowRelative(+1);
                break;
            case toputils.Key.SPACE:
            case toputils.Key.PAGE_DOWN:
                this.selectFlowRelative(+10);
                break;
            case toputils.Key.PAGE_UP:
                this.selectFlowRelative(-10);
                break;
            case toputils.Key.END:
                this.selectFlowRelative(+1e10);
                break;
            case toputils.Key.HOME:
                this.selectFlowRelative(-1e10);
                break;
            case toputils.Key.ESC:
                this.selectFlow(null);
                break;
            case toputils.Key.H:
            case toputils.Key.LEFT:
                if (this.refs.flowDetails) {
                    this.refs.flowDetails.nextTab(-1);
                }
                break;
            case toputils.Key.L:
            case toputils.Key.TAB:
            case toputils.Key.RIGHT:
                if (this.refs.flowDetails) {
                    this.refs.flowDetails.nextTab(+1);
                }
                break;
            case toputils.Key.C:
                if (e.shiftKey) {
                    FlowActions.clear();
                }
                break;
            case toputils.Key.D:
                if (flow) {
                    if (e.shiftKey) {
                        FlowActions.duplicate(flow);
                    } else {
                        FlowActions.delete(flow);
                    }
                }
                break;
            case toputils.Key.A:
                if (e.shiftKey) {
                    FlowActions.accept_all();
                } else if (flow && flow.intercepted) {
                    FlowActions.accept(flow);
                }
                break;
            case toputils.Key.R:
                if (!e.shiftKey && flow) {
                    FlowActions.replay(flow);
                }
                break;
            case toputils.Key.V:
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

},{"../filt/filt.js":16,"../store/view.js":19,"../utils.js":20,"./flowdetail.js":5,"./flowtable.js":7,"./utils.js":12,"react":"react"}],11:[function(require,module,exports){
var React = require("react");
var ReactRouter = require("react-router");
var _ = require("lodash");

var utils = require("./utils.js");
var MainView = require("./mainview.js");
var Footer = require("./footer.js");
var header = require("./header.js");
var EventLog = require("./eventlog.js");
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
                React.createElement(utils.Splitter, {key: "splitter", axis: "y"}),
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


},{"../store/store.js":18,"./eventlog.js":4,"./footer.js":8,"./header.js":9,"./mainview.js":10,"./utils.js":12,"lodash":"lodash","react":"react","react-router":"react-router"}],12:[function(require,module,exports){
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
},{"lodash":"lodash","react":"react","react-router":"react-router"}],13:[function(require,module,exports){
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
},{"react":"react"}],14:[function(require,module,exports){

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
},{"./actions.js":2}],15:[function(require,module,exports){
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
},{}],16:[function(require,module,exports){
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

},{}],17:[function(require,module,exports){
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
},{"lodash":"lodash"}],18:[function(require,module,exports){

var _ = require("lodash");
var $ = require("jquery");
var EventEmitter = require('events').EventEmitter;

var utils = require("../utils.js");
var actions = require("../actions.js");
var dispatcher = require("../dispatcher.js");


function ListStore() {
    EventEmitter.call(this);
    this.reset();
}
_.extend(ListStore.prototype, EventEmitter.prototype, {
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
    EventEmitter.call(this);
    this.reset();
}
_.extend(DictStore.prototype, EventEmitter.prototype, {
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
},{"../actions.js":2,"../dispatcher.js":15,"../utils.js":20,"events":1,"jquery":"jquery","lodash":"lodash"}],19:[function(require,module,exports){

var EventEmitter = require('events').EventEmitter;
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
    EventEmitter.call(this);
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

_.extend(StoreView.prototype, EventEmitter.prototype, {
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
},{"../utils.js":20,"events":1,"lodash":"lodash"}],20:[function(require,module,exports){
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
    formatSize: formatSize,
    formatTimeDelta: formatTimeDelta,
    formatTimeStamp: formatTimeStamp,
    Key: Key
};
},{"jquery":"jquery"}]},{},[3])
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIm5vZGVfbW9kdWxlcy9icm93c2VyaWZ5L25vZGVfbW9kdWxlcy9icm93c2VyLXBhY2svX3ByZWx1ZGUuanMiLCJub2RlX21vZHVsZXMvYnJvd3NlcmlmeS9ub2RlX21vZHVsZXMvZXZlbnRzL2V2ZW50cy5qcyIsInNyYy9qcy9hY3Rpb25zLmpzIiwic3JjL2pzL2FwcC5qcyIsInNyYy9qcy9jb21wb25lbnRzL2V2ZW50bG9nLmpzIiwic3JjL2pzL2NvbXBvbmVudHMvZmxvd2RldGFpbC5qcyIsInNyYy9qcy9jb21wb25lbnRzL2Zsb3d0YWJsZS1jb2x1bW5zLmpzIiwic3JjL2pzL2NvbXBvbmVudHMvZmxvd3RhYmxlLmpzIiwic3JjL2pzL2NvbXBvbmVudHMvZm9vdGVyLmpzIiwic3JjL2pzL2NvbXBvbmVudHMvaGVhZGVyLmpzIiwic3JjL2pzL2NvbXBvbmVudHMvbWFpbnZpZXcuanMiLCJzcmMvanMvY29tcG9uZW50cy9wcm94eWFwcC5qcyIsInNyYy9qcy9jb21wb25lbnRzL3V0aWxzLmpzIiwic3JjL2pzL2NvbXBvbmVudHMvdmlydHVhbHNjcm9sbC5qcyIsInNyYy9qcy9jb25uZWN0aW9uLmpzIiwic3JjL2pzL2Rpc3BhdGNoZXIuanMiLCJzcmMvanMvZmlsdC9maWx0LmpzIiwic3JjL2pzL2Zsb3cvdXRpbHMuanMiLCJzcmMvanMvc3RvcmUvc3RvcmUuanMiLCJzcmMvanMvc3RvcmUvdmlldy5qcyIsInNyYy9qcy91dGlscy5qcyJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQTtBQ0FBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDN1NBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUN2SEE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ2RBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDMUpBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUM5WUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ3BLQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ3hJQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ2hCQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ3BZQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ3hPQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDNUZBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ25NQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUNwRkE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDM0JBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUN0Q0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDaHZEQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDakVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ3BMQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQzdHQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSIsImZpbGUiOiJnZW5lcmF0ZWQuanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlc0NvbnRlbnQiOlsiKGZ1bmN0aW9uIGUodCxuLHIpe2Z1bmN0aW9uIHMobyx1KXtpZighbltvXSl7aWYoIXRbb10pe3ZhciBhPXR5cGVvZiByZXF1aXJlPT1cImZ1bmN0aW9uXCImJnJlcXVpcmU7aWYoIXUmJmEpcmV0dXJuIGEobywhMCk7aWYoaSlyZXR1cm4gaShvLCEwKTt2YXIgZj1uZXcgRXJyb3IoXCJDYW5ub3QgZmluZCBtb2R1bGUgJ1wiK28rXCInXCIpO3Rocm93IGYuY29kZT1cIk1PRFVMRV9OT1RfRk9VTkRcIixmfXZhciBsPW5bb109e2V4cG9ydHM6e319O3Rbb11bMF0uY2FsbChsLmV4cG9ydHMsZnVuY3Rpb24oZSl7dmFyIG49dFtvXVsxXVtlXTtyZXR1cm4gcyhuP246ZSl9LGwsbC5leHBvcnRzLGUsdCxuLHIpfXJldHVybiBuW29dLmV4cG9ydHN9dmFyIGk9dHlwZW9mIHJlcXVpcmU9PVwiZnVuY3Rpb25cIiYmcmVxdWlyZTtmb3IodmFyIG89MDtvPHIubGVuZ3RoO28rKylzKHJbb10pO3JldHVybiBzfSkiLCIvLyBDb3B5cmlnaHQgSm95ZW50LCBJbmMuIGFuZCBvdGhlciBOb2RlIGNvbnRyaWJ1dG9ycy5cbi8vXG4vLyBQZXJtaXNzaW9uIGlzIGhlcmVieSBncmFudGVkLCBmcmVlIG9mIGNoYXJnZSwgdG8gYW55IHBlcnNvbiBvYnRhaW5pbmcgYVxuLy8gY29weSBvZiB0aGlzIHNvZnR3YXJlIGFuZCBhc3NvY2lhdGVkIGRvY3VtZW50YXRpb24gZmlsZXMgKHRoZVxuLy8gXCJTb2Z0d2FyZVwiKSwgdG8gZGVhbCBpbiB0aGUgU29mdHdhcmUgd2l0aG91dCByZXN0cmljdGlvbiwgaW5jbHVkaW5nXG4vLyB3aXRob3V0IGxpbWl0YXRpb24gdGhlIHJpZ2h0cyB0byB1c2UsIGNvcHksIG1vZGlmeSwgbWVyZ2UsIHB1Ymxpc2gsXG4vLyBkaXN0cmlidXRlLCBzdWJsaWNlbnNlLCBhbmQvb3Igc2VsbCBjb3BpZXMgb2YgdGhlIFNvZnR3YXJlLCBhbmQgdG8gcGVybWl0XG4vLyBwZXJzb25zIHRvIHdob20gdGhlIFNvZnR3YXJlIGlzIGZ1cm5pc2hlZCB0byBkbyBzbywgc3ViamVjdCB0byB0aGVcbi8vIGZvbGxvd2luZyBjb25kaXRpb25zOlxuLy9cbi8vIFRoZSBhYm92ZSBjb3B5cmlnaHQgbm90aWNlIGFuZCB0aGlzIHBlcm1pc3Npb24gbm90aWNlIHNoYWxsIGJlIGluY2x1ZGVkXG4vLyBpbiBhbGwgY29waWVzIG9yIHN1YnN0YW50aWFsIHBvcnRpb25zIG9mIHRoZSBTb2Z0d2FyZS5cbi8vXG4vLyBUSEUgU09GVFdBUkUgSVMgUFJPVklERUQgXCJBUyBJU1wiLCBXSVRIT1VUIFdBUlJBTlRZIE9GIEFOWSBLSU5ELCBFWFBSRVNTXG4vLyBPUiBJTVBMSUVELCBJTkNMVURJTkcgQlVUIE5PVCBMSU1JVEVEIFRPIFRIRSBXQVJSQU5USUVTIE9GXG4vLyBNRVJDSEFOVEFCSUxJVFksIEZJVE5FU1MgRk9SIEEgUEFSVElDVUxBUiBQVVJQT1NFIEFORCBOT05JTkZSSU5HRU1FTlQuIElOXG4vLyBOTyBFVkVOVCBTSEFMTCBUSEUgQVVUSE9SUyBPUiBDT1BZUklHSFQgSE9MREVSUyBCRSBMSUFCTEUgRk9SIEFOWSBDTEFJTSxcbi8vIERBTUFHRVMgT1IgT1RIRVIgTElBQklMSVRZLCBXSEVUSEVSIElOIEFOIEFDVElPTiBPRiBDT05UUkFDVCwgVE9SVCBPUlxuLy8gT1RIRVJXSVNFLCBBUklTSU5HIEZST00sIE9VVCBPRiBPUiBJTiBDT05ORUNUSU9OIFdJVEggVEhFIFNPRlRXQVJFIE9SIFRIRVxuLy8gVVNFIE9SIE9USEVSIERFQUxJTkdTIElOIFRIRSBTT0ZUV0FSRS5cblxuZnVuY3Rpb24gRXZlbnRFbWl0dGVyKCkge1xuICB0aGlzLl9ldmVudHMgPSB0aGlzLl9ldmVudHMgfHwge307XG4gIHRoaXMuX21heExpc3RlbmVycyA9IHRoaXMuX21heExpc3RlbmVycyB8fCB1bmRlZmluZWQ7XG59XG5tb2R1bGUuZXhwb3J0cyA9IEV2ZW50RW1pdHRlcjtcblxuLy8gQmFja3dhcmRzLWNvbXBhdCB3aXRoIG5vZGUgMC4xMC54XG5FdmVudEVtaXR0ZXIuRXZlbnRFbWl0dGVyID0gRXZlbnRFbWl0dGVyO1xuXG5FdmVudEVtaXR0ZXIucHJvdG90eXBlLl9ldmVudHMgPSB1bmRlZmluZWQ7XG5FdmVudEVtaXR0ZXIucHJvdG90eXBlLl9tYXhMaXN0ZW5lcnMgPSB1bmRlZmluZWQ7XG5cbi8vIEJ5IGRlZmF1bHQgRXZlbnRFbWl0dGVycyB3aWxsIHByaW50IGEgd2FybmluZyBpZiBtb3JlIHRoYW4gMTAgbGlzdGVuZXJzIGFyZVxuLy8gYWRkZWQgdG8gaXQuIFRoaXMgaXMgYSB1c2VmdWwgZGVmYXVsdCB3aGljaCBoZWxwcyBmaW5kaW5nIG1lbW9yeSBsZWFrcy5cbkV2ZW50RW1pdHRlci5kZWZhdWx0TWF4TGlzdGVuZXJzID0gMTA7XG5cbi8vIE9idmlvdXNseSBub3QgYWxsIEVtaXR0ZXJzIHNob3VsZCBiZSBsaW1pdGVkIHRvIDEwLiBUaGlzIGZ1bmN0aW9uIGFsbG93c1xuLy8gdGhhdCB0byBiZSBpbmNyZWFzZWQuIFNldCB0byB6ZXJvIGZvciB1bmxpbWl0ZWQuXG5FdmVudEVtaXR0ZXIucHJvdG90eXBlLnNldE1heExpc3RlbmVycyA9IGZ1bmN0aW9uKG4pIHtcbiAgaWYgKCFpc051bWJlcihuKSB8fCBuIDwgMCB8fCBpc05hTihuKSlcbiAgICB0aHJvdyBUeXBlRXJyb3IoJ24gbXVzdCBiZSBhIHBvc2l0aXZlIG51bWJlcicpO1xuICB0aGlzLl9tYXhMaXN0ZW5lcnMgPSBuO1xuICByZXR1cm4gdGhpcztcbn07XG5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUuZW1pdCA9IGZ1bmN0aW9uKHR5cGUpIHtcbiAgdmFyIGVyLCBoYW5kbGVyLCBsZW4sIGFyZ3MsIGksIGxpc3RlbmVycztcblxuICBpZiAoIXRoaXMuX2V2ZW50cylcbiAgICB0aGlzLl9ldmVudHMgPSB7fTtcblxuICAvLyBJZiB0aGVyZSBpcyBubyAnZXJyb3InIGV2ZW50IGxpc3RlbmVyIHRoZW4gdGhyb3cuXG4gIGlmICh0eXBlID09PSAnZXJyb3InKSB7XG4gICAgaWYgKCF0aGlzLl9ldmVudHMuZXJyb3IgfHxcbiAgICAgICAgKGlzT2JqZWN0KHRoaXMuX2V2ZW50cy5lcnJvcikgJiYgIXRoaXMuX2V2ZW50cy5lcnJvci5sZW5ndGgpKSB7XG4gICAgICBlciA9IGFyZ3VtZW50c1sxXTtcbiAgICAgIGlmIChlciBpbnN0YW5jZW9mIEVycm9yKSB7XG4gICAgICAgIHRocm93IGVyOyAvLyBVbmhhbmRsZWQgJ2Vycm9yJyBldmVudFxuICAgICAgfVxuICAgICAgdGhyb3cgVHlwZUVycm9yKCdVbmNhdWdodCwgdW5zcGVjaWZpZWQgXCJlcnJvclwiIGV2ZW50LicpO1xuICAgIH1cbiAgfVxuXG4gIGhhbmRsZXIgPSB0aGlzLl9ldmVudHNbdHlwZV07XG5cbiAgaWYgKGlzVW5kZWZpbmVkKGhhbmRsZXIpKVxuICAgIHJldHVybiBmYWxzZTtcblxuICBpZiAoaXNGdW5jdGlvbihoYW5kbGVyKSkge1xuICAgIHN3aXRjaCAoYXJndW1lbnRzLmxlbmd0aCkge1xuICAgICAgLy8gZmFzdCBjYXNlc1xuICAgICAgY2FzZSAxOlxuICAgICAgICBoYW5kbGVyLmNhbGwodGhpcyk7XG4gICAgICAgIGJyZWFrO1xuICAgICAgY2FzZSAyOlxuICAgICAgICBoYW5kbGVyLmNhbGwodGhpcywgYXJndW1lbnRzWzFdKTtcbiAgICAgICAgYnJlYWs7XG4gICAgICBjYXNlIDM6XG4gICAgICAgIGhhbmRsZXIuY2FsbCh0aGlzLCBhcmd1bWVudHNbMV0sIGFyZ3VtZW50c1syXSk7XG4gICAgICAgIGJyZWFrO1xuICAgICAgLy8gc2xvd2VyXG4gICAgICBkZWZhdWx0OlxuICAgICAgICBsZW4gPSBhcmd1bWVudHMubGVuZ3RoO1xuICAgICAgICBhcmdzID0gbmV3IEFycmF5KGxlbiAtIDEpO1xuICAgICAgICBmb3IgKGkgPSAxOyBpIDwgbGVuOyBpKyspXG4gICAgICAgICAgYXJnc1tpIC0gMV0gPSBhcmd1bWVudHNbaV07XG4gICAgICAgIGhhbmRsZXIuYXBwbHkodGhpcywgYXJncyk7XG4gICAgfVxuICB9IGVsc2UgaWYgKGlzT2JqZWN0KGhhbmRsZXIpKSB7XG4gICAgbGVuID0gYXJndW1lbnRzLmxlbmd0aDtcbiAgICBhcmdzID0gbmV3IEFycmF5KGxlbiAtIDEpO1xuICAgIGZvciAoaSA9IDE7IGkgPCBsZW47IGkrKylcbiAgICAgIGFyZ3NbaSAtIDFdID0gYXJndW1lbnRzW2ldO1xuXG4gICAgbGlzdGVuZXJzID0gaGFuZGxlci5zbGljZSgpO1xuICAgIGxlbiA9IGxpc3RlbmVycy5sZW5ndGg7XG4gICAgZm9yIChpID0gMDsgaSA8IGxlbjsgaSsrKVxuICAgICAgbGlzdGVuZXJzW2ldLmFwcGx5KHRoaXMsIGFyZ3MpO1xuICB9XG5cbiAgcmV0dXJuIHRydWU7XG59O1xuXG5FdmVudEVtaXR0ZXIucHJvdG90eXBlLmFkZExpc3RlbmVyID0gZnVuY3Rpb24odHlwZSwgbGlzdGVuZXIpIHtcbiAgdmFyIG07XG5cbiAgaWYgKCFpc0Z1bmN0aW9uKGxpc3RlbmVyKSlcbiAgICB0aHJvdyBUeXBlRXJyb3IoJ2xpc3RlbmVyIG11c3QgYmUgYSBmdW5jdGlvbicpO1xuXG4gIGlmICghdGhpcy5fZXZlbnRzKVxuICAgIHRoaXMuX2V2ZW50cyA9IHt9O1xuXG4gIC8vIFRvIGF2b2lkIHJlY3Vyc2lvbiBpbiB0aGUgY2FzZSB0aGF0IHR5cGUgPT09IFwibmV3TGlzdGVuZXJcIiEgQmVmb3JlXG4gIC8vIGFkZGluZyBpdCB0byB0aGUgbGlzdGVuZXJzLCBmaXJzdCBlbWl0IFwibmV3TGlzdGVuZXJcIi5cbiAgaWYgKHRoaXMuX2V2ZW50cy5uZXdMaXN0ZW5lcilcbiAgICB0aGlzLmVtaXQoJ25ld0xpc3RlbmVyJywgdHlwZSxcbiAgICAgICAgICAgICAgaXNGdW5jdGlvbihsaXN0ZW5lci5saXN0ZW5lcikgP1xuICAgICAgICAgICAgICBsaXN0ZW5lci5saXN0ZW5lciA6IGxpc3RlbmVyKTtcblxuICBpZiAoIXRoaXMuX2V2ZW50c1t0eXBlXSlcbiAgICAvLyBPcHRpbWl6ZSB0aGUgY2FzZSBvZiBvbmUgbGlzdGVuZXIuIERvbid0IG5lZWQgdGhlIGV4dHJhIGFycmF5IG9iamVjdC5cbiAgICB0aGlzLl9ldmVudHNbdHlwZV0gPSBsaXN0ZW5lcjtcbiAgZWxzZSBpZiAoaXNPYmplY3QodGhpcy5fZXZlbnRzW3R5cGVdKSlcbiAgICAvLyBJZiB3ZSd2ZSBhbHJlYWR5IGdvdCBhbiBhcnJheSwganVzdCBhcHBlbmQuXG4gICAgdGhpcy5fZXZlbnRzW3R5cGVdLnB1c2gobGlzdGVuZXIpO1xuICBlbHNlXG4gICAgLy8gQWRkaW5nIHRoZSBzZWNvbmQgZWxlbWVudCwgbmVlZCB0byBjaGFuZ2UgdG8gYXJyYXkuXG4gICAgdGhpcy5fZXZlbnRzW3R5cGVdID0gW3RoaXMuX2V2ZW50c1t0eXBlXSwgbGlzdGVuZXJdO1xuXG4gIC8vIENoZWNrIGZvciBsaXN0ZW5lciBsZWFrXG4gIGlmIChpc09iamVjdCh0aGlzLl9ldmVudHNbdHlwZV0pICYmICF0aGlzLl9ldmVudHNbdHlwZV0ud2FybmVkKSB7XG4gICAgdmFyIG07XG4gICAgaWYgKCFpc1VuZGVmaW5lZCh0aGlzLl9tYXhMaXN0ZW5lcnMpKSB7XG4gICAgICBtID0gdGhpcy5fbWF4TGlzdGVuZXJzO1xuICAgIH0gZWxzZSB7XG4gICAgICBtID0gRXZlbnRFbWl0dGVyLmRlZmF1bHRNYXhMaXN0ZW5lcnM7XG4gICAgfVxuXG4gICAgaWYgKG0gJiYgbSA+IDAgJiYgdGhpcy5fZXZlbnRzW3R5cGVdLmxlbmd0aCA+IG0pIHtcbiAgICAgIHRoaXMuX2V2ZW50c1t0eXBlXS53YXJuZWQgPSB0cnVlO1xuICAgICAgY29uc29sZS5lcnJvcignKG5vZGUpIHdhcm5pbmc6IHBvc3NpYmxlIEV2ZW50RW1pdHRlciBtZW1vcnkgJyArXG4gICAgICAgICAgICAgICAgICAgICdsZWFrIGRldGVjdGVkLiAlZCBsaXN0ZW5lcnMgYWRkZWQuICcgK1xuICAgICAgICAgICAgICAgICAgICAnVXNlIGVtaXR0ZXIuc2V0TWF4TGlzdGVuZXJzKCkgdG8gaW5jcmVhc2UgbGltaXQuJyxcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5fZXZlbnRzW3R5cGVdLmxlbmd0aCk7XG4gICAgICBpZiAodHlwZW9mIGNvbnNvbGUudHJhY2UgPT09ICdmdW5jdGlvbicpIHtcbiAgICAgICAgLy8gbm90IHN1cHBvcnRlZCBpbiBJRSAxMFxuICAgICAgICBjb25zb2xlLnRyYWNlKCk7XG4gICAgICB9XG4gICAgfVxuICB9XG5cbiAgcmV0dXJuIHRoaXM7XG59O1xuXG5FdmVudEVtaXR0ZXIucHJvdG90eXBlLm9uID0gRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5hZGRMaXN0ZW5lcjtcblxuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5vbmNlID0gZnVuY3Rpb24odHlwZSwgbGlzdGVuZXIpIHtcbiAgaWYgKCFpc0Z1bmN0aW9uKGxpc3RlbmVyKSlcbiAgICB0aHJvdyBUeXBlRXJyb3IoJ2xpc3RlbmVyIG11c3QgYmUgYSBmdW5jdGlvbicpO1xuXG4gIHZhciBmaXJlZCA9IGZhbHNlO1xuXG4gIGZ1bmN0aW9uIGcoKSB7XG4gICAgdGhpcy5yZW1vdmVMaXN0ZW5lcih0eXBlLCBnKTtcblxuICAgIGlmICghZmlyZWQpIHtcbiAgICAgIGZpcmVkID0gdHJ1ZTtcbiAgICAgIGxpc3RlbmVyLmFwcGx5KHRoaXMsIGFyZ3VtZW50cyk7XG4gICAgfVxuICB9XG5cbiAgZy5saXN0ZW5lciA9IGxpc3RlbmVyO1xuICB0aGlzLm9uKHR5cGUsIGcpO1xuXG4gIHJldHVybiB0aGlzO1xufTtcblxuLy8gZW1pdHMgYSAncmVtb3ZlTGlzdGVuZXInIGV2ZW50IGlmZiB0aGUgbGlzdGVuZXIgd2FzIHJlbW92ZWRcbkV2ZW50RW1pdHRlci5wcm90b3R5cGUucmVtb3ZlTGlzdGVuZXIgPSBmdW5jdGlvbih0eXBlLCBsaXN0ZW5lcikge1xuICB2YXIgbGlzdCwgcG9zaXRpb24sIGxlbmd0aCwgaTtcblxuICBpZiAoIWlzRnVuY3Rpb24obGlzdGVuZXIpKVxuICAgIHRocm93IFR5cGVFcnJvcignbGlzdGVuZXIgbXVzdCBiZSBhIGZ1bmN0aW9uJyk7XG5cbiAgaWYgKCF0aGlzLl9ldmVudHMgfHwgIXRoaXMuX2V2ZW50c1t0eXBlXSlcbiAgICByZXR1cm4gdGhpcztcblxuICBsaXN0ID0gdGhpcy5fZXZlbnRzW3R5cGVdO1xuICBsZW5ndGggPSBsaXN0Lmxlbmd0aDtcbiAgcG9zaXRpb24gPSAtMTtcblxuICBpZiAobGlzdCA9PT0gbGlzdGVuZXIgfHxcbiAgICAgIChpc0Z1bmN0aW9uKGxpc3QubGlzdGVuZXIpICYmIGxpc3QubGlzdGVuZXIgPT09IGxpc3RlbmVyKSkge1xuICAgIGRlbGV0ZSB0aGlzLl9ldmVudHNbdHlwZV07XG4gICAgaWYgKHRoaXMuX2V2ZW50cy5yZW1vdmVMaXN0ZW5lcilcbiAgICAgIHRoaXMuZW1pdCgncmVtb3ZlTGlzdGVuZXInLCB0eXBlLCBsaXN0ZW5lcik7XG5cbiAgfSBlbHNlIGlmIChpc09iamVjdChsaXN0KSkge1xuICAgIGZvciAoaSA9IGxlbmd0aDsgaS0tID4gMDspIHtcbiAgICAgIGlmIChsaXN0W2ldID09PSBsaXN0ZW5lciB8fFxuICAgICAgICAgIChsaXN0W2ldLmxpc3RlbmVyICYmIGxpc3RbaV0ubGlzdGVuZXIgPT09IGxpc3RlbmVyKSkge1xuICAgICAgICBwb3NpdGlvbiA9IGk7XG4gICAgICAgIGJyZWFrO1xuICAgICAgfVxuICAgIH1cblxuICAgIGlmIChwb3NpdGlvbiA8IDApXG4gICAgICByZXR1cm4gdGhpcztcblxuICAgIGlmIChsaXN0Lmxlbmd0aCA9PT0gMSkge1xuICAgICAgbGlzdC5sZW5ndGggPSAwO1xuICAgICAgZGVsZXRlIHRoaXMuX2V2ZW50c1t0eXBlXTtcbiAgICB9IGVsc2Uge1xuICAgICAgbGlzdC5zcGxpY2UocG9zaXRpb24sIDEpO1xuICAgIH1cblxuICAgIGlmICh0aGlzLl9ldmVudHMucmVtb3ZlTGlzdGVuZXIpXG4gICAgICB0aGlzLmVtaXQoJ3JlbW92ZUxpc3RlbmVyJywgdHlwZSwgbGlzdGVuZXIpO1xuICB9XG5cbiAgcmV0dXJuIHRoaXM7XG59O1xuXG5FdmVudEVtaXR0ZXIucHJvdG90eXBlLnJlbW92ZUFsbExpc3RlbmVycyA9IGZ1bmN0aW9uKHR5cGUpIHtcbiAgdmFyIGtleSwgbGlzdGVuZXJzO1xuXG4gIGlmICghdGhpcy5fZXZlbnRzKVxuICAgIHJldHVybiB0aGlzO1xuXG4gIC8vIG5vdCBsaXN0ZW5pbmcgZm9yIHJlbW92ZUxpc3RlbmVyLCBubyBuZWVkIHRvIGVtaXRcbiAgaWYgKCF0aGlzLl9ldmVudHMucmVtb3ZlTGlzdGVuZXIpIHtcbiAgICBpZiAoYXJndW1lbnRzLmxlbmd0aCA9PT0gMClcbiAgICAgIHRoaXMuX2V2ZW50cyA9IHt9O1xuICAgIGVsc2UgaWYgKHRoaXMuX2V2ZW50c1t0eXBlXSlcbiAgICAgIGRlbGV0ZSB0aGlzLl9ldmVudHNbdHlwZV07XG4gICAgcmV0dXJuIHRoaXM7XG4gIH1cblxuICAvLyBlbWl0IHJlbW92ZUxpc3RlbmVyIGZvciBhbGwgbGlzdGVuZXJzIG9uIGFsbCBldmVudHNcbiAgaWYgKGFyZ3VtZW50cy5sZW5ndGggPT09IDApIHtcbiAgICBmb3IgKGtleSBpbiB0aGlzLl9ldmVudHMpIHtcbiAgICAgIGlmIChrZXkgPT09ICdyZW1vdmVMaXN0ZW5lcicpIGNvbnRpbnVlO1xuICAgICAgdGhpcy5yZW1vdmVBbGxMaXN0ZW5lcnMoa2V5KTtcbiAgICB9XG4gICAgdGhpcy5yZW1vdmVBbGxMaXN0ZW5lcnMoJ3JlbW92ZUxpc3RlbmVyJyk7XG4gICAgdGhpcy5fZXZlbnRzID0ge307XG4gICAgcmV0dXJuIHRoaXM7XG4gIH1cblxuICBsaXN0ZW5lcnMgPSB0aGlzLl9ldmVudHNbdHlwZV07XG5cbiAgaWYgKGlzRnVuY3Rpb24obGlzdGVuZXJzKSkge1xuICAgIHRoaXMucmVtb3ZlTGlzdGVuZXIodHlwZSwgbGlzdGVuZXJzKTtcbiAgfSBlbHNlIHtcbiAgICAvLyBMSUZPIG9yZGVyXG4gICAgd2hpbGUgKGxpc3RlbmVycy5sZW5ndGgpXG4gICAgICB0aGlzLnJlbW92ZUxpc3RlbmVyKHR5cGUsIGxpc3RlbmVyc1tsaXN0ZW5lcnMubGVuZ3RoIC0gMV0pO1xuICB9XG4gIGRlbGV0ZSB0aGlzLl9ldmVudHNbdHlwZV07XG5cbiAgcmV0dXJuIHRoaXM7XG59O1xuXG5FdmVudEVtaXR0ZXIucHJvdG90eXBlLmxpc3RlbmVycyA9IGZ1bmN0aW9uKHR5cGUpIHtcbiAgdmFyIHJldDtcbiAgaWYgKCF0aGlzLl9ldmVudHMgfHwgIXRoaXMuX2V2ZW50c1t0eXBlXSlcbiAgICByZXQgPSBbXTtcbiAgZWxzZSBpZiAoaXNGdW5jdGlvbih0aGlzLl9ldmVudHNbdHlwZV0pKVxuICAgIHJldCA9IFt0aGlzLl9ldmVudHNbdHlwZV1dO1xuICBlbHNlXG4gICAgcmV0ID0gdGhpcy5fZXZlbnRzW3R5cGVdLnNsaWNlKCk7XG4gIHJldHVybiByZXQ7XG59O1xuXG5FdmVudEVtaXR0ZXIubGlzdGVuZXJDb3VudCA9IGZ1bmN0aW9uKGVtaXR0ZXIsIHR5cGUpIHtcbiAgdmFyIHJldDtcbiAgaWYgKCFlbWl0dGVyLl9ldmVudHMgfHwgIWVtaXR0ZXIuX2V2ZW50c1t0eXBlXSlcbiAgICByZXQgPSAwO1xuICBlbHNlIGlmIChpc0Z1bmN0aW9uKGVtaXR0ZXIuX2V2ZW50c1t0eXBlXSkpXG4gICAgcmV0ID0gMTtcbiAgZWxzZVxuICAgIHJldCA9IGVtaXR0ZXIuX2V2ZW50c1t0eXBlXS5sZW5ndGg7XG4gIHJldHVybiByZXQ7XG59O1xuXG5mdW5jdGlvbiBpc0Z1bmN0aW9uKGFyZykge1xuICByZXR1cm4gdHlwZW9mIGFyZyA9PT0gJ2Z1bmN0aW9uJztcbn1cblxuZnVuY3Rpb24gaXNOdW1iZXIoYXJnKSB7XG4gIHJldHVybiB0eXBlb2YgYXJnID09PSAnbnVtYmVyJztcbn1cblxuZnVuY3Rpb24gaXNPYmplY3QoYXJnKSB7XG4gIHJldHVybiB0eXBlb2YgYXJnID09PSAnb2JqZWN0JyAmJiBhcmcgIT09IG51bGw7XG59XG5cbmZ1bmN0aW9uIGlzVW5kZWZpbmVkKGFyZykge1xuICByZXR1cm4gYXJnID09PSB2b2lkIDA7XG59XG4iLCJ2YXIgJCA9IHJlcXVpcmUoXCJqcXVlcnlcIik7XG5cbnZhciBBY3Rpb25UeXBlcyA9IHtcbiAgICAvLyBDb25uZWN0aW9uXG4gICAgQ09OTkVDVElPTl9PUEVOOiBcImNvbm5lY3Rpb25fb3BlblwiLFxuICAgIENPTk5FQ1RJT05fQ0xPU0U6IFwiY29ubmVjdGlvbl9jbG9zZVwiLFxuICAgIENPTk5FQ1RJT05fRVJST1I6IFwiY29ubmVjdGlvbl9lcnJvclwiLFxuXG4gICAgLy8gU3RvcmVzXG4gICAgU0VUVElOR1NfU1RPUkU6IFwic2V0dGluZ3NcIixcbiAgICBFVkVOVF9TVE9SRTogXCJldmVudHNcIixcbiAgICBGTE9XX1NUT1JFOiBcImZsb3dzXCIsXG59O1xuXG52YXIgU3RvcmVDbWRzID0ge1xuICAgIEFERDogXCJhZGRcIixcbiAgICBVUERBVEU6IFwidXBkYXRlXCIsXG4gICAgUkVNT1ZFOiBcInJlbW92ZVwiLFxuICAgIFJFU0VUOiBcInJlc2V0XCJcbn07XG5cbnZhciBDb25uZWN0aW9uQWN0aW9ucyA9IHtcbiAgICBvcGVuOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIEFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uKHtcbiAgICAgICAgICAgIHR5cGU6IEFjdGlvblR5cGVzLkNPTk5FQ1RJT05fT1BFTlxuICAgICAgICB9KTtcbiAgICB9LFxuICAgIGNsb3NlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIEFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uKHtcbiAgICAgICAgICAgIHR5cGU6IEFjdGlvblR5cGVzLkNPTk5FQ1RJT05fQ0xPU0VcbiAgICAgICAgfSk7XG4gICAgfSxcbiAgICBlcnJvcjogZnVuY3Rpb24gKCkge1xuICAgICAgICBBcHBEaXNwYXRjaGVyLmRpc3BhdGNoVmlld0FjdGlvbih7XG4gICAgICAgICAgICB0eXBlOiBBY3Rpb25UeXBlcy5DT05ORUNUSU9OX0VSUk9SXG4gICAgICAgIH0pO1xuICAgIH1cbn07XG5cbnZhciBTZXR0aW5nc0FjdGlvbnMgPSB7XG4gICAgdXBkYXRlOiBmdW5jdGlvbiAoc2V0dGluZ3MpIHtcblxuICAgICAgICAkLmFqYXgoe1xuICAgICAgICAgICAgdHlwZTogXCJQVVRcIixcbiAgICAgICAgICAgIHVybDogXCIvc2V0dGluZ3NcIixcbiAgICAgICAgICAgIGRhdGE6IHNldHRpbmdzXG4gICAgICAgIH0pO1xuXG4gICAgICAgIC8qXG4gICAgICAgIC8vRmFjZWJvb2sgRmx1eDogV2UgZG8gYW4gb3B0aW1pc3RpYyB1cGRhdGUgb24gdGhlIGNsaWVudCBhbHJlYWR5LlxuICAgICAgICBBcHBEaXNwYXRjaGVyLmRpc3BhdGNoVmlld0FjdGlvbih7XG4gICAgICAgICAgICB0eXBlOiBBY3Rpb25UeXBlcy5TRVRUSU5HU19TVE9SRSxcbiAgICAgICAgICAgIGNtZDogU3RvcmVDbWRzLlVQREFURSxcbiAgICAgICAgICAgIGRhdGE6IHNldHRpbmdzXG4gICAgICAgIH0pO1xuICAgICAgICAqL1xuICAgIH1cbn07XG5cbnZhciBFdmVudExvZ0FjdGlvbnNfZXZlbnRfaWQgPSAwO1xudmFyIEV2ZW50TG9nQWN0aW9ucyA9IHtcbiAgICBhZGRfZXZlbnQ6IGZ1bmN0aW9uIChtZXNzYWdlKSB7XG4gICAgICAgIEFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uKHtcbiAgICAgICAgICAgIHR5cGU6IEFjdGlvblR5cGVzLkVWRU5UX1NUT1JFLFxuICAgICAgICAgICAgY21kOiBTdG9yZUNtZHMuQURELFxuICAgICAgICAgICAgZGF0YToge1xuICAgICAgICAgICAgICAgIG1lc3NhZ2U6IG1lc3NhZ2UsXG4gICAgICAgICAgICAgICAgbGV2ZWw6IFwid2ViXCIsXG4gICAgICAgICAgICAgICAgaWQ6IFwidmlld0FjdGlvbi1cIiArIEV2ZW50TG9nQWN0aW9uc19ldmVudF9pZCsrXG4gICAgICAgICAgICB9XG4gICAgICAgIH0pO1xuICAgIH1cbn07XG5cbnZhciBGbG93QWN0aW9ucyA9IHtcbiAgICBhY2NlcHQ6IGZ1bmN0aW9uIChmbG93KSB7XG4gICAgICAgICQucG9zdChcIi9mbG93cy9cIiArIGZsb3cuaWQgKyBcIi9hY2NlcHRcIik7XG4gICAgfSxcbiAgICBhY2NlcHRfYWxsOiBmdW5jdGlvbigpe1xuICAgICAgICAkLnBvc3QoXCIvZmxvd3MvYWNjZXB0XCIpO1xuICAgIH0sXG4gICAgXCJkZWxldGVcIjogZnVuY3Rpb24oZmxvdyl7XG4gICAgICAgICQuYWpheCh7XG4gICAgICAgICAgICB0eXBlOlwiREVMRVRFXCIsXG4gICAgICAgICAgICB1cmw6IFwiL2Zsb3dzL1wiICsgZmxvdy5pZFxuICAgICAgICB9KTtcbiAgICB9LFxuICAgIGR1cGxpY2F0ZTogZnVuY3Rpb24oZmxvdyl7XG4gICAgICAgICQucG9zdChcIi9mbG93cy9cIiArIGZsb3cuaWQgKyBcIi9kdXBsaWNhdGVcIik7XG4gICAgfSxcbiAgICByZXBsYXk6IGZ1bmN0aW9uKGZsb3cpe1xuICAgICAgICAkLnBvc3QoXCIvZmxvd3MvXCIgKyBmbG93LmlkICsgXCIvcmVwbGF5XCIpO1xuICAgIH0sXG4gICAgcmV2ZXJ0OiBmdW5jdGlvbihmbG93KXtcbiAgICAgICAgJC5wb3N0KFwiL2Zsb3dzL1wiICsgZmxvdy5pZCArIFwiL3JldmVydFwiKTtcbiAgICB9LFxuICAgIHVwZGF0ZTogZnVuY3Rpb24gKGZsb3cpIHtcbiAgICAgICAgQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFZpZXdBY3Rpb24oe1xuICAgICAgICAgICAgdHlwZTogQWN0aW9uVHlwZXMuRkxPV19TVE9SRSxcbiAgICAgICAgICAgIGNtZDogU3RvcmVDbWRzLlVQREFURSxcbiAgICAgICAgICAgIGRhdGE6IGZsb3dcbiAgICAgICAgfSk7XG4gICAgfSxcbiAgICBjbGVhcjogZnVuY3Rpb24oKXtcbiAgICAgICAgJC5wb3N0KFwiL2NsZWFyXCIpO1xuICAgIH1cbn07XG5cblF1ZXJ5ID0ge1xuICAgIEZJTFRFUjogXCJmXCIsXG4gICAgSElHSExJR0hUOiBcImhcIixcbiAgICBTSE9XX0VWRU5UTE9HOiBcImVcIlxufTtcblxubW9kdWxlLmV4cG9ydHMgPSB7XG4gICAgQWN0aW9uVHlwZXM6IEFjdGlvblR5cGVzLFxuICAgIENvbm5lY3Rpb25BY3Rpb25zOiBDb25uZWN0aW9uQWN0aW9ucyxcbiAgICBGbG93QWN0aW9uczogRmxvd0FjdGlvbnMsXG4gICAgU3RvcmVDbWRzOiBTdG9yZUNtZHNcbn07IiwiXG52YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XG52YXIgUmVhY3RSb3V0ZXIgPSByZXF1aXJlKFwicmVhY3Qtcm91dGVyXCIpO1xudmFyICQgPSByZXF1aXJlKFwianF1ZXJ5XCIpO1xuXG52YXIgQ29ubmVjdGlvbiA9IHJlcXVpcmUoXCIuL2Nvbm5lY3Rpb25cIik7XG52YXIgcHJveHlhcHAgPSByZXF1aXJlKFwiLi9jb21wb25lbnRzL3Byb3h5YXBwLmpzXCIpO1xuXG4kKGZ1bmN0aW9uICgpIHtcbiAgICB3aW5kb3cud3MgPSBuZXcgQ29ubmVjdGlvbihcIi91cGRhdGVzXCIpO1xuXG4gICAgUmVhY3RSb3V0ZXIucnVuKHByb3h5YXBwLnJvdXRlcywgZnVuY3Rpb24gKEhhbmRsZXIpIHtcbiAgICAgICAgUmVhY3QucmVuZGVyKFJlYWN0LmNyZWF0ZUVsZW1lbnQoSGFuZGxlciwgbnVsbCksIGRvY3VtZW50LmJvZHkpO1xuICAgIH0pO1xufSk7IiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xudmFyIHV0aWxzID0gcmVxdWlyZShcIi4vdXRpbHMuanNcIik7XG52YXIgVmlydHVhbFNjcm9sbE1peGluID0gcmVxdWlyZShcIi4vdmlydHVhbHNjcm9sbC5qc1wiKTtcbnZhciB2aWV3cyA9IHJlcXVpcmUoXCIuLi9zdG9yZS92aWV3LmpzXCIpO1xuXG52YXIgTG9nTWVzc2FnZSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJMb2dNZXNzYWdlXCIsXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBlbnRyeSA9IHRoaXMucHJvcHMuZW50cnk7XG4gICAgICAgIHZhciBpbmRpY2F0b3I7XG4gICAgICAgIHN3aXRjaCAoZW50cnkubGV2ZWwpIHtcbiAgICAgICAgICAgIGNhc2UgXCJ3ZWJcIjpcbiAgICAgICAgICAgICAgICBpbmRpY2F0b3IgPSBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaVwiLCB7Y2xhc3NOYW1lOiBcImZhIGZhLWZ3IGZhLWh0bWw1XCJ9KTtcbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgXCJkZWJ1Z1wiOlxuICAgICAgICAgICAgICAgIGluZGljYXRvciA9IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJpXCIsIHtjbGFzc05hbWU6IFwiZmEgZmEtZncgZmEtYnVnXCJ9KTtcbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGRlZmF1bHQ6XG4gICAgICAgICAgICAgICAgaW5kaWNhdG9yID0gUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge2NsYXNzTmFtZTogXCJmYSBmYS1mdyBmYS1pbmZvXCJ9KTtcbiAgICAgICAgfVxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICBpbmRpY2F0b3IsIFwiIFwiLCBlbnRyeS5tZXNzYWdlXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfSxcbiAgICBzaG91bGRDb21wb25lbnRVcGRhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIGZhbHNlOyAvLyBsb2cgZW50cmllcyBhcmUgaW1tdXRhYmxlLlxuICAgIH1cbn0pO1xuXG52YXIgRXZlbnRMb2dDb250ZW50cyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJFdmVudExvZ0NvbnRlbnRzXCIsXG4gICAgbWl4aW5zOiBbdXRpbHMuQXV0b1Njcm9sbE1peGluLCBWaXJ0dWFsU2Nyb2xsTWl4aW5dLFxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgbG9nOiBbXVxuICAgICAgICB9O1xuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbE1vdW50OiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMub3BlblZpZXcodGhpcy5wcm9wcy5ldmVudFN0b3JlKTtcbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxVbm1vdW50OiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuY2xvc2VWaWV3KCk7XG4gICAgfSxcbiAgICBvcGVuVmlldzogZnVuY3Rpb24gKHN0b3JlKSB7XG4gICAgICAgIHZhciB2aWV3ID0gbmV3IHZpZXdzLlN0b3JlVmlldyhzdG9yZSwgZnVuY3Rpb24gKGVudHJ5KSB7XG4gICAgICAgICAgICByZXR1cm4gdGhpcy5wcm9wcy5maWx0ZXJbZW50cnkubGV2ZWxdO1xuICAgICAgICB9LmJpbmQodGhpcykpO1xuICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgIHZpZXc6IHZpZXdcbiAgICAgICAgfSk7XG5cbiAgICAgICAgdmlldy5hZGRMaXN0ZW5lcihcImFkZCByZWNhbGN1bGF0ZVwiLCB0aGlzLm9uRXZlbnRMb2dDaGFuZ2UpO1xuICAgIH0sXG4gICAgY2xvc2VWaWV3OiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuc3RhdGUudmlldy5jbG9zZSgpO1xuICAgIH0sXG4gICAgb25FdmVudExvZ0NoYW5nZTogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgIGxvZzogdGhpcy5zdGF0ZS52aWV3Lmxpc3RcbiAgICAgICAgfSk7XG4gICAgfSxcbiAgICBjb21wb25lbnRXaWxsUmVjZWl2ZVByb3BzOiBmdW5jdGlvbiAobmV4dFByb3BzKSB7XG4gICAgICAgIGlmIChuZXh0UHJvcHMuZmlsdGVyICE9PSB0aGlzLnByb3BzLmZpbHRlcikge1xuICAgICAgICAgICAgdGhpcy5wcm9wcy5maWx0ZXIgPSBuZXh0UHJvcHMuZmlsdGVyOyAvLyBEaXJ0eTogTWFrZSBzdXJlIHRoYXQgdmlldyBmaWx0ZXIgc2VlcyB0aGUgdXBkYXRlLlxuICAgICAgICAgICAgdGhpcy5zdGF0ZS52aWV3LnJlY2FsY3VsYXRlKCk7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKG5leHRQcm9wcy5ldmVudFN0b3JlICE9PSB0aGlzLnByb3BzLmV2ZW50U3RvcmUpIHtcbiAgICAgICAgICAgIHRoaXMuY2xvc2VWaWV3KCk7XG4gICAgICAgICAgICB0aGlzLm9wZW5WaWV3KG5leHRQcm9wcy5ldmVudFN0b3JlKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgZ2V0RGVmYXVsdFByb3BzOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHJldHVybiB7XG4gICAgICAgICAgICByb3dIZWlnaHQ6IDQ1LFxuICAgICAgICAgICAgcm93SGVpZ2h0TWluOiAxNSxcbiAgICAgICAgICAgIHBsYWNlaG9sZGVyVGFnTmFtZTogXCJkaXZcIlxuICAgICAgICB9O1xuICAgIH0sXG4gICAgcmVuZGVyUm93OiBmdW5jdGlvbiAoZWxlbSkge1xuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChMb2dNZXNzYWdlLCB7a2V5OiBlbGVtLmlkLCBlbnRyeTogZWxlbX0pO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciByb3dzID0gdGhpcy5yZW5kZXJSb3dzKHRoaXMuc3RhdGUubG9nKTtcblxuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInByZVwiLCB7b25TY3JvbGw6IHRoaXMub25TY3JvbGx9LCBcbiAgICAgICAgICAgICB0aGlzLmdldFBsYWNlaG9sZGVyVG9wKHRoaXMuc3RhdGUubG9nLmxlbmd0aCksIFxuICAgICAgICAgICAgcm93cywgXG4gICAgICAgICAgICAgdGhpcy5nZXRQbGFjZWhvbGRlckJvdHRvbSh0aGlzLnN0YXRlLmxvZy5sZW5ndGgpIFxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgVG9nZ2xlRmlsdGVyID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlRvZ2dsZUZpbHRlclwiLFxuICAgIHRvZ2dsZTogZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICByZXR1cm4gdGhpcy5wcm9wcy50b2dnbGVMZXZlbCh0aGlzLnByb3BzLm5hbWUpO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBjbGFzc05hbWUgPSBcImxhYmVsIFwiO1xuICAgICAgICBpZiAodGhpcy5wcm9wcy5hY3RpdmUpIHtcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcImxhYmVsLXByaW1hcnlcIjtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcImxhYmVsLWRlZmF1bHRcIjtcbiAgICAgICAgfVxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImFcIiwge1xuICAgICAgICAgICAgICAgIGhyZWY6IFwiI1wiLCBcbiAgICAgICAgICAgICAgICBjbGFzc05hbWU6IGNsYXNzTmFtZSwgXG4gICAgICAgICAgICAgICAgb25DbGljazogdGhpcy50b2dnbGV9LCBcbiAgICAgICAgICAgICAgICB0aGlzLnByb3BzLm5hbWVcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxudmFyIEV2ZW50TG9nID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkV2ZW50TG9nXCIsXG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHJldHVybiB7XG4gICAgICAgICAgICBmaWx0ZXI6IHtcbiAgICAgICAgICAgICAgICBcImRlYnVnXCI6IGZhbHNlLFxuICAgICAgICAgICAgICAgIFwiaW5mb1wiOiB0cnVlLFxuICAgICAgICAgICAgICAgIFwid2ViXCI6IHRydWVcbiAgICAgICAgICAgIH1cbiAgICAgICAgfTtcbiAgICB9LFxuICAgIGNsb3NlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBkID0ge307XG4gICAgICAgIGRbUXVlcnkuU0hPV19FVkVOVExPR10gPSB1bmRlZmluZWQ7XG4gICAgICAgIHRoaXMuc2V0UXVlcnkoZCk7XG4gICAgfSxcbiAgICB0b2dnbGVMZXZlbDogZnVuY3Rpb24gKGxldmVsKSB7XG4gICAgICAgIHZhciBmaWx0ZXIgPSBfLmV4dGVuZCh7fSwgdGhpcy5zdGF0ZS5maWx0ZXIpO1xuICAgICAgICBmaWx0ZXJbbGV2ZWxdID0gIWZpbHRlcltsZXZlbF07XG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe2ZpbHRlcjogZmlsdGVyfSk7XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJldmVudGxvZ1wifSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICAgICAgXCJFdmVudGxvZ1wiLCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcInB1bGwtcmlnaHRcIn0sIFxuICAgICAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChUb2dnbGVGaWx0ZXIsIHtuYW1lOiBcImRlYnVnXCIsIGFjdGl2ZTogdGhpcy5zdGF0ZS5maWx0ZXIuZGVidWcsIHRvZ2dsZUxldmVsOiB0aGlzLnRvZ2dsZUxldmVsfSksIFxuICAgICAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChUb2dnbGVGaWx0ZXIsIHtuYW1lOiBcImluZm9cIiwgYWN0aXZlOiB0aGlzLnN0YXRlLmZpbHRlci5pbmZvLCB0b2dnbGVMZXZlbDogdGhpcy50b2dnbGVMZXZlbH0pLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoVG9nZ2xlRmlsdGVyLCB7bmFtZTogXCJ3ZWJcIiwgYWN0aXZlOiB0aGlzLnN0YXRlLmZpbHRlci53ZWIsIHRvZ2dsZUxldmVsOiB0aGlzLnRvZ2dsZUxldmVsfSksIFxuICAgICAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge29uQ2xpY2s6IHRoaXMuY2xvc2UsIGNsYXNzTmFtZTogXCJmYSBmYS1jbG9zZVwifSlcbiAgICAgICAgICAgICAgICAgICAgKVxuXG4gICAgICAgICAgICAgICAgKSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChFdmVudExvZ0NvbnRlbnRzLCB7ZmlsdGVyOiB0aGlzLnN0YXRlLmZpbHRlciwgZXZlbnRTdG9yZTogdGhpcy5wcm9wcy5ldmVudFN0b3JlfSlcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxubW9kdWxlLmV4cG9ydHMgPSBFdmVudExvZzsiLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XG52YXIgXyA9IHJlcXVpcmUoXCJsb2Rhc2hcIik7XG5cbnZhciB1dGlscyA9IHJlcXVpcmUoXCIuL3V0aWxzLmpzXCIpO1xudmFyIGFjdGlvbnMgPSByZXF1aXJlKFwiLi4vYWN0aW9ucy5qc1wiKTtcbnZhciBmbG93dXRpbHMgPSByZXF1aXJlKFwiLi4vZmxvdy91dGlscy5qc1wiKTtcbnZhciB0b3B1dGlscyA9IHJlcXVpcmUoXCIuLi91dGlscy5qc1wiKTtcblxudmFyIE5hdkFjdGlvbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJOYXZBY3Rpb25cIixcbiAgICBvbkNsaWNrOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XG4gICAgICAgIHRoaXMucHJvcHMub25DbGljaygpO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiYVwiLCB7dGl0bGU6IHRoaXMucHJvcHMudGl0bGUsIFxuICAgICAgICAgICAgICAgIGhyZWY6IFwiI1wiLCBcbiAgICAgICAgICAgICAgICBjbGFzc05hbWU6IFwibmF2LWFjdGlvblwiLCBcbiAgICAgICAgICAgICAgICBvbkNsaWNrOiB0aGlzLm9uQ2xpY2t9LCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaVwiLCB7Y2xhc3NOYW1lOiBcImZhIGZhLWZ3IFwiICsgdGhpcy5wcm9wcy5pY29ufSlcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxudmFyIEZsb3dEZXRhaWxOYXYgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiRmxvd0RldGFpbE5hdlwiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcblxuICAgICAgICB2YXIgdGFicyA9IHRoaXMucHJvcHMudGFicy5tYXAoZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgICAgIHZhciBzdHIgPSBlLmNoYXJBdCgwKS50b1VwcGVyQ2FzZSgpICsgZS5zbGljZSgxKTtcbiAgICAgICAgICAgIHZhciBjbGFzc05hbWUgPSB0aGlzLnByb3BzLmFjdGl2ZSA9PT0gZSA/IFwiYWN0aXZlXCIgOiBcIlwiO1xuICAgICAgICAgICAgdmFyIG9uQ2xpY2sgPSBmdW5jdGlvbiAoZXZlbnQpIHtcbiAgICAgICAgICAgICAgICB0aGlzLnByb3BzLnNlbGVjdFRhYihlKTtcbiAgICAgICAgICAgICAgICBldmVudC5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICAgICAgfS5iaW5kKHRoaXMpO1xuICAgICAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJhXCIsIHtrZXk6IGUsIFxuICAgICAgICAgICAgICAgIGhyZWY6IFwiI1wiLCBcbiAgICAgICAgICAgICAgICBjbGFzc05hbWU6IGNsYXNzTmFtZSwgXG4gICAgICAgICAgICAgICAgb25DbGljazogb25DbGlja30sIHN0cik7XG4gICAgICAgIH0uYmluZCh0aGlzKSk7XG5cbiAgICAgICAgdmFyIGFjY2VwdEJ1dHRvbiA9IG51bGw7XG4gICAgICAgIGlmKGZsb3cuaW50ZXJjZXB0ZWQpe1xuICAgICAgICAgICAgYWNjZXB0QnV0dG9uID0gUmVhY3QuY3JlYXRlRWxlbWVudChOYXZBY3Rpb24sIHt0aXRsZTogXCJbYV1jY2VwdCBpbnRlcmNlcHRlZCBmbG93XCIsIGljb246IFwiZmEtcGxheVwiLCBvbkNsaWNrOiBhY3Rpb25zLkZsb3dBY3Rpb25zLmFjY2VwdC5iaW5kKG51bGwsIGZsb3cpfSk7XG4gICAgICAgIH1cbiAgICAgICAgdmFyIHJldmVydEJ1dHRvbiA9IG51bGw7XG4gICAgICAgIGlmKGZsb3cubW9kaWZpZWQpe1xuICAgICAgICAgICAgcmV2ZXJ0QnV0dG9uID0gUmVhY3QuY3JlYXRlRWxlbWVudChOYXZBY3Rpb24sIHt0aXRsZTogXCJyZXZlcnQgY2hhbmdlcyB0byBmbG93IFtWXVwiLCBpY29uOiBcImZhLWhpc3RvcnlcIiwgb25DbGljazogYWN0aW9ucy5GbG93QWN0aW9ucy5yZXZlcnQuYmluZChudWxsLCBmbG93KX0pO1xuICAgICAgICB9XG5cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJuYXZcIiwge3JlZjogXCJoZWFkXCIsIGNsYXNzTmFtZTogXCJuYXYtdGFicyBuYXYtdGFicy1zbVwifSwgXG4gICAgICAgICAgICAgICAgdGFicywgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChOYXZBY3Rpb24sIHt0aXRsZTogXCJbZF1lbGV0ZSBmbG93XCIsIGljb246IFwiZmEtdHJhc2hcIiwgb25DbGljazogYWN0aW9ucy5GbG93QWN0aW9ucy5kZWxldGUuYmluZChudWxsLCBmbG93KX0pLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KE5hdkFjdGlvbiwge3RpdGxlOiBcIltEXXVwbGljYXRlIGZsb3dcIiwgaWNvbjogXCJmYS1jb3B5XCIsIG9uQ2xpY2s6IGFjdGlvbnMuRmxvd0FjdGlvbnMuZHVwbGljYXRlLmJpbmQobnVsbCwgZmxvdyl9KSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChOYXZBY3Rpb24sIHtkaXNhYmxlZDogdHJ1ZSwgdGl0bGU6IFwiW3JdZXBsYXkgZmxvd1wiLCBpY29uOiBcImZhLXJlcGVhdFwiLCBvbkNsaWNrOiBhY3Rpb25zLkZsb3dBY3Rpb25zLnJlcGxheS5iaW5kKG51bGwsIGZsb3cpfSksIFxuICAgICAgICAgICAgICAgIGFjY2VwdEJ1dHRvbiwgXG4gICAgICAgICAgICAgICAgcmV2ZXJ0QnV0dG9uXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBIZWFkZXJzID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkhlYWRlcnNcIixcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIHJvd3MgPSB0aGlzLnByb3BzLm1lc3NhZ2UuaGVhZGVycy5tYXAoZnVuY3Rpb24gKGhlYWRlciwgaSkge1xuICAgICAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidHJcIiwge2tleTogaX0sIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwge2NsYXNzTmFtZTogXCJoZWFkZXItbmFtZVwifSwgaGVhZGVyWzBdICsgXCI6XCIpLCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIHtjbGFzc05hbWU6IFwiaGVhZGVyLXZhbHVlXCJ9LCBoZWFkZXJbMV0pXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKTtcbiAgICAgICAgfSk7XG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGFibGVcIiwge2NsYXNzTmFtZTogXCJoZWFkZXItdGFibGVcIn0sIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0Ym9keVwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICAgICAgcm93c1xuICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxudmFyIEZsb3dEZXRhaWxSZXF1ZXN0ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZsb3dEZXRhaWxSZXF1ZXN0XCIsXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuICAgICAgICB2YXIgZmlyc3RfbGluZSA9IFtcbiAgICAgICAgICAgIGZsb3cucmVxdWVzdC5tZXRob2QsXG4gICAgICAgICAgICBmbG93dXRpbHMuUmVxdWVzdFV0aWxzLnByZXR0eV91cmwoZmxvdy5yZXF1ZXN0KSxcbiAgICAgICAgICAgIFwiSFRUUC9cIiArIGZsb3cucmVxdWVzdC5odHRwdmVyc2lvbi5qb2luKFwiLlwiKVxuICAgICAgICBdLmpvaW4oXCIgXCIpO1xuICAgICAgICB2YXIgY29udGVudCA9IG51bGw7XG4gICAgICAgIGlmIChmbG93LnJlcXVlc3QuY29udGVudExlbmd0aCA+IDApIHtcbiAgICAgICAgICAgIGNvbnRlbnQgPSBcIlJlcXVlc3QgQ29udGVudCBTaXplOiBcIiArIHRvcHV0aWxzLmZvcm1hdFNpemUoZmxvdy5yZXF1ZXN0LmNvbnRlbnRMZW5ndGgpO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgY29udGVudCA9IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJhbGVydCBhbGVydC1pbmZvXCJ9LCBcIk5vIENvbnRlbnRcIik7XG4gICAgICAgIH1cblxuICAgICAgICAvL1RPRE86IFN0eWxpbmdcblxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInNlY3Rpb25cIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcImZpcnN0LWxpbmVcIn0sIGZpcnN0X2xpbmUgKSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChIZWFkZXJzLCB7bWVzc2FnZTogZmxvdy5yZXF1ZXN0fSksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJoclwiLCBudWxsKSwgXG4gICAgICAgICAgICAgICAgY29udGVudFxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgRmxvd0RldGFpbFJlc3BvbnNlID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZsb3dEZXRhaWxSZXNwb25zZVwiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgdmFyIGZpcnN0X2xpbmUgPSBbXG4gICAgICAgICAgICBcIkhUVFAvXCIgKyBmbG93LnJlc3BvbnNlLmh0dHB2ZXJzaW9uLmpvaW4oXCIuXCIpLFxuICAgICAgICAgICAgZmxvdy5yZXNwb25zZS5jb2RlLFxuICAgICAgICAgICAgZmxvdy5yZXNwb25zZS5tc2dcbiAgICAgICAgXS5qb2luKFwiIFwiKTtcbiAgICAgICAgdmFyIGNvbnRlbnQgPSBudWxsO1xuICAgICAgICBpZiAoZmxvdy5yZXNwb25zZS5jb250ZW50TGVuZ3RoID4gMCkge1xuICAgICAgICAgICAgY29udGVudCA9IFwiUmVzcG9uc2UgQ29udGVudCBTaXplOiBcIiArIHRvcHV0aWxzLmZvcm1hdFNpemUoZmxvdy5yZXNwb25zZS5jb250ZW50TGVuZ3RoKTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGNvbnRlbnQgPSBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwiYWxlcnQgYWxlcnQtaW5mb1wifSwgXCJObyBDb250ZW50XCIpO1xuICAgICAgICB9XG5cbiAgICAgICAgLy9UT0RPOiBTdHlsaW5nXG5cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJzZWN0aW9uXCIsIG51bGwsIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJmaXJzdC1saW5lXCJ9LCBmaXJzdF9saW5lICksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoSGVhZGVycywge21lc3NhZ2U6IGZsb3cucmVzcG9uc2V9KSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImhyXCIsIG51bGwpLCBcbiAgICAgICAgICAgICAgICBjb250ZW50XG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBGbG93RGV0YWlsRXJyb3IgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiRmxvd0RldGFpbEVycm9yXCIsXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInNlY3Rpb25cIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcImFsZXJ0IGFsZXJ0LXdhcm5pbmdcIn0sIFxuICAgICAgICAgICAgICAgIGZsb3cuZXJyb3IubXNnLCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJzbWFsbFwiLCBudWxsLCAgdG9wdXRpbHMuZm9ybWF0VGltZVN0YW1wKGZsb3cuZXJyb3IudGltZXN0YW1wKSApXG4gICAgICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBUaW1lU3RhbXAgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiVGltZVN0YW1wXCIsXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG5cbiAgICAgICAgaWYgKCF0aGlzLnByb3BzLnQpIHtcbiAgICAgICAgICAgIC8vc2hvdWxkIGJlIHJldHVybiBudWxsLCBidXQgdGhhdCB0cmlnZ2VycyBhIFJlYWN0IGJ1Zy5cbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidHJcIiwgbnVsbCk7XG4gICAgICAgIH1cblxuICAgICAgICB2YXIgdHMgPSB0b3B1dGlscy5mb3JtYXRUaW1lU3RhbXAodGhpcy5wcm9wcy50KTtcblxuICAgICAgICB2YXIgZGVsdGE7XG4gICAgICAgIGlmICh0aGlzLnByb3BzLmRlbHRhVG8pIHtcbiAgICAgICAgICAgIGRlbHRhID0gdG9wdXRpbHMuZm9ybWF0VGltZURlbHRhKDEwMDAgKiAodGhpcy5wcm9wcy50IC0gdGhpcy5wcm9wcy5kZWx0YVRvKSk7XG4gICAgICAgICAgICBkZWx0YSA9IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIsIHtjbGFzc05hbWU6IFwidGV4dC1tdXRlZFwifSwgXCIoXCIgKyBkZWx0YSArIFwiKVwiKTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGRlbHRhID0gbnVsbDtcbiAgICAgICAgfVxuXG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidHJcIiwgbnVsbCwgXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwgbnVsbCwgdGhpcy5wcm9wcy50aXRsZSArIFwiOlwiKSwgXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwgbnVsbCwgdHMsIFwiIFwiLCBkZWx0YSlcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxudmFyIENvbm5lY3Rpb25JbmZvID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkNvbm5lY3Rpb25JbmZvXCIsXG5cbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGNvbm4gPSB0aGlzLnByb3BzLmNvbm47XG4gICAgICAgIHZhciBhZGRyZXNzID0gY29ubi5hZGRyZXNzLmFkZHJlc3Muam9pbihcIjpcIik7XG5cbiAgICAgICAgdmFyIHNuaSA9IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0clwiLCB7a2V5OiBcInNuaVwifSk7IC8vc2hvdWxkIGJlIG51bGwsIGJ1dCB0aGF0IHRyaWdnZXJzIGEgUmVhY3QgYnVnLlxuICAgICAgICBpZiAoY29ubi5zbmkpIHtcbiAgICAgICAgICAgIHNuaSA9IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0clwiLCB7a2V5OiBcInNuaVwifSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIG51bGwsIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiYWJiclwiLCB7dGl0bGU6IFwiVExTIFNlcnZlciBOYW1lIEluZGljYXRpb25cIn0sIFwiVExTIFNOSTpcIilcbiAgICAgICAgICAgICAgICApLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwgbnVsbCwgY29ubi5zbmkpXG4gICAgICAgICAgICApO1xuICAgICAgICB9XG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGFibGVcIiwge2NsYXNzTmFtZTogXCJjb25uZWN0aW9uLXRhYmxlXCJ9LCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGJvZHlcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0clwiLCB7a2V5OiBcImFkZHJlc3NcIn0sIFxuICAgICAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIG51bGwsIFwiQWRkcmVzczpcIiksIFxuICAgICAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIG51bGwsIGFkZHJlc3MpXG4gICAgICAgICAgICAgICAgICAgICksIFxuICAgICAgICAgICAgICAgICAgICBzbmlcbiAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBDZXJ0aWZpY2F0ZUluZm8gPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiQ2VydGlmaWNhdGVJbmZvXCIsXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIC8vVE9ETzogV2Ugc2hvdWxkIGZldGNoIGh1bWFuLXJlYWRhYmxlIGNlcnRpZmljYXRlIHJlcHJlc2VudGF0aW9uXG4gICAgICAgIC8vIGZyb20gdGhlIHNlcnZlclxuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgdmFyIGNsaWVudF9jb25uID0gZmxvdy5jbGllbnRfY29ubjtcbiAgICAgICAgdmFyIHNlcnZlcl9jb25uID0gZmxvdy5zZXJ2ZXJfY29ubjtcblxuICAgICAgICB2YXIgcHJlU3R5bGUgPSB7bWF4SGVpZ2h0OiAxMDB9O1xuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCBudWxsLCBcbiAgICAgICAgICAgIGNsaWVudF9jb25uLmNlcnQgPyBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaDRcIiwgbnVsbCwgXCJDbGllbnQgQ2VydGlmaWNhdGVcIikgOiBudWxsLCBcbiAgICAgICAgICAgIGNsaWVudF9jb25uLmNlcnQgPyBSZWFjdC5jcmVhdGVFbGVtZW50KFwicHJlXCIsIHtzdHlsZTogcHJlU3R5bGV9LCBjbGllbnRfY29ubi5jZXJ0KSA6IG51bGwsIFxuXG4gICAgICAgICAgICBzZXJ2ZXJfY29ubi5jZXJ0ID8gUmVhY3QuY3JlYXRlRWxlbWVudChcImg0XCIsIG51bGwsIFwiU2VydmVyIENlcnRpZmljYXRlXCIpIDogbnVsbCwgXG4gICAgICAgICAgICBzZXJ2ZXJfY29ubi5jZXJ0ID8gUmVhY3QuY3JlYXRlRWxlbWVudChcInByZVwiLCB7c3R5bGU6IHByZVN0eWxlfSwgc2VydmVyX2Nvbm4uY2VydCkgOiBudWxsXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBUaW1pbmcgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiVGltaW5nXCIsXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuICAgICAgICB2YXIgc2MgPSBmbG93LnNlcnZlcl9jb25uO1xuICAgICAgICB2YXIgY2MgPSBmbG93LmNsaWVudF9jb25uO1xuICAgICAgICB2YXIgcmVxID0gZmxvdy5yZXF1ZXN0O1xuICAgICAgICB2YXIgcmVzcCA9IGZsb3cucmVzcG9uc2U7XG5cbiAgICAgICAgdmFyIHRpbWVzdGFtcHMgPSBbXG4gICAgICAgICAgICB7XG4gICAgICAgICAgICAgICAgdGl0bGU6IFwiU2VydmVyIGNvbm4uIGluaXRpYXRlZFwiLFxuICAgICAgICAgICAgICAgIHQ6IHNjLnRpbWVzdGFtcF9zdGFydCxcbiAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XG4gICAgICAgICAgICB9LCB7XG4gICAgICAgICAgICAgICAgdGl0bGU6IFwiU2VydmVyIGNvbm4uIFRDUCBoYW5kc2hha2VcIixcbiAgICAgICAgICAgICAgICB0OiBzYy50aW1lc3RhbXBfdGNwX3NldHVwLFxuICAgICAgICAgICAgICAgIGRlbHRhVG86IHJlcS50aW1lc3RhbXBfc3RhcnRcbiAgICAgICAgICAgIH0sIHtcbiAgICAgICAgICAgICAgICB0aXRsZTogXCJTZXJ2ZXIgY29ubi4gU1NMIGhhbmRzaGFrZVwiLFxuICAgICAgICAgICAgICAgIHQ6IHNjLnRpbWVzdGFtcF9zc2xfc2V0dXAsXG4gICAgICAgICAgICAgICAgZGVsdGFUbzogcmVxLnRpbWVzdGFtcF9zdGFydFxuICAgICAgICAgICAgfSwge1xuICAgICAgICAgICAgICAgIHRpdGxlOiBcIkNsaWVudCBjb25uLiBlc3RhYmxpc2hlZFwiLFxuICAgICAgICAgICAgICAgIHQ6IGNjLnRpbWVzdGFtcF9zdGFydCxcbiAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XG4gICAgICAgICAgICB9LCB7XG4gICAgICAgICAgICAgICAgdGl0bGU6IFwiQ2xpZW50IGNvbm4uIFNTTCBoYW5kc2hha2VcIixcbiAgICAgICAgICAgICAgICB0OiBjYy50aW1lc3RhbXBfc3NsX3NldHVwLFxuICAgICAgICAgICAgICAgIGRlbHRhVG86IHJlcS50aW1lc3RhbXBfc3RhcnRcbiAgICAgICAgICAgIH0sIHtcbiAgICAgICAgICAgICAgICB0aXRsZTogXCJGaXJzdCByZXF1ZXN0IGJ5dGVcIixcbiAgICAgICAgICAgICAgICB0OiByZXEudGltZXN0YW1wX3N0YXJ0LFxuICAgICAgICAgICAgfSwge1xuICAgICAgICAgICAgICAgIHRpdGxlOiBcIlJlcXVlc3QgY29tcGxldGVcIixcbiAgICAgICAgICAgICAgICB0OiByZXEudGltZXN0YW1wX2VuZCxcbiAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XG4gICAgICAgICAgICB9XG4gICAgICAgIF07XG5cbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UpIHtcbiAgICAgICAgICAgIHRpbWVzdGFtcHMucHVzaChcbiAgICAgICAgICAgICAgICB7XG4gICAgICAgICAgICAgICAgICAgIHRpdGxlOiBcIkZpcnN0IHJlc3BvbnNlIGJ5dGVcIixcbiAgICAgICAgICAgICAgICAgICAgdDogcmVzcC50aW1lc3RhbXBfc3RhcnQsXG4gICAgICAgICAgICAgICAgICAgIGRlbHRhVG86IHJlcS50aW1lc3RhbXBfc3RhcnRcbiAgICAgICAgICAgICAgICB9LCB7XG4gICAgICAgICAgICAgICAgICAgIHRpdGxlOiBcIlJlc3BvbnNlIGNvbXBsZXRlXCIsXG4gICAgICAgICAgICAgICAgICAgIHQ6IHJlc3AudGltZXN0YW1wX2VuZCxcbiAgICAgICAgICAgICAgICAgICAgZGVsdGFUbzogcmVxLnRpbWVzdGFtcF9zdGFydFxuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICk7XG4gICAgICAgIH1cblxuICAgICAgICAvL0FkZCB1bmlxdWUga2V5IGZvciBlYWNoIHJvdy5cbiAgICAgICAgdGltZXN0YW1wcy5mb3JFYWNoKGZ1bmN0aW9uIChlKSB7XG4gICAgICAgICAgICBlLmtleSA9IGUudGl0bGU7XG4gICAgICAgIH0pO1xuXG4gICAgICAgIHRpbWVzdGFtcHMgPSBfLnNvcnRCeSh0aW1lc3RhbXBzLCAndCcpO1xuXG4gICAgICAgIHZhciByb3dzID0gdGltZXN0YW1wcy5tYXAoZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFRpbWVTdGFtcCwgUmVhY3QuX19zcHJlYWQoe30sICBlKSk7XG4gICAgICAgIH0pO1xuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIG51bGwsIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJoNFwiLCBudWxsLCBcIlRpbWluZ1wiKSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRhYmxlXCIsIHtjbGFzc05hbWU6IFwidGltaW5nLXRhYmxlXCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRib2R5XCIsIG51bGwsIFxuICAgICAgICAgICAgICAgICAgICByb3dzXG4gICAgICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBGbG93RGV0YWlsQ29ubmVjdGlvbkluZm8gPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiRmxvd0RldGFpbENvbm5lY3Rpb25JbmZvXCIsXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuICAgICAgICB2YXIgY2xpZW50X2Nvbm4gPSBmbG93LmNsaWVudF9jb25uO1xuICAgICAgICB2YXIgc2VydmVyX2Nvbm4gPSBmbG93LnNlcnZlcl9jb25uO1xuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInNlY3Rpb25cIiwgbnVsbCwgXG5cbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaDRcIiwgbnVsbCwgXCJDbGllbnQgQ29ubmVjdGlvblwiKSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChDb25uZWN0aW9uSW5mbywge2Nvbm46IGNsaWVudF9jb25ufSksIFxuXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImg0XCIsIG51bGwsIFwiU2VydmVyIENvbm5lY3Rpb25cIiksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoQ29ubmVjdGlvbkluZm8sIHtjb25uOiBzZXJ2ZXJfY29ubn0pLCBcblxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoQ2VydGlmaWNhdGVJbmZvLCB7ZmxvdzogZmxvd30pLCBcblxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoVGltaW5nLCB7ZmxvdzogZmxvd30pXG5cbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxudmFyIGFsbFRhYnMgPSB7XG4gICAgcmVxdWVzdDogRmxvd0RldGFpbFJlcXVlc3QsXG4gICAgcmVzcG9uc2U6IEZsb3dEZXRhaWxSZXNwb25zZSxcbiAgICBlcnJvcjogRmxvd0RldGFpbEVycm9yLFxuICAgIGRldGFpbHM6IEZsb3dEZXRhaWxDb25uZWN0aW9uSW5mb1xufTtcblxudmFyIEZsb3dEZXRhaWwgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiRmxvd0RldGFpbFwiLFxuICAgIG1peGluczogW3V0aWxzLlN0aWNreUhlYWRNaXhpbiwgdXRpbHMuTmF2aWdhdGlvbiwgdXRpbHMuU3RhdGVdLFxuICAgIGdldFRhYnM6IGZ1bmN0aW9uIChmbG93KSB7XG4gICAgICAgIHZhciB0YWJzID0gW107XG4gICAgICAgIFtcInJlcXVlc3RcIiwgXCJyZXNwb25zZVwiLCBcImVycm9yXCJdLmZvckVhY2goZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgICAgIGlmIChmbG93W2VdKSB7XG4gICAgICAgICAgICAgICAgdGFicy5wdXNoKGUpO1xuICAgICAgICAgICAgfVxuICAgICAgICB9KTtcbiAgICAgICAgdGFicy5wdXNoKFwiZGV0YWlsc1wiKTtcbiAgICAgICAgcmV0dXJuIHRhYnM7XG4gICAgfSxcbiAgICBuZXh0VGFiOiBmdW5jdGlvbiAoaSkge1xuICAgICAgICB2YXIgdGFicyA9IHRoaXMuZ2V0VGFicyh0aGlzLnByb3BzLmZsb3cpO1xuICAgICAgICB2YXIgY3VycmVudEluZGV4ID0gdGFicy5pbmRleE9mKHRoaXMuZ2V0UGFyYW1zKCkuZGV0YWlsVGFiKTtcbiAgICAgICAgLy8gSlMgbW9kdWxvIG9wZXJhdG9yIGRvZXNuJ3QgY29ycmVjdCBuZWdhdGl2ZSBudW1iZXJzLCBtYWtlIHN1cmUgdGhhdCB3ZSBhcmUgcG9zaXRpdmUuXG4gICAgICAgIHZhciBuZXh0SW5kZXggPSAoY3VycmVudEluZGV4ICsgaSArIHRhYnMubGVuZ3RoKSAlIHRhYnMubGVuZ3RoO1xuICAgICAgICB0aGlzLnNlbGVjdFRhYih0YWJzW25leHRJbmRleF0pO1xuICAgIH0sXG4gICAgc2VsZWN0VGFiOiBmdW5jdGlvbiAocGFuZWwpIHtcbiAgICAgICAgdGhpcy5yZXBsYWNlV2l0aChcbiAgICAgICAgICAgIFwiZmxvd1wiLFxuICAgICAgICAgICAge1xuICAgICAgICAgICAgICAgIGZsb3dJZDogdGhpcy5nZXRQYXJhbXMoKS5mbG93SWQsXG4gICAgICAgICAgICAgICAgZGV0YWlsVGFiOiBwYW5lbFxuICAgICAgICAgICAgfVxuICAgICAgICApO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuICAgICAgICB2YXIgdGFicyA9IHRoaXMuZ2V0VGFicyhmbG93KTtcbiAgICAgICAgdmFyIGFjdGl2ZSA9IHRoaXMuZ2V0UGFyYW1zKCkuZGV0YWlsVGFiO1xuXG4gICAgICAgIGlmICghXy5jb250YWlucyh0YWJzLCBhY3RpdmUpKSB7XG4gICAgICAgICAgICBpZiAoYWN0aXZlID09PSBcInJlc3BvbnNlXCIgJiYgZmxvdy5lcnJvcikge1xuICAgICAgICAgICAgICAgIGFjdGl2ZSA9IFwiZXJyb3JcIjtcbiAgICAgICAgICAgIH0gZWxzZSBpZiAoYWN0aXZlID09PSBcImVycm9yXCIgJiYgZmxvdy5yZXNwb25zZSkge1xuICAgICAgICAgICAgICAgIGFjdGl2ZSA9IFwicmVzcG9uc2VcIjtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgYWN0aXZlID0gdGFic1swXTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIHRoaXMuc2VsZWN0VGFiKGFjdGl2ZSk7XG4gICAgICAgIH1cblxuICAgICAgICB2YXIgVGFiID0gYWxsVGFic1thY3RpdmVdO1xuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcImZsb3ctZGV0YWlsXCIsIG9uU2Nyb2xsOiB0aGlzLmFkanVzdEhlYWR9LCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KEZsb3dEZXRhaWxOYXYsIHtyZWY6IFwiaGVhZFwiLCBcbiAgICAgICAgICAgICAgICAgICAgZmxvdzogZmxvdywgXG4gICAgICAgICAgICAgICAgICAgIHRhYnM6IHRhYnMsIFxuICAgICAgICAgICAgICAgICAgICBhY3RpdmU6IGFjdGl2ZSwgXG4gICAgICAgICAgICAgICAgICAgIHNlbGVjdFRhYjogdGhpcy5zZWxlY3RUYWJ9KSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChUYWIsIHtmbG93OiBmbG93fSlcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxubW9kdWxlLmV4cG9ydHMgPSB7XG4gICAgRmxvd0RldGFpbDogRmxvd0RldGFpbFxufTsiLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XG52YXIgZmxvd3V0aWxzID0gcmVxdWlyZShcIi4uL2Zsb3cvdXRpbHMuanNcIik7XG52YXIgdXRpbHMgPSByZXF1aXJlKFwiLi4vdXRpbHMuanNcIik7XG5cbnZhciBUTFNDb2x1bW4gPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiVExTQ29sdW1uXCIsXG4gICAgc3RhdGljczoge1xuICAgICAgICByZW5kZXJUaXRsZTogZnVuY3Rpb24gKCkge1xuICAgICAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0aFwiLCB7a2V5OiBcInRsc1wiLCBjbGFzc05hbWU6IFwiY29sLXRsc1wifSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgdmFyIHNzbCA9IChmbG93LnJlcXVlc3Quc2NoZW1lID09IFwiaHR0cHNcIik7XG4gICAgICAgIHZhciBjbGFzc2VzO1xuICAgICAgICBpZiAoc3NsKSB7XG4gICAgICAgICAgICBjbGFzc2VzID0gXCJjb2wtdGxzIGNvbC10bHMtaHR0cHNcIjtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGNsYXNzZXMgPSBcImNvbC10bHMgY29sLXRscy1odHRwXCI7XG4gICAgICAgIH1cbiAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCB7Y2xhc3NOYW1lOiBjbGFzc2VzfSk7XG4gICAgfVxufSk7XG5cblxudmFyIEljb25Db2x1bW4gPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiSWNvbkNvbHVtblwiLFxuICAgIHN0YXRpY3M6IHtcbiAgICAgICAgcmVuZGVyVGl0bGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGhcIiwge2tleTogXCJpY29uXCIsIGNsYXNzTmFtZTogXCJjb2wtaWNvblwifSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcblxuICAgICAgICB2YXIgaWNvbjtcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UpIHtcbiAgICAgICAgICAgIHZhciBjb250ZW50VHlwZSA9IGZsb3d1dGlscy5SZXNwb25zZVV0aWxzLmdldENvbnRlbnRUeXBlKGZsb3cucmVzcG9uc2UpO1xuXG4gICAgICAgICAgICAvL1RPRE86IFdlIHNob3VsZCBhc3NpZ24gYSB0eXBlIHRvIHRoZSBmbG93IHNvbWV3aGVyZSBlbHNlLlxuICAgICAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UuY29kZSA9PSAzMDQpIHtcbiAgICAgICAgICAgICAgICBpY29uID0gXCJyZXNvdXJjZS1pY29uLW5vdC1tb2RpZmllZFwiO1xuICAgICAgICAgICAgfSBlbHNlIGlmICgzMDAgPD0gZmxvdy5yZXNwb25zZS5jb2RlICYmIGZsb3cucmVzcG9uc2UuY29kZSA8IDQwMCkge1xuICAgICAgICAgICAgICAgIGljb24gPSBcInJlc291cmNlLWljb24tcmVkaXJlY3RcIjtcbiAgICAgICAgICAgIH0gZWxzZSBpZiAoY29udGVudFR5cGUgJiYgY29udGVudFR5cGUuaW5kZXhPZihcImltYWdlXCIpID49IDApIHtcbiAgICAgICAgICAgICAgICBpY29uID0gXCJyZXNvdXJjZS1pY29uLWltYWdlXCI7XG4gICAgICAgICAgICB9IGVsc2UgaWYgKGNvbnRlbnRUeXBlICYmIGNvbnRlbnRUeXBlLmluZGV4T2YoXCJqYXZhc2NyaXB0XCIpID49IDApIHtcbiAgICAgICAgICAgICAgICBpY29uID0gXCJyZXNvdXJjZS1pY29uLWpzXCI7XG4gICAgICAgICAgICB9IGVsc2UgaWYgKGNvbnRlbnRUeXBlICYmIGNvbnRlbnRUeXBlLmluZGV4T2YoXCJjc3NcIikgPj0gMCkge1xuICAgICAgICAgICAgICAgIGljb24gPSBcInJlc291cmNlLWljb24tY3NzXCI7XG4gICAgICAgICAgICB9IGVsc2UgaWYgKGNvbnRlbnRUeXBlICYmIGNvbnRlbnRUeXBlLmluZGV4T2YoXCJodG1sXCIpID49IDApIHtcbiAgICAgICAgICAgICAgICBpY29uID0gXCJyZXNvdXJjZS1pY29uLWRvY3VtZW50XCI7XG4gICAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKCFpY29uKSB7XG4gICAgICAgICAgICBpY29uID0gXCJyZXNvdXJjZS1pY29uLXBsYWluXCI7XG4gICAgICAgIH1cblxuXG4gICAgICAgIGljb24gKz0gXCIgcmVzb3VyY2UtaWNvblwiO1xuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIHtjbGFzc05hbWU6IFwiY29sLWljb25cIn0sIFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBpY29ufSlcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxudmFyIFBhdGhDb2x1bW4gPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiUGF0aENvbHVtblwiLFxuICAgIHN0YXRpY3M6IHtcbiAgICAgICAgcmVuZGVyVGl0bGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGhcIiwge2tleTogXCJwYXRoXCIsIGNsYXNzTmFtZTogXCJjb2wtcGF0aFwifSwgXCJQYXRoXCIpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwge2NsYXNzTmFtZTogXCJjb2wtcGF0aFwifSwgXG4gICAgICAgICAgICBmbG93LnJlcXVlc3QuaXNfcmVwbGF5ID8gUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge2NsYXNzTmFtZTogXCJmYSBmYS1mdyBmYS1yZXBlYXQgcHVsbC1yaWdodFwifSkgOiBudWxsLCBcbiAgICAgICAgICAgIGZsb3cuaW50ZXJjZXB0ZWQgPyBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaVwiLCB7Y2xhc3NOYW1lOiBcImZhIGZhLWZ3IGZhLXBhdXNlIHB1bGwtcmlnaHRcIn0pIDogbnVsbCwgXG4gICAgICAgICAgICBmbG93LnJlcXVlc3Quc2NoZW1lICsgXCI6Ly9cIiArIGZsb3cucmVxdWVzdC5ob3N0ICsgZmxvdy5yZXF1ZXN0LnBhdGhcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxuXG52YXIgTWV0aG9kQ29sdW1uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIk1ldGhvZENvbHVtblwiLFxuICAgIHN0YXRpY3M6IHtcbiAgICAgICAgcmVuZGVyVGl0bGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGhcIiwge2tleTogXCJtZXRob2RcIiwgY2xhc3NOYW1lOiBcImNvbC1tZXRob2RcIn0sIFwiTWV0aG9kXCIpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwge2NsYXNzTmFtZTogXCJjb2wtbWV0aG9kXCJ9LCBmbG93LnJlcXVlc3QubWV0aG9kKTtcbiAgICB9XG59KTtcblxuXG52YXIgU3RhdHVzQ29sdW1uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlN0YXR1c0NvbHVtblwiLFxuICAgIHN0YXRpY3M6IHtcbiAgICAgICAgcmVuZGVyVGl0bGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGhcIiwge2tleTogXCJzdGF0dXNcIiwgY2xhc3NOYW1lOiBcImNvbC1zdGF0dXNcIn0sIFwiU3RhdHVzXCIpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG4gICAgICAgIHZhciBzdGF0dXM7XG4gICAgICAgIGlmIChmbG93LnJlc3BvbnNlKSB7XG4gICAgICAgICAgICBzdGF0dXMgPSBmbG93LnJlc3BvbnNlLmNvZGU7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzdGF0dXMgPSBudWxsO1xuICAgICAgICB9XG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwge2NsYXNzTmFtZTogXCJjb2wtc3RhdHVzXCJ9LCBzdGF0dXMpO1xuICAgIH1cbn0pO1xuXG5cbnZhciBTaXplQ29sdW1uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlNpemVDb2x1bW5cIixcbiAgICBzdGF0aWNzOiB7XG4gICAgICAgIHJlbmRlclRpdGxlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRoXCIsIHtrZXk6IFwic2l6ZVwiLCBjbGFzc05hbWU6IFwiY29sLXNpemVcIn0sIFwiU2l6ZVwiKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuXG4gICAgICAgIHZhciB0b3RhbCA9IGZsb3cucmVxdWVzdC5jb250ZW50TGVuZ3RoO1xuICAgICAgICBpZiAoZmxvdy5yZXNwb25zZSkge1xuICAgICAgICAgICAgdG90YWwgKz0gZmxvdy5yZXNwb25zZS5jb250ZW50TGVuZ3RoIHx8IDA7XG4gICAgICAgIH1cbiAgICAgICAgdmFyIHNpemUgPSB1dGlscy5mb3JtYXRTaXplKHRvdGFsKTtcbiAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCB7Y2xhc3NOYW1lOiBcImNvbC1zaXplXCJ9LCBzaXplKTtcbiAgICB9XG59KTtcblxuXG52YXIgVGltZUNvbHVtbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJUaW1lQ29sdW1uXCIsXG4gICAgc3RhdGljczoge1xuICAgICAgICByZW5kZXJUaXRsZTogZnVuY3Rpb24gKCkge1xuICAgICAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0aFwiLCB7a2V5OiBcInRpbWVcIiwgY2xhc3NOYW1lOiBcImNvbC10aW1lXCJ9LCBcIlRpbWVcIik7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgdmFyIHRpbWU7XG4gICAgICAgIGlmIChmbG93LnJlc3BvbnNlKSB7XG4gICAgICAgICAgICB0aW1lID0gdXRpbHMuZm9ybWF0VGltZURlbHRhKDEwMDAgKiAoZmxvdy5yZXNwb25zZS50aW1lc3RhbXBfZW5kIC0gZmxvdy5yZXF1ZXN0LnRpbWVzdGFtcF9zdGFydCkpO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgdGltZSA9IFwiLi4uXCI7XG4gICAgICAgIH1cbiAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCB7Y2xhc3NOYW1lOiBcImNvbC10aW1lXCJ9LCB0aW1lKTtcbiAgICB9XG59KTtcblxuXG52YXIgYWxsX2NvbHVtbnMgPSBbXG4gICAgVExTQ29sdW1uLFxuICAgIEljb25Db2x1bW4sXG4gICAgUGF0aENvbHVtbixcbiAgICBNZXRob2RDb2x1bW4sXG4gICAgU3RhdHVzQ29sdW1uLFxuICAgIFNpemVDb2x1bW4sXG4gICAgVGltZUNvbHVtbl07XG5cblxubW9kdWxlLmV4cG9ydHMgPSBhbGxfY29sdW1ucztcblxuXG4iLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XG52YXIgdXRpbHMgPSByZXF1aXJlKFwiLi91dGlscy5qc1wiKTtcbnZhciBWaXJ0dWFsU2Nyb2xsTWl4aW4gPSByZXF1aXJlKFwiLi92aXJ0dWFsc2Nyb2xsLmpzXCIpO1xudmFyIGZsb3d0YWJsZV9jb2x1bW5zID0gcmVxdWlyZShcIi4vZmxvd3RhYmxlLWNvbHVtbnMuanNcIik7XG5cbnZhciBGbG93Um93ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZsb3dSb3dcIixcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG4gICAgICAgIHZhciBjb2x1bW5zID0gdGhpcy5wcm9wcy5jb2x1bW5zLm1hcChmdW5jdGlvbiAoQ29sdW1uKSB7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChDb2x1bW4sIHtrZXk6IENvbHVtbi5kaXNwbGF5TmFtZSwgZmxvdzogZmxvd30pO1xuICAgICAgICB9LmJpbmQodGhpcykpO1xuICAgICAgICB2YXIgY2xhc3NOYW1lID0gXCJcIjtcbiAgICAgICAgaWYgKHRoaXMucHJvcHMuc2VsZWN0ZWQpIHtcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcIiBzZWxlY3RlZFwiO1xuICAgICAgICB9XG4gICAgICAgIGlmICh0aGlzLnByb3BzLmhpZ2hsaWdodGVkKSB7XG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCIgaGlnaGxpZ2h0ZWRcIjtcbiAgICAgICAgfVxuICAgICAgICBpZiAoZmxvdy5pbnRlcmNlcHRlZCkge1xuICAgICAgICAgICAgY2xhc3NOYW1lICs9IFwiIGludGVyY2VwdGVkXCI7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKGZsb3cucmVxdWVzdCkge1xuICAgICAgICAgICAgY2xhc3NOYW1lICs9IFwiIGhhcy1yZXF1ZXN0XCI7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UpIHtcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcIiBoYXMtcmVzcG9uc2VcIjtcbiAgICAgICAgfVxuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidHJcIiwge2NsYXNzTmFtZTogY2xhc3NOYW1lLCBvbkNsaWNrOiB0aGlzLnByb3BzLnNlbGVjdEZsb3cuYmluZChudWxsLCBmbG93KX0sIFxuICAgICAgICAgICAgICAgIGNvbHVtbnNcbiAgICAgICAgICAgICkpO1xuICAgIH0sXG4gICAgc2hvdWxkQ29tcG9uZW50VXBkYXRlOiBmdW5jdGlvbiAobmV4dFByb3BzKSB7XG4gICAgICAgIHJldHVybiB0cnVlO1xuICAgICAgICAvLyBGdXJ0aGVyIG9wdGltaXphdGlvbiBjb3VsZCBiZSBkb25lIGhlcmVcbiAgICAgICAgLy8gYnkgY2FsbGluZyBmb3JjZVVwZGF0ZSBvbiBmbG93IHVwZGF0ZXMsIHNlbGVjdGlvbiBjaGFuZ2VzIGFuZCBjb2x1bW4gY2hhbmdlcy5cbiAgICAgICAgLy9yZXR1cm4gKFxuICAgICAgICAvLyh0aGlzLnByb3BzLmNvbHVtbnMubGVuZ3RoICE9PSBuZXh0UHJvcHMuY29sdW1ucy5sZW5ndGgpIHx8XG4gICAgICAgIC8vKHRoaXMucHJvcHMuc2VsZWN0ZWQgIT09IG5leHRQcm9wcy5zZWxlY3RlZClcbiAgICAgICAgLy8pO1xuICAgIH1cbn0pO1xuXG52YXIgRmxvd1RhYmxlSGVhZCA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGbG93VGFibGVIZWFkXCIsXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBjb2x1bW5zID0gdGhpcy5wcm9wcy5jb2x1bW5zLm1hcChmdW5jdGlvbiAoY29sdW1uKSB7XG4gICAgICAgICAgICByZXR1cm4gY29sdW1uLnJlbmRlclRpdGxlKCk7XG4gICAgICAgIH0uYmluZCh0aGlzKSk7XG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGhlYWRcIiwgbnVsbCwgXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidHJcIiwgbnVsbCwgY29sdW1ucylcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxuXG52YXIgUk9XX0hFSUdIVCA9IDMyO1xuXG52YXIgRmxvd1RhYmxlID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZsb3dUYWJsZVwiLFxuICAgIG1peGluczogW3V0aWxzLlN0aWNreUhlYWRNaXhpbiwgdXRpbHMuQXV0b1Njcm9sbE1peGluLCBWaXJ0dWFsU2Nyb2xsTWl4aW5dLFxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgY29sdW1uczogZmxvd3RhYmxlX2NvbHVtbnNcbiAgICAgICAgfTtcbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxNb3VudDogZnVuY3Rpb24gKCkge1xuICAgICAgICBpZiAodGhpcy5wcm9wcy52aWV3KSB7XG4gICAgICAgICAgICB0aGlzLnByb3BzLnZpZXcuYWRkTGlzdGVuZXIoXCJhZGQgdXBkYXRlIHJlbW92ZSByZWNhbGN1bGF0ZVwiLCB0aGlzLm9uQ2hhbmdlKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbFJlY2VpdmVQcm9wczogZnVuY3Rpb24gKG5leHRQcm9wcykge1xuICAgICAgICBpZiAobmV4dFByb3BzLnZpZXcgIT09IHRoaXMucHJvcHMudmlldykge1xuICAgICAgICAgICAgaWYgKHRoaXMucHJvcHMudmlldykge1xuICAgICAgICAgICAgICAgIHRoaXMucHJvcHMudmlldy5yZW1vdmVMaXN0ZW5lcihcImFkZCB1cGRhdGUgcmVtb3ZlIHJlY2FsY3VsYXRlXCIpO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgbmV4dFByb3BzLnZpZXcuYWRkTGlzdGVuZXIoXCJhZGQgdXBkYXRlIHJlbW92ZSByZWNhbGN1bGF0ZVwiLCB0aGlzLm9uQ2hhbmdlKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgZ2V0RGVmYXVsdFByb3BzOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHJldHVybiB7XG4gICAgICAgICAgICByb3dIZWlnaHQ6IFJPV19IRUlHSFRcbiAgICAgICAgfTtcbiAgICB9LFxuICAgIG9uU2Nyb2xsRmxvd1RhYmxlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuYWRqdXN0SGVhZCgpO1xuICAgICAgICB0aGlzLm9uU2Nyb2xsKCk7XG4gICAgfSxcbiAgICBvbkNoYW5nZTogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLmZvcmNlVXBkYXRlKCk7XG4gICAgfSxcbiAgICBzY3JvbGxJbnRvVmlldzogZnVuY3Rpb24gKGZsb3cpIHtcbiAgICAgICAgdGhpcy5zY3JvbGxSb3dJbnRvVmlldyhcbiAgICAgICAgICAgIHRoaXMucHJvcHMudmlldy5pbmRleChmbG93KSxcbiAgICAgICAgICAgIHRoaXMucmVmcy5ib2R5LmdldERPTU5vZGUoKS5vZmZzZXRUb3BcbiAgICAgICAgKTtcbiAgICB9LFxuICAgIHJlbmRlclJvdzogZnVuY3Rpb24gKGZsb3cpIHtcbiAgICAgICAgdmFyIHNlbGVjdGVkID0gKGZsb3cgPT09IHRoaXMucHJvcHMuc2VsZWN0ZWQpO1xuICAgICAgICB2YXIgaGlnaGxpZ2h0ZWQgPVxuICAgICAgICAgICAgKFxuICAgICAgICAgICAgdGhpcy5wcm9wcy52aWV3Ll9oaWdobGlnaHQgJiZcbiAgICAgICAgICAgIHRoaXMucHJvcHMudmlldy5faGlnaGxpZ2h0W2Zsb3cuaWRdXG4gICAgICAgICAgICApO1xuXG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KEZsb3dSb3csIHtrZXk6IGZsb3cuaWQsIFxuICAgICAgICAgICAgcmVmOiBmbG93LmlkLCBcbiAgICAgICAgICAgIGZsb3c6IGZsb3csIFxuICAgICAgICAgICAgY29sdW1uczogdGhpcy5zdGF0ZS5jb2x1bW5zLCBcbiAgICAgICAgICAgIHNlbGVjdGVkOiBzZWxlY3RlZCwgXG4gICAgICAgICAgICBoaWdobGlnaHRlZDogaGlnaGxpZ2h0ZWQsIFxuICAgICAgICAgICAgc2VsZWN0RmxvdzogdGhpcy5wcm9wcy5zZWxlY3RGbG93fVxuICAgICAgICApO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIC8vY29uc29sZS5sb2coXCJyZW5kZXIgZmxvd3RhYmxlXCIsIHRoaXMuc3RhdGUuc3RhcnQsIHRoaXMuc3RhdGUuc3RvcCwgdGhpcy5wcm9wcy5zZWxlY3RlZCk7XG4gICAgICAgIHZhciBmbG93cyA9IHRoaXMucHJvcHMudmlldyA/IHRoaXMucHJvcHMudmlldy5saXN0IDogW107XG5cbiAgICAgICAgdmFyIHJvd3MgPSB0aGlzLnJlbmRlclJvd3MoZmxvd3MpO1xuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwiZmxvdy10YWJsZVwiLCBvblNjcm9sbDogdGhpcy5vblNjcm9sbEZsb3dUYWJsZX0sIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0YWJsZVwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChGbG93VGFibGVIZWFkLCB7cmVmOiBcImhlYWRcIiwgXG4gICAgICAgICAgICAgICAgICAgICAgICBjb2x1bW5zOiB0aGlzLnN0YXRlLmNvbHVtbnN9KSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0Ym9keVwiLCB7cmVmOiBcImJvZHlcIn0sIFxuICAgICAgICAgICAgICAgICAgICAgICAgIHRoaXMuZ2V0UGxhY2Vob2xkZXJUb3AoZmxvd3MubGVuZ3RoKSwgXG4gICAgICAgICAgICAgICAgICAgICAgICByb3dzLCBcbiAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmdldFBsYWNlaG9sZGVyQm90dG9tKGZsb3dzLmxlbmd0aCkgXG4gICAgICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbm1vZHVsZS5leHBvcnRzID0gRmxvd1RhYmxlO1xuIiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xuXG52YXIgRm9vdGVyID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZvb3RlclwiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgbW9kZSA9IHRoaXMucHJvcHMuc2V0dGluZ3MubW9kZTtcbiAgICAgICAgdmFyIGludGVyY2VwdCA9IHRoaXMucHJvcHMuc2V0dGluZ3MuaW50ZXJjZXB0O1xuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImZvb3RlclwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICBtb2RlICE9IFwicmVndWxhclwiID8gUmVhY3QuY3JlYXRlRWxlbWVudChcInNwYW5cIiwge2NsYXNzTmFtZTogXCJsYWJlbCBsYWJlbC1zdWNjZXNzXCJ9LCBtb2RlLCBcIiBtb2RlXCIpIDogbnVsbCwgXG4gICAgICAgICAgICAgICAgXCLCoFwiLCBcbiAgICAgICAgICAgICAgICBpbnRlcmNlcHQgPyBSZWFjdC5jcmVhdGVFbGVtZW50KFwic3BhblwiLCB7Y2xhc3NOYW1lOiBcImxhYmVsIGxhYmVsLXN1Y2Nlc3NcIn0sIFwiSW50ZXJjZXB0OiBcIiwgaW50ZXJjZXB0KSA6IG51bGxcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxubW9kdWxlLmV4cG9ydHMgPSBGb290ZXI7IiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xudmFyICQgPSByZXF1aXJlKFwianF1ZXJ5XCIpO1xuXG52YXIgdXRpbHMgPSByZXF1aXJlKFwiLi91dGlscy5qc1wiKTtcblxudmFyIEZpbHRlckRvY3MgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiRmlsdGVyRG9jc1wiLFxuICAgIHN0YXRpY3M6IHtcbiAgICAgICAgeGhyOiBmYWxzZSxcbiAgICAgICAgZG9jOiBmYWxzZVxuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbE1vdW50OiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIGlmICghRmlsdGVyRG9jcy5kb2MpIHtcbiAgICAgICAgICAgIEZpbHRlckRvY3MueGhyID0gJC5nZXRKU09OKFwiL2ZpbHRlci1oZWxwXCIpLmRvbmUoZnVuY3Rpb24gKGRvYykge1xuICAgICAgICAgICAgICAgIEZpbHRlckRvY3MuZG9jID0gZG9jO1xuICAgICAgICAgICAgICAgIEZpbHRlckRvY3MueGhyID0gZmFsc2U7XG4gICAgICAgICAgICB9KTtcbiAgICAgICAgfVxuICAgICAgICBpZiAoRmlsdGVyRG9jcy54aHIpIHtcbiAgICAgICAgICAgIEZpbHRlckRvY3MueGhyLmRvbmUoZnVuY3Rpb24gKCkge1xuICAgICAgICAgICAgICAgIHRoaXMuZm9yY2VVcGRhdGUoKTtcbiAgICAgICAgICAgIH0uYmluZCh0aGlzKSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICBpZiAoIUZpbHRlckRvY3MuZG9jKSB7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge2NsYXNzTmFtZTogXCJmYSBmYS1zcGlubmVyIGZhLXNwaW5cIn0pO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgdmFyIGNvbW1hbmRzID0gRmlsdGVyRG9jcy5kb2MuY29tbWFuZHMubWFwKGZ1bmN0aW9uIChjKSB7XG4gICAgICAgICAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0clwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIG51bGwsIGNbMF0ucmVwbGFjZShcIiBcIiwgJ1xcdTAwYTAnKSksIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwgbnVsbCwgY1sxXSlcbiAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgfSk7XG4gICAgICAgICAgICBjb21tYW5kcy5wdXNoKFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0clwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwge2NvbFNwYW46IFwiMlwifSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJhXCIsIHtocmVmOiBcImh0dHBzOi8vbWl0bXByb3h5Lm9yZy9kb2MvZmVhdHVyZXMvZmlsdGVycy5odG1sXCIsIFxuICAgICAgICAgICAgICAgICAgICAgICAgdGFyZ2V0OiBcIl9ibGFua1wifSwgXG4gICAgICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaVwiLCB7Y2xhc3NOYW1lOiBcImZhIGZhLWV4dGVybmFsLWxpbmtcIn0pLCBcbiAgICAgICAgICAgICAgICAgICAgXCLCoCBtaXRtcHJveHkgZG9jc1wiKVxuICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgICkpO1xuICAgICAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0YWJsZVwiLCB7Y2xhc3NOYW1lOiBcInRhYmxlIHRhYmxlLWNvbmRlbnNlZFwifSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRib2R5XCIsIG51bGwsIGNvbW1hbmRzKVxuICAgICAgICAgICAgKTtcbiAgICAgICAgfVxuICAgIH1cbn0pO1xudmFyIEZpbHRlcklucHV0ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZpbHRlcklucHV0XCIsXG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIC8vIENvbnNpZGVyIGJvdGggZm9jdXMgYW5kIG1vdXNlb3ZlciBmb3Igc2hvd2luZy9oaWRpbmcgdGhlIHRvb2x0aXAsXG4gICAgICAgIC8vIGJlY2F1c2Ugb25CbHVyIG9mIHRoZSBpbnB1dCBpcyB0cmlnZ2VyZWQgYmVmb3JlIHRoZSBjbGljayBvbiB0aGUgdG9vbHRpcFxuICAgICAgICAvLyBmaW5hbGl6ZWQsIGhpZGluZyB0aGUgdG9vbHRpcCBqdXN0IGFzIHRoZSB1c2VyIGNsaWNrcyBvbiBpdC5cbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgIHZhbHVlOiB0aGlzLnByb3BzLnZhbHVlLFxuICAgICAgICAgICAgZm9jdXM6IGZhbHNlLFxuICAgICAgICAgICAgbW91c2Vmb2N1czogZmFsc2VcbiAgICAgICAgfTtcbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxSZWNlaXZlUHJvcHM6IGZ1bmN0aW9uIChuZXh0UHJvcHMpIHtcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7dmFsdWU6IG5leHRQcm9wcy52YWx1ZX0pO1xuICAgIH0sXG4gICAgb25DaGFuZ2U6IGZ1bmN0aW9uIChlKSB7XG4gICAgICAgIHZhciBuZXh0VmFsdWUgPSBlLnRhcmdldC52YWx1ZTtcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7XG4gICAgICAgICAgICB2YWx1ZTogbmV4dFZhbHVlXG4gICAgICAgIH0pO1xuICAgICAgICAvLyBPbmx5IHByb3BhZ2F0ZSB2YWxpZCBmaWx0ZXJzIHVwd2FyZHMuXG4gICAgICAgIGlmICh0aGlzLmlzVmFsaWQobmV4dFZhbHVlKSkge1xuICAgICAgICAgICAgdGhpcy5wcm9wcy5vbkNoYW5nZShuZXh0VmFsdWUpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBpc1ZhbGlkOiBmdW5jdGlvbiAoZmlsdCkge1xuICAgICAgICB0cnkge1xuICAgICAgICAgICAgRmlsdC5wYXJzZShmaWx0IHx8IHRoaXMuc3RhdGUudmFsdWUpO1xuICAgICAgICAgICAgcmV0dXJuIHRydWU7XG4gICAgICAgIH0gY2F0Y2ggKGUpIHtcbiAgICAgICAgICAgIHJldHVybiBmYWxzZTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgZ2V0RGVzYzogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZGVzYztcbiAgICAgICAgdHJ5IHtcbiAgICAgICAgICAgIGRlc2MgPSBGaWx0LnBhcnNlKHRoaXMuc3RhdGUudmFsdWUpLmRlc2M7XG4gICAgICAgIH0gY2F0Y2ggKGUpIHtcbiAgICAgICAgICAgIGRlc2MgPSBcIlwiICsgZTtcbiAgICAgICAgfVxuICAgICAgICBpZiAoZGVzYyAhPT0gXCJ0cnVlXCIpIHtcbiAgICAgICAgICAgIHJldHVybiBkZXNjO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KEZpbHRlckRvY3MsIG51bGwpXG4gICAgICAgICAgICApO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBvbkZvY3VzOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe2ZvY3VzOiB0cnVlfSk7XG4gICAgfSxcbiAgICBvbkJsdXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7Zm9jdXM6IGZhbHNlfSk7XG4gICAgfSxcbiAgICBvbk1vdXNlRW50ZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7bW91c2Vmb2N1czogdHJ1ZX0pO1xuICAgIH0sXG4gICAgb25Nb3VzZUxlYXZlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe21vdXNlZm9jdXM6IGZhbHNlfSk7XG4gICAgfSxcbiAgICBvbktleURvd246IGZ1bmN0aW9uIChlKSB7XG4gICAgICAgIGlmIChlLmtleUNvZGUgPT09IEtleS5FU0MgfHwgZS5rZXlDb2RlID09PSBLZXkuRU5URVIpIHtcbiAgICAgICAgICAgIHRoaXMuYmx1cigpO1xuICAgICAgICAgICAgLy8gSWYgY2xvc2VkIHVzaW5nIEVTQy9FTlRFUiwgaGlkZSB0aGUgdG9vbHRpcC5cbiAgICAgICAgICAgIHRoaXMuc2V0U3RhdGUoe21vdXNlZm9jdXM6IGZhbHNlfSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGJsdXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5yZWZzLmlucHV0LmdldERPTU5vZGUoKS5ibHVyKCk7XG4gICAgfSxcbiAgICBmb2N1czogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLnJlZnMuaW5wdXQuZ2V0RE9NTm9kZSgpLnNlbGVjdCgpO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBpc1ZhbGlkID0gdGhpcy5pc1ZhbGlkKCk7XG4gICAgICAgIHZhciBpY29uID0gXCJmYSBmYS1mdyBmYS1cIiArIHRoaXMucHJvcHMudHlwZTtcbiAgICAgICAgdmFyIGdyb3VwQ2xhc3NOYW1lID0gXCJmaWx0ZXItaW5wdXQgaW5wdXQtZ3JvdXBcIiArIChpc1ZhbGlkID8gXCJcIiA6IFwiIGhhcy1lcnJvclwiKTtcblxuICAgICAgICB2YXIgcG9wb3ZlcjtcbiAgICAgICAgaWYgKHRoaXMuc3RhdGUuZm9jdXMgfHwgdGhpcy5zdGF0ZS5tb3VzZWZvY3VzKSB7XG4gICAgICAgICAgICBwb3BvdmVyID0gKFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJwb3BvdmVyIGJvdHRvbVwiLCBvbk1vdXNlRW50ZXI6IHRoaXMub25Nb3VzZUVudGVyLCBvbk1vdXNlTGVhdmU6IHRoaXMub25Nb3VzZUxlYXZlfSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJhcnJvd1wifSksIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwicG9wb3Zlci1jb250ZW50XCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5nZXREZXNjKClcbiAgICAgICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgICk7XG4gICAgICAgIH1cblxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBncm91cENsYXNzTmFtZX0sIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIsIHtjbGFzc05hbWU6IFwiaW5wdXQtZ3JvdXAtYWRkb25cIn0sIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaVwiLCB7Y2xhc3NOYW1lOiBpY29uLCBzdHlsZToge2NvbG9yOiB0aGlzLnByb3BzLmNvbG9yfX0pXG4gICAgICAgICAgICAgICAgKSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImlucHV0XCIsIHt0eXBlOiBcInRleHRcIiwgcGxhY2Vob2xkZXI6IHRoaXMucHJvcHMucGxhY2Vob2xkZXIsIGNsYXNzTmFtZTogXCJmb3JtLWNvbnRyb2xcIiwgXG4gICAgICAgICAgICAgICAgICAgIHJlZjogXCJpbnB1dFwiLCBcbiAgICAgICAgICAgICAgICAgICAgb25DaGFuZ2U6IHRoaXMub25DaGFuZ2UsIFxuICAgICAgICAgICAgICAgICAgICBvbkZvY3VzOiB0aGlzLm9uRm9jdXMsIFxuICAgICAgICAgICAgICAgICAgICBvbkJsdXI6IHRoaXMub25CbHVyLCBcbiAgICAgICAgICAgICAgICAgICAgb25LZXlEb3duOiB0aGlzLm9uS2V5RG93biwgXG4gICAgICAgICAgICAgICAgICAgIHZhbHVlOiB0aGlzLnN0YXRlLnZhbHVlfSksIFxuICAgICAgICAgICAgICAgIHBvcG92ZXJcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxudmFyIE1haW5NZW51ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIk1haW5NZW51XCIsXG4gICAgbWl4aW5zOiBbdXRpbHMuTmF2aWdhdGlvbiwgdXRpbHMuU3RhdGVdLFxuICAgIHN0YXRpY3M6IHtcbiAgICAgICAgdGl0bGU6IFwiU3RhcnRcIixcbiAgICAgICAgcm91dGU6IFwiZmxvd3NcIlxuICAgIH0sXG4gICAgb25GaWx0ZXJDaGFuZ2U6IGZ1bmN0aW9uICh2YWwpIHtcbiAgICAgICAgdmFyIGQgPSB7fTtcbiAgICAgICAgZFtRdWVyeS5GSUxURVJdID0gdmFsO1xuICAgICAgICB0aGlzLnNldFF1ZXJ5KGQpO1xuICAgIH0sXG4gICAgb25IaWdobGlnaHRDaGFuZ2U6IGZ1bmN0aW9uICh2YWwpIHtcbiAgICAgICAgdmFyIGQgPSB7fTtcbiAgICAgICAgZFtRdWVyeS5ISUdITElHSFRdID0gdmFsO1xuICAgICAgICB0aGlzLnNldFF1ZXJ5KGQpO1xuICAgIH0sXG4gICAgb25JbnRlcmNlcHRDaGFuZ2U6IGZ1bmN0aW9uICh2YWwpIHtcbiAgICAgICAgU2V0dGluZ3NBY3Rpb25zLnVwZGF0ZSh7aW50ZXJjZXB0OiB2YWx9KTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmlsdGVyID0gdGhpcy5nZXRRdWVyeSgpW1F1ZXJ5LkZJTFRFUl0gfHwgXCJcIjtcbiAgICAgICAgdmFyIGhpZ2hsaWdodCA9IHRoaXMuZ2V0UXVlcnkoKVtRdWVyeS5ISUdITElHSFRdIHx8IFwiXCI7XG4gICAgICAgIHZhciBpbnRlcmNlcHQgPSB0aGlzLnByb3BzLnNldHRpbmdzLmludGVyY2VwdCB8fCBcIlwiO1xuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIG51bGwsIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJtZW51LXJvd1wifSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoRmlsdGVySW5wdXQsIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHBsYWNlaG9sZGVyOiBcIkZpbHRlclwiLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIHR5cGU6IFwiZmlsdGVyXCIsIFxuICAgICAgICAgICAgICAgICAgICAgICAgY29sb3I6IFwiYmxhY2tcIiwgXG4gICAgICAgICAgICAgICAgICAgICAgICB2YWx1ZTogZmlsdGVyLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIG9uQ2hhbmdlOiB0aGlzLm9uRmlsdGVyQ2hhbmdlfSksIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KEZpbHRlcklucHV0LCB7XG4gICAgICAgICAgICAgICAgICAgICAgICBwbGFjZWhvbGRlcjogXCJIaWdobGlnaHRcIiwgXG4gICAgICAgICAgICAgICAgICAgICAgICB0eXBlOiBcInRhZ1wiLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIGNvbG9yOiBcImhzbCg0OCwgMTAwJSwgNTAlKVwiLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIHZhbHVlOiBoaWdobGlnaHQsIFxuICAgICAgICAgICAgICAgICAgICAgICAgb25DaGFuZ2U6IHRoaXMub25IaWdobGlnaHRDaGFuZ2V9KSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoRmlsdGVySW5wdXQsIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHBsYWNlaG9sZGVyOiBcIkludGVyY2VwdFwiLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIHR5cGU6IFwicGF1c2VcIiwgXG4gICAgICAgICAgICAgICAgICAgICAgICBjb2xvcjogXCJoc2woMjA4LCA1NiUsIDUzJSlcIiwgXG4gICAgICAgICAgICAgICAgICAgICAgICB2YWx1ZTogaW50ZXJjZXB0LCBcbiAgICAgICAgICAgICAgICAgICAgICAgIG9uQ2hhbmdlOiB0aGlzLm9uSW50ZXJjZXB0Q2hhbmdlfSlcbiAgICAgICAgICAgICAgICApLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwiY2xlYXJmaXhcIn0pXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cblxudmFyIFZpZXdNZW51ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlZpZXdNZW51XCIsXG4gICAgc3RhdGljczoge1xuICAgICAgICB0aXRsZTogXCJWaWV3XCIsXG4gICAgICAgIHJvdXRlOiBcImZsb3dzXCJcbiAgICB9LFxuICAgIG1peGluczogW3V0aWxzLk5hdmlnYXRpb24sIHV0aWxzLlN0YXRlXSxcbiAgICB0b2dnbGVFdmVudExvZzogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZCA9IHt9O1xuXG4gICAgICAgIGlmICh0aGlzLmdldFF1ZXJ5KClbUXVlcnkuU0hPV19FVkVOVExPR10pIHtcbiAgICAgICAgICAgIGRbUXVlcnkuU0hPV19FVkVOVExPR10gPSB1bmRlZmluZWQ7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBkW1F1ZXJ5LlNIT1dfRVZFTlRMT0ddID0gXCJ0XCI7IC8vIGFueSBub24tZmFsc2UgdmFsdWUgd2lsbCBkbyBpdCwga2VlcCBpdCBzaG9ydFxuICAgICAgICB9XG5cbiAgICAgICAgdGhpcy5zZXRRdWVyeShkKTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgc2hvd0V2ZW50TG9nID0gdGhpcy5nZXRRdWVyeSgpW1F1ZXJ5LlNIT1dfRVZFTlRMT0ddO1xuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiYnV0dG9uXCIsIHtcbiAgICAgICAgICAgICAgICAgICAgY2xhc3NOYW1lOiBcImJ0biBcIiArIChzaG93RXZlbnRMb2cgPyBcImJ0bi1wcmltYXJ5XCIgOiBcImJ0bi1kZWZhdWx0XCIpLCBcbiAgICAgICAgICAgICAgICAgICAgb25DbGljazogdGhpcy50b2dnbGVFdmVudExvZ30sIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaVwiLCB7Y2xhc3NOYW1lOiBcImZhIGZhLWRhdGFiYXNlXCJ9KSwgXG4gICAgICAgICAgICAgICAgXCLCoFNob3cgRXZlbnRsb2dcIlxuICAgICAgICAgICAgICAgICksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIsIG51bGwsIFwiIFwiKVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG5cbnZhciBSZXBvcnRzTWVudSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJSZXBvcnRzTWVudVwiLFxuICAgIHN0YXRpY3M6IHtcbiAgICAgICAgdGl0bGU6IFwiVmlzdWFsaXphdGlvblwiLFxuICAgICAgICByb3V0ZTogXCJyZXBvcnRzXCJcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCBudWxsLCBcIlJlcG9ydHMgTWVudVwiKTtcbiAgICB9XG59KTtcblxudmFyIEZpbGVNZW51ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZpbGVNZW51XCIsXG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHJldHVybiB7XG4gICAgICAgICAgICBzaG93RmlsZU1lbnU6IGZhbHNlXG4gICAgICAgIH07XG4gICAgfSxcbiAgICBoYW5kbGVGaWxlQ2xpY2s6IGZ1bmN0aW9uIChlKSB7XG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcbiAgICAgICAgaWYgKCF0aGlzLnN0YXRlLnNob3dGaWxlTWVudSkge1xuICAgICAgICAgICAgdmFyIGNsb3NlID0gZnVuY3Rpb24gKCkge1xuICAgICAgICAgICAgICAgIHRoaXMuc2V0U3RhdGUoe3Nob3dGaWxlTWVudTogZmFsc2V9KTtcbiAgICAgICAgICAgICAgICBkb2N1bWVudC5yZW1vdmVFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgY2xvc2UpO1xuICAgICAgICAgICAgfS5iaW5kKHRoaXMpO1xuICAgICAgICAgICAgZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsIGNsb3NlKTtcblxuICAgICAgICAgICAgdGhpcy5zZXRTdGF0ZSh7XG4gICAgICAgICAgICAgICAgc2hvd0ZpbGVNZW51OiB0cnVlXG4gICAgICAgICAgICB9KTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgaGFuZGxlTmV3Q2xpY2s6IGZ1bmN0aW9uIChlKSB7XG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcbiAgICAgICAgaWYgKGNvbmZpcm0oXCJEZWxldGUgYWxsIGZsb3dzP1wiKSkge1xuICAgICAgICAgICAgRmxvd0FjdGlvbnMuY2xlYXIoKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgaGFuZGxlT3BlbkNsaWNrOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XG4gICAgICAgIGNvbnNvbGUuZXJyb3IoXCJ1bmltcGxlbWVudGVkOiBoYW5kbGVPcGVuQ2xpY2tcIik7XG4gICAgfSxcbiAgICBoYW5kbGVTYXZlQ2xpY2s6IGZ1bmN0aW9uIChlKSB7XG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcbiAgICAgICAgY29uc29sZS5lcnJvcihcInVuaW1wbGVtZW50ZWQ6IGhhbmRsZVNhdmVDbGlja1wiKTtcbiAgICB9LFxuICAgIGhhbmRsZVNodXRkb3duQ2xpY2s6IGZ1bmN0aW9uIChlKSB7XG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcbiAgICAgICAgY29uc29sZS5lcnJvcihcInVuaW1wbGVtZW50ZWQ6IGhhbmRsZVNodXRkb3duQ2xpY2tcIik7XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZpbGVNZW51Q2xhc3MgPSBcImRyb3Bkb3duIHB1bGwtbGVmdFwiICsgKHRoaXMuc3RhdGUuc2hvd0ZpbGVNZW51ID8gXCIgb3BlblwiIDogXCJcIik7XG5cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogZmlsZU1lbnVDbGFzc30sIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJhXCIsIHtocmVmOiBcIiNcIiwgY2xhc3NOYW1lOiBcInNwZWNpYWxcIiwgb25DbGljazogdGhpcy5oYW5kbGVGaWxlQ2xpY2t9LCBcIiBGaWxlIFwiKSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInVsXCIsIHtjbGFzc05hbWU6IFwiZHJvcGRvd24tbWVudVwiLCByb2xlOiBcIm1lbnVcIn0sIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwibGlcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiYVwiLCB7aHJlZjogXCIjXCIsIG9uQ2xpY2s6IHRoaXMuaGFuZGxlTmV3Q2xpY2t9LCBcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaVwiLCB7Y2xhc3NOYW1lOiBcImZhIGZhLWZ3IGZhLWZpbGVcIn0pLCBcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBcIk5ld1wiXG4gICAgICAgICAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICAgICAgICAgICksIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwibGlcIiwge3JvbGU6IFwicHJlc2VudGF0aW9uXCIsIGNsYXNzTmFtZTogXCJkaXZpZGVyXCJ9KSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJsaVwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJhXCIsIHtocmVmOiBcImh0dHA6Ly9taXRtLml0L1wiLCB0YXJnZXQ6IFwiX2JsYW5rXCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaVwiLCB7Y2xhc3NOYW1lOiBcImZhIGZhLWZ3IGZhLWV4dGVybmFsLWxpbmtcIn0pLCBcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBcIkluc3RhbGwgQ2VydGlmaWNhdGVzLi4uXCJcbiAgICAgICAgICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgICAgIC8qXG4gICAgICAgICAgICAgICAgIDxsaT5cbiAgICAgICAgICAgICAgICAgPGEgaHJlZj1cIiNcIiBvbkNsaWNrPXt0aGlzLmhhbmRsZU9wZW5DbGlja30+XG4gICAgICAgICAgICAgICAgIDxpIGNsYXNzTmFtZT1cImZhIGZhLWZ3IGZhLWZvbGRlci1vcGVuXCI+PC9pPlxuICAgICAgICAgICAgICAgICBPcGVuXG4gICAgICAgICAgICAgICAgIDwvYT5cbiAgICAgICAgICAgICAgICAgPC9saT5cbiAgICAgICAgICAgICAgICAgPGxpPlxuICAgICAgICAgICAgICAgICA8YSBocmVmPVwiI1wiIG9uQ2xpY2s9e3RoaXMuaGFuZGxlU2F2ZUNsaWNrfT5cbiAgICAgICAgICAgICAgICAgPGkgY2xhc3NOYW1lPVwiZmEgZmEtZncgZmEtc2F2ZVwiPjwvaT5cbiAgICAgICAgICAgICAgICAgU2F2ZVxuICAgICAgICAgICAgICAgICA8L2E+XG4gICAgICAgICAgICAgICAgIDwvbGk+XG4gICAgICAgICAgICAgICAgIDxsaSByb2xlPVwicHJlc2VudGF0aW9uXCIgY2xhc3NOYW1lPVwiZGl2aWRlclwiPjwvbGk+XG4gICAgICAgICAgICAgICAgIDxsaT5cbiAgICAgICAgICAgICAgICAgPGEgaHJlZj1cIiNcIiBvbkNsaWNrPXt0aGlzLmhhbmRsZVNodXRkb3duQ2xpY2t9PlxuICAgICAgICAgICAgICAgICA8aSBjbGFzc05hbWU9XCJmYSBmYS1mdyBmYS1wbHVnXCI+PC9pPlxuICAgICAgICAgICAgICAgICBTaHV0ZG93blxuICAgICAgICAgICAgICAgICA8L2E+XG4gICAgICAgICAgICAgICAgIDwvbGk+XG4gICAgICAgICAgICAgICAgICovXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG5cbnZhciBoZWFkZXJfZW50cmllcyA9IFtNYWluTWVudSwgVmlld01lbnUgLyosIFJlcG9ydHNNZW51ICovXTtcblxuXG52YXIgSGVhZGVyID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkhlYWRlclwiLFxuICAgIG1peGluczogW3V0aWxzLk5hdmlnYXRpb25dLFxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgYWN0aXZlOiBoZWFkZXJfZW50cmllc1swXVxuICAgICAgICB9O1xuICAgIH0sXG4gICAgaGFuZGxlQ2xpY2s6IGZ1bmN0aW9uIChhY3RpdmUsIGUpIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICB0aGlzLnJlcGxhY2VXaXRoKGFjdGl2ZS5yb3V0ZSk7XG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe2FjdGl2ZTogYWN0aXZlfSk7XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGhlYWRlciA9IGhlYWRlcl9lbnRyaWVzLm1hcChmdW5jdGlvbiAoZW50cnksIGkpIHtcbiAgICAgICAgICAgIHZhciBjbGFzc2VzID0gUmVhY3QuYWRkb25zLmNsYXNzU2V0KHtcbiAgICAgICAgICAgICAgICBhY3RpdmU6IGVudHJ5ID09IHRoaXMuc3RhdGUuYWN0aXZlXG4gICAgICAgICAgICB9KTtcbiAgICAgICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImFcIiwge2tleTogaSwgXG4gICAgICAgICAgICAgICAgICAgIGhyZWY6IFwiI1wiLCBcbiAgICAgICAgICAgICAgICAgICAgY2xhc3NOYW1lOiBjbGFzc2VzLCBcbiAgICAgICAgICAgICAgICAgICAgb25DbGljazogdGhpcy5oYW5kbGVDbGljay5iaW5kKHRoaXMsIGVudHJ5KVxuICAgICAgICAgICAgICAgIH0sIFxuICAgICAgICAgICAgICAgICAgICAgZW50cnkudGl0bGVcbiAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICApO1xuICAgICAgICB9LmJpbmQodGhpcykpO1xuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaGVhZGVyXCIsIG51bGwsIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJ0aXRsZS1iYXJcIn0sIFxuICAgICAgICAgICAgICAgICAgICBcIm1pdG1wcm94eSBcIiwgIHRoaXMucHJvcHMuc2V0dGluZ3MudmVyc2lvblxuICAgICAgICAgICAgICAgICksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJuYXZcIiwge2NsYXNzTmFtZTogXCJuYXYtdGFicyBuYXYtdGFicy1sZ1wifSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoRmlsZU1lbnUsIG51bGwpLCBcbiAgICAgICAgICAgICAgICAgICAgaGVhZGVyXG4gICAgICAgICAgICAgICAgKSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcIm1lbnVcIn0sIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KHRoaXMuc3RhdGUuYWN0aXZlLCB7c2V0dGluZ3M6IHRoaXMucHJvcHMuc2V0dGluZ3N9KVxuICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxuXG5tb2R1bGUuZXhwb3J0cyA9IHtcbiAgICBIZWFkZXI6IEhlYWRlclxufSIsInZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcblxudmFyIHV0aWxzID0gcmVxdWlyZShcIi4vdXRpbHMuanNcIik7XG52YXIgdG9wdXRpbHMgPSByZXF1aXJlKFwiLi4vdXRpbHMuanNcIik7XG52YXIgdmlld3MgPSByZXF1aXJlKFwiLi4vc3RvcmUvdmlldy5qc1wiKTtcbnZhciBGaWx0ID0gcmVxdWlyZShcIi4uL2ZpbHQvZmlsdC5qc1wiKTtcbkZsb3dUYWJsZSA9IHJlcXVpcmUoXCIuL2Zsb3d0YWJsZS5qc1wiKTtcbnZhciBmbG93ZGV0YWlsID0gcmVxdWlyZShcIi4vZmxvd2RldGFpbC5qc1wiKTtcblxuXG52YXIgTWFpblZpZXcgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiTWFpblZpZXdcIixcbiAgICBtaXhpbnM6IFt1dGlscy5OYXZpZ2F0aW9uLCB1dGlscy5TdGF0ZV0sXG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMub25RdWVyeUNoYW5nZShRdWVyeS5GSUxURVIsIGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHRoaXMuc3RhdGUudmlldy5yZWNhbGN1bGF0ZSh0aGlzLmdldFZpZXdGaWx0KCksIHRoaXMuZ2V0Vmlld1NvcnQoKSk7XG4gICAgICAgIH0uYmluZCh0aGlzKSk7XG4gICAgICAgIHRoaXMub25RdWVyeUNoYW5nZShRdWVyeS5ISUdITElHSFQsIGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHRoaXMuc3RhdGUudmlldy5yZWNhbGN1bGF0ZSh0aGlzLmdldFZpZXdGaWx0KCksIHRoaXMuZ2V0Vmlld1NvcnQoKSk7XG4gICAgICAgIH0uYmluZCh0aGlzKSk7XG4gICAgICAgIHJldHVybiB7XG4gICAgICAgICAgICBmbG93czogW11cbiAgICAgICAgfTtcbiAgICB9LFxuICAgIGdldFZpZXdGaWx0OiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRyeSB7XG4gICAgICAgICAgICB2YXIgZmlsdCA9IEZpbHQucGFyc2UodGhpcy5nZXRRdWVyeSgpW1F1ZXJ5LkZJTFRFUl0gfHwgXCJcIik7XG4gICAgICAgICAgICB2YXIgaGlnaGxpZ2h0U3RyID0gdGhpcy5nZXRRdWVyeSgpW1F1ZXJ5LkhJR0hMSUdIVF07XG4gICAgICAgICAgICB2YXIgaGlnaGxpZ2h0ID0gaGlnaGxpZ2h0U3RyID8gRmlsdC5wYXJzZShoaWdobGlnaHRTdHIpIDogZmFsc2U7XG4gICAgICAgIH0gY2F0Y2ggKGUpIHtcbiAgICAgICAgICAgIGNvbnNvbGUuZXJyb3IoXCJFcnJvciB3aGVuIHByb2Nlc3NpbmcgZmlsdGVyOiBcIiArIGUpO1xuICAgICAgICB9XG5cbiAgICAgICAgcmV0dXJuIGZ1bmN0aW9uIGZpbHRlcl9hbmRfaGlnaGxpZ2h0KGZsb3cpIHtcbiAgICAgICAgICAgIGlmICghdGhpcy5faGlnaGxpZ2h0KSB7XG4gICAgICAgICAgICAgICAgdGhpcy5faGlnaGxpZ2h0ID0ge307XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICB0aGlzLl9oaWdobGlnaHRbZmxvdy5pZF0gPSBoaWdobGlnaHQgJiYgaGlnaGxpZ2h0KGZsb3cpO1xuICAgICAgICAgICAgcmV0dXJuIGZpbHQoZmxvdyk7XG4gICAgICAgIH07XG4gICAgfSxcbiAgICBnZXRWaWV3U29ydDogZnVuY3Rpb24gKCkge1xuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbFJlY2VpdmVQcm9wczogZnVuY3Rpb24gKG5leHRQcm9wcykge1xuICAgICAgICBpZiAobmV4dFByb3BzLmZsb3dTdG9yZSAhPT0gdGhpcy5wcm9wcy5mbG93U3RvcmUpIHtcbiAgICAgICAgICAgIHRoaXMuY2xvc2VWaWV3KCk7XG4gICAgICAgICAgICB0aGlzLm9wZW5WaWV3KG5leHRQcm9wcy5mbG93U3RvcmUpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBvcGVuVmlldzogZnVuY3Rpb24gKHN0b3JlKSB7XG4gICAgICAgIHZhciB2aWV3ID0gbmV3IHZpZXdzLlN0b3JlVmlldyhzdG9yZSwgdGhpcy5nZXRWaWV3RmlsdCgpLCB0aGlzLmdldFZpZXdTb3J0KCkpO1xuICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgIHZpZXc6IHZpZXdcbiAgICAgICAgfSk7XG5cbiAgICAgICAgdmlldy5hZGRMaXN0ZW5lcihcInJlY2FsY3VsYXRlXCIsIHRoaXMub25SZWNhbGN1bGF0ZSk7XG4gICAgICAgIHZpZXcuYWRkTGlzdGVuZXIoXCJhZGQgdXBkYXRlIHJlbW92ZVwiLCB0aGlzLm9uVXBkYXRlKTtcbiAgICAgICAgdmlldy5hZGRMaXN0ZW5lcihcInJlbW92ZVwiLCB0aGlzLm9uUmVtb3ZlKTtcbiAgICB9LFxuICAgIG9uUmVjYWxjdWxhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5mb3JjZVVwZGF0ZSgpO1xuICAgICAgICB2YXIgc2VsZWN0ZWQgPSB0aGlzLmdldFNlbGVjdGVkKCk7XG4gICAgICAgIGlmIChzZWxlY3RlZCkge1xuICAgICAgICAgICAgdGhpcy5yZWZzLmZsb3dUYWJsZS5zY3JvbGxJbnRvVmlldyhzZWxlY3RlZCk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIG9uVXBkYXRlOiBmdW5jdGlvbiAoZmxvdykge1xuICAgICAgICBpZiAoZmxvdy5pZCA9PT0gdGhpcy5nZXRQYXJhbXMoKS5mbG93SWQpIHtcbiAgICAgICAgICAgIHRoaXMuZm9yY2VVcGRhdGUoKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgb25SZW1vdmU6IGZ1bmN0aW9uIChmbG93X2lkLCBpbmRleCkge1xuICAgICAgICBpZiAoZmxvd19pZCA9PT0gdGhpcy5nZXRQYXJhbXMoKS5mbG93SWQpIHtcbiAgICAgICAgICAgIHZhciBmbG93X3RvX3NlbGVjdCA9IHRoaXMuc3RhdGUudmlldy5saXN0W01hdGgubWluKGluZGV4LCB0aGlzLnN0YXRlLnZpZXcubGlzdC5sZW5ndGggLTEpXTtcbiAgICAgICAgICAgIHRoaXMuc2VsZWN0RmxvdyhmbG93X3RvX3NlbGVjdCk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGNsb3NlVmlldzogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLnN0YXRlLnZpZXcuY2xvc2UoKTtcbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxNb3VudDogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLm9wZW5WaWV3KHRoaXMucHJvcHMuZmxvd1N0b3JlKTtcbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxVbm1vdW50OiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuY2xvc2VWaWV3KCk7XG4gICAgfSxcbiAgICBzZWxlY3RGbG93OiBmdW5jdGlvbiAoZmxvdykge1xuICAgICAgICBpZiAoZmxvdykge1xuICAgICAgICAgICAgdGhpcy5yZXBsYWNlV2l0aChcbiAgICAgICAgICAgICAgICBcImZsb3dcIixcbiAgICAgICAgICAgICAgICB7XG4gICAgICAgICAgICAgICAgICAgIGZsb3dJZDogZmxvdy5pZCxcbiAgICAgICAgICAgICAgICAgICAgZGV0YWlsVGFiOiB0aGlzLmdldFBhcmFtcygpLmRldGFpbFRhYiB8fCBcInJlcXVlc3RcIlxuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICk7XG4gICAgICAgICAgICB0aGlzLnJlZnMuZmxvd1RhYmxlLnNjcm9sbEludG9WaWV3KGZsb3cpO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgdGhpcy5yZXBsYWNlV2l0aChcImZsb3dzXCIsIHt9KTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgc2VsZWN0Rmxvd1JlbGF0aXZlOiBmdW5jdGlvbiAoc2hpZnQpIHtcbiAgICAgICAgdmFyIGZsb3dzID0gdGhpcy5zdGF0ZS52aWV3Lmxpc3Q7XG4gICAgICAgIHZhciBpbmRleDtcbiAgICAgICAgaWYgKCF0aGlzLmdldFBhcmFtcygpLmZsb3dJZCkge1xuICAgICAgICAgICAgaWYgKHNoaWZ0ID4gMCkge1xuICAgICAgICAgICAgICAgIGluZGV4ID0gZmxvd3MubGVuZ3RoIC0gMTtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgaW5kZXggPSAwO1xuICAgICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgdmFyIGN1cnJGbG93SWQgPSB0aGlzLmdldFBhcmFtcygpLmZsb3dJZDtcbiAgICAgICAgICAgIHZhciBpID0gZmxvd3MubGVuZ3RoO1xuICAgICAgICAgICAgd2hpbGUgKGktLSkge1xuICAgICAgICAgICAgICAgIGlmIChmbG93c1tpXS5pZCA9PT0gY3VyckZsb3dJZCkge1xuICAgICAgICAgICAgICAgICAgICBpbmRleCA9IGk7XG4gICAgICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGluZGV4ID0gTWF0aC5taW4oXG4gICAgICAgICAgICAgICAgTWF0aC5tYXgoMCwgaW5kZXggKyBzaGlmdCksXG4gICAgICAgICAgICAgICAgZmxvd3MubGVuZ3RoIC0gMSk7XG4gICAgICAgIH1cbiAgICAgICAgdGhpcy5zZWxlY3RGbG93KGZsb3dzW2luZGV4XSk7XG4gICAgfSxcbiAgICBvbktleURvd246IGZ1bmN0aW9uIChlKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5nZXRTZWxlY3RlZCgpO1xuICAgICAgICBpZiAoZS5jdHJsS2V5KSB7XG4gICAgICAgICAgICByZXR1cm47XG4gICAgICAgIH1cbiAgICAgICAgc3dpdGNoIChlLmtleUNvZGUpIHtcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5Lks6XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5VUDpcbiAgICAgICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3dSZWxhdGl2ZSgtMSk7XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5KOlxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuRE9XTjpcbiAgICAgICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3dSZWxhdGl2ZSgrMSk7XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5TUEFDRTpcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LlBBR0VfRE9XTjpcbiAgICAgICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3dSZWxhdGl2ZSgrMTApO1xuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuUEFHRV9VUDpcbiAgICAgICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3dSZWxhdGl2ZSgtMTApO1xuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuRU5EOlxuICAgICAgICAgICAgICAgIHRoaXMuc2VsZWN0Rmxvd1JlbGF0aXZlKCsxZTEwKTtcbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LkhPTUU6XG4gICAgICAgICAgICAgICAgdGhpcy5zZWxlY3RGbG93UmVsYXRpdmUoLTFlMTApO1xuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuRVNDOlxuICAgICAgICAgICAgICAgIHRoaXMuc2VsZWN0RmxvdyhudWxsKTtcbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5Lkg6XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5MRUZUOlxuICAgICAgICAgICAgICAgIGlmICh0aGlzLnJlZnMuZmxvd0RldGFpbHMpIHtcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5yZWZzLmZsb3dEZXRhaWxzLm5leHRUYWIoLTEpO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5Lkw6XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5UQUI6XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5SSUdIVDpcbiAgICAgICAgICAgICAgICBpZiAodGhpcy5yZWZzLmZsb3dEZXRhaWxzKSB7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMucmVmcy5mbG93RGV0YWlscy5uZXh0VGFiKCsxKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5DOlxuICAgICAgICAgICAgICAgIGlmIChlLnNoaWZ0S2V5KSB7XG4gICAgICAgICAgICAgICAgICAgIEZsb3dBY3Rpb25zLmNsZWFyKCk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuRDpcbiAgICAgICAgICAgICAgICBpZiAoZmxvdykge1xuICAgICAgICAgICAgICAgICAgICBpZiAoZS5zaGlmdEtleSkge1xuICAgICAgICAgICAgICAgICAgICAgICAgRmxvd0FjdGlvbnMuZHVwbGljYXRlKGZsb3cpO1xuICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgRmxvd0FjdGlvbnMuZGVsZXRlKGZsb3cpO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuQTpcbiAgICAgICAgICAgICAgICBpZiAoZS5zaGlmdEtleSkge1xuICAgICAgICAgICAgICAgICAgICBGbG93QWN0aW9ucy5hY2NlcHRfYWxsKCk7XG4gICAgICAgICAgICAgICAgfSBlbHNlIGlmIChmbG93ICYmIGZsb3cuaW50ZXJjZXB0ZWQpIHtcbiAgICAgICAgICAgICAgICAgICAgRmxvd0FjdGlvbnMuYWNjZXB0KGZsb3cpO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LlI6XG4gICAgICAgICAgICAgICAgaWYgKCFlLnNoaWZ0S2V5ICYmIGZsb3cpIHtcbiAgICAgICAgICAgICAgICAgICAgRmxvd0FjdGlvbnMucmVwbGF5KGZsb3cpO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LlY6XG4gICAgICAgICAgICAgICAgaWYoZS5zaGlmdEtleSAmJiBmbG93ICYmIGZsb3cubW9kaWZpZWQpIHtcbiAgICAgICAgICAgICAgICAgICAgRmxvd0FjdGlvbnMucmV2ZXJ0KGZsb3cpO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGRlZmF1bHQ6XG4gICAgICAgICAgICAgICAgY29uc29sZS5kZWJ1ZyhcImtleWRvd25cIiwgZS5rZXlDb2RlKTtcbiAgICAgICAgICAgICAgICByZXR1cm47XG4gICAgICAgIH1cbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgIH0sXG4gICAgZ2V0U2VsZWN0ZWQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIHRoaXMucHJvcHMuZmxvd1N0b3JlLmdldCh0aGlzLmdldFBhcmFtcygpLmZsb3dJZCk7XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIHNlbGVjdGVkID0gdGhpcy5nZXRTZWxlY3RlZCgpO1xuXG4gICAgICAgIHZhciBkZXRhaWxzO1xuICAgICAgICBpZiAoc2VsZWN0ZWQpIHtcbiAgICAgICAgICAgIGRldGFpbHMgPSBbXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudCh1dGlscy5TcGxpdHRlciwge2tleTogXCJzcGxpdHRlclwifSksXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChmbG93ZGV0YWlsLkZsb3dEZXRhaWwsIHtrZXk6IFwiZmxvd0RldGFpbHNcIiwgcmVmOiBcImZsb3dEZXRhaWxzXCIsIGZsb3c6IHNlbGVjdGVkfSlcbiAgICAgICAgICAgIF07XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBkZXRhaWxzID0gbnVsbDtcbiAgICAgICAgfVxuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwibWFpbi12aWV3XCIsIG9uS2V5RG93bjogdGhpcy5vbktleURvd24sIHRhYkluZGV4OiBcIjBcIn0sIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoRmxvd1RhYmxlLCB7cmVmOiBcImZsb3dUYWJsZVwiLCBcbiAgICAgICAgICAgICAgICAgICAgdmlldzogdGhpcy5zdGF0ZS52aWV3LCBcbiAgICAgICAgICAgICAgICAgICAgc2VsZWN0RmxvdzogdGhpcy5zZWxlY3RGbG93LCBcbiAgICAgICAgICAgICAgICAgICAgc2VsZWN0ZWQ6IHNlbGVjdGVkfSksIFxuICAgICAgICAgICAgICAgIGRldGFpbHNcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxubW9kdWxlLmV4cG9ydHMgPSBNYWluVmlldztcbiIsInZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcbnZhciBSZWFjdFJvdXRlciA9IHJlcXVpcmUoXCJyZWFjdC1yb3V0ZXJcIik7XG52YXIgXyA9IHJlcXVpcmUoXCJsb2Rhc2hcIik7XG5cbnZhciB1dGlscyA9IHJlcXVpcmUoXCIuL3V0aWxzLmpzXCIpO1xudmFyIE1haW5WaWV3ID0gcmVxdWlyZShcIi4vbWFpbnZpZXcuanNcIik7XG52YXIgRm9vdGVyID0gcmVxdWlyZShcIi4vZm9vdGVyLmpzXCIpO1xudmFyIGhlYWRlciA9IHJlcXVpcmUoXCIuL2hlYWRlci5qc1wiKTtcbnZhciBFdmVudExvZyA9IHJlcXVpcmUoXCIuL2V2ZW50bG9nLmpzXCIpO1xudmFyIHN0b3JlID0gcmVxdWlyZShcIi4uL3N0b3JlL3N0b3JlLmpzXCIpO1xuXG5cbi8vVE9ETzogTW92ZSBvdXQgb2YgaGVyZSwganVzdCBhIHN0dWIuXG52YXIgUmVwb3J0cyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJSZXBvcnRzXCIsXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIG51bGwsIFwiUmVwb3J0RWRpdG9yXCIpO1xuICAgIH1cbn0pO1xuXG5cbnZhciBQcm94eUFwcE1haW4gPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiUHJveHlBcHBNYWluXCIsXG4gICAgbWl4aW5zOiBbdXRpbHMuU3RhdGVdLFxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZXZlbnRTdG9yZSA9IG5ldyBzdG9yZS5FdmVudExvZ1N0b3JlKCk7XG4gICAgICAgIHZhciBmbG93U3RvcmUgPSBuZXcgc3RvcmUuRmxvd1N0b3JlKCk7XG4gICAgICAgIHZhciBzZXR0aW5ncyA9IG5ldyBzdG9yZS5TZXR0aW5nc1N0b3JlKCk7XG5cbiAgICAgICAgLy8gRGVmYXVsdCBTZXR0aW5ncyBiZWZvcmUgZmV0Y2hcbiAgICAgICAgXy5leHRlbmQoc2V0dGluZ3MuZGljdCx7XG4gICAgICAgIH0pO1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgc2V0dGluZ3M6IHNldHRpbmdzLFxuICAgICAgICAgICAgZmxvd1N0b3JlOiBmbG93U3RvcmUsXG4gICAgICAgICAgICBldmVudFN0b3JlOiBldmVudFN0b3JlXG4gICAgICAgIH07XG4gICAgfSxcbiAgICBjb21wb25lbnREaWRNb3VudDogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLnN0YXRlLnNldHRpbmdzLmFkZExpc3RlbmVyKFwicmVjYWxjdWxhdGVcIiwgdGhpcy5vblNldHRpbmdzQ2hhbmdlKTtcbiAgICAgICAgd2luZG93LmFwcCA9IHRoaXM7XG4gICAgfSxcbiAgICBjb21wb25lbnRXaWxsVW5tb3VudDogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLnN0YXRlLnNldHRpbmdzLnJlbW92ZUxpc3RlbmVyKFwicmVjYWxjdWxhdGVcIiwgdGhpcy5vblNldHRpbmdzQ2hhbmdlKTtcbiAgICB9LFxuICAgIG9uU2V0dGluZ3NDaGFuZ2U6IGZ1bmN0aW9uKCl7XG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe1xuICAgICAgICAgICAgc2V0dGluZ3M6IHRoaXMuc3RhdGUuc2V0dGluZ3NcbiAgICAgICAgfSk7XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcblxuICAgICAgICB2YXIgZXZlbnRsb2c7XG4gICAgICAgIGlmICh0aGlzLmdldFF1ZXJ5KClbUXVlcnkuU0hPV19FVkVOVExPR10pIHtcbiAgICAgICAgICAgIGV2ZW50bG9nID0gW1xuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQodXRpbHMuU3BsaXR0ZXIsIHtrZXk6IFwic3BsaXR0ZXJcIiwgYXhpczogXCJ5XCJ9KSxcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KEV2ZW50TG9nLCB7a2V5OiBcImV2ZW50bG9nXCIsIGV2ZW50U3RvcmU6IHRoaXMuc3RhdGUuZXZlbnRTdG9yZX0pXG4gICAgICAgICAgICBdO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgZXZlbnRsb2cgPSBudWxsO1xuICAgICAgICB9XG5cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2lkOiBcImNvbnRhaW5lclwifSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChoZWFkZXIuSGVhZGVyLCB7c2V0dGluZ3M6IHRoaXMuc3RhdGUuc2V0dGluZ3MuZGljdH0pLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFJvdXRlSGFuZGxlciwge3NldHRpbmdzOiB0aGlzLnN0YXRlLnNldHRpbmdzLmRpY3QsIGZsb3dTdG9yZTogdGhpcy5zdGF0ZS5mbG93U3RvcmV9KSwgXG4gICAgICAgICAgICAgICAgZXZlbnRsb2csIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoRm9vdGVyLCB7c2V0dGluZ3M6IHRoaXMuc3RhdGUuc2V0dGluZ3MuZGljdH0pXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cblxudmFyIFJvdXRlID0gUmVhY3RSb3V0ZXIuUm91dGU7XG52YXIgUm91dGVIYW5kbGVyID0gUmVhY3RSb3V0ZXIuUm91dGVIYW5kbGVyO1xudmFyIFJlZGlyZWN0ID0gUmVhY3RSb3V0ZXIuUmVkaXJlY3Q7XG52YXIgRGVmYXVsdFJvdXRlID0gUmVhY3RSb3V0ZXIuRGVmYXVsdFJvdXRlO1xudmFyIE5vdEZvdW5kUm91dGUgPSBSZWFjdFJvdXRlci5Ob3RGb3VuZFJvdXRlO1xuXG5cbnZhciByb3V0ZXMgPSAoXG4gICAgUmVhY3QuY3JlYXRlRWxlbWVudChSb3V0ZSwge3BhdGg6IFwiL1wiLCBoYW5kbGVyOiBQcm94eUFwcE1haW59LCBcbiAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChSb3V0ZSwge25hbWU6IFwiZmxvd3NcIiwgcGF0aDogXCJmbG93c1wiLCBoYW5kbGVyOiBNYWluVmlld30pLCBcbiAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChSb3V0ZSwge25hbWU6IFwiZmxvd1wiLCBwYXRoOiBcImZsb3dzLzpmbG93SWQvOmRldGFpbFRhYlwiLCBoYW5kbGVyOiBNYWluVmlld30pLCBcbiAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChSb3V0ZSwge25hbWU6IFwicmVwb3J0c1wiLCBoYW5kbGVyOiBSZXBvcnRzfSksIFxuICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFJlZGlyZWN0LCB7cGF0aDogXCIvXCIsIHRvOiBcImZsb3dzXCJ9KVxuICAgIClcbik7XG5cbm1vZHVsZS5leHBvcnRzID0ge1xuICAgIHJvdXRlczogcm91dGVzXG59O1xuXG4iLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XG52YXIgUmVhY3RSb3V0ZXIgPSByZXF1aXJlKFwicmVhY3Qtcm91dGVyXCIpO1xudmFyIF8gPSByZXF1aXJlKFwibG9kYXNoXCIpO1xuXG4vL1JlYWN0IHV0aWxzLiBGb3Igb3RoZXIgdXRpbGl0aWVzLCBzZWUgLi4vdXRpbHMuanNcblxuLy8gaHR0cDovL2Jsb2cudmpldXguY29tLzIwMTMvamF2YXNjcmlwdC9zY3JvbGwtcG9zaXRpb24td2l0aC1yZWFjdC5odG1sIChhbHNvIGNvbnRhaW5zIGludmVyc2UgZXhhbXBsZSlcbnZhciBBdXRvU2Nyb2xsTWl4aW4gPSB7XG4gICAgY29tcG9uZW50V2lsbFVwZGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgbm9kZSA9IHRoaXMuZ2V0RE9NTm9kZSgpO1xuICAgICAgICB0aGlzLl9zaG91bGRTY3JvbGxCb3R0b20gPSAoXG4gICAgICAgICAgICBub2RlLnNjcm9sbFRvcCAhPT0gMCAmJlxuICAgICAgICAgICAgbm9kZS5zY3JvbGxUb3AgKyBub2RlLmNsaWVudEhlaWdodCA9PT0gbm9kZS5zY3JvbGxIZWlnaHRcbiAgICAgICAgKTtcbiAgICB9LFxuICAgIGNvbXBvbmVudERpZFVwZGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICBpZiAodGhpcy5fc2hvdWxkU2Nyb2xsQm90dG9tKSB7XG4gICAgICAgICAgICB2YXIgbm9kZSA9IHRoaXMuZ2V0RE9NTm9kZSgpO1xuICAgICAgICAgICAgbm9kZS5zY3JvbGxUb3AgPSBub2RlLnNjcm9sbEhlaWdodDtcbiAgICAgICAgfVxuICAgIH0sXG59O1xuXG5cbnZhciBTdGlja3lIZWFkTWl4aW4gPSB7XG4gICAgYWRqdXN0SGVhZDogZnVuY3Rpb24gKCkge1xuICAgICAgICAvLyBBYnVzaW5nIENTUyB0cmFuc2Zvcm1zIHRvIHNldCB0aGUgZWxlbWVudFxuICAgICAgICAvLyByZWZlcmVuY2VkIGFzIGhlYWQgaW50byBzb21lIGtpbmQgb2YgcG9zaXRpb246c3RpY2t5LlxuICAgICAgICB2YXIgaGVhZCA9IHRoaXMucmVmcy5oZWFkLmdldERPTU5vZGUoKTtcbiAgICAgICAgaGVhZC5zdHlsZS50cmFuc2Zvcm0gPSBcInRyYW5zbGF0ZSgwLFwiICsgdGhpcy5nZXRET01Ob2RlKCkuc2Nyb2xsVG9wICsgXCJweClcIjtcbiAgICB9XG59O1xuXG5cbnZhciBOYXZpZ2F0aW9uID0gXy5leHRlbmQoe30sIFJlYWN0Um91dGVyLk5hdmlnYXRpb24sIHtcbiAgICBzZXRRdWVyeTogZnVuY3Rpb24gKGRpY3QpIHtcbiAgICAgICAgdmFyIHEgPSB0aGlzLmNvbnRleHQuZ2V0Q3VycmVudFF1ZXJ5KCk7XG4gICAgICAgIGZvcih2YXIgaSBpbiBkaWN0KXtcbiAgICAgICAgICAgIGlmKGRpY3QuaGFzT3duUHJvcGVydHkoaSkpe1xuICAgICAgICAgICAgICAgIHFbaV0gPSBkaWN0W2ldIHx8IHVuZGVmaW5lZDsgLy9mYWxzZXkgdmFsdWVzIHNoYWxsIGJlIHJlbW92ZWQuXG4gICAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgICAgcS5fID0gXCJfXCI7IC8vIHdvcmthcm91bmQgZm9yIGh0dHBzOi8vZ2l0aHViLmNvbS9yYWNrdC9yZWFjdC1yb3V0ZXIvcHVsbC81OTlcbiAgICAgICAgdGhpcy5yZXBsYWNlV2l0aCh0aGlzLmNvbnRleHQuZ2V0Q3VycmVudFBhdGgoKSwgdGhpcy5jb250ZXh0LmdldEN1cnJlbnRQYXJhbXMoKSwgcSk7XG4gICAgfSxcbiAgICByZXBsYWNlV2l0aDogZnVuY3Rpb24ocm91dGVOYW1lT3JQYXRoLCBwYXJhbXMsIHF1ZXJ5KSB7XG4gICAgICAgIGlmKHJvdXRlTmFtZU9yUGF0aCA9PT0gdW5kZWZpbmVkKXtcbiAgICAgICAgICAgIHJvdXRlTmFtZU9yUGF0aCA9IHRoaXMuY29udGV4dC5nZXRDdXJyZW50UGF0aCgpO1xuICAgICAgICB9XG4gICAgICAgIGlmKHBhcmFtcyA9PT0gdW5kZWZpbmVkKXtcbiAgICAgICAgICAgIHBhcmFtcyA9IHRoaXMuY29udGV4dC5nZXRDdXJyZW50UGFyYW1zKCk7XG4gICAgICAgIH1cbiAgICAgICAgaWYocXVlcnkgPT09IHVuZGVmaW5lZCl7XG4gICAgICAgICAgICBxdWVyeSA9IHRoaXMuY29udGV4dC5nZXRDdXJyZW50UXVlcnkoKTtcbiAgICAgICAgfVxuICAgICAgICBSZWFjdFJvdXRlci5OYXZpZ2F0aW9uLnJlcGxhY2VXaXRoLmNhbGwodGhpcywgcm91dGVOYW1lT3JQYXRoLCBwYXJhbXMsIHF1ZXJ5KTtcbiAgICB9XG59KTtcbl8uZXh0ZW5kKE5hdmlnYXRpb24uY29udGV4dFR5cGVzLCBSZWFjdFJvdXRlci5TdGF0ZS5jb250ZXh0VHlwZXMpO1xuXG52YXIgU3RhdGUgPSBfLmV4dGVuZCh7fSwgUmVhY3RSb3V0ZXIuU3RhdGUsIHtcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5fcXVlcnkgPSB0aGlzLmNvbnRleHQuZ2V0Q3VycmVudFF1ZXJ5KCk7XG4gICAgICAgIHRoaXMuX3F1ZXJ5V2F0Y2hlcyA9IFtdO1xuICAgICAgICByZXR1cm4gbnVsbDtcbiAgICB9LFxuICAgIG9uUXVlcnlDaGFuZ2U6IGZ1bmN0aW9uIChrZXksIGNhbGxiYWNrKSB7XG4gICAgICAgIHRoaXMuX3F1ZXJ5V2F0Y2hlcy5wdXNoKHtcbiAgICAgICAgICAgIGtleToga2V5LFxuICAgICAgICAgICAgY2FsbGJhY2s6IGNhbGxiYWNrXG4gICAgICAgIH0pO1xuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbFJlY2VpdmVQcm9wczogZnVuY3Rpb24gKG5leHRQcm9wcywgbmV4dFN0YXRlKSB7XG4gICAgICAgIHZhciBxID0gdGhpcy5jb250ZXh0LmdldEN1cnJlbnRRdWVyeSgpO1xuICAgICAgICBmb3IgKHZhciBpID0gMDsgaSA8IHRoaXMuX3F1ZXJ5V2F0Y2hlcy5sZW5ndGg7IGkrKykge1xuICAgICAgICAgICAgdmFyIHdhdGNoID0gdGhpcy5fcXVlcnlXYXRjaGVzW2ldO1xuICAgICAgICAgICAgaWYgKHRoaXMuX3F1ZXJ5W3dhdGNoLmtleV0gIT09IHFbd2F0Y2gua2V5XSkge1xuICAgICAgICAgICAgICAgIHdhdGNoLmNhbGxiYWNrKHRoaXMuX3F1ZXJ5W3dhdGNoLmtleV0sIHFbd2F0Y2gua2V5XSwgd2F0Y2gua2V5KTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgICB0aGlzLl9xdWVyeSA9IHE7XG4gICAgfVxufSk7XG5cbnZhciBTcGxpdHRlciA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJTcGxpdHRlclwiLFxuICAgIGdldERlZmF1bHRQcm9wczogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgYXhpczogXCJ4XCJcbiAgICAgICAgfTtcbiAgICB9LFxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgYXBwbGllZDogZmFsc2UsXG4gICAgICAgICAgICBzdGFydFg6IGZhbHNlLFxuICAgICAgICAgICAgc3RhcnRZOiBmYWxzZVxuICAgICAgICB9O1xuICAgIH0sXG4gICAgb25Nb3VzZURvd246IGZ1bmN0aW9uIChlKSB7XG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe1xuICAgICAgICAgICAgc3RhcnRYOiBlLnBhZ2VYLFxuICAgICAgICAgICAgc3RhcnRZOiBlLnBhZ2VZXG4gICAgICAgIH0pO1xuICAgICAgICB3aW5kb3cuYWRkRXZlbnRMaXN0ZW5lcihcIm1vdXNlbW92ZVwiLCB0aGlzLm9uTW91c2VNb3ZlKTtcbiAgICAgICAgd2luZG93LmFkZEV2ZW50TGlzdGVuZXIoXCJtb3VzZXVwXCIsIHRoaXMub25Nb3VzZVVwKTtcbiAgICAgICAgLy8gT2NjYXNpb25hbGx5LCBvbmx5IGEgZHJhZ0VuZCBldmVudCBpcyB0cmlnZ2VyZWQsIGJ1dCBubyBtb3VzZVVwLlxuICAgICAgICB3aW5kb3cuYWRkRXZlbnRMaXN0ZW5lcihcImRyYWdlbmRcIiwgdGhpcy5vbkRyYWdFbmQpO1xuICAgIH0sXG4gICAgb25EcmFnRW5kOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuZ2V0RE9NTm9kZSgpLnN0eWxlLnRyYW5zZm9ybSA9IFwiXCI7XG4gICAgICAgIHdpbmRvdy5yZW1vdmVFdmVudExpc3RlbmVyKFwiZHJhZ2VuZFwiLCB0aGlzLm9uRHJhZ0VuZCk7XG4gICAgICAgIHdpbmRvdy5yZW1vdmVFdmVudExpc3RlbmVyKFwibW91c2V1cFwiLCB0aGlzLm9uTW91c2VVcCk7XG4gICAgICAgIHdpbmRvdy5yZW1vdmVFdmVudExpc3RlbmVyKFwibW91c2Vtb3ZlXCIsIHRoaXMub25Nb3VzZU1vdmUpO1xuICAgIH0sXG4gICAgb25Nb3VzZVVwOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICB0aGlzLm9uRHJhZ0VuZCgpO1xuXG4gICAgICAgIHZhciBub2RlID0gdGhpcy5nZXRET01Ob2RlKCk7XG4gICAgICAgIHZhciBwcmV2ID0gbm9kZS5wcmV2aW91c0VsZW1lbnRTaWJsaW5nO1xuICAgICAgICB2YXIgbmV4dCA9IG5vZGUubmV4dEVsZW1lbnRTaWJsaW5nO1xuXG4gICAgICAgIHZhciBkWCA9IGUucGFnZVggLSB0aGlzLnN0YXRlLnN0YXJ0WDtcbiAgICAgICAgdmFyIGRZID0gZS5wYWdlWSAtIHRoaXMuc3RhdGUuc3RhcnRZO1xuICAgICAgICB2YXIgZmxleEJhc2lzO1xuICAgICAgICBpZiAodGhpcy5wcm9wcy5heGlzID09PSBcInhcIikge1xuICAgICAgICAgICAgZmxleEJhc2lzID0gcHJldi5vZmZzZXRXaWR0aCArIGRYO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgZmxleEJhc2lzID0gcHJldi5vZmZzZXRIZWlnaHQgKyBkWTtcbiAgICAgICAgfVxuXG4gICAgICAgIHByZXYuc3R5bGUuZmxleCA9IFwiMCAwIFwiICsgTWF0aC5tYXgoMCwgZmxleEJhc2lzKSArIFwicHhcIjtcbiAgICAgICAgbmV4dC5zdHlsZS5mbGV4ID0gXCIxIDEgYXV0b1wiO1xuXG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe1xuICAgICAgICAgICAgYXBwbGllZDogdHJ1ZVxuICAgICAgICB9KTtcbiAgICAgICAgdGhpcy5vblJlc2l6ZSgpO1xuICAgIH0sXG4gICAgb25Nb3VzZU1vdmU6IGZ1bmN0aW9uIChlKSB7XG4gICAgICAgIHZhciBkWCA9IDAsIGRZID0gMDtcbiAgICAgICAgaWYgKHRoaXMucHJvcHMuYXhpcyA9PT0gXCJ4XCIpIHtcbiAgICAgICAgICAgIGRYID0gZS5wYWdlWCAtIHRoaXMuc3RhdGUuc3RhcnRYO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgZFkgPSBlLnBhZ2VZIC0gdGhpcy5zdGF0ZS5zdGFydFk7XG4gICAgICAgIH1cbiAgICAgICAgdGhpcy5nZXRET01Ob2RlKCkuc3R5bGUudHJhbnNmb3JtID0gXCJ0cmFuc2xhdGUoXCIgKyBkWCArIFwicHgsXCIgKyBkWSArIFwicHgpXCI7XG4gICAgfSxcbiAgICBvblJlc2l6ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICAvLyBUcmlnZ2VyIGEgZ2xvYmFsIHJlc2l6ZSBldmVudC4gVGhpcyBub3RpZmllcyBjb21wb25lbnRzIHRoYXQgZW1wbG95IHZpcnR1YWwgc2Nyb2xsaW5nXG4gICAgICAgIC8vIHRoYXQgdGhlaXIgdmlld3BvcnQgbWF5IGhhdmUgY2hhbmdlZC5cbiAgICAgICAgd2luZG93LnNldFRpbWVvdXQoZnVuY3Rpb24gKCkge1xuICAgICAgICAgICAgd2luZG93LmRpc3BhdGNoRXZlbnQobmV3IEN1c3RvbUV2ZW50KFwicmVzaXplXCIpKTtcbiAgICAgICAgfSwgMSk7XG4gICAgfSxcbiAgICByZXNldDogZnVuY3Rpb24gKHdpbGxVbm1vdW50KSB7XG4gICAgICAgIGlmICghdGhpcy5zdGF0ZS5hcHBsaWVkKSB7XG4gICAgICAgICAgICByZXR1cm47XG4gICAgICAgIH1cbiAgICAgICAgdmFyIG5vZGUgPSB0aGlzLmdldERPTU5vZGUoKTtcbiAgICAgICAgdmFyIHByZXYgPSBub2RlLnByZXZpb3VzRWxlbWVudFNpYmxpbmc7XG4gICAgICAgIHZhciBuZXh0ID0gbm9kZS5uZXh0RWxlbWVudFNpYmxpbmc7XG5cbiAgICAgICAgcHJldi5zdHlsZS5mbGV4ID0gXCJcIjtcbiAgICAgICAgbmV4dC5zdHlsZS5mbGV4ID0gXCJcIjtcblxuICAgICAgICBpZiAoIXdpbGxVbm1vdW50KSB7XG4gICAgICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgICAgICBhcHBsaWVkOiBmYWxzZVxuICAgICAgICAgICAgfSk7XG4gICAgICAgIH1cbiAgICAgICAgdGhpcy5vblJlc2l6ZSgpO1xuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbFVubW91bnQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5yZXNldCh0cnVlKTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgY2xhc3NOYW1lID0gXCJzcGxpdHRlclwiO1xuICAgICAgICBpZiAodGhpcy5wcm9wcy5heGlzID09PSBcInhcIikge1xuICAgICAgICAgICAgY2xhc3NOYW1lICs9IFwiIHNwbGl0dGVyLXhcIjtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcIiBzcGxpdHRlci15XCI7XG4gICAgICAgIH1cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogY2xhc3NOYW1lfSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7b25Nb3VzZURvd246IHRoaXMub25Nb3VzZURvd24sIGRyYWdnYWJsZTogXCJ0cnVlXCJ9KVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG5tb2R1bGUuZXhwb3J0cyA9IHtcbiAgICBTdGF0ZTogU3RhdGUsXG4gICAgTmF2aWdhdGlvbjogTmF2aWdhdGlvbixcbiAgICBTdGlja3lIZWFkTWl4aW46IFN0aWNreUhlYWRNaXhpbixcbiAgICBBdXRvU2Nyb2xsTWl4aW46IEF1dG9TY3JvbGxNaXhpbixcbiAgICBTcGxpdHRlcjogU3BsaXR0ZXJcbn0iLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XG5cbnZhciBWaXJ0dWFsU2Nyb2xsTWl4aW4gPSB7XG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHJldHVybiB7XG4gICAgICAgICAgICBzdGFydDogMCxcbiAgICAgICAgICAgIHN0b3A6IDBcbiAgICAgICAgfTtcbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxNb3VudDogZnVuY3Rpb24gKCkge1xuICAgICAgICBpZiAoIXRoaXMucHJvcHMucm93SGVpZ2h0KSB7XG4gICAgICAgICAgICBjb25zb2xlLndhcm4oXCJWaXJ0dWFsU2Nyb2xsTWl4aW46IE5vIHJvd0hlaWdodCBzcGVjaWZpZWRcIiwgdGhpcyk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGdldFBsYWNlaG9sZGVyVG9wOiBmdW5jdGlvbiAodG90YWwpIHtcbiAgICAgICAgdmFyIFRhZyA9IHRoaXMucHJvcHMucGxhY2Vob2xkZXJUYWdOYW1lIHx8IFwidHJcIjtcbiAgICAgICAgLy8gV2hlbiBhIGxhcmdlIHRydW5rIG9mIGVsZW1lbnRzIGlzIHJlbW92ZWQgZnJvbSB0aGUgYnV0dG9uLCBzdGFydCBtYXkgYmUgZmFyIG9mZiB0aGUgdmlld3BvcnQuXG4gICAgICAgIC8vIFRvIG1ha2UgdGhpcyBpc3N1ZSBsZXNzIHNldmVyZSwgbGltaXQgdGhlIHRvcCBwbGFjZWhvbGRlciB0byB0aGUgdG90YWwgbnVtYmVyIG9mIHJvd3MuXG4gICAgICAgIHZhciBzdHlsZSA9IHtcbiAgICAgICAgICAgIGhlaWdodDogTWF0aC5taW4odGhpcy5zdGF0ZS5zdGFydCwgdG90YWwpICogdGhpcy5wcm9wcy5yb3dIZWlnaHRcbiAgICAgICAgfTtcbiAgICAgICAgdmFyIHNwYWNlciA9IFJlYWN0LmNyZWF0ZUVsZW1lbnQoVGFnLCB7a2V5OiBcInBsYWNlaG9sZGVyLXRvcFwiLCBzdHlsZTogc3R5bGV9KTtcblxuICAgICAgICBpZiAodGhpcy5zdGF0ZS5zdGFydCAlIDIgPT09IDEpIHtcbiAgICAgICAgICAgIC8vIGZpeCBldmVuL29kZCByb3dzXG4gICAgICAgICAgICByZXR1cm4gW3NwYWNlciwgUmVhY3QuY3JlYXRlRWxlbWVudChUYWcsIHtrZXk6IFwicGxhY2Vob2xkZXItdG9wLTJcIn0pXTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHJldHVybiBzcGFjZXI7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGdldFBsYWNlaG9sZGVyQm90dG9tOiBmdW5jdGlvbiAodG90YWwpIHtcbiAgICAgICAgdmFyIFRhZyA9IHRoaXMucHJvcHMucGxhY2Vob2xkZXJUYWdOYW1lIHx8IFwidHJcIjtcbiAgICAgICAgdmFyIHN0eWxlID0ge1xuICAgICAgICAgICAgaGVpZ2h0OiBNYXRoLm1heCgwLCB0b3RhbCAtIHRoaXMuc3RhdGUuc3RvcCkgKiB0aGlzLnByb3BzLnJvd0hlaWdodFxuICAgICAgICB9O1xuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChUYWcsIHtrZXk6IFwicGxhY2Vob2xkZXItYm90dG9tXCIsIHN0eWxlOiBzdHlsZX0pO1xuICAgIH0sXG4gICAgY29tcG9uZW50RGlkTW91bnQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5vblNjcm9sbCgpO1xuICAgICAgICB3aW5kb3cuYWRkRXZlbnRMaXN0ZW5lcigncmVzaXplJywgdGhpcy5vblNjcm9sbCk7XG4gICAgfSxcbiAgICBjb21wb25lbnRXaWxsVW5tb3VudDogZnVuY3Rpb24oKXtcbiAgICAgICAgd2luZG93LnJlbW92ZUV2ZW50TGlzdGVuZXIoJ3Jlc2l6ZScsIHRoaXMub25TY3JvbGwpO1xuICAgIH0sXG4gICAgb25TY3JvbGw6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIHZpZXdwb3J0ID0gdGhpcy5nZXRET01Ob2RlKCk7XG4gICAgICAgIHZhciB0b3AgPSB2aWV3cG9ydC5zY3JvbGxUb3A7XG4gICAgICAgIHZhciBoZWlnaHQgPSB2aWV3cG9ydC5vZmZzZXRIZWlnaHQ7XG4gICAgICAgIHZhciBzdGFydCA9IE1hdGguZmxvb3IodG9wIC8gdGhpcy5wcm9wcy5yb3dIZWlnaHQpO1xuICAgICAgICB2YXIgc3RvcCA9IHN0YXJ0ICsgTWF0aC5jZWlsKGhlaWdodCAvICh0aGlzLnByb3BzLnJvd0hlaWdodE1pbiB8fCB0aGlzLnByb3BzLnJvd0hlaWdodCkpO1xuXG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe1xuICAgICAgICAgICAgc3RhcnQ6IHN0YXJ0LFxuICAgICAgICAgICAgc3RvcDogc3RvcFxuICAgICAgICB9KTtcbiAgICB9LFxuICAgIHJlbmRlclJvd3M6IGZ1bmN0aW9uIChlbGVtcykge1xuICAgICAgICB2YXIgcm93cyA9IFtdO1xuICAgICAgICB2YXIgbWF4ID0gTWF0aC5taW4oZWxlbXMubGVuZ3RoLCB0aGlzLnN0YXRlLnN0b3ApO1xuXG4gICAgICAgIGZvciAodmFyIGkgPSB0aGlzLnN0YXRlLnN0YXJ0OyBpIDwgbWF4OyBpKyspIHtcbiAgICAgICAgICAgIHZhciBlbGVtID0gZWxlbXNbaV07XG4gICAgICAgICAgICByb3dzLnB1c2godGhpcy5yZW5kZXJSb3coZWxlbSkpO1xuICAgICAgICB9XG4gICAgICAgIHJldHVybiByb3dzO1xuICAgIH0sXG4gICAgc2Nyb2xsUm93SW50b1ZpZXc6IGZ1bmN0aW9uIChpbmRleCwgaGVhZF9oZWlnaHQpIHtcblxuICAgICAgICB2YXIgcm93X3RvcCA9IChpbmRleCAqIHRoaXMucHJvcHMucm93SGVpZ2h0KSArIGhlYWRfaGVpZ2h0O1xuICAgICAgICB2YXIgcm93X2JvdHRvbSA9IHJvd190b3AgKyB0aGlzLnByb3BzLnJvd0hlaWdodDtcblxuICAgICAgICB2YXIgdmlld3BvcnQgPSB0aGlzLmdldERPTU5vZGUoKTtcbiAgICAgICAgdmFyIHZpZXdwb3J0X3RvcCA9IHZpZXdwb3J0LnNjcm9sbFRvcDtcbiAgICAgICAgdmFyIHZpZXdwb3J0X2JvdHRvbSA9IHZpZXdwb3J0X3RvcCArIHZpZXdwb3J0Lm9mZnNldEhlaWdodDtcblxuICAgICAgICAvLyBBY2NvdW50IGZvciBwaW5uZWQgdGhlYWRcbiAgICAgICAgaWYgKHJvd190b3AgLSBoZWFkX2hlaWdodCA8IHZpZXdwb3J0X3RvcCkge1xuICAgICAgICAgICAgdmlld3BvcnQuc2Nyb2xsVG9wID0gcm93X3RvcCAtIGhlYWRfaGVpZ2h0O1xuICAgICAgICB9IGVsc2UgaWYgKHJvd19ib3R0b20gPiB2aWV3cG9ydF9ib3R0b20pIHtcbiAgICAgICAgICAgIHZpZXdwb3J0LnNjcm9sbFRvcCA9IHJvd19ib3R0b20gLSB2aWV3cG9ydC5vZmZzZXRIZWlnaHQ7XG4gICAgICAgIH1cbiAgICB9LFxufTtcblxubW9kdWxlLmV4cG9ydHMgID0gVmlydHVhbFNjcm9sbE1peGluOyIsIlxudmFyIGFjdGlvbnMgPSByZXF1aXJlKFwiLi9hY3Rpb25zLmpzXCIpO1xuXG5mdW5jdGlvbiBDb25uZWN0aW9uKHVybCkge1xuICAgIGlmICh1cmxbMF0gPT09IFwiL1wiKSB7XG4gICAgICAgIHVybCA9IGxvY2F0aW9uLm9yaWdpbi5yZXBsYWNlKFwiaHR0cFwiLCBcIndzXCIpICsgdXJsO1xuICAgIH1cblxuICAgIHZhciB3cyA9IG5ldyBXZWJTb2NrZXQodXJsKTtcbiAgICB3cy5vbm9wZW4gPSBmdW5jdGlvbiAoKSB7XG4gICAgICAgIGFjdGlvbnMuQ29ubmVjdGlvbkFjdGlvbnMub3BlbigpO1xuICAgIH07XG4gICAgd3Mub25tZXNzYWdlID0gZnVuY3Rpb24gKG1lc3NhZ2UpIHtcbiAgICAgICAgdmFyIG0gPSBKU09OLnBhcnNlKG1lc3NhZ2UuZGF0YSk7XG4gICAgICAgIEFwcERpc3BhdGNoZXIuZGlzcGF0Y2hTZXJ2ZXJBY3Rpb24obSk7XG4gICAgfTtcbiAgICB3cy5vbmVycm9yID0gZnVuY3Rpb24gKCkge1xuICAgICAgICBhY3Rpb25zLkNvbm5lY3Rpb25BY3Rpb25zLmVycm9yKCk7XG4gICAgICAgIEV2ZW50TG9nQWN0aW9ucy5hZGRfZXZlbnQoXCJXZWJTb2NrZXQgY29ubmVjdGlvbiBlcnJvci5cIik7XG4gICAgfTtcbiAgICB3cy5vbmNsb3NlID0gZnVuY3Rpb24gKCkge1xuICAgICAgICBhY3Rpb25zLkNvbm5lY3Rpb25BY3Rpb25zLmNsb3NlKCk7XG4gICAgICAgIEV2ZW50TG9nQWN0aW9ucy5hZGRfZXZlbnQoXCJXZWJTb2NrZXQgY29ubmVjdGlvbiBjbG9zZWQuXCIpO1xuICAgIH07XG4gICAgcmV0dXJuIHdzO1xufVxuXG5tb2R1bGUuZXhwb3J0cyA9IENvbm5lY3Rpb247IiwiY29uc3QgUGF5bG9hZFNvdXJjZXMgPSB7XG4gICAgVklFVzogXCJ2aWV3XCIsXG4gICAgU0VSVkVSOiBcInNlcnZlclwiXG59O1xuXG5cbmZ1bmN0aW9uIERpc3BhdGNoZXIoKSB7XG4gICAgdGhpcy5jYWxsYmFja3MgPSBbXTtcbn1cbkRpc3BhdGNoZXIucHJvdG90eXBlLnJlZ2lzdGVyID0gZnVuY3Rpb24gKGNhbGxiYWNrKSB7XG4gICAgdGhpcy5jYWxsYmFja3MucHVzaChjYWxsYmFjayk7XG59O1xuRGlzcGF0Y2hlci5wcm90b3R5cGUudW5yZWdpc3RlciA9IGZ1bmN0aW9uIChjYWxsYmFjaykge1xuICAgIHZhciBpbmRleCA9IHRoaXMuY2FsbGJhY2tzLmluZGV4T2YoY2FsbGJhY2spO1xuICAgIGlmIChpbmRleCA+PSAwKSB7XG4gICAgICAgIHRoaXMuY2FsbGJhY2tzLnNwbGljZShpbmRleCwgMSk7XG4gICAgfVxufTtcbkRpc3BhdGNoZXIucHJvdG90eXBlLmRpc3BhdGNoID0gZnVuY3Rpb24gKHBheWxvYWQpIHtcbiAgICBjb25zb2xlLmRlYnVnKFwiZGlzcGF0Y2hcIiwgcGF5bG9hZCk7XG4gICAgZm9yICh2YXIgaSA9IDA7IGkgPCB0aGlzLmNhbGxiYWNrcy5sZW5ndGg7IGkrKykge1xuICAgICAgICB0aGlzLmNhbGxiYWNrc1tpXShwYXlsb2FkKTtcbiAgICB9XG59O1xuXG5cbkFwcERpc3BhdGNoZXIgPSBuZXcgRGlzcGF0Y2hlcigpO1xuQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFZpZXdBY3Rpb24gPSBmdW5jdGlvbiAoYWN0aW9uKSB7XG4gICAgYWN0aW9uLnNvdXJjZSA9IFBheWxvYWRTb3VyY2VzLlZJRVc7XG4gICAgdGhpcy5kaXNwYXRjaChhY3Rpb24pO1xufTtcbkFwcERpc3BhdGNoZXIuZGlzcGF0Y2hTZXJ2ZXJBY3Rpb24gPSBmdW5jdGlvbiAoYWN0aW9uKSB7XG4gICAgYWN0aW9uLnNvdXJjZSA9IFBheWxvYWRTb3VyY2VzLlNFUlZFUjtcbiAgICB0aGlzLmRpc3BhdGNoKGFjdGlvbik7XG59O1xuXG5tb2R1bGUuZXhwb3J0cyA9IHtcbiAgICBBcHBEaXNwYXRjaGVyOiBBcHBEaXNwYXRjaGVyXG59OyIsIi8qIGpzaGludCBpZ25vcmU6c3RhcnQgKi9cbkZpbHQgPSAoZnVuY3Rpb24oKSB7XG4gIC8qXG4gICAqIEdlbmVyYXRlZCBieSBQRUcuanMgMC44LjAuXG4gICAqXG4gICAqIGh0dHA6Ly9wZWdqcy5tYWpkYS5jei9cbiAgICovXG5cbiAgZnVuY3Rpb24gcGVnJHN1YmNsYXNzKGNoaWxkLCBwYXJlbnQpIHtcbiAgICBmdW5jdGlvbiBjdG9yKCkgeyB0aGlzLmNvbnN0cnVjdG9yID0gY2hpbGQ7IH1cbiAgICBjdG9yLnByb3RvdHlwZSA9IHBhcmVudC5wcm90b3R5cGU7XG4gICAgY2hpbGQucHJvdG90eXBlID0gbmV3IGN0b3IoKTtcbiAgfVxuXG4gIGZ1bmN0aW9uIFN5bnRheEVycm9yKG1lc3NhZ2UsIGV4cGVjdGVkLCBmb3VuZCwgb2Zmc2V0LCBsaW5lLCBjb2x1bW4pIHtcbiAgICB0aGlzLm1lc3NhZ2UgID0gbWVzc2FnZTtcbiAgICB0aGlzLmV4cGVjdGVkID0gZXhwZWN0ZWQ7XG4gICAgdGhpcy5mb3VuZCAgICA9IGZvdW5kO1xuICAgIHRoaXMub2Zmc2V0ICAgPSBvZmZzZXQ7XG4gICAgdGhpcy5saW5lICAgICA9IGxpbmU7XG4gICAgdGhpcy5jb2x1bW4gICA9IGNvbHVtbjtcblxuICAgIHRoaXMubmFtZSAgICAgPSBcIlN5bnRheEVycm9yXCI7XG4gIH1cblxuICBwZWckc3ViY2xhc3MoU3ludGF4RXJyb3IsIEVycm9yKTtcblxuICBmdW5jdGlvbiBwYXJzZShpbnB1dCkge1xuICAgIHZhciBvcHRpb25zID0gYXJndW1lbnRzLmxlbmd0aCA+IDEgPyBhcmd1bWVudHNbMV0gOiB7fSxcblxuICAgICAgICBwZWckRkFJTEVEID0ge30sXG5cbiAgICAgICAgcGVnJHN0YXJ0UnVsZUZ1bmN0aW9ucyA9IHsgc3RhcnQ6IHBlZyRwYXJzZXN0YXJ0IH0sXG4gICAgICAgIHBlZyRzdGFydFJ1bGVGdW5jdGlvbiAgPSBwZWckcGFyc2VzdGFydCxcblxuICAgICAgICBwZWckYzAgPSB7IHR5cGU6IFwib3RoZXJcIiwgZGVzY3JpcHRpb246IFwiZmlsdGVyIGV4cHJlc3Npb25cIiB9LFxuICAgICAgICBwZWckYzEgPSBwZWckRkFJTEVELFxuICAgICAgICBwZWckYzIgPSBmdW5jdGlvbihvckV4cHIpIHsgcmV0dXJuIG9yRXhwcjsgfSxcbiAgICAgICAgcGVnJGMzID0gW10sXG4gICAgICAgIHBlZyRjNCA9IGZ1bmN0aW9uKCkge3JldHVybiB0cnVlRmlsdGVyOyB9LFxuICAgICAgICBwZWckYzUgPSB7IHR5cGU6IFwib3RoZXJcIiwgZGVzY3JpcHRpb246IFwid2hpdGVzcGFjZVwiIH0sXG4gICAgICAgIHBlZyRjNiA9IC9eWyBcXHRcXG5cXHJdLyxcbiAgICAgICAgcGVnJGM3ID0geyB0eXBlOiBcImNsYXNzXCIsIHZhbHVlOiBcIlsgXFxcXHRcXFxcblxcXFxyXVwiLCBkZXNjcmlwdGlvbjogXCJbIFxcXFx0XFxcXG5cXFxccl1cIiB9LFxuICAgICAgICBwZWckYzggPSB7IHR5cGU6IFwib3RoZXJcIiwgZGVzY3JpcHRpb246IFwiY29udHJvbCBjaGFyYWN0ZXJcIiB9LFxuICAgICAgICBwZWckYzkgPSAvXlt8JiEoKX5cIl0vLFxuICAgICAgICBwZWckYzEwID0geyB0eXBlOiBcImNsYXNzXCIsIHZhbHVlOiBcIlt8JiEoKX5cXFwiXVwiLCBkZXNjcmlwdGlvbjogXCJbfCYhKCl+XFxcIl1cIiB9LFxuICAgICAgICBwZWckYzExID0geyB0eXBlOiBcIm90aGVyXCIsIGRlc2NyaXB0aW9uOiBcIm9wdGlvbmFsIHdoaXRlc3BhY2VcIiB9LFxuICAgICAgICBwZWckYzEyID0gXCJ8XCIsXG4gICAgICAgIHBlZyRjMTMgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ8XCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ8XFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMTQgPSBmdW5jdGlvbihmaXJzdCwgc2Vjb25kKSB7IHJldHVybiBvcihmaXJzdCwgc2Vjb25kKTsgfSxcbiAgICAgICAgcGVnJGMxNSA9IFwiJlwiLFxuICAgICAgICBwZWckYzE2ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiJlwiLCBkZXNjcmlwdGlvbjogXCJcXFwiJlxcXCJcIiB9LFxuICAgICAgICBwZWckYzE3ID0gZnVuY3Rpb24oZmlyc3QsIHNlY29uZCkgeyByZXR1cm4gYW5kKGZpcnN0LCBzZWNvbmQpOyB9LFxuICAgICAgICBwZWckYzE4ID0gXCIhXCIsXG4gICAgICAgIHBlZyRjMTkgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCIhXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCIhXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMjAgPSBmdW5jdGlvbihleHByKSB7IHJldHVybiBub3QoZXhwcik7IH0sXG4gICAgICAgIHBlZyRjMjEgPSBcIihcIixcbiAgICAgICAgcGVnJGMyMiA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIihcIiwgZGVzY3JpcHRpb246IFwiXFxcIihcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMyMyA9IFwiKVwiLFxuICAgICAgICBwZWckYzI0ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiKVwiLCBkZXNjcmlwdGlvbjogXCJcXFwiKVxcXCJcIiB9LFxuICAgICAgICBwZWckYzI1ID0gZnVuY3Rpb24oZXhwcikgeyByZXR1cm4gYmluZGluZyhleHByKTsgfSxcbiAgICAgICAgcGVnJGMyNiA9IFwifmFcIixcbiAgICAgICAgcGVnJGMyNyA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5hXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+YVxcXCJcIiB9LFxuICAgICAgICBwZWckYzI4ID0gZnVuY3Rpb24oKSB7IHJldHVybiBhc3NldEZpbHRlcjsgfSxcbiAgICAgICAgcGVnJGMyOSA9IFwifmVcIixcbiAgICAgICAgcGVnJGMzMCA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5lXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+ZVxcXCJcIiB9LFxuICAgICAgICBwZWckYzMxID0gZnVuY3Rpb24oKSB7IHJldHVybiBlcnJvckZpbHRlcjsgfSxcbiAgICAgICAgcGVnJGMzMiA9IFwifnFcIixcbiAgICAgICAgcGVnJGMzMyA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5xXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+cVxcXCJcIiB9LFxuICAgICAgICBwZWckYzM0ID0gZnVuY3Rpb24oKSB7IHJldHVybiBub1Jlc3BvbnNlRmlsdGVyOyB9LFxuICAgICAgICBwZWckYzM1ID0gXCJ+c1wiLFxuICAgICAgICBwZWckYzM2ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifnNcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5zXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMzcgPSBmdW5jdGlvbigpIHsgcmV0dXJuIHJlc3BvbnNlRmlsdGVyOyB9LFxuICAgICAgICBwZWckYzM4ID0gXCJ0cnVlXCIsXG4gICAgICAgIHBlZyRjMzkgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ0cnVlXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ0cnVlXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNDAgPSBmdW5jdGlvbigpIHsgcmV0dXJuIHRydWVGaWx0ZXI7IH0sXG4gICAgICAgIHBlZyRjNDEgPSBcImZhbHNlXCIsXG4gICAgICAgIHBlZyRjNDIgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJmYWxzZVwiLCBkZXNjcmlwdGlvbjogXCJcXFwiZmFsc2VcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM0MyA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gZmFsc2VGaWx0ZXI7IH0sXG4gICAgICAgIHBlZyRjNDQgPSBcIn5jXCIsXG4gICAgICAgIHBlZyRjNDUgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+Y1wiLCBkZXNjcmlwdGlvbjogXCJcXFwifmNcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM0NiA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIHJlc3BvbnNlQ29kZShzKTsgfSxcbiAgICAgICAgcGVnJGM0NyA9IFwifmRcIixcbiAgICAgICAgcGVnJGM0OCA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5kXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+ZFxcXCJcIiB9LFxuICAgICAgICBwZWckYzQ5ID0gZnVuY3Rpb24ocykgeyByZXR1cm4gZG9tYWluKHMpOyB9LFxuICAgICAgICBwZWckYzUwID0gXCJ+aFwiLFxuICAgICAgICBwZWckYzUxID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifmhcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5oXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNTIgPSBmdW5jdGlvbihzKSB7IHJldHVybiBoZWFkZXIocyk7IH0sXG4gICAgICAgIHBlZyRjNTMgPSBcIn5ocVwiLFxuICAgICAgICBwZWckYzU0ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifmhxXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+aHFcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM1NSA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIHJlcXVlc3RIZWFkZXIocyk7IH0sXG4gICAgICAgIHBlZyRjNTYgPSBcIn5oc1wiLFxuICAgICAgICBwZWckYzU3ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifmhzXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+aHNcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM1OCA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIHJlc3BvbnNlSGVhZGVyKHMpOyB9LFxuICAgICAgICBwZWckYzU5ID0gXCJ+bVwiLFxuICAgICAgICBwZWckYzYwID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifm1cIiwgZGVzY3JpcHRpb246IFwiXFxcIn5tXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNjEgPSBmdW5jdGlvbihzKSB7IHJldHVybiBtZXRob2Qocyk7IH0sXG4gICAgICAgIHBlZyRjNjIgPSBcIn50XCIsXG4gICAgICAgIHBlZyRjNjMgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+dFwiLCBkZXNjcmlwdGlvbjogXCJcXFwifnRcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM2NCA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIGNvbnRlbnRUeXBlKHMpOyB9LFxuICAgICAgICBwZWckYzY1ID0gXCJ+dHFcIixcbiAgICAgICAgcGVnJGM2NiA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn50cVwiLCBkZXNjcmlwdGlvbjogXCJcXFwifnRxXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNjcgPSBmdW5jdGlvbihzKSB7IHJldHVybiByZXF1ZXN0Q29udGVudFR5cGUocyk7IH0sXG4gICAgICAgIHBlZyRjNjggPSBcIn50c1wiLFxuICAgICAgICBwZWckYzY5ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifnRzXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+dHNcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM3MCA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIHJlc3BvbnNlQ29udGVudFR5cGUocyk7IH0sXG4gICAgICAgIHBlZyRjNzEgPSBcIn51XCIsXG4gICAgICAgIHBlZyRjNzIgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+dVwiLCBkZXNjcmlwdGlvbjogXCJcXFwifnVcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM3MyA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIHVybChzKTsgfSxcbiAgICAgICAgcGVnJGM3NCA9IHsgdHlwZTogXCJvdGhlclwiLCBkZXNjcmlwdGlvbjogXCJpbnRlZ2VyXCIgfSxcbiAgICAgICAgcGVnJGM3NSA9IG51bGwsXG4gICAgICAgIHBlZyRjNzYgPSAvXlsnXCJdLyxcbiAgICAgICAgcGVnJGM3NyA9IHsgdHlwZTogXCJjbGFzc1wiLCB2YWx1ZTogXCJbJ1xcXCJdXCIsIGRlc2NyaXB0aW9uOiBcIlsnXFxcIl1cIiB9LFxuICAgICAgICBwZWckYzc4ID0gL15bMC05XS8sXG4gICAgICAgIHBlZyRjNzkgPSB7IHR5cGU6IFwiY2xhc3NcIiwgdmFsdWU6IFwiWzAtOV1cIiwgZGVzY3JpcHRpb246IFwiWzAtOV1cIiB9LFxuICAgICAgICBwZWckYzgwID0gZnVuY3Rpb24oZGlnaXRzKSB7IHJldHVybiBwYXJzZUludChkaWdpdHMuam9pbihcIlwiKSwgMTApOyB9LFxuICAgICAgICBwZWckYzgxID0geyB0eXBlOiBcIm90aGVyXCIsIGRlc2NyaXB0aW9uOiBcInN0cmluZ1wiIH0sXG4gICAgICAgIHBlZyRjODIgPSBcIlxcXCJcIixcbiAgICAgICAgcGVnJGM4MyA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIlxcXCJcIiwgZGVzY3JpcHRpb246IFwiXFxcIlxcXFxcXFwiXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjODQgPSBmdW5jdGlvbihjaGFycykgeyByZXR1cm4gY2hhcnMuam9pbihcIlwiKTsgfSxcbiAgICAgICAgcGVnJGM4NSA9IFwiJ1wiLFxuICAgICAgICBwZWckYzg2ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiJ1wiLCBkZXNjcmlwdGlvbjogXCJcXFwiJ1xcXCJcIiB9LFxuICAgICAgICBwZWckYzg3ID0gdm9pZCAwLFxuICAgICAgICBwZWckYzg4ID0gL15bXCJcXFxcXS8sXG4gICAgICAgIHBlZyRjODkgPSB7IHR5cGU6IFwiY2xhc3NcIiwgdmFsdWU6IFwiW1xcXCJcXFxcXFxcXF1cIiwgZGVzY3JpcHRpb246IFwiW1xcXCJcXFxcXFxcXF1cIiB9LFxuICAgICAgICBwZWckYzkwID0geyB0eXBlOiBcImFueVwiLCBkZXNjcmlwdGlvbjogXCJhbnkgY2hhcmFjdGVyXCIgfSxcbiAgICAgICAgcGVnJGM5MSA9IGZ1bmN0aW9uKGNoYXIpIHsgcmV0dXJuIGNoYXI7IH0sXG4gICAgICAgIHBlZyRjOTIgPSBcIlxcXFxcIixcbiAgICAgICAgcGVnJGM5MyA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIlxcXFxcIiwgZGVzY3JpcHRpb246IFwiXFxcIlxcXFxcXFxcXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjOTQgPSAvXlsnXFxcXF0vLFxuICAgICAgICBwZWckYzk1ID0geyB0eXBlOiBcImNsYXNzXCIsIHZhbHVlOiBcIlsnXFxcXFxcXFxdXCIsIGRlc2NyaXB0aW9uOiBcIlsnXFxcXFxcXFxdXCIgfSxcbiAgICAgICAgcGVnJGM5NiA9IC9eWydcIlxcXFxdLyxcbiAgICAgICAgcGVnJGM5NyA9IHsgdHlwZTogXCJjbGFzc1wiLCB2YWx1ZTogXCJbJ1xcXCJcXFxcXFxcXF1cIiwgZGVzY3JpcHRpb246IFwiWydcXFwiXFxcXFxcXFxdXCIgfSxcbiAgICAgICAgcGVnJGM5OCA9IFwiblwiLFxuICAgICAgICBwZWckYzk5ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiblwiLCBkZXNjcmlwdGlvbjogXCJcXFwiblxcXCJcIiB9LFxuICAgICAgICBwZWckYzEwMCA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gXCJcXG5cIjsgfSxcbiAgICAgICAgcGVnJGMxMDEgPSBcInJcIixcbiAgICAgICAgcGVnJGMxMDIgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJyXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJyXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMTAzID0gZnVuY3Rpb24oKSB7IHJldHVybiBcIlxcclwiOyB9LFxuICAgICAgICBwZWckYzEwNCA9IFwidFwiLFxuICAgICAgICBwZWckYzEwNSA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcInRcIiwgZGVzY3JpcHRpb246IFwiXFxcInRcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMxMDYgPSBmdW5jdGlvbigpIHsgcmV0dXJuIFwiXFx0XCI7IH0sXG5cbiAgICAgICAgcGVnJGN1cnJQb3MgICAgICAgICAgPSAwLFxuICAgICAgICBwZWckcmVwb3J0ZWRQb3MgICAgICA9IDAsXG4gICAgICAgIHBlZyRjYWNoZWRQb3MgICAgICAgID0gMCxcbiAgICAgICAgcGVnJGNhY2hlZFBvc0RldGFpbHMgPSB7IGxpbmU6IDEsIGNvbHVtbjogMSwgc2VlbkNSOiBmYWxzZSB9LFxuICAgICAgICBwZWckbWF4RmFpbFBvcyAgICAgICA9IDAsXG4gICAgICAgIHBlZyRtYXhGYWlsRXhwZWN0ZWQgID0gW10sXG4gICAgICAgIHBlZyRzaWxlbnRGYWlscyAgICAgID0gMCxcblxuICAgICAgICBwZWckcmVzdWx0O1xuXG4gICAgaWYgKFwic3RhcnRSdWxlXCIgaW4gb3B0aW9ucykge1xuICAgICAgaWYgKCEob3B0aW9ucy5zdGFydFJ1bGUgaW4gcGVnJHN0YXJ0UnVsZUZ1bmN0aW9ucykpIHtcbiAgICAgICAgdGhyb3cgbmV3IEVycm9yKFwiQ2FuJ3Qgc3RhcnQgcGFyc2luZyBmcm9tIHJ1bGUgXFxcIlwiICsgb3B0aW9ucy5zdGFydFJ1bGUgKyBcIlxcXCIuXCIpO1xuICAgICAgfVxuXG4gICAgICBwZWckc3RhcnRSdWxlRnVuY3Rpb24gPSBwZWckc3RhcnRSdWxlRnVuY3Rpb25zW29wdGlvbnMuc3RhcnRSdWxlXTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiB0ZXh0KCkge1xuICAgICAgcmV0dXJuIGlucHV0LnN1YnN0cmluZyhwZWckcmVwb3J0ZWRQb3MsIHBlZyRjdXJyUG9zKTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBvZmZzZXQoKSB7XG4gICAgICByZXR1cm4gcGVnJHJlcG9ydGVkUG9zO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIGxpbmUoKSB7XG4gICAgICByZXR1cm4gcGVnJGNvbXB1dGVQb3NEZXRhaWxzKHBlZyRyZXBvcnRlZFBvcykubGluZTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBjb2x1bW4oKSB7XG4gICAgICByZXR1cm4gcGVnJGNvbXB1dGVQb3NEZXRhaWxzKHBlZyRyZXBvcnRlZFBvcykuY29sdW1uO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIGV4cGVjdGVkKGRlc2NyaXB0aW9uKSB7XG4gICAgICB0aHJvdyBwZWckYnVpbGRFeGNlcHRpb24oXG4gICAgICAgIG51bGwsXG4gICAgICAgIFt7IHR5cGU6IFwib3RoZXJcIiwgZGVzY3JpcHRpb246IGRlc2NyaXB0aW9uIH1dLFxuICAgICAgICBwZWckcmVwb3J0ZWRQb3NcbiAgICAgICk7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gZXJyb3IobWVzc2FnZSkge1xuICAgICAgdGhyb3cgcGVnJGJ1aWxkRXhjZXB0aW9uKG1lc3NhZ2UsIG51bGwsIHBlZyRyZXBvcnRlZFBvcyk7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJGNvbXB1dGVQb3NEZXRhaWxzKHBvcykge1xuICAgICAgZnVuY3Rpb24gYWR2YW5jZShkZXRhaWxzLCBzdGFydFBvcywgZW5kUG9zKSB7XG4gICAgICAgIHZhciBwLCBjaDtcblxuICAgICAgICBmb3IgKHAgPSBzdGFydFBvczsgcCA8IGVuZFBvczsgcCsrKSB7XG4gICAgICAgICAgY2ggPSBpbnB1dC5jaGFyQXQocCk7XG4gICAgICAgICAgaWYgKGNoID09PSBcIlxcblwiKSB7XG4gICAgICAgICAgICBpZiAoIWRldGFpbHMuc2VlbkNSKSB7IGRldGFpbHMubGluZSsrOyB9XG4gICAgICAgICAgICBkZXRhaWxzLmNvbHVtbiA9IDE7XG4gICAgICAgICAgICBkZXRhaWxzLnNlZW5DUiA9IGZhbHNlO1xuICAgICAgICAgIH0gZWxzZSBpZiAoY2ggPT09IFwiXFxyXCIgfHwgY2ggPT09IFwiXFx1MjAyOFwiIHx8IGNoID09PSBcIlxcdTIwMjlcIikge1xuICAgICAgICAgICAgZGV0YWlscy5saW5lKys7XG4gICAgICAgICAgICBkZXRhaWxzLmNvbHVtbiA9IDE7XG4gICAgICAgICAgICBkZXRhaWxzLnNlZW5DUiA9IHRydWU7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGRldGFpbHMuY29sdW1uKys7XG4gICAgICAgICAgICBkZXRhaWxzLnNlZW5DUiA9IGZhbHNlO1xuICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICBpZiAocGVnJGNhY2hlZFBvcyAhPT0gcG9zKSB7XG4gICAgICAgIGlmIChwZWckY2FjaGVkUG9zID4gcG9zKSB7XG4gICAgICAgICAgcGVnJGNhY2hlZFBvcyA9IDA7XG4gICAgICAgICAgcGVnJGNhY2hlZFBvc0RldGFpbHMgPSB7IGxpbmU6IDEsIGNvbHVtbjogMSwgc2VlbkNSOiBmYWxzZSB9O1xuICAgICAgICB9XG4gICAgICAgIGFkdmFuY2UocGVnJGNhY2hlZFBvc0RldGFpbHMsIHBlZyRjYWNoZWRQb3MsIHBvcyk7XG4gICAgICAgIHBlZyRjYWNoZWRQb3MgPSBwb3M7XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBwZWckY2FjaGVkUG9zRGV0YWlscztcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckZmFpbChleHBlY3RlZCkge1xuICAgICAgaWYgKHBlZyRjdXJyUG9zIDwgcGVnJG1heEZhaWxQb3MpIHsgcmV0dXJuOyB9XG5cbiAgICAgIGlmIChwZWckY3VyclBvcyA+IHBlZyRtYXhGYWlsUG9zKSB7XG4gICAgICAgIHBlZyRtYXhGYWlsUG9zID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIHBlZyRtYXhGYWlsRXhwZWN0ZWQgPSBbXTtcbiAgICAgIH1cblxuICAgICAgcGVnJG1heEZhaWxFeHBlY3RlZC5wdXNoKGV4cGVjdGVkKTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckYnVpbGRFeGNlcHRpb24obWVzc2FnZSwgZXhwZWN0ZWQsIHBvcykge1xuICAgICAgZnVuY3Rpb24gY2xlYW51cEV4cGVjdGVkKGV4cGVjdGVkKSB7XG4gICAgICAgIHZhciBpID0gMTtcblxuICAgICAgICBleHBlY3RlZC5zb3J0KGZ1bmN0aW9uKGEsIGIpIHtcbiAgICAgICAgICBpZiAoYS5kZXNjcmlwdGlvbiA8IGIuZGVzY3JpcHRpb24pIHtcbiAgICAgICAgICAgIHJldHVybiAtMTtcbiAgICAgICAgICB9IGVsc2UgaWYgKGEuZGVzY3JpcHRpb24gPiBiLmRlc2NyaXB0aW9uKSB7XG4gICAgICAgICAgICByZXR1cm4gMTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcmV0dXJuIDA7XG4gICAgICAgICAgfVxuICAgICAgICB9KTtcblxuICAgICAgICB3aGlsZSAoaSA8IGV4cGVjdGVkLmxlbmd0aCkge1xuICAgICAgICAgIGlmIChleHBlY3RlZFtpIC0gMV0gPT09IGV4cGVjdGVkW2ldKSB7XG4gICAgICAgICAgICBleHBlY3RlZC5zcGxpY2UoaSwgMSk7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGkrKztcbiAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgIH1cblxuICAgICAgZnVuY3Rpb24gYnVpbGRNZXNzYWdlKGV4cGVjdGVkLCBmb3VuZCkge1xuICAgICAgICBmdW5jdGlvbiBzdHJpbmdFc2NhcGUocykge1xuICAgICAgICAgIGZ1bmN0aW9uIGhleChjaCkgeyByZXR1cm4gY2guY2hhckNvZGVBdCgwKS50b1N0cmluZygxNikudG9VcHBlckNhc2UoKTsgfVxuXG4gICAgICAgICAgcmV0dXJuIHNcbiAgICAgICAgICAgIC5yZXBsYWNlKC9cXFxcL2csICAgJ1xcXFxcXFxcJylcbiAgICAgICAgICAgIC5yZXBsYWNlKC9cIi9nLCAgICAnXFxcXFwiJylcbiAgICAgICAgICAgIC5yZXBsYWNlKC9cXHgwOC9nLCAnXFxcXGInKVxuICAgICAgICAgICAgLnJlcGxhY2UoL1xcdC9nLCAgICdcXFxcdCcpXG4gICAgICAgICAgICAucmVwbGFjZSgvXFxuL2csICAgJ1xcXFxuJylcbiAgICAgICAgICAgIC5yZXBsYWNlKC9cXGYvZywgICAnXFxcXGYnKVxuICAgICAgICAgICAgLnJlcGxhY2UoL1xcci9nLCAgICdcXFxccicpXG4gICAgICAgICAgICAucmVwbGFjZSgvW1xceDAwLVxceDA3XFx4MEJcXHgwRVxceDBGXS9nLCBmdW5jdGlvbihjaCkgeyByZXR1cm4gJ1xcXFx4MCcgKyBoZXgoY2gpOyB9KVxuICAgICAgICAgICAgLnJlcGxhY2UoL1tcXHgxMC1cXHgxRlxceDgwLVxceEZGXS9nLCAgICBmdW5jdGlvbihjaCkgeyByZXR1cm4gJ1xcXFx4JyAgKyBoZXgoY2gpOyB9KVxuICAgICAgICAgICAgLnJlcGxhY2UoL1tcXHUwMTgwLVxcdTBGRkZdL2csICAgICAgICAgZnVuY3Rpb24oY2gpIHsgcmV0dXJuICdcXFxcdTAnICsgaGV4KGNoKTsgfSlcbiAgICAgICAgICAgIC5yZXBsYWNlKC9bXFx1MTA4MC1cXHVGRkZGXS9nLCAgICAgICAgIGZ1bmN0aW9uKGNoKSB7IHJldHVybiAnXFxcXHUnICArIGhleChjaCk7IH0pO1xuICAgICAgICB9XG5cbiAgICAgICAgdmFyIGV4cGVjdGVkRGVzY3MgPSBuZXcgQXJyYXkoZXhwZWN0ZWQubGVuZ3RoKSxcbiAgICAgICAgICAgIGV4cGVjdGVkRGVzYywgZm91bmREZXNjLCBpO1xuXG4gICAgICAgIGZvciAoaSA9IDA7IGkgPCBleHBlY3RlZC5sZW5ndGg7IGkrKykge1xuICAgICAgICAgIGV4cGVjdGVkRGVzY3NbaV0gPSBleHBlY3RlZFtpXS5kZXNjcmlwdGlvbjtcbiAgICAgICAgfVxuXG4gICAgICAgIGV4cGVjdGVkRGVzYyA9IGV4cGVjdGVkLmxlbmd0aCA+IDFcbiAgICAgICAgICA/IGV4cGVjdGVkRGVzY3Muc2xpY2UoMCwgLTEpLmpvaW4oXCIsIFwiKVxuICAgICAgICAgICAgICArIFwiIG9yIFwiXG4gICAgICAgICAgICAgICsgZXhwZWN0ZWREZXNjc1tleHBlY3RlZC5sZW5ndGggLSAxXVxuICAgICAgICAgIDogZXhwZWN0ZWREZXNjc1swXTtcblxuICAgICAgICBmb3VuZERlc2MgPSBmb3VuZCA/IFwiXFxcIlwiICsgc3RyaW5nRXNjYXBlKGZvdW5kKSArIFwiXFxcIlwiIDogXCJlbmQgb2YgaW5wdXRcIjtcblxuICAgICAgICByZXR1cm4gXCJFeHBlY3RlZCBcIiArIGV4cGVjdGVkRGVzYyArIFwiIGJ1dCBcIiArIGZvdW5kRGVzYyArIFwiIGZvdW5kLlwiO1xuICAgICAgfVxuXG4gICAgICB2YXIgcG9zRGV0YWlscyA9IHBlZyRjb21wdXRlUG9zRGV0YWlscyhwb3MpLFxuICAgICAgICAgIGZvdW5kICAgICAgPSBwb3MgPCBpbnB1dC5sZW5ndGggPyBpbnB1dC5jaGFyQXQocG9zKSA6IG51bGw7XG5cbiAgICAgIGlmIChleHBlY3RlZCAhPT0gbnVsbCkge1xuICAgICAgICBjbGVhbnVwRXhwZWN0ZWQoZXhwZWN0ZWQpO1xuICAgICAgfVxuXG4gICAgICByZXR1cm4gbmV3IFN5bnRheEVycm9yKFxuICAgICAgICBtZXNzYWdlICE9PSBudWxsID8gbWVzc2FnZSA6IGJ1aWxkTWVzc2FnZShleHBlY3RlZCwgZm91bmQpLFxuICAgICAgICBleHBlY3RlZCxcbiAgICAgICAgZm91bmQsXG4gICAgICAgIHBvcyxcbiAgICAgICAgcG9zRGV0YWlscy5saW5lLFxuICAgICAgICBwb3NEZXRhaWxzLmNvbHVtblxuICAgICAgKTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VzdGFydCgpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyLCBzMztcblxuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgczEgPSBwZWckcGFyc2VfXygpO1xuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gcGVnJHBhcnNlT3JFeHByKCk7XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMzID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzIoczIpO1xuICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBzMSA9IFtdO1xuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICBzMSA9IHBlZyRjNCgpO1xuICAgICAgICB9XG4gICAgICAgIHMwID0gczE7XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMwKTsgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNld3MoKSB7XG4gICAgICB2YXIgczAsIHMxO1xuXG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIGlmIChwZWckYzYudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICBzMCA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMCA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM3KTsgfVxuICAgICAgfVxuICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNSk7IH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZWNjKCkge1xuICAgICAgdmFyIHMwLCBzMTtcblxuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBpZiAocGVnJGM5LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgczAgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczAgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMTApOyB9XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM4KTsgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlX18oKSB7XG4gICAgICB2YXIgczAsIHMxO1xuXG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIHMwID0gW107XG4gICAgICBzMSA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICB3aGlsZSAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAucHVzaChzMSk7XG4gICAgICAgIHMxID0gcGVnJHBhcnNld3MoKTtcbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzExKTsgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlT3JFeHByKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczIsIHMzLCBzNCwgczU7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBzMSA9IHBlZyRwYXJzZUFuZEV4cHIoKTtcbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMiA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMTI0KSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRjMTI7XG4gICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMTMpOyB9XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczQgPSBwZWckcGFyc2VfXygpO1xuICAgICAgICAgICAgaWYgKHM0ICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHM1ID0gcGVnJHBhcnNlT3JFeHByKCk7XG4gICAgICAgICAgICAgIGlmIChzNSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJGMxNChzMSwgczUpO1xuICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckcGFyc2VBbmRFeHByKCk7XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VBbmRFeHByKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczIsIHMzLCBzNCwgczU7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBzMSA9IHBlZyRwYXJzZU5vdEV4cHIoKTtcbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMiA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMzgpIHtcbiAgICAgICAgICAgIHMzID0gcGVnJGMxNTtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMzID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMxNik7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzNCA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICAgICAgICBpZiAoczQgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczUgPSBwZWckcGFyc2VBbmRFeHByKCk7XG4gICAgICAgICAgICAgIGlmIChzNSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJGMxNyhzMSwgczUpO1xuICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgczEgPSBwZWckcGFyc2VOb3RFeHByKCk7XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlQW5kRXhwcigpO1xuICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjMTcoczEsIHMzKTtcbiAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczAgPSBwZWckcGFyc2VOb3RFeHByKCk7XG4gICAgICAgIH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZU5vdEV4cHIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczM7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDMzKSB7XG4gICAgICAgIHMxID0gcGVnJGMxODtcbiAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzE5KTsgfVxuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczMgPSBwZWckcGFyc2VOb3RFeHByKCk7XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGMyMChzMyk7XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJHBhcnNlQmluZGluZ0V4cHIoKTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZUJpbmRpbmdFeHByKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczIsIHMzLCBzNCwgczU7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDQwKSB7XG4gICAgICAgIHMxID0gcGVnJGMyMTtcbiAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzIyKTsgfVxuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczMgPSBwZWckcGFyc2VPckV4cHIoKTtcbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHM0ID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgICAgIGlmIChzNCAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDQxKSB7XG4gICAgICAgICAgICAgICAgczUgPSBwZWckYzIzO1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgczUgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMyNCk7IH1cbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICBpZiAoczUgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMSA9IHBlZyRjMjUoczMpO1xuICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckcGFyc2VFeHByKCk7XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VFeHByKCkge1xuICAgICAgdmFyIHMwO1xuXG4gICAgICBzMCA9IHBlZyRwYXJzZU51bGxhcnlFeHByKCk7XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckcGFyc2VVbmFyeUV4cHIoKTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZU51bGxhcnlFeHByKCkge1xuICAgICAgdmFyIHMwLCBzMTtcblxuICAgICAgczAgPSBwZWckcGFyc2VCb29sZWFuTGl0ZXJhbCgpO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzI2KSB7XG4gICAgICAgICAgczEgPSBwZWckYzI2O1xuICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMyNyk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICBzMSA9IHBlZyRjMjgoKTtcbiAgICAgICAgfVxuICAgICAgICBzMCA9IHMxO1xuICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzI5KSB7XG4gICAgICAgICAgICBzMSA9IHBlZyRjMjk7XG4gICAgICAgICAgICBwZWckY3VyclBvcyArPSAyO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMzApOyB9XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICBzMSA9IHBlZyRjMzEoKTtcbiAgICAgICAgICB9XG4gICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGMzMikge1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjMzI7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMzMyk7IH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczEgPSBwZWckYzM0KCk7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzM1KSB7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckYzM1O1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMzNik7IH1cbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMSA9IHBlZyRjMzcoKTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlQm9vbGVhbkxpdGVyYWwoKSB7XG4gICAgICB2YXIgczAsIHMxO1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgNCkgPT09IHBlZyRjMzgpIHtcbiAgICAgICAgczEgPSBwZWckYzM4O1xuICAgICAgICBwZWckY3VyclBvcyArPSA0O1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMzkpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgIHMxID0gcGVnJGM0MCgpO1xuICAgICAgfVxuICAgICAgczAgPSBzMTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCA1KSA9PT0gcGVnJGM0MSkge1xuICAgICAgICAgIHMxID0gcGVnJGM0MTtcbiAgICAgICAgICBwZWckY3VyclBvcyArPSA1O1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNDIpOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgczEgPSBwZWckYzQzKCk7XG4gICAgICAgIH1cbiAgICAgICAgczAgPSBzMTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZVVuYXJ5RXhwcigpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyLCBzMztcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzQ0KSB7XG4gICAgICAgIHMxID0gcGVnJGM0NDtcbiAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzQ1KTsgfVxuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gW107XG4gICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczMgPSBwZWckcGFyc2VJbnRlZ2VyTGl0ZXJhbCgpO1xuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICBzMSA9IHBlZyRjNDYoczMpO1xuICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGM0Nykge1xuICAgICAgICAgIHMxID0gcGVnJGM0NztcbiAgICAgICAgICBwZWckY3VyclBvcyArPSAyO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNDgpOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGM0OShzMyk7XG4gICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjNTApIHtcbiAgICAgICAgICAgIHMxID0gcGVnJGM1MDtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM1MSk7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJGM1MihzMyk7XG4gICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAzKSA9PT0gcGVnJGM1Mykge1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjNTM7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDM7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM1NCk7IH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNTUoczMpO1xuICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAzKSA9PT0gcGVnJGM1Nikge1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJGM1NjtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyArPSAzO1xuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNTcpOyB9XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM1OChzMyk7XG4gICAgICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjNTkpIHtcbiAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM1OTtcbiAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM2MCk7IH1cbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM2MShzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGM2Mikge1xuICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNjI7XG4gICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM2Myk7IH1cbiAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNjQoczMpO1xuICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAzKSA9PT0gcGVnJGM2NSkge1xuICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM2NTtcbiAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyArPSAzO1xuICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNjYpOyB9XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM2NyhzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMykgPT09IHBlZyRjNjgpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM2ODtcbiAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDM7XG4gICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM2OSk7IH1cbiAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM3MChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGM3MSkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNzE7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM3Mik7IH1cbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNzMoczMpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzczKHMxKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlSW50ZWdlckxpdGVyYWwoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczM7XG5cbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIGlmIChwZWckYzc2LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgczEgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNzcpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczEgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckYzc1O1xuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gW107XG4gICAgICAgIGlmIChwZWckYzc4LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgICBzMyA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMyA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzc5KTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICBpZiAocGVnJGM3OC50ZXN0KGlucHV0LmNoYXJBdChwZWckY3VyclBvcykpKSB7XG4gICAgICAgICAgICAgIHMzID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHMzID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzc5KTsgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBpZiAocGVnJGM3Ni50ZXN0KGlucHV0LmNoYXJBdChwZWckY3VyclBvcykpKSB7XG4gICAgICAgICAgICBzMyA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNzcpOyB9XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMyA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczMgPSBwZWckYzc1O1xuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzgwKHMyKTtcbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM3NCk7IH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczM7XG5cbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMzQpIHtcbiAgICAgICAgczEgPSBwZWckYzgyO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjODMpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBbXTtcbiAgICAgICAgczMgPSBwZWckcGFyc2VEb3VibGVTdHJpbmdDaGFyKCk7XG4gICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgIHMzID0gcGVnJHBhcnNlRG91YmxlU3RyaW5nQ2hhcigpO1xuICAgICAgICB9XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMzQpIHtcbiAgICAgICAgICAgIHMzID0gcGVnJGM4MjtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMzID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM4Myk7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGM4NChzMik7XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMzkpIHtcbiAgICAgICAgICBzMSA9IHBlZyRjODU7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzg2KTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgczMgPSBwZWckcGFyc2VTaW5nbGVTdHJpbmdDaGFyKCk7XG4gICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU2luZ2xlU3RyaW5nQ2hhcigpO1xuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMzkpIHtcbiAgICAgICAgICAgICAgczMgPSBwZWckYzg1O1xuICAgICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgczMgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjODYpOyB9XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGM4NChzMik7XG4gICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgczEgPSBwZWckY3VyclBvcztcbiAgICAgICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgICAgICBzMiA9IHBlZyRwYXJzZWNjKCk7XG4gICAgICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICAgICAgaWYgKHMyID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMSA9IHBlZyRjODc7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczE7XG4gICAgICAgICAgICBzMSA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgczMgPSBwZWckcGFyc2VVbnF1b3RlZFN0cmluZ0NoYXIoKTtcbiAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVVucXVvdGVkU3RyaW5nQ2hhcigpO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczEgPSBwZWckYzg0KHMyKTtcbiAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM4MSk7IH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZURvdWJsZVN0cmluZ0NoYXIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMjtcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIHMxID0gcGVnJGN1cnJQb3M7XG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIGlmIChwZWckYzg4LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgczIgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczIgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjODkpOyB9XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMiA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRjODc7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMxO1xuICAgICAgICBzMSA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBpZiAoaW5wdXQubGVuZ3RoID4gcGVnJGN1cnJQb3MpIHtcbiAgICAgICAgICBzMiA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMiA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzkwKTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgIHMxID0gcGVnJGM5MShzMik7XG4gICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDkyKSB7XG4gICAgICAgICAgczEgPSBwZWckYzkyO1xuICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM5Myk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMiA9IHBlZyRwYXJzZUVzY2FwZVNlcXVlbmNlKCk7XG4gICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGM5MShzMik7XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZVNpbmdsZVN0cmluZ0NoYXIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMjtcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIHMxID0gcGVnJGN1cnJQb3M7XG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIGlmIChwZWckYzk0LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgczIgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczIgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOTUpOyB9XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMiA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRjODc7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMxO1xuICAgICAgICBzMSA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBpZiAoaW5wdXQubGVuZ3RoID4gcGVnJGN1cnJQb3MpIHtcbiAgICAgICAgICBzMiA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMiA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzkwKTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgIHMxID0gcGVnJGM5MShzMik7XG4gICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDkyKSB7XG4gICAgICAgICAgczEgPSBwZWckYzkyO1xuICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM5Myk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMiA9IHBlZyRwYXJzZUVzY2FwZVNlcXVlbmNlKCk7XG4gICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGM5MShzMik7XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZVVucXVvdGVkU3RyaW5nQ2hhcigpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyO1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgczEgPSBwZWckY3VyclBvcztcbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgczIgPSBwZWckcGFyc2V3cygpO1xuICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICBpZiAoczIgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckYzg3O1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMTtcbiAgICAgICAgczEgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgaWYgKGlucHV0Lmxlbmd0aCA+IHBlZyRjdXJyUG9zKSB7XG4gICAgICAgICAgczIgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczIgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM5MCk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICBzMSA9IHBlZyRjOTEoczIpO1xuICAgICAgICAgIHMwID0gczE7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VFc2NhcGVTZXF1ZW5jZSgpIHtcbiAgICAgIHZhciBzMCwgczE7XG5cbiAgICAgIGlmIChwZWckYzk2LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgczAgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczAgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOTcpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAxMTApIHtcbiAgICAgICAgICBzMSA9IHBlZyRjOTg7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzk5KTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgIHMxID0gcGVnJGMxMDAoKTtcbiAgICAgICAgfVxuICAgICAgICBzMCA9IHMxO1xuICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMTE0KSB7XG4gICAgICAgICAgICBzMSA9IHBlZyRjMTAxO1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzEwMik7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGMxMDMoKTtcbiAgICAgICAgICB9XG4gICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDExNikge1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjMTA0O1xuICAgICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMTA1KTsgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjMTA2KCk7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG5cbiAgICBmdW5jdGlvbiBvcihmaXJzdCwgc2Vjb25kKSB7XG4gICAgICAgIC8vIEFkZCBleHBsaWNpdCBmdW5jdGlvbiBuYW1lcyB0byBlYXNlIGRlYnVnZ2luZy5cbiAgICAgICAgZnVuY3Rpb24gb3JGaWx0ZXIoKSB7XG4gICAgICAgICAgICByZXR1cm4gZmlyc3QuYXBwbHkodGhpcywgYXJndW1lbnRzKSB8fCBzZWNvbmQuYXBwbHkodGhpcywgYXJndW1lbnRzKTtcbiAgICAgICAgfVxuICAgICAgICBvckZpbHRlci5kZXNjID0gZmlyc3QuZGVzYyArIFwiIG9yIFwiICsgc2Vjb25kLmRlc2M7XG4gICAgICAgIHJldHVybiBvckZpbHRlcjtcbiAgICB9XG4gICAgZnVuY3Rpb24gYW5kKGZpcnN0LCBzZWNvbmQpIHtcbiAgICAgICAgZnVuY3Rpb24gYW5kRmlsdGVyKCkge1xuICAgICAgICAgICAgcmV0dXJuIGZpcnN0LmFwcGx5KHRoaXMsIGFyZ3VtZW50cykgJiYgc2Vjb25kLmFwcGx5KHRoaXMsIGFyZ3VtZW50cyk7XG4gICAgICAgIH1cbiAgICAgICAgYW5kRmlsdGVyLmRlc2MgPSBmaXJzdC5kZXNjICsgXCIgYW5kIFwiICsgc2Vjb25kLmRlc2M7XG4gICAgICAgIHJldHVybiBhbmRGaWx0ZXI7XG4gICAgfVxuICAgIGZ1bmN0aW9uIG5vdChleHByKSB7XG4gICAgICAgIGZ1bmN0aW9uIG5vdEZpbHRlcigpIHtcbiAgICAgICAgICAgIHJldHVybiAhZXhwci5hcHBseSh0aGlzLCBhcmd1bWVudHMpO1xuICAgICAgICB9XG4gICAgICAgIG5vdEZpbHRlci5kZXNjID0gXCJub3QgXCIgKyBleHByLmRlc2M7XG4gICAgICAgIHJldHVybiBub3RGaWx0ZXI7XG4gICAgfVxuICAgIGZ1bmN0aW9uIGJpbmRpbmcoZXhwcikge1xuICAgICAgICBmdW5jdGlvbiBiaW5kaW5nRmlsdGVyKCkge1xuICAgICAgICAgICAgcmV0dXJuIGV4cHIuYXBwbHkodGhpcywgYXJndW1lbnRzKTtcbiAgICAgICAgfVxuICAgICAgICBiaW5kaW5nRmlsdGVyLmRlc2MgPSBcIihcIiArIGV4cHIuZGVzYyArIFwiKVwiO1xuICAgICAgICByZXR1cm4gYmluZGluZ0ZpbHRlcjtcbiAgICB9XG4gICAgZnVuY3Rpb24gdHJ1ZUZpbHRlcihmbG93KSB7XG4gICAgICAgIHJldHVybiB0cnVlO1xuICAgIH1cbiAgICB0cnVlRmlsdGVyLmRlc2MgPSBcInRydWVcIjtcbiAgICBmdW5jdGlvbiBmYWxzZUZpbHRlcihmbG93KSB7XG4gICAgICAgIHJldHVybiBmYWxzZTtcbiAgICB9XG4gICAgZmFsc2VGaWx0ZXIuZGVzYyA9IFwiZmFsc2VcIjtcblxuICAgIHZhciBBU1NFVF9UWVBFUyA9IFtcbiAgICAgICAgbmV3IFJlZ0V4cChcInRleHQvamF2YXNjcmlwdFwiKSxcbiAgICAgICAgbmV3IFJlZ0V4cChcImFwcGxpY2F0aW9uL3gtamF2YXNjcmlwdFwiKSxcbiAgICAgICAgbmV3IFJlZ0V4cChcImFwcGxpY2F0aW9uL2phdmFzY3JpcHRcIiksXG4gICAgICAgIG5ldyBSZWdFeHAoXCJ0ZXh0L2Nzc1wiKSxcbiAgICAgICAgbmV3IFJlZ0V4cChcImltYWdlLy4qXCIpLFxuICAgICAgICBuZXcgUmVnRXhwKFwiYXBwbGljYXRpb24veC1zaG9ja3dhdmUtZmxhc2hcIilcbiAgICBdO1xuICAgIGZ1bmN0aW9uIGFzc2V0RmlsdGVyKGZsb3cpIHtcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UpIHtcbiAgICAgICAgICAgIHZhciBjdCA9IFJlc3BvbnNlVXRpbHMuZ2V0Q29udGVudFR5cGUoZmxvdy5yZXNwb25zZSk7XG4gICAgICAgICAgICB2YXIgaSA9IEFTU0VUX1RZUEVTLmxlbmd0aDtcbiAgICAgICAgICAgIHdoaWxlIChpLS0pIHtcbiAgICAgICAgICAgICAgICBpZiAoQVNTRVRfVFlQRVNbaV0udGVzdChjdCkpIHtcbiAgICAgICAgICAgICAgICAgICAgcmV0dXJuIHRydWU7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICAgIHJldHVybiBmYWxzZTtcbiAgICB9XG4gICAgYXNzZXRGaWx0ZXIuZGVzYyA9IFwiaXMgYXNzZXRcIjtcbiAgICBmdW5jdGlvbiByZXNwb25zZUNvZGUoY29kZSl7XG4gICAgICAgIGZ1bmN0aW9uIHJlc3BvbnNlQ29kZUZpbHRlcihmbG93KXtcbiAgICAgICAgICAgIHJldHVybiBmbG93LnJlc3BvbnNlICYmIGZsb3cucmVzcG9uc2UuY29kZSA9PT0gY29kZTtcbiAgICAgICAgfVxuICAgICAgICByZXNwb25zZUNvZGVGaWx0ZXIuZGVzYyA9IFwicmVzcC4gY29kZSBpcyBcIiArIGNvZGU7XG4gICAgICAgIHJldHVybiByZXNwb25zZUNvZGVGaWx0ZXI7XG4gICAgfVxuICAgIGZ1bmN0aW9uIGRvbWFpbihyZWdleCl7XG4gICAgICAgIHJlZ2V4ID0gbmV3IFJlZ0V4cChyZWdleCwgXCJpXCIpO1xuICAgICAgICBmdW5jdGlvbiBkb21haW5GaWx0ZXIoZmxvdyl7XG4gICAgICAgICAgICByZXR1cm4gZmxvdy5yZXF1ZXN0ICYmIHJlZ2V4LnRlc3QoZmxvdy5yZXF1ZXN0Lmhvc3QpO1xuICAgICAgICB9XG4gICAgICAgIGRvbWFpbkZpbHRlci5kZXNjID0gXCJkb21haW4gbWF0Y2hlcyBcIiArIHJlZ2V4O1xuICAgICAgICByZXR1cm4gZG9tYWluRmlsdGVyO1xuICAgIH1cbiAgICBmdW5jdGlvbiBlcnJvckZpbHRlcihmbG93KXtcbiAgICAgICAgcmV0dXJuICEhZmxvdy5lcnJvcjtcbiAgICB9XG4gICAgZXJyb3JGaWx0ZXIuZGVzYyA9IFwiaGFzIGVycm9yXCI7XG4gICAgZnVuY3Rpb24gaGVhZGVyKHJlZ2V4KXtcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XG4gICAgICAgIGZ1bmN0aW9uIGhlYWRlckZpbHRlcihmbG93KXtcbiAgICAgICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICAgICAgKGZsb3cucmVxdWVzdCAmJiBSZXF1ZXN0VXRpbHMubWF0Y2hfaGVhZGVyKGZsb3cucmVxdWVzdCwgcmVnZXgpKVxuICAgICAgICAgICAgICAgIHx8XG4gICAgICAgICAgICAgICAgKGZsb3cucmVzcG9uc2UgJiYgUmVzcG9uc2VVdGlscy5tYXRjaF9oZWFkZXIoZmxvdy5yZXNwb25zZSwgcmVnZXgpKVxuICAgICAgICAgICAgKTtcbiAgICAgICAgfVxuICAgICAgICBoZWFkZXJGaWx0ZXIuZGVzYyA9IFwiaGVhZGVyIG1hdGNoZXMgXCIgKyByZWdleDtcbiAgICAgICAgcmV0dXJuIGhlYWRlckZpbHRlcjtcbiAgICB9XG4gICAgZnVuY3Rpb24gcmVxdWVzdEhlYWRlcihyZWdleCl7XG4gICAgICAgIHJlZ2V4ID0gbmV3IFJlZ0V4cChyZWdleCwgXCJpXCIpO1xuICAgICAgICBmdW5jdGlvbiByZXF1ZXN0SGVhZGVyRmlsdGVyKGZsb3cpe1xuICAgICAgICAgICAgcmV0dXJuIChmbG93LnJlcXVlc3QgJiYgUmVxdWVzdFV0aWxzLm1hdGNoX2hlYWRlcihmbG93LnJlcXVlc3QsIHJlZ2V4KSk7XG4gICAgICAgIH1cbiAgICAgICAgcmVxdWVzdEhlYWRlckZpbHRlci5kZXNjID0gXCJyZXEuIGhlYWRlciBtYXRjaGVzIFwiICsgcmVnZXg7XG4gICAgICAgIHJldHVybiByZXF1ZXN0SGVhZGVyRmlsdGVyO1xuICAgIH1cbiAgICBmdW5jdGlvbiByZXNwb25zZUhlYWRlcihyZWdleCl7XG4gICAgICAgIHJlZ2V4ID0gbmV3IFJlZ0V4cChyZWdleCwgXCJpXCIpO1xuICAgICAgICBmdW5jdGlvbiByZXNwb25zZUhlYWRlckZpbHRlcihmbG93KXtcbiAgICAgICAgICAgIHJldHVybiAoZmxvdy5yZXNwb25zZSAmJiBSZXNwb25zZVV0aWxzLm1hdGNoX2hlYWRlcihmbG93LnJlc3BvbnNlLCByZWdleCkpO1xuICAgICAgICB9XG4gICAgICAgIHJlc3BvbnNlSGVhZGVyRmlsdGVyLmRlc2MgPSBcInJlc3AuIGhlYWRlciBtYXRjaGVzIFwiICsgcmVnZXg7XG4gICAgICAgIHJldHVybiByZXNwb25zZUhlYWRlckZpbHRlcjtcbiAgICB9XG4gICAgZnVuY3Rpb24gbWV0aG9kKHJlZ2V4KXtcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XG4gICAgICAgIGZ1bmN0aW9uIG1ldGhvZEZpbHRlcihmbG93KXtcbiAgICAgICAgICAgIHJldHVybiBmbG93LnJlcXVlc3QgJiYgcmVnZXgudGVzdChmbG93LnJlcXVlc3QubWV0aG9kKTtcbiAgICAgICAgfVxuICAgICAgICBtZXRob2RGaWx0ZXIuZGVzYyA9IFwibWV0aG9kIG1hdGNoZXMgXCIgKyByZWdleDtcbiAgICAgICAgcmV0dXJuIG1ldGhvZEZpbHRlcjtcbiAgICB9XG4gICAgZnVuY3Rpb24gbm9SZXNwb25zZUZpbHRlcihmbG93KXtcbiAgICAgICAgcmV0dXJuIGZsb3cucmVxdWVzdCAmJiAhZmxvdy5yZXNwb25zZTtcbiAgICB9XG4gICAgbm9SZXNwb25zZUZpbHRlci5kZXNjID0gXCJoYXMgbm8gcmVzcG9uc2VcIjtcbiAgICBmdW5jdGlvbiByZXNwb25zZUZpbHRlcihmbG93KXtcbiAgICAgICAgcmV0dXJuICEhZmxvdy5yZXNwb25zZTtcbiAgICB9XG4gICAgcmVzcG9uc2VGaWx0ZXIuZGVzYyA9IFwiaGFzIHJlc3BvbnNlXCI7XG5cbiAgICBmdW5jdGlvbiBjb250ZW50VHlwZShyZWdleCl7XG4gICAgICAgIHJlZ2V4ID0gbmV3IFJlZ0V4cChyZWdleCwgXCJpXCIpO1xuICAgICAgICBmdW5jdGlvbiBjb250ZW50VHlwZUZpbHRlcihmbG93KXtcbiAgICAgICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICAgICAgKGZsb3cucmVxdWVzdCAmJiByZWdleC50ZXN0KFJlcXVlc3RVdGlscy5nZXRDb250ZW50VHlwZShmbG93LnJlcXVlc3QpKSlcbiAgICAgICAgICAgICAgICB8fFxuICAgICAgICAgICAgICAgIChmbG93LnJlc3BvbnNlICYmIHJlZ2V4LnRlc3QoUmVzcG9uc2VVdGlscy5nZXRDb250ZW50VHlwZShmbG93LnJlc3BvbnNlKSkpXG4gICAgICAgICAgICApO1xuICAgICAgICB9XG4gICAgICAgIGNvbnRlbnRUeXBlRmlsdGVyLmRlc2MgPSBcImNvbnRlbnQgdHlwZSBtYXRjaGVzIFwiICsgcmVnZXg7XG4gICAgICAgIHJldHVybiBjb250ZW50VHlwZUZpbHRlcjtcbiAgICB9XG4gICAgZnVuY3Rpb24gcmVxdWVzdENvbnRlbnRUeXBlKHJlZ2V4KXtcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XG4gICAgICAgIGZ1bmN0aW9uIHJlcXVlc3RDb250ZW50VHlwZUZpbHRlcihmbG93KXtcbiAgICAgICAgICAgIHJldHVybiBmbG93LnJlcXVlc3QgJiYgcmVnZXgudGVzdChSZXF1ZXN0VXRpbHMuZ2V0Q29udGVudFR5cGUoZmxvdy5yZXF1ZXN0KSk7XG4gICAgICAgIH1cbiAgICAgICAgcmVxdWVzdENvbnRlbnRUeXBlRmlsdGVyLmRlc2MgPSBcInJlcS4gY29udGVudCB0eXBlIG1hdGNoZXMgXCIgKyByZWdleDtcbiAgICAgICAgcmV0dXJuIHJlcXVlc3RDb250ZW50VHlwZUZpbHRlcjtcbiAgICB9XG4gICAgZnVuY3Rpb24gcmVzcG9uc2VDb250ZW50VHlwZShyZWdleCl7XG4gICAgICAgIHJlZ2V4ID0gbmV3IFJlZ0V4cChyZWdleCwgXCJpXCIpO1xuICAgICAgICBmdW5jdGlvbiByZXNwb25zZUNvbnRlbnRUeXBlRmlsdGVyKGZsb3cpe1xuICAgICAgICAgICAgcmV0dXJuIGZsb3cucmVzcG9uc2UgJiYgcmVnZXgudGVzdChSZXNwb25zZVV0aWxzLmdldENvbnRlbnRUeXBlKGZsb3cucmVzcG9uc2UpKTtcbiAgICAgICAgfVxuICAgICAgICByZXNwb25zZUNvbnRlbnRUeXBlRmlsdGVyLmRlc2MgPSBcInJlc3AuIGNvbnRlbnQgdHlwZSBtYXRjaGVzIFwiICsgcmVnZXg7XG4gICAgICAgIHJldHVybiByZXNwb25zZUNvbnRlbnRUeXBlRmlsdGVyO1xuICAgIH1cbiAgICBmdW5jdGlvbiB1cmwocmVnZXgpe1xuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcbiAgICAgICAgZnVuY3Rpb24gdXJsRmlsdGVyKGZsb3cpe1xuICAgICAgICAgICAgcmV0dXJuIGZsb3cucmVxdWVzdCAmJiByZWdleC50ZXN0KFJlcXVlc3RVdGlscy5wcmV0dHlfdXJsKGZsb3cucmVxdWVzdCkpO1xuICAgICAgICB9XG4gICAgICAgIHVybEZpbHRlci5kZXNjID0gXCJ1cmwgbWF0Y2hlcyBcIiArIHJlZ2V4O1xuICAgICAgICByZXR1cm4gdXJsRmlsdGVyO1xuICAgIH1cblxuXG4gICAgcGVnJHJlc3VsdCA9IHBlZyRzdGFydFJ1bGVGdW5jdGlvbigpO1xuXG4gICAgaWYgKHBlZyRyZXN1bHQgIT09IHBlZyRGQUlMRUQgJiYgcGVnJGN1cnJQb3MgPT09IGlucHV0Lmxlbmd0aCkge1xuICAgICAgcmV0dXJuIHBlZyRyZXN1bHQ7XG4gICAgfSBlbHNlIHtcbiAgICAgIGlmIChwZWckcmVzdWx0ICE9PSBwZWckRkFJTEVEICYmIHBlZyRjdXJyUG9zIDwgaW5wdXQubGVuZ3RoKSB7XG4gICAgICAgIHBlZyRmYWlsKHsgdHlwZTogXCJlbmRcIiwgZGVzY3JpcHRpb246IFwiZW5kIG9mIGlucHV0XCIgfSk7XG4gICAgICB9XG5cbiAgICAgIHRocm93IHBlZyRidWlsZEV4Y2VwdGlvbihudWxsLCBwZWckbWF4RmFpbEV4cGVjdGVkLCBwZWckbWF4RmFpbFBvcyk7XG4gICAgfVxuICB9XG5cbiAgcmV0dXJuIHtcbiAgICBTeW50YXhFcnJvcjogU3ludGF4RXJyb3IsXG4gICAgcGFyc2U6ICAgICAgIHBhcnNlXG4gIH07XG59KSgpO1xuLyoganNoaW50IGlnbm9yZTplbmQgKi9cblxubW9kdWxlLmV4cG9ydHMgPSBGaWx0O1xuIiwidmFyIF8gPSByZXF1aXJlKFwibG9kYXNoXCIpO1xuXG52YXIgX01lc3NhZ2VVdGlscyA9IHtcbiAgICBnZXRDb250ZW50VHlwZTogZnVuY3Rpb24gKG1lc3NhZ2UpIHtcbiAgICAgICAgcmV0dXJuIHRoaXMuZ2V0X2ZpcnN0X2hlYWRlcihtZXNzYWdlLCAvXkNvbnRlbnQtVHlwZSQvaSk7XG4gICAgfSxcbiAgICBnZXRfZmlyc3RfaGVhZGVyOiBmdW5jdGlvbiAobWVzc2FnZSwgcmVnZXgpIHtcbiAgICAgICAgLy9GSVhNRTogQ2FjaGUgSW52YWxpZGF0aW9uLlxuICAgICAgICBpZiAoIW1lc3NhZ2UuX2hlYWRlckxvb2t1cHMpXG4gICAgICAgICAgICBPYmplY3QuZGVmaW5lUHJvcGVydHkobWVzc2FnZSwgXCJfaGVhZGVyTG9va3Vwc1wiLCB7XG4gICAgICAgICAgICAgICAgdmFsdWU6IHt9LFxuICAgICAgICAgICAgICAgIGNvbmZpZ3VyYWJsZTogZmFsc2UsXG4gICAgICAgICAgICAgICAgZW51bWVyYWJsZTogZmFsc2UsXG4gICAgICAgICAgICAgICAgd3JpdGFibGU6IGZhbHNlXG4gICAgICAgICAgICB9KTtcbiAgICAgICAgaWYgKCEocmVnZXggaW4gbWVzc2FnZS5faGVhZGVyTG9va3VwcykpIHtcbiAgICAgICAgICAgIHZhciBoZWFkZXI7XG4gICAgICAgICAgICBmb3IgKHZhciBpID0gMDsgaSA8IG1lc3NhZ2UuaGVhZGVycy5sZW5ndGg7IGkrKykge1xuICAgICAgICAgICAgICAgIGlmICghIW1lc3NhZ2UuaGVhZGVyc1tpXVswXS5tYXRjaChyZWdleCkpIHtcbiAgICAgICAgICAgICAgICAgICAgaGVhZGVyID0gbWVzc2FnZS5oZWFkZXJzW2ldO1xuICAgICAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBtZXNzYWdlLl9oZWFkZXJMb29rdXBzW3JlZ2V4XSA9IGhlYWRlciA/IGhlYWRlclsxXSA6IHVuZGVmaW5lZDtcbiAgICAgICAgfVxuICAgICAgICByZXR1cm4gbWVzc2FnZS5faGVhZGVyTG9va3Vwc1tyZWdleF07XG4gICAgfSxcbiAgICBtYXRjaF9oZWFkZXI6IGZ1bmN0aW9uIChtZXNzYWdlLCByZWdleCkge1xuICAgICAgICB2YXIgaGVhZGVycyA9IG1lc3NhZ2UuaGVhZGVycztcbiAgICAgICAgdmFyIGkgPSBoZWFkZXJzLmxlbmd0aDtcbiAgICAgICAgd2hpbGUgKGktLSkge1xuICAgICAgICAgICAgaWYgKHJlZ2V4LnRlc3QoaGVhZGVyc1tpXS5qb2luKFwiIFwiKSkpIHtcbiAgICAgICAgICAgICAgICByZXR1cm4gaGVhZGVyc1tpXTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgICByZXR1cm4gZmFsc2U7XG4gICAgfVxufTtcblxudmFyIGRlZmF1bHRQb3J0cyA9IHtcbiAgICBcImh0dHBcIjogODAsXG4gICAgXCJodHRwc1wiOiA0NDNcbn07XG5cbnZhciBSZXF1ZXN0VXRpbHMgPSBfLmV4dGVuZChfTWVzc2FnZVV0aWxzLCB7XG4gICAgcHJldHR5X2hvc3Q6IGZ1bmN0aW9uIChyZXF1ZXN0KSB7XG4gICAgICAgIC8vRklYTUU6IEFkZCBob3N0aGVhZGVyXG4gICAgICAgIHJldHVybiByZXF1ZXN0Lmhvc3Q7XG4gICAgfSxcbiAgICBwcmV0dHlfdXJsOiBmdW5jdGlvbiAocmVxdWVzdCkge1xuICAgICAgICB2YXIgcG9ydCA9IFwiXCI7XG4gICAgICAgIGlmIChkZWZhdWx0UG9ydHNbcmVxdWVzdC5zY2hlbWVdICE9PSByZXF1ZXN0LnBvcnQpIHtcbiAgICAgICAgICAgIHBvcnQgPSBcIjpcIiArIHJlcXVlc3QucG9ydDtcbiAgICAgICAgfVxuICAgICAgICByZXR1cm4gcmVxdWVzdC5zY2hlbWUgKyBcIjovL1wiICsgdGhpcy5wcmV0dHlfaG9zdChyZXF1ZXN0KSArIHBvcnQgKyByZXF1ZXN0LnBhdGg7XG4gICAgfVxufSk7XG5cbnZhciBSZXNwb25zZVV0aWxzID0gXy5leHRlbmQoX01lc3NhZ2VVdGlscywge30pO1xuXG5cbm1vZHVsZS5leHBvcnRzID0ge1xuICAgIFJlc3BvbnNlVXRpbHM6IFJlc3BvbnNlVXRpbHMsXG4gICAgUmVxdWVzdFV0aWxzOiBSZXF1ZXN0VXRpbHNcblxufSIsIlxudmFyIF8gPSByZXF1aXJlKFwibG9kYXNoXCIpO1xudmFyICQgPSByZXF1aXJlKFwianF1ZXJ5XCIpO1xudmFyIEV2ZW50RW1pdHRlciA9IHJlcXVpcmUoJ2V2ZW50cycpLkV2ZW50RW1pdHRlcjtcblxudmFyIHV0aWxzID0gcmVxdWlyZShcIi4uL3V0aWxzLmpzXCIpO1xudmFyIGFjdGlvbnMgPSByZXF1aXJlKFwiLi4vYWN0aW9ucy5qc1wiKTtcbnZhciBkaXNwYXRjaGVyID0gcmVxdWlyZShcIi4uL2Rpc3BhdGNoZXIuanNcIik7XG5cblxuZnVuY3Rpb24gTGlzdFN0b3JlKCkge1xuICAgIEV2ZW50RW1pdHRlci5jYWxsKHRoaXMpO1xuICAgIHRoaXMucmVzZXQoKTtcbn1cbl8uZXh0ZW5kKExpc3RTdG9yZS5wcm90b3R5cGUsIEV2ZW50RW1pdHRlci5wcm90b3R5cGUsIHtcbiAgICBhZGQ6IGZ1bmN0aW9uIChlbGVtKSB7XG4gICAgICAgIGlmIChlbGVtLmlkIGluIHRoaXMuX3Bvc19tYXApIHtcbiAgICAgICAgICAgIHJldHVybjtcbiAgICAgICAgfVxuICAgICAgICB0aGlzLl9wb3NfbWFwW2VsZW0uaWRdID0gdGhpcy5saXN0Lmxlbmd0aDtcbiAgICAgICAgdGhpcy5saXN0LnB1c2goZWxlbSk7XG4gICAgICAgIHRoaXMuZW1pdChcImFkZFwiLCBlbGVtKTtcbiAgICB9LFxuICAgIHVwZGF0ZTogZnVuY3Rpb24gKGVsZW0pIHtcbiAgICAgICAgaWYgKCEoZWxlbS5pZCBpbiB0aGlzLl9wb3NfbWFwKSkge1xuICAgICAgICAgICAgcmV0dXJuO1xuICAgICAgICB9XG4gICAgICAgIHRoaXMubGlzdFt0aGlzLl9wb3NfbWFwW2VsZW0uaWRdXSA9IGVsZW07XG4gICAgICAgIHRoaXMuZW1pdChcInVwZGF0ZVwiLCBlbGVtKTtcbiAgICB9LFxuICAgIHJlbW92ZTogZnVuY3Rpb24gKGVsZW1faWQpIHtcbiAgICAgICAgaWYgKCEoZWxlbV9pZCBpbiB0aGlzLl9wb3NfbWFwKSkge1xuICAgICAgICAgICAgcmV0dXJuO1xuICAgICAgICB9XG4gICAgICAgIHRoaXMubGlzdC5zcGxpY2UodGhpcy5fcG9zX21hcFtlbGVtX2lkXSwgMSk7XG4gICAgICAgIHRoaXMuX2J1aWxkX21hcCgpO1xuICAgICAgICB0aGlzLmVtaXQoXCJyZW1vdmVcIiwgZWxlbV9pZCk7XG4gICAgfSxcbiAgICByZXNldDogZnVuY3Rpb24gKGVsZW1zKSB7XG4gICAgICAgIHRoaXMubGlzdCA9IGVsZW1zIHx8IFtdO1xuICAgICAgICB0aGlzLl9idWlsZF9tYXAoKTtcbiAgICAgICAgdGhpcy5lbWl0KFwicmVjYWxjdWxhdGVcIik7XG4gICAgfSxcbiAgICBfYnVpbGRfbWFwOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuX3Bvc19tYXAgPSB7fTtcbiAgICAgICAgZm9yICh2YXIgaSA9IDA7IGkgPCB0aGlzLmxpc3QubGVuZ3RoOyBpKyspIHtcbiAgICAgICAgICAgIHZhciBlbGVtID0gdGhpcy5saXN0W2ldO1xuICAgICAgICAgICAgdGhpcy5fcG9zX21hcFtlbGVtLmlkXSA9IGk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGdldDogZnVuY3Rpb24gKGVsZW1faWQpIHtcbiAgICAgICAgcmV0dXJuIHRoaXMubGlzdFt0aGlzLl9wb3NfbWFwW2VsZW1faWRdXTtcbiAgICB9LFxuICAgIGluZGV4OiBmdW5jdGlvbiAoZWxlbV9pZCkge1xuICAgICAgICByZXR1cm4gdGhpcy5fcG9zX21hcFtlbGVtX2lkXTtcbiAgICB9XG59KTtcblxuXG5mdW5jdGlvbiBEaWN0U3RvcmUoKSB7XG4gICAgRXZlbnRFbWl0dGVyLmNhbGwodGhpcyk7XG4gICAgdGhpcy5yZXNldCgpO1xufVxuXy5leHRlbmQoRGljdFN0b3JlLnByb3RvdHlwZSwgRXZlbnRFbWl0dGVyLnByb3RvdHlwZSwge1xuICAgIHVwZGF0ZTogZnVuY3Rpb24gKGRpY3QpIHtcbiAgICAgICAgXy5tZXJnZSh0aGlzLmRpY3QsIGRpY3QpO1xuICAgICAgICB0aGlzLmVtaXQoXCJyZWNhbGN1bGF0ZVwiKTtcbiAgICB9LFxuICAgIHJlc2V0OiBmdW5jdGlvbiAoZGljdCkge1xuICAgICAgICB0aGlzLmRpY3QgPSBkaWN0IHx8IHt9O1xuICAgICAgICB0aGlzLmVtaXQoXCJyZWNhbGN1bGF0ZVwiKTtcbiAgICB9XG59KTtcblxuZnVuY3Rpb24gTGl2ZVN0b3JlTWl4aW4odHlwZSkge1xuICAgIHRoaXMudHlwZSA9IHR5cGU7XG5cbiAgICB0aGlzLl91cGRhdGVzX2JlZm9yZV9mZXRjaCA9IHVuZGVmaW5lZDtcbiAgICB0aGlzLl9mZXRjaHhociA9IGZhbHNlO1xuXG4gICAgdGhpcy5oYW5kbGUgPSB0aGlzLmhhbmRsZS5iaW5kKHRoaXMpO1xuICAgIGRpc3BhdGNoZXIuQXBwRGlzcGF0Y2hlci5yZWdpc3Rlcih0aGlzLmhhbmRsZSk7XG5cbiAgICAvLyBBdm9pZCBkb3VibGUtZmV0Y2ggb24gc3RhcnR1cC5cbiAgICBpZiAoISh3aW5kb3cud3MgJiYgd2luZG93LndzLnJlYWR5U3RhdGUgPT09IFdlYlNvY2tldC5DT05ORUNUSU5HKSkge1xuICAgICAgICB0aGlzLmZldGNoKCk7XG4gICAgfVxufVxuXy5leHRlbmQoTGl2ZVN0b3JlTWl4aW4ucHJvdG90eXBlLCB7XG4gICAgaGFuZGxlOiBmdW5jdGlvbiAoZXZlbnQpIHtcbiAgICAgICAgaWYgKGV2ZW50LnR5cGUgPT09IGFjdGlvbnMuQWN0aW9uVHlwZXMuQ09OTkVDVElPTl9PUEVOKSB7XG4gICAgICAgICAgICByZXR1cm4gdGhpcy5mZXRjaCgpO1xuICAgICAgICB9XG4gICAgICAgIGlmIChldmVudC50eXBlID09PSB0aGlzLnR5cGUpIHtcbiAgICAgICAgICAgIGlmIChldmVudC5jbWQgPT09IGFjdGlvbnMuU3RvcmVDbWRzLlJFU0VUKSB7XG4gICAgICAgICAgICAgICAgdGhpcy5mZXRjaChldmVudC5kYXRhKTtcbiAgICAgICAgICAgIH0gZWxzZSBpZiAodGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2gpIHtcbiAgICAgICAgICAgICAgICBjb25zb2xlLmxvZyhcImRlZmVyIHVwZGF0ZVwiLCBldmVudCk7XG4gICAgICAgICAgICAgICAgdGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2gucHVzaChldmVudCk7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHRoaXNbZXZlbnQuY21kXShldmVudC5kYXRhKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgIH0sXG4gICAgY2xvc2U6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgZGlzcGF0Y2hlci5BcHBEaXNwYXRjaGVyLnVucmVnaXN0ZXIodGhpcy5oYW5kbGUpO1xuICAgIH0sXG4gICAgZmV0Y2g6IGZ1bmN0aW9uIChkYXRhKSB7XG4gICAgICAgIGNvbnNvbGUubG9nKFwiZmV0Y2ggXCIgKyB0aGlzLnR5cGUpO1xuICAgICAgICBpZiAodGhpcy5fZmV0Y2h4aHIpIHtcbiAgICAgICAgICAgIHRoaXMuX2ZldGNoeGhyLmFib3J0KCk7XG4gICAgICAgIH1cbiAgICAgICAgdGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2ggPSBbXTsgLy8gKEpTOiBlbXB0eSBhcnJheSBpcyB0cnVlKVxuICAgICAgICBpZiAoZGF0YSkge1xuICAgICAgICAgICAgdGhpcy5oYW5kbGVfZmV0Y2goZGF0YSk7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICB0aGlzLl9mZXRjaHhociA9ICQuZ2V0SlNPTihcIi9cIiArIHRoaXMudHlwZSlcbiAgICAgICAgICAgICAgICAuZG9uZShmdW5jdGlvbiAobWVzc2FnZSkge1xuICAgICAgICAgICAgICAgICAgICB0aGlzLmhhbmRsZV9mZXRjaChtZXNzYWdlLmRhdGEpO1xuICAgICAgICAgICAgICAgIH0uYmluZCh0aGlzKSlcbiAgICAgICAgICAgICAgICAuZmFpbChmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICAgICAgICAgIEV2ZW50TG9nQWN0aW9ucy5hZGRfZXZlbnQoXCJDb3VsZCBub3QgZmV0Y2ggXCIgKyB0aGlzLnR5cGUpO1xuICAgICAgICAgICAgICAgIH0uYmluZCh0aGlzKSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGhhbmRsZV9mZXRjaDogZnVuY3Rpb24gKGRhdGEpIHtcbiAgICAgICAgdGhpcy5fZmV0Y2h4aHIgPSBmYWxzZTtcbiAgICAgICAgY29uc29sZS5sb2codGhpcy50eXBlICsgXCIgZmV0Y2hlZC5cIiwgdGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2gpO1xuICAgICAgICB0aGlzLnJlc2V0KGRhdGEpO1xuICAgICAgICB2YXIgdXBkYXRlcyA9IHRoaXMuX3VwZGF0ZXNfYmVmb3JlX2ZldGNoO1xuICAgICAgICB0aGlzLl91cGRhdGVzX2JlZm9yZV9mZXRjaCA9IGZhbHNlO1xuICAgICAgICBmb3IgKHZhciBpID0gMDsgaSA8IHVwZGF0ZXMubGVuZ3RoOyBpKyspIHtcbiAgICAgICAgICAgIHRoaXMuaGFuZGxlKHVwZGF0ZXNbaV0pO1xuICAgICAgICB9XG4gICAgfSxcbn0pO1xuXG5mdW5jdGlvbiBMaXZlTGlzdFN0b3JlKHR5cGUpIHtcbiAgICBMaXN0U3RvcmUuY2FsbCh0aGlzKTtcbiAgICBMaXZlU3RvcmVNaXhpbi5jYWxsKHRoaXMsIHR5cGUpO1xufVxuXy5leHRlbmQoTGl2ZUxpc3RTdG9yZS5wcm90b3R5cGUsIExpc3RTdG9yZS5wcm90b3R5cGUsIExpdmVTdG9yZU1peGluLnByb3RvdHlwZSk7XG5cbmZ1bmN0aW9uIExpdmVEaWN0U3RvcmUodHlwZSkge1xuICAgIERpY3RTdG9yZS5jYWxsKHRoaXMpO1xuICAgIExpdmVTdG9yZU1peGluLmNhbGwodGhpcywgdHlwZSk7XG59XG5fLmV4dGVuZChMaXZlRGljdFN0b3JlLnByb3RvdHlwZSwgRGljdFN0b3JlLnByb3RvdHlwZSwgTGl2ZVN0b3JlTWl4aW4ucHJvdG90eXBlKTtcblxuXG5mdW5jdGlvbiBGbG93U3RvcmUoKSB7XG4gICAgcmV0dXJuIG5ldyBMaXZlTGlzdFN0b3JlKGFjdGlvbnMuQWN0aW9uVHlwZXMuRkxPV19TVE9SRSk7XG59XG5cbmZ1bmN0aW9uIFNldHRpbmdzU3RvcmUoKSB7XG4gICAgcmV0dXJuIG5ldyBMaXZlRGljdFN0b3JlKGFjdGlvbnMuQWN0aW9uVHlwZXMuU0VUVElOR1NfU1RPUkUpO1xufVxuXG5mdW5jdGlvbiBFdmVudExvZ1N0b3JlKCkge1xuICAgIExpdmVMaXN0U3RvcmUuY2FsbCh0aGlzLCBhY3Rpb25zLkFjdGlvblR5cGVzLkVWRU5UX1NUT1JFKTtcbn1cbl8uZXh0ZW5kKEV2ZW50TG9nU3RvcmUucHJvdG90eXBlLCBMaXZlTGlzdFN0b3JlLnByb3RvdHlwZSwge1xuICAgIGZldGNoOiBmdW5jdGlvbigpe1xuICAgICAgICBMaXZlTGlzdFN0b3JlLnByb3RvdHlwZS5mZXRjaC5hcHBseSh0aGlzLCBhcmd1bWVudHMpO1xuXG4gICAgICAgIC8vIE1ha2Ugc3VyZSB0byBkaXNwbGF5IHVwZGF0ZXMgZXZlbiBpZiBmZXRjaGluZyBhbGwgZXZlbnRzIGZhaWxlZC5cbiAgICAgICAgLy8gVGhpcyB3YXksIHdlIGNhbiBzZW5kIFwiZmV0Y2ggZmFpbGVkXCIgbG9nIG1lc3NhZ2VzIHRvIHRoZSBsb2cuXG4gICAgICAgIGlmKHRoaXMuX2ZldGNoeGhyKXtcbiAgICAgICAgICAgIHRoaXMuX2ZldGNoeGhyLmZhaWwoZnVuY3Rpb24oKXtcbiAgICAgICAgICAgICAgICB0aGlzLmhhbmRsZV9mZXRjaChudWxsKTtcbiAgICAgICAgICAgIH0uYmluZCh0aGlzKSk7XG4gICAgICAgIH1cbiAgICB9XG59KTtcblxuXG5tb2R1bGUuZXhwb3J0cyA9IHtcbiAgICBFdmVudExvZ1N0b3JlOiBFdmVudExvZ1N0b3JlLFxuICAgIFNldHRpbmdzU3RvcmU6IFNldHRpbmdzU3RvcmUsXG4gICAgRmxvd1N0b3JlOiBGbG93U3RvcmVcbn07IiwiXG52YXIgRXZlbnRFbWl0dGVyID0gcmVxdWlyZSgnZXZlbnRzJykuRXZlbnRFbWl0dGVyO1xudmFyIF8gPSByZXF1aXJlKFwibG9kYXNoXCIpO1xuXG5cbnZhciB1dGlscyA9IHJlcXVpcmUoXCIuLi91dGlscy5qc1wiKTtcblxuZnVuY3Rpb24gU29ydEJ5U3RvcmVPcmRlcihlbGVtKSB7XG4gICAgcmV0dXJuIHRoaXMuc3RvcmUuaW5kZXgoZWxlbS5pZCk7XG59XG5cbnZhciBkZWZhdWx0X3NvcnQgPSBTb3J0QnlTdG9yZU9yZGVyO1xudmFyIGRlZmF1bHRfZmlsdCA9IGZ1bmN0aW9uKGVsZW0pe1xuICAgIHJldHVybiB0cnVlO1xufTtcblxuZnVuY3Rpb24gU3RvcmVWaWV3KHN0b3JlLCBmaWx0LCBzb3J0ZnVuKSB7XG4gICAgRXZlbnRFbWl0dGVyLmNhbGwodGhpcyk7XG4gICAgZmlsdCA9IGZpbHQgfHwgZGVmYXVsdF9maWx0O1xuICAgIHNvcnRmdW4gPSBzb3J0ZnVuIHx8IGRlZmF1bHRfc29ydDtcblxuICAgIHRoaXMuc3RvcmUgPSBzdG9yZTtcblxuICAgIHRoaXMuYWRkID0gdGhpcy5hZGQuYmluZCh0aGlzKTtcbiAgICB0aGlzLnVwZGF0ZSA9IHRoaXMudXBkYXRlLmJpbmQodGhpcyk7XG4gICAgdGhpcy5yZW1vdmUgPSB0aGlzLnJlbW92ZS5iaW5kKHRoaXMpO1xuICAgIHRoaXMucmVjYWxjdWxhdGUgPSB0aGlzLnJlY2FsY3VsYXRlLmJpbmQodGhpcyk7XG4gICAgdGhpcy5zdG9yZS5hZGRMaXN0ZW5lcihcImFkZFwiLCB0aGlzLmFkZCk7XG4gICAgdGhpcy5zdG9yZS5hZGRMaXN0ZW5lcihcInVwZGF0ZVwiLCB0aGlzLnVwZGF0ZSk7XG4gICAgdGhpcy5zdG9yZS5hZGRMaXN0ZW5lcihcInJlbW92ZVwiLCB0aGlzLnJlbW92ZSk7XG4gICAgdGhpcy5zdG9yZS5hZGRMaXN0ZW5lcihcInJlY2FsY3VsYXRlXCIsIHRoaXMucmVjYWxjdWxhdGUpO1xuXG4gICAgdGhpcy5yZWNhbGN1bGF0ZShmaWx0LCBzb3J0ZnVuKTtcbn1cblxuXy5leHRlbmQoU3RvcmVWaWV3LnByb3RvdHlwZSwgRXZlbnRFbWl0dGVyLnByb3RvdHlwZSwge1xuICAgIGNsb3NlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuc3RvcmUucmVtb3ZlTGlzdGVuZXIoXCJhZGRcIiwgdGhpcy5hZGQpO1xuICAgICAgICB0aGlzLnN0b3JlLnJlbW92ZUxpc3RlbmVyKFwidXBkYXRlXCIsIHRoaXMudXBkYXRlKTtcbiAgICAgICAgdGhpcy5zdG9yZS5yZW1vdmVMaXN0ZW5lcihcInJlbW92ZVwiLCB0aGlzLnJlbW92ZSk7XG4gICAgICAgIHRoaXMuc3RvcmUucmVtb3ZlTGlzdGVuZXIoXCJyZWNhbGN1bGF0ZVwiLCB0aGlzLnJlY2FsY3VsYXRlKTtcbiAgICAgICAgfSxcbiAgICAgICAgcmVjYWxjdWxhdGU6IGZ1bmN0aW9uIChmaWx0LCBzb3J0ZnVuKSB7XG4gICAgICAgIGlmIChmaWx0KSB7XG4gICAgICAgICAgICB0aGlzLmZpbHQgPSBmaWx0LmJpbmQodGhpcyk7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHNvcnRmdW4pIHtcbiAgICAgICAgICAgIHRoaXMuc29ydGZ1biA9IHNvcnRmdW4uYmluZCh0aGlzKTtcbiAgICAgICAgfVxuXG4gICAgICAgIHRoaXMubGlzdCA9IHRoaXMuc3RvcmUubGlzdC5maWx0ZXIodGhpcy5maWx0KTtcbiAgICAgICAgdGhpcy5saXN0LnNvcnQoZnVuY3Rpb24gKGEsIGIpIHtcbiAgICAgICAgICAgIHJldHVybiB0aGlzLnNvcnRmdW4oYSkgLSB0aGlzLnNvcnRmdW4oYik7XG4gICAgICAgIH0uYmluZCh0aGlzKSk7XG4gICAgICAgIHRoaXMuZW1pdChcInJlY2FsY3VsYXRlXCIpO1xuICAgIH0sXG4gICAgaW5kZXg6IGZ1bmN0aW9uIChlbGVtKSB7XG4gICAgICAgIHJldHVybiBfLnNvcnRlZEluZGV4KHRoaXMubGlzdCwgZWxlbSwgdGhpcy5zb3J0ZnVuKTtcbiAgICB9LFxuICAgIGFkZDogZnVuY3Rpb24gKGVsZW0pIHtcbiAgICAgICAgaWYgKHRoaXMuZmlsdChlbGVtKSkge1xuICAgICAgICAgICAgdmFyIGlkeCA9IHRoaXMuaW5kZXgoZWxlbSk7XG4gICAgICAgICAgICBpZiAoaWR4ID09PSB0aGlzLmxpc3QubGVuZ3RoKSB7IC8vaGFwcGVucyBvZnRlbiwgLnB1c2ggaXMgd2F5IGZhc3Rlci5cbiAgICAgICAgICAgICAgICB0aGlzLmxpc3QucHVzaChlbGVtKTtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgdGhpcy5saXN0LnNwbGljZShpZHgsIDAsIGVsZW0pO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgdGhpcy5lbWl0KFwiYWRkXCIsIGVsZW0sIGlkeCk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIHVwZGF0ZTogZnVuY3Rpb24gKGVsZW0pIHtcbiAgICAgICAgdmFyIGlkeDtcbiAgICAgICAgdmFyIGkgPSB0aGlzLmxpc3QubGVuZ3RoO1xuICAgICAgICAvLyBTZWFyY2ggZnJvbSB0aGUgYmFjaywgd2UgdXN1YWxseSB1cGRhdGUgdGhlIGxhdGVzdCBlbnRyaWVzLlxuICAgICAgICB3aGlsZSAoaS0tKSB7XG4gICAgICAgICAgICBpZiAodGhpcy5saXN0W2ldLmlkID09PSBlbGVtLmlkKSB7XG4gICAgICAgICAgICAgICAgaWR4ID0gaTtcbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIH1cbiAgICAgICAgfVxuXG4gICAgICAgIGlmIChpZHggPT09IC0xKSB7IC8vbm90IGNvbnRhaW5lZCBpbiBsaXN0XG4gICAgICAgICAgICB0aGlzLmFkZChlbGVtKTtcbiAgICAgICAgfSBlbHNlIGlmICghdGhpcy5maWx0KGVsZW0pKSB7XG4gICAgICAgICAgICB0aGlzLnJlbW92ZShlbGVtLmlkKTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGlmICh0aGlzLnNvcnRmdW4odGhpcy5saXN0W2lkeF0pICE9PSB0aGlzLnNvcnRmdW4oZWxlbSkpIHsgLy9zb3J0cG9zIGhhcyBjaGFuZ2VkXG4gICAgICAgICAgICAgICAgdGhpcy5yZW1vdmUodGhpcy5saXN0W2lkeF0pO1xuICAgICAgICAgICAgICAgIHRoaXMuYWRkKGVsZW0pO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICB0aGlzLmxpc3RbaWR4XSA9IGVsZW07XG4gICAgICAgICAgICAgICAgdGhpcy5lbWl0KFwidXBkYXRlXCIsIGVsZW0sIGlkeCk7XG4gICAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICB9LFxuICAgIHJlbW92ZTogZnVuY3Rpb24gKGVsZW1faWQpIHtcbiAgICAgICAgdmFyIGlkeCA9IHRoaXMubGlzdC5sZW5ndGg7XG4gICAgICAgIHdoaWxlIChpZHgtLSkge1xuICAgICAgICAgICAgaWYgKHRoaXMubGlzdFtpZHhdLmlkID09PSBlbGVtX2lkKSB7XG4gICAgICAgICAgICAgICAgdGhpcy5saXN0LnNwbGljZShpZHgsIDEpO1xuICAgICAgICAgICAgICAgIHRoaXMuZW1pdChcInJlbW92ZVwiLCBlbGVtX2lkLCBpZHgpO1xuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgfVxuICAgICAgICB9XG4gICAgfVxufSk7XG5cbm1vZHVsZS5leHBvcnRzID0ge1xuICAgIFN0b3JlVmlldzogU3RvcmVWaWV3XG59OyIsInZhciAkID0gcmVxdWlyZShcImpxdWVyeVwiKTtcblxuXG52YXIgS2V5ID0ge1xuICAgIFVQOiAzOCxcbiAgICBET1dOOiA0MCxcbiAgICBQQUdFX1VQOiAzMyxcbiAgICBQQUdFX0RPV046IDM0LFxuICAgIEhPTUU6IDM2LFxuICAgIEVORDogMzUsXG4gICAgTEVGVDogMzcsXG4gICAgUklHSFQ6IDM5LFxuICAgIEVOVEVSOiAxMyxcbiAgICBFU0M6IDI3LFxuICAgIFRBQjogOSxcbiAgICBTUEFDRTogMzIsXG4gICAgQkFDS1NQQUNFOiA4LFxufTtcbi8vIEFkZCBBLVpcbmZvciAodmFyIGkgPSA2NTsgaSA8PSA5MDsgaSsrKSB7XG4gICAgS2V5W1N0cmluZy5mcm9tQ2hhckNvZGUoaSldID0gaTtcbn1cblxuXG52YXIgZm9ybWF0U2l6ZSA9IGZ1bmN0aW9uIChieXRlcykge1xuICAgIHZhciBzaXplID0gYnl0ZXM7XG4gICAgdmFyIHByZWZpeCA9IFtcIkJcIiwgXCJLQlwiLCBcIk1CXCIsIFwiR0JcIiwgXCJUQlwiXTtcbiAgICB2YXIgaSA9IDA7XG4gICAgd2hpbGUgKE1hdGguYWJzKHNpemUpID49IDEwMjQgJiYgaSA8IHByZWZpeC5sZW5ndGggLSAxKSB7XG4gICAgICAgIGkrKztcbiAgICAgICAgc2l6ZSA9IHNpemUgLyAxMDI0O1xuICAgIH1cbiAgICByZXR1cm4gKE1hdGguZmxvb3Ioc2l6ZSAqIDEwMCkgLyAxMDAuMCkudG9GaXhlZCgyKSArIHByZWZpeFtpXTtcbn07XG5cblxudmFyIGZvcm1hdFRpbWVEZWx0YSA9IGZ1bmN0aW9uIChtaWxsaXNlY29uZHMpIHtcbiAgICB2YXIgdGltZSA9IG1pbGxpc2Vjb25kcztcbiAgICB2YXIgcHJlZml4ID0gW1wibXNcIiwgXCJzXCIsIFwibWluXCIsIFwiaFwiXTtcbiAgICB2YXIgZGl2ID0gWzEwMDAsIDYwLCA2MF07XG4gICAgdmFyIGkgPSAwO1xuICAgIHdoaWxlIChNYXRoLmFicyh0aW1lKSA+PSBkaXZbaV0gJiYgaSA8IGRpdi5sZW5ndGgpIHtcbiAgICAgICAgdGltZSA9IHRpbWUgLyBkaXZbaV07XG4gICAgICAgIGkrKztcbiAgICB9XG4gICAgcmV0dXJuIE1hdGgucm91bmQodGltZSkgKyBwcmVmaXhbaV07XG59O1xuXG5cbnZhciBmb3JtYXRUaW1lU3RhbXAgPSBmdW5jdGlvbiAoc2Vjb25kcykge1xuICAgIHZhciB0cyA9IChuZXcgRGF0ZShzZWNvbmRzICogMTAwMCkpLnRvSVNPU3RyaW5nKCk7XG4gICAgcmV0dXJuIHRzLnJlcGxhY2UoXCJUXCIsIFwiIFwiKS5yZXBsYWNlKFwiWlwiLCBcIlwiKTtcbn07XG5cblxuZnVuY3Rpb24gZ2V0Q29va2llKG5hbWUpIHtcbiAgICB2YXIgciA9IGRvY3VtZW50LmNvb2tpZS5tYXRjaChcIlxcXFxiXCIgKyBuYW1lICsgXCI9KFteO10qKVxcXFxiXCIpO1xuICAgIHJldHVybiByID8gclsxXSA6IHVuZGVmaW5lZDtcbn1cbnZhciB4c3JmID0gJC5wYXJhbSh7X3hzcmY6IGdldENvb2tpZShcIl94c3JmXCIpfSk7XG5cbi8vVG9ybmFkbyBYU1JGIFByb3RlY3Rpb24uXG4kLmFqYXhQcmVmaWx0ZXIoZnVuY3Rpb24gKG9wdGlvbnMpIHtcbiAgICBpZiAoW1wicG9zdFwiLCBcInB1dFwiLCBcImRlbGV0ZVwiXS5pbmRleE9mKG9wdGlvbnMudHlwZS50b0xvd2VyQ2FzZSgpKSA+PSAwICYmIG9wdGlvbnMudXJsWzBdID09PSBcIi9cIikge1xuICAgICAgICBpZiAob3B0aW9ucy5kYXRhKSB7XG4gICAgICAgICAgICBvcHRpb25zLmRhdGEgKz0gKFwiJlwiICsgeHNyZik7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBvcHRpb25zLmRhdGEgPSB4c3JmO1xuICAgICAgICB9XG4gICAgfVxufSk7XG4vLyBMb2cgQUpBWCBFcnJvcnNcbiQoZG9jdW1lbnQpLmFqYXhFcnJvcihmdW5jdGlvbiAoZXZlbnQsIGpxWEhSLCBhamF4U2V0dGluZ3MsIHRocm93bkVycm9yKSB7XG4gICAgdmFyIG1lc3NhZ2UgPSBqcVhIUi5yZXNwb25zZVRleHQ7XG4gICAgY29uc29sZS5lcnJvcihtZXNzYWdlLCBhcmd1bWVudHMpO1xuICAgIEV2ZW50TG9nQWN0aW9ucy5hZGRfZXZlbnQodGhyb3duRXJyb3IgKyBcIjogXCIgKyBtZXNzYWdlKTtcbiAgICB3aW5kb3cuYWxlcnQobWVzc2FnZSk7XG59KTtcblxubW9kdWxlLmV4cG9ydHMgPSB7XG4gICAgZm9ybWF0U2l6ZTogZm9ybWF0U2l6ZSxcbiAgICBmb3JtYXRUaW1lRGVsdGE6IGZvcm1hdFRpbWVEZWx0YSxcbiAgICBmb3JtYXRUaW1lU3RhbXA6IGZvcm1hdFRpbWVTdGFtcCxcbiAgICBLZXk6IEtleVxufTsiXX0=
