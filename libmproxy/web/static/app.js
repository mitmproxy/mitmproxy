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
/**
 * Copyright (c) 2014, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the
 * LICENSE file in the root directory of this source tree. An additional grant
 * of patent rights can be found in the PATENTS file in the same directory.
 */

module.exports.Dispatcher = require('./lib/Dispatcher')

},{"./lib/Dispatcher":3}],3:[function(require,module,exports){
/*
 * Copyright (c) 2014, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the
 * LICENSE file in the root directory of this source tree. An additional grant
 * of patent rights can be found in the PATENTS file in the same directory.
 *
 * @providesModule Dispatcher
 * @typechecks
 */

"use strict";

var invariant = require('./invariant');

var _lastID = 1;
var _prefix = 'ID_';

/**
 * Dispatcher is used to broadcast payloads to registered callbacks. This is
 * different from generic pub-sub systems in two ways:
 *
 *   1) Callbacks are not subscribed to particular events. Every payload is
 *      dispatched to every registered callback.
 *   2) Callbacks can be deferred in whole or part until other callbacks have
 *      been executed.
 *
 * For example, consider this hypothetical flight destination form, which
 * selects a default city when a country is selected:
 *
 *   var flightDispatcher = new Dispatcher();
 *
 *   // Keeps track of which country is selected
 *   var CountryStore = {country: null};
 *
 *   // Keeps track of which city is selected
 *   var CityStore = {city: null};
 *
 *   // Keeps track of the base flight price of the selected city
 *   var FlightPriceStore = {price: null}
 *
 * When a user changes the selected city, we dispatch the payload:
 *
 *   flightDispatcher.dispatch({
 *     actionType: 'city-update',
 *     selectedCity: 'paris'
 *   });
 *
 * This payload is digested by `CityStore`:
 *
 *   flightDispatcher.register(function(payload) {
 *     if (payload.actionType === 'city-update') {
 *       CityStore.city = payload.selectedCity;
 *     }
 *   });
 *
 * When the user selects a country, we dispatch the payload:
 *
 *   flightDispatcher.dispatch({
 *     actionType: 'country-update',
 *     selectedCountry: 'australia'
 *   });
 *
 * This payload is digested by both stores:
 *
 *    CountryStore.dispatchToken = flightDispatcher.register(function(payload) {
 *     if (payload.actionType === 'country-update') {
 *       CountryStore.country = payload.selectedCountry;
 *     }
 *   });
 *
 * When the callback to update `CountryStore` is registered, we save a reference
 * to the returned token. Using this token with `waitFor()`, we can guarantee
 * that `CountryStore` is updated before the callback that updates `CityStore`
 * needs to query its data.
 *
 *   CityStore.dispatchToken = flightDispatcher.register(function(payload) {
 *     if (payload.actionType === 'country-update') {
 *       // `CountryStore.country` may not be updated.
 *       flightDispatcher.waitFor([CountryStore.dispatchToken]);
 *       // `CountryStore.country` is now guaranteed to be updated.
 *
 *       // Select the default city for the new country
 *       CityStore.city = getDefaultCityForCountry(CountryStore.country);
 *     }
 *   });
 *
 * The usage of `waitFor()` can be chained, for example:
 *
 *   FlightPriceStore.dispatchToken =
 *     flightDispatcher.register(function(payload) {
 *       switch (payload.actionType) {
 *         case 'country-update':
 *           flightDispatcher.waitFor([CityStore.dispatchToken]);
 *           FlightPriceStore.price =
 *             getFlightPriceStore(CountryStore.country, CityStore.city);
 *           break;
 *
 *         case 'city-update':
 *           FlightPriceStore.price =
 *             FlightPriceStore(CountryStore.country, CityStore.city);
 *           break;
 *     }
 *   });
 *
 * The `country-update` payload will be guaranteed to invoke the stores'
 * registered callbacks in order: `CountryStore`, `CityStore`, then
 * `FlightPriceStore`.
 */

  function Dispatcher() {
    this.$Dispatcher_callbacks = {};
    this.$Dispatcher_isPending = {};
    this.$Dispatcher_isHandled = {};
    this.$Dispatcher_isDispatching = false;
    this.$Dispatcher_pendingPayload = null;
  }

  /**
   * Registers a callback to be invoked with every dispatched payload. Returns
   * a token that can be used with `waitFor()`.
   *
   * @param {function} callback
   * @return {string}
   */
  Dispatcher.prototype.register=function(callback) {
    var id = _prefix + _lastID++;
    this.$Dispatcher_callbacks[id] = callback;
    return id;
  };

  /**
   * Removes a callback based on its token.
   *
   * @param {string} id
   */
  Dispatcher.prototype.unregister=function(id) {
    invariant(
      this.$Dispatcher_callbacks[id],
      'Dispatcher.unregister(...): `%s` does not map to a registered callback.',
      id
    );
    delete this.$Dispatcher_callbacks[id];
  };

  /**
   * Waits for the callbacks specified to be invoked before continuing execution
   * of the current callback. This method should only be used by a callback in
   * response to a dispatched payload.
   *
   * @param {array<string>} ids
   */
  Dispatcher.prototype.waitFor=function(ids) {
    invariant(
      this.$Dispatcher_isDispatching,
      'Dispatcher.waitFor(...): Must be invoked while dispatching.'
    );
    for (var ii = 0; ii < ids.length; ii++) {
      var id = ids[ii];
      if (this.$Dispatcher_isPending[id]) {
        invariant(
          this.$Dispatcher_isHandled[id],
          'Dispatcher.waitFor(...): Circular dependency detected while ' +
          'waiting for `%s`.',
          id
        );
        continue;
      }
      invariant(
        this.$Dispatcher_callbacks[id],
        'Dispatcher.waitFor(...): `%s` does not map to a registered callback.',
        id
      );
      this.$Dispatcher_invokeCallback(id);
    }
  };

  /**
   * Dispatches a payload to all registered callbacks.
   *
   * @param {object} payload
   */
  Dispatcher.prototype.dispatch=function(payload) {
    invariant(
      !this.$Dispatcher_isDispatching,
      'Dispatch.dispatch(...): Cannot dispatch in the middle of a dispatch.'
    );
    this.$Dispatcher_startDispatching(payload);
    try {
      for (var id in this.$Dispatcher_callbacks) {
        if (this.$Dispatcher_isPending[id]) {
          continue;
        }
        this.$Dispatcher_invokeCallback(id);
      }
    } finally {
      this.$Dispatcher_stopDispatching();
    }
  };

  /**
   * Is this Dispatcher currently dispatching.
   *
   * @return {boolean}
   */
  Dispatcher.prototype.isDispatching=function() {
    return this.$Dispatcher_isDispatching;
  };

  /**
   * Call the callback stored with the given id. Also do some internal
   * bookkeeping.
   *
   * @param {string} id
   * @internal
   */
  Dispatcher.prototype.$Dispatcher_invokeCallback=function(id) {
    this.$Dispatcher_isPending[id] = true;
    this.$Dispatcher_callbacks[id](this.$Dispatcher_pendingPayload);
    this.$Dispatcher_isHandled[id] = true;
  };

  /**
   * Set up bookkeeping needed when dispatching.
   *
   * @param {object} payload
   * @internal
   */
  Dispatcher.prototype.$Dispatcher_startDispatching=function(payload) {
    for (var id in this.$Dispatcher_callbacks) {
      this.$Dispatcher_isPending[id] = false;
      this.$Dispatcher_isHandled[id] = false;
    }
    this.$Dispatcher_pendingPayload = payload;
    this.$Dispatcher_isDispatching = true;
  };

  /**
   * Clear bookkeeping used for dispatching.
   *
   * @internal
   */
  Dispatcher.prototype.$Dispatcher_stopDispatching=function() {
    this.$Dispatcher_pendingPayload = null;
    this.$Dispatcher_isDispatching = false;
  };


module.exports = Dispatcher;

},{"./invariant":4}],4:[function(require,module,exports){
/**
 * Copyright (c) 2014, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the
 * LICENSE file in the root directory of this source tree. An additional grant
 * of patent rights can be found in the PATENTS file in the same directory.
 *
 * @providesModule invariant
 */

"use strict";

/**
 * Use invariant() to assert state which your program assumes to be true.
 *
 * Provide sprintf-style format (only %s is supported) and arguments
 * to provide information about what broke and what you were
 * expecting.
 *
 * The invariant message will be stripped in production, but the invariant
 * will remain to ensure logic does not differ in production.
 */

var invariant = function(condition, format, a, b, c, d, e, f) {
  if (false) {
    if (format === undefined) {
      throw new Error('invariant requires an error message argument');
    }
  }

  if (!condition) {
    var error;
    if (format === undefined) {
      error = new Error(
        'Minified exception occurred; use the non-minified dev environment ' +
        'for the full error message and additional helpful warnings.'
      );
    } else {
      var args = [a, b, c, d, e, f];
      var argIndex = 0;
      error = new Error(
        'Invariant Violation: ' +
        format.replace(/%s/g, function() { return args[argIndex++]; })
      );
    }

    error.framesToPop = 1; // we don't care about invariant's own frame
    throw error;
  }
};

module.exports = invariant;

},{}],5:[function(require,module,exports){
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
},{"jquery":"jquery"}],6:[function(require,module,exports){

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
},{"./components/proxyapp.js":14,"./connection":17,"jquery":"jquery","react":"react","react-router":"react-router"}],7:[function(require,module,exports){
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
},{"../store/view.js":22,"./utils.js":15,"./virtualscroll.js":16,"react":"react"}],8:[function(require,module,exports){
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
},{"../actions.js":5,"../flow/utils.js":20,"../utils.js":23,"./utils.js":15,"lodash":"lodash","react":"react"}],9:[function(require,module,exports){
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



},{"../flow/utils.js":20,"../utils.js":23,"react":"react"}],10:[function(require,module,exports){
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

},{"./flowtable-columns.js":9,"./utils.js":15,"./virtualscroll.js":16,"react":"react"}],11:[function(require,module,exports){
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
},{"react":"react"}],12:[function(require,module,exports){
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
},{"./utils.js":15,"jquery":"jquery","react":"react"}],13:[function(require,module,exports){
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

},{"../filt/filt.js":19,"../store/view.js":22,"../utils.js":23,"./flowdetail.js":8,"./flowtable.js":10,"./utils.js":15,"react":"react"}],14:[function(require,module,exports){
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


},{"../store/store.js":21,"./eventlog.js":7,"./footer.js":11,"./header.js":12,"./mainview.js":13,"./utils.js":15,"lodash":"lodash","react":"react","react-router":"react-router"}],15:[function(require,module,exports){
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
},{"lodash":"lodash","react":"react","react-router":"react-router"}],16:[function(require,module,exports){
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
},{"react":"react"}],17:[function(require,module,exports){

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
},{"./actions.js":5}],18:[function(require,module,exports){

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
},{"flux":2}],19:[function(require,module,exports){
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

},{}],20:[function(require,module,exports){
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
},{"lodash":"lodash"}],21:[function(require,module,exports){

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
},{"../actions.js":5,"../dispatcher.js":18,"../utils.js":23,"events":1,"jquery":"jquery","lodash":"lodash"}],22:[function(require,module,exports){

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
},{"../utils.js":23,"events":1,"lodash":"lodash"}],23:[function(require,module,exports){
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
},{"jquery":"jquery"}]},{},[6])
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIm5vZGVfbW9kdWxlcy9icm93c2VyaWZ5L25vZGVfbW9kdWxlcy9icm93c2VyLXBhY2svX3ByZWx1ZGUuanMiLCJub2RlX21vZHVsZXMvYnJvd3NlcmlmeS9ub2RlX21vZHVsZXMvZXZlbnRzL2V2ZW50cy5qcyIsIm5vZGVfbW9kdWxlcy9mbHV4L2luZGV4LmpzIiwibm9kZV9tb2R1bGVzL2ZsdXgvbGliL0Rpc3BhdGNoZXIuanMiLCJub2RlX21vZHVsZXMvZmx1eC9saWIvaW52YXJpYW50LmpzIiwic3JjL2pzL2FjdGlvbnMuanMiLCJzcmMvanMvYXBwLmpzIiwic3JjL2pzL2NvbXBvbmVudHMvZXZlbnRsb2cuanMiLCJzcmMvanMvY29tcG9uZW50cy9mbG93ZGV0YWlsLmpzIiwic3JjL2pzL2NvbXBvbmVudHMvZmxvd3RhYmxlLWNvbHVtbnMuanMiLCJzcmMvanMvY29tcG9uZW50cy9mbG93dGFibGUuanMiLCJzcmMvanMvY29tcG9uZW50cy9mb290ZXIuanMiLCJzcmMvanMvY29tcG9uZW50cy9oZWFkZXIuanMiLCJzcmMvanMvY29tcG9uZW50cy9tYWludmlldy5qcyIsInNyYy9qcy9jb21wb25lbnRzL3Byb3h5YXBwLmpzIiwic3JjL2pzL2NvbXBvbmVudHMvdXRpbHMuanMiLCJzcmMvanMvY29tcG9uZW50cy92aXJ0dWFsc2Nyb2xsLmpzIiwic3JjL2pzL2Nvbm5lY3Rpb24uanMiLCJzcmMvanMvZGlzcGF0Y2hlci5qcyIsInNyYy9qcy9maWx0L2ZpbHQuanMiLCJzcmMvanMvZmxvdy91dGlscy5qcyIsInNyYy9qcy9zdG9yZS9zdG9yZS5qcyIsInNyYy9qcy9zdG9yZS92aWV3LmpzIiwic3JjL2pzL3V0aWxzLmpzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiJBQUFBO0FDQUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUM3U0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUNWQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQzFQQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDckRBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUN2SEE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ2RBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDMUpBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUM5WUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ3BLQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ3hJQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ2hCQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ3BZQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ3hPQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDNUZBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ25NQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUNwRkE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDM0JBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQ3JCQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUNodkRBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUNqRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDcExBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FDN0dBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBIiwiZmlsZSI6ImdlbmVyYXRlZC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzQ29udGVudCI6WyIoZnVuY3Rpb24gZSh0LG4scil7ZnVuY3Rpb24gcyhvLHUpe2lmKCFuW29dKXtpZighdFtvXSl7dmFyIGE9dHlwZW9mIHJlcXVpcmU9PVwiZnVuY3Rpb25cIiYmcmVxdWlyZTtpZighdSYmYSlyZXR1cm4gYShvLCEwKTtpZihpKXJldHVybiBpKG8sITApO3ZhciBmPW5ldyBFcnJvcihcIkNhbm5vdCBmaW5kIG1vZHVsZSAnXCIrbytcIidcIik7dGhyb3cgZi5jb2RlPVwiTU9EVUxFX05PVF9GT1VORFwiLGZ9dmFyIGw9bltvXT17ZXhwb3J0czp7fX07dFtvXVswXS5jYWxsKGwuZXhwb3J0cyxmdW5jdGlvbihlKXt2YXIgbj10W29dWzFdW2VdO3JldHVybiBzKG4/bjplKX0sbCxsLmV4cG9ydHMsZSx0LG4scil9cmV0dXJuIG5bb10uZXhwb3J0c312YXIgaT10eXBlb2YgcmVxdWlyZT09XCJmdW5jdGlvblwiJiZyZXF1aXJlO2Zvcih2YXIgbz0wO288ci5sZW5ndGg7bysrKXMocltvXSk7cmV0dXJuIHN9KSIsIi8vIENvcHlyaWdodCBKb3llbnQsIEluYy4gYW5kIG90aGVyIE5vZGUgY29udHJpYnV0b3JzLlxuLy9cbi8vIFBlcm1pc3Npb24gaXMgaGVyZWJ5IGdyYW50ZWQsIGZyZWUgb2YgY2hhcmdlLCB0byBhbnkgcGVyc29uIG9idGFpbmluZyBhXG4vLyBjb3B5IG9mIHRoaXMgc29mdHdhcmUgYW5kIGFzc29jaWF0ZWQgZG9jdW1lbnRhdGlvbiBmaWxlcyAodGhlXG4vLyBcIlNvZnR3YXJlXCIpLCB0byBkZWFsIGluIHRoZSBTb2Z0d2FyZSB3aXRob3V0IHJlc3RyaWN0aW9uLCBpbmNsdWRpbmdcbi8vIHdpdGhvdXQgbGltaXRhdGlvbiB0aGUgcmlnaHRzIHRvIHVzZSwgY29weSwgbW9kaWZ5LCBtZXJnZSwgcHVibGlzaCxcbi8vIGRpc3RyaWJ1dGUsIHN1YmxpY2Vuc2UsIGFuZC9vciBzZWxsIGNvcGllcyBvZiB0aGUgU29mdHdhcmUsIGFuZCB0byBwZXJtaXRcbi8vIHBlcnNvbnMgdG8gd2hvbSB0aGUgU29mdHdhcmUgaXMgZnVybmlzaGVkIHRvIGRvIHNvLCBzdWJqZWN0IHRvIHRoZVxuLy8gZm9sbG93aW5nIGNvbmRpdGlvbnM6XG4vL1xuLy8gVGhlIGFib3ZlIGNvcHlyaWdodCBub3RpY2UgYW5kIHRoaXMgcGVybWlzc2lvbiBub3RpY2Ugc2hhbGwgYmUgaW5jbHVkZWRcbi8vIGluIGFsbCBjb3BpZXMgb3Igc3Vic3RhbnRpYWwgcG9ydGlvbnMgb2YgdGhlIFNvZnR3YXJlLlxuLy9cbi8vIFRIRSBTT0ZUV0FSRSBJUyBQUk9WSURFRCBcIkFTIElTXCIsIFdJVEhPVVQgV0FSUkFOVFkgT0YgQU5ZIEtJTkQsIEVYUFJFU1Ncbi8vIE9SIElNUExJRUQsIElOQ0xVRElORyBCVVQgTk9UIExJTUlURUQgVE8gVEhFIFdBUlJBTlRJRVMgT0Zcbi8vIE1FUkNIQU5UQUJJTElUWSwgRklUTkVTUyBGT1IgQSBQQVJUSUNVTEFSIFBVUlBPU0UgQU5EIE5PTklORlJJTkdFTUVOVC4gSU5cbi8vIE5PIEVWRU5UIFNIQUxMIFRIRSBBVVRIT1JTIE9SIENPUFlSSUdIVCBIT0xERVJTIEJFIExJQUJMRSBGT1IgQU5ZIENMQUlNLFxuLy8gREFNQUdFUyBPUiBPVEhFUiBMSUFCSUxJVFksIFdIRVRIRVIgSU4gQU4gQUNUSU9OIE9GIENPTlRSQUNULCBUT1JUIE9SXG4vLyBPVEhFUldJU0UsIEFSSVNJTkcgRlJPTSwgT1VUIE9GIE9SIElOIENPTk5FQ1RJT04gV0lUSCBUSEUgU09GVFdBUkUgT1IgVEhFXG4vLyBVU0UgT1IgT1RIRVIgREVBTElOR1MgSU4gVEhFIFNPRlRXQVJFLlxuXG5mdW5jdGlvbiBFdmVudEVtaXR0ZXIoKSB7XG4gIHRoaXMuX2V2ZW50cyA9IHRoaXMuX2V2ZW50cyB8fCB7fTtcbiAgdGhpcy5fbWF4TGlzdGVuZXJzID0gdGhpcy5fbWF4TGlzdGVuZXJzIHx8IHVuZGVmaW5lZDtcbn1cbm1vZHVsZS5leHBvcnRzID0gRXZlbnRFbWl0dGVyO1xuXG4vLyBCYWNrd2FyZHMtY29tcGF0IHdpdGggbm9kZSAwLjEwLnhcbkV2ZW50RW1pdHRlci5FdmVudEVtaXR0ZXIgPSBFdmVudEVtaXR0ZXI7XG5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUuX2V2ZW50cyA9IHVuZGVmaW5lZDtcbkV2ZW50RW1pdHRlci5wcm90b3R5cGUuX21heExpc3RlbmVycyA9IHVuZGVmaW5lZDtcblxuLy8gQnkgZGVmYXVsdCBFdmVudEVtaXR0ZXJzIHdpbGwgcHJpbnQgYSB3YXJuaW5nIGlmIG1vcmUgdGhhbiAxMCBsaXN0ZW5lcnMgYXJlXG4vLyBhZGRlZCB0byBpdC4gVGhpcyBpcyBhIHVzZWZ1bCBkZWZhdWx0IHdoaWNoIGhlbHBzIGZpbmRpbmcgbWVtb3J5IGxlYWtzLlxuRXZlbnRFbWl0dGVyLmRlZmF1bHRNYXhMaXN0ZW5lcnMgPSAxMDtcblxuLy8gT2J2aW91c2x5IG5vdCBhbGwgRW1pdHRlcnMgc2hvdWxkIGJlIGxpbWl0ZWQgdG8gMTAuIFRoaXMgZnVuY3Rpb24gYWxsb3dzXG4vLyB0aGF0IHRvIGJlIGluY3JlYXNlZC4gU2V0IHRvIHplcm8gZm9yIHVubGltaXRlZC5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUuc2V0TWF4TGlzdGVuZXJzID0gZnVuY3Rpb24obikge1xuICBpZiAoIWlzTnVtYmVyKG4pIHx8IG4gPCAwIHx8IGlzTmFOKG4pKVxuICAgIHRocm93IFR5cGVFcnJvcignbiBtdXN0IGJlIGEgcG9zaXRpdmUgbnVtYmVyJyk7XG4gIHRoaXMuX21heExpc3RlbmVycyA9IG47XG4gIHJldHVybiB0aGlzO1xufTtcblxuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5lbWl0ID0gZnVuY3Rpb24odHlwZSkge1xuICB2YXIgZXIsIGhhbmRsZXIsIGxlbiwgYXJncywgaSwgbGlzdGVuZXJzO1xuXG4gIGlmICghdGhpcy5fZXZlbnRzKVxuICAgIHRoaXMuX2V2ZW50cyA9IHt9O1xuXG4gIC8vIElmIHRoZXJlIGlzIG5vICdlcnJvcicgZXZlbnQgbGlzdGVuZXIgdGhlbiB0aHJvdy5cbiAgaWYgKHR5cGUgPT09ICdlcnJvcicpIHtcbiAgICBpZiAoIXRoaXMuX2V2ZW50cy5lcnJvciB8fFxuICAgICAgICAoaXNPYmplY3QodGhpcy5fZXZlbnRzLmVycm9yKSAmJiAhdGhpcy5fZXZlbnRzLmVycm9yLmxlbmd0aCkpIHtcbiAgICAgIGVyID0gYXJndW1lbnRzWzFdO1xuICAgICAgaWYgKGVyIGluc3RhbmNlb2YgRXJyb3IpIHtcbiAgICAgICAgdGhyb3cgZXI7IC8vIFVuaGFuZGxlZCAnZXJyb3InIGV2ZW50XG4gICAgICB9XG4gICAgICB0aHJvdyBUeXBlRXJyb3IoJ1VuY2F1Z2h0LCB1bnNwZWNpZmllZCBcImVycm9yXCIgZXZlbnQuJyk7XG4gICAgfVxuICB9XG5cbiAgaGFuZGxlciA9IHRoaXMuX2V2ZW50c1t0eXBlXTtcblxuICBpZiAoaXNVbmRlZmluZWQoaGFuZGxlcikpXG4gICAgcmV0dXJuIGZhbHNlO1xuXG4gIGlmIChpc0Z1bmN0aW9uKGhhbmRsZXIpKSB7XG4gICAgc3dpdGNoIChhcmd1bWVudHMubGVuZ3RoKSB7XG4gICAgICAvLyBmYXN0IGNhc2VzXG4gICAgICBjYXNlIDE6XG4gICAgICAgIGhhbmRsZXIuY2FsbCh0aGlzKTtcbiAgICAgICAgYnJlYWs7XG4gICAgICBjYXNlIDI6XG4gICAgICAgIGhhbmRsZXIuY2FsbCh0aGlzLCBhcmd1bWVudHNbMV0pO1xuICAgICAgICBicmVhaztcbiAgICAgIGNhc2UgMzpcbiAgICAgICAgaGFuZGxlci5jYWxsKHRoaXMsIGFyZ3VtZW50c1sxXSwgYXJndW1lbnRzWzJdKTtcbiAgICAgICAgYnJlYWs7XG4gICAgICAvLyBzbG93ZXJcbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIGxlbiA9IGFyZ3VtZW50cy5sZW5ndGg7XG4gICAgICAgIGFyZ3MgPSBuZXcgQXJyYXkobGVuIC0gMSk7XG4gICAgICAgIGZvciAoaSA9IDE7IGkgPCBsZW47IGkrKylcbiAgICAgICAgICBhcmdzW2kgLSAxXSA9IGFyZ3VtZW50c1tpXTtcbiAgICAgICAgaGFuZGxlci5hcHBseSh0aGlzLCBhcmdzKTtcbiAgICB9XG4gIH0gZWxzZSBpZiAoaXNPYmplY3QoaGFuZGxlcikpIHtcbiAgICBsZW4gPSBhcmd1bWVudHMubGVuZ3RoO1xuICAgIGFyZ3MgPSBuZXcgQXJyYXkobGVuIC0gMSk7XG4gICAgZm9yIChpID0gMTsgaSA8IGxlbjsgaSsrKVxuICAgICAgYXJnc1tpIC0gMV0gPSBhcmd1bWVudHNbaV07XG5cbiAgICBsaXN0ZW5lcnMgPSBoYW5kbGVyLnNsaWNlKCk7XG4gICAgbGVuID0gbGlzdGVuZXJzLmxlbmd0aDtcbiAgICBmb3IgKGkgPSAwOyBpIDwgbGVuOyBpKyspXG4gICAgICBsaXN0ZW5lcnNbaV0uYXBwbHkodGhpcywgYXJncyk7XG4gIH1cblxuICByZXR1cm4gdHJ1ZTtcbn07XG5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUuYWRkTGlzdGVuZXIgPSBmdW5jdGlvbih0eXBlLCBsaXN0ZW5lcikge1xuICB2YXIgbTtcblxuICBpZiAoIWlzRnVuY3Rpb24obGlzdGVuZXIpKVxuICAgIHRocm93IFR5cGVFcnJvcignbGlzdGVuZXIgbXVzdCBiZSBhIGZ1bmN0aW9uJyk7XG5cbiAgaWYgKCF0aGlzLl9ldmVudHMpXG4gICAgdGhpcy5fZXZlbnRzID0ge307XG5cbiAgLy8gVG8gYXZvaWQgcmVjdXJzaW9uIGluIHRoZSBjYXNlIHRoYXQgdHlwZSA9PT0gXCJuZXdMaXN0ZW5lclwiISBCZWZvcmVcbiAgLy8gYWRkaW5nIGl0IHRvIHRoZSBsaXN0ZW5lcnMsIGZpcnN0IGVtaXQgXCJuZXdMaXN0ZW5lclwiLlxuICBpZiAodGhpcy5fZXZlbnRzLm5ld0xpc3RlbmVyKVxuICAgIHRoaXMuZW1pdCgnbmV3TGlzdGVuZXInLCB0eXBlLFxuICAgICAgICAgICAgICBpc0Z1bmN0aW9uKGxpc3RlbmVyLmxpc3RlbmVyKSA/XG4gICAgICAgICAgICAgIGxpc3RlbmVyLmxpc3RlbmVyIDogbGlzdGVuZXIpO1xuXG4gIGlmICghdGhpcy5fZXZlbnRzW3R5cGVdKVxuICAgIC8vIE9wdGltaXplIHRoZSBjYXNlIG9mIG9uZSBsaXN0ZW5lci4gRG9uJ3QgbmVlZCB0aGUgZXh0cmEgYXJyYXkgb2JqZWN0LlxuICAgIHRoaXMuX2V2ZW50c1t0eXBlXSA9IGxpc3RlbmVyO1xuICBlbHNlIGlmIChpc09iamVjdCh0aGlzLl9ldmVudHNbdHlwZV0pKVxuICAgIC8vIElmIHdlJ3ZlIGFscmVhZHkgZ290IGFuIGFycmF5LCBqdXN0IGFwcGVuZC5cbiAgICB0aGlzLl9ldmVudHNbdHlwZV0ucHVzaChsaXN0ZW5lcik7XG4gIGVsc2VcbiAgICAvLyBBZGRpbmcgdGhlIHNlY29uZCBlbGVtZW50LCBuZWVkIHRvIGNoYW5nZSB0byBhcnJheS5cbiAgICB0aGlzLl9ldmVudHNbdHlwZV0gPSBbdGhpcy5fZXZlbnRzW3R5cGVdLCBsaXN0ZW5lcl07XG5cbiAgLy8gQ2hlY2sgZm9yIGxpc3RlbmVyIGxlYWtcbiAgaWYgKGlzT2JqZWN0KHRoaXMuX2V2ZW50c1t0eXBlXSkgJiYgIXRoaXMuX2V2ZW50c1t0eXBlXS53YXJuZWQpIHtcbiAgICB2YXIgbTtcbiAgICBpZiAoIWlzVW5kZWZpbmVkKHRoaXMuX21heExpc3RlbmVycykpIHtcbiAgICAgIG0gPSB0aGlzLl9tYXhMaXN0ZW5lcnM7XG4gICAgfSBlbHNlIHtcbiAgICAgIG0gPSBFdmVudEVtaXR0ZXIuZGVmYXVsdE1heExpc3RlbmVycztcbiAgICB9XG5cbiAgICBpZiAobSAmJiBtID4gMCAmJiB0aGlzLl9ldmVudHNbdHlwZV0ubGVuZ3RoID4gbSkge1xuICAgICAgdGhpcy5fZXZlbnRzW3R5cGVdLndhcm5lZCA9IHRydWU7XG4gICAgICBjb25zb2xlLmVycm9yKCcobm9kZSkgd2FybmluZzogcG9zc2libGUgRXZlbnRFbWl0dGVyIG1lbW9yeSAnICtcbiAgICAgICAgICAgICAgICAgICAgJ2xlYWsgZGV0ZWN0ZWQuICVkIGxpc3RlbmVycyBhZGRlZC4gJyArXG4gICAgICAgICAgICAgICAgICAgICdVc2UgZW1pdHRlci5zZXRNYXhMaXN0ZW5lcnMoKSB0byBpbmNyZWFzZSBsaW1pdC4nLFxuICAgICAgICAgICAgICAgICAgICB0aGlzLl9ldmVudHNbdHlwZV0ubGVuZ3RoKTtcbiAgICAgIGlmICh0eXBlb2YgY29uc29sZS50cmFjZSA9PT0gJ2Z1bmN0aW9uJykge1xuICAgICAgICAvLyBub3Qgc3VwcG9ydGVkIGluIElFIDEwXG4gICAgICAgIGNvbnNvbGUudHJhY2UoKTtcbiAgICAgIH1cbiAgICB9XG4gIH1cblxuICByZXR1cm4gdGhpcztcbn07XG5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUub24gPSBFdmVudEVtaXR0ZXIucHJvdG90eXBlLmFkZExpc3RlbmVyO1xuXG5FdmVudEVtaXR0ZXIucHJvdG90eXBlLm9uY2UgPSBmdW5jdGlvbih0eXBlLCBsaXN0ZW5lcikge1xuICBpZiAoIWlzRnVuY3Rpb24obGlzdGVuZXIpKVxuICAgIHRocm93IFR5cGVFcnJvcignbGlzdGVuZXIgbXVzdCBiZSBhIGZ1bmN0aW9uJyk7XG5cbiAgdmFyIGZpcmVkID0gZmFsc2U7XG5cbiAgZnVuY3Rpb24gZygpIHtcbiAgICB0aGlzLnJlbW92ZUxpc3RlbmVyKHR5cGUsIGcpO1xuXG4gICAgaWYgKCFmaXJlZCkge1xuICAgICAgZmlyZWQgPSB0cnVlO1xuICAgICAgbGlzdGVuZXIuYXBwbHkodGhpcywgYXJndW1lbnRzKTtcbiAgICB9XG4gIH1cblxuICBnLmxpc3RlbmVyID0gbGlzdGVuZXI7XG4gIHRoaXMub24odHlwZSwgZyk7XG5cbiAgcmV0dXJuIHRoaXM7XG59O1xuXG4vLyBlbWl0cyBhICdyZW1vdmVMaXN0ZW5lcicgZXZlbnQgaWZmIHRoZSBsaXN0ZW5lciB3YXMgcmVtb3ZlZFxuRXZlbnRFbWl0dGVyLnByb3RvdHlwZS5yZW1vdmVMaXN0ZW5lciA9IGZ1bmN0aW9uKHR5cGUsIGxpc3RlbmVyKSB7XG4gIHZhciBsaXN0LCBwb3NpdGlvbiwgbGVuZ3RoLCBpO1xuXG4gIGlmICghaXNGdW5jdGlvbihsaXN0ZW5lcikpXG4gICAgdGhyb3cgVHlwZUVycm9yKCdsaXN0ZW5lciBtdXN0IGJlIGEgZnVuY3Rpb24nKTtcblxuICBpZiAoIXRoaXMuX2V2ZW50cyB8fCAhdGhpcy5fZXZlbnRzW3R5cGVdKVxuICAgIHJldHVybiB0aGlzO1xuXG4gIGxpc3QgPSB0aGlzLl9ldmVudHNbdHlwZV07XG4gIGxlbmd0aCA9IGxpc3QubGVuZ3RoO1xuICBwb3NpdGlvbiA9IC0xO1xuXG4gIGlmIChsaXN0ID09PSBsaXN0ZW5lciB8fFxuICAgICAgKGlzRnVuY3Rpb24obGlzdC5saXN0ZW5lcikgJiYgbGlzdC5saXN0ZW5lciA9PT0gbGlzdGVuZXIpKSB7XG4gICAgZGVsZXRlIHRoaXMuX2V2ZW50c1t0eXBlXTtcbiAgICBpZiAodGhpcy5fZXZlbnRzLnJlbW92ZUxpc3RlbmVyKVxuICAgICAgdGhpcy5lbWl0KCdyZW1vdmVMaXN0ZW5lcicsIHR5cGUsIGxpc3RlbmVyKTtcblxuICB9IGVsc2UgaWYgKGlzT2JqZWN0KGxpc3QpKSB7XG4gICAgZm9yIChpID0gbGVuZ3RoOyBpLS0gPiAwOykge1xuICAgICAgaWYgKGxpc3RbaV0gPT09IGxpc3RlbmVyIHx8XG4gICAgICAgICAgKGxpc3RbaV0ubGlzdGVuZXIgJiYgbGlzdFtpXS5saXN0ZW5lciA9PT0gbGlzdGVuZXIpKSB7XG4gICAgICAgIHBvc2l0aW9uID0gaTtcbiAgICAgICAgYnJlYWs7XG4gICAgICB9XG4gICAgfVxuXG4gICAgaWYgKHBvc2l0aW9uIDwgMClcbiAgICAgIHJldHVybiB0aGlzO1xuXG4gICAgaWYgKGxpc3QubGVuZ3RoID09PSAxKSB7XG4gICAgICBsaXN0Lmxlbmd0aCA9IDA7XG4gICAgICBkZWxldGUgdGhpcy5fZXZlbnRzW3R5cGVdO1xuICAgIH0gZWxzZSB7XG4gICAgICBsaXN0LnNwbGljZShwb3NpdGlvbiwgMSk7XG4gICAgfVxuXG4gICAgaWYgKHRoaXMuX2V2ZW50cy5yZW1vdmVMaXN0ZW5lcilcbiAgICAgIHRoaXMuZW1pdCgncmVtb3ZlTGlzdGVuZXInLCB0eXBlLCBsaXN0ZW5lcik7XG4gIH1cblxuICByZXR1cm4gdGhpcztcbn07XG5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUucmVtb3ZlQWxsTGlzdGVuZXJzID0gZnVuY3Rpb24odHlwZSkge1xuICB2YXIga2V5LCBsaXN0ZW5lcnM7XG5cbiAgaWYgKCF0aGlzLl9ldmVudHMpXG4gICAgcmV0dXJuIHRoaXM7XG5cbiAgLy8gbm90IGxpc3RlbmluZyBmb3IgcmVtb3ZlTGlzdGVuZXIsIG5vIG5lZWQgdG8gZW1pdFxuICBpZiAoIXRoaXMuX2V2ZW50cy5yZW1vdmVMaXN0ZW5lcikge1xuICAgIGlmIChhcmd1bWVudHMubGVuZ3RoID09PSAwKVxuICAgICAgdGhpcy5fZXZlbnRzID0ge307XG4gICAgZWxzZSBpZiAodGhpcy5fZXZlbnRzW3R5cGVdKVxuICAgICAgZGVsZXRlIHRoaXMuX2V2ZW50c1t0eXBlXTtcbiAgICByZXR1cm4gdGhpcztcbiAgfVxuXG4gIC8vIGVtaXQgcmVtb3ZlTGlzdGVuZXIgZm9yIGFsbCBsaXN0ZW5lcnMgb24gYWxsIGV2ZW50c1xuICBpZiAoYXJndW1lbnRzLmxlbmd0aCA9PT0gMCkge1xuICAgIGZvciAoa2V5IGluIHRoaXMuX2V2ZW50cykge1xuICAgICAgaWYgKGtleSA9PT0gJ3JlbW92ZUxpc3RlbmVyJykgY29udGludWU7XG4gICAgICB0aGlzLnJlbW92ZUFsbExpc3RlbmVycyhrZXkpO1xuICAgIH1cbiAgICB0aGlzLnJlbW92ZUFsbExpc3RlbmVycygncmVtb3ZlTGlzdGVuZXInKTtcbiAgICB0aGlzLl9ldmVudHMgPSB7fTtcbiAgICByZXR1cm4gdGhpcztcbiAgfVxuXG4gIGxpc3RlbmVycyA9IHRoaXMuX2V2ZW50c1t0eXBlXTtcblxuICBpZiAoaXNGdW5jdGlvbihsaXN0ZW5lcnMpKSB7XG4gICAgdGhpcy5yZW1vdmVMaXN0ZW5lcih0eXBlLCBsaXN0ZW5lcnMpO1xuICB9IGVsc2Uge1xuICAgIC8vIExJRk8gb3JkZXJcbiAgICB3aGlsZSAobGlzdGVuZXJzLmxlbmd0aClcbiAgICAgIHRoaXMucmVtb3ZlTGlzdGVuZXIodHlwZSwgbGlzdGVuZXJzW2xpc3RlbmVycy5sZW5ndGggLSAxXSk7XG4gIH1cbiAgZGVsZXRlIHRoaXMuX2V2ZW50c1t0eXBlXTtcblxuICByZXR1cm4gdGhpcztcbn07XG5cbkV2ZW50RW1pdHRlci5wcm90b3R5cGUubGlzdGVuZXJzID0gZnVuY3Rpb24odHlwZSkge1xuICB2YXIgcmV0O1xuICBpZiAoIXRoaXMuX2V2ZW50cyB8fCAhdGhpcy5fZXZlbnRzW3R5cGVdKVxuICAgIHJldCA9IFtdO1xuICBlbHNlIGlmIChpc0Z1bmN0aW9uKHRoaXMuX2V2ZW50c1t0eXBlXSkpXG4gICAgcmV0ID0gW3RoaXMuX2V2ZW50c1t0eXBlXV07XG4gIGVsc2VcbiAgICByZXQgPSB0aGlzLl9ldmVudHNbdHlwZV0uc2xpY2UoKTtcbiAgcmV0dXJuIHJldDtcbn07XG5cbkV2ZW50RW1pdHRlci5saXN0ZW5lckNvdW50ID0gZnVuY3Rpb24oZW1pdHRlciwgdHlwZSkge1xuICB2YXIgcmV0O1xuICBpZiAoIWVtaXR0ZXIuX2V2ZW50cyB8fCAhZW1pdHRlci5fZXZlbnRzW3R5cGVdKVxuICAgIHJldCA9IDA7XG4gIGVsc2UgaWYgKGlzRnVuY3Rpb24oZW1pdHRlci5fZXZlbnRzW3R5cGVdKSlcbiAgICByZXQgPSAxO1xuICBlbHNlXG4gICAgcmV0ID0gZW1pdHRlci5fZXZlbnRzW3R5cGVdLmxlbmd0aDtcbiAgcmV0dXJuIHJldDtcbn07XG5cbmZ1bmN0aW9uIGlzRnVuY3Rpb24oYXJnKSB7XG4gIHJldHVybiB0eXBlb2YgYXJnID09PSAnZnVuY3Rpb24nO1xufVxuXG5mdW5jdGlvbiBpc051bWJlcihhcmcpIHtcbiAgcmV0dXJuIHR5cGVvZiBhcmcgPT09ICdudW1iZXInO1xufVxuXG5mdW5jdGlvbiBpc09iamVjdChhcmcpIHtcbiAgcmV0dXJuIHR5cGVvZiBhcmcgPT09ICdvYmplY3QnICYmIGFyZyAhPT0gbnVsbDtcbn1cblxuZnVuY3Rpb24gaXNVbmRlZmluZWQoYXJnKSB7XG4gIHJldHVybiBhcmcgPT09IHZvaWQgMDtcbn1cbiIsIi8qKlxuICogQ29weXJpZ2h0IChjKSAyMDE0LCBGYWNlYm9vaywgSW5jLlxuICogQWxsIHJpZ2h0cyByZXNlcnZlZC5cbiAqXG4gKiBUaGlzIHNvdXJjZSBjb2RlIGlzIGxpY2Vuc2VkIHVuZGVyIHRoZSBCU0Qtc3R5bGUgbGljZW5zZSBmb3VuZCBpbiB0aGVcbiAqIExJQ0VOU0UgZmlsZSBpbiB0aGUgcm9vdCBkaXJlY3Rvcnkgb2YgdGhpcyBzb3VyY2UgdHJlZS4gQW4gYWRkaXRpb25hbCBncmFudFxuICogb2YgcGF0ZW50IHJpZ2h0cyBjYW4gYmUgZm91bmQgaW4gdGhlIFBBVEVOVFMgZmlsZSBpbiB0aGUgc2FtZSBkaXJlY3RvcnkuXG4gKi9cblxubW9kdWxlLmV4cG9ydHMuRGlzcGF0Y2hlciA9IHJlcXVpcmUoJy4vbGliL0Rpc3BhdGNoZXInKVxuIiwiLypcbiAqIENvcHlyaWdodCAoYykgMjAxNCwgRmFjZWJvb2ssIEluYy5cbiAqIEFsbCByaWdodHMgcmVzZXJ2ZWQuXG4gKlxuICogVGhpcyBzb3VyY2UgY29kZSBpcyBsaWNlbnNlZCB1bmRlciB0aGUgQlNELXN0eWxlIGxpY2Vuc2UgZm91bmQgaW4gdGhlXG4gKiBMSUNFTlNFIGZpbGUgaW4gdGhlIHJvb3QgZGlyZWN0b3J5IG9mIHRoaXMgc291cmNlIHRyZWUuIEFuIGFkZGl0aW9uYWwgZ3JhbnRcbiAqIG9mIHBhdGVudCByaWdodHMgY2FuIGJlIGZvdW5kIGluIHRoZSBQQVRFTlRTIGZpbGUgaW4gdGhlIHNhbWUgZGlyZWN0b3J5LlxuICpcbiAqIEBwcm92aWRlc01vZHVsZSBEaXNwYXRjaGVyXG4gKiBAdHlwZWNoZWNrc1xuICovXG5cblwidXNlIHN0cmljdFwiO1xuXG52YXIgaW52YXJpYW50ID0gcmVxdWlyZSgnLi9pbnZhcmlhbnQnKTtcblxudmFyIF9sYXN0SUQgPSAxO1xudmFyIF9wcmVmaXggPSAnSURfJztcblxuLyoqXG4gKiBEaXNwYXRjaGVyIGlzIHVzZWQgdG8gYnJvYWRjYXN0IHBheWxvYWRzIHRvIHJlZ2lzdGVyZWQgY2FsbGJhY2tzLiBUaGlzIGlzXG4gKiBkaWZmZXJlbnQgZnJvbSBnZW5lcmljIHB1Yi1zdWIgc3lzdGVtcyBpbiB0d28gd2F5czpcbiAqXG4gKiAgIDEpIENhbGxiYWNrcyBhcmUgbm90IHN1YnNjcmliZWQgdG8gcGFydGljdWxhciBldmVudHMuIEV2ZXJ5IHBheWxvYWQgaXNcbiAqICAgICAgZGlzcGF0Y2hlZCB0byBldmVyeSByZWdpc3RlcmVkIGNhbGxiYWNrLlxuICogICAyKSBDYWxsYmFja3MgY2FuIGJlIGRlZmVycmVkIGluIHdob2xlIG9yIHBhcnQgdW50aWwgb3RoZXIgY2FsbGJhY2tzIGhhdmVcbiAqICAgICAgYmVlbiBleGVjdXRlZC5cbiAqXG4gKiBGb3IgZXhhbXBsZSwgY29uc2lkZXIgdGhpcyBoeXBvdGhldGljYWwgZmxpZ2h0IGRlc3RpbmF0aW9uIGZvcm0sIHdoaWNoXG4gKiBzZWxlY3RzIGEgZGVmYXVsdCBjaXR5IHdoZW4gYSBjb3VudHJ5IGlzIHNlbGVjdGVkOlxuICpcbiAqICAgdmFyIGZsaWdodERpc3BhdGNoZXIgPSBuZXcgRGlzcGF0Y2hlcigpO1xuICpcbiAqICAgLy8gS2VlcHMgdHJhY2sgb2Ygd2hpY2ggY291bnRyeSBpcyBzZWxlY3RlZFxuICogICB2YXIgQ291bnRyeVN0b3JlID0ge2NvdW50cnk6IG51bGx9O1xuICpcbiAqICAgLy8gS2VlcHMgdHJhY2sgb2Ygd2hpY2ggY2l0eSBpcyBzZWxlY3RlZFxuICogICB2YXIgQ2l0eVN0b3JlID0ge2NpdHk6IG51bGx9O1xuICpcbiAqICAgLy8gS2VlcHMgdHJhY2sgb2YgdGhlIGJhc2UgZmxpZ2h0IHByaWNlIG9mIHRoZSBzZWxlY3RlZCBjaXR5XG4gKiAgIHZhciBGbGlnaHRQcmljZVN0b3JlID0ge3ByaWNlOiBudWxsfVxuICpcbiAqIFdoZW4gYSB1c2VyIGNoYW5nZXMgdGhlIHNlbGVjdGVkIGNpdHksIHdlIGRpc3BhdGNoIHRoZSBwYXlsb2FkOlxuICpcbiAqICAgZmxpZ2h0RGlzcGF0Y2hlci5kaXNwYXRjaCh7XG4gKiAgICAgYWN0aW9uVHlwZTogJ2NpdHktdXBkYXRlJyxcbiAqICAgICBzZWxlY3RlZENpdHk6ICdwYXJpcydcbiAqICAgfSk7XG4gKlxuICogVGhpcyBwYXlsb2FkIGlzIGRpZ2VzdGVkIGJ5IGBDaXR5U3RvcmVgOlxuICpcbiAqICAgZmxpZ2h0RGlzcGF0Y2hlci5yZWdpc3RlcihmdW5jdGlvbihwYXlsb2FkKSB7XG4gKiAgICAgaWYgKHBheWxvYWQuYWN0aW9uVHlwZSA9PT0gJ2NpdHktdXBkYXRlJykge1xuICogICAgICAgQ2l0eVN0b3JlLmNpdHkgPSBwYXlsb2FkLnNlbGVjdGVkQ2l0eTtcbiAqICAgICB9XG4gKiAgIH0pO1xuICpcbiAqIFdoZW4gdGhlIHVzZXIgc2VsZWN0cyBhIGNvdW50cnksIHdlIGRpc3BhdGNoIHRoZSBwYXlsb2FkOlxuICpcbiAqICAgZmxpZ2h0RGlzcGF0Y2hlci5kaXNwYXRjaCh7XG4gKiAgICAgYWN0aW9uVHlwZTogJ2NvdW50cnktdXBkYXRlJyxcbiAqICAgICBzZWxlY3RlZENvdW50cnk6ICdhdXN0cmFsaWEnXG4gKiAgIH0pO1xuICpcbiAqIFRoaXMgcGF5bG9hZCBpcyBkaWdlc3RlZCBieSBib3RoIHN0b3JlczpcbiAqXG4gKiAgICBDb3VudHJ5U3RvcmUuZGlzcGF0Y2hUb2tlbiA9IGZsaWdodERpc3BhdGNoZXIucmVnaXN0ZXIoZnVuY3Rpb24ocGF5bG9hZCkge1xuICogICAgIGlmIChwYXlsb2FkLmFjdGlvblR5cGUgPT09ICdjb3VudHJ5LXVwZGF0ZScpIHtcbiAqICAgICAgIENvdW50cnlTdG9yZS5jb3VudHJ5ID0gcGF5bG9hZC5zZWxlY3RlZENvdW50cnk7XG4gKiAgICAgfVxuICogICB9KTtcbiAqXG4gKiBXaGVuIHRoZSBjYWxsYmFjayB0byB1cGRhdGUgYENvdW50cnlTdG9yZWAgaXMgcmVnaXN0ZXJlZCwgd2Ugc2F2ZSBhIHJlZmVyZW5jZVxuICogdG8gdGhlIHJldHVybmVkIHRva2VuLiBVc2luZyB0aGlzIHRva2VuIHdpdGggYHdhaXRGb3IoKWAsIHdlIGNhbiBndWFyYW50ZWVcbiAqIHRoYXQgYENvdW50cnlTdG9yZWAgaXMgdXBkYXRlZCBiZWZvcmUgdGhlIGNhbGxiYWNrIHRoYXQgdXBkYXRlcyBgQ2l0eVN0b3JlYFxuICogbmVlZHMgdG8gcXVlcnkgaXRzIGRhdGEuXG4gKlxuICogICBDaXR5U3RvcmUuZGlzcGF0Y2hUb2tlbiA9IGZsaWdodERpc3BhdGNoZXIucmVnaXN0ZXIoZnVuY3Rpb24ocGF5bG9hZCkge1xuICogICAgIGlmIChwYXlsb2FkLmFjdGlvblR5cGUgPT09ICdjb3VudHJ5LXVwZGF0ZScpIHtcbiAqICAgICAgIC8vIGBDb3VudHJ5U3RvcmUuY291bnRyeWAgbWF5IG5vdCBiZSB1cGRhdGVkLlxuICogICAgICAgZmxpZ2h0RGlzcGF0Y2hlci53YWl0Rm9yKFtDb3VudHJ5U3RvcmUuZGlzcGF0Y2hUb2tlbl0pO1xuICogICAgICAgLy8gYENvdW50cnlTdG9yZS5jb3VudHJ5YCBpcyBub3cgZ3VhcmFudGVlZCB0byBiZSB1cGRhdGVkLlxuICpcbiAqICAgICAgIC8vIFNlbGVjdCB0aGUgZGVmYXVsdCBjaXR5IGZvciB0aGUgbmV3IGNvdW50cnlcbiAqICAgICAgIENpdHlTdG9yZS5jaXR5ID0gZ2V0RGVmYXVsdENpdHlGb3JDb3VudHJ5KENvdW50cnlTdG9yZS5jb3VudHJ5KTtcbiAqICAgICB9XG4gKiAgIH0pO1xuICpcbiAqIFRoZSB1c2FnZSBvZiBgd2FpdEZvcigpYCBjYW4gYmUgY2hhaW5lZCwgZm9yIGV4YW1wbGU6XG4gKlxuICogICBGbGlnaHRQcmljZVN0b3JlLmRpc3BhdGNoVG9rZW4gPVxuICogICAgIGZsaWdodERpc3BhdGNoZXIucmVnaXN0ZXIoZnVuY3Rpb24ocGF5bG9hZCkge1xuICogICAgICAgc3dpdGNoIChwYXlsb2FkLmFjdGlvblR5cGUpIHtcbiAqICAgICAgICAgY2FzZSAnY291bnRyeS11cGRhdGUnOlxuICogICAgICAgICAgIGZsaWdodERpc3BhdGNoZXIud2FpdEZvcihbQ2l0eVN0b3JlLmRpc3BhdGNoVG9rZW5dKTtcbiAqICAgICAgICAgICBGbGlnaHRQcmljZVN0b3JlLnByaWNlID1cbiAqICAgICAgICAgICAgIGdldEZsaWdodFByaWNlU3RvcmUoQ291bnRyeVN0b3JlLmNvdW50cnksIENpdHlTdG9yZS5jaXR5KTtcbiAqICAgICAgICAgICBicmVhaztcbiAqXG4gKiAgICAgICAgIGNhc2UgJ2NpdHktdXBkYXRlJzpcbiAqICAgICAgICAgICBGbGlnaHRQcmljZVN0b3JlLnByaWNlID1cbiAqICAgICAgICAgICAgIEZsaWdodFByaWNlU3RvcmUoQ291bnRyeVN0b3JlLmNvdW50cnksIENpdHlTdG9yZS5jaXR5KTtcbiAqICAgICAgICAgICBicmVhaztcbiAqICAgICB9XG4gKiAgIH0pO1xuICpcbiAqIFRoZSBgY291bnRyeS11cGRhdGVgIHBheWxvYWQgd2lsbCBiZSBndWFyYW50ZWVkIHRvIGludm9rZSB0aGUgc3RvcmVzJ1xuICogcmVnaXN0ZXJlZCBjYWxsYmFja3MgaW4gb3JkZXI6IGBDb3VudHJ5U3RvcmVgLCBgQ2l0eVN0b3JlYCwgdGhlblxuICogYEZsaWdodFByaWNlU3RvcmVgLlxuICovXG5cbiAgZnVuY3Rpb24gRGlzcGF0Y2hlcigpIHtcbiAgICB0aGlzLiREaXNwYXRjaGVyX2NhbGxiYWNrcyA9IHt9O1xuICAgIHRoaXMuJERpc3BhdGNoZXJfaXNQZW5kaW5nID0ge307XG4gICAgdGhpcy4kRGlzcGF0Y2hlcl9pc0hhbmRsZWQgPSB7fTtcbiAgICB0aGlzLiREaXNwYXRjaGVyX2lzRGlzcGF0Y2hpbmcgPSBmYWxzZTtcbiAgICB0aGlzLiREaXNwYXRjaGVyX3BlbmRpbmdQYXlsb2FkID0gbnVsbDtcbiAgfVxuXG4gIC8qKlxuICAgKiBSZWdpc3RlcnMgYSBjYWxsYmFjayB0byBiZSBpbnZva2VkIHdpdGggZXZlcnkgZGlzcGF0Y2hlZCBwYXlsb2FkLiBSZXR1cm5zXG4gICAqIGEgdG9rZW4gdGhhdCBjYW4gYmUgdXNlZCB3aXRoIGB3YWl0Rm9yKClgLlxuICAgKlxuICAgKiBAcGFyYW0ge2Z1bmN0aW9ufSBjYWxsYmFja1xuICAgKiBAcmV0dXJuIHtzdHJpbmd9XG4gICAqL1xuICBEaXNwYXRjaGVyLnByb3RvdHlwZS5yZWdpc3Rlcj1mdW5jdGlvbihjYWxsYmFjaykge1xuICAgIHZhciBpZCA9IF9wcmVmaXggKyBfbGFzdElEKys7XG4gICAgdGhpcy4kRGlzcGF0Y2hlcl9jYWxsYmFja3NbaWRdID0gY2FsbGJhY2s7XG4gICAgcmV0dXJuIGlkO1xuICB9O1xuXG4gIC8qKlxuICAgKiBSZW1vdmVzIGEgY2FsbGJhY2sgYmFzZWQgb24gaXRzIHRva2VuLlxuICAgKlxuICAgKiBAcGFyYW0ge3N0cmluZ30gaWRcbiAgICovXG4gIERpc3BhdGNoZXIucHJvdG90eXBlLnVucmVnaXN0ZXI9ZnVuY3Rpb24oaWQpIHtcbiAgICBpbnZhcmlhbnQoXG4gICAgICB0aGlzLiREaXNwYXRjaGVyX2NhbGxiYWNrc1tpZF0sXG4gICAgICAnRGlzcGF0Y2hlci51bnJlZ2lzdGVyKC4uLik6IGAlc2AgZG9lcyBub3QgbWFwIHRvIGEgcmVnaXN0ZXJlZCBjYWxsYmFjay4nLFxuICAgICAgaWRcbiAgICApO1xuICAgIGRlbGV0ZSB0aGlzLiREaXNwYXRjaGVyX2NhbGxiYWNrc1tpZF07XG4gIH07XG5cbiAgLyoqXG4gICAqIFdhaXRzIGZvciB0aGUgY2FsbGJhY2tzIHNwZWNpZmllZCB0byBiZSBpbnZva2VkIGJlZm9yZSBjb250aW51aW5nIGV4ZWN1dGlvblxuICAgKiBvZiB0aGUgY3VycmVudCBjYWxsYmFjay4gVGhpcyBtZXRob2Qgc2hvdWxkIG9ubHkgYmUgdXNlZCBieSBhIGNhbGxiYWNrIGluXG4gICAqIHJlc3BvbnNlIHRvIGEgZGlzcGF0Y2hlZCBwYXlsb2FkLlxuICAgKlxuICAgKiBAcGFyYW0ge2FycmF5PHN0cmluZz59IGlkc1xuICAgKi9cbiAgRGlzcGF0Y2hlci5wcm90b3R5cGUud2FpdEZvcj1mdW5jdGlvbihpZHMpIHtcbiAgICBpbnZhcmlhbnQoXG4gICAgICB0aGlzLiREaXNwYXRjaGVyX2lzRGlzcGF0Y2hpbmcsXG4gICAgICAnRGlzcGF0Y2hlci53YWl0Rm9yKC4uLik6IE11c3QgYmUgaW52b2tlZCB3aGlsZSBkaXNwYXRjaGluZy4nXG4gICAgKTtcbiAgICBmb3IgKHZhciBpaSA9IDA7IGlpIDwgaWRzLmxlbmd0aDsgaWkrKykge1xuICAgICAgdmFyIGlkID0gaWRzW2lpXTtcbiAgICAgIGlmICh0aGlzLiREaXNwYXRjaGVyX2lzUGVuZGluZ1tpZF0pIHtcbiAgICAgICAgaW52YXJpYW50KFxuICAgICAgICAgIHRoaXMuJERpc3BhdGNoZXJfaXNIYW5kbGVkW2lkXSxcbiAgICAgICAgICAnRGlzcGF0Y2hlci53YWl0Rm9yKC4uLik6IENpcmN1bGFyIGRlcGVuZGVuY3kgZGV0ZWN0ZWQgd2hpbGUgJyArXG4gICAgICAgICAgJ3dhaXRpbmcgZm9yIGAlc2AuJyxcbiAgICAgICAgICBpZFxuICAgICAgICApO1xuICAgICAgICBjb250aW51ZTtcbiAgICAgIH1cbiAgICAgIGludmFyaWFudChcbiAgICAgICAgdGhpcy4kRGlzcGF0Y2hlcl9jYWxsYmFja3NbaWRdLFxuICAgICAgICAnRGlzcGF0Y2hlci53YWl0Rm9yKC4uLik6IGAlc2AgZG9lcyBub3QgbWFwIHRvIGEgcmVnaXN0ZXJlZCBjYWxsYmFjay4nLFxuICAgICAgICBpZFxuICAgICAgKTtcbiAgICAgIHRoaXMuJERpc3BhdGNoZXJfaW52b2tlQ2FsbGJhY2soaWQpO1xuICAgIH1cbiAgfTtcblxuICAvKipcbiAgICogRGlzcGF0Y2hlcyBhIHBheWxvYWQgdG8gYWxsIHJlZ2lzdGVyZWQgY2FsbGJhY2tzLlxuICAgKlxuICAgKiBAcGFyYW0ge29iamVjdH0gcGF5bG9hZFxuICAgKi9cbiAgRGlzcGF0Y2hlci5wcm90b3R5cGUuZGlzcGF0Y2g9ZnVuY3Rpb24ocGF5bG9hZCkge1xuICAgIGludmFyaWFudChcbiAgICAgICF0aGlzLiREaXNwYXRjaGVyX2lzRGlzcGF0Y2hpbmcsXG4gICAgICAnRGlzcGF0Y2guZGlzcGF0Y2goLi4uKTogQ2Fubm90IGRpc3BhdGNoIGluIHRoZSBtaWRkbGUgb2YgYSBkaXNwYXRjaC4nXG4gICAgKTtcbiAgICB0aGlzLiREaXNwYXRjaGVyX3N0YXJ0RGlzcGF0Y2hpbmcocGF5bG9hZCk7XG4gICAgdHJ5IHtcbiAgICAgIGZvciAodmFyIGlkIGluIHRoaXMuJERpc3BhdGNoZXJfY2FsbGJhY2tzKSB7XG4gICAgICAgIGlmICh0aGlzLiREaXNwYXRjaGVyX2lzUGVuZGluZ1tpZF0pIHtcbiAgICAgICAgICBjb250aW51ZTtcbiAgICAgICAgfVxuICAgICAgICB0aGlzLiREaXNwYXRjaGVyX2ludm9rZUNhbGxiYWNrKGlkKTtcbiAgICAgIH1cbiAgICB9IGZpbmFsbHkge1xuICAgICAgdGhpcy4kRGlzcGF0Y2hlcl9zdG9wRGlzcGF0Y2hpbmcoKTtcbiAgICB9XG4gIH07XG5cbiAgLyoqXG4gICAqIElzIHRoaXMgRGlzcGF0Y2hlciBjdXJyZW50bHkgZGlzcGF0Y2hpbmcuXG4gICAqXG4gICAqIEByZXR1cm4ge2Jvb2xlYW59XG4gICAqL1xuICBEaXNwYXRjaGVyLnByb3RvdHlwZS5pc0Rpc3BhdGNoaW5nPWZ1bmN0aW9uKCkge1xuICAgIHJldHVybiB0aGlzLiREaXNwYXRjaGVyX2lzRGlzcGF0Y2hpbmc7XG4gIH07XG5cbiAgLyoqXG4gICAqIENhbGwgdGhlIGNhbGxiYWNrIHN0b3JlZCB3aXRoIHRoZSBnaXZlbiBpZC4gQWxzbyBkbyBzb21lIGludGVybmFsXG4gICAqIGJvb2trZWVwaW5nLlxuICAgKlxuICAgKiBAcGFyYW0ge3N0cmluZ30gaWRcbiAgICogQGludGVybmFsXG4gICAqL1xuICBEaXNwYXRjaGVyLnByb3RvdHlwZS4kRGlzcGF0Y2hlcl9pbnZva2VDYWxsYmFjaz1mdW5jdGlvbihpZCkge1xuICAgIHRoaXMuJERpc3BhdGNoZXJfaXNQZW5kaW5nW2lkXSA9IHRydWU7XG4gICAgdGhpcy4kRGlzcGF0Y2hlcl9jYWxsYmFja3NbaWRdKHRoaXMuJERpc3BhdGNoZXJfcGVuZGluZ1BheWxvYWQpO1xuICAgIHRoaXMuJERpc3BhdGNoZXJfaXNIYW5kbGVkW2lkXSA9IHRydWU7XG4gIH07XG5cbiAgLyoqXG4gICAqIFNldCB1cCBib29ra2VlcGluZyBuZWVkZWQgd2hlbiBkaXNwYXRjaGluZy5cbiAgICpcbiAgICogQHBhcmFtIHtvYmplY3R9IHBheWxvYWRcbiAgICogQGludGVybmFsXG4gICAqL1xuICBEaXNwYXRjaGVyLnByb3RvdHlwZS4kRGlzcGF0Y2hlcl9zdGFydERpc3BhdGNoaW5nPWZ1bmN0aW9uKHBheWxvYWQpIHtcbiAgICBmb3IgKHZhciBpZCBpbiB0aGlzLiREaXNwYXRjaGVyX2NhbGxiYWNrcykge1xuICAgICAgdGhpcy4kRGlzcGF0Y2hlcl9pc1BlbmRpbmdbaWRdID0gZmFsc2U7XG4gICAgICB0aGlzLiREaXNwYXRjaGVyX2lzSGFuZGxlZFtpZF0gPSBmYWxzZTtcbiAgICB9XG4gICAgdGhpcy4kRGlzcGF0Y2hlcl9wZW5kaW5nUGF5bG9hZCA9IHBheWxvYWQ7XG4gICAgdGhpcy4kRGlzcGF0Y2hlcl9pc0Rpc3BhdGNoaW5nID0gdHJ1ZTtcbiAgfTtcblxuICAvKipcbiAgICogQ2xlYXIgYm9va2tlZXBpbmcgdXNlZCBmb3IgZGlzcGF0Y2hpbmcuXG4gICAqXG4gICAqIEBpbnRlcm5hbFxuICAgKi9cbiAgRGlzcGF0Y2hlci5wcm90b3R5cGUuJERpc3BhdGNoZXJfc3RvcERpc3BhdGNoaW5nPWZ1bmN0aW9uKCkge1xuICAgIHRoaXMuJERpc3BhdGNoZXJfcGVuZGluZ1BheWxvYWQgPSBudWxsO1xuICAgIHRoaXMuJERpc3BhdGNoZXJfaXNEaXNwYXRjaGluZyA9IGZhbHNlO1xuICB9O1xuXG5cbm1vZHVsZS5leHBvcnRzID0gRGlzcGF0Y2hlcjtcbiIsIi8qKlxuICogQ29weXJpZ2h0IChjKSAyMDE0LCBGYWNlYm9vaywgSW5jLlxuICogQWxsIHJpZ2h0cyByZXNlcnZlZC5cbiAqXG4gKiBUaGlzIHNvdXJjZSBjb2RlIGlzIGxpY2Vuc2VkIHVuZGVyIHRoZSBCU0Qtc3R5bGUgbGljZW5zZSBmb3VuZCBpbiB0aGVcbiAqIExJQ0VOU0UgZmlsZSBpbiB0aGUgcm9vdCBkaXJlY3Rvcnkgb2YgdGhpcyBzb3VyY2UgdHJlZS4gQW4gYWRkaXRpb25hbCBncmFudFxuICogb2YgcGF0ZW50IHJpZ2h0cyBjYW4gYmUgZm91bmQgaW4gdGhlIFBBVEVOVFMgZmlsZSBpbiB0aGUgc2FtZSBkaXJlY3RvcnkuXG4gKlxuICogQHByb3ZpZGVzTW9kdWxlIGludmFyaWFudFxuICovXG5cblwidXNlIHN0cmljdFwiO1xuXG4vKipcbiAqIFVzZSBpbnZhcmlhbnQoKSB0byBhc3NlcnQgc3RhdGUgd2hpY2ggeW91ciBwcm9ncmFtIGFzc3VtZXMgdG8gYmUgdHJ1ZS5cbiAqXG4gKiBQcm92aWRlIHNwcmludGYtc3R5bGUgZm9ybWF0IChvbmx5ICVzIGlzIHN1cHBvcnRlZCkgYW5kIGFyZ3VtZW50c1xuICogdG8gcHJvdmlkZSBpbmZvcm1hdGlvbiBhYm91dCB3aGF0IGJyb2tlIGFuZCB3aGF0IHlvdSB3ZXJlXG4gKiBleHBlY3RpbmcuXG4gKlxuICogVGhlIGludmFyaWFudCBtZXNzYWdlIHdpbGwgYmUgc3RyaXBwZWQgaW4gcHJvZHVjdGlvbiwgYnV0IHRoZSBpbnZhcmlhbnRcbiAqIHdpbGwgcmVtYWluIHRvIGVuc3VyZSBsb2dpYyBkb2VzIG5vdCBkaWZmZXIgaW4gcHJvZHVjdGlvbi5cbiAqL1xuXG52YXIgaW52YXJpYW50ID0gZnVuY3Rpb24oY29uZGl0aW9uLCBmb3JtYXQsIGEsIGIsIGMsIGQsIGUsIGYpIHtcbiAgaWYgKGZhbHNlKSB7XG4gICAgaWYgKGZvcm1hdCA9PT0gdW5kZWZpbmVkKSB7XG4gICAgICB0aHJvdyBuZXcgRXJyb3IoJ2ludmFyaWFudCByZXF1aXJlcyBhbiBlcnJvciBtZXNzYWdlIGFyZ3VtZW50Jyk7XG4gICAgfVxuICB9XG5cbiAgaWYgKCFjb25kaXRpb24pIHtcbiAgICB2YXIgZXJyb3I7XG4gICAgaWYgKGZvcm1hdCA9PT0gdW5kZWZpbmVkKSB7XG4gICAgICBlcnJvciA9IG5ldyBFcnJvcihcbiAgICAgICAgJ01pbmlmaWVkIGV4Y2VwdGlvbiBvY2N1cnJlZDsgdXNlIHRoZSBub24tbWluaWZpZWQgZGV2IGVudmlyb25tZW50ICcgK1xuICAgICAgICAnZm9yIHRoZSBmdWxsIGVycm9yIG1lc3NhZ2UgYW5kIGFkZGl0aW9uYWwgaGVscGZ1bCB3YXJuaW5ncy4nXG4gICAgICApO1xuICAgIH0gZWxzZSB7XG4gICAgICB2YXIgYXJncyA9IFthLCBiLCBjLCBkLCBlLCBmXTtcbiAgICAgIHZhciBhcmdJbmRleCA9IDA7XG4gICAgICBlcnJvciA9IG5ldyBFcnJvcihcbiAgICAgICAgJ0ludmFyaWFudCBWaW9sYXRpb246ICcgK1xuICAgICAgICBmb3JtYXQucmVwbGFjZSgvJXMvZywgZnVuY3Rpb24oKSB7IHJldHVybiBhcmdzW2FyZ0luZGV4KytdOyB9KVxuICAgICAgKTtcbiAgICB9XG5cbiAgICBlcnJvci5mcmFtZXNUb1BvcCA9IDE7IC8vIHdlIGRvbid0IGNhcmUgYWJvdXQgaW52YXJpYW50J3Mgb3duIGZyYW1lXG4gICAgdGhyb3cgZXJyb3I7XG4gIH1cbn07XG5cbm1vZHVsZS5leHBvcnRzID0gaW52YXJpYW50O1xuIiwidmFyICQgPSByZXF1aXJlKFwianF1ZXJ5XCIpO1xuXG52YXIgQWN0aW9uVHlwZXMgPSB7XG4gICAgLy8gQ29ubmVjdGlvblxuICAgIENPTk5FQ1RJT05fT1BFTjogXCJjb25uZWN0aW9uX29wZW5cIixcbiAgICBDT05ORUNUSU9OX0NMT1NFOiBcImNvbm5lY3Rpb25fY2xvc2VcIixcbiAgICBDT05ORUNUSU9OX0VSUk9SOiBcImNvbm5lY3Rpb25fZXJyb3JcIixcblxuICAgIC8vIFN0b3Jlc1xuICAgIFNFVFRJTkdTX1NUT1JFOiBcInNldHRpbmdzXCIsXG4gICAgRVZFTlRfU1RPUkU6IFwiZXZlbnRzXCIsXG4gICAgRkxPV19TVE9SRTogXCJmbG93c1wiLFxufTtcblxudmFyIFN0b3JlQ21kcyA9IHtcbiAgICBBREQ6IFwiYWRkXCIsXG4gICAgVVBEQVRFOiBcInVwZGF0ZVwiLFxuICAgIFJFTU9WRTogXCJyZW1vdmVcIixcbiAgICBSRVNFVDogXCJyZXNldFwiXG59O1xuXG52YXIgQ29ubmVjdGlvbkFjdGlvbnMgPSB7XG4gICAgb3BlbjogZnVuY3Rpb24gKCkge1xuICAgICAgICBBcHBEaXNwYXRjaGVyLmRpc3BhdGNoVmlld0FjdGlvbih7XG4gICAgICAgICAgICB0eXBlOiBBY3Rpb25UeXBlcy5DT05ORUNUSU9OX09QRU5cbiAgICAgICAgfSk7XG4gICAgfSxcbiAgICBjbG9zZTogZnVuY3Rpb24gKCkge1xuICAgICAgICBBcHBEaXNwYXRjaGVyLmRpc3BhdGNoVmlld0FjdGlvbih7XG4gICAgICAgICAgICB0eXBlOiBBY3Rpb25UeXBlcy5DT05ORUNUSU9OX0NMT1NFXG4gICAgICAgIH0pO1xuICAgIH0sXG4gICAgZXJyb3I6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFZpZXdBY3Rpb24oe1xuICAgICAgICAgICAgdHlwZTogQWN0aW9uVHlwZXMuQ09OTkVDVElPTl9FUlJPUlxuICAgICAgICB9KTtcbiAgICB9XG59O1xuXG52YXIgU2V0dGluZ3NBY3Rpb25zID0ge1xuICAgIHVwZGF0ZTogZnVuY3Rpb24gKHNldHRpbmdzKSB7XG5cbiAgICAgICAgJC5hamF4KHtcbiAgICAgICAgICAgIHR5cGU6IFwiUFVUXCIsXG4gICAgICAgICAgICB1cmw6IFwiL3NldHRpbmdzXCIsXG4gICAgICAgICAgICBkYXRhOiBzZXR0aW5nc1xuICAgICAgICB9KTtcblxuICAgICAgICAvKlxuICAgICAgICAvL0ZhY2Vib29rIEZsdXg6IFdlIGRvIGFuIG9wdGltaXN0aWMgdXBkYXRlIG9uIHRoZSBjbGllbnQgYWxyZWFkeS5cbiAgICAgICAgQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFZpZXdBY3Rpb24oe1xuICAgICAgICAgICAgdHlwZTogQWN0aW9uVHlwZXMuU0VUVElOR1NfU1RPUkUsXG4gICAgICAgICAgICBjbWQ6IFN0b3JlQ21kcy5VUERBVEUsXG4gICAgICAgICAgICBkYXRhOiBzZXR0aW5nc1xuICAgICAgICB9KTtcbiAgICAgICAgKi9cbiAgICB9XG59O1xuXG52YXIgRXZlbnRMb2dBY3Rpb25zX2V2ZW50X2lkID0gMDtcbnZhciBFdmVudExvZ0FjdGlvbnMgPSB7XG4gICAgYWRkX2V2ZW50OiBmdW5jdGlvbiAobWVzc2FnZSkge1xuICAgICAgICBBcHBEaXNwYXRjaGVyLmRpc3BhdGNoVmlld0FjdGlvbih7XG4gICAgICAgICAgICB0eXBlOiBBY3Rpb25UeXBlcy5FVkVOVF9TVE9SRSxcbiAgICAgICAgICAgIGNtZDogU3RvcmVDbWRzLkFERCxcbiAgICAgICAgICAgIGRhdGE6IHtcbiAgICAgICAgICAgICAgICBtZXNzYWdlOiBtZXNzYWdlLFxuICAgICAgICAgICAgICAgIGxldmVsOiBcIndlYlwiLFxuICAgICAgICAgICAgICAgIGlkOiBcInZpZXdBY3Rpb24tXCIgKyBFdmVudExvZ0FjdGlvbnNfZXZlbnRfaWQrK1xuICAgICAgICAgICAgfVxuICAgICAgICB9KTtcbiAgICB9XG59O1xuXG52YXIgRmxvd0FjdGlvbnMgPSB7XG4gICAgYWNjZXB0OiBmdW5jdGlvbiAoZmxvdykge1xuICAgICAgICAkLnBvc3QoXCIvZmxvd3MvXCIgKyBmbG93LmlkICsgXCIvYWNjZXB0XCIpO1xuICAgIH0sXG4gICAgYWNjZXB0X2FsbDogZnVuY3Rpb24oKXtcbiAgICAgICAgJC5wb3N0KFwiL2Zsb3dzL2FjY2VwdFwiKTtcbiAgICB9LFxuICAgIFwiZGVsZXRlXCI6IGZ1bmN0aW9uKGZsb3cpe1xuICAgICAgICAkLmFqYXgoe1xuICAgICAgICAgICAgdHlwZTpcIkRFTEVURVwiLFxuICAgICAgICAgICAgdXJsOiBcIi9mbG93cy9cIiArIGZsb3cuaWRcbiAgICAgICAgfSk7XG4gICAgfSxcbiAgICBkdXBsaWNhdGU6IGZ1bmN0aW9uKGZsb3cpe1xuICAgICAgICAkLnBvc3QoXCIvZmxvd3MvXCIgKyBmbG93LmlkICsgXCIvZHVwbGljYXRlXCIpO1xuICAgIH0sXG4gICAgcmVwbGF5OiBmdW5jdGlvbihmbG93KXtcbiAgICAgICAgJC5wb3N0KFwiL2Zsb3dzL1wiICsgZmxvdy5pZCArIFwiL3JlcGxheVwiKTtcbiAgICB9LFxuICAgIHJldmVydDogZnVuY3Rpb24oZmxvdyl7XG4gICAgICAgICQucG9zdChcIi9mbG93cy9cIiArIGZsb3cuaWQgKyBcIi9yZXZlcnRcIik7XG4gICAgfSxcbiAgICB1cGRhdGU6IGZ1bmN0aW9uIChmbG93KSB7XG4gICAgICAgIEFwcERpc3BhdGNoZXIuZGlzcGF0Y2hWaWV3QWN0aW9uKHtcbiAgICAgICAgICAgIHR5cGU6IEFjdGlvblR5cGVzLkZMT1dfU1RPUkUsXG4gICAgICAgICAgICBjbWQ6IFN0b3JlQ21kcy5VUERBVEUsXG4gICAgICAgICAgICBkYXRhOiBmbG93XG4gICAgICAgIH0pO1xuICAgIH0sXG4gICAgY2xlYXI6IGZ1bmN0aW9uKCl7XG4gICAgICAgICQucG9zdChcIi9jbGVhclwiKTtcbiAgICB9XG59O1xuXG5RdWVyeSA9IHtcbiAgICBGSUxURVI6IFwiZlwiLFxuICAgIEhJR0hMSUdIVDogXCJoXCIsXG4gICAgU0hPV19FVkVOVExPRzogXCJlXCJcbn07XG5cbm1vZHVsZS5leHBvcnRzID0ge1xuICAgIEFjdGlvblR5cGVzOiBBY3Rpb25UeXBlcyxcbiAgICBDb25uZWN0aW9uQWN0aW9uczogQ29ubmVjdGlvbkFjdGlvbnMsXG4gICAgRmxvd0FjdGlvbnM6IEZsb3dBY3Rpb25zLFxuICAgIFN0b3JlQ21kczogU3RvcmVDbWRzXG59OyIsIlxudmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xudmFyIFJlYWN0Um91dGVyID0gcmVxdWlyZShcInJlYWN0LXJvdXRlclwiKTtcbnZhciAkID0gcmVxdWlyZShcImpxdWVyeVwiKTtcblxudmFyIENvbm5lY3Rpb24gPSByZXF1aXJlKFwiLi9jb25uZWN0aW9uXCIpO1xudmFyIHByb3h5YXBwID0gcmVxdWlyZShcIi4vY29tcG9uZW50cy9wcm94eWFwcC5qc1wiKTtcblxuJChmdW5jdGlvbiAoKSB7XG4gICAgd2luZG93LndzID0gbmV3IENvbm5lY3Rpb24oXCIvdXBkYXRlc1wiKTtcblxuICAgIFJlYWN0Um91dGVyLnJ1bihwcm94eWFwcC5yb3V0ZXMsIGZ1bmN0aW9uIChIYW5kbGVyKSB7XG4gICAgICAgIFJlYWN0LnJlbmRlcihSZWFjdC5jcmVhdGVFbGVtZW50KEhhbmRsZXIsIG51bGwpLCBkb2N1bWVudC5ib2R5KTtcbiAgICB9KTtcbn0pOyIsInZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcbnZhciB1dGlscyA9IHJlcXVpcmUoXCIuL3V0aWxzLmpzXCIpO1xudmFyIFZpcnR1YWxTY3JvbGxNaXhpbiA9IHJlcXVpcmUoXCIuL3ZpcnR1YWxzY3JvbGwuanNcIik7XG52YXIgdmlld3MgPSByZXF1aXJlKFwiLi4vc3RvcmUvdmlldy5qc1wiKTtcblxudmFyIExvZ01lc3NhZ2UgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiTG9nTWVzc2FnZVwiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZW50cnkgPSB0aGlzLnByb3BzLmVudHJ5O1xuICAgICAgICB2YXIgaW5kaWNhdG9yO1xuICAgICAgICBzd2l0Y2ggKGVudHJ5LmxldmVsKSB7XG4gICAgICAgICAgICBjYXNlIFwid2ViXCI6XG4gICAgICAgICAgICAgICAgaW5kaWNhdG9yID0gUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge2NsYXNzTmFtZTogXCJmYSBmYS1mdyBmYS1odG1sNVwifSk7XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIFwiZGVidWdcIjpcbiAgICAgICAgICAgICAgICBpbmRpY2F0b3IgPSBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaVwiLCB7Y2xhc3NOYW1lOiBcImZhIGZhLWZ3IGZhLWJ1Z1wifSk7XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBkZWZhdWx0OlxuICAgICAgICAgICAgICAgIGluZGljYXRvciA9IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJpXCIsIHtjbGFzc05hbWU6IFwiZmEgZmEtZncgZmEtaW5mb1wifSk7XG4gICAgICAgIH1cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgaW5kaWNhdG9yLCBcIiBcIiwgZW50cnkubWVzc2FnZVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH0sXG4gICAgc2hvdWxkQ29tcG9uZW50VXBkYXRlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHJldHVybiBmYWxzZTsgLy8gbG9nIGVudHJpZXMgYXJlIGltbXV0YWJsZS5cbiAgICB9XG59KTtcblxudmFyIEV2ZW50TG9nQ29udGVudHMgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiRXZlbnRMb2dDb250ZW50c1wiLFxuICAgIG1peGluczogW3V0aWxzLkF1dG9TY3JvbGxNaXhpbiwgVmlydHVhbFNjcm9sbE1peGluXSxcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgIGxvZzogW11cbiAgICAgICAgfTtcbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxNb3VudDogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLm9wZW5WaWV3KHRoaXMucHJvcHMuZXZlbnRTdG9yZSk7XG4gICAgfSxcbiAgICBjb21wb25lbnRXaWxsVW5tb3VudDogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLmNsb3NlVmlldygpO1xuICAgIH0sXG4gICAgb3BlblZpZXc6IGZ1bmN0aW9uIChzdG9yZSkge1xuICAgICAgICB2YXIgdmlldyA9IG5ldyB2aWV3cy5TdG9yZVZpZXcoc3RvcmUsIGZ1bmN0aW9uIChlbnRyeSkge1xuICAgICAgICAgICAgcmV0dXJuIHRoaXMucHJvcHMuZmlsdGVyW2VudHJ5LmxldmVsXTtcbiAgICAgICAgfS5iaW5kKHRoaXMpKTtcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7XG4gICAgICAgICAgICB2aWV3OiB2aWV3XG4gICAgICAgIH0pO1xuXG4gICAgICAgIHZpZXcuYWRkTGlzdGVuZXIoXCJhZGQgcmVjYWxjdWxhdGVcIiwgdGhpcy5vbkV2ZW50TG9nQ2hhbmdlKTtcbiAgICB9LFxuICAgIGNsb3NlVmlldzogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLnN0YXRlLnZpZXcuY2xvc2UoKTtcbiAgICB9LFxuICAgIG9uRXZlbnRMb2dDaGFuZ2U6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7XG4gICAgICAgICAgICBsb2c6IHRoaXMuc3RhdGUudmlldy5saXN0XG4gICAgICAgIH0pO1xuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbFJlY2VpdmVQcm9wczogZnVuY3Rpb24gKG5leHRQcm9wcykge1xuICAgICAgICBpZiAobmV4dFByb3BzLmZpbHRlciAhPT0gdGhpcy5wcm9wcy5maWx0ZXIpIHtcbiAgICAgICAgICAgIHRoaXMucHJvcHMuZmlsdGVyID0gbmV4dFByb3BzLmZpbHRlcjsgLy8gRGlydHk6IE1ha2Ugc3VyZSB0aGF0IHZpZXcgZmlsdGVyIHNlZXMgdGhlIHVwZGF0ZS5cbiAgICAgICAgICAgIHRoaXMuc3RhdGUudmlldy5yZWNhbGN1bGF0ZSgpO1xuICAgICAgICB9XG4gICAgICAgIGlmIChuZXh0UHJvcHMuZXZlbnRTdG9yZSAhPT0gdGhpcy5wcm9wcy5ldmVudFN0b3JlKSB7XG4gICAgICAgICAgICB0aGlzLmNsb3NlVmlldygpO1xuICAgICAgICAgICAgdGhpcy5vcGVuVmlldyhuZXh0UHJvcHMuZXZlbnRTdG9yZSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGdldERlZmF1bHRQcm9wczogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgcm93SGVpZ2h0OiA0NSxcbiAgICAgICAgICAgIHJvd0hlaWdodE1pbjogMTUsXG4gICAgICAgICAgICBwbGFjZWhvbGRlclRhZ05hbWU6IFwiZGl2XCJcbiAgICAgICAgfTtcbiAgICB9LFxuICAgIHJlbmRlclJvdzogZnVuY3Rpb24gKGVsZW0pIHtcbiAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoTG9nTWVzc2FnZSwge2tleTogZWxlbS5pZCwgZW50cnk6IGVsZW19KTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgcm93cyA9IHRoaXMucmVuZGVyUm93cyh0aGlzLnN0YXRlLmxvZyk7XG5cbiAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJwcmVcIiwge29uU2Nyb2xsOiB0aGlzLm9uU2Nyb2xsfSwgXG4gICAgICAgICAgICAgdGhpcy5nZXRQbGFjZWhvbGRlclRvcCh0aGlzLnN0YXRlLmxvZy5sZW5ndGgpLCBcbiAgICAgICAgICAgIHJvd3MsIFxuICAgICAgICAgICAgIHRoaXMuZ2V0UGxhY2Vob2xkZXJCb3R0b20odGhpcy5zdGF0ZS5sb2cubGVuZ3RoKSBcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxudmFyIFRvZ2dsZUZpbHRlciA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJUb2dnbGVGaWx0ZXJcIixcbiAgICB0b2dnbGU6IGZ1bmN0aW9uIChlKSB7XG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcbiAgICAgICAgcmV0dXJuIHRoaXMucHJvcHMudG9nZ2xlTGV2ZWwodGhpcy5wcm9wcy5uYW1lKTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgY2xhc3NOYW1lID0gXCJsYWJlbCBcIjtcbiAgICAgICAgaWYgKHRoaXMucHJvcHMuYWN0aXZlKSB7XG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCJsYWJlbC1wcmltYXJ5XCI7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCJsYWJlbC1kZWZhdWx0XCI7XG4gICAgICAgIH1cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJhXCIsIHtcbiAgICAgICAgICAgICAgICBocmVmOiBcIiNcIiwgXG4gICAgICAgICAgICAgICAgY2xhc3NOYW1lOiBjbGFzc05hbWUsIFxuICAgICAgICAgICAgICAgIG9uQ2xpY2s6IHRoaXMudG9nZ2xlfSwgXG4gICAgICAgICAgICAgICAgdGhpcy5wcm9wcy5uYW1lXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBFdmVudExvZyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJFdmVudExvZ1wiLFxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgZmlsdGVyOiB7XG4gICAgICAgICAgICAgICAgXCJkZWJ1Z1wiOiBmYWxzZSxcbiAgICAgICAgICAgICAgICBcImluZm9cIjogdHJ1ZSxcbiAgICAgICAgICAgICAgICBcIndlYlwiOiB0cnVlXG4gICAgICAgICAgICB9XG4gICAgICAgIH07XG4gICAgfSxcbiAgICBjbG9zZTogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZCA9IHt9O1xuICAgICAgICBkW1F1ZXJ5LlNIT1dfRVZFTlRMT0ddID0gdW5kZWZpbmVkO1xuICAgICAgICB0aGlzLnNldFF1ZXJ5KGQpO1xuICAgIH0sXG4gICAgdG9nZ2xlTGV2ZWw6IGZ1bmN0aW9uIChsZXZlbCkge1xuICAgICAgICB2YXIgZmlsdGVyID0gXy5leHRlbmQoe30sIHRoaXMuc3RhdGUuZmlsdGVyKTtcbiAgICAgICAgZmlsdGVyW2xldmVsXSA9ICFmaWx0ZXJbbGV2ZWxdO1xuICAgICAgICB0aGlzLnNldFN0YXRlKHtmaWx0ZXI6IGZpbHRlcn0pO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwiZXZlbnRsb2dcIn0sIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgICAgIFwiRXZlbnRsb2dcIiwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJwdWxsLXJpZ2h0XCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoVG9nZ2xlRmlsdGVyLCB7bmFtZTogXCJkZWJ1Z1wiLCBhY3RpdmU6IHRoaXMuc3RhdGUuZmlsdGVyLmRlYnVnLCB0b2dnbGVMZXZlbDogdGhpcy50b2dnbGVMZXZlbH0pLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoVG9nZ2xlRmlsdGVyLCB7bmFtZTogXCJpbmZvXCIsIGFjdGl2ZTogdGhpcy5zdGF0ZS5maWx0ZXIuaW5mbywgdG9nZ2xlTGV2ZWw6IHRoaXMudG9nZ2xlTGV2ZWx9KSwgXG4gICAgICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFRvZ2dsZUZpbHRlciwge25hbWU6IFwid2ViXCIsIGFjdGl2ZTogdGhpcy5zdGF0ZS5maWx0ZXIud2ViLCB0b2dnbGVMZXZlbDogdGhpcy50b2dnbGVMZXZlbH0pLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJpXCIsIHtvbkNsaWNrOiB0aGlzLmNsb3NlLCBjbGFzc05hbWU6IFwiZmEgZmEtY2xvc2VcIn0pXG4gICAgICAgICAgICAgICAgICAgIClcblxuICAgICAgICAgICAgICAgICksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoRXZlbnRMb2dDb250ZW50cywge2ZpbHRlcjogdGhpcy5zdGF0ZS5maWx0ZXIsIGV2ZW50U3RvcmU6IHRoaXMucHJvcHMuZXZlbnRTdG9yZX0pXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbm1vZHVsZS5leHBvcnRzID0gRXZlbnRMb2c7IiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xudmFyIF8gPSByZXF1aXJlKFwibG9kYXNoXCIpO1xuXG52YXIgdXRpbHMgPSByZXF1aXJlKFwiLi91dGlscy5qc1wiKTtcbnZhciBhY3Rpb25zID0gcmVxdWlyZShcIi4uL2FjdGlvbnMuanNcIik7XG52YXIgZmxvd3V0aWxzID0gcmVxdWlyZShcIi4uL2Zsb3cvdXRpbHMuanNcIik7XG52YXIgdG9wdXRpbHMgPSByZXF1aXJlKFwiLi4vdXRpbHMuanNcIik7XG5cbnZhciBOYXZBY3Rpb24gPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiTmF2QWN0aW9uXCIsXG4gICAgb25DbGljazogZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICB0aGlzLnByb3BzLm9uQ2xpY2soKTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImFcIiwge3RpdGxlOiB0aGlzLnByb3BzLnRpdGxlLCBcbiAgICAgICAgICAgICAgICBocmVmOiBcIiNcIiwgXG4gICAgICAgICAgICAgICAgY2xhc3NOYW1lOiBcIm5hdi1hY3Rpb25cIiwgXG4gICAgICAgICAgICAgICAgb25DbGljazogdGhpcy5vbkNsaWNrfSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge2NsYXNzTmFtZTogXCJmYSBmYS1mdyBcIiArIHRoaXMucHJvcHMuaWNvbn0pXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBGbG93RGV0YWlsTmF2ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZsb3dEZXRhaWxOYXZcIixcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG5cbiAgICAgICAgdmFyIHRhYnMgPSB0aGlzLnByb3BzLnRhYnMubWFwKGZ1bmN0aW9uIChlKSB7XG4gICAgICAgICAgICB2YXIgc3RyID0gZS5jaGFyQXQoMCkudG9VcHBlckNhc2UoKSArIGUuc2xpY2UoMSk7XG4gICAgICAgICAgICB2YXIgY2xhc3NOYW1lID0gdGhpcy5wcm9wcy5hY3RpdmUgPT09IGUgPyBcImFjdGl2ZVwiIDogXCJcIjtcbiAgICAgICAgICAgIHZhciBvbkNsaWNrID0gZnVuY3Rpb24gKGV2ZW50KSB7XG4gICAgICAgICAgICAgICAgdGhpcy5wcm9wcy5zZWxlY3RUYWIoZSk7XG4gICAgICAgICAgICAgICAgZXZlbnQucHJldmVudERlZmF1bHQoKTtcbiAgICAgICAgICAgIH0uYmluZCh0aGlzKTtcbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwiYVwiLCB7a2V5OiBlLCBcbiAgICAgICAgICAgICAgICBocmVmOiBcIiNcIiwgXG4gICAgICAgICAgICAgICAgY2xhc3NOYW1lOiBjbGFzc05hbWUsIFxuICAgICAgICAgICAgICAgIG9uQ2xpY2s6IG9uQ2xpY2t9LCBzdHIpO1xuICAgICAgICB9LmJpbmQodGhpcykpO1xuXG4gICAgICAgIHZhciBhY2NlcHRCdXR0b24gPSBudWxsO1xuICAgICAgICBpZihmbG93LmludGVyY2VwdGVkKXtcbiAgICAgICAgICAgIGFjY2VwdEJ1dHRvbiA9IFJlYWN0LmNyZWF0ZUVsZW1lbnQoTmF2QWN0aW9uLCB7dGl0bGU6IFwiW2FdY2NlcHQgaW50ZXJjZXB0ZWQgZmxvd1wiLCBpY29uOiBcImZhLXBsYXlcIiwgb25DbGljazogYWN0aW9ucy5GbG93QWN0aW9ucy5hY2NlcHQuYmluZChudWxsLCBmbG93KX0pO1xuICAgICAgICB9XG4gICAgICAgIHZhciByZXZlcnRCdXR0b24gPSBudWxsO1xuICAgICAgICBpZihmbG93Lm1vZGlmaWVkKXtcbiAgICAgICAgICAgIHJldmVydEJ1dHRvbiA9IFJlYWN0LmNyZWF0ZUVsZW1lbnQoTmF2QWN0aW9uLCB7dGl0bGU6IFwicmV2ZXJ0IGNoYW5nZXMgdG8gZmxvdyBbVl1cIiwgaWNvbjogXCJmYS1oaXN0b3J5XCIsIG9uQ2xpY2s6IGFjdGlvbnMuRmxvd0FjdGlvbnMucmV2ZXJ0LmJpbmQobnVsbCwgZmxvdyl9KTtcbiAgICAgICAgfVxuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwibmF2XCIsIHtyZWY6IFwiaGVhZFwiLCBjbGFzc05hbWU6IFwibmF2LXRhYnMgbmF2LXRhYnMtc21cIn0sIFxuICAgICAgICAgICAgICAgIHRhYnMsIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoTmF2QWN0aW9uLCB7dGl0bGU6IFwiW2RdZWxldGUgZmxvd1wiLCBpY29uOiBcImZhLXRyYXNoXCIsIG9uQ2xpY2s6IGFjdGlvbnMuRmxvd0FjdGlvbnMuZGVsZXRlLmJpbmQobnVsbCwgZmxvdyl9KSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChOYXZBY3Rpb24sIHt0aXRsZTogXCJbRF11cGxpY2F0ZSBmbG93XCIsIGljb246IFwiZmEtY29weVwiLCBvbkNsaWNrOiBhY3Rpb25zLkZsb3dBY3Rpb25zLmR1cGxpY2F0ZS5iaW5kKG51bGwsIGZsb3cpfSksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoTmF2QWN0aW9uLCB7ZGlzYWJsZWQ6IHRydWUsIHRpdGxlOiBcIltyXWVwbGF5IGZsb3dcIiwgaWNvbjogXCJmYS1yZXBlYXRcIiwgb25DbGljazogYWN0aW9ucy5GbG93QWN0aW9ucy5yZXBsYXkuYmluZChudWxsLCBmbG93KX0pLCBcbiAgICAgICAgICAgICAgICBhY2NlcHRCdXR0b24sIFxuICAgICAgICAgICAgICAgIHJldmVydEJ1dHRvblxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgSGVhZGVycyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJIZWFkZXJzXCIsXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciByb3dzID0gdGhpcy5wcm9wcy5tZXNzYWdlLmhlYWRlcnMubWFwKGZ1bmN0aW9uIChoZWFkZXIsIGkpIHtcbiAgICAgICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRyXCIsIHtrZXk6IGl9LCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIHtjbGFzc05hbWU6IFwiaGVhZGVyLW5hbWVcIn0sIGhlYWRlclswXSArIFwiOlwiKSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCB7Y2xhc3NOYW1lOiBcImhlYWRlci12YWx1ZVwifSwgaGVhZGVyWzFdKVxuICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgICk7XG4gICAgICAgIH0pO1xuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRhYmxlXCIsIHtjbGFzc05hbWU6IFwiaGVhZGVyLXRhYmxlXCJ9LCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGJvZHlcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgICAgIHJvd3NcbiAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBGbG93RGV0YWlsUmVxdWVzdCA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGbG93RGV0YWlsUmVxdWVzdFwiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgdmFyIGZpcnN0X2xpbmUgPSBbXG4gICAgICAgICAgICBmbG93LnJlcXVlc3QubWV0aG9kLFxuICAgICAgICAgICAgZmxvd3V0aWxzLlJlcXVlc3RVdGlscy5wcmV0dHlfdXJsKGZsb3cucmVxdWVzdCksXG4gICAgICAgICAgICBcIkhUVFAvXCIgKyBmbG93LnJlcXVlc3QuaHR0cHZlcnNpb24uam9pbihcIi5cIilcbiAgICAgICAgXS5qb2luKFwiIFwiKTtcbiAgICAgICAgdmFyIGNvbnRlbnQgPSBudWxsO1xuICAgICAgICBpZiAoZmxvdy5yZXF1ZXN0LmNvbnRlbnRMZW5ndGggPiAwKSB7XG4gICAgICAgICAgICBjb250ZW50ID0gXCJSZXF1ZXN0IENvbnRlbnQgU2l6ZTogXCIgKyB0b3B1dGlscy5mb3JtYXRTaXplKGZsb3cucmVxdWVzdC5jb250ZW50TGVuZ3RoKTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGNvbnRlbnQgPSBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwiYWxlcnQgYWxlcnQtaW5mb1wifSwgXCJObyBDb250ZW50XCIpO1xuICAgICAgICB9XG5cbiAgICAgICAgLy9UT0RPOiBTdHlsaW5nXG5cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJzZWN0aW9uXCIsIG51bGwsIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJmaXJzdC1saW5lXCJ9LCBmaXJzdF9saW5lICksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoSGVhZGVycywge21lc3NhZ2U6IGZsb3cucmVxdWVzdH0pLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaHJcIiwgbnVsbCksIFxuICAgICAgICAgICAgICAgIGNvbnRlbnRcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxudmFyIEZsb3dEZXRhaWxSZXNwb25zZSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGbG93RGV0YWlsUmVzcG9uc2VcIixcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG4gICAgICAgIHZhciBmaXJzdF9saW5lID0gW1xuICAgICAgICAgICAgXCJIVFRQL1wiICsgZmxvdy5yZXNwb25zZS5odHRwdmVyc2lvbi5qb2luKFwiLlwiKSxcbiAgICAgICAgICAgIGZsb3cucmVzcG9uc2UuY29kZSxcbiAgICAgICAgICAgIGZsb3cucmVzcG9uc2UubXNnXG4gICAgICAgIF0uam9pbihcIiBcIik7XG4gICAgICAgIHZhciBjb250ZW50ID0gbnVsbDtcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UuY29udGVudExlbmd0aCA+IDApIHtcbiAgICAgICAgICAgIGNvbnRlbnQgPSBcIlJlc3BvbnNlIENvbnRlbnQgU2l6ZTogXCIgKyB0b3B1dGlscy5mb3JtYXRTaXplKGZsb3cucmVzcG9uc2UuY29udGVudExlbmd0aCk7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBjb250ZW50ID0gUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcImFsZXJ0IGFsZXJ0LWluZm9cIn0sIFwiTm8gQ29udGVudFwiKTtcbiAgICAgICAgfVxuXG4gICAgICAgIC8vVE9ETzogU3R5bGluZ1xuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwic2VjdGlvblwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwiZmlyc3QtbGluZVwifSwgZmlyc3RfbGluZSApLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KEhlYWRlcnMsIHttZXNzYWdlOiBmbG93LnJlc3BvbnNlfSksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJoclwiLCBudWxsKSwgXG4gICAgICAgICAgICAgICAgY29udGVudFxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgRmxvd0RldGFpbEVycm9yID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZsb3dEZXRhaWxFcnJvclwiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJzZWN0aW9uXCIsIG51bGwsIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJhbGVydCBhbGVydC13YXJuaW5nXCJ9LCBcbiAgICAgICAgICAgICAgICBmbG93LmVycm9yLm1zZywgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwic21hbGxcIiwgbnVsbCwgIHRvcHV0aWxzLmZvcm1hdFRpbWVTdGFtcChmbG93LmVycm9yLnRpbWVzdGFtcCkgKVxuICAgICAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgVGltZVN0YW1wID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlRpbWVTdGFtcFwiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuXG4gICAgICAgIGlmICghdGhpcy5wcm9wcy50KSB7XG4gICAgICAgICAgICAvL3Nob3VsZCBiZSByZXR1cm4gbnVsbCwgYnV0IHRoYXQgdHJpZ2dlcnMgYSBSZWFjdCBidWcuXG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRyXCIsIG51bGwpO1xuICAgICAgICB9XG5cbiAgICAgICAgdmFyIHRzID0gdG9wdXRpbHMuZm9ybWF0VGltZVN0YW1wKHRoaXMucHJvcHMudCk7XG5cbiAgICAgICAgdmFyIGRlbHRhO1xuICAgICAgICBpZiAodGhpcy5wcm9wcy5kZWx0YVRvKSB7XG4gICAgICAgICAgICBkZWx0YSA9IHRvcHV0aWxzLmZvcm1hdFRpbWVEZWx0YSgxMDAwICogKHRoaXMucHJvcHMudCAtIHRoaXMucHJvcHMuZGVsdGFUbykpO1xuICAgICAgICAgICAgZGVsdGEgPSBSZWFjdC5jcmVhdGVFbGVtZW50KFwic3BhblwiLCB7Y2xhc3NOYW1lOiBcInRleHQtbXV0ZWRcIn0sIFwiKFwiICsgZGVsdGEgKyBcIilcIik7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBkZWx0YSA9IG51bGw7XG4gICAgICAgIH1cblxuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRyXCIsIG51bGwsIFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIG51bGwsIHRoaXMucHJvcHMudGl0bGUgKyBcIjpcIiksIFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIG51bGwsIHRzLCBcIiBcIiwgZGVsdGEpXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBDb25uZWN0aW9uSW5mbyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJDb25uZWN0aW9uSW5mb1wiLFxuXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBjb25uID0gdGhpcy5wcm9wcy5jb25uO1xuICAgICAgICB2YXIgYWRkcmVzcyA9IGNvbm4uYWRkcmVzcy5hZGRyZXNzLmpvaW4oXCI6XCIpO1xuXG4gICAgICAgIHZhciBzbmkgPSBSZWFjdC5jcmVhdGVFbGVtZW50KFwidHJcIiwge2tleTogXCJzbmlcIn0pOyAvL3Nob3VsZCBiZSBudWxsLCBidXQgdGhhdCB0cmlnZ2VycyBhIFJlYWN0IGJ1Zy5cbiAgICAgICAgaWYgKGNvbm4uc25pKSB7XG4gICAgICAgICAgICBzbmkgPSBSZWFjdC5jcmVhdGVFbGVtZW50KFwidHJcIiwge2tleTogXCJzbmlcIn0sIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImFiYnJcIiwge3RpdGxlOiBcIlRMUyBTZXJ2ZXIgTmFtZSBJbmRpY2F0aW9uXCJ9LCBcIlRMUyBTTkk6XCIpXG4gICAgICAgICAgICAgICAgKSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIG51bGwsIGNvbm4uc25pKVxuICAgICAgICAgICAgKTtcbiAgICAgICAgfVxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRhYmxlXCIsIHtjbGFzc05hbWU6IFwiY29ubmVjdGlvbi10YWJsZVwifSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRib2R5XCIsIG51bGwsIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidHJcIiwge2tleTogXCJhZGRyZXNzXCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCBudWxsLCBcIkFkZHJlc3M6XCIpLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCBudWxsLCBhZGRyZXNzKVxuICAgICAgICAgICAgICAgICAgICApLCBcbiAgICAgICAgICAgICAgICAgICAgc25pXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgQ2VydGlmaWNhdGVJbmZvID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkNlcnRpZmljYXRlSW5mb1wiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICAvL1RPRE86IFdlIHNob3VsZCBmZXRjaCBodW1hbi1yZWFkYWJsZSBjZXJ0aWZpY2F0ZSByZXByZXNlbnRhdGlvblxuICAgICAgICAvLyBmcm9tIHRoZSBzZXJ2ZXJcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG4gICAgICAgIHZhciBjbGllbnRfY29ubiA9IGZsb3cuY2xpZW50X2Nvbm47XG4gICAgICAgIHZhciBzZXJ2ZXJfY29ubiA9IGZsb3cuc2VydmVyX2Nvbm47XG5cbiAgICAgICAgdmFyIHByZVN0eWxlID0ge21heEhlaWdodDogMTAwfTtcbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwgbnVsbCwgXG4gICAgICAgICAgICBjbGllbnRfY29ubi5jZXJ0ID8gUmVhY3QuY3JlYXRlRWxlbWVudChcImg0XCIsIG51bGwsIFwiQ2xpZW50IENlcnRpZmljYXRlXCIpIDogbnVsbCwgXG4gICAgICAgICAgICBjbGllbnRfY29ubi5jZXJ0ID8gUmVhY3QuY3JlYXRlRWxlbWVudChcInByZVwiLCB7c3R5bGU6IHByZVN0eWxlfSwgY2xpZW50X2Nvbm4uY2VydCkgOiBudWxsLCBcblxuICAgICAgICAgICAgc2VydmVyX2Nvbm4uY2VydCA/IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJoNFwiLCBudWxsLCBcIlNlcnZlciBDZXJ0aWZpY2F0ZVwiKSA6IG51bGwsIFxuICAgICAgICAgICAgc2VydmVyX2Nvbm4uY2VydCA/IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJwcmVcIiwge3N0eWxlOiBwcmVTdHlsZX0sIHNlcnZlcl9jb25uLmNlcnQpIDogbnVsbFxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgVGltaW5nID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlRpbWluZ1wiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgdmFyIHNjID0gZmxvdy5zZXJ2ZXJfY29ubjtcbiAgICAgICAgdmFyIGNjID0gZmxvdy5jbGllbnRfY29ubjtcbiAgICAgICAgdmFyIHJlcSA9IGZsb3cucmVxdWVzdDtcbiAgICAgICAgdmFyIHJlc3AgPSBmbG93LnJlc3BvbnNlO1xuXG4gICAgICAgIHZhciB0aW1lc3RhbXBzID0gW1xuICAgICAgICAgICAge1xuICAgICAgICAgICAgICAgIHRpdGxlOiBcIlNlcnZlciBjb25uLiBpbml0aWF0ZWRcIixcbiAgICAgICAgICAgICAgICB0OiBzYy50aW1lc3RhbXBfc3RhcnQsXG4gICAgICAgICAgICAgICAgZGVsdGFUbzogcmVxLnRpbWVzdGFtcF9zdGFydFxuICAgICAgICAgICAgfSwge1xuICAgICAgICAgICAgICAgIHRpdGxlOiBcIlNlcnZlciBjb25uLiBUQ1AgaGFuZHNoYWtlXCIsXG4gICAgICAgICAgICAgICAgdDogc2MudGltZXN0YW1wX3RjcF9zZXR1cCxcbiAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XG4gICAgICAgICAgICB9LCB7XG4gICAgICAgICAgICAgICAgdGl0bGU6IFwiU2VydmVyIGNvbm4uIFNTTCBoYW5kc2hha2VcIixcbiAgICAgICAgICAgICAgICB0OiBzYy50aW1lc3RhbXBfc3NsX3NldHVwLFxuICAgICAgICAgICAgICAgIGRlbHRhVG86IHJlcS50aW1lc3RhbXBfc3RhcnRcbiAgICAgICAgICAgIH0sIHtcbiAgICAgICAgICAgICAgICB0aXRsZTogXCJDbGllbnQgY29ubi4gZXN0YWJsaXNoZWRcIixcbiAgICAgICAgICAgICAgICB0OiBjYy50aW1lc3RhbXBfc3RhcnQsXG4gICAgICAgICAgICAgICAgZGVsdGFUbzogcmVxLnRpbWVzdGFtcF9zdGFydFxuICAgICAgICAgICAgfSwge1xuICAgICAgICAgICAgICAgIHRpdGxlOiBcIkNsaWVudCBjb25uLiBTU0wgaGFuZHNoYWtlXCIsXG4gICAgICAgICAgICAgICAgdDogY2MudGltZXN0YW1wX3NzbF9zZXR1cCxcbiAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XG4gICAgICAgICAgICB9LCB7XG4gICAgICAgICAgICAgICAgdGl0bGU6IFwiRmlyc3QgcmVxdWVzdCBieXRlXCIsXG4gICAgICAgICAgICAgICAgdDogcmVxLnRpbWVzdGFtcF9zdGFydCxcbiAgICAgICAgICAgIH0sIHtcbiAgICAgICAgICAgICAgICB0aXRsZTogXCJSZXF1ZXN0IGNvbXBsZXRlXCIsXG4gICAgICAgICAgICAgICAgdDogcmVxLnRpbWVzdGFtcF9lbmQsXG4gICAgICAgICAgICAgICAgZGVsdGFUbzogcmVxLnRpbWVzdGFtcF9zdGFydFxuICAgICAgICAgICAgfVxuICAgICAgICBdO1xuXG4gICAgICAgIGlmIChmbG93LnJlc3BvbnNlKSB7XG4gICAgICAgICAgICB0aW1lc3RhbXBzLnB1c2goXG4gICAgICAgICAgICAgICAge1xuICAgICAgICAgICAgICAgICAgICB0aXRsZTogXCJGaXJzdCByZXNwb25zZSBieXRlXCIsXG4gICAgICAgICAgICAgICAgICAgIHQ6IHJlc3AudGltZXN0YW1wX3N0YXJ0LFxuICAgICAgICAgICAgICAgICAgICBkZWx0YVRvOiByZXEudGltZXN0YW1wX3N0YXJ0XG4gICAgICAgICAgICAgICAgfSwge1xuICAgICAgICAgICAgICAgICAgICB0aXRsZTogXCJSZXNwb25zZSBjb21wbGV0ZVwiLFxuICAgICAgICAgICAgICAgICAgICB0OiByZXNwLnRpbWVzdGFtcF9lbmQsXG4gICAgICAgICAgICAgICAgICAgIGRlbHRhVG86IHJlcS50aW1lc3RhbXBfc3RhcnRcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICApO1xuICAgICAgICB9XG5cbiAgICAgICAgLy9BZGQgdW5pcXVlIGtleSBmb3IgZWFjaCByb3cuXG4gICAgICAgIHRpbWVzdGFtcHMuZm9yRWFjaChmdW5jdGlvbiAoZSkge1xuICAgICAgICAgICAgZS5rZXkgPSBlLnRpdGxlO1xuICAgICAgICB9KTtcblxuICAgICAgICB0aW1lc3RhbXBzID0gXy5zb3J0QnkodGltZXN0YW1wcywgJ3QnKTtcblxuICAgICAgICB2YXIgcm93cyA9IHRpbWVzdGFtcHMubWFwKGZ1bmN0aW9uIChlKSB7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChUaW1lU3RhbXAsIFJlYWN0Ll9fc3ByZWFkKHt9LCAgZSkpO1xuICAgICAgICB9KTtcblxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiaDRcIiwgbnVsbCwgXCJUaW1pbmdcIiksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0YWJsZVwiLCB7Y2xhc3NOYW1lOiBcInRpbWluZy10YWJsZVwifSwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0Ym9keVwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICAgICAgcm93c1xuICAgICAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG52YXIgRmxvd0RldGFpbENvbm5lY3Rpb25JbmZvID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZsb3dEZXRhaWxDb25uZWN0aW9uSW5mb1wiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgdmFyIGNsaWVudF9jb25uID0gZmxvdy5jbGllbnRfY29ubjtcbiAgICAgICAgdmFyIHNlcnZlcl9jb25uID0gZmxvdy5zZXJ2ZXJfY29ubjtcbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJzZWN0aW9uXCIsIG51bGwsIFxuXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImg0XCIsIG51bGwsIFwiQ2xpZW50IENvbm5lY3Rpb25cIiksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoQ29ubmVjdGlvbkluZm8sIHtjb25uOiBjbGllbnRfY29ubn0pLCBcblxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJoNFwiLCBudWxsLCBcIlNlcnZlciBDb25uZWN0aW9uXCIpLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KENvbm5lY3Rpb25JbmZvLCB7Y29ubjogc2VydmVyX2Nvbm59KSwgXG5cbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KENlcnRpZmljYXRlSW5mbywge2Zsb3c6IGZsb3d9KSwgXG5cbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFRpbWluZywge2Zsb3c6IGZsb3d9KVxuXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBhbGxUYWJzID0ge1xuICAgIHJlcXVlc3Q6IEZsb3dEZXRhaWxSZXF1ZXN0LFxuICAgIHJlc3BvbnNlOiBGbG93RGV0YWlsUmVzcG9uc2UsXG4gICAgZXJyb3I6IEZsb3dEZXRhaWxFcnJvcixcbiAgICBkZXRhaWxzOiBGbG93RGV0YWlsQ29ubmVjdGlvbkluZm9cbn07XG5cbnZhciBGbG93RGV0YWlsID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZsb3dEZXRhaWxcIixcbiAgICBtaXhpbnM6IFt1dGlscy5TdGlja3lIZWFkTWl4aW4sIHV0aWxzLk5hdmlnYXRpb24sIHV0aWxzLlN0YXRlXSxcbiAgICBnZXRUYWJzOiBmdW5jdGlvbiAoZmxvdykge1xuICAgICAgICB2YXIgdGFicyA9IFtdO1xuICAgICAgICBbXCJyZXF1ZXN0XCIsIFwicmVzcG9uc2VcIiwgXCJlcnJvclwiXS5mb3JFYWNoKGZ1bmN0aW9uIChlKSB7XG4gICAgICAgICAgICBpZiAoZmxvd1tlXSkge1xuICAgICAgICAgICAgICAgIHRhYnMucHVzaChlKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgfSk7XG4gICAgICAgIHRhYnMucHVzaChcImRldGFpbHNcIik7XG4gICAgICAgIHJldHVybiB0YWJzO1xuICAgIH0sXG4gICAgbmV4dFRhYjogZnVuY3Rpb24gKGkpIHtcbiAgICAgICAgdmFyIHRhYnMgPSB0aGlzLmdldFRhYnModGhpcy5wcm9wcy5mbG93KTtcbiAgICAgICAgdmFyIGN1cnJlbnRJbmRleCA9IHRhYnMuaW5kZXhPZih0aGlzLmdldFBhcmFtcygpLmRldGFpbFRhYik7XG4gICAgICAgIC8vIEpTIG1vZHVsbyBvcGVyYXRvciBkb2Vzbid0IGNvcnJlY3QgbmVnYXRpdmUgbnVtYmVycywgbWFrZSBzdXJlIHRoYXQgd2UgYXJlIHBvc2l0aXZlLlxuICAgICAgICB2YXIgbmV4dEluZGV4ID0gKGN1cnJlbnRJbmRleCArIGkgKyB0YWJzLmxlbmd0aCkgJSB0YWJzLmxlbmd0aDtcbiAgICAgICAgdGhpcy5zZWxlY3RUYWIodGFic1tuZXh0SW5kZXhdKTtcbiAgICB9LFxuICAgIHNlbGVjdFRhYjogZnVuY3Rpb24gKHBhbmVsKSB7XG4gICAgICAgIHRoaXMucmVwbGFjZVdpdGgoXG4gICAgICAgICAgICBcImZsb3dcIixcbiAgICAgICAgICAgIHtcbiAgICAgICAgICAgICAgICBmbG93SWQ6IHRoaXMuZ2V0UGFyYW1zKCkuZmxvd0lkLFxuICAgICAgICAgICAgICAgIGRldGFpbFRhYjogcGFuZWxcbiAgICAgICAgICAgIH1cbiAgICAgICAgKTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcbiAgICAgICAgdmFyIHRhYnMgPSB0aGlzLmdldFRhYnMoZmxvdyk7XG4gICAgICAgIHZhciBhY3RpdmUgPSB0aGlzLmdldFBhcmFtcygpLmRldGFpbFRhYjtcblxuICAgICAgICBpZiAoIV8uY29udGFpbnModGFicywgYWN0aXZlKSkge1xuICAgICAgICAgICAgaWYgKGFjdGl2ZSA9PT0gXCJyZXNwb25zZVwiICYmIGZsb3cuZXJyb3IpIHtcbiAgICAgICAgICAgICAgICBhY3RpdmUgPSBcImVycm9yXCI7XG4gICAgICAgICAgICB9IGVsc2UgaWYgKGFjdGl2ZSA9PT0gXCJlcnJvclwiICYmIGZsb3cucmVzcG9uc2UpIHtcbiAgICAgICAgICAgICAgICBhY3RpdmUgPSBcInJlc3BvbnNlXCI7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIGFjdGl2ZSA9IHRhYnNbMF07XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICB0aGlzLnNlbGVjdFRhYihhY3RpdmUpO1xuICAgICAgICB9XG5cbiAgICAgICAgdmFyIFRhYiA9IGFsbFRhYnNbYWN0aXZlXTtcbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJmbG93LWRldGFpbFwiLCBvblNjcm9sbDogdGhpcy5hZGp1c3RIZWFkfSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChGbG93RGV0YWlsTmF2LCB7cmVmOiBcImhlYWRcIiwgXG4gICAgICAgICAgICAgICAgICAgIGZsb3c6IGZsb3csIFxuICAgICAgICAgICAgICAgICAgICB0YWJzOiB0YWJzLCBcbiAgICAgICAgICAgICAgICAgICAgYWN0aXZlOiBhY3RpdmUsIFxuICAgICAgICAgICAgICAgICAgICBzZWxlY3RUYWI6IHRoaXMuc2VsZWN0VGFifSksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoVGFiLCB7ZmxvdzogZmxvd30pXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbm1vZHVsZS5leHBvcnRzID0ge1xuICAgIEZsb3dEZXRhaWw6IEZsb3dEZXRhaWxcbn07IiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xudmFyIGZsb3d1dGlscyA9IHJlcXVpcmUoXCIuLi9mbG93L3V0aWxzLmpzXCIpO1xudmFyIHV0aWxzID0gcmVxdWlyZShcIi4uL3V0aWxzLmpzXCIpO1xuXG52YXIgVExTQ29sdW1uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlRMU0NvbHVtblwiLFxuICAgIHN0YXRpY3M6IHtcbiAgICAgICAgcmVuZGVyVGl0bGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGhcIiwge2tleTogXCJ0bHNcIiwgY2xhc3NOYW1lOiBcImNvbC10bHNcIn0pO1xuICAgICAgICB9XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG4gICAgICAgIHZhciBzc2wgPSAoZmxvdy5yZXF1ZXN0LnNjaGVtZSA9PSBcImh0dHBzXCIpO1xuICAgICAgICB2YXIgY2xhc3NlcztcbiAgICAgICAgaWYgKHNzbCkge1xuICAgICAgICAgICAgY2xhc3NlcyA9IFwiY29sLXRscyBjb2wtdGxzLWh0dHBzXCI7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBjbGFzc2VzID0gXCJjb2wtdGxzIGNvbC10bHMtaHR0cFwiO1xuICAgICAgICB9XG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwge2NsYXNzTmFtZTogY2xhc3Nlc30pO1xuICAgIH1cbn0pO1xuXG5cbnZhciBJY29uQ29sdW1uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkljb25Db2x1bW5cIixcbiAgICBzdGF0aWNzOiB7XG4gICAgICAgIHJlbmRlclRpdGxlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRoXCIsIHtrZXk6IFwiaWNvblwiLCBjbGFzc05hbWU6IFwiY29sLWljb25cIn0pO1xuICAgICAgICB9XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG5cbiAgICAgICAgdmFyIGljb247XG4gICAgICAgIGlmIChmbG93LnJlc3BvbnNlKSB7XG4gICAgICAgICAgICB2YXIgY29udGVudFR5cGUgPSBmbG93dXRpbHMuUmVzcG9uc2VVdGlscy5nZXRDb250ZW50VHlwZShmbG93LnJlc3BvbnNlKTtcblxuICAgICAgICAgICAgLy9UT0RPOiBXZSBzaG91bGQgYXNzaWduIGEgdHlwZSB0byB0aGUgZmxvdyBzb21ld2hlcmUgZWxzZS5cbiAgICAgICAgICAgIGlmIChmbG93LnJlc3BvbnNlLmNvZGUgPT0gMzA0KSB7XG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1ub3QtbW9kaWZpZWRcIjtcbiAgICAgICAgICAgIH0gZWxzZSBpZiAoMzAwIDw9IGZsb3cucmVzcG9uc2UuY29kZSAmJiBmbG93LnJlc3BvbnNlLmNvZGUgPCA0MDApIHtcbiAgICAgICAgICAgICAgICBpY29uID0gXCJyZXNvdXJjZS1pY29uLXJlZGlyZWN0XCI7XG4gICAgICAgICAgICB9IGVsc2UgaWYgKGNvbnRlbnRUeXBlICYmIGNvbnRlbnRUeXBlLmluZGV4T2YoXCJpbWFnZVwiKSA+PSAwKSB7XG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1pbWFnZVwiO1xuICAgICAgICAgICAgfSBlbHNlIGlmIChjb250ZW50VHlwZSAmJiBjb250ZW50VHlwZS5pbmRleE9mKFwiamF2YXNjcmlwdFwiKSA+PSAwKSB7XG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1qc1wiO1xuICAgICAgICAgICAgfSBlbHNlIGlmIChjb250ZW50VHlwZSAmJiBjb250ZW50VHlwZS5pbmRleE9mKFwiY3NzXCIpID49IDApIHtcbiAgICAgICAgICAgICAgICBpY29uID0gXCJyZXNvdXJjZS1pY29uLWNzc1wiO1xuICAgICAgICAgICAgfSBlbHNlIGlmIChjb250ZW50VHlwZSAmJiBjb250ZW50VHlwZS5pbmRleE9mKFwiaHRtbFwiKSA+PSAwKSB7XG4gICAgICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1kb2N1bWVudFwiO1xuICAgICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICAgIGlmICghaWNvbikge1xuICAgICAgICAgICAgaWNvbiA9IFwicmVzb3VyY2UtaWNvbi1wbGFpblwiO1xuICAgICAgICB9XG5cblxuICAgICAgICBpY29uICs9IFwiIHJlc291cmNlLWljb25cIjtcbiAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCB7Y2xhc3NOYW1lOiBcImNvbC1pY29uXCJ9LCBcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogaWNvbn0pXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBQYXRoQ29sdW1uID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlBhdGhDb2x1bW5cIixcbiAgICBzdGF0aWNzOiB7XG4gICAgICAgIHJlbmRlclRpdGxlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRoXCIsIHtrZXk6IFwicGF0aFwiLCBjbGFzc05hbWU6IFwiY29sLXBhdGhcIn0sIFwiUGF0aFwiKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIHtjbGFzc05hbWU6IFwiY29sLXBhdGhcIn0sIFxuICAgICAgICAgICAgZmxvdy5yZXF1ZXN0LmlzX3JlcGxheSA/IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJpXCIsIHtjbGFzc05hbWU6IFwiZmEgZmEtZncgZmEtcmVwZWF0IHB1bGwtcmlnaHRcIn0pIDogbnVsbCwgXG4gICAgICAgICAgICBmbG93LmludGVyY2VwdGVkID8gUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge2NsYXNzTmFtZTogXCJmYSBmYS1mdyBmYS1wYXVzZSBwdWxsLXJpZ2h0XCJ9KSA6IG51bGwsIFxuICAgICAgICAgICAgZmxvdy5yZXF1ZXN0LnNjaGVtZSArIFwiOi8vXCIgKyBmbG93LnJlcXVlc3QuaG9zdCArIGZsb3cucmVxdWVzdC5wYXRoXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cblxudmFyIE1ldGhvZENvbHVtbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJNZXRob2RDb2x1bW5cIixcbiAgICBzdGF0aWNzOiB7XG4gICAgICAgIHJlbmRlclRpdGxlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRoXCIsIHtrZXk6IFwibWV0aG9kXCIsIGNsYXNzTmFtZTogXCJjb2wtbWV0aG9kXCJ9LCBcIk1ldGhvZFwiKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIHtjbGFzc05hbWU6IFwiY29sLW1ldGhvZFwifSwgZmxvdy5yZXF1ZXN0Lm1ldGhvZCk7XG4gICAgfVxufSk7XG5cblxudmFyIFN0YXR1c0NvbHVtbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJTdGF0dXNDb2x1bW5cIixcbiAgICBzdGF0aWNzOiB7XG4gICAgICAgIHJlbmRlclRpdGxlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRoXCIsIHtrZXk6IFwic3RhdHVzXCIsIGNsYXNzTmFtZTogXCJjb2wtc3RhdHVzXCJ9LCBcIlN0YXR1c1wiKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuICAgICAgICB2YXIgc3RhdHVzO1xuICAgICAgICBpZiAoZmxvdy5yZXNwb25zZSkge1xuICAgICAgICAgICAgc3RhdHVzID0gZmxvdy5yZXNwb25zZS5jb2RlO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgc3RhdHVzID0gbnVsbDtcbiAgICAgICAgfVxuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIHtjbGFzc05hbWU6IFwiY29sLXN0YXR1c1wifSwgc3RhdHVzKTtcbiAgICB9XG59KTtcblxuXG52YXIgU2l6ZUNvbHVtbiA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJTaXplQ29sdW1uXCIsXG4gICAgc3RhdGljczoge1xuICAgICAgICByZW5kZXJUaXRsZTogZnVuY3Rpb24gKCkge1xuICAgICAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0aFwiLCB7a2V5OiBcInNpemVcIiwgY2xhc3NOYW1lOiBcImNvbC1zaXplXCJ9LCBcIlNpemVcIik7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMucHJvcHMuZmxvdztcblxuICAgICAgICB2YXIgdG90YWwgPSBmbG93LnJlcXVlc3QuY29udGVudExlbmd0aDtcbiAgICAgICAgaWYgKGZsb3cucmVzcG9uc2UpIHtcbiAgICAgICAgICAgIHRvdGFsICs9IGZsb3cucmVzcG9uc2UuY29udGVudExlbmd0aCB8fCAwO1xuICAgICAgICB9XG4gICAgICAgIHZhciBzaXplID0gdXRpbHMuZm9ybWF0U2l6ZSh0b3RhbCk7XG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwge2NsYXNzTmFtZTogXCJjb2wtc2l6ZVwifSwgc2l6ZSk7XG4gICAgfVxufSk7XG5cblxudmFyIFRpbWVDb2x1bW4gPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiVGltZUNvbHVtblwiLFxuICAgIHN0YXRpY3M6IHtcbiAgICAgICAgcmVuZGVyVGl0bGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGhcIiwge2tleTogXCJ0aW1lXCIsIGNsYXNzTmFtZTogXCJjb2wtdGltZVwifSwgXCJUaW1lXCIpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZsb3cgPSB0aGlzLnByb3BzLmZsb3c7XG4gICAgICAgIHZhciB0aW1lO1xuICAgICAgICBpZiAoZmxvdy5yZXNwb25zZSkge1xuICAgICAgICAgICAgdGltZSA9IHV0aWxzLmZvcm1hdFRpbWVEZWx0YSgxMDAwICogKGZsb3cucmVzcG9uc2UudGltZXN0YW1wX2VuZCAtIGZsb3cucmVxdWVzdC50aW1lc3RhbXBfc3RhcnQpKTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHRpbWUgPSBcIi4uLlwiO1xuICAgICAgICB9XG4gICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGRcIiwge2NsYXNzTmFtZTogXCJjb2wtdGltZVwifSwgdGltZSk7XG4gICAgfVxufSk7XG5cblxudmFyIGFsbF9jb2x1bW5zID0gW1xuICAgIFRMU0NvbHVtbixcbiAgICBJY29uQ29sdW1uLFxuICAgIFBhdGhDb2x1bW4sXG4gICAgTWV0aG9kQ29sdW1uLFxuICAgIFN0YXR1c0NvbHVtbixcbiAgICBTaXplQ29sdW1uLFxuICAgIFRpbWVDb2x1bW5dO1xuXG5cbm1vZHVsZS5leHBvcnRzID0gYWxsX2NvbHVtbnM7XG5cblxuIiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xudmFyIHV0aWxzID0gcmVxdWlyZShcIi4vdXRpbHMuanNcIik7XG52YXIgVmlydHVhbFNjcm9sbE1peGluID0gcmVxdWlyZShcIi4vdmlydHVhbHNjcm9sbC5qc1wiKTtcbnZhciBmbG93dGFibGVfY29sdW1ucyA9IHJlcXVpcmUoXCIuL2Zsb3d0YWJsZS1jb2x1bW5zLmpzXCIpO1xuXG52YXIgRmxvd1JvdyA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGbG93Um93XCIsXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmbG93ID0gdGhpcy5wcm9wcy5mbG93O1xuICAgICAgICB2YXIgY29sdW1ucyA9IHRoaXMucHJvcHMuY29sdW1ucy5tYXAoZnVuY3Rpb24gKENvbHVtbikge1xuICAgICAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoQ29sdW1uLCB7a2V5OiBDb2x1bW4uZGlzcGxheU5hbWUsIGZsb3c6IGZsb3d9KTtcbiAgICAgICAgfS5iaW5kKHRoaXMpKTtcbiAgICAgICAgdmFyIGNsYXNzTmFtZSA9IFwiXCI7XG4gICAgICAgIGlmICh0aGlzLnByb3BzLnNlbGVjdGVkKSB7XG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCIgc2VsZWN0ZWRcIjtcbiAgICAgICAgfVxuICAgICAgICBpZiAodGhpcy5wcm9wcy5oaWdobGlnaHRlZCkge1xuICAgICAgICAgICAgY2xhc3NOYW1lICs9IFwiIGhpZ2hsaWdodGVkXCI7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKGZsb3cuaW50ZXJjZXB0ZWQpIHtcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcIiBpbnRlcmNlcHRlZFwiO1xuICAgICAgICB9XG4gICAgICAgIGlmIChmbG93LnJlcXVlc3QpIHtcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcIiBoYXMtcmVxdWVzdFwiO1xuICAgICAgICB9XG4gICAgICAgIGlmIChmbG93LnJlc3BvbnNlKSB7XG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCIgaGFzLXJlc3BvbnNlXCI7XG4gICAgICAgIH1cblxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRyXCIsIHtjbGFzc05hbWU6IGNsYXNzTmFtZSwgb25DbGljazogdGhpcy5wcm9wcy5zZWxlY3RGbG93LmJpbmQobnVsbCwgZmxvdyl9LCBcbiAgICAgICAgICAgICAgICBjb2x1bW5zXG4gICAgICAgICAgICApKTtcbiAgICB9LFxuICAgIHNob3VsZENvbXBvbmVudFVwZGF0ZTogZnVuY3Rpb24gKG5leHRQcm9wcykge1xuICAgICAgICByZXR1cm4gdHJ1ZTtcbiAgICAgICAgLy8gRnVydGhlciBvcHRpbWl6YXRpb24gY291bGQgYmUgZG9uZSBoZXJlXG4gICAgICAgIC8vIGJ5IGNhbGxpbmcgZm9yY2VVcGRhdGUgb24gZmxvdyB1cGRhdGVzLCBzZWxlY3Rpb24gY2hhbmdlcyBhbmQgY29sdW1uIGNoYW5nZXMuXG4gICAgICAgIC8vcmV0dXJuIChcbiAgICAgICAgLy8odGhpcy5wcm9wcy5jb2x1bW5zLmxlbmd0aCAhPT0gbmV4dFByb3BzLmNvbHVtbnMubGVuZ3RoKSB8fFxuICAgICAgICAvLyh0aGlzLnByb3BzLnNlbGVjdGVkICE9PSBuZXh0UHJvcHMuc2VsZWN0ZWQpXG4gICAgICAgIC8vKTtcbiAgICB9XG59KTtcblxudmFyIEZsb3dUYWJsZUhlYWQgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiRmxvd1RhYmxlSGVhZFwiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgY29sdW1ucyA9IHRoaXMucHJvcHMuY29sdW1ucy5tYXAoZnVuY3Rpb24gKGNvbHVtbikge1xuICAgICAgICAgICAgcmV0dXJuIGNvbHVtbi5yZW5kZXJUaXRsZSgpO1xuICAgICAgICB9LmJpbmQodGhpcykpO1xuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcInRoZWFkXCIsIG51bGwsIFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRyXCIsIG51bGwsIGNvbHVtbnMpXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cblxudmFyIFJPV19IRUlHSFQgPSAzMjtcblxudmFyIEZsb3dUYWJsZSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGbG93VGFibGVcIixcbiAgICBtaXhpbnM6IFt1dGlscy5TdGlja3lIZWFkTWl4aW4sIHV0aWxzLkF1dG9TY3JvbGxNaXhpbiwgVmlydHVhbFNjcm9sbE1peGluXSxcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgIGNvbHVtbnM6IGZsb3d0YWJsZV9jb2x1bW5zXG4gICAgICAgIH07XG4gICAgfSxcbiAgICBjb21wb25lbnRXaWxsTW91bnQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgaWYgKHRoaXMucHJvcHMudmlldykge1xuICAgICAgICAgICAgdGhpcy5wcm9wcy52aWV3LmFkZExpc3RlbmVyKFwiYWRkIHVwZGF0ZSByZW1vdmUgcmVjYWxjdWxhdGVcIiwgdGhpcy5vbkNoYW5nZSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxSZWNlaXZlUHJvcHM6IGZ1bmN0aW9uIChuZXh0UHJvcHMpIHtcbiAgICAgICAgaWYgKG5leHRQcm9wcy52aWV3ICE9PSB0aGlzLnByb3BzLnZpZXcpIHtcbiAgICAgICAgICAgIGlmICh0aGlzLnByb3BzLnZpZXcpIHtcbiAgICAgICAgICAgICAgICB0aGlzLnByb3BzLnZpZXcucmVtb3ZlTGlzdGVuZXIoXCJhZGQgdXBkYXRlIHJlbW92ZSByZWNhbGN1bGF0ZVwiKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIG5leHRQcm9wcy52aWV3LmFkZExpc3RlbmVyKFwiYWRkIHVwZGF0ZSByZW1vdmUgcmVjYWxjdWxhdGVcIiwgdGhpcy5vbkNoYW5nZSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGdldERlZmF1bHRQcm9wczogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgcm93SGVpZ2h0OiBST1dfSEVJR0hUXG4gICAgICAgIH07XG4gICAgfSxcbiAgICBvblNjcm9sbEZsb3dUYWJsZTogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLmFkanVzdEhlYWQoKTtcbiAgICAgICAgdGhpcy5vblNjcm9sbCgpO1xuICAgIH0sXG4gICAgb25DaGFuZ2U6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5mb3JjZVVwZGF0ZSgpO1xuICAgIH0sXG4gICAgc2Nyb2xsSW50b1ZpZXc6IGZ1bmN0aW9uIChmbG93KSB7XG4gICAgICAgIHRoaXMuc2Nyb2xsUm93SW50b1ZpZXcoXG4gICAgICAgICAgICB0aGlzLnByb3BzLnZpZXcuaW5kZXgoZmxvdyksXG4gICAgICAgICAgICB0aGlzLnJlZnMuYm9keS5nZXRET01Ob2RlKCkub2Zmc2V0VG9wXG4gICAgICAgICk7XG4gICAgfSxcbiAgICByZW5kZXJSb3c6IGZ1bmN0aW9uIChmbG93KSB7XG4gICAgICAgIHZhciBzZWxlY3RlZCA9IChmbG93ID09PSB0aGlzLnByb3BzLnNlbGVjdGVkKTtcbiAgICAgICAgdmFyIGhpZ2hsaWdodGVkID1cbiAgICAgICAgICAgIChcbiAgICAgICAgICAgIHRoaXMucHJvcHMudmlldy5faGlnaGxpZ2h0ICYmXG4gICAgICAgICAgICB0aGlzLnByb3BzLnZpZXcuX2hpZ2hsaWdodFtmbG93LmlkXVxuICAgICAgICAgICAgKTtcblxuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChGbG93Um93LCB7a2V5OiBmbG93LmlkLCBcbiAgICAgICAgICAgIHJlZjogZmxvdy5pZCwgXG4gICAgICAgICAgICBmbG93OiBmbG93LCBcbiAgICAgICAgICAgIGNvbHVtbnM6IHRoaXMuc3RhdGUuY29sdW1ucywgXG4gICAgICAgICAgICBzZWxlY3RlZDogc2VsZWN0ZWQsIFxuICAgICAgICAgICAgaGlnaGxpZ2h0ZWQ6IGhpZ2hsaWdodGVkLCBcbiAgICAgICAgICAgIHNlbGVjdEZsb3c6IHRoaXMucHJvcHMuc2VsZWN0Rmxvd31cbiAgICAgICAgKTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICAvL2NvbnNvbGUubG9nKFwicmVuZGVyIGZsb3d0YWJsZVwiLCB0aGlzLnN0YXRlLnN0YXJ0LCB0aGlzLnN0YXRlLnN0b3AsIHRoaXMucHJvcHMuc2VsZWN0ZWQpO1xuICAgICAgICB2YXIgZmxvd3MgPSB0aGlzLnByb3BzLnZpZXcgPyB0aGlzLnByb3BzLnZpZXcubGlzdCA6IFtdO1xuXG4gICAgICAgIHZhciByb3dzID0gdGhpcy5yZW5kZXJSb3dzKGZsb3dzKTtcblxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcImZsb3ctdGFibGVcIiwgb25TY3JvbGw6IHRoaXMub25TY3JvbGxGbG93VGFibGV9LCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGFibGVcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoRmxvd1RhYmxlSGVhZCwge3JlZjogXCJoZWFkXCIsIFxuICAgICAgICAgICAgICAgICAgICAgICAgY29sdW1uczogdGhpcy5zdGF0ZS5jb2x1bW5zfSksIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGJvZHlcIiwge3JlZjogXCJib2R5XCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmdldFBsYWNlaG9sZGVyVG9wKGZsb3dzLmxlbmd0aCksIFxuICAgICAgICAgICAgICAgICAgICAgICAgcm93cywgXG4gICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5nZXRQbGFjZWhvbGRlckJvdHRvbShmbG93cy5sZW5ndGgpIFxuICAgICAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG5tb2R1bGUuZXhwb3J0cyA9IEZsb3dUYWJsZTtcbiIsInZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcblxudmFyIEZvb3RlciA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGb290ZXJcIixcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIG1vZGUgPSB0aGlzLnByb3BzLnNldHRpbmdzLm1vZGU7XG4gICAgICAgIHZhciBpbnRlcmNlcHQgPSB0aGlzLnByb3BzLnNldHRpbmdzLmludGVyY2VwdDtcbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJmb290ZXJcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgbW9kZSAhPSBcInJlZ3VsYXJcIiA/IFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIsIHtjbGFzc05hbWU6IFwibGFiZWwgbGFiZWwtc3VjY2Vzc1wifSwgbW9kZSwgXCIgbW9kZVwiKSA6IG51bGwsIFxuICAgICAgICAgICAgICAgIFwiwqBcIiwgXG4gICAgICAgICAgICAgICAgaW50ZXJjZXB0ID8gUmVhY3QuY3JlYXRlRWxlbWVudChcInNwYW5cIiwge2NsYXNzTmFtZTogXCJsYWJlbCBsYWJlbC1zdWNjZXNzXCJ9LCBcIkludGVyY2VwdDogXCIsIGludGVyY2VwdCkgOiBudWxsXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbm1vZHVsZS5leHBvcnRzID0gRm9vdGVyOyIsInZhciBSZWFjdCA9IHJlcXVpcmUoXCJyZWFjdFwiKTtcbnZhciAkID0gcmVxdWlyZShcImpxdWVyeVwiKTtcblxudmFyIHV0aWxzID0gcmVxdWlyZShcIi4vdXRpbHMuanNcIik7XG5cbnZhciBGaWx0ZXJEb2NzID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIkZpbHRlckRvY3NcIixcbiAgICBzdGF0aWNzOiB7XG4gICAgICAgIHhocjogZmFsc2UsXG4gICAgICAgIGRvYzogZmFsc2VcbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxNb3VudDogZnVuY3Rpb24gKCkge1xuICAgICAgICBpZiAoIUZpbHRlckRvY3MuZG9jKSB7XG4gICAgICAgICAgICBGaWx0ZXJEb2NzLnhociA9ICQuZ2V0SlNPTihcIi9maWx0ZXItaGVscFwiKS5kb25lKGZ1bmN0aW9uIChkb2MpIHtcbiAgICAgICAgICAgICAgICBGaWx0ZXJEb2NzLmRvYyA9IGRvYztcbiAgICAgICAgICAgICAgICBGaWx0ZXJEb2NzLnhociA9IGZhbHNlO1xuICAgICAgICAgICAgfSk7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKEZpbHRlckRvY3MueGhyKSB7XG4gICAgICAgICAgICBGaWx0ZXJEb2NzLnhoci5kb25lKGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgICAgICB0aGlzLmZvcmNlVXBkYXRlKCk7XG4gICAgICAgICAgICB9LmJpbmQodGhpcykpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgaWYgKCFGaWx0ZXJEb2NzLmRvYykge1xuICAgICAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJpXCIsIHtjbGFzc05hbWU6IFwiZmEgZmEtc3Bpbm5lciBmYS1zcGluXCJ9KTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHZhciBjb21tYW5kcyA9IEZpbHRlckRvY3MuZG9jLmNvbW1hbmRzLm1hcChmdW5jdGlvbiAoYykge1xuICAgICAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidHJcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0ZFwiLCBudWxsLCBjWzBdLnJlcGxhY2UoXCIgXCIsICdcXHUwMGEwJykpLCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIG51bGwsIGNbMV0pXG4gICAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgIH0pO1xuICAgICAgICAgICAgY29tbWFuZHMucHVzaChSZWFjdC5jcmVhdGVFbGVtZW50KFwidHJcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcInRkXCIsIHtjb2xTcGFuOiBcIjJcIn0sIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiYVwiLCB7aHJlZjogXCJodHRwczovL21pdG1wcm94eS5vcmcvZG9jL2ZlYXR1cmVzL2ZpbHRlcnMuaHRtbFwiLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIHRhcmdldDogXCJfYmxhbmtcIn0sIFxuICAgICAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge2NsYXNzTmFtZTogXCJmYSBmYS1leHRlcm5hbC1saW5rXCJ9KSwgXG4gICAgICAgICAgICAgICAgICAgIFwiwqAgbWl0bXByb3h5IGRvY3NcIilcbiAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICApKTtcbiAgICAgICAgICAgIHJldHVybiBSZWFjdC5jcmVhdGVFbGVtZW50KFwidGFibGVcIiwge2NsYXNzTmFtZTogXCJ0YWJsZSB0YWJsZS1jb25kZW5zZWRcIn0sIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ0Ym9keVwiLCBudWxsLCBjb21tYW5kcylcbiAgICAgICAgICAgICk7XG4gICAgICAgIH1cbiAgICB9XG59KTtcbnZhciBGaWx0ZXJJbnB1dCA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGaWx0ZXJJbnB1dFwiLFxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICAvLyBDb25zaWRlciBib3RoIGZvY3VzIGFuZCBtb3VzZW92ZXIgZm9yIHNob3dpbmcvaGlkaW5nIHRoZSB0b29sdGlwLFxuICAgICAgICAvLyBiZWNhdXNlIG9uQmx1ciBvZiB0aGUgaW5wdXQgaXMgdHJpZ2dlcmVkIGJlZm9yZSB0aGUgY2xpY2sgb24gdGhlIHRvb2x0aXBcbiAgICAgICAgLy8gZmluYWxpemVkLCBoaWRpbmcgdGhlIHRvb2x0aXAganVzdCBhcyB0aGUgdXNlciBjbGlja3Mgb24gaXQuXG4gICAgICAgIHJldHVybiB7XG4gICAgICAgICAgICB2YWx1ZTogdGhpcy5wcm9wcy52YWx1ZSxcbiAgICAgICAgICAgIGZvY3VzOiBmYWxzZSxcbiAgICAgICAgICAgIG1vdXNlZm9jdXM6IGZhbHNlXG4gICAgICAgIH07XG4gICAgfSxcbiAgICBjb21wb25lbnRXaWxsUmVjZWl2ZVByb3BzOiBmdW5jdGlvbiAobmV4dFByb3BzKSB7XG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe3ZhbHVlOiBuZXh0UHJvcHMudmFsdWV9KTtcbiAgICB9LFxuICAgIG9uQ2hhbmdlOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICB2YXIgbmV4dFZhbHVlID0gZS50YXJnZXQudmFsdWU7XG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe1xuICAgICAgICAgICAgdmFsdWU6IG5leHRWYWx1ZVxuICAgICAgICB9KTtcbiAgICAgICAgLy8gT25seSBwcm9wYWdhdGUgdmFsaWQgZmlsdGVycyB1cHdhcmRzLlxuICAgICAgICBpZiAodGhpcy5pc1ZhbGlkKG5leHRWYWx1ZSkpIHtcbiAgICAgICAgICAgIHRoaXMucHJvcHMub25DaGFuZ2UobmV4dFZhbHVlKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgaXNWYWxpZDogZnVuY3Rpb24gKGZpbHQpIHtcbiAgICAgICAgdHJ5IHtcbiAgICAgICAgICAgIEZpbHQucGFyc2UoZmlsdCB8fCB0aGlzLnN0YXRlLnZhbHVlKTtcbiAgICAgICAgICAgIHJldHVybiB0cnVlO1xuICAgICAgICB9IGNhdGNoIChlKSB7XG4gICAgICAgICAgICByZXR1cm4gZmFsc2U7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGdldERlc2M6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGRlc2M7XG4gICAgICAgIHRyeSB7XG4gICAgICAgICAgICBkZXNjID0gRmlsdC5wYXJzZSh0aGlzLnN0YXRlLnZhbHVlKS5kZXNjO1xuICAgICAgICB9IGNhdGNoIChlKSB7XG4gICAgICAgICAgICBkZXNjID0gXCJcIiArIGU7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKGRlc2MgIT09IFwidHJ1ZVwiKSB7XG4gICAgICAgICAgICByZXR1cm4gZGVzYztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChGaWx0ZXJEb2NzLCBudWxsKVxuICAgICAgICAgICAgKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgb25Gb2N1czogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLnNldFN0YXRlKHtmb2N1czogdHJ1ZX0pO1xuICAgIH0sXG4gICAgb25CbHVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe2ZvY3VzOiBmYWxzZX0pO1xuICAgIH0sXG4gICAgb25Nb3VzZUVudGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuc2V0U3RhdGUoe21vdXNlZm9jdXM6IHRydWV9KTtcbiAgICB9LFxuICAgIG9uTW91c2VMZWF2ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLnNldFN0YXRlKHttb3VzZWZvY3VzOiBmYWxzZX0pO1xuICAgIH0sXG4gICAgb25LZXlEb3duOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICBpZiAoZS5rZXlDb2RlID09PSBLZXkuRVNDIHx8IGUua2V5Q29kZSA9PT0gS2V5LkVOVEVSKSB7XG4gICAgICAgICAgICB0aGlzLmJsdXIoKTtcbiAgICAgICAgICAgIC8vIElmIGNsb3NlZCB1c2luZyBFU0MvRU5URVIsIGhpZGUgdGhlIHRvb2x0aXAuXG4gICAgICAgICAgICB0aGlzLnNldFN0YXRlKHttb3VzZWZvY3VzOiBmYWxzZX0pO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBibHVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMucmVmcy5pbnB1dC5nZXRET01Ob2RlKCkuYmx1cigpO1xuICAgIH0sXG4gICAgZm9jdXM6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5yZWZzLmlucHV0LmdldERPTU5vZGUoKS5zZWxlY3QoKTtcbiAgICB9LFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgaXNWYWxpZCA9IHRoaXMuaXNWYWxpZCgpO1xuICAgICAgICB2YXIgaWNvbiA9IFwiZmEgZmEtZncgZmEtXCIgKyB0aGlzLnByb3BzLnR5cGU7XG4gICAgICAgIHZhciBncm91cENsYXNzTmFtZSA9IFwiZmlsdGVyLWlucHV0IGlucHV0LWdyb3VwXCIgKyAoaXNWYWxpZCA/IFwiXCIgOiBcIiBoYXMtZXJyb3JcIik7XG5cbiAgICAgICAgdmFyIHBvcG92ZXI7XG4gICAgICAgIGlmICh0aGlzLnN0YXRlLmZvY3VzIHx8IHRoaXMuc3RhdGUubW91c2Vmb2N1cykge1xuICAgICAgICAgICAgcG9wb3ZlciA9IChcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwicG9wb3ZlciBib3R0b21cIiwgb25Nb3VzZUVudGVyOiB0aGlzLm9uTW91c2VFbnRlciwgb25Nb3VzZUxlYXZlOiB0aGlzLm9uTW91c2VMZWF2ZX0sIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwiYXJyb3dcIn0pLCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcInBvcG92ZXItY29udGVudFwifSwgXG4gICAgICAgICAgICAgICAgICAgIHRoaXMuZ2V0RGVzYygpXG4gICAgICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICApO1xuICAgICAgICB9XG5cbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogZ3JvdXBDbGFzc05hbWV9LCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwic3BhblwiLCB7Y2xhc3NOYW1lOiBcImlucHV0LWdyb3VwLWFkZG9uXCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge2NsYXNzTmFtZTogaWNvbiwgc3R5bGU6IHtjb2xvcjogdGhpcy5wcm9wcy5jb2xvcn19KVxuICAgICAgICAgICAgICAgICksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJpbnB1dFwiLCB7dHlwZTogXCJ0ZXh0XCIsIHBsYWNlaG9sZGVyOiB0aGlzLnByb3BzLnBsYWNlaG9sZGVyLCBjbGFzc05hbWU6IFwiZm9ybS1jb250cm9sXCIsIFxuICAgICAgICAgICAgICAgICAgICByZWY6IFwiaW5wdXRcIiwgXG4gICAgICAgICAgICAgICAgICAgIG9uQ2hhbmdlOiB0aGlzLm9uQ2hhbmdlLCBcbiAgICAgICAgICAgICAgICAgICAgb25Gb2N1czogdGhpcy5vbkZvY3VzLCBcbiAgICAgICAgICAgICAgICAgICAgb25CbHVyOiB0aGlzLm9uQmx1ciwgXG4gICAgICAgICAgICAgICAgICAgIG9uS2V5RG93bjogdGhpcy5vbktleURvd24sIFxuICAgICAgICAgICAgICAgICAgICB2YWx1ZTogdGhpcy5zdGF0ZS52YWx1ZX0pLCBcbiAgICAgICAgICAgICAgICBwb3BvdmVyXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbnZhciBNYWluTWVudSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJNYWluTWVudVwiLFxuICAgIG1peGluczogW3V0aWxzLk5hdmlnYXRpb24sIHV0aWxzLlN0YXRlXSxcbiAgICBzdGF0aWNzOiB7XG4gICAgICAgIHRpdGxlOiBcIlN0YXJ0XCIsXG4gICAgICAgIHJvdXRlOiBcImZsb3dzXCJcbiAgICB9LFxuICAgIG9uRmlsdGVyQ2hhbmdlOiBmdW5jdGlvbiAodmFsKSB7XG4gICAgICAgIHZhciBkID0ge307XG4gICAgICAgIGRbUXVlcnkuRklMVEVSXSA9IHZhbDtcbiAgICAgICAgdGhpcy5zZXRRdWVyeShkKTtcbiAgICB9LFxuICAgIG9uSGlnaGxpZ2h0Q2hhbmdlOiBmdW5jdGlvbiAodmFsKSB7XG4gICAgICAgIHZhciBkID0ge307XG4gICAgICAgIGRbUXVlcnkuSElHSExJR0hUXSA9IHZhbDtcbiAgICAgICAgdGhpcy5zZXRRdWVyeShkKTtcbiAgICB9LFxuICAgIG9uSW50ZXJjZXB0Q2hhbmdlOiBmdW5jdGlvbiAodmFsKSB7XG4gICAgICAgIFNldHRpbmdzQWN0aW9ucy51cGRhdGUoe2ludGVyY2VwdDogdmFsfSk7XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGZpbHRlciA9IHRoaXMuZ2V0UXVlcnkoKVtRdWVyeS5GSUxURVJdIHx8IFwiXCI7XG4gICAgICAgIHZhciBoaWdobGlnaHQgPSB0aGlzLmdldFF1ZXJ5KClbUXVlcnkuSElHSExJR0hUXSB8fCBcIlwiO1xuICAgICAgICB2YXIgaW50ZXJjZXB0ID0gdGhpcy5wcm9wcy5zZXR0aW5ncy5pbnRlcmNlcHQgfHwgXCJcIjtcblxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwibWVudS1yb3dcIn0sIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KEZpbHRlcklucHV0LCB7XG4gICAgICAgICAgICAgICAgICAgICAgICBwbGFjZWhvbGRlcjogXCJGaWx0ZXJcIiwgXG4gICAgICAgICAgICAgICAgICAgICAgICB0eXBlOiBcImZpbHRlclwiLCBcbiAgICAgICAgICAgICAgICAgICAgICAgIGNvbG9yOiBcImJsYWNrXCIsIFxuICAgICAgICAgICAgICAgICAgICAgICAgdmFsdWU6IGZpbHRlciwgXG4gICAgICAgICAgICAgICAgICAgICAgICBvbkNoYW5nZTogdGhpcy5vbkZpbHRlckNoYW5nZX0pLCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChGaWx0ZXJJbnB1dCwge1xuICAgICAgICAgICAgICAgICAgICAgICAgcGxhY2Vob2xkZXI6IFwiSGlnaGxpZ2h0XCIsIFxuICAgICAgICAgICAgICAgICAgICAgICAgdHlwZTogXCJ0YWdcIiwgXG4gICAgICAgICAgICAgICAgICAgICAgICBjb2xvcjogXCJoc2woNDgsIDEwMCUsIDUwJSlcIiwgXG4gICAgICAgICAgICAgICAgICAgICAgICB2YWx1ZTogaGlnaGxpZ2h0LCBcbiAgICAgICAgICAgICAgICAgICAgICAgIG9uQ2hhbmdlOiB0aGlzLm9uSGlnaGxpZ2h0Q2hhbmdlfSksIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KEZpbHRlcklucHV0LCB7XG4gICAgICAgICAgICAgICAgICAgICAgICBwbGFjZWhvbGRlcjogXCJJbnRlcmNlcHRcIiwgXG4gICAgICAgICAgICAgICAgICAgICAgICB0eXBlOiBcInBhdXNlXCIsIFxuICAgICAgICAgICAgICAgICAgICAgICAgY29sb3I6IFwiaHNsKDIwOCwgNTYlLCA1MyUpXCIsIFxuICAgICAgICAgICAgICAgICAgICAgICAgdmFsdWU6IGludGVyY2VwdCwgXG4gICAgICAgICAgICAgICAgICAgICAgICBvbkNoYW5nZTogdGhpcy5vbkludGVyY2VwdENoYW5nZX0pXG4gICAgICAgICAgICAgICAgKSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcImNsZWFyZml4XCJ9KVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG5cbnZhciBWaWV3TWVudSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJWaWV3TWVudVwiLFxuICAgIHN0YXRpY3M6IHtcbiAgICAgICAgdGl0bGU6IFwiVmlld1wiLFxuICAgICAgICByb3V0ZTogXCJmbG93c1wiXG4gICAgfSxcbiAgICBtaXhpbnM6IFt1dGlscy5OYXZpZ2F0aW9uLCB1dGlscy5TdGF0ZV0sXG4gICAgdG9nZ2xlRXZlbnRMb2c6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGQgPSB7fTtcblxuICAgICAgICBpZiAodGhpcy5nZXRRdWVyeSgpW1F1ZXJ5LlNIT1dfRVZFTlRMT0ddKSB7XG4gICAgICAgICAgICBkW1F1ZXJ5LlNIT1dfRVZFTlRMT0ddID0gdW5kZWZpbmVkO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgZFtRdWVyeS5TSE9XX0VWRU5UTE9HXSA9IFwidFwiOyAvLyBhbnkgbm9uLWZhbHNlIHZhbHVlIHdpbGwgZG8gaXQsIGtlZXAgaXQgc2hvcnRcbiAgICAgICAgfVxuXG4gICAgICAgIHRoaXMuc2V0UXVlcnkoZCk7XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIHNob3dFdmVudExvZyA9IHRoaXMuZ2V0UXVlcnkoKVtRdWVyeS5TSE9XX0VWRU5UTE9HXTtcbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImJ1dHRvblwiLCB7XG4gICAgICAgICAgICAgICAgICAgIGNsYXNzTmFtZTogXCJidG4gXCIgKyAoc2hvd0V2ZW50TG9nID8gXCJidG4tcHJpbWFyeVwiIDogXCJidG4tZGVmYXVsdFwiKSwgXG4gICAgICAgICAgICAgICAgICAgIG9uQ2xpY2s6IHRoaXMudG9nZ2xlRXZlbnRMb2d9LCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge2NsYXNzTmFtZTogXCJmYSBmYS1kYXRhYmFzZVwifSksIFxuICAgICAgICAgICAgICAgIFwiwqBTaG93IEV2ZW50bG9nXCJcbiAgICAgICAgICAgICAgICApLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwic3BhblwiLCBudWxsLCBcIiBcIilcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxuXG52YXIgUmVwb3J0c01lbnUgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiUmVwb3J0c01lbnVcIixcbiAgICBzdGF0aWNzOiB7XG4gICAgICAgIHRpdGxlOiBcIlZpc3VhbGl6YXRpb25cIixcbiAgICAgICAgcm91dGU6IFwicmVwb3J0c1wiXG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwgbnVsbCwgXCJSZXBvcnRzIE1lbnVcIik7XG4gICAgfVxufSk7XG5cbnZhciBGaWxlTWVudSA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJGaWxlTWVudVwiLFxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgc2hvd0ZpbGVNZW51OiBmYWxzZVxuICAgICAgICB9O1xuICAgIH0sXG4gICAgaGFuZGxlRmlsZUNsaWNrOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XG4gICAgICAgIGlmICghdGhpcy5zdGF0ZS5zaG93RmlsZU1lbnUpIHtcbiAgICAgICAgICAgIHZhciBjbG9zZSA9IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgICAgICB0aGlzLnNldFN0YXRlKHtzaG93RmlsZU1lbnU6IGZhbHNlfSk7XG4gICAgICAgICAgICAgICAgZG9jdW1lbnQucmVtb3ZlRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsIGNsb3NlKTtcbiAgICAgICAgICAgIH0uYmluZCh0aGlzKTtcbiAgICAgICAgICAgIGRvY3VtZW50LmFkZEV2ZW50TGlzdGVuZXIoXCJjbGlja1wiLCBjbG9zZSk7XG5cbiAgICAgICAgICAgIHRoaXMuc2V0U3RhdGUoe1xuICAgICAgICAgICAgICAgIHNob3dGaWxlTWVudTogdHJ1ZVxuICAgICAgICAgICAgfSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGhhbmRsZU5ld0NsaWNrOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XG4gICAgICAgIGlmIChjb25maXJtKFwiRGVsZXRlIGFsbCBmbG93cz9cIikpIHtcbiAgICAgICAgICAgIEZsb3dBY3Rpb25zLmNsZWFyKCk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIGhhbmRsZU9wZW5DbGljazogZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICBjb25zb2xlLmVycm9yKFwidW5pbXBsZW1lbnRlZDogaGFuZGxlT3BlbkNsaWNrXCIpO1xuICAgIH0sXG4gICAgaGFuZGxlU2F2ZUNsaWNrOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XG4gICAgICAgIGNvbnNvbGUuZXJyb3IoXCJ1bmltcGxlbWVudGVkOiBoYW5kbGVTYXZlQ2xpY2tcIik7XG4gICAgfSxcbiAgICBoYW5kbGVTaHV0ZG93bkNsaWNrOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XG4gICAgICAgIGNvbnNvbGUuZXJyb3IoXCJ1bmltcGxlbWVudGVkOiBoYW5kbGVTaHV0ZG93bkNsaWNrXCIpO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBmaWxlTWVudUNsYXNzID0gXCJkcm9wZG93biBwdWxsLWxlZnRcIiArICh0aGlzLnN0YXRlLnNob3dGaWxlTWVudSA/IFwiIG9wZW5cIiA6IFwiXCIpO1xuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IGZpbGVNZW51Q2xhc3N9LCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiYVwiLCB7aHJlZjogXCIjXCIsIGNsYXNzTmFtZTogXCJzcGVjaWFsXCIsIG9uQ2xpY2s6IHRoaXMuaGFuZGxlRmlsZUNsaWNrfSwgXCIgRmlsZSBcIiksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJ1bFwiLCB7Y2xhc3NOYW1lOiBcImRyb3Bkb3duLW1lbnVcIiwgcm9sZTogXCJtZW51XCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImxpXCIsIG51bGwsIFxuICAgICAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImFcIiwge2hyZWY6IFwiI1wiLCBvbkNsaWNrOiB0aGlzLmhhbmRsZU5ld0NsaWNrfSwgXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge2NsYXNzTmFtZTogXCJmYSBmYS1mdyBmYS1maWxlXCJ9KSwgXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgXCJOZXdcIlxuICAgICAgICAgICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgICAgICAgICApLCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImxpXCIsIHtyb2xlOiBcInByZXNlbnRhdGlvblwiLCBjbGFzc05hbWU6IFwiZGl2aWRlclwifSksIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwibGlcIiwgbnVsbCwgXG4gICAgICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiYVwiLCB7aHJlZjogXCJodHRwOi8vbWl0bS5pdC9cIiwgdGFyZ2V0OiBcIl9ibGFua1wifSwgXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImlcIiwge2NsYXNzTmFtZTogXCJmYSBmYS1mdyBmYS1leHRlcm5hbC1saW5rXCJ9KSwgXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgXCJJbnN0YWxsIENlcnRpZmljYXRlcy4uLlwiXG4gICAgICAgICAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgICAgICAvKlxuICAgICAgICAgICAgICAgICA8bGk+XG4gICAgICAgICAgICAgICAgIDxhIGhyZWY9XCIjXCIgb25DbGljaz17dGhpcy5oYW5kbGVPcGVuQ2xpY2t9PlxuICAgICAgICAgICAgICAgICA8aSBjbGFzc05hbWU9XCJmYSBmYS1mdyBmYS1mb2xkZXItb3BlblwiPjwvaT5cbiAgICAgICAgICAgICAgICAgT3BlblxuICAgICAgICAgICAgICAgICA8L2E+XG4gICAgICAgICAgICAgICAgIDwvbGk+XG4gICAgICAgICAgICAgICAgIDxsaT5cbiAgICAgICAgICAgICAgICAgPGEgaHJlZj1cIiNcIiBvbkNsaWNrPXt0aGlzLmhhbmRsZVNhdmVDbGlja30+XG4gICAgICAgICAgICAgICAgIDxpIGNsYXNzTmFtZT1cImZhIGZhLWZ3IGZhLXNhdmVcIj48L2k+XG4gICAgICAgICAgICAgICAgIFNhdmVcbiAgICAgICAgICAgICAgICAgPC9hPlxuICAgICAgICAgICAgICAgICA8L2xpPlxuICAgICAgICAgICAgICAgICA8bGkgcm9sZT1cInByZXNlbnRhdGlvblwiIGNsYXNzTmFtZT1cImRpdmlkZXJcIj48L2xpPlxuICAgICAgICAgICAgICAgICA8bGk+XG4gICAgICAgICAgICAgICAgIDxhIGhyZWY9XCIjXCIgb25DbGljaz17dGhpcy5oYW5kbGVTaHV0ZG93bkNsaWNrfT5cbiAgICAgICAgICAgICAgICAgPGkgY2xhc3NOYW1lPVwiZmEgZmEtZncgZmEtcGx1Z1wiPjwvaT5cbiAgICAgICAgICAgICAgICAgU2h1dGRvd25cbiAgICAgICAgICAgICAgICAgPC9hPlxuICAgICAgICAgICAgICAgICA8L2xpPlxuICAgICAgICAgICAgICAgICAqL1xuICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxuXG52YXIgaGVhZGVyX2VudHJpZXMgPSBbTWFpbk1lbnUsIFZpZXdNZW51IC8qLCBSZXBvcnRzTWVudSAqL107XG5cblxudmFyIEhlYWRlciA9IFJlYWN0LmNyZWF0ZUNsYXNzKHtkaXNwbGF5TmFtZTogXCJIZWFkZXJcIixcbiAgICBtaXhpbnM6IFt1dGlscy5OYXZpZ2F0aW9uXSxcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgIGFjdGl2ZTogaGVhZGVyX2VudHJpZXNbMF1cbiAgICAgICAgfTtcbiAgICB9LFxuICAgIGhhbmRsZUNsaWNrOiBmdW5jdGlvbiAoYWN0aXZlLCBlKSB7XG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcbiAgICAgICAgdGhpcy5yZXBsYWNlV2l0aChhY3RpdmUucm91dGUpO1xuICAgICAgICB0aGlzLnNldFN0YXRlKHthY3RpdmU6IGFjdGl2ZX0pO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBoZWFkZXIgPSBoZWFkZXJfZW50cmllcy5tYXAoZnVuY3Rpb24gKGVudHJ5LCBpKSB7XG4gICAgICAgICAgICB2YXIgY2xhc3NlcyA9IFJlYWN0LmFkZG9ucy5jbGFzc1NldCh7XG4gICAgICAgICAgICAgICAgYWN0aXZlOiBlbnRyeSA9PSB0aGlzLnN0YXRlLmFjdGl2ZVxuICAgICAgICAgICAgfSk7XG4gICAgICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJhXCIsIHtrZXk6IGksIFxuICAgICAgICAgICAgICAgICAgICBocmVmOiBcIiNcIiwgXG4gICAgICAgICAgICAgICAgICAgIGNsYXNzTmFtZTogY2xhc3NlcywgXG4gICAgICAgICAgICAgICAgICAgIG9uQ2xpY2s6IHRoaXMuaGFuZGxlQ2xpY2suYmluZCh0aGlzLCBlbnRyeSlcbiAgICAgICAgICAgICAgICB9LCBcbiAgICAgICAgICAgICAgICAgICAgIGVudHJ5LnRpdGxlXG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgKTtcbiAgICAgICAgfS5iaW5kKHRoaXMpKTtcblxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImhlYWRlclwiLCBudWxsLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IFwidGl0bGUtYmFyXCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgXCJtaXRtcHJveHkgXCIsICB0aGlzLnByb3BzLnNldHRpbmdzLnZlcnNpb25cbiAgICAgICAgICAgICAgICApLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwibmF2XCIsIHtjbGFzc05hbWU6IFwibmF2LXRhYnMgbmF2LXRhYnMtbGdcIn0sIFxuICAgICAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KEZpbGVNZW51LCBudWxsKSwgXG4gICAgICAgICAgICAgICAgICAgIGhlYWRlclxuICAgICAgICAgICAgICAgICksIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge2NsYXNzTmFtZTogXCJtZW51XCJ9LCBcbiAgICAgICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudCh0aGlzLnN0YXRlLmFjdGl2ZSwge3NldHRpbmdzOiB0aGlzLnByb3BzLnNldHRpbmdzfSlcbiAgICAgICAgICAgICAgICApXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cblxubW9kdWxlLmV4cG9ydHMgPSB7XG4gICAgSGVhZGVyOiBIZWFkZXJcbn0iLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XG5cbnZhciB1dGlscyA9IHJlcXVpcmUoXCIuL3V0aWxzLmpzXCIpO1xudmFyIHRvcHV0aWxzID0gcmVxdWlyZShcIi4uL3V0aWxzLmpzXCIpO1xudmFyIHZpZXdzID0gcmVxdWlyZShcIi4uL3N0b3JlL3ZpZXcuanNcIik7XG52YXIgRmlsdCA9IHJlcXVpcmUoXCIuLi9maWx0L2ZpbHQuanNcIik7XG5GbG93VGFibGUgPSByZXF1aXJlKFwiLi9mbG93dGFibGUuanNcIik7XG52YXIgZmxvd2RldGFpbCA9IHJlcXVpcmUoXCIuL2Zsb3dkZXRhaWwuanNcIik7XG5cblxudmFyIE1haW5WaWV3ID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIk1haW5WaWV3XCIsXG4gICAgbWl4aW5zOiBbdXRpbHMuTmF2aWdhdGlvbiwgdXRpbHMuU3RhdGVdLFxuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLm9uUXVlcnlDaGFuZ2UoUXVlcnkuRklMVEVSLCBmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICB0aGlzLnN0YXRlLnZpZXcucmVjYWxjdWxhdGUodGhpcy5nZXRWaWV3RmlsdCgpLCB0aGlzLmdldFZpZXdTb3J0KCkpO1xuICAgICAgICB9LmJpbmQodGhpcykpO1xuICAgICAgICB0aGlzLm9uUXVlcnlDaGFuZ2UoUXVlcnkuSElHSExJR0hULCBmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICB0aGlzLnN0YXRlLnZpZXcucmVjYWxjdWxhdGUodGhpcy5nZXRWaWV3RmlsdCgpLCB0aGlzLmdldFZpZXdTb3J0KCkpO1xuICAgICAgICB9LmJpbmQodGhpcykpO1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgZmxvd3M6IFtdXG4gICAgICAgIH07XG4gICAgfSxcbiAgICBnZXRWaWV3RmlsdDogZnVuY3Rpb24gKCkge1xuICAgICAgICB0cnkge1xuICAgICAgICAgICAgdmFyIGZpbHQgPSBGaWx0LnBhcnNlKHRoaXMuZ2V0UXVlcnkoKVtRdWVyeS5GSUxURVJdIHx8IFwiXCIpO1xuICAgICAgICAgICAgdmFyIGhpZ2hsaWdodFN0ciA9IHRoaXMuZ2V0UXVlcnkoKVtRdWVyeS5ISUdITElHSFRdO1xuICAgICAgICAgICAgdmFyIGhpZ2hsaWdodCA9IGhpZ2hsaWdodFN0ciA/IEZpbHQucGFyc2UoaGlnaGxpZ2h0U3RyKSA6IGZhbHNlO1xuICAgICAgICB9IGNhdGNoIChlKSB7XG4gICAgICAgICAgICBjb25zb2xlLmVycm9yKFwiRXJyb3Igd2hlbiBwcm9jZXNzaW5nIGZpbHRlcjogXCIgKyBlKTtcbiAgICAgICAgfVxuXG4gICAgICAgIHJldHVybiBmdW5jdGlvbiBmaWx0ZXJfYW5kX2hpZ2hsaWdodChmbG93KSB7XG4gICAgICAgICAgICBpZiAoIXRoaXMuX2hpZ2hsaWdodCkge1xuICAgICAgICAgICAgICAgIHRoaXMuX2hpZ2hsaWdodCA9IHt9O1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgdGhpcy5faGlnaGxpZ2h0W2Zsb3cuaWRdID0gaGlnaGxpZ2h0ICYmIGhpZ2hsaWdodChmbG93KTtcbiAgICAgICAgICAgIHJldHVybiBmaWx0KGZsb3cpO1xuICAgICAgICB9O1xuICAgIH0sXG4gICAgZ2V0Vmlld1NvcnQ6IGZ1bmN0aW9uICgpIHtcbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxSZWNlaXZlUHJvcHM6IGZ1bmN0aW9uIChuZXh0UHJvcHMpIHtcbiAgICAgICAgaWYgKG5leHRQcm9wcy5mbG93U3RvcmUgIT09IHRoaXMucHJvcHMuZmxvd1N0b3JlKSB7XG4gICAgICAgICAgICB0aGlzLmNsb3NlVmlldygpO1xuICAgICAgICAgICAgdGhpcy5vcGVuVmlldyhuZXh0UHJvcHMuZmxvd1N0b3JlKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgb3BlblZpZXc6IGZ1bmN0aW9uIChzdG9yZSkge1xuICAgICAgICB2YXIgdmlldyA9IG5ldyB2aWV3cy5TdG9yZVZpZXcoc3RvcmUsIHRoaXMuZ2V0Vmlld0ZpbHQoKSwgdGhpcy5nZXRWaWV3U29ydCgpKTtcbiAgICAgICAgdGhpcy5zZXRTdGF0ZSh7XG4gICAgICAgICAgICB2aWV3OiB2aWV3XG4gICAgICAgIH0pO1xuXG4gICAgICAgIHZpZXcuYWRkTGlzdGVuZXIoXCJyZWNhbGN1bGF0ZVwiLCB0aGlzLm9uUmVjYWxjdWxhdGUpO1xuICAgICAgICB2aWV3LmFkZExpc3RlbmVyKFwiYWRkIHVwZGF0ZSByZW1vdmVcIiwgdGhpcy5vblVwZGF0ZSk7XG4gICAgICAgIHZpZXcuYWRkTGlzdGVuZXIoXCJyZW1vdmVcIiwgdGhpcy5vblJlbW92ZSk7XG4gICAgfSxcbiAgICBvblJlY2FsY3VsYXRlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuZm9yY2VVcGRhdGUoKTtcbiAgICAgICAgdmFyIHNlbGVjdGVkID0gdGhpcy5nZXRTZWxlY3RlZCgpO1xuICAgICAgICBpZiAoc2VsZWN0ZWQpIHtcbiAgICAgICAgICAgIHRoaXMucmVmcy5mbG93VGFibGUuc2Nyb2xsSW50b1ZpZXcoc2VsZWN0ZWQpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBvblVwZGF0ZTogZnVuY3Rpb24gKGZsb3cpIHtcbiAgICAgICAgaWYgKGZsb3cuaWQgPT09IHRoaXMuZ2V0UGFyYW1zKCkuZmxvd0lkKSB7XG4gICAgICAgICAgICB0aGlzLmZvcmNlVXBkYXRlKCk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIG9uUmVtb3ZlOiBmdW5jdGlvbiAoZmxvd19pZCwgaW5kZXgpIHtcbiAgICAgICAgaWYgKGZsb3dfaWQgPT09IHRoaXMuZ2V0UGFyYW1zKCkuZmxvd0lkKSB7XG4gICAgICAgICAgICB2YXIgZmxvd190b19zZWxlY3QgPSB0aGlzLnN0YXRlLnZpZXcubGlzdFtNYXRoLm1pbihpbmRleCwgdGhpcy5zdGF0ZS52aWV3Lmxpc3QubGVuZ3RoIC0xKV07XG4gICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3coZmxvd190b19zZWxlY3QpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBjbG9zZVZpZXc6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5zdGF0ZS52aWV3LmNsb3NlKCk7XG4gICAgfSxcbiAgICBjb21wb25lbnRXaWxsTW91bnQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5vcGVuVmlldyh0aGlzLnByb3BzLmZsb3dTdG9yZSk7XG4gICAgfSxcbiAgICBjb21wb25lbnRXaWxsVW5tb3VudDogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLmNsb3NlVmlldygpO1xuICAgIH0sXG4gICAgc2VsZWN0RmxvdzogZnVuY3Rpb24gKGZsb3cpIHtcbiAgICAgICAgaWYgKGZsb3cpIHtcbiAgICAgICAgICAgIHRoaXMucmVwbGFjZVdpdGgoXG4gICAgICAgICAgICAgICAgXCJmbG93XCIsXG4gICAgICAgICAgICAgICAge1xuICAgICAgICAgICAgICAgICAgICBmbG93SWQ6IGZsb3cuaWQsXG4gICAgICAgICAgICAgICAgICAgIGRldGFpbFRhYjogdGhpcy5nZXRQYXJhbXMoKS5kZXRhaWxUYWIgfHwgXCJyZXF1ZXN0XCJcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICApO1xuICAgICAgICAgICAgdGhpcy5yZWZzLmZsb3dUYWJsZS5zY3JvbGxJbnRvVmlldyhmbG93KTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHRoaXMucmVwbGFjZVdpdGgoXCJmbG93c1wiLCB7fSk7XG4gICAgICAgIH1cbiAgICB9LFxuICAgIHNlbGVjdEZsb3dSZWxhdGl2ZTogZnVuY3Rpb24gKHNoaWZ0KSB7XG4gICAgICAgIHZhciBmbG93cyA9IHRoaXMuc3RhdGUudmlldy5saXN0O1xuICAgICAgICB2YXIgaW5kZXg7XG4gICAgICAgIGlmICghdGhpcy5nZXRQYXJhbXMoKS5mbG93SWQpIHtcbiAgICAgICAgICAgIGlmIChzaGlmdCA+IDApIHtcbiAgICAgICAgICAgICAgICBpbmRleCA9IGZsb3dzLmxlbmd0aCAtIDE7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIGluZGV4ID0gMDtcbiAgICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHZhciBjdXJyRmxvd0lkID0gdGhpcy5nZXRQYXJhbXMoKS5mbG93SWQ7XG4gICAgICAgICAgICB2YXIgaSA9IGZsb3dzLmxlbmd0aDtcbiAgICAgICAgICAgIHdoaWxlIChpLS0pIHtcbiAgICAgICAgICAgICAgICBpZiAoZmxvd3NbaV0uaWQgPT09IGN1cnJGbG93SWQpIHtcbiAgICAgICAgICAgICAgICAgICAgaW5kZXggPSBpO1xuICAgICAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBpbmRleCA9IE1hdGgubWluKFxuICAgICAgICAgICAgICAgIE1hdGgubWF4KDAsIGluZGV4ICsgc2hpZnQpLFxuICAgICAgICAgICAgICAgIGZsb3dzLmxlbmd0aCAtIDEpO1xuICAgICAgICB9XG4gICAgICAgIHRoaXMuc2VsZWN0RmxvdyhmbG93c1tpbmRleF0pO1xuICAgIH0sXG4gICAgb25LZXlEb3duOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICB2YXIgZmxvdyA9IHRoaXMuZ2V0U2VsZWN0ZWQoKTtcbiAgICAgICAgaWYgKGUuY3RybEtleSkge1xuICAgICAgICAgICAgcmV0dXJuO1xuICAgICAgICB9XG4gICAgICAgIHN3aXRjaCAoZS5rZXlDb2RlKSB7XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5LOlxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuVVA6XG4gICAgICAgICAgICAgICAgdGhpcy5zZWxlY3RGbG93UmVsYXRpdmUoLTEpO1xuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuSjpcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LkRPV046XG4gICAgICAgICAgICAgICAgdGhpcy5zZWxlY3RGbG93UmVsYXRpdmUoKzEpO1xuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuU1BBQ0U6XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5QQUdFX0RPV046XG4gICAgICAgICAgICAgICAgdGhpcy5zZWxlY3RGbG93UmVsYXRpdmUoKzEwKTtcbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LlBBR0VfVVA6XG4gICAgICAgICAgICAgICAgdGhpcy5zZWxlY3RGbG93UmVsYXRpdmUoLTEwKTtcbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LkVORDpcbiAgICAgICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3dSZWxhdGl2ZSgrMWUxMCk7XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5IT01FOlxuICAgICAgICAgICAgICAgIHRoaXMuc2VsZWN0Rmxvd1JlbGF0aXZlKC0xZTEwKTtcbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LkVTQzpcbiAgICAgICAgICAgICAgICB0aGlzLnNlbGVjdEZsb3cobnVsbCk7XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5IOlxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuTEVGVDpcbiAgICAgICAgICAgICAgICBpZiAodGhpcy5yZWZzLmZsb3dEZXRhaWxzKSB7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMucmVmcy5mbG93RGV0YWlscy5uZXh0VGFiKC0xKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5MOlxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuVEFCOlxuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuUklHSFQ6XG4gICAgICAgICAgICAgICAgaWYgKHRoaXMucmVmcy5mbG93RGV0YWlscykge1xuICAgICAgICAgICAgICAgICAgICB0aGlzLnJlZnMuZmxvd0RldGFpbHMubmV4dFRhYigrMSk7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgY2FzZSB0b3B1dGlscy5LZXkuQzpcbiAgICAgICAgICAgICAgICBpZiAoZS5zaGlmdEtleSkge1xuICAgICAgICAgICAgICAgICAgICBGbG93QWN0aW9ucy5jbGVhcigpO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LkQ6XG4gICAgICAgICAgICAgICAgaWYgKGZsb3cpIHtcbiAgICAgICAgICAgICAgICAgICAgaWYgKGUuc2hpZnRLZXkpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIEZsb3dBY3Rpb25zLmR1cGxpY2F0ZShmbG93KTtcbiAgICAgICAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIEZsb3dBY3Rpb25zLmRlbGV0ZShmbG93KTtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBicmVhaztcbiAgICAgICAgICAgIGNhc2UgdG9wdXRpbHMuS2V5LkE6XG4gICAgICAgICAgICAgICAgaWYgKGUuc2hpZnRLZXkpIHtcbiAgICAgICAgICAgICAgICAgICAgRmxvd0FjdGlvbnMuYWNjZXB0X2FsbCgpO1xuICAgICAgICAgICAgICAgIH0gZWxzZSBpZiAoZmxvdyAmJiBmbG93LmludGVyY2VwdGVkKSB7XG4gICAgICAgICAgICAgICAgICAgIEZsb3dBY3Rpb25zLmFjY2VwdChmbG93KTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5SOlxuICAgICAgICAgICAgICAgIGlmICghZS5zaGlmdEtleSAmJiBmbG93KSB7XG4gICAgICAgICAgICAgICAgICAgIEZsb3dBY3Rpb25zLnJlcGxheShmbG93KTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBjYXNlIHRvcHV0aWxzLktleS5WOlxuICAgICAgICAgICAgICAgIGlmKGUuc2hpZnRLZXkgJiYgZmxvdyAmJiBmbG93Lm1vZGlmaWVkKSB7XG4gICAgICAgICAgICAgICAgICAgIEZsb3dBY3Rpb25zLnJldmVydChmbG93KTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICBkZWZhdWx0OlxuICAgICAgICAgICAgICAgIGNvbnNvbGUuZGVidWcoXCJrZXlkb3duXCIsIGUua2V5Q29kZSk7XG4gICAgICAgICAgICAgICAgcmV0dXJuO1xuICAgICAgICB9XG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcbiAgICB9LFxuICAgIGdldFNlbGVjdGVkOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHJldHVybiB0aGlzLnByb3BzLmZsb3dTdG9yZS5nZXQodGhpcy5nZXRQYXJhbXMoKS5mbG93SWQpO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBzZWxlY3RlZCA9IHRoaXMuZ2V0U2VsZWN0ZWQoKTtcblxuICAgICAgICB2YXIgZGV0YWlscztcbiAgICAgICAgaWYgKHNlbGVjdGVkKSB7XG4gICAgICAgICAgICBkZXRhaWxzID0gW1xuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQodXRpbHMuU3BsaXR0ZXIsIHtrZXk6IFwic3BsaXR0ZXJcIn0pLFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoZmxvd2RldGFpbC5GbG93RGV0YWlsLCB7a2V5OiBcImZsb3dEZXRhaWxzXCIsIHJlZjogXCJmbG93RGV0YWlsc1wiLCBmbG93OiBzZWxlY3RlZH0pXG4gICAgICAgICAgICBdO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgZGV0YWlscyA9IG51bGw7XG4gICAgICAgIH1cblxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCB7Y2xhc3NOYW1lOiBcIm1haW4tdmlld1wiLCBvbktleURvd246IHRoaXMub25LZXlEb3duLCB0YWJJbmRleDogXCIwXCJ9LCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KEZsb3dUYWJsZSwge3JlZjogXCJmbG93VGFibGVcIiwgXG4gICAgICAgICAgICAgICAgICAgIHZpZXc6IHRoaXMuc3RhdGUudmlldywgXG4gICAgICAgICAgICAgICAgICAgIHNlbGVjdEZsb3c6IHRoaXMuc2VsZWN0RmxvdywgXG4gICAgICAgICAgICAgICAgICAgIHNlbGVjdGVkOiBzZWxlY3RlZH0pLCBcbiAgICAgICAgICAgICAgICBkZXRhaWxzXG4gICAgICAgICAgICApXG4gICAgICAgICk7XG4gICAgfVxufSk7XG5cbm1vZHVsZS5leHBvcnRzID0gTWFpblZpZXc7XG4iLCJ2YXIgUmVhY3QgPSByZXF1aXJlKFwicmVhY3RcIik7XG52YXIgUmVhY3RSb3V0ZXIgPSByZXF1aXJlKFwicmVhY3Qtcm91dGVyXCIpO1xudmFyIF8gPSByZXF1aXJlKFwibG9kYXNoXCIpO1xuXG52YXIgdXRpbHMgPSByZXF1aXJlKFwiLi91dGlscy5qc1wiKTtcbnZhciBNYWluVmlldyA9IHJlcXVpcmUoXCIuL21haW52aWV3LmpzXCIpO1xudmFyIEZvb3RlciA9IHJlcXVpcmUoXCIuL2Zvb3Rlci5qc1wiKTtcbnZhciBoZWFkZXIgPSByZXF1aXJlKFwiLi9oZWFkZXIuanNcIik7XG52YXIgRXZlbnRMb2cgPSByZXF1aXJlKFwiLi9ldmVudGxvZy5qc1wiKTtcbnZhciBzdG9yZSA9IHJlcXVpcmUoXCIuLi9zdG9yZS9zdG9yZS5qc1wiKTtcblxuXG4vL1RPRE86IE1vdmUgb3V0IG9mIGhlcmUsIGp1c3QgYSBzdHViLlxudmFyIFJlcG9ydHMgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiUmVwb3J0c1wiLFxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4gUmVhY3QuY3JlYXRlRWxlbWVudChcImRpdlwiLCBudWxsLCBcIlJlcG9ydEVkaXRvclwiKTtcbiAgICB9XG59KTtcblxuXG52YXIgUHJveHlBcHBNYWluID0gUmVhY3QuY3JlYXRlQ2xhc3Moe2Rpc3BsYXlOYW1lOiBcIlByb3h5QXBwTWFpblwiLFxuICAgIG1peGluczogW3V0aWxzLlN0YXRlXSxcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGV2ZW50U3RvcmUgPSBuZXcgc3RvcmUuRXZlbnRMb2dTdG9yZSgpO1xuICAgICAgICB2YXIgZmxvd1N0b3JlID0gbmV3IHN0b3JlLkZsb3dTdG9yZSgpO1xuICAgICAgICB2YXIgc2V0dGluZ3MgPSBuZXcgc3RvcmUuU2V0dGluZ3NTdG9yZSgpO1xuXG4gICAgICAgIC8vIERlZmF1bHQgU2V0dGluZ3MgYmVmb3JlIGZldGNoXG4gICAgICAgIF8uZXh0ZW5kKHNldHRpbmdzLmRpY3Qse1xuICAgICAgICB9KTtcbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgIHNldHRpbmdzOiBzZXR0aW5ncyxcbiAgICAgICAgICAgIGZsb3dTdG9yZTogZmxvd1N0b3JlLFxuICAgICAgICAgICAgZXZlbnRTdG9yZTogZXZlbnRTdG9yZVxuICAgICAgICB9O1xuICAgIH0sXG4gICAgY29tcG9uZW50RGlkTW91bnQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5zdGF0ZS5zZXR0aW5ncy5hZGRMaXN0ZW5lcihcInJlY2FsY3VsYXRlXCIsIHRoaXMub25TZXR0aW5nc0NoYW5nZSk7XG4gICAgICAgIHdpbmRvdy5hcHAgPSB0aGlzO1xuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbFVubW91bnQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5zdGF0ZS5zZXR0aW5ncy5yZW1vdmVMaXN0ZW5lcihcInJlY2FsY3VsYXRlXCIsIHRoaXMub25TZXR0aW5nc0NoYW5nZSk7XG4gICAgfSxcbiAgICBvblNldHRpbmdzQ2hhbmdlOiBmdW5jdGlvbigpe1xuICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgIHNldHRpbmdzOiB0aGlzLnN0YXRlLnNldHRpbmdzXG4gICAgICAgIH0pO1xuICAgIH0sXG4gICAgcmVuZGVyOiBmdW5jdGlvbiAoKSB7XG5cbiAgICAgICAgdmFyIGV2ZW50bG9nO1xuICAgICAgICBpZiAodGhpcy5nZXRRdWVyeSgpW1F1ZXJ5LlNIT1dfRVZFTlRMT0ddKSB7XG4gICAgICAgICAgICBldmVudGxvZyA9IFtcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KHV0aWxzLlNwbGl0dGVyLCB7a2V5OiBcInNwbGl0dGVyXCIsIGF4aXM6IFwieVwifSksXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChFdmVudExvZywge2tleTogXCJldmVudGxvZ1wiLCBldmVudFN0b3JlOiB0aGlzLnN0YXRlLmV2ZW50U3RvcmV9KVxuICAgICAgICAgICAgXTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGV2ZW50bG9nID0gbnVsbDtcbiAgICAgICAgfVxuXG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtpZDogXCJjb250YWluZXJcIn0sIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoaGVhZGVyLkhlYWRlciwge3NldHRpbmdzOiB0aGlzLnN0YXRlLnNldHRpbmdzLmRpY3R9KSwgXG4gICAgICAgICAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChSb3V0ZUhhbmRsZXIsIHtzZXR0aW5nczogdGhpcy5zdGF0ZS5zZXR0aW5ncy5kaWN0LCBmbG93U3RvcmU6IHRoaXMuc3RhdGUuZmxvd1N0b3JlfSksIFxuICAgICAgICAgICAgICAgIGV2ZW50bG9nLCBcbiAgICAgICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KEZvb3Rlciwge3NldHRpbmdzOiB0aGlzLnN0YXRlLnNldHRpbmdzLmRpY3R9KVxuICAgICAgICAgICAgKVxuICAgICAgICApO1xuICAgIH1cbn0pO1xuXG5cbnZhciBSb3V0ZSA9IFJlYWN0Um91dGVyLlJvdXRlO1xudmFyIFJvdXRlSGFuZGxlciA9IFJlYWN0Um91dGVyLlJvdXRlSGFuZGxlcjtcbnZhciBSZWRpcmVjdCA9IFJlYWN0Um91dGVyLlJlZGlyZWN0O1xudmFyIERlZmF1bHRSb3V0ZSA9IFJlYWN0Um91dGVyLkRlZmF1bHRSb3V0ZTtcbnZhciBOb3RGb3VuZFJvdXRlID0gUmVhY3RSb3V0ZXIuTm90Rm91bmRSb3V0ZTtcblxuXG52YXIgcm91dGVzID0gKFxuICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoUm91dGUsIHtwYXRoOiBcIi9cIiwgaGFuZGxlcjogUHJveHlBcHBNYWlufSwgXG4gICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoUm91dGUsIHtuYW1lOiBcImZsb3dzXCIsIHBhdGg6IFwiZmxvd3NcIiwgaGFuZGxlcjogTWFpblZpZXd9KSwgXG4gICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoUm91dGUsIHtuYW1lOiBcImZsb3dcIiwgcGF0aDogXCJmbG93cy86Zmxvd0lkLzpkZXRhaWxUYWJcIiwgaGFuZGxlcjogTWFpblZpZXd9KSwgXG4gICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoUm91dGUsIHtuYW1lOiBcInJlcG9ydHNcIiwgaGFuZGxlcjogUmVwb3J0c30pLCBcbiAgICAgICAgUmVhY3QuY3JlYXRlRWxlbWVudChSZWRpcmVjdCwge3BhdGg6IFwiL1wiLCB0bzogXCJmbG93c1wifSlcbiAgICApXG4pO1xuXG5tb2R1bGUuZXhwb3J0cyA9IHtcbiAgICByb3V0ZXM6IHJvdXRlc1xufTtcblxuIiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xudmFyIFJlYWN0Um91dGVyID0gcmVxdWlyZShcInJlYWN0LXJvdXRlclwiKTtcbnZhciBfID0gcmVxdWlyZShcImxvZGFzaFwiKTtcblxuLy9SZWFjdCB1dGlscy4gRm9yIG90aGVyIHV0aWxpdGllcywgc2VlIC4uL3V0aWxzLmpzXG5cbi8vIGh0dHA6Ly9ibG9nLnZqZXV4LmNvbS8yMDEzL2phdmFzY3JpcHQvc2Nyb2xsLXBvc2l0aW9uLXdpdGgtcmVhY3QuaHRtbCAoYWxzbyBjb250YWlucyBpbnZlcnNlIGV4YW1wbGUpXG52YXIgQXV0b1Njcm9sbE1peGluID0ge1xuICAgIGNvbXBvbmVudFdpbGxVcGRhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIG5vZGUgPSB0aGlzLmdldERPTU5vZGUoKTtcbiAgICAgICAgdGhpcy5fc2hvdWxkU2Nyb2xsQm90dG9tID0gKFxuICAgICAgICAgICAgbm9kZS5zY3JvbGxUb3AgIT09IDAgJiZcbiAgICAgICAgICAgIG5vZGUuc2Nyb2xsVG9wICsgbm9kZS5jbGllbnRIZWlnaHQgPT09IG5vZGUuc2Nyb2xsSGVpZ2h0XG4gICAgICAgICk7XG4gICAgfSxcbiAgICBjb21wb25lbnREaWRVcGRhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgaWYgKHRoaXMuX3Nob3VsZFNjcm9sbEJvdHRvbSkge1xuICAgICAgICAgICAgdmFyIG5vZGUgPSB0aGlzLmdldERPTU5vZGUoKTtcbiAgICAgICAgICAgIG5vZGUuc2Nyb2xsVG9wID0gbm9kZS5zY3JvbGxIZWlnaHQ7XG4gICAgICAgIH1cbiAgICB9LFxufTtcblxuXG52YXIgU3RpY2t5SGVhZE1peGluID0ge1xuICAgIGFkanVzdEhlYWQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgLy8gQWJ1c2luZyBDU1MgdHJhbnNmb3JtcyB0byBzZXQgdGhlIGVsZW1lbnRcbiAgICAgICAgLy8gcmVmZXJlbmNlZCBhcyBoZWFkIGludG8gc29tZSBraW5kIG9mIHBvc2l0aW9uOnN0aWNreS5cbiAgICAgICAgdmFyIGhlYWQgPSB0aGlzLnJlZnMuaGVhZC5nZXRET01Ob2RlKCk7XG4gICAgICAgIGhlYWQuc3R5bGUudHJhbnNmb3JtID0gXCJ0cmFuc2xhdGUoMCxcIiArIHRoaXMuZ2V0RE9NTm9kZSgpLnNjcm9sbFRvcCArIFwicHgpXCI7XG4gICAgfVxufTtcblxuXG52YXIgTmF2aWdhdGlvbiA9IF8uZXh0ZW5kKHt9LCBSZWFjdFJvdXRlci5OYXZpZ2F0aW9uLCB7XG4gICAgc2V0UXVlcnk6IGZ1bmN0aW9uIChkaWN0KSB7XG4gICAgICAgIHZhciBxID0gdGhpcy5jb250ZXh0LmdldEN1cnJlbnRRdWVyeSgpO1xuICAgICAgICBmb3IodmFyIGkgaW4gZGljdCl7XG4gICAgICAgICAgICBpZihkaWN0Lmhhc093blByb3BlcnR5KGkpKXtcbiAgICAgICAgICAgICAgICBxW2ldID0gZGljdFtpXSB8fCB1bmRlZmluZWQ7IC8vZmFsc2V5IHZhbHVlcyBzaGFsbCBiZSByZW1vdmVkLlxuICAgICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICAgIHEuXyA9IFwiX1wiOyAvLyB3b3JrYXJvdW5kIGZvciBodHRwczovL2dpdGh1Yi5jb20vcmFja3QvcmVhY3Qtcm91dGVyL3B1bGwvNTk5XG4gICAgICAgIHRoaXMucmVwbGFjZVdpdGgodGhpcy5jb250ZXh0LmdldEN1cnJlbnRQYXRoKCksIHRoaXMuY29udGV4dC5nZXRDdXJyZW50UGFyYW1zKCksIHEpO1xuICAgIH0sXG4gICAgcmVwbGFjZVdpdGg6IGZ1bmN0aW9uKHJvdXRlTmFtZU9yUGF0aCwgcGFyYW1zLCBxdWVyeSkge1xuICAgICAgICBpZihyb3V0ZU5hbWVPclBhdGggPT09IHVuZGVmaW5lZCl7XG4gICAgICAgICAgICByb3V0ZU5hbWVPclBhdGggPSB0aGlzLmNvbnRleHQuZ2V0Q3VycmVudFBhdGgoKTtcbiAgICAgICAgfVxuICAgICAgICBpZihwYXJhbXMgPT09IHVuZGVmaW5lZCl7XG4gICAgICAgICAgICBwYXJhbXMgPSB0aGlzLmNvbnRleHQuZ2V0Q3VycmVudFBhcmFtcygpO1xuICAgICAgICB9XG4gICAgICAgIGlmKHF1ZXJ5ID09PSB1bmRlZmluZWQpe1xuICAgICAgICAgICAgcXVlcnkgPSB0aGlzLmNvbnRleHQuZ2V0Q3VycmVudFF1ZXJ5KCk7XG4gICAgICAgIH1cbiAgICAgICAgUmVhY3RSb3V0ZXIuTmF2aWdhdGlvbi5yZXBsYWNlV2l0aC5jYWxsKHRoaXMsIHJvdXRlTmFtZU9yUGF0aCwgcGFyYW1zLCBxdWVyeSk7XG4gICAgfVxufSk7XG5fLmV4dGVuZChOYXZpZ2F0aW9uLmNvbnRleHRUeXBlcywgUmVhY3RSb3V0ZXIuU3RhdGUuY29udGV4dFR5cGVzKTtcblxudmFyIFN0YXRlID0gXy5leHRlbmQoe30sIFJlYWN0Um91dGVyLlN0YXRlLCB7XG4gICAgZ2V0SW5pdGlhbFN0YXRlOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuX3F1ZXJ5ID0gdGhpcy5jb250ZXh0LmdldEN1cnJlbnRRdWVyeSgpO1xuICAgICAgICB0aGlzLl9xdWVyeVdhdGNoZXMgPSBbXTtcbiAgICAgICAgcmV0dXJuIG51bGw7XG4gICAgfSxcbiAgICBvblF1ZXJ5Q2hhbmdlOiBmdW5jdGlvbiAoa2V5LCBjYWxsYmFjaykge1xuICAgICAgICB0aGlzLl9xdWVyeVdhdGNoZXMucHVzaCh7XG4gICAgICAgICAgICBrZXk6IGtleSxcbiAgICAgICAgICAgIGNhbGxiYWNrOiBjYWxsYmFja1xuICAgICAgICB9KTtcbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxSZWNlaXZlUHJvcHM6IGZ1bmN0aW9uIChuZXh0UHJvcHMsIG5leHRTdGF0ZSkge1xuICAgICAgICB2YXIgcSA9IHRoaXMuY29udGV4dC5nZXRDdXJyZW50UXVlcnkoKTtcbiAgICAgICAgZm9yICh2YXIgaSA9IDA7IGkgPCB0aGlzLl9xdWVyeVdhdGNoZXMubGVuZ3RoOyBpKyspIHtcbiAgICAgICAgICAgIHZhciB3YXRjaCA9IHRoaXMuX3F1ZXJ5V2F0Y2hlc1tpXTtcbiAgICAgICAgICAgIGlmICh0aGlzLl9xdWVyeVt3YXRjaC5rZXldICE9PSBxW3dhdGNoLmtleV0pIHtcbiAgICAgICAgICAgICAgICB3YXRjaC5jYWxsYmFjayh0aGlzLl9xdWVyeVt3YXRjaC5rZXldLCBxW3dhdGNoLmtleV0sIHdhdGNoLmtleSk7XG4gICAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgICAgdGhpcy5fcXVlcnkgPSBxO1xuICAgIH1cbn0pO1xuXG52YXIgU3BsaXR0ZXIgPSBSZWFjdC5jcmVhdGVDbGFzcyh7ZGlzcGxheU5hbWU6IFwiU3BsaXR0ZXJcIixcbiAgICBnZXREZWZhdWx0UHJvcHM6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgIGF4aXM6IFwieFwiXG4gICAgICAgIH07XG4gICAgfSxcbiAgICBnZXRJbml0aWFsU3RhdGU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgIGFwcGxpZWQ6IGZhbHNlLFxuICAgICAgICAgICAgc3RhcnRYOiBmYWxzZSxcbiAgICAgICAgICAgIHN0YXJ0WTogZmFsc2VcbiAgICAgICAgfTtcbiAgICB9LFxuICAgIG9uTW91c2VEb3duOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgIHN0YXJ0WDogZS5wYWdlWCxcbiAgICAgICAgICAgIHN0YXJ0WTogZS5wYWdlWVxuICAgICAgICB9KTtcbiAgICAgICAgd2luZG93LmFkZEV2ZW50TGlzdGVuZXIoXCJtb3VzZW1vdmVcIiwgdGhpcy5vbk1vdXNlTW92ZSk7XG4gICAgICAgIHdpbmRvdy5hZGRFdmVudExpc3RlbmVyKFwibW91c2V1cFwiLCB0aGlzLm9uTW91c2VVcCk7XG4gICAgICAgIC8vIE9jY2FzaW9uYWxseSwgb25seSBhIGRyYWdFbmQgZXZlbnQgaXMgdHJpZ2dlcmVkLCBidXQgbm8gbW91c2VVcC5cbiAgICAgICAgd2luZG93LmFkZEV2ZW50TGlzdGVuZXIoXCJkcmFnZW5kXCIsIHRoaXMub25EcmFnRW5kKTtcbiAgICB9LFxuICAgIG9uRHJhZ0VuZDogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLmdldERPTU5vZGUoKS5zdHlsZS50cmFuc2Zvcm0gPSBcIlwiO1xuICAgICAgICB3aW5kb3cucmVtb3ZlRXZlbnRMaXN0ZW5lcihcImRyYWdlbmRcIiwgdGhpcy5vbkRyYWdFbmQpO1xuICAgICAgICB3aW5kb3cucmVtb3ZlRXZlbnRMaXN0ZW5lcihcIm1vdXNldXBcIiwgdGhpcy5vbk1vdXNlVXApO1xuICAgICAgICB3aW5kb3cucmVtb3ZlRXZlbnRMaXN0ZW5lcihcIm1vdXNlbW92ZVwiLCB0aGlzLm9uTW91c2VNb3ZlKTtcbiAgICB9LFxuICAgIG9uTW91c2VVcDogZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgdGhpcy5vbkRyYWdFbmQoKTtcblxuICAgICAgICB2YXIgbm9kZSA9IHRoaXMuZ2V0RE9NTm9kZSgpO1xuICAgICAgICB2YXIgcHJldiA9IG5vZGUucHJldmlvdXNFbGVtZW50U2libGluZztcbiAgICAgICAgdmFyIG5leHQgPSBub2RlLm5leHRFbGVtZW50U2libGluZztcblxuICAgICAgICB2YXIgZFggPSBlLnBhZ2VYIC0gdGhpcy5zdGF0ZS5zdGFydFg7XG4gICAgICAgIHZhciBkWSA9IGUucGFnZVkgLSB0aGlzLnN0YXRlLnN0YXJ0WTtcbiAgICAgICAgdmFyIGZsZXhCYXNpcztcbiAgICAgICAgaWYgKHRoaXMucHJvcHMuYXhpcyA9PT0gXCJ4XCIpIHtcbiAgICAgICAgICAgIGZsZXhCYXNpcyA9IHByZXYub2Zmc2V0V2lkdGggKyBkWDtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGZsZXhCYXNpcyA9IHByZXYub2Zmc2V0SGVpZ2h0ICsgZFk7XG4gICAgICAgIH1cblxuICAgICAgICBwcmV2LnN0eWxlLmZsZXggPSBcIjAgMCBcIiArIE1hdGgubWF4KDAsIGZsZXhCYXNpcykgKyBcInB4XCI7XG4gICAgICAgIG5leHQuc3R5bGUuZmxleCA9IFwiMSAxIGF1dG9cIjtcblxuICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgIGFwcGxpZWQ6IHRydWVcbiAgICAgICAgfSk7XG4gICAgICAgIHRoaXMub25SZXNpemUoKTtcbiAgICB9LFxuICAgIG9uTW91c2VNb3ZlOiBmdW5jdGlvbiAoZSkge1xuICAgICAgICB2YXIgZFggPSAwLCBkWSA9IDA7XG4gICAgICAgIGlmICh0aGlzLnByb3BzLmF4aXMgPT09IFwieFwiKSB7XG4gICAgICAgICAgICBkWCA9IGUucGFnZVggLSB0aGlzLnN0YXRlLnN0YXJ0WDtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIGRZID0gZS5wYWdlWSAtIHRoaXMuc3RhdGUuc3RhcnRZO1xuICAgICAgICB9XG4gICAgICAgIHRoaXMuZ2V0RE9NTm9kZSgpLnN0eWxlLnRyYW5zZm9ybSA9IFwidHJhbnNsYXRlKFwiICsgZFggKyBcInB4LFwiICsgZFkgKyBcInB4KVwiO1xuICAgIH0sXG4gICAgb25SZXNpemU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgLy8gVHJpZ2dlciBhIGdsb2JhbCByZXNpemUgZXZlbnQuIFRoaXMgbm90aWZpZXMgY29tcG9uZW50cyB0aGF0IGVtcGxveSB2aXJ0dWFsIHNjcm9sbGluZ1xuICAgICAgICAvLyB0aGF0IHRoZWlyIHZpZXdwb3J0IG1heSBoYXZlIGNoYW5nZWQuXG4gICAgICAgIHdpbmRvdy5zZXRUaW1lb3V0KGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHdpbmRvdy5kaXNwYXRjaEV2ZW50KG5ldyBDdXN0b21FdmVudChcInJlc2l6ZVwiKSk7XG4gICAgICAgIH0sIDEpO1xuICAgIH0sXG4gICAgcmVzZXQ6IGZ1bmN0aW9uICh3aWxsVW5tb3VudCkge1xuICAgICAgICBpZiAoIXRoaXMuc3RhdGUuYXBwbGllZCkge1xuICAgICAgICAgICAgcmV0dXJuO1xuICAgICAgICB9XG4gICAgICAgIHZhciBub2RlID0gdGhpcy5nZXRET01Ob2RlKCk7XG4gICAgICAgIHZhciBwcmV2ID0gbm9kZS5wcmV2aW91c0VsZW1lbnRTaWJsaW5nO1xuICAgICAgICB2YXIgbmV4dCA9IG5vZGUubmV4dEVsZW1lbnRTaWJsaW5nO1xuXG4gICAgICAgIHByZXYuc3R5bGUuZmxleCA9IFwiXCI7XG4gICAgICAgIG5leHQuc3R5bGUuZmxleCA9IFwiXCI7XG5cbiAgICAgICAgaWYgKCF3aWxsVW5tb3VudCkge1xuICAgICAgICAgICAgdGhpcy5zZXRTdGF0ZSh7XG4gICAgICAgICAgICAgICAgYXBwbGllZDogZmFsc2VcbiAgICAgICAgICAgIH0pO1xuICAgICAgICB9XG4gICAgICAgIHRoaXMub25SZXNpemUoKTtcbiAgICB9LFxuICAgIGNvbXBvbmVudFdpbGxVbm1vdW50OiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMucmVzZXQodHJ1ZSk7XG4gICAgfSxcbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGNsYXNzTmFtZSA9IFwic3BsaXR0ZXJcIjtcbiAgICAgICAgaWYgKHRoaXMucHJvcHMuYXhpcyA9PT0gXCJ4XCIpIHtcbiAgICAgICAgICAgIGNsYXNzTmFtZSArPSBcIiBzcGxpdHRlci14XCI7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBjbGFzc05hbWUgKz0gXCIgc3BsaXR0ZXIteVwiO1xuICAgICAgICB9XG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgICBSZWFjdC5jcmVhdGVFbGVtZW50KFwiZGl2XCIsIHtjbGFzc05hbWU6IGNsYXNzTmFtZX0sIFxuICAgICAgICAgICAgICAgIFJlYWN0LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIiwge29uTW91c2VEb3duOiB0aGlzLm9uTW91c2VEb3duLCBkcmFnZ2FibGU6IFwidHJ1ZVwifSlcbiAgICAgICAgICAgIClcbiAgICAgICAgKTtcbiAgICB9XG59KTtcblxubW9kdWxlLmV4cG9ydHMgPSB7XG4gICAgU3RhdGU6IFN0YXRlLFxuICAgIE5hdmlnYXRpb246IE5hdmlnYXRpb24sXG4gICAgU3RpY2t5SGVhZE1peGluOiBTdGlja3lIZWFkTWl4aW4sXG4gICAgQXV0b1Njcm9sbE1peGluOiBBdXRvU2Nyb2xsTWl4aW4sXG4gICAgU3BsaXR0ZXI6IFNwbGl0dGVyXG59IiwidmFyIFJlYWN0ID0gcmVxdWlyZShcInJlYWN0XCIpO1xuXG52YXIgVmlydHVhbFNjcm9sbE1peGluID0ge1xuICAgIGdldEluaXRpYWxTdGF0ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgc3RhcnQ6IDAsXG4gICAgICAgICAgICBzdG9wOiAwXG4gICAgICAgIH07XG4gICAgfSxcbiAgICBjb21wb25lbnRXaWxsTW91bnQ6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgaWYgKCF0aGlzLnByb3BzLnJvd0hlaWdodCkge1xuICAgICAgICAgICAgY29uc29sZS53YXJuKFwiVmlydHVhbFNjcm9sbE1peGluOiBObyByb3dIZWlnaHQgc3BlY2lmaWVkXCIsIHRoaXMpO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBnZXRQbGFjZWhvbGRlclRvcDogZnVuY3Rpb24gKHRvdGFsKSB7XG4gICAgICAgIHZhciBUYWcgPSB0aGlzLnByb3BzLnBsYWNlaG9sZGVyVGFnTmFtZSB8fCBcInRyXCI7XG4gICAgICAgIC8vIFdoZW4gYSBsYXJnZSB0cnVuayBvZiBlbGVtZW50cyBpcyByZW1vdmVkIGZyb20gdGhlIGJ1dHRvbiwgc3RhcnQgbWF5IGJlIGZhciBvZmYgdGhlIHZpZXdwb3J0LlxuICAgICAgICAvLyBUbyBtYWtlIHRoaXMgaXNzdWUgbGVzcyBzZXZlcmUsIGxpbWl0IHRoZSB0b3AgcGxhY2Vob2xkZXIgdG8gdGhlIHRvdGFsIG51bWJlciBvZiByb3dzLlxuICAgICAgICB2YXIgc3R5bGUgPSB7XG4gICAgICAgICAgICBoZWlnaHQ6IE1hdGgubWluKHRoaXMuc3RhdGUuc3RhcnQsIHRvdGFsKSAqIHRoaXMucHJvcHMucm93SGVpZ2h0XG4gICAgICAgIH07XG4gICAgICAgIHZhciBzcGFjZXIgPSBSZWFjdC5jcmVhdGVFbGVtZW50KFRhZywge2tleTogXCJwbGFjZWhvbGRlci10b3BcIiwgc3R5bGU6IHN0eWxlfSk7XG5cbiAgICAgICAgaWYgKHRoaXMuc3RhdGUuc3RhcnQgJSAyID09PSAxKSB7XG4gICAgICAgICAgICAvLyBmaXggZXZlbi9vZGQgcm93c1xuICAgICAgICAgICAgcmV0dXJuIFtzcGFjZXIsIFJlYWN0LmNyZWF0ZUVsZW1lbnQoVGFnLCB7a2V5OiBcInBsYWNlaG9sZGVyLXRvcC0yXCJ9KV07XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICByZXR1cm4gc3BhY2VyO1xuICAgICAgICB9XG4gICAgfSxcbiAgICBnZXRQbGFjZWhvbGRlckJvdHRvbTogZnVuY3Rpb24gKHRvdGFsKSB7XG4gICAgICAgIHZhciBUYWcgPSB0aGlzLnByb3BzLnBsYWNlaG9sZGVyVGFnTmFtZSB8fCBcInRyXCI7XG4gICAgICAgIHZhciBzdHlsZSA9IHtcbiAgICAgICAgICAgIGhlaWdodDogTWF0aC5tYXgoMCwgdG90YWwgLSB0aGlzLnN0YXRlLnN0b3ApICogdGhpcy5wcm9wcy5yb3dIZWlnaHRcbiAgICAgICAgfTtcbiAgICAgICAgcmV0dXJuIFJlYWN0LmNyZWF0ZUVsZW1lbnQoVGFnLCB7a2V5OiBcInBsYWNlaG9sZGVyLWJvdHRvbVwiLCBzdHlsZTogc3R5bGV9KTtcbiAgICB9LFxuICAgIGNvbXBvbmVudERpZE1vdW50OiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMub25TY3JvbGwoKTtcbiAgICAgICAgd2luZG93LmFkZEV2ZW50TGlzdGVuZXIoJ3Jlc2l6ZScsIHRoaXMub25TY3JvbGwpO1xuICAgIH0sXG4gICAgY29tcG9uZW50V2lsbFVubW91bnQ6IGZ1bmN0aW9uKCl7XG4gICAgICAgIHdpbmRvdy5yZW1vdmVFdmVudExpc3RlbmVyKCdyZXNpemUnLCB0aGlzLm9uU2Nyb2xsKTtcbiAgICB9LFxuICAgIG9uU2Nyb2xsOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciB2aWV3cG9ydCA9IHRoaXMuZ2V0RE9NTm9kZSgpO1xuICAgICAgICB2YXIgdG9wID0gdmlld3BvcnQuc2Nyb2xsVG9wO1xuICAgICAgICB2YXIgaGVpZ2h0ID0gdmlld3BvcnQub2Zmc2V0SGVpZ2h0O1xuICAgICAgICB2YXIgc3RhcnQgPSBNYXRoLmZsb29yKHRvcCAvIHRoaXMucHJvcHMucm93SGVpZ2h0KTtcbiAgICAgICAgdmFyIHN0b3AgPSBzdGFydCArIE1hdGguY2VpbChoZWlnaHQgLyAodGhpcy5wcm9wcy5yb3dIZWlnaHRNaW4gfHwgdGhpcy5wcm9wcy5yb3dIZWlnaHQpKTtcblxuICAgICAgICB0aGlzLnNldFN0YXRlKHtcbiAgICAgICAgICAgIHN0YXJ0OiBzdGFydCxcbiAgICAgICAgICAgIHN0b3A6IHN0b3BcbiAgICAgICAgfSk7XG4gICAgfSxcbiAgICByZW5kZXJSb3dzOiBmdW5jdGlvbiAoZWxlbXMpIHtcbiAgICAgICAgdmFyIHJvd3MgPSBbXTtcbiAgICAgICAgdmFyIG1heCA9IE1hdGgubWluKGVsZW1zLmxlbmd0aCwgdGhpcy5zdGF0ZS5zdG9wKTtcblxuICAgICAgICBmb3IgKHZhciBpID0gdGhpcy5zdGF0ZS5zdGFydDsgaSA8IG1heDsgaSsrKSB7XG4gICAgICAgICAgICB2YXIgZWxlbSA9IGVsZW1zW2ldO1xuICAgICAgICAgICAgcm93cy5wdXNoKHRoaXMucmVuZGVyUm93KGVsZW0pKTtcbiAgICAgICAgfVxuICAgICAgICByZXR1cm4gcm93cztcbiAgICB9LFxuICAgIHNjcm9sbFJvd0ludG9WaWV3OiBmdW5jdGlvbiAoaW5kZXgsIGhlYWRfaGVpZ2h0KSB7XG5cbiAgICAgICAgdmFyIHJvd190b3AgPSAoaW5kZXggKiB0aGlzLnByb3BzLnJvd0hlaWdodCkgKyBoZWFkX2hlaWdodDtcbiAgICAgICAgdmFyIHJvd19ib3R0b20gPSByb3dfdG9wICsgdGhpcy5wcm9wcy5yb3dIZWlnaHQ7XG5cbiAgICAgICAgdmFyIHZpZXdwb3J0ID0gdGhpcy5nZXRET01Ob2RlKCk7XG4gICAgICAgIHZhciB2aWV3cG9ydF90b3AgPSB2aWV3cG9ydC5zY3JvbGxUb3A7XG4gICAgICAgIHZhciB2aWV3cG9ydF9ib3R0b20gPSB2aWV3cG9ydF90b3AgKyB2aWV3cG9ydC5vZmZzZXRIZWlnaHQ7XG5cbiAgICAgICAgLy8gQWNjb3VudCBmb3IgcGlubmVkIHRoZWFkXG4gICAgICAgIGlmIChyb3dfdG9wIC0gaGVhZF9oZWlnaHQgPCB2aWV3cG9ydF90b3ApIHtcbiAgICAgICAgICAgIHZpZXdwb3J0LnNjcm9sbFRvcCA9IHJvd190b3AgLSBoZWFkX2hlaWdodDtcbiAgICAgICAgfSBlbHNlIGlmIChyb3dfYm90dG9tID4gdmlld3BvcnRfYm90dG9tKSB7XG4gICAgICAgICAgICB2aWV3cG9ydC5zY3JvbGxUb3AgPSByb3dfYm90dG9tIC0gdmlld3BvcnQub2Zmc2V0SGVpZ2h0O1xuICAgICAgICB9XG4gICAgfSxcbn07XG5cbm1vZHVsZS5leHBvcnRzICA9IFZpcnR1YWxTY3JvbGxNaXhpbjsiLCJcbnZhciBhY3Rpb25zID0gcmVxdWlyZShcIi4vYWN0aW9ucy5qc1wiKTtcblxuZnVuY3Rpb24gQ29ubmVjdGlvbih1cmwpIHtcbiAgICBpZiAodXJsWzBdID09PSBcIi9cIikge1xuICAgICAgICB1cmwgPSBsb2NhdGlvbi5vcmlnaW4ucmVwbGFjZShcImh0dHBcIiwgXCJ3c1wiKSArIHVybDtcbiAgICB9XG5cbiAgICB2YXIgd3MgPSBuZXcgV2ViU29ja2V0KHVybCk7XG4gICAgd3Mub25vcGVuID0gZnVuY3Rpb24gKCkge1xuICAgICAgICBhY3Rpb25zLkNvbm5lY3Rpb25BY3Rpb25zLm9wZW4oKTtcbiAgICB9O1xuICAgIHdzLm9ubWVzc2FnZSA9IGZ1bmN0aW9uIChtZXNzYWdlKSB7XG4gICAgICAgIHZhciBtID0gSlNPTi5wYXJzZShtZXNzYWdlLmRhdGEpO1xuICAgICAgICBBcHBEaXNwYXRjaGVyLmRpc3BhdGNoU2VydmVyQWN0aW9uKG0pO1xuICAgIH07XG4gICAgd3Mub25lcnJvciA9IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgYWN0aW9ucy5Db25uZWN0aW9uQWN0aW9ucy5lcnJvcigpO1xuICAgICAgICBFdmVudExvZ0FjdGlvbnMuYWRkX2V2ZW50KFwiV2ViU29ja2V0IGNvbm5lY3Rpb24gZXJyb3IuXCIpO1xuICAgIH07XG4gICAgd3Mub25jbG9zZSA9IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgYWN0aW9ucy5Db25uZWN0aW9uQWN0aW9ucy5jbG9zZSgpO1xuICAgICAgICBFdmVudExvZ0FjdGlvbnMuYWRkX2V2ZW50KFwiV2ViU29ja2V0IGNvbm5lY3Rpb24gY2xvc2VkLlwiKTtcbiAgICB9O1xuICAgIHJldHVybiB3cztcbn1cblxubW9kdWxlLmV4cG9ydHMgPSBDb25uZWN0aW9uOyIsIlxudmFyIGZsdXggPSByZXF1aXJlKFwiZmx1eFwiKTtcblxuY29uc3QgUGF5bG9hZFNvdXJjZXMgPSB7XG4gICAgVklFVzogXCJ2aWV3XCIsXG4gICAgU0VSVkVSOiBcInNlcnZlclwiXG59O1xuXG5cbkFwcERpc3BhdGNoZXIgPSBuZXcgZmx1eC5EaXNwYXRjaGVyKCk7XG5BcHBEaXNwYXRjaGVyLmRpc3BhdGNoVmlld0FjdGlvbiA9IGZ1bmN0aW9uIChhY3Rpb24pIHtcbiAgICBhY3Rpb24uc291cmNlID0gUGF5bG9hZFNvdXJjZXMuVklFVztcbiAgICB0aGlzLmRpc3BhdGNoKGFjdGlvbik7XG59O1xuQXBwRGlzcGF0Y2hlci5kaXNwYXRjaFNlcnZlckFjdGlvbiA9IGZ1bmN0aW9uIChhY3Rpb24pIHtcbiAgICBhY3Rpb24uc291cmNlID0gUGF5bG9hZFNvdXJjZXMuU0VSVkVSO1xuICAgIHRoaXMuZGlzcGF0Y2goYWN0aW9uKTtcbn07XG5cbm1vZHVsZS5leHBvcnRzID0ge1xuICAgIEFwcERpc3BhdGNoZXI6IEFwcERpc3BhdGNoZXJcbn07IiwiLyoganNoaW50IGlnbm9yZTpzdGFydCAqL1xuRmlsdCA9IChmdW5jdGlvbigpIHtcbiAgLypcbiAgICogR2VuZXJhdGVkIGJ5IFBFRy5qcyAwLjguMC5cbiAgICpcbiAgICogaHR0cDovL3BlZ2pzLm1hamRhLmN6L1xuICAgKi9cblxuICBmdW5jdGlvbiBwZWckc3ViY2xhc3MoY2hpbGQsIHBhcmVudCkge1xuICAgIGZ1bmN0aW9uIGN0b3IoKSB7IHRoaXMuY29uc3RydWN0b3IgPSBjaGlsZDsgfVxuICAgIGN0b3IucHJvdG90eXBlID0gcGFyZW50LnByb3RvdHlwZTtcbiAgICBjaGlsZC5wcm90b3R5cGUgPSBuZXcgY3RvcigpO1xuICB9XG5cbiAgZnVuY3Rpb24gU3ludGF4RXJyb3IobWVzc2FnZSwgZXhwZWN0ZWQsIGZvdW5kLCBvZmZzZXQsIGxpbmUsIGNvbHVtbikge1xuICAgIHRoaXMubWVzc2FnZSAgPSBtZXNzYWdlO1xuICAgIHRoaXMuZXhwZWN0ZWQgPSBleHBlY3RlZDtcbiAgICB0aGlzLmZvdW5kICAgID0gZm91bmQ7XG4gICAgdGhpcy5vZmZzZXQgICA9IG9mZnNldDtcbiAgICB0aGlzLmxpbmUgICAgID0gbGluZTtcbiAgICB0aGlzLmNvbHVtbiAgID0gY29sdW1uO1xuXG4gICAgdGhpcy5uYW1lICAgICA9IFwiU3ludGF4RXJyb3JcIjtcbiAgfVxuXG4gIHBlZyRzdWJjbGFzcyhTeW50YXhFcnJvciwgRXJyb3IpO1xuXG4gIGZ1bmN0aW9uIHBhcnNlKGlucHV0KSB7XG4gICAgdmFyIG9wdGlvbnMgPSBhcmd1bWVudHMubGVuZ3RoID4gMSA/IGFyZ3VtZW50c1sxXSA6IHt9LFxuXG4gICAgICAgIHBlZyRGQUlMRUQgPSB7fSxcblxuICAgICAgICBwZWckc3RhcnRSdWxlRnVuY3Rpb25zID0geyBzdGFydDogcGVnJHBhcnNlc3RhcnQgfSxcbiAgICAgICAgcGVnJHN0YXJ0UnVsZUZ1bmN0aW9uICA9IHBlZyRwYXJzZXN0YXJ0LFxuXG4gICAgICAgIHBlZyRjMCA9IHsgdHlwZTogXCJvdGhlclwiLCBkZXNjcmlwdGlvbjogXCJmaWx0ZXIgZXhwcmVzc2lvblwiIH0sXG4gICAgICAgIHBlZyRjMSA9IHBlZyRGQUlMRUQsXG4gICAgICAgIHBlZyRjMiA9IGZ1bmN0aW9uKG9yRXhwcikgeyByZXR1cm4gb3JFeHByOyB9LFxuICAgICAgICBwZWckYzMgPSBbXSxcbiAgICAgICAgcGVnJGM0ID0gZnVuY3Rpb24oKSB7cmV0dXJuIHRydWVGaWx0ZXI7IH0sXG4gICAgICAgIHBlZyRjNSA9IHsgdHlwZTogXCJvdGhlclwiLCBkZXNjcmlwdGlvbjogXCJ3aGl0ZXNwYWNlXCIgfSxcbiAgICAgICAgcGVnJGM2ID0gL15bIFxcdFxcblxccl0vLFxuICAgICAgICBwZWckYzcgPSB7IHR5cGU6IFwiY2xhc3NcIiwgdmFsdWU6IFwiWyBcXFxcdFxcXFxuXFxcXHJdXCIsIGRlc2NyaXB0aW9uOiBcIlsgXFxcXHRcXFxcblxcXFxyXVwiIH0sXG4gICAgICAgIHBlZyRjOCA9IHsgdHlwZTogXCJvdGhlclwiLCBkZXNjcmlwdGlvbjogXCJjb250cm9sIGNoYXJhY3RlclwiIH0sXG4gICAgICAgIHBlZyRjOSA9IC9eW3wmISgpflwiXS8sXG4gICAgICAgIHBlZyRjMTAgPSB7IHR5cGU6IFwiY2xhc3NcIiwgdmFsdWU6IFwiW3wmISgpflxcXCJdXCIsIGRlc2NyaXB0aW9uOiBcIlt8JiEoKX5cXFwiXVwiIH0sXG4gICAgICAgIHBlZyRjMTEgPSB7IHR5cGU6IFwib3RoZXJcIiwgZGVzY3JpcHRpb246IFwib3B0aW9uYWwgd2hpdGVzcGFjZVwiIH0sXG4gICAgICAgIHBlZyRjMTIgPSBcInxcIixcbiAgICAgICAgcGVnJGMxMyA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcInxcIiwgZGVzY3JpcHRpb246IFwiXFxcInxcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMxNCA9IGZ1bmN0aW9uKGZpcnN0LCBzZWNvbmQpIHsgcmV0dXJuIG9yKGZpcnN0LCBzZWNvbmQpOyB9LFxuICAgICAgICBwZWckYzE1ID0gXCImXCIsXG4gICAgICAgIHBlZyRjMTYgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCImXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCImXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMTcgPSBmdW5jdGlvbihmaXJzdCwgc2Vjb25kKSB7IHJldHVybiBhbmQoZmlyc3QsIHNlY29uZCk7IH0sXG4gICAgICAgIHBlZyRjMTggPSBcIiFcIixcbiAgICAgICAgcGVnJGMxOSA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIiFcIiwgZGVzY3JpcHRpb246IFwiXFxcIiFcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMyMCA9IGZ1bmN0aW9uKGV4cHIpIHsgcmV0dXJuIG5vdChleHByKTsgfSxcbiAgICAgICAgcGVnJGMyMSA9IFwiKFwiLFxuICAgICAgICBwZWckYzIyID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiKFwiLCBkZXNjcmlwdGlvbjogXCJcXFwiKFxcXCJcIiB9LFxuICAgICAgICBwZWckYzIzID0gXCIpXCIsXG4gICAgICAgIHBlZyRjMjQgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCIpXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCIpXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMjUgPSBmdW5jdGlvbihleHByKSB7IHJldHVybiBiaW5kaW5nKGV4cHIpOyB9LFxuICAgICAgICBwZWckYzI2ID0gXCJ+YVwiLFxuICAgICAgICBwZWckYzI3ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifmFcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5hXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMjggPSBmdW5jdGlvbigpIHsgcmV0dXJuIGFzc2V0RmlsdGVyOyB9LFxuICAgICAgICBwZWckYzI5ID0gXCJ+ZVwiLFxuICAgICAgICBwZWckYzMwID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifmVcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5lXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMzEgPSBmdW5jdGlvbigpIHsgcmV0dXJuIGVycm9yRmlsdGVyOyB9LFxuICAgICAgICBwZWckYzMyID0gXCJ+cVwiLFxuICAgICAgICBwZWckYzMzID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifnFcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5xXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMzQgPSBmdW5jdGlvbigpIHsgcmV0dXJuIG5vUmVzcG9uc2VGaWx0ZXI7IH0sXG4gICAgICAgIHBlZyRjMzUgPSBcIn5zXCIsXG4gICAgICAgIHBlZyRjMzYgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+c1wiLCBkZXNjcmlwdGlvbjogXCJcXFwifnNcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMzNyA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gcmVzcG9uc2VGaWx0ZXI7IH0sXG4gICAgICAgIHBlZyRjMzggPSBcInRydWVcIixcbiAgICAgICAgcGVnJGMzOSA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcInRydWVcIiwgZGVzY3JpcHRpb246IFwiXFxcInRydWVcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM0MCA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gdHJ1ZUZpbHRlcjsgfSxcbiAgICAgICAgcGVnJGM0MSA9IFwiZmFsc2VcIixcbiAgICAgICAgcGVnJGM0MiA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcImZhbHNlXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJmYWxzZVxcXCJcIiB9LFxuICAgICAgICBwZWckYzQzID0gZnVuY3Rpb24oKSB7IHJldHVybiBmYWxzZUZpbHRlcjsgfSxcbiAgICAgICAgcGVnJGM0NCA9IFwifmNcIixcbiAgICAgICAgcGVnJGM0NSA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn5jXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+Y1xcXCJcIiB9LFxuICAgICAgICBwZWckYzQ2ID0gZnVuY3Rpb24ocykgeyByZXR1cm4gcmVzcG9uc2VDb2RlKHMpOyB9LFxuICAgICAgICBwZWckYzQ3ID0gXCJ+ZFwiLFxuICAgICAgICBwZWckYzQ4ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifmRcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5kXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjNDkgPSBmdW5jdGlvbihzKSB7IHJldHVybiBkb21haW4ocyk7IH0sXG4gICAgICAgIHBlZyRjNTAgPSBcIn5oXCIsXG4gICAgICAgIHBlZyRjNTEgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+aFwiLCBkZXNjcmlwdGlvbjogXCJcXFwifmhcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM1MiA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIGhlYWRlcihzKTsgfSxcbiAgICAgICAgcGVnJGM1MyA9IFwifmhxXCIsXG4gICAgICAgIHBlZyRjNTQgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+aHFcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5ocVxcXCJcIiB9LFxuICAgICAgICBwZWckYzU1ID0gZnVuY3Rpb24ocykgeyByZXR1cm4gcmVxdWVzdEhlYWRlcihzKTsgfSxcbiAgICAgICAgcGVnJGM1NiA9IFwifmhzXCIsXG4gICAgICAgIHBlZyRjNTcgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+aHNcIiwgZGVzY3JpcHRpb246IFwiXFxcIn5oc1xcXCJcIiB9LFxuICAgICAgICBwZWckYzU4ID0gZnVuY3Rpb24ocykgeyByZXR1cm4gcmVzcG9uc2VIZWFkZXIocyk7IH0sXG4gICAgICAgIHBlZyRjNTkgPSBcIn5tXCIsXG4gICAgICAgIHBlZyRjNjAgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+bVwiLCBkZXNjcmlwdGlvbjogXCJcXFwifm1cXFwiXCIgfSxcbiAgICAgICAgcGVnJGM2MSA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIG1ldGhvZChzKTsgfSxcbiAgICAgICAgcGVnJGM2MiA9IFwifnRcIixcbiAgICAgICAgcGVnJGM2MyA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn50XCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+dFxcXCJcIiB9LFxuICAgICAgICBwZWckYzY0ID0gZnVuY3Rpb24ocykgeyByZXR1cm4gY29udGVudFR5cGUocyk7IH0sXG4gICAgICAgIHBlZyRjNjUgPSBcIn50cVwiLFxuICAgICAgICBwZWckYzY2ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwifnRxXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+dHFcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM2NyA9IGZ1bmN0aW9uKHMpIHsgcmV0dXJuIHJlcXVlc3RDb250ZW50VHlwZShzKTsgfSxcbiAgICAgICAgcGVnJGM2OCA9IFwifnRzXCIsXG4gICAgICAgIHBlZyRjNjkgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJ+dHNcIiwgZGVzY3JpcHRpb246IFwiXFxcIn50c1xcXCJcIiB9LFxuICAgICAgICBwZWckYzcwID0gZnVuY3Rpb24ocykgeyByZXR1cm4gcmVzcG9uc2VDb250ZW50VHlwZShzKTsgfSxcbiAgICAgICAgcGVnJGM3MSA9IFwifnVcIixcbiAgICAgICAgcGVnJGM3MiA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcIn51XCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJ+dVxcXCJcIiB9LFxuICAgICAgICBwZWckYzczID0gZnVuY3Rpb24ocykgeyByZXR1cm4gdXJsKHMpOyB9LFxuICAgICAgICBwZWckYzc0ID0geyB0eXBlOiBcIm90aGVyXCIsIGRlc2NyaXB0aW9uOiBcImludGVnZXJcIiB9LFxuICAgICAgICBwZWckYzc1ID0gbnVsbCxcbiAgICAgICAgcGVnJGM3NiA9IC9eWydcIl0vLFxuICAgICAgICBwZWckYzc3ID0geyB0eXBlOiBcImNsYXNzXCIsIHZhbHVlOiBcIlsnXFxcIl1cIiwgZGVzY3JpcHRpb246IFwiWydcXFwiXVwiIH0sXG4gICAgICAgIHBlZyRjNzggPSAvXlswLTldLyxcbiAgICAgICAgcGVnJGM3OSA9IHsgdHlwZTogXCJjbGFzc1wiLCB2YWx1ZTogXCJbMC05XVwiLCBkZXNjcmlwdGlvbjogXCJbMC05XVwiIH0sXG4gICAgICAgIHBlZyRjODAgPSBmdW5jdGlvbihkaWdpdHMpIHsgcmV0dXJuIHBhcnNlSW50KGRpZ2l0cy5qb2luKFwiXCIpLCAxMCk7IH0sXG4gICAgICAgIHBlZyRjODEgPSB7IHR5cGU6IFwib3RoZXJcIiwgZGVzY3JpcHRpb246IFwic3RyaW5nXCIgfSxcbiAgICAgICAgcGVnJGM4MiA9IFwiXFxcIlwiLFxuICAgICAgICBwZWckYzgzID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiXFxcIlwiLCBkZXNjcmlwdGlvbjogXCJcXFwiXFxcXFxcXCJcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM4NCA9IGZ1bmN0aW9uKGNoYXJzKSB7IHJldHVybiBjaGFycy5qb2luKFwiXCIpOyB9LFxuICAgICAgICBwZWckYzg1ID0gXCInXCIsXG4gICAgICAgIHBlZyRjODYgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCInXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCInXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjODcgPSB2b2lkIDAsXG4gICAgICAgIHBlZyRjODggPSAvXltcIlxcXFxdLyxcbiAgICAgICAgcGVnJGM4OSA9IHsgdHlwZTogXCJjbGFzc1wiLCB2YWx1ZTogXCJbXFxcIlxcXFxcXFxcXVwiLCBkZXNjcmlwdGlvbjogXCJbXFxcIlxcXFxcXFxcXVwiIH0sXG4gICAgICAgIHBlZyRjOTAgPSB7IHR5cGU6IFwiYW55XCIsIGRlc2NyaXB0aW9uOiBcImFueSBjaGFyYWN0ZXJcIiB9LFxuICAgICAgICBwZWckYzkxID0gZnVuY3Rpb24oY2hhcikgeyByZXR1cm4gY2hhcjsgfSxcbiAgICAgICAgcGVnJGM5MiA9IFwiXFxcXFwiLFxuICAgICAgICBwZWckYzkzID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwiXFxcXFwiLCBkZXNjcmlwdGlvbjogXCJcXFwiXFxcXFxcXFxcXFwiXCIgfSxcbiAgICAgICAgcGVnJGM5NCA9IC9eWydcXFxcXS8sXG4gICAgICAgIHBlZyRjOTUgPSB7IHR5cGU6IFwiY2xhc3NcIiwgdmFsdWU6IFwiWydcXFxcXFxcXF1cIiwgZGVzY3JpcHRpb246IFwiWydcXFxcXFxcXF1cIiB9LFxuICAgICAgICBwZWckYzk2ID0gL15bJ1wiXFxcXF0vLFxuICAgICAgICBwZWckYzk3ID0geyB0eXBlOiBcImNsYXNzXCIsIHZhbHVlOiBcIlsnXFxcIlxcXFxcXFxcXVwiLCBkZXNjcmlwdGlvbjogXCJbJ1xcXCJcXFxcXFxcXF1cIiB9LFxuICAgICAgICBwZWckYzk4ID0gXCJuXCIsXG4gICAgICAgIHBlZyRjOTkgPSB7IHR5cGU6IFwibGl0ZXJhbFwiLCB2YWx1ZTogXCJuXCIsIGRlc2NyaXB0aW9uOiBcIlxcXCJuXFxcIlwiIH0sXG4gICAgICAgIHBlZyRjMTAwID0gZnVuY3Rpb24oKSB7IHJldHVybiBcIlxcblwiOyB9LFxuICAgICAgICBwZWckYzEwMSA9IFwiclwiLFxuICAgICAgICBwZWckYzEwMiA9IHsgdHlwZTogXCJsaXRlcmFsXCIsIHZhbHVlOiBcInJcIiwgZGVzY3JpcHRpb246IFwiXFxcInJcXFwiXCIgfSxcbiAgICAgICAgcGVnJGMxMDMgPSBmdW5jdGlvbigpIHsgcmV0dXJuIFwiXFxyXCI7IH0sXG4gICAgICAgIHBlZyRjMTA0ID0gXCJ0XCIsXG4gICAgICAgIHBlZyRjMTA1ID0geyB0eXBlOiBcImxpdGVyYWxcIiwgdmFsdWU6IFwidFwiLCBkZXNjcmlwdGlvbjogXCJcXFwidFxcXCJcIiB9LFxuICAgICAgICBwZWckYzEwNiA9IGZ1bmN0aW9uKCkgeyByZXR1cm4gXCJcXHRcIjsgfSxcblxuICAgICAgICBwZWckY3VyclBvcyAgICAgICAgICA9IDAsXG4gICAgICAgIHBlZyRyZXBvcnRlZFBvcyAgICAgID0gMCxcbiAgICAgICAgcGVnJGNhY2hlZFBvcyAgICAgICAgPSAwLFxuICAgICAgICBwZWckY2FjaGVkUG9zRGV0YWlscyA9IHsgbGluZTogMSwgY29sdW1uOiAxLCBzZWVuQ1I6IGZhbHNlIH0sXG4gICAgICAgIHBlZyRtYXhGYWlsUG9zICAgICAgID0gMCxcbiAgICAgICAgcGVnJG1heEZhaWxFeHBlY3RlZCAgPSBbXSxcbiAgICAgICAgcGVnJHNpbGVudEZhaWxzICAgICAgPSAwLFxuXG4gICAgICAgIHBlZyRyZXN1bHQ7XG5cbiAgICBpZiAoXCJzdGFydFJ1bGVcIiBpbiBvcHRpb25zKSB7XG4gICAgICBpZiAoIShvcHRpb25zLnN0YXJ0UnVsZSBpbiBwZWckc3RhcnRSdWxlRnVuY3Rpb25zKSkge1xuICAgICAgICB0aHJvdyBuZXcgRXJyb3IoXCJDYW4ndCBzdGFydCBwYXJzaW5nIGZyb20gcnVsZSBcXFwiXCIgKyBvcHRpb25zLnN0YXJ0UnVsZSArIFwiXFxcIi5cIik7XG4gICAgICB9XG5cbiAgICAgIHBlZyRzdGFydFJ1bGVGdW5jdGlvbiA9IHBlZyRzdGFydFJ1bGVGdW5jdGlvbnNbb3B0aW9ucy5zdGFydFJ1bGVdO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHRleHQoKSB7XG4gICAgICByZXR1cm4gaW5wdXQuc3Vic3RyaW5nKHBlZyRyZXBvcnRlZFBvcywgcGVnJGN1cnJQb3MpO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIG9mZnNldCgpIHtcbiAgICAgIHJldHVybiBwZWckcmVwb3J0ZWRQb3M7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gbGluZSgpIHtcbiAgICAgIHJldHVybiBwZWckY29tcHV0ZVBvc0RldGFpbHMocGVnJHJlcG9ydGVkUG9zKS5saW5lO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIGNvbHVtbigpIHtcbiAgICAgIHJldHVybiBwZWckY29tcHV0ZVBvc0RldGFpbHMocGVnJHJlcG9ydGVkUG9zKS5jb2x1bW47XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gZXhwZWN0ZWQoZGVzY3JpcHRpb24pIHtcbiAgICAgIHRocm93IHBlZyRidWlsZEV4Y2VwdGlvbihcbiAgICAgICAgbnVsbCxcbiAgICAgICAgW3sgdHlwZTogXCJvdGhlclwiLCBkZXNjcmlwdGlvbjogZGVzY3JpcHRpb24gfV0sXG4gICAgICAgIHBlZyRyZXBvcnRlZFBvc1xuICAgICAgKTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBlcnJvcihtZXNzYWdlKSB7XG4gICAgICB0aHJvdyBwZWckYnVpbGRFeGNlcHRpb24obWVzc2FnZSwgbnVsbCwgcGVnJHJlcG9ydGVkUG9zKTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckY29tcHV0ZVBvc0RldGFpbHMocG9zKSB7XG4gICAgICBmdW5jdGlvbiBhZHZhbmNlKGRldGFpbHMsIHN0YXJ0UG9zLCBlbmRQb3MpIHtcbiAgICAgICAgdmFyIHAsIGNoO1xuXG4gICAgICAgIGZvciAocCA9IHN0YXJ0UG9zOyBwIDwgZW5kUG9zOyBwKyspIHtcbiAgICAgICAgICBjaCA9IGlucHV0LmNoYXJBdChwKTtcbiAgICAgICAgICBpZiAoY2ggPT09IFwiXFxuXCIpIHtcbiAgICAgICAgICAgIGlmICghZGV0YWlscy5zZWVuQ1IpIHsgZGV0YWlscy5saW5lKys7IH1cbiAgICAgICAgICAgIGRldGFpbHMuY29sdW1uID0gMTtcbiAgICAgICAgICAgIGRldGFpbHMuc2VlbkNSID0gZmFsc2U7XG4gICAgICAgICAgfSBlbHNlIGlmIChjaCA9PT0gXCJcXHJcIiB8fCBjaCA9PT0gXCJcXHUyMDI4XCIgfHwgY2ggPT09IFwiXFx1MjAyOVwiKSB7XG4gICAgICAgICAgICBkZXRhaWxzLmxpbmUrKztcbiAgICAgICAgICAgIGRldGFpbHMuY29sdW1uID0gMTtcbiAgICAgICAgICAgIGRldGFpbHMuc2VlbkNSID0gdHJ1ZTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgZGV0YWlscy5jb2x1bW4rKztcbiAgICAgICAgICAgIGRldGFpbHMuc2VlbkNSID0gZmFsc2U7XG4gICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICB9XG5cbiAgICAgIGlmIChwZWckY2FjaGVkUG9zICE9PSBwb3MpIHtcbiAgICAgICAgaWYgKHBlZyRjYWNoZWRQb3MgPiBwb3MpIHtcbiAgICAgICAgICBwZWckY2FjaGVkUG9zID0gMDtcbiAgICAgICAgICBwZWckY2FjaGVkUG9zRGV0YWlscyA9IHsgbGluZTogMSwgY29sdW1uOiAxLCBzZWVuQ1I6IGZhbHNlIH07XG4gICAgICAgIH1cbiAgICAgICAgYWR2YW5jZShwZWckY2FjaGVkUG9zRGV0YWlscywgcGVnJGNhY2hlZFBvcywgcG9zKTtcbiAgICAgICAgcGVnJGNhY2hlZFBvcyA9IHBvcztcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHBlZyRjYWNoZWRQb3NEZXRhaWxzO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRmYWlsKGV4cGVjdGVkKSB7XG4gICAgICBpZiAocGVnJGN1cnJQb3MgPCBwZWckbWF4RmFpbFBvcykgeyByZXR1cm47IH1cblxuICAgICAgaWYgKHBlZyRjdXJyUG9zID4gcGVnJG1heEZhaWxQb3MpIHtcbiAgICAgICAgcGVnJG1heEZhaWxQb3MgPSBwZWckY3VyclBvcztcbiAgICAgICAgcGVnJG1heEZhaWxFeHBlY3RlZCA9IFtdO1xuICAgICAgfVxuXG4gICAgICBwZWckbWF4RmFpbEV4cGVjdGVkLnB1c2goZXhwZWN0ZWQpO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRidWlsZEV4Y2VwdGlvbihtZXNzYWdlLCBleHBlY3RlZCwgcG9zKSB7XG4gICAgICBmdW5jdGlvbiBjbGVhbnVwRXhwZWN0ZWQoZXhwZWN0ZWQpIHtcbiAgICAgICAgdmFyIGkgPSAxO1xuXG4gICAgICAgIGV4cGVjdGVkLnNvcnQoZnVuY3Rpb24oYSwgYikge1xuICAgICAgICAgIGlmIChhLmRlc2NyaXB0aW9uIDwgYi5kZXNjcmlwdGlvbikge1xuICAgICAgICAgICAgcmV0dXJuIC0xO1xuICAgICAgICAgIH0gZWxzZSBpZiAoYS5kZXNjcmlwdGlvbiA+IGIuZGVzY3JpcHRpb24pIHtcbiAgICAgICAgICAgIHJldHVybiAxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICByZXR1cm4gMDtcbiAgICAgICAgICB9XG4gICAgICAgIH0pO1xuXG4gICAgICAgIHdoaWxlIChpIDwgZXhwZWN0ZWQubGVuZ3RoKSB7XG4gICAgICAgICAgaWYgKGV4cGVjdGVkW2kgLSAxXSA9PT0gZXhwZWN0ZWRbaV0pIHtcbiAgICAgICAgICAgIGV4cGVjdGVkLnNwbGljZShpLCAxKTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgaSsrO1xuICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICBmdW5jdGlvbiBidWlsZE1lc3NhZ2UoZXhwZWN0ZWQsIGZvdW5kKSB7XG4gICAgICAgIGZ1bmN0aW9uIHN0cmluZ0VzY2FwZShzKSB7XG4gICAgICAgICAgZnVuY3Rpb24gaGV4KGNoKSB7IHJldHVybiBjaC5jaGFyQ29kZUF0KDApLnRvU3RyaW5nKDE2KS50b1VwcGVyQ2FzZSgpOyB9XG5cbiAgICAgICAgICByZXR1cm4gc1xuICAgICAgICAgICAgLnJlcGxhY2UoL1xcXFwvZywgICAnXFxcXFxcXFwnKVxuICAgICAgICAgICAgLnJlcGxhY2UoL1wiL2csICAgICdcXFxcXCInKVxuICAgICAgICAgICAgLnJlcGxhY2UoL1xceDA4L2csICdcXFxcYicpXG4gICAgICAgICAgICAucmVwbGFjZSgvXFx0L2csICAgJ1xcXFx0JylcbiAgICAgICAgICAgIC5yZXBsYWNlKC9cXG4vZywgICAnXFxcXG4nKVxuICAgICAgICAgICAgLnJlcGxhY2UoL1xcZi9nLCAgICdcXFxcZicpXG4gICAgICAgICAgICAucmVwbGFjZSgvXFxyL2csICAgJ1xcXFxyJylcbiAgICAgICAgICAgIC5yZXBsYWNlKC9bXFx4MDAtXFx4MDdcXHgwQlxceDBFXFx4MEZdL2csIGZ1bmN0aW9uKGNoKSB7IHJldHVybiAnXFxcXHgwJyArIGhleChjaCk7IH0pXG4gICAgICAgICAgICAucmVwbGFjZSgvW1xceDEwLVxceDFGXFx4ODAtXFx4RkZdL2csICAgIGZ1bmN0aW9uKGNoKSB7IHJldHVybiAnXFxcXHgnICArIGhleChjaCk7IH0pXG4gICAgICAgICAgICAucmVwbGFjZSgvW1xcdTAxODAtXFx1MEZGRl0vZywgICAgICAgICBmdW5jdGlvbihjaCkgeyByZXR1cm4gJ1xcXFx1MCcgKyBoZXgoY2gpOyB9KVxuICAgICAgICAgICAgLnJlcGxhY2UoL1tcXHUxMDgwLVxcdUZGRkZdL2csICAgICAgICAgZnVuY3Rpb24oY2gpIHsgcmV0dXJuICdcXFxcdScgICsgaGV4KGNoKTsgfSk7XG4gICAgICAgIH1cblxuICAgICAgICB2YXIgZXhwZWN0ZWREZXNjcyA9IG5ldyBBcnJheShleHBlY3RlZC5sZW5ndGgpLFxuICAgICAgICAgICAgZXhwZWN0ZWREZXNjLCBmb3VuZERlc2MsIGk7XG5cbiAgICAgICAgZm9yIChpID0gMDsgaSA8IGV4cGVjdGVkLmxlbmd0aDsgaSsrKSB7XG4gICAgICAgICAgZXhwZWN0ZWREZXNjc1tpXSA9IGV4cGVjdGVkW2ldLmRlc2NyaXB0aW9uO1xuICAgICAgICB9XG5cbiAgICAgICAgZXhwZWN0ZWREZXNjID0gZXhwZWN0ZWQubGVuZ3RoID4gMVxuICAgICAgICAgID8gZXhwZWN0ZWREZXNjcy5zbGljZSgwLCAtMSkuam9pbihcIiwgXCIpXG4gICAgICAgICAgICAgICsgXCIgb3IgXCJcbiAgICAgICAgICAgICAgKyBleHBlY3RlZERlc2NzW2V4cGVjdGVkLmxlbmd0aCAtIDFdXG4gICAgICAgICAgOiBleHBlY3RlZERlc2NzWzBdO1xuXG4gICAgICAgIGZvdW5kRGVzYyA9IGZvdW5kID8gXCJcXFwiXCIgKyBzdHJpbmdFc2NhcGUoZm91bmQpICsgXCJcXFwiXCIgOiBcImVuZCBvZiBpbnB1dFwiO1xuXG4gICAgICAgIHJldHVybiBcIkV4cGVjdGVkIFwiICsgZXhwZWN0ZWREZXNjICsgXCIgYnV0IFwiICsgZm91bmREZXNjICsgXCIgZm91bmQuXCI7XG4gICAgICB9XG5cbiAgICAgIHZhciBwb3NEZXRhaWxzID0gcGVnJGNvbXB1dGVQb3NEZXRhaWxzKHBvcyksXG4gICAgICAgICAgZm91bmQgICAgICA9IHBvcyA8IGlucHV0Lmxlbmd0aCA/IGlucHV0LmNoYXJBdChwb3MpIDogbnVsbDtcblxuICAgICAgaWYgKGV4cGVjdGVkICE9PSBudWxsKSB7XG4gICAgICAgIGNsZWFudXBFeHBlY3RlZChleHBlY3RlZCk7XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBuZXcgU3ludGF4RXJyb3IoXG4gICAgICAgIG1lc3NhZ2UgIT09IG51bGwgPyBtZXNzYWdlIDogYnVpbGRNZXNzYWdlKGV4cGVjdGVkLCBmb3VuZCksXG4gICAgICAgIGV4cGVjdGVkLFxuICAgICAgICBmb3VuZCxcbiAgICAgICAgcG9zLFxuICAgICAgICBwb3NEZXRhaWxzLmxpbmUsXG4gICAgICAgIHBvc0RldGFpbHMuY29sdW1uXG4gICAgICApO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZXN0YXJ0KCkge1xuICAgICAgdmFyIHMwLCBzMSwgczIsIHMzO1xuXG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBzMSA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBwZWckcGFyc2VPckV4cHIoKTtcbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczMgPSBwZWckcGFyc2VfXygpO1xuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICBzMSA9IHBlZyRjMihzMik7XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIHMxID0gW107XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgIHMxID0gcGVnJGM0KCk7XG4gICAgICAgIH1cbiAgICAgICAgczAgPSBzMTtcbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzApOyB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2V3cygpIHtcbiAgICAgIHZhciBzMCwgczE7XG5cbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgaWYgKHBlZyRjNi50ZXN0KGlucHV0LmNoYXJBdChwZWckY3VyclBvcykpKSB7XG4gICAgICAgIHMwID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHMwID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzcpOyB9XG4gICAgICB9XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM1KTsgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlY2MoKSB7XG4gICAgICB2YXIgczAsIHMxO1xuXG4gICAgICBwZWckc2lsZW50RmFpbHMrKztcbiAgICAgIGlmIChwZWckYzkudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICBzMCA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMCA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMxMCk7IH1cbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzgpOyB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VfXygpIHtcbiAgICAgIHZhciBzMCwgczE7XG5cbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgczAgPSBbXTtcbiAgICAgIHMxID0gcGVnJHBhcnNld3MoKTtcbiAgICAgIHdoaWxlIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMC5wdXNoKHMxKTtcbiAgICAgICAgczEgPSBwZWckcGFyc2V3cygpO1xuICAgICAgfVxuICAgICAgcGVnJHNpbGVudEZhaWxzLS07XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMTEpOyB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VPckV4cHIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczMsIHM0LCBzNTtcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIHMxID0gcGVnJHBhcnNlQW5kRXhwcigpO1xuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAxMjQpIHtcbiAgICAgICAgICAgIHMzID0gcGVnJGMxMjtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMzID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMxMyk7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzNCA9IHBlZyRwYXJzZV9fKCk7XG4gICAgICAgICAgICBpZiAoczQgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczUgPSBwZWckcGFyc2VPckV4cHIoKTtcbiAgICAgICAgICAgICAgaWYgKHM1ICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckYzE0KHMxLCBzNSk7XG4gICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRwYXJzZUFuZEV4cHIoKTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZUFuZEV4cHIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczMsIHM0LCBzNTtcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIHMxID0gcGVnJHBhcnNlTm90RXhwcigpO1xuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMyID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAzOCkge1xuICAgICAgICAgICAgczMgPSBwZWckYzE1O1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczMgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzE2KTsgfVxuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHM0ID0gcGVnJHBhcnNlX18oKTtcbiAgICAgICAgICAgIGlmIChzNCAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBzNSA9IHBlZyRwYXJzZUFuZEV4cHIoKTtcbiAgICAgICAgICAgICAgaWYgKHM1ICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckYzE3KHMxLCBzNSk7XG4gICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBzMSA9IHBlZyRwYXJzZU5vdEV4cHIoKTtcbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczMgPSBwZWckcGFyc2VBbmRFeHByKCk7XG4gICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGMxNyhzMSwgczMpO1xuICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMCA9IHBlZyRwYXJzZU5vdEV4cHIoKTtcbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlTm90RXhwcigpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyLCBzMztcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMzMpIHtcbiAgICAgICAgczEgPSBwZWckYzE4O1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMTkpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBwZWckcGFyc2VfXygpO1xuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZU5vdEV4cHIoKTtcbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzIwKHMzKTtcbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckcGFyc2VCaW5kaW5nRXhwcigpO1xuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlQmluZGluZ0V4cHIoKSB7XG4gICAgICB2YXIgczAsIHMxLCBzMiwgczMsIHM0LCBzNTtcblxuICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gNDApIHtcbiAgICAgICAgczEgPSBwZWckYzIxO1xuICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMjIpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBwZWckcGFyc2VfXygpO1xuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZU9yRXhwcigpO1xuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczQgPSBwZWckcGFyc2VfXygpO1xuICAgICAgICAgICAgaWYgKHM0ICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gNDEpIHtcbiAgICAgICAgICAgICAgICBzNSA9IHBlZyRjMjM7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBzNSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzI0KTsgfVxuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIGlmIChzNSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJGMyNShzMyk7XG4gICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRwYXJzZUV4cHIoKTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZUV4cHIoKSB7XG4gICAgICB2YXIgczA7XG5cbiAgICAgIHMwID0gcGVnJHBhcnNlTnVsbGFyeUV4cHIoKTtcbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRwYXJzZVVuYXJ5RXhwcigpO1xuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlTnVsbGFyeUV4cHIoKSB7XG4gICAgICB2YXIgczAsIHMxO1xuXG4gICAgICBzMCA9IHBlZyRwYXJzZUJvb2xlYW5MaXRlcmFsKCk7XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjMjYpIHtcbiAgICAgICAgICBzMSA9IHBlZyRjMjY7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzI3KTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgIHMxID0gcGVnJGMyOCgpO1xuICAgICAgICB9XG4gICAgICAgIHMwID0gczE7XG4gICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjMjkpIHtcbiAgICAgICAgICAgIHMxID0gcGVnJGMyOTtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMzMCk7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGMzMSgpO1xuICAgICAgICAgIH1cbiAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzMyKSB7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGMzMjtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzMzKTsgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjMzQoKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjMzUpIHtcbiAgICAgICAgICAgICAgICBzMSA9IHBlZyRjMzU7XG4gICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzM2KTsgfVxuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICAgIHMxID0gcGVnJGMzNygpO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VCb29sZWFuTGl0ZXJhbCgpIHtcbiAgICAgIHZhciBzMCwgczE7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCA0KSA9PT0gcGVnJGMzOCkge1xuICAgICAgICBzMSA9IHBlZyRjMzg7XG4gICAgICAgIHBlZyRjdXJyUG9zICs9IDQ7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMzOSk7IH1cbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgczEgPSBwZWckYzQwKCk7XG4gICAgICB9XG4gICAgICBzMCA9IHMxO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDUpID09PSBwZWckYzQxKSB7XG4gICAgICAgICAgczEgPSBwZWckYzQxO1xuICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDU7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM0Mik7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICBzMSA9IHBlZyRjNDMoKTtcbiAgICAgICAgfVxuICAgICAgICBzMCA9IHMxO1xuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlVW5hcnlFeHByKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczIsIHMzO1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgaWYgKGlucHV0LnN1YnN0cihwZWckY3VyclBvcywgMikgPT09IHBlZyRjNDQpIHtcbiAgICAgICAgczEgPSBwZWckYzQ0O1xuICAgICAgICBwZWckY3VyclBvcyArPSAyO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNDUpOyB9XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBbXTtcbiAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZUludGVnZXJMaXRlcmFsKCk7XG4gICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgIHMxID0gcGVnJGM0NihzMyk7XG4gICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzQ3KSB7XG4gICAgICAgICAgczEgPSBwZWckYzQ3O1xuICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDI7XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM0OCk7IH1cbiAgICAgICAgfVxuICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczEgPSBwZWckYzQ5KHMzKTtcbiAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGM1MCkge1xuICAgICAgICAgICAgczEgPSBwZWckYzUwO1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzUxKTsgfVxuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckYzUyKHMzKTtcbiAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDMpID09PSBwZWckYzUzKSB7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGM1MztcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMztcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzU0KTsgfVxuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM1NShzMyk7XG4gICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDMpID09PSBwZWckYzU2KSB7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckYzU2O1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDM7XG4gICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM1Nyk7IH1cbiAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzU4KHMzKTtcbiAgICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAyKSA9PT0gcGVnJGM1OSkge1xuICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzU5O1xuICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzYwKTsgfVxuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzYxKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzYyKSB7XG4gICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM2MjtcbiAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzYzKTsgfVxuICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM2NChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDMpID09PSBwZWckYzY1KSB7XG4gICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzY1O1xuICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zICs9IDM7XG4gICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM2Nik7IH1cbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICBzMiA9IFtdO1xuICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzY3KHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgICAgICAgICAgICBpZiAoaW5wdXQuc3Vic3RyKHBlZyRjdXJyUG9zLCAzKSA9PT0gcGVnJGM2OCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzY4O1xuICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMztcbiAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzY5KTsgfVxuICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2V3cygpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMiA9IHBlZyRjMTtcbiAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVN0cmluZ0xpdGVyYWwoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczEgPSBwZWckYzcwKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgICAgICAgICAgICAgIGlmIChpbnB1dC5zdWJzdHIocGVnJGN1cnJQb3MsIDIpID09PSBwZWckYzcxKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM3MTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgKz0gMjtcbiAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzcyKTsgfVxuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNld3MoKTtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczIgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTdHJpbmdMaXRlcmFsKCk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJGM3MyhzMyk7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMxID0gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzMSA9IHBlZyRjNzMoczEpO1xuICAgICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBwZWckcGFyc2VJbnRlZ2VyTGl0ZXJhbCgpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyLCBzMztcblxuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgaWYgKHBlZyRjNzYudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICBzMSA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM3Nyk7IH1cbiAgICAgIH1cbiAgICAgIGlmIChzMSA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRjNzU7XG4gICAgICB9XG4gICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczIgPSBbXTtcbiAgICAgICAgaWYgKHBlZyRjNzgudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICAgIHMzID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMzID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNzkpOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMi5wdXNoKHMzKTtcbiAgICAgICAgICAgIGlmIChwZWckYzc4LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgICAgICAgczMgPSBpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpO1xuICAgICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgczMgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjNzkpOyB9XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIGlmIChwZWckYzc2LnRlc3QoaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKSkpIHtcbiAgICAgICAgICAgIHMzID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHMzID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM3Nyk7IH1cbiAgICAgICAgICB9XG4gICAgICAgICAgaWYgKHMzID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICBzMyA9IHBlZyRjNzU7XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICBzMSA9IHBlZyRjODAoczIpO1xuICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzc0KTsgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlU3RyaW5nTGl0ZXJhbCgpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyLCBzMztcblxuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAzNCkge1xuICAgICAgICBzMSA9IHBlZyRjODI7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM4Myk7IH1cbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMiA9IFtdO1xuICAgICAgICBzMyA9IHBlZyRwYXJzZURvdWJsZVN0cmluZ0NoYXIoKTtcbiAgICAgICAgd2hpbGUgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczIucHVzaChzMyk7XG4gICAgICAgICAgczMgPSBwZWckcGFyc2VEb3VibGVTdHJpbmdDaGFyKCk7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAzNCkge1xuICAgICAgICAgICAgczMgPSBwZWckYzgyO1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgczMgPSBwZWckRkFJTEVEO1xuICAgICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzgzKTsgfVxuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzg0KHMyKTtcbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICB9XG4gICAgICBpZiAoczAgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAzOSkge1xuICAgICAgICAgIHMxID0gcGVnJGM4NTtcbiAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjODYpOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczIgPSBbXTtcbiAgICAgICAgICBzMyA9IHBlZyRwYXJzZVNpbmdsZVN0cmluZ0NoYXIoKTtcbiAgICAgICAgICB3aGlsZSAoczMgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgczMgPSBwZWckcGFyc2VTaW5nbGVTdHJpbmdDaGFyKCk7XG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAzOSkge1xuICAgICAgICAgICAgICBzMyA9IHBlZyRjODU7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBzMyA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM4Nik7IH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGlmIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICBwZWckcmVwb3J0ZWRQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczEgPSBwZWckYzg0KHMyKTtcbiAgICAgICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgfVxuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICBzMSA9IHBlZyRjdXJyUG9zO1xuICAgICAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgICAgIHMyID0gcGVnJHBhcnNlY2MoKTtcbiAgICAgICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgICAgICBpZiAoczIgPT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMxID0gcGVnJGM4NztcbiAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMTtcbiAgICAgICAgICAgIHMxID0gcGVnJGMxO1xuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHMyID0gW107XG4gICAgICAgICAgICBzMyA9IHBlZyRwYXJzZVVucXVvdGVkU3RyaW5nQ2hhcigpO1xuICAgICAgICAgICAgaWYgKHMzICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHdoaWxlIChzMyAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgICAgIHMyLnB1c2goczMpO1xuICAgICAgICAgICAgICAgIHMzID0gcGVnJHBhcnNlVW5xdW90ZWRTdHJpbmdDaGFyKCk7XG4gICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgIHMyID0gcGVnJGMxO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgICBzMSA9IHBlZyRjODQoczIpO1xuICAgICAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzgxKTsgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlRG91YmxlU3RyaW5nQ2hhcigpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyO1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgczEgPSBwZWckY3VyclBvcztcbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgaWYgKHBlZyRjODgudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICBzMiA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMiA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM4OSk7IH1cbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMyID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJGM4NztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczE7XG4gICAgICAgIHMxID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIGlmIChpbnB1dC5sZW5ndGggPiBwZWckY3VyclBvcykge1xuICAgICAgICAgIHMyID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMyID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOTApOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgczEgPSBwZWckYzkxKHMyKTtcbiAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gOTIpIHtcbiAgICAgICAgICBzMSA9IHBlZyRjOTI7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzkzKTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMyID0gcGVnJHBhcnNlRXNjYXBlU2VxdWVuY2UoKTtcbiAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzkxKHMyKTtcbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlU2luZ2xlU3RyaW5nQ2hhcigpIHtcbiAgICAgIHZhciBzMCwgczEsIHMyO1xuXG4gICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgczEgPSBwZWckY3VyclBvcztcbiAgICAgIHBlZyRzaWxlbnRGYWlscysrO1xuICAgICAgaWYgKHBlZyRjOTQudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICBzMiA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMiA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM5NSk7IH1cbiAgICAgIH1cbiAgICAgIHBlZyRzaWxlbnRGYWlscy0tO1xuICAgICAgaWYgKHMyID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMxID0gcGVnJGM4NztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczE7XG4gICAgICAgIHMxID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIGlmIChpbnB1dC5sZW5ndGggPiBwZWckY3VyclBvcykge1xuICAgICAgICAgIHMyID0gaW5wdXQuY2hhckF0KHBlZyRjdXJyUG9zKTtcbiAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMyID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOTApOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMyICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgczEgPSBwZWckYzkxKHMyKTtcbiAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgczAgPSBwZWckYzE7XG4gICAgICAgIH1cbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgfVxuICAgICAgaWYgKHMwID09PSBwZWckRkFJTEVEKSB7XG4gICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gOTIpIHtcbiAgICAgICAgICBzMSA9IHBlZyRjOTI7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzkzKTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMyID0gcGVnJHBhcnNlRXNjYXBlU2VxdWVuY2UoKTtcbiAgICAgICAgICBpZiAoczIgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzkxKHMyKTtcbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHBlZyRjdXJyUG9zID0gczA7XG4gICAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgICB9XG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgcGVnJGN1cnJQb3MgPSBzMDtcbiAgICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICByZXR1cm4gczA7XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gcGVnJHBhcnNlVW5xdW90ZWRTdHJpbmdDaGFyKCkge1xuICAgICAgdmFyIHMwLCBzMSwgczI7XG5cbiAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICBzMSA9IHBlZyRjdXJyUG9zO1xuICAgICAgcGVnJHNpbGVudEZhaWxzKys7XG4gICAgICBzMiA9IHBlZyRwYXJzZXdzKCk7XG4gICAgICBwZWckc2lsZW50RmFpbHMtLTtcbiAgICAgIGlmIChzMiA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMSA9IHBlZyRjODc7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMxO1xuICAgICAgICBzMSA9IHBlZyRjMTtcbiAgICAgIH1cbiAgICAgIGlmIChzMSAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBpZiAoaW5wdXQubGVuZ3RoID4gcGVnJGN1cnJQb3MpIHtcbiAgICAgICAgICBzMiA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgICAgcGVnJGN1cnJQb3MrKztcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBzMiA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgaWYgKHBlZyRzaWxlbnRGYWlscyA9PT0gMCkgeyBwZWckZmFpbChwZWckYzkwKTsgfVxuICAgICAgICB9XG4gICAgICAgIGlmIChzMiAhPT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgIHMxID0gcGVnJGM5MShzMik7XG4gICAgICAgICAgczAgPSBzMTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICAgIHMwID0gcGVnJGMxO1xuICAgICAgICB9XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwZWckY3VyclBvcyA9IHMwO1xuICAgICAgICBzMCA9IHBlZyRjMTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHMwO1xuICAgIH1cblxuICAgIGZ1bmN0aW9uIHBlZyRwYXJzZUVzY2FwZVNlcXVlbmNlKCkge1xuICAgICAgdmFyIHMwLCBzMTtcblxuICAgICAgaWYgKHBlZyRjOTYudGVzdChpbnB1dC5jaGFyQXQocGVnJGN1cnJQb3MpKSkge1xuICAgICAgICBzMCA9IGlucHV0LmNoYXJBdChwZWckY3VyclBvcyk7XG4gICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzMCA9IHBlZyRGQUlMRUQ7XG4gICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGM5Nyk7IH1cbiAgICAgIH1cbiAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICBzMCA9IHBlZyRjdXJyUG9zO1xuICAgICAgICBpZiAoaW5wdXQuY2hhckNvZGVBdChwZWckY3VyclBvcykgPT09IDExMCkge1xuICAgICAgICAgIHMxID0gcGVnJGM5ODtcbiAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHMxID0gcGVnJEZBSUxFRDtcbiAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjOTkpOyB9XG4gICAgICAgIH1cbiAgICAgICAgaWYgKHMxICE9PSBwZWckRkFJTEVEKSB7XG4gICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgczEgPSBwZWckYzEwMCgpO1xuICAgICAgICB9XG4gICAgICAgIHMwID0gczE7XG4gICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgIHMwID0gcGVnJGN1cnJQb3M7XG4gICAgICAgICAgaWYgKGlucHV0LmNoYXJDb2RlQXQocGVnJGN1cnJQb3MpID09PSAxMTQpIHtcbiAgICAgICAgICAgIHMxID0gcGVnJGMxMDE7XG4gICAgICAgICAgICBwZWckY3VyclBvcysrO1xuICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICBpZiAocGVnJHNpbGVudEZhaWxzID09PSAwKSB7IHBlZyRmYWlsKHBlZyRjMTAyKTsgfVxuICAgICAgICAgIH1cbiAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgIHBlZyRyZXBvcnRlZFBvcyA9IHMwO1xuICAgICAgICAgICAgczEgPSBwZWckYzEwMygpO1xuICAgICAgICAgIH1cbiAgICAgICAgICBzMCA9IHMxO1xuICAgICAgICAgIGlmIChzMCA9PT0gcGVnJEZBSUxFRCkge1xuICAgICAgICAgICAgczAgPSBwZWckY3VyclBvcztcbiAgICAgICAgICAgIGlmIChpbnB1dC5jaGFyQ29kZUF0KHBlZyRjdXJyUG9zKSA9PT0gMTE2KSB7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGMxMDQ7XG4gICAgICAgICAgICAgIHBlZyRjdXJyUG9zKys7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICBzMSA9IHBlZyRGQUlMRUQ7XG4gICAgICAgICAgICAgIGlmIChwZWckc2lsZW50RmFpbHMgPT09IDApIHsgcGVnJGZhaWwocGVnJGMxMDUpOyB9XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBpZiAoczEgIT09IHBlZyRGQUlMRUQpIHtcbiAgICAgICAgICAgICAgcGVnJHJlcG9ydGVkUG9zID0gczA7XG4gICAgICAgICAgICAgIHMxID0gcGVnJGMxMDYoKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIHMwID0gczE7XG4gICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICB9XG5cbiAgICAgIHJldHVybiBzMDtcbiAgICB9XG5cblxuICAgIGZ1bmN0aW9uIG9yKGZpcnN0LCBzZWNvbmQpIHtcbiAgICAgICAgLy8gQWRkIGV4cGxpY2l0IGZ1bmN0aW9uIG5hbWVzIHRvIGVhc2UgZGVidWdnaW5nLlxuICAgICAgICBmdW5jdGlvbiBvckZpbHRlcigpIHtcbiAgICAgICAgICAgIHJldHVybiBmaXJzdC5hcHBseSh0aGlzLCBhcmd1bWVudHMpIHx8IHNlY29uZC5hcHBseSh0aGlzLCBhcmd1bWVudHMpO1xuICAgICAgICB9XG4gICAgICAgIG9yRmlsdGVyLmRlc2MgPSBmaXJzdC5kZXNjICsgXCIgb3IgXCIgKyBzZWNvbmQuZGVzYztcbiAgICAgICAgcmV0dXJuIG9yRmlsdGVyO1xuICAgIH1cbiAgICBmdW5jdGlvbiBhbmQoZmlyc3QsIHNlY29uZCkge1xuICAgICAgICBmdW5jdGlvbiBhbmRGaWx0ZXIoKSB7XG4gICAgICAgICAgICByZXR1cm4gZmlyc3QuYXBwbHkodGhpcywgYXJndW1lbnRzKSAmJiBzZWNvbmQuYXBwbHkodGhpcywgYXJndW1lbnRzKTtcbiAgICAgICAgfVxuICAgICAgICBhbmRGaWx0ZXIuZGVzYyA9IGZpcnN0LmRlc2MgKyBcIiBhbmQgXCIgKyBzZWNvbmQuZGVzYztcbiAgICAgICAgcmV0dXJuIGFuZEZpbHRlcjtcbiAgICB9XG4gICAgZnVuY3Rpb24gbm90KGV4cHIpIHtcbiAgICAgICAgZnVuY3Rpb24gbm90RmlsdGVyKCkge1xuICAgICAgICAgICAgcmV0dXJuICFleHByLmFwcGx5KHRoaXMsIGFyZ3VtZW50cyk7XG4gICAgICAgIH1cbiAgICAgICAgbm90RmlsdGVyLmRlc2MgPSBcIm5vdCBcIiArIGV4cHIuZGVzYztcbiAgICAgICAgcmV0dXJuIG5vdEZpbHRlcjtcbiAgICB9XG4gICAgZnVuY3Rpb24gYmluZGluZyhleHByKSB7XG4gICAgICAgIGZ1bmN0aW9uIGJpbmRpbmdGaWx0ZXIoKSB7XG4gICAgICAgICAgICByZXR1cm4gZXhwci5hcHBseSh0aGlzLCBhcmd1bWVudHMpO1xuICAgICAgICB9XG4gICAgICAgIGJpbmRpbmdGaWx0ZXIuZGVzYyA9IFwiKFwiICsgZXhwci5kZXNjICsgXCIpXCI7XG4gICAgICAgIHJldHVybiBiaW5kaW5nRmlsdGVyO1xuICAgIH1cbiAgICBmdW5jdGlvbiB0cnVlRmlsdGVyKGZsb3cpIHtcbiAgICAgICAgcmV0dXJuIHRydWU7XG4gICAgfVxuICAgIHRydWVGaWx0ZXIuZGVzYyA9IFwidHJ1ZVwiO1xuICAgIGZ1bmN0aW9uIGZhbHNlRmlsdGVyKGZsb3cpIHtcbiAgICAgICAgcmV0dXJuIGZhbHNlO1xuICAgIH1cbiAgICBmYWxzZUZpbHRlci5kZXNjID0gXCJmYWxzZVwiO1xuXG4gICAgdmFyIEFTU0VUX1RZUEVTID0gW1xuICAgICAgICBuZXcgUmVnRXhwKFwidGV4dC9qYXZhc2NyaXB0XCIpLFxuICAgICAgICBuZXcgUmVnRXhwKFwiYXBwbGljYXRpb24veC1qYXZhc2NyaXB0XCIpLFxuICAgICAgICBuZXcgUmVnRXhwKFwiYXBwbGljYXRpb24vamF2YXNjcmlwdFwiKSxcbiAgICAgICAgbmV3IFJlZ0V4cChcInRleHQvY3NzXCIpLFxuICAgICAgICBuZXcgUmVnRXhwKFwiaW1hZ2UvLipcIiksXG4gICAgICAgIG5ldyBSZWdFeHAoXCJhcHBsaWNhdGlvbi94LXNob2Nrd2F2ZS1mbGFzaFwiKVxuICAgIF07XG4gICAgZnVuY3Rpb24gYXNzZXRGaWx0ZXIoZmxvdykge1xuICAgICAgICBpZiAoZmxvdy5yZXNwb25zZSkge1xuICAgICAgICAgICAgdmFyIGN0ID0gUmVzcG9uc2VVdGlscy5nZXRDb250ZW50VHlwZShmbG93LnJlc3BvbnNlKTtcbiAgICAgICAgICAgIHZhciBpID0gQVNTRVRfVFlQRVMubGVuZ3RoO1xuICAgICAgICAgICAgd2hpbGUgKGktLSkge1xuICAgICAgICAgICAgICAgIGlmIChBU1NFVF9UWVBFU1tpXS50ZXN0KGN0KSkge1xuICAgICAgICAgICAgICAgICAgICByZXR1cm4gdHJ1ZTtcbiAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICAgICAgcmV0dXJuIGZhbHNlO1xuICAgIH1cbiAgICBhc3NldEZpbHRlci5kZXNjID0gXCJpcyBhc3NldFwiO1xuICAgIGZ1bmN0aW9uIHJlc3BvbnNlQ29kZShjb2RlKXtcbiAgICAgICAgZnVuY3Rpb24gcmVzcG9uc2VDb2RlRmlsdGVyKGZsb3cpe1xuICAgICAgICAgICAgcmV0dXJuIGZsb3cucmVzcG9uc2UgJiYgZmxvdy5yZXNwb25zZS5jb2RlID09PSBjb2RlO1xuICAgICAgICB9XG4gICAgICAgIHJlc3BvbnNlQ29kZUZpbHRlci5kZXNjID0gXCJyZXNwLiBjb2RlIGlzIFwiICsgY29kZTtcbiAgICAgICAgcmV0dXJuIHJlc3BvbnNlQ29kZUZpbHRlcjtcbiAgICB9XG4gICAgZnVuY3Rpb24gZG9tYWluKHJlZ2V4KXtcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XG4gICAgICAgIGZ1bmN0aW9uIGRvbWFpbkZpbHRlcihmbG93KXtcbiAgICAgICAgICAgIHJldHVybiBmbG93LnJlcXVlc3QgJiYgcmVnZXgudGVzdChmbG93LnJlcXVlc3QuaG9zdCk7XG4gICAgICAgIH1cbiAgICAgICAgZG9tYWluRmlsdGVyLmRlc2MgPSBcImRvbWFpbiBtYXRjaGVzIFwiICsgcmVnZXg7XG4gICAgICAgIHJldHVybiBkb21haW5GaWx0ZXI7XG4gICAgfVxuICAgIGZ1bmN0aW9uIGVycm9yRmlsdGVyKGZsb3cpe1xuICAgICAgICByZXR1cm4gISFmbG93LmVycm9yO1xuICAgIH1cbiAgICBlcnJvckZpbHRlci5kZXNjID0gXCJoYXMgZXJyb3JcIjtcbiAgICBmdW5jdGlvbiBoZWFkZXIocmVnZXgpe1xuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcbiAgICAgICAgZnVuY3Rpb24gaGVhZGVyRmlsdGVyKGZsb3cpe1xuICAgICAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgICAgICAoZmxvdy5yZXF1ZXN0ICYmIFJlcXVlc3RVdGlscy5tYXRjaF9oZWFkZXIoZmxvdy5yZXF1ZXN0LCByZWdleCkpXG4gICAgICAgICAgICAgICAgfHxcbiAgICAgICAgICAgICAgICAoZmxvdy5yZXNwb25zZSAmJiBSZXNwb25zZVV0aWxzLm1hdGNoX2hlYWRlcihmbG93LnJlc3BvbnNlLCByZWdleCkpXG4gICAgICAgICAgICApO1xuICAgICAgICB9XG4gICAgICAgIGhlYWRlckZpbHRlci5kZXNjID0gXCJoZWFkZXIgbWF0Y2hlcyBcIiArIHJlZ2V4O1xuICAgICAgICByZXR1cm4gaGVhZGVyRmlsdGVyO1xuICAgIH1cbiAgICBmdW5jdGlvbiByZXF1ZXN0SGVhZGVyKHJlZ2V4KXtcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XG4gICAgICAgIGZ1bmN0aW9uIHJlcXVlc3RIZWFkZXJGaWx0ZXIoZmxvdyl7XG4gICAgICAgICAgICByZXR1cm4gKGZsb3cucmVxdWVzdCAmJiBSZXF1ZXN0VXRpbHMubWF0Y2hfaGVhZGVyKGZsb3cucmVxdWVzdCwgcmVnZXgpKTtcbiAgICAgICAgfVxuICAgICAgICByZXF1ZXN0SGVhZGVyRmlsdGVyLmRlc2MgPSBcInJlcS4gaGVhZGVyIG1hdGNoZXMgXCIgKyByZWdleDtcbiAgICAgICAgcmV0dXJuIHJlcXVlc3RIZWFkZXJGaWx0ZXI7XG4gICAgfVxuICAgIGZ1bmN0aW9uIHJlc3BvbnNlSGVhZGVyKHJlZ2V4KXtcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XG4gICAgICAgIGZ1bmN0aW9uIHJlc3BvbnNlSGVhZGVyRmlsdGVyKGZsb3cpe1xuICAgICAgICAgICAgcmV0dXJuIChmbG93LnJlc3BvbnNlICYmIFJlc3BvbnNlVXRpbHMubWF0Y2hfaGVhZGVyKGZsb3cucmVzcG9uc2UsIHJlZ2V4KSk7XG4gICAgICAgIH1cbiAgICAgICAgcmVzcG9uc2VIZWFkZXJGaWx0ZXIuZGVzYyA9IFwicmVzcC4gaGVhZGVyIG1hdGNoZXMgXCIgKyByZWdleDtcbiAgICAgICAgcmV0dXJuIHJlc3BvbnNlSGVhZGVyRmlsdGVyO1xuICAgIH1cbiAgICBmdW5jdGlvbiBtZXRob2QocmVnZXgpe1xuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcbiAgICAgICAgZnVuY3Rpb24gbWV0aG9kRmlsdGVyKGZsb3cpe1xuICAgICAgICAgICAgcmV0dXJuIGZsb3cucmVxdWVzdCAmJiByZWdleC50ZXN0KGZsb3cucmVxdWVzdC5tZXRob2QpO1xuICAgICAgICB9XG4gICAgICAgIG1ldGhvZEZpbHRlci5kZXNjID0gXCJtZXRob2QgbWF0Y2hlcyBcIiArIHJlZ2V4O1xuICAgICAgICByZXR1cm4gbWV0aG9kRmlsdGVyO1xuICAgIH1cbiAgICBmdW5jdGlvbiBub1Jlc3BvbnNlRmlsdGVyKGZsb3cpe1xuICAgICAgICByZXR1cm4gZmxvdy5yZXF1ZXN0ICYmICFmbG93LnJlc3BvbnNlO1xuICAgIH1cbiAgICBub1Jlc3BvbnNlRmlsdGVyLmRlc2MgPSBcImhhcyBubyByZXNwb25zZVwiO1xuICAgIGZ1bmN0aW9uIHJlc3BvbnNlRmlsdGVyKGZsb3cpe1xuICAgICAgICByZXR1cm4gISFmbG93LnJlc3BvbnNlO1xuICAgIH1cbiAgICByZXNwb25zZUZpbHRlci5kZXNjID0gXCJoYXMgcmVzcG9uc2VcIjtcblxuICAgIGZ1bmN0aW9uIGNvbnRlbnRUeXBlKHJlZ2V4KXtcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XG4gICAgICAgIGZ1bmN0aW9uIGNvbnRlbnRUeXBlRmlsdGVyKGZsb3cpe1xuICAgICAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgICAgICAoZmxvdy5yZXF1ZXN0ICYmIHJlZ2V4LnRlc3QoUmVxdWVzdFV0aWxzLmdldENvbnRlbnRUeXBlKGZsb3cucmVxdWVzdCkpKVxuICAgICAgICAgICAgICAgIHx8XG4gICAgICAgICAgICAgICAgKGZsb3cucmVzcG9uc2UgJiYgcmVnZXgudGVzdChSZXNwb25zZVV0aWxzLmdldENvbnRlbnRUeXBlKGZsb3cucmVzcG9uc2UpKSlcbiAgICAgICAgICAgICk7XG4gICAgICAgIH1cbiAgICAgICAgY29udGVudFR5cGVGaWx0ZXIuZGVzYyA9IFwiY29udGVudCB0eXBlIG1hdGNoZXMgXCIgKyByZWdleDtcbiAgICAgICAgcmV0dXJuIGNvbnRlbnRUeXBlRmlsdGVyO1xuICAgIH1cbiAgICBmdW5jdGlvbiByZXF1ZXN0Q29udGVudFR5cGUocmVnZXgpe1xuICAgICAgICByZWdleCA9IG5ldyBSZWdFeHAocmVnZXgsIFwiaVwiKTtcbiAgICAgICAgZnVuY3Rpb24gcmVxdWVzdENvbnRlbnRUeXBlRmlsdGVyKGZsb3cpe1xuICAgICAgICAgICAgcmV0dXJuIGZsb3cucmVxdWVzdCAmJiByZWdleC50ZXN0KFJlcXVlc3RVdGlscy5nZXRDb250ZW50VHlwZShmbG93LnJlcXVlc3QpKTtcbiAgICAgICAgfVxuICAgICAgICByZXF1ZXN0Q29udGVudFR5cGVGaWx0ZXIuZGVzYyA9IFwicmVxLiBjb250ZW50IHR5cGUgbWF0Y2hlcyBcIiArIHJlZ2V4O1xuICAgICAgICByZXR1cm4gcmVxdWVzdENvbnRlbnRUeXBlRmlsdGVyO1xuICAgIH1cbiAgICBmdW5jdGlvbiByZXNwb25zZUNvbnRlbnRUeXBlKHJlZ2V4KXtcbiAgICAgICAgcmVnZXggPSBuZXcgUmVnRXhwKHJlZ2V4LCBcImlcIik7XG4gICAgICAgIGZ1bmN0aW9uIHJlc3BvbnNlQ29udGVudFR5cGVGaWx0ZXIoZmxvdyl7XG4gICAgICAgICAgICByZXR1cm4gZmxvdy5yZXNwb25zZSAmJiByZWdleC50ZXN0KFJlc3BvbnNlVXRpbHMuZ2V0Q29udGVudFR5cGUoZmxvdy5yZXNwb25zZSkpO1xuICAgICAgICB9XG4gICAgICAgIHJlc3BvbnNlQ29udGVudFR5cGVGaWx0ZXIuZGVzYyA9IFwicmVzcC4gY29udGVudCB0eXBlIG1hdGNoZXMgXCIgKyByZWdleDtcbiAgICAgICAgcmV0dXJuIHJlc3BvbnNlQ29udGVudFR5cGVGaWx0ZXI7XG4gICAgfVxuICAgIGZ1bmN0aW9uIHVybChyZWdleCl7XG4gICAgICAgIHJlZ2V4ID0gbmV3IFJlZ0V4cChyZWdleCwgXCJpXCIpO1xuICAgICAgICBmdW5jdGlvbiB1cmxGaWx0ZXIoZmxvdyl7XG4gICAgICAgICAgICByZXR1cm4gZmxvdy5yZXF1ZXN0ICYmIHJlZ2V4LnRlc3QoUmVxdWVzdFV0aWxzLnByZXR0eV91cmwoZmxvdy5yZXF1ZXN0KSk7XG4gICAgICAgIH1cbiAgICAgICAgdXJsRmlsdGVyLmRlc2MgPSBcInVybCBtYXRjaGVzIFwiICsgcmVnZXg7XG4gICAgICAgIHJldHVybiB1cmxGaWx0ZXI7XG4gICAgfVxuXG5cbiAgICBwZWckcmVzdWx0ID0gcGVnJHN0YXJ0UnVsZUZ1bmN0aW9uKCk7XG5cbiAgICBpZiAocGVnJHJlc3VsdCAhPT0gcGVnJEZBSUxFRCAmJiBwZWckY3VyclBvcyA9PT0gaW5wdXQubGVuZ3RoKSB7XG4gICAgICByZXR1cm4gcGVnJHJlc3VsdDtcbiAgICB9IGVsc2Uge1xuICAgICAgaWYgKHBlZyRyZXN1bHQgIT09IHBlZyRGQUlMRUQgJiYgcGVnJGN1cnJQb3MgPCBpbnB1dC5sZW5ndGgpIHtcbiAgICAgICAgcGVnJGZhaWwoeyB0eXBlOiBcImVuZFwiLCBkZXNjcmlwdGlvbjogXCJlbmQgb2YgaW5wdXRcIiB9KTtcbiAgICAgIH1cblxuICAgICAgdGhyb3cgcGVnJGJ1aWxkRXhjZXB0aW9uKG51bGwsIHBlZyRtYXhGYWlsRXhwZWN0ZWQsIHBlZyRtYXhGYWlsUG9zKTtcbiAgICB9XG4gIH1cblxuICByZXR1cm4ge1xuICAgIFN5bnRheEVycm9yOiBTeW50YXhFcnJvcixcbiAgICBwYXJzZTogICAgICAgcGFyc2VcbiAgfTtcbn0pKCk7XG4vKiBqc2hpbnQgaWdub3JlOmVuZCAqL1xuXG5tb2R1bGUuZXhwb3J0cyA9IEZpbHQ7XG4iLCJ2YXIgXyA9IHJlcXVpcmUoXCJsb2Rhc2hcIik7XG5cbnZhciBfTWVzc2FnZVV0aWxzID0ge1xuICAgIGdldENvbnRlbnRUeXBlOiBmdW5jdGlvbiAobWVzc2FnZSkge1xuICAgICAgICByZXR1cm4gdGhpcy5nZXRfZmlyc3RfaGVhZGVyKG1lc3NhZ2UsIC9eQ29udGVudC1UeXBlJC9pKTtcbiAgICB9LFxuICAgIGdldF9maXJzdF9oZWFkZXI6IGZ1bmN0aW9uIChtZXNzYWdlLCByZWdleCkge1xuICAgICAgICAvL0ZJWE1FOiBDYWNoZSBJbnZhbGlkYXRpb24uXG4gICAgICAgIGlmICghbWVzc2FnZS5faGVhZGVyTG9va3VwcylcbiAgICAgICAgICAgIE9iamVjdC5kZWZpbmVQcm9wZXJ0eShtZXNzYWdlLCBcIl9oZWFkZXJMb29rdXBzXCIsIHtcbiAgICAgICAgICAgICAgICB2YWx1ZToge30sXG4gICAgICAgICAgICAgICAgY29uZmlndXJhYmxlOiBmYWxzZSxcbiAgICAgICAgICAgICAgICBlbnVtZXJhYmxlOiBmYWxzZSxcbiAgICAgICAgICAgICAgICB3cml0YWJsZTogZmFsc2VcbiAgICAgICAgICAgIH0pO1xuICAgICAgICBpZiAoIShyZWdleCBpbiBtZXNzYWdlLl9oZWFkZXJMb29rdXBzKSkge1xuICAgICAgICAgICAgdmFyIGhlYWRlcjtcbiAgICAgICAgICAgIGZvciAodmFyIGkgPSAwOyBpIDwgbWVzc2FnZS5oZWFkZXJzLmxlbmd0aDsgaSsrKSB7XG4gICAgICAgICAgICAgICAgaWYgKCEhbWVzc2FnZS5oZWFkZXJzW2ldWzBdLm1hdGNoKHJlZ2V4KSkge1xuICAgICAgICAgICAgICAgICAgICBoZWFkZXIgPSBtZXNzYWdlLmhlYWRlcnNbaV07XG4gICAgICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIG1lc3NhZ2UuX2hlYWRlckxvb2t1cHNbcmVnZXhdID0gaGVhZGVyID8gaGVhZGVyWzFdIDogdW5kZWZpbmVkO1xuICAgICAgICB9XG4gICAgICAgIHJldHVybiBtZXNzYWdlLl9oZWFkZXJMb29rdXBzW3JlZ2V4XTtcbiAgICB9LFxuICAgIG1hdGNoX2hlYWRlcjogZnVuY3Rpb24gKG1lc3NhZ2UsIHJlZ2V4KSB7XG4gICAgICAgIHZhciBoZWFkZXJzID0gbWVzc2FnZS5oZWFkZXJzO1xuICAgICAgICB2YXIgaSA9IGhlYWRlcnMubGVuZ3RoO1xuICAgICAgICB3aGlsZSAoaS0tKSB7XG4gICAgICAgICAgICBpZiAocmVnZXgudGVzdChoZWFkZXJzW2ldLmpvaW4oXCIgXCIpKSkge1xuICAgICAgICAgICAgICAgIHJldHVybiBoZWFkZXJzW2ldO1xuICAgICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICAgIHJldHVybiBmYWxzZTtcbiAgICB9XG59O1xuXG52YXIgZGVmYXVsdFBvcnRzID0ge1xuICAgIFwiaHR0cFwiOiA4MCxcbiAgICBcImh0dHBzXCI6IDQ0M1xufTtcblxudmFyIFJlcXVlc3RVdGlscyA9IF8uZXh0ZW5kKF9NZXNzYWdlVXRpbHMsIHtcbiAgICBwcmV0dHlfaG9zdDogZnVuY3Rpb24gKHJlcXVlc3QpIHtcbiAgICAgICAgLy9GSVhNRTogQWRkIGhvc3RoZWFkZXJcbiAgICAgICAgcmV0dXJuIHJlcXVlc3QuaG9zdDtcbiAgICB9LFxuICAgIHByZXR0eV91cmw6IGZ1bmN0aW9uIChyZXF1ZXN0KSB7XG4gICAgICAgIHZhciBwb3J0ID0gXCJcIjtcbiAgICAgICAgaWYgKGRlZmF1bHRQb3J0c1tyZXF1ZXN0LnNjaGVtZV0gIT09IHJlcXVlc3QucG9ydCkge1xuICAgICAgICAgICAgcG9ydCA9IFwiOlwiICsgcmVxdWVzdC5wb3J0O1xuICAgICAgICB9XG4gICAgICAgIHJldHVybiByZXF1ZXN0LnNjaGVtZSArIFwiOi8vXCIgKyB0aGlzLnByZXR0eV9ob3N0KHJlcXVlc3QpICsgcG9ydCArIHJlcXVlc3QucGF0aDtcbiAgICB9XG59KTtcblxudmFyIFJlc3BvbnNlVXRpbHMgPSBfLmV4dGVuZChfTWVzc2FnZVV0aWxzLCB7fSk7XG5cblxubW9kdWxlLmV4cG9ydHMgPSB7XG4gICAgUmVzcG9uc2VVdGlsczogUmVzcG9uc2VVdGlscyxcbiAgICBSZXF1ZXN0VXRpbHM6IFJlcXVlc3RVdGlsc1xuXG59IiwiXG52YXIgXyA9IHJlcXVpcmUoXCJsb2Rhc2hcIik7XG52YXIgJCA9IHJlcXVpcmUoXCJqcXVlcnlcIik7XG52YXIgRXZlbnRFbWl0dGVyID0gcmVxdWlyZSgnZXZlbnRzJykuRXZlbnRFbWl0dGVyO1xuXG52YXIgdXRpbHMgPSByZXF1aXJlKFwiLi4vdXRpbHMuanNcIik7XG52YXIgYWN0aW9ucyA9IHJlcXVpcmUoXCIuLi9hY3Rpb25zLmpzXCIpO1xudmFyIGRpc3BhdGNoZXIgPSByZXF1aXJlKFwiLi4vZGlzcGF0Y2hlci5qc1wiKTtcblxuXG5mdW5jdGlvbiBMaXN0U3RvcmUoKSB7XG4gICAgRXZlbnRFbWl0dGVyLmNhbGwodGhpcyk7XG4gICAgdGhpcy5yZXNldCgpO1xufVxuXy5leHRlbmQoTGlzdFN0b3JlLnByb3RvdHlwZSwgRXZlbnRFbWl0dGVyLnByb3RvdHlwZSwge1xuICAgIGFkZDogZnVuY3Rpb24gKGVsZW0pIHtcbiAgICAgICAgaWYgKGVsZW0uaWQgaW4gdGhpcy5fcG9zX21hcCkge1xuICAgICAgICAgICAgcmV0dXJuO1xuICAgICAgICB9XG4gICAgICAgIHRoaXMuX3Bvc19tYXBbZWxlbS5pZF0gPSB0aGlzLmxpc3QubGVuZ3RoO1xuICAgICAgICB0aGlzLmxpc3QucHVzaChlbGVtKTtcbiAgICAgICAgdGhpcy5lbWl0KFwiYWRkXCIsIGVsZW0pO1xuICAgIH0sXG4gICAgdXBkYXRlOiBmdW5jdGlvbiAoZWxlbSkge1xuICAgICAgICBpZiAoIShlbGVtLmlkIGluIHRoaXMuX3Bvc19tYXApKSB7XG4gICAgICAgICAgICByZXR1cm47XG4gICAgICAgIH1cbiAgICAgICAgdGhpcy5saXN0W3RoaXMuX3Bvc19tYXBbZWxlbS5pZF1dID0gZWxlbTtcbiAgICAgICAgdGhpcy5lbWl0KFwidXBkYXRlXCIsIGVsZW0pO1xuICAgIH0sXG4gICAgcmVtb3ZlOiBmdW5jdGlvbiAoZWxlbV9pZCkge1xuICAgICAgICBpZiAoIShlbGVtX2lkIGluIHRoaXMuX3Bvc19tYXApKSB7XG4gICAgICAgICAgICByZXR1cm47XG4gICAgICAgIH1cbiAgICAgICAgdGhpcy5saXN0LnNwbGljZSh0aGlzLl9wb3NfbWFwW2VsZW1faWRdLCAxKTtcbiAgICAgICAgdGhpcy5fYnVpbGRfbWFwKCk7XG4gICAgICAgIHRoaXMuZW1pdChcInJlbW92ZVwiLCBlbGVtX2lkKTtcbiAgICB9LFxuICAgIHJlc2V0OiBmdW5jdGlvbiAoZWxlbXMpIHtcbiAgICAgICAgdGhpcy5saXN0ID0gZWxlbXMgfHwgW107XG4gICAgICAgIHRoaXMuX2J1aWxkX21hcCgpO1xuICAgICAgICB0aGlzLmVtaXQoXCJyZWNhbGN1bGF0ZVwiKTtcbiAgICB9LFxuICAgIF9idWlsZF9tYXA6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5fcG9zX21hcCA9IHt9O1xuICAgICAgICBmb3IgKHZhciBpID0gMDsgaSA8IHRoaXMubGlzdC5sZW5ndGg7IGkrKykge1xuICAgICAgICAgICAgdmFyIGVsZW0gPSB0aGlzLmxpc3RbaV07XG4gICAgICAgICAgICB0aGlzLl9wb3NfbWFwW2VsZW0uaWRdID0gaTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgZ2V0OiBmdW5jdGlvbiAoZWxlbV9pZCkge1xuICAgICAgICByZXR1cm4gdGhpcy5saXN0W3RoaXMuX3Bvc19tYXBbZWxlbV9pZF1dO1xuICAgIH0sXG4gICAgaW5kZXg6IGZ1bmN0aW9uIChlbGVtX2lkKSB7XG4gICAgICAgIHJldHVybiB0aGlzLl9wb3NfbWFwW2VsZW1faWRdO1xuICAgIH1cbn0pO1xuXG5cbmZ1bmN0aW9uIERpY3RTdG9yZSgpIHtcbiAgICBFdmVudEVtaXR0ZXIuY2FsbCh0aGlzKTtcbiAgICB0aGlzLnJlc2V0KCk7XG59XG5fLmV4dGVuZChEaWN0U3RvcmUucHJvdG90eXBlLCBFdmVudEVtaXR0ZXIucHJvdG90eXBlLCB7XG4gICAgdXBkYXRlOiBmdW5jdGlvbiAoZGljdCkge1xuICAgICAgICBfLm1lcmdlKHRoaXMuZGljdCwgZGljdCk7XG4gICAgICAgIHRoaXMuZW1pdChcInJlY2FsY3VsYXRlXCIpO1xuICAgIH0sXG4gICAgcmVzZXQ6IGZ1bmN0aW9uIChkaWN0KSB7XG4gICAgICAgIHRoaXMuZGljdCA9IGRpY3QgfHwge307XG4gICAgICAgIHRoaXMuZW1pdChcInJlY2FsY3VsYXRlXCIpO1xuICAgIH1cbn0pO1xuXG5mdW5jdGlvbiBMaXZlU3RvcmVNaXhpbih0eXBlKSB7XG4gICAgdGhpcy50eXBlID0gdHlwZTtcblxuICAgIHRoaXMuX3VwZGF0ZXNfYmVmb3JlX2ZldGNoID0gdW5kZWZpbmVkO1xuICAgIHRoaXMuX2ZldGNoeGhyID0gZmFsc2U7XG5cbiAgICB0aGlzLmhhbmRsZSA9IHRoaXMuaGFuZGxlLmJpbmQodGhpcyk7XG4gICAgZGlzcGF0Y2hlci5BcHBEaXNwYXRjaGVyLnJlZ2lzdGVyKHRoaXMuaGFuZGxlKTtcblxuICAgIC8vIEF2b2lkIGRvdWJsZS1mZXRjaCBvbiBzdGFydHVwLlxuICAgIGlmICghKHdpbmRvdy53cyAmJiB3aW5kb3cud3MucmVhZHlTdGF0ZSA9PT0gV2ViU29ja2V0LkNPTk5FQ1RJTkcpKSB7XG4gICAgICAgIHRoaXMuZmV0Y2goKTtcbiAgICB9XG59XG5fLmV4dGVuZChMaXZlU3RvcmVNaXhpbi5wcm90b3R5cGUsIHtcbiAgICBoYW5kbGU6IGZ1bmN0aW9uIChldmVudCkge1xuICAgICAgICBpZiAoZXZlbnQudHlwZSA9PT0gYWN0aW9ucy5BY3Rpb25UeXBlcy5DT05ORUNUSU9OX09QRU4pIHtcbiAgICAgICAgICAgIHJldHVybiB0aGlzLmZldGNoKCk7XG4gICAgICAgIH1cbiAgICAgICAgaWYgKGV2ZW50LnR5cGUgPT09IHRoaXMudHlwZSkge1xuICAgICAgICAgICAgaWYgKGV2ZW50LmNtZCA9PT0gYWN0aW9ucy5TdG9yZUNtZHMuUkVTRVQpIHtcbiAgICAgICAgICAgICAgICB0aGlzLmZldGNoKGV2ZW50LmRhdGEpO1xuICAgICAgICAgICAgfSBlbHNlIGlmICh0aGlzLl91cGRhdGVzX2JlZm9yZV9mZXRjaCkge1xuICAgICAgICAgICAgICAgIGNvbnNvbGUubG9nKFwiZGVmZXIgdXBkYXRlXCIsIGV2ZW50KTtcbiAgICAgICAgICAgICAgICB0aGlzLl91cGRhdGVzX2JlZm9yZV9mZXRjaC5wdXNoKGV2ZW50KTtcbiAgICAgICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICAgICAgdGhpc1tldmVudC5jbWRdKGV2ZW50LmRhdGEpO1xuICAgICAgICAgICAgfVxuICAgICAgICB9XG4gICAgfSxcbiAgICBjbG9zZTogZnVuY3Rpb24gKCkge1xuICAgICAgICBkaXNwYXRjaGVyLkFwcERpc3BhdGNoZXIudW5yZWdpc3Rlcih0aGlzLmhhbmRsZSk7XG4gICAgfSxcbiAgICBmZXRjaDogZnVuY3Rpb24gKGRhdGEpIHtcbiAgICAgICAgY29uc29sZS5sb2coXCJmZXRjaCBcIiArIHRoaXMudHlwZSk7XG4gICAgICAgIGlmICh0aGlzLl9mZXRjaHhocikge1xuICAgICAgICAgICAgdGhpcy5fZmV0Y2h4aHIuYWJvcnQoKTtcbiAgICAgICAgfVxuICAgICAgICB0aGlzLl91cGRhdGVzX2JlZm9yZV9mZXRjaCA9IFtdOyAvLyAoSlM6IGVtcHR5IGFycmF5IGlzIHRydWUpXG4gICAgICAgIGlmIChkYXRhKSB7XG4gICAgICAgICAgICB0aGlzLmhhbmRsZV9mZXRjaChkYXRhKTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIHRoaXMuX2ZldGNoeGhyID0gJC5nZXRKU09OKFwiL1wiICsgdGhpcy50eXBlKVxuICAgICAgICAgICAgICAgIC5kb25lKGZ1bmN0aW9uIChtZXNzYWdlKSB7XG4gICAgICAgICAgICAgICAgICAgIHRoaXMuaGFuZGxlX2ZldGNoKG1lc3NhZ2UuZGF0YSk7XG4gICAgICAgICAgICAgICAgfS5iaW5kKHRoaXMpKVxuICAgICAgICAgICAgICAgIC5mYWlsKGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgICAgICAgICAgRXZlbnRMb2dBY3Rpb25zLmFkZF9ldmVudChcIkNvdWxkIG5vdCBmZXRjaCBcIiArIHRoaXMudHlwZSk7XG4gICAgICAgICAgICAgICAgfS5iaW5kKHRoaXMpKTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgaGFuZGxlX2ZldGNoOiBmdW5jdGlvbiAoZGF0YSkge1xuICAgICAgICB0aGlzLl9mZXRjaHhociA9IGZhbHNlO1xuICAgICAgICBjb25zb2xlLmxvZyh0aGlzLnR5cGUgKyBcIiBmZXRjaGVkLlwiLCB0aGlzLl91cGRhdGVzX2JlZm9yZV9mZXRjaCk7XG4gICAgICAgIHRoaXMucmVzZXQoZGF0YSk7XG4gICAgICAgIHZhciB1cGRhdGVzID0gdGhpcy5fdXBkYXRlc19iZWZvcmVfZmV0Y2g7XG4gICAgICAgIHRoaXMuX3VwZGF0ZXNfYmVmb3JlX2ZldGNoID0gZmFsc2U7XG4gICAgICAgIGZvciAodmFyIGkgPSAwOyBpIDwgdXBkYXRlcy5sZW5ndGg7IGkrKykge1xuICAgICAgICAgICAgdGhpcy5oYW5kbGUodXBkYXRlc1tpXSk7XG4gICAgICAgIH1cbiAgICB9LFxufSk7XG5cbmZ1bmN0aW9uIExpdmVMaXN0U3RvcmUodHlwZSkge1xuICAgIExpc3RTdG9yZS5jYWxsKHRoaXMpO1xuICAgIExpdmVTdG9yZU1peGluLmNhbGwodGhpcywgdHlwZSk7XG59XG5fLmV4dGVuZChMaXZlTGlzdFN0b3JlLnByb3RvdHlwZSwgTGlzdFN0b3JlLnByb3RvdHlwZSwgTGl2ZVN0b3JlTWl4aW4ucHJvdG90eXBlKTtcblxuZnVuY3Rpb24gTGl2ZURpY3RTdG9yZSh0eXBlKSB7XG4gICAgRGljdFN0b3JlLmNhbGwodGhpcyk7XG4gICAgTGl2ZVN0b3JlTWl4aW4uY2FsbCh0aGlzLCB0eXBlKTtcbn1cbl8uZXh0ZW5kKExpdmVEaWN0U3RvcmUucHJvdG90eXBlLCBEaWN0U3RvcmUucHJvdG90eXBlLCBMaXZlU3RvcmVNaXhpbi5wcm90b3R5cGUpO1xuXG5cbmZ1bmN0aW9uIEZsb3dTdG9yZSgpIHtcbiAgICByZXR1cm4gbmV3IExpdmVMaXN0U3RvcmUoYWN0aW9ucy5BY3Rpb25UeXBlcy5GTE9XX1NUT1JFKTtcbn1cblxuZnVuY3Rpb24gU2V0dGluZ3NTdG9yZSgpIHtcbiAgICByZXR1cm4gbmV3IExpdmVEaWN0U3RvcmUoYWN0aW9ucy5BY3Rpb25UeXBlcy5TRVRUSU5HU19TVE9SRSk7XG59XG5cbmZ1bmN0aW9uIEV2ZW50TG9nU3RvcmUoKSB7XG4gICAgTGl2ZUxpc3RTdG9yZS5jYWxsKHRoaXMsIGFjdGlvbnMuQWN0aW9uVHlwZXMuRVZFTlRfU1RPUkUpO1xufVxuXy5leHRlbmQoRXZlbnRMb2dTdG9yZS5wcm90b3R5cGUsIExpdmVMaXN0U3RvcmUucHJvdG90eXBlLCB7XG4gICAgZmV0Y2g6IGZ1bmN0aW9uKCl7XG4gICAgICAgIExpdmVMaXN0U3RvcmUucHJvdG90eXBlLmZldGNoLmFwcGx5KHRoaXMsIGFyZ3VtZW50cyk7XG5cbiAgICAgICAgLy8gTWFrZSBzdXJlIHRvIGRpc3BsYXkgdXBkYXRlcyBldmVuIGlmIGZldGNoaW5nIGFsbCBldmVudHMgZmFpbGVkLlxuICAgICAgICAvLyBUaGlzIHdheSwgd2UgY2FuIHNlbmQgXCJmZXRjaCBmYWlsZWRcIiBsb2cgbWVzc2FnZXMgdG8gdGhlIGxvZy5cbiAgICAgICAgaWYodGhpcy5fZmV0Y2h4aHIpe1xuICAgICAgICAgICAgdGhpcy5fZmV0Y2h4aHIuZmFpbChmdW5jdGlvbigpe1xuICAgICAgICAgICAgICAgIHRoaXMuaGFuZGxlX2ZldGNoKG51bGwpO1xuICAgICAgICAgICAgfS5iaW5kKHRoaXMpKTtcbiAgICAgICAgfVxuICAgIH1cbn0pO1xuXG5cbm1vZHVsZS5leHBvcnRzID0ge1xuICAgIEV2ZW50TG9nU3RvcmU6IEV2ZW50TG9nU3RvcmUsXG4gICAgU2V0dGluZ3NTdG9yZTogU2V0dGluZ3NTdG9yZSxcbiAgICBGbG93U3RvcmU6IEZsb3dTdG9yZVxufTsiLCJcbnZhciBFdmVudEVtaXR0ZXIgPSByZXF1aXJlKCdldmVudHMnKS5FdmVudEVtaXR0ZXI7XG52YXIgXyA9IHJlcXVpcmUoXCJsb2Rhc2hcIik7XG5cblxudmFyIHV0aWxzID0gcmVxdWlyZShcIi4uL3V0aWxzLmpzXCIpO1xuXG5mdW5jdGlvbiBTb3J0QnlTdG9yZU9yZGVyKGVsZW0pIHtcbiAgICByZXR1cm4gdGhpcy5zdG9yZS5pbmRleChlbGVtLmlkKTtcbn1cblxudmFyIGRlZmF1bHRfc29ydCA9IFNvcnRCeVN0b3JlT3JkZXI7XG52YXIgZGVmYXVsdF9maWx0ID0gZnVuY3Rpb24oZWxlbSl7XG4gICAgcmV0dXJuIHRydWU7XG59O1xuXG5mdW5jdGlvbiBTdG9yZVZpZXcoc3RvcmUsIGZpbHQsIHNvcnRmdW4pIHtcbiAgICBFdmVudEVtaXR0ZXIuY2FsbCh0aGlzKTtcbiAgICBmaWx0ID0gZmlsdCB8fCBkZWZhdWx0X2ZpbHQ7XG4gICAgc29ydGZ1biA9IHNvcnRmdW4gfHwgZGVmYXVsdF9zb3J0O1xuXG4gICAgdGhpcy5zdG9yZSA9IHN0b3JlO1xuXG4gICAgdGhpcy5hZGQgPSB0aGlzLmFkZC5iaW5kKHRoaXMpO1xuICAgIHRoaXMudXBkYXRlID0gdGhpcy51cGRhdGUuYmluZCh0aGlzKTtcbiAgICB0aGlzLnJlbW92ZSA9IHRoaXMucmVtb3ZlLmJpbmQodGhpcyk7XG4gICAgdGhpcy5yZWNhbGN1bGF0ZSA9IHRoaXMucmVjYWxjdWxhdGUuYmluZCh0aGlzKTtcbiAgICB0aGlzLnN0b3JlLmFkZExpc3RlbmVyKFwiYWRkXCIsIHRoaXMuYWRkKTtcbiAgICB0aGlzLnN0b3JlLmFkZExpc3RlbmVyKFwidXBkYXRlXCIsIHRoaXMudXBkYXRlKTtcbiAgICB0aGlzLnN0b3JlLmFkZExpc3RlbmVyKFwicmVtb3ZlXCIsIHRoaXMucmVtb3ZlKTtcbiAgICB0aGlzLnN0b3JlLmFkZExpc3RlbmVyKFwicmVjYWxjdWxhdGVcIiwgdGhpcy5yZWNhbGN1bGF0ZSk7XG5cbiAgICB0aGlzLnJlY2FsY3VsYXRlKGZpbHQsIHNvcnRmdW4pO1xufVxuXG5fLmV4dGVuZChTdG9yZVZpZXcucHJvdG90eXBlLCBFdmVudEVtaXR0ZXIucHJvdG90eXBlLCB7XG4gICAgY2xvc2U6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5zdG9yZS5yZW1vdmVMaXN0ZW5lcihcImFkZFwiLCB0aGlzLmFkZCk7XG4gICAgICAgIHRoaXMuc3RvcmUucmVtb3ZlTGlzdGVuZXIoXCJ1cGRhdGVcIiwgdGhpcy51cGRhdGUpO1xuICAgICAgICB0aGlzLnN0b3JlLnJlbW92ZUxpc3RlbmVyKFwicmVtb3ZlXCIsIHRoaXMucmVtb3ZlKTtcbiAgICAgICAgdGhpcy5zdG9yZS5yZW1vdmVMaXN0ZW5lcihcInJlY2FsY3VsYXRlXCIsIHRoaXMucmVjYWxjdWxhdGUpO1xuICAgICAgICB9LFxuICAgICAgICByZWNhbGN1bGF0ZTogZnVuY3Rpb24gKGZpbHQsIHNvcnRmdW4pIHtcbiAgICAgICAgaWYgKGZpbHQpIHtcbiAgICAgICAgICAgIHRoaXMuZmlsdCA9IGZpbHQuYmluZCh0aGlzKTtcbiAgICAgICAgfVxuICAgICAgICBpZiAoc29ydGZ1bikge1xuICAgICAgICAgICAgdGhpcy5zb3J0ZnVuID0gc29ydGZ1bi5iaW5kKHRoaXMpO1xuICAgICAgICB9XG5cbiAgICAgICAgdGhpcy5saXN0ID0gdGhpcy5zdG9yZS5saXN0LmZpbHRlcih0aGlzLmZpbHQpO1xuICAgICAgICB0aGlzLmxpc3Quc29ydChmdW5jdGlvbiAoYSwgYikge1xuICAgICAgICAgICAgcmV0dXJuIHRoaXMuc29ydGZ1bihhKSAtIHRoaXMuc29ydGZ1bihiKTtcbiAgICAgICAgfS5iaW5kKHRoaXMpKTtcbiAgICAgICAgdGhpcy5lbWl0KFwicmVjYWxjdWxhdGVcIik7XG4gICAgfSxcbiAgICBpbmRleDogZnVuY3Rpb24gKGVsZW0pIHtcbiAgICAgICAgcmV0dXJuIF8uc29ydGVkSW5kZXgodGhpcy5saXN0LCBlbGVtLCB0aGlzLnNvcnRmdW4pO1xuICAgIH0sXG4gICAgYWRkOiBmdW5jdGlvbiAoZWxlbSkge1xuICAgICAgICBpZiAodGhpcy5maWx0KGVsZW0pKSB7XG4gICAgICAgICAgICB2YXIgaWR4ID0gdGhpcy5pbmRleChlbGVtKTtcbiAgICAgICAgICAgIGlmIChpZHggPT09IHRoaXMubGlzdC5sZW5ndGgpIHsgLy9oYXBwZW5zIG9mdGVuLCAucHVzaCBpcyB3YXkgZmFzdGVyLlxuICAgICAgICAgICAgICAgIHRoaXMubGlzdC5wdXNoKGVsZW0pO1xuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICB0aGlzLmxpc3Quc3BsaWNlKGlkeCwgMCwgZWxlbSk7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgICB0aGlzLmVtaXQoXCJhZGRcIiwgZWxlbSwgaWR4KTtcbiAgICAgICAgfVxuICAgIH0sXG4gICAgdXBkYXRlOiBmdW5jdGlvbiAoZWxlbSkge1xuICAgICAgICB2YXIgaWR4O1xuICAgICAgICB2YXIgaSA9IHRoaXMubGlzdC5sZW5ndGg7XG4gICAgICAgIC8vIFNlYXJjaCBmcm9tIHRoZSBiYWNrLCB3ZSB1c3VhbGx5IHVwZGF0ZSB0aGUgbGF0ZXN0IGVudHJpZXMuXG4gICAgICAgIHdoaWxlIChpLS0pIHtcbiAgICAgICAgICAgIGlmICh0aGlzLmxpc3RbaV0uaWQgPT09IGVsZW0uaWQpIHtcbiAgICAgICAgICAgICAgICBpZHggPSBpO1xuICAgICAgICAgICAgICAgIGJyZWFrO1xuICAgICAgICAgICAgfVxuICAgICAgICB9XG5cbiAgICAgICAgaWYgKGlkeCA9PT0gLTEpIHsgLy9ub3QgY29udGFpbmVkIGluIGxpc3RcbiAgICAgICAgICAgIHRoaXMuYWRkKGVsZW0pO1xuICAgICAgICB9IGVsc2UgaWYgKCF0aGlzLmZpbHQoZWxlbSkpIHtcbiAgICAgICAgICAgIHRoaXMucmVtb3ZlKGVsZW0uaWQpO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgaWYgKHRoaXMuc29ydGZ1bih0aGlzLmxpc3RbaWR4XSkgIT09IHRoaXMuc29ydGZ1bihlbGVtKSkgeyAvL3NvcnRwb3MgaGFzIGNoYW5nZWRcbiAgICAgICAgICAgICAgICB0aGlzLnJlbW92ZSh0aGlzLmxpc3RbaWR4XSk7XG4gICAgICAgICAgICAgICAgdGhpcy5hZGQoZWxlbSk7XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHRoaXMubGlzdFtpZHhdID0gZWxlbTtcbiAgICAgICAgICAgICAgICB0aGlzLmVtaXQoXCJ1cGRhdGVcIiwgZWxlbSwgaWR4KTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgIH0sXG4gICAgcmVtb3ZlOiBmdW5jdGlvbiAoZWxlbV9pZCkge1xuICAgICAgICB2YXIgaWR4ID0gdGhpcy5saXN0Lmxlbmd0aDtcbiAgICAgICAgd2hpbGUgKGlkeC0tKSB7XG4gICAgICAgICAgICBpZiAodGhpcy5saXN0W2lkeF0uaWQgPT09IGVsZW1faWQpIHtcbiAgICAgICAgICAgICAgICB0aGlzLmxpc3Quc3BsaWNlKGlkeCwgMSk7XG4gICAgICAgICAgICAgICAgdGhpcy5lbWl0KFwicmVtb3ZlXCIsIGVsZW1faWQsIGlkeCk7XG4gICAgICAgICAgICAgICAgYnJlYWs7XG4gICAgICAgICAgICB9XG4gICAgICAgIH1cbiAgICB9XG59KTtcblxubW9kdWxlLmV4cG9ydHMgPSB7XG4gICAgU3RvcmVWaWV3OiBTdG9yZVZpZXdcbn07IiwidmFyICQgPSByZXF1aXJlKFwianF1ZXJ5XCIpO1xuXG5cbnZhciBLZXkgPSB7XG4gICAgVVA6IDM4LFxuICAgIERPV046IDQwLFxuICAgIFBBR0VfVVA6IDMzLFxuICAgIFBBR0VfRE9XTjogMzQsXG4gICAgSE9NRTogMzYsXG4gICAgRU5EOiAzNSxcbiAgICBMRUZUOiAzNyxcbiAgICBSSUdIVDogMzksXG4gICAgRU5URVI6IDEzLFxuICAgIEVTQzogMjcsXG4gICAgVEFCOiA5LFxuICAgIFNQQUNFOiAzMixcbiAgICBCQUNLU1BBQ0U6IDgsXG59O1xuLy8gQWRkIEEtWlxuZm9yICh2YXIgaSA9IDY1OyBpIDw9IDkwOyBpKyspIHtcbiAgICBLZXlbU3RyaW5nLmZyb21DaGFyQ29kZShpKV0gPSBpO1xufVxuXG5cbnZhciBmb3JtYXRTaXplID0gZnVuY3Rpb24gKGJ5dGVzKSB7XG4gICAgdmFyIHNpemUgPSBieXRlcztcbiAgICB2YXIgcHJlZml4ID0gW1wiQlwiLCBcIktCXCIsIFwiTUJcIiwgXCJHQlwiLCBcIlRCXCJdO1xuICAgIHZhciBpID0gMDtcbiAgICB3aGlsZSAoTWF0aC5hYnMoc2l6ZSkgPj0gMTAyNCAmJiBpIDwgcHJlZml4Lmxlbmd0aCAtIDEpIHtcbiAgICAgICAgaSsrO1xuICAgICAgICBzaXplID0gc2l6ZSAvIDEwMjQ7XG4gICAgfVxuICAgIHJldHVybiAoTWF0aC5mbG9vcihzaXplICogMTAwKSAvIDEwMC4wKS50b0ZpeGVkKDIpICsgcHJlZml4W2ldO1xufTtcblxuXG52YXIgZm9ybWF0VGltZURlbHRhID0gZnVuY3Rpb24gKG1pbGxpc2Vjb25kcykge1xuICAgIHZhciB0aW1lID0gbWlsbGlzZWNvbmRzO1xuICAgIHZhciBwcmVmaXggPSBbXCJtc1wiLCBcInNcIiwgXCJtaW5cIiwgXCJoXCJdO1xuICAgIHZhciBkaXYgPSBbMTAwMCwgNjAsIDYwXTtcbiAgICB2YXIgaSA9IDA7XG4gICAgd2hpbGUgKE1hdGguYWJzKHRpbWUpID49IGRpdltpXSAmJiBpIDwgZGl2Lmxlbmd0aCkge1xuICAgICAgICB0aW1lID0gdGltZSAvIGRpdltpXTtcbiAgICAgICAgaSsrO1xuICAgIH1cbiAgICByZXR1cm4gTWF0aC5yb3VuZCh0aW1lKSArIHByZWZpeFtpXTtcbn07XG5cblxudmFyIGZvcm1hdFRpbWVTdGFtcCA9IGZ1bmN0aW9uIChzZWNvbmRzKSB7XG4gICAgdmFyIHRzID0gKG5ldyBEYXRlKHNlY29uZHMgKiAxMDAwKSkudG9JU09TdHJpbmcoKTtcbiAgICByZXR1cm4gdHMucmVwbGFjZShcIlRcIiwgXCIgXCIpLnJlcGxhY2UoXCJaXCIsIFwiXCIpO1xufTtcblxuXG5mdW5jdGlvbiBnZXRDb29raWUobmFtZSkge1xuICAgIHZhciByID0gZG9jdW1lbnQuY29va2llLm1hdGNoKFwiXFxcXGJcIiArIG5hbWUgKyBcIj0oW147XSopXFxcXGJcIik7XG4gICAgcmV0dXJuIHIgPyByWzFdIDogdW5kZWZpbmVkO1xufVxudmFyIHhzcmYgPSAkLnBhcmFtKHtfeHNyZjogZ2V0Q29va2llKFwiX3hzcmZcIil9KTtcblxuLy9Ub3JuYWRvIFhTUkYgUHJvdGVjdGlvbi5cbiQuYWpheFByZWZpbHRlcihmdW5jdGlvbiAob3B0aW9ucykge1xuICAgIGlmIChbXCJwb3N0XCIsIFwicHV0XCIsIFwiZGVsZXRlXCJdLmluZGV4T2Yob3B0aW9ucy50eXBlLnRvTG93ZXJDYXNlKCkpID49IDAgJiYgb3B0aW9ucy51cmxbMF0gPT09IFwiL1wiKSB7XG4gICAgICAgIGlmIChvcHRpb25zLmRhdGEpIHtcbiAgICAgICAgICAgIG9wdGlvbnMuZGF0YSArPSAoXCImXCIgKyB4c3JmKTtcbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIG9wdGlvbnMuZGF0YSA9IHhzcmY7XG4gICAgICAgIH1cbiAgICB9XG59KTtcbi8vIExvZyBBSkFYIEVycm9yc1xuJChkb2N1bWVudCkuYWpheEVycm9yKGZ1bmN0aW9uIChldmVudCwganFYSFIsIGFqYXhTZXR0aW5ncywgdGhyb3duRXJyb3IpIHtcbiAgICB2YXIgbWVzc2FnZSA9IGpxWEhSLnJlc3BvbnNlVGV4dDtcbiAgICBjb25zb2xlLmVycm9yKG1lc3NhZ2UsIGFyZ3VtZW50cyk7XG4gICAgRXZlbnRMb2dBY3Rpb25zLmFkZF9ldmVudCh0aHJvd25FcnJvciArIFwiOiBcIiArIG1lc3NhZ2UpO1xuICAgIHdpbmRvdy5hbGVydChtZXNzYWdlKTtcbn0pO1xuXG5tb2R1bGUuZXhwb3J0cyA9IHtcbiAgICBmb3JtYXRTaXplOiBmb3JtYXRTaXplLFxuICAgIGZvcm1hdFRpbWVEZWx0YTogZm9ybWF0VGltZURlbHRhLFxuICAgIGZvcm1hdFRpbWVTdGFtcDogZm9ybWF0VGltZVN0YW1wLFxuICAgIEtleTogS2V5XG59OyJdfQ==
