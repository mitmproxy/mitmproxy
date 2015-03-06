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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIm5vZGVfbW9kdWxlc1xcYnJvd3NlcmlmeVxcbm9kZV9tb2R1bGVzXFxicm93c2VyLXBhY2tcXF9wcmVsdWRlLmpzIiwibm9kZV9tb2R1bGVzXFxicm93c2VyaWZ5XFxub2RlX21vZHVsZXNcXGV2ZW50c1xcZXZlbnRzLmpzIiwiRDpcXGdpdGh1YlxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGFjdGlvbnMuanMiLCJEOlxcZ2l0aHViXFxtaXRtcHJveHlcXHdlYlxcc3JjXFxqc1xcYXBwLmpzIiwiRDpcXGdpdGh1YlxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGNvbXBvbmVudHNcXGNvbW1vbi5qcyIsIkQ6XFxnaXRodWJcXG1pdG1wcm94eVxcd2ViXFxzcmNcXGpzXFxjb21wb25lbnRzXFxldmVudGxvZy5qcyIsIkQ6XFxnaXRodWJcXG1pdG1wcm94eVxcd2ViXFxzcmNcXGpzXFxjb21wb25lbnRzXFxmbG93ZGV0YWlsLmpzIiwiRDpcXGdpdGh1YlxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGNvbXBvbmVudHNcXGZsb3d0YWJsZS1jb2x1bW5zLmpzIiwiRDpcXGdpdGh1YlxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGNvbXBvbmVudHNcXGZsb3d0YWJsZS5qcyIsIkQ6XFxnaXRodWJcXG1pdG1wcm94eVxcd2ViXFxzcmNcXGpzXFxjb21wb25lbnRzXFxmb290ZXIuanMiLCJEOlxcZ2l0aHViXFxtaXRtcHJveHlcXHdlYlxcc3JjXFxqc1xcY29tcG9uZW50c1xcaGVhZGVyLmpzIiwiRDpcXGdpdGh1YlxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGNvbXBvbmVudHNcXG1haW52aWV3LmpzIiwiRDpcXGdpdGh1YlxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGNvbXBvbmVudHNcXHByb3h5YXBwLmpzIiwiRDpcXGdpdGh1YlxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGNvbXBvbmVudHNcXHZpcnR1YWxzY3JvbGwuanMiLCJEOlxcZ2l0aHViXFxtaXRtcHJveHlcXHdlYlxcc3JjXFxqc1xcY29ubmVjdGlvbi5qcyIsIkQ6XFxnaXRodWJcXG1pdG1wcm94eVxcd2ViXFxzcmNcXGpzXFxkaXNwYXRjaGVyLmpzIiwiRDpcXGdpdGh1YlxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXGZpbHRcXGZpbHQuanMiLCJEOlxcZ2l0aHViXFxtaXRtcHJveHlcXHdlYlxcc3JjXFxqc1xcZmxvd1xcdXRpbHMuanMiLCJEOlxcZ2l0aHViXFxtaXRtcHJveHlcXHdlYlxcc3JjXFxqc1xcc3RvcmVcXHN0b3JlLmpzIiwiRDpcXGdpdGh1YlxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXHN0b3JlXFx2aWV3LmpzIiwiRDpcXGdpdGh1YlxcbWl0bXByb3h5XFx3ZWJcXHNyY1xcanNcXHV0aWxzLmpzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBO0FDQUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FB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LENBQUM7Q0FDaEI7QUFDRCxDQUFDLENBQUMsTUFBTSxDQUFDLFNBQVMsQ0FBQyxTQUFTLEVBQUUsWUFBWSxDQUFDLFNBQVMsRUFBRTtJQUNsRCxHQUFHLEVBQUUsVUFBVSxJQUFJLEVBQUU7UUFDakIsSUFBSSxJQUFJLENBQUMsRUFBRSxJQUFJLElBQUksQ0FBQyxRQUFRLEVBQUU7WUFDMUIsT0FBTztTQUNWO1FBQ0QsSUFBSSxDQUFDLFFBQVEsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLEdBQUcsSUFBSSxDQUFDLElBQUksQ0FBQyxNQUFNLENBQUM7UUFDMUMsSUFBSSxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUM7UUFDckIsSUFBSSxDQUFDLElBQUksQ0FBQyxLQUFLLEVBQUUsSUFBSSxDQUFDLENBQUM7S0FDMUI7SUFDRCxNQUFNLEVBQUUsVUFBVSxJQUFJLEVBQUU7UUFDcEIsSUFBSSxFQUFFLElBQUksQ0FBQyxFQUFFLElBQUksSUFBSSxDQUFDLFFBQVEsQ0FBQyxFQUFFO1lBQzdCLE9BQU87U0FDVjtRQUNELElBQUksQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLFFBQVEsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsR0FBRyxJQUFJLENBQUM7UUFDekMsSUFBSSxDQUFDLElBQUksQ0FBQyxRQUFRLEVBQUUsSUFBSSxDQUFDLENBQUM7S0FDN0I7SUFDRCxNQUFNLEVBQUUsVUFBVSxPQUFPLEVBQUU7UUFDdkIsSUFBSSxFQUFFLE9BQU8sSUFBSSxJQUFJLENBQUMsUUFBUSxDQUFDLEVBQUU7WUFDN0IsT0FBTztTQUNWO1FBQ0QsSUFBSSxDQUFDLElBQUksQ0FBQyxNQUFNLENBQUMsSUFBSSxDQUFDLFFBQVEsQ0FBQyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQztRQUM1QyxJQUFJLENBQUMsVUFBVSxFQUFFLENBQUM7UUFDbEIsSUFBSSxDQUFDLElBQUksQ0FBQyxRQUFRLEVBQUUsT0FBTyxDQUFDLENBQUM7S0FDaEM7SUFDRCxLQUFLLEVBQUUsVUFB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LFNBQVMsQ0FBQyxVQUFVLEtBQUssRUFBRSxLQUFLLEVBQUUsWUFBWSxFQUFFLFdBQVcsRUFBRTtJQUNyRSxJQUFJLE9BQU8sR0FBRyxLQUFLLENBQUMsWUFBWSxDQUFDO0lBQ2pDLE9BQU8sQ0FBQyxLQUFLLENBQUMsT0FBTyxFQUFFLFNBQVMsQ0FBQyxDQUFDO0lBQ2xDLGVBQWUsQ0FBQyxTQUFTLENBQUMsV0FBVyxHQUFHLElBQUksR0FBRyxPQUFPLENBQUMsQ0FBQztJQUN4RCxNQUFNLENBQUMsS0FBSyxDQUFDLE9BQU8sQ0FBQyxDQUFDO0FBQzFCLENBQUMsQ0FBQyxDQUFDOztBQUVILE1BQU0sQ0FBQyxPQUFPLEdBQUc7SUFDYixVQUFVLEVBQUUsVUFBVTtJQUN0QixlQUFlLEVBQUUsZUFBZTtJQUNoQyxlQUFlLEVBQUUsZUFBZTtJQUNoQyxHQUFHLEVBQUUsR0FBRztDQUNYIiwiZmlsZSI6ImdlbmVyYXRlZC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzQ29udGVudCI6WyIoZnVuY3Rpb24gZSh0LG4scil7ZnVuY3Rpb24gcyhvLHUpe2lmKCFuW29dKXtpZighdFtvXSl7dmFyIGE9dHlwZW9mIHJlcXVpcmU9PVwiZnVuY3Rpb25cIiYmcmVxdWlyZTtpZighdSYmYSlyZXR1cm4gYShvLCEwKTtpZihpKXJldHVybiBpKG8sITApO3ZhciBmPW5ldyBFcnJvcihcIkNhbm5vdCBmaW5kIG1vZHVsZSAnXCIrbytcIidcIik7dGhyb3cgZi5jb2RlPVwiTU9EVUxFX05PVF9GT1VORFwiLGZ9dmFyIGw9bltvXT17ZXhwb3J0czp7fX07dFtvXVswXS5jYWxsKGwuZXhwb3J0cyxmdW5jdGlvbihlKXt2YXIgbj10W29dWzFdW2VdO3JldHVybiBzKG4/bjplKX0sbCxsLmV4cG9ydHMsZSx0LG4scil9cmV0dXJuIG5bb10uZXhwb3J0c312YXIgaT10eXBlb2YgcmVxdWlyZT09XCJmdW5jdGlvblwiJiZyZXF1aXJlO2Zvcih2YXIgbz0wO288ci5sZW5ndGg7bysrKXMocltvXSk7cmV0dXJuIHN9KSIsIi8vIENvcHlyaWdodCBKb3llbnQsIEluYy4gYW5kIG90aGVyIE5vZGUgY29udHJpYnV0b3JzLlxuLy9cbi8vIFBlcm1pc3Npb24gaXMgaGVyZWJ5IGdyYW50ZWQsIGZyZWUgb2YgY2hhcmdlLCB0byBhbnkgcGVyc29uIG9idGFpbmluZyBhXG4vLyBjb3B5IG9mIHRoaXMgc29mdHdhcmUgYW5kIGFzc29jaWF0ZWQgZG9jdW1lbnRhdGlvbiBmaWxlcyAodGhlXG4vLyBcIlNvZnR3YXJlXCIpLCB0byBkZWFsIGluIHRoZSBTb2Z0d2FyZSB3aXRob3V0IHJlc3RyaWN0aW9uLCBpbmNsdWRpbmdcbi8vIHdpdGhvdXQgbGltaXRhdGlvbiB0aGUgcmlnaHRzIHRvIHVzZSwgY29weSwgbW9kaWZ5LCBtZXJnZSwgcHVibGlzaCxcbi8vIGRpc3RyaWJ1dGUsIHN1YmxpY2Vuc2UsIGFuZC9vciBzZWxsIGNvcGllcyBvZiB0aGUgU29mdHdhcmUsIGFuZCB0byBwZXJtaXRcbi8vIHBlcnNvbnMgdG8gd2hvbSB0aGUgU29mdHdhcmUgaXMgZnVybmlzaGVkIHRvIGRvIHNvLCBzdWJqZWN0IHRvIHRoZVxuLy8gZm9sbG93aW5nIGNvbmRpdGlvbnM6XG4vL1xuLy8gVGhlIGFib3ZlIGNvcHlyaWdodCBub3RpY2UgYW5kIHRoaXMgcGVybWlzc2lvbiBub3RpY2Ugc2hhbGwgYmUgaW5jbHVkZWRcbi8vIGluIGFsbCBjb3BpZXMgb3Igc3Vic3RhbnRpYWwgcG9ydGlvbnMgb2YgdGhlIFNvZnR3YXJlLlxuLy9cbi8vIFRIRSBTT0ZUV0FSRSBJUyBQUk9WSURFRCBcIkFTIElTXCIsIFdJVEhPVVQgV0FSUkFOVFkgT0YgQU5ZIEtJTkQsIEVYUFJFU1Ncbi8vIE9SIElNUExJRUQsIElOQ0xVRElORyBCVVQgTk9UIExJTUlURUQgVE8gVEhFIFdBUlJBTlRJRVMgT0Zcbi8vIE1FUkNIQU5UQUJJTElUWSwgRklUTkVTUyBGT1IgQSBQQVJUSUNVTEFSIFBVUlBPU0UgQU5EIE5PTklORlJJTkdFTUVOVC4gSU5cbi8vIE5PIEVWRU5UIFNIQUxMIFRIRSBBVVRIT1JTIE9SIENPUFlSSUdIVCBIT0xERVJTIEJFIExJQUJMRSBGT1IgQU5ZIENMQUlNLFxuLy8gREFNQUdFUyBPUiBPVEhFUiBMSUFCSUxJVFksIFdIRVRIRVIgSU4gQU4gQUNUSU9OIE9GIENPTlRSQUNULCBUT1JUIE9SXG4vLyBPVEhFUldJU0UsIEFSSVNJTkcgRlJPTSwgT1VUIE9GIE9SIElOIENPTk5FQ1RJT04gV0lUSCBUSEUgU09GVFdBUkUgT1IgVEhFXG4vLyBVU0UgT1IgT1RIRVIgREVBTElOR1MgSU4gVEhFIFNPRlRXQVJFLlxuXG5mdW5jdGlvbiBFdmVudEVtaXR0ZXIoKSB7XG4gIHRoaXMuX2V2ZW50cyA9IHRoaXMuX2V2ZW50cyB8fCB7fTtcbiAgdGhpcy5fbWF4TGlzdGVuZXJzID0gdGhpcy5fbWF4TGlzdGVuZXJzIHx8IHVuZGVmaW5lZDtcbn1cbm1vZHVsZS5leHBvcnRzID0gRXZlbnRFbWl0dGVyO1xuXG4vLyBCYWNrd2FyZHMtY29tcGF0IHdpdGggbm9kZSAwLjEwLnhcbkV2ZW50RW1pdHRlci5FdmVudEVtaXR0ZXIgPSBFdmVudEVtaXR0ZXI7XG5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUuX2V2ZW50cyA9IHVuZGVmaW5lZDtcbkV2ZW50RW1pdHRlci5wcm90b3R5cGUuX21heExpc3RlbmVycyA9IHVuZGVmaW5lZDtcblxuLy8gQnkgZGVmYXVsdCBFdmVudEVtaXR0ZXJzIHdpbGwgcHJpbnQgYSB3YXJuaW5nIGlmIG1vcmUgdGhhbiAxMCBsaXN0ZW5lcnMgYXJlXG4vLyBhZGRlZCB0byBpdC4gVGhpcyBpcyBhIHVzZWZ1bCBkZWZhdWx0IHdoaWNoIGhlbHBzIGZpbmRpbmcgbWVtb3J5IGxlYWtzLlxuRXZlbnRFbWl0dGVyLmRlZmF1bHRNYXhMaXN0ZW5lcnMgPSAxMDtcblxuLy8gT2J2aW91c2x5IG5vdCBhbGwgRW1pdHRlcnMgc2hvdWxkIGJlIGxpbWl0ZWQgdG8gMTAuIFRoaXMgZnVuY3Rpb24gYWxsb3dzXG4vLyB0aGF0IHRvIGJlIGluY3JlYXNlZC4gU2V0IHRvIHplcm8gZm9yIHVubGltaXRlZC5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUuc2V0TWF4TGlzdGVuZXJzID0gZnVuY3Rpb24obikge1xuICBpZiAoIWlzTnVtYmVyKG4pIHx8IG4gPCAwIHx8IGlzTmFOKG4pKVxuICAgIHRocm93IFR5cGVFcnJvcignbiBtdXN0IGJlIGEgcG9zaXRpdmUgbnVtYmVyJyk7XG4gIHRoaXMuX21heExpc3RlbmVycyA9IG47XG4gIHJldHVybiB0aGlzO1xufTtcblxuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5lbWl0ID0gZnVuY3Rpb24odHlwZSkge1xuICB2YXIgZXIsIGhhbmRsZXIsIGxlbiwgYXJncywgaSwgbGlzdGVuZXJzO1xuXG4gIGlmICghdGhpcy5fZXZlbnRzKVxuICAgIHRoaXMuX2V2ZW50cyA9IHt9O1xuXG4gIC8vIElmIHRoZXJlIGlzIG5vICdlcnJvcicgZXZlbnQgbGlzdGVuZXIgdGhlbiB0aHJvdy5cbiAgaWYgKHR5cGUgPT09ICdlcnJvcicpIHtcbiAgICBpZiAoIXRoaXMuX2V2ZW50cy5lcnJvciB8fFxuICAgICAgICAoaXNPYmplY3QodGhpcy5fZXZlbnRzLmVycm9yKSAmJiAhdGhpcy5fZXZlbnRzLmVycm9yLmxlbmd0aCkpIHtcbiAgICAgIGVyID0gYXJndW1lbnRzWzFdO1xuICAgICAgaWYgKGVyIGluc3RhbmNlb2YgRXJyb3IpIHtcbiAgICAgICAgdGhyb3cgZXI7IC8vIFVuaGFuZGxlZCAnZXJyb3InIGV2ZW50XG4gICAgICB9XG4gICAgICB0aHJvdyBUeXBlRXJyb3IoJ1VuY2F1Z2h0LCB1bnNwZWNpZmllZCBcImVycm9yXCIgZXZlbnQuJyk7XG4gICAgfVxuICB9XG5cbiAgaGFuZGxlciA9IHRoaXMuX2V2ZW50c1t0eXBlXTtcblxuICBpZiAoaXNVbmRlZmluZWQoaGFuZGxlcikpXG4gICAgcmV0dXJuIGZhbHNlO1xuXG4gIGlmIChpc0Z1bmN0aW9uKGhhbmRsZXIpKSB7XG4gICAgc3dpdGNoIChhcmd1bWVudHMubGVuZ3RoKSB7XG4gICAgICAvLyBmYXN0IGNhc2VzXG4gICAgICBjYXNlIDE6XG4gICAgICAgIGhhbmRsZXIuY2FsbCh0aGlzKTtcbiAgICAgICAgYnJlYWs7XG4gICAgICBjYXNlIDI6XG4gICAgICAgIGhhbmRsZXIuY2FsbCh0aGlzLCBhcmd1bWVudHNbMV0pO1xuICAgICAgICBicmVhaztcbiAgICAgIGNhc2UgMzpcbiAgICAgICAgaGFuZGxlci5jYWxsKHRoaXMsIGFyZ3VtZW50c1sxXSwgYXJndW1lbnRzWzJdKTtcbiAgICAgICAgYnJlYWs7XG4gICAgICAvLyBzbG93ZXJcbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIGxlbiA9IGFyZ3VtZW50cy5sZW5ndGg7XG4gICAgICAgIGFyZ3MgPSBuZXcgQXJyYXkobGVuIC0gMSk7XG4gICAgICAgIGZvciAoaSA9IDE7IGkgPCBsZW47IGkrKylcbiAgICAgICAgICBhcmdzW2kgLSAxXSA9IGFyZ3VtZW50c1tpXTtcbiAgICAgICAgaGFuZGxlci5hcHBseSh0aGlzLCBhcmdzKTtcbiAgICB9XG4gIH0gZWxzZSBpZiAoaXNPYmplY3QoaGFuZGxlcikpIHtcbiAgICBsZW4gPSBhcmd1bWVudHMubGVuZ3RoO1xuICAgIGFyZ3MgPSBuZXcgQXJyYXkobGVuIC0gMSk7XG4gICAgZm9yIChpID0gMTsgaSA8IGxlbjsgaSsrKVxuICAgICAgYXJnc1tpIC0gMV0gPSBhcmd1bWVudHNbaV07XG5cbiAgICBsaXN0ZW5lcnMgPSBoYW5kbGVyLnNsaWNlKCk7XG4gICAgbGVuID0gbGlzdGVuZXJzLmxlbmd0aDtcbiAgICBmb3IgKGkgPSAwOyBpIDwgbGVuOyBpKyspXG4gICAgICBsaXN0ZW5lcnNbaV0uYXBwbHkodGhpcywgYXJncyk7XG4gIH1cblxuICByZXR1cm4gdHJ1ZTtcbn07XG5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUuYWRkTGlzdGVuZXIgPSBmdW5jdGlvbih0eXBlLCBsaXN0ZW5lcikge1xuICB2YXIgbTtcblxuICBpZiAoIWlzRnVuY3Rpb24obGlzdGVuZXIpKVxuICAgIHRocm93IFR5cGVFcnJvcignbGlzdGVuZXIgbXVzdCBiZSBhIGZ1bmN0aW9uJyk7XG5cbiAgaWYgKCF0aGlzLl9ldmVudHMpXG4gICAgdGhpcy5fZXZlbnRzID0ge307XG5cbiAgLy8gVG8gYXZvaWQgcmVjdXJzaW9uIGluIHRoZSBjYXNlIHRoYXQgdHlwZSA9PT0gXCJuZXdMaXN0ZW5lclwiISBCZWZvcmVcbiAgLy8gYWRkaW5nIGl0IHRvIHRoZSBsaXN0ZW5lcnMsIGZpcnN0IGVtaXQgXCJuZXdMaXN0ZW5lclwiLlxuICBpZiAodGhpcy5fZXZlbnRzLm5ld0xpc3RlbmVyKVxuICAgIHRoaXMuZW1pdCgnbmV3TGlzdGVuZXInLCB0eXBlLFxuICAgICAgICAgICAgICBpc0Z1bmN0aW9uKGxpc3RlbmVyLmxpc3RlbmVyKSA/XG4gICAgICAgICAgICAgIGxpc3RlbmVyLmxpc3RlbmVyIDogbGlzdGVuZXIpO1xuXG4gIGlmICghdGhpcy5fZXZlbnRzW3R5cGVdKVxuICAgIC8vIE9wdGltaXplIHRoZSBjYXNlIG9mIG9uZSBsaXN0ZW5lci4gRG9uJ3QgbmVlZCB0aGUgZXh0cmEgYXJyYXkgb2JqZWN0LlxuICAgIHRoaXMuX2V2ZW50c1t0eXBlXSA9IGxpc3RlbmVyO1xuICBlbHNlIGlmIChpc09iamVjdCh0aGlzLl9ldmVudHNbdHlwZV0pKVxuICAgIC8vIElmIHdlJ3ZlIGFscmVhZHkgZ290IGFuIGFycmF5LCBqdXN0IGFwcGVuZC5cbiAgICB0aGlzLl9ldmVudHNbdHlwZV0ucHVzaChsaXN0ZW5lcik7XG4gIGVsc2VcbiAgICAvLyBBZGRpbmcgdGhlIHNlY29uZCBlbGVtZW50LCBuZWVkIHRvIGNoYW5nZSB0byBhcnJheS5cbiAgICB0aGlzLl9ldmVudHNbdHlwZV0gPSBbdGhpcy5fZXZlbnRzW3R5cGVdLCBsaXN0ZW5lcl07XG5cbiAgLy8gQ2hlY2sgZm9yIGxpc3RlbmVyIGxlYWtcbiAgaWYgKGlzT2JqZWN0KHRoaXMuX2V2ZW50c1t0eXBlXSkgJiYgIXRoaXMuX2V2ZW50c1t0eXBlXS53YXJuZWQpIHtcbiAgICB2YXIgbTtcbiAgICBpZiAoIWlzVW5kZWZpbmVkKHRoaXMuX21heExpc3RlbmVycykpIHtcbiAgICAgIG0gPSB0aGlzLl9tYXhMaXN0ZW5lcnM7XG4gICAgfSBlbHNlIHtcbiAgICAgIG0gPSBFdmVudEVtaXR0ZXIuZGVmYXVsdE1heExpc3RlbmVycztcbiAgICB9XG5cbiAgICBpZiAobSAmJiBtID4gMCAmJiB0aGlzLl9ldmVudHNbdHlwZV0ubGVuZ3RoID4gbSkge1xuICAgICAgdGhpcy5fZXZlbnRzW3R5cGVdLndhcm5lZCA9IHRydWU7XG4gICAgICBjb25zb2xlLmVycm9yKCcobm9kZSkgd2FybmluZzogcG9zc2libGUgRXZlbnRFbWl0dGVyIG1lbW9yeSAnICtcbiAgICAgICAgICAgICAgICAgICAgJ2xlYWsgZGV0ZWN0ZWQuICVkIGxpc3RlbmVycyBhZGRlZC4gJyArXG4gICAgICAgICAgICAgICAgICAgICdVc2UgZW1pdHRlci5zZXRNYXhMaXN0ZW5lcnMoKSB0byBpbmNyZWFzZSBsaW1pdC4nLFxuICAgICAgICAgICAgICAgICAgICB0aGlzLl9ldmVudHNbdHlwZV0ubGVuZ3RoKTtcbiAgICAgIGlmICh0eXBlb2YgY29uc29sZS50cmFjZSA9PT0gJ2Z1bmN0aW9uJykge1xuICAgICAgICAvLyBub3Qgc3VwcG9ydGVkIGluIElFIDEwXG4gICAgICAgIGNvbnNvbGUudHJhY2UoKTtcbiAgICAgIH1cbiAgICB9XG4gIH1cblxuICByZXR1cm4gdGhpcztcbn07XG5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUub24gPSBFdmVudEVtaXR0ZXIucHJvdG90eXBlLmFkZExpc3RlbmVyO1xuXG5FdmVudEVtaXR0ZXIucHJvdG90eXBlLm9uY2UgPSBmdW5jdGlvbih0eXBlLCBsaXN0ZW5lcikge1xuICBpZiAoIWlzRnVuY3Rpb24obGlzdGVuZXIpKVxuICAgIHRocm93IFR5cGVFcnJvcignbGlzdGVuZXIgbXVzdCBiZSBhIGZ1bmN0aW9uJyk7XG5cbiAgdmFyIGZpcmVkID0gZmFsc2U7XG5cbiAgZnVuY3Rpb24gZygpIHtcbiAgICB0aGlzLnJlbW92ZUxpc3RlbmVyKHR5cGUsIGcpO1xuXG4gICAgaWYgKCFmaXJlZCkge1xuICAgICAgZmlyZWQgPSB0cnVlO1xuICAgICAgbGlzdGVuZXIuYXBwbHkodGhpcywgYXJndW1lbnRzKTtcbiAgICB9XG4gIH1cblxuICBnLmxpc3RlbmVyID0gbGlzdGVuZXI7XG4gIHRoaXMub24odHlwZSwgZyk7XG5cbiAgcmV0dXJuIHRoaXM7XG59O1xuXG4vLyBlbWl0cyBhICdyZW1vdmVMaXN0ZW5lcicgZXZlbnQgaWZmIHRoZSBsaXN0ZW5lciB3YXMgcmVtb3ZlZFxuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5yZW1vdmVMaXN0ZW5lciA9IGZ1bmN0aW9uKHR5cGUsIGxpc3RlbmVyKSB7XG4gIHZhciBsaXN0LCBwb3NpdGlvbiwgbGVuZ3RoLCBpO1xuXG4gIGlmICghaXNGdW5jdGlvbihsaXN0ZW5lcikpXG4gICAgdGhyb3cgVHlwZUVycm9yKCdsaXN0ZW5lciBtdXN0IGJlIGEgZnVuY3Rpb24nKTtcblxuICBpZiAoIXRoaXMuX2V2ZW50cyB8fCAhdGhpcy5fZXZlbnRzW3R5cGVdKVxuICAgIHJldHVybiB0aGlzO1xuXG4gIGxpc3QgPSB0aGlzLl9ldmVudHNbdHlwZV07XG4gIGxlbmd0aCA9IGxpc3QubGVuZ3RoO1xuICBwb3NpdGlvbiA9IC0xO1xuXG4gIGlmIChsaXN0ID09PSBsaXN0ZW5lciB8fFxuICAgICAgKGlzRnVuY3Rpb24obGlzdC5saXN0ZW5lcikgJiYgbGlzdC5saXN0ZW5lciA9PT0gbGlzdGVuZXIpKSB7XG4gICAgZGVsZXRlIHRoaXMuX2V2ZW50c1t0eXBlXTtcbiAgICBpZiAodGhpcy5fZXZlbnRzLnJlbW92ZUxpc3RlbmVyKVxuICAgICAgdGhpcy5lbWl0KCdyZW1vdmVMaXN0ZW5lcicsIHR5cGUsIGxpc3RlbmVyKTtcblxuICB9IGVsc2UgaWYgKGlzT2JqZWN0KGxpc3QpKSB7XG4gICAgZm9yIChpID0gbGVuZ3RoOyBpLS0gPiAwOykge1xuICAgICAgaWYgKGxpc3RbaV0gPT09IGxpc3RlbmVyIHx8XG4gICAgICAgICAgKGxpc3RbaV0ubGlzdGVuZXIgJiYgbGlzdFtpXS5saXN0ZW5lciA9PT0gbGlzdGVuZXIpKSB7XG4gICAgICAgIHBvc2l0aW9uID0gaTtcbiAgICAgICAgYnJlYWs7XG4gICAgICB9XG4gICAgfVxuXG4gICAgaWYgKHBvc2l0aW9uIDwgMClcbiAgICAgIHJldHVybiB0aGlzO1xuXG4gICAgaWYgKGxpc3QubGVuZ3RoID09PSAxKSB7XG4gICAgICBsaXN0Lmxlbmd0aCA9IDA7XG4gICAgICBkZWxldGUgdGhpcy5fZXZlbnRzW3R5cGVdO1xuICAgIH0gZWxzZSB7XG4gICAgICBsaXN0LnNwbGljZShwb3NpdGlvbiwgMSk7XG4gICAgfVxuXG4gICAgaWYgKHRoaXMuX2V2ZW50cy5yZW1vdmVMaXN0ZW5lcilcbiAgICAgIHRoaXMuZW1pdCgncmVtb3ZlTGlzdGVuZXInLCB0eXBlLCBsaXN0ZW5lcik7XG4gIH1cblxuICByZXR1cm4gdGhpcztcbn07XG5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUucmVtb3ZlQWxsTGlzdGVuZXJzID0gZnVuY3Rpb24odHlwZSkge1xuICB2YXIga2V5LCBsaXN0ZW5lcnM7XG5cbiAgaWYgKCF0aGlzLl9ldmVudHMpXG4gICAgcmV0dXJuIHRoaXM7XG5cbiAgLy8gbm90IGxpc3RlbmluZyBmb3IgcmVtb3ZlTGlzdGVuZXIsIG5vIG5lZWQgdG8gZW1pdFxuICBpZiAoIXRoaXMuX2V2ZW50cy5yZW1vdmVMaXN0ZW5lcikge1xuICAgIGlmIChhcmd1bWVudHMubGVuZ3RoID09PSAwKVxuICAgICAgdGhpcy5fZXZlbnRzID0ge307XG4gICAgZWxzZSBpZiAodGhpcy5fZXZlbnRzW3R5cGVdKVxuICAgICAgZGVsZXRlIHRoaXMuX2V2ZW50c1t0eXBlXTtcbiAgICByZXR1cm4gdGhpcztcbiAgfVxuXG4gIC8vIGVtaXQgcmVtb3ZlTGlzdGVuZXIgZm9yIGFsbCBsaXN0ZW5lcnMgb24gYWxsIGV2ZW50c1xuICBpZiAoYXJndW1lbnRzLmxlbmd0aCA9PT0gMCkge1xuICAgIGZvciAoa2V5IGluIHRoaXMuX2V2ZW50cykge1xuICAgICAgaWYgKGtleSA9PT0gJ3JlbW92ZUxpc3RlbmVyJykgY29udGludWU7XG4gICAgICB0aGlzLnJlbW92ZUFsbExpc3RlbmVycyhrZXkpO1xuICAgIH1cbiAgICB0aGlzLnJlbW92ZUFsbExpc3RlbmVycygncmVtb3ZlTGlzdGVuZXInKTtcbiAgICB0aGlzLl9ldmVudHMgPSB7fTtcbiAgICByZXR1cm4gdGhpcztcbiAgfVxuXG4gIGxpc3RlbmVycyA9IHRoaXMuX2V2ZW50c1t0eXBlXTtcblxuICBpZiAoaXNGdW5jdGlvbihsaXN0ZW5lcnMpKSB7XG4gICAgdGhpcy5yZW1vdmVMaXN0ZW5lcih0eXBlLCBsaXN0ZW5lcnMpO1xuICB9IGVsc2Uge1xuICAgIC8vIExJRk8gb3JkZXJcbiAgICB3aGlsZSAobGlzdGVuZXJzLmxlbmd0aClcbiAgICAgIHRoaXMucmVtb3ZlTGlzdGVuZXIodHlwZSwgbGlzdGVuZXJzW2xpc3RlbmVycy5sZW5ndGggLSAxXSk7XG4gIH1cbiAgZGVsZXRlIHRoaXMuX2V2ZW50c1t0eXBlXTtcblxuICByZXR1cm4gdGhpcztcbn07XG5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUubGlzdGVuZXJzID0gZnVuY3Rpb24odHlwZSkge1xuICB2YXIgcmV0O1xuICBpZiAoIXRoaXMuX2V2ZW50cyB8fCAhdGhpcy5fZXZlbnRzW3R5cGVdKVxuICAgIHJldCA9IFtdO1xuICBlbHNlIGlmIChpc0Z1bmN0aW9uKHRoaXMuX2V2ZW50c1t0eXBlXSkpXG4gICAgcmV0ID0gW3RoaXMuX2V2ZW50c1t0eXBlXV07XG4gIGVsc2VcbiAgICByZXQgPSB0aGlzLl9ldmVudHNbdHlwZV0uc2xpY2UoKTtcbiAgcmV0dXJuIHJldDtcbn07XG5cbkV2ZW50RW1pdHRlci5saXN0ZW5lckNvdW50ID0gZnVuY3Rpb24oZW1pdHRlciwgdHlwZSkge1xuICB2YXIgcmV0O1xuICBpZiAoIWVtaXR0ZXIuX2V2ZW50cyB8fCAhZW1pdHRlci5fZXZlbnRzW3R5cGVdKVxuICAgIHJldCA9IDA7XG4gIGVsc2UgaWYgKGlzRnVuY3Rpb24oZW1pdHRlci5fZXZlbnRzW3R5cGVdKSlcbiAgICByZXQgPSAxO1xuICBlbHNlXG4gICAgcmV0ID0gZW1pdHRlci5fZXZlbnRzW3R5cGVdLmxlbmd0aDtcbiAgcmV0dXJuIHJldDtcbn07XG5cbmZ1bmN0aW9uIGlzRnVuY3Rpb24oYXJnKSB7XG4gIHJldHVybiB0eXBlb2YgYXJnID09PSAnZnVuY3Rpb24nO1xufVxuXG5mdW5jdGlvbiBpc051bWJlcihhcmcpIHtcbiAgcmV0dXJuIHR5cGVvZiBhcmcgPT09ICdudW1iZXInO1xufVxuXG5mdW5jdGlvbiBpc09iamVjdChhcmcpIHtcbiAgcmV0dXJuIHR5cGVvZiBhcmcgPT09ICdvYmplY3QnICYmIGFyZyAhPT0gbnVsbDtcbn1cblxuZnVuY3Rpb24gaXNVbmRlZmluZWQoYXJnKSB7XG4gIHJldHVybiBhcmcgPT09IHZvaWQgMDtcbn1cbiIsInZhciAkID0gcmVxdWlyZShcImpxdWVyeVwiKTtcclxuXHJcbnZhciBBY3Rpb25UeXBlcyA9IHtcclxuICAgIC8vIENvbm5lY3Rpb25cclxuICAgIENPTk5FQ1RJT05fT1BFTjogXCJjb25uZWN0aW9uX29wZW5cIixcclxuICAgIENPTk5FQ1RJT05fQ0xPU0U6IFwiY29ubmVjdGlvbl9jbG9zZVwiLFxyXG4gICAgQ09OTkVDVElPTl9FUlJPUjogXCJjb25uZWN0aW9uX2Vycm9yXCIsXHJcblxyXG4gICAgLy8gU3RvcmVzXHJcbiAgICBTRVRUSU5HU19TVE9SRTogXCJzZXR0aW5nc1wiLFxyXG4gICAgRVZFTlRfU1RPUkU6IFwiZXZlbnRzXCIsXHJcbiAgICBGTE9XX1NUT1JFOiBcImZsb3dzXCIsXHJcbn07XHJcblxyXG52YXIgU3RvcmVDbWRzID0ge1xyXG4gICAgQUREOiBcImFkZFwiLFxyXG4gICAgVVBEQVRFOiBcInVwZGF0ZVwiLFxyXG4gICAgUkVNT1ZFOiBcInJlbW92ZVwiLFxyXG4gICAgUkVTRVQ6IFwicmVzZXRcIlxyXG59O1xyXG5cclxudmFyIENvbm5lY3Rpb25BY3Rpb25zID0ge1xyXG4gICAgb3BlbjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIEFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uKHtcclxuICAgICAgICAgICAgdHlwZTogQWN0aW9uVHlwZXMuQ09OTkVDVElPTl9PUEVOXHJcbiAgICAgICAgfSk7XHJcbiAgICB9LFxyXG4gICAgY2xvc2U6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICBBcHBEaXNwYXRjaGVyLmRpc3BhdGNoVmlld0FjdGlvbih7XHJcbiAgICAgICAgICAgIHR5cGU6IEFjdGlvblR5cGVzLkNPTk5FQ1RJT05fQ0xPU0VcclxuICAgICAgICB9KTtcclxuICAgIH0sXHJcbiAgICBlcnJvcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIEFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uKHtcclxuICAgICAgICAgICAgdHlwZTogQWN0aW9uVHlwZXMuQ09OTkVDVElPTl9FUlJPUlxyXG4gICAgICAgIH0pO1xyXG4gICAgfVxyXG59O1xyXG5cclxudmFyIFNldHRpbmdzQWN0aW9ucyA9IHtcclxuICAgIHVwZGF0ZTogZnVuY3Rpb24gKHNldHRpbmdzKSB7XHJcblxyXG4gICAgICAgICQuYWpheCh7XHJcbiAgICAgICAgICAgIHR5cGU6IFwiUFVUXCIsXHJcbiAgICAgICAgICAgIHVybDogXCIvc2V0dGluZ3NcIixcclxuICAgICAgICAgICAgZGF0YTogc2V0dGluZ3NcclxuICAgICAgICB9KTtcclxuXHJcbiAgICAgICAgLypcclxuICAgICAgICAvL0ZhY2Vib29rIEZsdXg6IFdlIGRvIGFuIG9wdGltaXN0aWMgdXBkYXRlIG9uIHRoZSBjbGllbnQgYWxyZWFkeS5cclxuICAgICAgICBBcHBEaXNwYXRjaGVyLmRpc3BhdGNoVmlld0FjdGlvbih7XHJcbiAgICAgICAgICAgIHR5cGU6IEFjdGlvblR5cGVzLlNFVFRJTkdTX1NUT1JFLFxyXG4gICAgICAgICAgICBjbWQ6IFN0b3JlQ21kcy5VUERBVEUsXHJcbiAgICAgICAgICAgIGRhdGE6IHNldHRpbmdzXHJcbiAgICAgICAgfSk7XHJcbiAgICAgICAgKi9cclxuICAgIH1cclxufTtcclxuXHJcbnZhciBFdmVudExvZ0FjdGlvbnNfZXZlbnRfaWQgPSAwO1xyXG52YXIgRXZlbnRMb2dBY3Rpb25zID0ge1xyXG4gICAgYWRkX2V2ZW50OiBmdW5jdGlvbiAobWVzc2FnZSkge1xyXG4gICAgICAgIEFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uKHtcclxuICAgICAgICAgICAgdHlwZTogQWN0aW9uVHlwZXMuRVZFTlRfU1RPUkUsXHJcbiAgICAgICAgICAgIGNtZDogU3RvcmVDbWRzLkFERCxcclxuICAgICAgICAgICAgZGF0YToge1xyXG4gICAgICAgICAgICAgICAgbWVzc2FnZTogbWVzc2FnZSxcclxuICAgICAgICAgICAgICAgIGxldmVsOiBcIndlYlwiLFxyXG4gICAgICAgICAgICAgICAgaWQ6IFwidmlld0FjdGlvbi1cIiArIEV2ZW50TG9nQWN0aW9uc19ldmVudF9pZCsrXHJcbiAgICAgICAgICAgIH1cclxuICAgICAgICB9KTtcclxuICAgIH1cclxufTtcclxuXHJcbnZhciBGbG93QWN0aW9ucyA9IHtcclxuICAgIGFjY2VwdDogZnVuY3Rpb24gKGZsb3cpIHtcclxuICAgICAgICAkLnBvc3QoXCIvZmxvd3MvXCIgKyBmbG93LmlkICsgXCIvYWNjZXB0XCIpO1xyXG4gICAgfSxcclxuICAgIGFjY2VwdF9hbGw6IGZ1bmN0aW9uKCl7XHJcbiAgICAgICAgJC5wb3N0KFwiL2Zsb3dzL2FjY2VwdFwiKTtcclxuICAgIH0sXHJcbiAgICBcImRlbGV0ZVwiOiBmdW5jdGlvbihmbG93KXtcclxuICAgICAgICAkLmFqYXgoe1xyXG4gICAgICAgICAgICB0eXBlOlwiREVMRVRFXCIsXHJcbiAgICAgICAgICAgIHVybDogXCIvZmxvd3MvXCIgKyBmbG93LmlkXHJcbiAgICAgICAgfSk7XHJcbiAgICB9LFxyXG4gICAgZHVwbGljYXRlOiBmdW5jdGlvbihmbG93KXtcclxuICAgICAgICAkLnBvc3QoXCIvZmxvd3MvXCIgKyBmbG93LmlkICsgXCIvZHVwbGljYXRlXCIpO1xyXG4gICAgfSxcclxuICAgIHJlcGxheTogZnVuY3Rpb24oZmxvdyl7XHJcbiAgICAgICAgJC5wb3N0KFwiL2Zsb3dzL1wiICsgZmxvdy5pZCArIFwiL3JlcGxheVwiKTtcclxuICAgIH0sXHJcbiAgICByZXZlcnQ6IGZ1bmN0aW9uKGZsb3cpe1xyXG4gICAgICAgICQucG9zdChcIi9mbG93cy9cIiArIGZsb3cuaWQgKyBcIi9yZXZlcnRcIik7XHJcbiAgICB9LFxyXG4gICAgdXBkYXRlOiBmdW5jdGlvbiAoZmxvdykge1xyXG4gICAgICAgIEFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uKHtcclxuICAgICAgICAgICAgdHlwZTogQWN0aW9uVHlwZXMuRkxPV19TVE9SRSxcclxuICAgICAgICAgICAgY21kOiBTdG9yZUNtZHMuVVBEQVRFLFxyXG4gICAgICAgICAgICBkYXRhOiBmbG93XHJcbiAgICAgICAgfSk7XHJcbiAgICB9LFxyXG4gICAgY2xlYXI6IGZ1bmN0aW9uKCl7XHJcbiAgICAgICAgJC5wb3N0KFwiL2NsZWFyXCIpO1xyXG4gICAgfVxyXG59O1xyXG5cclxuUXVlcnkgPSB7XHJcbiAgICBGSUxURVI6IFwiZlwiLFxyXG4gICAgSElHSExJR0hUOiBcImhcIixcclxuICAgIFNIT1dfRVZFTlRMT0c6IFwiZVwiXHJcbn07XHJcblxyXG5tb2R1bGUuZXhwb3J0cyA9IHtcclxuICAgIEFjdGlvblR5cGVzOiBBY3Rpb25UeXBlcyxcclxuICAgIENvbm5lY3Rpb25BY3Rpb25zOiBDb25uZWN0aW9uQWN0aW9ucyxcclxuICAgIEZsb3dBY3Rpb25zOiBGbG93QWN0aW9ucyxcclxuICAgIFN0b3JlQ21kczogU3RvcmVDbWRzXHJcbn07IiwiXHJcbnZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcclxudmFyIFJlYWN0Um91dGVyID0gcmVxdWlyZShcInJlYWN0LXJvdXRlclwiKTtcclxudmFyICQgPSByZXF1aXJlKFwianF1ZXJ5XCIpO1xyXG5cclxudmFyIENvbm5lY3Rpb24gPSByZXF1aXJlKFwiLi9jb25uZWN0aW9uXCIpO1xyXG52YXIgcHJveHlhcHAgPSByZXF1aXJlKFwiLi9jb21wb25lbnRzL3Byb3h5YXBwLmpzXCIpO1xyXG5cclxuJChmdW5jdGlvbiAoKSB7XHJcbiAgICB3aW5kb3cud3MgPSBuZXcgQ29ubmVjdGlvbihcIi91cGRhdGVzXCIpO1xyXG5cclxuICAgIFJlYWN0Um91dGVyLnJ1bihwcm94eWFwcC5yb3V0ZXMsIGZ1bmN0aW9uIChIYW5kbGVyKSB7XHJcbiAgICAgICAgUmVhY3QucmVuZGVyKDxIYW5kbGVyLz4sIGRvY3VtZW50LmJvZHkpO1xyXG4gICAgfSk7XHJcbn0pO1xyXG5cclxuIiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xyXG52YXIgUmVhY3RSb3V0ZXIgPSByZXF1aXJlKFwicmVhY3Qtcm91dGVyXCIpO1xyXG52YXIgXyA9IHJlcXVpcmUoXCJsb2Rhc2hcIik7XHJcblxyXG4vLyBodHRwOi8vYmxvZy52amV1eC5jb20vMjAxMy9qYXZhc2NyaXB0L3Njcm9sbC1wb3NpdGlvbi13aXRoLXJlYWN0Lmh0bWwgKGFsc28gY29udGFpbnMgaW52ZXJzZSBleGFtcGxlKVxyXG52YXIgQXV0b1Njcm9sbE1peGluID0ge1xyXG4gICAgY29tcG9uZW50V2lsbFVwZGF0ZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBub2RlID0gdGhpcy5nZXRET01Ob2RlKCk7XHJcbiAgICAgICAgdGhpcy5fc2hvdWxkU2Nyb2xsQm90dG9tID0gKFxyXG4gICAgICAgICAgICBub2RlLnNjcm9sbFRvcCAhPT0gMCAmJlxyXG4gICAgICAgICAgICBub2RlLnNjcm9sbFRvcCArIG5vZGUuY2xpZW50SGVpZ2h0ID09PSBub2RlLnNjcm9sbEhlaWdodFxyXG4gICAgICAgICk7XHJcbiAgICB9LFxyXG4gICAgY29tcG9uZW50RGlkVXBkYXRlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgaWYgKHRoaXMuX3Nob3VsZFNjcm9sbEJvdHRvbSkge1xyXG4gICAgICAgICAgICB2YXIgbm9kZSA9IHRoaXMuZ2V0RE9NTm9kZSgpO1xyXG4gICAgICAgICAgICBub2RlLnNjcm9sbFRvcCA9IG5vZGUuc2Nyb2xsSGVpZ2h0O1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbn07XHJcblxyXG5cclxudmFyIFN0aWNreUhlYWRNaXhpbiA9IHtcclxuICAgIGFkanVzdEhlYWQ6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAvLyBBYnVzaW5nIENTUyB0cmFuc2Zvcm1zIHRvIHNldCB0aGUgZWxlbWVudFxyXG4gICAgICAgIC8vIHJlZmVyZW5jZWQgYXMgaGVhZCBpbnRvIHNvbWUga2luZCBvZiBwb3NpdGlvbjpzdGlja3kuXHJcbiAgICAgICAgdmFyIGhlYWQgPSB0aGlzLnJlZnMuaGVhZC5nZXRET01Ob2RlKCk7XHJcbiAgICAgICAgaGVhZC5zdHlsZS50cmFuc2Zvcm0gPSBcInRyYW5zbGF0ZSgwLFwiICsgdGhpcy5nZXRET01Ob2RlKCkuc2Nyb2xsVG9wICsgXCJweClcIjtcclxuICAgIH1cclxufTtcclxuXHJcblxyXG52YXIgTmF2aWdhdGlvbiA9IF8uZXh0ZW5kKHt9LCBSZWFjdFJvdXRlci5OYXZpZ2F0aW9uLCB7XHJcbiAgICBzZXRRdWVyeTogZnVuY3Rpb24gKGRpY3QpIHtcclxuICAgICAgICB2YXIgcSA9IHRoaXMuY29udGV4dC5nZXRDdXJyZW50UXVlcnkoKTtcclxuICAgICAgICBmb3IodmFyIGkgaW4gZGljdCl7XHJcbiAgICAgICAgICAgIGlmKGRpY3QuaGFzT3duUHJvcGVydHkoaSkpe1xyXG4gICAgICAgICAgICAgICAgcVtpXSA9IGRpY3RbaV0gfHwgdW5kZWZpbmVkOyAvL2ZhbHNleSB2YWx1ZXMgc2hhbGwgYmUgcmVtb3ZlZC5cclxuICAgICAgICAgICAgfVxyXG4gICAgICAgIH1cclxuICAgICAgICBxLl8gPSBcIl9cIjsgLy8gd29ya2Fyb3VuZCBmb3IgaHR0cHM6Ly9naXRodWIuY29tL3JhY2t0L3JlYWN0LXJvdXRlci9wdWxsLzU5OVxyXG4gICAgICAgIHRoaXMucmVwbGFjZVdpdGgodGhpcy5jb250ZXh0LmdldEN1cnJlbnRQYXRoKCksIHRoaXMuY29udGV4dC5nZXRDdXJyZW50UGFyYW1zKCksIHEpO1xyXG4gICAgfSxcclxuICAgIHJlcGxhY2VXaXRoOiBmdW5jdGlvbihyb3V0ZU5hbWVPclBhdGgsIHBhcmFtcywgcXVlcnkpIHtcclxuICAgICAgICBpZihyb3V0ZU5hbWVPclBhdGggPT09IHVuZGVmaW5lZCl7XHJcbiAgICAgICAgICAgIHJvdXRlTmFtZU9yUGF0aCA9IHRoaXMuY29udGV4dC5nZXRDdXJyZW50UGF0aCgpO1xyXG4gICAgICAgIH1cclxuICAgICAgICBpZihwYXJhbXMgPT09IHVuZGVmaW5lZCl7XHJcbiAgICAgICAgICAgIHBhcmFtcyA9IHRoaXMuY29udGV4dC5nZXRDdXJyZW50UGFyYW1zKCk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIGlmKHF1ZXJ5ID09PSB1bmRlZmluZWQpe1xyXG4gICAgICAgICAgICBxdWVyeSA9IHRoaXMuY29udGV4dC5nZXRDdXJyZW50UXVlcnkoKTtcclxuICAgICAgICB9XHJcbiAgICAgICAgUmVhY3RSb3V0ZXIuTmF2aWdhdGlvbi5yZXBsYWNlV2l0aC5jYWxsKHRoaXMsIHJvdXRlTmFtZU9yUGF0aCwgcGFyYW1zLCBxdWVyeSk7XHJcbiAgICB9XHJcbn0pO1xyXG5fLmV4dGVuZChOYXZpZ2F0aW9uLmNvbnRleHRUeXBlcywgUmVhY3RSb3V0ZXIuU3RhdGUuY29udGV4dFR5cGVzKTtcclxuXHJcbnZhciBTdGF0ZSA9IF8uZXh0ZW5kKHt9LCBSZWFjdFJvdXRlci5TdGF0ZSwge1xyXG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdGhpcy5fcXVlcnkgPSB0aGlzLmNvbnRleHQuZ2V0Q3VycmVudFF1ZXJ5KCk7XHJcbiAgICAgICAgdGhpcy5fcXVlcnlXYXRjaGVzID0gW107XHJcbiAgICAgICAgcmV0dXJuIG51bGw7XHJcbiAgICB9LFxyXG4gICAgb25RdWVyeUNoYW5nZTogZnVuY3Rpb24gKGtleSwgY2FsbGJhY2spIHtcclxuICAgICAgICB0aGlzLl9xdWVyeVdhdGNoZXMucHVzaCh7XHJcbiAgICAgICAgICAgIGtleToga2V5LFxyXG4gICAgICAgICAgICBjYWxsYmFjazogY2FsbGJhY2tcclxuICAgICAgICB9KTtcclxuICAgIH0sXHJcbiAgICBjb21wb25lbnRXaWxsUmVjZWl2ZVByb3BzOiBmdW5jdGlvbiAobmV4dFByb3BzLCBuZXh0U3RhdGUpIHtcclxuICAgICAgICB2YXIgcSA9IHRoaXMuY29udGV4dC5nZXRDdXJyZW50UXVlcnkoKTtcclxuICAgICAgICBmb3IgKHZhciBpID0gMDsgaSA8IHRoaXMuX3F1ZXJ5V2F0Y2hlcy5sZW5ndGg7IGkrKykge1xyXG4gICAgICAgICAgICB2YXIgd2F0Y2ggPSB0aGlzLl9xdWVyeVdhdGNoZXNbaV07XHJcbiAgICAgICAgICAgIGlmICh0aGlzLl9xdWVyeVt3YXRjaC5rZXldICE9PSBxW3dhdGNoLmtleV0pIHtcclxuICAgICAgICAgICAgICAgIHdhdGNoLmNhbGxiYWNrKHRoaXMuX3F1ZXJ5W3dhdGNoLmtleV0sIHFbd2F0Y2gua2V5XSwgd2F0Y2gua2V5KTtcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgIH1cclxuICAgICAgICB0aGlzLl9xdWVyeSA9IHE7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIFNwbGl0dGVyID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgZ2V0RGVmYXVsdFByb3BzOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgcmV0dXJuIHtcclxuICAgICAgICAgICAgYXhpczogXCJ4XCJcclxuICAgICAgICB9O1xyXG4gICAgfSxcclxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHJldHVybiB7XHJcbiAgICAgICAgICAgIGFwcGxpZWQ6IGZhbHNlLFxyXG4gICAgICAgICAgICBzdGFydFg6IGZhbHNlLFxyXG4gICAgICAgICAgICBzdGFydFk6IGZhbHNlXHJcbiAgICAgICAgfTtcclxuICAgIH0sXHJcbiAgICBvbk1vdXNlRG93bjogZnVuY3Rpb24gKGUpIHtcclxuICAgICAgICB0aGlzLnNldFN0YXRlKHtcclxuICAgICAgICAgICAgc3RhcnRYOiBlLnBhZ2VYLFxyXG4gICAgICAgICAgICBzdGFydFk6IGUucGFnZVlcclxuICAgICAgICB9KTtcclxuICAgICAgICB3aW5kb3cuYWRkRXZlbnRMaXN0ZW5lcihcIm1vdXNlbW92ZVwiLCB0aGlzLm9uTW91c2VNb3ZlKTtcclxuICAgICAgICB3aW5kb3cuYWRkRXZlbnRMaXN0ZW5lcihcIm1vdXNldXBcIiwgdGhpcy5vbk1vdXNlVXApO1xyXG4gICAgICAgIC8vIE9jY2FzaW9uYWxseSwgb25seSBhIGRyYWdFbmQgZXZlbnQgaXMgdHJpZ2dlcmVkLCBidXQgbm8gbW91c2VVcC5cclxuICAgICAgICB3aW5kb3cuYWRkRXZlbnRMaXN0ZW5lcihcImRyYWdlbmRcIiwgdGhpcy5vbkRyYWdFbmQpO1xyXG4gICAgfSxcclxuICAgIG9uRHJhZ0VuZDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMuZ2V0RE9NTm9kZSgpLnN0eWxlLnRyYW5zZm9ybSA9IFwiXCI7XHJcbiAgICAgICAgd2luZG93LnJlbW92ZUV2ZW50TGlzdGVuZXIoXCJkcmFnZW5kXCIsIHRoaXMub25EcmFnRW5kKTtcclxuICAgICAgICB3aW5kb3cucmVtb3ZlRXZlbnRMaXN0ZW5lcihcIm1vdXNldXBcIiwgdGhpcy5vbk1vdXNlVXApO1xyXG4gICAgICAgIHdpbmRvdy5yZW1vdmVFdmVudExpc3RlbmVyKFwibW91c2Vtb3ZlXCIsIHRoaXMub25Nb3VzZU1vdmUpO1xyXG4gICAgfSxcclxuICAgIG9uTW91c2VVcDogZnVuY3Rpb24gKGUpIHtcclxuICAgICAgICB0aGlzLm9uRHJhZ0VuZCgpO1xyXG5cclxuICAgICAgICB2YXIgbm9kZSA9IHRoaXMuZ2V0RE9NTm9kZSgpO1xyXG4gICAgICAgIHZhciBwcmV2ID0gbm9kZS5wcmV2aW91c0VsZW1lbnRTaWJsaW5nO1xyXG4gICAgICAgIHZhciBuZXh0ID0gbm9kZS5uZXh0RWxlbWVudFNpYmxpbmc7XHJcblxyXG4gICAgICAgIHZhciBkWCA9IGUucGFnZVggLSB0aGlzLnN0YXRlLnN0YXJ0WDtcclxuICAgICAgICB2YXIgZFkgPSBlLnBhZ2VZIC0gdGhpcy5zdGF0ZS5zdGFydFk7XHJcbiAgICAgICAgdmFyIGZsZXhCYXNpcztcclxuICAgICAgICBpZiAodGhpcy5wcm9wcy5heGlzID09PSBcInhcIikge1xyXG4gICAgICAgICAgICBmbGV4QmFzaXMgPSBwcmV2Lm9mZnNldFdpZHRoICsgZFg7XHJcbiAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgZmxleEJhc2lzID0gcHJldi5vZmZzZXRIZWlnaHQgKyBkWTtcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIHByZXYuc3R5bGUuZmxleCA9IFwiMCAwIFwiICsgTWF0aC5tYXgoMCwgZmxleEJhc2lzKSArIFwicHhcIjtcclxuICAgICAgICBuZXh0LnN0eWxlLmZsZXggPSBcIjEgMSBhdXRvXCI7XHJcblxyXG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe1xyXG4gICAgICAgICAgICBhcHBsaWVkOiB0cnVlXHJcbiAgICAgICAgfSk7XHJcbiAgICAgICAgdGhpcy5vblJlc2l6ZSgpO1xyXG4gICAgfSxcclxuICAgIG9uTW91c2VNb3ZlOiBmdW5jdGlvbiAoZSkge1xyXG4gICAgICAgIHZhciBkWCA9IDAsIGRZID0gMDtcclxuICAgICAgICBpZiAodGhpcy5wcm9wcy5heGlzID09PSBcInhcIikge1xyXG4gICAgICAgICAgICBkWCA9IGUucGFnZVggLSB0aGlzLnN0YXRlLnN0YXJ0WDtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICBkWSA9IGUucGFnZVkgLSB0aGlzLnN0YXRlLnN0YXJ0WTtcclxuICAgICAgICB9XHJcbiAgICAgICAgdGhpcy5nZXRET01Ob2RlKCkuc3R5bGUudHJhbnNmb3JtID0gXCJ0cmFuc2xhdGUoXCIgKyBkWCArIFwicHgsXCIgKyBkWSArIFwicHgpXCI7XHJcbiAgICB9LFxyXG4gICAgb25SZXNpemU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAvLyBUcmlnZ2VyIGEgZ2xvYmFsIHJlc2l6ZSBldmVudC4gVGhpcyBub3RpZmllcyBjb21wb25lbnRzIHRoYXQgZW1wbG95IHZpcnR1YWwgc2Nyb2xsaW5nXHJcbiAgICAgICAgLy8gdGhhdCB0aGVpciB2aWV3cG9ydCBtYXkgaGF2ZSBjaGFuZ2VkLlxyXG4gICAgICAgIHdpbmRvdy5zZXRUaW1lb3V0KGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAgICAgd2luZG93LmRpc3BhdGNoRXZlbnQobmV3IEN1c3RvbUV2ZW50KFwicmVzaXplXCIpKTtcclxuICAgICAgICB9LCAxKTtcclxuICAgIH0sXHJcbiAgICByZXNldDogZnVuY3Rpb24gKHdpbGxVbm1vdW50KSB7XHJcbiAgICAgICAgaWYgKCF0aGlzLnN0YXRlLmFwcGxpZWQpIHtcclxuICAgICAgICAgICAgcmV0dXJuO1xyXG4gICAgICAgIH1cclxuICAgICAgICB2YXIgbm9kZSA9IHRoaXMuZ2V0RE9NTm9kZSgpO1xyXG4gICAgICAgIHZhciBwcmV2ID0gbm9kZS5wcmV2aW91c0VsZW1lbnRTaWJsaW5nO1xyXG4gICAgICAgIHZhciBuZXh0ID0gbm9kZS5uZXh0RWxlbWVudFNpYmxpbmc7XHJcblxyXG4gICAgICAgIHByZXYuc3R5bGUuZmxleCA9IFwiXCI7XHJcbiAgICAgICAgbmV4dC5zdHlsZS5mbGV4ID0gXCJcIjtcclxuXHJcbiAgICAgICAgaWYgKCF3aWxsVW5tb3VudCkge1xyXG4gICAgICAgICAgICB0aGlzLnNldFN0YXRlKHtcclxuICAgICAgICAgICAgICAgIGFwcGxpZWQ6IGZhbHNlXHJcbiAgICAgICAgICAgIH0pO1xyXG4gICAgICAgIH1cclxuICAgICAgICB0aGlzLm9uUmVzaXplKCk7XHJcbiAgICB9LFxyXG4gICAgY29tcG9uZW50V2lsbFVubW91bnQ6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLnJlc2V0KHRydWUpO1xyXG4gICAgfSxcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBjbGFzc05hbWUgPSBcInNwbGl0dGVyXCI7XHJcbiAgICAgICAgaWYgKHRoaXMucHJvcHMuYXhpcyA9PT0gXCJ4XCIpIHtcclxuICAgICAgICAgICAgY2xhc3NOYW1lICs9IFwiIHNwbGl0dGVyLXhcIjtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCIgc3BsaXR0ZXIteVwiO1xyXG4gICAgICAgIH1cclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT17Y2xhc3NOYW1lfT5cclxuICAgICAgICAgICAgICAgIDxkaXYgb25Nb3VzZURvd249e3RoaXMub25Nb3VzZURvd259IGRyYWdnYWJsZT1cInRydWVcIj48L2Rpdj5cclxuICAgICAgICAgICAgPC9kaXY+XHJcbiAgICAgICAgKTtcclxuICAgIH1cclxufSk7XHJcblxyXG5tb2R1bGUuZXhwb3J0cyA9IHtcclxuICAgIFN0YXRlOiBTdGF0ZSxcclxuICAgIE5hdmlnYXRpb246IE5hdmlnYXRpb24sXHJcbiAgICBTdGlja3lIZWFkTWl4aW46IFN0aWNreUhlYWRNaXhpbixcclxuICAgIEF1dG9TY3JvbGxNaXhpbjogQXV0b1Njcm9sbE1peGluLFxyXG4gICAgU3BsaXR0ZXI6IFNwbGl0dGVyXHJcbn0iLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XHJcbnZhciBjb21tb24gPSByZXF1aXJlKFwiLi9jb21tb24uanNcIik7XHJcbnZhciBWaXJ0dWFsU2Nyb2xsTWl4aW4gPSByZXF1aXJlKFwiLi92aXJ0dWFsc2Nyb2xsLmpzXCIpO1xyXG52YXIgdmlld3MgPSByZXF1aXJlKFwiLi4vc3RvcmUvdmlldy5qc1wiKTtcclxuXHJcbnZhciBMb2dNZXNzYWdlID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGVudHJ5ID0gdGhpcy5wcm9wcy5lbnRyeTtcclxuICAgICAgICB2YXIgaW5kaWNhdG9yO1xyXG4gICAgICAgIHN3aXRjaCAoZW50cnkubGV2ZWwpIHtcclxuICAgICAgICAgICAgY2FzZSBcIndlYlwiOlxyXG4gICAgICAgICAgICAgICAgaW5kaWNhdG9yID0gPGkgY2xhc3NOYW1lPVwiZmEgZmEtZncgZmEtaHRtbDVcIj48L2k+O1xyXG4gICAgICAgICAgICAgICAgYnJlYWs7XHJcbiAgICAgICAgICAgIGNhc2UgXCJkZWJ1Z1wiOlxyXG4gICAgICAgICAgICAgICAgaW5kaWNhdG9yID0gPGkgY2xhc3NOYW1lPVwiZmEgZmEtZncgZmEtYnVnXCI+PC9pPjtcclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBkZWZhdWx0OlxyXG4gICAgICAgICAgICAgICAgaW5kaWNhdG9yID0gPGkgY2xhc3NOYW1lPVwiZmEgZmEtZncgZmEtaW5mb1wiPjwvaT47XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxkaXY+XHJcbiAgICAgICAgICAgICAgICB7IGluZGljYXRvciB9IHtlbnRyeS5tZXNzYWdlfVxyXG4gICAgICAgICAgICA8L2Rpdj5cclxuICAgICAgICApO1xyXG4gICAgfSxcclxuICAgIHNob3VsZENvbXBvbmVudFVwZGF0ZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHJldHVybiBmYWxzZTsgLy8gbG9nIGVudHJpZXMgYXJlIGltbXV0YWJsZS5cclxuICAgIH1cclxufSk7XHJcblxyXG52YXIgRXZlbnRMb2dDb250ZW50cyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIG1peGluczogW2NvbW1vbi5BdXRvU2Nyb2xsTWl4aW4sIFZpcnR1YWxTY3JvbGxNaXhpbl0sXHJcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICByZXR1cm4ge1xyXG4gICAgICAgICAgICBsb2c6IFtdXHJcbiAgICAgICAgfTtcclxuICAgIH0sXHJcbiAgICBjb21wb25lbnRXaWxsTW91bnQ6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLm9wZW5WaWV3KHRoaXMucHJvcHMuZXZlbnRTdG9yZSk7XHJcbiAgICB9LFxyXG4gICAgY29tcG9uZW50V2lsbFVubW91bnQ6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLmNsb3NlVmlldygpO1xyXG4gICAgfSxcclxuICAgIG9wZW5WaWV3OiBmdW5jdGlvbiAoc3RvcmUpIHtcclxuICAgICAgICB2YXIgdmlldyA9IG5ldyB2aWV3cy5TdG9yZVZpZXcoc3RvcmUsIGZ1bmN0aW9uIChlbnRyeSkge1xyXG4gICAgICAgICAgICByZXR1cm4gdGhpcy5wcm9wcy5maWx0ZXJbZW50cnkubGV2ZWxdO1xyXG4gICAgICAgIH0uYmluZCh0aGlzKSk7XHJcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7XHJcbiAgICAgICAgICAgIHZpZXc6IHZpZXdcclxuICAgICAgICB9KTtcclxuXHJcbiAgICAgICAgdmlldy5hZGRMaXN0ZW5lcihcImFkZCByZWNhbGN1bGF0ZVwiLCB0aGlzLm9uRXZlbnRMb2dDaGFuZ2UpO1xyXG4gICAgfSxcclxuICAgIGNsb3NlVmlldzogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMuc3RhdGUudmlldy5jbG9zZSgpO1xyXG4gICAgfSxcclxuICAgIG9uRXZlbnRMb2dDaGFuZ2U6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLnNldFN0YXRlKHtcclxuICAgICAgICAgICAgbG9nOiB0aGlzLnN0YXRlLnZpZXcubGlzdFxyXG4gICAgICAgIH0pO1xyXG4gICAgfSxcclxuICAgIGNvbXBvbmVudFdpbGxSZWNlaXZlUHJvcHM6IGZ1bmN0aW9uIChuZXh0UHJvcHMpIHtcclxuICAgICAgICBpZiAobmV4dFByb3BzLmZpbHRlciAhPT0gdGhpcy5wcm9wcy5maWx0ZXIpIHtcclxuICAgICAgICAgICAgdGhpcy5wcm9wcy5maWx0ZXIgPSBuZXh0UHJvcHMuZmlsdGVyOyAvLyBEaXJ0eTogTWFrZSBzdXJlIHRoYXQgdmlldyBmaWx0ZXIgc2VlcyB0aGUgdXBkYXRlLlxyXG4gICAgICAgICAgICB0aGlzLnN0YXRlLnZpZXcucmVjYWxjdWxhdGUoKTtcclxuICAgICAgICB9XHJcbiAgICAgICAgaWYgKG5leHRQcm9wcy5ldmVudFN0b3JlICE9PSB0aGlzLnByb3BzLmV2ZW50U3RvcmUpIHtcclxuICAgICAgICAgICAgdGhpcy5jbG9zZVZpZXcoKTtcclxuICAgICAgICAgICAgdGhpcy5vcGVuVmlldyhuZXh0UHJvcHMuZXZlbnRTdG9yZSk7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIGdldERlZmF1bHRQcm9wczogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHJldHVybiB7XHJcbiAgICAgICAgICAgIHJvd0hlaWdodDogNDUsXHJcbiAgICAgICAgICAgIHJvd0hlaWdodE1pbjogMTUsXHJcbiAgICAgICAgICAgIHBsYWNlaG9sZGVyVGFnTmFtZTogXCJkaXZcIlxyXG4gICAgICAgIH07XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyUm93OiBmdW5jdGlvbiAoZWxlbSkge1xyXG4gICAgICAgIHJldHVybiA8TG9nTWVzc2FnZSBrZXk9e2VsZW0uaWR9IGVudHJ5PXtlbGVtfS8+O1xyXG4gICAgfSxcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciByb3dzID0gdGhpcy5yZW5kZXJSb3dzKHRoaXMuc3RhdGUubG9nKTtcclxuXHJcbiAgICAgICAgcmV0dXJuIDxwcmUgb25TY3JvbGw9e3RoaXMub25TY3JvbGx9PlxyXG4gICAgICAgICAgICB7IHRoaXMuZ2V0UGxhY2Vob2xkZXJUb3AodGhpcy5zdGF0ZS5sb2cubGVuZ3RoKSB9XHJcbiAgICAgICAgICAgIHtyb3dzfVxyXG4gICAgICAgICAgICB7IHRoaXMuZ2V0UGxhY2Vob2xkZXJCb3R0b20odGhpcy5zdGF0ZS5sb2cubGVuZ3RoKSB9XHJcbiAgICAgICAgPC9wcmU+O1xyXG4gICAgfVxyXG59KTtcclxuXHJcbnZhciBUb2dnbGVGaWx0ZXIgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICB0b2dnbGU6IGZ1bmN0aW9uIChlKSB7XHJcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xyXG4gICAgICAgIHJldHVybiB0aGlzLnByb3BzLnRvZ2dsZUxldmVsKHRoaXMucHJvcHMubmFtZSk7XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGNsYXNzTmFtZSA9IFwibGFiZWwgXCI7XHJcbiAgICAgICAgaWYgKHRoaXMucHJvcHMuYWN0aXZlKSB7XHJcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcImxhYmVsLXByaW1hcnlcIjtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCJsYWJlbC1kZWZhdWx0XCI7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxhXHJcbiAgICAgICAgICAgICAgICBocmVmPVwiI1wiXHJcbiAgICAgICAgICAgICAgICBjbGFzc05hbWU9e2NsYXNzTmFtZX1cclxuICAgICAgICAgICAgICAgIG9uQ2xpY2s9e3RoaXMudG9nZ2xlfT5cclxuICAgICAgICAgICAgICAgIHt0aGlzLnByb3BzLm5hbWV9XHJcbiAgICAgICAgICAgIDwvYT5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbnZhciBFdmVudExvZyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHJldHVybiB7XHJcbiAgICAgICAgICAgIGZpbHRlcjoge1xyXG4gICAgICAgICAgICAgICAgXCJkZWJ1Z1wiOiBmYWxzZSxcclxuICAgICAgICAgICAgICAgIFwiaW5mb1wiOiB0cnVlLFxyXG4gICAgICAgICAgICAgICAgXCJ3ZWJcIjogdHJ1ZVxyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgfTtcclxuICAgIH0sXHJcbiAgICBjbG9zZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBkID0ge307XHJcbiAgICAgICAgZFtRdWVyeS5TSE9XX0VWRU5UTE9HXSA9IHVuZGVmaW5lZDtcclxuICAgICAgICB0aGlzLnNldFF1ZXJ5KGQpO1xyXG4gICAgfSxcclxuICAgIHRvZ2dsZUxldmVsOiBmdW5jdGlvbiAobGV2ZWwpIHtcclxuICAgICAgICB2YXIgZmlsdGVyID0gXy5leHRlbmQoe30sIHRoaXMuc3RhdGUuZmlsdGVyKTtcclxuICAgICAgICBmaWx0ZXJbbGV2ZWxdID0gIWZpbHRlcltsZXZlbF07XHJcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7ZmlsdGVyOiBmaWx0ZXJ9KTtcclxuICAgIH0sXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cImV2ZW50bG9nXCI+XHJcbiAgICAgICAgICAgICAgICA8ZGl2PlxyXG4gICAgICAgICAgICAgICAgICAgIEV2ZW50bG9nXHJcbiAgICAgICAgICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJwdWxsLXJpZ2h0XCI+XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIDxUb2dnbGVGaWx0ZXIgbmFtZT1cImRlYnVnXCIgYWN0aXZlPXt0aGlzLnN0YXRlLmZpbHRlci5kZWJ1Z30gdG9nZ2xlTGV2ZWw9e3RoaXMudG9nZ2xlTGV2ZWx9Lz5cclxuICAgICAgICAgICAgICAgICAgICAgICAgPFRvZ2dsZUZpbHRlciBuYW1lPVwiaW5mb1wiIGFjdGl2ZT17dGhpcy5zdGF0ZS5maWx0ZXIuaW5mb30gdG9nZ2xlTGV2ZWw9e3RoaXMudG9nZ2xlTGV2ZWx9Lz5cclxuICAgICAgICAgICAgICAgICAgICAgICAgPFRvZ2dsZUZpbHRlciBuYW1lPVwid2ViXCIgYWN0aXZlPXt0aGlzLnN0YXRlLmZpbHRlci53ZWJ9IHRvZ2dsZUxldmVsPXt0aGlzLnRvZ2dsZUxldmVsfS8+XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIDxpIG9uQ2xpY2s9e3RoaXMuY2xvc2V9IGNsYXNzTmFtZT1cImZhIGZhLWNsb3NlXCI+PC9pPlxyXG4gICAgICAgICAgICAgICAgICAgIDwvZGl2PlxyXG5cclxuICAgICAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICAgICAgICAgPEV2ZW50TG9nQ29udGVudHMgZmlsdGVyPXt0aGlzLnN0YXRlLmZpbHRlcn0gZXZlbnRTdG9yZT17dGhpcy5wcm9wcy5ldmVudFN0b3JlfS8+XHJcbiAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxubW9kdWxlLmV4cG9ydHMgPSBFdmVudExvZzsiLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XHJcbnZhciBfID0gcmVxdWlyZShcImxvZGFzaFwiKTtcclxuXHJcbnZhciBjb21tb24gPSByZXF1aXJlKFwiLi9jb21tb24uanNcIik7XHJcbnZhciBhY3Rpb25zID0gcmVxdWlyZShcIi4uL2FjdGlvbnMuanNcIik7XHJcbnZhciBmbG93dXRpbHMgPSByZXF1aXJlKFwiLi4vZmxvdy91dGlscy5qc1wiKTtcclxudmFyIHRvcHV0aWxzID0gcmVxdWlyZShcIi4uL3V0aWxzLmpzXCIpO1xyXG5cclxudmFyIE5hdkFjdGlvbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIG9uQ2xpY2s6IGZ1bmN0aW9uIChlKSB7XHJcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xyXG4gICAgICAgIHRoaXMucHJvcHMub25DbGljaygpO1xyXG4gICAgfSxcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxhIHRpdGxlPXt0aGlzLnByb3BzLnRpdGxlfVxyXG4gICAgICAgICAgICAgICAgaHJlZj1cIiNcIlxyXG4gICAgICAgICAgICAgICAgY2xhc3NOYW1lPVwibmF2LWFjdGlvblwiXHJcbiAgICAgICAgICAgICAgICBvbkNsaWNrPXt0aGlzLm9uQ2xpY2t9PlxyXG4gICAgICAgICAgICAgICAgPGkgY2xhc3NOYW1lPXtcImZhIGZhLWZ3IFwiICsgdGhpcy5wcm9wcy5pY29ufT48L2k+XHJcbiAgICAgICAgICAgIDwvYT5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbnZhciBGbG93RGV0YWlsTmF2ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XHJcblxyXG4gICAgICAgIHZhciB0YWJzID0gdGhpcy5wcm9wcy50YWJzLm1hcChmdW5jdGlvbiAoZSkge1xyXG4gICAgICAgICAgICB2YXIgc3RyID0gZS5jaGFyQXQoMCkudG9VcHBlckNhc2UoKSArIGUuc2xpY2UoMSk7XHJcbiAgICAgICAgICAgIHZhciBjbGFzc05hbWUgPSB0aGlzLnByb3BzLmFjdGl2ZSA9PT0gZSA/IFwiYWN0aXZlXCIgOiBcIlwiO1xyXG4gICAgICAgICAgICB2YXIgb25DbGljayA9IGZ1bmN0aW9uIChldmVudCkge1xyXG4gICAgICAgICAgICAgICAgdGhpcy5wcm9wcy5zZWxlY3RUYWIoZSk7XHJcbiAgICAgICAgICAgICAgICBldmVudC5wcmV2ZW50RGVmYXVsdCgpO1xyXG4gICAgICAgICAgICB9LmJpbmQodGhpcyk7XHJcbiAgICAgICAgICAgIHJldHVybiA8YSBrZXk9e2V9XHJcbiAgICAgICAgICAgICAgICBocmVmPVwiI1wiXHJcbiAgICAgICAgICAgICAgICBjbGFzc05hbWU9e2NsYXNzTmFtZX1cclxuICAgICAgICAgICAgICAgIG9uQ2xpY2s9e29uQ2xpY2t9PntzdHJ9PC9hPjtcclxuICAgICAgICB9LmJpbmQodGhpcykpO1xyXG5cclxuICAgICAgICB2YXIgYWNjZXB0QnV0dG9uID0gbnVsbDtcclxuICAgICAgICBpZihmbG93LmludGVyY2VwdGVkKXtcclxuICAgICAgICAgICAgYWNjZXB0QnV0dG9uID0gPE5hdkFjdGlvbiB0aXRsZT1cIlthXWNjZXB0IGludGVyY2VwdGVkIGZsb3dcIiBpY29uPVwiZmEtcGxheVwiIG9uQ2xpY2s9e2FjdGlvbnMuRmxvd0FjdGlvbnMuYWNjZXB0LmJpbmQobnVsbCwgZmxvdyl9IC8+O1xyXG4gICAgICAgIH1cclxuICAgICAgICB2YXIgcmV2ZXJ0QnV0dG9uID0gbnVsbDtcclxuICAgICAgICBpZihmbG93Lm1vZGlmaWVkKXtcclxuICAgICAgICAgICAgcmV2ZXJ0QnV0dG9uID0gPE5hdkFjdGlvbiB0aXRsZT1cInJldmVydCBjaGFuZ2VzIHRvIGZsb3cgW1ZdXCIgaWNvbj1cImZhLWhpc3RvcnlcIiBvbkNsaWNrPXthY3Rpb25zLkZsb3dBY3Rpb25zLnJldmVydC5iaW5kKG51bGwsIGZsb3cpfSAvPjtcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxuYXYgcmVmPVwiaGVhZFwiIGNsYXNzTmFtZT1cIm5hdi10YWJzIG5hdi10YWJzLXNtXCI+XHJcbiAgICAgICAgICAgICAgICB7dGFic31cclxuICAgICAgICAgICAgICAgIDxOYXZBY3Rpb24gdGl0bGU9XCJbZF1lbGV0ZSBmbG93XCIgaWNvbj1cImZhLXRyYXNoXCIgb25DbGljaz17YWN0aW9ucy5GbG93QWN0aW9ucy5kZWxldGUuYmluZChudWxsLCBmbG93KX0gLz5cclxuICAgICAgICAgICAgICAgIDxOYXZBY3Rpb24gdGl0bGU9XCJbRF11cGxpY2F0ZSBmbG93XCIgaWNvbj1cImZhLWNvcHlcIiBvbkNsaWNrPXthY3Rpb25zLkZsb3dBY3Rpb25zLmR1cGxpY2F0ZS5iaW5kKG51bGwsIGZsb3cpfSAvPlxyXG4gICAgICAgICAgICAgICAgPE5hdkFjdGlvbiBkaXNhYmxlZCB0aXRsZT1cIltyXWVwbGF5IGZsb3dcIiBpY29uPVwiZmEtcmVwZWF0XCIgb25DbGljaz17YWN0aW9ucy5GbG93QWN0aW9ucy5yZXBsYXkuYmluZChudWxsLCBmbG93KX0gLz5cclxuICAgICAgICAgICAgICAgIHthY2NlcHRCdXR0b259XHJcbiAgICAgICAgICAgICAgICB7cmV2ZXJ0QnV0dG9ufVxyXG4gICAgICAgICAgICA8L25hdj5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbnZhciBIZWFkZXJzID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIHJvd3MgPSB0aGlzLnByb3BzLm1lc3NhZ2UuaGVhZGVycy5tYXAoZnVuY3Rpb24gKGhlYWRlciwgaSkge1xyXG4gICAgICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICAgICAgPHRyIGtleT17aX0+XHJcbiAgICAgICAgICAgICAgICAgICAgPHRkIGNsYXNzTmFtZT1cImhlYWRlci1uYW1lXCI+e2hlYWRlclswXSArIFwiOlwifTwvdGQ+XHJcbiAgICAgICAgICAgICAgICAgICAgPHRkIGNsYXNzTmFtZT1cImhlYWRlci12YWx1ZVwiPntoZWFkZXJbMV19PC90ZD5cclxuICAgICAgICAgICAgICAgIDwvdHI+XHJcbiAgICAgICAgICAgICk7XHJcbiAgICAgICAgfSk7XHJcbiAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgPHRhYmxlIGNsYXNzTmFtZT1cImhlYWRlci10YWJsZVwiPlxyXG4gICAgICAgICAgICAgICAgPHRib2R5PlxyXG4gICAgICAgICAgICAgICAgICAgIHtyb3dzfVxyXG4gICAgICAgICAgICAgICAgPC90Ym9keT5cclxuICAgICAgICAgICAgPC90YWJsZT5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbnZhciBGbG93RGV0YWlsUmVxdWVzdCA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xyXG4gICAgICAgIHZhciBmaXJzdF9saW5lID0gW1xyXG4gICAgICAgICAgICBmbG93LnJlcXVlc3QubWV0aG9kLFxyXG4gICAgICAgICAgICBmbG93dXRpbHMuUmVxdWVzdFV0aWxzLnByZXR0eV91cmwoZmxvdy5yZXF1ZXN0KSxcclxuICAgICAgICAgICAgXCJIVFRQL1wiICsgZmxvdy5yZXF1ZXN0Lmh0dHB2ZXJzaW9uLmpvaW4oXCIuXCIpXHJcbiAgICAgICAgXS5qb2luKFwiIFwiKTtcclxuICAgICAgICB2YXIgY29udGVudCA9IG51bGw7XHJcbiAgICAgICAgaWYgKGZsb3cucmVxdWVzdC5jb250ZW50TGVuZ3RoID4gMCkge1xyXG4gICAgICAgICAgICBjb250ZW50ID0gXCJSZXF1ZXN0IENvbnRlbnQgU2l6ZTogXCIgKyB0b3B1dGlscy5mb3JtYXRTaXplKGZsb3cucmVxdWVzdC5jb250ZW50TGVuZ3RoKTtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICBjb250ZW50ID0gPGRpdiBjbGFzc05hbWU9XCJhbGVydCBhbGVydC1pbmZvXCI+Tm8gQ29udGVudDwvZGl2PjtcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIC8vVE9ETzogU3R5bGluZ1xyXG5cclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8c2VjdGlvbj5cclxuICAgICAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPVwiZmlyc3QtbGluZVwiPnsgZmlyc3RfbGluZSB9PC9kaXY+XHJcbiAgICAgICAgICAgICAgICA8SGVhZGVycyBtZXNzYWdlPXtmbG93LnJlcXVlc3R9Lz5cclxuICAgICAgICAgICAgICAgIDxoci8+XHJcbiAgICAgICAgICAgICAgICB7Y29udGVudH1cclxuICAgICAgICAgICAgPC9zZWN0aW9uPlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIEZsb3dEZXRhaWxSZXNwb25zZSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xyXG4gICAgICAgIHZhciBmaXJzdF9saW5lID0gW1xyXG4gICAgICAgICAgICBcIkhUVFAvXCIgKyBmbG93LnJlc3BvbnNlLmh0dHB2ZXJzaW9uLmpvaW4oXCIuXCIpLFxyXG4gICAgICAgICAgICBmbG93LnJlc3BvbnNlLmNvZGUsXHJcbiAgICAgICAgICAgIGZsb3cucmVzcG9uc2UubXNnXHJcbiAgICAgICAgXS5qb2luKFwiIFwiKTtcclxuICAgICAgICB2YXIgY29udGVudCA9IG51bGw7XHJcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UuY29udGVudExlbmd0aCA+IDApIHtcclxuICAgICAgICAgICAgY29udGVudCA9IFwiUmVzcG9uc2UgQ29udGVudCBTaXplOiBcIiArIHRvcHV0aWxzLmZvcm1hdFNpemUoZmxvdy5yZXNwb25zZS5jb250ZW50TGVuZ3RoKTtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICBjb250ZW50ID0gPGRpdiBjbGFzc05hbWU9XCJhbGVydCBhbGVydC1pbmZvXCI+Tm8gQ29udGVudDwvZGl2PjtcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIC8vVE9ETzogU3R5bGluZ1xyXG5cclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8c2VjdGlvbj5cclxuICAgICAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPVwiZmlyc3QtbGluZVwiPnsgZmlyc3RfbGluZSB9PC9kaXY+XHJcbiAgICAgICAgICAgICAgICA8SGVhZGVycyBtZXNzYWdlPXtmbG93LnJlc3BvbnNlfS8+XHJcbiAgICAgICAgICAgICAgICA8aHIvPlxyXG4gICAgICAgICAgICAgICAge2NvbnRlbnR9XHJcbiAgICAgICAgICAgIDwvc2VjdGlvbj5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbnZhciBGbG93RGV0YWlsRXJyb3IgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8c2VjdGlvbj5cclxuICAgICAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPVwiYWxlcnQgYWxlcnQtd2FybmluZ1wiPlxyXG4gICAgICAgICAgICAgICAge2Zsb3cuZXJyb3IubXNnfVxyXG4gICAgICAgICAgICAgICAgICAgIDxkaXY+XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIDxzbWFsbD57IHRvcHV0aWxzLmZvcm1hdFRpbWVTdGFtcChmbG93LmVycm9yLnRpbWVzdGFtcCkgfTwvc21hbGw+XHJcbiAgICAgICAgICAgICAgICAgICAgPC9kaXY+XHJcbiAgICAgICAgICAgICAgICA8L2Rpdj5cclxuICAgICAgICAgICAgPC9zZWN0aW9uPlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIFRpbWVTdGFtcCA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG5cclxuICAgICAgICBpZiAoIXRoaXMucHJvcHMudCkge1xyXG4gICAgICAgICAgICAvL3Nob3VsZCBiZSByZXR1cm4gbnVsbCwgYnV0IHRoYXQgdHJpZ2dlcnMgYSBSZWFjdCBidWcuXHJcbiAgICAgICAgICAgIHJldHVybiA8dHI+PC90cj47XHJcbiAgICAgICAgfVxyXG5cclxuICAgICAgICB2YXIgdHMgPSB0b3B1dGlscy5mb3JtYXRUaW1lU3RhbXAodGhpcy5wcm9wcy50KTtcclxuXHJcbiAgICAgICAgdmFyIGRlbHRhO1xyXG4gICAgICAgIGlmICh0aGlzLnByb3BzLmRlbHRhVG8pIHtcclxuICAgICAgICAgICAgZGVsdGEgPSB0b3B1dGlscy5mb3JtYXRUaW1lRGVsdGEoMTAwMCAqICh0aGlzLnByb3BzLnQgLSB0aGlzLnByb3BzLmRlbHRhVG8pKTtcclxuICAgICAgICAgICAgZGVsdGEgPSA8c3BhbiBjbGFzc05hbWU9XCJ0ZXh0LW11dGVkXCI+e1wiKFwiICsgZGVsdGEgKyBcIilcIn08L3NwYW4+O1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIGRlbHRhID0gbnVsbDtcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIHJldHVybiA8dHI+XHJcbiAgICAgICAgICAgIDx0ZD57dGhpcy5wcm9wcy50aXRsZSArIFwiOlwifTwvdGQ+XHJcbiAgICAgICAgICAgIDx0ZD57dHN9IHtkZWx0YX08L3RkPlxyXG4gICAgICAgIDwvdHI+O1xyXG4gICAgfVxyXG59KTtcclxuXHJcbnZhciBDb25uZWN0aW9uSW5mbyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgY29ubiA9IHRoaXMucHJvcHMuY29ubjtcclxuICAgICAgICB2YXIgYWRkcmVzcyA9IGNvbm4uYWRkcmVzcy5hZGRyZXNzLmpvaW4oXCI6XCIpO1xyXG5cclxuICAgICAgICB2YXIgc25pID0gPHRyIGtleT1cInNuaVwiPjwvdHI+OyAvL3Nob3VsZCBiZSBudWxsLCBidXQgdGhhdCB0cmlnZ2VycyBhIFJlYWN0IGJ1Zy5cclxuICAgICAgICBpZiAoY29ubi5zbmkpIHtcclxuICAgICAgICAgICAgc25pID0gPHRyIGtleT1cInNuaVwiPlxyXG4gICAgICAgICAgICAgICAgPHRkPlxyXG4gICAgICAgICAgICAgICAgICAgIDxhYmJyIHRpdGxlPVwiVExTIFNlcnZlciBOYW1lIEluZGljYXRpb25cIj5UTFMgU05JOjwvYWJicj5cclxuICAgICAgICAgICAgICAgIDwvdGQ+XHJcbiAgICAgICAgICAgICAgICA8dGQ+e2Nvbm4uc25pfTwvdGQ+XHJcbiAgICAgICAgICAgIDwvdHI+O1xyXG4gICAgICAgIH1cclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8dGFibGUgY2xhc3NOYW1lPVwiY29ubmVjdGlvbi10YWJsZVwiPlxyXG4gICAgICAgICAgICAgICAgPHRib2R5PlxyXG4gICAgICAgICAgICAgICAgICAgIDx0ciBrZXk9XCJhZGRyZXNzXCI+XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIDx0ZD5BZGRyZXNzOjwvdGQ+XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIDx0ZD57YWRkcmVzc308L3RkPlxyXG4gICAgICAgICAgICAgICAgICAgIDwvdHI+XHJcbiAgICAgICAgICAgICAgICAgICAge3NuaX1cclxuICAgICAgICAgICAgICAgIDwvdGJvZHk+XHJcbiAgICAgICAgICAgIDwvdGFibGU+XHJcbiAgICAgICAgKTtcclxuICAgIH1cclxufSk7XHJcblxyXG52YXIgQ2VydGlmaWNhdGVJbmZvID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgLy9UT0RPOiBXZSBzaG91bGQgZmV0Y2ggaHVtYW4tcmVhZGFibGUgY2VydGlmaWNhdGUgcmVwcmVzZW50YXRpb25cclxuICAgICAgICAvLyBmcm9tIHRoZSBzZXJ2ZXJcclxuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcclxuICAgICAgICB2YXIgY2xpZW50X2Nvbm4gPSBmbG93LmNsaWVudF9jb25uO1xyXG4gICAgICAgIHZhciBzZXJ2ZXJfY29ubiA9IGZsb3cuc2VydmVyX2Nvbm47XHJcblxyXG4gICAgICAgIHZhciBwcmVTdHlsZSA9IHttYXhIZWlnaHQ6IDEwMH07XHJcbiAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgPGRpdj5cclxuICAgICAgICAgICAge2NsaWVudF9jb25uLmNlcnQgPyA8aDQ+Q2xpZW50IENlcnRpZmljYXRlPC9oND4gOiBudWxsfVxyXG4gICAgICAgICAgICB7Y2xpZW50X2Nvbm4uY2VydCA/IDxwcmUgc3R5bGU9e3ByZVN0eWxlfT57Y2xpZW50X2Nvbm4uY2VydH08L3ByZT4gOiBudWxsfVxyXG5cclxuICAgICAgICAgICAge3NlcnZlcl9jb25uLmNlcnQgPyA8aDQ+U2VydmVyIENlcnRpZmljYXRlPC9oND4gOiBudWxsfVxyXG4gICAgICAgICAgICB7c2VydmVyX2Nvbm4uY2VydCA/IDxwcmUgc3R5bGU9e3ByZVN0eWxlfT57c2VydmVyX2Nvbm4uY2VydH08L3ByZT4gOiBudWxsfVxyXG4gICAgICAgICAgICA8L2Rpdj5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbnZhciBUaW1pbmcgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcclxuICAgICAgICB2YXIgc2MgPSBmbG93LnNlcnZlcl9jb25uO1xyXG4gICAgICAgIHZhciBjYyA9IGZsb3cuY2xpZW50X2Nvbm47XHJcbiAgICAgICAgdmFyIHJlcSA9IGZsb3cucmVxdWVzdDtcclxuICAgICAgICB2YXIgcmVzcCA9IGZsb3cucmVzcG9uc2U7XHJcblxyXG4gICAgICAgIHZhciB0aW1lc3RhbXBzID0gW1xyXG4gICAgICAgICAgICB7XHJcbiAgICAgICAgICAgICAgICB0aXRsZTogXCJTZXJ2ZXIgY29ubi4gaW5pdGlhdGVkXCIsXHJcbiAgICAgICAgICAgICAgICB0OiBzYy50aW1lc3RhbXBfc3RhcnQsXHJcbiAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XHJcbiAgICAgICAgICAgIH0sIHtcclxuICAgICAgICAgICAgICAgIHRpdGxlOiBcIlNlcnZlciBjb25uLiBUQ1AgaGFuZHNoYWtlXCIsXHJcbiAgICAgICAgICAgICAgICB0OiBzYy50aW1lc3RhbXBfdGNwX3NldHVwLFxyXG4gICAgICAgICAgICAgICAgZGVsdGFUbzogcmVxLnRpbWVzdGFtcF9zdGFydFxyXG4gICAgICAgICAgICB9LCB7XHJcbiAgICAgICAgICAgICAgICB0aXRsZTogXCJTZXJ2ZXIgY29ubi4gU1NMIGhhbmRzaGFrZVwiLFxyXG4gICAgICAgICAgICAgICAgdDogc2MudGltZXN0YW1wX3NzbF9zZXR1cCxcclxuICAgICAgICAgICAgICAgIGRlbHRhVG86IHJlcS50aW1lc3RhbXBfc3RhcnRcclxuICAgICAgICAgICAgfSwge1xyXG4gICAgICAgICAgICAgICAgdGl0bGU6IFwiQ2xpZW50IGNvbm4uIGVzdGFibGlzaGVkXCIsXHJcbiAgICAgICAgICAgICAgICB0OiBjYy50aW1lc3RhbXBfc3RhcnQsXHJcbiAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XHJcbiAgICAgICAgICAgIH0sIHtcclxuICAgICAgICAgICAgICAgIHRpdGxlOiBcIkNsaWVudCBjb25uLiBTU0wgaGFuZHNoYWtlXCIsXHJcbiAgICAgICAgICAgICAgICB0OiBjYy50aW1lc3RhbXBfc3NsX3NldHVwLFxyXG4gICAgICAgICAgICAgICAgZGVsdGFUbzogcmVxLnRpbWVzdGFtcF9zdGFydFxyXG4gICAgICAgICAgICB9LCB7XHJcbiAgICAgICAgICAgICAgICB0aXRsZTogXCJGaXJzdCByZXF1ZXN0IGJ5dGVcIixcclxuICAgICAgICAgICAgICAgIHQ6IHJlcS50aW1lc3RhbXBfc3RhcnQsXHJcbiAgICAgICAgICAgIH0sIHtcclxuICAgICAgICAgICAgICAgIHRpdGxlOiBcIlJlcXVlc3QgY29tcGxldGVcIixcclxuICAgICAgICAgICAgICAgIHQ6IHJlcS50aW1lc3RhbXBfZW5kLFxyXG4gICAgICAgICAgICAgICAgZGVsdGFUbzogcmVxLnRpbWVzdGFtcF9zdGFydFxyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgXTtcclxuXHJcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UpIHtcclxuICAgICAgICAgICAgdGltZXN0YW1wcy5wdXNoKFxyXG4gICAgICAgICAgICAgICAge1xyXG4gICAgICAgICAgICAgICAgICAgIHRpdGxlOiBcIkZpcnN0IHJlc3BvbnNlIGJ5dGVcIixcclxuICAgICAgICAgICAgICAgICAgICB0OiByZXNwLnRpbWVzdGFtcF9zdGFydCxcclxuICAgICAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XHJcbiAgICAgICAgICAgICAgICB9LCB7XHJcbiAgICAgICAgICAgICAgICAgICAgdGl0bGU6IFwiUmVzcG9uc2UgY29tcGxldGVcIixcclxuICAgICAgICAgICAgICAgICAgICB0OiByZXNwLnRpbWVzdGFtcF9lbmQsXHJcbiAgICAgICAgICAgICAgICAgICAgZGVsdGFUbzogcmVxLnRpbWVzdGFtcF9zdGFydFxyXG4gICAgICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICApO1xyXG4gICAgICAgIH1cclxuXHJcbiAgICAgICAgLy9BZGQgdW5pcXVlIGtleSBmb3IgZWFjaCByb3cuXHJcbiAgICAgICAgdGltZXN0YW1wcy5mb3JFYWNoKGZ1bmN0aW9uIChlKSB7XHJcbiAgICAgICAgICAgIGUua2V5ID0gZS50aXRsZTtcclxuICAgICAgICB9KTtcclxuXHJcbiAgICAgICAgdGltZXN0YW1wcyA9IF8uc29ydEJ5KHRpbWVzdGFtcHMsICd0Jyk7XHJcblxyXG4gICAgICAgIHZhciByb3dzID0gdGltZXN0YW1wcy5tYXAoZnVuY3Rpb24gKGUpIHtcclxuICAgICAgICAgICAgcmV0dXJuIDxUaW1lU3RhbXAgey4uLmV9Lz47XHJcbiAgICAgICAgfSk7XHJcblxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxkaXY+XHJcbiAgICAgICAgICAgICAgICA8aDQ+VGltaW5nPC9oND5cclxuICAgICAgICAgICAgICAgIDx0YWJsZSBjbGFzc05hbWU9XCJ0aW1pbmctdGFibGVcIj5cclxuICAgICAgICAgICAgICAgICAgICA8dGJvZHk+XHJcbiAgICAgICAgICAgICAgICAgICAge3Jvd3N9XHJcbiAgICAgICAgICAgICAgICAgICAgPC90Ym9keT5cclxuICAgICAgICAgICAgICAgIDwvdGFibGU+XHJcbiAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIEZsb3dEZXRhaWxDb25uZWN0aW9uSW5mbyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xyXG4gICAgICAgIHZhciBjbGllbnRfY29ubiA9IGZsb3cuY2xpZW50X2Nvbm47XHJcbiAgICAgICAgdmFyIHNlcnZlcl9jb25uID0gZmxvdy5zZXJ2ZXJfY29ubjtcclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8c2VjdGlvbj5cclxuXHJcbiAgICAgICAgICAgICAgICA8aDQ+Q2xpZW50IENvbm5lY3Rpb248L2g0PlxyXG4gICAgICAgICAgICAgICAgPENvbm5lY3Rpb25JbmZvIGNvbm49e2NsaWVudF9jb25ufS8+XHJcblxyXG4gICAgICAgICAgICAgICAgPGg0PlNlcnZlciBDb25uZWN0aW9uPC9oND5cclxuICAgICAgICAgICAgICAgIDxDb25uZWN0aW9uSW5mbyBjb25uPXtzZXJ2ZXJfY29ubn0vPlxyXG5cclxuICAgICAgICAgICAgICAgIDxDZXJ0aWZpY2F0ZUluZm8gZmxvdz17Zmxvd30vPlxyXG5cclxuICAgICAgICAgICAgICAgIDxUaW1pbmcgZmxvdz17Zmxvd30vPlxyXG5cclxuICAgICAgICAgICAgPC9zZWN0aW9uPlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIGFsbFRhYnMgPSB7XHJcbiAgICByZXF1ZXN0OiBGbG93RGV0YWlsUmVxdWVzdCxcclxuICAgIHJlc3BvbnNlOiBGbG93RGV0YWlsUmVzcG9uc2UsXHJcbiAgICBlcnJvcjogRmxvd0RldGFpbEVycm9yLFxyXG4gICAgZGV0YWlsczogRmxvd0RldGFpbENvbm5lY3Rpb25JbmZvXHJcbn07XHJcblxyXG52YXIgRmxvd0RldGFpbCA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIG1peGluczogW2NvbW1vbi5TdGlja3lIZWFkTWl4aW4sIGNvbW1vbi5OYXZpZ2F0aW9uLCBjb21tb24uU3RhdGVdLFxyXG4gICAgZ2V0VGFiczogZnVuY3Rpb24gKGZsb3cpIHtcclxuICAgICAgICB2YXIgdGFicyA9IFtdO1xyXG4gICAgICAgIFtcInJlcXVlc3RcIiwgXCJyZXNwb25zZVwiLCBcImVycm9yXCJdLmZvckVhY2goZnVuY3Rpb24gKGUpIHtcclxuICAgICAgICAgICAgaWYgKGZsb3dbZV0pIHtcclxuICAgICAgICAgICAgICAgIHRhYnMucHVzaChlKTtcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgIH0pO1xyXG4gICAgICAgIHRhYnMucHVzaChcImRldGFpbHNcIik7XHJcbiAgICAgICAgcmV0dXJuIHRhYnM7XHJcbiAgICB9LFxyXG4gICAgbmV4dFRhYjogZnVuY3Rpb24gKGkpIHtcclxuICAgICAgICB2YXIgdGFicyA9IHRoaXMuZ2V0VGFicyh0aGlzLnByb3BzLmZsb3cpO1xyXG4gICAgICAgIHZhciBjdXJyZW50SW5kZXggPSB0YWJzLmluZGV4T2YodGhpcy5nZXRQYXJhbXMoKS5kZXRhaWxUYWIpO1xyXG4gICAgICAgIC8vIEpTIG1vZHVsbyBvcGVyYXRvciBkb2Vzbid0IGNvcnJlY3QgbmVnYXRpdmUgbnVtYmVycywgbWFrZSBzdXJlIHRoYXQgd2UgYXJlIHBvc2l0aXZlLlxyXG4gICAgICAgIHZhciBuZXh0SW5kZXggPSAoY3VycmVudEluZGV4ICsgaSArIHRhYnMubGVuZ3RoKSAlIHRhYnMubGVuZ3RoO1xyXG4gICAgICAgIHRoaXMuc2VsZWN0VGFiKHRhYnNbbmV4dEluZGV4XSk7XHJcbiAgICB9LFxyXG4gICAgc2VsZWN0VGFiOiBmdW5jdGlvbiAocGFuZWwpIHtcclxuICAgICAgICB0aGlzLnJlcGxhY2VXaXRoKFxyXG4gICAgICAgICAgICBcImZsb3dcIixcclxuICAgICAgICAgICAge1xyXG4gICAgICAgICAgICAgICAgZmxvd0lkOiB0aGlzLmdldFBhcmFtcygpLmZsb3dJZCxcclxuICAgICAgICAgICAgICAgIGRldGFpbFRhYjogcGFuZWxcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgICk7XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XHJcbiAgICAgICAgdmFyIHRhYnMgPSB0aGlzLmdldFRhYnMoZmxvdyk7XHJcbiAgICAgICAgdmFyIGFjdGl2ZSA9IHRoaXMuZ2V0UGFyYW1zKCkuZGV0YWlsVGFiO1xyXG5cclxuICAgICAgICBpZiAoIV8uY29udGFpbnModGFicywgYWN0aXZlKSkge1xyXG4gICAgICAgICAgICBpZiAoYWN0aXZlID09PSBcInJlc3BvbnNlXCIgJiYgZmxvdy5lcnJvcikge1xyXG4gICAgICAgICAgICAgICAgYWN0aXZlID0gXCJlcnJvclwiO1xyXG4gICAgICAgICAgICB9IGVsc2UgaWYgKGFjdGl2ZSA9PT0gXCJlcnJvclwiICYmIGZsb3cucmVzcG9uc2UpIHtcclxuICAgICAgICAgICAgICAgIGFjdGl2ZSA9IFwicmVzcG9uc2VcIjtcclxuICAgICAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgICAgIGFjdGl2ZSA9IHRhYnNbMF07XHJcbiAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgdGhpcy5zZWxlY3RUYWIoYWN0aXZlKTtcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIHZhciBUYWIgPSBhbGxUYWJzW2FjdGl2ZV07XHJcbiAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJmbG93LWRldGFpbFwiIG9uU2Nyb2xsPXt0aGlzLmFkanVzdEhlYWR9PlxyXG4gICAgICAgICAgICAgICAgPEZsb3dEZXRhaWxOYXYgcmVmPVwiaGVhZFwiXHJcbiAgICAgICAgICAgICAgICAgICAgZmxvdz17Zmxvd31cclxuICAgICAgICAgICAgICAgICAgICB0YWJzPXt0YWJzfVxyXG4gICAgICAgICAgICAgICAgICAgIGFjdGl2ZT17YWN0aXZlfVxyXG4gICAgICAgICAgICAgICAgICAgIHNlbGVjdFRhYj17dGhpcy5zZWxlY3RUYWJ9Lz5cclxuICAgICAgICAgICAgICAgIDxUYWIgZmxvdz17Zmxvd30vPlxyXG4gICAgICAgICAgICA8L2Rpdj5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbm1vZHVsZS5leHBvcnRzID0ge1xyXG4gICAgRmxvd0RldGFpbDogRmxvd0RldGFpbFxyXG59OyIsInZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcclxudmFyIGZsb3d1dGlscyA9IHJlcXVpcmUoXCIuLi9mbG93L3V0aWxzLmpzXCIpO1xyXG52YXIgdXRpbHMgPSByZXF1aXJlKFwiLi4vdXRpbHMuanNcIik7XHJcblxyXG52YXIgVExTQ29sdW1uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgc3RhdGljczoge1xyXG4gICAgICAgIHJlbmRlclRpdGxlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgICAgIHJldHVybiA8dGgga2V5PVwidGxzXCIgY2xhc3NOYW1lPVwiY29sLXRsc1wiPjwvdGg+O1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcclxuICAgICAgICB2YXIgc3NsID0gKGZsb3cucmVxdWVzdC5zY2hlbWUgPT0gXCJodHRwc1wiKTtcclxuICAgICAgICB2YXIgY2xhc3NlcztcclxuICAgICAgICBpZiAoc3NsKSB7XHJcbiAgICAgICAgICAgIGNsYXNzZXMgPSBcImNvbC10bHMgY29sLXRscy1odHRwc1wiO1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIGNsYXNzZXMgPSBcImNvbC10bHMgY29sLXRscy1odHRwXCI7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHJldHVybiA8dGQgY2xhc3NOYW1lPXtjbGFzc2VzfT48L3RkPjtcclxuICAgIH1cclxufSk7XHJcblxyXG5cclxudmFyIEljb25Db2x1bW4gPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICBzdGF0aWNzOiB7XHJcbiAgICAgICAgcmVuZGVyVGl0bGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAgICAgcmV0dXJuIDx0aCBrZXk9XCJpY29uXCIgY2xhc3NOYW1lPVwiY29sLWljb25cIj48L3RoPjtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XHJcblxyXG4gICAgICAgIHZhciBpY29uO1xyXG4gICAgICAgIGlmIChmbG93LnJlc3BvbnNlKSB7XHJcbiAgICAgICAgICAgIHZhciBjb250ZW50VHlwZSA9IGZsb3d1dGlscy5SZXNwb25zZVV0aWxzLmdldENvbnRlbnRUeXBlKGZsb3cucmVzcG9uc2UpO1xyXG5cclxuICAgICAgICAgICAgLy9UT0RPOiBXZSBzaG91bGQgYXNzaWduIGEgdHlwZSB0byB0aGUgZmxvdyBzb21ld2hlcmUgZWxzZS5cclxuICAgICAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UuY29kZSA9PSAzMDQpIHtcclxuICAgICAgICAgICAgICAgIGljb24gPSBcInJlc291cmNlLWljb24tbm90LW1vZGlmaWVkXCI7XHJcbiAgICAgICAgICAgIH0gZWxzZSBpZiAoMzAwIDw9IGZsb3cucmVzcG9uc2UuY29kZSAmJiBmbG93LnJlc3BvbnNlLmNvZGUgPCA0MDApIHtcclxuICAgICAgICAgICAgICAgIGljb24gPSBcInJlc291cmNlLWljb24tcmVkaXJlY3RcIjtcclxuICAgICAgICAgICAgfSBlbHNlIGlmIChjb250ZW50VHlwZSAmJiBjb250ZW50VHlwZS5pbmRleE9mKFwiaW1hZ2VcIikgPj0gMCkge1xyXG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1pbWFnZVwiO1xyXG4gICAgICAgICAgICB9IGVsc2UgaWYgKGNvbnRlbnRUeXBlICYmIGNvbnRlbnRUeXBlLmluZGV4T2YoXCJqYXZhc2NyaXB0XCIpID49IDApIHtcclxuICAgICAgICAgICAgICAgIGljb24gPSBcInJlc291cmNlLWljb24tanNcIjtcclxuICAgICAgICAgICAgfSBlbHNlIGlmIChjb250ZW50VHlwZSAmJiBjb250ZW50VHlwZS5pbmRleE9mKFwiY3NzXCIpID49IDApIHtcclxuICAgICAgICAgICAgICAgIGljb24gPSBcInJlc291cmNlLWljb24tY3NzXCI7XHJcbiAgICAgICAgICAgIH0gZWxzZSBpZiAoY29udGVudFR5cGUgJiYgY29udGVudFR5cGUuaW5kZXhPZihcImh0bWxcIikgPj0gMCkge1xyXG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1kb2N1bWVudFwiO1xyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgfVxyXG4gICAgICAgIGlmICghaWNvbikge1xyXG4gICAgICAgICAgICBpY29uID0gXCJyZXNvdXJjZS1pY29uLXBsYWluXCI7XHJcbiAgICAgICAgfVxyXG5cclxuXHJcbiAgICAgICAgaWNvbiArPSBcIiByZXNvdXJjZS1pY29uXCI7XHJcbiAgICAgICAgcmV0dXJuIDx0ZCBjbGFzc05hbWU9XCJjb2wtaWNvblwiPlxyXG4gICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT17aWNvbn0+PC9kaXY+XHJcbiAgICAgICAgPC90ZD47XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIFBhdGhDb2x1bW4gPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICBzdGF0aWNzOiB7XHJcbiAgICAgICAgcmVuZGVyVGl0bGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAgICAgcmV0dXJuIDx0aCBrZXk9XCJwYXRoXCIgY2xhc3NOYW1lPVwiY29sLXBhdGhcIj5QYXRoPC90aD47XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xyXG4gICAgICAgIHJldHVybiA8dGQgY2xhc3NOYW1lPVwiY29sLXBhdGhcIj5cclxuICAgICAgICAgICAge2Zsb3cucmVxdWVzdC5pc19yZXBsYXkgPyA8aSBjbGFzc05hbWU9XCJmYSBmYS1mdyBmYS1yZXBlYXQgcHVsbC1yaWdodFwiPjwvaT4gOiBudWxsfVxyXG4gICAgICAgICAgICB7Zmxvdy5pbnRlcmNlcHRlZCA/IDxpIGNsYXNzTmFtZT1cImZhIGZhLWZ3IGZhLXBhdXNlIHB1bGwtcmlnaHRcIj48L2k+IDogbnVsbH1cclxuICAgICAgICAgICAge2Zsb3cucmVxdWVzdC5zY2hlbWUgKyBcIjovL1wiICsgZmxvdy5yZXF1ZXN0Lmhvc3QgKyBmbG93LnJlcXVlc3QucGF0aH1cclxuICAgICAgICA8L3RkPjtcclxuICAgIH1cclxufSk7XHJcblxyXG5cclxudmFyIE1ldGhvZENvbHVtbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHN0YXRpY3M6IHtcclxuICAgICAgICByZW5kZXJUaXRsZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgICAgICByZXR1cm4gPHRoIGtleT1cIm1ldGhvZFwiIGNsYXNzTmFtZT1cImNvbC1tZXRob2RcIj5NZXRob2Q8L3RoPjtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XHJcbiAgICAgICAgcmV0dXJuIDx0ZCBjbGFzc05hbWU9XCJjb2wtbWV0aG9kXCI+e2Zsb3cucmVxdWVzdC5tZXRob2R9PC90ZD47XHJcbiAgICB9XHJcbn0pO1xyXG5cclxuXHJcbnZhciBTdGF0dXNDb2x1bW4gPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICBzdGF0aWNzOiB7XHJcbiAgICAgICAgcmVuZGVyVGl0bGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAgICAgcmV0dXJuIDx0aCBrZXk9XCJzdGF0dXNcIiBjbGFzc05hbWU9XCJjb2wtc3RhdHVzXCI+U3RhdHVzPC90aD47XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xyXG4gICAgICAgIHZhciBzdGF0dXM7XHJcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UpIHtcclxuICAgICAgICAgICAgc3RhdHVzID0gZmxvdy5yZXNwb25zZS5jb2RlO1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIHN0YXR1cyA9IG51bGw7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHJldHVybiA8dGQgY2xhc3NOYW1lPVwiY29sLXN0YXR1c1wiPntzdGF0dXN9PC90ZD47XHJcbiAgICB9XHJcbn0pO1xyXG5cclxuXHJcbnZhciBTaXplQ29sdW1uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgc3RhdGljczoge1xyXG4gICAgICAgIHJlbmRlclRpdGxlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgICAgIHJldHVybiA8dGgga2V5PVwic2l6ZVwiIGNsYXNzTmFtZT1cImNvbC1zaXplXCI+U2l6ZTwvdGg+O1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcclxuXHJcbiAgICAgICAgdmFyIHRvdGFsID0gZmxvdy5yZXF1ZXN0LmNvbnRlbnRMZW5ndGg7XHJcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UpIHtcclxuICAgICAgICAgICAgdG90YWwgKz0gZmxvdy5yZXNwb25zZS5jb250ZW50TGVuZ3RoIHx8IDA7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHZhciBzaXplID0gdXRpbHMuZm9ybWF0U2l6ZSh0b3RhbCk7XHJcbiAgICAgICAgcmV0dXJuIDx0ZCBjbGFzc05hbWU9XCJjb2wtc2l6ZVwiPntzaXplfTwvdGQ+O1xyXG4gICAgfVxyXG59KTtcclxuXHJcblxyXG52YXIgVGltZUNvbHVtbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHN0YXRpY3M6IHtcclxuICAgICAgICByZW5kZXJUaXRsZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgICAgICByZXR1cm4gPHRoIGtleT1cInRpbWVcIiBjbGFzc05hbWU9XCJjb2wtdGltZVwiPlRpbWU8L3RoPjtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XHJcbiAgICAgICAgdmFyIHRpbWU7XHJcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UpIHtcclxuICAgICAgICAgICAgdGltZSA9IHV0aWxzLmZvcm1hdFRpbWVEZWx0YSgxMDAwICogKGZsb3cucmVzcG9uc2UudGltZXN0YW1wX2VuZCAtIGZsb3cucmVxdWVzdC50aW1lc3RhbXBfc3RhcnQpKTtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICB0aW1lID0gXCIuLi5cIjtcclxuICAgICAgICB9XHJcbiAgICAgICAgcmV0dXJuIDx0ZCBjbGFzc05hbWU9XCJjb2wtdGltZVwiPnt0aW1lfTwvdGQ+O1xyXG4gICAgfVxyXG59KTtcclxuXHJcblxyXG52YXIgYWxsX2NvbHVtbnMgPSBbXHJcbiAgICBUTFNDb2x1bW4sXHJcbiAgICBJY29uQ29sdW1uLFxyXG4gICAgUGF0aENvbHVtbixcclxuICAgIE1ldGhvZENvbHVtbixcclxuICAgIFN0YXR1c0NvbHVtbixcclxuICAgIFNpemVDb2x1bW4sXHJcbiAgICBUaW1lQ29sdW1uXTtcclxuXHJcblxyXG5tb2R1bGUuZXhwb3J0cyA9IGFsbF9jb2x1bW5zO1xyXG5cclxuXHJcbiIsInZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcclxudmFyIGNvbW1vbiA9IHJlcXVpcmUoXCIuL2NvbW1vbi5qc1wiKTtcclxudmFyIFZpcnR1YWxTY3JvbGxNaXhpbiA9IHJlcXVpcmUoXCIuL3ZpcnR1YWxzY3JvbGwuanNcIik7XHJcbnZhciBmbG93dGFibGVfY29sdW1ucyA9IHJlcXVpcmUoXCIuL2Zsb3d0YWJsZS1jb2x1bW5zLmpzXCIpO1xyXG5cclxudmFyIEZsb3dSb3cgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcclxuICAgICAgICB2YXIgY29sdW1ucyA9IHRoaXMucHJvcHMuY29sdW1ucy5tYXAoZnVuY3Rpb24gKENvbHVtbikge1xyXG4gICAgICAgICAgICByZXR1cm4gPENvbHVtbiBrZXk9e0NvbHVtbi5kaXNwbGF5TmFtZX0gZmxvdz17Zmxvd30vPjtcclxuICAgICAgICB9LmJpbmQodGhpcykpO1xyXG4gICAgICAgIHZhciBjbGFzc05hbWUgPSBcIlwiO1xyXG4gICAgICAgIGlmICh0aGlzLnByb3BzLnNlbGVjdGVkKSB7XHJcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcIiBzZWxlY3RlZFwiO1xyXG4gICAgICAgIH1cclxuICAgICAgICBpZiAodGhpcy5wcm9wcy5oaWdobGlnaHRlZCkge1xyXG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCIgaGlnaGxpZ2h0ZWRcIjtcclxuICAgICAgICB9XHJcbiAgICAgICAgaWYgKGZsb3cuaW50ZXJjZXB0ZWQpIHtcclxuICAgICAgICAgICAgY2xhc3NOYW1lICs9IFwiIGludGVyY2VwdGVkXCI7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIGlmIChmbG93LnJlcXVlc3QpIHtcclxuICAgICAgICAgICAgY2xhc3NOYW1lICs9IFwiIGhhcy1yZXF1ZXN0XCI7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIGlmIChmbG93LnJlc3BvbnNlKSB7XHJcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcIiBoYXMtcmVzcG9uc2VcIjtcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDx0ciBjbGFzc05hbWU9e2NsYXNzTmFtZX0gb25DbGljaz17dGhpcy5wcm9wcy5zZWxlY3RGbG93LmJpbmQobnVsbCwgZmxvdyl9PlxyXG4gICAgICAgICAgICAgICAge2NvbHVtbnN9XHJcbiAgICAgICAgICAgIDwvdHI+KTtcclxuICAgIH0sXHJcbiAgICBzaG91bGRDb21wb25lbnRVcGRhdGU6IGZ1bmN0aW9uIChuZXh0UHJvcHMpIHtcclxuICAgICAgICByZXR1cm4gdHJ1ZTtcclxuICAgICAgICAvLyBGdXJ0aGVyIG9wdGltaXphdGlvbiBjb3VsZCBiZSBkb25lIGhlcmVcclxuICAgICAgICAvLyBieSBjYWxsaW5nIGZvcmNlVXBkYXRlIG9uIGZsb3cgdXBkYXRlcywgc2VsZWN0aW9uIGNoYW5nZXMgYW5kIGNvbHVtbiBjaGFuZ2VzLlxyXG4gICAgICAgIC8vcmV0dXJuIChcclxuICAgICAgICAvLyh0aGlzLnByb3BzLmNvbHVtbnMubGVuZ3RoICE9PSBuZXh0UHJvcHMuY29sdW1ucy5sZW5ndGgpIHx8XHJcbiAgICAgICAgLy8odGhpcy5wcm9wcy5zZWxlY3RlZCAhPT0gbmV4dFByb3BzLnNlbGVjdGVkKVxyXG4gICAgICAgIC8vKTtcclxuICAgIH1cclxufSk7XHJcblxyXG52YXIgRmxvd1RhYmxlSGVhZCA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBjb2x1bW5zID0gdGhpcy5wcm9wcy5jb2x1bW5zLm1hcChmdW5jdGlvbiAoY29sdW1uKSB7XHJcbiAgICAgICAgICAgIHJldHVybiBjb2x1bW4ucmVuZGVyVGl0bGUoKTtcclxuICAgICAgICB9LmJpbmQodGhpcykpO1xyXG4gICAgICAgIHJldHVybiA8dGhlYWQ+XHJcbiAgICAgICAgICAgIDx0cj57Y29sdW1uc308L3RyPlxyXG4gICAgICAgIDwvdGhlYWQ+O1xyXG4gICAgfVxyXG59KTtcclxuXHJcblxyXG52YXIgUk9XX0hFSUdIVCA9IDMyO1xyXG5cclxudmFyIEZsb3dUYWJsZSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIG1peGluczogW2NvbW1vbi5TdGlja3lIZWFkTWl4aW4sIGNvbW1vbi5BdXRvU2Nyb2xsTWl4aW4sIFZpcnR1YWxTY3JvbGxNaXhpbl0sXHJcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICByZXR1cm4ge1xyXG4gICAgICAgICAgICBjb2x1bW5zOiBmbG93dGFibGVfY29sdW1uc1xyXG4gICAgICAgIH07XHJcbiAgICB9LFxyXG4gICAgY29tcG9uZW50V2lsbE1vdW50OiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgaWYgKHRoaXMucHJvcHMudmlldykge1xyXG4gICAgICAgICAgICB0aGlzLnByb3BzLnZpZXcuYWRkTGlzdGVuZXIoXCJhZGQgdXBkYXRlIHJlbW92ZSByZWNhbGN1bGF0ZVwiLCB0aGlzLm9uQ2hhbmdlKTtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgY29tcG9uZW50V2lsbFJlY2VpdmVQcm9wczogZnVuY3Rpb24gKG5leHRQcm9wcykge1xyXG4gICAgICAgIGlmIChuZXh0UHJvcHMudmlldyAhPT0gdGhpcy5wcm9wcy52aWV3KSB7XHJcbiAgICAgICAgICAgIGlmICh0aGlzLnByb3BzLnZpZXcpIHtcclxuICAgICAgICAgICAgICAgIHRoaXMucHJvcHMudmlldy5yZW1vdmVMaXN0ZW5lcihcImFkZCB1cGRhdGUgcmVtb3ZlIHJlY2FsY3VsYXRlXCIpO1xyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgICAgIG5leHRQcm9wcy52aWV3LmFkZExpc3RlbmVyKFwiYWRkIHVwZGF0ZSByZW1vdmUgcmVjYWxjdWxhdGVcIiwgdGhpcy5vbkNoYW5nZSk7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIGdldERlZmF1bHRQcm9wczogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHJldHVybiB7XHJcbiAgICAgICAgICAgIHJvd0hlaWdodDogUk9XX0hFSUdIVFxyXG4gICAgICAgIH07XHJcbiAgICB9LFxyXG4gICAgb25TY3JvbGxGbG93VGFibGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLmFkanVzdEhlYWQoKTtcclxuICAgICAgICB0aGlzLm9uU2Nyb2xsKCk7XHJcbiAgICB9LFxyXG4gICAgb25DaGFuZ2U6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLmZvcmNlVXBkYXRlKCk7XHJcbiAgICB9LFxyXG4gICAgc2Nyb2xsSW50b1ZpZXc6IGZ1bmN0aW9uIChmbG93KSB7XHJcbiAgICAgICAgdGhpcy5zY3JvbGxSb3dJbnRvVmlldyhcclxuICAgICAgICAgICAgdGhpcy5wcm9wcy52aWV3LmluZGV4KGZsb3cpLFxyXG4gICAgICAgICAgICB0aGlzLnJlZnMuYm9keS5nZXRET01Ob2RlKCkub2Zmc2V0VG9wXHJcbiAgICAgICAgKTtcclxuICAgIH0sXHJcbiAgICByZW5kZXJSb3c6IGZ1bmN0aW9uIChmbG93KSB7XHJcbiAgICAgICAgdmFyIHNlbGVjdGVkID0gKGZsb3cgPT09IHRoaXMucHJvcHMuc2VsZWN0ZWQpO1xyXG4gICAgICAgIHZhciBoaWdobGlnaHRlZCA9XHJcbiAgICAgICAgICAgIChcclxuICAgICAgICAgICAgdGhpcy5wcm9wcy52aWV3Ll9oaWdobGlnaHQgJiZcclxuICAgICAgICAgICAgdGhpcy5wcm9wcy52aWV3Ll9oaWdobGlnaHRbZmxvdy5pZF1cclxuICAgICAgICAgICAgKTtcclxuXHJcbiAgICAgICAgcmV0dXJuIDxGbG93Um93IGtleT17Zmxvdy5pZH1cclxuICAgICAgICAgICAgcmVmPXtmbG93LmlkfVxyXG4gICAgICAgICAgICBmbG93PXtmbG93fVxyXG4gICAgICAgICAgICBjb2x1bW5zPXt0aGlzLnN0YXRlLmNvbHVtbnN9XHJcbiAgICAgICAgICAgIHNlbGVjdGVkPXtzZWxlY3RlZH1cclxuICAgICAgICAgICAgaGlnaGxpZ2h0ZWQ9e2hpZ2hsaWdodGVkfVxyXG4gICAgICAgICAgICBzZWxlY3RGbG93PXt0aGlzLnByb3BzLnNlbGVjdEZsb3d9XHJcbiAgICAgICAgLz47XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgLy9jb25zb2xlLmxvZyhcInJlbmRlciBmbG93dGFibGVcIiwgdGhpcy5zdGF0ZS5zdGFydCwgdGhpcy5zdGF0ZS5zdG9wLCB0aGlzLnByb3BzLnNlbGVjdGVkKTtcclxuICAgICAgICB2YXIgZmxvd3MgPSB0aGlzLnByb3BzLnZpZXcgPyB0aGlzLnByb3BzLnZpZXcubGlzdCA6IFtdO1xyXG5cclxuICAgICAgICB2YXIgcm93cyA9IHRoaXMucmVuZGVyUm93cyhmbG93cyk7XHJcblxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPVwiZmxvdy10YWJsZVwiIG9uU2Nyb2xsPXt0aGlzLm9uU2Nyb2xsRmxvd1RhYmxlfT5cclxuICAgICAgICAgICAgICAgIDx0YWJsZT5cclxuICAgICAgICAgICAgICAgICAgICA8Rmxvd1RhYmxlSGVhZCByZWY9XCJoZWFkXCJcclxuICAgICAgICAgICAgICAgICAgICAgICAgY29sdW1ucz17dGhpcy5zdGF0ZS5jb2x1bW5zfS8+XHJcbiAgICAgICAgICAgICAgICAgICAgPHRib2R5IHJlZj1cImJvZHlcIj5cclxuICAgICAgICAgICAgICAgICAgICAgICAgeyB0aGlzLmdldFBsYWNlaG9sZGVyVG9wKGZsb3dzLmxlbmd0aCkgfVxyXG4gICAgICAgICAgICAgICAgICAgICAgICB7cm93c31cclxuICAgICAgICAgICAgICAgICAgICAgICAgeyB0aGlzLmdldFBsYWNlaG9sZGVyQm90dG9tKGZsb3dzLmxlbmd0aCkgfVxyXG4gICAgICAgICAgICAgICAgICAgIDwvdGJvZHk+XHJcbiAgICAgICAgICAgICAgICA8L3RhYmxlPlxyXG4gICAgICAgICAgICA8L2Rpdj5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbm1vZHVsZS5leHBvcnRzID0gRmxvd1RhYmxlO1xyXG4iLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XHJcblxyXG52YXIgRm9vdGVyID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIG1vZGUgPSB0aGlzLnByb3BzLnNldHRpbmdzLm1vZGU7XHJcbiAgICAgICAgdmFyIGludGVyY2VwdCA9IHRoaXMucHJvcHMuc2V0dGluZ3MuaW50ZXJjZXB0O1xyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxmb290ZXI+XHJcbiAgICAgICAgICAgICAgICB7bW9kZSAhPSBcInJlZ3VsYXJcIiA/IDxzcGFuIGNsYXNzTmFtZT1cImxhYmVsIGxhYmVsLXN1Y2Nlc3NcIj57bW9kZX0gbW9kZTwvc3Bhbj4gOiBudWxsfVxyXG4gICAgICAgICAgICAgICAgJm5ic3A7XHJcbiAgICAgICAgICAgICAgICB7aW50ZXJjZXB0ID8gPHNwYW4gY2xhc3NOYW1lPVwibGFiZWwgbGFiZWwtc3VjY2Vzc1wiPkludGVyY2VwdDoge2ludGVyY2VwdH08L3NwYW4+IDogbnVsbH1cclxuICAgICAgICAgICAgPC9mb290ZXI+XHJcbiAgICAgICAgKTtcclxuICAgIH1cclxufSk7XHJcblxyXG5tb2R1bGUuZXhwb3J0cyA9IEZvb3RlcjsiLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XHJcbnZhciAkID0gcmVxdWlyZShcImpxdWVyeVwiKTtcclxuXHJcbnZhciBGaWx0ID0gcmVxdWlyZShcIi4uL2ZpbHQvZmlsdC5qc1wiKTtcclxudmFyIHV0aWxzID0gcmVxdWlyZShcIi4uL3V0aWxzLmpzXCIpO1xyXG5cclxudmFyIGNvbW1vbiA9IHJlcXVpcmUoXCIuL2NvbW1vbi5qc1wiKTtcclxudmFyIGFjdGlvbnMgPSByZXF1aXJlKFwiLi4vYWN0aW9ucy5qc1wiKTtcclxuXHJcbnZhciBGaWx0ZXJEb2NzID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgc3RhdGljczoge1xyXG4gICAgICAgIHhocjogZmFsc2UsXHJcbiAgICAgICAgZG9jOiBmYWxzZVxyXG4gICAgfSxcclxuICAgIGNvbXBvbmVudFdpbGxNb3VudDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIGlmICghRmlsdGVyRG9jcy5kb2MpIHtcclxuICAgICAgICAgICAgRmlsdGVyRG9jcy54aHIgPSAkLmdldEpTT04oXCIvZmlsdGVyLWhlbHBcIikuZG9uZShmdW5jdGlvbiAoZG9jKSB7XHJcbiAgICAgICAgICAgICAgICBGaWx0ZXJEb2NzLmRvYyA9IGRvYztcclxuICAgICAgICAgICAgICAgIEZpbHRlckRvY3MueGhyID0gZmFsc2U7XHJcbiAgICAgICAgICAgIH0pO1xyXG4gICAgICAgIH1cclxuICAgICAgICBpZiAoRmlsdGVyRG9jcy54aHIpIHtcclxuICAgICAgICAgICAgRmlsdGVyRG9jcy54aHIuZG9uZShmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgICAgICAgICB0aGlzLmZvcmNlVXBkYXRlKCk7XHJcbiAgICAgICAgICAgIH0uYmluZCh0aGlzKSk7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIGlmICghRmlsdGVyRG9jcy5kb2MpIHtcclxuICAgICAgICAgICAgcmV0dXJuIDxpIGNsYXNzTmFtZT1cImZhIGZhLXNwaW5uZXIgZmEtc3BpblwiPjwvaT47XHJcbiAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgdmFyIGNvbW1hbmRzID0gRmlsdGVyRG9jcy5kb2MuY29tbWFuZHMubWFwKGZ1bmN0aW9uIChjKSB7XHJcbiAgICAgICAgICAgICAgICByZXR1cm4gPHRyPlxyXG4gICAgICAgICAgICAgICAgICAgIDx0ZD57Y1swXS5yZXBsYWNlKFwiIFwiLCAnXFx1MDBhMCcpfTwvdGQ+XHJcbiAgICAgICAgICAgICAgICAgICAgPHRkPntjWzFdfTwvdGQ+XHJcbiAgICAgICAgICAgICAgICA8L3RyPjtcclxuICAgICAgICAgICAgfSk7XHJcbiAgICAgICAgICAgIGNvbW1hbmRzLnB1c2goPHRyPlxyXG4gICAgICAgICAgICAgICAgPHRkIGNvbFNwYW49XCIyXCI+XHJcbiAgICAgICAgICAgICAgICAgICAgPGEgaHJlZj1cImh0dHBzOi8vbWl0bXByb3h5Lm9yZy9kb2MvZmVhdHVyZXMvZmlsdGVycy5odG1sXCJcclxuICAgICAgICAgICAgICAgICAgICAgICAgdGFyZ2V0PVwiX2JsYW5rXCI+XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIDxpIGNsYXNzTmFtZT1cImZhIGZhLWV4dGVybmFsLWxpbmtcIj48L2k+XHJcbiAgICAgICAgICAgICAgICAgICAgJm5ic3A7IG1pdG1wcm94eSBkb2NzPC9hPlxyXG4gICAgICAgICAgICAgICAgPC90ZD5cclxuICAgICAgICAgICAgPC90cj4pO1xyXG4gICAgICAgICAgICByZXR1cm4gPHRhYmxlIGNsYXNzTmFtZT1cInRhYmxlIHRhYmxlLWNvbmRlbnNlZFwiPlxyXG4gICAgICAgICAgICAgICAgPHRib2R5Pntjb21tYW5kc308L3Rib2R5PlxyXG4gICAgICAgICAgICA8L3RhYmxlPjtcclxuICAgICAgICB9XHJcbiAgICB9XHJcbn0pO1xyXG52YXIgRmlsdGVySW5wdXQgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAvLyBDb25zaWRlciBib3RoIGZvY3VzIGFuZCBtb3VzZW92ZXIgZm9yIHNob3dpbmcvaGlkaW5nIHRoZSB0b29sdGlwLFxyXG4gICAgICAgIC8vIGJlY2F1c2Ugb25CbHVyIG9mIHRoZSBpbnB1dCBpcyB0cmlnZ2VyZWQgYmVmb3JlIHRoZSBjbGljayBvbiB0aGUgdG9vbHRpcFxyXG4gICAgICAgIC8vIGZpbmFsaXplZCwgaGlkaW5nIHRoZSB0b29sdGlwIGp1c3QgYXMgdGhlIHVzZXIgY2xpY2tzIG9uIGl0LlxyXG4gICAgICAgIHJldHVybiB7XHJcbiAgICAgICAgICAgIHZhbHVlOiB0aGlzLnByb3BzLnZhbHVlLFxyXG4gICAgICAgICAgICBmb2N1czogZmFsc2UsXHJcbiAgICAgICAgICAgIG1vdXNlZm9jdXM6IGZhbHNlXHJcbiAgICAgICAgfTtcclxuICAgIH0sXHJcbiAgICBjb21wb25lbnRXaWxsUmVjZWl2ZVByb3BzOiBmdW5jdGlvbiAobmV4dFByb3BzKSB7XHJcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7dmFsdWU6IG5leHRQcm9wcy52YWx1ZX0pO1xyXG4gICAgfSxcclxuICAgIG9uQ2hhbmdlOiBmdW5jdGlvbiAoZSkge1xyXG4gICAgICAgIHZhciBuZXh0VmFsdWUgPSBlLnRhcmdldC52YWx1ZTtcclxuICAgICAgICB0aGlzLnNldFN0YXRlKHtcclxuICAgICAgICAgICAgdmFsdWU6IG5leHRWYWx1ZVxyXG4gICAgICAgIH0pO1xyXG4gICAgICAgIC8vIE9ubHkgcHJvcGFnYXRlIHZhbGlkIGZpbHRlcnMgdXB3YXJkcy5cclxuICAgICAgICBpZiAodGhpcy5pc1ZhbGlkKG5leHRWYWx1ZSkpIHtcclxuICAgICAgICAgICAgdGhpcy5wcm9wcy5vbkNoYW5nZShuZXh0VmFsdWUpO1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICBpc1ZhbGlkOiBmdW5jdGlvbiAoZmlsdCkge1xyXG4gICAgICAgIHRyeSB7XHJcbiAgICAgICAgICAgIEZpbHQucGFyc2UoZmlsdCB8fCB0aGlzLnN0YXRlLnZhbHVlKTtcclxuICAgICAgICAgICAgcmV0dXJuIHRydWU7XHJcbiAgICAgICAgfSBjYXRjaCAoZSkge1xyXG4gICAgICAgICAgICByZXR1cm4gZmFsc2U7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIGdldERlc2M6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB2YXIgZGVzYztcclxuICAgICAgICB0cnkge1xyXG4gICAgICAgICAgICBkZXNjID0gRmlsdC5wYXJzZSh0aGlzLnN0YXRlLnZhbHVlKS5kZXNjO1xyXG4gICAgICAgIH0gY2F0Y2ggKGUpIHtcclxuICAgICAgICAgICAgZGVzYyA9IFwiXCIgKyBlO1xyXG4gICAgICAgIH1cclxuICAgICAgICBpZiAoZGVzYyAhPT0gXCJ0cnVlXCIpIHtcclxuICAgICAgICAgICAgcmV0dXJuIGRlc2M7XHJcbiAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgICAgIDxGaWx0ZXJEb2NzLz5cclxuICAgICAgICAgICAgKTtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgb25Gb2N1czogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe2ZvY3VzOiB0cnVlfSk7XHJcbiAgICB9LFxyXG4gICAgb25CbHVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7Zm9jdXM6IGZhbHNlfSk7XHJcbiAgICB9LFxyXG4gICAgb25Nb3VzZUVudGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7bW91c2Vmb2N1czogdHJ1ZX0pO1xyXG4gICAgfSxcclxuICAgIG9uTW91c2VMZWF2ZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe21vdXNlZm9jdXM6IGZhbHNlfSk7XHJcbiAgICB9LFxyXG4gICAgb25LZXlEb3duOiBmdW5jdGlvbiAoZSkge1xyXG4gICAgICAgIGlmIChlLmtleUNvZGUgPT09IHV0aWxzLktleS5FU0MgfHwgZS5rZXlDb2RlID09PSB1dGlscy5LZXkuRU5URVIpIHtcclxuICAgICAgICAgICAgdGhpcy5ibHVyKCk7XHJcbiAgICAgICAgICAgIC8vIElmIGNsb3NlZCB1c2luZyBFU0MvRU5URVIsIGhpZGUgdGhlIHRvb2x0aXAuXHJcbiAgICAgICAgICAgIHRoaXMuc2V0U3RhdGUoe21vdXNlZm9jdXM6IGZhbHNlfSk7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIGJsdXI6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLnJlZnMuaW5wdXQuZ2V0RE9NTm9kZSgpLmJsdXIoKTtcclxuICAgIH0sXHJcbiAgICBmb2N1czogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMucmVmcy5pbnB1dC5nZXRET01Ob2RlKCkuc2VsZWN0KCk7XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGlzVmFsaWQgPSB0aGlzLmlzVmFsaWQoKTtcclxuICAgICAgICB2YXIgaWNvbiA9IFwiZmEgZmEtZncgZmEtXCIgKyB0aGlzLnByb3BzLnR5cGU7XHJcbiAgICAgICAgdmFyIGdyb3VwQ2xhc3NOYW1lID0gXCJmaWx0ZXItaW5wdXQgaW5wdXQtZ3JvdXBcIiArIChpc1ZhbGlkID8gXCJcIiA6IFwiIGhhcy1lcnJvclwiKTtcclxuXHJcbiAgICAgICAgdmFyIHBvcG92ZXI7XHJcbiAgICAgICAgaWYgKHRoaXMuc3RhdGUuZm9jdXMgfHwgdGhpcy5zdGF0ZS5tb3VzZWZvY3VzKSB7XHJcbiAgICAgICAgICAgIHBvcG92ZXIgPSAoXHJcbiAgICAgICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cInBvcG92ZXIgYm90dG9tXCIgb25Nb3VzZUVudGVyPXt0aGlzLm9uTW91c2VFbnRlcn0gb25Nb3VzZUxlYXZlPXt0aGlzLm9uTW91c2VMZWF2ZX0+XHJcbiAgICAgICAgICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJhcnJvd1wiPjwvZGl2PlxyXG4gICAgICAgICAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPVwicG9wb3Zlci1jb250ZW50XCI+XHJcbiAgICAgICAgICAgICAgICAgICAge3RoaXMuZ2V0RGVzYygpfVxyXG4gICAgICAgICAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICAgICAgICAgPC9kaXY+XHJcbiAgICAgICAgICAgICk7XHJcbiAgICAgICAgfVxyXG5cclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT17Z3JvdXBDbGFzc05hbWV9PlxyXG4gICAgICAgICAgICAgICAgPHNwYW4gY2xhc3NOYW1lPVwiaW5wdXQtZ3JvdXAtYWRkb25cIj5cclxuICAgICAgICAgICAgICAgICAgICA8aSBjbGFzc05hbWU9e2ljb259IHN0eWxlPXt7Y29sb3I6IHRoaXMucHJvcHMuY29sb3J9fT48L2k+XHJcbiAgICAgICAgICAgICAgICA8L3NwYW4+XHJcbiAgICAgICAgICAgICAgICA8aW5wdXQgdHlwZT1cInRleHRcIiBwbGFjZWhvbGRlcj17dGhpcy5wcm9wcy5wbGFjZWhvbGRlcn0gY2xhc3NOYW1lPVwiZm9ybS1jb250cm9sXCJcclxuICAgICAgICAgICAgICAgICAgICByZWY9XCJpbnB1dFwiXHJcbiAgICAgICAgICAgICAgICAgICAgb25DaGFuZ2U9e3RoaXMub25DaGFuZ2V9XHJcbiAgICAgICAgICAgICAgICAgICAgb25Gb2N1cz17dGhpcy5vbkZvY3VzfVxyXG4gICAgICAgICAgICAgICAgICAgIG9uQmx1cj17dGhpcy5vbkJsdXJ9XHJcbiAgICAgICAgICAgICAgICAgICAgb25LZXlEb3duPXt0aGlzLm9uS2V5RG93bn1cclxuICAgICAgICAgICAgICAgICAgICB2YWx1ZT17dGhpcy5zdGF0ZS52YWx1ZX0vPlxyXG4gICAgICAgICAgICAgICAge3BvcG92ZXJ9XHJcbiAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxudmFyIE1haW5NZW51ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgbWl4aW5zOiBbY29tbW9uLk5hdmlnYXRpb24sIGNvbW1vbi5TdGF0ZV0sXHJcbiAgICBzdGF0aWNzOiB7XHJcbiAgICAgICAgdGl0bGU6IFwiU3RhcnRcIixcclxuICAgICAgICByb3V0ZTogXCJmbG93c1wiXHJcbiAgICB9LFxyXG4gICAgb25GaWx0ZXJDaGFuZ2U6IGZ1bmN0aW9uICh2YWwpIHtcclxuICAgICAgICB2YXIgZCA9IHt9O1xyXG4gICAgICAgIGRbUXVlcnkuRklMVEVSXSA9IHZhbDtcclxuICAgICAgICB0aGlzLnNldFF1ZXJ5KGQpO1xyXG4gICAgfSxcclxuICAgIG9uSGlnaGxpZ2h0Q2hhbmdlOiBmdW5jdGlvbiAodmFsKSB7XHJcbiAgICAgICAgdmFyIGQgPSB7fTtcclxuICAgICAgICBkW1F1ZXJ5LkhJR0hMSUdIVF0gPSB2YWw7XHJcbiAgICAgICAgdGhpcy5zZXRRdWVyeShkKTtcclxuICAgIH0sXHJcbiAgICBvbkludGVyY2VwdENoYW5nZTogZnVuY3Rpb24gKHZhbCkge1xyXG4gICAgICAgIFNldHRpbmdzQWN0aW9ucy51cGRhdGUoe2ludGVyY2VwdDogdmFsfSk7XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGZpbHRlciA9IHRoaXMuZ2V0UXVlcnkoKVtRdWVyeS5GSUxURVJdIHx8IFwiXCI7XHJcbiAgICAgICAgdmFyIGhpZ2hsaWdodCA9IHRoaXMuZ2V0UXVlcnkoKVtRdWVyeS5ISUdITElHSFRdIHx8IFwiXCI7XHJcbiAgICAgICAgdmFyIGludGVyY2VwdCA9IHRoaXMucHJvcHMuc2V0dGluZ3MuaW50ZXJjZXB0IHx8IFwiXCI7XHJcblxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxkaXY+XHJcbiAgICAgICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cIm1lbnUtcm93XCI+XHJcbiAgICAgICAgICAgICAgICAgICAgPEZpbHRlcklucHV0XHJcbiAgICAgICAgICAgICAgICAgICAgICAgIHBsYWNlaG9sZGVyPVwiRmlsdGVyXCJcclxuICAgICAgICAgICAgICAgICAgICAgICAgdHlwZT1cImZpbHRlclwiXHJcbiAgICAgICAgICAgICAgICAgICAgICAgIGNvbG9yPVwiYmxhY2tcIlxyXG4gICAgICAgICAgICAgICAgICAgICAgICB2YWx1ZT17ZmlsdGVyfVxyXG4gICAgICAgICAgICAgICAgICAgICAgICBvbkNoYW5nZT17dGhpcy5vbkZpbHRlckNoYW5nZX0gLz5cclxuICAgICAgICAgICAgICAgICAgICA8RmlsdGVySW5wdXRcclxuICAgICAgICAgICAgICAgICAgICAgICAgcGxhY2Vob2xkZXI9XCJIaWdobGlnaHRcIlxyXG4gICAgICAgICAgICAgICAgICAgICAgICB0eXBlPVwidGFnXCJcclxuICAgICAgICAgICAgICAgICAgICAgICAgY29sb3I9XCJoc2woNDgsIDEwMCUsIDUwJSlcIlxyXG4gICAgICAgICAgICAgICAgICAgICAgICB2YWx1ZT17aGlnaGxpZ2h0fVxyXG4gICAgICAgICAgICAgICAgICAgICAgICBvbkNoYW5nZT17dGhpcy5vbkhpZ2hsaWdodENoYW5nZX0vPlxyXG4gICAgICAgICAgICAgICAgICAgIDxGaWx0ZXJJbnB1dFxyXG4gICAgICAgICAgICAgICAgICAgICAgICBwbGFjZWhvbGRlcj1cIkludGVyY2VwdFwiXHJcbiAgICAgICAgICAgICAgICAgICAgICAgIHR5cGU9XCJwYXVzZVwiXHJcbiAgICAgICAgICAgICAgICAgICAgICAgIGNvbG9yPVwiaHNsKDIwOCwgNTYlLCA1MyUpXCJcclxuICAgICAgICAgICAgICAgICAgICAgICAgdmFsdWU9e2ludGVyY2VwdH1cclxuICAgICAgICAgICAgICAgICAgICAgICAgb25DaGFuZ2U9e3RoaXMub25JbnRlcmNlcHRDaGFuZ2V9Lz5cclxuICAgICAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJjbGVhcmZpeFwiPjwvZGl2PlxyXG4gICAgICAgICAgICA8L2Rpdj5cclxuICAgICAgICApO1xyXG4gICAgfVxyXG59KTtcclxuXHJcblxyXG52YXIgVmlld01lbnUgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICBzdGF0aWNzOiB7XHJcbiAgICAgICAgdGl0bGU6IFwiVmlld1wiLFxyXG4gICAgICAgIHJvdXRlOiBcImZsb3dzXCJcclxuICAgIH0sXHJcbiAgICBtaXhpbnM6IFtjb21tb24uTmF2aWdhdGlvbiwgY29tbW9uLlN0YXRlXSxcclxuICAgIHRvZ2dsZUV2ZW50TG9nOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGQgPSB7fTtcclxuXHJcbiAgICAgICAgaWYgKHRoaXMuZ2V0UXVlcnkoKVtRdWVyeS5TSE9XX0VWRU5UTE9HXSkge1xyXG4gICAgICAgICAgICBkW1F1ZXJ5LlNIT1dfRVZFTlRMT0ddID0gdW5kZWZpbmVkO1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIGRbUXVlcnkuU0hPV19FVkVOVExPR10gPSBcInRcIjsgLy8gYW55IG5vbi1mYWxzZSB2YWx1ZSB3aWxsIGRvIGl0LCBrZWVwIGl0IHNob3J0XHJcbiAgICAgICAgfVxyXG5cclxuICAgICAgICB0aGlzLnNldFF1ZXJ5KGQpO1xyXG4gICAgfSxcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBzaG93RXZlbnRMb2cgPSB0aGlzLmdldFF1ZXJ5KClbUXVlcnkuU0hPV19FVkVOVExPR107XHJcbiAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgPGRpdj5cclxuICAgICAgICAgICAgICAgIDxidXR0b25cclxuICAgICAgICAgICAgICAgICAgICBjbGFzc05hbWU9e1wiYnRuIFwiICsgKHNob3dFdmVudExvZyA/IFwiYnRuLXByaW1hcnlcIiA6IFwiYnRuLWRlZmF1bHRcIil9XHJcbiAgICAgICAgICAgICAgICAgICAgb25DbGljaz17dGhpcy50b2dnbGVFdmVudExvZ30+XHJcbiAgICAgICAgICAgICAgICAgICAgPGkgY2xhc3NOYW1lPVwiZmEgZmEtZGF0YWJhc2VcIj48L2k+XHJcbiAgICAgICAgICAgICAgICAmbmJzcDtTaG93IEV2ZW50bG9nXHJcbiAgICAgICAgICAgICAgICA8L2J1dHRvbj5cclxuICAgICAgICAgICAgICAgIDxzcGFuPiA8L3NwYW4+XHJcbiAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxuXHJcbnZhciBSZXBvcnRzTWVudSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIHN0YXRpY3M6IHtcclxuICAgICAgICB0aXRsZTogXCJWaXN1YWxpemF0aW9uXCIsXHJcbiAgICAgICAgcm91dGU6IFwicmVwb3J0c1wiXHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgcmV0dXJuIDxkaXY+UmVwb3J0cyBNZW51PC9kaXY+O1xyXG4gICAgfVxyXG59KTtcclxuXHJcbnZhciBGaWxlTWVudSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtcclxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHJldHVybiB7XHJcbiAgICAgICAgICAgIHNob3dGaWxlTWVudTogZmFsc2VcclxuICAgICAgICB9O1xyXG4gICAgfSxcclxuICAgIGhhbmRsZUZpbGVDbGljazogZnVuY3Rpb24gKGUpIHtcclxuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XHJcbiAgICAgICAgaWYgKCF0aGlzLnN0YXRlLnNob3dGaWxlTWVudSkge1xyXG4gICAgICAgICAgICB2YXIgY2xvc2UgPSBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgICAgICAgICB0aGlzLnNldFN0YXRlKHtzaG93RmlsZU1lbnU6IGZhbHNlfSk7XHJcbiAgICAgICAgICAgICAgICBkb2N1bWVudC5yZW1vdmVFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgY2xvc2UpO1xyXG4gICAgICAgICAgICB9LmJpbmQodGhpcyk7XHJcbiAgICAgICAgICAgIGRvY3VtZW50LmFkZEV2ZW50TGlzdGVuZXIoXCJjbGlja1wiLCBjbG9zZSk7XHJcblxyXG4gICAgICAgICAgICB0aGlzLnNldFN0YXRlKHtcclxuICAgICAgICAgICAgICAgIHNob3dGaWxlTWVudTogdHJ1ZVxyXG4gICAgICAgICAgICB9KTtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgaGFuZGxlTmV3Q2xpY2s6IGZ1bmN0aW9uIChlKSB7XHJcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xyXG4gICAgICAgIGlmIChjb25maXJtKFwiRGVsZXRlIGFsbCBmbG93cz9cIikpIHtcclxuICAgICAgICAgICAgYWN0aW9ucy5GbG93QWN0aW9ucy5jbGVhcigpO1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICBoYW5kbGVPcGVuQ2xpY2s6IGZ1bmN0aW9uIChlKSB7XHJcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xyXG4gICAgICAgIGNvbnNvbGUuZXJyb3IoXCJ1bmltcGxlbWVudGVkOiBoYW5kbGVPcGVuQ2xpY2tcIik7XHJcbiAgICB9LFxyXG4gICAgaGFuZGxlU2F2ZUNsaWNrOiBmdW5jdGlvbiAoZSkge1xyXG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcclxuICAgICAgICBjb25zb2xlLmVycm9yKFwidW5pbXBsZW1lbnRlZDogaGFuZGxlU2F2ZUNsaWNrXCIpO1xyXG4gICAgfSxcclxuICAgIGhhbmRsZVNodXRkb3duQ2xpY2s6IGZ1bmN0aW9uIChlKSB7XHJcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xyXG4gICAgICAgIGNvbnNvbGUuZXJyb3IoXCJ1bmltcGxlbWVudGVkOiBoYW5kbGVTaHV0ZG93bkNsaWNrXCIpO1xyXG4gICAgfSxcclxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBmaWxlTWVudUNsYXNzID0gXCJkcm9wZG93biBwdWxsLWxlZnRcIiArICh0aGlzLnN0YXRlLnNob3dGaWxlTWVudSA/IFwiIG9wZW5cIiA6IFwiXCIpO1xyXG5cclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT17ZmlsZU1lbnVDbGFzc30+XHJcbiAgICAgICAgICAgICAgICA8YSBocmVmPVwiI1wiIGNsYXNzTmFtZT1cInNwZWNpYWxcIiBvbkNsaWNrPXt0aGlzLmhhbmRsZUZpbGVDbGlja30+IG1pdG1wcm94eSA8L2E+XHJcbiAgICAgICAgICAgICAgICA8dWwgY2xhc3NOYW1lPVwiZHJvcGRvd24tbWVudVwiIHJvbGU9XCJtZW51XCI+XHJcbiAgICAgICAgICAgICAgICAgICAgPGxpPlxyXG4gICAgICAgICAgICAgICAgICAgICAgICA8YSBocmVmPVwiI1wiIG9uQ2xpY2s9e3RoaXMuaGFuZGxlTmV3Q2xpY2t9PlxyXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgPGkgY2xhc3NOYW1lPVwiZmEgZmEtZncgZmEtZmlsZVwiPjwvaT5cclxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIE5ld1xyXG4gICAgICAgICAgICAgICAgICAgICAgICA8L2E+XHJcbiAgICAgICAgICAgICAgICAgICAgPC9saT5cclxuICAgICAgICAgICAgICAgICAgICA8bGkgcm9sZT1cInByZXNlbnRhdGlvblwiIGNsYXNzTmFtZT1cImRpdmlkZXJcIj48L2xpPlxyXG4gICAgICAgICAgICAgICAgICAgIDxsaT5cclxuICAgICAgICAgICAgICAgICAgICAgICAgPGEgaHJlZj1cImh0dHA6Ly9taXRtLml0L1wiIHRhcmdldD1cIl9ibGFua1wiPlxyXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgPGkgY2xhc3NOYW1lPVwiZmEgZmEtZncgZmEtZXh0ZXJuYWwtbGlua1wiPjwvaT5cclxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIEluc3RhbGwgQ2VydGlmaWNhdGVzLi4uXHJcbiAgICAgICAgICAgICAgICAgICAgICAgIDwvYT5cclxuICAgICAgICAgICAgICAgICAgICA8L2xpPlxyXG4gICAgICAgICAgICAgICAgey8qXHJcbiAgICAgICAgICAgICAgICAgPGxpPlxyXG4gICAgICAgICAgICAgICAgIDxhIGhyZWY9XCIjXCIgb25DbGljaz17dGhpcy5oYW5kbGVPcGVuQ2xpY2t9PlxyXG4gICAgICAgICAgICAgICAgIDxpIGNsYXNzTmFtZT1cImZhIGZhLWZ3IGZhLWZvbGRlci1vcGVuXCI+PC9pPlxyXG4gICAgICAgICAgICAgICAgIE9wZW5cclxuICAgICAgICAgICAgICAgICA8L2E+XHJcbiAgICAgICAgICAgICAgICAgPC9saT5cclxuICAgICAgICAgICAgICAgICA8bGk+XHJcbiAgICAgICAgICAgICAgICAgPGEgaHJlZj1cIiNcIiBvbkNsaWNrPXt0aGlzLmhhbmRsZVNhdmVDbGlja30+XHJcbiAgICAgICAgICAgICAgICAgPGkgY2xhc3NOYW1lPVwiZmEgZmEtZncgZmEtc2F2ZVwiPjwvaT5cclxuICAgICAgICAgICAgICAgICBTYXZlXHJcbiAgICAgICAgICAgICAgICAgPC9hPlxyXG4gICAgICAgICAgICAgICAgIDwvbGk+XHJcbiAgICAgICAgICAgICAgICAgPGxpIHJvbGU9XCJwcmVzZW50YXRpb25cIiBjbGFzc05hbWU9XCJkaXZpZGVyXCI+PC9saT5cclxuICAgICAgICAgICAgICAgICA8bGk+XHJcbiAgICAgICAgICAgICAgICAgPGEgaHJlZj1cIiNcIiBvbkNsaWNrPXt0aGlzLmhhbmRsZVNodXRkb3duQ2xpY2t9PlxyXG4gICAgICAgICAgICAgICAgIDxpIGNsYXNzTmFtZT1cImZhIGZhLWZ3IGZhLXBsdWdcIj48L2k+XHJcbiAgICAgICAgICAgICAgICAgU2h1dGRvd25cclxuICAgICAgICAgICAgICAgICA8L2E+XHJcbiAgICAgICAgICAgICAgICAgPC9saT5cclxuICAgICAgICAgICAgICAgICAqL31cclxuICAgICAgICAgICAgICAgIDwvdWw+XHJcbiAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxuXHJcbnZhciBoZWFkZXJfZW50cmllcyA9IFtNYWluTWVudSwgVmlld01lbnUgLyosIFJlcG9ydHNNZW51ICovXTtcclxuXHJcblxyXG52YXIgSGVhZGVyID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgbWl4aW5zOiBbY29tbW9uLk5hdmlnYXRpb25dLFxyXG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgcmV0dXJuIHtcclxuICAgICAgICAgICAgYWN0aXZlOiBoZWFkZXJfZW50cmllc1swXVxyXG4gICAgICAgIH07XHJcbiAgICB9LFxyXG4gICAgaGFuZGxlQ2xpY2s6IGZ1bmN0aW9uIChhY3RpdmUsIGUpIHtcclxuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XHJcbiAgICAgICAgdGhpcy5yZXBsYWNlV2l0aChhY3RpdmUucm91dGUpO1xyXG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe2FjdGl2ZTogYWN0aXZlfSk7XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIGhlYWRlciA9IGhlYWRlcl9lbnRyaWVzLm1hcChmdW5jdGlvbiAoZW50cnksIGkpIHtcclxuICAgICAgICAgICAgdmFyIGNsYXNzZXMgPSBSZWFjdC5hZGRvbnMuY2xhc3NTZXQoe1xyXG4gICAgICAgICAgICAgICAgYWN0aXZlOiBlbnRyeSA9PSB0aGlzLnN0YXRlLmFjdGl2ZVxyXG4gICAgICAgICAgICB9KTtcclxuICAgICAgICAgICAgcmV0dXJuIChcclxuICAgICAgICAgICAgICAgIDxhIGtleT17aX1cclxuICAgICAgICAgICAgICAgICAgICBocmVmPVwiI1wiXHJcbiAgICAgICAgICAgICAgICAgICAgY2xhc3NOYW1lPXtjbGFzc2VzfVxyXG4gICAgICAgICAgICAgICAgICAgIG9uQ2xpY2s9e3RoaXMuaGFuZGxlQ2xpY2suYmluZCh0aGlzLCBlbnRyeSl9XHJcbiAgICAgICAgICAgICAgICA+XHJcbiAgICAgICAgICAgICAgICAgICAgeyBlbnRyeS50aXRsZX1cclxuICAgICAgICAgICAgICAgIDwvYT5cclxuICAgICAgICAgICAgKTtcclxuICAgICAgICB9LmJpbmQodGhpcykpO1xyXG5cclxuICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICA8aGVhZGVyPlxyXG4gICAgICAgICAgICAgICAgPG5hdiBjbGFzc05hbWU9XCJuYXYtdGFicyBuYXYtdGFicy1sZ1wiPlxyXG4gICAgICAgICAgICAgICAgICAgIDxGaWxlTWVudS8+XHJcbiAgICAgICAgICAgICAgICAgICAge2hlYWRlcn1cclxuICAgICAgICAgICAgICAgIDwvbmF2PlxyXG4gICAgICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJtZW51XCI+XHJcbiAgICAgICAgICAgICAgICAgICAgPHRoaXMuc3RhdGUuYWN0aXZlIHNldHRpbmdzPXt0aGlzLnByb3BzLnNldHRpbmdzfS8+XHJcbiAgICAgICAgICAgICAgICA8L2Rpdj5cclxuICAgICAgICAgICAgPC9oZWFkZXI+XHJcbiAgICAgICAgKTtcclxuICAgIH1cclxufSk7XHJcblxyXG5cclxubW9kdWxlLmV4cG9ydHMgPSB7XHJcbiAgICBIZWFkZXI6IEhlYWRlclxyXG59IiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xyXG5cclxudmFyIGNvbW1vbiA9IHJlcXVpcmUoXCIuL2NvbW1vbi5qc1wiKTtcclxudmFyIGFjdGlvbnMgPSByZXF1aXJlKFwiLi4vYWN0aW9ucy5qc1wiKTtcclxudmFyIHRvcHV0aWxzID0gcmVxdWlyZShcIi4uL3V0aWxzLmpzXCIpO1xyXG52YXIgdmlld3MgPSByZXF1aXJlKFwiLi4vc3RvcmUvdmlldy5qc1wiKTtcclxudmFyIEZpbHQgPSByZXF1aXJlKFwiLi4vZmlsdC9maWx0LmpzXCIpO1xyXG5GbG93VGFibGUgPSByZXF1aXJlKFwiLi9mbG93dGFibGUuanNcIik7XHJcbnZhciBmbG93ZGV0YWlsID0gcmVxdWlyZShcIi4vZmxvd2RldGFpbC5qc1wiKTtcclxuXHJcblxyXG52YXIgTWFpblZpZXcgPSBSZWFjdC5jcmVhdGVDbGFzcyh7XHJcbiAgICBtaXhpbnM6IFtjb21tb24uTmF2aWdhdGlvbiwgY29tbW9uLlN0YXRlXSxcclxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMub25RdWVyeUNoYW5nZShRdWVyeS5GSUxURVIsIGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAgICAgdGhpcy5zdGF0ZS52aWV3LnJlY2FsY3VsYXRlKHRoaXMuZ2V0Vmlld0ZpbHQoKSwgdGhpcy5nZXRWaWV3U29ydCgpKTtcclxuICAgICAgICB9LmJpbmQodGhpcykpO1xyXG4gICAgICAgIHRoaXMub25RdWVyeUNoYW5nZShRdWVyeS5ISUdITElHSFQsIGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAgICAgdGhpcy5zdGF0ZS52aWV3LnJlY2FsY3VsYXRlKHRoaXMuZ2V0Vmlld0ZpbHQoKSwgdGhpcy5nZXRWaWV3U29ydCgpKTtcclxuICAgICAgICB9LmJpbmQodGhpcykpO1xyXG4gICAgICAgIHJldHVybiB7XHJcbiAgICAgICAgICAgIGZsb3dzOiBbXVxyXG4gICAgICAgIH07XHJcbiAgICB9LFxyXG4gICAgZ2V0Vmlld0ZpbHQ6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0cnkge1xyXG4gICAgICAgICAgICB2YXIgZmlsdCA9IEZpbHQucGFyc2UodGhpcy5nZXRRdWVyeSgpW1F1ZXJ5LkZJTFRFUl0gfHwgXCJcIik7XHJcbiAgICAgICAgICAgIHZhciBoaWdobGlnaHRTdHIgPSB0aGlzLmdldFF1ZXJ5KClbUXVlcnkuSElHSExJR0hUXTtcclxuICAgICAgICAgICAgdmFyIGhpZ2hsaWdodCA9IGhpZ2hsaWdodFN0ciA/IEZpbHQucGFyc2UoaGlnaGxpZ2h0U3RyKSA6IGZhbHNlO1xyXG4gICAgICAgIH0gY2F0Y2ggKGUpIHtcclxuICAgICAgICAgICAgY29uc29sZS5lcnJvcihcIkVycm9yIHdoZW4gcHJvY2Vzc2luZyBmaWx0ZXI6IFwiICsgZSk7XHJcbiAgICAgICAgfVxyXG5cclxuICAgICAgICByZXR1cm4gZnVuY3Rpb24gZmlsdGVyX2FuZF9oaWdobGlnaHQoZmxvdykge1xyXG4gICAgICAgICAgICBpZiAoIXRoaXMuX2hpZ2hsaWdodCkge1xyXG4gICAgICAgICAgICAgICAgdGhpcy5faGlnaGxpZ2h0ID0ge307XHJcbiAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgdGhpcy5faGlnaGxpZ2h0W2Zsb3cuaWRdID0gaGlnaGxpZ2h0ICYmIGhpZ2hsaWdodChmbG93KTtcclxuICAgICAgICAgICAgcmV0dXJuIGZpbHQoZmxvdyk7XHJcbiAgICAgICAgfTtcclxuICAgIH0sXHJcbiAgICBnZXRWaWV3U29ydDogZnVuY3Rpb24gKCkge1xyXG4gICAgfSxcclxuICAgIGNvbXBvbmVudFdpbGxSZWNlaXZlUHJvcHM6IGZ1bmN0aW9uIChuZXh0UHJvcHMpIHtcclxuICAgICAgICBpZiAobmV4dFByb3BzLmZsb3dTdG9yZSAhPT0gdGhpcy5wcm9wcy5mbG93U3RvcmUpIHtcclxuICAgICAgICAgICAgdGhpcy5jbG9zZVZpZXcoKTtcclxuICAgICAgICAgICAgdGhpcy5vcGVuVmlldyhuZXh0UHJvcHMuZmxvd1N0b3JlKTtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgb3BlblZpZXc6IGZ1bmN0aW9uIChzdG9yZSkge1xyXG4gICAgICAgIHZhciB2aWV3ID0gbmV3IHZpZXdzLlN0b3JlVmlldyhzdG9yZSwgdGhpcy5nZXRWaWV3RmlsdCgpLCB0aGlzLmdldFZpZXdTb3J0KCkpO1xyXG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe1xyXG4gICAgICAgICAgICB2aWV3OiB2aWV3XHJcbiAgICAgICAgfSk7XHJcblxyXG4gICAgICAgIHZpZXcuYWRkTGlzdGVuZXIoXCJyZWNhbGN1bGF0ZVwiLCB0aGlzLm9uUmVjYWxjdWxhdGUpO1xyXG4gICAgICAgIHZpZXcuYWRkTGlzdGVuZXIoXCJhZGQgdXBkYXRlIHJlbW92ZVwiLCB0aGlzLm9uVXBkYXRlKTtcclxuICAgICAgICB2aWV3LmFkZExpc3RlbmVyKFwicmVtb3ZlXCIsIHRoaXMub25SZW1vdmUpO1xyXG4gICAgfSxcclxuICAgIG9uUmVjYWxjdWxhdGU6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLmZvcmNlVXBkYXRlKCk7XHJcbiAgICAgICAgdmFyIHNlbGVjdGVkID0gdGhpcy5nZXRTZWxlY3RlZCgpO1xyXG4gICAgICAgIGlmIChzZWxlY3RlZCkge1xyXG4gICAgICAgICAgICB0aGlzLnJlZnMuZmxvd1RhYmxlLnNjcm9sbEludG9WaWV3KHNlbGVjdGVkKTtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgb25VcGRhdGU6IGZ1bmN0aW9uIChmbG93KSB7XHJcbiAgICAgICAgaWYgKGZsb3cuaWQgPT09IHRoaXMuZ2V0UGFyYW1zKCkuZmxvd0lkKSB7XHJcbiAgICAgICAgICAgIHRoaXMuZm9yY2VVcGRhdGUoKTtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgb25SZW1vdmU6IGZ1bmN0aW9uIChmbG93X2lkLCBpbmRleCkge1xyXG4gICAgICAgIGlmIChmbG93X2lkID09PSB0aGlzLmdldFBhcmFtcygpLmZsb3dJZCkge1xyXG4gICAgICAgICAgICB2YXIgZmxvd190b19zZWxlY3QgPSB0aGlzLnN0YXRlLnZpZXcubGlzdFtNYXRoLm1pbihpbmRleCwgdGhpcy5zdGF0ZS52aWV3Lmxpc3QubGVuZ3RoIC0xKV07XHJcbiAgICAgICAgICAgIHRoaXMuc2VsZWN0RmxvdyhmbG93X3RvX3NlbGVjdCk7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIGNsb3NlVmlldzogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMuc3RhdGUudmlldy5jbG9zZSgpO1xyXG4gICAgfSxcclxuICAgIGNvbXBvbmVudFdpbGxNb3VudDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMub3BlblZpZXcodGhpcy5wcm9wcy5mbG93U3RvcmUpO1xyXG4gICAgfSxcclxuICAgIGNvbXBvbmVudFdpbGxVbm1vdW50OiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdGhpcy5jbG9zZVZpZXcoKTtcclxuICAgIH0sXHJcbiAgICBzZWxlY3RGbG93OiBmdW5jdGlvbiAoZmxvdykge1xyXG4gICAgICAgIGlmIChmbG93KSB7XHJcbiAgICAgICAgICAgIHRoaXMucmVwbGFjZVdpdGgoXHJcbiAgICAgICAgICAgICAgICBcImZsb3dcIixcclxuICAgICAgICAgICAgICAgIHtcclxuICAgICAgICAgICAgICAgICAgICBmbG93SWQ6IGZsb3cuaWQsXHJcbiAgICAgICAgICAgICAgICAgICAgZGV0YWlsVGFiOiB0aGlzLmdldFBhcmFtcygpLmRldGFpbFRhYiB8fCBcInJlcXVlc3RcIlxyXG4gICAgICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICApO1xyXG4gICAgICAgICAgICB0aGlzLnJlZnMuZmxvd1RhYmxlLnNjcm9sbEludG9WaWV3KGZsb3cpO1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIHRoaXMucmVwbGFjZVdpdGgoXCJmbG93c1wiLCB7fSk7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIHNlbGVjdEZsb3dSZWxhdGl2ZTogZnVuY3Rpb24gKHNoaWZ0KSB7XHJcbiAgICAgICAgdmFyIGZsb3dzID0gdGhpcy5zdGF0ZS52aWV3Lmxpc3Q7XHJcbiAgICAgICAgdmFyIGluZGV4O1xyXG4gICAgICAgIGlmICghdGhpcy5nZXRQYXJhbXMoKS5mbG93SWQpIHtcclxuICAgICAgICAgICAgaWYgKHNoaWZ0ID4gMCkge1xyXG4gICAgICAgICAgICAgICAgaW5kZXggPSBmbG93cy5sZW5ndGggLSAxO1xyXG4gICAgICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICAgICAgaW5kZXggPSAwO1xyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgdmFyIGN1cnJGbG93SWQgPSB0aGlzLmdldFBhcmFtcygpLmZsb3dJZDtcclxuICAgICAgICAgICAgdmFyIGkgPSBmbG93cy5sZW5ndGg7XHJcbiAgICAgICAgICAgIHdoaWxlIChpLS0pIHtcclxuICAgICAgICAgICAgICAgIGlmIChmbG93c1tpXS5pZCA9PT0gY3VyckZsb3dJZCkge1xyXG4gICAgICAgICAgICAgICAgICAgIGluZGV4ID0gaTtcclxuICAgICAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICBpbmRleCA9IE1hdGgubWluKFxyXG4gICAgICAgICAgICAgICAgTWF0aC5tYXgoMCwgaW5kZXggKyBzaGlmdCksXHJcbiAgICAgICAgICAgICAgICBmbG93cy5sZW5ndGggLSAxKTtcclxuICAgICAgICB9XHJcbiAgICAgICAgdGhpcy5zZWxlY3RGbG93KGZsb3dzW2luZGV4XSk7XHJcbiAgICB9LFxyXG4gICAgb25LZXlEb3duOiBmdW5jdGlvbiAoZSkge1xyXG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5nZXRTZWxlY3RlZCgpO1xyXG4gICAgICAgIGlmIChlLmN0cmxLZXkpIHtcclxuICAgICAgICAgICAgcmV0dXJuO1xyXG4gICAgICAgIH1cclxuICAgICAgICBzd2l0Y2ggKGUua2V5Q29kZSkge1xyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5LOlxyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5VUDpcclxuICAgICAgICAgICAgICAgIHRoaXMuc2VsZWN0Rmxvd1JlbGF0aXZlKC0xKTtcclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5KOlxyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5ET1dOOlxyXG4gICAgICAgICAgICAgICAgdGhpcy5zZWxlY3RGbG93UmVsYXRpdmUoKzEpO1xyXG4gICAgICAgICAgICAgICAgYnJlYWs7XHJcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LlNQQUNFOlxyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5QQUdFX0RPV046XHJcbiAgICAgICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3dSZWxhdGl2ZSgrMTApO1xyXG4gICAgICAgICAgICAgICAgYnJlYWs7XHJcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LlBBR0VfVVA6XHJcbiAgICAgICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3dSZWxhdGl2ZSgtMTApO1xyXG4gICAgICAgICAgICAgICAgYnJlYWs7XHJcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LkVORDpcclxuICAgICAgICAgICAgICAgIHRoaXMuc2VsZWN0Rmxvd1JlbGF0aXZlKCsxZTEwKTtcclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5IT01FOlxyXG4gICAgICAgICAgICAgICAgdGhpcy5zZWxlY3RGbG93UmVsYXRpdmUoLTFlMTApO1xyXG4gICAgICAgICAgICAgICAgYnJlYWs7XHJcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LkVTQzpcclxuICAgICAgICAgICAgICAgIHRoaXMuc2VsZWN0RmxvdyhudWxsKTtcclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5IOlxyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5MRUZUOlxyXG4gICAgICAgICAgICAgICAgaWYgKHRoaXMucmVmcy5mbG93RGV0YWlscykge1xyXG4gICAgICAgICAgICAgICAgICAgIHRoaXMucmVmcy5mbG93RGV0YWlscy5uZXh0VGFiKC0xKTtcclxuICAgICAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5MOlxyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5UQUI6XHJcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LlJJR0hUOlxyXG4gICAgICAgICAgICAgICAgaWYgKHRoaXMucmVmcy5mbG93RGV0YWlscykge1xyXG4gICAgICAgICAgICAgICAgICAgIHRoaXMucmVmcy5mbG93RGV0YWlscy5uZXh0VGFiKCsxKTtcclxuICAgICAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5DOlxyXG4gICAgICAgICAgICAgICAgaWYgKGUuc2hpZnRLZXkpIHtcclxuICAgICAgICAgICAgICAgICAgICBhY3Rpb25zLkZsb3dBY3Rpb25zLmNsZWFyKCk7XHJcbiAgICAgICAgICAgICAgICB9XHJcbiAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuRDpcclxuICAgICAgICAgICAgICAgIGlmIChmbG93KSB7XHJcbiAgICAgICAgICAgICAgICAgICAgaWYgKGUuc2hpZnRLZXkpIHtcclxuICAgICAgICAgICAgICAgICAgICAgICAgYWN0aW9ucy5GbG93QWN0aW9ucy5kdXBsaWNhdGUoZmxvdyk7XHJcbiAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgICAgICAgICAgICAgYWN0aW9ucy5GbG93QWN0aW9ucy5kZWxldGUoZmxvdyk7XHJcbiAgICAgICAgICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICAgICAgYnJlYWs7XHJcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LkE6XHJcbiAgICAgICAgICAgICAgICBpZiAoZS5zaGlmdEtleSkge1xyXG4gICAgICAgICAgICAgICAgICAgIGFjdGlvbnMuRmxvd0FjdGlvbnMuYWNjZXB0X2FsbCgpO1xyXG4gICAgICAgICAgICAgICAgfSBlbHNlIGlmIChmbG93ICYmIGZsb3cuaW50ZXJjZXB0ZWQpIHtcclxuICAgICAgICAgICAgICAgICAgICBhY3Rpb25zLkZsb3dBY3Rpb25zLmFjY2VwdChmbG93KTtcclxuICAgICAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5SOlxyXG4gICAgICAgICAgICAgICAgaWYgKCFlLnNoaWZ0S2V5ICYmIGZsb3cpIHtcclxuICAgICAgICAgICAgICAgICAgICBhY3Rpb25zLkZsb3dBY3Rpb25zLnJlcGxheShmbG93KTtcclxuICAgICAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5WOlxyXG4gICAgICAgICAgICAgICAgaWYoZS5zaGlmdEtleSAmJiBmbG93ICYmIGZsb3cubW9kaWZpZWQpIHtcclxuICAgICAgICAgICAgICAgICAgICBhY3Rpb25zLkZsb3dBY3Rpb25zLnJldmVydChmbG93KTtcclxuICAgICAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICBkZWZhdWx0OlxyXG4gICAgICAgICAgICAgICAgY29uc29sZS5kZWJ1ZyhcImtleWRvd25cIiwgZS5rZXlDb2RlKTtcclxuICAgICAgICAgICAgICAgIHJldHVybjtcclxuICAgICAgICB9XHJcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xyXG4gICAgfSxcclxuICAgIGdldFNlbGVjdGVkOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgcmV0dXJuIHRoaXMucHJvcHMuZmxvd1N0b3JlLmdldCh0aGlzLmdldFBhcmFtcygpLmZsb3dJZCk7XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIHNlbGVjdGVkID0gdGhpcy5nZXRTZWxlY3RlZCgpO1xyXG5cclxuICAgICAgICB2YXIgZGV0YWlscztcclxuICAgICAgICBpZiAoc2VsZWN0ZWQpIHtcclxuICAgICAgICAgICAgZGV0YWlscyA9IFtcclxuICAgICAgICAgICAgICAgIDxjb21tb24uU3BsaXR0ZXIga2V5PVwic3BsaXR0ZXJcIi8+LFxyXG4gICAgICAgICAgICAgICAgPGZsb3dkZXRhaWwuRmxvd0RldGFpbCBrZXk9XCJmbG93RGV0YWlsc1wiIHJlZj1cImZsb3dEZXRhaWxzXCIgZmxvdz17c2VsZWN0ZWR9Lz5cclxuICAgICAgICAgICAgXTtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICBkZXRhaWxzID0gbnVsbDtcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPVwibWFpbi12aWV3XCIgb25LZXlEb3duPXt0aGlzLm9uS2V5RG93bn0gdGFiSW5kZXg9XCIwXCI+XHJcbiAgICAgICAgICAgICAgICA8Rmxvd1RhYmxlIHJlZj1cImZsb3dUYWJsZVwiXHJcbiAgICAgICAgICAgICAgICAgICAgdmlldz17dGhpcy5zdGF0ZS52aWV3fVxyXG4gICAgICAgICAgICAgICAgICAgIHNlbGVjdEZsb3c9e3RoaXMuc2VsZWN0Rmxvd31cclxuICAgICAgICAgICAgICAgICAgICBzZWxlY3RlZD17c2VsZWN0ZWR9IC8+XHJcbiAgICAgICAgICAgICAgICB7ZGV0YWlsc31cclxuICAgICAgICAgICAgPC9kaXY+XHJcbiAgICAgICAgKTtcclxuICAgIH1cclxufSk7XHJcblxyXG5tb2R1bGUuZXhwb3J0cyA9IE1haW5WaWV3O1xyXG4iLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XHJcbnZhciBSZWFjdFJvdXRlciA9IHJlcXVpcmUoXCJyZWFjdC1yb3V0ZXJcIik7XHJcbnZhciBfID0gcmVxdWlyZShcImxvZGFzaFwiKTtcclxuXHJcbnZhciBjb21tb24gPSByZXF1aXJlKFwiLi9jb21tb24uanNcIik7XHJcbnZhciBNYWluVmlldyA9IHJlcXVpcmUoXCIuL21haW52aWV3LmpzXCIpO1xyXG52YXIgRm9vdGVyID0gcmVxdWlyZShcIi4vZm9vdGVyLmpzXCIpO1xyXG52YXIgaGVhZGVyID0gcmVxdWlyZShcIi4vaGVhZGVyLmpzXCIpO1xyXG52YXIgRXZlbnRMb2cgPSByZXF1aXJlKFwiLi9ldmVudGxvZy5qc1wiKTtcclxudmFyIHN0b3JlID0gcmVxdWlyZShcIi4uL3N0b3JlL3N0b3JlLmpzXCIpO1xyXG5cclxuXHJcbi8vVE9ETzogTW92ZSBvdXQgb2YgaGVyZSwganVzdCBhIHN0dWIuXHJcbnZhciBSZXBvcnRzID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgcmV0dXJuIDxkaXY+UmVwb3J0RWRpdG9yPC9kaXY+O1xyXG4gICAgfVxyXG59KTtcclxuXHJcblxyXG52YXIgUHJveHlBcHBNYWluID0gUmVhY3QuY3JlYXRlQ2xhc3Moe1xyXG4gICAgbWl4aW5zOiBbY29tbW9uLlN0YXRlXSxcclxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHZhciBldmVudFN0b3JlID0gbmV3IHN0b3JlLkV2ZW50TG9nU3RvcmUoKTtcclxuICAgICAgICB2YXIgZmxvd1N0b3JlID0gbmV3IHN0b3JlLkZsb3dTdG9yZSgpO1xyXG4gICAgICAgIHZhciBzZXR0aW5ncyA9IG5ldyBzdG9yZS5TZXR0aW5nc1N0b3JlKCk7XHJcblxyXG4gICAgICAgIC8vIERlZmF1bHQgU2V0dGluZ3MgYmVmb3JlIGZldGNoXHJcbiAgICAgICAgXy5leHRlbmQoc2V0dGluZ3MuZGljdCx7XHJcbiAgICAgICAgfSk7XHJcbiAgICAgICAgcmV0dXJuIHtcclxuICAgICAgICAgICAgc2V0dGluZ3M6IHNldHRpbmdzLFxyXG4gICAgICAgICAgICBmbG93U3RvcmU6IGZsb3dTdG9yZSxcclxuICAgICAgICAgICAgZXZlbnRTdG9yZTogZXZlbnRTdG9yZVxyXG4gICAgICAgIH07XHJcbiAgICB9LFxyXG4gICAgY29tcG9uZW50RGlkTW91bnQ6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLnN0YXRlLnNldHRpbmdzLmFkZExpc3RlbmVyKFwicmVjYWxjdWxhdGVcIiwgdGhpcy5vblNldHRpbmdzQ2hhbmdlKTtcclxuICAgICAgICB3aW5kb3cuYXBwID0gdGhpcztcclxuICAgIH0sXHJcbiAgICBjb21wb25lbnRXaWxsVW5tb3VudDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMuc3RhdGUuc2V0dGluZ3MucmVtb3ZlTGlzdGVuZXIoXCJyZWNhbGN1bGF0ZVwiLCB0aGlzLm9uU2V0dGluZ3NDaGFuZ2UpO1xyXG4gICAgfSxcclxuICAgIG9uU2V0dGluZ3NDaGFuZ2U6IGZ1bmN0aW9uKCl7XHJcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7XHJcbiAgICAgICAgICAgIHNldHRpbmdzOiB0aGlzLnN0YXRlLnNldHRpbmdzXHJcbiAgICAgICAgfSk7XHJcbiAgICB9LFxyXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XHJcblxyXG4gICAgICAgIHZhciBldmVudGxvZztcclxuICAgICAgICBpZiAodGhpcy5nZXRRdWVyeSgpW1F1ZXJ5LlNIT1dfRVZFTlRMT0ddKSB7XHJcbiAgICAgICAgICAgIGV2ZW50bG9nID0gW1xyXG4gICAgICAgICAgICAgICAgPGNvbW1vbi5TcGxpdHRlciBrZXk9XCJzcGxpdHRlclwiIGF4aXM9XCJ5XCIvPixcclxuICAgICAgICAgICAgICAgIDxFdmVudExvZyBrZXk9XCJldmVudGxvZ1wiIGV2ZW50U3RvcmU9e3RoaXMuc3RhdGUuZXZlbnRTdG9yZX0vPlxyXG4gICAgICAgICAgICBdO1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIGV2ZW50bG9nID0gbnVsbDtcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgIDxkaXYgaWQ9XCJjb250YWluZXJcIj5cclxuICAgICAgICAgICAgICAgIDxoZWFkZXIuSGVhZGVyIHNldHRpbmdzPXt0aGlzLnN0YXRlLnNldHRpbmdzLmRpY3R9Lz5cclxuICAgICAgICAgICAgICAgIDxSb3V0ZUhhbmRsZXIgc2V0dGluZ3M9e3RoaXMuc3RhdGUuc2V0dGluZ3MuZGljdH0gZmxvd1N0b3JlPXt0aGlzLnN0YXRlLmZsb3dTdG9yZX0vPlxyXG4gICAgICAgICAgICAgICAge2V2ZW50bG9nfVxyXG4gICAgICAgICAgICAgICAgPEZvb3RlciBzZXR0aW5ncz17dGhpcy5zdGF0ZS5zZXR0aW5ncy5kaWN0fS8+XHJcbiAgICAgICAgICAgIDwvZGl2PlxyXG4gICAgICAgICk7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxuXHJcbnZhciBSb3V0ZSA9IFJlYWN0Um91dGVyLlJvdXRlO1xyXG52YXIgUm91dGVIYW5kbGVyID0gUmVhY3RSb3V0ZXIuUm91dGVIYW5kbGVyO1xyXG52YXIgUmVkaXJlY3QgPSBSZWFjdFJvdXRlci5SZWRpcmVjdDtcclxudmFyIERlZmF1bHRSb3V0ZSA9IFJlYWN0Um91dGVyLkRlZmF1bHRSb3V0ZTtcclxudmFyIE5vdEZvdW5kUm91dGUgPSBSZWFjdFJvdXRlci5Ob3RGb3VuZFJvdXRlO1xyXG5cclxuXHJcbnZhciByb3V0ZXMgPSAoXHJcbiAgICA8Um91dGUgcGF0aD1cIi9cIiBoYW5kbGVyPXtQcm94eUFwcE1haW59PlxyXG4gICAgICAgIDxSb3V0ZSBuYW1lPVwiZmxvd3NcIiBwYXRoPVwiZmxvd3NcIiBoYW5kbGVyPXtNYWluVmlld30vPlxyXG4gICAgICAgIDxSb3V0ZSBuYW1lPVwiZmxvd1wiIHBhdGg9XCJmbG93cy86Zmxvd0lkLzpkZXRhaWxUYWJcIiBoYW5kbGVyPXtNYWluVmlld30vPlxyXG4gICAgICAgIDxSb3V0ZSBuYW1lPVwicmVwb3J0c1wiIGhhbmRsZXI9e1JlcG9ydHN9Lz5cclxuICAgICAgICA8UmVkaXJlY3QgcGF0aD1cIi9cIiB0bz1cImZsb3dzXCIgLz5cclxuICAgIDwvUm91dGU+XHJcbik7XHJcblxyXG5tb2R1bGUuZXhwb3J0cyA9IHtcclxuICAgIHJvdXRlczogcm91dGVzXHJcbn07XHJcblxyXG4iLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XHJcblxyXG52YXIgVmlydHVhbFNjcm9sbE1peGluID0ge1xyXG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgcmV0dXJuIHtcclxuICAgICAgICAgICAgc3RhcnQ6IDAsXHJcbiAgICAgICAgICAgIHN0b3A6IDBcclxuICAgICAgICB9O1xyXG4gICAgfSxcclxuICAgIGNvbXBvbmVudFdpbGxNb3VudDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIGlmICghdGhpcy5wcm9wcy5yb3dIZWlnaHQpIHtcclxuICAgICAgICAgICAgY29uc29sZS53YXJuKFwiVmlydHVhbFNjcm9sbE1peGluOiBObyByb3dIZWlnaHQgc3BlY2lmaWVkXCIsIHRoaXMpO1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICBnZXRQbGFjZWhvbGRlclRvcDogZnVuY3Rpb24gKHRvdGFsKSB7XHJcbiAgICAgICAgdmFyIFRhZyA9IHRoaXMucHJvcHMucGxhY2Vob2xkZXJUYWdOYW1lIHx8IFwidHJcIjtcclxuICAgICAgICAvLyBXaGVuIGEgbGFyZ2UgdHJ1bmsgb2YgZWxlbWVudHMgaXMgcmVtb3ZlZCBmcm9tIHRoZSBidXR0b24sIHN0YXJ0IG1heSBiZSBmYXIgb2ZmIHRoZSB2aWV3cG9ydC5cclxuICAgICAgICAvLyBUbyBtYWtlIHRoaXMgaXNzdWUgbGVzcyBzZXZlcmUsIGxpbWl0IHRoZSB0b3AgcGxhY2Vob2xkZXIgdG8gdGhlIHRvdGFsIG51bWJlciBvZiByb3dzLlxyXG4gICAgICAgIHZhciBzdHlsZSA9IHtcclxuICAgICAgICAgICAgaGVpZ2h0OiBNYXRoLm1pbih0aGlzLnN0YXRlLnN0YXJ0LCB0b3RhbCkgKiB0aGlzLnByb3BzLnJvd0hlaWdodFxyXG4gICAgICAgIH07XHJcbiAgICAgICAgdmFyIHNwYWNlciA9IDxUYWcga2V5PVwicGxhY2Vob2xkZXItdG9wXCIgc3R5bGU9e3N0eWxlfT48L1RhZz47XHJcblxyXG4gICAgICAgIGlmICh0aGlzLnN0YXRlLnN0YXJ0ICUgMiA9PT0gMSkge1xyXG4gICAgICAgICAgICAvLyBmaXggZXZlbi9vZGQgcm93c1xyXG4gICAgICAgICAgICByZXR1cm4gW3NwYWNlciwgPFRhZyBrZXk9XCJwbGFjZWhvbGRlci10b3AtMlwiPjwvVGFnPl07XHJcbiAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgcmV0dXJuIHNwYWNlcjtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgZ2V0UGxhY2Vob2xkZXJCb3R0b206IGZ1bmN0aW9uICh0b3RhbCkge1xyXG4gICAgICAgIHZhciBUYWcgPSB0aGlzLnByb3BzLnBsYWNlaG9sZGVyVGFnTmFtZSB8fCBcInRyXCI7XHJcbiAgICAgICAgdmFyIHN0eWxlID0ge1xyXG4gICAgICAgICAgICBoZWlnaHQ6IE1hdGgubWF4KDAsIHRvdGFsIC0gdGhpcy5zdGF0ZS5zdG9wKSAqIHRoaXMucHJvcHMucm93SGVpZ2h0XHJcbiAgICAgICAgfTtcclxuICAgICAgICByZXR1cm4gPFRhZyBrZXk9XCJwbGFjZWhvbGRlci1ib3R0b21cIiBzdHlsZT17c3R5bGV9PjwvVGFnPjtcclxuICAgIH0sXHJcbiAgICBjb21wb25lbnREaWRNb3VudDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMub25TY3JvbGwoKTtcclxuICAgICAgICB3aW5kb3cuYWRkRXZlbnRMaXN0ZW5lcigncmVzaXplJywgdGhpcy5vblNjcm9sbCk7XHJcbiAgICB9LFxyXG4gICAgY29tcG9uZW50V2lsbFVubW91bnQ6IGZ1bmN0aW9uKCl7XHJcbiAgICAgICAgd2luZG93LnJlbW92ZUV2ZW50TGlzdGVuZXIoJ3Jlc2l6ZScsIHRoaXMub25TY3JvbGwpO1xyXG4gICAgfSxcclxuICAgIG9uU2Nyb2xsOiBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgdmFyIHZpZXdwb3J0ID0gdGhpcy5nZXRET01Ob2RlKCk7XHJcbiAgICAgICAgdmFyIHRvcCA9IHZpZXdwb3J0LnNjcm9sbFRvcDtcclxuICAgICAgICB2YXIgaGVpZ2h0ID0gdmlld3BvcnQub2Zmc2V0SGVpZ2h0O1xyXG4gICAgICAgIHZhciBzdGFydCA9IE1hdGguZmxvb3IodG9wIC8gdGhpcy5wcm9wcy5yb3dIZWlnaHQpO1xyXG4gICAgICAgIHZhciBzdG9wID0gc3RhcnQgKyBNYXRoLmNlaWwoaGVpZ2h0IC8gKHRoaXMucHJvcHMucm93SGVpZ2h0TWluIHx8IHRoaXMucHJvcHMucm93SGVpZ2h0KSk7XHJcblxyXG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe1xyXG4gICAgICAgICAgICBzdGFydDogc3RhcnQsXHJcbiAgICAgICAgICAgIHN0b3A6IHN0b3BcclxuICAgICAgICB9KTtcclxuICAgIH0sXHJcbiAgICByZW5kZXJSb3dzOiBmdW5jdGlvbiAoZWxlbXMpIHtcclxuICAgICAgICB2YXIgcm93cyA9IFtdO1xyXG4gICAgICAgIHZhciBtYXggPSBNYXRoLm1pbihlbGVtcy5sZW5ndGgsIHRoaXMuc3RhdGUuc3RvcCk7XHJcblxyXG4gICAgICAgIGZvciAodmFyIGkgPSB0aGlzLnN0YXRlLnN0YXJ0OyBpIDwgbWF4OyBpKyspIHtcclxuICAgICAgICAgICAgdmFyIGVsZW0gPSBlbGVtc1tpXTtcclxuICAgICAgICAgICAgcm93cy5wdXNoKHRoaXMucmVuZGVyUm93KGVsZW0pKTtcclxuICAgICAgICB9XHJcbiAgICAgICAgcmV0dXJuIHJvd3M7XHJcbiAgICB9LFxyXG4gICAgc2Nyb2xsUm93SW50b1ZpZXc6IGZ1bmN0aW9uIChpbmRleCwgaGVhZF9oZWlnaHQpIHtcclxuXHJcbiAgICAgICAgdmFyIHJvd190b3AgPSAoaW5kZXggKiB0aGlzLnByb3BzLnJvd0hlaWdodCkgKyBoZWFkX2hlaWdodDtcclxuICAgICAgICB2YXIgcm93X2JvdHRvbSA9IHJvd190b3AgKyB0aGlzLnByb3BzLnJvd0hlaWdodDtcclxuXHJcbiAgICAgICAgdmFyIHZpZXdwb3J0ID0gdGhpcy5nZXRET01Ob2RlKCk7XHJcbiAgICAgICAgdmFyIHZpZXdwb3J0X3RvcCA9IHZpZXdwb3J0LnNjcm9sbFRvcDtcclxuICAgICAgICB2YXIgdmlld3BvcnRfYm90dG9tID0gdmlld3BvcnRfdG9wICsgdmlld3BvcnQub2Zmc2V0SGVpZ2h0O1xyXG5cclxuICAgICAgICAvLyBBY2NvdW50IGZvciBwaW5uZWQgdGhlYWRcclxuICAgICAgICBpZiAocm93X3RvcCAtIGhlYWRfaGVpZ2h0IDwgdmlld3BvcnRfdG9wKSB7XHJcbiAgICAgICAgICAgIHZpZXdwb3J0LnNjcm9sbFRvcCA9IHJvd190b3AgLSBoZWFkX2hlaWdodDtcclxuICAgICAgICB9IGVsc2UgaWYgKHJvd19ib3R0b20gPiB2aWV3cG9ydF9ib3R0b20pIHtcclxuICAgICAgICAgICAgdmlld3BvcnQuc2Nyb2xsVG9wID0gcm93X2JvdHRvbSAtIHZpZXdwb3J0Lm9mZnNldEhlaWdodDtcclxuICAgICAgICB9XHJcbiAgICB9LFxyXG59O1xyXG5cclxubW9kdWxlLmV4cG9ydHMgID0gVmlydHVhbFNjcm9sbE1peGluOyIsIlxyXG52YXIgYWN0aW9ucyA9IHJlcXVpcmUoXCIuL2FjdGlvbnMuanNcIik7XHJcblxyXG5mdW5jdGlvbiBDb25uZWN0aW9uKHVybCkge1xyXG4gICAgaWYgKHVybFswXSA9PT0gXCIvXCIpIHtcclxuICAgICAgICB1cmwgPSBsb2NhdGlvbi5vcmlnaW4ucmVwbGFjZShcImh0dHBcIiwgXCJ3c1wiKSArIHVybDtcclxuICAgIH1cclxuXHJcbiAgICB2YXIgd3MgPSBuZXcgV2ViU29ja2V0KHVybCk7XHJcbiAgICB3cy5vbm9wZW4gPSBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgYWN0aW9ucy5Db25uZWN0aW9uQWN0aW9ucy5vcGVuKCk7XHJcbiAgICB9O1xyXG4gICAgd3Mub25tZXNzYWdlID0gZnVuY3Rpb24gKG1lc3NhZ2UpIHtcclxuICAgICAgICB2YXIgbSA9IEpTT04ucGFyc2UobWVzc2FnZS5kYXRhKTtcclxuICAgICAgICBBcHBEaXNwYXRjaGVyLmRpc3BhdGNoU2VydmVyQWN0aW9uKG0pO1xyXG4gICAgfTtcclxuICAgIHdzLm9uZXJyb3IgPSBmdW5jdGlvbiAoKSB7XHJcbiAgICAgICAgYWN0aW9ucy5Db25uZWN0aW9uQWN0aW9ucy5lcnJvcigpO1xyXG4gICAgICAgIEV2ZW50TG9nQWN0aW9ucy5hZGRfZXZlbnQoXCJXZWJTb2NrZXQgY29ubmVjdGlvbiBlcnJvci5cIik7XHJcbiAgICB9O1xyXG4gICAgd3Mub25jbG9zZSA9IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICBhY3Rpb25zLkNvbm5lY3Rpb25BY3Rpb25zLmNsb3NlKCk7XHJcbiAgICAgICAgRXZlbnRMb2dBY3Rpb25zLmFkZF9ldmVudChcIldlYlNvY2tldCBjb25uZWN0aW9uIGNsb3NlZC5cIik7XHJcbiAgICB9O1xyXG4gICAgcmV0dXJuIHdzO1xyXG59XHJcblxyXG5tb2R1bGUuZXhwb3J0cyA9IENvbm5lY3Rpb247IiwiXHJcbnZhciBmbHV4ID0gcmVxdWlyZShcImZsdXhcIik7XHJcblxyXG5jb25zdCBQYXlsb2FkU291cmNlcyA9IHtcclxuICAgIFZJRVc6IFwidmlld1wiLFxyXG4gICAgU0VSVkVSOiBcInNlcnZlclwiXHJcbn07XHJcblxyXG5cclxuQXBwRGlzcGF0Y2hlciA9IG5ldyBmbHV4LkRpc3BhdGNoZXIoKTtcclxuQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFZpZXdBY3Rpb24gPSBmdW5jdGlvbiAoYWN0aW9uKSB7XHJcbiAgICBhY3Rpb24uc291cmNlID0gUGF5bG9hZFNvdXJjZXMuVklFVztcclxuICAgIHRoaXMuZGlzcGF0Y2goYWN0aW9uKTtcclxufTtcclxuQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFNlcnZlckFjdGlvbiA9IGZ1bmN0aW9uIChhY3Rpb24pIHtcclxuICAgIGFjdGlvbi5zb3VyY2UgPSBQYXlsb2FkU291cmNlcy5TRVJWRVI7XHJcbiAgICB0aGlzLmRpc3BhdGNoKGFjdGlvbik7XHJcbn07XHJcblxyXG5tb2R1bGUuZXhwb3J0cyA9IHtcclxuICAgIEFwcERpc3BhdGNoZXI6IEFwcERpc3BhdGNoZXJcclxufTsiLCJtb2R1bGUuZXhwb3J0cyA9IChmdW5jdGlvbigpIHtcbiAgLypcbiAgICogR2VuZXJhdGVkIGJ5IFBFRy5qcyAwLjguMC5cbiAgICpcbiAgICogaHR0cDovL3BlZ2pzLm1hamRhLmN6L1xuICAgKi9cblxuICBmdW5jdGlvbiBwZWckc3ViY2xhc3MoY2hpbGQsIHBhcmVudCkge1xuICAgIGZ1bmN0aW9uIGN0b3IoKSB7IHRoaXMuY29uc3RydWN0b3IgPSBjaGlsZDsgfVxuICAgIGN0b3IucHJvdG90eXBlID0gcGFyZW50LnByb3RvdHlwZTtcbiAgICBjaGlsZC5wcm90b3R5cGUgPSBuZXcgY3RvcigpO1xuICB9XG5cbiAgZnVuY3Rpb24gU3ludGF4RXJyb3IobWVzc2FnZSwgZXhwZWN0ZWQsIGZvdW5kLCBvZmZzZXQsIGxpbmUsIGNvbHVtbikge1xuICAgIHRoaXMubWVzc2FnZSAgPSBtZXNzYWdlO1xuICAgIHRoaXMuZXhwZWN0ZWQgPSBleHBlY3RlZDtcbiAgICB0aGlzLmZvdW5kICAgID0gZm91bmQ7XG4gICAgdGhpcy5vZmZzZXQgICA9IG9mZnNldDtcbiAgICB0aGlzLmxpbmUgICAgID0gbGluZTtcbiAgICB0aGlzLmNvbHVtbiAgID0gY29sdW1uO1xuXG4gICAgdGhpcy5uYW1lICAgICA9IFwiU3ludGF4RXJyb3JcIjtcbiAgfVxuXG4gIHBlZyRzdWJjbGFzcyhTeW50YXhFcnJvciwgRXJyb3IpO1xuXG4gIGZ1bmN0aW9uIHBhcnNlKGlucHV0KSB7XG4gICAgdmFyIG9wdGlvbnMgPSBhcmd1bWVudHMubGVuZ3RoID4gMSA/IGFyZ3VtZW50c1sxXSA6IHt9LFxuXG4gICAgICAgIHBlZyRGQUlMRUQgPSB7fSxcblxuICAgICAgICBwZWckc3RhcnRSdWxlRnVuY3Rpb25zID0geyBzdGFydDogcGVnJHBhcnNlc3RhcnQgfSxcbiAgICAgICAgcGVnJHN0YXJ0UnVsZUZ1bmN0aW9uICA9IHBlZyRwYXJzZXN0YXJ0LFxuXG4gICAgICAgIHBlZyRjMCA9IHsgdHlwZTogXCJvdGhlclwiLCBkZXNjcmlwdGlvbjogXCJmaWx0ZXIgZXhwcmVzc2lvblwiIH0sXG4gICAgICAgIHBlZyRjMSA9IHBlZyRGQUlMRUQsXG4gICAgICAgIHBlZyRjMiA9IGZ1bmN0aW9uKG9yRXhwcikgeyByZXR1cm4gb3JFeHByOyB9LFxuICAgICAgICBwZWckYzMgPSBbXSxcbiAgICAgICAgcGVnJGM0ID0gZnVuY3Rpb24oKSB7cmV0dXJuIHRydWVGaWx0ZXI7IH0sXG4gICAgICAgIHBlZyRjNSA9IHsgdHlwZTogXCJvdGhlclwiLCBkZXNjcmlwdGlvbjogXCJ3aGl0ZXNwYWNlXCIgfSxcbiAgICAgICAgcGVnJGM2ID0gL15bIFxcdFxcblxccl0vLFxuICAgICAgICBwZWckYzcgPSB7IHR5cGU6IFwiY2xhc3NcIiwgdmFsdWU6IFwiWyBcXFxcdFxcXFxuXFxcXHJdXCIsIGRlc2NyaXB0aW9uOiBcIlsgXFxcXHRcXFxcblxcXFxyXVwiIH0sXG4gICAgICAgIHBlZyRjOCA9IHsgdHlwZTogXCJvdGhlclwiLCBkZXNjcmlwdGlvbjogXCJjb250cm9sIGNoYXJhY3RlclwiIH0sXG4gICAgICAgIHBlZyRjOSA9IC9eW3wmISgpflwiXS8sXG4gICAgICAgIHBlZyRjMTAgPSB7IHR5cGU6IFwiY2xhc3NcIiwgdmFsdWU6IFwiW3wmISgpflxcXCJdXCIsIGRlc2NyaXB0aW9uOiBcIlt8JiEoKX5cXFwiXVwiIH0sXG4gICAgICAgIHBlZyRjMTEgPSB7IHR5cGU6IFwib3RoZXJcIiwgZGVzY3JpcHRpb246IFwib3B0aW9uYWwgd2hpdGVzcGFjZVwiIH0sXG4gICAgICAgIHBlZyRjMTIgPSBcInxcIixcbiAgICAgICAgcGVnJGMxMyA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcInxcIiwgZGVzY3JpcHRpb246IFwiXFxcInxcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMxNCA9IGZ1bmN0aW9uKGZpcnN0LCBzZWNvbmQpIHsgcmV0dXJuIG9yKGZpcnN0LCBzZWNvbmQpOyB9LFxuICAgICAgICBwZWckYzE1ID0gXCImXCIsXG4gICAgICAgIHBlZyRjMTYgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCImXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCImXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMTcgPSBmdW5jdGlvbihmaXJzdCwgc2Vjb25kKSB7IHJldHVybiBhbmQoZmlyc3QsIHNlY29uZCk7IH0sXG4gICAgICAgIHBlZyRjMTggPSBcIiFcIixcbiAgICAgICAgcGVnJGMxOSA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIiFcIiwgZGVzY3JpcHRpb246IFwiXFxcIiFcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMyMCA9IGZ1bmN0aW9uKGV4cHIpIHsgcmV0dXJuIG5vdChleHByKTsgfSxcbiAgICAgICAgcGVnJGMyMSA9IFwiKFwiLFxuICAgICAgICBwZWckYzIyID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiKFwiLCBkZXNjcmlwdGlvbjogXCJcXFwiKFxcXCJcIiB9LFxuICAgICAgICBwZWckYzIzID0gXCIpXCIsXG4gICAgICAgIHBlZyRjMjQgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCIpXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCIpXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMjUgPSBmdW5jdGlvbihleHByKSB7IHJldHVybiBiaW5kaW5nKGV4cHIpOyB9LFxuICAgICAgICBwZWckYzI2ID0gXCJ+YVwiLFxuICAgICAgICBwZWckYzI3ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifmFcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5hXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMjggPSBmdW5jdGlvbigpIHsgcmV0dXJuIGFzc2V0RmlsdGVyOyB9LFxuICAgICAgICBwZWckYzI5ID0gXCJ+ZVwiLFxuICAgICAgICBwZWckYzMwID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifmVcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5lXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMzEgPSBmdW5jdGlvbigpIHsgcmV0dXJuIGVycm9yRmlsdGVyOyB9LFxuICAgICAgICBwZWckYzMyID0gXCJ+cVwiLFxuICAgICAgICBwZWckYzMzID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifnFcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5xXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMzQgPSBmdW5jdGlvbigpIHsgcmV0dXJuIG5vUmVzcG9uc2VGaWx0ZXI7IH0sXG4gICAgICAgIHBlZyRjMzUgPSBcIn5zXCIsXG4gICAgICAgIHBlZyRjMzYgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+c1wiLCBkZXNjcmlwdGlvbjogXCJcXFwifnNcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMzNyA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gcmVzcG9uc2VGaWx0ZXI7IH0sXG4gICAgICAgIHBlZyRjMzggPSBcInRydWVcIixcbiAgICAgICAgcGVnJGMzOSA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcInRydWVcIiwgZGVzY3JpcHRpb246IFwiXFxcInRydWVcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM0MCA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gdHJ1ZUZpbHRlcjsgfSxcbiAgICAgICAgcGVnJGM0MSA9IFwiZmFsc2VcIixcbiAgICAgICAgcGVnJGM0MiA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcImZhbHNlXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJmYWxzZVxcXCJcIiB9LFxuICAgICAgICBwZWckYzQzID0gZnVuY3Rpb24oKSB7IHJldHVybiBmYWxzZUZpbHRlcjsgfSxcbiAgICAgICAgcGVnJGM0NCA9IFwifmNcIixcbiAgICAgICAgcGVnJGM0NSA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5jXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+Y1xcXCJcIiB9LFxuICAgICAgICBwZWckYzQ2ID0gZnVuY3Rpb24ocykgeyByZXR1cm4gcmVzcG9uc2VDb2RlKHMpOyB9LFxuICAgICAgICBwZWckYzQ3ID0gXCJ+ZFwiLFxuICAgICAgICBwZWckYzQ4ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifmRcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5kXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNDkgPSBmdW5jdGlvbihzKSB7IHJldHVybiBkb21haW4ocyk7IH0sXG4gICAgICAgIHBlZyRjNTAgPSBcIn5oXCIsXG4gICAgICAgIHBlZyRjNTEgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+aFwiLCBkZXNjcmlwdGlvbjogXCJcXFwifmhcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM1MiA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIGhlYWRlcihzKTsgfSxcbiAgICAgICAgcGVnJGM1MyA9IFwifmhxXCIsXG4gICAgICAgIHBlZyRjNTQgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+aHFcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5ocVxcXCJcIiB9LFxuICAgICAgICBwZWckYzU1ID0gZnVuY3Rpb24ocykgeyByZXR1cm4gcmVxdWVzdEhlYWRlcihzKTsgfSxcbiAgICAgICAgcGVnJGM1NiA9IFwifmhzXCIsXG4gICAgICAgIHBlZyRjNTcgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+aHNcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5oc1xcXCJcIiB9LFxuICAgICAgICBwZWckYzU4ID0gZnVuY3Rpb24ocykgeyByZXR1cm4gcmVzcG9uc2VIZWFkZXIocyk7IH0sXG4gICAgICAgIHBlZyRjNTkgPSBcIn5tXCIsXG4gICAgICAgIHBlZyRjNjAgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+bVwiLCBkZXNjcmlwdGlvbjogXCJcXFwifm1cXFwiXCIgfSxcbiAgICAgICAgcGVnJGM2MSA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIG1ldGhvZChzKTsgfSxcbiAgICAgICAgcGVnJGM2MiA9IFwifnRcIixcbiAgICAgICAgcGVnJGM2MyA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn50XCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+dFxcXCJcIiB9LFxuICAgICAgICBwZWckYzY0ID0gZnVuY3Rpb24ocykgeyByZXR1cm4gY29udGVudFR5cGUocyk7IH0sXG4gICAgICAgIHBlZyRjNjUgPSBcIn50cVwiLFxuICAgICAgICBwZWckYzY2ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifnRxXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+dHFcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM2NyA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIHJlcXVlc3RDb250ZW50VHlwZShzKTsgfSxcbiAgICAgICAgcGVnJGM2OCA9IFwifnRzXCIsXG4gICAgICAgIHBlZyRjNjkgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+dHNcIiwgZGVzY3JpcHRpb246IFwiXFxcIn50c1xcXCJcIiB9LFxuICAgICAgICBwZWckYzcwID0gZnVuY3Rpb24ocykgeyByZXR1cm4gcmVzcG9uc2VDb250ZW50VHlwZShzKTsgfSxcbiAgICAgICAgcGVnJGM3MSA9IFwifnVcIixcbiAgICAgICAgcGVnJGM3MiA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn51XCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+dVxcXCJcIiB9LFxuICAgICAgICBwZWckYzczID0gZnVuY3Rpb24ocykgeyByZXR1cm4gdXJsKHMpOyB9LFxuICAgICAgICBwZWckYzc0ID0geyB0eXBlOiBcIm90aGVyXCIsIGRlc2NyaXB0aW9uOiBcImludGVnZXJcIiB9LFxuICAgICAgICBwZWckYzc1ID0gbnVsbCxcbiAgICAgICAgcGVnJGM3NiA9IC9eWydcIl0vLFxuICAgICAgICBwZWckYzc3ID0geyB0eXBlOiBcImNsYXNzXCIsIHZhbHVlOiBcIlsnXFxcIl1cIiwgZGVzY3JpcHRpb246IFwiWydcXFwiXVwiIH0sXG4gICAgICAgIHBlZyRjNzggPSAvXlswLTldLyxcbiAgICAgICAgcGVnJGM3OSA9IHsgdHlwZTogXCJjbGFzc1wiLCB2YWx1ZTogXCJbMC05XVwiLCBkZXNjcmlwdGlvbjogXCJbMC05XVwiIH0sXG4gICAgICAgIHBlZyRjODAgPSBmdW5jdGlvbihkaWdpdHMpIHsgcmV0dXJuIHBhcnNlSW50KGRpZ2l0cy5qb2luKFwiXCIpLCAxMCk7IH0sXG4gICAgICAgIHBlZyRjODEgPSB7IHR5cGU6IFwib3RoZXJcIiwgZGVzY3JpcHRpb246IFwic3RyaW5nXCIgfSxcbiAgICAgICAgcGVnJGM4MiA9IFwiXFxcIlwiLFxuICAgICAgICBwZWckYzgzID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiXFxcIlwiLCBkZXNjcmlwdGlvbjogXCJcXFwiXFxcXFxcXCJcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM4NCA9IGZ1bmN0aW9uKGNoYXJzKSB7IHJldHVybiBjaGFycy5qb2luKFwiXCIpOyB9LFxuICAgICAgICBwZWckYzg1ID0gXCInXCIsXG4gICAgICAgIHBlZyRjODYgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCInXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCInXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjODcgPSB2b2lkIDAsXG4gICAgICAgIHBlZyRjODggPSAvXltcIlxcXFxdLyxcbiAgICAgICAgcGVnJGM4OSA9IHsgdHlwZTogXCJjbGFzc1wiLCB2YWx1ZTogXCJbXFxcIlxcXFxcXFxcXVwiLCBkZXNjcmlwdGlvbjogXCJbXFxcIlxcXFxcXFxcXVwiIH0sXG4gICAgICAgIHBlZyRjOTAgPSB7IHR5cGU6IFwiYW55XCIsIGRlc2NyaXB0aW9uOiBcImFueSBjaGFyYWN0ZXJcIiB9LFxuICAgICAgICBwZWckYzkxID0gZnVuY3Rpb24oY2hhcikgeyByZXR1cm4gY2hhcjsgfSxcbiAgICAgICAgcGVnJGM5MiA9IFwiXFxcXFwiLFxuICAgICAgICBwZWckYzkzID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiXFxcXFwiLCBkZXNjcmlwdGlvbjogXCJcXFwiXFxcXFxcXFxcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM5NCA9IC9eWydcXFxcXS8sXG4gICAgICAgIHBlZyRjOTUgPSB7IHR5cGU6IFwiY2xhc3NcIiwgdmFsdWU6IFwiWydcXFxcXFxcXF1cIiwgZGVzY3JpcHRpb246IFwiWydcXFxcXFxcXF1cIiB9LFxuICAgICAgICBwZWckYzk2ID0gL15bJ1wiXFxcXF0vLFxuICAgICAgICBwZWckYzk3ID0geyB0eXBlOiBcImNsYXNzXCIsIHZhbHVlOiBcIlsnXFxcIlxcXFxcXFxcXVwiLCBkZXNjcmlwdGlvbjogXCJbJ1xcXCJcXFxcXFxcXF1cIiB9LFxuICAgICAgICBwZWckYzk4ID0gXCJuXCIsXG4gICAgICAgIHBlZyRjOTkgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJuXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJuXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMTAwID0gZnVuY3Rpb24oKSB7IHJldHVybiBcIlxcblwiOyB9LFxuICAgICAgICBwZWckYzEwMSA9IFwiclwiLFxuICAgICAgICBwZWckYzEwMiA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcInJcIiwgZGVzY3JpcHRpb246IFwiXFxcInJcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMxMDMgPSBmdW5jdGlvbigpIHsgcmV0dXJuIFwiXFxyXCI7IH0sXG4gICAgICAgIHBlZyRjMTA0ID0gXCJ0XCIsXG4gICAgICAgIHBlZyRjMTA1ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwidFwiLCBkZXNjcmlwdGlvbjogXCJcXFwidFxcXCJcIiB9LFxuICAgICAgICBwZWckYzEwNiA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gXCJcXHRcIjsgfSxcblxuICAgICAgICBwZWckY3VyclBvcyAgICAgICAgICA9IDAsXG4gICAgICAgIHBlZyRyZXBvcnRlZFBvcyAgICAgID0gMCxcbiAgICAgICAgcGVnJGNhY2hlZFBvcyAgICAgICAgPSAwLFxuICAgICAgICBwZWckY2FjaGVkUG9zRGV0YWlscyA9IHsgbGluZTogMSwgY29sdW1uOiAxLCBzZWVuQ1I6IGZhbHNlIH0sXG4gICAgICAgIHBlZyRtYXhGYWlsUG9zICAgICAgID0gMCxcbiAgICAgICAgcGVnJG1heEZhaWxFeHBlY3RlZCAgPSBbXSxcbiAgICAgICAgcGVnJHNpbGVudEZhaWxzICAgICAgPSAwLFxuXG4gICAgICAgIHBlZyRyZXN1bHQ7XG5cbiAgICBpZiAoXCJzdGFydFJ1bGVcIiBpbiBvcHRpb25zKSB7XG4gICAgICBpZiAoIShvcHRpb25zLnN0YXJ0UnVsZSBpbiBwZWckc3RhcnRSdWxlRnVuY3Rpb25zKSkge1xuICAgICAgICB0aHJvdyBuZXcgRXJyb3IoXCJDYW4ndCBzdGFydCBwYXJzaW5nIGZyb20gcnVsZSBcXFwiXCIgKyBvcHRpb25zLnN0YXJ0UnVsZSArIFwiXFxcIi5cIik7XG4gICAgICB9XG5cbiAgICAgIHBlZyRzdGFydFJ1bGVGdW5jdGlvbiA9IHBlZyRzdGFydFJ1bGVGdW5jdGlvbnNbb3B0aW9ucy5zdGFydFJ1bGVdO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHRleHQoKSB7XG4gICAgICByZXR1cm4gaW5wdXQuc3Vic3RyaW5nKHBlZyRyZXBvcnRlZFBvcywgcGVnJGN1cnJQb3MpO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIG9mZnNldCgpIHtcbiAgICAgIHJldHVybiBwZWckcmVwb3J0ZWRQb3M7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gbGluZSgpIHtcbiAgICAgIHJldHVybiBwZWckY29tcHV0ZVBvc0RldGFpbHMocGVnJHJlcG9ydGVkUG9zKS5saW5lO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIGNvbHVtbigpIHtcbiAgICAgIHJldHVybiBwZWckY29tcHV0ZVBvc0RldGFpbHMocGVnJHJlcG9ydGVkUG9zKS5jb2x1bW47XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gZXhwZWN0ZWQoZGVzY3JpcHRpb24pIHtcbiAgICAgIHRocm93IHBlZyRidWlsZEV4Y2VwdGlvbihcbiAgICAgICAgbnVsbCxcbiAgICAgICAgW3sgdHlwZTogXCJvdGhlclwiLCBkZXNjcmlwdGlvbjogZGVzY3JpcHRpb24gfV0sXG4gICAgICAgIHBlZyRyZXBvcnRlZFBvc1xuICAgICAgKTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBlcnJvcihtZXNzYWdlKSB7XG4gICAgICB0aHJvdyBwZWckYnVpbGRFeGNlcHRpb24obWVzc2FnZSwgbnVsbCwgcGVnJHJlcG9ydGVkUG9zKTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckY29tcHV0ZVBvc0RldGFpbHMocG9zKSB7XG4gICAgICBmdW5jdGlvbiBhZHZhbmNlKGRldGFpbHMsIHN0YXJ0UG9zLCBlbmRQb3MpIHtcbiAgICAgICAgdmFyIHAsIGNoO1xuXG4gICAgICAgIGZvciAocCA9IHN0YXJ0UG9zOyBwIDwgZW5kUG9zOyBwKyspIHtcbiAgICAgICAgICBjaCA9IGlucHV0LmNoYXJBdChwKTtcbiAgICAgICAgICBpZiAoY2ggPT09IFwiXFxuXCIpIHtcbiAgICAgICAgICAgIGlmICghZGV0YWlscy5zZWVuQ1IpIHsgZGV0YWlscy5saW5lKys7IH1cbiAgICAgICAgICAgIGRldGFpbHMuY29sdW1uID0gMTtcbiAgICAgICAgICAgIGRldGFpbHMuc2VlbkNSID0gZmFsc2U7XG4gICAgICAgICAgfSBlbHNlIGlmIChjaCA9PT0gXCJcXHJcIiB8fCBjaCA9PT0gXCJcXHUyMDI4XCIgfHwgY2ggPT09IFwiXFx1MjAyOVwiKSB7XG4gICAgICAgICAgICBkZXRhaWxzLmxpbmUrKztcbiAgICAgICAgICAgIGRldGFpbHMuY29sdW1uID0gMTtcbiAgICAgICAgICAgIGRldGFpbHMuc2VlbkNSID0gdHJ1ZTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgZGV0YWlscy5jb2x1bW4rKztcbiAgICAgICAgICAgIGRldGFpbHMuc2VlbkNSID0gZmFsc2U7XG4gICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICB9XG5cbiAgICAgIGlmIChwZWckY2FjaGVkUG9zICE9PSBwb3MpIHtcbiAgICAgICAgaWYgKHBlZyRjYWNoZWRQb3MgPiBwb3MpIHtcbiAgICAgICAgICBwZWckY2FjaGVkUG9zID0gMDtcbiAgICAgICAgICBwZWckY2FjaGVkUG9zRGV0YWlscyA9IHsgbGluZTogMSwgY29sdW1uOiAxLCBzZWVuQ1I6IGZhbHNlIH07XG4gICAgICAgIH1cbiAgICAgICAgYWR2YW5jZShwZWckY2FjaGVkUG9zRGV0YWlscywgcGVnJGNhY2hlZFBvcywgcG9zKTtcbiAgICAgICAgcGVnJGNhY2hlZFBvcyA9IHBvcztcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHBlZyRjYWNoZWRQb3NEZXRhaWxzO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRmYWlsKGV4cGVjdGVkKSB7XG4gICAgICBpZiAocGVnJGN1cnJQb3MgPCBwZWckbWF4RmFpbFBvcykgeyByZXR1cm47IH1cblxuICAgICAgaWYgKHBlZyRjdXJyUG9zID4gcGVnJG1heEZhaWxQb3MpIHtcbiAgICAgICAgcGVnJG1heEZhaWxQb3MgPSBwZWckY3VyclBvcztcbiAgICAgICAgcGVnJG1heEZhaWxFeHBlY3RlZCA9IFtdO1xuICAgICAgfVxuXG4gICAgICBwZWckbWF4RmFpbEV4cGVjdGVkLnB1c2goZXhwZWN0ZWQpO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRidWlsZEV4Y2VwdGlvbihtZXNzYWdlLCBleHBlY3RlZCwgcG9zKSB7XG4gICAgICBmdW5jdGlvbiBjbGVhbnVwRXhwZWN0ZWQoZXhwZWN0ZWQpIHtcbiAgICAgICAgdmFyIGkgPSAxO1xuXG4gICAgICAgIGV4cGVjdGVkLnNvcnQoZnVuY3Rpb24oYSwgYikge1xuICAgICAgICAgIGlmIChhLmRlc2NyaXB0aW9uIDwgYi5kZXNjcmlwdGlvbikge1xuICAgICAgICAgICAgcmV0dXJuIC0xO1xuICAgICAgICAgIH0gZWxzZSBpZiAoYS5kZXNjcmlwdGlvbiA+IGIuZGVzY3JpcHRpb24pIHtcbiAgICAgICAgICAgIHJldHVybiAxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICByZXR1cm4gMDtcbiAgICAgICAgICB9XG4gICAgICAgIH0pO1xuXG4gICAgICAgIHdoaWxlIChpIDwgZXhwZWN0ZWQubGVuZ3RoKSB7XG4gICAgICAgICAgaWYgKGV4cGVjdGVkW2kgLSAxXSA9PT0gZXhwZWN0ZWRbaV0pIHtcbiAgICAgICAgICAgIGV4cGVjdGVkLnNwbGljZShpLCAxKTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgaSsrO1xuICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICBmdW5jdGlvbiBidWlsZE1lc3NhZ2UoZXhwZWN0ZWQsIGZvdW5kKSB7XG4gICAgICAgIGZ1bmN0aW9uIHN0cmluZ0VzY2FwZShzKSB7XG4gICAgICAgICAgZnVuY3Rpb24gaGV4KGNoKSB7IHJldHVybiBjaC5jaGFyQ29kZUF0KDApLnRvU3RyaW5nKDE2KS50b1VwcGVyQ2FzZSgpOyB9XG5cbiAgICAgICAgICByZXR1cm4gc1xuICAgICAgICAgICAgLnJlcGxhY2UoL1xcXFwvZywgICAnXFxcXFxcXFwnKVxuICAgICAgICAgICAgLnJlcGxhY2UoL1wiL2csICAgICdcXFxcXCInKVxuICAgICAgICAgICAgLnJlcGxhY2UoL1xceDA4L2csICdcXFxcYicpXG4gICAgICAgICAgICAucmVwbGFjZSgvXFx0L2csICAgJ1xcXFx0JylcbiAgICAgICAgICAgIC5yZXBsYWNlKC9cXG4vZywgICAnXFxcXG4nKVxuICAgICAgICAgICAgLnJlcGxhY2UoL1xcZi9nLCAgICdcXFxcZicpXG4gICAgICAgICAgICAucmVwbGFjZSgvXFxyL2csICAgJ1xcXFxyJylcbiAgICAgICAgICAgIC5yZXBsYWNlKC9bXFx4MDAtXFx4MDdcXHgwQlxceDBFXFx4MEZdL2csIGZ1bmN0aW9uKGNoKSB7IHJldHVybiAnXFxcXHgwJyArIGhleChjaCk7IH0pXG4gICAgICAgICAgICAucmVwbGFjZSgvW1xceDEwLVxceDFGXFx4ODAtXFx4RkZdL2csICAgIGZ1bmN0aW9uKGNoKSB7IHJldHVybiAnXFxcXHgnICArIGhleChjaCk7IH0pXG4gICAgICAgICAgICAucmVwbGFjZSgvW1xcdTAxODAtXFx1MEZGRl0vZywgICAgICAgICBmdW5jdGlvbihjaCkgeyByZXR1cm4gJ1xcXFx1MCcgKyBoZXgoY2gpOyB9KVxuICAgICAgICAgICAgLnJlcGxhY2UoL1tcXHUxMDgwLVxcdUZGRkZdL2csICAgICAgICAgZnVuY3Rpb24oY2gpIHsgcmV0dXJuICdcXFxcdScgICsgaGV4KGNoKTsgfSk7XG4gICAgICAgIH1cblxuICAgICAgICB2YXIgZXhwZWN0ZWREZXNjcyA9IG5ldyBBcnJheShleHBlY3RlZC5sZW5ndGgpLFxuICAgICAgICAgICAgZXhwZWN0ZWREZXNjLCBmb3VuZERlc2MsIGk7XG5cbiAgICAgICAgZm9yIChpID0gMDsgaSA8IGV4cGVjdGVkLmxlbmd0aDsgaSsrKSB7XG4gICAgICAgICAgZXhwZWN0ZWREZXNjc1tpXSA9IGV4cGVjdGVkW2ldLmRlc2NyaXB0aW9uO1xuICAgICAgICB9XG5cbiAgICAgICAgZXhwZWN0ZWREZXNjID0gZXhwZWN0ZWQubGVuZ3RoID4gMVxuICAgICAgICAgID8gZXhwZWN0ZWREZXNjcy5zbGljZSgwLCAtMSkuam9pbihcIiwgXCIpXG4gICAgICAgICAgICAgICsgXCIgb3IgXCJcbiAgICAgICAgICAgICAgKyBleHBlY3RlZERlc2NzW2V4cGVjdGVkLmxlbmd0aCAtIDFdXG4gICAgICAgICAgOiBleHBlY3RlZERlc2NzWzBdO1xuXG4gICAgICAgIGZvdW5kRGVzYyA9IGZvdW5kID8gXCJcXFwiXCIgKyBzdHJpbmdFc2NhcGUoZm91bmQpICsgXCJcXFwiXCIgOiBcImVuZCBvZiBpbnB1dFwiO1xuXG4gICAgICAgIHJldHVybiBcIkV4cGVjdGVkIFwiICsgZXhwZWN0ZWREZXNjICsgXCIgYnV0IFwiICsgZm91bmREZXNjICsgXCIgZm91bmQuXCI7XG4gICAgICB9XG5cbiAgICAgIHZhciBwb3NEZXRhaWxzID0gcGVnJGNvbXB1dGVQb3NEZXRhaWxzKHBvcyksXG4gICAgICAgICAgZm91bmQgICAgICA9IHBvcyA8IGlucHV0Lmxlbmd0aCA/IGlucHV0LmNoYXJBdChwb3MpIDogbnVsbDtcblxuICAgICAgaWYgKGV4cGVjdGVkICE9PSBudWxsKSB7XG4gICAgICAgIGNsZWFudXBFeHBlY3RlZChleHBlY3RlZCk7XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBuZXcgU3ludGF4RXJyb3IoXG4gICAgICAgIG1lc3NhZ2UgIT09IG51bGwgPyBtZXNzYWdlIDogYnVpbGRNZXNzYWdlKGV4cGVjdGVkLCBmb3VuZCksXG4gICAgICAgIGV4cGVjdGVkLFxuICAgICAgICBmb3VuZCxcbiAgICAgICAgcG9zLFxuICAgICAgICBwb3NEZXRhaWxzLmxpbmUsXG4gICAgICAgIHBvc0RldGFpbHMuY29sdW1uXG4gICAgICApO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZXN0YXJ0KCkge1xuICAgICAgdmFyIHMwLCBzMSwgczIsIHMzO1xuXG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBzMSA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBwZWckcGFyc2VPckV4cHIoKTtcbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczMgPSBwZWckcGFyc2VfXygpO1xuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICBzMSA9IHBlZyRjMihzMik7XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIHMxID0gW107XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgIHMxID0gcGVnJGM0KCk7XG4gICAgICAgIH1cbiAgICAgICAgczAgPSBzMTtcbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzApOyB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2V3cygpIHtcbiAgICAgIHZhciBzMCwgczE7XG5cbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgaWYgKHBlZyRjNi50ZXN0KGlucHV0LmNoYXJBdChwZWckY3VyclBvcykpKSB7XG4gICAgICAgIHMwID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMwID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzcpOyB9XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM1KTsgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlY2MoKSB7XG4gICAgICB2YXIgczAsIHMxO1xuXG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIGlmIChwZWckYzkudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICBzMCA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMCA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMxMCk7IH1cbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzgpOyB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VfXygpIHtcbiAgICAgIHZhciBzMCwgczE7XG5cbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgczAgPSBbXTtcbiAgICAgIHMxID0gcGVnJHBhcnNld3MoKTtcbiAgICAgIHdoaWxlIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMC5wdXNoKHMxKTtcbiAgICAgICAgczEgPSBwZWckcGFyc2V3cygpO1xuICAgICAgfVxuICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMTEpOyB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VPckV4cHIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczMsIHM0LCBzNTtcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIHMxID0gcGVnJHBhcnNlQW5kRXhwcigpO1xuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAxMjQpIHtcbiAgICAgICAgICAgIHMzID0gcGVnJGMxMjtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMzID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMxMyk7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzNCA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICAgICAgICBpZiAoczQgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczUgPSBwZWckcGFyc2VPckV4cHIoKTtcbiAgICAgICAgICAgICAgaWYgKHM1ICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckYzE0KHMxLCBzNSk7XG4gICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRwYXJzZUFuZEV4cHIoKTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZUFuZEV4cHIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczMsIHM0LCBzNTtcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIHMxID0gcGVnJHBhcnNlTm90RXhwcigpO1xuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAzOCkge1xuICAgICAgICAgICAgczMgPSBwZWckYzE1O1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczMgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzE2KTsgfVxuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHM0ID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgICAgIGlmIChzNCAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBzNSA9IHBlZyRwYXJzZUFuZEV4cHIoKTtcbiAgICAgICAgICAgICAgaWYgKHM1ICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckYzE3KHMxLCBzNSk7XG4gICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBzMSA9IHBlZyRwYXJzZU5vdEV4cHIoKTtcbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczMgPSBwZWckcGFyc2VBbmRFeHByKCk7XG4gICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGMxNyhzMSwgczMpO1xuICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMCA9IHBlZyRwYXJzZU5vdEV4cHIoKTtcbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlTm90RXhwcigpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyLCBzMztcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMzMpIHtcbiAgICAgICAgczEgPSBwZWckYzE4O1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMTkpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBwZWckcGFyc2VfXygpO1xuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZU5vdEV4cHIoKTtcbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzIwKHMzKTtcbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckcGFyc2VCaW5kaW5nRXhwcigpO1xuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlQmluZGluZ0V4cHIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczMsIHM0LCBzNTtcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gNDApIHtcbiAgICAgICAgczEgPSBwZWckYzIxO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMjIpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBwZWckcGFyc2VfXygpO1xuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZU9yRXhwcigpO1xuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczQgPSBwZWckcGFyc2VfXygpO1xuICAgICAgICAgICAgaWYgKHM0ICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gNDEpIHtcbiAgICAgICAgICAgICAgICBzNSA9IHBlZyRjMjM7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBzNSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzI0KTsgfVxuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIGlmIChzNSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJGMyNShzMyk7XG4gICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRwYXJzZUV4cHIoKTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZUV4cHIoKSB7XG4gICAgICB2YXIgczA7XG5cbiAgICAgIHMwID0gcGVnJHBhcnNlTnVsbGFyeUV4cHIoKTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRwYXJzZVVuYXJ5RXhwcigpO1xuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlTnVsbGFyeUV4cHIoKSB7XG4gICAgICB2YXIgczAsIHMxO1xuXG4gICAgICBzMCA9IHBlZyRwYXJzZUJvb2xlYW5MaXRlcmFsKCk7XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjMjYpIHtcbiAgICAgICAgICBzMSA9IHBlZyRjMjY7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzI3KTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgIHMxID0gcGVnJGMyOCgpO1xuICAgICAgICB9XG4gICAgICAgIHMwID0gczE7XG4gICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjMjkpIHtcbiAgICAgICAgICAgIHMxID0gcGVnJGMyOTtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMzMCk7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGMzMSgpO1xuICAgICAgICAgIH1cbiAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzMyKSB7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGMzMjtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzMzKTsgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjMzQoKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjMzUpIHtcbiAgICAgICAgICAgICAgICBzMSA9IHBlZyRjMzU7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzM2KTsgfVxuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJGMzNygpO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VCb29sZWFuTGl0ZXJhbCgpIHtcbiAgICAgIHZhciBzMCwgczE7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCA0KSA9PT0gcGVnJGMzOCkge1xuICAgICAgICBzMSA9IHBlZyRjMzg7XG4gICAgICAgIHBlZyRjdXJyUG9zICs9IDQ7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMzOSk7IH1cbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgczEgPSBwZWckYzQwKCk7XG4gICAgICB9XG4gICAgICBzMCA9IHMxO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDUpID09PSBwZWckYzQxKSB7XG4gICAgICAgICAgczEgPSBwZWckYzQxO1xuICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDU7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM0Mik7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICBzMSA9IHBlZyRjNDMoKTtcbiAgICAgICAgfVxuICAgICAgICBzMCA9IHMxO1xuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlVW5hcnlFeHByKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczIsIHMzO1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjNDQpIHtcbiAgICAgICAgczEgPSBwZWckYzQ0O1xuICAgICAgICBwZWckY3VyclBvcyArPSAyO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNDUpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBbXTtcbiAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZUludGVnZXJMaXRlcmFsKCk7XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGM0NihzMyk7XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzQ3KSB7XG4gICAgICAgICAgczEgPSBwZWckYzQ3O1xuICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM0OCk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczEgPSBwZWckYzQ5KHMzKTtcbiAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGM1MCkge1xuICAgICAgICAgICAgczEgPSBwZWckYzUwO1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzUxKTsgfVxuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckYzUyKHMzKTtcbiAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDMpID09PSBwZWckYzUzKSB7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGM1MztcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMztcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzU0KTsgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM1NShzMyk7XG4gICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDMpID09PSBwZWckYzU2KSB7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckYzU2O1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDM7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM1Nyk7IH1cbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzU4KHMzKTtcbiAgICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGM1OSkge1xuICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzU5O1xuICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzYwKTsgfVxuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzYxKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzYyKSB7XG4gICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM2MjtcbiAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzYzKTsgfVxuICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM2NChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDMpID09PSBwZWckYzY1KSB7XG4gICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzY1O1xuICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDM7XG4gICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM2Nik7IH1cbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzY3KHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAzKSA9PT0gcGVnJGM2OCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzY4O1xuICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMztcbiAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzY5KTsgfVxuICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzcwKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzcxKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM3MTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzcyKTsgfVxuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM3MyhzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNzMoczEpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VJbnRlZ2VyTGl0ZXJhbCgpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyLCBzMztcblxuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgaWYgKHBlZyRjNzYudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICBzMSA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM3Nyk7IH1cbiAgICAgIH1cbiAgICAgIGlmIChzMSA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRjNzU7XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBbXTtcbiAgICAgICAgaWYgKHBlZyRjNzgudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICAgIHMzID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMzID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNzkpOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgIGlmIChwZWckYzc4LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgICAgICAgczMgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgczMgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNzkpOyB9XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIGlmIChwZWckYzc2LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgICAgIHMzID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMzID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM3Nyk7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMzID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRjNzU7XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICBzMSA9IHBlZyRjODAoczIpO1xuICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzc0KTsgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyLCBzMztcblxuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAzNCkge1xuICAgICAgICBzMSA9IHBlZyRjODI7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM4Myk7IH1cbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMiA9IFtdO1xuICAgICAgICBzMyA9IHBlZyRwYXJzZURvdWJsZVN0cmluZ0NoYXIoKTtcbiAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgczMgPSBwZWckcGFyc2VEb3VibGVTdHJpbmdDaGFyKCk7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAzNCkge1xuICAgICAgICAgICAgczMgPSBwZWckYzgyO1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczMgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzgzKTsgfVxuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzg0KHMyKTtcbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAzOSkge1xuICAgICAgICAgIHMxID0gcGVnJGM4NTtcbiAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjODYpOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZVNpbmdsZVN0cmluZ0NoYXIoKTtcbiAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTaW5nbGVTdHJpbmdDaGFyKCk7XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAzOSkge1xuICAgICAgICAgICAgICBzMyA9IHBlZyRjODU7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBzMyA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM4Nik7IH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczEgPSBwZWckYzg0KHMyKTtcbiAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICBzMSA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgICAgIHMyID0gcGVnJHBhcnNlY2MoKTtcbiAgICAgICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgICAgICBpZiAoczIgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMxID0gcGVnJGM4NztcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMTtcbiAgICAgICAgICAgIHMxID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVVucXVvdGVkU3RyaW5nQ2hhcigpO1xuICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlVW5xdW90ZWRTdHJpbmdDaGFyKCk7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjODQoczIpO1xuICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzgxKTsgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlRG91YmxlU3RyaW5nQ2hhcigpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyO1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgczEgPSBwZWckY3VyclBvcztcbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgaWYgKHBlZyRjODgudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICBzMiA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMiA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM4OSk7IH1cbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMyID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJGM4NztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczE7XG4gICAgICAgIHMxID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIGlmIChpbnB1dC5sZW5ndGggPiBwZWckY3VyclBvcykge1xuICAgICAgICAgIHMyID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMyID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOTApOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgczEgPSBwZWckYzkxKHMyKTtcbiAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gOTIpIHtcbiAgICAgICAgICBzMSA9IHBlZyRjOTI7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzkzKTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMyID0gcGVnJHBhcnNlRXNjYXBlU2VxdWVuY2UoKTtcbiAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzkxKHMyKTtcbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlU2luZ2xlU3RyaW5nQ2hhcigpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyO1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgczEgPSBwZWckY3VyclBvcztcbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgaWYgKHBlZyRjOTQudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICBzMiA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMiA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM5NSk7IH1cbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMyID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJGM4NztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczE7XG4gICAgICAgIHMxID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIGlmIChpbnB1dC5sZW5ndGggPiBwZWckY3VyclBvcykge1xuICAgICAgICAgIHMyID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMyID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOTApOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgczEgPSBwZWckYzkxKHMyKTtcbiAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gOTIpIHtcbiAgICAgICAgICBzMSA9IHBlZyRjOTI7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzkzKTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMyID0gcGVnJHBhcnNlRXNjYXBlU2VxdWVuY2UoKTtcbiAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzkxKHMyKTtcbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlVW5xdW90ZWRTdHJpbmdDaGFyKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczI7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBzMSA9IHBlZyRjdXJyUG9zO1xuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBzMiA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMiA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRjODc7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMxO1xuICAgICAgICBzMSA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBpZiAoaW5wdXQubGVuZ3RoID4gcGVnJGN1cnJQb3MpIHtcbiAgICAgICAgICBzMiA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMiA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzkwKTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgIHMxID0gcGVnJGM5MShzMik7XG4gICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZUVzY2FwZVNlcXVlbmNlKCkge1xuICAgICAgdmFyIHMwLCBzMTtcblxuICAgICAgaWYgKHBlZyRjOTYudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICBzMCA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMCA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM5Nyk7IH1cbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDExMCkge1xuICAgICAgICAgIHMxID0gcGVnJGM5ODtcbiAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOTkpOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgczEgPSBwZWckYzEwMCgpO1xuICAgICAgICB9XG4gICAgICAgIHMwID0gczE7XG4gICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAxMTQpIHtcbiAgICAgICAgICAgIHMxID0gcGVnJGMxMDE7XG4gICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMTAyKTsgfVxuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzEwMygpO1xuICAgICAgICAgIH1cbiAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMTE2KSB7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGMxMDQ7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMxMDUpOyB9XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGMxMDYoKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cblxyXG4gICAgdmFyIGZsb3d1dGlscyA9IHJlcXVpcmUoXCIuLi9mbG93L3V0aWxzLmpzXCIpO1xyXG5cclxuICAgIGZ1bmN0aW9uIG9yKGZpcnN0LCBzZWNvbmQpIHtcclxuICAgICAgICAvLyBBZGQgZXhwbGljaXQgZnVuY3Rpb24gbmFtZXMgdG8gZWFzZSBkZWJ1Z2dpbmcuXHJcbiAgICAgICAgZnVuY3Rpb24gb3JGaWx0ZXIoKSB7XHJcbiAgICAgICAgICAgIHJldHVybiBmaXJzdC5hcHBseSh0aGlzLCBhcmd1bWVudHMpIHx8IHNlY29uZC5hcHBseSh0aGlzLCBhcmd1bWVudHMpO1xyXG4gICAgICAgIH1cclxuICAgICAgICBvckZpbHRlci5kZXNjID0gZmlyc3QuZGVzYyArIFwiIG9yIFwiICsgc2Vjb25kLmRlc2M7XHJcbiAgICAgICAgcmV0dXJuIG9yRmlsdGVyO1xyXG4gICAgfVxyXG4gICAgZnVuY3Rpb24gYW5kKGZpcnN0LCBzZWNvbmQpIHtcclxuICAgICAgICBmdW5jdGlvbiBhbmRGaWx0ZXIoKSB7XHJcbiAgICAgICAgICAgIHJldHVybiBmaXJzdC5hcHBseSh0aGlzLCBhcmd1bWVudHMpICYmIHNlY29uZC5hcHBseSh0aGlzLCBhcmd1bWVudHMpO1xyXG4gICAgICAgIH1cclxuICAgICAgICBhbmRGaWx0ZXIuZGVzYyA9IGZpcnN0LmRlc2MgKyBcIiBhbmQgXCIgKyBzZWNvbmQuZGVzYztcclxuICAgICAgICByZXR1cm4gYW5kRmlsdGVyO1xyXG4gICAgfVxyXG4gICAgZnVuY3Rpb24gbm90KGV4cHIpIHtcclxuICAgICAgICBmdW5jdGlvbiBub3RGaWx0ZXIoKSB7XHJcbiAgICAgICAgICAgIHJldHVybiAhZXhwci5hcHBseSh0aGlzLCBhcmd1bWVudHMpO1xyXG4gICAgICAgIH1cclxuICAgICAgICBub3RGaWx0ZXIuZGVzYyA9IFwibm90IFwiICsgZXhwci5kZXNjO1xyXG4gICAgICAgIHJldHVybiBub3RGaWx0ZXI7XHJcbiAgICB9XHJcbiAgICBmdW5jdGlvbiBiaW5kaW5nKGV4cHIpIHtcclxuICAgICAgICBmdW5jdGlvbiBiaW5kaW5nRmlsdGVyKCkge1xyXG4gICAgICAgICAgICByZXR1cm4gZXhwci5hcHBseSh0aGlzLCBhcmd1bWVudHMpO1xyXG4gICAgICAgIH1cclxuICAgICAgICBiaW5kaW5nRmlsdGVyLmRlc2MgPSBcIihcIiArIGV4cHIuZGVzYyArIFwiKVwiO1xyXG4gICAgICAgIHJldHVybiBiaW5kaW5nRmlsdGVyO1xyXG4gICAgfVxyXG4gICAgZnVuY3Rpb24gdHJ1ZUZpbHRlcihmbG93KSB7XHJcbiAgICAgICAgcmV0dXJuIHRydWU7XHJcbiAgICB9XHJcbiAgICB0cnVlRmlsdGVyLmRlc2MgPSBcInRydWVcIjtcclxuICAgIGZ1bmN0aW9uIGZhbHNlRmlsdGVyKGZsb3cpIHtcclxuICAgICAgICByZXR1cm4gZmFsc2U7XHJcbiAgICB9XHJcbiAgICBmYWxzZUZpbHRlci5kZXNjID0gXCJmYWxzZVwiO1xyXG5cclxuICAgIHZhciBBU1NFVF9UWVBFUyA9IFtcclxuICAgICAgICBuZXcgUmVnRXhwKFwidGV4dC9qYXZhc2NyaXB0XCIpLFxyXG4gICAgICAgIG5ldyBSZWdFeHAoXCJhcHBsaWNhdGlvbi94LWphdmFzY3JpcHRcIiksXHJcbiAgICAgICAgbmV3IFJlZ0V4cChcImFwcGxpY2F0aW9uL2phdmFzY3JpcHRcIiksXHJcbiAgICAgICAgbmV3IFJlZ0V4cChcInRleHQvY3NzXCIpLFxyXG4gICAgICAgIG5ldyBSZWdFeHAoXCJpbWFnZS8uKlwiKSxcclxuICAgICAgICBuZXcgUmVnRXhwKFwiYXBwbGljYXRpb24veC1zaG9ja3dhdmUtZmxhc2hcIilcclxuICAgIF07XHJcbiAgICBmdW5jdGlvbiBhc3NldEZpbHRlcihmbG93KSB7XHJcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UpIHtcclxuICAgICAgICAgICAgdmFyIGN0ID0gZmxvd3V0aWxzLlJlc3BvbnNlVXRpbHMuZ2V0Q29udGVudFR5cGUoZmxvdy5yZXNwb25zZSk7XHJcbiAgICAgICAgICAgIHZhciBpID0gQVNTRVRfVFlQRVMubGVuZ3RoO1xyXG4gICAgICAgICAgICB3aGlsZSAoaS0tKSB7XHJcbiAgICAgICAgICAgICAgICBpZiAoQVNTRVRfVFlQRVNbaV0udGVzdChjdCkpIHtcclxuICAgICAgICAgICAgICAgICAgICByZXR1cm4gdHJ1ZTtcclxuICAgICAgICAgICAgICAgIH1cclxuICAgICAgICAgICAgfVxyXG4gICAgICAgIH1cclxuICAgICAgICByZXR1cm4gZmFsc2U7XHJcbiAgICB9XHJcbiAgICBhc3NldEZpbHRlci5kZXNjID0gXCJpcyBhc3NldFwiO1xyXG4gICAgZnVuY3Rpb24gcmVzcG9uc2VDb2RlKGNvZGUpe1xyXG4gICAgICAgIGZ1bmN0aW9uIHJlc3BvbnNlQ29kZUZpbHRlcihmbG93KXtcclxuICAgICAgICAgICAgcmV0dXJuIGZsb3cucmVzcG9uc2UgJiYgZmxvdy5yZXNwb25zZS5jb2RlID09PSBjb2RlO1xyXG4gICAgICAgIH1cclxuICAgICAgICByZXNwb25zZUNvZGVGaWx0ZXIuZGVzYyA9IFwicmVzcC4gY29kZSBpcyBcIiArIGNvZGU7XHJcbiAgICAgICAgcmV0dXJuIHJlc3BvbnNlQ29kZUZpbHRlcjtcclxuICAgIH1cclxuICAgIGZ1bmN0aW9uIGRvbWFpbihyZWdleCl7XHJcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XHJcbiAgICAgICAgZnVuY3Rpb24gZG9tYWluRmlsdGVyKGZsb3cpe1xyXG4gICAgICAgICAgICByZXR1cm4gZmxvdy5yZXF1ZXN0ICYmIHJlZ2V4LnRlc3QoZmxvdy5yZXF1ZXN0Lmhvc3QpO1xyXG4gICAgICAgIH1cclxuICAgICAgICBkb21haW5GaWx0ZXIuZGVzYyA9IFwiZG9tYWluIG1hdGNoZXMgXCIgKyByZWdleDtcclxuICAgICAgICByZXR1cm4gZG9tYWluRmlsdGVyO1xyXG4gICAgfVxyXG4gICAgZnVuY3Rpb24gZXJyb3JGaWx0ZXIoZmxvdyl7XHJcbiAgICAgICAgcmV0dXJuICEhZmxvdy5lcnJvcjtcclxuICAgIH1cclxuICAgIGVycm9yRmlsdGVyLmRlc2MgPSBcImhhcyBlcnJvclwiO1xyXG4gICAgZnVuY3Rpb24gaGVhZGVyKHJlZ2V4KXtcclxuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcclxuICAgICAgICBmdW5jdGlvbiBoZWFkZXJGaWx0ZXIoZmxvdyl7XHJcbiAgICAgICAgICAgIHJldHVybiAoXHJcbiAgICAgICAgICAgICAgICAoZmxvdy5yZXF1ZXN0ICYmIGZsb3d1dGlscy5SZXF1ZXN0VXRpbHMubWF0Y2hfaGVhZGVyKGZsb3cucmVxdWVzdCwgcmVnZXgpKVxyXG4gICAgICAgICAgICAgICAgfHxcclxuICAgICAgICAgICAgICAgIChmbG93LnJlc3BvbnNlICYmIGZsb3d1dGlscy5SZXNwb25zZVV0aWxzLm1hdGNoX2hlYWRlcihmbG93LnJlc3BvbnNlLCByZWdleCkpXHJcbiAgICAgICAgICAgICk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIGhlYWRlckZpbHRlci5kZXNjID0gXCJoZWFkZXIgbWF0Y2hlcyBcIiArIHJlZ2V4O1xyXG4gICAgICAgIHJldHVybiBoZWFkZXJGaWx0ZXI7XHJcbiAgICB9XHJcbiAgICBmdW5jdGlvbiByZXF1ZXN0SGVhZGVyKHJlZ2V4KXtcclxuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcclxuICAgICAgICBmdW5jdGlvbiByZXF1ZXN0SGVhZGVyRmlsdGVyKGZsb3cpe1xyXG4gICAgICAgICAgICByZXR1cm4gKGZsb3cucmVxdWVzdCAmJiBmbG93dXRpbHMuUmVxdWVzdFV0aWxzLm1hdGNoX2hlYWRlcihmbG93LnJlcXVlc3QsIHJlZ2V4KSk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHJlcXVlc3RIZWFkZXJGaWx0ZXIuZGVzYyA9IFwicmVxLiBoZWFkZXIgbWF0Y2hlcyBcIiArIHJlZ2V4O1xyXG4gICAgICAgIHJldHVybiByZXF1ZXN0SGVhZGVyRmlsdGVyO1xyXG4gICAgfVxyXG4gICAgZnVuY3Rpb24gcmVzcG9uc2VIZWFkZXIocmVnZXgpe1xyXG4gICAgICAgIHJlZ2V4ID0gbmV3IFJlZ0V4cChyZWdleCwgXCJpXCIpO1xyXG4gICAgICAgIGZ1bmN0aW9uIHJlc3BvbnNlSGVhZGVyRmlsdGVyKGZsb3cpe1xyXG4gICAgICAgICAgICByZXR1cm4gKGZsb3cucmVzcG9uc2UgJiYgZmxvd3V0aWxzLlJlc3BvbnNlVXRpbHMubWF0Y2hfaGVhZGVyKGZsb3cucmVzcG9uc2UsIHJlZ2V4KSk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHJlc3BvbnNlSGVhZGVyRmlsdGVyLmRlc2MgPSBcInJlc3AuIGhlYWRlciBtYXRjaGVzIFwiICsgcmVnZXg7XHJcbiAgICAgICAgcmV0dXJuIHJlc3BvbnNlSGVhZGVyRmlsdGVyO1xyXG4gICAgfVxyXG4gICAgZnVuY3Rpb24gbWV0aG9kKHJlZ2V4KXtcclxuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcclxuICAgICAgICBmdW5jdGlvbiBtZXRob2RGaWx0ZXIoZmxvdyl7XHJcbiAgICAgICAgICAgIHJldHVybiBmbG93LnJlcXVlc3QgJiYgcmVnZXgudGVzdChmbG93LnJlcXVlc3QubWV0aG9kKTtcclxuICAgICAgICB9XHJcbiAgICAgICAgbWV0aG9kRmlsdGVyLmRlc2MgPSBcIm1ldGhvZCBtYXRjaGVzIFwiICsgcmVnZXg7XHJcbiAgICAgICAgcmV0dXJuIG1ldGhvZEZpbHRlcjtcclxuICAgIH1cclxuICAgIGZ1bmN0aW9uIG5vUmVzcG9uc2VGaWx0ZXIoZmxvdyl7XHJcbiAgICAgICAgcmV0dXJuIGZsb3cucmVxdWVzdCAmJiAhZmxvdy5yZXNwb25zZTtcclxuICAgIH1cclxuICAgIG5vUmVzcG9uc2VGaWx0ZXIuZGVzYyA9IFwiaGFzIG5vIHJlc3BvbnNlXCI7XHJcbiAgICBmdW5jdGlvbiByZXNwb25zZUZpbHRlcihmbG93KXtcclxuICAgICAgICByZXR1cm4gISFmbG93LnJlc3BvbnNlO1xyXG4gICAgfVxyXG4gICAgcmVzcG9uc2VGaWx0ZXIuZGVzYyA9IFwiaGFzIHJlc3BvbnNlXCI7XHJcblxyXG4gICAgZnVuY3Rpb24gY29udGVudFR5cGUocmVnZXgpe1xyXG4gICAgICAgIHJlZ2V4ID0gbmV3IFJlZ0V4cChyZWdleCwgXCJpXCIpO1xyXG4gICAgICAgIGZ1bmN0aW9uIGNvbnRlbnRUeXBlRmlsdGVyKGZsb3cpe1xyXG4gICAgICAgICAgICByZXR1cm4gKFxyXG4gICAgICAgICAgICAgICAgKGZsb3cucmVxdWVzdCAmJiByZWdleC50ZXN0KGZsb3d1dGlscy5SZXF1ZXN0VXRpbHMuZ2V0Q29udGVudFR5cGUoZmxvdy5yZXF1ZXN0KSkpXHJcbiAgICAgICAgICAgICAgICB8fFxyXG4gICAgICAgICAgICAgICAgKGZsb3cucmVzcG9uc2UgJiYgcmVnZXgudGVzdChmbG93dXRpbHMuUmVzcG9uc2VVdGlscy5nZXRDb250ZW50VHlwZShmbG93LnJlc3BvbnNlKSkpXHJcbiAgICAgICAgICAgICk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIGNvbnRlbnRUeXBlRmlsdGVyLmRlc2MgPSBcImNvbnRlbnQgdHlwZSBtYXRjaGVzIFwiICsgcmVnZXg7XHJcbiAgICAgICAgcmV0dXJuIGNvbnRlbnRUeXBlRmlsdGVyO1xyXG4gICAgfVxyXG4gICAgZnVuY3Rpb24gcmVxdWVzdENvbnRlbnRUeXBlKHJlZ2V4KXtcclxuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcclxuICAgICAgICBmdW5jdGlvbiByZXF1ZXN0Q29udGVudFR5cGVGaWx0ZXIoZmxvdyl7XHJcbiAgICAgICAgICAgIHJldHVybiBmbG93LnJlcXVlc3QgJiYgcmVnZXgudGVzdChmbG93dXRpbHMuUmVxdWVzdFV0aWxzLmdldENvbnRlbnRUeXBlKGZsb3cucmVxdWVzdCkpO1xyXG4gICAgICAgIH1cclxuICAgICAgICByZXF1ZXN0Q29udGVudFR5cGVGaWx0ZXIuZGVzYyA9IFwicmVxLiBjb250ZW50IHR5cGUgbWF0Y2hlcyBcIiArIHJlZ2V4O1xyXG4gICAgICAgIHJldHVybiByZXF1ZXN0Q29udGVudFR5cGVGaWx0ZXI7XHJcbiAgICB9XHJcbiAgICBmdW5jdGlvbiByZXNwb25zZUNvbnRlbnRUeXBlKHJlZ2V4KXtcclxuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcclxuICAgICAgICBmdW5jdGlvbiByZXNwb25zZUNvbnRlbnRUeXBlRmlsdGVyKGZsb3cpe1xyXG4gICAgICAgICAgICByZXR1cm4gZmxvdy5yZXNwb25zZSAmJiByZWdleC50ZXN0KGZsb3d1dGlscy5SZXNwb25zZVV0aWxzLmdldENvbnRlbnRUeXBlKGZsb3cucmVzcG9uc2UpKTtcclxuICAgICAgICB9XHJcbiAgICAgICAgcmVzcG9uc2VDb250ZW50VHlwZUZpbHRlci5kZXNjID0gXCJyZXNwLiBjb250ZW50IHR5cGUgbWF0Y2hlcyBcIiArIHJlZ2V4O1xyXG4gICAgICAgIHJldHVybiByZXNwb25zZUNvbnRlbnRUeXBlRmlsdGVyO1xyXG4gICAgfVxyXG4gICAgZnVuY3Rpb24gdXJsKHJlZ2V4KXtcclxuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcclxuICAgICAgICBmdW5jdGlvbiB1cmxGaWx0ZXIoZmxvdyl7XHJcbiAgICAgICAgICAgIHJldHVybiBmbG93LnJlcXVlc3QgJiYgcmVnZXgudGVzdChmbG93dXRpbHMuUmVxdWVzdFV0aWxzLnByZXR0eV91cmwoZmxvdy5yZXF1ZXN0KSk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHVybEZpbHRlci5kZXNjID0gXCJ1cmwgbWF0Y2hlcyBcIiArIHJlZ2V4O1xyXG4gICAgICAgIHJldHVybiB1cmxGaWx0ZXI7XHJcbiAgICB9XHJcblxuXG4gICAgcGVnJHJlc3VsdCA9IHBlZyRzdGFydFJ1bGVGdW5jdGlvbigpO1xuXG4gICAgaWYgKHBlZyRyZXN1bHQgIT09IHBlZyRGQUlMRUQgJiYgcGVnJGN1cnJQb3MgPT09IGlucHV0Lmxlbmd0aCkge1xuICAgICAgcmV0dXJuIHBlZyRyZXN1bHQ7XG4gICAgfSBlbHNlIHtcbiAgICAgIGlmIChwZWckcmVzdWx0ICE9PSBwZWckRkFJTEVEICYmIHBlZyRjdXJyUG9zIDwgaW5wdXQubGVuZ3RoKSB7XG4gICAgICAgIHBlZyRmYWlsKHsgdHlwZTogXCJlbmRcIiwgZGVzY3JpcHRpb246IFwiZW5kIG9mIGlucHV0XCIgfSk7XG4gICAgICB9XG5cbiAgICAgIHRocm93IHBlZyRidWlsZEV4Y2VwdGlvbihudWxsLCBwZWckbWF4RmFpbEV4cGVjdGVkLCBwZWckbWF4RmFpbFBvcyk7XG4gICAgfVxuICB9XG5cbiAgcmV0dXJuIHtcbiAgICBTeW50YXhFcnJvcjogU3ludGF4RXJyb3IsXG4gICAgcGFyc2U6ICAgICAgIHBhcnNlXG4gIH07XG59KSgpOyIsInZhciBfID0gcmVxdWlyZShcImxvZGFzaFwiKTtcclxuXHJcbnZhciBfTWVzc2FnZVV0aWxzID0ge1xyXG4gICAgZ2V0Q29udGVudFR5cGU6IGZ1bmN0aW9uIChtZXNzYWdlKSB7XHJcbiAgICAgICAgcmV0dXJuIHRoaXMuZ2V0X2ZpcnN0X2hlYWRlcihtZXNzYWdlLCAvXkNvbnRlbnQtVHlwZSQvaSk7XHJcbiAgICB9LFxyXG4gICAgZ2V0X2ZpcnN0X2hlYWRlcjogZnVuY3Rpb24gKG1lc3NhZ2UsIHJlZ2V4KSB7XHJcbiAgICAgICAgLy9GSVhNRTogQ2FjaGUgSW52YWxpZGF0aW9uLlxyXG4gICAgICAgIGlmICghbWVzc2FnZS5faGVhZGVyTG9va3VwcylcclxuICAgICAgICAgICAgT2JqZWN0LmRlZmluZVByb3BlcnR5KG1lc3NhZ2UsIFwiX2hlYWRlckxvb2t1cHNcIiwge1xyXG4gICAgICAgICAgICAgICAgdmFsdWU6IHt9LFxyXG4gICAgICAgICAgICAgICAgY29uZmlndXJhYmxlOiBmYWxzZSxcclxuICAgICAgICAgICAgICAgIGVudW1lcmFibGU6IGZhbHNlLFxyXG4gICAgICAgICAgICAgICAgd3JpdGFibGU6IGZhbHNlXHJcbiAgICAgICAgICAgIH0pO1xyXG4gICAgICAgIGlmICghKHJlZ2V4IGluIG1lc3NhZ2UuX2hlYWRlckxvb2t1cHMpKSB7XHJcbiAgICAgICAgICAgIHZhciBoZWFkZXI7XHJcbiAgICAgICAgICAgIGZvciAodmFyIGkgPSAwOyBpIDwgbWVzc2FnZS5oZWFkZXJzLmxlbmd0aDsgaSsrKSB7XHJcbiAgICAgICAgICAgICAgICBpZiAoISFtZXNzYWdlLmhlYWRlcnNbaV1bMF0ubWF0Y2gocmVnZXgpKSB7XHJcbiAgICAgICAgICAgICAgICAgICAgaGVhZGVyID0gbWVzc2FnZS5oZWFkZXJzW2ldO1xyXG4gICAgICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgICAgIG1lc3NhZ2UuX2hlYWRlckxvb2t1cHNbcmVnZXhdID0gaGVhZGVyID8gaGVhZGVyWzFdIDogdW5kZWZpbmVkO1xyXG4gICAgICAgIH1cclxuICAgICAgICByZXR1cm4gbWVzc2FnZS5faGVhZGVyTG9va3Vwc1tyZWdleF07XHJcbiAgICB9LFxyXG4gICAgbWF0Y2hfaGVhZGVyOiBmdW5jdGlvbiAobWVzc2FnZSwgcmVnZXgpIHtcclxuICAgICAgICB2YXIgaGVhZGVycyA9IG1lc3NhZ2UuaGVhZGVycztcclxuICAgICAgICB2YXIgaSA9IGhlYWRlcnMubGVuZ3RoO1xyXG4gICAgICAgIHdoaWxlIChpLS0pIHtcclxuICAgICAgICAgICAgaWYgKHJlZ2V4LnRlc3QoaGVhZGVyc1tpXS5qb2luKFwiIFwiKSkpIHtcclxuICAgICAgICAgICAgICAgIHJldHVybiBoZWFkZXJzW2ldO1xyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHJldHVybiBmYWxzZTtcclxuICAgIH1cclxufTtcclxuXHJcbnZhciBkZWZhdWx0UG9ydHMgPSB7XHJcbiAgICBcImh0dHBcIjogODAsXHJcbiAgICBcImh0dHBzXCI6IDQ0M1xyXG59O1xyXG5cclxudmFyIFJlcXVlc3RVdGlscyA9IF8uZXh0ZW5kKF9NZXNzYWdlVXRpbHMsIHtcclxuICAgIHByZXR0eV9ob3N0OiBmdW5jdGlvbiAocmVxdWVzdCkge1xyXG4gICAgICAgIC8vRklYTUU6IEFkZCBob3N0aGVhZGVyXHJcbiAgICAgICAgcmV0dXJuIHJlcXVlc3QuaG9zdDtcclxuICAgIH0sXHJcbiAgICBwcmV0dHlfdXJsOiBmdW5jdGlvbiAocmVxdWVzdCkge1xyXG4gICAgICAgIHZhciBwb3J0ID0gXCJcIjtcclxuICAgICAgICBpZiAoZGVmYXVsdFBvcnRzW3JlcXVlc3Quc2NoZW1lXSAhPT0gcmVxdWVzdC5wb3J0KSB7XHJcbiAgICAgICAgICAgIHBvcnQgPSBcIjpcIiArIHJlcXVlc3QucG9ydDtcclxuICAgICAgICB9XHJcbiAgICAgICAgcmV0dXJuIHJlcXVlc3Quc2NoZW1lICsgXCI6Ly9cIiArIHRoaXMucHJldHR5X2hvc3QocmVxdWVzdCkgKyBwb3J0ICsgcmVxdWVzdC5wYXRoO1xyXG4gICAgfVxyXG59KTtcclxuXHJcbnZhciBSZXNwb25zZVV0aWxzID0gXy5leHRlbmQoX01lc3NhZ2VVdGlscywge30pO1xyXG5cclxuXHJcbm1vZHVsZS5leHBvcnRzID0ge1xyXG4gICAgUmVzcG9uc2VVdGlsczogUmVzcG9uc2VVdGlscyxcclxuICAgIFJlcXVlc3RVdGlsczogUmVxdWVzdFV0aWxzXHJcblxyXG59IiwiXHJcbnZhciBfID0gcmVxdWlyZShcImxvZGFzaFwiKTtcclxudmFyICQgPSByZXF1aXJlKFwianF1ZXJ5XCIpO1xyXG52YXIgRXZlbnRFbWl0dGVyID0gcmVxdWlyZSgnZXZlbnRzJykuRXZlbnRFbWl0dGVyO1xyXG5cclxudmFyIHV0aWxzID0gcmVxdWlyZShcIi4uL3V0aWxzLmpzXCIpO1xyXG52YXIgYWN0aW9ucyA9IHJlcXVpcmUoXCIuLi9hY3Rpb25zLmpzXCIpO1xyXG52YXIgZGlzcGF0Y2hlciA9IHJlcXVpcmUoXCIuLi9kaXNwYXRjaGVyLmpzXCIpO1xyXG5cclxuXHJcbmZ1bmN0aW9uIExpc3RTdG9yZSgpIHtcclxuICAgIEV2ZW50RW1pdHRlci5jYWxsKHRoaXMpO1xyXG4gICAgdGhpcy5yZXNldCgpO1xyXG59XHJcbl8uZXh0ZW5kKExpc3RTdG9yZS5wcm90b3R5cGUsIEV2ZW50RW1pdHRlci5wcm90b3R5cGUsIHtcclxuICAgIGFkZDogZnVuY3Rpb24gKGVsZW0pIHtcclxuICAgICAgICBpZiAoZWxlbS5pZCBpbiB0aGlzLl9wb3NfbWFwKSB7XHJcbiAgICAgICAgICAgIHJldHVybjtcclxuICAgICAgICB9XHJcbiAgICAgICAgdGhpcy5fcG9zX21hcFtlbGVtLmlkXSA9IHRoaXMubGlzdC5sZW5ndGg7XHJcbiAgICAgICAgdGhpcy5saXN0LnB1c2goZWxlbSk7XHJcbiAgICAgICAgdGhpcy5lbWl0KFwiYWRkXCIsIGVsZW0pO1xyXG4gICAgfSxcclxuICAgIHVwZGF0ZTogZnVuY3Rpb24gKGVsZW0pIHtcclxuICAgICAgICBpZiAoIShlbGVtLmlkIGluIHRoaXMuX3Bvc19tYXApKSB7XHJcbiAgICAgICAgICAgIHJldHVybjtcclxuICAgICAgICB9XHJcbiAgICAgICAgdGhpcy5saXN0W3RoaXMuX3Bvc19tYXBbZWxlbS5pZF1dID0gZWxlbTtcclxuICAgICAgICB0aGlzLmVtaXQoXCJ1cGRhdGVcIiwgZWxlbSk7XHJcbiAgICB9LFxyXG4gICAgcmVtb3ZlOiBmdW5jdGlvbiAoZWxlbV9pZCkge1xyXG4gICAgICAgIGlmICghKGVsZW1faWQgaW4gdGhpcy5fcG9zX21hcCkpIHtcclxuICAgICAgICAgICAgcmV0dXJuO1xyXG4gICAgICAgIH1cclxuICAgICAgICB0aGlzLmxpc3Quc3BsaWNlKHRoaXMuX3Bvc19tYXBbZWxlbV9pZF0sIDEpO1xyXG4gICAgICAgIHRoaXMuX2J1aWxkX21hcCgpO1xyXG4gICAgICAgIHRoaXMuZW1pdChcInJlbW92ZVwiLCBlbGVtX2lkKTtcclxuICAgIH0sXHJcbiAgICByZXNldDogZnVuY3Rpb24gKGVsZW1zKSB7XHJcbiAgICAgICAgdGhpcy5saXN0ID0gZWxlbXMgfHwgW107XHJcbiAgICAgICAgdGhpcy5fYnVpbGRfbWFwKCk7XHJcbiAgICAgICAgdGhpcy5lbWl0KFwicmVjYWxjdWxhdGVcIik7XHJcbiAgICB9LFxyXG4gICAgX2J1aWxkX21hcDogZnVuY3Rpb24gKCkge1xyXG4gICAgICAgIHRoaXMuX3Bvc19tYXAgPSB7fTtcclxuICAgICAgICBmb3IgKHZhciBpID0gMDsgaSA8IHRoaXMubGlzdC5sZW5ndGg7IGkrKykge1xyXG4gICAgICAgICAgICB2YXIgZWxlbSA9IHRoaXMubGlzdFtpXTtcclxuICAgICAgICAgICAgdGhpcy5fcG9zX21hcFtlbGVtLmlkXSA9IGk7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIGdldDogZnVuY3Rpb24gKGVsZW1faWQpIHtcclxuICAgICAgICByZXR1cm4gdGhpcy5saXN0W3RoaXMuX3Bvc19tYXBbZWxlbV9pZF1dO1xyXG4gICAgfSxcclxuICAgIGluZGV4OiBmdW5jdGlvbiAoZWxlbV9pZCkge1xyXG4gICAgICAgIHJldHVybiB0aGlzLl9wb3NfbWFwW2VsZW1faWRdO1xyXG4gICAgfVxyXG59KTtcclxuXHJcblxyXG5mdW5jdGlvbiBEaWN0U3RvcmUoKSB7XHJcbiAgICBFdmVudEVtaXR0ZXIuY2FsbCh0aGlzKTtcclxuICAgIHRoaXMucmVzZXQoKTtcclxufVxyXG5fLmV4dGVuZChEaWN0U3RvcmUucHJvdG90eXBlLCBFdmVudEVtaXR0ZXIucHJvdG90eXBlLCB7XHJcbiAgICB1cGRhdGU6IGZ1bmN0aW9uIChkaWN0KSB7XHJcbiAgICAgICAgXy5tZXJnZSh0aGlzLmRpY3QsIGRpY3QpO1xyXG4gICAgICAgIHRoaXMuZW1pdChcInJlY2FsY3VsYXRlXCIpO1xyXG4gICAgfSxcclxuICAgIHJlc2V0OiBmdW5jdGlvbiAoZGljdCkge1xyXG4gICAgICAgIHRoaXMuZGljdCA9IGRpY3QgfHwge307XHJcbiAgICAgICAgdGhpcy5lbWl0KFwicmVjYWxjdWxhdGVcIik7XHJcbiAgICB9XHJcbn0pO1xyXG5cclxuZnVuY3Rpb24gTGl2ZVN0b3JlTWl4aW4odHlwZSkge1xyXG4gICAgdGhpcy50eXBlID0gdHlwZTtcclxuXHJcbiAgICB0aGlzLl91cGRhdGVzX2JlZm9yZV9mZXRjaCA9IHVuZGVmaW5lZDtcclxuICAgIHRoaXMuX2ZldGNoeGhyID0gZmFsc2U7XHJcblxyXG4gICAgdGhpcy5oYW5kbGUgPSB0aGlzLmhhbmRsZS5iaW5kKHRoaXMpO1xyXG4gICAgZGlzcGF0Y2hlci5BcHBEaXNwYXRjaGVyLnJlZ2lzdGVyKHRoaXMuaGFuZGxlKTtcclxuXHJcbiAgICAvLyBBdm9pZCBkb3VibGUtZmV0Y2ggb24gc3RhcnR1cC5cclxuICAgIGlmICghKHdpbmRvdy53cyAmJiB3aW5kb3cud3MucmVhZHlTdGF0ZSA9PT0gV2ViU29ja2V0LkNPTk5FQ1RJTkcpKSB7XHJcbiAgICAgICAgdGhpcy5mZXRjaCgpO1xyXG4gICAgfVxyXG59XHJcbl8uZXh0ZW5kKExpdmVTdG9yZU1peGluLnByb3RvdHlwZSwge1xyXG4gICAgaGFuZGxlOiBmdW5jdGlvbiAoZXZlbnQpIHtcclxuICAgICAgICBpZiAoZXZlbnQudHlwZSA9PT0gYWN0aW9ucy5BY3Rpb25UeXBlcy5DT05ORUNUSU9OX09QRU4pIHtcclxuICAgICAgICAgICAgcmV0dXJuIHRoaXMuZmV0Y2goKTtcclxuICAgICAgICB9XHJcbiAgICAgICAgaWYgKGV2ZW50LnR5cGUgPT09IHRoaXMudHlwZSkge1xyXG4gICAgICAgICAgICBpZiAoZXZlbnQuY21kID09PSBhY3Rpb25zLlN0b3JlQ21kcy5SRVNFVCkge1xyXG4gICAgICAgICAgICAgICAgdGhpcy5mZXRjaChldmVudC5kYXRhKTtcclxuICAgICAgICAgICAgfSBlbHNlIGlmICh0aGlzLl91cGRhdGVzX2JlZm9yZV9mZXRjaCkge1xyXG4gICAgICAgICAgICAgICAgY29uc29sZS5sb2coXCJkZWZlciB1cGRhdGVcIiwgZXZlbnQpO1xyXG4gICAgICAgICAgICAgICAgdGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2gucHVzaChldmVudCk7XHJcbiAgICAgICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgICAgICB0aGlzW2V2ZW50LmNtZF0oZXZlbnQuZGF0YSk7XHJcbiAgICAgICAgICAgIH1cclxuICAgICAgICB9XHJcbiAgICB9LFxyXG4gICAgY2xvc2U6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICBkaXNwYXRjaGVyLkFwcERpc3BhdGNoZXIudW5yZWdpc3Rlcih0aGlzLmhhbmRsZSk7XHJcbiAgICB9LFxyXG4gICAgZmV0Y2g6IGZ1bmN0aW9uIChkYXRhKSB7XHJcbiAgICAgICAgY29uc29sZS5sb2coXCJmZXRjaCBcIiArIHRoaXMudHlwZSk7XHJcbiAgICAgICAgaWYgKHRoaXMuX2ZldGNoeGhyKSB7XHJcbiAgICAgICAgICAgIHRoaXMuX2ZldGNoeGhyLmFib3J0KCk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIHRoaXMuX3VwZGF0ZXNfYmVmb3JlX2ZldGNoID0gW107IC8vIChKUzogZW1wdHkgYXJyYXkgaXMgdHJ1ZSlcclxuICAgICAgICBpZiAoZGF0YSkge1xyXG4gICAgICAgICAgICB0aGlzLmhhbmRsZV9mZXRjaChkYXRhKTtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICB0aGlzLl9mZXRjaHhociA9ICQuZ2V0SlNPTihcIi9cIiArIHRoaXMudHlwZSlcclxuICAgICAgICAgICAgICAgIC5kb25lKGZ1bmN0aW9uIChtZXNzYWdlKSB7XHJcbiAgICAgICAgICAgICAgICAgICAgdGhpcy5oYW5kbGVfZmV0Y2gobWVzc2FnZS5kYXRhKTtcclxuICAgICAgICAgICAgICAgIH0uYmluZCh0aGlzKSlcclxuICAgICAgICAgICAgICAgIC5mYWlsKGZ1bmN0aW9uICgpIHtcclxuICAgICAgICAgICAgICAgICAgICBFdmVudExvZ0FjdGlvbnMuYWRkX2V2ZW50KFwiQ291bGQgbm90IGZldGNoIFwiICsgdGhpcy50eXBlKTtcclxuICAgICAgICAgICAgICAgIH0uYmluZCh0aGlzKSk7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIGhhbmRsZV9mZXRjaDogZnVuY3Rpb24gKGRhdGEpIHtcclxuICAgICAgICB0aGlzLl9mZXRjaHhociA9IGZhbHNlO1xyXG4gICAgICAgIGNvbnNvbGUubG9nKHRoaXMudHlwZSArIFwiIGZldGNoZWQuXCIsIHRoaXMuX3VwZGF0ZXNfYmVmb3JlX2ZldGNoKTtcclxuICAgICAgICB0aGlzLnJlc2V0KGRhdGEpO1xyXG4gICAgICAgIHZhciB1cGRhdGVzID0gdGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2g7XHJcbiAgICAgICAgdGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2ggPSBmYWxzZTtcclxuICAgICAgICBmb3IgKHZhciBpID0gMDsgaSA8IHVwZGF0ZXMubGVuZ3RoOyBpKyspIHtcclxuICAgICAgICAgICAgdGhpcy5oYW5kbGUodXBkYXRlc1tpXSk7XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxufSk7XHJcblxyXG5mdW5jdGlvbiBMaXZlTGlzdFN0b3JlKHR5cGUpIHtcclxuICAgIExpc3RTdG9yZS5jYWxsKHRoaXMpO1xyXG4gICAgTGl2ZVN0b3JlTWl4aW4uY2FsbCh0aGlzLCB0eXBlKTtcclxufVxyXG5fLmV4dGVuZChMaXZlTGlzdFN0b3JlLnByb3RvdHlwZSwgTGlzdFN0b3JlLnByb3RvdHlwZSwgTGl2ZVN0b3JlTWl4aW4ucHJvdG90eXBlKTtcclxuXHJcbmZ1bmN0aW9uIExpdmVEaWN0U3RvcmUodHlwZSkge1xyXG4gICAgRGljdFN0b3JlLmNhbGwodGhpcyk7XHJcbiAgICBMaXZlU3RvcmVNaXhpbi5jYWxsKHRoaXMsIHR5cGUpO1xyXG59XHJcbl8uZXh0ZW5kKExpdmVEaWN0U3RvcmUucHJvdG90eXBlLCBEaWN0U3RvcmUucHJvdG90eXBlLCBMaXZlU3RvcmVNaXhpbi5wcm90b3R5cGUpO1xyXG5cclxuXHJcbmZ1bmN0aW9uIEZsb3dTdG9yZSgpIHtcclxuICAgIHJldHVybiBuZXcgTGl2ZUxpc3RTdG9yZShhY3Rpb25zLkFjdGlvblR5cGVzLkZMT1dfU1RPUkUpO1xyXG59XHJcblxyXG5mdW5jdGlvbiBTZXR0aW5nc1N0b3JlKCkge1xyXG4gICAgcmV0dXJuIG5ldyBMaXZlRGljdFN0b3JlKGFjdGlvbnMuQWN0aW9uVHlwZXMuU0VUVElOR1NfU1RPUkUpO1xyXG59XHJcblxyXG5mdW5jdGlvbiBFdmVudExvZ1N0b3JlKCkge1xyXG4gICAgTGl2ZUxpc3RTdG9yZS5jYWxsKHRoaXMsIGFjdGlvbnMuQWN0aW9uVHlwZXMuRVZFTlRfU1RPUkUpO1xyXG59XHJcbl8uZXh0ZW5kKEV2ZW50TG9nU3RvcmUucHJvdG90eXBlLCBMaXZlTGlzdFN0b3JlLnByb3RvdHlwZSwge1xyXG4gICAgZmV0Y2g6IGZ1bmN0aW9uKCl7XHJcbiAgICAgICAgTGl2ZUxpc3RTdG9yZS5wcm90b3R5cGUuZmV0Y2guYXBwbHkodGhpcywgYXJndW1lbnRzKTtcclxuXHJcbiAgICAgICAgLy8gTWFrZSBzdXJlIHRvIGRpc3BsYXkgdXBkYXRlcyBldmVuIGlmIGZldGNoaW5nIGFsbCBldmVudHMgZmFpbGVkLlxyXG4gICAgICAgIC8vIFRoaXMgd2F5LCB3ZSBjYW4gc2VuZCBcImZldGNoIGZhaWxlZFwiIGxvZyBtZXNzYWdlcyB0byB0aGUgbG9nLlxyXG4gICAgICAgIGlmKHRoaXMuX2ZldGNoeGhyKXtcclxuICAgICAgICAgICAgdGhpcy5fZmV0Y2h4aHIuZmFpbChmdW5jdGlvbigpe1xyXG4gICAgICAgICAgICAgICAgdGhpcy5oYW5kbGVfZmV0Y2gobnVsbCk7XHJcbiAgICAgICAgICAgIH0uYmluZCh0aGlzKSk7XHJcbiAgICAgICAgfVxyXG4gICAgfVxyXG59KTtcclxuXHJcblxyXG5tb2R1bGUuZXhwb3J0cyA9IHtcclxuICAgIEV2ZW50TG9nU3RvcmU6IEV2ZW50TG9nU3RvcmUsXHJcbiAgICBTZXR0aW5nc1N0b3JlOiBTZXR0aW5nc1N0b3JlLFxyXG4gICAgRmxvd1N0b3JlOiBGbG93U3RvcmVcclxufTsiLCJcclxudmFyIEV2ZW50RW1pdHRlciA9IHJlcXVpcmUoJ2V2ZW50cycpLkV2ZW50RW1pdHRlcjtcclxudmFyIF8gPSByZXF1aXJlKFwibG9kYXNoXCIpO1xyXG5cclxuXHJcbnZhciB1dGlscyA9IHJlcXVpcmUoXCIuLi91dGlscy5qc1wiKTtcclxuXHJcbmZ1bmN0aW9uIFNvcnRCeVN0b3JlT3JkZXIoZWxlbSkge1xyXG4gICAgcmV0dXJuIHRoaXMuc3RvcmUuaW5kZXgoZWxlbS5pZCk7XHJcbn1cclxuXHJcbnZhciBkZWZhdWx0X3NvcnQgPSBTb3J0QnlTdG9yZU9yZGVyO1xyXG52YXIgZGVmYXVsdF9maWx0ID0gZnVuY3Rpb24oZWxlbSl7XHJcbiAgICByZXR1cm4gdHJ1ZTtcclxufTtcclxuXHJcbmZ1bmN0aW9uIFN0b3JlVmlldyhzdG9yZSwgZmlsdCwgc29ydGZ1bikge1xyXG4gICAgRXZlbnRFbWl0dGVyLmNhbGwodGhpcyk7XHJcbiAgICBmaWx0ID0gZmlsdCB8fCBkZWZhdWx0X2ZpbHQ7XHJcbiAgICBzb3J0ZnVuID0gc29ydGZ1biB8fCBkZWZhdWx0X3NvcnQ7XHJcblxyXG4gICAgdGhpcy5zdG9yZSA9IHN0b3JlO1xyXG5cclxuICAgIHRoaXMuYWRkID0gdGhpcy5hZGQuYmluZCh0aGlzKTtcclxuICAgIHRoaXMudXBkYXRlID0gdGhpcy51cGRhdGUuYmluZCh0aGlzKTtcclxuICAgIHRoaXMucmVtb3ZlID0gdGhpcy5yZW1vdmUuYmluZCh0aGlzKTtcclxuICAgIHRoaXMucmVjYWxjdWxhdGUgPSB0aGlzLnJlY2FsY3VsYXRlLmJpbmQodGhpcyk7XHJcbiAgICB0aGlzLnN0b3JlLmFkZExpc3RlbmVyKFwiYWRkXCIsIHRoaXMuYWRkKTtcclxuICAgIHRoaXMuc3RvcmUuYWRkTGlzdGVuZXIoXCJ1cGRhdGVcIiwgdGhpcy51cGRhdGUpO1xyXG4gICAgdGhpcy5zdG9yZS5hZGRMaXN0ZW5lcihcInJlbW92ZVwiLCB0aGlzLnJlbW92ZSk7XHJcbiAgICB0aGlzLnN0b3JlLmFkZExpc3RlbmVyKFwicmVjYWxjdWxhdGVcIiwgdGhpcy5yZWNhbGN1bGF0ZSk7XHJcblxyXG4gICAgdGhpcy5yZWNhbGN1bGF0ZShmaWx0LCBzb3J0ZnVuKTtcclxufVxyXG5cclxuXy5leHRlbmQoU3RvcmVWaWV3LnByb3RvdHlwZSwgRXZlbnRFbWl0dGVyLnByb3RvdHlwZSwge1xyXG4gICAgY2xvc2U6IGZ1bmN0aW9uICgpIHtcclxuICAgICAgICB0aGlzLnN0b3JlLnJlbW92ZUxpc3RlbmVyKFwiYWRkXCIsIHRoaXMuYWRkKTtcclxuICAgICAgICB0aGlzLnN0b3JlLnJlbW92ZUxpc3RlbmVyKFwidXBkYXRlXCIsIHRoaXMudXBkYXRlKTtcclxuICAgICAgICB0aGlzLnN0b3JlLnJlbW92ZUxpc3RlbmVyKFwicmVtb3ZlXCIsIHRoaXMucmVtb3ZlKTtcclxuICAgICAgICB0aGlzLnN0b3JlLnJlbW92ZUxpc3RlbmVyKFwicmVjYWxjdWxhdGVcIiwgdGhpcy5yZWNhbGN1bGF0ZSk7XHJcbiAgICAgICAgfSxcclxuICAgICAgICByZWNhbGN1bGF0ZTogZnVuY3Rpb24gKGZpbHQsIHNvcnRmdW4pIHtcclxuICAgICAgICBpZiAoZmlsdCkge1xyXG4gICAgICAgICAgICB0aGlzLmZpbHQgPSBmaWx0LmJpbmQodGhpcyk7XHJcbiAgICAgICAgfVxyXG4gICAgICAgIGlmIChzb3J0ZnVuKSB7XHJcbiAgICAgICAgICAgIHRoaXMuc29ydGZ1biA9IHNvcnRmdW4uYmluZCh0aGlzKTtcclxuICAgICAgICB9XHJcblxyXG4gICAgICAgIHRoaXMubGlzdCA9IHRoaXMuc3RvcmUubGlzdC5maWx0ZXIodGhpcy5maWx0KTtcclxuICAgICAgICB0aGlzLmxpc3Quc29ydChmdW5jdGlvbiAoYSwgYikge1xyXG4gICAgICAgICAgICByZXR1cm4gdGhpcy5zb3J0ZnVuKGEpIC0gdGhpcy5zb3J0ZnVuKGIpO1xyXG4gICAgICAgIH0uYmluZCh0aGlzKSk7XHJcbiAgICAgICAgdGhpcy5lbWl0KFwicmVjYWxjdWxhdGVcIik7XHJcbiAgICB9LFxyXG4gICAgaW5kZXg6IGZ1bmN0aW9uIChlbGVtKSB7XHJcbiAgICAgICAgcmV0dXJuIF8uc29ydGVkSW5kZXgodGhpcy5saXN0LCBlbGVtLCB0aGlzLnNvcnRmdW4pO1xyXG4gICAgfSxcclxuICAgIGFkZDogZnVuY3Rpb24gKGVsZW0pIHtcclxuICAgICAgICBpZiAodGhpcy5maWx0KGVsZW0pKSB7XHJcbiAgICAgICAgICAgIHZhciBpZHggPSB0aGlzLmluZGV4KGVsZW0pO1xyXG4gICAgICAgICAgICBpZiAoaWR4ID09PSB0aGlzLmxpc3QubGVuZ3RoKSB7IC8vaGFwcGVucyBvZnRlbiwgLnB1c2ggaXMgd2F5IGZhc3Rlci5cclxuICAgICAgICAgICAgICAgIHRoaXMubGlzdC5wdXNoKGVsZW0pO1xyXG4gICAgICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICAgICAgdGhpcy5saXN0LnNwbGljZShpZHgsIDAsIGVsZW0pO1xyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgICAgIHRoaXMuZW1pdChcImFkZFwiLCBlbGVtLCBpZHgpO1xyXG4gICAgICAgIH1cclxuICAgIH0sXHJcbiAgICB1cGRhdGU6IGZ1bmN0aW9uIChlbGVtKSB7XHJcbiAgICAgICAgdmFyIGlkeDtcclxuICAgICAgICB2YXIgaSA9IHRoaXMubGlzdC5sZW5ndGg7XHJcbiAgICAgICAgLy8gU2VhcmNoIGZyb20gdGhlIGJhY2ssIHdlIHVzdWFsbHkgdXBkYXRlIHRoZSBsYXRlc3QgZW50cmllcy5cclxuICAgICAgICB3aGlsZSAoaS0tKSB7XHJcbiAgICAgICAgICAgIGlmICh0aGlzLmxpc3RbaV0uaWQgPT09IGVsZW0uaWQpIHtcclxuICAgICAgICAgICAgICAgIGlkeCA9IGk7XHJcbiAgICAgICAgICAgICAgICBicmVhaztcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgIH1cclxuXHJcbiAgICAgICAgaWYgKGlkeCA9PT0gLTEpIHsgLy9ub3QgY29udGFpbmVkIGluIGxpc3RcclxuICAgICAgICAgICAgdGhpcy5hZGQoZWxlbSk7XHJcbiAgICAgICAgfSBlbHNlIGlmICghdGhpcy5maWx0KGVsZW0pKSB7XHJcbiAgICAgICAgICAgIHRoaXMucmVtb3ZlKGVsZW0uaWQpO1xyXG4gICAgICAgIH0gZWxzZSB7XHJcbiAgICAgICAgICAgIGlmICh0aGlzLnNvcnRmdW4odGhpcy5saXN0W2lkeF0pICE9PSB0aGlzLnNvcnRmdW4oZWxlbSkpIHsgLy9zb3J0cG9zIGhhcyBjaGFuZ2VkXHJcbiAgICAgICAgICAgICAgICB0aGlzLnJlbW92ZSh0aGlzLmxpc3RbaWR4XSk7XHJcbiAgICAgICAgICAgICAgICB0aGlzLmFkZChlbGVtKTtcclxuICAgICAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgICAgIHRoaXMubGlzdFtpZHhdID0gZWxlbTtcclxuICAgICAgICAgICAgICAgIHRoaXMuZW1pdChcInVwZGF0ZVwiLCBlbGVtLCBpZHgpO1xyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgfVxyXG4gICAgfSxcclxuICAgIHJlbW92ZTogZnVuY3Rpb24gKGVsZW1faWQpIHtcclxuICAgICAgICB2YXIgaWR4ID0gdGhpcy5saXN0Lmxlbmd0aDtcclxuICAgICAgICB3aGlsZSAoaWR4LS0pIHtcclxuICAgICAgICAgICAgaWYgKHRoaXMubGlzdFtpZHhdLmlkID09PSBlbGVtX2lkKSB7XHJcbiAgICAgICAgICAgICAgICB0aGlzLmxpc3Quc3BsaWNlKGlkeCwgMSk7XHJcbiAgICAgICAgICAgICAgICB0aGlzLmVtaXQoXCJyZW1vdmVcIiwgZWxlbV9pZCwgaWR4KTtcclxuICAgICAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgICAgICB9XHJcbiAgICAgICAgfVxyXG4gICAgfVxyXG59KTtcclxuXHJcbm1vZHVsZS5leHBvcnRzID0ge1xyXG4gICAgU3RvcmVWaWV3OiBTdG9yZVZpZXdcclxufTsiLCJ2YXIgJCA9IHJlcXVpcmUoXCJqcXVlcnlcIik7XHJcblxyXG5cclxudmFyIEtleSA9IHtcclxuICAgIFVQOiAzOCxcclxuICAgIERPV046IDQwLFxyXG4gICAgUEFHRV9VUDogMzMsXHJcbiAgICBQQUdFX0RPV046IDM0LFxyXG4gICAgSE9NRTogMzYsXHJcbiAgICBFTkQ6IDM1LFxyXG4gICAgTEVGVDogMzcsXHJcbiAgICBSSUdIVDogMzksXHJcbiAgICBFTlRFUjogMTMsXHJcbiAgICBFU0M6IDI3LFxyXG4gICAgVEFCOiA5LFxyXG4gICAgU1BBQ0U6IDMyLFxyXG4gICAgQkFDS1NQQUNFOiA4LFxyXG59O1xyXG4vLyBBZGQgQS1aXHJcbmZvciAodmFyIGkgPSA2NTsgaSA8PSA5MDsgaSsrKSB7XHJcbiAgICBLZXlbU3RyaW5nLmZyb21DaGFyQ29kZShpKV0gPSBpO1xyXG59XHJcblxyXG5cclxudmFyIGZvcm1hdFNpemUgPSBmdW5jdGlvbiAoYnl0ZXMpIHtcclxuICAgIGlmIChieXRlcyA9PT0gMClcclxuICAgICAgICByZXR1cm4gXCIwXCI7XHJcbiAgICB2YXIgcHJlZml4ID0gW1wiYlwiLCBcImtiXCIsIFwibWJcIiwgXCJnYlwiLCBcInRiXCJdO1xyXG4gICAgZm9yICh2YXIgaSA9IDA7IGkgPCBwcmVmaXgubGVuZ3RoOyBpKyspe1xyXG4gICAgICAgIGlmIChNYXRoLnBvdygxMDI0LCBpICsgMSkgPiBieXRlcyl7XHJcbiAgICAgICAgICAgIGJyZWFrO1xyXG4gICAgICAgIH1cclxuICAgIH1cclxuICAgIHZhciBwcmVjaXNpb247XHJcbiAgICBpZiAoYnl0ZXMlTWF0aC5wb3coMTAyNCwgaSkgPT09IDApXHJcbiAgICAgICAgcHJlY2lzaW9uID0gMDtcclxuICAgIGVsc2VcclxuICAgICAgICBwcmVjaXNpb24gPSAxO1xyXG4gICAgcmV0dXJuIChieXRlcy9NYXRoLnBvdygxMDI0LCBpKSkudG9GaXhlZChwcmVjaXNpb24pICsgcHJlZml4W2ldO1xyXG59O1xyXG5cclxuXHJcbnZhciBmb3JtYXRUaW1lRGVsdGEgPSBmdW5jdGlvbiAobWlsbGlzZWNvbmRzKSB7XHJcbiAgICB2YXIgdGltZSA9IG1pbGxpc2Vjb25kcztcclxuICAgIHZhciBwcmVmaXggPSBbXCJtc1wiLCBcInNcIiwgXCJtaW5cIiwgXCJoXCJdO1xyXG4gICAgdmFyIGRpdiA9IFsxMDAwLCA2MCwgNjBdO1xyXG4gICAgdmFyIGkgPSAwO1xyXG4gICAgd2hpbGUgKE1hdGguYWJzKHRpbWUpID49IGRpdltpXSAmJiBpIDwgZGl2Lmxlbmd0aCkge1xyXG4gICAgICAgIHRpbWUgPSB0aW1lIC8gZGl2W2ldO1xyXG4gICAgICAgIGkrKztcclxuICAgIH1cclxuICAgIHJldHVybiBNYXRoLnJvdW5kKHRpbWUpICsgcHJlZml4W2ldO1xyXG59O1xyXG5cclxuXHJcbnZhciBmb3JtYXRUaW1lU3RhbXAgPSBmdW5jdGlvbiAoc2Vjb25kcykge1xyXG4gICAgdmFyIHRzID0gKG5ldyBEYXRlKHNlY29uZHMgKiAxMDAwKSkudG9JU09TdHJpbmcoKTtcclxuICAgIHJldHVybiB0cy5yZXBsYWNlKFwiVFwiLCBcIiBcIikucmVwbGFjZShcIlpcIiwgXCJcIik7XHJcbn07XHJcblxyXG5cclxuZnVuY3Rpb24gZ2V0Q29va2llKG5hbWUpIHtcclxuICAgIHZhciByID0gZG9jdW1lbnQuY29va2llLm1hdGNoKFwiXFxcXGJcIiArIG5hbWUgKyBcIj0oW147XSopXFxcXGJcIik7XHJcbiAgICByZXR1cm4gciA/IHJbMV0gOiB1bmRlZmluZWQ7XHJcbn1cclxudmFyIHhzcmYgPSAkLnBhcmFtKHtfeHNyZjogZ2V0Q29va2llKFwiX3hzcmZcIil9KTtcclxuXHJcbi8vVG9ybmFkbyBYU1JGIFByb3RlY3Rpb24uXHJcbiQuYWpheFByZWZpbHRlcihmdW5jdGlvbiAob3B0aW9ucykge1xyXG4gICAgaWYgKFtcInBvc3RcIiwgXCJwdXRcIiwgXCJkZWxldGVcIl0uaW5kZXhPZihvcHRpb25zLnR5cGUudG9Mb3dlckNhc2UoKSkgPj0gMCAmJiBvcHRpb25zLnVybFswXSA9PT0gXCIvXCIpIHtcclxuICAgICAgICBpZiAob3B0aW9ucy5kYXRhKSB7XHJcbiAgICAgICAgICAgIG9wdGlvbnMuZGF0YSArPSAoXCImXCIgKyB4c3JmKTtcclxuICAgICAgICB9IGVsc2Uge1xyXG4gICAgICAgICAgICBvcHRpb25zLmRhdGEgPSB4c3JmO1xyXG4gICAgICAgIH1cclxuICAgIH1cclxufSk7XHJcbi8vIExvZyBBSkFYIEVycm9yc1xyXG4kKGRvY3VtZW50KS5hamF4RXJyb3IoZnVuY3Rpb24gKGV2ZW50LCBqcVhIUiwgYWpheFNldHRpbmdzLCB0aHJvd25FcnJvcikge1xyXG4gICAgdmFyIG1lc3NhZ2UgPSBqcVhIUi5yZXNwb25zZVRleHQ7XHJcbiAgICBjb25zb2xlLmVycm9yKG1lc3NhZ2UsIGFyZ3VtZW50cyk7XHJcbiAgICBFdmVudExvZ0FjdGlvbnMuYWRkX2V2ZW50KHRocm93bkVycm9yICsgXCI6IFwiICsgbWVzc2FnZSk7XHJcbiAgICB3aW5kb3cuYWxlcnQobWVzc2FnZSk7XHJcbn0pO1xyXG5cclxubW9kdWxlLmV4cG9ydHMgPSB7XHJcbiAgICBmb3JtYXRTaXplOiBmb3JtYXRTaXplLFxyXG4gICAgZm9ybWF0VGltZURlbHRhOiBmb3JtYXRUaW1lRGVsdGEsXHJcbiAgICBmb3JtYXRUaW1lU3RhbXA6IGZvcm1hdFRpbWVTdGFtcCxcclxuICAgIEtleTogS2V5XHJcbn07Il19
