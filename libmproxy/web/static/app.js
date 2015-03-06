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



},{"./components/proxyapp.js":12,"./connection":14,"jquery":"jquery","react":"react","react-router":"react-router"}],4:[function(require,module,exports){
var React = require("react");
var ReactRouter = require("react-router");
var _ = require("lodash");

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

},{"lodash":"lodash","react":"react","react-router":"react-router"}],5:[function(require,module,exports){
var React = require("react");
var common = require("./common.js");
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
    mixins: [common.AutoScrollMixin, VirtualScrollMixin],
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

        view.addListener("add", this.onEventLogChange);
        view.addListener("recalculate", this.onEventLogChange);
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

},{"../store/view.js":19,"./common.js":4,"./virtualscroll.js":13,"react":"react"}],6:[function(require,module,exports){
var React = require("react");
var _ = require("lodash");

var common = require("./common.js");
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
    mixins: [common.StickyHeadMixin, common.Navigation, common.State],
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

},{"../actions.js":2,"../flow/utils.js":17,"../utils.js":20,"./common.js":4,"lodash":"lodash","react":"react"}],7:[function(require,module,exports){
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




},{"../flow/utils.js":17,"../utils.js":20,"react":"react"}],8:[function(require,module,exports){
var React = require("react");
var common = require("./common.js");
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
    mixins: [common.StickyHeadMixin, common.AutoScrollMixin, VirtualScrollMixin],
    getInitialState: function () {
        return {
            columns: flowtable_columns
        };
    },
    componentWillMount: function () {
        if (this.props.view) {
            this.props.view.addListener("add", this.onChange);
            this.props.view.addListener("update", this.onChange);
            this.props.view.addListener("remove", this.onChange);
            this.props.view.addListener("recalculate", this.onChange);
        }
    },
    componentWillReceiveProps: function (nextProps) {
        if (nextProps.view !== this.props.view) {
            if (this.props.view) {
                this.props.view.removeListener("add");
                this.props.view.removeListener("update");
                this.props.view.removeListener("remove");
                this.props.view.removeListener("recalculate");
            }
            nextProps.view.addListener("add", this.onChange);
            nextProps.view.addListener("update", this.onChange);
            nextProps.view.addListener("remove", this.onChange);
            nextProps.view.addListener("recalculate", this.onChange);
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


},{"./common.js":4,"./flowtable-columns.js":7,"./virtualscroll.js":13,"react":"react"}],9:[function(require,module,exports){
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

},{"react":"react"}],10:[function(require,module,exports){
var React = require("react");
var $ = require("jquery");

var Filt = require("../filt/filt.js");
var utils = require("../utils.js");

var common = require("./common.js");
var actions = require("../actions.js");

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
        if (e.keyCode === utils.Key.ESC || e.keyCode === utils.Key.ENTER) {
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
    mixins: [common.Navigation, common.State],
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
    mixins: [common.Navigation, common.State],
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
            actions.FlowActions.clear();
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
                React.createElement("a", {href: "#", className: "special", onClick: this.handleFileClick}, " mitmproxy "), 
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
    mixins: [common.Navigation],
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

},{"../actions.js":2,"../filt/filt.js":16,"../utils.js":20,"./common.js":4,"jquery":"jquery","react":"react"}],11:[function(require,module,exports){
var React = require("react");

var common = require("./common.js");
var actions = require("../actions.js");
var toputils = require("../utils.js");
var views = require("../store/view.js");
var Filt = require("../filt/filt.js");
FlowTable = require("./flowtable.js");
var flowdetail = require("./flowdetail.js");


var MainView = React.createClass({displayName: "MainView",
    mixins: [common.Navigation, common.State],
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
        view.addListener("add", this.onUpdate);
        view.addListener("update", this.onUpdate);
        view.addListener("remove", this.onUpdate);
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
                    actions.FlowActions.clear();
                }
                break;
            case toputils.Key.D:
                if (flow) {
                    if (e.shiftKey) {
                        actions.FlowActions.duplicate(flow);
                    } else {
                        actions.FlowActions.delete(flow);
                    }
                }
                break;
            case toputils.Key.A:
                if (e.shiftKey) {
                    actions.FlowActions.accept_all();
                } else if (flow && flow.intercepted) {
                    actions.FlowActions.accept(flow);
                }
                break;
            case toputils.Key.R:
                if (!e.shiftKey && flow) {
                    actions.FlowActions.replay(flow);
                }
                break;
            case toputils.Key.V:
                if(e.shiftKey && flow && flow.modified) {
                    actions.FlowActions.revert(flow);
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
                React.createElement(common.Splitter, {key: "splitter"}),
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


},{"../actions.js":2,"../filt/filt.js":16,"../store/view.js":19,"../utils.js":20,"./common.js":4,"./flowdetail.js":6,"./flowtable.js":8,"react":"react"}],12:[function(require,module,exports){
var React = require("react");
var ReactRouter = require("react-router");
var _ = require("lodash");

var common = require("./common.js");
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
    mixins: [common.State],
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
                React.createElement(common.Splitter, {key: "splitter", axis: "y"}),
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



},{"../store/store.js":18,"./common.js":4,"./eventlog.js":5,"./footer.js":9,"./header.js":10,"./mainview.js":11,"lodash":"lodash","react":"react","react-router":"react-router"}],13:[function(require,module,exports){
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

var flux = require("flux");

const PayloadSources = {
    VIEW: "view",
    SERVER: "server"
};


AppDispatcher = new flux.Dispatcher();
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

},{"flux":"flux"}],16:[function(require,module,exports){
module.exports = (function() {
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


    var flowutils = require("../flow/utils.js");

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
            var ct = flowutils.ResponseUtils.getContentType(flow.response);
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
                (flow.request && flowutils.RequestUtils.match_header(flow.request, regex))
                ||
                (flow.response && flowutils.ResponseUtils.match_header(flow.response, regex))
            );
        }
        headerFilter.desc = "header matches " + regex;
        return headerFilter;
    }
    function requestHeader(regex){
        regex = new RegExp(regex, "i");
        function requestHeaderFilter(flow){
            return (flow.request && flowutils.RequestUtils.match_header(flow.request, regex));
        }
        requestHeaderFilter.desc = "req. header matches " + regex;
        return requestHeaderFilter;
    }
    function responseHeader(regex){
        regex = new RegExp(regex, "i");
        function responseHeaderFilter(flow){
            return (flow.response && flowutils.ResponseUtils.match_header(flow.response, regex));
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
                (flow.request && regex.test(flowutils.RequestUtils.getContentType(flow.request)))
                ||
                (flow.response && regex.test(flowutils.ResponseUtils.getContentType(flow.response)))
            );
        }
        contentTypeFilter.desc = "content type matches " + regex;
        return contentTypeFilter;
    }
    function requestContentType(regex){
        regex = new RegExp(regex, "i");
        function requestContentTypeFilter(flow){
            return flow.request && regex.test(flowutils.RequestUtils.getContentType(flow.request));
        }
        requestContentTypeFilter.desc = "req. content type matches " + regex;
        return requestContentTypeFilter;
    }
    function responseContentType(regex){
        regex = new RegExp(regex, "i");
        function responseContentTypeFilter(flow){
            return flow.response && regex.test(flowutils.ResponseUtils.getContentType(flow.response));
        }
        responseContentTypeFilter.desc = "resp. content type matches " + regex;
        return responseContentTypeFilter;
    }
    function url(regex){
        regex = new RegExp(regex, "i");
        function urlFilter(flow){
            return flow.request && regex.test(flowutils.RequestUtils.pretty_url(flow.request));
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

},{"../flow/utils.js":17}],17:[function(require,module,exports){
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
    if (bytes === 0)
        return "0";
    var prefix = ["b", "kb", "mb", "gb", "tb"];
    for (var i = 0; i < prefix.length; i++){
        if (Math.pow(1024, i + 1) > bytes){
            break;
        }
    }
    var precision;
    if (bytes%Math.pow(1024, i) === 0)
        precision = 0;
    else
        precision = 1;
    return (bytes/Math.pow(1024, i)).toFixed(precision) + prefix[i];
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIm5vZGVfbW9kdWxlc1xcYnJvd3NlcmlmeVxcbm9kZV9tb2R1bGVzXFxicm93c2VyLXBhY2tcXF9wcmVsdWRlLmpzIiwibm9kZV9tb2R1bGVzXFxicm93c2VyaWZ5XFxub2RlX21vZHVsZXNcXGV2ZW50c1xcZXZlbnRzLmpzIiwiQzpcXFVzZXJzXFx1c2VyXFxnaXRcXG1pdG1wcm94eVxcd2ViXFxzcmNcXGpzXFxhY3Rpb25zLmpzIiwiQzpcXFVzZXJzXFx1c2VyXFxnaXRcXG1pdG1wcm94eVxcd2ViXFxzcmNcXGpzXFxhcHAuanMiLCJDOlxcVXNlcnNcXHVzZXJcXGdpdFxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGNvbXBvbmVudHNcXGNvbW1vbi5qcyIsIkM6XFxVc2Vyc1xcdXNlclxcZ2l0XFxtaXRtcHJveHlcXHdlYlxcc3JjXFxqc1xcY29tcG9uZW50c1xcZXZlbnRsb2cuanMiLCJDOlxcVXNlcnNcXHVzZXJcXGdpdFxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGNvbXBvbmVudHNcXGZsb3dkZXRhaWwuanMiLCJDOlxcVXNlcnNcXHVzZXJcXGdpdFxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGNvbXBvbmVudHNcXGZsb3d0YWJsZS1jb2x1bW5zLmpzIiwiQzpcXFVzZXJzXFx1c2VyXFxnaXRcXG1pdG1wcm94eVxcd2ViXFxzcmNcXGpzXFxjb21wb25lbnRzXFxmbG93dGFibGUuanMiLCJDOlxcVXNlcnNcXHVzZXJcXGdpdFxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGNvbXBvbmVudHNcXGZvb3Rlci5qcyIsIkM6XFxVc2Vyc1xcdXNlclxcZ2l0XFxtaXRtcHJveHlcXHdlYlxcc3JjXFxqc1xcY29tcG9uZW50c1xcaGVhZGVyLmpzIiwiQzpcXFVzZXJzXFx1c2VyXFxnaXRcXG1pdG1wcm94eVxcd2ViXFxzcmNcXGpzXFxjb21wb25lbnRzXFxtYWludmlldy5qcyIsIkM6XFxVc2Vyc1xcdXNlclxcZ2l0XFxtaXRtcHJveHlcXHdlYlxcc3JjXFxqc1xcY29tcG9uZW50c1xccHJveHlhcHAuanMiLCJDOlxcVXNlcnNcXHVzZXJcXGdpdFxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGNvbXBvbmVudHNcXHZpcnR1YWxzY3JvbGwuanMiLCJDOlxcVXNlcnNcXHVzZXJcXGdpdFxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGNvbm5lY3Rpb24uanMiLCJDOlxcVXNlcnNcXHVzZXJcXGdpdFxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGRpc3BhdGNoZXIuanMiLCJDOlxcVXNlcnNcXHVzZXJcXGdpdFxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGZpbHRcXGZpbHQuanMiLCJDOlxcVXNlcnNcXHVzZXJcXGdpdFxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGZsb3dcXHV0aWxzLmpzIiwiQzpcXFVzZXJzXFx1c2VyXFxnaXRcXG1pdG1wcm94eVxcd2ViXFxzcmNcXGpzXFxzdG9yZVxcc3RvcmUuanMiLCJDOlxcVXNlcnNcXHVzZXJcXGdpdFxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXHN0b3JlXFx2aWV3LmpzIiwiQzpcXFVzZXJzXFx1c2VyXFxnaXRcXG1pdG1wcm94eVxcd2ViXFxzcmNcXGpzXFx1dGlscy5qcyJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFBQTtBQ0FBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDN1NBLElBQUksQ0FBQyxHQUFHLE9BQU8sQ0FBQyxRQUFRLENBQUMsQ0FBQzs7QUFFMUIsSUFBSSxXQUFXLEdBQUc7O0lBRWQsZUFBZSxFQUFFLGlCQUFpQjtJQUNsQyxnQkFBZ0IsRUFBRSxrQkFBa0I7QUFDeEMsSUFBSSxnQkFBZ0IsRUFBRSxrQkFBa0I7QUFDeEM7O0lBRUksY0FBYyxFQUFFLFVBQVU7SUFDMUIsV0FBVyxFQUFFLFFBQVE7SUFDckIsVUFBVSxFQUFFLE9BQU87QUFDdkIsQ0FBQyxDQUFDOztBQUVGLElBQUksU0FBUyxHQUFHO0lBQ1osR0FBRyxFQUFFLEtBQUs7SUFDVixNQUFNLEVBQUUsUUFBUTtJQUNoQixNQUFNLEVBQUUsUUFBUTtJQUNoQixLQUFLLEVBQUUsT0FBTztBQUNsQixDQUFDLENBQUM7O0FBRUYsSUFBSSxpQkFBaUIsR0FBRztJQUNwQixJQUFJLEVBQUUsWUFBWTtRQUNkLGFBQWEsQ0FBQyxrQkFBa0IsQ0FBQztZQUM3QixJQUFJLEVBQUUsV0FBVyxDQUFDLGVBQWU7U0FDcEMsQ0FBQyxDQUFDO0tBQ047SUFDRCxLQUFLLEVBQUUsWUFBWTtRQUNmLGFBQWEsQ0FBQyxrQkFBa0IsQ0FBQztZQUM3QixJQUFJLEVBQUUsV0FBVyxDQUFDLGdCQUFnQjtTQUNyQyxDQUFDLENBQUM7S0FDTjtJQUNELEtBQUssRUFBRSxZQUFZO1FBQ2YsYUFBYSxDQUFDLGtCQUFrQixDQUFDO1lBQzdCLElBQUksRUFBRSxXQUFXLENBQUMsZ0JBQWdCO1NBQ3JDLENBQUMsQ0FBQztLQUNOO0FBQ0wsQ0FBQyxDQUFDOztBQUVGLElBQUksZUFBZSxHQUFHO0FBQ3RCLElBQUksTUFBTSxFQUFFLFVBQVUsUUFBUSxFQUFFOztRQUV4QixDQUFDLENBQUMsSUFBSSxDQUFDO1lBQ0gsSUFBSSxFQUFFLEtBQUs7WUFDWCxHQUFHLEVBQUUsV0FBVztZQUNoQixJQUFJLEVBQUUsUUFBUTtBQUMxQixTQUFTLENBQUMsQ0FBQztBQUNYO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0tBRUs7QUFDTCxDQUFDLENBQUM7O0FBRUYsSUFBSSx3QkFBd0IsR0FBRyxDQUFDLENBQUM7QUFDakMsSUFBSSxlQUFlLEdBQUc7SUFDbEIsU0FBUyxFQUFFLFVBQVUsT0FBTyxFQUFFO1FBQzFCLGFBQWEsQ0FBQyxrQkFBa0IsQ0FBQztZQUM3QixJQUFJLEVBQUUsV0FBVyxDQUFDLFdBQVc7WUFDN0IsR0FBRyxFQUFFLFNBQVMsQ0FBQyxHQUFHO1lBQ2xCLElBQUksRUFBRTtnQkFDRixPQUFPLEVBQUUsT0FBTztnQkFDaEIsS0FBSyxFQUFFLEtBQUs7Z0JBQ1osRUFBRSxFQUFFLGFBQWEsR0FBRyx3QkFBd0IsRUFBRTthQUNqRDtTQUNKLENBQUMsQ0FBQztLQUNOO0FBQ0wsQ0FBQyxDQUFDOztBQUVGLElBQUksV0FBVyxHQUFHO0lBQ2QsTUFBTSxFQUFFLFVBQVUsSUFBSSxFQUFFO1FBQ3BCLENBQUMsQ0FBQyxJQUFJLENBQUMsU0FBUyxHQUFHLElBQUksQ0FBQyxFQUFFLEdBQUcsU0FBUyxDQUFDLENBQUM7S0FDM0M7SUFDRCxVQUFVLEVBQUUsVUFBVTtRQUNsQixDQUFDLENBQUMsSUFBSSxDQUFDLGVBQWUsQ0FBQyxDQUFDO0tBQzNCO0lBQ0QsUUFBUSxFQUFFLFNBQVMsSUFBSSxDQUFDO1FBQ3BCLENBQUMsQ0FBQyxJQUFJLENBQUM7WUFDSCxJQUFJLENBQUMsUUFBUTtZQUNiLEdBQUcsRUFBRSxTQUFTLEdBQUcsSUFBSSxDQUFDLEVBQUU7U0FDM0IsQ0FBQyxDQUFDO0tBQ047SUFDRCxTQUFTLEVBQUUsU0FBUyxJQUFJLENBQUM7UUFDckIsQ0FBQyxDQUFDLElBQUksQ0FBQyxTQUFTLEdBQUcsSUFBSSxDQUFDLEVBQUUsR0FBRyxZQUFZLENBQUMsQ0FBQztLQUM5QztJQUNELE1BQU0sRUFBRSxTQUFTLElBQUksQ0FBQztRQUNsQixDQUFDLENBQUMsSUFBSSxDQUFDLFNBQVMsR0FBRyxJQUFJLENBQUMsRUFBRSxHQUFHLFNBQVMsQ0FBQyxDQUFDO0tBQzNDO0lBQ0QsTUFBTSxFQUFFLFNBQVMsSUFBSSxDQUFDO1FBQ2xCLENBQUMsQ0FBQyxJQUFJLENBQUMsU0FBUyxHQUFHLElBQUksQ0FBQyxFQUFFLEdBQUcsU0FBUyxDQUFDLENBQUM7S0FDM0M7SUFDRCxNQUFNLEVBQUUsVUFBVSxJQUFJLEVBQUU7UUFDcEIsYUFBYSxDQUFDLGtCQUFrQixDQUFDO1lBQzdCLElBQUksRUFBRSxXQUFXLENBQUMsVUFBVTtZQUM1QixHQUFHLEVBQUUsU0FBUyxDQUFDLE1BQU07WUFDckIsSUFBSSxFQUFFLElBQUk7U0FDYixDQUFDLENBQUM7S0FDTjtJQUNELEtBQUssRUFBRSxVQUFVO1FBQ2IsQ0FBQyxDQUFDLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQztLQUNwQjtBQUNMLENBQUMsQ0FBQzs7QUFFRixLQUFLLEdBQUc7SUFDSixNQUFNLEVBQUUsR0FBRztJQUNYLFNBQVMsRUFBRSxHQUFHO0lBQ2QsYUFBYSxFQUFFLEdBQUc7QUFDdEIsQ0FBQyxDQUFDOztBQUVGLE1BQU0sQ0FBQyxPQUFPLEdBQUc7SUFDYixXQUFXLEVBQUUsV0FBVztJQUN4QixpQkFBaUIsRUFBRSxpQkFBaUI7SUFDcEMsV0FBVyxFQUFFLFdBQVc7SUFDeEIsU0FBUyxFQUFFLFNBQVM7Q0FDdkI7OztBQ3ZIRDtBQUNBLElBQUksS0FBSyxHQUFHLE9BQU8sQ0FBQyxPQUFPLENBQUMsQ0FBQztBQUM3QixJQUFJLFdBQVcsR0FBRyxPQUFPLENBQUMsY0FBYyxDQUFDLENBQUM7QUFDMUMsSUFBSSxDQUFDLEdBQUcsT0FBTyxDQUFDLFFBQVEsQ0FBQyxDQUFDOztBQUUxQixJQUFJLFVBQVUsR0FBRyxPQUFPLENBQUMsY0FBYyxDQUFDLENBQUM7QUFDekMsSUFBSSxRQUFRLEdBQUcsT0FBTyxDQUFDLDBCQUEwQixDQUFDLENBQUM7O0FBRW5ELENBQUMsQ0FBQyxZQUFZO0FBQ2QsSUFBSSxNQUFNLENBQUMsRUFBRSxHQUFHLElBQUksVUFBVSxDQUFDLFVBQVUsQ0FBQyxDQUFDOztJQUV2QyxXQUFXLENBQUMsR0FBRyxDQUFDLFFBQVEsQ0FBQyxNQUFNLEVBQUUsVUFBVSxPQUFPLEVBQUU7UUFDaEQsS0FBSyxDQUFDLE1BQU0sQ0FBQyxvQkFBQyxPQUFPLEVBQUEsSUFBRSxDQUFBLEVBQUUsUUFBUSxDQUFDLElBQUksQ0FBQyxDQUFDO0tBQzNDLENBQUMsQ0FBQztBQUNQLENBQUMsQ0FBQyxDQUFDOzs7OztBQ2RILElBQUksS0FBSyxHQUFHLE9BQU8sQ0FBQyxPQUFPLENBQUMsQ0FBQztBQUM3QixJQUFJLFdBQVcsR0FBRyxPQUFPLENBQUMsY0FBYyxDQUFDLENBQUM7QUFDMUMsSUFBSSxDQUFDLEdBQUcsT0FBTyxDQUFDLFFBQVEsQ0FBQyxDQUFDOztBQUUxQix3R0FBd0c7QUFDeEcsSUFBSSxlQUFlLEdBQUc7SUFDbEIsbUJBQW1CLEVBQUUsWUFBWTtRQUM3QixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsVUFBVSxFQUFFLENBQUM7UUFDN0IsSUFBSSxDQUFDLG1CQUFtQjtZQUNwQixJQUFJLENBQUMsU0FBUyxLQUFLLENBQUM7WUFDcEIsSUFBSSxDQUFDLFNBQVMsR0FBRyxJQUFJLENBQUMsWUFBWSxLQUFLLElBQUksQ0FBQyxZQUFZO1NBQzNELENBQUM7S0FDTDtJQUNELGtCQUFrQixFQUFFLFlBQVk7UUFDNUIsSUFBSSxJQUFJLENBQUMsbUJBQW1CLEVBQUU7WUFDMUIsSUFBSSxJQUFJLEdBQUcsSUFBSSxDQUFDLFVBQVUsRUFBRSxDQUFDO1lBQzdCLElBQUksQ0FBQyxTQUFTLEdBQUcsSUFBSSxDQUFDLFlBQVksQ0FBQztTQUN0QztLQUNKO0FBQ0wsQ0FBQyxDQUFDO0FBQ0Y7O0FBRUEsSUFBSSxlQUFlLEdBQUc7QUFDdEIsSUFBSSxVQUFVLEVBQUUsWUFBWTtBQUM1Qjs7UUFFUSxJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxVQUFVLEVBQUUsQ0FBQztRQUN2QyxJQUFJLENBQUMsS0FBSyxDQUFDLFNBQVMsR0FBRyxjQUFjLEdBQUcsSUFBSSxDQUFDLFVBQVUsRUFBRSxDQUFDLFNBQVMsR0FBRyxLQUFLLENBQUM7S0FDL0U7QUFDTCxDQUFDLENBQUM7QUFDRjs7QUFFQSxJQUFJLFVBQVUsR0FBRyxDQUFDLENBQUMsTUFBTSxDQUFDLEVBQUUsRUFBRSxXQUFXLENBQUMsVUFBVSxFQUFFO0lBQ2xELFFBQVEsRUFBRSxVQUFVLElBQUksRUFBRTtRQUN0QixJQUFJLENBQUMsR0FBRyxJQUFJLENBQUMsT0FBTyxDQUFDLGVBQWUsRUFBRSxDQUFDO1FBQ3ZDLElBQUksSUFBSSxDQUFDLElBQUksSUFBSSxDQUFDO1lBQ2QsR0FBRyxJQUFJLENBQUMsY0FBYyxDQUFDLENBQUMsQ0FBQyxDQUFDO2dCQUN0QixDQUFDLENBQUMsQ0FBQyxDQUFDLEdBQUcsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLFNBQVMsQ0FBQzthQUMvQjtTQUNKO1FBQ0QsQ0FBQyxDQUFDLENBQUMsR0FBRyxHQUFHLENBQUM7UUFDVixJQUFJLENBQUMsV0FBVyxDQUFDLElBQUksQ0FBQyxPQUFPLENBQUMsY0FBYyxFQUFFLEVBQUUsSUFBSSxDQUFDLE9BQU8sQ0FBQyxnQkFBZ0IsRUFBRSxFQUFFLENBQUMsQ0FBQyxDQUFDO0tBQ3ZGO0lBQ0QsV0FBVyxFQUFFLFNBQVMsZUFBZSxFQUFFLE1BQU0sRUFBRSxLQUFLLEVBQUU7UUFDbEQsR0FBRyxlQUFlLEtBQUssU0FBUyxDQUFDO1lBQzdCLGVBQWUsR0FBRyxJQUFJLENBQUMsT0FBTyxDQUFDLGNBQWMsRUFBRSxDQUFDO1NBQ25EO1FBQ0QsR0FBRyxNQUFNLEtBQUssU0FBUyxDQUFDO1lBQ3BCLE1BQU0sR0FBRyxJQUFJLENBQUMsT0FBTyxDQUFDLGdCQUFnQixFQUFFLENBQUM7U0FDNUM7UUFDRCxHQUFHLEtBQUssS0FBSyxTQUFTLENBQUM7WUFDbkIsS0FBSyxHQUFHLElBQUksQ0FBQyxPQUFPLENBQUMsZUFBZSxFQUFFLENBQUM7U0FDMUM7UUFDRCxXQUFXLENBQUMsVUFBVSxDQUFDLFdBQVcsQ0FBQyxJQUFJLENBQUMsSUFBSSxFQUFFLGVBQWUsRUFBRSxNQUFNLEVBQUUsS0FBSyxDQUFDLENBQUM7S0FDakY7Q0FDSixDQUFDLENBQUM7QUFDSCxDQUFDLENBQUMsTUFBTSxDQUFDLFVBQVUsQ0FBQyxZQUFZLEVBQUUsV0FBVyxDQUFDLEtBQUssQ0FBQyxZQUFZLENBQUMsQ0FBQzs7QUFFbEUsSUFBSSxLQUFLLEdBQUcsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxFQUFFLEVBQUUsV0FBVyxDQUFDLEtBQUssRUFBRTtJQUN4QyxlQUFlLEVBQUUsWUFBWTtRQUN6QixJQUFJLENBQUMsTUFBTSxHQUFHLElBQUksQ0FBQyxPQUFPLENBQUMsZUFBZSxFQUFFLENBQUM7UUFDN0MsSUFBSSxDQUFDLGFBQWEsR0FBRyxFQUFFLENBQUM7UUFDeEIsT0FBTyxJQUFJLENBQUM7S0FDZjtJQUNELGFBQWEsRUFBRSxVQUFVLEdBQUcsRUFBRSxRQUFRLEVBQUU7UUFDcEMsSUFBSSxDQUFDLGFBQWEsQ0FBQyxJQUFJLENBQUM7WUFDcEIsR0FBRyxFQUFFLEdBQUc7WUFDUixRQUFRLEVBQUUsUUFBUTtTQUNyQixDQUFDLENBQUM7S0FDTjtJQUNELHlCQUF5QixFQUFFLFVBQVUsU0FBUyxFQUFFLFNBQVMsRUFBRTtRQUN2RCxJQUFJLENBQUMsR0FBRyxJQUFJLENBQUMsT0FBTyxDQUFDLGVBQWUsRUFBRSxDQUFDO1FBQ3ZDLEtBQUssSUFBSSxDQUFDLEdBQUcsQ0FBQyxFQUFFLENBQUMsR0FBRyxJQUFJLENBQUMsYUFBYSxDQUFDLE1BQU0sRUFBRSxDQUFDLEVBQUUsRUFBRTtZQUNoRCxJQUFJLEtBQUssR0FBRyxJQUFJLENBQUMsYUFBYSxDQUFDLENBQUMsQ0FBQyxDQUFDO1lBQ2xDLElBQUksSUFBSSxDQUFDLE1BQU0sQ0FBQyxLQUFLLENBQUMsR0FBRyxDQUFDLEtBQUssQ0FBQyxDQUFDLEtBQUssQ0FBQyxHQUFHLENBQUMsRUFBRTtnQkFDekMsS0FBSyxDQUFDLFFBQVEsQ0FBQyxJQUFJLENBQUMsTUFBTSxDQUFDLEtBQUssQ0FBQyxHQUFHLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLEdBQUcsQ0FBQyxFQUFFLEtBQUssQ0FBQyxHQUFHLENBQUMsQ0FBQzthQUNuRTtTQUNKO1FBQ0QsSUFBSSxDQUFDLE1BQU0sR0FBRyxDQUFDLENBQUM7S0FDbkI7QUFDTCxDQUFDLENBQUMsQ0FBQzs7QUFFSCxJQUFJLDhCQUE4Qix3QkFBQTtJQUM5QixlQUFlLEVBQUUsWUFBWTtRQUN6QixPQUFPO1lBQ0gsSUFBSSxFQUFFLEdBQUc7U0FDWixDQUFDO0tBQ0w7SUFDRCxlQUFlLEVBQUUsWUFBWTtRQUN6QixPQUFPO1lBQ0gsT0FBTyxFQUFFLEtBQUs7WUFDZCxNQUFNLEVBQUUsS0FBSztZQUNiLE1BQU0sRUFBRSxLQUFLO1NBQ2hCLENBQUM7S0FDTDtJQUNELFdBQVcsRUFBRSxVQUFVLENBQUMsRUFBRTtRQUN0QixJQUFJLENBQUMsUUFBUSxDQUFDO1lBQ1YsTUFBTSxFQUFFLENBQUMsQ0FBQyxLQUFLO1lBQ2YsTUFBTSxFQUFFLENBQUMsQ0FBQyxLQUFLO1NBQ2xCLENBQUMsQ0FBQztRQUNILE1BQU0sQ0FBQyxnQkFBZ0IsQ0FBQyxXQUFXLEVBQUUsSUFBSSxDQUFDLFdBQVcsQ0FBQyxDQUFDO0FBQy9ELFFBQVEsTUFBTSxDQUFDLGdCQUFnQixDQUFDLFNBQVMsRUFBRSxJQUFJLENBQUMsU0FBUyxDQUFDLENBQUM7O1FBRW5ELE1BQU0sQ0FBQyxnQkFBZ0IsQ0FBQyxTQUFTLEVBQUUsSUFBSSxDQUFDLFNBQVMsQ0FBQyxDQUFDO0tBQ3REO0lBQ0QsU0FBUyxFQUFFLFlBQVk7UUFDbkIsSUFBSSxDQUFDLFVBQVUsRUFBRSxDQUFDLEtBQUssQ0FBQyxTQUFTLEdBQUcsRUFBRSxDQUFDO1FBQ3ZDLE1BQU0sQ0FBQyxtQkFBbUIsQ0FBQyxTQUFTLEVBQUUsSUFBSSxDQUFDLFNBQVMsQ0FBQyxDQUFDO1FBQ3RELE1BQU0sQ0FBQyxtQkFBbUIsQ0FBQyxTQUFTLEVBQUUsSUFBSSxDQUFDLFNBQVMsQ0FBQyxDQUFDO1FBQ3RELE1BQU0sQ0FBQyxtQkFBbUIsQ0FBQyxXQUFXLEVBQUUsSUFBSSxDQUFDLFdBQVcsQ0FBQyxDQUFDO0tBQzdEO0lBQ0QsU0FBUyxFQUFFLFVBQVUsQ0FBQyxFQUFFO0FBQzVCLFFBQVEsSUFBSSxDQUFDLFNBQVMsRUFBRSxDQUFDOztRQUVqQixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsVUFBVSxFQUFFLENBQUM7UUFDN0IsSUFBSSxJQUFJLEdBQUcsSUFBSSxDQUFDLHNCQUFzQixDQUFDO0FBQy9DLFFBQVEsSUFBSSxJQUFJLEdBQUcsSUFBSSxDQUFDLGtCQUFrQixDQUFDOztRQUVuQyxJQUFJLEVBQUUsR0FBRyxDQUFDLENBQUMsS0FBSyxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDO1FBQ3JDLElBQUksRUFBRSxHQUFHLENBQUMsQ0FBQyxLQUFLLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUM7UUFDckMsSUFBSSxTQUFTLENBQUM7UUFDZCxJQUFJLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxLQUFLLEdBQUcsRUFBRTtZQUN6QixTQUFTLEdBQUcsSUFBSSxDQUFDLFdBQVcsR0FBRyxFQUFFLENBQUM7U0FDckMsTUFBTTtZQUNILFNBQVMsR0FBRyxJQUFJLENBQUMsWUFBWSxHQUFHLEVBQUUsQ0FBQztBQUMvQyxTQUFTOztRQUVELElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxHQUFHLE1BQU0sR0FBRyxJQUFJLENBQUMsR0FBRyxDQUFDLENBQUMsRUFBRSxTQUFTLENBQUMsR0FBRyxJQUFJLENBQUM7QUFDakUsUUFBUSxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksR0FBRyxVQUFVLENBQUM7O1FBRTdCLElBQUksQ0FBQyxRQUFRLENBQUM7WUFDVixPQUFPLEVBQUUsSUFBSTtTQUNoQixDQUFDLENBQUM7UUFDSCxJQUFJLENBQUMsUUFBUSxFQUFFLENBQUM7S0FDbkI7SUFDRCxXQUFXLEVBQUUsVUFBVSxDQUFDLEVBQUU7UUFDdEIsSUFBSSxFQUFFLEdBQUcsQ0FBQyxFQUFFLEVBQUUsR0FBRyxDQUFDLENBQUM7UUFDbkIsSUFBSSxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksS0FBSyxHQUFHLEVBQUU7WUFDekIsRUFBRSxHQUFHLENBQUMsQ0FBQyxLQUFLLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUM7U0FDcEMsTUFBTTtZQUNILEVBQUUsR0FBRyxDQUFDLENBQUMsS0FBSyxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDO1NBQ3BDO1FBQ0QsSUFBSSxDQUFDLFVBQVUsRUFBRSxDQUFDLEtBQUssQ0FBQyxTQUFTLEdBQUcsWUFBWSxHQUFHLEVBQUUsR0FBRyxLQUFLLEdBQUcsRUFBRSxHQUFHLEtBQUssQ0FBQztLQUM5RTtBQUNMLElBQUksUUFBUSxFQUFFLFlBQVk7QUFDMUI7O1FBRVEsTUFBTSxDQUFDLFVBQVUsQ0FBQyxZQUFZO1lBQzFCLE1BQU0sQ0FBQyxhQUFhLENBQUMsSUFBSSxXQUFXLENBQUMsUUFBUSxDQUFDLENBQUMsQ0FBQztTQUNuRCxFQUFFLENBQUMsQ0FBQyxDQUFDO0tBQ1Q7SUFDRCxLQUFLLEVBQUUsVUFBVSxXQUFXLEVBQUU7UUFDMUIsSUFBSSxDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsT0FBTyxFQUFFO1lBQ3JCLE9BQU87U0FDVjtRQUNELElBQUksSUFBSSxHQUFHLElBQUksQ0FBQyxVQUFVLEVBQUUsQ0FBQztRQUM3QixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsc0JBQXNCLENBQUM7QUFDL0MsUUFBUSxJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsa0JBQWtCLENBQUM7O1FBRW5DLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxHQUFHLEVBQUUsQ0FBQztBQUM3QixRQUFRLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxHQUFHLEVBQUUsQ0FBQzs7UUFFckIsSUFBSSxDQUFDLFdBQVcsRUFBRTtZQUNkLElBQUksQ0FBQyxRQUFRLENBQUM7Z0JBQ1YsT0FBTyxFQUFFLEtBQUs7YUFDakIsQ0FBQyxDQUFDO1NBQ047UUFDRCxJQUFJLENBQUMsUUFBUSxFQUFFLENBQUM7S0FDbkI7SUFDRCxvQkFBb0IsRUFBRSxZQUFZO1FBQzlCLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLENBQUM7S0FDcEI7SUFDRCxNQUFNLEVBQUUsWUFBWTtRQUNoQixJQUFJLFNBQVMsR0FBRyxVQUFVLENBQUM7UUFDM0IsSUFBSSxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksS0FBSyxHQUFHLEVBQUU7WUFDekIsU0FBUyxJQUFJLGFBQWEsQ0FBQztTQUM5QixNQUFNO1lBQ0gsU0FBUyxJQUFJLGFBQWEsQ0FBQztTQUM5QjtRQUNEO1lBQ0ksb0JBQUEsS0FBSSxFQUFBLENBQUEsQ0FBQyxTQUFBLEVBQVMsQ0FBRSxTQUFXLENBQUEsRUFBQTtnQkFDdkIsb0JBQUEsS0FBSSxFQUFBLENBQUEsQ0FBQyxXQUFBLEVBQVcsQ0FBRSxJQUFJLENBQUMsV0FBVyxFQUFDLENBQUMsU0FBQSxFQUFTLENBQUMsTUFBTyxDQUFNLENBQUE7WUFDekQsQ0FBQTtVQUNSO0tBQ0w7QUFDTCxDQUFDLENBQUMsQ0FBQzs7QUFFSCxNQUFNLENBQUMsT0FBTyxHQUFHO0lBQ2IsS0FBSyxFQUFFLEtBQUs7SUFDWixVQUFVLEVBQUUsVUFBVTtJQUN0QixlQUFlLEVBQUUsZUFBZTtJQUNoQyxlQUFlLEVBQUUsZUFBZTtJQUNoQyxRQUFRLEVBQUUsUUFBUTs7OztBQ2hNdEIsSUFBSSxLQUFLLEdBQUcsT0FBTyxDQUFDLE9BQU8sQ0FBQyxDQUFDO0FBQzdCLElBQUksTUFBTSxHQUFHLE9BQU8sQ0FBQyxhQUFhLENBQUMsQ0FBQztBQUNwQyxJQUFJLGtCQUFrQixHQUFHLE9BQU8sQ0FBQyxvQkFBb0IsQ0FBQyxDQUFDO0FBQ3ZELElBQUksS0FBSyxHQUFHLE9BQU8sQ0FBQyxrQkFBa0IsQ0FBQyxDQUFDOztBQUV4QyxJQUFJLGdDQUFnQywwQkFBQTtJQUNoQyxNQUFNLEVBQUUsWUFBWTtRQUNoQixJQUFJLEtBQUssR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLEtBQUssQ0FBQztRQUM3QixJQUFJLFNBQVMsQ0FBQztRQUNkLFFBQVEsS0FBSyxDQUFDLEtBQUs7WUFDZixLQUFLLEtBQUs7Z0JBQ04sU0FBUyxHQUFHLG9CQUFBLEdBQUUsRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMsbUJBQW9CLENBQUksQ0FBQSxDQUFDO2dCQUNsRCxNQUFNO1lBQ1YsS0FBSyxPQUFPO2dCQUNSLFNBQVMsR0FBRyxvQkFBQSxHQUFFLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLGlCQUFrQixDQUFJLENBQUEsQ0FBQztnQkFDaEQsTUFBTTtZQUNWO2dCQUNJLFNBQVMsR0FBRyxvQkFBQSxHQUFFLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLGtCQUFtQixDQUFJLENBQUEsQ0FBQztTQUN4RDtRQUNEO1lBQ0ksb0JBQUEsS0FBSSxFQUFBLElBQUMsRUFBQTtnQkFDQSxVQUFVLEVBQUEsQ0FBRSxHQUFBLEVBQUUsS0FBSyxDQUFDLE9BQVE7WUFDM0IsQ0FBQTtVQUNSO0tBQ0w7SUFDRCxxQkFBcUIsRUFBRSxZQUFZO1FBQy9CLE9BQU8sS0FBSyxDQUFDO0tBQ2hCO0FBQ0wsQ0FBQyxDQUFDLENBQUM7O0FBRUgsSUFBSSxzQ0FBc0MsZ0NBQUE7SUFDdEMsTUFBTSxFQUFFLENBQUMsTUFBTSxDQUFDLGVBQWUsRUFBRSxrQkFBa0IsQ0FBQztJQUNwRCxlQUFlLEVBQUUsWUFBWTtRQUN6QixPQUFPO1lBQ0gsR0FBRyxFQUFFLEVBQUU7U0FDVixDQUFDO0tBQ0w7SUFDRCxrQkFBa0IsRUFBRSxZQUFZO1FBQzVCLElBQUksQ0FBQyxRQUFRLENBQUMsSUFBSSxDQUFDLEtBQUssQ0FBQyxVQUFVLENBQUMsQ0FBQztLQUN4QztJQUNELG9CQUFvQixFQUFFLFlBQVk7UUFDOUIsSUFBSSxDQUFDLFNBQVMsRUFBRSxDQUFDO0tBQ3BCO0lBQ0QsUUFBUSxFQUFFLFVBQVUsS0FBSyxFQUFFO1FBQ3ZCLElBQUksSUFBSSxHQUFHLElBQUksS0FBSyxDQUFDLFNBQVMsQ0FBQyxLQUFLLEVBQUUsVUFBVSxLQUFLLEVBQUU7WUFDbkQsT0FBTyxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxLQUFLLENBQUMsS0FBSyxDQUFDLENBQUM7U0FDekMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQztRQUNkLElBQUksQ0FBQyxRQUFRLENBQUM7WUFDVixJQUFJLEVBQUUsSUFBSTtBQUN0QixTQUFTLENBQUMsQ0FBQzs7UUFFSCxJQUFJLENBQUMsV0FBVyxDQUFDLEtBQUssRUFBRSxJQUFJLENBQUMsZ0JBQWdCLENBQUMsQ0FBQztRQUMvQyxJQUFJLENBQUMsV0FBVyxDQUFDLGFBQWEsRUFBRSxJQUFJLENBQUMsZ0JBQWdCLENBQUMsQ0FBQztLQUMxRDtJQUNELFNBQVMsRUFBRSxZQUFZO1FBQ25CLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLEtBQUssRUFBRSxDQUFDO0tBQzNCO0lBQ0QsZ0JBQWdCLEVBQUUsWUFBWTtRQUMxQixJQUFJLENBQUMsUUFBUSxDQUFDO1lBQ1YsR0FBRyxFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLElBQUk7U0FDNUIsQ0FBQyxDQUFDO0tBQ047SUFDRCx5QkFBeUIsRUFBRSxVQUFVLFNBQVMsRUFBRTtRQUM1QyxJQUFJLFNBQVMsQ0FBQyxNQUFNLEtBQUssSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLEVBQUU7WUFDeEMsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLEdBQUcsU0FBUyxDQUFDLE1BQU0sQ0FBQztZQUNyQyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQztTQUNqQztRQUNELElBQUksU0FBUyxDQUFDLFVBQVUsS0FBSyxJQUFJLENBQUMsS0FBSyxDQUFDLFVBQVUsRUFBRTtZQUNoRCxJQUFJLENBQUMsU0FBUyxFQUFFLENBQUM7WUFDakIsSUFBSSxDQUFDLFFBQVEsQ0FBQyxTQUFTLENBQUMsVUFBVSxDQUFDLENBQUM7U0FDdkM7S0FDSjtJQUNELGVBQWUsRUFBRSxZQUFZO1FBQ3pCLE9BQU87WUFDSCxTQUFTLEVBQUUsRUFBRTtZQUNiLFlBQVksRUFBRSxFQUFFO1lBQ2hCLGtCQUFrQixFQUFFLEtBQUs7U0FDNUIsQ0FBQztLQUNMO0lBQ0QsU0FBUyxFQUFFLFVBQVUsSUFBSSxFQUFFO1FBQ3ZCLE9BQU8sb0JBQUMsVUFBVSxFQUFBLENBQUEsQ0FBQyxHQUFBLEVBQUcsQ0FBRSxJQUFJLENBQUMsRUFBRSxFQUFDLENBQUMsS0FBQSxFQUFLLENBQUUsSUFBSyxDQUFFLENBQUEsQ0FBQztLQUNuRDtJQUNELE1BQU0sRUFBRSxZQUFZO0FBQ3hCLFFBQVEsSUFBSSxJQUFJLEdBQUcsSUFBSSxDQUFDLFVBQVUsQ0FBQyxJQUFJLENBQUMsS0FBSyxDQUFDLEdBQUcsQ0FBQyxDQUFDOztRQUUzQyxPQUFPLG9CQUFBLEtBQUksRUFBQSxDQUFBLENBQUMsUUFBQSxFQUFRLENBQUUsSUFBSSxDQUFDLFFBQVUsQ0FBQSxFQUFBO1lBQ2hDLENBQUMsSUFBSSxDQUFDLGlCQUFpQixDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsR0FBRyxDQUFDLE1BQU0sQ0FBQyxFQUFBLENBQUU7WUFDaEQsSUFBSSxFQUFDO1lBQ0wsQ0FBQyxJQUFJLENBQUMsb0JBQW9CLENBQUMsSUFBSSxDQUFDLEtBQUssQ0FBQyxHQUFHLENBQUMsTUFBTSxFQUFHO1FBQ2xELENBQUEsQ0FBQztLQUNWO0FBQ0wsQ0FBQyxDQUFDLENBQUM7O0FBRUgsSUFBSSxrQ0FBa0MsNEJBQUE7SUFDbEMsTUFBTSxFQUFFLFVBQVUsQ0FBQyxFQUFFO1FBQ2pCLENBQUMsQ0FBQyxjQUFjLEVBQUUsQ0FBQztRQUNuQixPQUFPLElBQUksQ0FBQyxLQUFLLENBQUMsV0FBVyxDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLENBQUM7S0FDbEQ7SUFDRCxNQUFNLEVBQUUsWUFBWTtRQUNoQixJQUFJLFNBQVMsR0FBRyxRQUFRLENBQUM7UUFDekIsSUFBSSxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sRUFBRTtZQUNuQixTQUFTLElBQUksZUFBZSxDQUFDO1NBQ2hDLE1BQU07WUFDSCxTQUFTLElBQUksZUFBZSxDQUFDO1NBQ2hDO1FBQ0Q7WUFDSSxvQkFBQSxHQUFFLEVBQUEsQ0FBQTtnQkFDRSxJQUFBLEVBQUksQ0FBQyxHQUFBLEVBQUc7Z0JBQ1IsU0FBQSxFQUFTLENBQUUsU0FBUyxFQUFDO2dCQUNyQixPQUFBLEVBQU8sQ0FBRSxJQUFJLENBQUMsTUFBUSxDQUFBLEVBQUE7Z0JBQ3JCLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSztZQUNqQixDQUFBO1VBQ047S0FDTDtBQUNMLENBQUMsQ0FBQyxDQUFDOztBQUVILElBQUksOEJBQThCLHdCQUFBO0lBQzlCLGVBQWUsRUFBRSxZQUFZO1FBQ3pCLE9BQU87WUFDSCxNQUFNLEVBQUU7Z0JBQ0osT0FBTyxFQUFFLEtBQUs7Z0JBQ2QsTUFBTSxFQUFFLElBQUk7Z0JBQ1osS0FBSyxFQUFFLElBQUk7YUFDZDtTQUNKLENBQUM7S0FDTDtJQUNELEtBQUssRUFBRSxZQUFZO1FBQ2YsSUFBSSxDQUFDLEdBQUcsRUFBRSxDQUFDO1FBQ1gsQ0FBQyxDQUFDLEtBQUssQ0FBQyxhQUFhLENBQUMsR0FBRyxTQUFTLENBQUM7UUFDbkMsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDLENBQUMsQ0FBQztLQUNwQjtJQUNELFdBQVcsRUFBRSxVQUFVLEtBQUssRUFBRTtRQUMxQixJQUFJLE1BQU0sR0FBRyxDQUFDLENBQUMsTUFBTSxDQUFDLEVBQUUsRUFBRSxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxDQUFDO1FBQzdDLE1BQU0sQ0FBQyxLQUFLLENBQUMsR0FBRyxDQUFDLE1BQU0sQ0FBQyxLQUFLLENBQUMsQ0FBQztRQUMvQixJQUFJLENBQUMsUUFBUSxDQUFDLENBQUMsTUFBTSxFQUFFLE1BQU0sQ0FBQyxDQUFDLENBQUM7S0FDbkM7SUFDRCxNQUFNLEVBQUUsWUFBWTtRQUNoQjtZQUNJLG9CQUFBLEtBQUksRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMsVUFBVyxDQUFBLEVBQUE7Z0JBQ3RCLG9CQUFBLEtBQUksRUFBQSxJQUFDLEVBQUE7QUFBQSxvQkFBQSxVQUFBLEVBQUE7QUFBQSxvQkFFRCxvQkFBQSxLQUFJLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLFlBQWEsQ0FBQSxFQUFBO3dCQUN4QixvQkFBQyxZQUFZLEVBQUEsQ0FBQSxDQUFDLElBQUEsRUFBSSxDQUFDLE9BQUEsRUFBTyxDQUFDLE1BQUEsRUFBTSxDQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLEtBQUssRUFBQyxDQUFDLFdBQUEsRUFBVyxDQUFFLElBQUksQ0FBQyxXQUFZLENBQUUsQ0FBQSxFQUFBO3dCQUM1RixvQkFBQyxZQUFZLEVBQUEsQ0FBQSxDQUFDLElBQUEsRUFBSSxDQUFDLE1BQUEsRUFBTSxDQUFDLE1BQUEsRUFBTSxDQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLElBQUksRUFBQyxDQUFDLFdBQUEsRUFBVyxDQUFFLElBQUksQ0FBQyxXQUFZLENBQUUsQ0FBQSxFQUFBO3dCQUMxRixvQkFBQyxZQUFZLEVBQUEsQ0FBQSxDQUFDLElBQUEsRUFBSSxDQUFDLEtBQUEsRUFBSyxDQUFDLE1BQUEsRUFBTSxDQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLEdBQUcsRUFBQyxDQUFDLFdBQUEsRUFBVyxDQUFFLElBQUksQ0FBQyxXQUFZLENBQUUsQ0FBQSxFQUFBO3dCQUN4RixvQkFBQSxHQUFFLEVBQUEsQ0FBQSxDQUFDLE9BQUEsRUFBTyxDQUFFLElBQUksQ0FBQyxLQUFLLEVBQUMsQ0FBQyxTQUFBLEVBQVMsQ0FBQyxhQUFjLENBQUksQ0FBQTtBQUM1RSxvQkFBMEIsQ0FBQTs7Z0JBRUosQ0FBQSxFQUFBO2dCQUNOLG9CQUFDLGdCQUFnQixFQUFBLENBQUEsQ0FBQyxNQUFBLEVBQU0sQ0FBRSxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sRUFBQyxDQUFDLFVBQUEsRUFBVSxDQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsVUFBVyxDQUFFLENBQUE7WUFDL0UsQ0FBQTtVQUNSO0tBQ0w7QUFDTCxDQUFDLENBQUMsQ0FBQzs7QUFFSCxNQUFNLENBQUMsT0FBTyxHQUFHLFFBQVE7OztBQzNKekIsSUFBSSxLQUFLLEdBQUcsT0FBTyxDQUFDLE9BQU8sQ0FBQyxDQUFDO0FBQzdCLElBQUksQ0FBQyxHQUFHLE9BQU8sQ0FBQyxRQUFRLENBQUMsQ0FBQzs7QUFFMUIsSUFBSSxNQUFNLEdBQUcsT0FBTyxDQUFDLGFBQWEsQ0FBQyxDQUFDO0FBQ3BDLElBQUksT0FBTyxHQUFHLE9BQU8sQ0FBQyxlQUFlLENBQUMsQ0FBQztBQUN2QyxJQUFJLFNBQVMsR0FBRyxPQUFPLENBQUMsa0JBQWtCLENBQUMsQ0FBQztBQUM1QyxJQUFJLFFBQVEsR0FBRyxPQUFPLENBQUMsYUFBYSxDQUFDLENBQUM7O0FBRXRDLElBQUksK0JBQStCLHlCQUFBO0lBQy9CLE9BQU8sRUFBRSxVQUFVLENBQUMsRUFBRTtRQUNsQixDQUFDLENBQUMsY0FBYyxFQUFFLENBQUM7UUFDbkIsSUFBSSxDQUFDLEtBQUssQ0FBQyxPQUFPLEVBQUUsQ0FBQztLQUN4QjtJQUNELE1BQU0sRUFBRSxZQUFZO1FBQ2hCO1lBQ0ksb0JBQUEsR0FBRSxFQUFBLENBQUEsQ0FBQyxLQUFBLEVBQUssQ0FBRSxJQUFJLENBQUMsS0FBSyxDQUFDLEtBQUssRUFBQztnQkFDdkIsSUFBQSxFQUFJLENBQUMsR0FBQSxFQUFHO2dCQUNSLFNBQUEsRUFBUyxDQUFDLFlBQUEsRUFBWTtnQkFDdEIsT0FBQSxFQUFPLENBQUUsSUFBSSxDQUFDLE9BQVMsQ0FBQSxFQUFBO2dCQUN2QixvQkFBQSxHQUFFLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFFLFdBQVcsR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQU0sQ0FBSSxDQUFBO1lBQ2pELENBQUE7VUFDTjtLQUNMO0FBQ0wsQ0FBQyxDQUFDLENBQUM7O0FBRUgsSUFBSSxtQ0FBbUMsNkJBQUE7SUFDbkMsTUFBTSxFQUFFLFlBQVk7QUFDeEIsUUFBUSxJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQzs7UUFFM0IsSUFBSSxJQUFJLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsR0FBRyxDQUFDLFVBQVUsQ0FBQyxFQUFFO1lBQ3hDLElBQUksR0FBRyxHQUFHLENBQUMsQ0FBQyxNQUFNLENBQUMsQ0FBQyxDQUFDLENBQUMsV0FBVyxFQUFFLEdBQUcsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLENBQUMsQ0FBQztZQUNqRCxJQUFJLFNBQVMsR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sS0FBSyxDQUFDLEdBQUcsUUFBUSxHQUFHLEVBQUUsQ0FBQztZQUN4RCxJQUFJLE9BQU8sR0FBRyxVQUFVLEtBQUssRUFBRTtnQkFDM0IsSUFBSSxDQUFDLEtBQUssQ0FBQyxTQUFTLENBQUMsQ0FBQyxDQUFDLENBQUM7Z0JBQ3hCLEtBQUssQ0FBQyxjQUFjLEVBQUUsQ0FBQzthQUMxQixDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQztZQUNiLE9BQU8sb0JBQUEsR0FBRSxFQUFBLENBQUEsQ0FBQyxHQUFBLEVBQUcsQ0FBRSxDQUFDLEVBQUM7Z0JBQ2IsSUFBQSxFQUFJLENBQUMsR0FBQSxFQUFHO2dCQUNSLFNBQUEsRUFBUyxDQUFFLFNBQVMsRUFBQztnQkFDckIsT0FBQSxFQUFPLENBQUUsT0FBUyxDQUFBLEVBQUMsR0FBUSxDQUFBLENBQUM7QUFDNUMsU0FBUyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDOztRQUVkLElBQUksWUFBWSxHQUFHLElBQUksQ0FBQztRQUN4QixHQUFHLElBQUksQ0FBQyxXQUFXLENBQUM7WUFDaEIsWUFBWSxHQUFHLG9CQUFDLFNBQVMsRUFBQSxDQUFBLENBQUMsS0FBQSxFQUFLLENBQUMsMkJBQUEsRUFBMkIsQ0FBQyxJQUFBLEVBQUksQ0FBQyxTQUFBLEVBQVMsQ0FBQyxPQUFBLEVBQU8sQ0FBRSxPQUFPLENBQUMsV0FBVyxDQUFDLE1BQU0sQ0FBQyxJQUFJLENBQUMsSUFBSSxFQUFFLElBQUksQ0FBRSxDQUFBLENBQUcsQ0FBQSxDQUFDO1NBQ3ZJO1FBQ0QsSUFBSSxZQUFZLEdBQUcsSUFBSSxDQUFDO1FBQ3hCLEdBQUcsSUFBSSxDQUFDLFFBQVEsQ0FBQztZQUNiLFlBQVksR0FBRyxvQkFBQyxTQUFTLEVBQUEsQ0FBQSxDQUFDLEtBQUEsRUFBSyxDQUFDLDRCQUFBLEVBQTRCLENBQUMsSUFBQSxFQUFJLENBQUMsWUFBQSxFQUFZLENBQUMsT0FBQSxFQUFPLENBQUUsT0FBTyxDQUFDLFdBQVcsQ0FBQyxNQUFNLENBQUMsSUFBSSxDQUFDLElBQUksRUFBRSxJQUFJLENBQUUsQ0FBQSxDQUFHLENBQUEsQ0FBQztBQUNwSixTQUFTOztRQUVEO1lBQ0ksb0JBQUEsS0FBSSxFQUFBLENBQUEsQ0FBQyxHQUFBLEVBQUcsQ0FBQyxNQUFBLEVBQU0sQ0FBQyxTQUFBLEVBQVMsQ0FBQyxzQkFBdUIsQ0FBQSxFQUFBO2dCQUM1QyxJQUFJLEVBQUM7Z0JBQ04sb0JBQUMsU0FBUyxFQUFBLENBQUEsQ0FBQyxLQUFBLEVBQUssQ0FBQyxlQUFBLEVBQWUsQ0FBQyxJQUFBLEVBQUksQ0FBQyxVQUFBLEVBQVUsQ0FBQyxPQUFBLEVBQU8sQ0FBRSxPQUFPLENBQUMsV0FBVyxDQUFDLE1BQU0sQ0FBQyxJQUFJLENBQUMsSUFBSSxFQUFFLElBQUksQ0FBRSxDQUFBLENBQUcsQ0FBQSxFQUFBO2dCQUN6RyxvQkFBQyxTQUFTLEVBQUEsQ0FBQSxDQUFDLEtBQUEsRUFBSyxDQUFDLGtCQUFBLEVBQWtCLENBQUMsSUFBQSxFQUFJLENBQUMsU0FBQSxFQUFTLENBQUMsT0FBQSxFQUFPLENBQUUsT0FBTyxDQUFDLFdBQVcsQ0FBQyxTQUFTLENBQUMsSUFBSSxDQUFDLElBQUksRUFBRSxJQUFJLENBQUUsQ0FBQSxDQUFHLENBQUEsRUFBQTtnQkFDOUcsb0JBQUMsU0FBUyxFQUFBLENBQUEsQ0FBQyxRQUFBLEVBQUEsRUFBQSxDQUFDLEtBQUEsRUFBSyxDQUFDLGVBQUEsRUFBZSxDQUFDLElBQUEsRUFBSSxDQUFDLFdBQUEsRUFBVyxDQUFDLE9BQUEsRUFBTyxDQUFFLE9BQU8sQ0FBQyxXQUFXLENBQUMsTUFBTSxDQUFDLElBQUksQ0FBQyxJQUFJLEVBQUUsSUFBSSxDQUFFLENBQUEsQ0FBRyxDQUFBLEVBQUE7Z0JBQzFHLFlBQVksRUFBQztnQkFDYixZQUFhO1lBQ1osQ0FBQTtVQUNSO0tBQ0w7QUFDTCxDQUFDLENBQUMsQ0FBQzs7QUFFSCxJQUFJLDZCQUE2Qix1QkFBQTtJQUM3QixNQUFNLEVBQUUsWUFBWTtRQUNoQixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLE9BQU8sQ0FBQyxPQUFPLENBQUMsR0FBRyxDQUFDLFVBQVUsTUFBTSxFQUFFLENBQUMsRUFBRTtZQUMzRDtnQkFDSSxvQkFBQSxJQUFHLEVBQUEsQ0FBQSxDQUFDLEdBQUEsRUFBRyxDQUFFLENBQUcsQ0FBQSxFQUFBO29CQUNSLG9CQUFBLElBQUcsRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMsYUFBYyxDQUFBLEVBQUMsTUFBTSxDQUFDLENBQUMsQ0FBQyxHQUFHLEdBQVMsQ0FBQSxFQUFBO29CQUNsRCxvQkFBQSxJQUFHLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLGNBQWUsQ0FBQSxFQUFDLE1BQU0sQ0FBQyxDQUFDLENBQU8sQ0FBQTtnQkFDNUMsQ0FBQTtjQUNQO1NBQ0wsQ0FBQyxDQUFDO1FBQ0g7WUFDSSxvQkFBQSxPQUFNLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLGNBQWUsQ0FBQSxFQUFBO2dCQUM1QixvQkFBQSxPQUFNLEVBQUEsSUFBQyxFQUFBO29CQUNGLElBQUs7Z0JBQ0YsQ0FBQTtZQUNKLENBQUE7VUFDVjtLQUNMO0FBQ0wsQ0FBQyxDQUFDLENBQUM7O0FBRUgsSUFBSSx1Q0FBdUMsaUNBQUE7SUFDdkMsTUFBTSxFQUFFLFlBQVk7UUFDaEIsSUFBSSxJQUFJLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUM7UUFDM0IsSUFBSSxVQUFVLEdBQUc7WUFDYixJQUFJLENBQUMsT0FBTyxDQUFDLE1BQU07WUFDbkIsU0FBUyxDQUFDLFlBQVksQ0FBQyxVQUFVLENBQUMsSUFBSSxDQUFDLE9BQU8sQ0FBQztZQUMvQyxPQUFPLEdBQUcsSUFBSSxDQUFDLE9BQU8sQ0FBQyxXQUFXLENBQUMsSUFBSSxDQUFDLEdBQUcsQ0FBQztTQUMvQyxDQUFDLElBQUksQ0FBQyxHQUFHLENBQUMsQ0FBQztRQUNaLElBQUksT0FBTyxHQUFHLElBQUksQ0FBQztRQUNuQixJQUFJLElBQUksQ0FBQyxPQUFPLENBQUMsYUFBYSxHQUFHLENBQUMsRUFBRTtZQUNoQyxPQUFPLEdBQUcsd0JBQXdCLEdBQUcsUUFBUSxDQUFDLFVBQVUsQ0FBQyxJQUFJLENBQUMsT0FBTyxDQUFDLGFBQWEsQ0FBQyxDQUFDO1NBQ3hGLE1BQU07WUFDSCxPQUFPLEdBQUcsb0JBQUEsS0FBSSxFQUFBLENBQUEsQ0FBQyxTQUFBLEVBQVMsQ0FBQyxrQkFBbUIsQ0FBQSxFQUFBLFlBQWdCLENBQUEsQ0FBQztBQUN6RSxTQUFTO0FBQ1Q7QUFDQTs7UUFFUTtZQUNJLG9CQUFBLFNBQVEsRUFBQSxJQUFDLEVBQUE7Z0JBQ0wsb0JBQUEsS0FBSSxFQUFBLENBQUEsQ0FBQyxTQUFBLEVBQVMsQ0FBQyxZQUFhLENBQUEsRUFBQyxZQUFtQixDQUFBLEVBQUE7Z0JBQ2hELG9CQUFDLE9BQU8sRUFBQSxDQUFBLENBQUMsT0FBQSxFQUFPLENBQUUsSUFBSSxDQUFDLE9BQVEsQ0FBRSxDQUFBLEVBQUE7Z0JBQ2pDLG9CQUFBLElBQUcsRUFBQSxJQUFFLENBQUEsRUFBQTtnQkFDSixPQUFRO1lBQ0gsQ0FBQTtVQUNaO0tBQ0w7QUFDTCxDQUFDLENBQUMsQ0FBQzs7QUFFSCxJQUFJLHdDQUF3QyxrQ0FBQTtJQUN4QyxNQUFNLEVBQUUsWUFBWTtRQUNoQixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQztRQUMzQixJQUFJLFVBQVUsR0FBRztZQUNiLE9BQU8sR0FBRyxJQUFJLENBQUMsUUFBUSxDQUFDLFdBQVcsQ0FBQyxJQUFJLENBQUMsR0FBRyxDQUFDO1lBQzdDLElBQUksQ0FBQyxRQUFRLENBQUMsSUFBSTtZQUNsQixJQUFJLENBQUMsUUFBUSxDQUFDLEdBQUc7U0FDcEIsQ0FBQyxJQUFJLENBQUMsR0FBRyxDQUFDLENBQUM7UUFDWixJQUFJLE9BQU8sR0FBRyxJQUFJLENBQUM7UUFDbkIsSUFBSSxJQUFJLENBQUMsUUFBUSxDQUFDLGFBQWEsR0FBRyxDQUFDLEVBQUU7WUFDakMsT0FBTyxHQUFHLHlCQUF5QixHQUFHLFFBQVEsQ0FBQyxVQUFVLENBQUMsSUFBSSxDQUFDLFFBQVEsQ0FBQyxhQUFhLENBQUMsQ0FBQztTQUMxRixNQUFNO1lBQ0gsT0FBTyxHQUFHLG9CQUFBLEtBQUksRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMsa0JBQW1CLENBQUEsRUFBQSxZQUFnQixDQUFBLENBQUM7QUFDekUsU0FBUztBQUNUO0FBQ0E7O1FBRVE7WUFDSSxvQkFBQSxTQUFRLEVBQUEsSUFBQyxFQUFBO2dCQUNMLG9CQUFBLEtBQUksRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMsWUFBYSxDQUFBLEVBQUMsWUFBbUIsQ0FBQSxFQUFBO2dCQUNoRCxvQkFBQyxPQUFPLEVBQUEsQ0FBQSxDQUFDLE9BQUEsRUFBTyxDQUFFLElBQUksQ0FBQyxRQUFTLENBQUUsQ0FBQSxFQUFBO2dCQUNsQyxvQkFBQSxJQUFHLEVBQUEsSUFBRSxDQUFBLEVBQUE7Z0JBQ0osT0FBUTtZQUNILENBQUE7VUFDWjtLQUNMO0FBQ0wsQ0FBQyxDQUFDLENBQUM7O0FBRUgsSUFBSSxxQ0FBcUMsK0JBQUE7SUFDckMsTUFBTSxFQUFFLFlBQVk7UUFDaEIsSUFBSSxJQUFJLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUM7UUFDM0I7WUFDSSxvQkFBQSxTQUFRLEVBQUEsSUFBQyxFQUFBO2dCQUNMLG9CQUFBLEtBQUksRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMscUJBQXNCLENBQUEsRUFBQTtnQkFDcEMsSUFBSSxDQUFDLEtBQUssQ0FBQyxHQUFHLEVBQUM7b0JBQ1osb0JBQUEsS0FBSSxFQUFBLElBQUMsRUFBQTt3QkFDRCxvQkFBQSxPQUFNLEVBQUEsSUFBQyxFQUFDLENBQUMsUUFBUSxDQUFDLGVBQWUsQ0FBQyxJQUFJLENBQUMsS0FBSyxDQUFDLFNBQVMsRUFBVyxDQUFBO29CQUMvRCxDQUFBO2dCQUNKLENBQUE7WUFDQSxDQUFBO1VBQ1o7S0FDTDtBQUNMLENBQUMsQ0FBQyxDQUFDOztBQUVILElBQUksK0JBQStCLHlCQUFBO0FBQ25DLElBQUksTUFBTSxFQUFFLFlBQVk7O0FBRXhCLFFBQVEsSUFBSSxDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsQ0FBQyxFQUFFOztZQUVmLE9BQU8sb0JBQUEsSUFBRyxFQUFBLElBQU0sQ0FBQSxDQUFDO0FBQzdCLFNBQVM7O0FBRVQsUUFBUSxJQUFJLEVBQUUsR0FBRyxRQUFRLENBQUMsZUFBZSxDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsQ0FBQyxDQUFDLENBQUM7O1FBRWhELElBQUksS0FBSyxDQUFDO1FBQ1YsSUFBSSxJQUFJLENBQUMsS0FBSyxDQUFDLE9BQU8sRUFBRTtZQUNwQixLQUFLLEdBQUcsUUFBUSxDQUFDLGVBQWUsQ0FBQyxJQUFJLElBQUksSUFBSSxDQUFDLEtBQUssQ0FBQyxDQUFDLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxPQUFPLENBQUMsQ0FBQyxDQUFDO1lBQzdFLEtBQUssR0FBRyxvQkFBQSxNQUFLLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLFlBQWEsQ0FBQSxFQUFDLEdBQUcsR0FBRyxLQUFLLEdBQUcsR0FBVyxDQUFBLENBQUM7U0FDbkUsTUFBTTtZQUNILEtBQUssR0FBRyxJQUFJLENBQUM7QUFDekIsU0FBUzs7UUFFRCxPQUFPLG9CQUFBLElBQUcsRUFBQSxJQUFDLEVBQUE7WUFDUCxvQkFBQSxJQUFHLEVBQUEsSUFBQyxFQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsS0FBSyxHQUFHLEdBQVMsQ0FBQSxFQUFBO1lBQ2pDLG9CQUFBLElBQUcsRUFBQSxJQUFDLEVBQUMsRUFBRSxFQUFDLEdBQUEsRUFBRSxLQUFXLENBQUE7UUFDcEIsQ0FBQSxDQUFDO0tBQ1Q7QUFDTCxDQUFDLENBQUMsQ0FBQzs7QUFFSCxJQUFJLG9DQUFvQyw4QkFBQTs7SUFFcEMsTUFBTSxFQUFFLFlBQVk7UUFDaEIsSUFBSSxJQUFJLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUM7QUFDbkMsUUFBUSxJQUFJLE9BQU8sR0FBRyxJQUFJLENBQUMsT0FBTyxDQUFDLE9BQU8sQ0FBQyxJQUFJLENBQUMsR0FBRyxDQUFDLENBQUM7O1FBRTdDLElBQUksR0FBRyxHQUFHLG9CQUFBLElBQUcsRUFBQSxDQUFBLENBQUMsR0FBQSxFQUFHLENBQUMsS0FBTSxDQUFLLENBQUEsQ0FBQztRQUM5QixJQUFJLElBQUksQ0FBQyxHQUFHLEVBQUU7WUFDVixHQUFHLEdBQUcsb0JBQUEsSUFBRyxFQUFBLENBQUEsQ0FBQyxHQUFBLEVBQUcsQ0FBQyxLQUFNLENBQUEsRUFBQTtnQkFDaEIsb0JBQUEsSUFBRyxFQUFBLElBQUMsRUFBQTtvQkFDQSxvQkFBQSxNQUFLLEVBQUEsQ0FBQSxDQUFDLEtBQUEsRUFBSyxDQUFDLDRCQUE2QixDQUFBLEVBQUEsVUFBZSxDQUFBO2dCQUN2RCxDQUFBLEVBQUE7Z0JBQ0wsb0JBQUEsSUFBRyxFQUFBLElBQUMsRUFBQyxJQUFJLENBQUMsR0FBUyxDQUFBO1lBQ2xCLENBQUEsQ0FBQztTQUNUO1FBQ0Q7WUFDSSxvQkFBQSxPQUFNLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLGtCQUFtQixDQUFBLEVBQUE7Z0JBQ2hDLG9CQUFBLE9BQU0sRUFBQSxJQUFDLEVBQUE7b0JBQ0gsb0JBQUEsSUFBRyxFQUFBLENBQUEsQ0FBQyxHQUFBLEVBQUcsQ0FBQyxTQUFVLENBQUEsRUFBQTt3QkFDZCxvQkFBQSxJQUFHLEVBQUEsSUFBQyxFQUFBLFVBQWEsQ0FBQSxFQUFBO3dCQUNqQixvQkFBQSxJQUFHLEVBQUEsSUFBQyxFQUFDLE9BQWEsQ0FBQTtvQkFDakIsQ0FBQSxFQUFBO29CQUNKLEdBQUk7Z0JBQ0QsQ0FBQTtZQUNKLENBQUE7VUFDVjtLQUNMO0FBQ0wsQ0FBQyxDQUFDLENBQUM7O0FBRUgsSUFBSSxxQ0FBcUMsK0JBQUE7QUFDekMsSUFBSSxNQUFNLEVBQUUsWUFBWTtBQUN4Qjs7UUFFUSxJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQztRQUMzQixJQUFJLFdBQVcsR0FBRyxJQUFJLENBQUMsV0FBVyxDQUFDO0FBQzNDLFFBQVEsSUFBSSxXQUFXLEdBQUcsSUFBSSxDQUFDLFdBQVcsQ0FBQzs7UUFFbkMsSUFBSSxRQUFRLEdBQUcsQ0FBQyxTQUFTLEVBQUUsR0FBRyxDQUFDLENBQUM7UUFDaEM7WUFDSSxvQkFBQSxLQUFJLEVBQUEsSUFBQyxFQUFBO1lBQ0osV0FBVyxDQUFDLElBQUksR0FBRyxvQkFBQSxJQUFHLEVBQUEsSUFBQyxFQUFBLG9CQUF1QixDQUFBLEdBQUcsSUFBSSxFQUFDO0FBQ25FLFlBQWEsV0FBVyxDQUFDLElBQUksR0FBRyxvQkFBQSxLQUFJLEVBQUEsQ0FBQSxDQUFDLEtBQUEsRUFBSyxDQUFFLFFBQVUsQ0FBQSxFQUFDLFdBQVcsQ0FBQyxJQUFXLENBQUEsR0FBRyxJQUFJLEVBQUM7O1lBRXpFLFdBQVcsQ0FBQyxJQUFJLEdBQUcsb0JBQUEsSUFBRyxFQUFBLElBQUMsRUFBQSxvQkFBdUIsQ0FBQSxHQUFHLElBQUksRUFBQztZQUN0RCxXQUFXLENBQUMsSUFBSSxHQUFHLG9CQUFBLEtBQUksRUFBQSxDQUFBLENBQUMsS0FBQSxFQUFLLENBQUUsUUFBVSxDQUFBLEVBQUMsV0FBVyxDQUFDLElBQVcsQ0FBQSxHQUFHLElBQUs7WUFDcEUsQ0FBQTtVQUNSO0tBQ0w7QUFDTCxDQUFDLENBQUMsQ0FBQzs7QUFFSCxJQUFJLDRCQUE0QixzQkFBQTtJQUM1QixNQUFNLEVBQUUsWUFBWTtRQUNoQixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQztRQUMzQixJQUFJLEVBQUUsR0FBRyxJQUFJLENBQUMsV0FBVyxDQUFDO1FBQzFCLElBQUksRUFBRSxHQUFHLElBQUksQ0FBQyxXQUFXLENBQUM7UUFDMUIsSUFBSSxHQUFHLEdBQUcsSUFBSSxDQUFDLE9BQU8sQ0FBQztBQUMvQixRQUFRLElBQUksSUFBSSxHQUFHLElBQUksQ0FBQyxRQUFRLENBQUM7O1FBRXpCLElBQUksVUFBVSxHQUFHO1lBQ2I7Z0JBQ0ksS0FBSyxFQUFFLHdCQUF3QjtnQkFDL0IsQ0FBQyxFQUFFLEVBQUUsQ0FBQyxlQUFlO2dCQUNyQixPQUFPLEVBQUUsR0FBRyxDQUFDLGVBQWU7YUFDL0IsRUFBRTtnQkFDQyxLQUFLLEVBQUUsNEJBQTRCO2dCQUNuQyxDQUFDLEVBQUUsRUFBRSxDQUFDLG1CQUFtQjtnQkFDekIsT0FBTyxFQUFFLEdBQUcsQ0FBQyxlQUFlO2FBQy9CLEVBQUU7Z0JBQ0MsS0FBSyxFQUFFLDRCQUE0QjtnQkFDbkMsQ0FBQyxFQUFFLEVBQUUsQ0FBQyxtQkFBbUI7Z0JBQ3pCLE9BQU8sRUFBRSxHQUFHLENBQUMsZUFBZTthQUMvQixFQUFFO2dCQUNDLEtBQUssRUFBRSwwQkFBMEI7Z0JBQ2pDLENBQUMsRUFBRSxFQUFFLENBQUMsZUFBZTtnQkFDckIsT0FBTyxFQUFFLEdBQUcsQ0FBQyxlQUFlO2FBQy9CLEVBQUU7Z0JBQ0MsS0FBSyxFQUFFLDRCQUE0QjtnQkFDbkMsQ0FBQyxFQUFFLEVBQUUsQ0FBQyxtQkFBbUI7Z0JBQ3pCLE9BQU8sRUFBRSxHQUFHLENBQUMsZUFBZTthQUMvQixFQUFFO2dCQUNDLEtBQUssRUFBRSxvQkFBb0I7Z0JBQzNCLENBQUMsRUFBRSxHQUFHLENBQUMsZUFBZTthQUN6QixFQUFFO2dCQUNDLEtBQUssRUFBRSxrQkFBa0I7Z0JBQ3pCLENBQUMsRUFBRSxHQUFHLENBQUMsYUFBYTtnQkFDcEIsT0FBTyxFQUFFLEdBQUcsQ0FBQyxlQUFlO2FBQy9CO0FBQ2IsU0FBUyxDQUFDOztRQUVGLElBQUksSUFBSSxDQUFDLFFBQVEsRUFBRTtZQUNmLFVBQVUsQ0FBQyxJQUFJO2dCQUNYO29CQUNJLEtBQUssRUFBRSxxQkFBcUI7b0JBQzVCLENBQUMsRUFBRSxJQUFJLENBQUMsZUFBZTtvQkFDdkIsT0FBTyxFQUFFLEdBQUcsQ0FBQyxlQUFlO2lCQUMvQixFQUFFO29CQUNDLEtBQUssRUFBRSxtQkFBbUI7b0JBQzFCLENBQUMsRUFBRSxJQUFJLENBQUMsYUFBYTtvQkFDckIsT0FBTyxFQUFFLEdBQUcsQ0FBQyxlQUFlO2lCQUMvQjthQUNKLENBQUM7QUFDZCxTQUFTO0FBQ1Q7O1FBRVEsVUFBVSxDQUFDLE9BQU8sQ0FBQyxVQUFVLENBQUMsRUFBRTtZQUM1QixDQUFDLENBQUMsR0FBRyxHQUFHLENBQUMsQ0FBQyxLQUFLLENBQUM7QUFDNUIsU0FBUyxDQUFDLENBQUM7O0FBRVgsUUFBUSxVQUFVLEdBQUcsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxVQUFVLEVBQUUsR0FBRyxDQUFDLENBQUM7O1FBRXZDLElBQUksSUFBSSxHQUFHLFVBQVUsQ0FBQyxHQUFHLENBQUMsVUFBVSxDQUFDLEVBQUU7WUFDbkMsT0FBTyxvQkFBQyxTQUFTLEVBQUEsZ0JBQUEsR0FBQSxDQUFFLEdBQUcsQ0FBRSxDQUFFLENBQUEsQ0FBQztBQUN2QyxTQUFTLENBQUMsQ0FBQzs7UUFFSDtZQUNJLG9CQUFBLEtBQUksRUFBQSxJQUFDLEVBQUE7Z0JBQ0Qsb0JBQUEsSUFBRyxFQUFBLElBQUMsRUFBQSxRQUFXLENBQUEsRUFBQTtnQkFDZixvQkFBQSxPQUFNLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLGNBQWUsQ0FBQSxFQUFBO29CQUM1QixvQkFBQSxPQUFNLEVBQUEsSUFBQyxFQUFBO29CQUNOLElBQUs7b0JBQ0UsQ0FBQTtnQkFDSixDQUFBO1lBQ04sQ0FBQTtVQUNSO0tBQ0w7QUFDTCxDQUFDLENBQUMsQ0FBQzs7QUFFSCxJQUFJLDhDQUE4Qyx3Q0FBQTtJQUM5QyxNQUFNLEVBQUUsWUFBWTtRQUNoQixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQztRQUMzQixJQUFJLFdBQVcsR0FBRyxJQUFJLENBQUMsV0FBVyxDQUFDO1FBQ25DLElBQUksV0FBVyxHQUFHLElBQUksQ0FBQyxXQUFXLENBQUM7UUFDbkM7QUFDUixZQUFZLG9CQUFBLFNBQVEsRUFBQSxJQUFDLEVBQUE7O2dCQUVMLG9CQUFBLElBQUcsRUFBQSxJQUFDLEVBQUEsbUJBQXNCLENBQUEsRUFBQTtBQUMxQyxnQkFBZ0Isb0JBQUMsY0FBYyxFQUFBLENBQUEsQ0FBQyxJQUFBLEVBQUksQ0FBRSxXQUFZLENBQUUsQ0FBQSxFQUFBOztnQkFFcEMsb0JBQUEsSUFBRyxFQUFBLElBQUMsRUFBQSxtQkFBc0IsQ0FBQSxFQUFBO0FBQzFDLGdCQUFnQixvQkFBQyxjQUFjLEVBQUEsQ0FBQSxDQUFDLElBQUEsRUFBSSxDQUFFLFdBQVksQ0FBRSxDQUFBLEVBQUE7O0FBRXBELGdCQUFnQixvQkFBQyxlQUFlLEVBQUEsQ0FBQSxDQUFDLElBQUEsRUFBSSxDQUFFLElBQUssQ0FBRSxDQUFBLEVBQUE7O0FBRTlDLGdCQUFnQixvQkFBQyxNQUFNLEVBQUEsQ0FBQSxDQUFDLElBQUEsRUFBSSxDQUFFLElBQUssQ0FBRSxDQUFBOztZQUVmLENBQUE7VUFDWjtLQUNMO0FBQ0wsQ0FBQyxDQUFDLENBQUM7O0FBRUgsSUFBSSxPQUFPLEdBQUc7SUFDVixPQUFPLEVBQUUsaUJBQWlCO0lBQzFCLFFBQVEsRUFBRSxrQkFBa0I7SUFDNUIsS0FBSyxFQUFFLGVBQWU7SUFDdEIsT0FBTyxFQUFFLHdCQUF3QjtBQUNyQyxDQUFDLENBQUM7O0FBRUYsSUFBSSxnQ0FBZ0MsMEJBQUE7SUFDaEMsTUFBTSxFQUFFLENBQUMsTUFBTSxDQUFDLGVBQWUsRUFBRSxNQUFNLENBQUMsVUFBVSxFQUFFLE1BQU0sQ0FBQyxLQUFLLENBQUM7SUFDakUsT0FBTyxFQUFFLFVBQVUsSUFBSSxFQUFFO1FBQ3JCLElBQUksSUFBSSxHQUFHLEVBQUUsQ0FBQztRQUNkLENBQUMsU0FBUyxFQUFFLFVBQVUsRUFBRSxPQUFPLENBQUMsQ0FBQyxPQUFPLENBQUMsVUFBVSxDQUFDLEVBQUU7WUFDbEQsSUFBSSxJQUFJLENBQUMsQ0FBQyxDQUFDLEVBQUU7Z0JBQ1QsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQzthQUNoQjtTQUNKLENBQUMsQ0FBQztRQUNILElBQUksQ0FBQyxJQUFJLENBQUMsU0FBUyxDQUFDLENBQUM7UUFDckIsT0FBTyxJQUFJLENBQUM7S0FDZjtJQUNELE9BQU8sRUFBRSxVQUFVLENBQUMsRUFBRTtRQUNsQixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsT0FBTyxDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLENBQUM7QUFDakQsUUFBUSxJQUFJLFlBQVksR0FBRyxJQUFJLENBQUMsT0FBTyxDQUFDLElBQUksQ0FBQyxTQUFTLEVBQUUsQ0FBQyxTQUFTLENBQUMsQ0FBQzs7UUFFNUQsSUFBSSxTQUFTLEdBQUcsQ0FBQyxZQUFZLEdBQUcsQ0FBQyxHQUFHLElBQUksQ0FBQyxNQUFNLElBQUksSUFBSSxDQUFDLE1BQU0sQ0FBQztRQUMvRCxJQUFJLENBQUMsU0FBUyxDQUFDLElBQUksQ0FBQyxTQUFTLENBQUMsQ0FBQyxDQUFDO0tBQ25DO0lBQ0QsU0FBUyxFQUFFLFVBQVUsS0FBSyxFQUFFO1FBQ3hCLElBQUksQ0FBQyxXQUFXO1lBQ1osTUFBTTtZQUNOO2dCQUNJLE1BQU0sRUFBRSxJQUFJLENBQUMsU0FBUyxFQUFFLENBQUMsTUFBTTtnQkFDL0IsU0FBUyxFQUFFLEtBQUs7YUFDbkI7U0FDSixDQUFDO0tBQ0w7SUFDRCxNQUFNLEVBQUUsWUFBWTtRQUNoQixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQztRQUMzQixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsT0FBTyxDQUFDLElBQUksQ0FBQyxDQUFDO0FBQ3RDLFFBQVEsSUFBSSxNQUFNLEdBQUcsSUFBSSxDQUFDLFNBQVMsRUFBRSxDQUFDLFNBQVMsQ0FBQzs7UUFFeEMsSUFBSSxDQUFDLENBQUMsQ0FBQyxRQUFRLENBQUMsSUFBSSxFQUFFLE1BQU0sQ0FBQyxFQUFFO1lBQzNCLElBQUksTUFBTSxLQUFLLFVBQVUsSUFBSSxJQUFJLENBQUMsS0FBSyxFQUFFO2dCQUNyQyxNQUFNLEdBQUcsT0FBTyxDQUFDO2FBQ3BCLE1BQU0sSUFBSSxNQUFNLEtBQUssT0FBTyxJQUFJLElBQUksQ0FBQyxRQUFRLEVBQUU7Z0JBQzVDLE1BQU0sR0FBRyxVQUFVLENBQUM7YUFDdkIsTUFBTTtnQkFDSCxNQUFNLEdBQUcsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDO2FBQ3BCO1lBQ0QsSUFBSSxDQUFDLFNBQVMsQ0FBQyxNQUFNLENBQUMsQ0FBQztBQUNuQyxTQUFTOztRQUVELElBQUksR0FBRyxHQUFHLE9BQU8sQ0FBQyxNQUFNLENBQUMsQ0FBQztRQUMxQjtZQUNJLG9CQUFBLEtBQUksRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMsYUFBQSxFQUFhLENBQUMsUUFBQSxFQUFRLENBQUUsSUFBSSxDQUFDLFVBQVksQ0FBQSxFQUFBO2dCQUNwRCxvQkFBQyxhQUFhLEVBQUEsQ0FBQSxDQUFDLEdBQUEsRUFBRyxDQUFDLE1BQUEsRUFBTTtvQkFDckIsSUFBQSxFQUFJLENBQUUsSUFBSSxFQUFDO29CQUNYLElBQUEsRUFBSSxDQUFFLElBQUksRUFBQztvQkFDWCxNQUFBLEVBQU0sQ0FBRSxNQUFNLEVBQUM7b0JBQ2YsU0FBQSxFQUFTLENBQUUsSUFBSSxDQUFDLFNBQVUsQ0FBRSxDQUFBLEVBQUE7Z0JBQ2hDLG9CQUFDLEdBQUcsRUFBQSxDQUFBLENBQUMsSUFBQSxFQUFJLENBQUUsSUFBSyxDQUFFLENBQUE7WUFDaEIsQ0FBQTtVQUNSO0tBQ0w7QUFDTCxDQUFDLENBQUMsQ0FBQzs7QUFFSCxNQUFNLENBQUMsT0FBTyxHQUFHO0lBQ2IsVUFBVSxFQUFFLFVBQVU7Q0FDekI7OztBQzlZRCxJQUFJLEtBQUssR0FBRyxPQUFPLENBQUMsT0FBTyxDQUFDLENBQUM7QUFDN0IsSUFBSSxTQUFTLEdBQUcsT0FBTyxDQUFDLGtCQUFrQixDQUFDLENBQUM7QUFDNUMsSUFBSSxLQUFLLEdBQUcsT0FBTyxDQUFDLGFBQWEsQ0FBQyxDQUFDOztBQUVuQyxJQUFJLCtCQUErQix5QkFBQTtJQUMvQixPQUFPLEVBQUU7UUFDTCxXQUFXLEVBQUUsWUFBWTtZQUNyQixPQUFPLG9CQUFBLElBQUcsRUFBQSxDQUFBLENBQUMsR0FBQSxFQUFHLENBQUMsS0FBQSxFQUFLLENBQUMsU0FBQSxFQUFTLENBQUMsU0FBVSxDQUFLLENBQUEsQ0FBQztTQUNsRDtLQUNKO0lBQ0QsTUFBTSxFQUFFLFlBQVk7UUFDaEIsSUFBSSxJQUFJLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUM7UUFDM0IsSUFBSSxHQUFHLElBQUksSUFBSSxDQUFDLE9BQU8sQ0FBQyxNQUFNLElBQUksT0FBTyxDQUFDLENBQUM7UUFDM0MsSUFBSSxPQUFPLENBQUM7UUFDWixJQUFJLEdBQUcsRUFBRTtZQUNMLE9BQU8sR0FBRyx1QkFBdUIsQ0FBQztTQUNyQyxNQUFNO1lBQ0gsT0FBTyxHQUFHLHNCQUFzQixDQUFDO1NBQ3BDO1FBQ0QsT0FBTyxvQkFBQSxJQUFHLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFFLE9BQVMsQ0FBSyxDQUFBLENBQUM7S0FDeEM7QUFDTCxDQUFDLENBQUMsQ0FBQztBQUNIOztBQUVBLElBQUksZ0NBQWdDLDBCQUFBO0lBQ2hDLE9BQU8sRUFBRTtRQUNMLFdBQVcsRUFBRSxZQUFZO1lBQ3JCLE9BQU8sb0JBQUEsSUFBRyxFQUFBLENBQUEsQ0FBQyxHQUFBLEVBQUcsQ0FBQyxNQUFBLEVBQU0sQ0FBQyxTQUFBLEVBQVMsQ0FBQyxVQUFXLENBQUssQ0FBQSxDQUFDO1NBQ3BEO0tBQ0o7SUFDRCxNQUFNLEVBQUUsWUFBWTtBQUN4QixRQUFRLElBQUksSUFBSSxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDOztRQUUzQixJQUFJLElBQUksQ0FBQztRQUNULElBQUksSUFBSSxDQUFDLFFBQVEsRUFBRTtBQUMzQixZQUFZLElBQUksV0FBVyxHQUFHLFNBQVMsQ0FBQyxhQUFhLENBQUMsY0FBYyxDQUFDLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQztBQUNwRjs7WUFFWSxJQUFJLElBQUksQ0FBQyxRQUFRLENBQUMsSUFBSSxJQUFJLEdBQUcsRUFBRTtnQkFDM0IsSUFBSSxHQUFHLDRCQUE0QixDQUFDO2FBQ3ZDLE1BQU0sSUFBSSxHQUFHLElBQUksSUFBSSxDQUFDLFFBQVEsQ0FBQyxJQUFJLElBQUksSUFBSSxDQUFDLFFBQVEsQ0FBQyxJQUFJLEdBQUcsR0FBRyxFQUFFO2dCQUM5RCxJQUFJLEdBQUcsd0JBQXdCLENBQUM7YUFDbkMsTUFBTSxJQUFJLFdBQVcsSUFBSSxXQUFXLENBQUMsT0FBTyxDQUFDLE9BQU8sQ0FBQyxJQUFJLENBQUMsRUFBRTtnQkFDekQsSUFBSSxHQUFHLHFCQUFxQixDQUFDO2FBQ2hDLE1BQU0sSUFBSSxXQUFXLElBQUksV0FBVyxDQUFDLE9BQU8sQ0FBQyxZQUFZLENBQUMsSUFBSSxDQUFDLEVBQUU7Z0JBQzlELElBQUksR0FBRyxrQkFBa0IsQ0FBQzthQUM3QixNQUFNLElBQUksV0FBVyxJQUFJLFdBQVcsQ0FBQyxPQUFPLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQyxFQUFFO2dCQUN2RCxJQUFJLEdBQUcsbUJBQW1CLENBQUM7YUFDOUIsTUFBTSxJQUFJLFdBQVcsSUFBSSxXQUFXLENBQUMsT0FBTyxDQUFDLE1BQU0sQ0FBQyxJQUFJLENBQUMsRUFBRTtnQkFDeEQsSUFBSSxHQUFHLHdCQUF3QixDQUFDO2FBQ25DO1NBQ0o7UUFDRCxJQUFJLENBQUMsSUFBSSxFQUFFO1lBQ1AsSUFBSSxHQUFHLHFCQUFxQixDQUFDO0FBQ3pDLFNBQVM7QUFDVDs7UUFFUSxJQUFJLElBQUksZ0JBQWdCLENBQUM7UUFDekIsT0FBTyxvQkFBQSxJQUFHLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLFVBQVcsQ0FBQSxFQUFBO1lBQzVCLG9CQUFBLEtBQUksRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUUsSUFBTSxDQUFNLENBQUE7UUFDM0IsQ0FBQSxDQUFDO0tBQ1Q7QUFDTCxDQUFDLENBQUMsQ0FBQzs7QUFFSCxJQUFJLGdDQUFnQywwQkFBQTtJQUNoQyxPQUFPLEVBQUU7UUFDTCxXQUFXLEVBQUUsWUFBWTtZQUNyQixPQUFPLG9CQUFBLElBQUcsRUFBQSxDQUFBLENBQUMsR0FBQSxFQUFHLENBQUMsTUFBQSxFQUFNLENBQUMsU0FBQSxFQUFTLENBQUMsVUFBVyxDQUFBLEVBQUEsTUFBUyxDQUFBLENBQUM7U0FDeEQ7S0FDSjtJQUNELE1BQU0sRUFBRSxZQUFZO1FBQ2hCLElBQUksSUFBSSxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDO1FBQzNCLE9BQU8sb0JBQUEsSUFBRyxFQUFBLENBQUEsQ0FBQyxTQUFBLEVBQVMsQ0FBQyxVQUFXLENBQUEsRUFBQTtZQUMzQixJQUFJLENBQUMsT0FBTyxDQUFDLFNBQVMsR0FBRyxvQkFBQSxHQUFFLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLCtCQUFnQyxDQUFJLENBQUEsR0FBRyxJQUFJLEVBQUM7WUFDbEYsSUFBSSxDQUFDLFdBQVcsR0FBRyxvQkFBQSxHQUFFLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLDhCQUErQixDQUFJLENBQUEsR0FBRyxJQUFJLEVBQUM7WUFDM0UsSUFBSSxDQUFDLE9BQU8sQ0FBQyxNQUFNLEdBQUcsS0FBSyxHQUFHLElBQUksQ0FBQyxPQUFPLENBQUMsSUFBSSxHQUFHLElBQUksQ0FBQyxPQUFPLENBQUMsSUFBSztRQUNwRSxDQUFBLENBQUM7S0FDVDtBQUNMLENBQUMsQ0FBQyxDQUFDO0FBQ0g7O0FBRUEsSUFBSSxrQ0FBa0MsNEJBQUE7SUFDbEMsT0FBTyxFQUFFO1FBQ0wsV0FBVyxFQUFFLFlBQVk7WUFDckIsT0FBTyxvQkFBQSxJQUFHLEVBQUEsQ0FBQSxDQUFDLEdBQUEsRUFBRyxDQUFDLFFBQUEsRUFBUSxDQUFDLFNBQUEsRUFBUyxDQUFDLFlBQWEsQ0FBQSxFQUFBLFFBQVcsQ0FBQSxDQUFDO1NBQzlEO0tBQ0o7SUFDRCxNQUFNLEVBQUUsWUFBWTtRQUNoQixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQztRQUMzQixPQUFPLG9CQUFBLElBQUcsRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMsWUFBYSxDQUFBLEVBQUMsSUFBSSxDQUFDLE9BQU8sQ0FBQyxNQUFZLENBQUEsQ0FBQztLQUNoRTtBQUNMLENBQUMsQ0FBQyxDQUFDO0FBQ0g7O0FBRUEsSUFBSSxrQ0FBa0MsNEJBQUE7SUFDbEMsT0FBTyxFQUFFO1FBQ0wsV0FBVyxFQUFFLFlBQVk7WUFDckIsT0FBTyxvQkFBQSxJQUFHLEVBQUEsQ0FBQSxDQUFDLEdBQUEsRUFBRyxDQUFDLFFBQUEsRUFBUSxDQUFDLFNBQUEsRUFBUyxDQUFDLFlBQWEsQ0FBQSxFQUFBLFFBQVcsQ0FBQSxDQUFDO1NBQzlEO0tBQ0o7SUFDRCxNQUFNLEVBQUUsWUFBWTtRQUNoQixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQztRQUMzQixJQUFJLE1BQU0sQ0FBQztRQUNYLElBQUksSUFBSSxDQUFDLFFBQVEsRUFBRTtZQUNmLE1BQU0sR0FBRyxJQUFJLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQztTQUMvQixNQUFNO1lBQ0gsTUFBTSxHQUFHLElBQUksQ0FBQztTQUNqQjtRQUNELE9BQU8sb0JBQUEsSUFBRyxFQUFBLENBQUEsQ0FBQyxTQUFBLEVBQVMsQ0FBQyxZQUFhLENBQUEsRUFBQyxNQUFZLENBQUEsQ0FBQztLQUNuRDtBQUNMLENBQUMsQ0FBQyxDQUFDO0FBQ0g7O0FBRUEsSUFBSSxnQ0FBZ0MsMEJBQUE7SUFDaEMsT0FBTyxFQUFFO1FBQ0wsV0FBVyxFQUFFLFlBQVk7WUFDckIsT0FBTyxvQkFBQSxJQUFHLEVBQUEsQ0FBQSxDQUFDLEdBQUEsRUFBRyxDQUFDLE1BQUEsRUFBTSxDQUFDLFNBQUEsRUFBUyxDQUFDLFVBQVcsQ0FBQSxFQUFBLE1BQVMsQ0FBQSxDQUFDO1NBQ3hEO0tBQ0o7SUFDRCxNQUFNLEVBQUUsWUFBWTtBQUN4QixRQUFRLElBQUksSUFBSSxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDOztRQUUzQixJQUFJLEtBQUssR0FBRyxJQUFJLENBQUMsT0FBTyxDQUFDLGFBQWEsQ0FBQztRQUN2QyxJQUFJLElBQUksQ0FBQyxRQUFRLEVBQUU7WUFDZixLQUFLLElBQUksSUFBSSxDQUFDLFFBQVEsQ0FBQyxhQUFhLElBQUksQ0FBQyxDQUFDO1NBQzdDO1FBQ0QsSUFBSSxJQUFJLEdBQUcsS0FBSyxDQUFDLFVBQVUsQ0FBQyxLQUFLLENBQUMsQ0FBQztRQUNuQyxPQUFPLG9CQUFBLElBQUcsRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMsVUFBVyxDQUFBLEVBQUMsSUFBVSxDQUFBLENBQUM7S0FDL0M7QUFDTCxDQUFDLENBQUMsQ0FBQztBQUNIOztBQUVBLElBQUksZ0NBQWdDLDBCQUFBO0lBQ2hDLE9BQU8sRUFBRTtRQUNMLFdBQVcsRUFBRSxZQUFZO1lBQ3JCLE9BQU8sb0JBQUEsSUFBRyxFQUFBLENBQUEsQ0FBQyxHQUFBLEVBQUcsQ0FBQyxNQUFBLEVBQU0sQ0FBQyxTQUFBLEVBQVMsQ0FBQyxVQUFXLENBQUEsRUFBQSxNQUFTLENBQUEsQ0FBQztTQUN4RDtLQUNKO0lBQ0QsTUFBTSxFQUFFLFlBQVk7UUFDaEIsSUFBSSxJQUFJLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUM7UUFDM0IsSUFBSSxJQUFJLENBQUM7UUFDVCxJQUFJLElBQUksQ0FBQyxRQUFRLEVBQUU7WUFDZixJQUFJLEdBQUcsS0FBSyxDQUFDLGVBQWUsQ0FBQyxJQUFJLElBQUksSUFBSSxDQUFDLFFBQVEsQ0FBQyxhQUFhLEdBQUcsSUFBSSxDQUFDLE9BQU8sQ0FBQyxlQUFlLENBQUMsQ0FBQyxDQUFDO1NBQ3JHLE1BQU07WUFDSCxJQUFJLEdBQUcsS0FBSyxDQUFDO1NBQ2hCO1FBQ0QsT0FBTyxvQkFBQSxJQUFHLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLFVBQVcsQ0FBQSxFQUFDLElBQVUsQ0FBQSxDQUFDO0tBQy9DO0FBQ0wsQ0FBQyxDQUFDLENBQUM7QUFDSDs7QUFFQSxJQUFJLFdBQVcsR0FBRztJQUNkLFNBQVM7SUFDVCxVQUFVO0lBQ1YsVUFBVTtJQUNWLFlBQVk7SUFDWixZQUFZO0lBQ1osVUFBVTtBQUNkLElBQUksVUFBVSxDQUFDLENBQUM7QUFDaEI7O0FBRUEsTUFBTSxDQUFDLE9BQU8sR0FBRyxXQUFXLENBQUM7QUFDN0I7Ozs7O0FDbEtBLElBQUksS0FBSyxHQUFHLE9BQU8sQ0FBQyxPQUFPLENBQUMsQ0FBQztBQUM3QixJQUFJLE1BQU0sR0FBRyxPQUFPLENBQUMsYUFBYSxDQUFDLENBQUM7QUFDcEMsSUFBSSxrQkFBa0IsR0FBRyxPQUFPLENBQUMsb0JBQW9CLENBQUMsQ0FBQztBQUN2RCxJQUFJLGlCQUFpQixHQUFHLE9BQU8sQ0FBQyx3QkFBd0IsQ0FBQyxDQUFDOztBQUUxRCxJQUFJLDZCQUE2Qix1QkFBQTtJQUM3QixNQUFNLEVBQUUsWUFBWTtRQUNoQixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQztRQUMzQixJQUFJLE9BQU8sR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLE9BQU8sQ0FBQyxHQUFHLENBQUMsVUFBVSxNQUFNLEVBQUU7WUFDbkQsT0FBTyxvQkFBQyxNQUFNLEVBQUEsQ0FBQSxDQUFDLEdBQUEsRUFBRyxDQUFFLE1BQU0sQ0FBQyxXQUFXLEVBQUMsQ0FBQyxJQUFBLEVBQUksQ0FBRSxJQUFLLENBQUUsQ0FBQSxDQUFDO1NBQ3pELENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUM7UUFDZCxJQUFJLFNBQVMsR0FBRyxFQUFFLENBQUM7UUFDbkIsSUFBSSxJQUFJLENBQUMsS0FBSyxDQUFDLFFBQVEsRUFBRTtZQUNyQixTQUFTLElBQUksV0FBVyxDQUFDO1NBQzVCO1FBQ0QsSUFBSSxJQUFJLENBQUMsS0FBSyxDQUFDLFdBQVcsRUFBRTtZQUN4QixTQUFTLElBQUksY0FBYyxDQUFDO1NBQy9CO1FBQ0QsSUFBSSxJQUFJLENBQUMsV0FBVyxFQUFFO1lBQ2xCLFNBQVMsSUFBSSxjQUFjLENBQUM7U0FDL0I7UUFDRCxJQUFJLElBQUksQ0FBQyxPQUFPLEVBQUU7WUFDZCxTQUFTLElBQUksY0FBYyxDQUFDO1NBQy9CO1FBQ0QsSUFBSSxJQUFJLENBQUMsUUFBUSxFQUFFO1lBQ2YsU0FBUyxJQUFJLGVBQWUsQ0FBQztBQUN6QyxTQUFTOztRQUVEO1lBQ0ksb0JBQUEsSUFBRyxFQUFBLENBQUEsQ0FBQyxTQUFBLEVBQVMsQ0FBRSxTQUFTLEVBQUMsQ0FBQyxPQUFBLEVBQU8sQ0FBRSxJQUFJLENBQUMsS0FBSyxDQUFDLFVBQVUsQ0FBQyxJQUFJLENBQUMsSUFBSSxFQUFFLElBQUksQ0FBRyxDQUFBLEVBQUE7Z0JBQ3RFLE9BQVE7WUFDUixDQUFBLEVBQUU7S0FDZDtJQUNELHFCQUFxQixFQUFFLFVBQVUsU0FBUyxFQUFFO0FBQ2hELFFBQVEsT0FBTyxJQUFJLENBQUM7QUFDcEI7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7S0FFSztBQUNMLENBQUMsQ0FBQyxDQUFDOztBQUVILElBQUksbUNBQW1DLDZCQUFBO0lBQ25DLE1BQU0sRUFBRSxZQUFZO1FBQ2hCLElBQUksT0FBTyxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsT0FBTyxDQUFDLEdBQUcsQ0FBQyxVQUFVLE1BQU0sRUFBRTtZQUNuRCxPQUFPLE1BQU0sQ0FBQyxXQUFXLEVBQUUsQ0FBQztTQUMvQixDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDO1FBQ2QsT0FBTyxvQkFBQSxPQUFNLEVBQUEsSUFBQyxFQUFBO1lBQ1Ysb0JBQUEsSUFBRyxFQUFBLElBQUMsRUFBQyxPQUFhLENBQUE7UUFDZCxDQUFBLENBQUM7S0FDWjtBQUNMLENBQUMsQ0FBQyxDQUFDO0FBQ0g7O0FBRUEsSUFBSSxVQUFVLEdBQUcsRUFBRSxDQUFDOztBQUVwQixJQUFJLCtCQUErQix5QkFBQTtJQUMvQixNQUFNLEVBQUUsQ0FBQyxNQUFNLENBQUMsZUFBZSxFQUFFLE1BQU0sQ0FBQyxlQUFlLEVBQUUsa0JBQWtCLENBQUM7SUFDNUUsZUFBZSxFQUFFLFlBQVk7UUFDekIsT0FBTztZQUNILE9BQU8sRUFBRSxpQkFBaUI7U0FDN0IsQ0FBQztLQUNMO0lBQ0Qsa0JBQWtCLEVBQUUsWUFBWTtRQUM1QixJQUFJLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxFQUFFO1lBQ2pCLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLFdBQVcsQ0FBQyxLQUFLLEVBQUUsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDO1lBQ2xELElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLFdBQVcsQ0FBQyxRQUFRLEVBQUUsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDO1lBQ3JELElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLFdBQVcsQ0FBQyxRQUFRLEVBQUUsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDO1lBQ3JELElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLFdBQVcsQ0FBQyxhQUFhLEVBQUUsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDO1NBQzdEO0tBQ0o7SUFDRCx5QkFBeUIsRUFBRSxVQUFVLFNBQVMsRUFBRTtRQUM1QyxJQUFJLFNBQVMsQ0FBQyxJQUFJLEtBQUssSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLEVBQUU7WUFDcEMsSUFBSSxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksRUFBRTtnQkFDakIsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsY0FBYyxDQUFDLEtBQUssQ0FBQyxDQUFDO2dCQUN0QyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQyxjQUFjLENBQUMsUUFBUSxDQUFDLENBQUM7Z0JBQ3pDLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLGNBQWMsQ0FBQyxRQUFRLENBQUMsQ0FBQztnQkFDekMsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsY0FBYyxDQUFDLGFBQWEsQ0FBQyxDQUFDO2FBQ2pEO1lBQ0QsU0FBUyxDQUFDLElBQUksQ0FBQyxXQUFXLENBQUMsS0FBSyxFQUFFLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQztZQUNqRCxTQUFTLENBQUMsSUFBSSxDQUFDLFdBQVcsQ0FBQyxRQUFRLEVBQUUsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDO1lBQ3BELFNBQVMsQ0FBQyxJQUFJLENBQUMsV0FBVyxDQUFDLFFBQVEsRUFBRSxJQUFJLENBQUMsUUFBUSxDQUFDLENBQUM7WUFDcEQsU0FBUyxDQUFDLElBQUksQ0FBQyxXQUFXLENBQUMsYUFBYSxFQUFFLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQztTQUM1RDtLQUNKO0lBQ0QsZUFBZSxFQUFFLFlBQVk7UUFDekIsT0FBTztZQUNILFNBQVMsRUFBRSxVQUFVO1NBQ3hCLENBQUM7S0FDTDtJQUNELGlCQUFpQixFQUFFLFlBQVk7UUFDM0IsSUFBSSxDQUFDLFVBQVUsRUFBRSxDQUFDO1FBQ2xCLElBQUksQ0FBQyxRQUFRLEVBQUUsQ0FBQztLQUNuQjtJQUNELFFBQVEsRUFBRSxZQUFZO1FBQ2xCLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQztLQUN0QjtJQUNELGNBQWMsRUFBRSxVQUFVLElBQUksRUFBRTtRQUM1QixJQUFJLENBQUMsaUJBQWlCO1lBQ2xCLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUM7WUFDM0IsSUFBSSxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsVUFBVSxFQUFFLENBQUMsU0FBUztTQUN4QyxDQUFDO0tBQ0w7SUFDRCxTQUFTLEVBQUUsVUFBVSxJQUFJLEVBQUU7UUFDdkIsSUFBSSxRQUFRLElBQUksSUFBSSxLQUFLLElBQUksQ0FBQyxLQUFLLENBQUMsUUFBUSxDQUFDLENBQUM7QUFDdEQsUUFBUSxJQUFJLFdBQVc7O1lBRVgsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsVUFBVTtZQUMxQixJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQyxVQUFVLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQztBQUMvQyxhQUFhLENBQUM7O1FBRU4sT0FBTyxvQkFBQyxPQUFPLEVBQUEsQ0FBQSxDQUFDLEdBQUEsRUFBRyxDQUFFLElBQUksQ0FBQyxFQUFFLEVBQUM7WUFDekIsR0FBQSxFQUFHLENBQUUsSUFBSSxDQUFDLEVBQUUsRUFBQztZQUNiLElBQUEsRUFBSSxDQUFFLElBQUksRUFBQztZQUNYLE9BQUEsRUFBTyxDQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsT0FBTyxFQUFDO1lBQzVCLFFBQUEsRUFBUSxDQUFFLFFBQVEsRUFBQztZQUNuQixXQUFBLEVBQVcsQ0FBRSxXQUFXLEVBQUM7WUFDekIsVUFBQSxFQUFVLENBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxVQUFXLENBQUE7UUFDcEMsQ0FBQSxDQUFDO0tBQ047QUFDTCxJQUFJLE1BQU0sRUFBRSxZQUFZOztBQUV4QixRQUFRLElBQUksS0FBSyxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLElBQUksR0FBRyxFQUFFLENBQUM7O0FBRWhFLFFBQVEsSUFBSSxJQUFJLEdBQUcsSUFBSSxDQUFDLFVBQVUsQ0FBQyxLQUFLLENBQUMsQ0FBQzs7UUFFbEM7WUFDSSxvQkFBQSxLQUFJLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLFlBQUEsRUFBWSxDQUFDLFFBQUEsRUFBUSxDQUFFLElBQUksQ0FBQyxpQkFBbUIsQ0FBQSxFQUFBO2dCQUMxRCxvQkFBQSxPQUFNLEVBQUEsSUFBQyxFQUFBO29CQUNILG9CQUFDLGFBQWEsRUFBQSxDQUFBLENBQUMsR0FBQSxFQUFHLENBQUMsTUFBQSxFQUFNO3dCQUNyQixPQUFBLEVBQU8sQ0FBRSxJQUFJLENBQUMsS0FBSyxDQUFDLE9BQVEsQ0FBRSxDQUFBLEVBQUE7b0JBQ2xDLG9CQUFBLE9BQU0sRUFBQSxDQUFBLENBQUMsR0FBQSxFQUFHLENBQUMsTUFBTyxDQUFBLEVBQUE7d0JBQ2IsQ0FBQyxJQUFJLENBQUMsaUJBQWlCLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxFQUFBLENBQUU7d0JBQ3ZDLElBQUksRUFBQzt3QkFDTCxDQUFDLElBQUksQ0FBQyxvQkFBb0IsQ0FBQyxLQUFLLENBQUMsTUFBTSxFQUFHO29CQUN2QyxDQUFBO2dCQUNKLENBQUE7WUFDTixDQUFBO1VBQ1I7S0FDTDtBQUNMLENBQUMsQ0FBQyxDQUFDOztBQUVILE1BQU0sQ0FBQyxPQUFPLEdBQUcsU0FBUyxDQUFDOzs7O0FDaEozQixJQUFJLEtBQUssR0FBRyxPQUFPLENBQUMsT0FBTyxDQUFDLENBQUM7O0FBRTdCLElBQUksNEJBQTRCLHNCQUFBO0lBQzVCLE1BQU0sRUFBRSxZQUFZO1FBQ2hCLElBQUksSUFBSSxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQztRQUNwQyxJQUFJLFNBQVMsR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLFFBQVEsQ0FBQyxTQUFTLENBQUM7UUFDOUM7WUFDSSxvQkFBQSxRQUFPLEVBQUEsSUFBQyxFQUFBO2dCQUNILElBQUksSUFBSSxTQUFTLEdBQUcsb0JBQUEsTUFBSyxFQUFBLENBQUEsQ0FBQyxTQUFBLEVBQVMsQ0FBQyxxQkFBc0IsQ0FBQSxFQUFDLElBQUksRUFBQyxPQUFZLENBQUEsR0FBRyxJQUFJLEVBQUM7QUFBQSxnQkFBQSxHQUFBLEVBQUE7QUFBQSxnQkFFcEYsU0FBUyxHQUFHLG9CQUFBLE1BQUssRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMscUJBQXNCLENBQUEsRUFBQSxhQUFBLEVBQVksU0FBaUIsQ0FBQSxHQUFHLElBQUs7WUFDbkYsQ0FBQTtVQUNYO0tBQ0w7QUFDTCxDQUFDLENBQUMsQ0FBQzs7QUFFSCxNQUFNLENBQUMsT0FBTyxHQUFHLE1BQU07OztBQ2hCdkIsSUFBSSxLQUFLLEdBQUcsT0FBTyxDQUFDLE9BQU8sQ0FBQyxDQUFDO0FBQzdCLElBQUksQ0FBQyxHQUFHLE9BQU8sQ0FBQyxRQUFRLENBQUMsQ0FBQzs7QUFFMUIsSUFBSSxJQUFJLEdBQUcsT0FBTyxDQUFDLGlCQUFpQixDQUFDLENBQUM7QUFDdEMsSUFBSSxLQUFLLEdBQUcsT0FBTyxDQUFDLGFBQWEsQ0FBQyxDQUFDOztBQUVuQyxJQUFJLE1BQU0sR0FBRyxPQUFPLENBQUMsYUFBYSxDQUFDLENBQUM7QUFDcEMsSUFBSSxPQUFPLEdBQUcsT0FBTyxDQUFDLGVBQWUsQ0FBQyxDQUFDOztBQUV2QyxJQUFJLGdDQUFnQywwQkFBQTtJQUNoQyxPQUFPLEVBQUU7UUFDTCxHQUFHLEVBQUUsS0FBSztRQUNWLEdBQUcsRUFBRSxLQUFLO0tBQ2I7SUFDRCxrQkFBa0IsRUFBRSxZQUFZO1FBQzVCLElBQUksQ0FBQyxVQUFVLENBQUMsR0FBRyxFQUFFO1lBQ2pCLFVBQVUsQ0FBQyxHQUFHLEdBQUcsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxjQUFjLENBQUMsQ0FBQyxJQUFJLENBQUMsVUFBVSxHQUFHLEVBQUU7Z0JBQzNELFVBQVUsQ0FBQyxHQUFHLEdBQUcsR0FBRyxDQUFDO2dCQUNyQixVQUFVLENBQUMsR0FBRyxHQUFHLEtBQUssQ0FBQzthQUMxQixDQUFDLENBQUM7U0FDTjtRQUNELElBQUksVUFBVSxDQUFDLEdBQUcsRUFBRTtZQUNoQixVQUFVLENBQUMsR0FBRyxDQUFDLElBQUksQ0FBQyxZQUFZO2dCQUM1QixJQUFJLENBQUMsV0FBVyxFQUFFLENBQUM7YUFDdEIsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQztTQUNqQjtLQUNKO0lBQ0QsTUFBTSxFQUFFLFlBQVk7UUFDaEIsSUFBSSxDQUFDLFVBQVUsQ0FBQyxHQUFHLEVBQUU7WUFDakIsT0FBTyxvQkFBQSxHQUFFLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLHVCQUF3QixDQUFJLENBQUEsQ0FBQztTQUNwRCxNQUFNO1lBQ0gsSUFBSSxRQUFRLEdBQUcsVUFBVSxDQUFDLEdBQUcsQ0FBQyxRQUFRLENBQUMsR0FBRyxDQUFDLFVBQVUsQ0FBQyxFQUFFO2dCQUNwRCxPQUFPLG9CQUFBLElBQUcsRUFBQSxJQUFDLEVBQUE7b0JBQ1Asb0JBQUEsSUFBRyxFQUFBLElBQUMsRUFBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsT0FBTyxDQUFDLEdBQUcsRUFBRSxRQUFRLENBQU8sQ0FBQSxFQUFBO29CQUN0QyxvQkFBQSxJQUFHLEVBQUEsSUFBQyxFQUFDLENBQUMsQ0FBQyxDQUFDLENBQU8sQ0FBQTtnQkFDZCxDQUFBLENBQUM7YUFDVCxDQUFDLENBQUM7WUFDSCxRQUFRLENBQUMsSUFBSSxDQUFDLG9CQUFBLElBQUcsRUFBQSxJQUFDLEVBQUE7Z0JBQ2Qsb0JBQUEsSUFBRyxFQUFBLENBQUEsQ0FBQyxPQUFBLEVBQU8sQ0FBQyxHQUFJLENBQUEsRUFBQTtvQkFDWixvQkFBQSxHQUFFLEVBQUEsQ0FBQSxDQUFDLElBQUEsRUFBSSxDQUFDLGlEQUFBLEVBQWlEO3dCQUNyRCxNQUFBLEVBQU0sQ0FBQyxRQUFTLENBQUEsRUFBQTt3QkFDaEIsb0JBQUEsR0FBRSxFQUFBLENBQUEsQ0FBQyxTQUFBLEVBQVMsQ0FBQyxxQkFBc0IsQ0FBSSxDQUFBLEVBQUE7QUFBQSxvQkFBQSxrQkFDbEIsQ0FBQTtnQkFDeEIsQ0FBQTtZQUNKLENBQUEsQ0FBQyxDQUFDO1lBQ1AsT0FBTyxvQkFBQSxPQUFNLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLHVCQUF3QixDQUFBLEVBQUE7Z0JBQzVDLG9CQUFBLE9BQU0sRUFBQSxJQUFDLEVBQUMsUUFBaUIsQ0FBQTtZQUNyQixDQUFBLENBQUM7U0FDWjtLQUNKO0NBQ0osQ0FBQyxDQUFDO0FBQ0gsSUFBSSxpQ0FBaUMsMkJBQUE7QUFDckMsSUFBSSxlQUFlLEVBQUUsWUFBWTtBQUNqQztBQUNBOztRQUVRLE9BQU87WUFDSCxLQUFLLEVBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxLQUFLO1lBQ3ZCLEtBQUssRUFBRSxLQUFLO1lBQ1osVUFBVSxFQUFFLEtBQUs7U0FDcEIsQ0FBQztLQUNMO0lBQ0QseUJBQXlCLEVBQUUsVUFBVSxTQUFTLEVBQUU7UUFDNUMsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDLEtBQUssRUFBRSxTQUFTLENBQUMsS0FBSyxDQUFDLENBQUMsQ0FBQztLQUMzQztJQUNELFFBQVEsRUFBRSxVQUFVLENBQUMsRUFBRTtRQUNuQixJQUFJLFNBQVMsR0FBRyxDQUFDLENBQUMsTUFBTSxDQUFDLEtBQUssQ0FBQztRQUMvQixJQUFJLENBQUMsUUFBUSxDQUFDO1lBQ1YsS0FBSyxFQUFFLFNBQVM7QUFDNUIsU0FBUyxDQUFDLENBQUM7O1FBRUgsSUFBSSxJQUFJLENBQUMsT0FBTyxDQUFDLFNBQVMsQ0FBQyxFQUFFO1lBQ3pCLElBQUksQ0FBQyxLQUFLLENBQUMsUUFBUSxDQUFDLFNBQVMsQ0FBQyxDQUFDO1NBQ2xDO0tBQ0o7SUFDRCxPQUFPLEVBQUUsVUFBVSxJQUFJLEVBQUU7UUFDckIsSUFBSTtZQUNBLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxJQUFJLElBQUksQ0FBQyxLQUFLLENBQUMsS0FBSyxDQUFDLENBQUM7WUFDckMsT0FBTyxJQUFJLENBQUM7U0FDZixDQUFDLE9BQU8sQ0FBQyxFQUFFO1lBQ1IsT0FBTyxLQUFLLENBQUM7U0FDaEI7S0FDSjtJQUNELE9BQU8sRUFBRSxZQUFZO1FBQ2pCLElBQUksSUFBSSxDQUFDO1FBQ1QsSUFBSTtZQUNBLElBQUksR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsS0FBSyxDQUFDLENBQUMsSUFBSSxDQUFDO1NBQzVDLENBQUMsT0FBTyxDQUFDLEVBQUU7WUFDUixJQUFJLEdBQUcsRUFBRSxHQUFHLENBQUMsQ0FBQztTQUNqQjtRQUNELElBQUksSUFBSSxLQUFLLE1BQU0sRUFBRTtZQUNqQixPQUFPLElBQUksQ0FBQztTQUNmLE1BQU07WUFDSDtnQkFDSSxvQkFBQyxVQUFVLEVBQUEsSUFBRSxDQUFBO2NBQ2Y7U0FDTDtLQUNKO0lBQ0QsT0FBTyxFQUFFLFlBQVk7UUFDakIsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDLEtBQUssRUFBRSxJQUFJLENBQUMsQ0FBQyxDQUFDO0tBQ2hDO0lBQ0QsTUFBTSxFQUFFLFlBQVk7UUFDaEIsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDLEtBQUssRUFBRSxLQUFLLENBQUMsQ0FBQyxDQUFDO0tBQ2pDO0lBQ0QsWUFBWSxFQUFFLFlBQVk7UUFDdEIsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDLFVBQVUsRUFBRSxJQUFJLENBQUMsQ0FBQyxDQUFDO0tBQ3JDO0lBQ0QsWUFBWSxFQUFFLFlBQVk7UUFDdEIsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDLFVBQVUsRUFBRSxLQUFLLENBQUMsQ0FBQyxDQUFDO0tBQ3RDO0lBQ0QsU0FBUyxFQUFFLFVBQVUsQ0FBQyxFQUFFO1FBQ3BCLElBQUksQ0FBQyxDQUFDLE9BQU8sS0FBSyxLQUFLLENBQUMsR0FBRyxDQUFDLEdBQUcsSUFBSSxDQUFDLENBQUMsT0FBTyxLQUFLLEtBQUssQ0FBQyxHQUFHLENBQUMsS0FBSyxFQUFFO0FBQzFFLFlBQVksSUFBSSxDQUFDLElBQUksRUFBRSxDQUFDOztZQUVaLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQyxVQUFVLEVBQUUsS0FBSyxDQUFDLENBQUMsQ0FBQztTQUN0QztLQUNKO0lBQ0QsSUFBSSxFQUFFLFlBQVk7UUFDZCxJQUFJLENBQUMsSUFBSSxDQUFDLEtBQUssQ0FBQyxVQUFVLEVBQUUsQ0FBQyxJQUFJLEVBQUUsQ0FBQztLQUN2QztJQUNELEtBQUssRUFBRSxZQUFZO1FBQ2YsSUFBSSxDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsVUFBVSxFQUFFLENBQUMsTUFBTSxFQUFFLENBQUM7S0FDekM7SUFDRCxNQUFNLEVBQUUsWUFBWTtRQUNoQixJQUFJLE9BQU8sR0FBRyxJQUFJLENBQUMsT0FBTyxFQUFFLENBQUM7UUFDN0IsSUFBSSxJQUFJLEdBQUcsY0FBYyxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDO0FBQ3BELFFBQVEsSUFBSSxjQUFjLEdBQUcsMEJBQTBCLElBQUksT0FBTyxHQUFHLEVBQUUsR0FBRyxZQUFZLENBQUMsQ0FBQzs7UUFFaEYsSUFBSSxPQUFPLENBQUM7UUFDWixJQUFJLElBQUksQ0FBQyxLQUFLLENBQUMsS0FBSyxJQUFJLElBQUksQ0FBQyxLQUFLLENBQUMsVUFBVSxFQUFFO1lBQzNDLE9BQU87Z0JBQ0gsb0JBQUEsS0FBSSxFQUFBLENBQUEsQ0FBQyxTQUFBLEVBQVMsQ0FBQyxnQkFBQSxFQUFnQixDQUFDLFlBQUEsRUFBWSxDQUFFLElBQUksQ0FBQyxZQUFZLEVBQUMsQ0FBQyxZQUFBLEVBQVksQ0FBRSxJQUFJLENBQUMsWUFBYyxDQUFBLEVBQUE7b0JBQzlGLG9CQUFBLEtBQUksRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMsT0FBUSxDQUFNLENBQUEsRUFBQTtvQkFDN0Isb0JBQUEsS0FBSSxFQUFBLENBQUEsQ0FBQyxTQUFBLEVBQVMsQ0FBQyxpQkFBa0IsQ0FBQSxFQUFBO29CQUNoQyxJQUFJLENBQUMsT0FBTyxFQUFHO29CQUNWLENBQUE7Z0JBQ0osQ0FBQTthQUNULENBQUM7QUFDZCxTQUFTOztRQUVEO1lBQ0ksb0JBQUEsS0FBSSxFQUFBLENBQUEsQ0FBQyxTQUFBLEVBQVMsQ0FBRSxjQUFnQixDQUFBLEVBQUE7Z0JBQzVCLG9CQUFBLE1BQUssRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMsbUJBQW9CLENBQUEsRUFBQTtvQkFDaEMsb0JBQUEsR0FBRSxFQUFBLENBQUEsQ0FBQyxTQUFBLEVBQVMsQ0FBRSxJQUFJLEVBQUMsQ0FBQyxLQUFBLEVBQUssQ0FBRSxDQUFDLEtBQUssRUFBRSxJQUFJLENBQUMsS0FBSyxDQUFDLEtBQUssQ0FBRyxDQUFJLENBQUE7Z0JBQ3ZELENBQUEsRUFBQTtnQkFDUCxvQkFBQSxPQUFNLEVBQUEsQ0FBQSxDQUFDLElBQUEsRUFBSSxDQUFDLE1BQUEsRUFBTSxDQUFDLFdBQUEsRUFBVyxDQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsV0FBVyxFQUFDLENBQUMsU0FBQSxFQUFTLENBQUMsY0FBQSxFQUFjO29CQUM1RSxHQUFBLEVBQUcsQ0FBQyxPQUFBLEVBQU87b0JBQ1gsUUFBQSxFQUFRLENBQUUsSUFBSSxDQUFDLFFBQVEsRUFBQztvQkFDeEIsT0FBQSxFQUFPLENBQUUsSUFBSSxDQUFDLE9BQU8sRUFBQztvQkFDdEIsTUFBQSxFQUFNLENBQUUsSUFBSSxDQUFDLE1BQU0sRUFBQztvQkFDcEIsU0FBQSxFQUFTLENBQUUsSUFBSSxDQUFDLFNBQVMsRUFBQztvQkFDMUIsS0FBQSxFQUFLLENBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxLQUFNLENBQUUsQ0FBQSxFQUFBO2dCQUM3QixPQUFRO1lBQ1AsQ0FBQTtVQUNSO0tBQ0w7QUFDTCxDQUFDLENBQUMsQ0FBQzs7QUFFSCxJQUFJLDhCQUE4Qix3QkFBQTtJQUM5QixNQUFNLEVBQUUsQ0FBQyxNQUFNLENBQUMsVUFBVSxFQUFFLE1BQU0sQ0FBQyxLQUFLLENBQUM7SUFDekMsT0FBTyxFQUFFO1FBQ0wsS0FBSyxFQUFFLE9BQU87UUFDZCxLQUFLLEVBQUUsT0FBTztLQUNqQjtJQUNELGNBQWMsRUFBRSxVQUFVLEdBQUcsRUFBRTtRQUMzQixJQUFJLENBQUMsR0FBRyxFQUFFLENBQUM7UUFDWCxDQUFDLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxHQUFHLEdBQUcsQ0FBQztRQUN0QixJQUFJLENBQUMsUUFBUSxDQUFDLENBQUMsQ0FBQyxDQUFDO0tBQ3BCO0lBQ0QsaUJBQWlCLEVBQUUsVUFBVSxHQUFHLEVBQUU7UUFDOUIsSUFBSSxDQUFDLEdBQUcsRUFBRSxDQUFDO1FBQ1gsQ0FBQyxDQUFDLEtBQUssQ0FBQyxTQUFTLENBQUMsR0FBRyxHQUFHLENBQUM7UUFDekIsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDLENBQUMsQ0FBQztLQUNwQjtJQUNELGlCQUFpQixFQUFFLFVBQVUsR0FBRyxFQUFFO1FBQzlCLGVBQWUsQ0FBQyxNQUFNLENBQUMsQ0FBQyxTQUFTLEVBQUUsR0FBRyxDQUFDLENBQUMsQ0FBQztLQUM1QztJQUNELE1BQU0sRUFBRSxZQUFZO1FBQ2hCLElBQUksTUFBTSxHQUFHLElBQUksQ0FBQyxRQUFRLEVBQUUsQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLElBQUksRUFBRSxDQUFDO1FBQ2pELElBQUksU0FBUyxHQUFHLElBQUksQ0FBQyxRQUFRLEVBQUUsQ0FBQyxLQUFLLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxDQUFDO0FBQy9ELFFBQVEsSUFBSSxTQUFTLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxRQUFRLENBQUMsU0FBUyxJQUFJLEVBQUUsQ0FBQzs7UUFFcEQ7WUFDSSxvQkFBQSxLQUFJLEVBQUEsSUFBQyxFQUFBO2dCQUNELG9CQUFBLEtBQUksRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMsVUFBVyxDQUFBLEVBQUE7b0JBQ3RCLG9CQUFDLFdBQVcsRUFBQSxDQUFBO3dCQUNSLFdBQUEsRUFBVyxDQUFDLFFBQUEsRUFBUTt3QkFDcEIsSUFBQSxFQUFJLENBQUMsUUFBQSxFQUFRO3dCQUNiLEtBQUEsRUFBSyxDQUFDLE9BQUEsRUFBTzt3QkFDYixLQUFBLEVBQUssQ0FBRSxNQUFNLEVBQUM7d0JBQ2QsUUFBQSxFQUFRLENBQUUsSUFBSSxDQUFDLGNBQWUsQ0FBQSxDQUFHLENBQUEsRUFBQTtvQkFDckMsb0JBQUMsV0FBVyxFQUFBLENBQUE7d0JBQ1IsV0FBQSxFQUFXLENBQUMsV0FBQSxFQUFXO3dCQUN2QixJQUFBLEVBQUksQ0FBQyxLQUFBLEVBQUs7d0JBQ1YsS0FBQSxFQUFLLENBQUMsb0JBQUEsRUFBb0I7d0JBQzFCLEtBQUEsRUFBSyxDQUFFLFNBQVMsRUFBQzt3QkFDakIsUUFBQSxFQUFRLENBQUUsSUFBSSxDQUFDLGlCQUFrQixDQUFFLENBQUEsRUFBQTtvQkFDdkMsb0JBQUMsV0FBVyxFQUFBLENBQUE7d0JBQ1IsV0FBQSxFQUFXLENBQUMsV0FBQSxFQUFXO3dCQUN2QixJQUFBLEVBQUksQ0FBQyxPQUFBLEVBQU87d0JBQ1osS0FBQSxFQUFLLENBQUMsb0JBQUEsRUFBb0I7d0JBQzFCLEtBQUEsRUFBSyxDQUFFLFNBQVMsRUFBQzt3QkFDakIsUUFBQSxFQUFRLENBQUUsSUFBSSxDQUFDLGlCQUFrQixDQUFFLENBQUE7Z0JBQ3JDLENBQUEsRUFBQTtnQkFDTixvQkFBQSxLQUFJLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLFVBQVcsQ0FBTSxDQUFBO1lBQzlCLENBQUE7VUFDUjtLQUNMO0FBQ0wsQ0FBQyxDQUFDLENBQUM7QUFDSDs7QUFFQSxJQUFJLDhCQUE4Qix3QkFBQTtJQUM5QixPQUFPLEVBQUU7UUFDTCxLQUFLLEVBQUUsTUFBTTtRQUNiLEtBQUssRUFBRSxPQUFPO0tBQ2pCO0lBQ0QsTUFBTSxFQUFFLENBQUMsTUFBTSxDQUFDLFVBQVUsRUFBRSxNQUFNLENBQUMsS0FBSyxDQUFDO0lBQ3pDLGNBQWMsRUFBRSxZQUFZO0FBQ2hDLFFBQVEsSUFBSSxDQUFDLEdBQUcsRUFBRSxDQUFDOztRQUVYLElBQUksSUFBSSxDQUFDLFFBQVEsRUFBRSxDQUFDLEtBQUssQ0FBQyxhQUFhLENBQUMsRUFBRTtZQUN0QyxDQUFDLENBQUMsS0FBSyxDQUFDLGFBQWEsQ0FBQyxHQUFHLFNBQVMsQ0FBQztTQUN0QyxNQUFNO1lBQ0gsQ0FBQyxDQUFDLEtBQUssQ0FBQyxhQUFhLENBQUMsR0FBRyxHQUFHLENBQUM7QUFDekMsU0FBUzs7UUFFRCxJQUFJLENBQUMsUUFBUSxDQUFDLENBQUMsQ0FBQyxDQUFDO0tBQ3BCO0lBQ0QsTUFBTSxFQUFFLFlBQVk7UUFDaEIsSUFBSSxZQUFZLEdBQUcsSUFBSSxDQUFDLFFBQVEsRUFBRSxDQUFDLEtBQUssQ0FBQyxhQUFhLENBQUMsQ0FBQztRQUN4RDtZQUNJLG9CQUFBLEtBQUksRUFBQSxJQUFDLEVBQUE7Z0JBQ0Qsb0JBQUEsUUFBTyxFQUFBLENBQUE7b0JBQ0gsU0FBQSxFQUFTLENBQUUsTUFBTSxJQUFJLFlBQVksR0FBRyxhQUFhLEdBQUcsYUFBYSxDQUFDLEVBQUM7b0JBQ25FLE9BQUEsRUFBTyxDQUFFLElBQUksQ0FBQyxjQUFnQixDQUFBLEVBQUE7b0JBQzlCLG9CQUFBLEdBQUUsRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMsZ0JBQWlCLENBQUksQ0FBQSxFQUFBO0FBQUEsZ0JBQUEsZ0JBQUE7QUFBQSxnQkFFN0IsQ0FBQSxFQUFBO2dCQUNULG9CQUFBLE1BQUssRUFBQSxJQUFDLEVBQUEsR0FBUSxDQUFBO1lBQ1osQ0FBQTtVQUNSO0tBQ0w7QUFDTCxDQUFDLENBQUMsQ0FBQztBQUNIOztBQUVBLElBQUksaUNBQWlDLDJCQUFBO0lBQ2pDLE9BQU8sRUFBRTtRQUNMLEtBQUssRUFBRSxlQUFlO1FBQ3RCLEtBQUssRUFBRSxTQUFTO0tBQ25CO0lBQ0QsTUFBTSxFQUFFLFlBQVk7UUFDaEIsT0FBTyxvQkFBQSxLQUFJLEVBQUEsSUFBQyxFQUFBLGNBQWtCLENBQUEsQ0FBQztLQUNsQztBQUNMLENBQUMsQ0FBQyxDQUFDOztBQUVILElBQUksOEJBQThCLHdCQUFBO0lBQzlCLGVBQWUsRUFBRSxZQUFZO1FBQ3pCLE9BQU87WUFDSCxZQUFZLEVBQUUsS0FBSztTQUN0QixDQUFDO0tBQ0w7SUFDRCxlQUFlLEVBQUUsVUFBVSxDQUFDLEVBQUU7UUFDMUIsQ0FBQyxDQUFDLGNBQWMsRUFBRSxDQUFDO1FBQ25CLElBQUksQ0FBQyxJQUFJLENBQUMsS0FBSyxDQUFDLFlBQVksRUFBRTtZQUMxQixJQUFJLEtBQUssR0FBRyxZQUFZO2dCQUNwQixJQUFJLENBQUMsUUFBUSxDQUFDLENBQUMsWUFBWSxFQUFFLEtBQUssQ0FBQyxDQUFDLENBQUM7Z0JBQ3JDLFFBQVEsQ0FBQyxtQkFBbUIsQ0FBQyxPQUFPLEVBQUUsS0FBSyxDQUFDLENBQUM7YUFDaEQsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUM7QUFDekIsWUFBWSxRQUFRLENBQUMsZ0JBQWdCLENBQUMsT0FBTyxFQUFFLEtBQUssQ0FBQyxDQUFDOztZQUUxQyxJQUFJLENBQUMsUUFBUSxDQUFDO2dCQUNWLFlBQVksRUFBRSxJQUFJO2FBQ3JCLENBQUMsQ0FBQztTQUNOO0tBQ0o7SUFDRCxjQUFjLEVBQUUsVUFBVSxDQUFDLEVBQUU7UUFDekIsQ0FBQyxDQUFDLGNBQWMsRUFBRSxDQUFDO1FBQ25CLElBQUksT0FBTyxDQUFDLG1CQUFtQixDQUFDLEVBQUU7WUFDOUIsT0FBTyxDQUFDLFdBQVcsQ0FBQyxLQUFLLEVBQUUsQ0FBQztTQUMvQjtLQUNKO0lBQ0QsZUFBZSxFQUFFLFVBQVUsQ0FBQyxFQUFFO1FBQzFCLENBQUMsQ0FBQyxjQUFjLEVBQUUsQ0FBQztRQUNuQixPQUFPLENBQUMsS0FBSyxDQUFDLGdDQUFnQyxDQUFDLENBQUM7S0FDbkQ7SUFDRCxlQUFlLEVBQUUsVUFBVSxDQUFDLEVBQUU7UUFDMUIsQ0FBQyxDQUFDLGNBQWMsRUFBRSxDQUFDO1FBQ25CLE9BQU8sQ0FBQyxLQUFLLENBQUMsZ0NBQWdDLENBQUMsQ0FBQztLQUNuRDtJQUNELG1CQUFtQixFQUFFLFVBQVUsQ0FBQyxFQUFFO1FBQzlCLENBQUMsQ0FBQyxjQUFjLEVBQUUsQ0FBQztRQUNuQixPQUFPLENBQUMsS0FBSyxDQUFDLG9DQUFvQyxDQUFDLENBQUM7S0FDdkQ7SUFDRCxNQUFNLEVBQUUsWUFBWTtBQUN4QixRQUFRLElBQUksYUFBYSxHQUFHLG9CQUFvQixJQUFJLElBQUksQ0FBQyxLQUFLLENBQUMsWUFBWSxHQUFHLE9BQU8sR0FBRyxFQUFFLENBQUMsQ0FBQzs7UUFFcEY7WUFDSSxvQkFBQSxLQUFJLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFFLGFBQWUsQ0FBQSxFQUFBO2dCQUMzQixvQkFBQSxHQUFFLEVBQUEsQ0FBQSxDQUFDLElBQUEsRUFBSSxDQUFDLEdBQUEsRUFBRyxDQUFDLFNBQUEsRUFBUyxDQUFDLFNBQUEsRUFBUyxDQUFDLE9BQUEsRUFBTyxDQUFFLElBQUksQ0FBQyxlQUFpQixDQUFBLEVBQUEsYUFBZSxDQUFBLEVBQUE7Z0JBQzlFLG9CQUFBLElBQUcsRUFBQSxDQUFBLENBQUMsU0FBQSxFQUFTLENBQUMsZUFBQSxFQUFlLENBQUMsSUFBQSxFQUFJLENBQUMsTUFBTyxDQUFBLEVBQUE7b0JBQ3RDLG9CQUFBLElBQUcsRUFBQSxJQUFDLEVBQUE7d0JBQ0Esb0JBQUEsR0FBRSxFQUFBLENBQUEsQ0FBQyxJQUFBLEVBQUksQ0FBQyxHQUFBLEVBQUcsQ0FBQyxPQUFBLEVBQU8sQ0FBRSxJQUFJLENBQUMsY0FBZ0IsQ0FBQSxFQUFBOzRCQUN0QyxvQkFBQSxHQUFFLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLGtCQUFtQixDQUFJLENBQUEsRUFBQTtBQUFBLDRCQUFBLEtBQUE7QUFBQSx3QkFFcEMsQ0FBQTtvQkFDSCxDQUFBLEVBQUE7b0JBQ0wsb0JBQUEsSUFBRyxFQUFBLENBQUEsQ0FBQyxJQUFBLEVBQUksQ0FBQyxjQUFBLEVBQWMsQ0FBQyxTQUFBLEVBQVMsQ0FBQyxTQUFVLENBQUssQ0FBQSxFQUFBO29CQUNqRCxvQkFBQSxJQUFHLEVBQUEsSUFBQyxFQUFBO3dCQUNBLG9CQUFBLEdBQUUsRUFBQSxDQUFBLENBQUMsSUFBQSxFQUFJLENBQUMsaUJBQUEsRUFBaUIsQ0FBQyxNQUFBLEVBQU0sQ0FBQyxRQUFTLENBQUEsRUFBQTs0QkFDdEMsb0JBQUEsR0FBRSxFQUFBLENBQUEsQ0FBQyxTQUFBLEVBQVMsQ0FBQywyQkFBNEIsQ0FBSSxDQUFBLEVBQUE7QUFBQSw0QkFBQSx5QkFBQTtBQUFBLHdCQUU3QyxDQUFBO29CQUNILENBQUE7QUFDekIsZ0JBQWlCO0FBQ2pCO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7bUJBRW9CO2dCQUNDLENBQUE7WUFDSCxDQUFBO1VBQ1I7S0FDTDtBQUNMLENBQUMsQ0FBQyxDQUFDO0FBQ0g7O0FBRUEsSUFBSSxjQUFjLEdBQUcsQ0FBQyxRQUFRLEVBQUUsUUFBUSxvQkFBb0IsQ0FBQztBQUM3RDs7QUFFQSxJQUFJLDRCQUE0QixzQkFBQTtJQUM1QixNQUFNLEVBQUUsQ0FBQyxNQUFNLENBQUMsVUFBVSxDQUFDO0lBQzNCLGVBQWUsRUFBRSxZQUFZO1FBQ3pCLE9BQU87WUFDSCxNQUFNLEVBQUUsY0FBYyxDQUFDLENBQUMsQ0FBQztTQUM1QixDQUFDO0tBQ0w7SUFDRCxXQUFXLEVBQUUsVUFBVSxNQUFNLEVBQUUsQ0FBQyxFQUFFO1FBQzlCLENBQUMsQ0FBQyxjQUFjLEVBQUUsQ0FBQztRQUNuQixJQUFJLENBQUMsV0FBVyxDQUFDLE1BQU0sQ0FBQyxLQUFLLENBQUMsQ0FBQztRQUMvQixJQUFJLENBQUMsUUFBUSxDQUFDLENBQUMsTUFBTSxFQUFFLE1BQU0sQ0FBQyxDQUFDLENBQUM7S0FDbkM7SUFDRCxNQUFNLEVBQUUsWUFBWTtRQUNoQixJQUFJLE1BQU0sR0FBRyxjQUFjLENBQUMsR0FBRyxDQUFDLFVBQVUsS0FBSyxFQUFFLENBQUMsRUFBRTtZQUNoRCxJQUFJLE9BQU8sR0FBRyxLQUFLLENBQUMsTUFBTSxDQUFDLFFBQVEsQ0FBQztnQkFDaEMsTUFBTSxFQUFFLEtBQUssSUFBSSxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU07YUFDckMsQ0FBQyxDQUFDO1lBQ0g7Z0JBQ0ksb0JBQUEsR0FBRSxFQUFBLENBQUEsQ0FBQyxHQUFBLEVBQUcsQ0FBRSxDQUFDLEVBQUM7b0JBQ04sSUFBQSxFQUFJLENBQUMsR0FBQSxFQUFHO29CQUNSLFNBQUEsRUFBUyxDQUFFLE9BQU8sRUFBQztvQkFDbkIsT0FBQSxFQUFPLENBQUUsSUFBSSxDQUFDLFdBQVcsQ0FBQyxJQUFJLENBQUMsSUFBSSxFQUFFLEtBQUssQ0FBRTtnQkFDL0MsQ0FBQSxFQUFBO29CQUNJLENBQUMsS0FBSyxDQUFDLEtBQU07Z0JBQ2QsQ0FBQTtjQUNOO0FBQ2QsU0FBUyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDOztRQUVkO1lBQ0ksb0JBQUEsUUFBTyxFQUFBLElBQUMsRUFBQTtnQkFDSixvQkFBQSxLQUFJLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLHNCQUF1QixDQUFBLEVBQUE7b0JBQ2xDLG9CQUFDLFFBQVEsRUFBQSxJQUFFLENBQUEsRUFBQTtvQkFDVixNQUFPO2dCQUNOLENBQUEsRUFBQTtnQkFDTixvQkFBQSxLQUFJLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLE1BQU8sQ0FBQSxFQUFBO29CQUNsQixvQkFBQyxpQkFBaUIsRUFBQSxDQUFBLENBQUMsUUFBQSxFQUFRLENBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxRQUFTLENBQUUsQ0FBQTtnQkFDakQsQ0FBQTtZQUNELENBQUE7VUFDWDtLQUNMO0FBQ0wsQ0FBQyxDQUFDLENBQUM7QUFDSDs7QUFFQSxNQUFNLENBQUMsT0FBTyxHQUFHO0lBQ2IsTUFBTSxFQUFFLE1BQU07Ozs7QUNwWWxCLElBQUksS0FBSyxHQUFHLE9BQU8sQ0FBQyxPQUFPLENBQUMsQ0FBQzs7QUFFN0IsSUFBSSxNQUFNLEdBQUcsT0FBTyxDQUFDLGFBQWEsQ0FBQyxDQUFDO0FBQ3BDLElBQUksT0FBTyxHQUFHLE9BQU8sQ0FBQyxlQUFlLENBQUMsQ0FBQztBQUN2QyxJQUFJLFFBQVEsR0FBRyxPQUFPLENBQUMsYUFBYSxDQUFDLENBQUM7QUFDdEMsSUFBSSxLQUFLLEdBQUcsT0FBTyxDQUFDLGtCQUFrQixDQUFDLENBQUM7QUFDeEMsSUFBSSxJQUFJLEdBQUcsT0FBTyxDQUFDLGlCQUFpQixDQUFDLENBQUM7QUFDdEMsU0FBUyxHQUFHLE9BQU8sQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDO0FBQ3RDLElBQUksVUFBVSxHQUFHLE9BQU8sQ0FBQyxpQkFBaUIsQ0FBQyxDQUFDO0FBQzVDOztBQUVBLElBQUksOEJBQThCLHdCQUFBO0lBQzlCLE1BQU0sRUFBRSxDQUFDLE1BQU0sQ0FBQyxVQUFVLEVBQUUsTUFBTSxDQUFDLEtBQUssQ0FBQztJQUN6QyxlQUFlLEVBQUUsWUFBWTtRQUN6QixJQUFJLENBQUMsYUFBYSxDQUFDLEtBQUssQ0FBQyxNQUFNLEVBQUUsWUFBWTtZQUN6QyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQyxXQUFXLENBQUMsSUFBSSxDQUFDLFdBQVcsRUFBRSxFQUFFLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQyxDQUFDO1NBQ3ZFLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUM7UUFDZCxJQUFJLENBQUMsYUFBYSxDQUFDLEtBQUssQ0FBQyxTQUFTLEVBQUUsWUFBWTtZQUM1QyxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQyxXQUFXLENBQUMsSUFBSSxDQUFDLFdBQVcsRUFBRSxFQUFFLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQyxDQUFDO1NBQ3ZFLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUM7UUFDZCxPQUFPO1lBQ0gsS0FBSyxFQUFFLEVBQUU7U0FDWixDQUFDO0tBQ0w7SUFDRCxXQUFXLEVBQUUsWUFBWTtRQUNyQixJQUFJO1lBQ0EsSUFBSSxJQUFJLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsUUFBUSxFQUFFLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxJQUFJLEVBQUUsQ0FBQyxDQUFDO1lBQzNELElBQUksWUFBWSxHQUFHLElBQUksQ0FBQyxRQUFRLEVBQUUsQ0FBQyxLQUFLLENBQUMsU0FBUyxDQUFDLENBQUM7WUFDcEQsSUFBSSxTQUFTLEdBQUcsWUFBWSxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsWUFBWSxDQUFDLEdBQUcsS0FBSyxDQUFDO1NBQ25FLENBQUMsT0FBTyxDQUFDLEVBQUU7WUFDUixPQUFPLENBQUMsS0FBSyxDQUFDLGdDQUFnQyxHQUFHLENBQUMsQ0FBQyxDQUFDO0FBQ2hFLFNBQVM7O1FBRUQsT0FBTyxTQUFTLG9CQUFvQixDQUFDLElBQUksRUFBRTtZQUN2QyxJQUFJLENBQUMsSUFBSSxDQUFDLFVBQVUsRUFBRTtnQkFDbEIsSUFBSSxDQUFDLFVBQVUsR0FBRyxFQUFFLENBQUM7YUFDeEI7WUFDRCxJQUFJLENBQUMsVUFBVSxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsR0FBRyxTQUFTLElBQUksU0FBUyxDQUFDLElBQUksQ0FBQyxDQUFDO1lBQ3hELE9BQU8sSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDO1NBQ3JCLENBQUM7S0FDTDtJQUNELFdBQVcsRUFBRSxZQUFZO0tBQ3hCO0lBQ0QseUJBQXlCLEVBQUUsVUFBVSxTQUFTLEVBQUU7UUFDNUMsSUFBSSxTQUFTLENBQUMsU0FBUyxLQUFLLElBQUksQ0FBQyxLQUFLLENBQUMsU0FBUyxFQUFFO1lBQzlDLElBQUksQ0FBQyxTQUFTLEVBQUUsQ0FBQztZQUNqQixJQUFJLENBQUMsUUFBUSxDQUFDLFNBQVMsQ0FBQyxTQUFTLENBQUMsQ0FBQztTQUN0QztLQUNKO0lBQ0QsUUFBUSxFQUFFLFVBQVUsS0FBSyxFQUFFO1FBQ3ZCLElBQUksSUFBSSxHQUFHLElBQUksS0FBSyxDQUFDLFNBQVMsQ0FBQyxLQUFLLEVBQUUsSUFBSSxDQUFDLFdBQVcsRUFBRSxFQUFFLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQyxDQUFDO1FBQzlFLElBQUksQ0FBQyxRQUFRLENBQUM7WUFDVixJQUFJLEVBQUUsSUFBSTtBQUN0QixTQUFTLENBQUMsQ0FBQzs7UUFFSCxJQUFJLENBQUMsV0FBVyxDQUFDLGFBQWEsRUFBRSxJQUFJLENBQUMsYUFBYSxDQUFDLENBQUM7UUFDcEQsSUFBSSxDQUFDLFdBQVcsQ0FBQyxLQUFLLEVBQUUsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDO1FBQ3ZDLElBQUksQ0FBQyxXQUFXLENBQUMsUUFBUSxFQUFFLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQztRQUMxQyxJQUFJLENBQUMsV0FBVyxDQUFDLFFBQVEsRUFBRSxJQUFJLENBQUMsUUFBUSxDQUFDLENBQUM7UUFDMUMsSUFBSSxDQUFDLFdBQVcsQ0FBQyxRQUFRLEVBQUUsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDO0tBQzdDO0lBQ0QsYUFBYSxFQUFFLFlBQVk7UUFDdkIsSUFBSSxDQUFDLFdBQVcsRUFBRSxDQUFDO1FBQ25CLElBQUksUUFBUSxHQUFHLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQztRQUNsQyxJQUFJLFFBQVEsRUFBRTtZQUNWLElBQUksQ0FBQyxJQUFJLENBQUMsU0FBUyxDQUFDLGNBQWMsQ0FBQyxRQUFRLENBQUMsQ0FBQztTQUNoRDtLQUNKO0lBQ0QsUUFBUSxFQUFFLFVBQVUsSUFBSSxFQUFFO1FBQ3RCLElBQUksSUFBSSxDQUFDLEVBQUUsS0FBSyxJQUFJLENBQUMsU0FBUyxFQUFFLENBQUMsTUFBTSxFQUFFO1lBQ3JDLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQztTQUN0QjtLQUNKO0lBQ0QsUUFBUSxFQUFFLFVBQVUsT0FBTyxFQUFFLEtBQUssRUFBRTtRQUNoQyxJQUFJLE9BQU8sS0FBSyxJQUFJLENBQUMsU0FBUyxFQUFFLENBQUMsTUFBTSxFQUFFO1lBQ3JDLElBQUksY0FBYyxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsR0FBRyxDQUFDLEtBQUssRUFBRSxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsTUFBTSxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUM7WUFDM0YsSUFBSSxDQUFDLFVBQVUsQ0FBQyxjQUFjLENBQUMsQ0FBQztTQUNuQztLQUNKO0lBQ0QsU0FBUyxFQUFFLFlBQVk7UUFDbkIsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsS0FBSyxFQUFFLENBQUM7S0FDM0I7SUFDRCxrQkFBa0IsRUFBRSxZQUFZO1FBQzVCLElBQUksQ0FBQyxRQUFRLENBQUMsSUFBSSxDQUFDLEtBQUssQ0FBQyxTQUFTLENBQUMsQ0FBQztLQUN2QztJQUNELG9CQUFvQixFQUFFLFlBQVk7UUFDOUIsSUFBSSxDQUFDLFNBQVMsRUFBRSxDQUFDO0tBQ3BCO0lBQ0QsVUFBVSxFQUFFLFVBQVUsSUFBSSxFQUFFO1FBQ3hCLElBQUksSUFBSSxFQUFFO1lBQ04sSUFBSSxDQUFDLFdBQVc7Z0JBQ1osTUFBTTtnQkFDTjtvQkFDSSxNQUFNLEVBQUUsSUFBSSxDQUFDLEVBQUU7b0JBQ2YsU0FBUyxFQUFFLElBQUksQ0FBQyxTQUFTLEVBQUUsQ0FBQyxTQUFTLElBQUksU0FBUztpQkFDckQ7YUFDSixDQUFDO1lBQ0YsSUFBSSxDQUFDLElBQUksQ0FBQyxTQUFTLENBQUMsY0FBYyxDQUFDLElBQUksQ0FBQyxDQUFDO1NBQzVDLE1BQU07WUFDSCxJQUFJLENBQUMsV0FBVyxDQUFDLE9BQU8sRUFBRSxFQUFFLENBQUMsQ0FBQztTQUNqQztLQUNKO0lBQ0Qsa0JBQWtCLEVBQUUsVUFBVSxLQUFLLEVBQUU7UUFDakMsSUFBSSxLQUFLLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDO1FBQ2pDLElBQUksS0FBSyxDQUFDO1FBQ1YsSUFBSSxDQUFDLElBQUksQ0FBQyxTQUFTLEVBQUUsQ0FBQyxNQUFNLEVBQUU7WUFDMUIsSUFBSSxLQUFLLEdBQUcsQ0FBQyxFQUFFO2dCQUNYLEtBQUssR0FBRyxLQUFLLENBQUMsTUFBTSxHQUFHLENBQUMsQ0FBQzthQUM1QixNQUFNO2dCQUNILEtBQUssR0FBRyxDQUFDLENBQUM7YUFDYjtTQUNKLE1BQU07WUFDSCxJQUFJLFVBQVUsR0FBRyxJQUFJLENBQUMsU0FBUyxFQUFFLENBQUMsTUFBTSxDQUFDO1lBQ3pDLElBQUksQ0FBQyxHQUFHLEtBQUssQ0FBQyxNQUFNLENBQUM7WUFDckIsT0FBTyxDQUFDLEVBQUUsRUFBRTtnQkFDUixJQUFJLEtBQUssQ0FBQyxDQUFDLENBQUMsQ0FBQyxFQUFFLEtBQUssVUFBVSxFQUFFO29CQUM1QixLQUFLLEdBQUcsQ0FBQyxDQUFDO29CQUNWLE1BQU07aUJBQ1Q7YUFDSjtZQUNELEtBQUssR0FBRyxJQUFJLENBQUMsR0FBRztnQkFDWixJQUFJLENBQUMsR0FBRyxDQUFDLENBQUMsRUFBRSxLQUFLLEdBQUcsS0FBSyxDQUFDO2dCQUMxQixLQUFLLENBQUMsTUFBTSxHQUFHLENBQUMsQ0FBQyxDQUFDO1NBQ3pCO1FBQ0QsSUFBSSxDQUFDLFVBQVUsQ0FBQyxLQUFLLENBQUMsS0FBSyxDQUFDLENBQUMsQ0FBQztLQUNqQztJQUNELFNBQVMsRUFBRSxVQUFVLENBQUMsRUFBRTtRQUNwQixJQUFJLElBQUksR0FBRyxJQUFJLENBQUMsV0FBVyxFQUFFLENBQUM7UUFDOUIsSUFBSSxDQUFDLENBQUMsT0FBTyxFQUFFO1lBQ1gsT0FBTztTQUNWO1FBQ0QsUUFBUSxDQUFDLENBQUMsT0FBTztZQUNiLEtBQUssUUFBUSxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUM7WUFDcEIsS0FBSyxRQUFRLENBQUMsR0FBRyxDQUFDLEVBQUU7Z0JBQ2hCLElBQUksQ0FBQyxrQkFBa0IsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDO2dCQUM1QixNQUFNO1lBQ1YsS0FBSyxRQUFRLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQztZQUNwQixLQUFLLFFBQVEsQ0FBQyxHQUFHLENBQUMsSUFBSTtnQkFDbEIsSUFBSSxDQUFDLGtCQUFrQixDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUM7Z0JBQzVCLE1BQU07WUFDVixLQUFLLFFBQVEsQ0FBQyxHQUFHLENBQUMsS0FBSyxDQUFDO1lBQ3hCLEtBQUssUUFBUSxDQUFDLEdBQUcsQ0FBQyxTQUFTO2dCQUN2QixJQUFJLENBQUMsa0JBQWtCLENBQUMsQ0FBQyxFQUFFLENBQUMsQ0FBQztnQkFDN0IsTUFBTTtZQUNWLEtBQUssUUFBUSxDQUFDLEdBQUcsQ0FBQyxPQUFPO2dCQUNyQixJQUFJLENBQUMsa0JBQWtCLENBQUMsQ0FBQyxFQUFFLENBQUMsQ0FBQztnQkFDN0IsTUFBTTtZQUNWLEtBQUssUUFBUSxDQUFDLEdBQUcsQ0FBQyxHQUFHO2dCQUNqQixJQUFJLENBQUMsa0JBQWtCLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQztnQkFDL0IsTUFBTTtZQUNWLEtBQUssUUFBUSxDQUFDLEdBQUcsQ0FBQyxJQUFJO2dCQUNsQixJQUFJLENBQUMsa0JBQWtCLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQztnQkFDL0IsTUFBTTtZQUNWLEtBQUssUUFBUSxDQUFDLEdBQUcsQ0FBQyxHQUFHO2dCQUNqQixJQUFJLENBQUMsVUFBVSxDQUFDLElBQUksQ0FBQyxDQUFDO2dCQUN0QixNQUFNO1lBQ1YsS0FBSyxRQUFRLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQztZQUNwQixLQUFLLFFBQVEsQ0FBQyxHQUFHLENBQUMsSUFBSTtnQkFDbEIsSUFBSSxJQUFJLENBQUMsSUFBSSxDQUFDLFdBQVcsRUFBRTtvQkFDdkIsSUFBSSxDQUFDLElBQUksQ0FBQyxXQUFXLENBQUMsT0FBTyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUM7aUJBQ3JDO2dCQUNELE1BQU07WUFDVixLQUFLLFFBQVEsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDO1lBQ3BCLEtBQUssUUFBUSxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUM7WUFDdEIsS0FBSyxRQUFRLENBQUMsR0FBRyxDQUFDLEtBQUs7Z0JBQ25CLElBQUksSUFBSSxDQUFDLElBQUksQ0FBQyxXQUFXLEVBQUU7b0JBQ3ZCLElBQUksQ0FBQyxJQUFJLENBQUMsV0FBVyxDQUFDLE9BQU8sQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDO2lCQUNyQztnQkFDRCxNQUFNO1lBQ1YsS0FBSyxRQUFRLENBQUMsR0FBRyxDQUFDLENBQUM7Z0JBQ2YsSUFBSSxDQUFDLENBQUMsUUFBUSxFQUFFO29CQUNaLE9BQU8sQ0FBQyxXQUFXLENBQUMsS0FBSyxFQUFFLENBQUM7aUJBQy9CO2dCQUNELE1BQU07WUFDVixLQUFLLFFBQVEsQ0FBQyxHQUFHLENBQUMsQ0FBQztnQkFDZixJQUFJLElBQUksRUFBRTtvQkFDTixJQUFJLENBQUMsQ0FBQyxRQUFRLEVBQUU7d0JBQ1osT0FBTyxDQUFDLFdBQVcsQ0FBQyxTQUFTLENBQUMsSUFBSSxDQUFDLENBQUM7cUJBQ3ZDLE1BQU07d0JBQ0gsT0FBTyxDQUFDLFdBQVcsQ0FBQyxNQUFNLENBQUMsSUFBSSxDQUFDLENBQUM7cUJBQ3BDO2lCQUNKO2dCQUNELE1BQU07WUFDVixLQUFLLFFBQVEsQ0FBQyxHQUFHLENBQUMsQ0FBQztnQkFDZixJQUFJLENBQUMsQ0FBQyxRQUFRLEVBQUU7b0JBQ1osT0FBTyxDQUFDLFdBQVcsQ0FBQyxVQUFVLEVBQUUsQ0FBQztpQkFDcEMsTUFBTSxJQUFJLElBQUksSUFBSSxJQUFJLENBQUMsV0FBVyxFQUFFO29CQUNqQyxPQUFPLENBQUMsV0FBVyxDQUFDLE1BQU0sQ0FBQyxJQUFJLENBQUMsQ0FBQztpQkFDcEM7Z0JBQ0QsTUFBTTtZQUNWLEtBQUssUUFBUSxDQUFDLEdBQUcsQ0FBQyxDQUFDO2dCQUNmLElBQUksQ0FBQyxDQUFDLENBQUMsUUFBUSxJQUFJLElBQUksRUFBRTtvQkFDckIsT0FBTyxDQUFDLFdBQVcsQ0FBQyxNQUFNLENBQUMsSUFBSSxDQUFDLENBQUM7aUJBQ3BDO2dCQUNELE1BQU07WUFDVixLQUFLLFFBQVEsQ0FBQyxHQUFHLENBQUMsQ0FBQztnQkFDZixHQUFHLENBQUMsQ0FBQyxRQUFRLElBQUksSUFBSSxJQUFJLElBQUksQ0FBQyxRQUFRLEVBQUU7b0JBQ3BDLE9BQU8sQ0FBQyxXQUFXLENBQUMsTUFBTSxDQUFDLElBQUksQ0FBQyxDQUFDO2lCQUNwQztnQkFDRCxNQUFNO1lBQ1Y7Z0JBQ0ksT0FBTyxDQUFDLEtBQUssQ0FBQyxTQUFTLEVBQUUsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxDQUFDO2dCQUNwQyxPQUFPO1NBQ2Q7UUFDRCxDQUFDLENBQUMsY0FBYyxFQUFFLENBQUM7S0FDdEI7SUFDRCxXQUFXLEVBQUUsWUFBWTtRQUNyQixPQUFPLElBQUksQ0FBQyxLQUFLLENBQUMsU0FBUyxDQUFDLEdBQUcsQ0FBQyxJQUFJLENBQUMsU0FBUyxFQUFFLENBQUMsTUFBTSxDQUFDLENBQUM7S0FDNUQ7SUFDRCxNQUFNLEVBQUUsWUFBWTtBQUN4QixRQUFRLElBQUksUUFBUSxHQUFHLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQzs7UUFFbEMsSUFBSSxPQUFPLENBQUM7UUFDWixJQUFJLFFBQVEsRUFBRTtZQUNWLE9BQU8sR0FBRztnQkFDTixvQkFBQyxlQUFlLEVBQUEsQ0FBQSxDQUFDLEdBQUEsRUFBRyxDQUFDLFVBQVUsQ0FBRSxDQUFBO2dCQUNqQyxvQkFBQyxxQkFBcUIsRUFBQSxDQUFBLENBQUMsR0FBQSxFQUFHLENBQUMsYUFBQSxFQUFhLENBQUMsR0FBQSxFQUFHLENBQUMsYUFBQSxFQUFhLENBQUMsSUFBQSxFQUFJLENBQUUsUUFBUyxDQUFFLENBQUE7YUFDL0UsQ0FBQztTQUNMLE1BQU07WUFDSCxPQUFPLEdBQUcsSUFBSSxDQUFDO0FBQzNCLFNBQVM7O1FBRUQ7WUFDSSxvQkFBQSxLQUFJLEVBQUEsQ0FBQSxDQUFDLFNBQUEsRUFBUyxDQUFDLFdBQUEsRUFBVyxDQUFDLFNBQUEsRUFBUyxDQUFFLElBQUksQ0FBQyxTQUFTLEVBQUMsQ0FBQyxRQUFBLEVBQVEsQ0FBQyxHQUFJLENBQUEsRUFBQTtnQkFDL0Qsb0JBQUMsU0FBUyxFQUFBLENBQUEsQ0FBQyxHQUFBLEVBQUcsQ0FBQyxXQUFBLEVBQVc7b0JBQ3RCLElBQUEsRUFBSSxDQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxFQUFDO29CQUN0QixVQUFBLEVBQVUsQ0FBRSxJQUFJLENBQUMsVUFBVSxFQUFDO29CQUM1QixRQUFBLEVBQVEsQ0FBRSxRQUFTLENBQUEsQ0FBRyxDQUFBLEVBQUE7Z0JBQ3pCLE9BQVE7WUFDUCxDQUFBO1VBQ1I7S0FDTDtBQUNMLENBQUMsQ0FBQyxDQUFDOztBQUVILE1BQU0sQ0FBQyxPQUFPLEdBQUcsUUFBUSxDQUFDOzs7O0FDMU8xQixJQUFJLEtBQUssR0FBRyxPQUFPLENBQUMsT0FBTyxDQUFDLENBQUM7QUFDN0IsSUFBSSxXQUFXLEdBQUcsT0FBTyxDQUFDLGNBQWMsQ0FBQyxDQUFDO0FBQzFDLElBQUksQ0FBQyxHQUFHLE9BQU8sQ0FBQyxRQUFRLENBQUMsQ0FBQzs7QUFFMUIsSUFBSSxNQUFNLEdBQUcsT0FBTyxDQUFDLGFBQWEsQ0FBQyxDQUFDO0FBQ3BDLElBQUksUUFBUSxHQUFHLE9BQU8sQ0FBQyxlQUFlLENBQUMsQ0FBQztBQUN4QyxJQUFJLE1BQU0sR0FBRyxPQUFPLENBQUMsYUFBYSxDQUFDLENBQUM7QUFDcEMsSUFBSSxNQUFNLEdBQUcsT0FBTyxDQUFDLGFBQWEsQ0FBQyxDQUFDO0FBQ3BDLElBQUksUUFBUSxHQUFHLE9BQU8sQ0FBQyxlQUFlLENBQUMsQ0FBQztBQUN4QyxJQUFJLEtBQUssR0FBRyxPQUFPLENBQUMsbUJBQW1CLENBQUMsQ0FBQztBQUN6Qzs7QUFFQSxzQ0FBc0M7QUFDdEMsSUFBSSw2QkFBNkIsdUJBQUE7SUFDN0IsTUFBTSxFQUFFLFlBQVk7UUFDaEIsT0FBTyxvQkFBQSxLQUFJLEVBQUEsSUFBQyxFQUFBLGNBQWtCLENBQUEsQ0FBQztLQUNsQztBQUNMLENBQUMsQ0FBQyxDQUFDO0FBQ0g7O0FBRUEsSUFBSSxrQ0FBa0MsNEJBQUE7SUFDbEMsTUFBTSxFQUFFLENBQUMsTUFBTSxDQUFDLEtBQUssQ0FBQztJQUN0QixlQUFlLEVBQUUsWUFBWTtRQUN6QixJQUFJLFVBQVUsR0FBRyxJQUFJLEtBQUssQ0FBQyxhQUFhLEVBQUUsQ0FBQztRQUMzQyxJQUFJLFNBQVMsR0FBRyxJQUFJLEtBQUssQ0FBQyxTQUFTLEVBQUUsQ0FBQztBQUM5QyxRQUFRLElBQUksUUFBUSxHQUFHLElBQUksS0FBSyxDQUFDLGFBQWEsRUFBRSxDQUFDO0FBQ2pEOztRQUVRLENBQUMsQ0FBQyxNQUFNLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQztTQUN0QixDQUFDLENBQUM7UUFDSCxPQUFPO1lBQ0gsUUFBUSxFQUFFLFFBQVE7WUFDbEIsU0FBUyxFQUFFLFNBQVM7WUFDcEIsVUFBVSxFQUFFLFVBQVU7U0FDekIsQ0FBQztLQUNMO0lBQ0QsaUJBQWlCLEVBQUUsWUFBWTtRQUMzQixJQUFJLENBQUMsS0FBSyxDQUFDLFFBQVEsQ0FBQyxXQUFXLENBQUMsYUFBYSxFQUFFLElBQUksQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDO1FBQ3RFLE1BQU0sQ0FBQyxHQUFHLEdBQUcsSUFBSSxDQUFDO0tBQ3JCO0lBQ0Qsb0JBQW9CLEVBQUUsWUFBWTtRQUM5QixJQUFJLENBQUMsS0FBSyxDQUFDLFFBQVEsQ0FBQyxjQUFjLENBQUMsYUFBYSxFQUFFLElBQUksQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDO0tBQzVFO0lBQ0QsZ0JBQWdCLEVBQUUsVUFBVTtRQUN4QixJQUFJLENBQUMsUUFBUSxDQUFDO1lBQ1YsUUFBUSxFQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsUUFBUTtTQUNoQyxDQUFDLENBQUM7S0FDTjtBQUNMLElBQUksTUFBTSxFQUFFLFlBQVk7O1FBRWhCLElBQUksUUFBUSxDQUFDO1FBQ2IsSUFBSSxJQUFJLENBQUMsUUFBUSxFQUFFLENBQUMsS0FBSyxDQUFDLGFBQWEsQ0FBQyxFQUFFO1lBQ3RDLFFBQVEsR0FBRztnQkFDUCxvQkFBQyxlQUFlLEVBQUEsQ0FBQSxDQUFDLEdBQUEsRUFBRyxDQUFDLFVBQUEsRUFBVSxDQUFDLElBQUEsRUFBSSxDQUFDLEdBQUcsQ0FBRSxDQUFBO2dCQUMxQyxvQkFBQyxRQUFRLEVBQUEsQ0FBQSxDQUFDLEdBQUEsRUFBRyxDQUFDLFVBQUEsRUFBVSxDQUFDLFVBQUEsRUFBVSxDQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsVUFBVyxDQUFFLENBQUE7YUFDaEUsQ0FBQztTQUNMLE1BQU07WUFDSCxRQUFRLEdBQUcsSUFBSSxDQUFDO0FBQzVCLFNBQVM7O1FBRUQ7WUFDSSxvQkFBQSxLQUFJLEVBQUEsQ0FBQSxDQUFDLEVBQUEsRUFBRSxDQUFDLFdBQVksQ0FBQSxFQUFBO2dCQUNoQixvQkFBQyxhQUFhLEVBQUEsQ0FBQSxDQUFDLFFBQUEsRUFBUSxDQUFFLElBQUksQ0FBQyxLQUFLLENBQUMsUUFBUSxDQUFDLElBQUssQ0FBRSxDQUFBLEVBQUE7Z0JBQ3BELG9CQUFDLFlBQVksRUFBQSxDQUFBLENBQUMsUUFBQSxFQUFRLENBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxRQUFRLENBQUMsSUFBSSxFQUFDLENBQUMsU0FBQSxFQUFTLENBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxTQUFVLENBQUUsQ0FBQSxFQUFBO2dCQUNuRixRQUFRLEVBQUM7Z0JBQ1Ysb0JBQUMsTUFBTSxFQUFBLENBQUEsQ0FBQyxRQUFBLEVBQVEsQ0FBRSxJQUFJLENBQUMsS0FBSyxDQUFDLFFBQVEsQ0FBQyxJQUFLLENBQUUsQ0FBQTtZQUMzQyxDQUFBO1VBQ1I7S0FDTDtBQUNMLENBQUMsQ0FBQyxDQUFDO0FBQ0g7O0FBRUEsSUFBSSxLQUFLLEdBQUcsV0FBVyxDQUFDLEtBQUssQ0FBQztBQUM5QixJQUFJLFlBQVksR0FBRyxXQUFXLENBQUMsWUFBWSxDQUFDO0FBQzVDLElBQUksUUFBUSxHQUFHLFdBQVcsQ0FBQyxRQUFRLENBQUM7QUFDcEMsSUFBSSxZQUFZLEdBQUcsV0FBVyxDQUFDLFlBQVksQ0FBQztBQUM1QyxJQUFJLGFBQWEsR0FBRyxXQUFXLENBQUMsYUFBYSxDQUFDO0FBQzlDOztBQUVBLElBQUksTUFBTTtJQUNOLG9CQUFDLEtBQUssRUFBQSxDQUFBLENBQUMsSUFBQSxFQUFJLENBQUMsR0FBQSxFQUFHLENBQUMsT0FBQSxFQUFPLENBQUUsWUFBYyxDQUFBLEVBQUE7UUFDbkMsb0JBQUMsS0FBSyxFQUFBLENBQUEsQ0FBQyxJQUFBLEVBQUksQ0FBQyxPQUFBLEVBQU8sQ0FBQyxJQUFBLEVBQUksQ0FBQyxPQUFBLEVBQU8sQ0FBQyxPQUFBLEVBQU8sQ0FBRSxRQUFTLENBQUUsQ0FBQSxFQUFBO1FBQ3JELG9CQUFDLEtBQUssRUFBQSxDQUFBLENBQUMsSUFBQSxFQUFJLENBQUMsTUFBQSxFQUFNLENBQUMsSUFBQSxFQUFJLENBQUMsMEJBQUEsRUFBMEIsQ0FBQyxPQUFBLEVBQU8sQ0FBRSxRQUFTLENBQUUsQ0FBQSxFQUFBO1FBQ3ZFLG9CQUFDLEtBQUssRUFBQSxDQUFBLENBQUMsSUFBQSxFQUFJLENBQUMsU0FBQSxFQUFTLENBQUMsT0FBQSxFQUFPLENBQUUsT0FBUSxDQUFFLENBQUEsRUFBQTtRQUN6QyxvQkFBQyxRQUFRLEVBQUEsQ0FBQSxDQUFDLElBQUEsRUFBSSxDQUFDLEdBQUEsRUFBRyxDQUFDLEVBQUEsRUFBRSxDQUFDLE9BQU8sQ0FBQSxDQUFHLENBQUE7SUFDNUIsQ0FBQTtBQUNaLENBQUMsQ0FBQzs7QUFFRixNQUFNLENBQUMsT0FBTyxHQUFHO0lBQ2IsTUFBTSxFQUFFLE1BQU07QUFDbEIsQ0FBQyxDQUFDOzs7OztBQzFGRixJQUFJLEtBQUssR0FBRyxPQUFPLENBQUMsT0FBTyxDQUFDLENBQUM7O0FBRTdCLElBQUksa0JBQWtCLEdBQUc7SUFDckIsZUFBZSxFQUFFLFlBQVk7UUFDekIsT0FBTztZQUNILEtBQUssRUFBRSxDQUFDO1lBQ1IsSUFBSSxFQUFFLENBQUM7U0FDVixDQUFDO0tBQ0w7SUFDRCxrQkFBa0IsRUFBRSxZQUFZO1FBQzVCLElBQUksQ0FBQyxJQUFJLENBQUMsS0FBSyxDQUFDLFNBQVMsRUFBRTtZQUN2QixPQUFPLENBQUMsSUFBSSxDQUFDLDRDQUE0QyxFQUFFLElBQUksQ0FBQyxDQUFDO1NBQ3BFO0tBQ0o7SUFDRCxpQkFBaUIsRUFBRSxVQUFVLEtBQUssRUFBRTtBQUN4QyxRQUFRLElBQUksR0FBRyxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsa0JBQWtCLElBQUksSUFBSSxDQUFDO0FBQ3hEOztRQUVRLElBQUksS0FBSyxHQUFHO1lBQ1IsTUFBTSxFQUFFLElBQUksQ0FBQyxHQUFHLENBQUMsSUFBSSxDQUFDLEtBQUssQ0FBQyxLQUFLLEVBQUUsS0FBSyxDQUFDLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxTQUFTO1NBQ25FLENBQUM7QUFDVixRQUFRLElBQUksTUFBTSxHQUFHLG9CQUFDLEdBQUcsRUFBQSxDQUFBLENBQUMsR0FBQSxFQUFHLENBQUMsaUJBQUEsRUFBaUIsQ0FBQyxLQUFBLEVBQUssQ0FBRSxLQUFPLENBQU0sQ0FBQSxDQUFDOztBQUVyRSxRQUFRLElBQUksSUFBSSxDQUFDLEtBQUssQ0FBQyxLQUFLLEdBQUcsQ0FBQyxLQUFLLENBQUMsRUFBRTs7WUFFNUIsT0FBTyxDQUFDLE1BQU0sRUFBRSxvQkFBQyxHQUFHLEVBQUEsQ0FBQSxDQUFDLEdBQUEsRUFBRyxDQUFDLG1CQUFvQixDQUFNLENBQUEsQ0FBQyxDQUFDO1NBQ3hELE1BQU07WUFDSCxPQUFPLE1BQU0sQ0FBQztTQUNqQjtLQUNKO0lBQ0Qsb0JBQW9CLEVBQUUsVUFBVSxLQUFLLEVBQUU7UUFDbkMsSUFBSSxHQUFHLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxrQkFBa0IsSUFBSSxJQUFJLENBQUM7UUFDaEQsSUFBSSxLQUFLLEdBQUc7WUFDUixNQUFNLEVBQUUsSUFBSSxDQUFDLEdBQUcsQ0FBQyxDQUFDLEVBQUUsS0FBSyxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxTQUFTO1NBQ3RFLENBQUM7UUFDRixPQUFPLG9CQUFDLEdBQUcsRUFBQSxDQUFBLENBQUMsR0FBQSxFQUFHLENBQUMsb0JBQUEsRUFBb0IsQ0FBQyxLQUFBLEVBQUssQ0FBRSxLQUFPLENBQU0sQ0FBQSxDQUFDO0tBQzdEO0lBQ0QsaUJBQWlCLEVBQUUsWUFBWTtRQUMzQixJQUFJLENBQUMsUUFBUSxFQUFFLENBQUM7UUFDaEIsTUFBTSxDQUFDLGdCQUFnQixDQUFDLFFBQVEsRUFBRSxJQUFJLENBQUMsUUFBUSxDQUFDLENBQUM7S0FDcEQ7SUFDRCxvQkFBb0IsRUFBRSxVQUFVO1FBQzVCLE1BQU0sQ0FBQyxtQkFBbUIsQ0FBQyxRQUFRLEVBQUUsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDO0tBQ3ZEO0lBQ0QsUUFBUSxFQUFFLFlBQVk7UUFDbEIsSUFBSSxRQUFRLEdBQUcsSUFBSSxDQUFDLFVBQVUsRUFBRSxDQUFDO1FBQ2pDLElBQUksR0FBRyxHQUFHLFFBQVEsQ0FBQyxTQUFTLENBQUM7UUFDN0IsSUFBSSxNQUFNLEdBQUcsUUFBUSxDQUFDLFlBQVksQ0FBQztRQUNuQyxJQUFJLEtBQUssR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLEdBQUcsR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLFNBQVMsQ0FBQyxDQUFDO0FBQzNELFFBQVEsSUFBSSxJQUFJLEdBQUcsS0FBSyxHQUFHLElBQUksQ0FBQyxJQUFJLENBQUMsTUFBTSxJQUFJLElBQUksQ0FBQyxLQUFLLENBQUMsWUFBWSxJQUFJLElBQUksQ0FBQyxLQUFLLENBQUMsU0FBUyxDQUFDLENBQUMsQ0FBQzs7UUFFekYsSUFBSSxDQUFDLFFBQVEsQ0FBQztZQUNWLEtBQUssRUFBRSxLQUFLO1lBQ1osSUFBSSxFQUFFLElBQUk7U0FDYixDQUFDLENBQUM7S0FDTjtJQUNELFVBQVUsRUFBRSxVQUFVLEtBQUssRUFBRTtRQUN6QixJQUFJLElBQUksR0FBRyxFQUFFLENBQUM7QUFDdEIsUUFBUSxJQUFJLEdBQUcsR0FBRyxJQUFJLENBQUMsR0FBRyxDQUFDLEtBQUssQ0FBQyxNQUFNLEVBQUUsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsQ0FBQzs7UUFFbEQsS0FBSyxJQUFJLENBQUMsR0FBRyxJQUFJLENBQUMsS0FBSyxDQUFDLEtBQUssRUFBRSxDQUFDLEdBQUcsR0FBRyxFQUFFLENBQUMsRUFBRSxFQUFFO1lBQ3pDLElBQUksSUFBSSxHQUFHLEtBQUssQ0FBQyxDQUFDLENBQUMsQ0FBQztZQUNwQixJQUFJLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxTQUFTLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQztTQUNuQztRQUNELE9BQU8sSUFBSSxDQUFDO0tBQ2Y7QUFDTCxJQUFJLGlCQUFpQixFQUFFLFVBQVUsS0FBSyxFQUFFLFdBQVcsRUFBRTs7UUFFN0MsSUFBSSxPQUFPLEdBQUcsQ0FBQyxLQUFLLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxTQUFTLElBQUksV0FBVyxDQUFDO0FBQ25FLFFBQVEsSUFBSSxVQUFVLEdBQUcsT0FBTyxHQUFHLElBQUksQ0FBQyxLQUFLLENBQUMsU0FBUyxDQUFDOztRQUVoRCxJQUFJLFFBQVEsR0FBRyxJQUFJLENBQUMsVUFBVSxFQUFFLENBQUM7UUFDakMsSUFBSSxZQUFZLEdBQUcsUUFBUSxDQUFDLFNBQVMsQ0FBQztBQUM5QyxRQUFRLElBQUksZUFBZSxHQUFHLFlBQVksR0FBRyxRQUFRLENBQUMsWUFBWSxDQUFDO0FBQ25FOztRQUVRLElBQUksT0FBTyxHQUFHLFdBQVcsR0FBRyxZQUFZLEVBQUU7WUFDdEMsUUFBUSxDQUFDLFNBQVMsR0FBRyxPQUFPLEdBQUcsV0FBVyxDQUFDO1NBQzlDLE1BQU0sSUFBSSxVQUFVLEdBQUcsZUFBZSxFQUFFO1lBQ3JDLFFBQVEsQ0FBQyxTQUFTLEdBQUcsVUFBVSxHQUFHLFFBQVEsQ0FBQyxZQUFZLENBQUM7U0FDM0Q7S0FDSjtBQUNMLENBQUMsQ0FBQzs7QUFFRixNQUFNLENBQUMsT0FBTyxJQUFJLGtCQUFrQjs7O0FDcEZwQztBQUNBLElBQUksT0FBTyxHQUFHLE9BQU8sQ0FBQyxjQUFjLENBQUMsQ0FBQzs7QUFFdEMsU0FBUyxVQUFVLENBQUMsR0FBRyxFQUFFO0lBQ3JCLElBQUksR0FBRyxDQUFDLENBQUMsQ0FBQyxLQUFLLEdBQUcsRUFBRTtRQUNoQixHQUFHLEdBQUcsUUFBUSxDQUFDLE1BQU0sQ0FBQyxPQUFPLENBQUMsTUFBTSxFQUFFLElBQUksQ0FBQyxHQUFHLEdBQUcsQ0FBQztBQUMxRCxLQUFLOztJQUVELElBQUksRUFBRSxHQUFHLElBQUksU0FBUyxDQUFDLEdBQUcsQ0FBQyxDQUFDO0lBQzVCLEVBQUUsQ0FBQyxNQUFNLEdBQUcsWUFBWTtRQUNwQixPQUFPLENBQUMsaUJBQWlCLENBQUMsSUFBSSxFQUFFLENBQUM7S0FDcEMsQ0FBQztJQUNGLEVBQUUsQ0FBQyxTQUFTLEdBQUcsVUFBVSxPQUFPLEVBQUU7UUFDOUIsSUFBSSxDQUFDLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxPQUFPLENBQUMsSUFBSSxDQUFDLENBQUM7UUFDakMsYUFBYSxDQUFDLG9CQUFvQixDQUFDLENBQUMsQ0FBQyxDQUFDO0tBQ3pDLENBQUM7SUFDRixFQUFFLENBQUMsT0FBTyxHQUFHLFlBQVk7UUFDckIsT0FBTyxDQUFDLGlCQUFpQixDQUFDLEtBQUssRUFBRSxDQUFDO1FBQ2xDLGVBQWUsQ0FBQyxTQUFTLENBQUMsNkJBQTZCLENBQUMsQ0FBQztLQUM1RCxDQUFDO0lBQ0YsRUFBRSxDQUFDLE9BQU8sR0FBRyxZQUFZO1FBQ3JCLE9BQU8sQ0FBQyxpQkFBaUIsQ0FBQyxLQUFLLEVBQUUsQ0FBQztRQUNsQyxlQUFlLENBQUMsU0FBUyxDQUFDLDhCQUE4QixDQUFDLENBQUM7S0FDN0QsQ0FBQztJQUNGLE9BQU8sRUFBRSxDQUFDO0FBQ2QsQ0FBQzs7QUFFRCxNQUFNLENBQUMsT0FBTyxHQUFHLFVBQVU7OztBQzNCM0I7QUFDQSxJQUFJLElBQUksR0FBRyxPQUFPLENBQUMsTUFBTSxDQUFDLENBQUM7O0FBRTNCLE1BQU0sY0FBYyxHQUFHO0lBQ25CLElBQUksRUFBRSxNQUFNO0lBQ1osTUFBTSxFQUFFLFFBQVE7QUFDcEIsQ0FBQyxDQUFDO0FBQ0Y7O0FBRUEsYUFBYSxHQUFHLElBQUksSUFBSSxDQUFDLFVBQVUsRUFBRSxDQUFDO0FBQ3RDLGFBQWEsQ0FBQyxrQkFBa0IsR0FBRyxVQUFVLE1BQU0sRUFBRTtJQUNqRCxNQUFNLENBQUMsTUFBTSxHQUFHLGNBQWMsQ0FBQyxJQUFJLENBQUM7SUFDcEMsSUFBSSxDQUFDLFFBQVEsQ0FBQyxNQUFNLENBQUMsQ0FBQztDQUN6QixDQUFDO0FBQ0YsYUFBYSxDQUFDLG9CQUFvQixHQUFHLFVBQVUsTUFBTSxFQUFFO0lBQ25ELE1BQU0sQ0FBQyxNQUFNLEdBQUcsY0FBYyxDQUFDLE1BQU0sQ0FBQztJQUN0QyxJQUFJLENBQUMsUUFBUSxDQUFDLE1BQU0sQ0FBQyxDQUFDO0FBQzFCLENBQUMsQ0FBQzs7QUFFRixNQUFNLENBQUMsT0FBTyxHQUFHO0lBQ2IsYUFBYSxFQUFFLGFBQWE7Q0FDL0I7OztBQ3JCRCxNQUFNLENBQUMsT0FBTyxHQUFHLENBQUMsV0FBVztBQUM3QjtBQUNBO0FBQ0E7QUFDQTtBQUNBOztFQUVFLFNBQVMsWUFBWSxDQUFDLEtBQUssRUFBRSxNQUFNLEVBQUU7SUFDbkMsU0FBUyxJQUFJLEdBQUcsRUFBRSxJQUFJLENBQUMsV0FBVyxHQUFHLEtBQUssQ0FBQyxFQUFFO0lBQzdDLElBQUksQ0FBQyxTQUFTLEdBQUcsTUFBTSxDQUFDLFNBQVMsQ0FBQztJQUNsQyxLQUFLLENBQUMsU0FBUyxHQUFHLElBQUksSUFBSSxFQUFFLENBQUM7QUFDakMsR0FBRzs7RUFFRCxTQUFTLFdBQVcsQ0FBQyxPQUFPLEVBQUUsUUFBUSxFQUFFLEtBQUssRUFBRSxNQUFNLEVBQUUsSUFBSSxFQUFFLE1BQU0sRUFBRTtJQUNuRSxJQUFJLENBQUMsT0FBTyxJQUFJLE9BQU8sQ0FBQztJQUN4QixJQUFJLENBQUMsUUFBUSxHQUFHLFFBQVEsQ0FBQztJQUN6QixJQUFJLENBQUMsS0FBSyxNQUFNLEtBQUssQ0FBQztJQUN0QixJQUFJLENBQUMsTUFBTSxLQUFLLE1BQU0sQ0FBQztJQUN2QixJQUFJLENBQUMsSUFBSSxPQUFPLElBQUksQ0FBQztBQUN6QixJQUFJLElBQUksQ0FBQyxNQUFNLEtBQUssTUFBTSxDQUFDOztJQUV2QixJQUFJLENBQUMsSUFBSSxPQUFPLGFBQWEsQ0FBQztBQUNsQyxHQUFHOztBQUVILEVBQUUsWUFBWSxDQUFDLFdBQVcsRUFBRSxLQUFLLENBQUMsQ0FBQzs7RUFFakMsU0FBUyxLQUFLLENBQUMsS0FBSyxFQUFFO0FBQ3hCLElBQUksSUFBSSxPQUFPLEdBQUcsU0FBUyxDQUFDLE1BQU0sR0FBRyxDQUFDLEdBQUcsU0FBUyxDQUFDLENBQUMsQ0FBQyxHQUFHLEVBQUU7O0FBRTFELFFBQVEsVUFBVSxHQUFHLEVBQUU7O1FBRWYsc0JBQXNCLEdBQUcsRUFBRSxLQUFLLEVBQUUsY0FBYyxFQUFFO0FBQzFELFFBQVEscUJBQXFCLElBQUksY0FBYzs7UUFFdkMsTUFBTSxHQUFHLEVBQUUsSUFBSSxFQUFFLE9BQU8sRUFBRSxXQUFXLEVBQUUsbUJBQW1CLEVBQUU7UUFDNUQsTUFBTSxHQUFHLFVBQVU7UUFDbkIsTUFBTSxHQUFHLFNBQVMsTUFBTSxFQUFFLEVBQUUsT0FBTyxNQUFNLENBQUMsRUFBRTtRQUM1QyxNQUFNLEdBQUcsRUFBRTtRQUNYLE1BQU0sR0FBRyxXQUFXLENBQUMsT0FBTyxVQUFVLENBQUMsRUFBRTtRQUN6QyxNQUFNLEdBQUcsRUFBRSxJQUFJLEVBQUUsT0FBTyxFQUFFLFdBQVcsRUFBRSxZQUFZLEVBQUU7UUFDckQsTUFBTSxHQUFHLFlBQVk7UUFDckIsTUFBTSxHQUFHLEVBQUUsSUFBSSxFQUFFLE9BQU8sRUFBRSxLQUFLLEVBQUUsY0FBYyxFQUFFLFdBQVcsRUFBRSxjQUFjLEVBQUU7UUFDOUUsTUFBTSxHQUFHLEVBQUUsSUFBSSxFQUFFLE9BQU8sRUFBRSxXQUFXLEVBQUUsbUJBQW1CLEVBQUU7UUFDNUQsTUFBTSxHQUFHLFlBQVk7UUFDckIsT0FBTyxHQUFHLEVBQUUsSUFBSSxFQUFFLE9BQU8sRUFBRSxLQUFLLEVBQUUsWUFBWSxFQUFFLFdBQVcsRUFBRSxZQUFZLEVBQUU7UUFDM0UsT0FBTyxHQUFHLEVBQUUsSUFBSSxFQUFFLE9BQU8sRUFBRSxXQUFXLEVBQUUscUJBQXFCLEVBQUU7UUFDL0QsT0FBTyxHQUFHLEdBQUc7UUFDYixPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsU0FBUyxFQUFFLEtBQUssRUFBRSxHQUFHLEVBQUUsV0FBVyxFQUFFLE9BQU8sRUFBRTtRQUMvRCxPQUFPLEdBQUcsU0FBUyxLQUFLLEVBQUUsTUFBTSxFQUFFLEVBQUUsT0FBTyxFQUFFLENBQUMsS0FBSyxFQUFFLE1BQU0sQ0FBQyxDQUFDLEVBQUU7UUFDL0QsT0FBTyxHQUFHLEdBQUc7UUFDYixPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsU0FBUyxFQUFFLEtBQUssRUFBRSxHQUFHLEVBQUUsV0FBVyxFQUFFLE9BQU8sRUFBRTtRQUMvRCxPQUFPLEdBQUcsU0FBUyxLQUFLLEVBQUUsTUFBTSxFQUFFLEVBQUUsT0FBTyxHQUFHLENBQUMsS0FBSyxFQUFFLE1BQU0sQ0FBQyxDQUFDLEVBQUU7UUFDaEUsT0FBTyxHQUFHLEdBQUc7UUFDYixPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsU0FBUyxFQUFFLEtBQUssRUFBRSxHQUFHLEVBQUUsV0FBVyxFQUFFLE9BQU8sRUFBRTtRQUMvRCxPQUFPLEdBQUcsU0FBUyxJQUFJLEVBQUUsRUFBRSxPQUFPLEdBQUcsQ0FBQyxJQUFJLENBQUMsQ0FBQyxFQUFFO1FBQzlDLE9BQU8sR0FBRyxHQUFHO1FBQ2IsT0FBTyxHQUFHLEVBQUUsSUFBSSxFQUFFLFNBQVMsRUFBRSxLQUFLLEVBQUUsR0FBRyxFQUFFLFdBQVcsRUFBRSxPQUFPLEVBQUU7UUFDL0QsT0FBTyxHQUFHLEdBQUc7UUFDYixPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsU0FBUyxFQUFFLEtBQUssRUFBRSxHQUFHLEVBQUUsV0FBVyxFQUFFLE9BQU8sRUFBRTtRQUMvRCxPQUFPLEdBQUcsU0FBUyxJQUFJLEVBQUUsRUFBRSxPQUFPLE9BQU8sQ0FBQyxJQUFJLENBQUMsQ0FBQyxFQUFFO1FBQ2xELE9BQU8sR0FBRyxJQUFJO1FBQ2QsT0FBTyxHQUFHLEVBQUUsSUFBSSxFQUFFLFNBQVMsRUFBRSxLQUFLLEVBQUUsSUFBSSxFQUFFLFdBQVcsRUFBRSxRQUFRLEVBQUU7UUFDakUsT0FBTyxHQUFHLFdBQVcsRUFBRSxPQUFPLFdBQVcsQ0FBQyxFQUFFO1FBQzVDLE9BQU8sR0FBRyxJQUFJO1FBQ2QsT0FBTyxHQUFHLEVBQUUsSUFBSSxFQUFFLFNBQVMsRUFBRSxLQUFLLEVBQUUsSUFBSSxFQUFFLFdBQVcsRUFBRSxRQUFRLEVBQUU7UUFDakUsT0FBTyxHQUFHLFdBQVcsRUFBRSxPQUFPLFdBQVcsQ0FBQyxFQUFFO1FBQzVDLE9BQU8sR0FBRyxJQUFJO1FBQ2QsT0FBTyxHQUFHLEVBQUUsSUFBSSxFQUFFLFNBQVMsRUFBRSxLQUFLLEVBQUUsSUFBSSxFQUFFLFdBQVcsRUFBRSxRQUFRLEVBQUU7UUFDakUsT0FBTyxHQUFHLFdBQVcsRUFBRSxPQUFPLGdCQUFnQixDQUFDLEVBQUU7UUFDakQsT0FBTyxHQUFHLElBQUk7UUFDZCxPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsU0FBUyxFQUFFLEtBQUssRUFBRSxJQUFJLEVBQUUsV0FBVyxFQUFFLFFBQVEsRUFBRTtRQUNqRSxPQUFPLEdBQUcsV0FBVyxFQUFFLE9BQU8sY0FBYyxDQUFDLEVBQUU7UUFDL0MsT0FBTyxHQUFHLE1BQU07UUFDaEIsT0FBTyxHQUFHLEVBQUUsSUFBSSxFQUFFLFNBQVMsRUFBRSxLQUFLLEVBQUUsTUFBTSxFQUFFLFdBQVcsRUFBRSxVQUFVLEVBQUU7UUFDckUsT0FBTyxHQUFHLFdBQVcsRUFBRSxPQUFPLFVBQVUsQ0FBQyxFQUFFO1FBQzNDLE9BQU8sR0FBRyxPQUFPO1FBQ2pCLE9BQU8sR0FBRyxFQUFFLElBQUksRUFBRSxTQUFTLEVBQUUsS0FBSyxFQUFFLE9BQU8sRUFBRSxXQUFXLEVBQUUsV0FBVyxFQUFFO1FBQ3ZFLE9BQU8sR0FBRyxXQUFXLEVBQUUsT0FBTyxXQUFXLENBQUMsRUFBRTtRQUM1QyxPQUFPLEdBQUcsSUFBSTtRQUNkLE9BQU8sR0FBRyxFQUFFLElBQUksRUFBRSxTQUFTLEVBQUUsS0FBSyxFQUFFLElBQUksRUFBRSxXQUFXLEVBQUUsUUFBUSxFQUFFO1FBQ2pFLE9BQU8sR0FBRyxTQUFTLENBQUMsRUFBRSxFQUFFLE9BQU8sWUFBWSxDQUFDLENBQUMsQ0FBQyxDQUFDLEVBQUU7UUFDakQsT0FBTyxHQUFHLElBQUk7UUFDZCxPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsU0FBUyxFQUFFLEtBQUssRUFBRSxJQUFJLEVBQUUsV0FBVyxFQUFFLFFBQVEsRUFBRTtRQUNqRSxPQUFPLEdBQUcsU0FBUyxDQUFDLEVBQUUsRUFBRSxPQUFPLE1BQU0sQ0FBQyxDQUFDLENBQUMsQ0FBQyxFQUFFO1FBQzNDLE9BQU8sR0FBRyxJQUFJO1FBQ2QsT0FBTyxHQUFHLEVBQUUsSUFBSSxFQUFFLFNBQVMsRUFBRSxLQUFLLEVBQUUsSUFBSSxFQUFFLFdBQVcsRUFBRSxRQUFRLEVBQUU7UUFDakUsT0FBTyxHQUFHLFNBQVMsQ0FBQyxFQUFFLEVBQUUsT0FBTyxNQUFNLENBQUMsQ0FBQyxDQUFDLENBQUMsRUFBRTtRQUMzQyxPQUFPLEdBQUcsS0FBSztRQUNmLE9BQU8sR0FBRyxFQUFFLElBQUksRUFBRSxTQUFTLEVBQUUsS0FBSyxFQUFFLEtBQUssRUFBRSxXQUFXLEVBQUUsU0FBUyxFQUFFO1FBQ25FLE9BQU8sR0FBRyxTQUFTLENBQUMsRUFBRSxFQUFFLE9BQU8sYUFBYSxDQUFDLENBQUMsQ0FBQyxDQUFDLEVBQUU7UUFDbEQsT0FBTyxHQUFHLEtBQUs7UUFDZixPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsU0FBUyxFQUFFLEtBQUssRUFBRSxLQUFLLEVBQUUsV0FBVyxFQUFFLFNBQVMsRUFBRTtRQUNuRSxPQUFPLEdBQUcsU0FBUyxDQUFDLEVBQUUsRUFBRSxPQUFPLGNBQWMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxFQUFFO1FBQ25ELE9BQU8sR0FBRyxJQUFJO1FBQ2QsT0FBTyxHQUFHLEVBQUUsSUFBSSxFQUFFLFNBQVMsRUFBRSxLQUFLLEVBQUUsSUFBSSxFQUFFLFdBQVcsRUFBRSxRQUFRLEVBQUU7UUFDakUsT0FBTyxHQUFHLFNBQVMsQ0FBQyxFQUFFLEVBQUUsT0FBTyxNQUFNLENBQUMsQ0FBQyxDQUFDLENBQUMsRUFBRTtRQUMzQyxPQUFPLEdBQUcsSUFBSTtRQUNkLE9BQU8sR0FBRyxFQUFFLElBQUksRUFBRSxTQUFTLEVBQUUsS0FBSyxFQUFFLElBQUksRUFBRSxXQUFXLEVBQUUsUUFBUSxFQUFFO1FBQ2pFLE9BQU8sR0FBRyxTQUFTLENBQUMsRUFBRSxFQUFFLE9BQU8sV0FBVyxDQUFDLENBQUMsQ0FBQyxDQUFDLEVBQUU7UUFDaEQsT0FBTyxHQUFHLEtBQUs7UUFDZixPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsU0FBUyxFQUFFLEtBQUssRUFBRSxLQUFLLEVBQUUsV0FBVyxFQUFFLFNBQVMsRUFBRTtRQUNuRSxPQUFPLEdBQUcsU0FBUyxDQUFDLEVBQUUsRUFBRSxPQUFPLGtCQUFrQixDQUFDLENBQUMsQ0FBQyxDQUFDLEVBQUU7UUFDdkQsT0FBTyxHQUFHLEtBQUs7UUFDZixPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsU0FBUyxFQUFFLEtBQUssRUFBRSxLQUFLLEVBQUUsV0FBVyxFQUFFLFNBQVMsRUFBRTtRQUNuRSxPQUFPLEdBQUcsU0FBUyxDQUFDLEVBQUUsRUFBRSxPQUFPLG1CQUFtQixDQUFDLENBQUMsQ0FBQyxDQUFDLEVBQUU7UUFDeEQsT0FBTyxHQUFHLElBQUk7UUFDZCxPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsU0FBUyxFQUFFLEtBQUssRUFBRSxJQUFJLEVBQUUsV0FBVyxFQUFFLFFBQVEsRUFBRTtRQUNqRSxPQUFPLEdBQUcsU0FBUyxDQUFDLEVBQUUsRUFBRSxPQUFPLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxFQUFFO1FBQ3hDLE9BQU8sR0FBRyxFQUFFLElBQUksRUFBRSxPQUFPLEVBQUUsV0FBVyxFQUFFLFNBQVMsRUFBRTtRQUNuRCxPQUFPLEdBQUcsSUFBSTtRQUNkLE9BQU8sR0FBRyxPQUFPO1FBQ2pCLE9BQU8sR0FBRyxFQUFFLElBQUksRUFBRSxPQUFPLEVBQUUsS0FBSyxFQUFFLE9BQU8sRUFBRSxXQUFXLEVBQUUsT0FBTyxFQUFFO1FBQ2pFLE9BQU8sR0FBRyxRQUFRO1FBQ2xCLE9BQU8sR0FBRyxFQUFFLElBQUksRUFBRSxPQUFPLEVBQUUsS0FBSyxFQUFFLE9BQU8sRUFBRSxXQUFXLEVBQUUsT0FBTyxFQUFFO1FBQ2pFLE9BQU8sR0FBRyxTQUFTLE1BQU0sRUFBRSxFQUFFLE9BQU8sUUFBUSxDQUFDLE1BQU0sQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLEVBQUUsRUFBRSxDQUFDLENBQUMsRUFBRTtRQUNwRSxPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsT0FBTyxFQUFFLFdBQVcsRUFBRSxRQUFRLEVBQUU7UUFDbEQsT0FBTyxHQUFHLElBQUk7UUFDZCxPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsU0FBUyxFQUFFLEtBQUssRUFBRSxJQUFJLEVBQUUsV0FBVyxFQUFFLFVBQVUsRUFBRTtRQUNuRSxPQUFPLEdBQUcsU0FBUyxLQUFLLEVBQUUsRUFBRSxPQUFPLEtBQUssQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsRUFBRTtRQUNwRCxPQUFPLEdBQUcsR0FBRztRQUNiLE9BQU8sR0FBRyxFQUFFLElBQUksRUFBRSxTQUFTLEVBQUUsS0FBSyxFQUFFLEdBQUcsRUFBRSxXQUFXLEVBQUUsT0FBTyxFQUFFO1FBQy9ELE9BQU8sR0FBRyxLQUFLLENBQUM7UUFDaEIsT0FBTyxHQUFHLFFBQVE7UUFDbEIsT0FBTyxHQUFHLEVBQUUsSUFBSSxFQUFFLE9BQU8sRUFBRSxLQUFLLEVBQUUsVUFBVSxFQUFFLFdBQVcsRUFBRSxVQUFVLEVBQUU7UUFDdkUsT0FBTyxHQUFHLEVBQUUsSUFBSSxFQUFFLEtBQUssRUFBRSxXQUFXLEVBQUUsZUFBZSxFQUFFO1FBQ3ZELE9BQU8sR0FBRyxTQUFTLElBQUksRUFBRSxFQUFFLE9BQU8sSUFBSSxDQUFDLEVBQUU7UUFDekMsT0FBTyxHQUFHLElBQUk7UUFDZCxPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsU0FBUyxFQUFFLEtBQUssRUFBRSxJQUFJLEVBQUUsV0FBVyxFQUFFLFVBQVUsRUFBRTtRQUNuRSxPQUFPLEdBQUcsUUFBUTtRQUNsQixPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsT0FBTyxFQUFFLEtBQUssRUFBRSxTQUFTLEVBQUUsV0FBVyxFQUFFLFNBQVMsRUFBRTtRQUNyRSxPQUFPLEdBQUcsU0FBUztRQUNuQixPQUFPLEdBQUcsRUFBRSxJQUFJLEVBQUUsT0FBTyxFQUFFLEtBQUssRUFBRSxXQUFXLEVBQUUsV0FBVyxFQUFFLFdBQVcsRUFBRTtRQUN6RSxPQUFPLEdBQUcsR0FBRztRQUNiLE9BQU8sR0FBRyxFQUFFLElBQUksRUFBRSxTQUFTLEVBQUUsS0FBSyxFQUFFLEdBQUcsRUFBRSxXQUFXLEVBQUUsT0FBTyxFQUFFO1FBQy9ELFFBQVEsR0FBRyxXQUFXLEVBQUUsT0FBTyxJQUFJLENBQUMsRUFBRTtRQUN0QyxRQUFRLEdBQUcsR0FBRztRQUNkLFFBQVEsR0FBRyxFQUFFLElBQUksRUFBRSxTQUFTLEVBQUUsS0FBSyxFQUFFLEdBQUcsRUFBRSxXQUFXLEVBQUUsT0FBTyxFQUFFO1FBQ2hFLFFBQVEsR0FBRyxXQUFXLEVBQUUsT0FBTyxJQUFJLENBQUMsRUFBRTtRQUN0QyxRQUFRLEdBQUcsR0FBRztRQUNkLFFBQVEsR0FBRyxFQUFFLElBQUksRUFBRSxTQUFTLEVBQUUsS0FBSyxFQUFFLEdBQUcsRUFBRSxXQUFXLEVBQUUsT0FBTyxFQUFFO0FBQ3hFLFFBQVEsUUFBUSxHQUFHLFdBQVcsRUFBRSxPQUFPLElBQUksQ0FBQyxFQUFFOztRQUV0QyxXQUFXLFlBQVksQ0FBQztRQUN4QixlQUFlLFFBQVEsQ0FBQztRQUN4QixhQUFhLFVBQVUsQ0FBQztRQUN4QixvQkFBb0IsR0FBRyxFQUFFLElBQUksRUFBRSxDQUFDLEVBQUUsTUFBTSxFQUFFLENBQUMsRUFBRSxNQUFNLEVBQUUsS0FBSyxFQUFFO1FBQzVELGNBQWMsU0FBUyxDQUFDO1FBQ3hCLG1CQUFtQixJQUFJLEVBQUU7QUFDakMsUUFBUSxlQUFlLFFBQVEsQ0FBQzs7QUFFaEMsUUFBUSxVQUFVLENBQUM7O0lBRWYsSUFBSSxXQUFXLElBQUksT0FBTyxFQUFFO01BQzFCLElBQUksRUFBRSxPQUFPLENBQUMsU0FBUyxJQUFJLHNCQUFzQixDQUFDLEVBQUU7UUFDbEQsTUFBTSxJQUFJLEtBQUssQ0FBQyxrQ0FBa0MsR0FBRyxPQUFPLENBQUMsU0FBUyxHQUFHLEtBQUssQ0FBQyxDQUFDO0FBQ3hGLE9BQU87O01BRUQscUJBQXFCLEdBQUcsc0JBQXNCLENBQUMsT0FBTyxDQUFDLFNBQVMsQ0FBQyxDQUFDO0FBQ3hFLEtBQUs7O0lBRUQsU0FBUyxJQUFJLEdBQUc7TUFDZCxPQUFPLEtBQUssQ0FBQyxTQUFTLENBQUMsZUFBZSxFQUFFLFdBQVcsQ0FBQyxDQUFDO0FBQzNELEtBQUs7O0lBRUQsU0FBUyxNQUFNLEdBQUc7TUFDaEIsT0FBTyxlQUFlLENBQUM7QUFDN0IsS0FBSzs7SUFFRCxTQUFTLElBQUksR0FBRztNQUNkLE9BQU8scUJBQXFCLENBQUMsZUFBZSxDQUFDLENBQUMsSUFBSSxDQUFDO0FBQ3pELEtBQUs7O0lBRUQsU0FBUyxNQUFNLEdBQUc7TUFDaEIsT0FBTyxxQkFBcUIsQ0FBQyxlQUFlLENBQUMsQ0FBQyxNQUFNLENBQUM7QUFDM0QsS0FBSzs7SUFFRCxTQUFTLFFBQVEsQ0FBQyxXQUFXLEVBQUU7TUFDN0IsTUFBTSxrQkFBa0I7UUFDdEIsSUFBSTtRQUNKLENBQUMsRUFBRSxJQUFJLEVBQUUsT0FBTyxFQUFFLFdBQVcsRUFBRSxXQUFXLEVBQUUsQ0FBQztRQUM3QyxlQUFlO09BQ2hCLENBQUM7QUFDUixLQUFLOztJQUVELFNBQVMsS0FBSyxDQUFDLE9BQU8sRUFBRTtNQUN0QixNQUFNLGtCQUFrQixDQUFDLE9BQU8sRUFBRSxJQUFJLEVBQUUsZUFBZSxDQUFDLENBQUM7QUFDL0QsS0FBSzs7SUFFRCxTQUFTLHFCQUFxQixDQUFDLEdBQUcsRUFBRTtNQUNsQyxTQUFTLE9BQU8sQ0FBQyxPQUFPLEVBQUUsUUFBUSxFQUFFLE1BQU0sRUFBRTtBQUNsRCxRQUFRLElBQUksQ0FBQyxFQUFFLEVBQUUsQ0FBQzs7UUFFVixLQUFLLENBQUMsR0FBRyxRQUFRLEVBQUUsQ0FBQyxHQUFHLE1BQU0sRUFBRSxDQUFDLEVBQUUsRUFBRTtVQUNsQyxFQUFFLEdBQUcsS0FBSyxDQUFDLE1BQU0sQ0FBQyxDQUFDLENBQUMsQ0FBQztVQUNyQixJQUFJLEVBQUUsS0FBSyxJQUFJLEVBQUU7WUFDZixJQUFJLENBQUMsT0FBTyxDQUFDLE1BQU0sRUFBRSxFQUFFLE9BQU8sQ0FBQyxJQUFJLEVBQUUsQ0FBQyxFQUFFO1lBQ3hDLE9BQU8sQ0FBQyxNQUFNLEdBQUcsQ0FBQyxDQUFDO1lBQ25CLE9BQU8sQ0FBQyxNQUFNLEdBQUcsS0FBSyxDQUFDO1dBQ3hCLE1BQU0sSUFBSSxFQUFFLEtBQUssSUFBSSxJQUFJLEVBQUUsS0FBSyxRQUFRLElBQUksRUFBRSxLQUFLLFFBQVEsRUFBRTtZQUM1RCxPQUFPLENBQUMsSUFBSSxFQUFFLENBQUM7WUFDZixPQUFPLENBQUMsTUFBTSxHQUFHLENBQUMsQ0FBQztZQUNuQixPQUFPLENBQUMsTUFBTSxHQUFHLElBQUksQ0FBQztXQUN2QixNQUFNO1lBQ0wsT0FBTyxDQUFDLE1BQU0sRUFBRSxDQUFDO1lBQ2pCLE9BQU8sQ0FBQyxNQUFNLEdBQUcsS0FBSyxDQUFDO1dBQ3hCO1NBQ0Y7QUFDVCxPQUFPOztNQUVELElBQUksYUFBYSxLQUFLLEdBQUcsRUFBRTtRQUN6QixJQUFJLGFBQWEsR0FBRyxHQUFHLEVBQUU7VUFDdkIsYUFBYSxHQUFHLENBQUMsQ0FBQztVQUNsQixvQkFBb0IsR0FBRyxFQUFFLElBQUksRUFBRSxDQUFDLEVBQUUsTUFBTSxFQUFFLENBQUMsRUFBRSxNQUFNLEVBQUUsS0FBSyxFQUFFLENBQUM7U0FDOUQ7UUFDRCxPQUFPLENBQUMsb0JBQW9CLEVBQUUsYUFBYSxFQUFFLEdBQUcsQ0FBQyxDQUFDO1FBQ2xELGFBQWEsR0FBRyxHQUFHLENBQUM7QUFDNUIsT0FBTzs7TUFFRCxPQUFPLG9CQUFvQixDQUFDO0FBQ2xDLEtBQUs7O0lBRUQsU0FBUyxRQUFRLENBQUMsUUFBUSxFQUFFO0FBQ2hDLE1BQU0sSUFBSSxXQUFXLEdBQUcsY0FBYyxFQUFFLEVBQUUsT0FBTyxFQUFFOztNQUU3QyxJQUFJLFdBQVcsR0FBRyxjQUFjLEVBQUU7UUFDaEMsY0FBYyxHQUFHLFdBQVcsQ0FBQztRQUM3QixtQkFBbUIsR0FBRyxFQUFFLENBQUM7QUFDakMsT0FBTzs7TUFFRCxtQkFBbUIsQ0FBQyxJQUFJLENBQUMsUUFBUSxDQUFDLENBQUM7QUFDekMsS0FBSzs7SUFFRCxTQUFTLGtCQUFrQixDQUFDLE9BQU8sRUFBRSxRQUFRLEVBQUUsR0FBRyxFQUFFO01BQ2xELFNBQVMsZUFBZSxDQUFDLFFBQVEsRUFBRTtBQUN6QyxRQUFRLElBQUksQ0FBQyxHQUFHLENBQUMsQ0FBQzs7UUFFVixRQUFRLENBQUMsSUFBSSxDQUFDLFNBQVMsQ0FBQyxFQUFFLENBQUMsRUFBRTtVQUMzQixJQUFJLENBQUMsQ0FBQyxXQUFXLEdBQUcsQ0FBQyxDQUFDLFdBQVcsRUFBRTtZQUNqQyxPQUFPLENBQUMsQ0FBQyxDQUFDO1dBQ1gsTUFBTSxJQUFJLENBQUMsQ0FBQyxXQUFXLEdBQUcsQ0FBQyxDQUFDLFdBQVcsRUFBRTtZQUN4QyxPQUFPLENBQUMsQ0FBQztXQUNWLE1BQU07WUFDTCxPQUFPLENBQUMsQ0FBQztXQUNWO0FBQ1gsU0FBUyxDQUFDLENBQUM7O1FBRUgsT0FBTyxDQUFDLEdBQUcsUUFBUSxDQUFDLE1BQU0sRUFBRTtVQUMxQixJQUFJLFFBQVEsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLEtBQUssUUFBUSxDQUFDLENBQUMsQ0FBQyxFQUFFO1lBQ25DLFFBQVEsQ0FBQyxNQUFNLENBQUMsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDO1dBQ3ZCLE1BQU07WUFDTCxDQUFDLEVBQUUsQ0FBQztXQUNMO1NBQ0Y7QUFDVCxPQUFPOztNQUVELFNBQVMsWUFBWSxDQUFDLFFBQVEsRUFBRSxLQUFLLEVBQUU7UUFDckMsU0FBUyxZQUFZLENBQUMsQ0FBQyxFQUFFO0FBQ2pDLFVBQVUsU0FBUyxHQUFHLENBQUMsRUFBRSxFQUFFLEVBQUUsT0FBTyxFQUFFLENBQUMsVUFBVSxDQUFDLENBQUMsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxFQUFFLENBQUMsQ0FBQyxXQUFXLEVBQUUsQ0FBQyxFQUFFOztVQUV4RSxPQUFPLENBQUM7YUFDTCxPQUFPLENBQUMsS0FBSyxJQUFJLE1BQU0sQ0FBQzthQUN4QixPQUFPLENBQUMsSUFBSSxLQUFLLEtBQUssQ0FBQzthQUN2QixPQUFPLENBQUMsT0FBTyxFQUFFLEtBQUssQ0FBQzthQUN2QixPQUFPLENBQUMsS0FBSyxJQUFJLEtBQUssQ0FBQzthQUN2QixPQUFPLENBQUMsS0FBSyxJQUFJLEtBQUssQ0FBQzthQUN2QixPQUFPLENBQUMsS0FBSyxJQUFJLEtBQUssQ0FBQzthQUN2QixPQUFPLENBQUMsS0FBSyxJQUFJLEtBQUssQ0FBQzthQUN2QixPQUFPLENBQUMsMEJBQTBCLEVBQUUsU0FBUyxFQUFFLEVBQUUsRUFBRSxPQUFPLE1BQU0sR0FBRyxHQUFHLENBQUMsRUFBRSxDQUFDLENBQUMsRUFBRSxDQUFDO2FBQzlFLE9BQU8sQ0FBQyx1QkFBdUIsS0FBSyxTQUFTLEVBQUUsRUFBRSxFQUFFLE9BQU8sS0FBSyxJQUFJLEdBQUcsQ0FBQyxFQUFFLENBQUMsQ0FBQyxFQUFFLENBQUM7YUFDOUUsT0FBTyxDQUFDLGtCQUFrQixVQUFVLFNBQVMsRUFBRSxFQUFFLEVBQUUsT0FBTyxNQUFNLEdBQUcsR0FBRyxDQUFDLEVBQUUsQ0FBQyxDQUFDLEVBQUUsQ0FBQzthQUM5RSxPQUFPLENBQUMsa0JBQWtCLFVBQVUsU0FBUyxFQUFFLEVBQUUsRUFBRSxPQUFPLEtBQUssSUFBSSxHQUFHLENBQUMsRUFBRSxDQUFDLENBQUMsRUFBRSxDQUFDLENBQUM7QUFDNUYsU0FBUzs7UUFFRCxJQUFJLGFBQWEsR0FBRyxJQUFJLEtBQUssQ0FBQyxRQUFRLENBQUMsTUFBTSxDQUFDO0FBQ3RELFlBQVksWUFBWSxFQUFFLFNBQVMsRUFBRSxDQUFDLENBQUM7O1FBRS9CLEtBQUssQ0FBQyxHQUFHLENBQUMsRUFBRSxDQUFDLEdBQUcsUUFBUSxDQUFDLE1BQU0sRUFBRSxDQUFDLEVBQUUsRUFBRTtVQUNwQyxhQUFhLENBQUMsQ0FBQyxDQUFDLEdBQUcsUUFBUSxDQUFDLENBQUMsQ0FBQyxDQUFDLFdBQVcsQ0FBQztBQUNyRCxTQUFTOztRQUVELFlBQVksR0FBRyxRQUFRLENBQUMsTUFBTSxHQUFHLENBQUM7WUFDOUIsYUFBYSxDQUFDLEtBQUssQ0FBQyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDO2dCQUNqQyxNQUFNO2dCQUNOLGFBQWEsQ0FBQyxRQUFRLENBQUMsTUFBTSxHQUFHLENBQUMsQ0FBQztBQUNsRCxZQUFZLGFBQWEsQ0FBQyxDQUFDLENBQUMsQ0FBQzs7QUFFN0IsUUFBUSxTQUFTLEdBQUcsS0FBSyxHQUFHLElBQUksR0FBRyxZQUFZLENBQUMsS0FBSyxDQUFDLEdBQUcsSUFBSSxHQUFHLGNBQWMsQ0FBQzs7UUFFdkUsT0FBTyxXQUFXLEdBQUcsWUFBWSxHQUFHLE9BQU8sR0FBRyxTQUFTLEdBQUcsU0FBUyxDQUFDO0FBQzVFLE9BQU87O01BRUQsSUFBSSxVQUFVLEdBQUcscUJBQXFCLENBQUMsR0FBRyxDQUFDO0FBQ2pELFVBQVUsS0FBSyxRQUFRLEdBQUcsR0FBRyxLQUFLLENBQUMsTUFBTSxHQUFHLEtBQUssQ0FBQyxNQUFNLENBQUMsR0FBRyxDQUFDLEdBQUcsSUFBSSxDQUFDOztNQUUvRCxJQUFJLFFBQVEsS0FBSyxJQUFJLEVBQUU7UUFDckIsZUFBZSxDQUFDLFFBQVEsQ0FBQyxDQUFDO0FBQ2xDLE9BQU87O01BRUQsT0FBTyxJQUFJLFdBQVc7UUFDcEIsT0FBTyxLQUFLLElBQUksR0FBRyxPQUFPLEdBQUcsWUFBWSxDQUFDLFFBQVEsRUFBRSxLQUFLLENBQUM7UUFDMUQsUUFBUTtRQUNSLEtBQUs7UUFDTCxHQUFHO1FBQ0gsVUFBVSxDQUFDLElBQUk7UUFDZixVQUFVLENBQUMsTUFBTTtPQUNsQixDQUFDO0FBQ1IsS0FBSzs7SUFFRCxTQUFTLGNBQWMsR0FBRztBQUM5QixNQUFNLElBQUksRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxDQUFDOztNQUVuQixlQUFlLEVBQUUsQ0FBQztNQUNsQixFQUFFLEdBQUcsV0FBVyxDQUFDO01BQ2pCLEVBQUUsR0FBRyxXQUFXLEVBQUUsQ0FBQztNQUNuQixJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDckIsRUFBRSxHQUFHLGVBQWUsRUFBRSxDQUFDO1FBQ3ZCLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtVQUNyQixFQUFFLEdBQUcsV0FBVyxFQUFFLENBQUM7VUFDbkIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1lBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7WUFDckIsRUFBRSxHQUFHLE1BQU0sQ0FBQyxFQUFFLENBQUMsQ0FBQztZQUNoQixFQUFFLEdBQUcsRUFBRSxDQUFDO1dBQ1QsTUFBTTtZQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7WUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztXQUNiO1NBQ0YsTUFBTTtVQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7VUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztTQUNiO09BQ0YsTUFBTTtRQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7UUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztPQUNiO01BQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1FBQ3JCLEVBQUUsR0FBRyxXQUFXLENBQUM7UUFDakIsRUFBRSxHQUFHLEVBQUUsQ0FBQztRQUNSLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtVQUNyQixlQUFlLEdBQUcsRUFBRSxDQUFDO1VBQ3JCLEVBQUUsR0FBRyxNQUFNLEVBQUUsQ0FBQztTQUNmO1FBQ0QsRUFBRSxHQUFHLEVBQUUsQ0FBQztPQUNUO01BQ0QsZUFBZSxFQUFFLENBQUM7TUFDbEIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1FBQ3JCLEVBQUUsR0FBRyxVQUFVLENBQUM7UUFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE1BQU0sQ0FBQyxDQUFDLEVBQUU7QUFDeEQsT0FBTzs7TUFFRCxPQUFPLEVBQUUsQ0FBQztBQUNoQixLQUFLOztJQUVELFNBQVMsV0FBVyxHQUFHO0FBQzNCLE1BQU0sSUFBSSxFQUFFLEVBQUUsRUFBRSxDQUFDOztNQUVYLGVBQWUsRUFBRSxDQUFDO01BQ2xCLElBQUksTUFBTSxDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsQ0FBQyxDQUFDLEVBQUU7UUFDMUMsRUFBRSxHQUFHLEtBQUssQ0FBQyxNQUFNLENBQUMsV0FBVyxDQUFDLENBQUM7UUFDL0IsV0FBVyxFQUFFLENBQUM7T0FDZixNQUFNO1FBQ0wsRUFBRSxHQUFHLFVBQVUsQ0FBQztRQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsTUFBTSxDQUFDLENBQUMsRUFBRTtPQUNqRDtNQUNELGVBQWUsRUFBRSxDQUFDO01BQ2xCLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtRQUNyQixFQUFFLEdBQUcsVUFBVSxDQUFDO1FBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxNQUFNLENBQUMsQ0FBQyxFQUFFO0FBQ3hELE9BQU87O01BRUQsT0FBTyxFQUFFLENBQUM7QUFDaEIsS0FBSzs7SUFFRCxTQUFTLFdBQVcsR0FBRztBQUMzQixNQUFNLElBQUksRUFBRSxFQUFFLEVBQUUsQ0FBQzs7TUFFWCxlQUFlLEVBQUUsQ0FBQztNQUNsQixJQUFJLE1BQU0sQ0FBQyxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLENBQUMsQ0FBQyxFQUFFO1FBQzFDLEVBQUUsR0FBRyxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsQ0FBQyxDQUFDO1FBQy9CLFdBQVcsRUFBRSxDQUFDO09BQ2YsTUFBTTtRQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7UUFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE9BQU8sQ0FBQyxDQUFDLEVBQUU7T0FDbEQ7TUFDRCxlQUFlLEVBQUUsQ0FBQztNQUNsQixJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDckIsRUFBRSxHQUFHLFVBQVUsQ0FBQztRQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsTUFBTSxDQUFDLENBQUMsRUFBRTtBQUN4RCxPQUFPOztNQUVELE9BQU8sRUFBRSxDQUFDO0FBQ2hCLEtBQUs7O0lBRUQsU0FBUyxXQUFXLEdBQUc7QUFDM0IsTUFBTSxJQUFJLEVBQUUsRUFBRSxFQUFFLENBQUM7O01BRVgsZUFBZSxFQUFFLENBQUM7TUFDbEIsRUFBRSxHQUFHLEVBQUUsQ0FBQztNQUNSLEVBQUUsR0FBRyxXQUFXLEVBQUUsQ0FBQztNQUNuQixPQUFPLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDeEIsRUFBRSxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQztRQUNaLEVBQUUsR0FBRyxXQUFXLEVBQUUsQ0FBQztPQUNwQjtNQUNELGVBQWUsRUFBRSxDQUFDO01BQ2xCLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtRQUNyQixFQUFFLEdBQUcsVUFBVSxDQUFDO1FBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO0FBQ3pELE9BQU87O01BRUQsT0FBTyxFQUFFLENBQUM7QUFDaEIsS0FBSzs7SUFFRCxTQUFTLGVBQWUsR0FBRztBQUMvQixNQUFNLElBQUksRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLENBQUM7O01BRTNCLEVBQUUsR0FBRyxXQUFXLENBQUM7TUFDakIsRUFBRSxHQUFHLGdCQUFnQixFQUFFLENBQUM7TUFDeEIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1FBQ3JCLEVBQUUsR0FBRyxXQUFXLEVBQUUsQ0FBQztRQUNuQixJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7VUFDckIsSUFBSSxLQUFLLENBQUMsVUFBVSxDQUFDLFdBQVcsQ0FBQyxLQUFLLEdBQUcsRUFBRTtZQUN6QyxFQUFFLEdBQUcsT0FBTyxDQUFDO1lBQ2IsV0FBVyxFQUFFLENBQUM7V0FDZixNQUFNO1lBQ0wsRUFBRSxHQUFHLFVBQVUsQ0FBQztZQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsT0FBTyxDQUFDLENBQUMsRUFBRTtXQUNsRDtVQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtZQUNyQixFQUFFLEdBQUcsV0FBVyxFQUFFLENBQUM7WUFDbkIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO2NBQ3JCLEVBQUUsR0FBRyxlQUFlLEVBQUUsQ0FBQztjQUN2QixJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7Z0JBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7Z0JBQ3JCLEVBQUUsR0FBRyxPQUFPLENBQUMsRUFBRSxFQUFFLEVBQUUsQ0FBQyxDQUFDO2dCQUNyQixFQUFFLEdBQUcsRUFBRSxDQUFDO2VBQ1QsTUFBTTtnQkFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO2dCQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO2VBQ2I7YUFDRixNQUFNO2NBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztjQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO2FBQ2I7V0FDRixNQUFNO1lBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztZQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO1dBQ2I7U0FDRixNQUFNO1VBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztVQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO1NBQ2I7T0FDRixNQUFNO1FBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztRQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO09BQ2I7TUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDckIsRUFBRSxHQUFHLGdCQUFnQixFQUFFLENBQUM7QUFDaEMsT0FBTzs7TUFFRCxPQUFPLEVBQUUsQ0FBQztBQUNoQixLQUFLOztJQUVELFNBQVMsZ0JBQWdCLEdBQUc7QUFDaEMsTUFBTSxJQUFJLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxDQUFDOztNQUUzQixFQUFFLEdBQUcsV0FBVyxDQUFDO01BQ2pCLEVBQUUsR0FBRyxnQkFBZ0IsRUFBRSxDQUFDO01BQ3hCLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtRQUNyQixFQUFFLEdBQUcsV0FBVyxFQUFFLENBQUM7UUFDbkIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1VBQ3JCLElBQUksS0FBSyxDQUFDLFVBQVUsQ0FBQyxXQUFXLENBQUMsS0FBSyxFQUFFLEVBQUU7WUFDeEMsRUFBRSxHQUFHLE9BQU8sQ0FBQztZQUNiLFdBQVcsRUFBRSxDQUFDO1dBQ2YsTUFBTTtZQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7WUFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE9BQU8sQ0FBQyxDQUFDLEVBQUU7V0FDbEQ7VUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7WUFDckIsRUFBRSxHQUFHLFdBQVcsRUFBRSxDQUFDO1lBQ25CLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtjQUNyQixFQUFFLEdBQUcsZ0JBQWdCLEVBQUUsQ0FBQztjQUN4QixJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7Z0JBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7Z0JBQ3JCLEVBQUUsR0FBRyxPQUFPLENBQUMsRUFBRSxFQUFFLEVBQUUsQ0FBQyxDQUFDO2dCQUNyQixFQUFFLEdBQUcsRUFBRSxDQUFDO2VBQ1QsTUFBTTtnQkFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO2dCQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO2VBQ2I7YUFDRixNQUFNO2NBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztjQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO2FBQ2I7V0FDRixNQUFNO1lBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztZQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO1dBQ2I7U0FDRixNQUFNO1VBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztVQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO1NBQ2I7T0FDRixNQUFNO1FBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztRQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO09BQ2I7TUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDckIsRUFBRSxHQUFHLFdBQVcsQ0FBQztRQUNqQixFQUFFLEdBQUcsZ0JBQWdCLEVBQUUsQ0FBQztRQUN4QixJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7VUFDckIsRUFBRSxHQUFHLEVBQUUsQ0FBQztVQUNSLEVBQUUsR0FBRyxXQUFXLEVBQUUsQ0FBQztVQUNuQixJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7WUFDckIsT0FBTyxFQUFFLEtBQUssVUFBVSxFQUFFO2NBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7Y0FDWixFQUFFLEdBQUcsV0FBVyxFQUFFLENBQUM7YUFDcEI7V0FDRixNQUFNO1lBQ0wsRUFBRSxHQUFHLE1BQU0sQ0FBQztXQUNiO1VBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1lBQ3JCLEVBQUUsR0FBRyxnQkFBZ0IsRUFBRSxDQUFDO1lBQ3hCLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtjQUNyQixlQUFlLEdBQUcsRUFBRSxDQUFDO2NBQ3JCLEVBQUUsR0FBRyxPQUFPLENBQUMsRUFBRSxFQUFFLEVBQUUsQ0FBQyxDQUFDO2NBQ3JCLEVBQUUsR0FBRyxFQUFFLENBQUM7YUFDVCxNQUFNO2NBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztjQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO2FBQ2I7V0FDRixNQUFNO1lBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztZQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO1dBQ2I7U0FDRixNQUFNO1VBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztVQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO1NBQ2I7UUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7VUFDckIsRUFBRSxHQUFHLGdCQUFnQixFQUFFLENBQUM7U0FDekI7QUFDVCxPQUFPOztNQUVELE9BQU8sRUFBRSxDQUFDO0FBQ2hCLEtBQUs7O0lBRUQsU0FBUyxnQkFBZ0IsR0FBRztBQUNoQyxNQUFNLElBQUksRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxDQUFDOztNQUVuQixFQUFFLEdBQUcsV0FBVyxDQUFDO01BQ2pCLElBQUksS0FBSyxDQUFDLFVBQVUsQ0FBQyxXQUFXLENBQUMsS0FBSyxFQUFFLEVBQUU7UUFDeEMsRUFBRSxHQUFHLE9BQU8sQ0FBQztRQUNiLFdBQVcsRUFBRSxDQUFDO09BQ2YsTUFBTTtRQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7UUFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE9BQU8sQ0FBQyxDQUFDLEVBQUU7T0FDbEQ7TUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDckIsRUFBRSxHQUFHLFdBQVcsRUFBRSxDQUFDO1FBQ25CLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtVQUNyQixFQUFFLEdBQUcsZ0JBQWdCLEVBQUUsQ0FBQztVQUN4QixJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7WUFDckIsZUFBZSxHQUFHLEVBQUUsQ0FBQztZQUNyQixFQUFFLEdBQUcsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDO1lBQ2pCLEVBQUUsR0FBRyxFQUFFLENBQUM7V0FDVCxNQUFNO1lBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztZQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO1dBQ2I7U0FDRixNQUFNO1VBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztVQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO1NBQ2I7T0FDRixNQUFNO1FBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztRQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO09BQ2I7TUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDckIsRUFBRSxHQUFHLG9CQUFvQixFQUFFLENBQUM7QUFDcEMsT0FBTzs7TUFFRCxPQUFPLEVBQUUsQ0FBQztBQUNoQixLQUFLOztJQUVELFNBQVMsb0JBQW9CLEdBQUc7QUFDcEMsTUFBTSxJQUFJLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxDQUFDOztNQUUzQixFQUFFLEdBQUcsV0FBVyxDQUFDO01BQ2pCLElBQUksS0FBSyxDQUFDLFVBQVUsQ0FBQyxXQUFXLENBQUMsS0FBSyxFQUFFLEVBQUU7UUFDeEMsRUFBRSxHQUFHLE9BQU8sQ0FBQztRQUNiLFdBQVcsRUFBRSxDQUFDO09BQ2YsTUFBTTtRQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7UUFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE9BQU8sQ0FBQyxDQUFDLEVBQUU7T0FDbEQ7TUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDckIsRUFBRSxHQUFHLFdBQVcsRUFBRSxDQUFDO1FBQ25CLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtVQUNyQixFQUFFLEdBQUcsZUFBZSxFQUFFLENBQUM7VUFDdkIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1lBQ3JCLEVBQUUsR0FBRyxXQUFXLEVBQUUsQ0FBQztZQUNuQixJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7Y0FDckIsSUFBSSxLQUFLLENBQUMsVUFBVSxDQUFDLFdBQVcsQ0FBQyxLQUFLLEVBQUUsRUFBRTtnQkFDeEMsRUFBRSxHQUFHLE9BQU8sQ0FBQztnQkFDYixXQUFXLEVBQUUsQ0FBQztlQUNmLE1BQU07Z0JBQ0wsRUFBRSxHQUFHLFVBQVUsQ0FBQztnQkFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE9BQU8sQ0FBQyxDQUFDLEVBQUU7ZUFDbEQ7Y0FDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7Z0JBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7Z0JBQ3JCLEVBQUUsR0FBRyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUM7Z0JBQ2pCLEVBQUUsR0FBRyxFQUFFLENBQUM7ZUFDVCxNQUFNO2dCQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7Z0JBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7ZUFDYjthQUNGLE1BQU07Y0FDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO2NBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7YUFDYjtXQUNGLE1BQU07WUFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO1lBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7V0FDYjtTQUNGLE1BQU07VUFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO1VBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7U0FDYjtPQUNGLE1BQU07UUFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO1FBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7T0FDYjtNQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtRQUNyQixFQUFFLEdBQUcsYUFBYSxFQUFFLENBQUM7QUFDN0IsT0FBTzs7TUFFRCxPQUFPLEVBQUUsQ0FBQztBQUNoQixLQUFLOztJQUVELFNBQVMsYUFBYSxHQUFHO0FBQzdCLE1BQU0sSUFBSSxFQUFFLENBQUM7O01BRVAsRUFBRSxHQUFHLG9CQUFvQixFQUFFLENBQUM7TUFDNUIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1FBQ3JCLEVBQUUsR0FBRyxrQkFBa0IsRUFBRSxDQUFDO0FBQ2xDLE9BQU87O01BRUQsT0FBTyxFQUFFLENBQUM7QUFDaEIsS0FBSzs7SUFFRCxTQUFTLG9CQUFvQixHQUFHO0FBQ3BDLE1BQU0sSUFBSSxFQUFFLEVBQUUsRUFBRSxDQUFDOztNQUVYLEVBQUUsR0FBRyx1QkFBdUIsRUFBRSxDQUFDO01BQy9CLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtRQUNyQixFQUFFLEdBQUcsV0FBVyxDQUFDO1FBQ2pCLElBQUksS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLEVBQUUsQ0FBQyxDQUFDLEtBQUssT0FBTyxFQUFFO1VBQzVDLEVBQUUsR0FBRyxPQUFPLENBQUM7VUFDYixXQUFXLElBQUksQ0FBQyxDQUFDO1NBQ2xCLE1BQU07VUFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO1VBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO1NBQ2xEO1FBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1VBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7VUFDckIsRUFBRSxHQUFHLE9BQU8sRUFBRSxDQUFDO1NBQ2hCO1FBQ0QsRUFBRSxHQUFHLEVBQUUsQ0FBQztRQUNSLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtVQUNyQixFQUFFLEdBQUcsV0FBVyxDQUFDO1VBQ2pCLElBQUksS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLEVBQUUsQ0FBQyxDQUFDLEtBQUssT0FBTyxFQUFFO1lBQzVDLEVBQUUsR0FBRyxPQUFPLENBQUM7WUFDYixXQUFXLElBQUksQ0FBQyxDQUFDO1dBQ2xCLE1BQU07WUFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO1lBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO1dBQ2xEO1VBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1lBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7WUFDckIsRUFBRSxHQUFHLE9BQU8sRUFBRSxDQUFDO1dBQ2hCO1VBQ0QsRUFBRSxHQUFHLEVBQUUsQ0FBQztVQUNSLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtZQUNyQixFQUFFLEdBQUcsV0FBVyxDQUFDO1lBQ2pCLElBQUksS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLEVBQUUsQ0FBQyxDQUFDLEtBQUssT0FBTyxFQUFFO2NBQzVDLEVBQUUsR0FBRyxPQUFPLENBQUM7Y0FDYixXQUFXLElBQUksQ0FBQyxDQUFDO2FBQ2xCLE1BQU07Y0FDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO2NBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO2FBQ2xEO1lBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO2NBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7Y0FDckIsRUFBRSxHQUFHLE9BQU8sRUFBRSxDQUFDO2FBQ2hCO1lBQ0QsRUFBRSxHQUFHLEVBQUUsQ0FBQztZQUNSLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtjQUNyQixFQUFFLEdBQUcsV0FBVyxDQUFDO2NBQ2pCLElBQUksS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLEVBQUUsQ0FBQyxDQUFDLEtBQUssT0FBTyxFQUFFO2dCQUM1QyxFQUFFLEdBQUcsT0FBTyxDQUFDO2dCQUNiLFdBQVcsSUFBSSxDQUFDLENBQUM7ZUFDbEIsTUFBTTtnQkFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO2dCQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsT0FBTyxDQUFDLENBQUMsRUFBRTtlQUNsRDtjQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtnQkFDckIsZUFBZSxHQUFHLEVBQUUsQ0FBQztnQkFDckIsRUFBRSxHQUFHLE9BQU8sRUFBRSxDQUFDO2VBQ2hCO2NBQ0QsRUFBRSxHQUFHLEVBQUUsQ0FBQzthQUNUO1dBQ0Y7U0FDRjtBQUNULE9BQU87O01BRUQsT0FBTyxFQUFFLENBQUM7QUFDaEIsS0FBSzs7SUFFRCxTQUFTLHVCQUF1QixHQUFHO0FBQ3ZDLE1BQU0sSUFBSSxFQUFFLEVBQUUsRUFBRSxDQUFDOztNQUVYLEVBQUUsR0FBRyxXQUFXLENBQUM7TUFDakIsSUFBSSxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsRUFBRSxDQUFDLENBQUMsS0FBSyxPQUFPLEVBQUU7UUFDNUMsRUFBRSxHQUFHLE9BQU8sQ0FBQztRQUNiLFdBQVcsSUFBSSxDQUFDLENBQUM7T0FDbEIsTUFBTTtRQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7UUFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE9BQU8sQ0FBQyxDQUFDLEVBQUU7T0FDbEQ7TUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDckIsZUFBZSxHQUFHLEVBQUUsQ0FBQztRQUNyQixFQUFFLEdBQUcsT0FBTyxFQUFFLENBQUM7T0FDaEI7TUFDRCxFQUFFLEdBQUcsRUFBRSxDQUFDO01BQ1IsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1FBQ3JCLEVBQUUsR0FBRyxXQUFXLENBQUM7UUFDakIsSUFBSSxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsRUFBRSxDQUFDLENBQUMsS0FBSyxPQUFPLEVBQUU7VUFDNUMsRUFBRSxHQUFHLE9BQU8sQ0FBQztVQUNiLFdBQVcsSUFBSSxDQUFDLENBQUM7U0FDbEIsTUFBTTtVQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7VUFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE9BQU8sQ0FBQyxDQUFDLEVBQUU7U0FDbEQ7UUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7VUFDckIsZUFBZSxHQUFHLEVBQUUsQ0FBQztVQUNyQixFQUFFLEdBQUcsT0FBTyxFQUFFLENBQUM7U0FDaEI7UUFDRCxFQUFFLEdBQUcsRUFBRSxDQUFDO0FBQ2hCLE9BQU87O01BRUQsT0FBTyxFQUFFLENBQUM7QUFDaEIsS0FBSzs7SUFFRCxTQUFTLGtCQUFrQixHQUFHO0FBQ2xDLE1BQU0sSUFBSSxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLENBQUM7O01BRW5CLEVBQUUsR0FBRyxXQUFXLENBQUM7TUFDakIsSUFBSSxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsRUFBRSxDQUFDLENBQUMsS0FBSyxPQUFPLEVBQUU7UUFDNUMsRUFBRSxHQUFHLE9BQU8sQ0FBQztRQUNiLFdBQVcsSUFBSSxDQUFDLENBQUM7T0FDbEIsTUFBTTtRQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7UUFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE9BQU8sQ0FBQyxDQUFDLEVBQUU7T0FDbEQ7TUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDckIsRUFBRSxHQUFHLEVBQUUsQ0FBQztRQUNSLEVBQUUsR0FBRyxXQUFXLEVBQUUsQ0FBQztRQUNuQixJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7VUFDckIsT0FBTyxFQUFFLEtBQUssVUFBVSxFQUFFO1lBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7WUFDWixFQUFFLEdBQUcsV0FBVyxFQUFFLENBQUM7V0FDcEI7U0FDRixNQUFNO1VBQ0wsRUFBRSxHQUFHLE1BQU0sQ0FBQztTQUNiO1FBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1VBQ3JCLEVBQUUsR0FBRyx1QkFBdUIsRUFBRSxDQUFDO1VBQy9CLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtZQUNyQixlQUFlLEdBQUcsRUFBRSxDQUFDO1lBQ3JCLEVBQUUsR0FBRyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUM7WUFDakIsRUFBRSxHQUFHLEVBQUUsQ0FBQztXQUNULE1BQU07WUFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO1lBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7V0FDYjtTQUNGLE1BQU07VUFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO1VBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7U0FDYjtPQUNGLE1BQU07UUFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO1FBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7T0FDYjtNQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtRQUNyQixFQUFFLEdBQUcsV0FBVyxDQUFDO1FBQ2pCLElBQUksS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLEVBQUUsQ0FBQyxDQUFDLEtBQUssT0FBTyxFQUFFO1VBQzVDLEVBQUUsR0FBRyxPQUFPLENBQUM7VUFDYixXQUFXLElBQUksQ0FBQyxDQUFDO1NBQ2xCLE1BQU07VUFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO1VBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO1NBQ2xEO1FBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1VBQ3JCLEVBQUUsR0FBRyxFQUFFLENBQUM7VUFDUixFQUFFLEdBQUcsV0FBVyxFQUFFLENBQUM7VUFDbkIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1lBQ3JCLE9BQU8sRUFBRSxLQUFLLFVBQVUsRUFBRTtjQUN4QixFQUFFLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDO2NBQ1osRUFBRSxHQUFHLFdBQVcsRUFBRSxDQUFDO2FBQ3BCO1dBQ0YsTUFBTTtZQUNMLEVBQUUsR0FBRyxNQUFNLENBQUM7V0FDYjtVQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtZQUNyQixFQUFFLEdBQUcsc0JBQXNCLEVBQUUsQ0FBQztZQUM5QixJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7Y0FDckIsZUFBZSxHQUFHLEVBQUUsQ0FBQztjQUNyQixFQUFFLEdBQUcsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDO2NBQ2pCLEVBQUUsR0FBRyxFQUFFLENBQUM7YUFDVCxNQUFNO2NBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztjQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO2FBQ2I7V0FDRixNQUFNO1lBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztZQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO1dBQ2I7U0FDRixNQUFNO1VBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztVQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO1NBQ2I7UUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7VUFDckIsRUFBRSxHQUFHLFdBQVcsQ0FBQztVQUNqQixJQUFJLEtBQUssQ0FBQyxNQUFNLENBQUMsV0FBVyxFQUFFLENBQUMsQ0FBQyxLQUFLLE9BQU8sRUFBRTtZQUM1QyxFQUFFLEdBQUcsT0FBTyxDQUFDO1lBQ2IsV0FBVyxJQUFJLENBQUMsQ0FBQztXQUNsQixNQUFNO1lBQ0wsRUFBRSxHQUFHLFVBQVUsQ0FBQztZQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsT0FBTyxDQUFDLENBQUMsRUFBRTtXQUNsRDtVQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtZQUNyQixFQUFFLEdBQUcsRUFBRSxDQUFDO1lBQ1IsRUFBRSxHQUFHLFdBQVcsRUFBRSxDQUFDO1lBQ25CLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtjQUNyQixPQUFPLEVBQUUsS0FBSyxVQUFVLEVBQUU7Z0JBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7Z0JBQ1osRUFBRSxHQUFHLFdBQVcsRUFBRSxDQUFDO2VBQ3BCO2FBQ0YsTUFBTTtjQUNMLEVBQUUsR0FBRyxNQUFNLENBQUM7YUFDYjtZQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtjQUNyQixFQUFFLEdBQUcsc0JBQXNCLEVBQUUsQ0FBQztjQUM5QixJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7Z0JBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7Z0JBQ3JCLEVBQUUsR0FBRyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUM7Z0JBQ2pCLEVBQUUsR0FBRyxFQUFFLENBQUM7ZUFDVCxNQUFNO2dCQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7Z0JBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7ZUFDYjthQUNGLE1BQU07Y0FDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO2NBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7YUFDYjtXQUNGLE1BQU07WUFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO1lBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7V0FDYjtVQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtZQUNyQixFQUFFLEdBQUcsV0FBVyxDQUFDO1lBQ2pCLElBQUksS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLEVBQUUsQ0FBQyxDQUFDLEtBQUssT0FBTyxFQUFFO2NBQzVDLEVBQUUsR0FBRyxPQUFPLENBQUM7Y0FDYixXQUFXLElBQUksQ0FBQyxDQUFDO2FBQ2xCLE1BQU07Y0FDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO2NBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO2FBQ2xEO1lBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO2NBQ3JCLEVBQUUsR0FBRyxFQUFFLENBQUM7Y0FDUixFQUFFLEdBQUcsV0FBVyxFQUFFLENBQUM7Y0FDbkIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO2dCQUNyQixPQUFPLEVBQUUsS0FBSyxVQUFVLEVBQUU7a0JBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7a0JBQ1osRUFBRSxHQUFHLFdBQVcsRUFBRSxDQUFDO2lCQUNwQjtlQUNGLE1BQU07Z0JBQ0wsRUFBRSxHQUFHLE1BQU0sQ0FBQztlQUNiO2NBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO2dCQUNyQixFQUFFLEdBQUcsc0JBQXNCLEVBQUUsQ0FBQztnQkFDOUIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO2tCQUNyQixlQUFlLEdBQUcsRUFBRSxDQUFDO2tCQUNyQixFQUFFLEdBQUcsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDO2tCQUNqQixFQUFFLEdBQUcsRUFBRSxDQUFDO2lCQUNULE1BQU07a0JBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztrQkFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztpQkFDYjtlQUNGLE1BQU07Z0JBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztnQkFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztlQUNiO2FBQ0YsTUFBTTtjQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7Y0FDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQzthQUNiO1lBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO2NBQ3JCLEVBQUUsR0FBRyxXQUFXLENBQUM7Y0FDakIsSUFBSSxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsRUFBRSxDQUFDLENBQUMsS0FBSyxPQUFPLEVBQUU7Z0JBQzVDLEVBQUUsR0FBRyxPQUFPLENBQUM7Z0JBQ2IsV0FBVyxJQUFJLENBQUMsQ0FBQztlQUNsQixNQUFNO2dCQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7Z0JBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO2VBQ2xEO2NBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO2dCQUNyQixFQUFFLEdBQUcsRUFBRSxDQUFDO2dCQUNSLEVBQUUsR0FBRyxXQUFXLEVBQUUsQ0FBQztnQkFDbkIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO2tCQUNyQixPQUFPLEVBQUUsS0FBSyxVQUFVLEVBQUU7b0JBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7b0JBQ1osRUFBRSxHQUFHLFdBQVcsRUFBRSxDQUFDO21CQUNwQjtpQkFDRixNQUFNO2tCQUNMLEVBQUUsR0FBRyxNQUFNLENBQUM7aUJBQ2I7Z0JBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO2tCQUNyQixFQUFFLEdBQUcsc0JBQXNCLEVBQUUsQ0FBQztrQkFDOUIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO29CQUNyQixlQUFlLEdBQUcsRUFBRSxDQUFDO29CQUNyQixFQUFFLEdBQUcsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDO29CQUNqQixFQUFFLEdBQUcsRUFBRSxDQUFDO21CQUNULE1BQU07b0JBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztvQkFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQzttQkFDYjtpQkFDRixNQUFNO2tCQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7a0JBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7aUJBQ2I7ZUFDRixNQUFNO2dCQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7Z0JBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7ZUFDYjtjQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtnQkFDckIsRUFBRSxHQUFHLFdBQVcsQ0FBQztnQkFDakIsSUFBSSxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsRUFBRSxDQUFDLENBQUMsS0FBSyxPQUFPLEVBQUU7a0JBQzVDLEVBQUUsR0FBRyxPQUFPLENBQUM7a0JBQ2IsV0FBVyxJQUFJLENBQUMsQ0FBQztpQkFDbEIsTUFBTTtrQkFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO2tCQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsT0FBTyxDQUFDLENBQUMsRUFBRTtpQkFDbEQ7Z0JBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO2tCQUNyQixFQUFFLEdBQUcsRUFBRSxDQUFDO2tCQUNSLEVBQUUsR0FBRyxXQUFXLEVBQUUsQ0FBQztrQkFDbkIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO29CQUNyQixPQUFPLEVBQUUsS0FBSyxVQUFVLEVBQUU7c0JBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7c0JBQ1osRUFBRSxHQUFHLFdBQVcsRUFBRSxDQUFDO3FCQUNwQjttQkFDRixNQUFNO29CQUNMLEVBQUUsR0FBRyxNQUFNLENBQUM7bUJBQ2I7a0JBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO29CQUNyQixFQUFFLEdBQUcsc0JBQXNCLEVBQUUsQ0FBQztvQkFDOUIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO3NCQUNyQixlQUFlLEdBQUcsRUFBRSxDQUFDO3NCQUNyQixFQUFFLEdBQUcsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDO3NCQUNqQixFQUFFLEdBQUcsRUFBRSxDQUFDO3FCQUNULE1BQU07c0JBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztzQkFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztxQkFDYjttQkFDRixNQUFNO29CQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7b0JBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7bUJBQ2I7aUJBQ0YsTUFBTTtrQkFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO2tCQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO2lCQUNiO2dCQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtrQkFDckIsRUFBRSxHQUFHLFdBQVcsQ0FBQztrQkFDakIsSUFBSSxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsRUFBRSxDQUFDLENBQUMsS0FBSyxPQUFPLEVBQUU7b0JBQzVDLEVBQUUsR0FBRyxPQUFPLENBQUM7b0JBQ2IsV0FBVyxJQUFJLENBQUMsQ0FBQzttQkFDbEIsTUFBTTtvQkFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO29CQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsT0FBTyxDQUFDLENBQUMsRUFBRTttQkFDbEQ7a0JBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO29CQUNyQixFQUFFLEdBQUcsRUFBRSxDQUFDO29CQUNSLEVBQUUsR0FBRyxXQUFXLEVBQUUsQ0FBQztvQkFDbkIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO3NCQUNyQixPQUFPLEVBQUUsS0FBSyxVQUFVLEVBQUU7d0JBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7d0JBQ1osRUFBRSxHQUFHLFdBQVcsRUFBRSxDQUFDO3VCQUNwQjtxQkFDRixNQUFNO3NCQUNMLEVBQUUsR0FBRyxNQUFNLENBQUM7cUJBQ2I7b0JBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO3NCQUNyQixFQUFFLEdBQUcsc0JBQXNCLEVBQUUsQ0FBQztzQkFDOUIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO3dCQUNyQixlQUFlLEdBQUcsRUFBRSxDQUFDO3dCQUNyQixFQUFFLEdBQUcsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDO3dCQUNqQixFQUFFLEdBQUcsRUFBRSxDQUFDO3VCQUNULE1BQU07d0JBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQzt3QkFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQzt1QkFDYjtxQkFDRixNQUFNO3NCQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7c0JBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7cUJBQ2I7bUJBQ0YsTUFBTTtvQkFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO29CQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO21CQUNiO2tCQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtvQkFDckIsRUFBRSxHQUFHLFdBQVcsQ0FBQztvQkFDakIsSUFBSSxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsRUFBRSxDQUFDLENBQUMsS0FBSyxPQUFPLEVBQUU7c0JBQzVDLEVBQUUsR0FBRyxPQUFPLENBQUM7c0JBQ2IsV0FBVyxJQUFJLENBQUMsQ0FBQztxQkFDbEIsTUFBTTtzQkFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO3NCQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsT0FBTyxDQUFDLENBQUMsRUFBRTtxQkFDbEQ7b0JBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO3NCQUNyQixFQUFFLEdBQUcsRUFBRSxDQUFDO3NCQUNSLEVBQUUsR0FBRyxXQUFXLEVBQUUsQ0FBQztzQkFDbkIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO3dCQUNyQixPQUFPLEVBQUUsS0FBSyxVQUFVLEVBQUU7MEJBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7MEJBQ1osRUFBRSxHQUFHLFdBQVcsRUFBRSxDQUFDO3lCQUNwQjt1QkFDRixNQUFNO3dCQUNMLEVBQUUsR0FBRyxNQUFNLENBQUM7dUJBQ2I7c0JBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO3dCQUNyQixFQUFFLEdBQUcsc0JBQXNCLEVBQUUsQ0FBQzt3QkFDOUIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFOzBCQUNyQixlQUFlLEdBQUcsRUFBRSxDQUFDOzBCQUNyQixFQUFFLEdBQUcsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDOzBCQUNqQixFQUFFLEdBQUcsRUFBRSxDQUFDO3lCQUNULE1BQU07MEJBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQzswQkFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQzt5QkFDYjt1QkFDRixNQUFNO3dCQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7d0JBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7dUJBQ2I7cUJBQ0YsTUFBTTtzQkFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO3NCQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO3FCQUNiO29CQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtzQkFDckIsRUFBRSxHQUFHLFdBQVcsQ0FBQztzQkFDakIsSUFBSSxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsRUFBRSxDQUFDLENBQUMsS0FBSyxPQUFPLEVBQUU7d0JBQzVDLEVBQUUsR0FBRyxPQUFPLENBQUM7d0JBQ2IsV0FBVyxJQUFJLENBQUMsQ0FBQzt1QkFDbEIsTUFBTTt3QkFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO3dCQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsT0FBTyxDQUFDLENBQUMsRUFBRTt1QkFDbEQ7c0JBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO3dCQUNyQixFQUFFLEdBQUcsRUFBRSxDQUFDO3dCQUNSLEVBQUUsR0FBRyxXQUFXLEVBQUUsQ0FBQzt3QkFDbkIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFOzBCQUNyQixPQUFPLEVBQUUsS0FBSyxVQUFVLEVBQUU7NEJBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7NEJBQ1osRUFBRSxHQUFHLFdBQVcsRUFBRSxDQUFDOzJCQUNwQjt5QkFDRixNQUFNOzBCQUNMLEVBQUUsR0FBRyxNQUFNLENBQUM7eUJBQ2I7d0JBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFOzBCQUNyQixFQUFFLEdBQUcsc0JBQXNCLEVBQUUsQ0FBQzswQkFDOUIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFOzRCQUNyQixlQUFlLEdBQUcsRUFBRSxDQUFDOzRCQUNyQixFQUFFLEdBQUcsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDOzRCQUNqQixFQUFFLEdBQUcsRUFBRSxDQUFDOzJCQUNULE1BQU07NEJBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQzs0QkFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQzsyQkFDYjt5QkFDRixNQUFNOzBCQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7MEJBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7eUJBQ2I7dUJBQ0YsTUFBTTt3QkFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO3dCQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO3VCQUNiO3NCQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTt3QkFDckIsRUFBRSxHQUFHLFdBQVcsQ0FBQzt3QkFDakIsSUFBSSxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsRUFBRSxDQUFDLENBQUMsS0FBSyxPQUFPLEVBQUU7MEJBQzVDLEVBQUUsR0FBRyxPQUFPLENBQUM7MEJBQ2IsV0FBVyxJQUFJLENBQUMsQ0FBQzt5QkFDbEIsTUFBTTswQkFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDOzBCQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsT0FBTyxDQUFDLENBQUMsRUFBRTt5QkFDbEQ7d0JBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFOzBCQUNyQixFQUFFLEdBQUcsRUFBRSxDQUFDOzBCQUNSLEVBQUUsR0FBRyxXQUFXLEVBQUUsQ0FBQzswQkFDbkIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFOzRCQUNyQixPQUFPLEVBQUUsS0FBSyxVQUFVLEVBQUU7OEJBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7OEJBQ1osRUFBRSxHQUFHLFdBQVcsRUFBRSxDQUFDOzZCQUNwQjsyQkFDRixNQUFNOzRCQUNMLEVBQUUsR0FBRyxNQUFNLENBQUM7MkJBQ2I7MEJBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFOzRCQUNyQixFQUFFLEdBQUcsc0JBQXNCLEVBQUUsQ0FBQzs0QkFDOUIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFOzhCQUNyQixlQUFlLEdBQUcsRUFBRSxDQUFDOzhCQUNyQixFQUFFLEdBQUcsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDOzhCQUNqQixFQUFFLEdBQUcsRUFBRSxDQUFDOzZCQUNULE1BQU07OEJBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQzs4QkFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQzs2QkFDYjsyQkFDRixNQUFNOzRCQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7NEJBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7MkJBQ2I7eUJBQ0YsTUFBTTswQkFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDOzBCQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO3lCQUNiO3dCQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTswQkFDckIsRUFBRSxHQUFHLFdBQVcsQ0FBQzswQkFDakIsRUFBRSxHQUFHLHNCQUFzQixFQUFFLENBQUM7MEJBQzlCLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTs0QkFDckIsZUFBZSxHQUFHLEVBQUUsQ0FBQzs0QkFDckIsRUFBRSxHQUFHLE9BQU8sQ0FBQyxFQUFFLENBQUMsQ0FBQzsyQkFDbEI7MEJBQ0QsRUFBRSxHQUFHLEVBQUUsQ0FBQzt5QkFDVDt1QkFDRjtxQkFDRjttQkFDRjtpQkFDRjtlQUNGO2FBQ0Y7V0FDRjtTQUNGO0FBQ1QsT0FBTzs7TUFFRCxPQUFPLEVBQUUsQ0FBQztBQUNoQixLQUFLOztJQUVELFNBQVMsdUJBQXVCLEdBQUc7QUFDdkMsTUFBTSxJQUFJLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsQ0FBQzs7TUFFbkIsZUFBZSxFQUFFLENBQUM7TUFDbEIsRUFBRSxHQUFHLFdBQVcsQ0FBQztNQUNqQixJQUFJLE9BQU8sQ0FBQyxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLENBQUMsQ0FBQyxFQUFFO1FBQzNDLEVBQUUsR0FBRyxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsQ0FBQyxDQUFDO1FBQy9CLFdBQVcsRUFBRSxDQUFDO09BQ2YsTUFBTTtRQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7UUFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE9BQU8sQ0FBQyxDQUFDLEVBQUU7T0FDbEQ7TUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDckIsRUFBRSxHQUFHLE9BQU8sQ0FBQztPQUNkO01BQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1FBQ3JCLEVBQUUsR0FBRyxFQUFFLENBQUM7UUFDUixJQUFJLE9BQU8sQ0FBQyxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLENBQUMsQ0FBQyxFQUFFO1VBQzNDLEVBQUUsR0FBRyxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsQ0FBQyxDQUFDO1VBQy9CLFdBQVcsRUFBRSxDQUFDO1NBQ2YsTUFBTTtVQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7VUFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE9BQU8sQ0FBQyxDQUFDLEVBQUU7U0FDbEQ7UUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7VUFDckIsT0FBTyxFQUFFLEtBQUssVUFBVSxFQUFFO1lBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7WUFDWixJQUFJLE9BQU8sQ0FBQyxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLENBQUMsQ0FBQyxFQUFFO2NBQzNDLEVBQUUsR0FBRyxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsQ0FBQyxDQUFDO2NBQy9CLFdBQVcsRUFBRSxDQUFDO2FBQ2YsTUFBTTtjQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7Y0FDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE9BQU8sQ0FBQyxDQUFDLEVBQUU7YUFDbEQ7V0FDRjtTQUNGLE1BQU07VUFDTCxFQUFFLEdBQUcsTUFBTSxDQUFDO1NBQ2I7UUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7VUFDckIsSUFBSSxPQUFPLENBQUMsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUMsV0FBVyxDQUFDLENBQUMsRUFBRTtZQUMzQyxFQUFFLEdBQUcsS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLENBQUMsQ0FBQztZQUMvQixXQUFXLEVBQUUsQ0FBQztXQUNmLE1BQU07WUFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO1lBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO1dBQ2xEO1VBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1lBQ3JCLEVBQUUsR0FBRyxPQUFPLENBQUM7V0FDZDtVQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtZQUNyQixlQUFlLEdBQUcsRUFBRSxDQUFDO1lBQ3JCLEVBQUUsR0FBRyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUM7WUFDakIsRUFBRSxHQUFHLEVBQUUsQ0FBQztXQUNULE1BQU07WUFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO1lBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7V0FDYjtTQUNGLE1BQU07VUFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO1VBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7U0FDYjtPQUNGLE1BQU07UUFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO1FBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7T0FDYjtNQUNELGVBQWUsRUFBRSxDQUFDO01BQ2xCLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtRQUNyQixFQUFFLEdBQUcsVUFBVSxDQUFDO1FBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO0FBQ3pELE9BQU87O01BRUQsT0FBTyxFQUFFLENBQUM7QUFDaEIsS0FBSzs7SUFFRCxTQUFTLHNCQUFzQixHQUFHO0FBQ3RDLE1BQU0sSUFBSSxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLENBQUM7O01BRW5CLGVBQWUsRUFBRSxDQUFDO01BQ2xCLEVBQUUsR0FBRyxXQUFXLENBQUM7TUFDakIsSUFBSSxLQUFLLENBQUMsVUFBVSxDQUFDLFdBQVcsQ0FBQyxLQUFLLEVBQUUsRUFBRTtRQUN4QyxFQUFFLEdBQUcsT0FBTyxDQUFDO1FBQ2IsV0FBVyxFQUFFLENBQUM7T0FDZixNQUFNO1FBQ0wsRUFBRSxHQUFHLFVBQVUsQ0FBQztRQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsT0FBTyxDQUFDLENBQUMsRUFBRTtPQUNsRDtNQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtRQUNyQixFQUFFLEdBQUcsRUFBRSxDQUFDO1FBQ1IsRUFBRSxHQUFHLHlCQUF5QixFQUFFLENBQUM7UUFDakMsT0FBTyxFQUFFLEtBQUssVUFBVSxFQUFFO1VBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7VUFDWixFQUFFLEdBQUcseUJBQXlCLEVBQUUsQ0FBQztTQUNsQztRQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtVQUNyQixJQUFJLEtBQUssQ0FBQyxVQUFVLENBQUMsV0FBVyxDQUFDLEtBQUssRUFBRSxFQUFFO1lBQ3hDLEVBQUUsR0FBRyxPQUFPLENBQUM7WUFDYixXQUFXLEVBQUUsQ0FBQztXQUNmLE1BQU07WUFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO1lBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO1dBQ2xEO1VBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1lBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7WUFDckIsRUFBRSxHQUFHLE9BQU8sQ0FBQyxFQUFFLENBQUMsQ0FBQztZQUNqQixFQUFFLEdBQUcsRUFBRSxDQUFDO1dBQ1QsTUFBTTtZQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7WUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztXQUNiO1NBQ0YsTUFBTTtVQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7VUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztTQUNiO09BQ0YsTUFBTTtRQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7UUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztPQUNiO01BQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1FBQ3JCLEVBQUUsR0FBRyxXQUFXLENBQUM7UUFDakIsSUFBSSxLQUFLLENBQUMsVUFBVSxDQUFDLFdBQVcsQ0FBQyxLQUFLLEVBQUUsRUFBRTtVQUN4QyxFQUFFLEdBQUcsT0FBTyxDQUFDO1VBQ2IsV0FBVyxFQUFFLENBQUM7U0FDZixNQUFNO1VBQ0wsRUFBRSxHQUFHLFVBQVUsQ0FBQztVQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsT0FBTyxDQUFDLENBQUMsRUFBRTtTQUNsRDtRQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtVQUNyQixFQUFFLEdBQUcsRUFBRSxDQUFDO1VBQ1IsRUFBRSxHQUFHLHlCQUF5QixFQUFFLENBQUM7VUFDakMsT0FBTyxFQUFFLEtBQUssVUFBVSxFQUFFO1lBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7WUFDWixFQUFFLEdBQUcseUJBQXlCLEVBQUUsQ0FBQztXQUNsQztVQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtZQUNyQixJQUFJLEtBQUssQ0FBQyxVQUFVLENBQUMsV0FBVyxDQUFDLEtBQUssRUFBRSxFQUFFO2NBQ3hDLEVBQUUsR0FBRyxPQUFPLENBQUM7Y0FDYixXQUFXLEVBQUUsQ0FBQzthQUNmLE1BQU07Y0FDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO2NBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO2FBQ2xEO1lBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO2NBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7Y0FDckIsRUFBRSxHQUFHLE9BQU8sQ0FBQyxFQUFFLENBQUMsQ0FBQztjQUNqQixFQUFFLEdBQUcsRUFBRSxDQUFDO2FBQ1QsTUFBTTtjQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7Y0FDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQzthQUNiO1dBQ0YsTUFBTTtZQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7WUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztXQUNiO1NBQ0YsTUFBTTtVQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7VUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztTQUNiO1FBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1VBQ3JCLEVBQUUsR0FBRyxXQUFXLENBQUM7VUFDakIsRUFBRSxHQUFHLFdBQVcsQ0FBQztVQUNqQixlQUFlLEVBQUUsQ0FBQztVQUNsQixFQUFFLEdBQUcsV0FBVyxFQUFFLENBQUM7VUFDbkIsZUFBZSxFQUFFLENBQUM7VUFDbEIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1lBQ3JCLEVBQUUsR0FBRyxPQUFPLENBQUM7V0FDZCxNQUFNO1lBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztZQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO1dBQ2I7VUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7WUFDckIsRUFBRSxHQUFHLEVBQUUsQ0FBQztZQUNSLEVBQUUsR0FBRywyQkFBMkIsRUFBRSxDQUFDO1lBQ25DLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtjQUNyQixPQUFPLEVBQUUsS0FBSyxVQUFVLEVBQUU7Z0JBQ3hCLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUM7Z0JBQ1osRUFBRSxHQUFHLDJCQUEyQixFQUFFLENBQUM7ZUFDcEM7YUFDRixNQUFNO2NBQ0wsRUFBRSxHQUFHLE1BQU0sQ0FBQzthQUNiO1lBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO2NBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7Y0FDckIsRUFBRSxHQUFHLE9BQU8sQ0FBQyxFQUFFLENBQUMsQ0FBQztjQUNqQixFQUFFLEdBQUcsRUFBRSxDQUFDO2FBQ1QsTUFBTTtjQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7Y0FDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQzthQUNiO1dBQ0YsTUFBTTtZQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7WUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztXQUNiO1NBQ0Y7T0FDRjtNQUNELGVBQWUsRUFBRSxDQUFDO01BQ2xCLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtRQUNyQixFQUFFLEdBQUcsVUFBVSxDQUFDO1FBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO0FBQ3pELE9BQU87O01BRUQsT0FBTyxFQUFFLENBQUM7QUFDaEIsS0FBSzs7SUFFRCxTQUFTLHlCQUF5QixHQUFHO0FBQ3pDLE1BQU0sSUFBSSxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsQ0FBQzs7TUFFZixFQUFFLEdBQUcsV0FBVyxDQUFDO01BQ2pCLEVBQUUsR0FBRyxXQUFXLENBQUM7TUFDakIsZUFBZSxFQUFFLENBQUM7TUFDbEIsSUFBSSxPQUFPLENBQUMsSUFBSSxDQUFDLEtBQUssQ0FBQyxNQUFNLENBQUMsV0FBVyxDQUFDLENBQUMsRUFBRTtRQUMzQyxFQUFFLEdBQUcsS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLENBQUMsQ0FBQztRQUMvQixXQUFXLEVBQUUsQ0FBQztPQUNmLE1BQU07UUFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO1FBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO09BQ2xEO01BQ0QsZUFBZSxFQUFFLENBQUM7TUFDbEIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1FBQ3JCLEVBQUUsR0FBRyxPQUFPLENBQUM7T0FDZCxNQUFNO1FBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztRQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO09BQ2I7TUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDckIsSUFBSSxLQUFLLENBQUMsTUFBTSxHQUFHLFdBQVcsRUFBRTtVQUM5QixFQUFFLEdBQUcsS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLENBQUMsQ0FBQztVQUMvQixXQUFXLEVBQUUsQ0FBQztTQUNmLE1BQU07VUFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO1VBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO1NBQ2xEO1FBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1VBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7VUFDckIsRUFBRSxHQUFHLE9BQU8sQ0FBQyxFQUFFLENBQUMsQ0FBQztVQUNqQixFQUFFLEdBQUcsRUFBRSxDQUFDO1NBQ1QsTUFBTTtVQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7VUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztTQUNiO09BQ0YsTUFBTTtRQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7UUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztPQUNiO01BQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1FBQ3JCLEVBQUUsR0FBRyxXQUFXLENBQUM7UUFDakIsSUFBSSxLQUFLLENBQUMsVUFBVSxDQUFDLFdBQVcsQ0FBQyxLQUFLLEVBQUUsRUFBRTtVQUN4QyxFQUFFLEdBQUcsT0FBTyxDQUFDO1VBQ2IsV0FBVyxFQUFFLENBQUM7U0FDZixNQUFNO1VBQ0wsRUFBRSxHQUFHLFVBQVUsQ0FBQztVQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsT0FBTyxDQUFDLENBQUMsRUFBRTtTQUNsRDtRQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtVQUNyQixFQUFFLEdBQUcsdUJBQXVCLEVBQUUsQ0FBQztVQUMvQixJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7WUFDckIsZUFBZSxHQUFHLEVBQUUsQ0FBQztZQUNyQixFQUFFLEdBQUcsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDO1lBQ2pCLEVBQUUsR0FBRyxFQUFFLENBQUM7V0FDVCxNQUFNO1lBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztZQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO1dBQ2I7U0FDRixNQUFNO1VBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztVQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO1NBQ2I7QUFDVCxPQUFPOztNQUVELE9BQU8sRUFBRSxDQUFDO0FBQ2hCLEtBQUs7O0lBRUQsU0FBUyx5QkFBeUIsR0FBRztBQUN6QyxNQUFNLElBQUksRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLENBQUM7O01BRWYsRUFBRSxHQUFHLFdBQVcsQ0FBQztNQUNqQixFQUFFLEdBQUcsV0FBVyxDQUFDO01BQ2pCLGVBQWUsRUFBRSxDQUFDO01BQ2xCLElBQUksT0FBTyxDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsQ0FBQyxDQUFDLEVBQUU7UUFDM0MsRUFBRSxHQUFHLEtBQUssQ0FBQyxNQUFNLENBQUMsV0FBVyxDQUFDLENBQUM7UUFDL0IsV0FBVyxFQUFFLENBQUM7T0FDZixNQUFNO1FBQ0wsRUFBRSxHQUFHLFVBQVUsQ0FBQztRQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsT0FBTyxDQUFDLENBQUMsRUFBRTtPQUNsRDtNQUNELGVBQWUsRUFBRSxDQUFDO01BQ2xCLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtRQUNyQixFQUFFLEdBQUcsT0FBTyxDQUFDO09BQ2QsTUFBTTtRQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7UUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztPQUNiO01BQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1FBQ3JCLElBQUksS0FBSyxDQUFDLE1BQU0sR0FBRyxXQUFXLEVBQUU7VUFDOUIsRUFBRSxHQUFHLEtBQUssQ0FBQyxNQUFNLENBQUMsV0FBVyxDQUFDLENBQUM7VUFDL0IsV0FBVyxFQUFFLENBQUM7U0FDZixNQUFNO1VBQ0wsRUFBRSxHQUFHLFVBQVUsQ0FBQztVQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsT0FBTyxDQUFDLENBQUMsRUFBRTtTQUNsRDtRQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtVQUNyQixlQUFlLEdBQUcsRUFBRSxDQUFDO1VBQ3JCLEVBQUUsR0FBRyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUM7VUFDakIsRUFBRSxHQUFHLEVBQUUsQ0FBQztTQUNULE1BQU07VUFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO1VBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7U0FDYjtPQUNGLE1BQU07UUFDTCxXQUFXLEdBQUcsRUFBRSxDQUFDO1FBQ2pCLEVBQUUsR0FBRyxNQUFNLENBQUM7T0FDYjtNQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtRQUNyQixFQUFFLEdBQUcsV0FBVyxDQUFDO1FBQ2pCLElBQUksS0FBSyxDQUFDLFVBQVUsQ0FBQyxXQUFXLENBQUMsS0FBSyxFQUFFLEVBQUU7VUFDeEMsRUFBRSxHQUFHLE9BQU8sQ0FBQztVQUNiLFdBQVcsRUFBRSxDQUFDO1NBQ2YsTUFBTTtVQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7VUFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE9BQU8sQ0FBQyxDQUFDLEVBQUU7U0FDbEQ7UUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7VUFDckIsRUFBRSxHQUFHLHVCQUF1QixFQUFFLENBQUM7VUFDL0IsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1lBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7WUFDckIsRUFBRSxHQUFHLE9BQU8sQ0FBQyxFQUFFLENBQUMsQ0FBQztZQUNqQixFQUFFLEdBQUcsRUFBRSxDQUFDO1dBQ1QsTUFBTTtZQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7WUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztXQUNiO1NBQ0YsTUFBTTtVQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7VUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztTQUNiO0FBQ1QsT0FBTzs7TUFFRCxPQUFPLEVBQUUsQ0FBQztBQUNoQixLQUFLOztJQUVELFNBQVMsMkJBQTJCLEdBQUc7QUFDM0MsTUFBTSxJQUFJLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxDQUFDOztNQUVmLEVBQUUsR0FBRyxXQUFXLENBQUM7TUFDakIsRUFBRSxHQUFHLFdBQVcsQ0FBQztNQUNqQixlQUFlLEVBQUUsQ0FBQztNQUNsQixFQUFFLEdBQUcsV0FBVyxFQUFFLENBQUM7TUFDbkIsZUFBZSxFQUFFLENBQUM7TUFDbEIsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1FBQ3JCLEVBQUUsR0FBRyxPQUFPLENBQUM7T0FDZCxNQUFNO1FBQ0wsV0FBVyxHQUFHLEVBQUUsQ0FBQztRQUNqQixFQUFFLEdBQUcsTUFBTSxDQUFDO09BQ2I7TUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDckIsSUFBSSxLQUFLLENBQUMsTUFBTSxHQUFHLFdBQVcsRUFBRTtVQUM5QixFQUFFLEdBQUcsS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLENBQUMsQ0FBQztVQUMvQixXQUFXLEVBQUUsQ0FBQztTQUNmLE1BQU07VUFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO1VBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO1NBQ2xEO1FBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1VBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7VUFDckIsRUFBRSxHQUFHLE9BQU8sQ0FBQyxFQUFFLENBQUMsQ0FBQztVQUNqQixFQUFFLEdBQUcsRUFBRSxDQUFDO1NBQ1QsTUFBTTtVQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7VUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztTQUNiO09BQ0YsTUFBTTtRQUNMLFdBQVcsR0FBRyxFQUFFLENBQUM7UUFDakIsRUFBRSxHQUFHLE1BQU0sQ0FBQztBQUNwQixPQUFPOztNQUVELE9BQU8sRUFBRSxDQUFDO0FBQ2hCLEtBQUs7O0lBRUQsU0FBUyx1QkFBdUIsR0FBRztBQUN2QyxNQUFNLElBQUksRUFBRSxFQUFFLEVBQUUsQ0FBQzs7TUFFWCxJQUFJLE9BQU8sQ0FBQyxJQUFJLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxXQUFXLENBQUMsQ0FBQyxFQUFFO1FBQzNDLEVBQUUsR0FBRyxLQUFLLENBQUMsTUFBTSxDQUFDLFdBQVcsQ0FBQyxDQUFDO1FBQy9CLFdBQVcsRUFBRSxDQUFDO09BQ2YsTUFBTTtRQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7UUFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLE9BQU8sQ0FBQyxDQUFDLEVBQUU7T0FDbEQ7TUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7UUFDckIsRUFBRSxHQUFHLFdBQVcsQ0FBQztRQUNqQixJQUFJLEtBQUssQ0FBQyxVQUFVLENBQUMsV0FBVyxDQUFDLEtBQUssR0FBRyxFQUFFO1VBQ3pDLEVBQUUsR0FBRyxPQUFPLENBQUM7VUFDYixXQUFXLEVBQUUsQ0FBQztTQUNmLE1BQU07VUFDTCxFQUFFLEdBQUcsVUFBVSxDQUFDO1VBQ2hCLElBQUksZUFBZSxLQUFLLENBQUMsRUFBRSxFQUFFLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxFQUFFO1NBQ2xEO1FBQ0QsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1VBQ3JCLGVBQWUsR0FBRyxFQUFFLENBQUM7VUFDckIsRUFBRSxHQUFHLFFBQVEsRUFBRSxDQUFDO1NBQ2pCO1FBQ0QsRUFBRSxHQUFHLEVBQUUsQ0FBQztRQUNSLElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtVQUNyQixFQUFFLEdBQUcsV0FBVyxDQUFDO1VBQ2pCLElBQUksS0FBSyxDQUFDLFVBQVUsQ0FBQyxXQUFXLENBQUMsS0FBSyxHQUFHLEVBQUU7WUFDekMsRUFBRSxHQUFHLFFBQVEsQ0FBQztZQUNkLFdBQVcsRUFBRSxDQUFDO1dBQ2YsTUFBTTtZQUNMLEVBQUUsR0FBRyxVQUFVLENBQUM7WUFDaEIsSUFBSSxlQUFlLEtBQUssQ0FBQyxFQUFFLEVBQUUsUUFBUSxDQUFDLFFBQVEsQ0FBQyxDQUFDLEVBQUU7V0FDbkQ7VUFDRCxJQUFJLEVBQUUsS0FBSyxVQUFVLEVBQUU7WUFDckIsZUFBZSxHQUFHLEVBQUUsQ0FBQztZQUNyQixFQUFFLEdBQUcsUUFBUSxFQUFFLENBQUM7V0FDakI7VUFDRCxFQUFFLEdBQUcsRUFBRSxDQUFDO1VBQ1IsSUFBSSxFQUFFLEtBQUssVUFBVSxFQUFFO1lBQ3JCLEVBQUUsR0FBRyxXQUFXLENBQUM7WUFDakIsSUFBSSxLQUFLLENBQUMsVUFBVSxDQUFDLFdBQVcsQ0FBQyxLQUFLLEdBQUcsRUFBRTtjQUN6QyxFQUFFLEdBQUcsUUFBUSxDQUFDO2NBQ2QsV0FBVyxFQUFFLENBQUM7YUFDZixNQUFNO2NBQ0wsRUFBRSxHQUFHLFVBQVUsQ0FBQztjQUNoQixJQUFJLGVBQWUsS0FBSyxDQUFDLEVBQUUsRUFBRSxRQUFRLENBQUMsUUFBUSxDQUFDLENBQUMsRUFBRTthQUNuRDtZQUNELElBQUksRUFBRSxLQUFLLFVBQVUsRUFBRTtjQUNyQixlQUFlLEdBQUcsRUFBRSxDQUFDO2NBQ3JCLEVBQUUsR0FBRyxRQUFRLEVBQUUsQ0FBQzthQUNqQjtZQUNELEVBQUUsR0FBRyxFQUFFLENBQUM7V0FDVDtTQUNGO0FBQ1QsT0FBTzs7TUFFRCxPQUFPLEVBQUUsQ0FBQztBQUNoQixLQUFLO0FBQ0w7O0FBRUEsSUFBSSxJQUFJLFNBQVMsR0FBRyxPQUFPLENBQUMsa0JBQWtCLENBQUMsQ0FBQzs7QUFFaEQsSUFBSSxTQUFTLEVBQUUsQ0FBQyxLQUFLLEVBQUUsTUFBTSxFQUFFOztRQUV2QixTQUFTLFFBQVEsR0FBRztZQUNoQixPQUFPLEtBQUssQ0FBQyxLQUFLLENBQUMsSUFBSSxFQUFFLFNBQVMsQ0FBQyxJQUFJLE1BQU0sQ0FBQyxLQUFLLENBQUMsSUFBSSxFQUFFLFNBQVMsQ0FBQyxDQUFDO1NBQ3hFO1FBQ0QsUUFBUSxDQUFDLElBQUksR0FBRyxLQUFLLENBQUMsSUFBSSxHQUFHLE1BQU0sR0FBRyxNQUFNLENBQUMsSUFBSSxDQUFDO1FBQ2xELE9BQU8sUUFBUSxDQUFDO0tBQ25CO0lBQ0QsU0FBUyxHQUFHLENBQUMsS0FBSyxFQUFFLE1BQU0sRUFBRTtRQUN4QixTQUFTLFNBQVMsR0FBRztZQUNqQixPQUFPLEtBQUssQ0FBQyxLQUFLLENBQUMsSUFBSSxFQUFFLFNBQVMsQ0FBQyxJQUFJLE1BQU0sQ0FBQyxLQUFLLENBQUMsSUFBSSxFQUFFLFNBQVMsQ0FBQyxDQUFDO1NBQ3hFO1FBQ0QsU0FBUyxDQUFDLElBQUksR0FBRyxLQUFLLENBQUMsSUFBSSxHQUFHLE9BQU8sR0FBRyxNQUFNLENBQUMsSUFBSSxDQUFDO1FBQ3BELE9BQU8sU0FBUyxDQUFDO0tBQ3BCO0lBQ0QsU0FBUyxHQUFHLENBQUMsSUFBSSxFQUFFO1FBQ2YsU0FBUyxTQUFTLEdBQUc7WUFDakIsT0FBTyxDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxFQUFFLFNBQVMsQ0FBQyxDQUFDO1NBQ3ZDO1FBQ0QsU0FBUyxDQUFDLElBQUksR0FBRyxNQUFNLEdBQUcsSUFBSSxDQUFDLElBQUksQ0FBQztRQUNwQyxPQUFPLFNBQVMsQ0FBQztLQUNwQjtJQUNELFNBQVMsT0FBTyxDQUFDLElBQUksRUFBRTtRQUNuQixTQUFTLGFBQWEsR0FBRztZQUNyQixPQUFPLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxFQUFFLFNBQVMsQ0FBQyxDQUFDO1NBQ3RDO1FBQ0QsYUFBYSxDQUFDLElBQUksR0FBRyxHQUFHLEdBQUcsSUFBSSxDQUFDLElBQUksR0FBRyxHQUFHLENBQUM7UUFDM0MsT0FBTyxhQUFhLENBQUM7S0FDeEI7SUFDRCxTQUFTLFVBQVUsQ0FBQyxJQUFJLEVBQUU7UUFDdEIsT0FBTyxJQUFJLENBQUM7S0FDZjtJQUNELFVBQVUsQ0FBQyxJQUFJLEdBQUcsTUFBTSxDQUFDO0lBQ3pCLFNBQVMsV0FBVyxDQUFDLElBQUksRUFBRTtRQUN2QixPQUFPLEtBQUssQ0FBQztLQUNoQjtBQUNMLElBQUksV0FBVyxDQUFDLElBQUksR0FBRyxPQUFPLENBQUM7O0lBRTNCLElBQUksV0FBVyxHQUFHO1FBQ2QsSUFBSSxNQUFNLENBQUMsaUJBQWlCLENBQUM7UUFDN0IsSUFBSSxNQUFNLENBQUMsMEJBQTBCLENBQUM7UUFDdEMsSUFBSSxNQUFNLENBQUMsd0JBQXdCLENBQUM7UUFDcEMsSUFBSSxNQUFNLENBQUMsVUFBVSxDQUFDO1FBQ3RCLElBQUksTUFBTSxDQUFDLFVBQVUsQ0FBQztRQUN0QixJQUFJLE1BQU0sQ0FBQywrQkFBK0IsQ0FBQztLQUM5QyxDQUFDO0lBQ0YsU0FBUyxXQUFXLENBQUMsSUFBSSxFQUFFO1FBQ3ZCLElBQUksSUFBSSxDQUFDLFFBQVEsRUFBRTtZQUNmLElBQUksRUFBRSxHQUFHLFNBQVMsQ0FBQyxhQUFhLENBQUMsY0FBYyxDQUFDLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQztZQUMvRCxJQUFJLENBQUMsR0FBRyxXQUFXLENBQUMsTUFBTSxDQUFDO1lBQzNCLE9BQU8sQ0FBQyxFQUFFLEVBQUU7Z0JBQ1IsSUFBSSxXQUFXLENBQUMsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxFQUFFO29CQUN6QixPQUFPLElBQUksQ0FBQztpQkFDZjthQUNKO1NBQ0o7UUFDRCxPQUFPLEtBQUssQ0FBQztLQUNoQjtJQUNELFdBQVcsQ0FBQyxJQUFJLEdBQUcsVUFBVSxDQUFDO0lBQzlCLFNBQVMsWUFBWSxDQUFDLElBQUksQ0FBQztRQUN2QixTQUFTLGtCQUFrQixDQUFDLElBQUksQ0FBQztZQUM3QixPQUFPLElBQUksQ0FBQyxRQUFRLElBQUksSUFBSSxDQUFDLFFBQVEsQ0FBQyxJQUFJLEtBQUssSUFBSSxDQUFDO1NBQ3ZEO1FBQ0Qsa0JBQWtCLENBQUMsSUFBSSxHQUFHLGdCQUFnQixHQUFHLElBQUksQ0FBQztRQUNsRCxPQUFPLGtCQUFrQixDQUFDO0tBQzdCO0lBQ0QsU0FBUyxNQUFNLENBQUMsS0FBSyxDQUFDO1FBQ2xCLEtBQUssR0FBRyxJQUFJLE1BQU0sQ0FBQyxLQUFLLEVBQUUsR0FBRyxDQUFDLENBQUM7UUFDL0IsU0FBUyxZQUFZLENBQUMsSUFBSSxDQUFDO1lBQ3ZCLE9BQU8sSUFBSSxDQUFDLE9BQU8sSUFBSSxLQUFLLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxPQUFPLENBQUMsSUFBSSxDQUFDLENBQUM7U0FDeEQ7UUFDRCxZQUFZLENBQUMsSUFBSSxHQUFHLGlCQUFpQixHQUFHLEtBQUssQ0FBQztRQUM5QyxPQUFPLFlBQVksQ0FBQztLQUN2QjtJQUNELFNBQVMsV0FBVyxDQUFDLElBQUksQ0FBQztRQUN0QixPQUFPLENBQUMsQ0FBQyxJQUFJLENBQUMsS0FBSyxDQUFDO0tBQ3ZCO0lBQ0QsV0FBVyxDQUFDLElBQUksR0FBRyxXQUFXLENBQUM7SUFDL0IsU0FBUyxNQUFNLENBQUMsS0FBSyxDQUFDO1FBQ2xCLEtBQUssR0FBRyxJQUFJLE1BQU0sQ0FBQyxLQUFLLEVBQUUsR0FBRyxDQUFDLENBQUM7UUFDL0IsU0FBUyxZQUFZLENBQUMsSUFBSSxDQUFDO1lBQ3ZCO0FBQ1osZ0JBQWdCLENBQUMsSUFBSSxDQUFDLE9BQU8sSUFBSSxTQUFTLENBQUMsWUFBWSxDQUFDLFlBQVksQ0FBQyxJQUFJLENBQUMsT0FBTyxFQUFFLEtBQUssQ0FBQzs7aUJBRXhFLElBQUksQ0FBQyxRQUFRLElBQUksU0FBUyxDQUFDLGFBQWEsQ0FBQyxZQUFZLENBQUMsSUFBSSxDQUFDLFFBQVEsRUFBRSxLQUFLLENBQUMsQ0FBQztjQUMvRTtTQUNMO1FBQ0QsWUFBWSxDQUFDLElBQUksR0FBRyxpQkFBaUIsR0FBRyxLQUFLLENBQUM7UUFDOUMsT0FBTyxZQUFZLENBQUM7S0FDdkI7SUFDRCxTQUFTLGFBQWEsQ0FBQyxLQUFLLENBQUM7UUFDekIsS0FBSyxHQUFHLElBQUksTUFBTSxDQUFDLEtBQUssRUFBRSxHQUFHLENBQUMsQ0FBQztRQUMvQixTQUFTLG1CQUFtQixDQUFDLElBQUksQ0FBQztZQUM5QixRQUFRLElBQUksQ0FBQyxPQUFPLElBQUksU0FBUyxDQUFDLFlBQVksQ0FBQyxZQUFZLENBQUMsSUFBSSxDQUFDLE9BQU8sRUFBRSxLQUFLLENBQUMsRUFBRTtTQUNyRjtRQUNELG1CQUFtQixDQUFDLElBQUksR0FBRyxzQkFBc0IsR0FBRyxLQUFLLENBQUM7UUFDMUQsT0FBTyxtQkFBbUIsQ0FBQztLQUM5QjtJQUNELFNBQVMsY0FBYyxDQUFDLEtBQUssQ0FBQztRQUMxQixLQUFLLEdBQUcsSUFBSSxNQUFNLENBQUMsS0FBSyxFQUFFLEdBQUcsQ0FBQyxDQUFDO1FBQy9CLFNBQVMsb0JBQW9CLENBQUMsSUFBSSxDQUFDO1lBQy9CLFFBQVEsSUFBSSxDQUFDLFFBQVEsSUFBSSxTQUFTLENBQUMsYUFBYSxDQUFDLFlBQVksQ0FBQyxJQUFJLENBQUMsUUFBUSxFQUFFLEtBQUssQ0FBQyxFQUFFO1NBQ3hGO1FBQ0Qsb0JBQW9CLENBQUMsSUFBSSxHQUFHLHVCQUF1QixHQUFHLEtBQUssQ0FBQztRQUM1RCxPQUFPLG9CQUFvQixDQUFDO0tBQy9CO0lBQ0QsU0FBUyxNQUFNLENBQUMsS0FBSyxDQUFDO1FBQ2xCLEtBQUssR0FBRyxJQUFJLE1BQU0sQ0FBQyxLQUFLLEVBQUUsR0FBRyxDQUFDLENBQUM7UUFDL0IsU0FBUyxZQUFZLENBQUMsSUFBSSxDQUFDO1lBQ3ZCLE9BQU8sSUFBSSxDQUFDLE9BQU8sSUFBSSxLQUFLLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxPQUFPLENBQUMsTUFBTSxDQUFDLENBQUM7U0FDMUQ7UUFDRCxZQUFZLENBQUMsSUFBSSxHQUFHLGlCQUFpQixHQUFHLEtBQUssQ0FBQztRQUM5QyxPQUFPLFlBQVksQ0FBQztLQUN2QjtJQUNELFNBQVMsZ0JBQWdCLENBQUMsSUFBSSxDQUFDO1FBQzNCLE9BQU8sSUFBSSxDQUFDLE9BQU8sSUFBSSxDQUFDLElBQUksQ0FBQyxRQUFRLENBQUM7S0FDekM7SUFDRCxnQkFBZ0IsQ0FBQyxJQUFJLEdBQUcsaUJBQWlCLENBQUM7SUFDMUMsU0FBUyxjQUFjLENBQUMsSUFBSSxDQUFDO1FBQ3pCLE9BQU8sQ0FBQyxDQUFDLElBQUksQ0FBQyxRQUFRLENBQUM7S0FDMUI7QUFDTCxJQUFJLGNBQWMsQ0FBQyxJQUFJLEdBQUcsY0FBYyxDQUFDOztJQUVyQyxTQUFTLFdBQVcsQ0FBQyxLQUFLLENBQUM7UUFDdkIsS0FBSyxHQUFHLElBQUksTUFBTSxDQUFDLEtBQUssRUFBRSxHQUFHLENBQUMsQ0FBQztRQUMvQixTQUFTLGlCQUFpQixDQUFDLElBQUksQ0FBQztZQUM1QjtBQUNaLGdCQUFnQixDQUFDLElBQUksQ0FBQyxPQUFPLElBQUksS0FBSyxDQUFDLElBQUksQ0FBQyxTQUFTLENBQUMsWUFBWSxDQUFDLGNBQWMsQ0FBQyxJQUFJLENBQUMsT0FBTyxDQUFDLENBQUM7O2lCQUUvRSxJQUFJLENBQUMsUUFBUSxJQUFJLEtBQUssQ0FBQyxJQUFJLENBQUMsU0FBUyxDQUFDLGFBQWEsQ0FBQyxjQUFjLENBQUMsSUFBSSxDQUFDLFFBQVEsQ0FBQyxDQUFDLENBQUM7Y0FDdEY7U0FDTDtRQUNELGlCQUFpQixDQUFDLElBQUksR0FBRyx1QkFBdUIsR0FBRyxLQUFLLENBQUM7UUFDekQsT0FBTyxpQkFBaUIsQ0FBQztLQUM1QjtJQUNELFNBQVMsa0JBQWtCLENBQUMsS0FBSyxDQUFDO1FBQzlCLEtBQUssR0FBRyxJQUFJLE1BQU0sQ0FBQyxLQUFLLEVBQUUsR0FBRyxDQUFDLENBQUM7UUFDL0IsU0FBUyx3QkFBd0IsQ0FBQyxJQUFJLENBQUM7WUFDbkMsT0FBTyxJQUFJLENBQUMsT0FBTyxJQUFJLEtBQUssQ0FBQyxJQUFJLENBQUMsU0FBUyxDQUFDLFlBQVksQ0FBQyxjQUFjLENBQUMsSUFBSSxDQUFDLE9BQU8sQ0FBQyxDQUFDLENBQUM7U0FDMUY7UUFDRCx3QkFBd0IsQ0FBQyxJQUFJLEdBQUcsNEJBQTRCLEdBQUcsS0FBSyxDQUFDO1FBQ3JFLE9BQU8sd0JBQXdCLENBQUM7S0FDbkM7SUFDRCxTQUFTLG1CQUFtQixDQUFDLEtBQUssQ0FBQztRQUMvQixLQUFLLEdBQUcsSUFBSSxNQUFNLENBQUMsS0FBSyxFQUFFLEdBQUcsQ0FBQyxDQUFDO1FBQy9CLFNBQVMseUJBQXlCLENBQUMsSUFBSSxDQUFDO1lBQ3BDLE9BQU8sSUFBSSxDQUFDLFFBQVEsSUFBSSxLQUFLLENBQUMsSUFBSSxDQUFDLFNBQVMsQ0FBQyxhQUFhLENBQUMsY0FBYyxDQUFDLElBQUksQ0FBQyxRQUFRLENBQUMsQ0FBQyxDQUFDO1NBQzdGO1FBQ0QseUJBQXlCLENBQUMsSUFBSSxHQUFHLDZCQUE2QixHQUFHLEtBQUssQ0FBQztRQUN2RSxPQUFPLHlCQUF5QixDQUFDO0tBQ3BDO0lBQ0QsU0FBUyxHQUFHLENBQUMsS0FBSyxDQUFDO1FBQ2YsS0FBSyxHQUFHLElBQUksTUFBTSxDQUFDLEtBQUssRUFBRSxHQUFHLENBQUMsQ0FBQztRQUMvQixTQUFTLFNBQVMsQ0FBQyxJQUFJLENBQUM7WUFDcEIsT0FBTyxJQUFJLENBQUMsT0FBTyxJQUFJLEtBQUssQ0FBQyxJQUFJLENBQUMsU0FBUyxDQUFDLFlBQVksQ0FBQyxVQUFVLENBQUMsSUFBSSxDQUFDLE9BQU8sQ0FBQyxDQUFDLENBQUM7U0FDdEY7UUFDRCxTQUFTLENBQUMsSUFBSSxHQUFHLGNBQWMsR0FBRyxLQUFLLENBQUM7UUFDeEMsT0FBTyxTQUFTLENBQUM7QUFDekIsS0FBSztBQUNMOztBQUVBLElBQUksVUFBVSxHQUFHLHFCQUFxQixFQUFFLENBQUM7O0lBRXJDLElBQUksVUFBVSxLQUFLLFVBQVUsSUFBSSxXQUFXLEtBQUssS0FBSyxDQUFDLE1BQU0sRUFBRTtNQUM3RCxPQUFPLFVBQVUsQ0FBQztLQUNuQixNQUFNO01BQ0wsSUFBSSxVQUFVLEtBQUssVUFBVSxJQUFJLFdBQVcsR0FBRyxLQUFLLENBQUMsTUFBTSxFQUFFO1FBQzNELFFBQVEsQ0FBQyxFQUFFLElBQUksRUFBRSxLQUFLLEVBQUUsV0FBVyxFQUFFLGNBQWMsRUFBRSxDQUFDLENBQUM7QUFDL0QsT0FBTzs7TUFFRCxNQUFNLGtCQUFrQixDQUFDLElBQUksRUFBRSxtQkFBbUIsRUFBRSxjQUFjLENBQUMsQ0FBQztLQUNyRTtBQUNMLEdBQUc7O0VBRUQsT0FBTztJQUNMLFdBQVcsRUFBRSxXQUFXO0lBQ3hCLEtBQUssUUFBUSxLQUFLO0dBQ25CLENBQUM7Q0FDSCxHQUFHOzs7QUM3dURKLElBQUksQ0FBQyxHQUFHLE9BQU8sQ0FBQyxRQUFRLENBQUMsQ0FBQzs7QUFFMUIsSUFBSSxhQUFhLEdBQUc7SUFDaEIsY0FBYyxFQUFFLFVBQVUsT0FBTyxFQUFFO1FBQy9CLE9BQU8sSUFBSSxDQUFDLGdCQUFnQixDQUFDLE9BQU8sRUFBRSxpQkFBaUIsQ0FBQyxDQUFDO0tBQzVEO0FBQ0wsSUFBSSxnQkFBZ0IsRUFBRSxVQUFVLE9BQU8sRUFBRSxLQUFLLEVBQUU7O1FBRXhDLElBQUksQ0FBQyxPQUFPLENBQUMsY0FBYztZQUN2QixNQUFNLENBQUMsY0FBYyxDQUFDLE9BQU8sRUFBRSxnQkFBZ0IsRUFBRTtnQkFDN0MsS0FBSyxFQUFFLEVBQUU7Z0JBQ1QsWUFBWSxFQUFFLEtBQUs7Z0JBQ25CLFVBQVUsRUFBRSxLQUFLO2dCQUNqQixRQUFRLEVBQUUsS0FBSzthQUNsQixDQUFDLENBQUM7UUFDUCxJQUFJLEVBQUUsS0FBSyxJQUFJLE9BQU8sQ0FBQyxjQUFjLENBQUMsRUFBRTtZQUNwQyxJQUFJLE1BQU0sQ0FBQztZQUNYLEtBQUssSUFBSSxDQUFDLEdBQUcsQ0FBQyxFQUFFLENBQUMsR0FBRyxPQUFPLENBQUMsT0FBTyxDQUFDLE1BQU0sRUFBRSxDQUFDLEVBQUUsRUFBRTtnQkFDN0MsSUFBSSxDQUFDLENBQUMsT0FBTyxDQUFDLE9BQU8sQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsS0FBSyxDQUFDLEVBQUU7b0JBQ3RDLE1BQU0sR0FBRyxPQUFPLENBQUMsT0FBTyxDQUFDLENBQUMsQ0FBQyxDQUFDO29CQUM1QixNQUFNO2lCQUNUO2FBQ0o7WUFDRCxPQUFPLENBQUMsY0FBYyxDQUFDLEtBQUssQ0FBQyxHQUFHLE1BQU0sR0FBRyxNQUFNLENBQUMsQ0FBQyxDQUFDLEdBQUcsU0FBUyxDQUFDO1NBQ2xFO1FBQ0QsT0FBTyxPQUFPLENBQUMsY0FBYyxDQUFDLEtBQUssQ0FBQyxDQUFDO0tBQ3hDO0lBQ0QsWUFBWSxFQUFFLFVBQVUsT0FBTyxFQUFFLEtBQUssRUFBRTtRQUNwQyxJQUFJLE9BQU8sR0FBRyxPQUFPLENBQUMsT0FBTyxDQUFDO1FBQzlCLElBQUksQ0FBQyxHQUFHLE9BQU8sQ0FBQyxNQUFNLENBQUM7UUFDdkIsT0FBTyxDQUFDLEVBQUUsRUFBRTtZQUNSLElBQUksS0FBSyxDQUFDLElBQUksQ0FBQyxPQUFPLENBQUMsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEdBQUcsQ0FBQyxDQUFDLEVBQUU7Z0JBQ2xDLE9BQU8sT0FBTyxDQUFDLENBQUMsQ0FBQyxDQUFDO2FBQ3JCO1NBQ0o7UUFDRCxPQUFPLEtBQUssQ0FBQztLQUNoQjtBQUNMLENBQUMsQ0FBQzs7QUFFRixJQUFJLFlBQVksR0FBRztJQUNmLE1BQU0sRUFBRSxFQUFFO0lBQ1YsT0FBTyxFQUFFLEdBQUc7QUFDaEIsQ0FBQyxDQUFDOztBQUVGLElBQUksWUFBWSxHQUFHLENBQUMsQ0FBQyxNQUFNLENBQUMsYUFBYSxFQUFFO0FBQzNDLElBQUksV0FBVyxFQUFFLFVBQVUsT0FBTyxFQUFFOztRQUU1QixPQUFPLE9BQU8sQ0FBQyxJQUFJLENBQUM7S0FDdkI7SUFDRCxVQUFVLEVBQUUsVUFBVSxPQUFPLEVBQUU7UUFDM0IsSUFBSSxJQUFJLEdBQUcsRUFBRSxDQUFDO1FBQ2QsSUFBSSxZQUFZLENBQUMsT0FBTyxDQUFDLE1BQU0sQ0FBQyxLQUFLLE9BQU8sQ0FBQyxJQUFJLEVBQUU7WUFDL0MsSUFBSSxHQUFHLEdBQUcsR0FBRyxPQUFPLENBQUMsSUFBSSxDQUFDO1NBQzdCO1FBQ0QsT0FBTyxPQUFPLENBQUMsTUFBTSxHQUFHLEtBQUssR0FBRyxJQUFJLENBQUMsV0FBVyxDQUFDLE9BQU8sQ0FBQyxHQUFHLElBQUksR0FBRyxPQUFPLENBQUMsSUFBSSxDQUFDO0tBQ25GO0FBQ0wsQ0FBQyxDQUFDLENBQUM7O0FBRUgsSUFBSSxhQUFhLEdBQUcsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxhQUFhLEVBQUUsRUFBRSxDQUFDLENBQUM7QUFDaEQ7O0FBRUEsTUFBTSxDQUFDLE9BQU8sR0FBRztJQUNiLGFBQWEsRUFBRSxhQUFhO0FBQ2hDLElBQUksWUFBWSxFQUFFLFlBQVk7Ozs7O0FDL0Q5QjtBQUNBLElBQUksQ0FBQyxHQUFHLE9BQU8sQ0FBQyxRQUFRLENBQUMsQ0FBQztBQUMxQixJQUFJLENBQUMsR0FBRyxPQUFPLENBQUMsUUFBUSxDQUFDLENBQUM7QUFDMUIsSUFBSSxZQUFZLEdBQUcsT0FBTyxDQUFDLFFBQVEsQ0FBQyxDQUFDLFlBQVksQ0FBQzs7QUFFbEQsSUFBSSxLQUFLLEdBQUcsT0FBTyxDQUFDLGFBQWEsQ0FBQyxDQUFDO0FBQ25DLElBQUksT0FBTyxHQUFHLE9BQU8sQ0FBQyxlQUFlLENBQUMsQ0FBQztBQUN2QyxJQUFJLFVBQVUsR0FBRyxPQUFPLENBQUMsa0JBQWtCLENBQUMsQ0FBQztBQUM3Qzs7QUFFQSxTQUFTLFNBQVMsR0FBRztJQUNqQixZQUFZLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDO0lBQ3hCLElBQUksQ0FBQyxLQUFLLEVBQUUsQ0FBQztDQUNoQjtBQUNELENBQUMsQ0FBQyxNQUFNLENBQUMsU0FBUyxDQUFDLFNBQVMsRUFBRSxZQUFZLENBQUMsU0FBUyxFQUFFO0lBQ2xELEdBQUcsRUFBRSxVQUFVLElBQUksRUFBRTtRQUNqQixJQUFJLElBQUksQ0FBQyxFQUFFLElBQUksSUFBSSxDQUFDLFFBQVEsRUFBRTtZQUMxQixPQUFPO1NBQ1Y7UUFDRCxJQUFJLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsR0FBRyxJQUFJLENBQUMsSUFBSSxDQUFDLE1BQU0sQ0FBQztRQUMxQyxJQUFJLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQztRQUNyQixJQUFJLENBQUMsSUFBSSxDQUFDLEtBQUssRUFBRSxJQUFJLENBQUMsQ0FBQztLQUMxQjtJQUNELE1BQU0sRUFBRSxVQUFVLElBQUksRUFBRTtRQUNwQixJQUFJLEVBQUUsSUFBSSxDQUFDLEVBQUUsSUFBSSxJQUFJLENBQUMsUUFBUSxDQUFDLEVBQUU7WUFDN0IsT0FBTztTQUNWO1FBQ0QsSUFBSSxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQyxHQUFHLElBQUksQ0FBQztRQUN6QyxJQUFJLENBQUMsSUFBSSxDQUFDLFFBQVEsRUFBRSxJQUFJLENBQUMsQ0FBQztLQUM3QjtJQUNELE1BQU0sRUFBRSxVQUFVLE9BQU8sRUFBRTtRQUN2QixJQUFJLEVBQUUsT0FBTyxJQUFJLElBQUksQ0FBQyxRQUFRLENBQUMsRUFBRTtZQUM3QixPQUFPO1NBQ1Y7UUFDRCxJQUFJLENBQUMsSUFBSSxDQUFDLE1BQU0sQ0FBQyxJQUFJLENBQUMsUUFBUSxDQUFDLE9BQU8sQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDO1FBQzVDLElBQUksQ0FBQyxVQUFVLEVBQUUsQ0FBQztRQUNsQixJQUFJLENBQUMsSUFBSSxDQUFDLFFBQVEsRUFBRSxPQUFPLENBQUMsQ0FBQztLQUNoQztJQUNELEtBQUssRUFBRSxVQUFVLEtBQUssRUFBRTtRQUNwQixJQUFJLENBQUMsSUFBSSxHQUFHLEtBQUssSUFBSSxFQUFFLENBQUM7UUFDeEIsSUFBSSxDQUFDLFVBQVUsRUFBRSxDQUFDO1FBQ2xCLElBQUksQ0FBQyxJQUFJLENBQUMsYUFBYSxDQUFDLENBQUM7S0FDNUI7SUFDRCxVQUFVLEVBQUUsWUFBWTtRQUNwQixJQUFJLENBQUMsUUFBUSxHQUFHLEVBQUUsQ0FBQztRQUNuQixLQUFLLElBQUksQ0FBQyxHQUFHLENBQUMsRUFBRSxDQUFDLEdBQUcsSUFBSSxDQUFDLElBQUksQ0FBQyxNQUFNLEVBQUUsQ0FBQyxFQUFFLEVBQUU7WUFDdkMsSUFBSSxJQUFJLEdBQUcsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQztZQUN4QixJQUFJLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsR0FBRyxDQUFDLENBQUM7U0FDOUI7S0FDSjtJQUNELEdBQUcsRUFBRSxVQUFVLE9BQU8sRUFBRTtRQUNwQixPQUFPLElBQUksQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQyxDQUFDO0tBQzVDO0lBQ0QsS0FBSyxFQUFFLFVBQVUsT0FBTyxFQUFFO1FBQ3RCLE9BQU8sSUFBSSxDQUFDLFFBQVEsQ0FBQyxPQUFPLENBQUMsQ0FBQztLQUNqQztBQUNMLENBQUMsQ0FBQyxDQUFDO0FBQ0g7O0FBRUEsU0FBUyxTQUFTLEdBQUc7SUFDakIsWUFBWSxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQztJQUN4QixJQUFJLENBQUMsS0FBSyxFQUFFLENBQUM7Q0FDaEI7QUFDRCxDQUFDLENBQUMsTUFBTSxDQUFDLFNBQVMsQ0FBQyxTQUFTLEVBQUUsWUFBWSxDQUFDLFNBQVMsRUFBRTtJQUNsRCxNQUFNLEVBQUUsVUFBVSxJQUFJLEVBQUU7UUFDcEIsQ0FBQyxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsSUFBSSxFQUFFLElBQUksQ0FBQyxDQUFDO1FBQ3pCLElBQUksQ0FBQyxJQUFJLENBQUMsYUFBYSxDQUFDLENBQUM7S0FDNUI7SUFDRCxLQUFLLEVBQUUsVUFBVSxJQUFJLEVBQUU7UUFDbkIsSUFBSSxDQUFDLElBQUksR0FBRyxJQUFJLElBQUksRUFBRSxDQUFDO1FBQ3ZCLElBQUksQ0FBQyxJQUFJLENBQUMsYUFBYSxDQUFDLENBQUM7S0FDNUI7QUFDTCxDQUFDLENBQUMsQ0FBQzs7QUFFSCxTQUFTLGNBQWMsQ0FBQyxJQUFJLEVBQUU7QUFDOUIsSUFBSSxJQUFJLENBQUMsSUFBSSxHQUFHLElBQUksQ0FBQzs7SUFFakIsSUFBSSxDQUFDLHFCQUFxQixHQUFHLFNBQVMsQ0FBQztBQUMzQyxJQUFJLElBQUksQ0FBQyxTQUFTLEdBQUcsS0FBSyxDQUFDOztJQUV2QixJQUFJLENBQUMsTUFBTSxHQUFHLElBQUksQ0FBQyxNQUFNLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDO0FBQ3pDLElBQUksVUFBVSxDQUFDLGFBQWEsQ0FBQyxRQUFRLENBQUMsSUFBSSxDQUFDLE1BQU0sQ0FBQyxDQUFDO0FBQ25EOztJQUVJLElBQUksRUFBRSxNQUFNLENBQUMsRUFBRSxJQUFJLE1BQU0sQ0FBQyxFQUFFLENBQUMsVUFBVSxLQUFLLFNBQVMsQ0FBQyxVQUFVLENBQUMsRUFBRTtRQUMvRCxJQUFJLENBQUMsS0FBSyxFQUFFLENBQUM7S0FDaEI7Q0FDSjtBQUNELENBQUMsQ0FBQyxNQUFNLENBQUMsY0FBYyxDQUFDLFNBQVMsRUFBRTtJQUMvQixNQUFNLEVBQUUsVUFBVSxLQUFLLEVBQUU7UUFDckIsSUFBSSxLQUFLLENBQUMsSUFBSSxLQUFLLE9BQU8sQ0FBQyxXQUFXLENBQUMsZUFBZSxFQUFFO1lBQ3BELE9BQU8sSUFBSSxDQUFDLEtBQUssRUFBRSxDQUFDO1NBQ3ZCO1FBQ0QsSUFBSSxLQUFLLENBQUMsSUFBSSxLQUFLLElBQUksQ0FBQyxJQUFJLEVBQUU7WUFDMUIsSUFBSSxLQUFLLENBQUMsR0FBRyxLQUFLLE9BQU8sQ0FBQyxTQUFTLENBQUMsS0FBSyxFQUFFO2dCQUN2QyxJQUFJLENBQUMsS0FBSyxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsQ0FBQzthQUMxQixNQUFNLElBQUksSUFBSSxDQUFDLHFCQUFxQixFQUFFO2dCQUNuQyxPQUFPLENBQUMsR0FBRyxDQUFDLGNBQWMsRUFBRSxLQUFLLENBQUMsQ0FBQztnQkFDbkMsSUFBSSxDQUFDLHFCQUFxQixDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsQ0FBQzthQUMxQyxNQUFNO2dCQUNILElBQUksQ0FBQyxLQUFLLENBQUMsR0FBRyxDQUFDLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQyxDQUFDO2FBQy9CO1NBQ0o7S0FDSjtJQUNELEtBQUssRUFBRSxZQUFZO1FBQ2YsVUFBVSxDQUFDLGFBQWEsQ0FBQyxVQUFVLENBQUMsSUFBSSxDQUFDLE1BQU0sQ0FBQyxDQUFDO0tBQ3BEO0lBQ0QsS0FBSyxFQUFFLFVBQVUsSUFBSSxFQUFFO1FBQ25CLE9BQU8sQ0FBQyxHQUFHLENBQUMsUUFBUSxHQUFHLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQztRQUNsQyxJQUFJLElBQUksQ0FBQyxTQUFTLEVBQUU7WUFDaEIsSUFBSSxDQUFDLFNBQVMsQ0FBQyxLQUFLLEVBQUUsQ0FBQztTQUMxQjtRQUNELElBQUksQ0FBQyxxQkFBcUIsR0FBRyxFQUFFLENBQUM7UUFDaEMsSUFBSSxJQUFJLEVBQUU7WUFDTixJQUFJLENBQUMsWUFBWSxDQUFDLElBQUksQ0FBQyxDQUFDO1NBQzNCLE1BQU07WUFDSCxJQUFJLENBQUMsU0FBUyxHQUFHLENBQUMsQ0FBQyxPQUFPLENBQUMsR0FBRyxHQUFHLElBQUksQ0FBQyxJQUFJLENBQUM7aUJBQ3RDLElBQUksQ0FBQyxVQUFVLE9BQU8sRUFBRTtvQkFDckIsSUFBSSxDQUFDLFlBQVksQ0FBQyxPQUFPLENBQUMsSUFBSSxDQUFDLENBQUM7aUJBQ25DLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDO2lCQUNaLElBQUksQ0FBQyxZQUFZO29CQUNkLGVBQWUsQ0FBQyxTQUFTLENBQUMsa0JBQWtCLEdBQUcsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDO2lCQUM3RCxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDO1NBQ3JCO0tBQ0o7SUFDRCxZQUFZLEVBQUUsVUFBVSxJQUFJLEVBQUU7UUFDMUIsSUFBSSxDQUFDLFNBQVMsR0FBRyxLQUFLLENBQUM7UUFDdkIsT0FBTyxDQUFDLEdBQUcsQ0FBQyxJQUFJLENBQUMsSUFBSSxHQUFHLFdBQVcsRUFBRSxJQUFJLENBQUMscUJBQXFCLENBQUMsQ0FBQztRQUNqRSxJQUFJLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQyxDQUFDO1FBQ2pCLElBQUksT0FBTyxHQUFHLElBQUksQ0FBQyxxQkFBcUIsQ0FBQztRQUN6QyxJQUFJLENBQUMscUJBQXFCLEdBQUcsS0FBSyxDQUFDO1FBQ25DLEtBQUssSUFBSSxDQUFDLEdBQUcsQ0FBQyxFQUFFLENBQUMsR0FBRyxPQUFPLENBQUMsTUFBTSxFQUFFLENBQUMsRUFBRSxFQUFFO1lBQ3JDLElBQUksQ0FBQyxNQUFNLENBQUMsT0FBTyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUM7U0FDM0I7S0FDSjtBQUNMLENBQUMsQ0FBQyxDQUFDOztBQUVILFNBQVMsYUFBYSxDQUFDLElBQUksRUFBRTtJQUN6QixTQUFTLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDO0lBQ3JCLGNBQWMsQ0FBQyxJQUFJLENBQUMsSUFBSSxFQUFFLElBQUksQ0FBQyxDQUFDO0NBQ25DO0FBQ0QsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxhQUFhLENBQUMsU0FBUyxFQUFFLFNBQVMsQ0FBQyxTQUFTLEVBQUUsY0FBYyxDQUFDLFNBQVMsQ0FBQyxDQUFDOztBQUVqRixTQUFTLGFBQWEsQ0FBQyxJQUFJLEVBQUU7SUFDekIsU0FBUyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQztJQUNyQixjQUFjLENBQUMsSUFBSSxDQUFDLElBQUksRUFBRSxJQUFJLENBQUMsQ0FBQztDQUNuQztBQUNELENBQUMsQ0FBQyxNQUFNLENBQUMsYUFBYSxDQUFDLFNBQVMsRUFBRSxTQUFTLENBQUMsU0FBUyxFQUFFLGNBQWMsQ0FBQyxTQUFTLENBQUMsQ0FBQztBQUNqRjs7QUFFQSxTQUFTLFNBQVMsR0FBRztJQUNqQixPQUFPLElBQUksYUFBYSxDQUFDLE9BQU8sQ0FBQyxXQUFXLENBQUMsVUFBVSxDQUFDLENBQUM7QUFDN0QsQ0FBQzs7QUFFRCxTQUFTLGFBQWEsR0FBRztJQUNyQixPQUFPLElBQUksYUFBYSxDQUFDLE9BQU8sQ0FBQyxXQUFXLENBQUMsY0FBYyxDQUFDLENBQUM7QUFDakUsQ0FBQzs7QUFFRCxTQUFTLGFBQWEsR0FBRztJQUNyQixhQUFhLENBQUMsSUFBSSxDQUFDLElBQUksRUFBRSxPQUFPLENBQUMsV0FBVyxDQUFDLFdBQVcsQ0FBQyxDQUFDO0NBQzdEO0FBQ0QsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxhQUFhLENBQUMsU0FBUyxFQUFFLGFBQWEsQ0FBQyxTQUFTLEVBQUU7SUFDdkQsS0FBSyxFQUFFLFVBQVU7QUFDckIsUUFBUSxhQUFhLENBQUMsU0FBUyxDQUFDLEtBQUssQ0FBQyxLQUFLLENBQUMsSUFBSSxFQUFFLFNBQVMsQ0FBQyxDQUFDO0FBQzdEO0FBQ0E7O1FBRVEsR0FBRyxJQUFJLENBQUMsU0FBUyxDQUFDO1lBQ2QsSUFBSSxDQUFDLFNBQVMsQ0FBQyxJQUFJLENBQUMsVUFBVTtnQkFDMUIsSUFBSSxDQUFDLFlBQVksQ0FBQyxJQUFJLENBQUMsQ0FBQzthQUMzQixDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDO1NBQ2pCO0tBQ0o7QUFDTCxDQUFDLENBQUMsQ0FBQztBQUNIOztBQUVBLE1BQU0sQ0FBQyxPQUFPLEdBQUc7SUFDYixhQUFhLEVBQUUsYUFBYTtJQUM1QixhQUFhLEVBQUUsYUFBYTtJQUM1QixTQUFTLEVBQUUsU0FBUztDQUN2Qjs7O0FDcExEO0FBQ0EsSUFBSSxZQUFZLEdBQUcsT0FBTyxDQUFDLFFBQVEsQ0FBQyxDQUFDLFlBQVksQ0FBQztBQUNsRCxJQUFJLENBQUMsR0FBRyxPQUFPLENBQUMsUUFBUSxDQUFDLENBQUM7QUFDMUI7O0FBRUEsSUFBSSxLQUFLLEdBQUcsT0FBTyxDQUFDLGFBQWEsQ0FBQyxDQUFDOztBQUVuQyxTQUFTLGdCQUFnQixDQUFDLElBQUksRUFBRTtJQUM1QixPQUFPLElBQUksQ0FBQyxLQUFLLENBQUMsS0FBSyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQztBQUNyQyxDQUFDOztBQUVELElBQUksWUFBWSxHQUFHLGdCQUFnQixDQUFDO0FBQ3BDLElBQUksWUFBWSxHQUFHLFNBQVMsSUFBSSxDQUFDO0lBQzdCLE9BQU8sSUFBSSxDQUFDO0FBQ2hCLENBQUMsQ0FBQzs7QUFFRixTQUFTLFNBQVMsQ0FBQyxLQUFLLEVBQUUsSUFBSSxFQUFFLE9BQU8sRUFBRTtJQUNyQyxZQUFZLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDO0lBQ3hCLElBQUksR0FBRyxJQUFJLElBQUksWUFBWSxDQUFDO0FBQ2hDLElBQUksT0FBTyxHQUFHLE9BQU8sSUFBSSxZQUFZLENBQUM7O0FBRXRDLElBQUksSUFBSSxDQUFDLEtBQUssR0FBRyxLQUFLLENBQUM7O0lBRW5CLElBQUksQ0FBQyxHQUFHLEdBQUcsSUFBSSxDQUFDLEdBQUcsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUM7SUFDL0IsSUFBSSxDQUFDLE1BQU0sR0FBRyxJQUFJLENBQUMsTUFBTSxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQztJQUNyQyxJQUFJLENBQUMsTUFBTSxHQUFHLElBQUksQ0FBQyxNQUFNLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDO0lBQ3JDLElBQUksQ0FBQyxXQUFXLEdBQUcsSUFBSSxDQUFDLFdBQVcsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUM7SUFDL0MsSUFBSSxDQUFDLEtBQUssQ0FBQyxXQUFXLENBQUMsS0FBSyxFQUFFLElBQUksQ0FBQyxHQUFHLENBQUMsQ0FBQztJQUN4QyxJQUFJLENBQUMsS0FBSyxDQUFDLFdBQVcsQ0FBQyxRQUFRLEVBQUUsSUFBSSxDQUFDLE1BQU0sQ0FBQyxDQUFDO0lBQzlDLElBQUksQ0FBQyxLQUFLLENBQUMsV0FBVyxDQUFDLFFBQVEsRUFBRSxJQUFJLENBQUMsTUFBTSxDQUFDLENBQUM7QUFDbEQsSUFBSSxJQUFJLENBQUMsS0FBSyxDQUFDLFdBQVcsQ0FBQyxhQUFhLEVBQUUsSUFBSSxDQUFDLFdBQVcsQ0FBQyxDQUFDOztJQUV4RCxJQUFJLENBQUMsV0FBVyxDQUFDLElBQUksRUFBRSxPQUFPLENBQUMsQ0FBQztBQUNwQyxDQUFDOztBQUVELENBQUMsQ0FBQyxNQUFNLENBQUMsU0FBUyxDQUFDLFNBQVMsRUFBRSxZQUFZLENBQUMsU0FBUyxFQUFFO0lBQ2xELEtBQUssRUFBRSxZQUFZO1FBQ2YsSUFBSSxDQUFDLEtBQUssQ0FBQyxjQUFjLENBQUMsS0FBSyxFQUFFLElBQUksQ0FBQyxHQUFHLENBQUMsQ0FBQztRQUMzQyxJQUFJLENBQUMsS0FBSyxDQUFDLGNBQWMsQ0FBQyxRQUFRLEVBQUUsSUFBSSxDQUFDLE1BQU0sQ0FBQyxDQUFDO1FBQ2pELElBQUksQ0FBQyxLQUFLLENBQUMsY0FBYyxDQUFDLFFBQVEsRUFBRSxJQUFJLENBQUMsTUFBTSxDQUFDLENBQUM7UUFDakQsSUFBSSxDQUFDLEtBQUssQ0FBQyxjQUFjLENBQUMsYUFBYSxFQUFFLElBQUksQ0FBQyxXQUFXLENBQUMsQ0FBQztTQUMxRDtRQUNELFdBQVcsRUFBRSxVQUFVLElBQUksRUFBRSxPQUFPLEVBQUU7UUFDdEMsSUFBSSxJQUFJLEVBQUU7WUFDTixJQUFJLENBQUMsSUFBSSxHQUFHLElBQUksQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUM7U0FDL0I7UUFDRCxJQUFJLE9BQU8sRUFBRTtZQUNULElBQUksQ0FBQyxPQUFPLEdBQUcsT0FBTyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQztBQUM5QyxTQUFTOztRQUVELElBQUksQ0FBQyxJQUFJLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsTUFBTSxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQztRQUM5QyxJQUFJLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxVQUFVLENBQUMsRUFBRSxDQUFDLEVBQUU7WUFDM0IsT0FBTyxJQUFJLENBQUMsT0FBTyxDQUFDLENBQUMsQ0FBQyxHQUFHLElBQUksQ0FBQyxPQUFPLENBQUMsQ0FBQyxDQUFDLENBQUM7U0FDNUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQztRQUNkLElBQUksQ0FBQyxJQUFJLENBQUMsYUFBYSxDQUFDLENBQUM7S0FDNUI7SUFDRCxLQUFLLEVBQUUsVUFBVSxJQUFJLEVBQUU7UUFDbkIsT0FBTyxDQUFDLENBQUMsV0FBVyxDQUFDLElBQUksQ0FBQyxJQUFJLEVBQUUsSUFBSSxFQUFFLElBQUksQ0FBQyxPQUFPLENBQUMsQ0FBQztLQUN2RDtJQUNELEdBQUcsRUFBRSxVQUFVLElBQUksRUFBRTtRQUNqQixJQUFJLElBQUksQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLEVBQUU7WUFDakIsSUFBSSxHQUFHLEdBQUcsSUFBSSxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsQ0FBQztZQUMzQixJQUFJLEdBQUcsS0FBSyxJQUFJLENBQUMsSUFBSSxDQUFDLE1BQU0sRUFBRTtnQkFDMUIsSUFBSSxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUM7YUFDeEIsTUFBTTtnQkFDSCxJQUFJLENBQUMsSUFBSSxDQUFDLE1BQU0sQ0FBQyxHQUFHLEVBQUUsQ0FBQyxFQUFFLElBQUksQ0FBQyxDQUFDO2FBQ2xDO1lBQ0QsSUFBSSxDQUFDLElBQUksQ0FBQyxLQUFLLEVBQUUsSUFBSSxFQUFFLEdBQUcsQ0FBQyxDQUFDO1NBQy9CO0tBQ0o7SUFDRCxNQUFNLEVBQUUsVUFBVSxJQUFJLEVBQUU7UUFDcEIsSUFBSSxHQUFHLENBQUM7QUFDaEIsUUFBUSxJQUFJLENBQUMsR0FBRyxJQUFJLENBQUMsSUFBSSxDQUFDLE1BQU0sQ0FBQzs7UUFFekIsT0FBTyxDQUFDLEVBQUUsRUFBRTtZQUNSLElBQUksSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxFQUFFLEtBQUssSUFBSSxDQUFDLEVBQUUsRUFBRTtnQkFDN0IsR0FBRyxHQUFHLENBQUMsQ0FBQztnQkFDUixNQUFNO2FBQ1Q7QUFDYixTQUFTOztRQUVELElBQUksR0FBRyxLQUFLLENBQUMsQ0FBQyxFQUFFO1lBQ1osSUFBSSxDQUFDLEdBQUcsQ0FBQyxJQUFJLENBQUMsQ0FBQztTQUNsQixNQUFNLElBQUksQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxFQUFFO1lBQ3pCLElBQUksQ0FBQyxNQUFNLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDO1NBQ3hCLE1BQU07WUFDSCxJQUFJLElBQUksQ0FBQyxPQUFPLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxHQUFHLENBQUMsQ0FBQyxLQUFLLElBQUksQ0FBQyxPQUFPLENBQUMsSUFBSSxDQUFDLEVBQUU7Z0JBQ3JELElBQUksQ0FBQyxNQUFNLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDO2dCQUM1QixJQUFJLENBQUMsR0FBRyxDQUFDLElBQUksQ0FBQyxDQUFDO2FBQ2xCLE1BQU07Z0JBQ0gsSUFBSSxDQUFDLElBQUksQ0FBQyxHQUFHLENBQUMsR0FBRyxJQUFJLENBQUM7Z0JBQ3RCLElBQUksQ0FBQyxJQUFJLENBQUMsUUFBUSxFQUFFLElBQUksRUFBRSxHQUFHLENBQUMsQ0FBQzthQUNsQztTQUNKO0tBQ0o7SUFDRCxNQUFNLEVBQUUsVUFBVSxPQUFPLEVBQUU7UUFDdkIsSUFBSSxHQUFHLEdBQUcsSUFBSSxDQUFDLElBQUksQ0FBQyxNQUFNLENBQUM7UUFDM0IsT0FBTyxHQUFHLEVBQUUsRUFBRTtZQUNWLElBQUksSUFBSSxDQUFDLElBQUksQ0FBQyxHQUFHLENBQUMsQ0FBQyxFQUFFLEtBQUssT0FBTyxFQUFFO2dCQUMvQixJQUFJLENBQUMsSUFBSSxDQUFDLE1BQU0sQ0FBQyxHQUFHLEVBQUUsQ0FBQyxDQUFDLENBQUM7Z0JBQ3pCLElBQUksQ0FBQyxJQUFJLENBQUMsUUFBUSxFQUFFLE9BQU8sRUFBRSxHQUFHLENBQUMsQ0FBQztnQkFDbEMsTUFBTTthQUNUO1NBQ0o7S0FDSjtBQUNMLENBQUMsQ0FBQyxDQUFDOztBQUVILE1BQU0sQ0FBQyxPQUFPLEdBQUc7SUFDYixTQUFTLEVBQUUsU0FBUztDQUN2Qjs7O0FDN0dELElBQUksQ0FBQyxHQUFHLE9BQU8sQ0FBQyxRQUFRLENBQUMsQ0FBQztBQUMxQjs7QUFFQSxJQUFJLEdBQUcsR0FBRztJQUNOLEVBQUUsRUFBRSxFQUFFO0lBQ04sSUFBSSxFQUFFLEVBQUU7SUFDUixPQUFPLEVBQUUsRUFBRTtJQUNYLFNBQVMsRUFBRSxFQUFFO0lBQ2IsSUFBSSxFQUFFLEVBQUU7SUFDUixHQUFHLEVBQUUsRUFBRTtJQUNQLElBQUksRUFBRSxFQUFFO0lBQ1IsS0FBSyxFQUFFLEVBQUU7SUFDVCxLQUFLLEVBQUUsRUFBRTtJQUNULEdBQUcsRUFBRSxFQUFFO0lBQ1AsR0FBRyxFQUFFLENBQUM7SUFDTixLQUFLLEVBQUUsRUFBRTtJQUNULFNBQVMsRUFBRSxDQUFDO0NBQ2YsQ0FBQztBQUNGLFVBQVU7QUFDVixLQUFLLElBQUksQ0FBQyxHQUFHLEVBQUUsRUFBRSxDQUFDLElBQUksRUFBRSxFQUFFLENBQUMsRUFBRSxFQUFFO0lBQzNCLEdBQUcsQ0FBQyxNQUFNLENBQUMsWUFBWSxDQUFDLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDO0FBQ3BDLENBQUM7QUFDRDs7QUFFQSxJQUFJLFVBQVUsR0FBRyxVQUFVLEtBQUssRUFBRTtJQUM5QixJQUFJLEtBQUssS0FBSyxDQUFDO1FBQ1gsT0FBTyxHQUFHLENBQUM7SUFDZixJQUFJLE1BQU0sR0FBRyxDQUFDLEdBQUcsRUFBRSxJQUFJLEVBQUUsSUFBSSxFQUFFLElBQUksRUFBRSxJQUFJLENBQUMsQ0FBQztJQUMzQyxLQUFLLElBQUksQ0FBQyxHQUFHLENBQUMsRUFBRSxDQUFDLEdBQUcsTUFBTSxDQUFDLE1BQU0sRUFBRSxDQUFDLEVBQUUsQ0FBQztRQUNuQyxJQUFJLElBQUksQ0FBQyxHQUFHLENBQUMsSUFBSSxFQUFFLENBQUMsR0FBRyxDQUFDLENBQUMsR0FBRyxLQUFLLENBQUM7WUFDOUIsTUFBTTtTQUNUO0tBQ0o7SUFDRCxJQUFJLFNBQVMsQ0FBQztJQUNkLElBQUksS0FBSyxDQUFDLElBQUksQ0FBQyxHQUFHLENBQUMsSUFBSSxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUM7QUFDckMsUUFBUSxTQUFTLEdBQUcsQ0FBQyxDQUFDOztRQUVkLFNBQVMsR0FBRyxDQUFDLENBQUM7SUFDbEIsT0FBTyxDQUFDLEtBQUssQ0FBQyxJQUFJLENBQUMsR0FBRyxDQUFDLElBQUksRUFBRSxDQUFDLENBQUMsRUFBRSxPQUFPLENBQUMsU0FBUyxDQUFDLEdBQUcsTUFBTSxDQUFDLENBQUMsQ0FBQyxDQUFDO0FBQ3BFLENBQUMsQ0FBQztBQUNGOztBQUVBLElBQUksZUFBZSxHQUFHLFVBQVUsWUFBWSxFQUFFO0lBQzFDLElBQUksSUFBSSxHQUFHLFlBQVksQ0FBQztJQUN4QixJQUFJLE1BQU0sR0FBRyxDQUFDLElBQUksRUFBRSxHQUFHLEVBQUUsS0FBSyxFQUFFLEdBQUcsQ0FBQyxDQUFDO0lBQ3JDLElBQUksR0FBRyxHQUFHLENBQUMsSUFBSSxFQUFFLEVBQUUsRUFBRSxFQUFFLENBQUMsQ0FBQztJQUN6QixJQUFJLENBQUMsR0FBRyxDQUFDLENBQUM7SUFDVixPQUFPLElBQUksQ0FBQyxHQUFHLENBQUMsSUFBSSxDQUFDLElBQUksR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsR0FBRyxHQUFHLENBQUMsTUFBTSxFQUFFO1FBQy9DLElBQUksR0FBRyxJQUFJLEdBQUcsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDO1FBQ3JCLENBQUMsRUFBRSxDQUFDO0tBQ1A7SUFDRCxPQUFPLElBQUksQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLEdBQUcsTUFBTSxDQUFDLENBQUMsQ0FBQyxDQUFDO0FBQ3hDLENBQUMsQ0FBQztBQUNGOztBQUVBLElBQUksZUFBZSxHQUFHLFVBQVUsT0FBTyxFQUFFO0lBQ3JDLElBQUksRUFBRSxHQUFHLENBQUMsSUFBSSxJQUFJLENBQUMsT0FBTyxHQUFHLElBQUksQ0FBQyxFQUFFLFdBQVcsRUFBRSxDQUFDO0lBQ2xELE9BQU8sRUFBRSxDQUFDLE9BQU8sQ0FBQyxHQUFHLEVBQUUsR0FBRyxDQUFDLENBQUMsT0FBTyxDQUFDLEdBQUcsRUFBRSxFQUFFLENBQUMsQ0FBQztBQUNqRCxDQUFDLENBQUM7QUFDRjs7QUFFQSxTQUFTLFNBQVMsQ0FBQyxJQUFJLEVBQUU7SUFDckIsSUFBSSxDQUFDLEdBQUcsUUFBUSxDQUFDLE1BQU0sQ0FBQyxLQUFLLENBQUMsS0FBSyxHQUFHLElBQUksR0FBRyxhQUFhLENBQUMsQ0FBQztJQUM1RCxPQUFPLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEdBQUcsU0FBUyxDQUFDO0NBQy9CO0FBQ0QsSUFBSSxJQUFJLEdBQUcsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLEtBQUssRUFBRSxTQUFTLENBQUMsT0FBTyxDQUFDLENBQUMsQ0FBQyxDQUFDOztBQUVoRCwwQkFBMEI7QUFDMUIsQ0FBQyxDQUFDLGFBQWEsQ0FBQyxVQUFVLE9BQU8sRUFBRTtJQUMvQixJQUFJLENBQUMsTUFBTSxFQUFFLEtBQUssRUFBRSxRQUFRLENBQUMsQ0FBQyxPQUFPLENBQUMsT0FBTyxDQUFDLElBQUksQ0FBQyxXQUFXLEVBQUUsQ0FBQyxJQUFJLENBQUMsSUFBSSxPQUFPLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxLQUFLLEdBQUcsRUFBRTtRQUM5RixJQUFJLE9BQU8sQ0FBQyxJQUFJLEVBQUU7WUFDZCxPQUFPLENBQUMsSUFBSSxLQUFLLEdBQUcsR0FBRyxJQUFJLENBQUMsQ0FBQztTQUNoQyxNQUFNO1lBQ0gsT0FBTyxDQUFDLElBQUksR0FBRyxJQUFJLENBQUM7U0FDdkI7S0FDSjtDQUNKLENBQUMsQ0FBQztBQUNILGtCQUFrQjtBQUNsQixDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsU0FBUyxDQUFDLFVBQVUsS0FBSyxFQUFFLEtBQUssRUFBRSxZQUFZLEVBQUUsV0FBVyxFQUFFO0lBQ3JFLElBQUksT0FBTyxHQUFHLEtBQUssQ0FBQyxZQUFZLENBQUM7SUFDakMsT0FBTyxDQUFDLEtBQUssQ0FBQyxPQUFPLEVBQUUsU0FBUyxDQUFDLENBQUM7SUFDbEMsZUFBZSxDQUFDLFNBQVMsQ0FBQyxXQUFXLEdBQUcsSUFBSSxHQUFHLE9BQU8sQ0FBQyxDQUFDO0lBQ3hELE1BQU0sQ0FBQyxLQUFLLENBQUMsT0FBTyxDQUFDLENBQUM7QUFDMUIsQ0FBQyxDQUFDLENBQUM7O0FBRUgsTUFBTSxDQUFDLE9BQU8sR0FBRztJQUNiLFVBQVUsRUFBRSxVQUFVO0lBQ3RCLGVBQWUsRUFBRSxlQUFlO0lBQ2hDLGVBQWUsRUFBRSxlQUFlO0lBQ2hDLEdBQUcsRUFBRSxHQUFHO0NBQ1giLCJmaWxlIjoiZ2VuZXJhdGVkLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXNDb250ZW50IjpbIihmdW5jdGlvbiBlKHQsbixyKXtmdW5jdGlvbiBzKG8sdSl7aWYoIW5bb10pe2lmKCF0W29dKXt2YXIgYT10eXBlb2YgcmVxdWlyZT09XCJmdW5jdGlvblwiJiZyZXF1aXJlO2lmKCF1JiZhKXJldHVybiBhKG8sITApO2lmKGkpcmV0dXJuIGkobywhMCk7dmFyIGY9bmV3IEVycm9yKFwiQ2Fubm90IGZpbmQgbW9kdWxlICdcIitvK1wiJ1wiKTt0aHJvdyBmLmNvZGU9XCJNT0RVTEVfTk9UX0ZPVU5EXCIsZn12YXIgbD1uW29dPXtleHBvcnRzOnt9fTt0W29dWzBdLmNhbGwobC5leHBvcnRzLGZ1bmN0aW9uKGUpe3ZhciBuPXRbb11bMV1bZV07cmV0dXJuIHMobj9uOmUpfSxsLGwuZXhwb3J0cyxlLHQsbixyKX1yZXR1cm4gbltvXS5leHBvcnRzfXZhciBpPXR5cGVvZiByZXF1aXJlPT1cImZ1bmN0aW9uXCImJnJlcXVpcmU7Zm9yKHZhciBvPTA7bzxyLmxlbmd0aDtvKyspcyhyW29dKTtyZXR1cm4gc30pIiwiLy8gQ29weXJpZ2h0IEpveWVudCwgSW5jLiBhbmQgb3RoZXIgTm9kZSBjb250cmlidXRvcnMuXG4vL1xuLy8gUGVybWlzc2lvbiBpcyBoZXJlYnkgZ3JhbnRlZCwgZnJlZSBvZiBjaGFyZ2UsIHRvIGFueSBwZXJzb24gb2J0YWluaW5nIGFcbi8vIGNvcHkgb2YgdGhpcyBzb2Z0d2FyZSBhbmQgYXNzb2NpYXRlZCBkb2N1bWVudGF0aW9uIGZpbGVzICh0aGVcbi8vIFwiU29mdHdhcmVcIiksIHRvIGRlYWwgaW4gdGhlIFNvZnR3YXJlIHdpdGhvdXQgcmVzdHJpY3Rpb24sIGluY2x1ZGluZ1xuLy8gd2l0aG91dCBsaW1pdGF0aW9uIHRoZSByaWdodHMgdG8gdXNlLCBjb3B5LCBtb2RpZnksIG1lcmdlLCBwdWJsaXNoLFxuLy8gZGlzdHJpYnV0ZSwgc3VibGljZW5zZSwgYW5kL29yIHNlbGwgY29waWVzIG9mIHRoZSBTb2Z0d2FyZSwgYW5kIHRvIHBlcm1pdFxuLy8gcGVyc29ucyB0byB3aG9tIHRoZSBTb2Z0d2FyZSBpcyBmdXJuaXNoZWQgdG8gZG8gc28sIHN1YmplY3QgdG8gdGhlXG4vLyBmb2xsb3dpbmcgY29uZGl0aW9uczpcbi8vXG4vLyBUaGUgYWJvdmUgY29weXJpZ2h0IG5vdGljZSBhbmQgdGhpcyBwZXJtaXNzaW9uIG5vdGljZSBzaGFsbCBiZSBpbmNsdWRlZFxuLy8gaW4gYWxsIGNvcGllcyBvciBzdWJzdGFudGlhbCBwb3J0aW9ucyBvZiB0aGUgU29mdHdhcmUuXG4vL1xuLy8gVEhFIFNPRlRXQVJFIElTIFBST1ZJREVEIFwiQVMgSVNcIiwgV0lUSE9VVCBXQVJSQU5UWSBPRiBBTlkgS0lORCwgRVhQUkVTU1xuLy8gT1IgSU1QTElFRCwgSU5DTFVESU5HIEJVVCBOT1QgTElNSVRFRCBUTyBUSEUgV0FSUkFOVElFUyBPRlxuLy8gTUVSQ0hBTlRBQklMSVRZLCBGSVRORVNTIEZPUiBBIFBBUlRJQ1VMQVIgUFVSUE9TRSBBTkQgTk9OSU5GUklOR0VNRU5ULiBJTlxuLy8gTk8gRVZFTlQgU0hBTEwgVEhFIEFVVEhPUlMgT1IgQ09QWVJJR0hUIEhPTERFUlMgQkUgTElBQkxFIEZPUiBBTlkgQ0xBSU0sXG4vLyBEQU1BR0VTIE9SIE9USEVSIExJQUJJTElUWSwgV0hFVEhFUiBJTiBBTiBBQ1RJT04gT0YgQ09OVFJBQ1QsIFRPUlQgT1Jcbi8vIE9USEVSV0lTRSwgQVJJU0lORyBGUk9NLCBPVVQgT0YgT1IgSU4gQ09OTkVDVElPTiBXSVRIIFRIRSBTT0ZUV0FSRSBPUiBUSEVcbi8vIFVTRSBPUiBPVEhFUiBERUFMSU5HUyBJTiBUSEUgU09GVFdBUkUuXG5cbmZ1bmN0aW9uIEV2ZW50RW1pdHRlcigpIHtcbiAgdGhpcy5fZXZlbnRzID0gdGhpcy5fZXZlbnRzIHx8IHt9O1xuICB0aGlzLl9tYXhMaXN0ZW5lcnMgPSB0aGlzLl9tYXhMaXN0ZW5lcnMgfHwgdW5kZWZpbmVkO1xufVxubW9kdWxlLmV4cG9ydHMgPSBFdmVudEVtaXR0ZXI7XG5cbi8vIEJhY2t3YXJkcy1jb21wYXQgd2l0aCBub2RlIDAuMTAueFxuRXZlbnRFbWl0dGVyLkV2ZW50RW1pdHRlciA9IEV2ZW50RW1pdHRlcjtcblxuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5fZXZlbnRzID0gdW5kZWZpbmVkO1xuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5fbWF4TGlzdGVuZXJzID0gdW5kZWZpbmVkO1xuXG4vLyBCeSBkZWZhdWx0IEV2ZW50RW1pdHRlcnMgd2lsbCBwcmludCBhIHdhcm5pbmcgaWYgbW9yZSB0aGFuIDEwIGxpc3RlbmVycyBhcmVcbi8vIGFkZGVkIHRvIGl0LiBUaGlzIGlzIGEgdXNlZnVsIGRlZmF1bHQgd2hpY2ggaGVscHMgZmluZGluZyBtZW1vcnkgbGVha3MuXG5FdmVudEVtaXR0ZXIuZGVmYXVsdE1heExpc3RlbmVycyA9IDEwO1xuXG4vLyBPYnZpb3VzbHkgbm90IGFsbCBFbWl0dGVycyBzaG91bGQgYmUgbGltaXRlZCB0byAxMC4gVGhpcyBmdW5jdGlvbiBhbGxvd3Ncbi8vIHRoYXQgdG8gYmUgaW5jcmVhc2VkLiBTZXQgdG8gemVybyBmb3IgdW5saW1pdGVkLlxuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5zZXRNYXhMaXN0ZW5lcnMgPSBmdW5jdGlvbihuKSB7XG4gIGlmICghaXNOdW1iZXIobikgfHwgbiA8IDAgfHwgaXNOYU4obikpXG4gICAgdGhyb3cgVHlwZUVycm9yKCduIG11c3QgYmUgYSBwb3NpdGl2ZSBudW1iZXInKTtcbiAgdGhpcy5fbWF4TGlzdGVuZXJzID0gbjtcbiAgcmV0dXJuIHRoaXM7XG59O1xuXG5FdmVudEVtaXR0ZXIucHJvdG90eXBlLmVtaXQgPSBmdW5jdGlvbih0eXBlKSB7XG4gIHZhciBlciwgaGFuZGxlciwgbGVuLCBhcmdzLCBpLCBsaXN0ZW5lcnM7XG5cbiAgaWYgKCF0aGlzLl9ldmVudHMpXG4gICAgdGhpcy5fZXZlbnRzID0ge307XG5cbiAgLy8gSWYgdGhlcmUgaXMgbm8gJ2Vycm9yJyBldmVudCBsaXN0ZW5lciB0aGVuIHRocm93LlxuICBpZiAodHlwZSA9PT0gJ2Vycm9yJykge1xuICAgIGlmICghdGhpcy5fZXZlbnRzLmVycm9yIHx8XG4gICAgICAgIChpc09iamVjdCh0aGlzLl9ldmVudHMuZXJyb3IpICYmICF0aGlzLl9ldmVudHMuZXJyb3IubGVuZ3RoKSkge1xuICAgICAgZXIgPSBhcmd1bWVudHNbMV07XG4gICAgICBpZiAoZXIgaW5zdGFuY2VvZiBFcnJvcikge1xuICAgICAgICB0aHJvdyBlcjsgLy8gVW5oYW5kbGVkICdlcnJvcicgZXZlbnRcbiAgICAgIH1cbiAgICAgIHRocm93IFR5cGVFcnJvcignVW5jYXVnaHQsIHVuc3BlY2lmaWVkIFwiZXJyb3JcIiBldmVudC4nKTtcbiAgICB9XG4gIH1cblxuICBoYW5kbGVyID0gdGhpcy5fZXZlbnRzW3R5cGVdO1xuXG4gIGlmIChpc1VuZGVmaW5lZChoYW5kbGVyKSlcbiAgICByZXR1cm4gZmFsc2U7XG5cbiAgaWYgKGlzRnVuY3Rpb24oaGFuZGxlcikpIHtcbiAgICBzd2l0Y2ggKGFyZ3VtZW50cy5sZW5ndGgpIHtcbiAgICAgIC8vIGZhc3QgY2FzZXNcbiAgICAgIGNhc2UgMTpcbiAgICAgICAgaGFuZGxlci5jYWxsKHRoaXMpO1xuICAgICAgICBicmVhaztcbiAgICAgIGNhc2UgMjpcbiAgICAgICAgaGFuZGxlci5jYWxsKHRoaXMsIGFyZ3VtZW50c1sxXSk7XG4gICAgICAgIGJyZWFrO1xuICAgICAgY2FzZSAzOlxuICAgICAgICBoYW5kbGVyLmNhbGwodGhpcywgYXJndW1lbnRzWzFdLCBhcmd1bWVudHNbMl0pO1xuICAgICAgICBicmVhaztcbiAgICAgIC8vIHNsb3dlclxuICAgICAgZGVmYXVsdDpcbiAgICAgICAgbGVuID0gYXJndW1lbnRzLmxlbmd0aDtcbiAgICAgICAgYXJncyA9IG5ldyBBcnJheShsZW4gLSAxKTtcbiAgICAgICAgZm9yIChpID0gMTsgaSA8IGxlbjsgaSsrKVxuICAgICAgICAgIGFyZ3NbaSAtIDFdID0gYXJndW1lbnRzW2ldO1xuICAgICAgICBoYW5kbGVyLmFwcGx5KHRoaXMsIGFyZ3MpO1xuICAgIH1cbiAgfSBlbHNlIGlmIChpc09iamVjdChoYW5kbGVyKSkge1xuICAgIGxlbiA9IGFyZ3VtZW50cy5sZW5ndGg7XG4gICAgYXJncyA9IG5ldyBBcnJheShsZW4gLSAxKTtcbiAgICBmb3IgKGkgPSAxOyBpIDwgbGVuOyBpKyspXG4gICAgICBhcmdzW2kgLSAxXSA9IGFyZ3VtZW50c1tpXTtcblxuICAgIGxpc3RlbmVycyA9IGhhbmRsZXIuc2xpY2UoKTtcbiAgICBsZW4gPSBsaXN0ZW5lcnMubGVuZ3RoO1xuICAgIGZvciAoaSA9IDA7IGkgPCBsZW47IGkrKylcbiAgICAgIGxpc3RlbmVyc1tpXS5hcHBseSh0aGlzLCBhcmdzKTtcbiAgfVxuXG4gIHJldHVybiB0cnVlO1xufTtcblxuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5hZGRMaXN0ZW5lciA9IGZ1bmN0aW9uKHR5cGUsIGxpc3RlbmVyKSB7XG4gIHZhciBtO1xuXG4gIGlmICghaXNGdW5jdGlvbihsaXN0ZW5lcikpXG4gICAgdGhyb3cgVHlwZUVycm9yKCdsaXN0ZW5lciBtdXN0IGJlIGEgZnVuY3Rpb24nKTtcblxuICBpZiAoIXRoaXMuX2V2ZW50cylcbiAgICB0aGlzLl9ldmVudHMgPSB7fTtcblxuICAvLyBUbyBhdm9pZCByZWN1cnNpb24gaW4gdGhlIGNhc2UgdGhhdCB0eXBlID09PSBcIm5ld0xpc3RlbmVyXCIhIEJlZm9yZVxuICAvLyBhZGRpbmcgaXQgdG8gdGhlIGxpc3RlbmVycywgZmlyc3QgZW1pdCBcIm5ld0xpc3RlbmVyXCIuXG4gIGlmICh0aGlzLl9ldmVudHMubmV3TGlzdGVuZXIpXG4gICAgdGhpcy5lbWl0KCduZXdMaXN0ZW5lcicsIHR5cGUsXG4gICAgICAgICAgICAgIGlzRnVuY3Rpb24obGlzdGVuZXIubGlzdGVuZXIpID9cbiAgICAgICAgICAgICAgbGlzdGVuZXIubGlzdGVuZXIgOiBsaXN0ZW5lcik7XG5cbiAgaWYgKCF0aGlzLl9ldmVudHNbdHlwZV0pXG4gICAgLy8gT3B0aW1pemUgdGhlIGNhc2Ugb2Ygb25lIGxpc3RlbmVyLiBEb24ndCBuZWVkIHRoZSBleHRyYSBhcnJheSBvYmplY3QuXG4gICAgdGhpcy5fZXZlbnRzW3R5cGVdID0gbGlzdGVuZXI7XG4gIGVsc2UgaWYgKGlzT2JqZWN0KHRoaXMuX2V2ZW50c1t0eXBlXSkpXG4gICAgLy8gSWYgd2UndmUgYWxyZWFkeSBnb3QgYW4gYXJyYXksIGp1c3QgYXBwZW5kLlxuICAgIHRoaXMuX2V2ZW50c1t0eXBlXS5wdXNoKGxpc3RlbmVyKTtcbiAgZWxzZVxuICAgIC8vIEFkZGluZyB0aGUgc2Vjb25kIGVsZW1lbnQsIG5lZWQgdG8gY2hhbmdlIHRvIGFycmF5LlxuICAgIHRoaXMuX2V2ZW50c1t0eXBlXSA9IFt0aGlzLl9ldmVudHNbdHlwZV0sIGxpc3RlbmVyXTtcblxuICAvLyBDaGVjayBmb3IgbGlzdGVuZXIgbGVha1xuICBpZiAoaXNPYmplY3QodGhpcy5fZXZlbnRzW3R5cGVdKSAmJiAhdGhpcy5fZXZlbnRzW3R5cGVdLndhcm5lZCkge1xuICAgIHZhciBtO1xuICAgIGlmICghaXNVbmRlZmluZWQodGhpcy5fbWF4TGlzdGVuZXJzKSkge1xuICAgICAgbSA9IHRoaXMuX21heExpc3RlbmVycztcbiAgICB9IGVsc2Uge1xuICAgICAgbSA9IEV2ZW50RW1pdHRlci5kZWZhdWx0TWF4TGlzdGVuZXJzO1xuICAgIH1cblxuICAgIGlmIChtICYmIG0gPiAwICYmIHRoaXMuX2V2ZW50c1t0eXBlXS5sZW5ndGggPiBtKSB7XG4gICAgICB0aGlzLl9ldmVudHNbdHlwZV0ud2FybmVkID0gdHJ1ZTtcbiAgICAgIGNvbnNvbGUuZXJyb3IoJyhub2RlKSB3YXJuaW5nOiBwb3NzaWJsZSBFdmVudEVtaXR0ZXIgbWVtb3J5ICcgK1xuICAgICAgICAgICAgICAgICAgICAnbGVhayBkZXRlY3RlZC4gJWQgbGlzdGVuZXJzIGFkZGVkLiAnICtcbiAgICAgICAgICAgICAgICAgICAgJ1VzZSBlbWl0dGVyLnNldE1heExpc3RlbmVycygpIHRvIGluY3JlYXNlIGxpbWl0LicsXG4gICAgICAgICAgICAgICAgICAgIHRoaXMuX2V2ZW50c1t0eXBlXS5sZW5ndGgpO1xuICAgICAgaWYgKHR5cGVvZiBjb25zb2xlLnRyYWNlID09PSAnZnVuY3Rpb24nKSB7XG4gICAgICAgIC8vIG5vdCBzdXBwb3J0ZWQgaW4gSUUgMTBcbiAgICAgICAgY29uc29sZS50cmFjZSgpO1xuICAgICAgfVxuICAgIH1cbiAgfVxuXG4gIHJldHVybiB0aGlzO1xufTtcblxuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5vbiA9IEV2ZW50RW1pdHRlci5wcm90b3R5cGUuYWRkTGlzdGVuZXI7XG5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUub25jZSA9IGZ1bmN0aW9uKHR5cGUsIGxpc3RlbmVyKSB7XG4gIGlmICghaXNGdW5jdGlvbihsaXN0ZW5lcikpXG4gICAgdGhyb3cgVHlwZUVycm9yKCdsaXN0ZW5lciBtdXN0IGJlIGEgZnVuY3Rpb24nKTtcblxuICB2YXIgZmlyZWQgPSBmYWxzZTtcblxuICBmdW5jdGlvbiBnKCkge1xuICAgIHRoaXMucmVtb3ZlTGlzdGVuZXIodHlwZSwgZyk7XG5cbiAgICBpZiAoIWZpcmVkKSB7XG4gICAgICBmaXJlZCA9IHRydWU7XG4gICAgICBsaXN0ZW5lci5hcHBseSh0aGlzLCBhcmd1bWVudHMpO1xuICAgIH1cbiAgfVxuXG4gIGcubGlzdGVuZXIgPSBsaXN0ZW5lcjtcbiAgdGhpcy5vbih0eXBlLCBnKTtcblxuICByZXR1cm4gdGhpcztcbn07XG5cbi8vIGVtaXRzIGEgJ3JlbW92ZUxpc3RlbmVyJyBldmVudCBpZmYgdGhlIGxpc3RlbmVyIHdhcyByZW1vdmVkXG5FdmVudEVtaXR0ZXIucHJvdG90eXBlLnJlbW92ZUxpc3RlbmVyID0gZnVuY3Rpb24odHlwZSwgbGlzdGVuZXIpIHtcbiAgdmFyIGxpc3QsIHBvc2l0aW9uLCBsZW5ndGgsIGk7XG5cbiAgaWYgKCFpc0Z1bmN0aW9uKGxpc3RlbmVyKSlcbiAgICB0aHJvdyBUeXBlRXJyb3IoJ2xpc3RlbmVyIG11c3QgYmUgYSBmdW5jdGlvbicpO1xuXG4gIGlmICghdGhpcy5fZXZlbnRzIHx8ICF0aGlzLl9ldmVudHNbdHlwZV0pXG4gICAgcmV0dXJuIHRoaXM7XG5cbiAgbGlzdCA9IHRoaXMuX2V2ZW50c1t0eXBlXTtcbiAgbGVuZ3RoID0gbGlzdC5sZW5ndGg7XG4gIHBvc2l0aW9uID0gLTE7XG5cbiAgaWYgKGxpc3QgPT09IGxpc3RlbmVyIHx8XG4gICAgICAoaXNGdW5jdGlvbihsaXN0Lmxpc3RlbmVyKSAmJiBsaXN0Lmxpc3RlbmVyID09PSBsaXN0ZW5lcikpIHtcbiAgICBkZWxldGUgdGhpcy5fZXZlbnRzW3R5cGVdO1xuICAgIGlmICh0aGlzLl9ldmVudHMucmVtb3ZlTGlzdGVuZXIpXG4gICAgICB0aGlzLmVtaXQoJ3JlbW92ZUxpc3RlbmVyJywgdHlwZSwgbGlzdGVuZXIpO1xuXG4gIH0gZWxzZSBpZiAoaXNPYmplY3QobGlzdCkpIHtcbiAgICBmb3IgKGkgPSBsZW5ndGg7IGktLSA+IDA7KSB7XG4gICAgICBpZiAobGlzdFtpXSA9PT0gbGlzdGVuZXIgfHxcbiAgICAgICAgICAobGlzdFtpXS5saXN0ZW5lciAmJiBsaXN0W2ldLmxpc3RlbmVyID09PSBsaXN0ZW5lcikpIHtcbiAgICAgICAgcG9zaXRpb24gPSBpO1xuICAgICAgICBicmVhaztcbiAgICAgIH1cbiAgICB9XG5cbiAgICBpZiAocG9zaXRpb24gPCAwKVxuICAgICAgcmV0dXJuIHRoaXM7XG5cbiAgICBpZiAobGlzdC5sZW5ndGggPT09IDEpIHtcbiAgICAgIGxpc3QubGVuZ3RoID0gMDtcbiAgICAgIGRlbGV0ZSB0aGlzLl9ldmVudHNbdHlwZV07XG4gICAgfSBlbHNlIHtcbiAgICAgIGxpc3Quc3BsaWNlKHBvc2l0aW9uLCAxKTtcbiAgICB9XG5cbiAgICBpZiAodGhpcy5fZXZlbnRzLnJlbW92ZUxpc3RlbmVyKVxuICAgICAgdGhpcy5lbWl0KCdyZW1vdmVMaXN0ZW5lcicsIHR5cGUsIGxpc3RlbmVyKTtcbiAgfVxuXG4gIHJldHVybiB0aGlzO1xufTtcblxuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5yZW1vdmVBbGxMaXN0ZW5lcnMgPSBmdW5jdGlvbih0eXBlKSB7XG4gIHZhciBrZXksIGxpc3RlbmVycztcblxuICBpZiAoIXRoaXMuX2V2ZW50cylcbiAgICByZXR1cm4gdGhpcztcblxuICAvLyBub3QgbGlzdGVuaW5nIGZvciByZW1vdmVMaXN0ZW5lciwgbm8gbmVlZCB0byBlbWl0XG4gIGlmICghdGhpcy5fZXZlbnRzLnJlbW92ZUxpc3RlbmVyKSB7XG4gICAgaWYgKGFyZ3VtZW50cy5sZW5ndGggPT09IDApXG4gICAgICB0aGlzLl9ldmVudHMgPSB7fTtcbiAgICBlbHNlIGlmICh0aGlzLl9ldmVudHNbdHlwZV0pXG4gICAgICBkZWxldGUgdGhpcy5fZXZlbnRzW3R5cGVdO1xuICAgIHJldHVybiB0aGlzO1xuICB9XG5cbiAgLy8gZW1pdCByZW1vdmVMaXN0ZW5lciBmb3IgYWxsIGxpc3RlbmVycyBvbiBhbGwgZXZlbnRzXG4gIGlmIChhcmd1bWVudHMubGVuZ3RoID09PSAwKSB7XG4gICAgZm9yIChrZXkgaW4gdGhpcy5fZXZlbnRzKSB7XG4gICAgICBpZiAoa2V5ID09PSAncmVtb3ZlTGlzdGVuZXInKSBjb250aW51ZTtcbiAgICAgIHRoaXMucmVtb3ZlQWxsTGlzdGVuZXJzKGtleSk7XG4gICAgfVxuICAgIHRoaXMucmVtb3ZlQWxsTGlzdGVuZXJzKCdyZW1vdmVMaXN0ZW5lcicpO1xuICAgIHRoaXMuX2V2ZW50cyA9IHt9O1xuICAgIHJldHVybiB0aGlzO1xuICB9XG5cbiAgbGlzdGVuZXJzID0gdGhpcy5fZXZlbnRzW3R5cGVdO1xuXG4gIGlmIChpc0Z1bmN0aW9uKGxpc3RlbmVycykpIHtcbiAgICB0aGlzLnJlbW92ZUxpc3RlbmVyKHR5cGUsIGxpc3RlbmVycyk7XG4gIH0gZWxzZSB7XG4gICAgLy8gTElGTyBvcmRlclxuICAgIHdoaWxlIChsaXN0ZW5lcnMubGVuZ3RoKVxuICAgICAgdGhpcy5yZW1vdmVMaXN0ZW5lcih0eXBlLCBsaXN0ZW5lcnNbbGlzdGVuZXJzLmxlbmd0aCAtIDFdKTtcbiAgfVxuICBkZWxldGUgdGhpcy5fZXZlbnRzW3R5cGVdO1xuXG4gIHJldHVybiB0aGlzO1xufTtcblxuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5saXN0ZW5lcnMgPSBmdW5jdGlvbih0eXBlKSB7XG4gIHZhciByZXQ7XG4gIGlmICghdGhpcy5fZXZlbnRzIHx8ICF0aGlzLl9ldmVudHNbdHlwZV0pXG4gICAgcmV0ID0gW107XG4gIGVsc2UgaWYgKGlzRnVuY3Rpb24odGhpcy5fZXZlbnRzW3R5cGVdKSlcbiAgICByZXQgPSBbdGhpcy5fZXZlbnRzW3R5cGVdXTtcbiAgZWxzZVxuICAgIHJldCA9IHRoaXMuX2V2ZW50c1t0eXBlXS5zbGljZSgpO1xuICByZXR1cm4gcmV0O1xufTtcblxuRXZlbnRFbWl0dGVyLmxpc3RlbmVyQ291bnQgPSBmdW5jdGlvbihlbWl0dGVyLCB0eXBlKSB7XG4gIHZhciByZXQ7XG4gIGlmICghZW1pdHRlci5fZXZlbnRzIHx8ICFlbWl0dGVyLl9ldmVudHNbdHlwZV0pXG4gICAgcmV0ID0gMDtcbiAgZWxzZSBpZiAoaXNGdW5jdGlvbihlbWl0dGVyLl9ldmVudHNbdHlwZV0pKVxuICAgIHJldCA9IDE7XG4gIGVsc2VcbiAgICByZXQgPSBlbWl0dGVyLl9ldmVudHNbdHlwZV0ubGVuZ3RoO1xuICByZXR1cm4gcmV0O1xufTtcblxuZnVuY3Rpb24gaXNGdW5jdGlvbihhcmcpIHtcbiAgcmV0dXJuIHR5cGVvZiBhcmcgPT09ICdmdW5jdGlvbic7XG59XG5cbmZ1bmN0aW9uIGlzTnVtYmVyKGFyZykge1xuICByZXR1cm4gdHlwZW9mIGFyZyA9PT0gJ251bWJlcic7XG59XG5cbmZ1bmN0aW9uIGlzT2JqZWN0KGFyZykge1xuICByZXR1cm4gdHlwZW9mIGFyZyA9PT0gJ29iamVjdCcgJiYgYXJnICE9PSBudWxsO1xufVxuXG5mdW5jdGlvbiBpc1VuZGVmaW5lZChhcmcpIHtcbiAgcmV0dXJuIGFyZyA9PT0gdm9pZCAwO1xufVxuIiwidmFyICQgPSByZXF1aXJlKFwianF1ZXJ5XCIpO1xyXG5cclxudmFyIEFjdGlvblR5cGVzID0ge1xyXG4gICAgLy8gQ29ubmVjdGlvblxyXG4gICAgQ09OTkVDVElPTl9PUEVOOiBcImNvbm5lY3Rpb25fb3BlblwiLFxyXG4gICAgQ09OTkVDVElPTl9DTE9TRTogXCJjb25uZWN0aW9uX2Nsb3NlXCIsXHJcbiAgICBDT05ORUNUSU9OX0VSUk9SOiBcImNvbm5lY3Rpb25fZXJyb3JcIixcclxuXHJcbiAgICAvLyBTdG9yZXNcclxuICAgIFNFVFRJTkdTX1NUT1JFOiBcInNldHRpbmdzXCIsXHJcbiAgICBFVkVOVF9TVE9SRTogXCJldmVudHNcIixcclxuICAgIEZMT1dfU1RPUkU6IFwiZmxvd3NcIixcclxufTtcclxuXHJcbnZhciBTdG9yZUNtZHMgPSB7XHJcbiAgICBBREQ6IFwiYWRkXCIsXHJcbiAgICBVUERBVEU6IFwidXBkYXRlXCIsXHJcbiAgICBSRU1PVkU6IFwicmVtb3ZlXCIsXHJcbiAgICBSRVNFVDogXCJyZXNldFwiXHJcbn07XHJcblxyXG52YXIgQ29ubmVjdGlvbkFjdGlvbnMgPSB7XHJcbiAgICBvcGVuOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFZpZXdBY3Rpb24oe1xyXG4gICAgICAgICAgICB0eXBlOiBBY3Rpb25UeXBlcy5DT05ORUNUSU9OX09QRU5cclxuICAgICAgICB9KTtcclxuICAgIH0sXHJcbiAgICBjbG9zZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIEFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uKHtcclxuICAgICAgICAgICAgdHlwZTogQWN0aW9uVHlwZXMuQ09OTkVDVElPTl9DTE9TRVxyXG4gICAgICAgIH0pO1xyXG4gICAgfSxcclxuICAgIGVycm9yOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFZpZXdBY3Rpb24oe1xyXG4gICAgICAgICAgICB0eXBlOiBBY3Rpb25UeXBlcy5DT05ORUNUSU9OX0VSUk9SXHJcbiAgICAgICAgfSk7XHJcbiAgICB9XHJcbn07XHJcblxyXG52YXIgU2V0dGluZ3NBY3Rpb25zID0ge1xyXG4gICAgdXBkYXRlOiBmdW5jdGlvbiAoc2V0dGluZ3MpIHtcclxuXHJcbiAgICAgICAgJC5hamF4KHtcclxuICAgICAgICAgICAgdHlwZTogXCJQVVRcIixcclxuICAgICAgICAgICAgdXJsOiBcIi9zZXR0aW5nc1wiLFxyXG4gICAgICAgICAgICBkYXRhOiBzZXR0aW5nc1xyXG4gICAgICAgIH0pO1xyXG5cclxuICAgICAgICAvKlxyXG4gICAgICAgIC8vRmFjZWJvb2sgRmx1eDogV2UgZG8gYW4gb3B0aW1pc3RpYyB1cGRhdGUgb24gdGhlIGNsaWVudCBhbHJlYWR5LlxyXG4gICAgICAgIEFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uKHtcclxuICAgICAgICAgICAgdHlwZTogQWN0aW9uVHlwZXMuU0VUVElOR1NfU1RPUkUsXHJcbiAgICAgICAgICAgIGNtZDogU3RvcmVDbWRzLlVQREFURSxcclxuICAgICAgICAgICAgZGF0YTogc2V0dGluZ3NcclxuICAgICAgICB9KTtcclxuICAgICAgICAqL1xyXG4gICAgfVxyXG59O1xyXG5cclxudmFyIEV2ZW50TG9nQWN0aW9uc19ldmVudF9pZCA9IDA7XHJcbnZhciBFdmVudExvZ0FjdGlvbnMgPSB7XHJcbiAgICBhZGRfZXZlbnQ6IGZ1bmN0aW9uIChtZXNzYWdlKSB7XHJcbiAgICAgICAgQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFZpZXdBY3Rpb24oe1xyXG4gICAgICAgICAgICB0eXBlOiBBY3Rpb25UeXBlcy5FVkVOVF9TVE9SRSxcclxuICAgICAgICAgICAgY21kOiBTdG9yZUNtZHMuQURELFxyXG4gICAgICAgICAgICBkYXRhOiB7XHJcbiAgICAgICAgICAgICAgICBtZXNzYWdlOiBtZXNzYWdlLFxyXG4gICAgICAgICAgICAgICAgbGV2ZWw6IFwid2ViXCIsXHJcbiAgICAgICAgICAgICAgICBpZDogXCJ2aWV3QWN0aW9uLVwiICsgRXZlbnRMb2dBY3Rpb25zX2V2ZW50X2lkKytcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgIH0pO1xyXG4gICAgfVxyXG59O1xyXG5cclxudmFyIEZsb3dBY3Rpb25zID0ge1xyXG4gICAgYWNjZXB0OiBmdW5jdGlvbiAoZmxvdykge1xyXG4gICAgICAgICQucG9zdChcIi9mbG93cy9cIiArIGZsb3cuaWQgKyBcIi9hY2NlcHRcIik7XHJcbiAgICB9LFxyXG4gICAgYWNjZXB0X2FsbDogZnVuY3Rpb24oKXtcclxuICAgICAgICAkLnBvc3QoXCIvZmxvd3MvYWNjZXB0XCIpO1xyXG4gICAgfSxcclxuICAgIFwiZGVsZXRlXCI6IGZ1bmN0aW9uKGZsb3cpe1xyXG4gICAgICAgICQuYWpheCh7XHJcbiAgICAgICAgICAgIHR5cGU6XCJERUxFVEVcIixcclxuICAgICAgICAgICAgdXJsOiBcIi9mbG93cy9cIiArIGZsb3cuaWRcclxuICAgICAgICB9KTtcclxuICAgIH0sXHJcbiAgICBkdXBsaWNhdGU6IGZ1bmN0aW9uKGZsb3cpe1xyXG4gICAgICAgICQucG9zdChcIi9mbG93cy9cIiArIGZsb3cuaWQgKyBcIi9kdXBsaWNhdGVcIik7XHJcbiAgICB9LFxyXG4gICAgcmVwbGF5OiBmdW5jdGlvbihmbG93KXtcclxuICAgICAgICAkLnBvc3QoXCIvZmxvd3MvXCIgKyBmbG93LmlkICsgXCIvcmVwbGF5XCIpO1xyXG4gICAgfSxcclxuICAgIHJldmVydDogZnVuY3Rpb24oZmxvdyl7XHJcbiAgICAgICAgJC5wb3N0KFwiL2Zsb3dzL1wiICsgZmxvdy5pZCArIFwiL3JldmVydFwiKTtcclxuICAgIH0sXHJcbiAgICB1cGRhdGU6IGZ1bmN0aW9uIChmbG93KSB7XHJcbiAgICAgICAgQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFZpZXdBY3Rpb24oe1xyXG4gICAgICAgICAgICB0eXBlOiBBY3Rpb25UeXBlcy5GTE9XX1NUT1JFLFxyXG4gICAgICAgICAgICBjbWQ6IFN0b3JlQ21kcy5VUERBVEUsXHJcbiAgICAgICAgICAgIGRhdGE6IGZsb3dcclxuICAgICAgICB9KTtcclxuICAgIH0sXHJcbiAgICBjbGVhcjogZnVuY3Rpb24oKXtcclxuICAgICAgICAkLnBvc3QoXCIvY2xlYXJcIik7XHJcbiAgICB9XHJcbn07XHJcblxyXG5RdWVyeSA9IHtcclxuICAgIEZJTFRFUjogXCJmXCIsXHJcbiAgICBISUdITElHSFQ6IFwiaFwiLFxyXG4gICAgU0hPV19FVkVOVExPRzogXCJlXCJcclxufTtcclxuXHJcbm1vZHVsZS5leHBvcnRzID0ge1xyXG4gICAgQWN0aW9uVHlwZXM6IEFjdGlvblR5cGVzLFxyXG4gICAgQ29ubmVjdGlvbkFjdGlvbnM6IENvbm5lY3Rpb25BY3Rpb25zLFxyXG4gICAgRmxvd0FjdGlvbnM6IEZsb3dBY3Rpb25zLFxyXG4gICAgU3RvcmVDbWRzOiBTdG9yZUNtZHNcclxufTsiLCJcclxudmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xyXG52YXIgUmVhY3RSb3V0ZXIgPSByZXF1aXJlKFwicmVhY3Qtcm91dGVyXCIpO1xyXG52YXIgJCA9IHJlcXVpcmUoXCJqcXVlcnlcIik7XHJcblxyXG52YXIgQ29ubmVjdGlvbiA9IHJlcXVpcmUoXCIuL2Nvbm5lY3Rpb25cIik7XHJcbnZhciBwcm94eWFwcCA9IHJlcXVpcmUoXCIuL2NvbXBvbmVudHMvcHJveHlhcHAuanNcIik7XHJcblxyXG4kKGZ1bmN0aW9uICgpIHtcclxuICAgIHdpbmRvdy53cyA9IG5ldyBDb25uZWN0aW9uKFwiL3VwZGF0ZXNcIik7XHJcblxyXG4gICAgUmVhY3RSb3V0ZXIucnVuKHByb3h5YXBwLnJvdXRlcywgZnVuY3Rpb24gKEhhbmRsZXIpIHtcclxuICAgICAgICBSZWFjdC5yZW5kZXIoPEhhbmRsZXIvPiwgZG9jdW1lbnQuYm9keSk7XHJcbiAgICB9KTtcclxufSk7XHJcblxyXG4iLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XHJcbnZhciBSZWFjdFJvdXRlciA9IHJlcXVpcmUoXCJyZWFjdC1yb3V0ZXJcIik7XHJcbnZhciBfID0gcmVxdWlyZShcImxvZGFzaFwiKTtcclxuXHJcbi8vIGh0dHA6Ly9ibG9nLnZqZXV4LmNvbS8yMDEzL2phdmFzY3JpcHQvc2Nyb2xsLXBvc2l0aW9uLXdpdGgtcmVhY3QuaHRtbCAoYWxzbyBjb250YWlucyBpbnZlcnNlIGV4YW1wbGUpXHJcbnZhciBBdXRvU2Nyb2xsTWl4aW4gPSB7XHJcbiAgICBjb21wb25lbnRXaWxsVXBkYXRlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIG5vZGUgPSB0aGlzLmdldERPTU5vZGUoKTtcclxuICAgICAgICB0aGlzLl9zaG91bGRTY3JvbGxCb3R0b20gPSAoXHJcbiAgICAgICAgICAgIG5vZGUuc2Nyb2xsVG9wICE9PSAwICYmXHJcbiAgICAgICAgICAgIG5vZGUuc2Nyb2xsVG9wICsgbm9kZS5jbGllbnRIZWlnaHQgPT09IG5vZGUuc2Nyb2xsSGVpZ2h0XHJcbiAgICAgICAgKTtcclxuICAgIH0sXHJcbiAgICBjb21wb25lbnREaWRVcGRhdGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICBpZiAodGhpcy5fc2hvdWxkU2Nyb2xsQm90dG9tKSB7XHJcbiAgICAgICAgICAgIHZhciBub2RlID0gdGhpcy5nZXRET01Ob2RlKCk7XHJcbiAgICAgICAgICAgIG5vZGUuc2Nyb2xsVG9wID0gbm9kZS5zY3JvbGxIZWlnaHQ7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxufTtcclxuXHJcblxyXG52YXIgU3RpY2t5SGVhZE1peGluID0ge1xyXG4gICAgYWRqdXN0SGVhZDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIC8vIEFidXNpbmcgQ1NTIHRyYW5zZm9ybXMgdG8gc2V0IHRoZSBlbGVtZW50XHJcbiAgICAgICAgLy8gcmVmZXJlbmNlZCBhcyBoZWFkIGludG8gc29tZSBraW5kIG9mIHBvc2l0aW9uOnN0aWNreS5cclxuICAgICAgICB2YXIgaGVhZCA9IHRoaXMucmVmcy5oZWFkLmdldERPTU5vZGUoKTtcclxuICAgICAgICBoZWFkLnN0eWxlLnRyYW5zZm9ybSA9IFwidHJhbnNsYXRlKDAsXCIgKyB0aGlzLmdldERPTU5vZGUoKS5zY3JvbGxUb3AgKyBcInB4KVwiO1xyXG4gICAgfVxyXG59O1xyXG5cclxuXHJcbnZhciBOYXZpZ2F0aW9uID0gXy5leHRlbmQoe30sIFJlYWN0Um91dGVyLk5hdmlnYXRpb24sIHtcclxuICAgIHNldFF1ZXJ5OiBmdW5jdGlvbiAoZGljdCkge1xyXG4gICAgICAgIHZhciBxID0gdGhpcy5jb250ZXh0LmdldEN1cnJlbnRRdWVyeSgpO1xyXG4gICAgICAgIGZvcih2YXIgaSBpbiBkaWN0KXtcclxuICAgICAgICAgICAgaWYoZGljdC5oYXNPd25Qcm9wZXJ0eShpKSl7XHJcbiAgICAgICAgICAgICAgICBxW2ldID0gZGljdFtpXSB8fCB1bmRlZmluZWQ7IC8vZmFsc2V5IHZhbHVlcyBzaGFsbCBiZSByZW1vdmVkLlxyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHEuXyA9IFwiX1wiOyAvLyB3b3JrYXJvdW5kIGZvciBodHRwczovL2dpdGh1Yi5jb20vcmFja3QvcmVhY3Qtcm91dGVyL3B1bGwvNTk5XHJcbiAgICAgICAgdGhpcy5yZXBsYWNlV2l0aCh0aGlzLmNvbnRleHQuZ2V0Q3VycmVudFBhdGgoKSwgdGhpcy5jb250ZXh0LmdldEN1cnJlbnRQYXJhbXMoKSwgcSk7XHJcbiAgICB9LFxyXG4gICAgcmVwbGFjZVdpdGg6IGZ1bmN0aW9uKHJvdXRlTmFtZU9yUGF0aCwgcGFyYW1zLCBxdWVyeSkge1xyXG4gICAgICAgIGlmKHJvdXRlTmFtZU9yUGF0aCA9PT0gdW5kZWZpbmVkKXtcclxuICAgICAgICAgICAgcm91dGVOYW1lT3JQYXRoID0gdGhpcy5jb250ZXh0LmdldEN1cnJlbnRQYXRoKCk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIGlmKHBhcmFtcyA9PT0gdW5kZWZpbmVkKXtcclxuICAgICAgICAgICAgcGFyYW1zID0gdGhpcy5jb250ZXh0LmdldEN1cnJlbnRQYXJhbXMoKTtcclxuICAgICAgICB9XHJcbiAgICAgICAgaWYocXVlcnkgPT09IHVuZGVmaW5lZCl7XHJcbiAgICAgICAgICAgIHF1ZXJ5ID0gdGhpcy5jb250ZXh0LmdldEN1cnJlbnRRdWVyeSgpO1xyXG4gICAgICAgIH1cclxuICAgICAgICBSZWFjdFJvdXRlci5OYXZpZ2F0aW9uLnJlcGxhY2VXaXRoLmNhbGwodGhpcywgcm91dGVOYW1lT3JQYXRoLCBwYXJhbXMsIHF1ZXJ5KTtcclxuICAgIH1cclxufSk7XHJcbl8uZXh0ZW5kKE5hdmlnYXRpb24uY29udGV4dFR5cGVzLCBSZWFjdFJvdXRlci5TdGF0ZS5jb250ZXh0VHlwZXMpO1xyXG5cclxudmFyIFN0YXRlID0gXy5leHRlbmQoe30sIFJlYWN0Um91dGVyLlN0YXRlLCB7XHJcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLl9xdWVyeSA9IHRoaXMuY29udGV4dC5nZXRDdXJyZW50UXVlcnkoKTtcclxuICAgICAgICB0aGlzLl9xdWVyeVdhdGNoZXMgPSBbXTtcclxuICAgICAgICByZXR1cm4gbnVsbDtcclxuICAgIH0sXHJcbiAgICBvblF1ZXJ5Q2hhbmdlOiBmdW5jdGlvbiAoa2V5LCBjYWxsYmFjaykge1xyXG4gICAgICAgIHRoaXMuX3F1ZXJ5V2F0Y2hlcy5wdXNoKHtcclxuICAgICAgICAgICAga2V5OiBrZXksXHJcbiAgICAgICAgICAgIGNhbGxiYWNrOiBjYWxsYmFja1xyXG4gICAgICAgIH0pO1xyXG4gICAgfSxcclxuICAgIGNvbXBvbmVudFdpbGxSZWNlaXZlUHJvcHM6IGZ1bmN0aW9uIChuZXh0UHJvcHMsIG5leHRTdGF0ZSkge1xyXG4gICAgICAgIHZhciBxID0gdGhpcy5jb250ZXh0LmdldEN1cnJlbnRRdWVyeSgpO1xyXG4gICAgICAgIGZvciAodmFyIGkgPSAwOyBpIDwgdGhpcy5fcXVlcnlXYXRjaGVzLmxlbmd0aDsgaSsrKSB7XHJcbiAgICAgICAgICAgIHZhciB3YXRjaCA9IHRoaXMuX3F1ZXJ5V2F0Y2hlc1tpXTtcclxuICAgICAgICAgICAgaWYgKHRoaXMuX3F1ZXJ5W3dhdGNoLmtleV0gIT09IHFbd2F0Y2gua2V5XSkge1xyXG4gICAgICAgICAgICAgICAgd2F0Y2guY2FsbGJhY2sodGhpcy5fcXVlcnlbd2F0Y2gua2V5XSwgcVt3YXRjaC5rZXldLCB3YXRjaC5rZXkpO1xyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHRoaXMuX3F1ZXJ5ID0gcTtcclxuICAgIH1cclxufSk7XHJcblxyXG52YXIgU3BsaXR0ZXIgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICBnZXREZWZhdWx0UHJvcHM6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICByZXR1cm4ge1xyXG4gICAgICAgICAgICBheGlzOiBcInhcIlxyXG4gICAgICAgIH07XHJcbiAgICB9LFxyXG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgcmV0dXJuIHtcclxuICAgICAgICAgICAgYXBwbGllZDogZmFsc2UsXHJcbiAgICAgICAgICAgIHN0YXJ0WDogZmFsc2UsXHJcbiAgICAgICAgICAgIHN0YXJ0WTogZmFsc2VcclxuICAgICAgICB9O1xyXG4gICAgfSxcclxuICAgIG9uTW91c2VEb3duOiBmdW5jdGlvbiAoZSkge1xyXG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe1xyXG4gICAgICAgICAgICBzdGFydFg6IGUucGFnZVgsXHJcbiAgICAgICAgICAgIHN0YXJ0WTogZS5wYWdlWVxyXG4gICAgICAgIH0pO1xyXG4gICAgICAgIHdpbmRvdy5hZGRFdmVudExpc3RlbmVyKFwibW91c2Vtb3ZlXCIsIHRoaXMub25Nb3VzZU1vdmUpO1xyXG4gICAgICAgIHdpbmRvdy5hZGRFdmVudExpc3RlbmVyKFwibW91c2V1cFwiLCB0aGlzLm9uTW91c2VVcCk7XHJcbiAgICAgICAgLy8gT2NjYXNpb25hbGx5LCBvbmx5IGEgZHJhZ0VuZCBldmVudCBpcyB0cmlnZ2VyZWQsIGJ1dCBubyBtb3VzZVVwLlxyXG4gICAgICAgIHdpbmRvdy5hZGRFdmVudExpc3RlbmVyKFwiZHJhZ2VuZFwiLCB0aGlzLm9uRHJhZ0VuZCk7XHJcbiAgICB9LFxyXG4gICAgb25EcmFnRW5kOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdGhpcy5nZXRET01Ob2RlKCkuc3R5bGUudHJhbnNmb3JtID0gXCJcIjtcclxuICAgICAgICB3aW5kb3cucmVtb3ZlRXZlbnRMaXN0ZW5lcihcImRyYWdlbmRcIiwgdGhpcy5vbkRyYWdFbmQpO1xyXG4gICAgICAgIHdpbmRvdy5yZW1vdmVFdmVudExpc3RlbmVyKFwibW91c2V1cFwiLCB0aGlzLm9uTW91c2VVcCk7XHJcbiAgICAgICAgd2luZG93LnJlbW92ZUV2ZW50TGlzdGVuZXIoXCJtb3VzZW1vdmVcIiwgdGhpcy5vbk1vdXNlTW92ZSk7XHJcbiAgICB9LFxyXG4gICAgb25Nb3VzZVVwOiBmdW5jdGlvbiAoZSkge1xyXG4gICAgICAgIHRoaXMub25EcmFnRW5kKCk7XHJcblxyXG4gICAgICAgIHZhciBub2RlID0gdGhpcy5nZXRET01Ob2RlKCk7XHJcbiAgICAgICAgdmFyIHByZXYgPSBub2RlLnByZXZpb3VzRWxlbWVudFNpYmxpbmc7XHJcbiAgICAgICAgdmFyIG5leHQgPSBub2RlLm5leHRFbGVtZW50U2libGluZztcclxuXHJcbiAgICAgICAgdmFyIGRYID0gZS5wYWdlWCAtIHRoaXMuc3RhdGUuc3RhcnRYO1xyXG4gICAgICAgIHZhciBkWSA9IGUucGFnZVkgLSB0aGlzLnN0YXRlLnN0YXJ0WTtcclxuICAgICAgICB2YXIgZmxleEJhc2lzO1xyXG4gICAgICAgIGlmICh0aGlzLnByb3BzLmF4aXMgPT09IFwieFwiKSB7XHJcbiAgICAgICAgICAgIGZsZXhCYXNpcyA9IHByZXYub2Zmc2V0V2lkdGggKyBkWDtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICBmbGV4QmFzaXMgPSBwcmV2Lm9mZnNldEhlaWdodCArIGRZO1xyXG4gICAgICAgIH1cclxuXHJcbiAgICAgICAgcHJldi5zdHlsZS5mbGV4ID0gXCIwIDAgXCIgKyBNYXRoLm1heCgwLCBmbGV4QmFzaXMpICsgXCJweFwiO1xyXG4gICAgICAgIG5leHQuc3R5bGUuZmxleCA9IFwiMSAxIGF1dG9cIjtcclxuXHJcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7XHJcbiAgICAgICAgICAgIGFwcGxpZWQ6IHRydWVcclxuICAgICAgICB9KTtcclxuICAgICAgICB0aGlzLm9uUmVzaXplKCk7XHJcbiAgICB9LFxyXG4gICAgb25Nb3VzZU1vdmU6IGZ1bmN0aW9uIChlKSB7XHJcbiAgICAgICAgdmFyIGRYID0gMCwgZFkgPSAwO1xyXG4gICAgICAgIGlmICh0aGlzLnByb3BzLmF4aXMgPT09IFwieFwiKSB7XHJcbiAgICAgICAgICAgIGRYID0gZS5wYWdlWCAtIHRoaXMuc3RhdGUuc3RhcnRYO1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIGRZID0gZS5wYWdlWSAtIHRoaXMuc3RhdGUuc3RhcnRZO1xyXG4gICAgICAgIH1cclxuICAgICAgICB0aGlzLmdldERPTU5vZGUoKS5zdHlsZS50cmFuc2Zvcm0gPSBcInRyYW5zbGF0ZShcIiArIGRYICsgXCJweCxcIiArIGRZICsgXCJweClcIjtcclxuICAgIH0sXHJcbiAgICBvblJlc2l6ZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIC8vIFRyaWdnZXIgYSBnbG9iYWwgcmVzaXplIGV2ZW50LiBUaGlzIG5vdGlmaWVzIGNvbXBvbmVudHMgdGhhdCBlbXBsb3kgdmlydHVhbCBzY3JvbGxpbmdcclxuICAgICAgICAvLyB0aGF0IHRoZWlyIHZpZXdwb3J0IG1heSBoYXZlIGNoYW5nZWQuXHJcbiAgICAgICAgd2luZG93LnNldFRpbWVvdXQoZnVuY3Rpb24gKCkge1xyXG4gICAgICAgICAgICB3aW5kb3cuZGlzcGF0Y2hFdmVudChuZXcgQ3VzdG9tRXZlbnQoXCJyZXNpemVcIikpO1xyXG4gICAgICAgIH0sIDEpO1xyXG4gICAgfSxcclxuICAgIHJlc2V0OiBmdW5jdGlvbiAod2lsbFVubW91bnQpIHtcclxuICAgICAgICBpZiAoIXRoaXMuc3RhdGUuYXBwbGllZCkge1xyXG4gICAgICAgICAgICByZXR1cm47XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHZhciBub2RlID0gdGhpcy5nZXRET01Ob2RlKCk7XHJcbiAgICAgICAgdmFyIHByZXYgPSBub2RlLnByZXZpb3VzRWxlbWVudFNpYmxpbmc7XHJcbiAgICAgICAgdmFyIG5leHQgPSBub2RlLm5leHRFbGVtZW50U2libGluZztcclxuXHJcbiAgICAgICAgcHJldi5zdHlsZS5mbGV4ID0gXCJcIjtcclxuICAgICAgICBuZXh0LnN0eWxlLmZsZXggPSBcIlwiO1xyXG5cclxuICAgICAgICBpZiAoIXdpbGxVbm1vdW50KSB7XHJcbiAgICAgICAgICAgIHRoaXMuc2V0U3RhdGUoe1xyXG4gICAgICAgICAgICAgICAgYXBwbGllZDogZmFsc2VcclxuICAgICAgICAgICAgfSk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHRoaXMub25SZXNpemUoKTtcclxuICAgIH0sXHJcbiAgICBjb21wb25lbnRXaWxsVW5tb3VudDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMucmVzZXQodHJ1ZSk7XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGNsYXNzTmFtZSA9IFwic3BsaXR0ZXJcIjtcclxuICAgICAgICBpZiAodGhpcy5wcm9wcy5heGlzID09PSBcInhcIikge1xyXG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCIgc3BsaXR0ZXIteFwiO1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcIiBzcGxpdHRlci15XCI7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPXtjbGFzc05hbWV9PlxyXG4gICAgICAgICAgICAgICAgPGRpdiBvbk1vdXNlRG93bj17dGhpcy5vbk1vdXNlRG93bn0gZHJhZ2dhYmxlPVwidHJ1ZVwiPjwvZGl2PlxyXG4gICAgICAgICAgICA8L2Rpdj5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbm1vZHVsZS5leHBvcnRzID0ge1xyXG4gICAgU3RhdGU6IFN0YXRlLFxyXG4gICAgTmF2aWdhdGlvbjogTmF2aWdhdGlvbixcclxuICAgIFN0aWNreUhlYWRNaXhpbjogU3RpY2t5SGVhZE1peGluLFxyXG4gICAgQXV0b1Njcm9sbE1peGluOiBBdXRvU2Nyb2xsTWl4aW4sXHJcbiAgICBTcGxpdHRlcjogU3BsaXR0ZXJcclxufSIsInZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcclxudmFyIGNvbW1vbiA9IHJlcXVpcmUoXCIuL2NvbW1vbi5qc1wiKTtcclxudmFyIFZpcnR1YWxTY3JvbGxNaXhpbiA9IHJlcXVpcmUoXCIuL3ZpcnR1YWxzY3JvbGwuanNcIik7XHJcbnZhciB2aWV3cyA9IHJlcXVpcmUoXCIuLi9zdG9yZS92aWV3LmpzXCIpO1xyXG5cclxudmFyIExvZ01lc3NhZ2UgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZW50cnkgPSB0aGlzLnByb3BzLmVudHJ5O1xyXG4gICAgICAgIHZhciBpbmRpY2F0b3I7XHJcbiAgICAgICAgc3dpdGNoIChlbnRyeS5sZXZlbCkge1xyXG4gICAgICAgICAgICBjYXNlIFwid2ViXCI6XHJcbiAgICAgICAgICAgICAgICBpbmRpY2F0b3IgPSA8aSBjbGFzc05hbWU9XCJmYSBmYS1mdyBmYS1odG1sNVwiPjwvaT47XHJcbiAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgY2FzZSBcImRlYnVnXCI6XHJcbiAgICAgICAgICAgICAgICBpbmRpY2F0b3IgPSA8aSBjbGFzc05hbWU9XCJmYSBmYS1mdyBmYS1idWdcIj48L2k+O1xyXG4gICAgICAgICAgICAgICAgYnJlYWs7XHJcbiAgICAgICAgICAgIGRlZmF1bHQ6XHJcbiAgICAgICAgICAgICAgICBpbmRpY2F0b3IgPSA8aSBjbGFzc05hbWU9XCJmYSBmYS1mdyBmYS1pbmZvXCI+PC9pPjtcclxuICAgICAgICB9XHJcbiAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgPGRpdj5cclxuICAgICAgICAgICAgICAgIHsgaW5kaWNhdG9yIH0ge2VudHJ5Lm1lc3NhZ2V9XHJcbiAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICk7XHJcbiAgICB9LFxyXG4gICAgc2hvdWxkQ29tcG9uZW50VXBkYXRlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgcmV0dXJuIGZhbHNlOyAvLyBsb2cgZW50cmllcyBhcmUgaW1tdXRhYmxlLlxyXG4gICAgfVxyXG59KTtcclxuXHJcbnZhciBFdmVudExvZ0NvbnRlbnRzID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgbWl4aW5zOiBbY29tbW9uLkF1dG9TY3JvbGxNaXhpbiwgVmlydHVhbFNjcm9sbE1peGluXSxcclxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHJldHVybiB7XHJcbiAgICAgICAgICAgIGxvZzogW11cclxuICAgICAgICB9O1xyXG4gICAgfSxcclxuICAgIGNvbXBvbmVudFdpbGxNb3VudDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMub3BlblZpZXcodGhpcy5wcm9wcy5ldmVudFN0b3JlKTtcclxuICAgIH0sXHJcbiAgICBjb21wb25lbnRXaWxsVW5tb3VudDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMuY2xvc2VWaWV3KCk7XHJcbiAgICB9LFxyXG4gICAgb3BlblZpZXc6IGZ1bmN0aW9uIChzdG9yZSkge1xyXG4gICAgICAgIHZhciB2aWV3ID0gbmV3IHZpZXdzLlN0b3JlVmlldyhzdG9yZSwgZnVuY3Rpb24gKGVudHJ5KSB7XHJcbiAgICAgICAgICAgIHJldHVybiB0aGlzLnByb3BzLmZpbHRlcltlbnRyeS5sZXZlbF07XHJcbiAgICAgICAgfS5iaW5kKHRoaXMpKTtcclxuICAgICAgICB0aGlzLnNldFN0YXRlKHtcclxuICAgICAgICAgICAgdmlldzogdmlld1xyXG4gICAgICAgIH0pO1xyXG5cclxuICAgICAgICB2aWV3LmFkZExpc3RlbmVyKFwiYWRkXCIsIHRoaXMub25FdmVudExvZ0NoYW5nZSk7XHJcbiAgICAgICAgdmlldy5hZGRMaXN0ZW5lcihcInJlY2FsY3VsYXRlXCIsIHRoaXMub25FdmVudExvZ0NoYW5nZSk7XHJcbiAgICB9LFxyXG4gICAgY2xvc2VWaWV3OiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdGhpcy5zdGF0ZS52aWV3LmNsb3NlKCk7XHJcbiAgICB9LFxyXG4gICAgb25FdmVudExvZ0NoYW5nZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe1xyXG4gICAgICAgICAgICBsb2c6IHRoaXMuc3RhdGUudmlldy5saXN0XHJcbiAgICAgICAgfSk7XHJcbiAgICB9LFxyXG4gICAgY29tcG9uZW50V2lsbFJlY2VpdmVQcm9wczogZnVuY3Rpb24gKG5leHRQcm9wcykge1xyXG4gICAgICAgIGlmIChuZXh0UHJvcHMuZmlsdGVyICE9PSB0aGlzLnByb3BzLmZpbHRlcikge1xyXG4gICAgICAgICAgICB0aGlzLnByb3BzLmZpbHRlciA9IG5leHRQcm9wcy5maWx0ZXI7IC8vIERpcnR5OiBNYWtlIHN1cmUgdGhhdCB2aWV3IGZpbHRlciBzZWVzIHRoZSB1cGRhdGUuXHJcbiAgICAgICAgICAgIHRoaXMuc3RhdGUudmlldy5yZWNhbGN1bGF0ZSgpO1xyXG4gICAgICAgIH1cclxuICAgICAgICBpZiAobmV4dFByb3BzLmV2ZW50U3RvcmUgIT09IHRoaXMucHJvcHMuZXZlbnRTdG9yZSkge1xyXG4gICAgICAgICAgICB0aGlzLmNsb3NlVmlldygpO1xyXG4gICAgICAgICAgICB0aGlzLm9wZW5WaWV3KG5leHRQcm9wcy5ldmVudFN0b3JlKTtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgZ2V0RGVmYXVsdFByb3BzOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgcmV0dXJuIHtcclxuICAgICAgICAgICAgcm93SGVpZ2h0OiA0NSxcclxuICAgICAgICAgICAgcm93SGVpZ2h0TWluOiAxNSxcclxuICAgICAgICAgICAgcGxhY2Vob2xkZXJUYWdOYW1lOiBcImRpdlwiXHJcbiAgICAgICAgfTtcclxuICAgIH0sXHJcbiAgICByZW5kZXJSb3c6IGZ1bmN0aW9uIChlbGVtKSB7XHJcbiAgICAgICAgcmV0dXJuIDxMb2dNZXNzYWdlIGtleT17ZWxlbS5pZH0gZW50cnk9e2VsZW19Lz47XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIHJvd3MgPSB0aGlzLnJlbmRlclJvd3ModGhpcy5zdGF0ZS5sb2cpO1xyXG5cclxuICAgICAgICByZXR1cm4gPHByZSBvblNjcm9sbD17dGhpcy5vblNjcm9sbH0+XHJcbiAgICAgICAgICAgIHsgdGhpcy5nZXRQbGFjZWhvbGRlclRvcCh0aGlzLnN0YXRlLmxvZy5sZW5ndGgpIH1cclxuICAgICAgICAgICAge3Jvd3N9XHJcbiAgICAgICAgICAgIHsgdGhpcy5nZXRQbGFjZWhvbGRlckJvdHRvbSh0aGlzLnN0YXRlLmxvZy5sZW5ndGgpIH1cclxuICAgICAgICA8L3ByZT47XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIFRvZ2dsZUZpbHRlciA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHRvZ2dsZTogZnVuY3Rpb24gKGUpIHtcclxuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XHJcbiAgICAgICAgcmV0dXJuIHRoaXMucHJvcHMudG9nZ2xlTGV2ZWwodGhpcy5wcm9wcy5uYW1lKTtcclxuICAgIH0sXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgY2xhc3NOYW1lID0gXCJsYWJlbCBcIjtcclxuICAgICAgICBpZiAodGhpcy5wcm9wcy5hY3RpdmUpIHtcclxuICAgICAgICAgICAgY2xhc3NOYW1lICs9IFwibGFiZWwtcHJpbWFyeVwiO1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcImxhYmVsLWRlZmF1bHRcIjtcclxuICAgICAgICB9XHJcbiAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgPGFcclxuICAgICAgICAgICAgICAgIGhyZWY9XCIjXCJcclxuICAgICAgICAgICAgICAgIGNsYXNzTmFtZT17Y2xhc3NOYW1lfVxyXG4gICAgICAgICAgICAgICAgb25DbGljaz17dGhpcy50b2dnbGV9PlxyXG4gICAgICAgICAgICAgICAge3RoaXMucHJvcHMubmFtZX1cclxuICAgICAgICAgICAgPC9hPlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIEV2ZW50TG9nID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgcmV0dXJuIHtcclxuICAgICAgICAgICAgZmlsdGVyOiB7XHJcbiAgICAgICAgICAgICAgICBcImRlYnVnXCI6IGZhbHNlLFxyXG4gICAgICAgICAgICAgICAgXCJpbmZvXCI6IHRydWUsXHJcbiAgICAgICAgICAgICAgICBcIndlYlwiOiB0cnVlXHJcbiAgICAgICAgICAgIH1cclxuICAgICAgICB9O1xyXG4gICAgfSxcclxuICAgIGNsb3NlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGQgPSB7fTtcclxuICAgICAgICBkW1F1ZXJ5LlNIT1dfRVZFTlRMT0ddID0gdW5kZWZpbmVkO1xyXG4gICAgICAgIHRoaXMuc2V0UXVlcnkoZCk7XHJcbiAgICB9LFxyXG4gICAgdG9nZ2xlTGV2ZWw6IGZ1bmN0aW9uIChsZXZlbCkge1xyXG4gICAgICAgIHZhciBmaWx0ZXIgPSBfLmV4dGVuZCh7fSwgdGhpcy5zdGF0ZS5maWx0ZXIpO1xyXG4gICAgICAgIGZpbHRlcltsZXZlbF0gPSAhZmlsdGVyW2xldmVsXTtcclxuICAgICAgICB0aGlzLnNldFN0YXRlKHtmaWx0ZXI6IGZpbHRlcn0pO1xyXG4gICAgfSxcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPVwiZXZlbnRsb2dcIj5cclxuICAgICAgICAgICAgICAgIDxkaXY+XHJcbiAgICAgICAgICAgICAgICAgICAgRXZlbnRsb2dcclxuICAgICAgICAgICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cInB1bGwtcmlnaHRcIj5cclxuICAgICAgICAgICAgICAgICAgICAgICAgPFRvZ2dsZUZpbHRlciBuYW1lPVwiZGVidWdcIiBhY3RpdmU9e3RoaXMuc3RhdGUuZmlsdGVyLmRlYnVnfSB0b2dnbGVMZXZlbD17dGhpcy50b2dnbGVMZXZlbH0vPlxyXG4gICAgICAgICAgICAgICAgICAgICAgICA8VG9nZ2xlRmlsdGVyIG5hbWU9XCJpbmZvXCIgYWN0aXZlPXt0aGlzLnN0YXRlLmZpbHRlci5pbmZvfSB0b2dnbGVMZXZlbD17dGhpcy50b2dnbGVMZXZlbH0vPlxyXG4gICAgICAgICAgICAgICAgICAgICAgICA8VG9nZ2xlRmlsdGVyIG5hbWU9XCJ3ZWJcIiBhY3RpdmU9e3RoaXMuc3RhdGUuZmlsdGVyLndlYn0gdG9nZ2xlTGV2ZWw9e3RoaXMudG9nZ2xlTGV2ZWx9Lz5cclxuICAgICAgICAgICAgICAgICAgICAgICAgPGkgb25DbGljaz17dGhpcy5jbG9zZX0gY2xhc3NOYW1lPVwiZmEgZmEtY2xvc2VcIj48L2k+XHJcbiAgICAgICAgICAgICAgICAgICAgPC9kaXY+XHJcblxyXG4gICAgICAgICAgICAgICAgPC9kaXY+XHJcbiAgICAgICAgICAgICAgICA8RXZlbnRMb2dDb250ZW50cyBmaWx0ZXI9e3RoaXMuc3RhdGUuZmlsdGVyfSBldmVudFN0b3JlPXt0aGlzLnByb3BzLmV2ZW50U3RvcmV9Lz5cclxuICAgICAgICAgICAgPC9kaXY+XHJcbiAgICAgICAgKTtcclxuICAgIH1cclxufSk7XHJcblxyXG5tb2R1bGUuZXhwb3J0cyA9IEV2ZW50TG9nOyIsInZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcclxudmFyIF8gPSByZXF1aXJlKFwibG9kYXNoXCIpO1xyXG5cclxudmFyIGNvbW1vbiA9IHJlcXVpcmUoXCIuL2NvbW1vbi5qc1wiKTtcclxudmFyIGFjdGlvbnMgPSByZXF1aXJlKFwiLi4vYWN0aW9ucy5qc1wiKTtcclxudmFyIGZsb3d1dGlscyA9IHJlcXVpcmUoXCIuLi9mbG93L3V0aWxzLmpzXCIpO1xyXG52YXIgdG9wdXRpbHMgPSByZXF1aXJlKFwiLi4vdXRpbHMuanNcIik7XHJcblxyXG52YXIgTmF2QWN0aW9uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgb25DbGljazogZnVuY3Rpb24gKGUpIHtcclxuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XHJcbiAgICAgICAgdGhpcy5wcm9wcy5vbkNsaWNrKCk7XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgPGEgdGl0bGU9e3RoaXMucHJvcHMudGl0bGV9XHJcbiAgICAgICAgICAgICAgICBocmVmPVwiI1wiXHJcbiAgICAgICAgICAgICAgICBjbGFzc05hbWU9XCJuYXYtYWN0aW9uXCJcclxuICAgICAgICAgICAgICAgIG9uQ2xpY2s9e3RoaXMub25DbGlja30+XHJcbiAgICAgICAgICAgICAgICA8aSBjbGFzc05hbWU9e1wiZmEgZmEtZncgXCIgKyB0aGlzLnByb3BzLmljb259PjwvaT5cclxuICAgICAgICAgICAgPC9hPlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIEZsb3dEZXRhaWxOYXYgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcclxuXHJcbiAgICAgICAgdmFyIHRhYnMgPSB0aGlzLnByb3BzLnRhYnMubWFwKGZ1bmN0aW9uIChlKSB7XHJcbiAgICAgICAgICAgIHZhciBzdHIgPSBlLmNoYXJBdCgwKS50b1VwcGVyQ2FzZSgpICsgZS5zbGljZSgxKTtcclxuICAgICAgICAgICAgdmFyIGNsYXNzTmFtZSA9IHRoaXMucHJvcHMuYWN0aXZlID09PSBlID8gXCJhY3RpdmVcIiA6IFwiXCI7XHJcbiAgICAgICAgICAgIHZhciBvbkNsaWNrID0gZnVuY3Rpb24gKGV2ZW50KSB7XHJcbiAgICAgICAgICAgICAgICB0aGlzLnByb3BzLnNlbGVjdFRhYihlKTtcclxuICAgICAgICAgICAgICAgIGV2ZW50LnByZXZlbnREZWZhdWx0KCk7XHJcbiAgICAgICAgICAgIH0uYmluZCh0aGlzKTtcclxuICAgICAgICAgICAgcmV0dXJuIDxhIGtleT17ZX1cclxuICAgICAgICAgICAgICAgIGhyZWY9XCIjXCJcclxuICAgICAgICAgICAgICAgIGNsYXNzTmFtZT17Y2xhc3NOYW1lfVxyXG4gICAgICAgICAgICAgICAgb25DbGljaz17b25DbGlja30+e3N0cn08L2E+O1xyXG4gICAgICAgIH0uYmluZCh0aGlzKSk7XHJcblxyXG4gICAgICAgIHZhciBhY2NlcHRCdXR0b24gPSBudWxsO1xyXG4gICAgICAgIGlmKGZsb3cuaW50ZXJjZXB0ZWQpe1xyXG4gICAgICAgICAgICBhY2NlcHRCdXR0b24gPSA8TmF2QWN0aW9uIHRpdGxlPVwiW2FdY2NlcHQgaW50ZXJjZXB0ZWQgZmxvd1wiIGljb249XCJmYS1wbGF5XCIgb25DbGljaz17YWN0aW9ucy5GbG93QWN0aW9ucy5hY2NlcHQuYmluZChudWxsLCBmbG93KX0gLz47XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHZhciByZXZlcnRCdXR0b24gPSBudWxsO1xyXG4gICAgICAgIGlmKGZsb3cubW9kaWZpZWQpe1xyXG4gICAgICAgICAgICByZXZlcnRCdXR0b24gPSA8TmF2QWN0aW9uIHRpdGxlPVwicmV2ZXJ0IGNoYW5nZXMgdG8gZmxvdyBbVl1cIiBpY29uPVwiZmEtaGlzdG9yeVwiIG9uQ2xpY2s9e2FjdGlvbnMuRmxvd0FjdGlvbnMucmV2ZXJ0LmJpbmQobnVsbCwgZmxvdyl9IC8+O1xyXG4gICAgICAgIH1cclxuXHJcbiAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgPG5hdiByZWY9XCJoZWFkXCIgY2xhc3NOYW1lPVwibmF2LXRhYnMgbmF2LXRhYnMtc21cIj5cclxuICAgICAgICAgICAgICAgIHt0YWJzfVxyXG4gICAgICAgICAgICAgICAgPE5hdkFjdGlvbiB0aXRsZT1cIltkXWVsZXRlIGZsb3dcIiBpY29uPVwiZmEtdHJhc2hcIiBvbkNsaWNrPXthY3Rpb25zLkZsb3dBY3Rpb25zLmRlbGV0ZS5iaW5kKG51bGwsIGZsb3cpfSAvPlxyXG4gICAgICAgICAgICAgICAgPE5hdkFjdGlvbiB0aXRsZT1cIltEXXVwbGljYXRlIGZsb3dcIiBpY29uPVwiZmEtY29weVwiIG9uQ2xpY2s9e2FjdGlvbnMuRmxvd0FjdGlvbnMuZHVwbGljYXRlLmJpbmQobnVsbCwgZmxvdyl9IC8+XHJcbiAgICAgICAgICAgICAgICA8TmF2QWN0aW9uIGRpc2FibGVkIHRpdGxlPVwiW3JdZXBsYXkgZmxvd1wiIGljb249XCJmYS1yZXBlYXRcIiBvbkNsaWNrPXthY3Rpb25zLkZsb3dBY3Rpb25zLnJlcGxheS5iaW5kKG51bGwsIGZsb3cpfSAvPlxyXG4gICAgICAgICAgICAgICAge2FjY2VwdEJ1dHRvbn1cclxuICAgICAgICAgICAgICAgIHtyZXZlcnRCdXR0b259XHJcbiAgICAgICAgICAgIDwvbmF2PlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIEhlYWRlcnMgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgcm93cyA9IHRoaXMucHJvcHMubWVzc2FnZS5oZWFkZXJzLm1hcChmdW5jdGlvbiAoaGVhZGVyLCBpKSB7XHJcbiAgICAgICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgICAgICA8dHIga2V5PXtpfT5cclxuICAgICAgICAgICAgICAgICAgICA8dGQgY2xhc3NOYW1lPVwiaGVhZGVyLW5hbWVcIj57aGVhZGVyWzBdICsgXCI6XCJ9PC90ZD5cclxuICAgICAgICAgICAgICAgICAgICA8dGQgY2xhc3NOYW1lPVwiaGVhZGVyLXZhbHVlXCI+e2hlYWRlclsxXX08L3RkPlxyXG4gICAgICAgICAgICAgICAgPC90cj5cclxuICAgICAgICAgICAgKTtcclxuICAgICAgICB9KTtcclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8dGFibGUgY2xhc3NOYW1lPVwiaGVhZGVyLXRhYmxlXCI+XHJcbiAgICAgICAgICAgICAgICA8dGJvZHk+XHJcbiAgICAgICAgICAgICAgICAgICAge3Jvd3N9XHJcbiAgICAgICAgICAgICAgICA8L3Rib2R5PlxyXG4gICAgICAgICAgICA8L3RhYmxlPlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIEZsb3dEZXRhaWxSZXF1ZXN0ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XHJcbiAgICAgICAgdmFyIGZpcnN0X2xpbmUgPSBbXHJcbiAgICAgICAgICAgIGZsb3cucmVxdWVzdC5tZXRob2QsXHJcbiAgICAgICAgICAgIGZsb3d1dGlscy5SZXF1ZXN0VXRpbHMucHJldHR5X3VybChmbG93LnJlcXVlc3QpLFxyXG4gICAgICAgICAgICBcIkhUVFAvXCIgKyBmbG93LnJlcXVlc3QuaHR0cHZlcnNpb24uam9pbihcIi5cIilcclxuICAgICAgICBdLmpvaW4oXCIgXCIpO1xyXG4gICAgICAgIHZhciBjb250ZW50ID0gbnVsbDtcclxuICAgICAgICBpZiAoZmxvdy5yZXF1ZXN0LmNvbnRlbnRMZW5ndGggPiAwKSB7XHJcbiAgICAgICAgICAgIGNvbnRlbnQgPSBcIlJlcXVlc3QgQ29udGVudCBTaXplOiBcIiArIHRvcHV0aWxzLmZvcm1hdFNpemUoZmxvdy5yZXF1ZXN0LmNvbnRlbnRMZW5ndGgpO1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIGNvbnRlbnQgPSA8ZGl2IGNsYXNzTmFtZT1cImFsZXJ0IGFsZXJ0LWluZm9cIj5ObyBDb250ZW50PC9kaXY+O1xyXG4gICAgICAgIH1cclxuXHJcbiAgICAgICAgLy9UT0RPOiBTdHlsaW5nXHJcblxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxzZWN0aW9uPlxyXG4gICAgICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJmaXJzdC1saW5lXCI+eyBmaXJzdF9saW5lIH08L2Rpdj5cclxuICAgICAgICAgICAgICAgIDxIZWFkZXJzIG1lc3NhZ2U9e2Zsb3cucmVxdWVzdH0vPlxyXG4gICAgICAgICAgICAgICAgPGhyLz5cclxuICAgICAgICAgICAgICAgIHtjb250ZW50fVxyXG4gICAgICAgICAgICA8L3NlY3Rpb24+XHJcbiAgICAgICAgKTtcclxuICAgIH1cclxufSk7XHJcblxyXG52YXIgRmxvd0RldGFpbFJlc3BvbnNlID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XHJcbiAgICAgICAgdmFyIGZpcnN0X2xpbmUgPSBbXHJcbiAgICAgICAgICAgIFwiSFRUUC9cIiArIGZsb3cucmVzcG9uc2UuaHR0cHZlcnNpb24uam9pbihcIi5cIiksXHJcbiAgICAgICAgICAgIGZsb3cucmVzcG9uc2UuY29kZSxcclxuICAgICAgICAgICAgZmxvdy5yZXNwb25zZS5tc2dcclxuICAgICAgICBdLmpvaW4oXCIgXCIpO1xyXG4gICAgICAgIHZhciBjb250ZW50ID0gbnVsbDtcclxuICAgICAgICBpZiAoZmxvdy5yZXNwb25zZS5jb250ZW50TGVuZ3RoID4gMCkge1xyXG4gICAgICAgICAgICBjb250ZW50ID0gXCJSZXNwb25zZSBDb250ZW50IFNpemU6IFwiICsgdG9wdXRpbHMuZm9ybWF0U2l6ZShmbG93LnJlc3BvbnNlLmNvbnRlbnRMZW5ndGgpO1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIGNvbnRlbnQgPSA8ZGl2IGNsYXNzTmFtZT1cImFsZXJ0IGFsZXJ0LWluZm9cIj5ObyBDb250ZW50PC9kaXY+O1xyXG4gICAgICAgIH1cclxuXHJcbiAgICAgICAgLy9UT0RPOiBTdHlsaW5nXHJcblxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxzZWN0aW9uPlxyXG4gICAgICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJmaXJzdC1saW5lXCI+eyBmaXJzdF9saW5lIH08L2Rpdj5cclxuICAgICAgICAgICAgICAgIDxIZWFkZXJzIG1lc3NhZ2U9e2Zsb3cucmVzcG9uc2V9Lz5cclxuICAgICAgICAgICAgICAgIDxoci8+XHJcbiAgICAgICAgICAgICAgICB7Y29udGVudH1cclxuICAgICAgICAgICAgPC9zZWN0aW9uPlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIEZsb3dEZXRhaWxFcnJvciA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxzZWN0aW9uPlxyXG4gICAgICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJhbGVydCBhbGVydC13YXJuaW5nXCI+XHJcbiAgICAgICAgICAgICAgICB7Zmxvdy5lcnJvci5tc2d9XHJcbiAgICAgICAgICAgICAgICAgICAgPGRpdj5cclxuICAgICAgICAgICAgICAgICAgICAgICAgPHNtYWxsPnsgdG9wdXRpbHMuZm9ybWF0VGltZVN0YW1wKGZsb3cuZXJyb3IudGltZXN0YW1wKSB9PC9zbWFsbD5cclxuICAgICAgICAgICAgICAgICAgICA8L2Rpdj5cclxuICAgICAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICAgICA8L3NlY3Rpb24+XHJcbiAgICAgICAgKTtcclxuICAgIH1cclxufSk7XHJcblxyXG52YXIgVGltZVN0YW1wID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcblxyXG4gICAgICAgIGlmICghdGhpcy5wcm9wcy50KSB7XHJcbiAgICAgICAgICAgIC8vc2hvdWxkIGJlIHJldHVybiBudWxsLCBidXQgdGhhdCB0cmlnZ2VycyBhIFJlYWN0IGJ1Zy5cclxuICAgICAgICAgICAgcmV0dXJuIDx0cj48L3RyPjtcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIHZhciB0cyA9IHRvcHV0aWxzLmZvcm1hdFRpbWVTdGFtcCh0aGlzLnByb3BzLnQpO1xyXG5cclxuICAgICAgICB2YXIgZGVsdGE7XHJcbiAgICAgICAgaWYgKHRoaXMucHJvcHMuZGVsdGFUbykge1xyXG4gICAgICAgICAgICBkZWx0YSA9IHRvcHV0aWxzLmZvcm1hdFRpbWVEZWx0YSgxMDAwICogKHRoaXMucHJvcHMudCAtIHRoaXMucHJvcHMuZGVsdGFUbykpO1xyXG4gICAgICAgICAgICBkZWx0YSA9IDxzcGFuIGNsYXNzTmFtZT1cInRleHQtbXV0ZWRcIj57XCIoXCIgKyBkZWx0YSArIFwiKVwifTwvc3Bhbj47XHJcbiAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgZGVsdGEgPSBudWxsO1xyXG4gICAgICAgIH1cclxuXHJcbiAgICAgICAgcmV0dXJuIDx0cj5cclxuICAgICAgICAgICAgPHRkPnt0aGlzLnByb3BzLnRpdGxlICsgXCI6XCJ9PC90ZD5cclxuICAgICAgICAgICAgPHRkPnt0c30ge2RlbHRhfTwvdGQ+XHJcbiAgICAgICAgPC90cj47XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIENvbm5lY3Rpb25JbmZvID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG5cclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBjb25uID0gdGhpcy5wcm9wcy5jb25uO1xyXG4gICAgICAgIHZhciBhZGRyZXNzID0gY29ubi5hZGRyZXNzLmFkZHJlc3Muam9pbihcIjpcIik7XHJcblxyXG4gICAgICAgIHZhciBzbmkgPSA8dHIga2V5PVwic25pXCI+PC90cj47IC8vc2hvdWxkIGJlIG51bGwsIGJ1dCB0aGF0IHRyaWdnZXJzIGEgUmVhY3QgYnVnLlxyXG4gICAgICAgIGlmIChjb25uLnNuaSkge1xyXG4gICAgICAgICAgICBzbmkgPSA8dHIga2V5PVwic25pXCI+XHJcbiAgICAgICAgICAgICAgICA8dGQ+XHJcbiAgICAgICAgICAgICAgICAgICAgPGFiYnIgdGl0bGU9XCJUTFMgU2VydmVyIE5hbWUgSW5kaWNhdGlvblwiPlRMUyBTTkk6PC9hYmJyPlxyXG4gICAgICAgICAgICAgICAgPC90ZD5cclxuICAgICAgICAgICAgICAgIDx0ZD57Y29ubi5zbml9PC90ZD5cclxuICAgICAgICAgICAgPC90cj47XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDx0YWJsZSBjbGFzc05hbWU9XCJjb25uZWN0aW9uLXRhYmxlXCI+XHJcbiAgICAgICAgICAgICAgICA8dGJvZHk+XHJcbiAgICAgICAgICAgICAgICAgICAgPHRyIGtleT1cImFkZHJlc3NcIj5cclxuICAgICAgICAgICAgICAgICAgICAgICAgPHRkPkFkZHJlc3M6PC90ZD5cclxuICAgICAgICAgICAgICAgICAgICAgICAgPHRkPnthZGRyZXNzfTwvdGQ+XHJcbiAgICAgICAgICAgICAgICAgICAgPC90cj5cclxuICAgICAgICAgICAgICAgICAgICB7c25pfVxyXG4gICAgICAgICAgICAgICAgPC90Ym9keT5cclxuICAgICAgICAgICAgPC90YWJsZT5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbnZhciBDZXJ0aWZpY2F0ZUluZm8gPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAvL1RPRE86IFdlIHNob3VsZCBmZXRjaCBodW1hbi1yZWFkYWJsZSBjZXJ0aWZpY2F0ZSByZXByZXNlbnRhdGlvblxyXG4gICAgICAgIC8vIGZyb20gdGhlIHNlcnZlclxyXG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xyXG4gICAgICAgIHZhciBjbGllbnRfY29ubiA9IGZsb3cuY2xpZW50X2Nvbm47XHJcbiAgICAgICAgdmFyIHNlcnZlcl9jb25uID0gZmxvdy5zZXJ2ZXJfY29ubjtcclxuXHJcbiAgICAgICAgdmFyIHByZVN0eWxlID0ge21heEhlaWdodDogMTAwfTtcclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8ZGl2PlxyXG4gICAgICAgICAgICB7Y2xpZW50X2Nvbm4uY2VydCA/IDxoND5DbGllbnQgQ2VydGlmaWNhdGU8L2g0PiA6IG51bGx9XHJcbiAgICAgICAgICAgIHtjbGllbnRfY29ubi5jZXJ0ID8gPHByZSBzdHlsZT17cHJlU3R5bGV9PntjbGllbnRfY29ubi5jZXJ0fTwvcHJlPiA6IG51bGx9XHJcblxyXG4gICAgICAgICAgICB7c2VydmVyX2Nvbm4uY2VydCA/IDxoND5TZXJ2ZXIgQ2VydGlmaWNhdGU8L2g0PiA6IG51bGx9XHJcbiAgICAgICAgICAgIHtzZXJ2ZXJfY29ubi5jZXJ0ID8gPHByZSBzdHlsZT17cHJlU3R5bGV9PntzZXJ2ZXJfY29ubi5jZXJ0fTwvcHJlPiA6IG51bGx9XHJcbiAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIFRpbWluZyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xyXG4gICAgICAgIHZhciBzYyA9IGZsb3cuc2VydmVyX2Nvbm47XHJcbiAgICAgICAgdmFyIGNjID0gZmxvdy5jbGllbnRfY29ubjtcclxuICAgICAgICB2YXIgcmVxID0gZmxvdy5yZXF1ZXN0O1xyXG4gICAgICAgIHZhciByZXNwID0gZmxvdy5yZXNwb25zZTtcclxuXHJcbiAgICAgICAgdmFyIHRpbWVzdGFtcHMgPSBbXHJcbiAgICAgICAgICAgIHtcclxuICAgICAgICAgICAgICAgIHRpdGxlOiBcIlNlcnZlciBjb25uLiBpbml0aWF0ZWRcIixcclxuICAgICAgICAgICAgICAgIHQ6IHNjLnRpbWVzdGFtcF9zdGFydCxcclxuICAgICAgICAgICAgICAgIGRlbHRhVG86IHJlcS50aW1lc3RhbXBfc3RhcnRcclxuICAgICAgICAgICAgfSwge1xyXG4gICAgICAgICAgICAgICAgdGl0bGU6IFwiU2VydmVyIGNvbm4uIFRDUCBoYW5kc2hha2VcIixcclxuICAgICAgICAgICAgICAgIHQ6IHNjLnRpbWVzdGFtcF90Y3Bfc2V0dXAsXHJcbiAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XHJcbiAgICAgICAgICAgIH0sIHtcclxuICAgICAgICAgICAgICAgIHRpdGxlOiBcIlNlcnZlciBjb25uLiBTU0wgaGFuZHNoYWtlXCIsXHJcbiAgICAgICAgICAgICAgICB0OiBzYy50aW1lc3RhbXBfc3NsX3NldHVwLFxyXG4gICAgICAgICAgICAgICAgZGVsdGFUbzogcmVxLnRpbWVzdGFtcF9zdGFydFxyXG4gICAgICAgICAgICB9LCB7XHJcbiAgICAgICAgICAgICAgICB0aXRsZTogXCJDbGllbnQgY29ubi4gZXN0YWJsaXNoZWRcIixcclxuICAgICAgICAgICAgICAgIHQ6IGNjLnRpbWVzdGFtcF9zdGFydCxcclxuICAgICAgICAgICAgICAgIGRlbHRhVG86IHJlcS50aW1lc3RhbXBfc3RhcnRcclxuICAgICAgICAgICAgfSwge1xyXG4gICAgICAgICAgICAgICAgdGl0bGU6IFwiQ2xpZW50IGNvbm4uIFNTTCBoYW5kc2hha2VcIixcclxuICAgICAgICAgICAgICAgIHQ6IGNjLnRpbWVzdGFtcF9zc2xfc2V0dXAsXHJcbiAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XHJcbiAgICAgICAgICAgIH0sIHtcclxuICAgICAgICAgICAgICAgIHRpdGxlOiBcIkZpcnN0IHJlcXVlc3QgYnl0ZVwiLFxyXG4gICAgICAgICAgICAgICAgdDogcmVxLnRpbWVzdGFtcF9zdGFydCxcclxuICAgICAgICAgICAgfSwge1xyXG4gICAgICAgICAgICAgICAgdGl0bGU6IFwiUmVxdWVzdCBjb21wbGV0ZVwiLFxyXG4gICAgICAgICAgICAgICAgdDogcmVxLnRpbWVzdGFtcF9lbmQsXHJcbiAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XHJcbiAgICAgICAgICAgIH1cclxuICAgICAgICBdO1xyXG5cclxuICAgICAgICBpZiAoZmxvdy5yZXNwb25zZSkge1xyXG4gICAgICAgICAgICB0aW1lc3RhbXBzLnB1c2goXHJcbiAgICAgICAgICAgICAgICB7XHJcbiAgICAgICAgICAgICAgICAgICAgdGl0bGU6IFwiRmlyc3QgcmVzcG9uc2UgYnl0ZVwiLFxyXG4gICAgICAgICAgICAgICAgICAgIHQ6IHJlc3AudGltZXN0YW1wX3N0YXJ0LFxyXG4gICAgICAgICAgICAgICAgICAgIGRlbHRhVG86IHJlcS50aW1lc3RhbXBfc3RhcnRcclxuICAgICAgICAgICAgICAgIH0sIHtcclxuICAgICAgICAgICAgICAgICAgICB0aXRsZTogXCJSZXNwb25zZSBjb21wbGV0ZVwiLFxyXG4gICAgICAgICAgICAgICAgICAgIHQ6IHJlc3AudGltZXN0YW1wX2VuZCxcclxuICAgICAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XHJcbiAgICAgICAgICAgICAgICB9XHJcbiAgICAgICAgICAgICk7XHJcbiAgICAgICAgfVxyXG5cclxuICAgICAgICAvL0FkZCB1bmlxdWUga2V5IGZvciBlYWNoIHJvdy5cclxuICAgICAgICB0aW1lc3RhbXBzLmZvckVhY2goZnVuY3Rpb24gKGUpIHtcclxuICAgICAgICAgICAgZS5rZXkgPSBlLnRpdGxlO1xyXG4gICAgICAgIH0pO1xyXG5cclxuICAgICAgICB0aW1lc3RhbXBzID0gXy5zb3J0QnkodGltZXN0YW1wcywgJ3QnKTtcclxuXHJcbiAgICAgICAgdmFyIHJvd3MgPSB0aW1lc3RhbXBzLm1hcChmdW5jdGlvbiAoZSkge1xyXG4gICAgICAgICAgICByZXR1cm4gPFRpbWVTdGFtcCB7Li4uZX0vPjtcclxuICAgICAgICB9KTtcclxuXHJcbiAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgPGRpdj5cclxuICAgICAgICAgICAgICAgIDxoND5UaW1pbmc8L2g0PlxyXG4gICAgICAgICAgICAgICAgPHRhYmxlIGNsYXNzTmFtZT1cInRpbWluZy10YWJsZVwiPlxyXG4gICAgICAgICAgICAgICAgICAgIDx0Ym9keT5cclxuICAgICAgICAgICAgICAgICAgICB7cm93c31cclxuICAgICAgICAgICAgICAgICAgICA8L3Rib2R5PlxyXG4gICAgICAgICAgICAgICAgPC90YWJsZT5cclxuICAgICAgICAgICAgPC9kaXY+XHJcbiAgICAgICAgKTtcclxuICAgIH1cclxufSk7XHJcblxyXG52YXIgRmxvd0RldGFpbENvbm5lY3Rpb25JbmZvID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XHJcbiAgICAgICAgdmFyIGNsaWVudF9jb25uID0gZmxvdy5jbGllbnRfY29ubjtcclxuICAgICAgICB2YXIgc2VydmVyX2Nvbm4gPSBmbG93LnNlcnZlcl9jb25uO1xyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxzZWN0aW9uPlxyXG5cclxuICAgICAgICAgICAgICAgIDxoND5DbGllbnQgQ29ubmVjdGlvbjwvaDQ+XHJcbiAgICAgICAgICAgICAgICA8Q29ubmVjdGlvbkluZm8gY29ubj17Y2xpZW50X2Nvbm59Lz5cclxuXHJcbiAgICAgICAgICAgICAgICA8aDQ+U2VydmVyIENvbm5lY3Rpb248L2g0PlxyXG4gICAgICAgICAgICAgICAgPENvbm5lY3Rpb25JbmZvIGNvbm49e3NlcnZlcl9jb25ufS8+XHJcblxyXG4gICAgICAgICAgICAgICAgPENlcnRpZmljYXRlSW5mbyBmbG93PXtmbG93fS8+XHJcblxyXG4gICAgICAgICAgICAgICAgPFRpbWluZyBmbG93PXtmbG93fS8+XHJcblxyXG4gICAgICAgICAgICA8L3NlY3Rpb24+XHJcbiAgICAgICAgKTtcclxuICAgIH1cclxufSk7XHJcblxyXG52YXIgYWxsVGFicyA9IHtcclxuICAgIHJlcXVlc3Q6IEZsb3dEZXRhaWxSZXF1ZXN0LFxyXG4gICAgcmVzcG9uc2U6IEZsb3dEZXRhaWxSZXNwb25zZSxcclxuICAgIGVycm9yOiBGbG93RGV0YWlsRXJyb3IsXHJcbiAgICBkZXRhaWxzOiBGbG93RGV0YWlsQ29ubmVjdGlvbkluZm9cclxufTtcclxuXHJcbnZhciBGbG93RGV0YWlsID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgbWl4aW5zOiBbY29tbW9uLlN0aWNreUhlYWRNaXhpbiwgY29tbW9uLk5hdmlnYXRpb24sIGNvbW1vbi5TdGF0ZV0sXHJcbiAgICBnZXRUYWJzOiBmdW5jdGlvbiAoZmxvdykge1xyXG4gICAgICAgIHZhciB0YWJzID0gW107XHJcbiAgICAgICAgW1wicmVxdWVzdFwiLCBcInJlc3BvbnNlXCIsIFwiZXJyb3JcIl0uZm9yRWFjaChmdW5jdGlvbiAoZSkge1xyXG4gICAgICAgICAgICBpZiAoZmxvd1tlXSkge1xyXG4gICAgICAgICAgICAgICAgdGFicy5wdXNoKGUpO1xyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgfSk7XHJcbiAgICAgICAgdGFicy5wdXNoKFwiZGV0YWlsc1wiKTtcclxuICAgICAgICByZXR1cm4gdGFicztcclxuICAgIH0sXHJcbiAgICBuZXh0VGFiOiBmdW5jdGlvbiAoaSkge1xyXG4gICAgICAgIHZhciB0YWJzID0gdGhpcy5nZXRUYWJzKHRoaXMucHJvcHMuZmxvdyk7XHJcbiAgICAgICAgdmFyIGN1cnJlbnRJbmRleCA9IHRhYnMuaW5kZXhPZih0aGlzLmdldFBhcmFtcygpLmRldGFpbFRhYik7XHJcbiAgICAgICAgLy8gSlMgbW9kdWxvIG9wZXJhdG9yIGRvZXNuJ3QgY29ycmVjdCBuZWdhdGl2ZSBudW1iZXJzLCBtYWtlIHN1cmUgdGhhdCB3ZSBhcmUgcG9zaXRpdmUuXHJcbiAgICAgICAgdmFyIG5leHRJbmRleCA9IChjdXJyZW50SW5kZXggKyBpICsgdGFicy5sZW5ndGgpICUgdGFicy5sZW5ndGg7XHJcbiAgICAgICAgdGhpcy5zZWxlY3RUYWIodGFic1tuZXh0SW5kZXhdKTtcclxuICAgIH0sXHJcbiAgICBzZWxlY3RUYWI6IGZ1bmN0aW9uIChwYW5lbCkge1xyXG4gICAgICAgIHRoaXMucmVwbGFjZVdpdGgoXHJcbiAgICAgICAgICAgIFwiZmxvd1wiLFxyXG4gICAgICAgICAgICB7XHJcbiAgICAgICAgICAgICAgICBmbG93SWQ6IHRoaXMuZ2V0UGFyYW1zKCkuZmxvd0lkLFxyXG4gICAgICAgICAgICAgICAgZGV0YWlsVGFiOiBwYW5lbFxyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgKTtcclxuICAgIH0sXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcclxuICAgICAgICB2YXIgdGFicyA9IHRoaXMuZ2V0VGFicyhmbG93KTtcclxuICAgICAgICB2YXIgYWN0aXZlID0gdGhpcy5nZXRQYXJhbXMoKS5kZXRhaWxUYWI7XHJcblxyXG4gICAgICAgIGlmICghXy5jb250YWlucyh0YWJzLCBhY3RpdmUpKSB7XHJcbiAgICAgICAgICAgIGlmIChhY3RpdmUgPT09IFwicmVzcG9uc2VcIiAmJiBmbG93LmVycm9yKSB7XHJcbiAgICAgICAgICAgICAgICBhY3RpdmUgPSBcImVycm9yXCI7XHJcbiAgICAgICAgICAgIH0gZWxzZSBpZiAoYWN0aXZlID09PSBcImVycm9yXCIgJiYgZmxvdy5yZXNwb25zZSkge1xyXG4gICAgICAgICAgICAgICAgYWN0aXZlID0gXCJyZXNwb25zZVwiO1xyXG4gICAgICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICAgICAgYWN0aXZlID0gdGFic1swXTtcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICB0aGlzLnNlbGVjdFRhYihhY3RpdmUpO1xyXG4gICAgICAgIH1cclxuXHJcbiAgICAgICAgdmFyIFRhYiA9IGFsbFRhYnNbYWN0aXZlXTtcclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cImZsb3ctZGV0YWlsXCIgb25TY3JvbGw9e3RoaXMuYWRqdXN0SGVhZH0+XHJcbiAgICAgICAgICAgICAgICA8Rmxvd0RldGFpbE5hdiByZWY9XCJoZWFkXCJcclxuICAgICAgICAgICAgICAgICAgICBmbG93PXtmbG93fVxyXG4gICAgICAgICAgICAgICAgICAgIHRhYnM9e3RhYnN9XHJcbiAgICAgICAgICAgICAgICAgICAgYWN0aXZlPXthY3RpdmV9XHJcbiAgICAgICAgICAgICAgICAgICAgc2VsZWN0VGFiPXt0aGlzLnNlbGVjdFRhYn0vPlxyXG4gICAgICAgICAgICAgICAgPFRhYiBmbG93PXtmbG93fS8+XHJcbiAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxubW9kdWxlLmV4cG9ydHMgPSB7XHJcbiAgICBGbG93RGV0YWlsOiBGbG93RGV0YWlsXHJcbn07IiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xyXG52YXIgZmxvd3V0aWxzID0gcmVxdWlyZShcIi4uL2Zsb3cvdXRpbHMuanNcIik7XHJcbnZhciB1dGlscyA9IHJlcXVpcmUoXCIuLi91dGlscy5qc1wiKTtcclxuXHJcbnZhciBUTFNDb2x1bW4gPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICBzdGF0aWNzOiB7XHJcbiAgICAgICAgcmVuZGVyVGl0bGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAgICAgcmV0dXJuIDx0aCBrZXk9XCJ0bHNcIiBjbGFzc05hbWU9XCJjb2wtdGxzXCI+PC90aD47XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xyXG4gICAgICAgIHZhciBzc2wgPSAoZmxvdy5yZXF1ZXN0LnNjaGVtZSA9PSBcImh0dHBzXCIpO1xyXG4gICAgICAgIHZhciBjbGFzc2VzO1xyXG4gICAgICAgIGlmIChzc2wpIHtcclxuICAgICAgICAgICAgY2xhc3NlcyA9IFwiY29sLXRscyBjb2wtdGxzLWh0dHBzXCI7XHJcbiAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgY2xhc3NlcyA9IFwiY29sLXRscyBjb2wtdGxzLWh0dHBcIjtcclxuICAgICAgICB9XHJcbiAgICAgICAgcmV0dXJuIDx0ZCBjbGFzc05hbWU9e2NsYXNzZXN9PjwvdGQ+O1xyXG4gICAgfVxyXG59KTtcclxuXHJcblxyXG52YXIgSWNvbkNvbHVtbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHN0YXRpY3M6IHtcclxuICAgICAgICByZW5kZXJUaXRsZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgICAgICByZXR1cm4gPHRoIGtleT1cImljb25cIiBjbGFzc05hbWU9XCJjb2wtaWNvblwiPjwvdGg+O1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcclxuXHJcbiAgICAgICAgdmFyIGljb247XHJcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UpIHtcclxuICAgICAgICAgICAgdmFyIGNvbnRlbnRUeXBlID0gZmxvd3V0aWxzLlJlc3BvbnNlVXRpbHMuZ2V0Q29udGVudFR5cGUoZmxvdy5yZXNwb25zZSk7XHJcblxyXG4gICAgICAgICAgICAvL1RPRE86IFdlIHNob3VsZCBhc3NpZ24gYSB0eXBlIHRvIHRoZSBmbG93IHNvbWV3aGVyZSBlbHNlLlxyXG4gICAgICAgICAgICBpZiAoZmxvdy5yZXNwb25zZS5jb2RlID09IDMwNCkge1xyXG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1ub3QtbW9kaWZpZWRcIjtcclxuICAgICAgICAgICAgfSBlbHNlIGlmICgzMDAgPD0gZmxvdy5yZXNwb25zZS5jb2RlICYmIGZsb3cucmVzcG9uc2UuY29kZSA8IDQwMCkge1xyXG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1yZWRpcmVjdFwiO1xyXG4gICAgICAgICAgICB9IGVsc2UgaWYgKGNvbnRlbnRUeXBlICYmIGNvbnRlbnRUeXBlLmluZGV4T2YoXCJpbWFnZVwiKSA+PSAwKSB7XHJcbiAgICAgICAgICAgICAgICBpY29uID0gXCJyZXNvdXJjZS1pY29uLWltYWdlXCI7XHJcbiAgICAgICAgICAgIH0gZWxzZSBpZiAoY29udGVudFR5cGUgJiYgY29udGVudFR5cGUuaW5kZXhPZihcImphdmFzY3JpcHRcIikgPj0gMCkge1xyXG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1qc1wiO1xyXG4gICAgICAgICAgICB9IGVsc2UgaWYgKGNvbnRlbnRUeXBlICYmIGNvbnRlbnRUeXBlLmluZGV4T2YoXCJjc3NcIikgPj0gMCkge1xyXG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1jc3NcIjtcclxuICAgICAgICAgICAgfSBlbHNlIGlmIChjb250ZW50VHlwZSAmJiBjb250ZW50VHlwZS5pbmRleE9mKFwiaHRtbFwiKSA+PSAwKSB7XHJcbiAgICAgICAgICAgICAgICBpY29uID0gXCJyZXNvdXJjZS1pY29uLWRvY3VtZW50XCI7XHJcbiAgICAgICAgICAgIH1cclxuICAgICAgICB9XHJcbiAgICAgICAgaWYgKCFpY29uKSB7XHJcbiAgICAgICAgICAgIGljb24gPSBcInJlc291cmNlLWljb24tcGxhaW5cIjtcclxuICAgICAgICB9XHJcblxyXG5cclxuICAgICAgICBpY29uICs9IFwiIHJlc291cmNlLWljb25cIjtcclxuICAgICAgICByZXR1cm4gPHRkIGNsYXNzTmFtZT1cImNvbC1pY29uXCI+XHJcbiAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPXtpY29ufT48L2Rpdj5cclxuICAgICAgICA8L3RkPjtcclxuICAgIH1cclxufSk7XHJcblxyXG52YXIgUGF0aENvbHVtbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHN0YXRpY3M6IHtcclxuICAgICAgICByZW5kZXJUaXRsZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgICAgICByZXR1cm4gPHRoIGtleT1cInBhdGhcIiBjbGFzc05hbWU9XCJjb2wtcGF0aFwiPlBhdGg8L3RoPjtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XHJcbiAgICAgICAgcmV0dXJuIDx0ZCBjbGFzc05hbWU9XCJjb2wtcGF0aFwiPlxyXG4gICAgICAgICAgICB7Zmxvdy5yZXF1ZXN0LmlzX3JlcGxheSA/IDxpIGNsYXNzTmFtZT1cImZhIGZhLWZ3IGZhLXJlcGVhdCBwdWxsLXJpZ2h0XCI+PC9pPiA6IG51bGx9XHJcbiAgICAgICAgICAgIHtmbG93LmludGVyY2VwdGVkID8gPGkgY2xhc3NOYW1lPVwiZmEgZmEtZncgZmEtcGF1c2UgcHVsbC1yaWdodFwiPjwvaT4gOiBudWxsfVxyXG4gICAgICAgICAgICB7Zmxvdy5yZXF1ZXN0LnNjaGVtZSArIFwiOi8vXCIgKyBmbG93LnJlcXVlc3QuaG9zdCArIGZsb3cucmVxdWVzdC5wYXRofVxyXG4gICAgICAgIDwvdGQ+O1xyXG4gICAgfVxyXG59KTtcclxuXHJcblxyXG52YXIgTWV0aG9kQ29sdW1uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgc3RhdGljczoge1xyXG4gICAgICAgIHJlbmRlclRpdGxlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgICAgIHJldHVybiA8dGgga2V5PVwibWV0aG9kXCIgY2xhc3NOYW1lPVwiY29sLW1ldGhvZFwiPk1ldGhvZDwvdGg+O1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcclxuICAgICAgICByZXR1cm4gPHRkIGNsYXNzTmFtZT1cImNvbC1tZXRob2RcIj57Zmxvdy5yZXF1ZXN0Lm1ldGhvZH08L3RkPjtcclxuICAgIH1cclxufSk7XHJcblxyXG5cclxudmFyIFN0YXR1c0NvbHVtbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHN0YXRpY3M6IHtcclxuICAgICAgICByZW5kZXJUaXRsZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgICAgICByZXR1cm4gPHRoIGtleT1cInN0YXR1c1wiIGNsYXNzTmFtZT1cImNvbC1zdGF0dXNcIj5TdGF0dXM8L3RoPjtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XHJcbiAgICAgICAgdmFyIHN0YXR1cztcclxuICAgICAgICBpZiAoZmxvdy5yZXNwb25zZSkge1xyXG4gICAgICAgICAgICBzdGF0dXMgPSBmbG93LnJlc3BvbnNlLmNvZGU7XHJcbiAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgc3RhdHVzID0gbnVsbDtcclxuICAgICAgICB9XHJcbiAgICAgICAgcmV0dXJuIDx0ZCBjbGFzc05hbWU9XCJjb2wtc3RhdHVzXCI+e3N0YXR1c308L3RkPjtcclxuICAgIH1cclxufSk7XHJcblxyXG5cclxudmFyIFNpemVDb2x1bW4gPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICBzdGF0aWNzOiB7XHJcbiAgICAgICAgcmVuZGVyVGl0bGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAgICAgcmV0dXJuIDx0aCBrZXk9XCJzaXplXCIgY2xhc3NOYW1lPVwiY29sLXNpemVcIj5TaXplPC90aD47XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xyXG5cclxuICAgICAgICB2YXIgdG90YWwgPSBmbG93LnJlcXVlc3QuY29udGVudExlbmd0aDtcclxuICAgICAgICBpZiAoZmxvdy5yZXNwb25zZSkge1xyXG4gICAgICAgICAgICB0b3RhbCArPSBmbG93LnJlc3BvbnNlLmNvbnRlbnRMZW5ndGggfHwgMDtcclxuICAgICAgICB9XHJcbiAgICAgICAgdmFyIHNpemUgPSB1dGlscy5mb3JtYXRTaXplKHRvdGFsKTtcclxuICAgICAgICByZXR1cm4gPHRkIGNsYXNzTmFtZT1cImNvbC1zaXplXCI+e3NpemV9PC90ZD47XHJcbiAgICB9XHJcbn0pO1xyXG5cclxuXHJcbnZhciBUaW1lQ29sdW1uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgc3RhdGljczoge1xyXG4gICAgICAgIHJlbmRlclRpdGxlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgICAgIHJldHVybiA8dGgga2V5PVwidGltZVwiIGNsYXNzTmFtZT1cImNvbC10aW1lXCI+VGltZTwvdGg+O1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcclxuICAgICAgICB2YXIgdGltZTtcclxuICAgICAgICBpZiAoZmxvdy5yZXNwb25zZSkge1xyXG4gICAgICAgICAgICB0aW1lID0gdXRpbHMuZm9ybWF0VGltZURlbHRhKDEwMDAgKiAoZmxvdy5yZXNwb25zZS50aW1lc3RhbXBfZW5kIC0gZmxvdy5yZXF1ZXN0LnRpbWVzdGFtcF9zdGFydCkpO1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIHRpbWUgPSBcIi4uLlwiO1xyXG4gICAgICAgIH1cclxuICAgICAgICByZXR1cm4gPHRkIGNsYXNzTmFtZT1cImNvbC10aW1lXCI+e3RpbWV9PC90ZD47XHJcbiAgICB9XHJcbn0pO1xyXG5cclxuXHJcbnZhciBhbGxfY29sdW1ucyA9IFtcclxuICAgIFRMU0NvbHVtbixcclxuICAgIEljb25Db2x1bW4sXHJcbiAgICBQYXRoQ29sdW1uLFxyXG4gICAgTWV0aG9kQ29sdW1uLFxyXG4gICAgU3RhdHVzQ29sdW1uLFxyXG4gICAgU2l6ZUNvbHVtbixcclxuICAgIFRpbWVDb2x1bW5dO1xyXG5cclxuXHJcbm1vZHVsZS5leHBvcnRzID0gYWxsX2NvbHVtbnM7XHJcblxyXG5cclxuIiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xyXG52YXIgY29tbW9uID0gcmVxdWlyZShcIi4vY29tbW9uLmpzXCIpO1xyXG52YXIgVmlydHVhbFNjcm9sbE1peGluID0gcmVxdWlyZShcIi4vdmlydHVhbHNjcm9sbC5qc1wiKTtcclxudmFyIGZsb3d0YWJsZV9jb2x1bW5zID0gcmVxdWlyZShcIi4vZmxvd3RhYmxlLWNvbHVtbnMuanNcIik7XHJcblxyXG52YXIgRmxvd1JvdyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xyXG4gICAgICAgIHZhciBjb2x1bW5zID0gdGhpcy5wcm9wcy5jb2x1bW5zLm1hcChmdW5jdGlvbiAoQ29sdW1uKSB7XHJcbiAgICAgICAgICAgIHJldHVybiA8Q29sdW1uIGtleT17Q29sdW1uLmRpc3BsYXlOYW1lfSBmbG93PXtmbG93fS8+O1xyXG4gICAgICAgIH0uYmluZCh0aGlzKSk7XHJcbiAgICAgICAgdmFyIGNsYXNzTmFtZSA9IFwiXCI7XHJcbiAgICAgICAgaWYgKHRoaXMucHJvcHMuc2VsZWN0ZWQpIHtcclxuICAgICAgICAgICAgY2xhc3NOYW1lICs9IFwiIHNlbGVjdGVkXCI7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIGlmICh0aGlzLnByb3BzLmhpZ2hsaWdodGVkKSB7XHJcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcIiBoaWdobGlnaHRlZFwiO1xyXG4gICAgICAgIH1cclxuICAgICAgICBpZiAoZmxvdy5pbnRlcmNlcHRlZCkge1xyXG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCIgaW50ZXJjZXB0ZWRcIjtcclxuICAgICAgICB9XHJcbiAgICAgICAgaWYgKGZsb3cucmVxdWVzdCkge1xyXG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCIgaGFzLXJlcXVlc3RcIjtcclxuICAgICAgICB9XHJcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UpIHtcclxuICAgICAgICAgICAgY2xhc3NOYW1lICs9IFwiIGhhcy1yZXNwb25zZVwiO1xyXG4gICAgICAgIH1cclxuXHJcbiAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgPHRyIGNsYXNzTmFtZT17Y2xhc3NOYW1lfSBvbkNsaWNrPXt0aGlzLnByb3BzLnNlbGVjdEZsb3cuYmluZChudWxsLCBmbG93KX0+XHJcbiAgICAgICAgICAgICAgICB7Y29sdW1uc31cclxuICAgICAgICAgICAgPC90cj4pO1xyXG4gICAgfSxcclxuICAgIHNob3VsZENvbXBvbmVudFVwZGF0ZTogZnVuY3Rpb24gKG5leHRQcm9wcykge1xyXG4gICAgICAgIHJldHVybiB0cnVlO1xyXG4gICAgICAgIC8vIEZ1cnRoZXIgb3B0aW1pemF0aW9uIGNvdWxkIGJlIGRvbmUgaGVyZVxyXG4gICAgICAgIC8vIGJ5IGNhbGxpbmcgZm9yY2VVcGRhdGUgb24gZmxvdyB1cGRhdGVzLCBzZWxlY3Rpb24gY2hhbmdlcyBhbmQgY29sdW1uIGNoYW5nZXMuXHJcbiAgICAgICAgLy9yZXR1cm4gKFxyXG4gICAgICAgIC8vKHRoaXMucHJvcHMuY29sdW1ucy5sZW5ndGggIT09IG5leHRQcm9wcy5jb2x1bW5zLmxlbmd0aCkgfHxcclxuICAgICAgICAvLyh0aGlzLnByb3BzLnNlbGVjdGVkICE9PSBuZXh0UHJvcHMuc2VsZWN0ZWQpXHJcbiAgICAgICAgLy8pO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbnZhciBGbG93VGFibGVIZWFkID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGNvbHVtbnMgPSB0aGlzLnByb3BzLmNvbHVtbnMubWFwKGZ1bmN0aW9uIChjb2x1bW4pIHtcclxuICAgICAgICAgICAgcmV0dXJuIGNvbHVtbi5yZW5kZXJUaXRsZSgpO1xyXG4gICAgICAgIH0uYmluZCh0aGlzKSk7XHJcbiAgICAgICAgcmV0dXJuIDx0aGVhZD5cclxuICAgICAgICAgICAgPHRyPntjb2x1bW5zfTwvdHI+XHJcbiAgICAgICAgPC90aGVhZD47XHJcbiAgICB9XHJcbn0pO1xyXG5cclxuXHJcbnZhciBST1dfSEVJR0hUID0gMzI7XHJcblxyXG52YXIgRmxvd1RhYmxlID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgbWl4aW5zOiBbY29tbW9uLlN0aWNreUhlYWRNaXhpbiwgY29tbW9uLkF1dG9TY3JvbGxNaXhpbiwgVmlydHVhbFNjcm9sbE1peGluXSxcclxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHJldHVybiB7XHJcbiAgICAgICAgICAgIGNvbHVtbnM6IGZsb3d0YWJsZV9jb2x1bW5zXHJcbiAgICAgICAgfTtcclxuICAgIH0sXHJcbiAgICBjb21wb25lbnRXaWxsTW91bnQ6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICBpZiAodGhpcy5wcm9wcy52aWV3KSB7XHJcbiAgICAgICAgICAgIHRoaXMucHJvcHMudmlldy5hZGRMaXN0ZW5lcihcImFkZFwiLCB0aGlzLm9uQ2hhbmdlKTtcclxuICAgICAgICAgICAgdGhpcy5wcm9wcy52aWV3LmFkZExpc3RlbmVyKFwidXBkYXRlXCIsIHRoaXMub25DaGFuZ2UpO1xyXG4gICAgICAgICAgICB0aGlzLnByb3BzLnZpZXcuYWRkTGlzdGVuZXIoXCJyZW1vdmVcIiwgdGhpcy5vbkNoYW5nZSk7XHJcbiAgICAgICAgICAgIHRoaXMucHJvcHMudmlldy5hZGRMaXN0ZW5lcihcInJlY2FsY3VsYXRlXCIsIHRoaXMub25DaGFuZ2UpO1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICBjb21wb25lbnRXaWxsUmVjZWl2ZVByb3BzOiBmdW5jdGlvbiAobmV4dFByb3BzKSB7XHJcbiAgICAgICAgaWYgKG5leHRQcm9wcy52aWV3ICE9PSB0aGlzLnByb3BzLnZpZXcpIHtcclxuICAgICAgICAgICAgaWYgKHRoaXMucHJvcHMudmlldykge1xyXG4gICAgICAgICAgICAgICAgdGhpcy5wcm9wcy52aWV3LnJlbW92ZUxpc3RlbmVyKFwiYWRkXCIpO1xyXG4gICAgICAgICAgICAgICAgdGhpcy5wcm9wcy52aWV3LnJlbW92ZUxpc3RlbmVyKFwidXBkYXRlXCIpO1xyXG4gICAgICAgICAgICAgICAgdGhpcy5wcm9wcy52aWV3LnJlbW92ZUxpc3RlbmVyKFwicmVtb3ZlXCIpO1xyXG4gICAgICAgICAgICAgICAgdGhpcy5wcm9wcy52aWV3LnJlbW92ZUxpc3RlbmVyKFwicmVjYWxjdWxhdGVcIik7XHJcbiAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgbmV4dFByb3BzLnZpZXcuYWRkTGlzdGVuZXIoXCJhZGRcIiwgdGhpcy5vbkNoYW5nZSk7XHJcbiAgICAgICAgICAgIG5leHRQcm9wcy52aWV3LmFkZExpc3RlbmVyKFwidXBkYXRlXCIsIHRoaXMub25DaGFuZ2UpO1xyXG4gICAgICAgICAgICBuZXh0UHJvcHMudmlldy5hZGRMaXN0ZW5lcihcInJlbW92ZVwiLCB0aGlzLm9uQ2hhbmdlKTtcclxuICAgICAgICAgICAgbmV4dFByb3BzLnZpZXcuYWRkTGlzdGVuZXIoXCJyZWNhbGN1bGF0ZVwiLCB0aGlzLm9uQ2hhbmdlKTtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgZ2V0RGVmYXVsdFByb3BzOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgcmV0dXJuIHtcclxuICAgICAgICAgICAgcm93SGVpZ2h0OiBST1dfSEVJR0hUXHJcbiAgICAgICAgfTtcclxuICAgIH0sXHJcbiAgICBvblNjcm9sbEZsb3dUYWJsZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMuYWRqdXN0SGVhZCgpO1xyXG4gICAgICAgIHRoaXMub25TY3JvbGwoKTtcclxuICAgIH0sXHJcbiAgICBvbkNoYW5nZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMuZm9yY2VVcGRhdGUoKTtcclxuICAgIH0sXHJcbiAgICBzY3JvbGxJbnRvVmlldzogZnVuY3Rpb24gKGZsb3cpIHtcclxuICAgICAgICB0aGlzLnNjcm9sbFJvd0ludG9WaWV3KFxyXG4gICAgICAgICAgICB0aGlzLnByb3BzLnZpZXcuaW5kZXgoZmxvdyksXHJcbiAgICAgICAgICAgIHRoaXMucmVmcy5ib2R5LmdldERPTU5vZGUoKS5vZmZzZXRUb3BcclxuICAgICAgICApO1xyXG4gICAgfSxcclxuICAgIHJlbmRlclJvdzogZnVuY3Rpb24gKGZsb3cpIHtcclxuICAgICAgICB2YXIgc2VsZWN0ZWQgPSAoZmxvdyA9PT0gdGhpcy5wcm9wcy5zZWxlY3RlZCk7XHJcbiAgICAgICAgdmFyIGhpZ2hsaWdodGVkID1cclxuICAgICAgICAgICAgKFxyXG4gICAgICAgICAgICB0aGlzLnByb3BzLnZpZXcuX2hpZ2hsaWdodCAmJlxyXG4gICAgICAgICAgICB0aGlzLnByb3BzLnZpZXcuX2hpZ2hsaWdodFtmbG93LmlkXVxyXG4gICAgICAgICAgICApO1xyXG5cclxuICAgICAgICByZXR1cm4gPEZsb3dSb3cga2V5PXtmbG93LmlkfVxyXG4gICAgICAgICAgICByZWY9e2Zsb3cuaWR9XHJcbiAgICAgICAgICAgIGZsb3c9e2Zsb3d9XHJcbiAgICAgICAgICAgIGNvbHVtbnM9e3RoaXMuc3RhdGUuY29sdW1uc31cclxuICAgICAgICAgICAgc2VsZWN0ZWQ9e3NlbGVjdGVkfVxyXG4gICAgICAgICAgICBoaWdobGlnaHRlZD17aGlnaGxpZ2h0ZWR9XHJcbiAgICAgICAgICAgIHNlbGVjdEZsb3c9e3RoaXMucHJvcHMuc2VsZWN0Rmxvd31cclxuICAgICAgICAvPjtcclxuICAgIH0sXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAvL2NvbnNvbGUubG9nKFwicmVuZGVyIGZsb3d0YWJsZVwiLCB0aGlzLnN0YXRlLnN0YXJ0LCB0aGlzLnN0YXRlLnN0b3AsIHRoaXMucHJvcHMuc2VsZWN0ZWQpO1xyXG4gICAgICAgIHZhciBmbG93cyA9IHRoaXMucHJvcHMudmlldyA/IHRoaXMucHJvcHMudmlldy5saXN0IDogW107XHJcblxyXG4gICAgICAgIHZhciByb3dzID0gdGhpcy5yZW5kZXJSb3dzKGZsb3dzKTtcclxuXHJcbiAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJmbG93LXRhYmxlXCIgb25TY3JvbGw9e3RoaXMub25TY3JvbGxGbG93VGFibGV9PlxyXG4gICAgICAgICAgICAgICAgPHRhYmxlPlxyXG4gICAgICAgICAgICAgICAgICAgIDxGbG93VGFibGVIZWFkIHJlZj1cImhlYWRcIlxyXG4gICAgICAgICAgICAgICAgICAgICAgICBjb2x1bW5zPXt0aGlzLnN0YXRlLmNvbHVtbnN9Lz5cclxuICAgICAgICAgICAgICAgICAgICA8dGJvZHkgcmVmPVwiYm9keVwiPlxyXG4gICAgICAgICAgICAgICAgICAgICAgICB7IHRoaXMuZ2V0UGxhY2Vob2xkZXJUb3AoZmxvd3MubGVuZ3RoKSB9XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIHtyb3dzfVxyXG4gICAgICAgICAgICAgICAgICAgICAgICB7IHRoaXMuZ2V0UGxhY2Vob2xkZXJCb3R0b20oZmxvd3MubGVuZ3RoKSB9XHJcbiAgICAgICAgICAgICAgICAgICAgPC90Ym9keT5cclxuICAgICAgICAgICAgICAgIDwvdGFibGU+XHJcbiAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxubW9kdWxlLmV4cG9ydHMgPSBGbG93VGFibGU7XHJcbiIsInZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcclxuXHJcbnZhciBGb290ZXIgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgbW9kZSA9IHRoaXMucHJvcHMuc2V0dGluZ3MubW9kZTtcclxuICAgICAgICB2YXIgaW50ZXJjZXB0ID0gdGhpcy5wcm9wcy5zZXR0aW5ncy5pbnRlcmNlcHQ7XHJcbiAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgPGZvb3Rlcj5cclxuICAgICAgICAgICAgICAgIHttb2RlICE9IFwicmVndWxhclwiID8gPHNwYW4gY2xhc3NOYW1lPVwibGFiZWwgbGFiZWwtc3VjY2Vzc1wiPnttb2RlfSBtb2RlPC9zcGFuPiA6IG51bGx9XHJcbiAgICAgICAgICAgICAgICAmbmJzcDtcclxuICAgICAgICAgICAgICAgIHtpbnRlcmNlcHQgPyA8c3BhbiBjbGFzc05hbWU9XCJsYWJlbCBsYWJlbC1zdWNjZXNzXCI+SW50ZXJjZXB0OiB7aW50ZXJjZXB0fTwvc3Bhbj4gOiBudWxsfVxyXG4gICAgICAgICAgICA8L2Zvb3Rlcj5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbm1vZHVsZS5leHBvcnRzID0gRm9vdGVyOyIsInZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcclxudmFyICQgPSByZXF1aXJlKFwianF1ZXJ5XCIpO1xyXG5cclxudmFyIEZpbHQgPSByZXF1aXJlKFwiLi4vZmlsdC9maWx0LmpzXCIpO1xyXG52YXIgdXRpbHMgPSByZXF1aXJlKFwiLi4vdXRpbHMuanNcIik7XHJcblxyXG52YXIgY29tbW9uID0gcmVxdWlyZShcIi4vY29tbW9uLmpzXCIpO1xyXG52YXIgYWN0aW9ucyA9IHJlcXVpcmUoXCIuLi9hY3Rpb25zLmpzXCIpO1xyXG5cclxudmFyIEZpbHRlckRvY3MgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICBzdGF0aWNzOiB7XHJcbiAgICAgICAgeGhyOiBmYWxzZSxcclxuICAgICAgICBkb2M6IGZhbHNlXHJcbiAgICB9LFxyXG4gICAgY29tcG9uZW50V2lsbE1vdW50OiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgaWYgKCFGaWx0ZXJEb2NzLmRvYykge1xyXG4gICAgICAgICAgICBGaWx0ZXJEb2NzLnhociA9ICQuZ2V0SlNPTihcIi9maWx0ZXItaGVscFwiKS5kb25lKGZ1bmN0aW9uIChkb2MpIHtcclxuICAgICAgICAgICAgICAgIEZpbHRlckRvY3MuZG9jID0gZG9jO1xyXG4gICAgICAgICAgICAgICAgRmlsdGVyRG9jcy54aHIgPSBmYWxzZTtcclxuICAgICAgICAgICAgfSk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIGlmIChGaWx0ZXJEb2NzLnhocikge1xyXG4gICAgICAgICAgICBGaWx0ZXJEb2NzLnhoci5kb25lKGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAgICAgICAgIHRoaXMuZm9yY2VVcGRhdGUoKTtcclxuICAgICAgICAgICAgfS5iaW5kKHRoaXMpKTtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgaWYgKCFGaWx0ZXJEb2NzLmRvYykge1xyXG4gICAgICAgICAgICByZXR1cm4gPGkgY2xhc3NOYW1lPVwiZmEgZmEtc3Bpbm5lciBmYS1zcGluXCI+PC9pPjtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICB2YXIgY29tbWFuZHMgPSBGaWx0ZXJEb2NzLmRvYy5jb21tYW5kcy5tYXAoZnVuY3Rpb24gKGMpIHtcclxuICAgICAgICAgICAgICAgIHJldHVybiA8dHI+XHJcbiAgICAgICAgICAgICAgICAgICAgPHRkPntjWzBdLnJlcGxhY2UoXCIgXCIsICdcXHUwMGEwJyl9PC90ZD5cclxuICAgICAgICAgICAgICAgICAgICA8dGQ+e2NbMV19PC90ZD5cclxuICAgICAgICAgICAgICAgIDwvdHI+O1xyXG4gICAgICAgICAgICB9KTtcclxuICAgICAgICAgICAgY29tbWFuZHMucHVzaCg8dHI+XHJcbiAgICAgICAgICAgICAgICA8dGQgY29sU3Bhbj1cIjJcIj5cclxuICAgICAgICAgICAgICAgICAgICA8YSBocmVmPVwiaHR0cHM6Ly9taXRtcHJveHkub3JnL2RvYy9mZWF0dXJlcy9maWx0ZXJzLmh0bWxcIlxyXG4gICAgICAgICAgICAgICAgICAgICAgICB0YXJnZXQ9XCJfYmxhbmtcIj5cclxuICAgICAgICAgICAgICAgICAgICAgICAgPGkgY2xhc3NOYW1lPVwiZmEgZmEtZXh0ZXJuYWwtbGlua1wiPjwvaT5cclxuICAgICAgICAgICAgICAgICAgICAmbmJzcDsgbWl0bXByb3h5IGRvY3M8L2E+XHJcbiAgICAgICAgICAgICAgICA8L3RkPlxyXG4gICAgICAgICAgICA8L3RyPik7XHJcbiAgICAgICAgICAgIHJldHVybiA8dGFibGUgY2xhc3NOYW1lPVwidGFibGUgdGFibGUtY29uZGVuc2VkXCI+XHJcbiAgICAgICAgICAgICAgICA8dGJvZHk+e2NvbW1hbmRzfTwvdGJvZHk+XHJcbiAgICAgICAgICAgIDwvdGFibGU+O1xyXG4gICAgICAgIH1cclxuICAgIH1cclxufSk7XHJcbnZhciBGaWx0ZXJJbnB1dCA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIC8vIENvbnNpZGVyIGJvdGggZm9jdXMgYW5kIG1vdXNlb3ZlciBmb3Igc2hvd2luZy9oaWRpbmcgdGhlIHRvb2x0aXAsXHJcbiAgICAgICAgLy8gYmVjYXVzZSBvbkJsdXIgb2YgdGhlIGlucHV0IGlzIHRyaWdnZXJlZCBiZWZvcmUgdGhlIGNsaWNrIG9uIHRoZSB0b29sdGlwXHJcbiAgICAgICAgLy8gZmluYWxpemVkLCBoaWRpbmcgdGhlIHRvb2x0aXAganVzdCBhcyB0aGUgdXNlciBjbGlja3Mgb24gaXQuXHJcbiAgICAgICAgcmV0dXJuIHtcclxuICAgICAgICAgICAgdmFsdWU6IHRoaXMucHJvcHMudmFsdWUsXHJcbiAgICAgICAgICAgIGZvY3VzOiBmYWxzZSxcclxuICAgICAgICAgICAgbW91c2Vmb2N1czogZmFsc2VcclxuICAgICAgICB9O1xyXG4gICAgfSxcclxuICAgIGNvbXBvbmVudFdpbGxSZWNlaXZlUHJvcHM6IGZ1bmN0aW9uIChuZXh0UHJvcHMpIHtcclxuICAgICAgICB0aGlzLnNldFN0YXRlKHt2YWx1ZTogbmV4dFByb3BzLnZhbHVlfSk7XHJcbiAgICB9LFxyXG4gICAgb25DaGFuZ2U6IGZ1bmN0aW9uIChlKSB7XHJcbiAgICAgICAgdmFyIG5leHRWYWx1ZSA9IGUudGFyZ2V0LnZhbHVlO1xyXG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe1xyXG4gICAgICAgICAgICB2YWx1ZTogbmV4dFZhbHVlXHJcbiAgICAgICAgfSk7XHJcbiAgICAgICAgLy8gT25seSBwcm9wYWdhdGUgdmFsaWQgZmlsdGVycyB1cHdhcmRzLlxyXG4gICAgICAgIGlmICh0aGlzLmlzVmFsaWQobmV4dFZhbHVlKSkge1xyXG4gICAgICAgICAgICB0aGlzLnByb3BzLm9uQ2hhbmdlKG5leHRWYWx1ZSk7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIGlzVmFsaWQ6IGZ1bmN0aW9uIChmaWx0KSB7XHJcbiAgICAgICAgdHJ5IHtcclxuICAgICAgICAgICAgRmlsdC5wYXJzZShmaWx0IHx8IHRoaXMuc3RhdGUudmFsdWUpO1xyXG4gICAgICAgICAgICByZXR1cm4gdHJ1ZTtcclxuICAgICAgICB9IGNhdGNoIChlKSB7XHJcbiAgICAgICAgICAgIHJldHVybiBmYWxzZTtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgZ2V0RGVzYzogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBkZXNjO1xyXG4gICAgICAgIHRyeSB7XHJcbiAgICAgICAgICAgIGRlc2MgPSBGaWx0LnBhcnNlKHRoaXMuc3RhdGUudmFsdWUpLmRlc2M7XHJcbiAgICAgICAgfSBjYXRjaCAoZSkge1xyXG4gICAgICAgICAgICBkZXNjID0gXCJcIiArIGU7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIGlmIChkZXNjICE9PSBcInRydWVcIikge1xyXG4gICAgICAgICAgICByZXR1cm4gZGVzYztcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICAgICAgPEZpbHRlckRvY3MvPlxyXG4gICAgICAgICAgICApO1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICBvbkZvY3VzOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7Zm9jdXM6IHRydWV9KTtcclxuICAgIH0sXHJcbiAgICBvbkJsdXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLnNldFN0YXRlKHtmb2N1czogZmFsc2V9KTtcclxuICAgIH0sXHJcbiAgICBvbk1vdXNlRW50ZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLnNldFN0YXRlKHttb3VzZWZvY3VzOiB0cnVlfSk7XHJcbiAgICB9LFxyXG4gICAgb25Nb3VzZUxlYXZlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7bW91c2Vmb2N1czogZmFsc2V9KTtcclxuICAgIH0sXHJcbiAgICBvbktleURvd246IGZ1bmN0aW9uIChlKSB7XHJcbiAgICAgICAgaWYgKGUua2V5Q29kZSA9PT0gdXRpbHMuS2V5LkVTQyB8fCBlLmtleUNvZGUgPT09IHV0aWxzLktleS5FTlRFUikge1xyXG4gICAgICAgICAgICB0aGlzLmJsdXIoKTtcclxuICAgICAgICAgICAgLy8gSWYgY2xvc2VkIHVzaW5nIEVTQy9FTlRFUiwgaGlkZSB0aGUgdG9vbHRpcC5cclxuICAgICAgICAgICAgdGhpcy5zZXRTdGF0ZSh7bW91c2Vmb2N1czogZmFsc2V9KTtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgYmx1cjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMucmVmcy5pbnB1dC5nZXRET01Ob2RlKCkuYmx1cigpO1xyXG4gICAgfSxcclxuICAgIGZvY3VzOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdGhpcy5yZWZzLmlucHV0LmdldERPTU5vZGUoKS5zZWxlY3QoKTtcclxuICAgIH0sXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgaXNWYWxpZCA9IHRoaXMuaXNWYWxpZCgpO1xyXG4gICAgICAgIHZhciBpY29uID0gXCJmYSBmYS1mdyBmYS1cIiArIHRoaXMucHJvcHMudHlwZTtcclxuICAgICAgICB2YXIgZ3JvdXBDbGFzc05hbWUgPSBcImZpbHRlci1pbnB1dCBpbnB1dC1ncm91cFwiICsgKGlzVmFsaWQgPyBcIlwiIDogXCIgaGFzLWVycm9yXCIpO1xyXG5cclxuICAgICAgICB2YXIgcG9wb3ZlcjtcclxuICAgICAgICBpZiAodGhpcy5zdGF0ZS5mb2N1cyB8fCB0aGlzLnN0YXRlLm1vdXNlZm9jdXMpIHtcclxuICAgICAgICAgICAgcG9wb3ZlciA9IChcclxuICAgICAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPVwicG9wb3ZlciBib3R0b21cIiBvbk1vdXNlRW50ZXI9e3RoaXMub25Nb3VzZUVudGVyfSBvbk1vdXNlTGVhdmU9e3RoaXMub25Nb3VzZUxlYXZlfT5cclxuICAgICAgICAgICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cImFycm93XCI+PC9kaXY+XHJcbiAgICAgICAgICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJwb3BvdmVyLWNvbnRlbnRcIj5cclxuICAgICAgICAgICAgICAgICAgICB7dGhpcy5nZXREZXNjKCl9XHJcbiAgICAgICAgICAgICAgICAgICAgPC9kaXY+XHJcbiAgICAgICAgICAgICAgICA8L2Rpdj5cclxuICAgICAgICAgICAgKTtcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPXtncm91cENsYXNzTmFtZX0+XHJcbiAgICAgICAgICAgICAgICA8c3BhbiBjbGFzc05hbWU9XCJpbnB1dC1ncm91cC1hZGRvblwiPlxyXG4gICAgICAgICAgICAgICAgICAgIDxpIGNsYXNzTmFtZT17aWNvbn0gc3R5bGU9e3tjb2xvcjogdGhpcy5wcm9wcy5jb2xvcn19PjwvaT5cclxuICAgICAgICAgICAgICAgIDwvc3Bhbj5cclxuICAgICAgICAgICAgICAgIDxpbnB1dCB0eXBlPVwidGV4dFwiIHBsYWNlaG9sZGVyPXt0aGlzLnByb3BzLnBsYWNlaG9sZGVyfSBjbGFzc05hbWU9XCJmb3JtLWNvbnRyb2xcIlxyXG4gICAgICAgICAgICAgICAgICAgIHJlZj1cImlucHV0XCJcclxuICAgICAgICAgICAgICAgICAgICBvbkNoYW5nZT17dGhpcy5vbkNoYW5nZX1cclxuICAgICAgICAgICAgICAgICAgICBvbkZvY3VzPXt0aGlzLm9uRm9jdXN9XHJcbiAgICAgICAgICAgICAgICAgICAgb25CbHVyPXt0aGlzLm9uQmx1cn1cclxuICAgICAgICAgICAgICAgICAgICBvbktleURvd249e3RoaXMub25LZXlEb3dufVxyXG4gICAgICAgICAgICAgICAgICAgIHZhbHVlPXt0aGlzLnN0YXRlLnZhbHVlfS8+XHJcbiAgICAgICAgICAgICAgICB7cG9wb3Zlcn1cclxuICAgICAgICAgICAgPC9kaXY+XHJcbiAgICAgICAgKTtcclxuICAgIH1cclxufSk7XHJcblxyXG52YXIgTWFpbk1lbnUgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICBtaXhpbnM6IFtjb21tb24uTmF2aWdhdGlvbiwgY29tbW9uLlN0YXRlXSxcclxuICAgIHN0YXRpY3M6IHtcclxuICAgICAgICB0aXRsZTogXCJTdGFydFwiLFxyXG4gICAgICAgIHJvdXRlOiBcImZsb3dzXCJcclxuICAgIH0sXHJcbiAgICBvbkZpbHRlckNoYW5nZTogZnVuY3Rpb24gKHZhbCkge1xyXG4gICAgICAgIHZhciBkID0ge307XHJcbiAgICAgICAgZFtRdWVyeS5GSUxURVJdID0gdmFsO1xyXG4gICAgICAgIHRoaXMuc2V0UXVlcnkoZCk7XHJcbiAgICB9LFxyXG4gICAgb25IaWdobGlnaHRDaGFuZ2U6IGZ1bmN0aW9uICh2YWwpIHtcclxuICAgICAgICB2YXIgZCA9IHt9O1xyXG4gICAgICAgIGRbUXVlcnkuSElHSExJR0hUXSA9IHZhbDtcclxuICAgICAgICB0aGlzLnNldFF1ZXJ5KGQpO1xyXG4gICAgfSxcclxuICAgIG9uSW50ZXJjZXB0Q2hhbmdlOiBmdW5jdGlvbiAodmFsKSB7XHJcbiAgICAgICAgU2V0dGluZ3NBY3Rpb25zLnVwZGF0ZSh7aW50ZXJjZXB0OiB2YWx9KTtcclxuICAgIH0sXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZmlsdGVyID0gdGhpcy5nZXRRdWVyeSgpW1F1ZXJ5LkZJTFRFUl0gfHwgXCJcIjtcclxuICAgICAgICB2YXIgaGlnaGxpZ2h0ID0gdGhpcy5nZXRRdWVyeSgpW1F1ZXJ5LkhJR0hMSUdIVF0gfHwgXCJcIjtcclxuICAgICAgICB2YXIgaW50ZXJjZXB0ID0gdGhpcy5wcm9wcy5zZXR0aW5ncy5pbnRlcmNlcHQgfHwgXCJcIjtcclxuXHJcbiAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgPGRpdj5cclxuICAgICAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPVwibWVudS1yb3dcIj5cclxuICAgICAgICAgICAgICAgICAgICA8RmlsdGVySW5wdXRcclxuICAgICAgICAgICAgICAgICAgICAgICAgcGxhY2Vob2xkZXI9XCJGaWx0ZXJcIlxyXG4gICAgICAgICAgICAgICAgICAgICAgICB0eXBlPVwiZmlsdGVyXCJcclxuICAgICAgICAgICAgICAgICAgICAgICAgY29sb3I9XCJibGFja1wiXHJcbiAgICAgICAgICAgICAgICAgICAgICAgIHZhbHVlPXtmaWx0ZXJ9XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIG9uQ2hhbmdlPXt0aGlzLm9uRmlsdGVyQ2hhbmdlfSAvPlxyXG4gICAgICAgICAgICAgICAgICAgIDxGaWx0ZXJJbnB1dFxyXG4gICAgICAgICAgICAgICAgICAgICAgICBwbGFjZWhvbGRlcj1cIkhpZ2hsaWdodFwiXHJcbiAgICAgICAgICAgICAgICAgICAgICAgIHR5cGU9XCJ0YWdcIlxyXG4gICAgICAgICAgICAgICAgICAgICAgICBjb2xvcj1cImhzbCg0OCwgMTAwJSwgNTAlKVwiXHJcbiAgICAgICAgICAgICAgICAgICAgICAgIHZhbHVlPXtoaWdobGlnaHR9XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIG9uQ2hhbmdlPXt0aGlzLm9uSGlnaGxpZ2h0Q2hhbmdlfS8+XHJcbiAgICAgICAgICAgICAgICAgICAgPEZpbHRlcklucHV0XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIHBsYWNlaG9sZGVyPVwiSW50ZXJjZXB0XCJcclxuICAgICAgICAgICAgICAgICAgICAgICAgdHlwZT1cInBhdXNlXCJcclxuICAgICAgICAgICAgICAgICAgICAgICAgY29sb3I9XCJoc2woMjA4LCA1NiUsIDUzJSlcIlxyXG4gICAgICAgICAgICAgICAgICAgICAgICB2YWx1ZT17aW50ZXJjZXB0fVxyXG4gICAgICAgICAgICAgICAgICAgICAgICBvbkNoYW5nZT17dGhpcy5vbkludGVyY2VwdENoYW5nZX0vPlxyXG4gICAgICAgICAgICAgICAgPC9kaXY+XHJcbiAgICAgICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cImNsZWFyZml4XCI+PC9kaXY+XHJcbiAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxuXHJcbnZhciBWaWV3TWVudSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHN0YXRpY3M6IHtcclxuICAgICAgICB0aXRsZTogXCJWaWV3XCIsXHJcbiAgICAgICAgcm91dGU6IFwiZmxvd3NcIlxyXG4gICAgfSxcclxuICAgIG1peGluczogW2NvbW1vbi5OYXZpZ2F0aW9uLCBjb21tb24uU3RhdGVdLFxyXG4gICAgdG9nZ2xlRXZlbnRMb2c6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZCA9IHt9O1xyXG5cclxuICAgICAgICBpZiAodGhpcy5nZXRRdWVyeSgpW1F1ZXJ5LlNIT1dfRVZFTlRMT0ddKSB7XHJcbiAgICAgICAgICAgIGRbUXVlcnkuU0hPV19FVkVOVExPR10gPSB1bmRlZmluZWQ7XHJcbiAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgZFtRdWVyeS5TSE9XX0VWRU5UTE9HXSA9IFwidFwiOyAvLyBhbnkgbm9uLWZhbHNlIHZhbHVlIHdpbGwgZG8gaXQsIGtlZXAgaXQgc2hvcnRcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIHRoaXMuc2V0UXVlcnkoZCk7XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIHNob3dFdmVudExvZyA9IHRoaXMuZ2V0UXVlcnkoKVtRdWVyeS5TSE9XX0VWRU5UTE9HXTtcclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8ZGl2PlxyXG4gICAgICAgICAgICAgICAgPGJ1dHRvblxyXG4gICAgICAgICAgICAgICAgICAgIGNsYXNzTmFtZT17XCJidG4gXCIgKyAoc2hvd0V2ZW50TG9nID8gXCJidG4tcHJpbWFyeVwiIDogXCJidG4tZGVmYXVsdFwiKX1cclxuICAgICAgICAgICAgICAgICAgICBvbkNsaWNrPXt0aGlzLnRvZ2dsZUV2ZW50TG9nfT5cclxuICAgICAgICAgICAgICAgICAgICA8aSBjbGFzc05hbWU9XCJmYSBmYS1kYXRhYmFzZVwiPjwvaT5cclxuICAgICAgICAgICAgICAgICZuYnNwO1Nob3cgRXZlbnRsb2dcclxuICAgICAgICAgICAgICAgIDwvYnV0dG9uPlxyXG4gICAgICAgICAgICAgICAgPHNwYW4+IDwvc3Bhbj5cclxuICAgICAgICAgICAgPC9kaXY+XHJcbiAgICAgICAgKTtcclxuICAgIH1cclxufSk7XHJcblxyXG5cclxudmFyIFJlcG9ydHNNZW51ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgc3RhdGljczoge1xyXG4gICAgICAgIHRpdGxlOiBcIlZpc3VhbGl6YXRpb25cIixcclxuICAgICAgICByb3V0ZTogXCJyZXBvcnRzXCJcclxuICAgIH0sXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICByZXR1cm4gPGRpdj5SZXBvcnRzIE1lbnU8L2Rpdj47XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIEZpbGVNZW51ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgcmV0dXJuIHtcclxuICAgICAgICAgICAgc2hvd0ZpbGVNZW51OiBmYWxzZVxyXG4gICAgICAgIH07XHJcbiAgICB9LFxyXG4gICAgaGFuZGxlRmlsZUNsaWNrOiBmdW5jdGlvbiAoZSkge1xyXG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcclxuICAgICAgICBpZiAoIXRoaXMuc3RhdGUuc2hvd0ZpbGVNZW51KSB7XHJcbiAgICAgICAgICAgIHZhciBjbG9zZSA9IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAgICAgICAgIHRoaXMuc2V0U3RhdGUoe3Nob3dGaWxlTWVudTogZmFsc2V9KTtcclxuICAgICAgICAgICAgICAgIGRvY3VtZW50LnJlbW92ZUV2ZW50TGlzdGVuZXIoXCJjbGlja1wiLCBjbG9zZSk7XHJcbiAgICAgICAgICAgIH0uYmluZCh0aGlzKTtcclxuICAgICAgICAgICAgZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsIGNsb3NlKTtcclxuXHJcbiAgICAgICAgICAgIHRoaXMuc2V0U3RhdGUoe1xyXG4gICAgICAgICAgICAgICAgc2hvd0ZpbGVNZW51OiB0cnVlXHJcbiAgICAgICAgICAgIH0pO1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICBoYW5kbGVOZXdDbGljazogZnVuY3Rpb24gKGUpIHtcclxuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XHJcbiAgICAgICAgaWYgKGNvbmZpcm0oXCJEZWxldGUgYWxsIGZsb3dzP1wiKSkge1xyXG4gICAgICAgICAgICBhY3Rpb25zLkZsb3dBY3Rpb25zLmNsZWFyKCk7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIGhhbmRsZU9wZW5DbGljazogZnVuY3Rpb24gKGUpIHtcclxuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XHJcbiAgICAgICAgY29uc29sZS5lcnJvcihcInVuaW1wbGVtZW50ZWQ6IGhhbmRsZU9wZW5DbGlja1wiKTtcclxuICAgIH0sXHJcbiAgICBoYW5kbGVTYXZlQ2xpY2s6IGZ1bmN0aW9uIChlKSB7XHJcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xyXG4gICAgICAgIGNvbnNvbGUuZXJyb3IoXCJ1bmltcGxlbWVudGVkOiBoYW5kbGVTYXZlQ2xpY2tcIik7XHJcbiAgICB9LFxyXG4gICAgaGFuZGxlU2h1dGRvd25DbGljazogZnVuY3Rpb24gKGUpIHtcclxuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XHJcbiAgICAgICAgY29uc29sZS5lcnJvcihcInVuaW1wbGVtZW50ZWQ6IGhhbmRsZVNodXRkb3duQ2xpY2tcIik7XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGZpbGVNZW51Q2xhc3MgPSBcImRyb3Bkb3duIHB1bGwtbGVmdFwiICsgKHRoaXMuc3RhdGUuc2hvd0ZpbGVNZW51ID8gXCIgb3BlblwiIDogXCJcIik7XHJcblxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPXtmaWxlTWVudUNsYXNzfT5cclxuICAgICAgICAgICAgICAgIDxhIGhyZWY9XCIjXCIgY2xhc3NOYW1lPVwic3BlY2lhbFwiIG9uQ2xpY2s9e3RoaXMuaGFuZGxlRmlsZUNsaWNrfT4gbWl0bXByb3h5IDwvYT5cclxuICAgICAgICAgICAgICAgIDx1bCBjbGFzc05hbWU9XCJkcm9wZG93bi1tZW51XCIgcm9sZT1cIm1lbnVcIj5cclxuICAgICAgICAgICAgICAgICAgICA8bGk+XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIDxhIGhyZWY9XCIjXCIgb25DbGljaz17dGhpcy5oYW5kbGVOZXdDbGlja30+XHJcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICA8aSBjbGFzc05hbWU9XCJmYSBmYS1mdyBmYS1maWxlXCI+PC9pPlxyXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgTmV3XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIDwvYT5cclxuICAgICAgICAgICAgICAgICAgICA8L2xpPlxyXG4gICAgICAgICAgICAgICAgICAgIDxsaSByb2xlPVwicHJlc2VudGF0aW9uXCIgY2xhc3NOYW1lPVwiZGl2aWRlclwiPjwvbGk+XHJcbiAgICAgICAgICAgICAgICAgICAgPGxpPlxyXG4gICAgICAgICAgICAgICAgICAgICAgICA8YSBocmVmPVwiaHR0cDovL21pdG0uaXQvXCIgdGFyZ2V0PVwiX2JsYW5rXCI+XHJcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICA8aSBjbGFzc05hbWU9XCJmYSBmYS1mdyBmYS1leHRlcm5hbC1saW5rXCI+PC9pPlxyXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgSW5zdGFsbCBDZXJ0aWZpY2F0ZXMuLi5cclxuICAgICAgICAgICAgICAgICAgICAgICAgPC9hPlxyXG4gICAgICAgICAgICAgICAgICAgIDwvbGk+XHJcbiAgICAgICAgICAgICAgICB7LypcclxuICAgICAgICAgICAgICAgICA8bGk+XHJcbiAgICAgICAgICAgICAgICAgPGEgaHJlZj1cIiNcIiBvbkNsaWNrPXt0aGlzLmhhbmRsZU9wZW5DbGlja30+XHJcbiAgICAgICAgICAgICAgICAgPGkgY2xhc3NOYW1lPVwiZmEgZmEtZncgZmEtZm9sZGVyLW9wZW5cIj48L2k+XHJcbiAgICAgICAgICAgICAgICAgT3BlblxyXG4gICAgICAgICAgICAgICAgIDwvYT5cclxuICAgICAgICAgICAgICAgICA8L2xpPlxyXG4gICAgICAgICAgICAgICAgIDxsaT5cclxuICAgICAgICAgICAgICAgICA8YSBocmVmPVwiI1wiIG9uQ2xpY2s9e3RoaXMuaGFuZGxlU2F2ZUNsaWNrfT5cclxuICAgICAgICAgICAgICAgICA8aSBjbGFzc05hbWU9XCJmYSBmYS1mdyBmYS1zYXZlXCI+PC9pPlxyXG4gICAgICAgICAgICAgICAgIFNhdmVcclxuICAgICAgICAgICAgICAgICA8L2E+XHJcbiAgICAgICAgICAgICAgICAgPC9saT5cclxuICAgICAgICAgICAgICAgICA8bGkgcm9sZT1cInByZXNlbnRhdGlvblwiIGNsYXNzTmFtZT1cImRpdmlkZXJcIj48L2xpPlxyXG4gICAgICAgICAgICAgICAgIDxsaT5cclxuICAgICAgICAgICAgICAgICA8YSBocmVmPVwiI1wiIG9uQ2xpY2s9e3RoaXMuaGFuZGxlU2h1dGRvd25DbGlja30+XHJcbiAgICAgICAgICAgICAgICAgPGkgY2xhc3NOYW1lPVwiZmEgZmEtZncgZmEtcGx1Z1wiPjwvaT5cclxuICAgICAgICAgICAgICAgICBTaHV0ZG93blxyXG4gICAgICAgICAgICAgICAgIDwvYT5cclxuICAgICAgICAgICAgICAgICA8L2xpPlxyXG4gICAgICAgICAgICAgICAgICovfVxyXG4gICAgICAgICAgICAgICAgPC91bD5cclxuICAgICAgICAgICAgPC9kaXY+XHJcbiAgICAgICAgKTtcclxuICAgIH1cclxufSk7XHJcblxyXG5cclxudmFyIGhlYWRlcl9lbnRyaWVzID0gW01haW5NZW51LCBWaWV3TWVudSAvKiwgUmVwb3J0c01lbnUgKi9dO1xyXG5cclxuXHJcbnZhciBIZWFkZXIgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICBtaXhpbnM6IFtjb21tb24uTmF2aWdhdGlvbl0sXHJcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICByZXR1cm4ge1xyXG4gICAgICAgICAgICBhY3RpdmU6IGhlYWRlcl9lbnRyaWVzWzBdXHJcbiAgICAgICAgfTtcclxuICAgIH0sXHJcbiAgICBoYW5kbGVDbGljazogZnVuY3Rpb24gKGFjdGl2ZSwgZSkge1xyXG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcclxuICAgICAgICB0aGlzLnJlcGxhY2VXaXRoKGFjdGl2ZS5yb3V0ZSk7XHJcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7YWN0aXZlOiBhY3RpdmV9KTtcclxuICAgIH0sXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgaGVhZGVyID0gaGVhZGVyX2VudHJpZXMubWFwKGZ1bmN0aW9uIChlbnRyeSwgaSkge1xyXG4gICAgICAgICAgICB2YXIgY2xhc3NlcyA9IFJlYWN0LmFkZG9ucy5jbGFzc1NldCh7XHJcbiAgICAgICAgICAgICAgICBhY3RpdmU6IGVudHJ5ID09IHRoaXMuc3RhdGUuYWN0aXZlXHJcbiAgICAgICAgICAgIH0pO1xyXG4gICAgICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICAgICAgPGEga2V5PXtpfVxyXG4gICAgICAgICAgICAgICAgICAgIGhyZWY9XCIjXCJcclxuICAgICAgICAgICAgICAgICAgICBjbGFzc05hbWU9e2NsYXNzZXN9XHJcbiAgICAgICAgICAgICAgICAgICAgb25DbGljaz17dGhpcy5oYW5kbGVDbGljay5iaW5kKHRoaXMsIGVudHJ5KX1cclxuICAgICAgICAgICAgICAgID5cclxuICAgICAgICAgICAgICAgICAgICB7IGVudHJ5LnRpdGxlfVxyXG4gICAgICAgICAgICAgICAgPC9hPlxyXG4gICAgICAgICAgICApO1xyXG4gICAgICAgIH0uYmluZCh0aGlzKSk7XHJcblxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxoZWFkZXI+XHJcbiAgICAgICAgICAgICAgICA8bmF2IGNsYXNzTmFtZT1cIm5hdi10YWJzIG5hdi10YWJzLWxnXCI+XHJcbiAgICAgICAgICAgICAgICAgICAgPEZpbGVNZW51Lz5cclxuICAgICAgICAgICAgICAgICAgICB7aGVhZGVyfVxyXG4gICAgICAgICAgICAgICAgPC9uYXY+XHJcbiAgICAgICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cIm1lbnVcIj5cclxuICAgICAgICAgICAgICAgICAgICA8dGhpcy5zdGF0ZS5hY3RpdmUgc2V0dGluZ3M9e3RoaXMucHJvcHMuc2V0dGluZ3N9Lz5cclxuICAgICAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICAgICA8L2hlYWRlcj5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcblxyXG5tb2R1bGUuZXhwb3J0cyA9IHtcclxuICAgIEhlYWRlcjogSGVhZGVyXHJcbn0iLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XHJcblxyXG52YXIgY29tbW9uID0gcmVxdWlyZShcIi4vY29tbW9uLmpzXCIpO1xyXG52YXIgYWN0aW9ucyA9IHJlcXVpcmUoXCIuLi9hY3Rpb25zLmpzXCIpO1xyXG52YXIgdG9wdXRpbHMgPSByZXF1aXJlKFwiLi4vdXRpbHMuanNcIik7XHJcbnZhciB2aWV3cyA9IHJlcXVpcmUoXCIuLi9zdG9yZS92aWV3LmpzXCIpO1xyXG52YXIgRmlsdCA9IHJlcXVpcmUoXCIuLi9maWx0L2ZpbHQuanNcIik7XHJcbkZsb3dUYWJsZSA9IHJlcXVpcmUoXCIuL2Zsb3d0YWJsZS5qc1wiKTtcclxudmFyIGZsb3dkZXRhaWwgPSByZXF1aXJlKFwiLi9mbG93ZGV0YWlsLmpzXCIpO1xyXG5cclxuXHJcbnZhciBNYWluVmlldyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIG1peGluczogW2NvbW1vbi5OYXZpZ2F0aW9uLCBjb21tb24uU3RhdGVdLFxyXG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdGhpcy5vblF1ZXJ5Q2hhbmdlKFF1ZXJ5LkZJTFRFUiwgZnVuY3Rpb24gKCkge1xyXG4gICAgICAgICAgICB0aGlzLnN0YXRlLnZpZXcucmVjYWxjdWxhdGUodGhpcy5nZXRWaWV3RmlsdCgpLCB0aGlzLmdldFZpZXdTb3J0KCkpO1xyXG4gICAgICAgIH0uYmluZCh0aGlzKSk7XHJcbiAgICAgICAgdGhpcy5vblF1ZXJ5Q2hhbmdlKFF1ZXJ5LkhJR0hMSUdIVCwgZnVuY3Rpb24gKCkge1xyXG4gICAgICAgICAgICB0aGlzLnN0YXRlLnZpZXcucmVjYWxjdWxhdGUodGhpcy5nZXRWaWV3RmlsdCgpLCB0aGlzLmdldFZpZXdTb3J0KCkpO1xyXG4gICAgICAgIH0uYmluZCh0aGlzKSk7XHJcbiAgICAgICAgcmV0dXJuIHtcclxuICAgICAgICAgICAgZmxvd3M6IFtdXHJcbiAgICAgICAgfTtcclxuICAgIH0sXHJcbiAgICBnZXRWaWV3RmlsdDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRyeSB7XHJcbiAgICAgICAgICAgIHZhciBmaWx0ID0gRmlsdC5wYXJzZSh0aGlzLmdldFF1ZXJ5KClbUXVlcnkuRklMVEVSXSB8fCBcIlwiKTtcclxuICAgICAgICAgICAgdmFyIGhpZ2hsaWdodFN0ciA9IHRoaXMuZ2V0UXVlcnkoKVtRdWVyeS5ISUdITElHSFRdO1xyXG4gICAgICAgICAgICB2YXIgaGlnaGxpZ2h0ID0gaGlnaGxpZ2h0U3RyID8gRmlsdC5wYXJzZShoaWdobGlnaHRTdHIpIDogZmFsc2U7XHJcbiAgICAgICAgfSBjYXRjaCAoZSkge1xyXG4gICAgICAgICAgICBjb25zb2xlLmVycm9yKFwiRXJyb3Igd2hlbiBwcm9jZXNzaW5nIGZpbHRlcjogXCIgKyBlKTtcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIHJldHVybiBmdW5jdGlvbiBmaWx0ZXJfYW5kX2hpZ2hsaWdodChmbG93KSB7XHJcbiAgICAgICAgICAgIGlmICghdGhpcy5faGlnaGxpZ2h0KSB7XHJcbiAgICAgICAgICAgICAgICB0aGlzLl9oaWdobGlnaHQgPSB7fTtcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICB0aGlzLl9oaWdobGlnaHRbZmxvdy5pZF0gPSBoaWdobGlnaHQgJiYgaGlnaGxpZ2h0KGZsb3cpO1xyXG4gICAgICAgICAgICByZXR1cm4gZmlsdChmbG93KTtcclxuICAgICAgICB9O1xyXG4gICAgfSxcclxuICAgIGdldFZpZXdTb3J0OiBmdW5jdGlvbiAoKSB7XHJcbiAgICB9LFxyXG4gICAgY29tcG9uZW50V2lsbFJlY2VpdmVQcm9wczogZnVuY3Rpb24gKG5leHRQcm9wcykge1xyXG4gICAgICAgIGlmIChuZXh0UHJvcHMuZmxvd1N0b3JlICE9PSB0aGlzLnByb3BzLmZsb3dTdG9yZSkge1xyXG4gICAgICAgICAgICB0aGlzLmNsb3NlVmlldygpO1xyXG4gICAgICAgICAgICB0aGlzLm9wZW5WaWV3KG5leHRQcm9wcy5mbG93U3RvcmUpO1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICBvcGVuVmlldzogZnVuY3Rpb24gKHN0b3JlKSB7XHJcbiAgICAgICAgdmFyIHZpZXcgPSBuZXcgdmlld3MuU3RvcmVWaWV3KHN0b3JlLCB0aGlzLmdldFZpZXdGaWx0KCksIHRoaXMuZ2V0Vmlld1NvcnQoKSk7XHJcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7XHJcbiAgICAgICAgICAgIHZpZXc6IHZpZXdcclxuICAgICAgICB9KTtcclxuXHJcbiAgICAgICAgdmlldy5hZGRMaXN0ZW5lcihcInJlY2FsY3VsYXRlXCIsIHRoaXMub25SZWNhbGN1bGF0ZSk7XHJcbiAgICAgICAgdmlldy5hZGRMaXN0ZW5lcihcImFkZFwiLCB0aGlzLm9uVXBkYXRlKTtcclxuICAgICAgICB2aWV3LmFkZExpc3RlbmVyKFwidXBkYXRlXCIsIHRoaXMub25VcGRhdGUpO1xyXG4gICAgICAgIHZpZXcuYWRkTGlzdGVuZXIoXCJyZW1vdmVcIiwgdGhpcy5vblVwZGF0ZSk7XHJcbiAgICAgICAgdmlldy5hZGRMaXN0ZW5lcihcInJlbW92ZVwiLCB0aGlzLm9uUmVtb3ZlKTtcclxuICAgIH0sXHJcbiAgICBvblJlY2FsY3VsYXRlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdGhpcy5mb3JjZVVwZGF0ZSgpO1xyXG4gICAgICAgIHZhciBzZWxlY3RlZCA9IHRoaXMuZ2V0U2VsZWN0ZWQoKTtcclxuICAgICAgICBpZiAoc2VsZWN0ZWQpIHtcclxuICAgICAgICAgICAgdGhpcy5yZWZzLmZsb3dUYWJsZS5zY3JvbGxJbnRvVmlldyhzZWxlY3RlZCk7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIG9uVXBkYXRlOiBmdW5jdGlvbiAoZmxvdykge1xyXG4gICAgICAgIGlmIChmbG93LmlkID09PSB0aGlzLmdldFBhcmFtcygpLmZsb3dJZCkge1xyXG4gICAgICAgICAgICB0aGlzLmZvcmNlVXBkYXRlKCk7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIG9uUmVtb3ZlOiBmdW5jdGlvbiAoZmxvd19pZCwgaW5kZXgpIHtcclxuICAgICAgICBpZiAoZmxvd19pZCA9PT0gdGhpcy5nZXRQYXJhbXMoKS5mbG93SWQpIHtcclxuICAgICAgICAgICAgdmFyIGZsb3dfdG9fc2VsZWN0ID0gdGhpcy5zdGF0ZS52aWV3Lmxpc3RbTWF0aC5taW4oaW5kZXgsIHRoaXMuc3RhdGUudmlldy5saXN0Lmxlbmd0aCAtMSldO1xyXG4gICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3coZmxvd190b19zZWxlY3QpO1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICBjbG9zZVZpZXc6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLnN0YXRlLnZpZXcuY2xvc2UoKTtcclxuICAgIH0sXHJcbiAgICBjb21wb25lbnRXaWxsTW91bnQ6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLm9wZW5WaWV3KHRoaXMucHJvcHMuZmxvd1N0b3JlKTtcclxuICAgIH0sXHJcbiAgICBjb21wb25lbnRXaWxsVW5tb3VudDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMuY2xvc2VWaWV3KCk7XHJcbiAgICB9LFxyXG4gICAgc2VsZWN0RmxvdzogZnVuY3Rpb24gKGZsb3cpIHtcclxuICAgICAgICBpZiAoZmxvdykge1xyXG4gICAgICAgICAgICB0aGlzLnJlcGxhY2VXaXRoKFxyXG4gICAgICAgICAgICAgICAgXCJmbG93XCIsXHJcbiAgICAgICAgICAgICAgICB7XHJcbiAgICAgICAgICAgICAgICAgICAgZmxvd0lkOiBmbG93LmlkLFxyXG4gICAgICAgICAgICAgICAgICAgIGRldGFpbFRhYjogdGhpcy5nZXRQYXJhbXMoKS5kZXRhaWxUYWIgfHwgXCJyZXF1ZXN0XCJcclxuICAgICAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgKTtcclxuICAgICAgICAgICAgdGhpcy5yZWZzLmZsb3dUYWJsZS5zY3JvbGxJbnRvVmlldyhmbG93KTtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICB0aGlzLnJlcGxhY2VXaXRoKFwiZmxvd3NcIiwge30pO1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICBzZWxlY3RGbG93UmVsYXRpdmU6IGZ1bmN0aW9uIChzaGlmdCkge1xyXG4gICAgICAgIHZhciBmbG93cyA9IHRoaXMuc3RhdGUudmlldy5saXN0O1xyXG4gICAgICAgIHZhciBpbmRleDtcclxuICAgICAgICBpZiAoIXRoaXMuZ2V0UGFyYW1zKCkuZmxvd0lkKSB7XHJcbiAgICAgICAgICAgIGlmIChzaGlmdCA+IDApIHtcclxuICAgICAgICAgICAgICAgIGluZGV4ID0gZmxvd3MubGVuZ3RoIC0gMTtcclxuICAgICAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgICAgIGluZGV4ID0gMDtcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIHZhciBjdXJyRmxvd0lkID0gdGhpcy5nZXRQYXJhbXMoKS5mbG93SWQ7XHJcbiAgICAgICAgICAgIHZhciBpID0gZmxvd3MubGVuZ3RoO1xyXG4gICAgICAgICAgICB3aGlsZSAoaS0tKSB7XHJcbiAgICAgICAgICAgICAgICBpZiAoZmxvd3NbaV0uaWQgPT09IGN1cnJGbG93SWQpIHtcclxuICAgICAgICAgICAgICAgICAgICBpbmRleCA9IGk7XHJcbiAgICAgICAgICAgICAgICAgICAgYnJlYWs7XHJcbiAgICAgICAgICAgICAgICB9XHJcbiAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgaW5kZXggPSBNYXRoLm1pbihcclxuICAgICAgICAgICAgICAgIE1hdGgubWF4KDAsIGluZGV4ICsgc2hpZnQpLFxyXG4gICAgICAgICAgICAgICAgZmxvd3MubGVuZ3RoIC0gMSk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHRoaXMuc2VsZWN0RmxvdyhmbG93c1tpbmRleF0pO1xyXG4gICAgfSxcclxuICAgIG9uS2V5RG93bjogZnVuY3Rpb24gKGUpIHtcclxuICAgICAgICB2YXIgZmxvdyA9IHRoaXMuZ2V0U2VsZWN0ZWQoKTtcclxuICAgICAgICBpZiAoZS5jdHJsS2V5KSB7XHJcbiAgICAgICAgICAgIHJldHVybjtcclxuICAgICAgICB9XHJcbiAgICAgICAgc3dpdGNoIChlLmtleUNvZGUpIHtcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuSzpcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuVVA6XHJcbiAgICAgICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3dSZWxhdGl2ZSgtMSk7XHJcbiAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuSjpcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuRE9XTjpcclxuICAgICAgICAgICAgICAgIHRoaXMuc2VsZWN0Rmxvd1JlbGF0aXZlKCsxKTtcclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5TUEFDRTpcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuUEFHRV9ET1dOOlxyXG4gICAgICAgICAgICAgICAgdGhpcy5zZWxlY3RGbG93UmVsYXRpdmUoKzEwKTtcclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5QQUdFX1VQOlxyXG4gICAgICAgICAgICAgICAgdGhpcy5zZWxlY3RGbG93UmVsYXRpdmUoLTEwKTtcclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5FTkQ6XHJcbiAgICAgICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3dSZWxhdGl2ZSgrMWUxMCk7XHJcbiAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuSE9NRTpcclxuICAgICAgICAgICAgICAgIHRoaXMuc2VsZWN0Rmxvd1JlbGF0aXZlKC0xZTEwKTtcclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5FU0M6XHJcbiAgICAgICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3cobnVsbCk7XHJcbiAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuSDpcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuTEVGVDpcclxuICAgICAgICAgICAgICAgIGlmICh0aGlzLnJlZnMuZmxvd0RldGFpbHMpIHtcclxuICAgICAgICAgICAgICAgICAgICB0aGlzLnJlZnMuZmxvd0RldGFpbHMubmV4dFRhYigtMSk7XHJcbiAgICAgICAgICAgICAgICB9XHJcbiAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuTDpcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuVEFCOlxyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5SSUdIVDpcclxuICAgICAgICAgICAgICAgIGlmICh0aGlzLnJlZnMuZmxvd0RldGFpbHMpIHtcclxuICAgICAgICAgICAgICAgICAgICB0aGlzLnJlZnMuZmxvd0RldGFpbHMubmV4dFRhYigrMSk7XHJcbiAgICAgICAgICAgICAgICB9XHJcbiAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuQzpcclxuICAgICAgICAgICAgICAgIGlmIChlLnNoaWZ0S2V5KSB7XHJcbiAgICAgICAgICAgICAgICAgICAgYWN0aW9ucy5GbG93QWN0aW9ucy5jbGVhcigpO1xyXG4gICAgICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICAgICAgYnJlYWs7XHJcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LkQ6XHJcbiAgICAgICAgICAgICAgICBpZiAoZmxvdykge1xyXG4gICAgICAgICAgICAgICAgICAgIGlmIChlLnNoaWZ0S2V5KSB7XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIGFjdGlvbnMuRmxvd0FjdGlvbnMuZHVwbGljYXRlKGZsb3cpO1xyXG4gICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIGFjdGlvbnMuRmxvd0FjdGlvbnMuZGVsZXRlKGZsb3cpO1xyXG4gICAgICAgICAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5BOlxyXG4gICAgICAgICAgICAgICAgaWYgKGUuc2hpZnRLZXkpIHtcclxuICAgICAgICAgICAgICAgICAgICBhY3Rpb25zLkZsb3dBY3Rpb25zLmFjY2VwdF9hbGwoKTtcclxuICAgICAgICAgICAgICAgIH0gZWxzZSBpZiAoZmxvdyAmJiBmbG93LmludGVyY2VwdGVkKSB7XHJcbiAgICAgICAgICAgICAgICAgICAgYWN0aW9ucy5GbG93QWN0aW9ucy5hY2NlcHQoZmxvdyk7XHJcbiAgICAgICAgICAgICAgICB9XHJcbiAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuUjpcclxuICAgICAgICAgICAgICAgIGlmICghZS5zaGlmdEtleSAmJiBmbG93KSB7XHJcbiAgICAgICAgICAgICAgICAgICAgYWN0aW9ucy5GbG93QWN0aW9ucy5yZXBsYXkoZmxvdyk7XHJcbiAgICAgICAgICAgICAgICB9XHJcbiAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuVjpcclxuICAgICAgICAgICAgICAgIGlmKGUuc2hpZnRLZXkgJiYgZmxvdyAmJiBmbG93Lm1vZGlmaWVkKSB7XHJcbiAgICAgICAgICAgICAgICAgICAgYWN0aW9ucy5GbG93QWN0aW9ucy5yZXZlcnQoZmxvdyk7XHJcbiAgICAgICAgICAgICAgICB9XHJcbiAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgZGVmYXVsdDpcclxuICAgICAgICAgICAgICAgIGNvbnNvbGUuZGVidWcoXCJrZXlkb3duXCIsIGUua2V5Q29kZSk7XHJcbiAgICAgICAgICAgICAgICByZXR1cm47XHJcbiAgICAgICAgfVxyXG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcclxuICAgIH0sXHJcbiAgICBnZXRTZWxlY3RlZDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHJldHVybiB0aGlzLnByb3BzLmZsb3dTdG9yZS5nZXQodGhpcy5nZXRQYXJhbXMoKS5mbG93SWQpO1xyXG4gICAgfSxcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBzZWxlY3RlZCA9IHRoaXMuZ2V0U2VsZWN0ZWQoKTtcclxuXHJcbiAgICAgICAgdmFyIGRldGFpbHM7XHJcbiAgICAgICAgaWYgKHNlbGVjdGVkKSB7XHJcbiAgICAgICAgICAgIGRldGFpbHMgPSBbXHJcbiAgICAgICAgICAgICAgICA8Y29tbW9uLlNwbGl0dGVyIGtleT1cInNwbGl0dGVyXCIvPixcclxuICAgICAgICAgICAgICAgIDxmbG93ZGV0YWlsLkZsb3dEZXRhaWwga2V5PVwiZmxvd0RldGFpbHNcIiByZWY9XCJmbG93RGV0YWlsc1wiIGZsb3c9e3NlbGVjdGVkfS8+XHJcbiAgICAgICAgICAgIF07XHJcbiAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgZGV0YWlscyA9IG51bGw7XHJcbiAgICAgICAgfVxyXG5cclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cIm1haW4tdmlld1wiIG9uS2V5RG93bj17dGhpcy5vbktleURvd259IHRhYkluZGV4PVwiMFwiPlxyXG4gICAgICAgICAgICAgICAgPEZsb3dUYWJsZSByZWY9XCJmbG93VGFibGVcIlxyXG4gICAgICAgICAgICAgICAgICAgIHZpZXc9e3RoaXMuc3RhdGUudmlld31cclxuICAgICAgICAgICAgICAgICAgICBzZWxlY3RGbG93PXt0aGlzLnNlbGVjdEZsb3d9XHJcbiAgICAgICAgICAgICAgICAgICAgc2VsZWN0ZWQ9e3NlbGVjdGVkfSAvPlxyXG4gICAgICAgICAgICAgICAge2RldGFpbHN9XHJcbiAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxubW9kdWxlLmV4cG9ydHMgPSBNYWluVmlldztcclxuIiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xyXG52YXIgUmVhY3RSb3V0ZXIgPSByZXF1aXJlKFwicmVhY3Qtcm91dGVyXCIpO1xyXG52YXIgXyA9IHJlcXVpcmUoXCJsb2Rhc2hcIik7XHJcblxyXG52YXIgY29tbW9uID0gcmVxdWlyZShcIi4vY29tbW9uLmpzXCIpO1xyXG52YXIgTWFpblZpZXcgPSByZXF1aXJlKFwiLi9tYWludmlldy5qc1wiKTtcclxudmFyIEZvb3RlciA9IHJlcXVpcmUoXCIuL2Zvb3Rlci5qc1wiKTtcclxudmFyIGhlYWRlciA9IHJlcXVpcmUoXCIuL2hlYWRlci5qc1wiKTtcclxudmFyIEV2ZW50TG9nID0gcmVxdWlyZShcIi4vZXZlbnRsb2cuanNcIik7XHJcbnZhciBzdG9yZSA9IHJlcXVpcmUoXCIuLi9zdG9yZS9zdG9yZS5qc1wiKTtcclxuXHJcblxyXG4vL1RPRE86IE1vdmUgb3V0IG9mIGhlcmUsIGp1c3QgYSBzdHViLlxyXG52YXIgUmVwb3J0cyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHJldHVybiA8ZGl2PlJlcG9ydEVkaXRvcjwvZGl2PjtcclxuICAgIH1cclxufSk7XHJcblxyXG5cclxudmFyIFByb3h5QXBwTWFpbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIG1peGluczogW2NvbW1vbi5TdGF0ZV0sXHJcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZXZlbnRTdG9yZSA9IG5ldyBzdG9yZS5FdmVudExvZ1N0b3JlKCk7XHJcbiAgICAgICAgdmFyIGZsb3dTdG9yZSA9IG5ldyBzdG9yZS5GbG93U3RvcmUoKTtcclxuICAgICAgICB2YXIgc2V0dGluZ3MgPSBuZXcgc3RvcmUuU2V0dGluZ3NTdG9yZSgpO1xyXG5cclxuICAgICAgICAvLyBEZWZhdWx0IFNldHRpbmdzIGJlZm9yZSBmZXRjaFxyXG4gICAgICAgIF8uZXh0ZW5kKHNldHRpbmdzLmRpY3Qse1xyXG4gICAgICAgIH0pO1xyXG4gICAgICAgIHJldHVybiB7XHJcbiAgICAgICAgICAgIHNldHRpbmdzOiBzZXR0aW5ncyxcclxuICAgICAgICAgICAgZmxvd1N0b3JlOiBmbG93U3RvcmUsXHJcbiAgICAgICAgICAgIGV2ZW50U3RvcmU6IGV2ZW50U3RvcmVcclxuICAgICAgICB9O1xyXG4gICAgfSxcclxuICAgIGNvbXBvbmVudERpZE1vdW50OiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdGhpcy5zdGF0ZS5zZXR0aW5ncy5hZGRMaXN0ZW5lcihcInJlY2FsY3VsYXRlXCIsIHRoaXMub25TZXR0aW5nc0NoYW5nZSk7XHJcbiAgICAgICAgd2luZG93LmFwcCA9IHRoaXM7XHJcbiAgICB9LFxyXG4gICAgY29tcG9uZW50V2lsbFVubW91bnQ6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLnN0YXRlLnNldHRpbmdzLnJlbW92ZUxpc3RlbmVyKFwicmVjYWxjdWxhdGVcIiwgdGhpcy5vblNldHRpbmdzQ2hhbmdlKTtcclxuICAgIH0sXHJcbiAgICBvblNldHRpbmdzQ2hhbmdlOiBmdW5jdGlvbigpe1xyXG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe1xyXG4gICAgICAgICAgICBzZXR0aW5nczogdGhpcy5zdGF0ZS5zZXR0aW5nc1xyXG4gICAgICAgIH0pO1xyXG4gICAgfSxcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG5cclxuICAgICAgICB2YXIgZXZlbnRsb2c7XHJcbiAgICAgICAgaWYgKHRoaXMuZ2V0UXVlcnkoKVtRdWVyeS5TSE9XX0VWRU5UTE9HXSkge1xyXG4gICAgICAgICAgICBldmVudGxvZyA9IFtcclxuICAgICAgICAgICAgICAgIDxjb21tb24uU3BsaXR0ZXIga2V5PVwic3BsaXR0ZXJcIiBheGlzPVwieVwiLz4sXHJcbiAgICAgICAgICAgICAgICA8RXZlbnRMb2cga2V5PVwiZXZlbnRsb2dcIiBldmVudFN0b3JlPXt0aGlzLnN0YXRlLmV2ZW50U3RvcmV9Lz5cclxuICAgICAgICAgICAgXTtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICBldmVudGxvZyA9IG51bGw7XHJcbiAgICAgICAgfVxyXG5cclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8ZGl2IGlkPVwiY29udGFpbmVyXCI+XHJcbiAgICAgICAgICAgICAgICA8aGVhZGVyLkhlYWRlciBzZXR0aW5ncz17dGhpcy5zdGF0ZS5zZXR0aW5ncy5kaWN0fS8+XHJcbiAgICAgICAgICAgICAgICA8Um91dGVIYW5kbGVyIHNldHRpbmdzPXt0aGlzLnN0YXRlLnNldHRpbmdzLmRpY3R9IGZsb3dTdG9yZT17dGhpcy5zdGF0ZS5mbG93U3RvcmV9Lz5cclxuICAgICAgICAgICAgICAgIHtldmVudGxvZ31cclxuICAgICAgICAgICAgICAgIDxGb290ZXIgc2V0dGluZ3M9e3RoaXMuc3RhdGUuc2V0dGluZ3MuZGljdH0vPlxyXG4gICAgICAgICAgICA8L2Rpdj5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcblxyXG52YXIgUm91dGUgPSBSZWFjdFJvdXRlci5Sb3V0ZTtcclxudmFyIFJvdXRlSGFuZGxlciA9IFJlYWN0Um91dGVyLlJvdXRlSGFuZGxlcjtcclxudmFyIFJlZGlyZWN0ID0gUmVhY3RSb3V0ZXIuUmVkaXJlY3Q7XHJcbnZhciBEZWZhdWx0Um91dGUgPSBSZWFjdFJvdXRlci5EZWZhdWx0Um91dGU7XHJcbnZhciBOb3RGb3VuZFJvdXRlID0gUmVhY3RSb3V0ZXIuTm90Rm91bmRSb3V0ZTtcclxuXHJcblxyXG52YXIgcm91dGVzID0gKFxyXG4gICAgPFJvdXRlIHBhdGg9XCIvXCIgaGFuZGxlcj17UHJveHlBcHBNYWlufT5cclxuICAgICAgICA8Um91dGUgbmFtZT1cImZsb3dzXCIgcGF0aD1cImZsb3dzXCIgaGFuZGxlcj17TWFpblZpZXd9Lz5cclxuICAgICAgICA8Um91dGUgbmFtZT1cImZsb3dcIiBwYXRoPVwiZmxvd3MvOmZsb3dJZC86ZGV0YWlsVGFiXCIgaGFuZGxlcj17TWFpblZpZXd9Lz5cclxuICAgICAgICA8Um91dGUgbmFtZT1cInJlcG9ydHNcIiBoYW5kbGVyPXtSZXBvcnRzfS8+XHJcbiAgICAgICAgPFJlZGlyZWN0IHBhdGg9XCIvXCIgdG89XCJmbG93c1wiIC8+XHJcbiAgICA8L1JvdXRlPlxyXG4pO1xyXG5cclxubW9kdWxlLmV4cG9ydHMgPSB7XHJcbiAgICByb3V0ZXM6IHJvdXRlc1xyXG59O1xyXG5cclxuIiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xyXG5cclxudmFyIFZpcnR1YWxTY3JvbGxNaXhpbiA9IHtcclxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHJldHVybiB7XHJcbiAgICAgICAgICAgIHN0YXJ0OiAwLFxyXG4gICAgICAgICAgICBzdG9wOiAwXHJcbiAgICAgICAgfTtcclxuICAgIH0sXHJcbiAgICBjb21wb25lbnRXaWxsTW91bnQ6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICBpZiAoIXRoaXMucHJvcHMucm93SGVpZ2h0KSB7XHJcbiAgICAgICAgICAgIGNvbnNvbGUud2FybihcIlZpcnR1YWxTY3JvbGxNaXhpbjogTm8gcm93SGVpZ2h0IHNwZWNpZmllZFwiLCB0aGlzKTtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgZ2V0UGxhY2Vob2xkZXJUb3A6IGZ1bmN0aW9uICh0b3RhbCkge1xyXG4gICAgICAgIHZhciBUYWcgPSB0aGlzLnByb3BzLnBsYWNlaG9sZGVyVGFnTmFtZSB8fCBcInRyXCI7XHJcbiAgICAgICAgLy8gV2hlbiBhIGxhcmdlIHRydW5rIG9mIGVsZW1lbnRzIGlzIHJlbW92ZWQgZnJvbSB0aGUgYnV0dG9uLCBzdGFydCBtYXkgYmUgZmFyIG9mZiB0aGUgdmlld3BvcnQuXHJcbiAgICAgICAgLy8gVG8gbWFrZSB0aGlzIGlzc3VlIGxlc3Mgc2V2ZXJlLCBsaW1pdCB0aGUgdG9wIHBsYWNlaG9sZGVyIHRvIHRoZSB0b3RhbCBudW1iZXIgb2Ygcm93cy5cclxuICAgICAgICB2YXIgc3R5bGUgPSB7XHJcbiAgICAgICAgICAgIGhlaWdodDogTWF0aC5taW4odGhpcy5zdGF0ZS5zdGFydCwgdG90YWwpICogdGhpcy5wcm9wcy5yb3dIZWlnaHRcclxuICAgICAgICB9O1xyXG4gICAgICAgIHZhciBzcGFjZXIgPSA8VGFnIGtleT1cInBsYWNlaG9sZGVyLXRvcFwiIHN0eWxlPXtzdHlsZX0+PC9UYWc+O1xyXG5cclxuICAgICAgICBpZiAodGhpcy5zdGF0ZS5zdGFydCAlIDIgPT09IDEpIHtcclxuICAgICAgICAgICAgLy8gZml4IGV2ZW4vb2RkIHJvd3NcclxuICAgICAgICAgICAgcmV0dXJuIFtzcGFjZXIsIDxUYWcga2V5PVwicGxhY2Vob2xkZXItdG9wLTJcIj48L1RhZz5dO1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIHJldHVybiBzcGFjZXI7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIGdldFBsYWNlaG9sZGVyQm90dG9tOiBmdW5jdGlvbiAodG90YWwpIHtcclxuICAgICAgICB2YXIgVGFnID0gdGhpcy5wcm9wcy5wbGFjZWhvbGRlclRhZ05hbWUgfHwgXCJ0clwiO1xyXG4gICAgICAgIHZhciBzdHlsZSA9IHtcclxuICAgICAgICAgICAgaGVpZ2h0OiBNYXRoLm1heCgwLCB0b3RhbCAtIHRoaXMuc3RhdGUuc3RvcCkgKiB0aGlzLnByb3BzLnJvd0hlaWdodFxyXG4gICAgICAgIH07XHJcbiAgICAgICAgcmV0dXJuIDxUYWcga2V5PVwicGxhY2Vob2xkZXItYm90dG9tXCIgc3R5bGU9e3N0eWxlfT48L1RhZz47XHJcbiAgICB9LFxyXG4gICAgY29tcG9uZW50RGlkTW91bnQ6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLm9uU2Nyb2xsKCk7XHJcbiAgICAgICAgd2luZG93LmFkZEV2ZW50TGlzdGVuZXIoJ3Jlc2l6ZScsIHRoaXMub25TY3JvbGwpO1xyXG4gICAgfSxcclxuICAgIGNvbXBvbmVudFdpbGxVbm1vdW50OiBmdW5jdGlvbigpe1xyXG4gICAgICAgIHdpbmRvdy5yZW1vdmVFdmVudExpc3RlbmVyKCdyZXNpemUnLCB0aGlzLm9uU2Nyb2xsKTtcclxuICAgIH0sXHJcbiAgICBvblNjcm9sbDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciB2aWV3cG9ydCA9IHRoaXMuZ2V0RE9NTm9kZSgpO1xyXG4gICAgICAgIHZhciB0b3AgPSB2aWV3cG9ydC5zY3JvbGxUb3A7XHJcbiAgICAgICAgdmFyIGhlaWdodCA9IHZpZXdwb3J0Lm9mZnNldEhlaWdodDtcclxuICAgICAgICB2YXIgc3RhcnQgPSBNYXRoLmZsb29yKHRvcCAvIHRoaXMucHJvcHMucm93SGVpZ2h0KTtcclxuICAgICAgICB2YXIgc3RvcCA9IHN0YXJ0ICsgTWF0aC5jZWlsKGhlaWdodCAvICh0aGlzLnByb3BzLnJvd0hlaWdodE1pbiB8fCB0aGlzLnByb3BzLnJvd0hlaWdodCkpO1xyXG5cclxuICAgICAgICB0aGlzLnNldFN0YXRlKHtcclxuICAgICAgICAgICAgc3RhcnQ6IHN0YXJ0LFxyXG4gICAgICAgICAgICBzdG9wOiBzdG9wXHJcbiAgICAgICAgfSk7XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyUm93czogZnVuY3Rpb24gKGVsZW1zKSB7XHJcbiAgICAgICAgdmFyIHJvd3MgPSBbXTtcclxuICAgICAgICB2YXIgbWF4ID0gTWF0aC5taW4oZWxlbXMubGVuZ3RoLCB0aGlzLnN0YXRlLnN0b3ApO1xyXG5cclxuICAgICAgICBmb3IgKHZhciBpID0gdGhpcy5zdGF0ZS5zdGFydDsgaSA8IG1heDsgaSsrKSB7XHJcbiAgICAgICAgICAgIHZhciBlbGVtID0gZWxlbXNbaV07XHJcbiAgICAgICAgICAgIHJvd3MucHVzaCh0aGlzLnJlbmRlclJvdyhlbGVtKSk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHJldHVybiByb3dzO1xyXG4gICAgfSxcclxuICAgIHNjcm9sbFJvd0ludG9WaWV3OiBmdW5jdGlvbiAoaW5kZXgsIGhlYWRfaGVpZ2h0KSB7XHJcblxyXG4gICAgICAgIHZhciByb3dfdG9wID0gKGluZGV4ICogdGhpcy5wcm9wcy5yb3dIZWlnaHQpICsgaGVhZF9oZWlnaHQ7XHJcbiAgICAgICAgdmFyIHJvd19ib3R0b20gPSByb3dfdG9wICsgdGhpcy5wcm9wcy5yb3dIZWlnaHQ7XHJcblxyXG4gICAgICAgIHZhciB2aWV3cG9ydCA9IHRoaXMuZ2V0RE9NTm9kZSgpO1xyXG4gICAgICAgIHZhciB2aWV3cG9ydF90b3AgPSB2aWV3cG9ydC5zY3JvbGxUb3A7XHJcbiAgICAgICAgdmFyIHZpZXdwb3J0X2JvdHRvbSA9IHZpZXdwb3J0X3RvcCArIHZpZXdwb3J0Lm9mZnNldEhlaWdodDtcclxuXHJcbiAgICAgICAgLy8gQWNjb3VudCBmb3IgcGlubmVkIHRoZWFkXHJcbiAgICAgICAgaWYgKHJvd190b3AgLSBoZWFkX2hlaWdodCA8IHZpZXdwb3J0X3RvcCkge1xyXG4gICAgICAgICAgICB2aWV3cG9ydC5zY3JvbGxUb3AgPSByb3dfdG9wIC0gaGVhZF9oZWlnaHQ7XHJcbiAgICAgICAgfSBlbHNlIGlmIChyb3dfYm90dG9tID4gdmlld3BvcnRfYm90dG9tKSB7XHJcbiAgICAgICAgICAgIHZpZXdwb3J0LnNjcm9sbFRvcCA9IHJvd19ib3R0b20gLSB2aWV3cG9ydC5vZmZzZXRIZWlnaHQ7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxufTtcclxuXHJcbm1vZHVsZS5leHBvcnRzICA9IFZpcnR1YWxTY3JvbGxNaXhpbjsiLCJcclxudmFyIGFjdGlvbnMgPSByZXF1aXJlKFwiLi9hY3Rpb25zLmpzXCIpO1xyXG5cclxuZnVuY3Rpb24gQ29ubmVjdGlvbih1cmwpIHtcclxuICAgIGlmICh1cmxbMF0gPT09IFwiL1wiKSB7XHJcbiAgICAgICAgdXJsID0gbG9jYXRpb24ub3JpZ2luLnJlcGxhY2UoXCJodHRwXCIsIFwid3NcIikgKyB1cmw7XHJcbiAgICB9XHJcblxyXG4gICAgdmFyIHdzID0gbmV3IFdlYlNvY2tldCh1cmwpO1xyXG4gICAgd3Mub25vcGVuID0gZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIGFjdGlvbnMuQ29ubmVjdGlvbkFjdGlvbnMub3BlbigpO1xyXG4gICAgfTtcclxuICAgIHdzLm9ubWVzc2FnZSA9IGZ1bmN0aW9uIChtZXNzYWdlKSB7XHJcbiAgICAgICAgdmFyIG0gPSBKU09OLnBhcnNlKG1lc3NhZ2UuZGF0YSk7XHJcbiAgICAgICAgQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFNlcnZlckFjdGlvbihtKTtcclxuICAgIH07XHJcbiAgICB3cy5vbmVycm9yID0gZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIGFjdGlvbnMuQ29ubmVjdGlvbkFjdGlvbnMuZXJyb3IoKTtcclxuICAgICAgICBFdmVudExvZ0FjdGlvbnMuYWRkX2V2ZW50KFwiV2ViU29ja2V0IGNvbm5lY3Rpb24gZXJyb3IuXCIpO1xyXG4gICAgfTtcclxuICAgIHdzLm9uY2xvc2UgPSBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgYWN0aW9ucy5Db25uZWN0aW9uQWN0aW9ucy5jbG9zZSgpO1xyXG4gICAgICAgIEV2ZW50TG9nQWN0aW9ucy5hZGRfZXZlbnQoXCJXZWJTb2NrZXQgY29ubmVjdGlvbiBjbG9zZWQuXCIpO1xyXG4gICAgfTtcclxuICAgIHJldHVybiB3cztcclxufVxyXG5cclxubW9kdWxlLmV4cG9ydHMgPSBDb25uZWN0aW9uOyIsIlxyXG52YXIgZmx1eCA9IHJlcXVpcmUoXCJmbHV4XCIpO1xyXG5cclxuY29uc3QgUGF5bG9hZFNvdXJjZXMgPSB7XHJcbiAgICBWSUVXOiBcInZpZXdcIixcclxuICAgIFNFUlZFUjogXCJzZXJ2ZXJcIlxyXG59O1xyXG5cclxuXHJcbkFwcERpc3BhdGNoZXIgPSBuZXcgZmx1eC5EaXNwYXRjaGVyKCk7XHJcbkFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uID0gZnVuY3Rpb24gKGFjdGlvbikge1xyXG4gICAgYWN0aW9uLnNvdXJjZSA9IFBheWxvYWRTb3VyY2VzLlZJRVc7XHJcbiAgICB0aGlzLmRpc3BhdGNoKGFjdGlvbik7XHJcbn07XHJcbkFwcERpc3BhdGNoZXIuZGlzcGF0Y2hTZXJ2ZXJBY3Rpb24gPSBmdW5jdGlvbiAoYWN0aW9uKSB7XHJcbiAgICBhY3Rpb24uc291cmNlID0gUGF5bG9hZFNvdXJjZXMuU0VSVkVSO1xyXG4gICAgdGhpcy5kaXNwYXRjaChhY3Rpb24pO1xyXG59O1xyXG5cclxubW9kdWxlLmV4cG9ydHMgPSB7XHJcbiAgICBBcHBEaXNwYXRjaGVyOiBBcHBEaXNwYXRjaGVyXHJcbn07IiwibW9kdWxlLmV4cG9ydHMgPSAoZnVuY3Rpb24oKSB7XG4gIC8qXG4gICAqIEdlbmVyYXRlZCBieSBQRUcuanMgMC44LjAuXG4gICAqXG4gICAqIGh0dHA6Ly9wZWdqcy5tYWpkYS5jei9cbiAgICovXG5cbiAgZnVuY3Rpb24gcGVnJHN1YmNsYXNzKGNoaWxkLCBwYXJlbnQpIHtcbiAgICBmdW5jdGlvbiBjdG9yKCkgeyB0aGlzLmNvbnN0cnVjdG9yID0gY2hpbGQ7IH1cbiAgICBjdG9yLnByb3RvdHlwZSA9IHBhcmVudC5wcm90b3R5cGU7XG4gICAgY2hpbGQucHJvdG90eXBlID0gbmV3IGN0b3IoKTtcbiAgfVxuXG4gIGZ1bmN0aW9uIFN5bnRheEVycm9yKG1lc3NhZ2UsIGV4cGVjdGVkLCBmb3VuZCwgb2Zmc2V0LCBsaW5lLCBjb2x1bW4pIHtcbiAgICB0aGlzLm1lc3NhZ2UgID0gbWVzc2FnZTtcbiAgICB0aGlzLmV4cGVjdGVkID0gZXhwZWN0ZWQ7XG4gICAgdGhpcy5mb3VuZCAgICA9IGZvdW5kO1xuICAgIHRoaXMub2Zmc2V0ICAgPSBvZmZzZXQ7XG4gICAgdGhpcy5saW5lICAgICA9IGxpbmU7XG4gICAgdGhpcy5jb2x1bW4gICA9IGNvbHVtbjtcblxuICAgIHRoaXMubmFtZSAgICAgPSBcIlN5bnRheEVycm9yXCI7XG4gIH1cblxuICBwZWckc3ViY2xhc3MoU3ludGF4RXJyb3IsIEVycm9yKTtcblxuICBmdW5jdGlvbiBwYXJzZShpbnB1dCkge1xuICAgIHZhciBvcHRpb25zID0gYXJndW1lbnRzLmxlbmd0aCA+IDEgPyBhcmd1bWVudHNbMV0gOiB7fSxcblxuICAgICAgICBwZWckRkFJTEVEID0ge30sXG5cbiAgICAgICAgcGVnJHN0YXJ0UnVsZUZ1bmN0aW9ucyA9IHsgc3RhcnQ6IHBlZyRwYXJzZXN0YXJ0IH0sXG4gICAgICAgIHBlZyRzdGFydFJ1bGVGdW5jdGlvbiAgPSBwZWckcGFyc2VzdGFydCxcblxuICAgICAgICBwZWckYzAgPSB7IHR5cGU6IFwib3RoZXJcIiwgZGVzY3JpcHRpb246IFwiZmlsdGVyIGV4cHJlc3Npb25cIiB9LFxuICAgICAgICBwZWckYzEgPSBwZWckRkFJTEVELFxuICAgICAgICBwZWckYzIgPSBmdW5jdGlvbihvckV4cHIpIHsgcmV0dXJuIG9yRXhwcjsgfSxcbiAgICAgICAgcGVnJGMzID0gW10sXG4gICAgICAgIHBlZyRjNCA9IGZ1bmN0aW9uKCkge3JldHVybiB0cnVlRmlsdGVyOyB9LFxuICAgICAgICBwZWckYzUgPSB7IHR5cGU6IFwib3RoZXJcIiwgZGVzY3JpcHRpb246IFwid2hpdGVzcGFjZVwiIH0sXG4gICAgICAgIHBlZyRjNiA9IC9eWyBcXHRcXG5cXHJdLyxcbiAgICAgICAgcGVnJGM3ID0geyB0eXBlOiBcImNsYXNzXCIsIHZhbHVlOiBcIlsgXFxcXHRcXFxcblxcXFxyXVwiLCBkZXNjcmlwdGlvbjogXCJbIFxcXFx0XFxcXG5cXFxccl1cIiB9LFxuICAgICAgICBwZWckYzggPSB7IHR5cGU6IFwib3RoZXJcIiwgZGVzY3JpcHRpb246IFwiY29udHJvbCBjaGFyYWN0ZXJcIiB9LFxuICAgICAgICBwZWckYzkgPSAvXlt8JiEoKX5cIl0vLFxuICAgICAgICBwZWckYzEwID0geyB0eXBlOiBcImNsYXNzXCIsIHZhbHVlOiBcIlt8JiEoKX5cXFwiXVwiLCBkZXNjcmlwdGlvbjogXCJbfCYhKCl+XFxcIl1cIiB9LFxuICAgICAgICBwZWckYzExID0geyB0eXBlOiBcIm90aGVyXCIsIGRlc2NyaXB0aW9uOiBcIm9wdGlvbmFsIHdoaXRlc3BhY2VcIiB9LFxuICAgICAgICBwZWckYzEyID0gXCJ8XCIsXG4gICAgICAgIHBlZyRjMTMgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ8XCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ8XFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMTQgPSBmdW5jdGlvbihmaXJzdCwgc2Vjb25kKSB7IHJldHVybiBvcihmaXJzdCwgc2Vjb25kKTsgfSxcbiAgICAgICAgcGVnJGMxNSA9IFwiJlwiLFxuICAgICAgICBwZWckYzE2ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiJlwiLCBkZXNjcmlwdGlvbjogXCJcXFwiJlxcXCJcIiB9LFxuICAgICAgICBwZWckYzE3ID0gZnVuY3Rpb24oZmlyc3QsIHNlY29uZCkgeyByZXR1cm4gYW5kKGZpcnN0LCBzZWNvbmQpOyB9LFxuICAgICAgICBwZWckYzE4ID0gXCIhXCIsXG4gICAgICAgIHBlZyRjMTkgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCIhXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCIhXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMjAgPSBmdW5jdGlvbihleHByKSB7IHJldHVybiBub3QoZXhwcik7IH0sXG4gICAgICAgIHBlZyRjMjEgPSBcIihcIixcbiAgICAgICAgcGVnJGMyMiA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIihcIiwgZGVzY3JpcHRpb246IFwiXFxcIihcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMyMyA9IFwiKVwiLFxuICAgICAgICBwZWckYzI0ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiKVwiLCBkZXNjcmlwdGlvbjogXCJcXFwiKVxcXCJcIiB9LFxuICAgICAgICBwZWckYzI1ID0gZnVuY3Rpb24oZXhwcikgeyByZXR1cm4gYmluZGluZyhleHByKTsgfSxcbiAgICAgICAgcGVnJGMyNiA9IFwifmFcIixcbiAgICAgICAgcGVnJGMyNyA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5hXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+YVxcXCJcIiB9LFxuICAgICAgICBwZWckYzI4ID0gZnVuY3Rpb24oKSB7IHJldHVybiBhc3NldEZpbHRlcjsgfSxcbiAgICAgICAgcGVnJGMyOSA9IFwifmVcIixcbiAgICAgICAgcGVnJGMzMCA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5lXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+ZVxcXCJcIiB9LFxuICAgICAgICBwZWckYzMxID0gZnVuY3Rpb24oKSB7IHJldHVybiBlcnJvckZpbHRlcjsgfSxcbiAgICAgICAgcGVnJGMzMiA9IFwifnFcIixcbiAgICAgICAgcGVnJGMzMyA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5xXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+cVxcXCJcIiB9LFxuICAgICAgICBwZWckYzM0ID0gZnVuY3Rpb24oKSB7IHJldHVybiBub1Jlc3BvbnNlRmlsdGVyOyB9LFxuICAgICAgICBwZWckYzM1ID0gXCJ+c1wiLFxuICAgICAgICBwZWckYzM2ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifnNcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5zXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMzcgPSBmdW5jdGlvbigpIHsgcmV0dXJuIHJlc3BvbnNlRmlsdGVyOyB9LFxuICAgICAgICBwZWckYzM4ID0gXCJ0cnVlXCIsXG4gICAgICAgIHBlZyRjMzkgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ0cnVlXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ0cnVlXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNDAgPSBmdW5jdGlvbigpIHsgcmV0dXJuIHRydWVGaWx0ZXI7IH0sXG4gICAgICAgIHBlZyRjNDEgPSBcImZhbHNlXCIsXG4gICAgICAgIHBlZyRjNDIgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJmYWxzZVwiLCBkZXNjcmlwdGlvbjogXCJcXFwiZmFsc2VcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM0MyA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gZmFsc2VGaWx0ZXI7IH0sXG4gICAgICAgIHBlZyRjNDQgPSBcIn5jXCIsXG4gICAgICAgIHBlZyRjNDUgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+Y1wiLCBkZXNjcmlwdGlvbjogXCJcXFwifmNcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM0NiA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIHJlc3BvbnNlQ29kZShzKTsgfSxcbiAgICAgICAgcGVnJGM0NyA9IFwifmRcIixcbiAgICAgICAgcGVnJGM0OCA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5kXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+ZFxcXCJcIiB9LFxuICAgICAgICBwZWckYzQ5ID0gZnVuY3Rpb24ocykgeyByZXR1cm4gZG9tYWluKHMpOyB9LFxuICAgICAgICBwZWckYzUwID0gXCJ+aFwiLFxuICAgICAgICBwZWckYzUxID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifmhcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5oXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNTIgPSBmdW5jdGlvbihzKSB7IHJldHVybiBoZWFkZXIocyk7IH0sXG4gICAgICAgIHBlZyRjNTMgPSBcIn5ocVwiLFxuICAgICAgICBwZWckYzU0ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifmhxXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+aHFcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM1NSA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIHJlcXVlc3RIZWFkZXIocyk7IH0sXG4gICAgICAgIHBlZyRjNTYgPSBcIn5oc1wiLFxuICAgICAgICBwZWckYzU3ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifmhzXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+aHNcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM1OCA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIHJlc3BvbnNlSGVhZGVyKHMpOyB9LFxuICAgICAgICBwZWckYzU5ID0gXCJ+bVwiLFxuICAgICAgICBwZWckYzYwID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifm1cIiwgZGVzY3JpcHRpb246IFwiXFxcIn5tXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNjEgPSBmdW5jdGlvbihzKSB7IHJldHVybiBtZXRob2Qocyk7IH0sXG4gICAgICAgIHBlZyRjNjIgPSBcIn50XCIsXG4gICAgICAgIHBlZyRjNjMgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+dFwiLCBkZXNjcmlwdGlvbjogXCJcXFwifnRcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM2NCA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIGNvbnRlbnRUeXBlKHMpOyB9LFxuICAgICAgICBwZWckYzY1ID0gXCJ+dHFcIixcbiAgICAgICAgcGVnJGM2NiA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn50cVwiLCBkZXNjcmlwdGlvbjogXCJcXFwifnRxXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNjcgPSBmdW5jdGlvbihzKSB7IHJldHVybiByZXF1ZXN0Q29udGVudFR5cGUocyk7IH0sXG4gICAgICAgIHBlZyRjNjggPSBcIn50c1wiLFxuICAgICAgICBwZWckYzY5ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifnRzXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+dHNcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM3MCA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIHJlc3BvbnNlQ29udGVudFR5cGUocyk7IH0sXG4gICAgICAgIHBlZyRjNzEgPSBcIn51XCIsXG4gICAgICAgIHBlZyRjNzIgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+dVwiLCBkZXNjcmlwdGlvbjogXCJcXFwifnVcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM3MyA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIHVybChzKTsgfSxcbiAgICAgICAgcGVnJGM3NCA9IHsgdHlwZTogXCJvdGhlclwiLCBkZXNjcmlwdGlvbjogXCJpbnRlZ2VyXCIgfSxcbiAgICAgICAgcGVnJGM3NSA9IG51bGwsXG4gICAgICAgIHBlZyRjNzYgPSAvXlsnXCJdLyxcbiAgICAgICAgcGVnJGM3NyA9IHsgdHlwZTogXCJjbGFzc1wiLCB2YWx1ZTogXCJbJ1xcXCJdXCIsIGRlc2NyaXB0aW9uOiBcIlsnXFxcIl1cIiB9LFxuICAgICAgICBwZWckYzc4ID0gL15bMC05XS8sXG4gICAgICAgIHBlZyRjNzkgPSB7IHR5cGU6IFwiY2xhc3NcIiwgdmFsdWU6IFwiWzAtOV1cIiwgZGVzY3JpcHRpb246IFwiWzAtOV1cIiB9LFxuICAgICAgICBwZWckYzgwID0gZnVuY3Rpb24oZGlnaXRzKSB7IHJldHVybiBwYXJzZUludChkaWdpdHMuam9pbihcIlwiKSwgMTApOyB9LFxuICAgICAgICBwZWckYzgxID0geyB0eXBlOiBcIm90aGVyXCIsIGRlc2NyaXB0aW9uOiBcInN0cmluZ1wiIH0sXG4gICAgICAgIHBlZyRjODIgPSBcIlxcXCJcIixcbiAgICAgICAgcGVnJGM4MyA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIlxcXCJcIiwgZGVzY3JpcHRpb246IFwiXFxcIlxcXFxcXFwiXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjODQgPSBmdW5jdGlvbihjaGFycykgeyByZXR1cm4gY2hhcnMuam9pbihcIlwiKTsgfSxcbiAgICAgICAgcGVnJGM4NSA9IFwiJ1wiLFxuICAgICAgICBwZWckYzg2ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiJ1wiLCBkZXNjcmlwdGlvbjogXCJcXFwiJ1xcXCJcIiB9LFxuICAgICAgICBwZWckYzg3ID0gdm9pZCAwLFxuICAgICAgICBwZWckYzg4ID0gL15bXCJcXFxcXS8sXG4gICAgICAgIHBlZyRjODkgPSB7IHR5cGU6IFwiY2xhc3NcIiwgdmFsdWU6IFwiW1xcXCJcXFxcXFxcXF1cIiwgZGVzY3JpcHRpb246IFwiW1xcXCJcXFxcXFxcXF1cIiB9LFxuICAgICAgICBwZWckYzkwID0geyB0eXBlOiBcImFueVwiLCBkZXNjcmlwdGlvbjogXCJhbnkgY2hhcmFjdGVyXCIgfSxcbiAgICAgICAgcGVnJGM5MSA9IGZ1bmN0aW9uKGNoYXIpIHsgcmV0dXJuIGNoYXI7IH0sXG4gICAgICAgIHBlZyRjOTIgPSBcIlxcXFxcIixcbiAgICAgICAgcGVnJGM5MyA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIlxcXFxcIiwgZGVzY3JpcHRpb246IFwiXFxcIlxcXFxcXFxcXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjOTQgPSAvXlsnXFxcXF0vLFxuICAgICAgICBwZWckYzk1ID0geyB0eXBlOiBcImNsYXNzXCIsIHZhbHVlOiBcIlsnXFxcXFxcXFxdXCIsIGRlc2NyaXB0aW9uOiBcIlsnXFxcXFxcXFxdXCIgfSxcbiAgICAgICAgcGVnJGM5NiA9IC9eWydcIlxcXFxdLyxcbiAgICAgICAgcGVnJGM5NyA9IHsgdHlwZTogXCJjbGFzc1wiLCB2YWx1ZTogXCJbJ1xcXCJcXFxcXFxcXF1cIiwgZGVzY3JpcHRpb246IFwiWydcXFwiXFxcXFxcXFxdXCIgfSxcbiAgICAgICAgcGVnJGM5OCA9IFwiblwiLFxuICAgICAgICBwZWckYzk5ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiblwiLCBkZXNjcmlwdGlvbjogXCJcXFwiblxcXCJcIiB9LFxuICAgICAgICBwZWckYzEwMCA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gXCJcXG5cIjsgfSxcbiAgICAgICAgcGVnJGMxMDEgPSBcInJcIixcbiAgICAgICAgcGVnJGMxMDIgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJyXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJyXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMTAzID0gZnVuY3Rpb24oKSB7IHJldHVybiBcIlxcclwiOyB9LFxuICAgICAgICBwZWckYzEwNCA9IFwidFwiLFxuICAgICAgICBwZWckYzEwNSA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcInRcIiwgZGVzY3JpcHRpb246IFwiXFxcInRcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMxMDYgPSBmdW5jdGlvbigpIHsgcmV0dXJuIFwiXFx0XCI7IH0sXG5cbiAgICAgICAgcGVnJGN1cnJQb3MgICAgICAgICAgPSAwLFxuICAgICAgICBwZWckcmVwb3J0ZWRQb3MgICAgICA9IDAsXG4gICAgICAgIHBlZyRjYWNoZWRQb3MgICAgICAgID0gMCxcbiAgICAgICAgcGVnJGNhY2hlZFBvc0RldGFpbHMgPSB7IGxpbmU6IDEsIGNvbHVtbjogMSwgc2VlbkNSOiBmYWxzZSB9LFxuICAgICAgICBwZWckbWF4RmFpbFBvcyAgICAgICA9IDAsXG4gICAgICAgIHBlZyRtYXhGYWlsRXhwZWN0ZWQgID0gW10sXG4gICAgICAgIHBlZyRzaWxlbnRGYWlscyAgICAgID0gMCxcblxuICAgICAgICBwZWckcmVzdWx0O1xuXG4gICAgaWYgKFwic3RhcnRSdWxlXCIgaW4gb3B0aW9ucykge1xuICAgICAgaWYgKCEob3B0aW9ucy5zdGFydFJ1bGUgaW4gcGVnJHN0YXJ0UnVsZUZ1bmN0aW9ucykpIHtcbiAgICAgICAgdGhyb3cgbmV3IEVycm9yKFwiQ2FuJ3Qgc3RhcnQgcGFyc2luZyBmcm9tIHJ1bGUgXFxcIlwiICsgb3B0aW9ucy5zdGFydFJ1bGUgKyBcIlxcXCIuXCIpO1xuICAgICAgfVxuXG4gICAgICBwZWckc3RhcnRSdWxlRnVuY3Rpb24gPSBwZWckc3RhcnRSdWxlRnVuY3Rpb25zW29wdGlvbnMuc3RhcnRSdWxlXTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiB0ZXh0KCkge1xuICAgICAgcmV0dXJuIGlucHV0LnN1YnN0cmluZyhwZWckcmVwb3J0ZWRQb3MsIHBlZyRjdXJyUG9zKTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBvZmZzZXQoKSB7XG4gICAgICByZXR1cm4gcGVnJHJlcG9ydGVkUG9zO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIGxpbmUoKSB7XG4gICAgICByZXR1cm4gcGVnJGNvbXB1dGVQb3NEZXRhaWxzKHBlZyRyZXBvcnRlZFBvcykubGluZTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBjb2x1bW4oKSB7XG4gICAgICByZXR1cm4gcGVnJGNvbXB1dGVQb3NEZXRhaWxzKHBlZyRyZXBvcnRlZFBvcykuY29sdW1uO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIGV4cGVjdGVkKGRlc2NyaXB0aW9uKSB7XG4gICAgICB0aHJvdyBwZWckYnVpbGRFeGNlcHRpb24oXG4gICAgICAgIG51bGwsXG4gICAgICAgIFt7IHR5cGU6IFwib3RoZXJcIiwgZGVzY3JpcHRpb246IGRlc2NyaXB0aW9uIH1dLFxuICAgICAgICBwZWckcmVwb3J0ZWRQb3NcbiAgICAgICk7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gZXJyb3IobWVzc2FnZSkge1xuICAgICAgdGhyb3cgcGVnJGJ1aWxkRXhjZXB0aW9uKG1lc3NhZ2UsIG51bGwsIHBlZyRyZXBvcnRlZFBvcyk7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJGNvbXB1dGVQb3NEZXRhaWxzKHBvcykge1xuICAgICAgZnVuY3Rpb24gYWR2YW5jZShkZXRhaWxzLCBzdGFydFBvcywgZW5kUG9zKSB7XG4gICAgICAgIHZhciBwLCBjaDtcblxuICAgICAgICBmb3IgKHAgPSBzdGFydFBvczsgcCA8IGVuZFBvczsgcCsrKSB7XG4gICAgICAgICAgY2ggPSBpbnB1dC5jaGFyQXQocCk7XG4gICAgICAgICAgaWYgKGNoID09PSBcIlxcblwiKSB7XG4gICAgICAgICAgICBpZiAoIWRldGFpbHMuc2VlbkNSKSB7IGRldGFpbHMubGluZSsrOyB9XG4gICAgICAgICAgICBkZXRhaWxzLmNvbHVtbiA9IDE7XG4gICAgICAgICAgICBkZXRhaWxzLnNlZW5DUiA9IGZhbHNlO1xuICAgICAgICAgIH0gZWxzZSBpZiAoY2ggPT09IFwiXFxyXCIgfHwgY2ggPT09IFwiXFx1MjAyOFwiIHx8IGNoID09PSBcIlxcdTIwMjlcIikge1xuICAgICAgICAgICAgZGV0YWlscy5saW5lKys7XG4gICAgICAgICAgICBkZXRhaWxzLmNvbHVtbiA9IDE7XG4gICAgICAgICAgICBkZXRhaWxzLnNlZW5DUiA9IHRydWU7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGRldGFpbHMuY29sdW1uKys7XG4gICAgICAgICAgICBkZXRhaWxzLnNlZW5DUiA9IGZhbHNlO1xuICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICBpZiAocGVnJGNhY2hlZFBvcyAhPT0gcG9zKSB7XG4gICAgICAgIGlmIChwZWckY2FjaGVkUG9zID4gcG9zKSB7XG4gICAgICAgICAgcGVnJGNhY2hlZFBvcyA9IDA7XG4gICAgICAgICAgcGVnJGNhY2hlZFBvc0RldGFpbHMgPSB7IGxpbmU6IDEsIGNvbHVtbjogMSwgc2VlbkNSOiBmYWxzZSB9O1xuICAgICAgICB9XG4gICAgICAgIGFkdmFuY2UocGVnJGNhY2hlZFBvc0RldGFpbHMsIHBlZyRjYWNoZWRQb3MsIHBvcyk7XG4gICAgICAgIHBlZyRjYWNoZWRQb3MgPSBwb3M7XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBwZWckY2FjaGVkUG9zRGV0YWlscztcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckZmFpbChleHBlY3RlZCkge1xuICAgICAgaWYgKHBlZyRjdXJyUG9zIDwgcGVnJG1heEZhaWxQb3MpIHsgcmV0dXJuOyB9XG5cbiAgICAgIGlmIChwZWckY3VyclBvcyA+IHBlZyRtYXhGYWlsUG9zKSB7XG4gICAgICAgIHBlZyRtYXhGYWlsUG9zID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIHBlZyRtYXhGYWlsRXhwZWN0ZWQgPSBbXTtcbiAgICAgIH1cblxuICAgICAgcGVnJG1heEZhaWxFeHBlY3RlZC5wdXNoKGV4cGVjdGVkKTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckYnVpbGRFeGNlcHRpb24obWVzc2FnZSwgZXhwZWN0ZWQsIHBvcykge1xuICAgICAgZnVuY3Rpb24gY2xlYW51cEV4cGVjdGVkKGV4cGVjdGVkKSB7XG4gICAgICAgIHZhciBpID0gMTtcblxuICAgICAgICBleHBlY3RlZC5zb3J0KGZ1bmN0aW9uKGEsIGIpIHtcbiAgICAgICAgICBpZiAoYS5kZXNjcmlwdGlvbiA8IGIuZGVzY3JpcHRpb24pIHtcbiAgICAgICAgICAgIHJldHVybiAtMTtcbiAgICAgICAgICB9IGVsc2UgaWYgKGEuZGVzY3JpcHRpb24gPiBiLmRlc2NyaXB0aW9uKSB7XG4gICAgICAgICAgICByZXR1cm4gMTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcmV0dXJuIDA7XG4gICAgICAgICAgfVxuICAgICAgICB9KTtcblxuICAgICAgICB3aGlsZSAoaSA8IGV4cGVjdGVkLmxlbmd0aCkge1xuICAgICAgICAgIGlmIChleHBlY3RlZFtpIC0gMV0gPT09IGV4cGVjdGVkW2ldKSB7XG4gICAgICAgICAgICBleHBlY3RlZC5zcGxpY2UoaSwgMSk7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGkrKztcbiAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgIH1cblxuICAgICAgZnVuY3Rpb24gYnVpbGRNZXNzYWdlKGV4cGVjdGVkLCBmb3VuZCkge1xuICAgICAgICBmdW5jdGlvbiBzdHJpbmdFc2NhcGUocykge1xuICAgICAgICAgIGZ1bmN0aW9uIGhleChjaCkgeyByZXR1cm4gY2guY2hhckNvZGVBdCgwKS50b1N0cmluZygxNikudG9VcHBlckNhc2UoKTsgfVxuXG4gICAgICAgICAgcmV0dXJuIHNcbiAgICAgICAgICAgIC5yZXBsYWNlKC9cXFxcL2csICAgJ1xcXFxcXFxcJylcbiAgICAgICAgICAgIC5yZXBsYWNlKC9cIi9nLCAgICAnXFxcXFwiJylcbiAgICAgICAgICAgIC5yZXBsYWNlKC9cXHgwOC9nLCAnXFxcXGInKVxuICAgICAgICAgICAgLnJlcGxhY2UoL1xcdC9nLCAgICdcXFxcdCcpXG4gICAgICAgICAgICAucmVwbGFjZSgvXFxuL2csICAgJ1xcXFxuJylcbiAgICAgICAgICAgIC5yZXBsYWNlKC9cXGYvZywgICAnXFxcXGYnKVxuICAgICAgICAgICAgLnJlcGxhY2UoL1xcci9nLCAgICdcXFxccicpXG4gICAgICAgICAgICAucmVwbGFjZSgvW1xceDAwLVxceDA3XFx4MEJcXHgwRVxceDBGXS9nLCBmdW5jdGlvbihjaCkgeyByZXR1cm4gJ1xcXFx4MCcgKyBoZXgoY2gpOyB9KVxuICAgICAgICAgICAgLnJlcGxhY2UoL1tcXHgxMC1cXHgxRlxceDgwLVxceEZGXS9nLCAgICBmdW5jdGlvbihjaCkgeyByZXR1cm4gJ1xcXFx4JyAgKyBoZXgoY2gpOyB9KVxuICAgICAgICAgICAgLnJlcGxhY2UoL1tcXHUwMTgwLVxcdTBGRkZdL2csICAgICAgICAgZnVuY3Rpb24oY2gpIHsgcmV0dXJuICdcXFxcdTAnICsgaGV4KGNoKTsgfSlcbiAgICAgICAgICAgIC5yZXBsYWNlKC9bXFx1MTA4MC1cXHVGRkZGXS9nLCAgICAgICAgIGZ1bmN0aW9uKGNoKSB7IHJldHVybiAnXFxcXHUnICArIGhleChjaCk7IH0pO1xuICAgICAgICB9XG5cbiAgICAgICAgdmFyIGV4cGVjdGVkRGVzY3MgPSBuZXcgQXJyYXkoZXhwZWN0ZWQubGVuZ3RoKSxcbiAgICAgICAgICAgIGV4cGVjdGVkRGVzYywgZm91bmREZXNjLCBpO1xuXG4gICAgICAgIGZvciAoaSA9IDA7IGkgPCBleHBlY3RlZC5sZW5ndGg7IGkrKykge1xuICAgICAgICAgIGV4cGVjdGVkRGVzY3NbaV0gPSBleHBlY3RlZFtpXS5kZXNjcmlwdGlvbjtcbiAgICAgICAgfVxuXG4gICAgICAgIGV4cGVjdGVkRGVzYyA9IGV4cGVjdGVkLmxlbmd0aCA+IDFcbiAgICAgICAgICA/IGV4cGVjdGVkRGVzY3Muc2xpY2UoMCwgLTEpLmpvaW4oXCIsIFwiKVxuICAgICAgICAgICAgICArIFwiIG9yIFwiXG4gICAgICAgICAgICAgICsgZXhwZWN0ZWREZXNjc1tleHBlY3RlZC5sZW5ndGggLSAxXVxuICAgICAgICAgIDogZXhwZWN0ZWREZXNjc1swXTtcblxuICAgICAgICBmb3VuZERlc2MgPSBmb3VuZCA/IFwiXFxcIlwiICsgc3RyaW5nRXNjYXBlKGZvdW5kKSArIFwiXFxcIlwiIDogXCJlbmQgb2YgaW5wdXRcIjtcblxuICAgICAgICByZXR1cm4gXCJFeHBlY3RlZCBcIiArIGV4cGVjdGVkRGVzYyArIFwiIGJ1dCBcIiArIGZvdW5kRGVzYyArIFwiIGZvdW5kLlwiO1xuICAgICAgfVxuXG4gICAgICB2YXIgcG9zRGV0YWlscyA9IHBlZyRjb21wdXRlUG9zRGV0YWlscyhwb3MpLFxuICAgICAgICAgIGZvdW5kICAgICAgPSBwb3MgPCBpbnB1dC5sZW5ndGggPyBpbnB1dC5jaGFyQXQocG9zKSA6IG51bGw7XG5cbiAgICAgIGlmIChleHBlY3RlZCAhPT0gbnVsbCkge1xuICAgICAgICBjbGVhbnVwRXhwZWN0ZWQoZXhwZWN0ZWQpO1xuICAgICAgfVxuXG4gICAgICByZXR1cm4gbmV3IFN5bnRheEVycm9yKFxuICAgICAgICBtZXNzYWdlICE9PSBudWxsID8gbWVzc2FnZSA6IGJ1aWxkTWVzc2FnZShleHBlY3RlZCwgZm91bmQpLFxuICAgICAgICBleHBlY3RlZCxcbiAgICAgICAgZm91bmQsXG4gICAgICAgIHBvcyxcbiAgICAgICAgcG9zRGV0YWlscy5saW5lLFxuICAgICAgICBwb3NEZXRhaWxzLmNvbHVtblxuICAgICAgKTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VzdGFydCgpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyLCBzMztcblxuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgczEgPSBwZWckcGFyc2VfXygpO1xuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gcGVnJHBhcnNlT3JFeHByKCk7XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMzID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzIoczIpO1xuICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBzMSA9IFtdO1xuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICBzMSA9IHBlZyRjNCgpO1xuICAgICAgICB9XG4gICAgICAgIHMwID0gczE7XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMwKTsgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNld3MoKSB7XG4gICAgICB2YXIgczAsIHMxO1xuXG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIGlmIChwZWckYzYudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICBzMCA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMCA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM3KTsgfVxuICAgICAgfVxuICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNSk7IH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZWNjKCkge1xuICAgICAgdmFyIHMwLCBzMTtcblxuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBpZiAocGVnJGM5LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgczAgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczAgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMTApOyB9XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM4KTsgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlX18oKSB7XG4gICAgICB2YXIgczAsIHMxO1xuXG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIHMwID0gW107XG4gICAgICBzMSA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICB3aGlsZSAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAucHVzaChzMSk7XG4gICAgICAgIHMxID0gcGVnJHBhcnNld3MoKTtcbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzExKTsgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlT3JFeHByKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczIsIHMzLCBzNCwgczU7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBzMSA9IHBlZyRwYXJzZUFuZEV4cHIoKTtcbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMiA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMTI0KSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRjMTI7XG4gICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMTMpOyB9XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczQgPSBwZWckcGFyc2VfXygpO1xuICAgICAgICAgICAgaWYgKHM0ICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHM1ID0gcGVnJHBhcnNlT3JFeHByKCk7XG4gICAgICAgICAgICAgIGlmIChzNSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJGMxNChzMSwgczUpO1xuICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckcGFyc2VBbmRFeHByKCk7XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VBbmRFeHByKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczIsIHMzLCBzNCwgczU7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBzMSA9IHBlZyRwYXJzZU5vdEV4cHIoKTtcbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMiA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMzgpIHtcbiAgICAgICAgICAgIHMzID0gcGVnJGMxNTtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMzID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMxNik7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzNCA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICAgICAgICBpZiAoczQgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczUgPSBwZWckcGFyc2VBbmRFeHByKCk7XG4gICAgICAgICAgICAgIGlmIChzNSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJGMxNyhzMSwgczUpO1xuICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgczEgPSBwZWckcGFyc2VOb3RFeHByKCk7XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlQW5kRXhwcigpO1xuICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjMTcoczEsIHMzKTtcbiAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczAgPSBwZWckcGFyc2VOb3RFeHByKCk7XG4gICAgICAgIH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZU5vdEV4cHIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczM7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDMzKSB7XG4gICAgICAgIHMxID0gcGVnJGMxODtcbiAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzE5KTsgfVxuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczMgPSBwZWckcGFyc2VOb3RFeHByKCk7XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGMyMChzMyk7XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJHBhcnNlQmluZGluZ0V4cHIoKTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZUJpbmRpbmdFeHByKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczIsIHMzLCBzNCwgczU7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDQwKSB7XG4gICAgICAgIHMxID0gcGVnJGMyMTtcbiAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzIyKTsgfVxuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczMgPSBwZWckcGFyc2VPckV4cHIoKTtcbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHM0ID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgICAgIGlmIChzNCAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDQxKSB7XG4gICAgICAgICAgICAgICAgczUgPSBwZWckYzIzO1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgczUgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMyNCk7IH1cbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICBpZiAoczUgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMSA9IHBlZyRjMjUoczMpO1xuICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckcGFyc2VFeHByKCk7XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VFeHByKCkge1xuICAgICAgdmFyIHMwO1xuXG4gICAgICBzMCA9IHBlZyRwYXJzZU51bGxhcnlFeHByKCk7XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckcGFyc2VVbmFyeUV4cHIoKTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZU51bGxhcnlFeHByKCkge1xuICAgICAgdmFyIHMwLCBzMTtcblxuICAgICAgczAgPSBwZWckcGFyc2VCb29sZWFuTGl0ZXJhbCgpO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzI2KSB7XG4gICAgICAgICAgczEgPSBwZWckYzI2O1xuICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMyNyk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICBzMSA9IHBlZyRjMjgoKTtcbiAgICAgICAgfVxuICAgICAgICBzMCA9IHMxO1xuICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzI5KSB7XG4gICAgICAgICAgICBzMSA9IHBlZyRjMjk7XG4gICAgICAgICAgICBwZWckY3VyclBvcyArPSAyO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMzApOyB9XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICBzMSA9IHBlZyRjMzEoKTtcbiAgICAgICAgICB9XG4gICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGMzMikge1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjMzI7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMzMyk7IH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczEgPSBwZWckYzM0KCk7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzM1KSB7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckYzM1O1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMzNik7IH1cbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICBzMSA9IHBlZyRjMzcoKTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlQm9vbGVhbkxpdGVyYWwoKSB7XG4gICAgICB2YXIgczAsIHMxO1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgNCkgPT09IHBlZyRjMzgpIHtcbiAgICAgICAgczEgPSBwZWckYzM4O1xuICAgICAgICBwZWckY3VyclBvcyArPSA0O1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMzkpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgIHMxID0gcGVnJGM0MCgpO1xuICAgICAgfVxuICAgICAgczAgPSBzMTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCA1KSA9PT0gcGVnJGM0MSkge1xuICAgICAgICAgIHMxID0gcGVnJGM0MTtcbiAgICAgICAgICBwZWckY3VyclBvcyArPSA1O1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNDIpOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgczEgPSBwZWckYzQzKCk7XG4gICAgICAgIH1cbiAgICAgICAgczAgPSBzMTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZVVuYXJ5RXhwcigpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyLCBzMztcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzQ0KSB7XG4gICAgICAgIHMxID0gcGVnJGM0NDtcbiAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzQ1KTsgfVxuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gW107XG4gICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczMgPSBwZWckcGFyc2VJbnRlZ2VyTGl0ZXJhbCgpO1xuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICBzMSA9IHBlZyRjNDYoczMpO1xuICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGM0Nykge1xuICAgICAgICAgIHMxID0gcGVnJGM0NztcbiAgICAgICAgICBwZWckY3VyclBvcyArPSAyO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNDgpOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGM0OShzMyk7XG4gICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjNTApIHtcbiAgICAgICAgICAgIHMxID0gcGVnJGM1MDtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM1MSk7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJGM1MihzMyk7XG4gICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAzKSA9PT0gcGVnJGM1Mykge1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjNTM7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDM7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM1NCk7IH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNTUoczMpO1xuICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAzKSA9PT0gcGVnJGM1Nikge1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJGM1NjtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyArPSAzO1xuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNTcpOyB9XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM1OChzMyk7XG4gICAgICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjNTkpIHtcbiAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM1OTtcbiAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM2MCk7IH1cbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM2MShzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGM2Mikge1xuICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNjI7XG4gICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM2Myk7IH1cbiAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNjQoczMpO1xuICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAzKSA9PT0gcGVnJGM2NSkge1xuICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM2NTtcbiAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyArPSAzO1xuICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNjYpOyB9XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM2NyhzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMykgPT09IHBlZyRjNjgpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM2ODtcbiAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDM7XG4gICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM2OSk7IH1cbiAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM3MChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGM3MSkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNzE7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM3Mik7IH1cbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNzMoczMpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzczKHMxKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlSW50ZWdlckxpdGVyYWwoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczM7XG5cbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIGlmIChwZWckYzc2LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgczEgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNzcpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczEgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckYzc1O1xuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gW107XG4gICAgICAgIGlmIChwZWckYzc4LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgICBzMyA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMyA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzc5KTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICBpZiAocGVnJGM3OC50ZXN0KGlucHV0LmNoYXJBdChwZWckY3VyclBvcykpKSB7XG4gICAgICAgICAgICAgIHMzID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHMzID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzc5KTsgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBpZiAocGVnJGM3Ni50ZXN0KGlucHV0LmNoYXJBdChwZWckY3VyclBvcykpKSB7XG4gICAgICAgICAgICBzMyA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNzcpOyB9XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMyA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczMgPSBwZWckYzc1O1xuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzgwKHMyKTtcbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM3NCk7IH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczM7XG5cbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMzQpIHtcbiAgICAgICAgczEgPSBwZWckYzgyO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjODMpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBbXTtcbiAgICAgICAgczMgPSBwZWckcGFyc2VEb3VibGVTdHJpbmdDaGFyKCk7XG4gICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgIHMzID0gcGVnJHBhcnNlRG91YmxlU3RyaW5nQ2hhcigpO1xuICAgICAgICB9XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMzQpIHtcbiAgICAgICAgICAgIHMzID0gcGVnJGM4MjtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMzID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM4Myk7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGM4NChzMik7XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMzkpIHtcbiAgICAgICAgICBzMSA9IHBlZyRjODU7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzg2KTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgczMgPSBwZWckcGFyc2VTaW5nbGVTdHJpbmdDaGFyKCk7XG4gICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlU2luZ2xlU3RyaW5nQ2hhcigpO1xuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMzkpIHtcbiAgICAgICAgICAgICAgczMgPSBwZWckYzg1O1xuICAgICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgczMgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjODYpOyB9XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGM4NChzMik7XG4gICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgczEgPSBwZWckY3VyclBvcztcbiAgICAgICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgICAgICBzMiA9IHBlZyRwYXJzZWNjKCk7XG4gICAgICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICAgICAgaWYgKHMyID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMSA9IHBlZyRjODc7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczE7XG4gICAgICAgICAgICBzMSA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgczMgPSBwZWckcGFyc2VVbnF1b3RlZFN0cmluZ0NoYXIoKTtcbiAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVVucXVvdGVkU3RyaW5nQ2hhcigpO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczEgPSBwZWckYzg0KHMyKTtcbiAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM4MSk7IH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZURvdWJsZVN0cmluZ0NoYXIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMjtcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIHMxID0gcGVnJGN1cnJQb3M7XG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIGlmIChwZWckYzg4LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgczIgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczIgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjODkpOyB9XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMiA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRjODc7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMxO1xuICAgICAgICBzMSA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBpZiAoaW5wdXQubGVuZ3RoID4gcGVnJGN1cnJQb3MpIHtcbiAgICAgICAgICBzMiA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMiA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzkwKTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgIHMxID0gcGVnJGM5MShzMik7XG4gICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDkyKSB7XG4gICAgICAgICAgczEgPSBwZWckYzkyO1xuICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM5Myk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMiA9IHBlZyRwYXJzZUVzY2FwZVNlcXVlbmNlKCk7XG4gICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGM5MShzMik7XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZVNpbmdsZVN0cmluZ0NoYXIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMjtcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIHMxID0gcGVnJGN1cnJQb3M7XG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIGlmIChwZWckYzk0LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgczIgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczIgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOTUpOyB9XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMiA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRjODc7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMxO1xuICAgICAgICBzMSA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBpZiAoaW5wdXQubGVuZ3RoID4gcGVnJGN1cnJQb3MpIHtcbiAgICAgICAgICBzMiA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMiA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzkwKTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgIHMxID0gcGVnJGM5MShzMik7XG4gICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDkyKSB7XG4gICAgICAgICAgczEgPSBwZWckYzkyO1xuICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM5Myk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMiA9IHBlZyRwYXJzZUVzY2FwZVNlcXVlbmNlKCk7XG4gICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGM5MShzMik7XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZVVucXVvdGVkU3RyaW5nQ2hhcigpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyO1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgczEgPSBwZWckY3VyclBvcztcbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgczIgPSBwZWckcGFyc2V3cygpO1xuICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICBpZiAoczIgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckYzg3O1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMTtcbiAgICAgICAgczEgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgaWYgKGlucHV0Lmxlbmd0aCA+IHBlZyRjdXJyUG9zKSB7XG4gICAgICAgICAgczIgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczIgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM5MCk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICBzMSA9IHBlZyRjOTEoczIpO1xuICAgICAgICAgIHMwID0gczE7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VFc2NhcGVTZXF1ZW5jZSgpIHtcbiAgICAgIHZhciBzMCwgczE7XG5cbiAgICAgIGlmIChwZWckYzk2LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgczAgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczAgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOTcpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAxMTApIHtcbiAgICAgICAgICBzMSA9IHBlZyRjOTg7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzk5KTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgIHMxID0gcGVnJGMxMDAoKTtcbiAgICAgICAgfVxuICAgICAgICBzMCA9IHMxO1xuICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMTE0KSB7XG4gICAgICAgICAgICBzMSA9IHBlZyRjMTAxO1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzEwMik7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGMxMDMoKTtcbiAgICAgICAgICB9XG4gICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDExNikge1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjMTA0O1xuICAgICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMTA1KTsgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjMTA2KCk7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG5cclxuICAgIHZhciBmbG93dXRpbHMgPSByZXF1aXJlKFwiLi4vZmxvdy91dGlscy5qc1wiKTtcclxuXHJcbiAgICBmdW5jdGlvbiBvcihmaXJzdCwgc2Vjb25kKSB7XHJcbiAgICAgICAgLy8gQWRkIGV4cGxpY2l0IGZ1bmN0aW9uIG5hbWVzIHRvIGVhc2UgZGVidWdnaW5nLlxyXG4gICAgICAgIGZ1bmN0aW9uIG9yRmlsdGVyKCkge1xyXG4gICAgICAgICAgICByZXR1cm4gZmlyc3QuYXBwbHkodGhpcywgYXJndW1lbnRzKSB8fCBzZWNvbmQuYXBwbHkodGhpcywgYXJndW1lbnRzKTtcclxuICAgICAgICB9XHJcbiAgICAgICAgb3JGaWx0ZXIuZGVzYyA9IGZpcnN0LmRlc2MgKyBcIiBvciBcIiArIHNlY29uZC5kZXNjO1xyXG4gICAgICAgIHJldHVybiBvckZpbHRlcjtcclxuICAgIH1cclxuICAgIGZ1bmN0aW9uIGFuZChmaXJzdCwgc2Vjb25kKSB7XHJcbiAgICAgICAgZnVuY3Rpb24gYW5kRmlsdGVyKCkge1xyXG4gICAgICAgICAgICByZXR1cm4gZmlyc3QuYXBwbHkodGhpcywgYXJndW1lbnRzKSAmJiBzZWNvbmQuYXBwbHkodGhpcywgYXJndW1lbnRzKTtcclxuICAgICAgICB9XHJcbiAgICAgICAgYW5kRmlsdGVyLmRlc2MgPSBmaXJzdC5kZXNjICsgXCIgYW5kIFwiICsgc2Vjb25kLmRlc2M7XHJcbiAgICAgICAgcmV0dXJuIGFuZEZpbHRlcjtcclxuICAgIH1cclxuICAgIGZ1bmN0aW9uIG5vdChleHByKSB7XHJcbiAgICAgICAgZnVuY3Rpb24gbm90RmlsdGVyKCkge1xyXG4gICAgICAgICAgICByZXR1cm4gIWV4cHIuYXBwbHkodGhpcywgYXJndW1lbnRzKTtcclxuICAgICAgICB9XHJcbiAgICAgICAgbm90RmlsdGVyLmRlc2MgPSBcIm5vdCBcIiArIGV4cHIuZGVzYztcclxuICAgICAgICByZXR1cm4gbm90RmlsdGVyO1xyXG4gICAgfVxyXG4gICAgZnVuY3Rpb24gYmluZGluZyhleHByKSB7XHJcbiAgICAgICAgZnVuY3Rpb24gYmluZGluZ0ZpbHRlcigpIHtcclxuICAgICAgICAgICAgcmV0dXJuIGV4cHIuYXBwbHkodGhpcywgYXJndW1lbnRzKTtcclxuICAgICAgICB9XHJcbiAgICAgICAgYmluZGluZ0ZpbHRlci5kZXNjID0gXCIoXCIgKyBleHByLmRlc2MgKyBcIilcIjtcclxuICAgICAgICByZXR1cm4gYmluZGluZ0ZpbHRlcjtcclxuICAgIH1cclxuICAgIGZ1bmN0aW9uIHRydWVGaWx0ZXIoZmxvdykge1xyXG4gICAgICAgIHJldHVybiB0cnVlO1xyXG4gICAgfVxyXG4gICAgdHJ1ZUZpbHRlci5kZXNjID0gXCJ0cnVlXCI7XHJcbiAgICBmdW5jdGlvbiBmYWxzZUZpbHRlcihmbG93KSB7XHJcbiAgICAgICAgcmV0dXJuIGZhbHNlO1xyXG4gICAgfVxyXG4gICAgZmFsc2VGaWx0ZXIuZGVzYyA9IFwiZmFsc2VcIjtcclxuXHJcbiAgICB2YXIgQVNTRVRfVFlQRVMgPSBbXHJcbiAgICAgICAgbmV3IFJlZ0V4cChcInRleHQvamF2YXNjcmlwdFwiKSxcclxuICAgICAgICBuZXcgUmVnRXhwKFwiYXBwbGljYXRpb24veC1qYXZhc2NyaXB0XCIpLFxyXG4gICAgICAgIG5ldyBSZWdFeHAoXCJhcHBsaWNhdGlvbi9qYXZhc2NyaXB0XCIpLFxyXG4gICAgICAgIG5ldyBSZWdFeHAoXCJ0ZXh0L2Nzc1wiKSxcclxuICAgICAgICBuZXcgUmVnRXhwKFwiaW1hZ2UvLipcIiksXHJcbiAgICAgICAgbmV3IFJlZ0V4cChcImFwcGxpY2F0aW9uL3gtc2hvY2t3YXZlLWZsYXNoXCIpXHJcbiAgICBdO1xyXG4gICAgZnVuY3Rpb24gYXNzZXRGaWx0ZXIoZmxvdykge1xyXG4gICAgICAgIGlmIChmbG93LnJlc3BvbnNlKSB7XHJcbiAgICAgICAgICAgIHZhciBjdCA9IGZsb3d1dGlscy5SZXNwb25zZVV0aWxzLmdldENvbnRlbnRUeXBlKGZsb3cucmVzcG9uc2UpO1xyXG4gICAgICAgICAgICB2YXIgaSA9IEFTU0VUX1RZUEVTLmxlbmd0aDtcclxuICAgICAgICAgICAgd2hpbGUgKGktLSkge1xyXG4gICAgICAgICAgICAgICAgaWYgKEFTU0VUX1RZUEVTW2ldLnRlc3QoY3QpKSB7XHJcbiAgICAgICAgICAgICAgICAgICAgcmV0dXJuIHRydWU7XHJcbiAgICAgICAgICAgICAgICB9XHJcbiAgICAgICAgICAgIH1cclxuICAgICAgICB9XHJcbiAgICAgICAgcmV0dXJuIGZhbHNlO1xyXG4gICAgfVxyXG4gICAgYXNzZXRGaWx0ZXIuZGVzYyA9IFwiaXMgYXNzZXRcIjtcclxuICAgIGZ1bmN0aW9uIHJlc3BvbnNlQ29kZShjb2RlKXtcclxuICAgICAgICBmdW5jdGlvbiByZXNwb25zZUNvZGVGaWx0ZXIoZmxvdyl7XHJcbiAgICAgICAgICAgIHJldHVybiBmbG93LnJlc3BvbnNlICYmIGZsb3cucmVzcG9uc2UuY29kZSA9PT0gY29kZTtcclxuICAgICAgICB9XHJcbiAgICAgICAgcmVzcG9uc2VDb2RlRmlsdGVyLmRlc2MgPSBcInJlc3AuIGNvZGUgaXMgXCIgKyBjb2RlO1xyXG4gICAgICAgIHJldHVybiByZXNwb25zZUNvZGVGaWx0ZXI7XHJcbiAgICB9XHJcbiAgICBmdW5jdGlvbiBkb21haW4ocmVnZXgpe1xyXG4gICAgICAgIHJlZ2V4ID0gbmV3IFJlZ0V4cChyZWdleCwgXCJpXCIpO1xyXG4gICAgICAgIGZ1bmN0aW9uIGRvbWFpbkZpbHRlcihmbG93KXtcclxuICAgICAgICAgICAgcmV0dXJuIGZsb3cucmVxdWVzdCAmJiByZWdleC50ZXN0KGZsb3cucmVxdWVzdC5ob3N0KTtcclxuICAgICAgICB9XHJcbiAgICAgICAgZG9tYWluRmlsdGVyLmRlc2MgPSBcImRvbWFpbiBtYXRjaGVzIFwiICsgcmVnZXg7XHJcbiAgICAgICAgcmV0dXJuIGRvbWFpbkZpbHRlcjtcclxuICAgIH1cclxuICAgIGZ1bmN0aW9uIGVycm9yRmlsdGVyKGZsb3cpe1xyXG4gICAgICAgIHJldHVybiAhIWZsb3cuZXJyb3I7XHJcbiAgICB9XHJcbiAgICBlcnJvckZpbHRlci5kZXNjID0gXCJoYXMgZXJyb3JcIjtcclxuICAgIGZ1bmN0aW9uIGhlYWRlcihyZWdleCl7XHJcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XHJcbiAgICAgICAgZnVuY3Rpb24gaGVhZGVyRmlsdGVyKGZsb3cpe1xyXG4gICAgICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICAgICAgKGZsb3cucmVxdWVzdCAmJiBmbG93dXRpbHMuUmVxdWVzdFV0aWxzLm1hdGNoX2hlYWRlcihmbG93LnJlcXVlc3QsIHJlZ2V4KSlcclxuICAgICAgICAgICAgICAgIHx8XHJcbiAgICAgICAgICAgICAgICAoZmxvdy5yZXNwb25zZSAmJiBmbG93dXRpbHMuUmVzcG9uc2VVdGlscy5tYXRjaF9oZWFkZXIoZmxvdy5yZXNwb25zZSwgcmVnZXgpKVxyXG4gICAgICAgICAgICApO1xyXG4gICAgICAgIH1cclxuICAgICAgICBoZWFkZXJGaWx0ZXIuZGVzYyA9IFwiaGVhZGVyIG1hdGNoZXMgXCIgKyByZWdleDtcclxuICAgICAgICByZXR1cm4gaGVhZGVyRmlsdGVyO1xyXG4gICAgfVxyXG4gICAgZnVuY3Rpb24gcmVxdWVzdEhlYWRlcihyZWdleCl7XHJcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XHJcbiAgICAgICAgZnVuY3Rpb24gcmVxdWVzdEhlYWRlckZpbHRlcihmbG93KXtcclxuICAgICAgICAgICAgcmV0dXJuIChmbG93LnJlcXVlc3QgJiYgZmxvd3V0aWxzLlJlcXVlc3RVdGlscy5tYXRjaF9oZWFkZXIoZmxvdy5yZXF1ZXN0LCByZWdleCkpO1xyXG4gICAgICAgIH1cclxuICAgICAgICByZXF1ZXN0SGVhZGVyRmlsdGVyLmRlc2MgPSBcInJlcS4gaGVhZGVyIG1hdGNoZXMgXCIgKyByZWdleDtcclxuICAgICAgICByZXR1cm4gcmVxdWVzdEhlYWRlckZpbHRlcjtcclxuICAgIH1cclxuICAgIGZ1bmN0aW9uIHJlc3BvbnNlSGVhZGVyKHJlZ2V4KXtcclxuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcclxuICAgICAgICBmdW5jdGlvbiByZXNwb25zZUhlYWRlckZpbHRlcihmbG93KXtcclxuICAgICAgICAgICAgcmV0dXJuIChmbG93LnJlc3BvbnNlICYmIGZsb3d1dGlscy5SZXNwb25zZVV0aWxzLm1hdGNoX2hlYWRlcihmbG93LnJlc3BvbnNlLCByZWdleCkpO1xyXG4gICAgICAgIH1cclxuICAgICAgICByZXNwb25zZUhlYWRlckZpbHRlci5kZXNjID0gXCJyZXNwLiBoZWFkZXIgbWF0Y2hlcyBcIiArIHJlZ2V4O1xyXG4gICAgICAgIHJldHVybiByZXNwb25zZUhlYWRlckZpbHRlcjtcclxuICAgIH1cclxuICAgIGZ1bmN0aW9uIG1ldGhvZChyZWdleCl7XHJcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XHJcbiAgICAgICAgZnVuY3Rpb24gbWV0aG9kRmlsdGVyKGZsb3cpe1xyXG4gICAgICAgICAgICByZXR1cm4gZmxvdy5yZXF1ZXN0ICYmIHJlZ2V4LnRlc3QoZmxvdy5yZXF1ZXN0Lm1ldGhvZCk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIG1ldGhvZEZpbHRlci5kZXNjID0gXCJtZXRob2QgbWF0Y2hlcyBcIiArIHJlZ2V4O1xyXG4gICAgICAgIHJldHVybiBtZXRob2RGaWx0ZXI7XHJcbiAgICB9XHJcbiAgICBmdW5jdGlvbiBub1Jlc3BvbnNlRmlsdGVyKGZsb3cpe1xyXG4gICAgICAgIHJldHVybiBmbG93LnJlcXVlc3QgJiYgIWZsb3cucmVzcG9uc2U7XHJcbiAgICB9XHJcbiAgICBub1Jlc3BvbnNlRmlsdGVyLmRlc2MgPSBcImhhcyBubyByZXNwb25zZVwiO1xyXG4gICAgZnVuY3Rpb24gcmVzcG9uc2VGaWx0ZXIoZmxvdyl7XHJcbiAgICAgICAgcmV0dXJuICEhZmxvdy5yZXNwb25zZTtcclxuICAgIH1cclxuICAgIHJlc3BvbnNlRmlsdGVyLmRlc2MgPSBcImhhcyByZXNwb25zZVwiO1xyXG5cclxuICAgIGZ1bmN0aW9uIGNvbnRlbnRUeXBlKHJlZ2V4KXtcclxuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcclxuICAgICAgICBmdW5jdGlvbiBjb250ZW50VHlwZUZpbHRlcihmbG93KXtcclxuICAgICAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgICAgIChmbG93LnJlcXVlc3QgJiYgcmVnZXgudGVzdChmbG93dXRpbHMuUmVxdWVzdFV0aWxzLmdldENvbnRlbnRUeXBlKGZsb3cucmVxdWVzdCkpKVxyXG4gICAgICAgICAgICAgICAgfHxcclxuICAgICAgICAgICAgICAgIChmbG93LnJlc3BvbnNlICYmIHJlZ2V4LnRlc3QoZmxvd3V0aWxzLlJlc3BvbnNlVXRpbHMuZ2V0Q29udGVudFR5cGUoZmxvdy5yZXNwb25zZSkpKVxyXG4gICAgICAgICAgICApO1xyXG4gICAgICAgIH1cclxuICAgICAgICBjb250ZW50VHlwZUZpbHRlci5kZXNjID0gXCJjb250ZW50IHR5cGUgbWF0Y2hlcyBcIiArIHJlZ2V4O1xyXG4gICAgICAgIHJldHVybiBjb250ZW50VHlwZUZpbHRlcjtcclxuICAgIH1cclxuICAgIGZ1bmN0aW9uIHJlcXVlc3RDb250ZW50VHlwZShyZWdleCl7XHJcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XHJcbiAgICAgICAgZnVuY3Rpb24gcmVxdWVzdENvbnRlbnRUeXBlRmlsdGVyKGZsb3cpe1xyXG4gICAgICAgICAgICByZXR1cm4gZmxvdy5yZXF1ZXN0ICYmIHJlZ2V4LnRlc3QoZmxvd3V0aWxzLlJlcXVlc3RVdGlscy5nZXRDb250ZW50VHlwZShmbG93LnJlcXVlc3QpKTtcclxuICAgICAgICB9XHJcbiAgICAgICAgcmVxdWVzdENvbnRlbnRUeXBlRmlsdGVyLmRlc2MgPSBcInJlcS4gY29udGVudCB0eXBlIG1hdGNoZXMgXCIgKyByZWdleDtcclxuICAgICAgICByZXR1cm4gcmVxdWVzdENvbnRlbnRUeXBlRmlsdGVyO1xyXG4gICAgfVxyXG4gICAgZnVuY3Rpb24gcmVzcG9uc2VDb250ZW50VHlwZShyZWdleCl7XHJcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XHJcbiAgICAgICAgZnVuY3Rpb24gcmVzcG9uc2VDb250ZW50VHlwZUZpbHRlcihmbG93KXtcclxuICAgICAgICAgICAgcmV0dXJuIGZsb3cucmVzcG9uc2UgJiYgcmVnZXgudGVzdChmbG93dXRpbHMuUmVzcG9uc2VVdGlscy5nZXRDb250ZW50VHlwZShmbG93LnJlc3BvbnNlKSk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHJlc3BvbnNlQ29udGVudFR5cGVGaWx0ZXIuZGVzYyA9IFwicmVzcC4gY29udGVudCB0eXBlIG1hdGNoZXMgXCIgKyByZWdleDtcclxuICAgICAgICByZXR1cm4gcmVzcG9uc2VDb250ZW50VHlwZUZpbHRlcjtcclxuICAgIH1cclxuICAgIGZ1bmN0aW9uIHVybChyZWdleCl7XHJcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XHJcbiAgICAgICAgZnVuY3Rpb24gdXJsRmlsdGVyKGZsb3cpe1xyXG4gICAgICAgICAgICByZXR1cm4gZmxvdy5yZXF1ZXN0ICYmIHJlZ2V4LnRlc3QoZmxvd3V0aWxzLlJlcXVlc3RVdGlscy5wcmV0dHlfdXJsKGZsb3cucmVxdWVzdCkpO1xyXG4gICAgICAgIH1cclxuICAgICAgICB1cmxGaWx0ZXIuZGVzYyA9IFwidXJsIG1hdGNoZXMgXCIgKyByZWdleDtcclxuICAgICAgICByZXR1cm4gdXJsRmlsdGVyO1xyXG4gICAgfVxyXG5cblxuICAgIHBlZyRyZXN1bHQgPSBwZWckc3RhcnRSdWxlRnVuY3Rpb24oKTtcblxuICAgIGlmIChwZWckcmVzdWx0ICE9PSBwZWckRkFJTEVEICYmIHBlZyRjdXJyUG9zID09PSBpbnB1dC5sZW5ndGgpIHtcbiAgICAgIHJldHVybiBwZWckcmVzdWx0O1xuICAgIH0gZWxzZSB7XG4gICAgICBpZiAocGVnJHJlc3VsdCAhPT0gcGVnJEZBSUxFRCAmJiBwZWckY3VyclBvcyA8IGlucHV0Lmxlbmd0aCkge1xuICAgICAgICBwZWckZmFpbCh7IHR5cGU6IFwiZW5kXCIsIGRlc2NyaXB0aW9uOiBcImVuZCBvZiBpbnB1dFwiIH0pO1xuICAgICAgfVxuXG4gICAgICB0aHJvdyBwZWckYnVpbGRFeGNlcHRpb24obnVsbCwgcGVnJG1heEZhaWxFeHBlY3RlZCwgcGVnJG1heEZhaWxQb3MpO1xuICAgIH1cbiAgfVxuXG4gIHJldHVybiB7XG4gICAgU3ludGF4RXJyb3I6IFN5bnRheEVycm9yLFxuICAgIHBhcnNlOiAgICAgICBwYXJzZVxuICB9O1xufSkoKTsiLCJ2YXIgXyA9IHJlcXVpcmUoXCJsb2Rhc2hcIik7XHJcblxyXG52YXIgX01lc3NhZ2VVdGlscyA9IHtcclxuICAgIGdldENvbnRlbnRUeXBlOiBmdW5jdGlvbiAobWVzc2FnZSkge1xyXG4gICAgICAgIHJldHVybiB0aGlzLmdldF9maXJzdF9oZWFkZXIobWVzc2FnZSwgL15Db250ZW50LVR5cGUkL2kpO1xyXG4gICAgfSxcclxuICAgIGdldF9maXJzdF9oZWFkZXI6IGZ1bmN0aW9uIChtZXNzYWdlLCByZWdleCkge1xyXG4gICAgICAgIC8vRklYTUU6IENhY2hlIEludmFsaWRhdGlvbi5cclxuICAgICAgICBpZiAoIW1lc3NhZ2UuX2hlYWRlckxvb2t1cHMpXHJcbiAgICAgICAgICAgIE9iamVjdC5kZWZpbmVQcm9wZXJ0eShtZXNzYWdlLCBcIl9oZWFkZXJMb29rdXBzXCIsIHtcclxuICAgICAgICAgICAgICAgIHZhbHVlOiB7fSxcclxuICAgICAgICAgICAgICAgIGNvbmZpZ3VyYWJsZTogZmFsc2UsXHJcbiAgICAgICAgICAgICAgICBlbnVtZXJhYmxlOiBmYWxzZSxcclxuICAgICAgICAgICAgICAgIHdyaXRhYmxlOiBmYWxzZVxyXG4gICAgICAgICAgICB9KTtcclxuICAgICAgICBpZiAoIShyZWdleCBpbiBtZXNzYWdlLl9oZWFkZXJMb29rdXBzKSkge1xyXG4gICAgICAgICAgICB2YXIgaGVhZGVyO1xyXG4gICAgICAgICAgICBmb3IgKHZhciBpID0gMDsgaSA8IG1lc3NhZ2UuaGVhZGVycy5sZW5ndGg7IGkrKykge1xyXG4gICAgICAgICAgICAgICAgaWYgKCEhbWVzc2FnZS5oZWFkZXJzW2ldWzBdLm1hdGNoKHJlZ2V4KSkge1xyXG4gICAgICAgICAgICAgICAgICAgIGhlYWRlciA9IG1lc3NhZ2UuaGVhZGVyc1tpXTtcclxuICAgICAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICBtZXNzYWdlLl9oZWFkZXJMb29rdXBzW3JlZ2V4XSA9IGhlYWRlciA/IGhlYWRlclsxXSA6IHVuZGVmaW5lZDtcclxuICAgICAgICB9XHJcbiAgICAgICAgcmV0dXJuIG1lc3NhZ2UuX2hlYWRlckxvb2t1cHNbcmVnZXhdO1xyXG4gICAgfSxcclxuICAgIG1hdGNoX2hlYWRlcjogZnVuY3Rpb24gKG1lc3NhZ2UsIHJlZ2V4KSB7XHJcbiAgICAgICAgdmFyIGhlYWRlcnMgPSBtZXNzYWdlLmhlYWRlcnM7XHJcbiAgICAgICAgdmFyIGkgPSBoZWFkZXJzLmxlbmd0aDtcclxuICAgICAgICB3aGlsZSAoaS0tKSB7XHJcbiAgICAgICAgICAgIGlmIChyZWdleC50ZXN0KGhlYWRlcnNbaV0uam9pbihcIiBcIikpKSB7XHJcbiAgICAgICAgICAgICAgICByZXR1cm4gaGVhZGVyc1tpXTtcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgIH1cclxuICAgICAgICByZXR1cm4gZmFsc2U7XHJcbiAgICB9XHJcbn07XHJcblxyXG52YXIgZGVmYXVsdFBvcnRzID0ge1xyXG4gICAgXCJodHRwXCI6IDgwLFxyXG4gICAgXCJodHRwc1wiOiA0NDNcclxufTtcclxuXHJcbnZhciBSZXF1ZXN0VXRpbHMgPSBfLmV4dGVuZChfTWVzc2FnZVV0aWxzLCB7XHJcbiAgICBwcmV0dHlfaG9zdDogZnVuY3Rpb24gKHJlcXVlc3QpIHtcclxuICAgICAgICAvL0ZJWE1FOiBBZGQgaG9zdGhlYWRlclxyXG4gICAgICAgIHJldHVybiByZXF1ZXN0Lmhvc3Q7XHJcbiAgICB9LFxyXG4gICAgcHJldHR5X3VybDogZnVuY3Rpb24gKHJlcXVlc3QpIHtcclxuICAgICAgICB2YXIgcG9ydCA9IFwiXCI7XHJcbiAgICAgICAgaWYgKGRlZmF1bHRQb3J0c1tyZXF1ZXN0LnNjaGVtZV0gIT09IHJlcXVlc3QucG9ydCkge1xyXG4gICAgICAgICAgICBwb3J0ID0gXCI6XCIgKyByZXF1ZXN0LnBvcnQ7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHJldHVybiByZXF1ZXN0LnNjaGVtZSArIFwiOi8vXCIgKyB0aGlzLnByZXR0eV9ob3N0KHJlcXVlc3QpICsgcG9ydCArIHJlcXVlc3QucGF0aDtcclxuICAgIH1cclxufSk7XHJcblxyXG52YXIgUmVzcG9uc2VVdGlscyA9IF8uZXh0ZW5kKF9NZXNzYWdlVXRpbHMsIHt9KTtcclxuXHJcblxyXG5tb2R1bGUuZXhwb3J0cyA9IHtcclxuICAgIFJlc3BvbnNlVXRpbHM6IFJlc3BvbnNlVXRpbHMsXHJcbiAgICBSZXF1ZXN0VXRpbHM6IFJlcXVlc3RVdGlsc1xyXG5cclxufSIsIlxyXG52YXIgXyA9IHJlcXVpcmUoXCJsb2Rhc2hcIik7XHJcbnZhciAkID0gcmVxdWlyZShcImpxdWVyeVwiKTtcclxudmFyIEV2ZW50RW1pdHRlciA9IHJlcXVpcmUoJ2V2ZW50cycpLkV2ZW50RW1pdHRlcjtcclxuXHJcbnZhciB1dGlscyA9IHJlcXVpcmUoXCIuLi91dGlscy5qc1wiKTtcclxudmFyIGFjdGlvbnMgPSByZXF1aXJlKFwiLi4vYWN0aW9ucy5qc1wiKTtcclxudmFyIGRpc3BhdGNoZXIgPSByZXF1aXJlKFwiLi4vZGlzcGF0Y2hlci5qc1wiKTtcclxuXHJcblxyXG5mdW5jdGlvbiBMaXN0U3RvcmUoKSB7XHJcbiAgICBFdmVudEVtaXR0ZXIuY2FsbCh0aGlzKTtcclxuICAgIHRoaXMucmVzZXQoKTtcclxufVxyXG5fLmV4dGVuZChMaXN0U3RvcmUucHJvdG90eXBlLCBFdmVudEVtaXR0ZXIucHJvdG90eXBlLCB7XHJcbiAgICBhZGQ6IGZ1bmN0aW9uIChlbGVtKSB7XHJcbiAgICAgICAgaWYgKGVsZW0uaWQgaW4gdGhpcy5fcG9zX21hcCkge1xyXG4gICAgICAgICAgICByZXR1cm47XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHRoaXMuX3Bvc19tYXBbZWxlbS5pZF0gPSB0aGlzLmxpc3QubGVuZ3RoO1xyXG4gICAgICAgIHRoaXMubGlzdC5wdXNoKGVsZW0pO1xyXG4gICAgICAgIHRoaXMuZW1pdChcImFkZFwiLCBlbGVtKTtcclxuICAgIH0sXHJcbiAgICB1cGRhdGU6IGZ1bmN0aW9uIChlbGVtKSB7XHJcbiAgICAgICAgaWYgKCEoZWxlbS5pZCBpbiB0aGlzLl9wb3NfbWFwKSkge1xyXG4gICAgICAgICAgICByZXR1cm47XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHRoaXMubGlzdFt0aGlzLl9wb3NfbWFwW2VsZW0uaWRdXSA9IGVsZW07XHJcbiAgICAgICAgdGhpcy5lbWl0KFwidXBkYXRlXCIsIGVsZW0pO1xyXG4gICAgfSxcclxuICAgIHJlbW92ZTogZnVuY3Rpb24gKGVsZW1faWQpIHtcclxuICAgICAgICBpZiAoIShlbGVtX2lkIGluIHRoaXMuX3Bvc19tYXApKSB7XHJcbiAgICAgICAgICAgIHJldHVybjtcclxuICAgICAgICB9XHJcbiAgICAgICAgdGhpcy5saXN0LnNwbGljZSh0aGlzLl9wb3NfbWFwW2VsZW1faWRdLCAxKTtcclxuICAgICAgICB0aGlzLl9idWlsZF9tYXAoKTtcclxuICAgICAgICB0aGlzLmVtaXQoXCJyZW1vdmVcIiwgZWxlbV9pZCk7XHJcbiAgICB9LFxyXG4gICAgcmVzZXQ6IGZ1bmN0aW9uIChlbGVtcykge1xyXG4gICAgICAgIHRoaXMubGlzdCA9IGVsZW1zIHx8IFtdO1xyXG4gICAgICAgIHRoaXMuX2J1aWxkX21hcCgpO1xyXG4gICAgICAgIHRoaXMuZW1pdChcInJlY2FsY3VsYXRlXCIpO1xyXG4gICAgfSxcclxuICAgIF9idWlsZF9tYXA6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLl9wb3NfbWFwID0ge307XHJcbiAgICAgICAgZm9yICh2YXIgaSA9IDA7IGkgPCB0aGlzLmxpc3QubGVuZ3RoOyBpKyspIHtcclxuICAgICAgICAgICAgdmFyIGVsZW0gPSB0aGlzLmxpc3RbaV07XHJcbiAgICAgICAgICAgIHRoaXMuX3Bvc19tYXBbZWxlbS5pZF0gPSBpO1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICBnZXQ6IGZ1bmN0aW9uIChlbGVtX2lkKSB7XHJcbiAgICAgICAgcmV0dXJuIHRoaXMubGlzdFt0aGlzLl9wb3NfbWFwW2VsZW1faWRdXTtcclxuICAgIH0sXHJcbiAgICBpbmRleDogZnVuY3Rpb24gKGVsZW1faWQpIHtcclxuICAgICAgICByZXR1cm4gdGhpcy5fcG9zX21hcFtlbGVtX2lkXTtcclxuICAgIH1cclxufSk7XHJcblxyXG5cclxuZnVuY3Rpb24gRGljdFN0b3JlKCkge1xyXG4gICAgRXZlbnRFbWl0dGVyLmNhbGwodGhpcyk7XHJcbiAgICB0aGlzLnJlc2V0KCk7XHJcbn1cclxuXy5leHRlbmQoRGljdFN0b3JlLnByb3RvdHlwZSwgRXZlbnRFbWl0dGVyLnByb3RvdHlwZSwge1xyXG4gICAgdXBkYXRlOiBmdW5jdGlvbiAoZGljdCkge1xyXG4gICAgICAgIF8ubWVyZ2UodGhpcy5kaWN0LCBkaWN0KTtcclxuICAgICAgICB0aGlzLmVtaXQoXCJyZWNhbGN1bGF0ZVwiKTtcclxuICAgIH0sXHJcbiAgICByZXNldDogZnVuY3Rpb24gKGRpY3QpIHtcclxuICAgICAgICB0aGlzLmRpY3QgPSBkaWN0IHx8IHt9O1xyXG4gICAgICAgIHRoaXMuZW1pdChcInJlY2FsY3VsYXRlXCIpO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbmZ1bmN0aW9uIExpdmVTdG9yZU1peGluKHR5cGUpIHtcclxuICAgIHRoaXMudHlwZSA9IHR5cGU7XHJcblxyXG4gICAgdGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2ggPSB1bmRlZmluZWQ7XHJcbiAgICB0aGlzLl9mZXRjaHhociA9IGZhbHNlO1xyXG5cclxuICAgIHRoaXMuaGFuZGxlID0gdGhpcy5oYW5kbGUuYmluZCh0aGlzKTtcclxuICAgIGRpc3BhdGNoZXIuQXBwRGlzcGF0Y2hlci5yZWdpc3Rlcih0aGlzLmhhbmRsZSk7XHJcblxyXG4gICAgLy8gQXZvaWQgZG91YmxlLWZldGNoIG9uIHN0YXJ0dXAuXHJcbiAgICBpZiAoISh3aW5kb3cud3MgJiYgd2luZG93LndzLnJlYWR5U3RhdGUgPT09IFdlYlNvY2tldC5DT05ORUNUSU5HKSkge1xyXG4gICAgICAgIHRoaXMuZmV0Y2goKTtcclxuICAgIH1cclxufVxyXG5fLmV4dGVuZChMaXZlU3RvcmVNaXhpbi5wcm90b3R5cGUsIHtcclxuICAgIGhhbmRsZTogZnVuY3Rpb24gKGV2ZW50KSB7XHJcbiAgICAgICAgaWYgKGV2ZW50LnR5cGUgPT09IGFjdGlvbnMuQWN0aW9uVHlwZXMuQ09OTkVDVElPTl9PUEVOKSB7XHJcbiAgICAgICAgICAgIHJldHVybiB0aGlzLmZldGNoKCk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIGlmIChldmVudC50eXBlID09PSB0aGlzLnR5cGUpIHtcclxuICAgICAgICAgICAgaWYgKGV2ZW50LmNtZCA9PT0gYWN0aW9ucy5TdG9yZUNtZHMuUkVTRVQpIHtcclxuICAgICAgICAgICAgICAgIHRoaXMuZmV0Y2goZXZlbnQuZGF0YSk7XHJcbiAgICAgICAgICAgIH0gZWxzZSBpZiAodGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2gpIHtcclxuICAgICAgICAgICAgICAgIGNvbnNvbGUubG9nKFwiZGVmZXIgdXBkYXRlXCIsIGV2ZW50KTtcclxuICAgICAgICAgICAgICAgIHRoaXMuX3VwZGF0ZXNfYmVmb3JlX2ZldGNoLnB1c2goZXZlbnQpO1xyXG4gICAgICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICAgICAgdGhpc1tldmVudC5jbWRdKGV2ZW50LmRhdGEpO1xyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIGNsb3NlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgZGlzcGF0Y2hlci5BcHBEaXNwYXRjaGVyLnVucmVnaXN0ZXIodGhpcy5oYW5kbGUpO1xyXG4gICAgfSxcclxuICAgIGZldGNoOiBmdW5jdGlvbiAoZGF0YSkge1xyXG4gICAgICAgIGNvbnNvbGUubG9nKFwiZmV0Y2ggXCIgKyB0aGlzLnR5cGUpO1xyXG4gICAgICAgIGlmICh0aGlzLl9mZXRjaHhocikge1xyXG4gICAgICAgICAgICB0aGlzLl9mZXRjaHhoci5hYm9ydCgpO1xyXG4gICAgICAgIH1cclxuICAgICAgICB0aGlzLl91cGRhdGVzX2JlZm9yZV9mZXRjaCA9IFtdOyAvLyAoSlM6IGVtcHR5IGFycmF5IGlzIHRydWUpXHJcbiAgICAgICAgaWYgKGRhdGEpIHtcclxuICAgICAgICAgICAgdGhpcy5oYW5kbGVfZmV0Y2goZGF0YSk7XHJcbiAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgdGhpcy5fZmV0Y2h4aHIgPSAkLmdldEpTT04oXCIvXCIgKyB0aGlzLnR5cGUpXHJcbiAgICAgICAgICAgICAgICAuZG9uZShmdW5jdGlvbiAobWVzc2FnZSkge1xyXG4gICAgICAgICAgICAgICAgICAgIHRoaXMuaGFuZGxlX2ZldGNoKG1lc3NhZ2UuZGF0YSk7XHJcbiAgICAgICAgICAgICAgICB9LmJpbmQodGhpcykpXHJcbiAgICAgICAgICAgICAgICAuZmFpbChmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgICAgICAgICAgICAgRXZlbnRMb2dBY3Rpb25zLmFkZF9ldmVudChcIkNvdWxkIG5vdCBmZXRjaCBcIiArIHRoaXMudHlwZSk7XHJcbiAgICAgICAgICAgICAgICB9LmJpbmQodGhpcykpO1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICBoYW5kbGVfZmV0Y2g6IGZ1bmN0aW9uIChkYXRhKSB7XHJcbiAgICAgICAgdGhpcy5fZmV0Y2h4aHIgPSBmYWxzZTtcclxuICAgICAgICBjb25zb2xlLmxvZyh0aGlzLnR5cGUgKyBcIiBmZXRjaGVkLlwiLCB0aGlzLl91cGRhdGVzX2JlZm9yZV9mZXRjaCk7XHJcbiAgICAgICAgdGhpcy5yZXNldChkYXRhKTtcclxuICAgICAgICB2YXIgdXBkYXRlcyA9IHRoaXMuX3VwZGF0ZXNfYmVmb3JlX2ZldGNoO1xyXG4gICAgICAgIHRoaXMuX3VwZGF0ZXNfYmVmb3JlX2ZldGNoID0gZmFsc2U7XHJcbiAgICAgICAgZm9yICh2YXIgaSA9IDA7IGkgPCB1cGRhdGVzLmxlbmd0aDsgaSsrKSB7XHJcbiAgICAgICAgICAgIHRoaXMuaGFuZGxlKHVwZGF0ZXNbaV0pO1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbn0pO1xyXG5cclxuZnVuY3Rpb24gTGl2ZUxpc3RTdG9yZSh0eXBlKSB7XHJcbiAgICBMaXN0U3RvcmUuY2FsbCh0aGlzKTtcclxuICAgIExpdmVTdG9yZU1peGluLmNhbGwodGhpcywgdHlwZSk7XHJcbn1cclxuXy5leHRlbmQoTGl2ZUxpc3RTdG9yZS5wcm90b3R5cGUsIExpc3RTdG9yZS5wcm90b3R5cGUsIExpdmVTdG9yZU1peGluLnByb3RvdHlwZSk7XHJcblxyXG5mdW5jdGlvbiBMaXZlRGljdFN0b3JlKHR5cGUpIHtcclxuICAgIERpY3RTdG9yZS5jYWxsKHRoaXMpO1xyXG4gICAgTGl2ZVN0b3JlTWl4aW4uY2FsbCh0aGlzLCB0eXBlKTtcclxufVxyXG5fLmV4dGVuZChMaXZlRGljdFN0b3JlLnByb3RvdHlwZSwgRGljdFN0b3JlLnByb3RvdHlwZSwgTGl2ZVN0b3JlTWl4aW4ucHJvdG90eXBlKTtcclxuXHJcblxyXG5mdW5jdGlvbiBGbG93U3RvcmUoKSB7XHJcbiAgICByZXR1cm4gbmV3IExpdmVMaXN0U3RvcmUoYWN0aW9ucy5BY3Rpb25UeXBlcy5GTE9XX1NUT1JFKTtcclxufVxyXG5cclxuZnVuY3Rpb24gU2V0dGluZ3NTdG9yZSgpIHtcclxuICAgIHJldHVybiBuZXcgTGl2ZURpY3RTdG9yZShhY3Rpb25zLkFjdGlvblR5cGVzLlNFVFRJTkdTX1NUT1JFKTtcclxufVxyXG5cclxuZnVuY3Rpb24gRXZlbnRMb2dTdG9yZSgpIHtcclxuICAgIExpdmVMaXN0U3RvcmUuY2FsbCh0aGlzLCBhY3Rpb25zLkFjdGlvblR5cGVzLkVWRU5UX1NUT1JFKTtcclxufVxyXG5fLmV4dGVuZChFdmVudExvZ1N0b3JlLnByb3RvdHlwZSwgTGl2ZUxpc3RTdG9yZS5wcm90b3R5cGUsIHtcclxuICAgIGZldGNoOiBmdW5jdGlvbigpe1xyXG4gICAgICAgIExpdmVMaXN0U3RvcmUucHJvdG90eXBlLmZldGNoLmFwcGx5KHRoaXMsIGFyZ3VtZW50cyk7XHJcblxyXG4gICAgICAgIC8vIE1ha2Ugc3VyZSB0byBkaXNwbGF5IHVwZGF0ZXMgZXZlbiBpZiBmZXRjaGluZyBhbGwgZXZlbnRzIGZhaWxlZC5cclxuICAgICAgICAvLyBUaGlzIHdheSwgd2UgY2FuIHNlbmQgXCJmZXRjaCBmYWlsZWRcIiBsb2cgbWVzc2FnZXMgdG8gdGhlIGxvZy5cclxuICAgICAgICBpZih0aGlzLl9mZXRjaHhocil7XHJcbiAgICAgICAgICAgIHRoaXMuX2ZldGNoeGhyLmZhaWwoZnVuY3Rpb24oKXtcclxuICAgICAgICAgICAgICAgIHRoaXMuaGFuZGxlX2ZldGNoKG51bGwpO1xyXG4gICAgICAgICAgICB9LmJpbmQodGhpcykpO1xyXG4gICAgICAgIH1cclxuICAgIH1cclxufSk7XHJcblxyXG5cclxubW9kdWxlLmV4cG9ydHMgPSB7XHJcbiAgICBFdmVudExvZ1N0b3JlOiBFdmVudExvZ1N0b3JlLFxyXG4gICAgU2V0dGluZ3NTdG9yZTogU2V0dGluZ3NTdG9yZSxcclxuICAgIEZsb3dTdG9yZTogRmxvd1N0b3JlXHJcbn07IiwiXHJcbnZhciBFdmVudEVtaXR0ZXIgPSByZXF1aXJlKCdldmVudHMnKS5FdmVudEVtaXR0ZXI7XHJcbnZhciBfID0gcmVxdWlyZShcImxvZGFzaFwiKTtcclxuXHJcblxyXG52YXIgdXRpbHMgPSByZXF1aXJlKFwiLi4vdXRpbHMuanNcIik7XHJcblxyXG5mdW5jdGlvbiBTb3J0QnlTdG9yZU9yZGVyKGVsZW0pIHtcclxuICAgIHJldHVybiB0aGlzLnN0b3JlLmluZGV4KGVsZW0uaWQpO1xyXG59XHJcblxyXG52YXIgZGVmYXVsdF9zb3J0ID0gU29ydEJ5U3RvcmVPcmRlcjtcclxudmFyIGRlZmF1bHRfZmlsdCA9IGZ1bmN0aW9uKGVsZW0pe1xyXG4gICAgcmV0dXJuIHRydWU7XHJcbn07XHJcblxyXG5mdW5jdGlvbiBTdG9yZVZpZXcoc3RvcmUsIGZpbHQsIHNvcnRmdW4pIHtcclxuICAgIEV2ZW50RW1pdHRlci5jYWxsKHRoaXMpO1xyXG4gICAgZmlsdCA9IGZpbHQgfHwgZGVmYXVsdF9maWx0O1xyXG4gICAgc29ydGZ1biA9IHNvcnRmdW4gfHwgZGVmYXVsdF9zb3J0O1xyXG5cclxuICAgIHRoaXMuc3RvcmUgPSBzdG9yZTtcclxuXHJcbiAgICB0aGlzLmFkZCA9IHRoaXMuYWRkLmJpbmQodGhpcyk7XHJcbiAgICB0aGlzLnVwZGF0ZSA9IHRoaXMudXBkYXRlLmJpbmQodGhpcyk7XHJcbiAgICB0aGlzLnJlbW92ZSA9IHRoaXMucmVtb3ZlLmJpbmQodGhpcyk7XHJcbiAgICB0aGlzLnJlY2FsY3VsYXRlID0gdGhpcy5yZWNhbGN1bGF0ZS5iaW5kKHRoaXMpO1xyXG4gICAgdGhpcy5zdG9yZS5hZGRMaXN0ZW5lcihcImFkZFwiLCB0aGlzLmFkZCk7XHJcbiAgICB0aGlzLnN0b3JlLmFkZExpc3RlbmVyKFwidXBkYXRlXCIsIHRoaXMudXBkYXRlKTtcclxuICAgIHRoaXMuc3RvcmUuYWRkTGlzdGVuZXIoXCJyZW1vdmVcIiwgdGhpcy5yZW1vdmUpO1xyXG4gICAgdGhpcy5zdG9yZS5hZGRMaXN0ZW5lcihcInJlY2FsY3VsYXRlXCIsIHRoaXMucmVjYWxjdWxhdGUpO1xyXG5cclxuICAgIHRoaXMucmVjYWxjdWxhdGUoZmlsdCwgc29ydGZ1bik7XHJcbn1cclxuXHJcbl8uZXh0ZW5kKFN0b3JlVmlldy5wcm90b3R5cGUsIEV2ZW50RW1pdHRlci5wcm90b3R5cGUsIHtcclxuICAgIGNsb3NlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdGhpcy5zdG9yZS5yZW1vdmVMaXN0ZW5lcihcImFkZFwiLCB0aGlzLmFkZCk7XHJcbiAgICAgICAgdGhpcy5zdG9yZS5yZW1vdmVMaXN0ZW5lcihcInVwZGF0ZVwiLCB0aGlzLnVwZGF0ZSk7XHJcbiAgICAgICAgdGhpcy5zdG9yZS5yZW1vdmVMaXN0ZW5lcihcInJlbW92ZVwiLCB0aGlzLnJlbW92ZSk7XHJcbiAgICAgICAgdGhpcy5zdG9yZS5yZW1vdmVMaXN0ZW5lcihcInJlY2FsY3VsYXRlXCIsIHRoaXMucmVjYWxjdWxhdGUpO1xyXG4gICAgICAgIH0sXHJcbiAgICAgICAgcmVjYWxjdWxhdGU6IGZ1bmN0aW9uIChmaWx0LCBzb3J0ZnVuKSB7XHJcbiAgICAgICAgaWYgKGZpbHQpIHtcclxuICAgICAgICAgICAgdGhpcy5maWx0ID0gZmlsdC5iaW5kKHRoaXMpO1xyXG4gICAgICAgIH1cclxuICAgICAgICBpZiAoc29ydGZ1bikge1xyXG4gICAgICAgICAgICB0aGlzLnNvcnRmdW4gPSBzb3J0ZnVuLmJpbmQodGhpcyk7XHJcbiAgICAgICAgfVxyXG5cclxuICAgICAgICB0aGlzLmxpc3QgPSB0aGlzLnN0b3JlLmxpc3QuZmlsdGVyKHRoaXMuZmlsdCk7XHJcbiAgICAgICAgdGhpcy5saXN0LnNvcnQoZnVuY3Rpb24gKGEsIGIpIHtcclxuICAgICAgICAgICAgcmV0dXJuIHRoaXMuc29ydGZ1bihhKSAtIHRoaXMuc29ydGZ1bihiKTtcclxuICAgICAgICB9LmJpbmQodGhpcykpO1xyXG4gICAgICAgIHRoaXMuZW1pdChcInJlY2FsY3VsYXRlXCIpO1xyXG4gICAgfSxcclxuICAgIGluZGV4OiBmdW5jdGlvbiAoZWxlbSkge1xyXG4gICAgICAgIHJldHVybiBfLnNvcnRlZEluZGV4KHRoaXMubGlzdCwgZWxlbSwgdGhpcy5zb3J0ZnVuKTtcclxuICAgIH0sXHJcbiAgICBhZGQ6IGZ1bmN0aW9uIChlbGVtKSB7XHJcbiAgICAgICAgaWYgKHRoaXMuZmlsdChlbGVtKSkge1xyXG4gICAgICAgICAgICB2YXIgaWR4ID0gdGhpcy5pbmRleChlbGVtKTtcclxuICAgICAgICAgICAgaWYgKGlkeCA9PT0gdGhpcy5saXN0Lmxlbmd0aCkgeyAvL2hhcHBlbnMgb2Z0ZW4sIC5wdXNoIGlzIHdheSBmYXN0ZXIuXHJcbiAgICAgICAgICAgICAgICB0aGlzLmxpc3QucHVzaChlbGVtKTtcclxuICAgICAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgICAgIHRoaXMubGlzdC5zcGxpY2UoaWR4LCAwLCBlbGVtKTtcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICB0aGlzLmVtaXQoXCJhZGRcIiwgZWxlbSwgaWR4KTtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgdXBkYXRlOiBmdW5jdGlvbiAoZWxlbSkge1xyXG4gICAgICAgIHZhciBpZHg7XHJcbiAgICAgICAgdmFyIGkgPSB0aGlzLmxpc3QubGVuZ3RoO1xyXG4gICAgICAgIC8vIFNlYXJjaCBmcm9tIHRoZSBiYWNrLCB3ZSB1c3VhbGx5IHVwZGF0ZSB0aGUgbGF0ZXN0IGVudHJpZXMuXHJcbiAgICAgICAgd2hpbGUgKGktLSkge1xyXG4gICAgICAgICAgICBpZiAodGhpcy5saXN0W2ldLmlkID09PSBlbGVtLmlkKSB7XHJcbiAgICAgICAgICAgICAgICBpZHggPSBpO1xyXG4gICAgICAgICAgICAgICAgYnJlYWs7XHJcbiAgICAgICAgICAgIH1cclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIGlmIChpZHggPT09IC0xKSB7IC8vbm90IGNvbnRhaW5lZCBpbiBsaXN0XHJcbiAgICAgICAgICAgIHRoaXMuYWRkKGVsZW0pO1xyXG4gICAgICAgIH0gZWxzZSBpZiAoIXRoaXMuZmlsdChlbGVtKSkge1xyXG4gICAgICAgICAgICB0aGlzLnJlbW92ZShlbGVtLmlkKTtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICBpZiAodGhpcy5zb3J0ZnVuKHRoaXMubGlzdFtpZHhdKSAhPT0gdGhpcy5zb3J0ZnVuKGVsZW0pKSB7IC8vc29ydHBvcyBoYXMgY2hhbmdlZFxyXG4gICAgICAgICAgICAgICAgdGhpcy5yZW1vdmUodGhpcy5saXN0W2lkeF0pO1xyXG4gICAgICAgICAgICAgICAgdGhpcy5hZGQoZWxlbSk7XHJcbiAgICAgICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgICAgICB0aGlzLmxpc3RbaWR4XSA9IGVsZW07XHJcbiAgICAgICAgICAgICAgICB0aGlzLmVtaXQoXCJ1cGRhdGVcIiwgZWxlbSwgaWR4KTtcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICByZW1vdmU6IGZ1bmN0aW9uIChlbGVtX2lkKSB7XHJcbiAgICAgICAgdmFyIGlkeCA9IHRoaXMubGlzdC5sZW5ndGg7XHJcbiAgICAgICAgd2hpbGUgKGlkeC0tKSB7XHJcbiAgICAgICAgICAgIGlmICh0aGlzLmxpc3RbaWR4XS5pZCA9PT0gZWxlbV9pZCkge1xyXG4gICAgICAgICAgICAgICAgdGhpcy5saXN0LnNwbGljZShpZHgsIDEpO1xyXG4gICAgICAgICAgICAgICAgdGhpcy5lbWl0KFwicmVtb3ZlXCIsIGVsZW1faWQsIGlkeCk7XHJcbiAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgIH1cclxuICAgIH1cclxufSk7XHJcblxyXG5tb2R1bGUuZXhwb3J0cyA9IHtcclxuICAgIFN0b3JlVmlldzogU3RvcmVWaWV3XHJcbn07IiwidmFyICQgPSByZXF1aXJlKFwianF1ZXJ5XCIpO1xyXG5cclxuXHJcbnZhciBLZXkgPSB7XHJcbiAgICBVUDogMzgsXHJcbiAgICBET1dOOiA0MCxcclxuICAgIFBBR0VfVVA6IDMzLFxyXG4gICAgUEFHRV9ET1dOOiAzNCxcclxuICAgIEhPTUU6IDM2LFxyXG4gICAgRU5EOiAzNSxcclxuICAgIExFRlQ6IDM3LFxyXG4gICAgUklHSFQ6IDM5LFxyXG4gICAgRU5URVI6IDEzLFxyXG4gICAgRVNDOiAyNyxcclxuICAgIFRBQjogOSxcclxuICAgIFNQQUNFOiAzMixcclxuICAgIEJBQ0tTUEFDRTogOCxcclxufTtcclxuLy8gQWRkIEEtWlxyXG5mb3IgKHZhciBpID0gNjU7IGkgPD0gOTA7IGkrKykge1xyXG4gICAgS2V5W1N0cmluZy5mcm9tQ2hhckNvZGUoaSldID0gaTtcclxufVxyXG5cclxuXHJcbnZhciBmb3JtYXRTaXplID0gZnVuY3Rpb24gKGJ5dGVzKSB7XHJcbiAgICBpZiAoYnl0ZXMgPT09IDApXHJcbiAgICAgICAgcmV0dXJuIFwiMFwiO1xyXG4gICAgdmFyIHByZWZpeCA9IFtcImJcIiwgXCJrYlwiLCBcIm1iXCIsIFwiZ2JcIiwgXCJ0YlwiXTtcclxuICAgIGZvciAodmFyIGkgPSAwOyBpIDwgcHJlZml4Lmxlbmd0aDsgaSsrKXtcclxuICAgICAgICBpZiAoTWF0aC5wb3coMTAyNCwgaSArIDEpID4gYnl0ZXMpe1xyXG4gICAgICAgICAgICBicmVhaztcclxuICAgICAgICB9XHJcbiAgICB9XHJcbiAgICB2YXIgcHJlY2lzaW9uO1xyXG4gICAgaWYgKGJ5dGVzJU1hdGgucG93KDEwMjQsIGkpID09PSAwKVxyXG4gICAgICAgIHByZWNpc2lvbiA9IDA7XHJcbiAgICBlbHNlXHJcbiAgICAgICAgcHJlY2lzaW9uID0gMTtcclxuICAgIHJldHVybiAoYnl0ZXMvTWF0aC5wb3coMTAyNCwgaSkpLnRvRml4ZWQocHJlY2lzaW9uKSArIHByZWZpeFtpXTtcclxufTtcclxuXHJcblxyXG52YXIgZm9ybWF0VGltZURlbHRhID0gZnVuY3Rpb24gKG1pbGxpc2Vjb25kcykge1xyXG4gICAgdmFyIHRpbWUgPSBtaWxsaXNlY29uZHM7XHJcbiAgICB2YXIgcHJlZml4ID0gW1wibXNcIiwgXCJzXCIsIFwibWluXCIsIFwiaFwiXTtcclxuICAgIHZhciBkaXYgPSBbMTAwMCwgNjAsIDYwXTtcclxuICAgIHZhciBpID0gMDtcclxuICAgIHdoaWxlIChNYXRoLmFicyh0aW1lKSA+PSBkaXZbaV0gJiYgaSA8IGRpdi5sZW5ndGgpIHtcclxuICAgICAgICB0aW1lID0gdGltZSAvIGRpdltpXTtcclxuICAgICAgICBpKys7XHJcbiAgICB9XHJcbiAgICByZXR1cm4gTWF0aC5yb3VuZCh0aW1lKSArIHByZWZpeFtpXTtcclxufTtcclxuXHJcblxyXG52YXIgZm9ybWF0VGltZVN0YW1wID0gZnVuY3Rpb24gKHNlY29uZHMpIHtcclxuICAgIHZhciB0cyA9IChuZXcgRGF0ZShzZWNvbmRzICogMTAwMCkpLnRvSVNPU3RyaW5nKCk7XHJcbiAgICByZXR1cm4gdHMucmVwbGFjZShcIlRcIiwgXCIgXCIpLnJlcGxhY2UoXCJaXCIsIFwiXCIpO1xyXG59O1xyXG5cclxuXHJcbmZ1bmN0aW9uIGdldENvb2tpZShuYW1lKSB7XHJcbiAgICB2YXIgciA9IGRvY3VtZW50LmNvb2tpZS5tYXRjaChcIlxcXFxiXCIgKyBuYW1lICsgXCI9KFteO10qKVxcXFxiXCIpO1xyXG4gICAgcmV0dXJuIHIgPyByWzFdIDogdW5kZWZpbmVkO1xyXG59XHJcbnZhciB4c3JmID0gJC5wYXJhbSh7X3hzcmY6IGdldENvb2tpZShcIl94c3JmXCIpfSk7XHJcblxyXG4vL1Rvcm5hZG8gWFNSRiBQcm90ZWN0aW9uLlxyXG4kLmFqYXhQcmVmaWx0ZXIoZnVuY3Rpb24gKG9wdGlvbnMpIHtcclxuICAgIGlmIChbXCJwb3N0XCIsIFwicHV0XCIsIFwiZGVsZXRlXCJdLmluZGV4T2Yob3B0aW9ucy50eXBlLnRvTG93ZXJDYXNlKCkpID49IDAgJiYgb3B0aW9ucy51cmxbMF0gPT09IFwiL1wiKSB7XHJcbiAgICAgICAgaWYgKG9wdGlvbnMuZGF0YSkge1xyXG4gICAgICAgICAgICBvcHRpb25zLmRhdGEgKz0gKFwiJlwiICsgeHNyZik7XHJcbiAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgb3B0aW9ucy5kYXRhID0geHNyZjtcclxuICAgICAgICB9XHJcbiAgICB9XHJcbn0pO1xyXG4vLyBMb2cgQUpBWCBFcnJvcnNcclxuJChkb2N1bWVudCkuYWpheEVycm9yKGZ1bmN0aW9uIChldmVudCwganFYSFIsIGFqYXhTZXR0aW5ncywgdGhyb3duRXJyb3IpIHtcclxuICAgIHZhciBtZXNzYWdlID0ganFYSFIucmVzcG9uc2VUZXh0O1xyXG4gICAgY29uc29sZS5lcnJvcihtZXNzYWdlLCBhcmd1bWVudHMpO1xyXG4gICAgRXZlbnRMb2dBY3Rpb25zLmFkZF9ldmVudCh0aHJvd25FcnJvciArIFwiOiBcIiArIG1lc3NhZ2UpO1xyXG4gICAgd2luZG93LmFsZXJ0KG1lc3NhZ2UpO1xyXG59KTtcclxuXHJcbm1vZHVsZS5leHBvcnRzID0ge1xyXG4gICAgZm9ybWF0U2l6ZTogZm9ybWF0U2l6ZSxcclxuICAgIGZvcm1hdFRpbWVEZWx0YTogZm9ybWF0VGltZURlbHRhLFxyXG4gICAgZm9ybWF0VGltZVN0YW1wOiBmb3JtYXRUaW1lU3RhbXAsXHJcbiAgICBLZXk6IEtleVxyXG59OyJdfQ==
