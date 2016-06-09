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
        args = Array.prototype.slice.call(arguments, 1);
        handler.apply(this, args);
    }
  } else if (isObject(handler)) {
    args = Array.prototype.slice.call(arguments, 1);
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
  } else if (listeners) {
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

EventEmitter.prototype.listenerCount = function(type) {
  if (this._events) {
    var evlistener = this._events[type];

    if (isFunction(evlistener))
      return 1;
    else if (evlistener)
      return evlistener.length;
  }
  return 0;
};

EventEmitter.listenerCount = function(emitter, type) {
  return emitter.listenerCount(type);
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
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.Query = exports.FlowActions = exports.SettingsActions = exports.ConnectionActions = exports.StoreCmds = exports.ActionTypes = undefined;

var _jquery = require("jquery");

var _jquery2 = _interopRequireDefault(_jquery);

var _dispatcher = require("./dispatcher.js");

var _utils = require("./utils.js");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var ActionTypes = exports.ActionTypes = {
    // Connection
    CONNECTION_OPEN: "connection_open",
    CONNECTION_CLOSE: "connection_close",
    CONNECTION_ERROR: "connection_error",

    // Stores
    SETTINGS_STORE: "settings",
    EVENT_STORE: "events",
    FLOW_STORE: "flows"
};

var StoreCmds = exports.StoreCmds = {
    ADD: "add",
    UPDATE: "update",
    REMOVE: "remove",
    RESET: "reset"
};

var ConnectionActions = exports.ConnectionActions = {
    open: function open() {
        _dispatcher.AppDispatcher.dispatchViewAction({
            type: ActionTypes.CONNECTION_OPEN
        });
    },
    close: function close() {
        _dispatcher.AppDispatcher.dispatchViewAction({
            type: ActionTypes.CONNECTION_CLOSE
        });
    },
    error: function error() {
        _dispatcher.AppDispatcher.dispatchViewAction({
            type: ActionTypes.CONNECTION_ERROR
        });
    }
};

var SettingsActions = exports.SettingsActions = {
    update: function update(settings) {

        _jquery2.default.ajax({
            type: "PUT",
            url: "/settings",
            contentType: 'application/json',
            data: JSON.stringify(settings)
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

var FlowActions = exports.FlowActions = {
    accept: function accept(flow) {
        _jquery2.default.post("/flows/" + flow.id + "/accept");
    },
    accept_all: function accept_all() {
        _jquery2.default.post("/flows/accept");
    },
    "delete": function _delete(flow) {
        _jquery2.default.ajax({
            type: "DELETE",
            url: "/flows/" + flow.id
        });
    },
    duplicate: function duplicate(flow) {
        _jquery2.default.post("/flows/" + flow.id + "/duplicate");
    },
    replay: function replay(flow) {
        _jquery2.default.post("/flows/" + flow.id + "/replay");
    },
    revert: function revert(flow) {
        _jquery2.default.post("/flows/" + flow.id + "/revert");
    },
    update: function update(flow, nextProps) {
        /*
        //Facebook Flux: We do an optimistic update on the client already.
        var nextFlow = _.cloneDeep(flow);
        _.merge(nextFlow, nextProps);
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.FLOW_STORE,
            cmd: StoreCmds.UPDATE,
            data: nextFlow
        });
        */
        _jquery2.default.ajax({
            type: "PUT",
            url: "/flows/" + flow.id,
            contentType: 'application/json',
            data: JSON.stringify(nextProps)
        });
    },
    clear: function clear() {
        _jquery2.default.post("/clear");
    },
    download: function download() {
        return window.location = "/flows/dump";
    },

    upload: function upload(file) {
        var data = new FormData();
        data.append('file', file);
        (0, _utils.fetchApi)("/flows/dump", {
            method: 'post',
            body: data
        });
    }
};

var Query = exports.Query = {
    SEARCH: "s",
    HIGHLIGHT: "h",
    SHOW_EVENTLOG: "e"
};

},{"./dispatcher.js":22,"./utils.js":32,"jquery":"jquery"}],3:[function(require,module,exports){
'use strict';

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactDom = require('react-dom');

var _redux = require('redux');

var _reactRedux = require('react-redux');

var _reduxLogger = require('redux-logger');

var _reduxLogger2 = _interopRequireDefault(_reduxLogger);

var _reduxThunk = require('redux-thunk');

var _reduxThunk2 = _interopRequireDefault(_reduxThunk);

var _reactRouter = require('react-router');

var _connection = require('./connection');

var _connection2 = _interopRequireDefault(_connection);

var _ProxyApp = require('./components/ProxyApp');

var _ProxyApp2 = _interopRequireDefault(_ProxyApp);

var _MainView = require('./components/MainView');

var _MainView2 = _interopRequireDefault(_MainView);

var _index = require('./ducks/index');

var _index2 = _interopRequireDefault(_index);

var _eventLog = require('./ducks/eventLog');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

// logger must be last
var store = (0, _redux.createStore)(_index2.default, (0, _redux.applyMiddleware)(_reduxThunk2.default, (0, _reduxLogger2.default)()));

window.addEventListener('error', function (msg) {
    store.dispatch((0, _eventLog.addLogEntry)(msg));
});

// @todo remove this
document.addEventListener('DOMContentLoaded', function () {
    window.ws = new _connection2.default("/updates", store.dispatch);

    (0, _reactDom.render)(_react2.default.createElement(
        _reactRedux.Provider,
        { store: store },
        _react2.default.createElement(
            _reactRouter.Router,
            { history: _reactRouter.hashHistory },
            _react2.default.createElement(_reactRouter.Redirect, { from: '/', to: '/flows' }),
            _react2.default.createElement(
                _reactRouter.Route,
                { path: '/', component: _ProxyApp2.default },
                _react2.default.createElement(_reactRouter.Route, { path: 'flows', component: _MainView2.default }),
                _react2.default.createElement(_reactRouter.Route, { path: 'flows/:flowId/:detailTab', component: _MainView2.default })
            )
        )
    ), document.getElementById("mitmproxy"));
});

},{"./components/MainView":4,"./components/ProxyApp":5,"./connection":21,"./ducks/eventLog":23,"./ducks/index":25,"react":"react","react-dom":"react-dom","react-redux":"react-redux","react-router":"react-router","redux":"redux","redux-logger":"redux-logger","redux-thunk":"redux-thunk"}],4:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _actions = require("../actions.js");

var _utils = require("../utils.js");

var _common = require("./common.js");

var _flowtable = require("./flowtable.js");

var _flowtable2 = _interopRequireDefault(_flowtable);

var _index = require("./flowview/index.js");

var _index2 = _interopRequireDefault(_index);

var _reactRedux = require("react-redux");

var _flows = require("../ducks/flows");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var MainView = function (_Component) {
    _inherits(MainView, _Component);

    function MainView() {
        _classCallCheck(this, MainView);

        return _possibleConstructorReturn(this, Object.getPrototypeOf(MainView).apply(this, arguments));
    }

    _createClass(MainView, [{
        key: "componentWillReceiveProps",


        /**
         * @todo move to actions
         * @todo replace with mapStateToProps
         */
        value: function componentWillReceiveProps(nextProps) {
            // Update redux store with route changes
            if (nextProps.routeParams.flowId !== (nextProps.selectedFlow || {}).id) {
                this.props.selectFlow(nextProps.routeParams.flowId);
            }
            if (nextProps.location.query[_actions.Query.SEARCH] !== nextProps.filter) {
                this.props.setFilter(nextProps.location.query[_actions.Query.SEARCH], false);
            }
            if (nextProps.location.query[_actions.Query.HIGHLIGHT] !== nextProps.highlight) {
                this.props.setHighlight(nextProps.location.query[_actions.Query.HIGHLIGHT], false);
            }
        }

        /**
         * @todo move to actions
         */

    }, {
        key: "selectFlow",
        value: function selectFlow(flow) {
            if (flow) {
                this.props.updateLocation("/flows/" + flow.id + "/" + (this.props.routeParams.detailTab || "request"));
            } else {
                this.props.updateLocation("/flows");
            }
        }

        /**
         * @todo move to actions
         */

    }, {
        key: "selectFlowRelative",
        value: function selectFlowRelative(shift) {
            var _props = this.props;
            var flows = _props.flows;
            var routeParams = _props.routeParams;
            var selectedFlow = _props.selectedFlow;

            var index = 0;
            if (!routeParams.flowId) {
                if (shift < 0) {
                    index = flows.length - 1;
                }
            } else {
                index = Math.min(Math.max(0, flows.indexOf(selectedFlow) + shift), flows.length - 1);
            }
            this.selectFlow(flows[index]);
        }

        /**
         * @todo move to actions
         */

    }, {
        key: "onMainKeyDown",
        value: function onMainKeyDown(e) {
            var flow = this.props.selectedFlow;
            if (e.ctrlKey) {
                return;
            }
            switch (e.keyCode) {
                case _utils.Key.K:
                case _utils.Key.UP:
                    this.selectFlowRelative(-1);
                    break;
                case _utils.Key.J:
                case _utils.Key.DOWN:
                    this.selectFlowRelative(+1);
                    break;
                case _utils.Key.SPACE:
                case _utils.Key.PAGE_DOWN:
                    this.selectFlowRelative(+10);
                    break;
                case _utils.Key.PAGE_UP:
                    this.selectFlowRelative(-10);
                    break;
                case _utils.Key.END:
                    this.selectFlowRelative(+1e10);
                    break;
                case _utils.Key.HOME:
                    this.selectFlowRelative(-1e10);
                    break;
                case _utils.Key.ESC:
                    this.selectFlow(null);
                    break;
                case _utils.Key.H:
                case _utils.Key.LEFT:
                    if (this.refs.flowDetails) {
                        this.refs.flowDetails.nextTab(-1);
                    }
                    break;
                case _utils.Key.L:
                case _utils.Key.TAB:
                case _utils.Key.RIGHT:
                    if (this.refs.flowDetails) {
                        this.refs.flowDetails.nextTab(+1);
                    }
                    break;
                case _utils.Key.C:
                    if (e.shiftKey) {
                        _actions.FlowActions.clear();
                    }
                    break;
                case _utils.Key.D:
                    if (flow) {
                        if (e.shiftKey) {
                            _actions.FlowActions.duplicate(flow);
                        } else {
                            _actions.FlowActions.delete(flow);
                        }
                    }
                    break;
                case _utils.Key.A:
                    if (e.shiftKey) {
                        _actions.FlowActions.accept_all();
                    } else if (flow && flow.intercepted) {
                        _actions.FlowActions.accept(flow);
                    }
                    break;
                case _utils.Key.R:
                    if (!e.shiftKey && flow) {
                        _actions.FlowActions.replay(flow);
                    }
                    break;
                case _utils.Key.V:
                    if (e.shiftKey && flow && flow.modified) {
                        _actions.FlowActions.revert(flow);
                    }
                    break;
                case _utils.Key.E:
                    if (this.refs.flowDetails) {
                        this.refs.flowDetails.promptEdit();
                    }
                    break;
                case _utils.Key.SHIFT:
                    break;
                default:
                    console.debug("keydown", e.keyCode);
                    return;
            }
            e.preventDefault();
        }
    }, {
        key: "render",
        value: function render() {
            var _this2 = this;

            var selectedFlow = this.props.selectedFlow;

            return _react2.default.createElement(
                "div",
                { className: "main-view" },
                _react2.default.createElement(_flowtable2.default, {
                    ref: "flowTable",
                    selectFlow: function selectFlow(flow) {
                        return _this2.selectFlow(flow);
                    },
                    selected: selectedFlow
                }),
                selectedFlow && [_react2.default.createElement(_common.Splitter, { key: "splitter" }), _react2.default.createElement(_index2.default, {
                    key: "flowDetails",
                    ref: "flowDetails",
                    tab: this.props.routeParams.detailTab,
                    query: this.props.query,
                    updateLocation: this.props.updateLocation,
                    flow: selectedFlow
                })]
            );
        }
    }]);

    return MainView;
}(_react.Component);

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        flows: state.flows.view,
        filter: state.flows.filter,
        highlight: state.flows.highlight,
        selectedFlow: state.flows.all.byId[state.flows.selected[0]]
    };
}, function (dispatch) {
    return {
        selectFlow: function selectFlow(flowId) {
            return dispatch((0, _flows.selectFlow)(flowId));
        },
        setFilter: function setFilter(filter) {
            return dispatch((0, _flows.setFilter)(filter));
        },
        setHighlight: function setHighlight(highlight) {
            return dispatch((0, _flows.setHighlight)(highlight));
        }
    };
}, undefined, { withRef: true })(MainView);

},{"../actions.js":2,"../ducks/flows":24,"../utils.js":32,"./common.js":6,"./flowtable.js":10,"./flowview/index.js":13,"react":"react","react-redux":"react-redux"}],5:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _reactDom = require("react-dom");

var _reactDom2 = _interopRequireDefault(_reactDom);

var _lodash = require("lodash");

var _lodash2 = _interopRequireDefault(_lodash);

var _reactRedux = require("react-redux");

var _common = require("./common.js");

var _header = require("./header.js");

var _eventlog = require("./eventlog.js");

var _eventlog2 = _interopRequireDefault(_eventlog);

var _footer = require("./footer.js");

var _footer2 = _interopRequireDefault(_footer);

var _store = require("../store/store.js");

var _utils = require("../utils.js");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var ProxyAppMain = function (_Component) {
    _inherits(ProxyAppMain, _Component);

    function ProxyAppMain(props, context) {
        _classCallCheck(this, ProxyAppMain);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(ProxyAppMain).call(this, props, context));

        _this.settingsStore = new _store.SettingsStore();

        // Default Settings before fetch
        _lodash2.default.extend(_this.settingsStore.dict, {});

        _this.state = { settings: _this.settingsStore.dict };

        _this.onKeyDown = _this.onKeyDown.bind(_this);
        _this.updateLocation = _this.updateLocation.bind(_this);
        _this.onSettingsChange = _this.onSettingsChange.bind(_this);
        return _this;
    }

    /**
     * @todo move to actions
     */


    _createClass(ProxyAppMain, [{
        key: "updateLocation",
        value: function updateLocation(pathname, queryUpdate) {
            if (pathname === undefined) {
                pathname = this.props.location.pathname;
            }
            var query = this.props.location.query;
            var _iteratorNormalCompletion = true;
            var _didIteratorError = false;
            var _iteratorError = undefined;

            try {
                for (var _iterator = Object.keys(queryUpdate || {})[Symbol.iterator](), _step; !(_iteratorNormalCompletion = (_step = _iterator.next()).done); _iteratorNormalCompletion = true) {
                    var key = _step.value;

                    query[i] = queryUpdate[i] || undefined;
                }
            } catch (err) {
                _didIteratorError = true;
                _iteratorError = err;
            } finally {
                try {
                    if (!_iteratorNormalCompletion && _iterator.return) {
                        _iterator.return();
                    }
                } finally {
                    if (_didIteratorError) {
                        throw _iteratorError;
                    }
                }
            }

            this.context.router.replace({ pathname: pathname, query: query });
        }

        /**
         * @todo pass in with props
         */

    }, {
        key: "getQuery",
        value: function getQuery() {
            // For whatever reason, react-router always returns the same object, which makes comparing
            // the current props with nextProps impossible. As a workaround, we just clone the query object.
            return _lodash2.default.clone(this.props.location.query);
        }

        /**
         * @todo remove settings store
         * @todo connect websocket here
         * @todo listen to window's key events
         */

    }, {
        key: "componentDidMount",
        value: function componentDidMount() {
            this.focus();
            this.settingsStore.addListener("recalculate", this.onSettingsChange);
        }

        /**
         * @todo remove settings store
         * @todo disconnect websocket here
         * @todo stop listening to window's key events
         */

    }, {
        key: "componentWillUnmount",
        value: function componentWillUnmount() {
            this.settingsStore.removeListener("recalculate", this.onSettingsChange);
        }

        /**
         * @todo move to actions
         */

    }, {
        key: "onSettingsChange",
        value: function onSettingsChange() {
            this.setState({ settings: this.settingsStore.dict });
        }

        /**
         * @todo use props
         */

    }, {
        key: "getChildContext",
        value: function getChildContext() {
            return {
                returnFocus: this.focus,
                location: this.props.location
            };
        }

        /**
         * @todo remove it
         */

    }, {
        key: "focus",
        value: function focus() {
            document.activeElement.blur();
            window.getSelection().removeAllRanges();
            _reactDom2.default.findDOMNode(this).focus();
        }

        /**
         * @todo move to actions
         */

    }, {
        key: "onKeyDown",
        value: function onKeyDown(e) {
            var _this2 = this;

            var name = null;

            switch (e.keyCode) {
                case _utils.Key.I:
                    name = "intercept";
                    break;
                case _utils.Key.L:
                    name = "search";
                    break;
                case _utils.Key.H:
                    name = "highlight";
                    break;
                default:
                    var main = this.refs.view;
                    if (this.refs.view.getWrappedInstance) {
                        main = this.refs.view.getWrappedInstance();
                    }
                    if (main.onMainKeyDown) {
                        main.onMainKeyDown(e);
                    }
                    return; // don't prevent default then
            }

            if (name) {
                (function () {
                    var headerComponent = _this2.refs.header;
                    headerComponent.setState({ active: _header.MainMenu }, function () {
                        headerComponent.refs.active.refs[name].select();
                    });
                })();
            }

            e.preventDefault();
        }
    }, {
        key: "render",
        value: function render() {
            var _props = this.props;
            var showEventLog = _props.showEventLog;
            var location = _props.location;
            var children = _props.children;
            var settings = this.state.settings;

            var query = this.getQuery();
            return _react2.default.createElement(
                "div",
                { id: "container", tabIndex: "0", onKeyDown: this.onKeyDown },
                _react2.default.createElement(_header.Header, { ref: "header", settings: settings, updateLocation: this.updateLocation, query: query }),
                _react2.default.cloneElement(children, { ref: "view", location: location, query: query, updateLocation: this.updateLocation }),
                showEventLog && [_react2.default.createElement(_common.Splitter, { key: "splitter", axis: "y" }), _react2.default.createElement(_eventlog2.default, { key: "eventlog" })],
                _react2.default.createElement(_footer2.default, { settings: settings })
            );
        }
    }]);

    return ProxyAppMain;
}(_react.Component);

ProxyAppMain.childContextTypes = {
    returnFocus: _react.PropTypes.func.isRequired,
    location: _react.PropTypes.object.isRequired
};
ProxyAppMain.contextTypes = {
    router: _react.PropTypes.object.isRequired
};
exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        showEventLog: state.eventLog.visible
    };
})(ProxyAppMain);

},{"../store/store.js":31,"../utils.js":32,"./common.js":6,"./eventlog.js":8,"./footer.js":16,"./header.js":17,"lodash":"lodash","react":"react","react-dom":"react-dom","react-redux":"react-redux"}],6:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.ToggleInputButton = exports.ToggleButton = exports.Splitter = undefined;

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _reactDom = require("react-dom");

var _reactDom2 = _interopRequireDefault(_reactDom);

var _utils = require("../utils.js");

var _lodash = require("lodash");

var _lodash2 = _interopRequireDefault(_lodash);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var Splitter = exports.Splitter = _react2.default.createClass({
    displayName: "Splitter",

    getDefaultProps: function getDefaultProps() {
        return {
            axis: "x"
        };
    },
    getInitialState: function getInitialState() {
        return {
            applied: false,
            startX: false,
            startY: false
        };
    },
    onMouseDown: function onMouseDown(e) {
        this.setState({
            startX: e.pageX,
            startY: e.pageY
        });
        window.addEventListener("mousemove", this.onMouseMove);
        window.addEventListener("mouseup", this.onMouseUp);
        // Occasionally, only a dragEnd event is triggered, but no mouseUp.
        window.addEventListener("dragend", this.onDragEnd);
    },
    onDragEnd: function onDragEnd() {
        _reactDom2.default.findDOMNode(this).style.transform = "";
        window.removeEventListener("dragend", this.onDragEnd);
        window.removeEventListener("mouseup", this.onMouseUp);
        window.removeEventListener("mousemove", this.onMouseMove);
    },
    onMouseUp: function onMouseUp(e) {
        this.onDragEnd();

        var node = _reactDom2.default.findDOMNode(this);
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
    onMouseMove: function onMouseMove(e) {
        var dX = 0,
            dY = 0;
        if (this.props.axis === "x") {
            dX = e.pageX - this.state.startX;
        } else {
            dY = e.pageY - this.state.startY;
        }
        _reactDom2.default.findDOMNode(this).style.transform = "translate(" + dX + "px," + dY + "px)";
    },
    onResize: function onResize() {
        // Trigger a global resize event. This notifies components that employ virtual scrolling
        // that their viewport may have changed.
        window.setTimeout(function () {
            window.dispatchEvent(new CustomEvent("resize"));
        }, 1);
    },
    reset: function reset(willUnmount) {
        if (!this.state.applied) {
            return;
        }
        var node = _reactDom2.default.findDOMNode(this);
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
    componentWillUnmount: function componentWillUnmount() {
        this.reset(true);
    },
    render: function render() {
        var className = "splitter";
        if (this.props.axis === "x") {
            className += " splitter-x";
        } else {
            className += " splitter-y";
        }
        return _react2.default.createElement(
            "div",
            { className: className },
            _react2.default.createElement("div", { onMouseDown: this.onMouseDown, draggable: "true" })
        );
    }
});

var ToggleButton = exports.ToggleButton = function ToggleButton(_ref) {
    var checked = _ref.checked;
    var onToggle = _ref.onToggle;
    var text = _ref.text;
    return _react2.default.createElement(
        "div",
        { className: "btn btn-toggle " + (checked ? "btn-primary" : "btn-default"), onClick: onToggle },
        _react2.default.createElement("i", { className: "fa fa-fw " + (checked ? "fa-check-square-o" : "fa-square-o") }),
        " ",
        text
    );
};

ToggleButton.propTypes = {
    checked: _react2.default.PropTypes.bool.isRequired,
    onToggle: _react2.default.PropTypes.func.isRequired,
    text: _react2.default.PropTypes.string.isRequired
};

var ToggleInputButton = exports.ToggleInputButton = function (_React$Component) {
    _inherits(ToggleInputButton, _React$Component);

    function ToggleInputButton(props) {
        _classCallCheck(this, ToggleInputButton);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(ToggleInputButton).call(this, props));

        _this.state = { txt: props.txt };
        return _this;
    }

    _createClass(ToggleInputButton, [{
        key: "render",
        value: function render() {
            var _this2 = this;

            return _react2.default.createElement(
                "div",
                { className: "input-group toggle-input-btn" },
                _react2.default.createElement(
                    "span",
                    {
                        className: "input-group-btn",
                        onClick: function onClick() {
                            return _this2.props.onToggleChanged(_this2.state.txt);
                        } },
                    _react2.default.createElement(
                        "div",
                        { className: "btn  " + (this.props.checked ? "btn-primary" : "btn-default") },
                        _react2.default.createElement("span", { className: "fa " + (this.props.checked ? "fa-check-square-o" : "fa-square-o") }),
                        " ",
                        this.props.name
                    )
                ),
                _react2.default.createElement("input", {
                    className: "form-control",
                    placeholder: this.props.placeholder,
                    disabled: this.props.checked,
                    value: this.state.txt,
                    type: this.props.inputType,
                    onChange: function onChange(e) {
                        return _this2.setState({ txt: e.target.value });
                    },
                    onKeyDown: function onKeyDown(e) {
                        if (e.keyCode === _utils.Key.ENTER) _this2.props.onToggleChanged(_this2.state.txt);e.stopPropagation();
                    } })
            );
        }
    }]);

    return ToggleInputButton;
}(_react2.default.Component);

ToggleInputButton.propTypes = {
    name: _react2.default.PropTypes.string.isRequired,
    txt: _react2.default.PropTypes.string.isRequired,
    onToggleChanged: _react2.default.PropTypes.func.isRequired
};

},{"../utils.js":32,"lodash":"lodash","react":"react","react-dom":"react-dom"}],7:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.ValueEditor = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _reactDom = require("react-dom");

var _reactDom2 = _interopRequireDefault(_reactDom);

var _utils = require("../utils.js");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var contentToHtml = function contentToHtml(content) {
    return _.escape(content);
};
var nodeToContent = function nodeToContent(node) {
    return node.textContent;
};

/*
 Basic Editor Functionality
 */
var EditorBase = _react2.default.createClass({
    displayName: "EditorBase",

    propTypes: {
        content: _react2.default.PropTypes.string.isRequired,
        onDone: _react2.default.PropTypes.func.isRequired,
        contentToHtml: _react2.default.PropTypes.func,
        nodeToContent: _react2.default.PropTypes.func, // content === nodeToContent( Node<innerHTML=contentToHtml(content)> )
        onStop: _react2.default.PropTypes.func,
        submitOnEnter: _react2.default.PropTypes.bool,
        className: _react2.default.PropTypes.string,
        tag: _react2.default.PropTypes.string
    },
    getDefaultProps: function getDefaultProps() {
        return {
            contentToHtml: contentToHtml,
            nodeToContent: nodeToContent,
            submitOnEnter: true,
            className: "",
            tag: "div"
        };
    },
    getInitialState: function getInitialState() {
        return {
            editable: false
        };
    },
    render: function render() {
        var className = "inline-input " + this.props.className;
        var html = { __html: this.props.contentToHtml(this.props.content) };
        var Tag = this.props.tag;
        return _react2.default.createElement(Tag, _extends({}, this.props, {
            tabIndex: "0",
            className: className,
            contentEditable: this.state.editable || undefined // workaround: use undef instead of false to remove attr
            , onFocus: this.onFocus,
            onMouseDown: this.onMouseDown,
            onClick: this.onClick,
            onBlur: this._stop,
            onKeyDown: this.onKeyDown,
            onInput: this.onInput,
            onPaste: this.onPaste,
            dangerouslySetInnerHTML: html
        }));
    },
    onPaste: function onPaste(e) {
        e.preventDefault();
        var content = e.clipboardData.getData("text/plain");
        document.execCommand("insertHTML", false, content);
    },
    onMouseDown: function onMouseDown(e) {
        this._mouseDown = true;
        window.addEventListener("mouseup", this.onMouseUp);
        this.props.onMouseDown && this.props.onMouseDown(e);
    },
    onMouseUp: function onMouseUp() {
        if (this._mouseDown) {
            this._mouseDown = false;
            window.removeEventListener("mouseup", this.onMouseUp);
        }
    },
    onClick: function onClick(e) {
        this.onMouseUp();
        this.onFocus(e);
    },
    onFocus: function onFocus(e) {
        console.log("onFocus", this._mouseDown, this._ignore_events, this.state.editable);
        if (this._mouseDown || this._ignore_events || this.state.editable) {
            return;
        }

        //contenteditable in FireFox is more or less broken.
        // - we need to blur() and then focus(), otherwise the caret is not shown.
        // - blur() + focus() == we need to save the caret position before
        //   Firefox sometimes just doesn't set a caret position => use caretPositionFromPoint
        var sel = window.getSelection();
        var range;
        if (sel.rangeCount > 0) {
            range = sel.getRangeAt(0);
        } else if (document.caretPositionFromPoint && e.clientX && e.clientY) {
            var pos = document.caretPositionFromPoint(e.clientX, e.clientY);
            range = document.createRange();
            range.setStart(pos.offsetNode, pos.offset);
        } else if (document.caretRangeFromPoint && e.clientX && e.clientY) {
            range = document.caretRangeFromPoint(e.clientX, e.clientY);
        } else {
            range = document.createRange();
            range.selectNodeContents(_reactDom2.default.findDOMNode(this));
        }

        this._ignore_events = true;
        this.setState({ editable: true }, function () {
            var node = _reactDom2.default.findDOMNode(this);
            node.blur();
            node.focus();
            this._ignore_events = false;
            //sel.removeAllRanges();
            //sel.addRange(range);
        });
    },
    stop: function stop() {
        // a stop would cause a blur as a side-effect.
        // but a blur event must trigger a stop as well.
        // to fix this, make stop = blur and do the actual stop in the onBlur handler.
        _reactDom2.default.findDOMNode(this).blur();
        this.props.onStop && this.props.onStop();
    },
    _stop: function _stop(e) {
        if (this._ignore_events) {
            return;
        }
        console.log("_stop", _.extend({}, e));
        window.getSelection().removeAllRanges(); //make sure that selection is cleared on blur
        var node = _reactDom2.default.findDOMNode(this);
        var content = this.props.nodeToContent(node);
        this.setState({ editable: false });
        this.props.onDone(content);
        this.props.onBlur && this.props.onBlur(e);
    },
    reset: function reset() {
        _reactDom2.default.findDOMNode(this).innerHTML = this.props.contentToHtml(this.props.content);
    },
    onKeyDown: function onKeyDown(e) {
        e.stopPropagation();
        switch (e.keyCode) {
            case _utils.Key.ESC:
                e.preventDefault();
                this.reset();
                this.stop();
                break;
            case _utils.Key.ENTER:
                if (this.props.submitOnEnter && !e.shiftKey) {
                    e.preventDefault();
                    this.stop();
                }
                break;
            default:
                break;
        }
    },
    onInput: function onInput() {
        var node = _reactDom2.default.findDOMNode(this);
        var content = this.props.nodeToContent(node);
        this.props.onInput && this.props.onInput(content);
    }
});

/*
 Add Validation to EditorBase
 */
var ValidateEditor = _react2.default.createClass({
    displayName: "ValidateEditor",

    propTypes: {
        content: _react2.default.PropTypes.string.isRequired,
        onDone: _react2.default.PropTypes.func.isRequired,
        onInput: _react2.default.PropTypes.func,
        isValid: _react2.default.PropTypes.func,
        className: _react2.default.PropTypes.string
    },
    getInitialState: function getInitialState() {
        return {
            currentContent: this.props.content
        };
    },
    componentWillReceiveProps: function componentWillReceiveProps() {
        this.setState({ currentContent: this.props.content });
    },
    onInput: function onInput(content) {
        this.setState({ currentContent: content });
        this.props.onInput && this.props.onInput(content);
    },
    render: function render() {
        var className = this.props.className || "";
        if (this.props.isValid) {
            if (this.props.isValid(this.state.currentContent)) {
                className += " has-success";
            } else {
                className += " has-warning";
            }
        }
        return _react2.default.createElement(EditorBase, _extends({}, this.props, {
            ref: "editor",
            className: className,
            onDone: this.onDone,
            onInput: this.onInput
        }));
    },
    onDone: function onDone(content) {
        if (this.props.isValid && !this.props.isValid(content)) {
            this.refs.editor.reset();
            content = this.props.content;
        }
        this.props.onDone(content);
    }
});

/*
 Text Editor with mitmweb-specific convenience features
 */
var ValueEditor = exports.ValueEditor = _react2.default.createClass({
    displayName: "ValueEditor",

    contextTypes: {
        returnFocus: _react2.default.PropTypes.func
    },
    propTypes: {
        content: _react2.default.PropTypes.string.isRequired,
        onDone: _react2.default.PropTypes.func.isRequired,
        inline: _react2.default.PropTypes.bool
    },
    render: function render() {
        var tag = this.props.inline ? "span" : "div";
        return _react2.default.createElement(ValidateEditor, _extends({}, this.props, {
            onStop: this.onStop,
            tag: tag
        }));
    },
    focus: function focus() {
        _reactDom2.default.findDOMNode(this).focus();
    },
    onStop: function onStop() {
        this.context.returnFocus();
    }
});

},{"../utils.js":32,"react":"react","react-dom":"react-dom"}],8:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.ToggleEventLog = undefined;

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _reactDom = require("react-dom");

var _reactDom2 = _interopRequireDefault(_reactDom);

var _reactRedux = require("react-redux");

var _shallowequal = require("shallowequal");

var _shallowequal2 = _interopRequireDefault(_shallowequal);

var _eventLog = require("../ducks/eventLog");

var _AutoScroll = require("./helpers/AutoScroll");

var _AutoScroll2 = _interopRequireDefault(_AutoScroll);

var _VirtualScroll = require("./helpers/VirtualScroll");

var _common = require("./common");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

function LogIcon(_ref) {
    var event = _ref.event;

    var icon = { web: "html5", debug: "bug" }[event.level] || "info";
    return _react2.default.createElement("i", { className: "fa fa-fw fa-" + icon });
}

function LogEntry(_ref2) {
    var event = _ref2.event;
    var registerHeight = _ref2.registerHeight;

    return _react2.default.createElement(
        "div",
        { ref: registerHeight },
        _react2.default.createElement(LogIcon, { event: event }),
        event.message
    );
}

var EventLogContents = function (_React$Component) {
    _inherits(EventLogContents, _React$Component);

    function EventLogContents(props) {
        _classCallCheck(this, EventLogContents);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(EventLogContents).call(this, props));

        _this.heights = {};
        _this.state = { vScroll: (0, _VirtualScroll.calcVScroll)() };

        _this.onViewportUpdate = _this.onViewportUpdate.bind(_this);
        return _this;
    }

    _createClass(EventLogContents, [{
        key: "componentDidMount",
        value: function componentDidMount() {
            window.addEventListener("resize", this.onViewportUpdate);
            this.onViewportUpdate();
        }
    }, {
        key: "componentWillUnmount",
        value: function componentWillUnmount() {
            window.removeEventListener("resize", this.onViewportUpdate);
        }
    }, {
        key: "componentDidUpdate",
        value: function componentDidUpdate() {
            this.onViewportUpdate();
        }
    }, {
        key: "onViewportUpdate",
        value: function onViewportUpdate() {
            var _this2 = this;

            var viewport = _reactDom2.default.findDOMNode(this);

            var vScroll = (0, _VirtualScroll.calcVScroll)({
                itemCount: this.props.events.length,
                rowHeight: this.props.rowHeight,
                viewportTop: viewport.scrollTop,
                viewportHeight: viewport.offsetHeight,
                itemHeights: this.props.events.map(function (entry) {
                    return _this2.heights[entry.id];
                })
            });

            if (!(0, _shallowequal2.default)(this.state.vScroll, vScroll)) {
                this.setState({ vScroll: vScroll });
            }
        }
    }, {
        key: "setHeight",
        value: function setHeight(id, node) {
            if (node && !this.heights[id]) {
                var height = node.offsetHeight;
                if (this.heights[id] !== height) {
                    this.heights[id] = height;
                    this.onViewportUpdate();
                }
            }
        }
    }, {
        key: "render",
        value: function render() {
            var _this3 = this;

            var vScroll = this.state.vScroll;
            var events = this.props.events.slice(vScroll.start, vScroll.end).map(function (event) {
                return _react2.default.createElement(LogEntry, {
                    event: event,
                    key: event.id,
                    registerHeight: function registerHeight(node) {
                        return _this3.setHeight(event.id, node);
                    }
                });
            });

            return _react2.default.createElement(
                "pre",
                { onScroll: this.onViewportUpdate },
                _react2.default.createElement("div", { style: { height: vScroll.paddingTop } }),
                events,
                _react2.default.createElement("div", { style: { height: vScroll.paddingBottom } })
            );
        }
    }]);

    return EventLogContents;
}(_react2.default.Component);

EventLogContents.defaultProps = {
    rowHeight: 18
};


EventLogContents = (0, _AutoScroll2.default)(EventLogContents);

var EventLogContentsContainer = (0, _reactRedux.connect)(function (state) {
    return {
        events: state.eventLog.filteredEvents
    };
})(EventLogContents);

var ToggleEventLog = exports.ToggleEventLog = (0, _reactRedux.connect)(function (state) {
    return {
        checked: state.eventLog.visible
    };
}, function (dispatch) {
    return {
        onToggle: function onToggle() {
            return dispatch((0, _eventLog.toggleEventLogVisibility)());
        }
    };
})(_common.ToggleButton);

var ToggleFilter = (0, _reactRedux.connect)(function (state, ownProps) {
    return {
        checked: state.eventLog.filter[ownProps.text]
    };
}, function (dispatch, ownProps) {
    return {
        onToggle: function onToggle() {
            return dispatch((0, _eventLog.toggleEventLogFilter)(ownProps.text));
        }
    };
})(_common.ToggleButton);

var EventLog = function EventLog(_ref3) {
    var close = _ref3.close;
    return _react2.default.createElement(
        "div",
        { className: "eventlog" },
        _react2.default.createElement(
            "div",
            null,
            "Eventlog",
            _react2.default.createElement(
                "div",
                { className: "pull-right" },
                _react2.default.createElement(ToggleFilter, { text: "debug" }),
                _react2.default.createElement(ToggleFilter, { text: "info" }),
                _react2.default.createElement(ToggleFilter, { text: "web" }),
                _react2.default.createElement("i", { onClick: close, className: "fa fa-close" })
            )
        ),
        _react2.default.createElement(EventLogContentsContainer, null)
    );
};

EventLog.propTypes = {
    close: _react2.default.PropTypes.func.isRequired
};

var EventLogContainer = (0, _reactRedux.connect)(undefined, function (dispatch) {
    return {
        close: function close() {
            return dispatch((0, _eventLog.toggleEventLogVisibility)());
        }
    };
})(EventLog);

exports.default = EventLogContainer;

},{"../ducks/eventLog":23,"./common":6,"./helpers/AutoScroll":18,"./helpers/VirtualScroll":19,"react":"react","react-dom":"react-dom","react-redux":"react-redux","shallowequal":"shallowequal"}],9:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.TLSColumn = TLSColumn;
exports.IconColumn = IconColumn;
exports.PathColumn = PathColumn;
exports.MethodColumn = MethodColumn;
exports.StatusColumn = StatusColumn;
exports.SizeColumn = SizeColumn;
exports.TimeColumn = TimeColumn;

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _utils = require("../flow/utils.js");

var _utils2 = require("../utils.js");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _objectWithoutProperties(obj, keys) { var target = {}; for (var i in obj) { if (keys.indexOf(i) >= 0) continue; if (!Object.prototype.hasOwnProperty.call(obj, i)) continue; target[i] = obj[i]; } return target; }

function TLSColumn(_ref) {
    var flow = _ref.flow;

    var ssl = flow.request.scheme === "https";
    var classes = void 0;
    if (ssl) {
        classes = "col-tls col-tls-https";
    } else {
        classes = "col-tls col-tls-http";
    }
    return _react2.default.createElement("td", { className: classes });
}
TLSColumn.Title = function (_ref2) {
    var _ref2$className = _ref2.className;
    var className = _ref2$className === undefined ? "" : _ref2$className;

    var props = _objectWithoutProperties(_ref2, ["className"]);

    return _react2.default.createElement("th", _extends({}, props, { className: "col-tls " + className }));
};
TLSColumn.sortKeyFun = function (flow) {
    return flow.request.scheme;
};

function IconColumn(_ref3) {
    var flow = _ref3.flow;

    var icon = void 0;
    if (flow.response) {
        var contentType = _utils.ResponseUtils.getContentType(flow.response);

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
    return _react2.default.createElement(
        "td",
        { className: "col-icon" },
        _react2.default.createElement("div", { className: icon })
    );
}
IconColumn.Title = function (_ref4) {
    var _ref4$className = _ref4.className;
    var className = _ref4$className === undefined ? "" : _ref4$className;

    var props = _objectWithoutProperties(_ref4, ["className"]);

    return _react2.default.createElement("th", _extends({}, props, { className: "col-icon " + className }));
};

function PathColumn(_ref5) {
    var flow = _ref5.flow;

    return _react2.default.createElement(
        "td",
        { className: "col-path" },
        flow.request.is_replay ? _react2.default.createElement("i", { className: "fa fa-fw fa-repeat pull-right" }) : null,
        flow.intercepted ? _react2.default.createElement("i", { className: "fa fa-fw fa-pause pull-right" }) : null,
        _utils.RequestUtils.pretty_url(flow.request)
    );
}
PathColumn.Title = function (_ref6) {
    var _ref6$className = _ref6.className;
    var className = _ref6$className === undefined ? "" : _ref6$className;

    var props = _objectWithoutProperties(_ref6, ["className"]);

    return _react2.default.createElement(
        "th",
        _extends({}, props, { className: "col-path " + className }),
        "Path"
    );
};
PathColumn.sortKeyFun = function (flow) {
    return _utils.RequestUtils.pretty_url(flow.request);
};

function MethodColumn(_ref7) {
    var flow = _ref7.flow;

    return _react2.default.createElement(
        "td",
        { className: "col-method" },
        flow.request.method
    );
}
MethodColumn.Title = function (_ref8) {
    var _ref8$className = _ref8.className;
    var className = _ref8$className === undefined ? "" : _ref8$className;

    var props = _objectWithoutProperties(_ref8, ["className"]);

    return _react2.default.createElement(
        "th",
        _extends({}, props, { className: "col-method " + className }),
        "Method"
    );
};
MethodColumn.sortKeyFun = function (flow) {
    return flow.request.method;
};

function StatusColumn(_ref9) {
    var flow = _ref9.flow;

    var status = void 0;
    if (flow.response) {
        status = flow.response.status_code;
    } else {
        status = null;
    }
    return _react2.default.createElement(
        "td",
        { className: "col-status" },
        status
    );
}
StatusColumn.Title = function (_ref10) {
    var _ref10$className = _ref10.className;
    var className = _ref10$className === undefined ? "" : _ref10$className;

    var props = _objectWithoutProperties(_ref10, ["className"]);

    return _react2.default.createElement(
        "th",
        _extends({}, props, { className: "col-status " + className }),
        "Status"
    );
};
StatusColumn.sortKeyFun = function (flow) {
    return flow.response ? flow.response.status_code : undefined;
};

function SizeColumn(_ref11) {
    var flow = _ref11.flow;

    var total = flow.request.contentLength;
    if (flow.response) {
        total += flow.response.contentLength || 0;
    }
    var size = (0, _utils2.formatSize)(total);
    return _react2.default.createElement(
        "td",
        { className: "col-size" },
        size
    );
}
SizeColumn.Title = function (_ref12) {
    var _ref12$className = _ref12.className;
    var className = _ref12$className === undefined ? "" : _ref12$className;

    var props = _objectWithoutProperties(_ref12, ["className"]);

    return _react2.default.createElement(
        "th",
        _extends({}, props, { className: "col-size " + className }),
        "Size"
    );
};
SizeColumn.sortKeyFun = function (flow) {
    var total = flow.request.contentLength;
    if (flow.response) {
        total += flow.response.contentLength || 0;
    }
    return total;
};

function TimeColumn(_ref13) {
    var flow = _ref13.flow;

    var time = void 0;
    if (flow.response) {
        time = (0, _utils2.formatTimeDelta)(1000 * (flow.response.timestamp_end - flow.request.timestamp_start));
    } else {
        time = "...";
    }
    return _react2.default.createElement(
        "td",
        { className: "col-time" },
        time
    );
}
TimeColumn.Title = function (_ref14) {
    var _ref14$className = _ref14.className;
    var className = _ref14$className === undefined ? "" : _ref14$className;

    var props = _objectWithoutProperties(_ref14, ["className"]);

    return _react2.default.createElement(
        "th",
        _extends({}, props, { className: "col-time " + className }),
        "Time"
    );
};
TimeColumn.sortKeyFun = function (flow) {
    return flow.response.timestamp_end - flow.request.timestamp_start;
};

var all_columns = [TLSColumn, IconColumn, PathColumn, MethodColumn, StatusColumn, SizeColumn, TimeColumn];

exports.default = all_columns;

},{"../flow/utils.js":30,"../utils.js":32,"react":"react"}],10:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _reactDom = require("react-dom");

var _reactDom2 = _interopRequireDefault(_reactDom);

var _reactRedux = require("react-redux");

var _classnames = require("classnames");

var _classnames2 = _interopRequireDefault(_classnames);

var _lodash = require("lodash");

var _lodash2 = _interopRequireDefault(_lodash);

var _shallowequal = require("shallowequal");

var _shallowequal2 = _interopRequireDefault(_shallowequal);

var _AutoScroll = require("./helpers/AutoScroll");

var _AutoScroll2 = _interopRequireDefault(_AutoScroll);

var _VirtualScroll = require("./helpers/VirtualScroll");

var _flowtableColumns = require("./flowtable-columns.js");

var _flowtableColumns2 = _interopRequireDefault(_flowtableColumns);

var _filt = require("../filt/filt");

var _filt2 = _interopRequireDefault(_filt);

var _flows = require("../ducks/flows");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

FlowRow.propTypes = {
    selectFlow: _react2.default.PropTypes.func.isRequired,
    columns: _react2.default.PropTypes.array.isRequired,
    flow: _react2.default.PropTypes.object.isRequired,
    highlight: _react2.default.PropTypes.string,
    selected: _react2.default.PropTypes.bool
};

function FlowRow(_ref) {
    var flow = _ref.flow;
    var selected = _ref.selected;
    var highlight = _ref.highlight;
    var columns = _ref.columns;
    var selectFlow = _ref.selectFlow;


    var className = (0, _classnames2.default)({
        "selected": selected,
        "highlighted": highlight && parseFilter(highlight)(flow),
        "intercepted": flow.intercepted,
        "has-request": flow.request,
        "has-response": flow.response
    });

    return _react2.default.createElement(
        "tr",
        { className: className, onClick: function onClick() {
                return selectFlow(flow);
            } },
        columns.map(function (Column) {
            return _react2.default.createElement(Column, { key: Column.name, flow: flow });
        })
    );
}

var FlowRowContainer = (0, _reactRedux.connect)(function (state, ownProps) {
    return {
        flow: state.flows.all.byId[ownProps.flowId],
        highlight: state.flows.highlight,
        selected: state.flows.selected.indexOf(ownProps.flowId) >= 0
    };
})(FlowRow);

function FlowTableHead(_ref2) {
    var setSort = _ref2.setSort;
    var columns = _ref2.columns;
    var sort = _ref2.sort;

    var sortColumn = sort.sortColumn;
    var sortType = sort.sortDesc ? "sort-desc" : "sort-asc";

    return _react2.default.createElement(
        "tr",
        null,
        columns.map(function (Column) {
            return _react2.default.createElement(Column.Title, {
                key: Column.name,
                onClick: function onClick() {
                    return setSort({ sortColumn: Column.name, sortDesc: Column.name != sort.sortColumn ? false : !sort.sortDesc });
                },
                className: sortColumn === Column.name ? sortType : undefined
            });
        })
    );
}

FlowTableHead.propTypes = {
    setSort: _react2.default.PropTypes.func.isRequired,
    sort: _react2.default.PropTypes.object.isRequired,
    columns: _react2.default.PropTypes.array.isRequired
};

var FlowTableHeadContainer = (0, _reactRedux.connect)(function (state) {
    return {
        sort: state.flows.sort
    };
}, function (dispatch) {
    return {
        setSort: function setSort(sort) {
            return dispatch((0, _flows.setSort)(sort));
        }
    };
})(FlowTableHead);

var FlowTable = function (_React$Component) {
    _inherits(FlowTable, _React$Component);

    function FlowTable(props, context) {
        _classCallCheck(this, FlowTable);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(FlowTable).call(this, props, context));

        _this.state = { vScroll: (0, _VirtualScroll.calcVScroll)() };

        _this.onViewportUpdate = _this.onViewportUpdate.bind(_this);
        return _this;
    }

    _createClass(FlowTable, [{
        key: "componentWillMount",
        value: function componentWillMount() {
            window.addEventListener("resize", this.onViewportUpdate);
        }
    }, {
        key: "componentWillUnmount",
        value: function componentWillUnmount() {
            window.removeEventListener("resize", this.onViewportUpdate);
        }
    }, {
        key: "componentWillReceiveProps",
        value: function componentWillReceiveProps(nextProps) {
            var _this2 = this;

            if (nextProps.selected && nextProps.selected !== this.props.selected) {
                window.setTimeout(function () {
                    return _this2.scrollIntoView(nextProps.selected);
                }, 1);
            }
        }
    }, {
        key: "componentDidUpdate",
        value: function componentDidUpdate() {
            this.onViewportUpdate();
        }
    }, {
        key: "onViewportUpdate",
        value: function onViewportUpdate() {
            var viewport = _reactDom2.default.findDOMNode(this);
            var viewportTop = viewport.scrollTop;

            var vScroll = (0, _VirtualScroll.calcVScroll)({
                viewportTop: viewportTop,
                viewportHeight: viewport.offsetHeight,
                itemCount: this.props.flows.length,
                rowHeight: this.props.rowHeight
            });

            if (!(0, _shallowequal2.default)(this.state.vScroll, vScroll) || this.state.viewportTop !== viewportTop) {
                this.setState({ vScroll: vScroll, viewportTop: viewportTop });
            }
        }
    }, {
        key: "scrollIntoView",
        value: function scrollIntoView(flow) {
            var viewport = _reactDom2.default.findDOMNode(this);
            var index = this.props.flows.indexOf(flow);
            var rowHeight = this.props.rowHeight;
            var head = _reactDom2.default.findDOMNode(this.refs.head);

            var headHeight = head ? head.offsetHeight : 0;

            var rowTop = index * rowHeight + headHeight;
            var rowBottom = rowTop + rowHeight;

            var viewportTop = viewport.scrollTop;
            var viewportHeight = viewport.offsetHeight;

            // Account for pinned thead
            if (rowTop - headHeight < viewportTop) {
                viewport.scrollTop = rowTop - headHeight;
            } else if (rowBottom > viewportTop + viewportHeight) {
                viewport.scrollTop = rowBottom - viewportHeight;
            }
        }
    }, {
        key: "render",
        value: function render() {
            var _this3 = this;

            var vScroll = this.state.vScroll;
            var flows = this.props.flows.slice(vScroll.start, vScroll.end);

            var transform = "translate(0," + this.state.viewportTop + "px)";

            return _react2.default.createElement(
                "div",
                { className: "flow-table", onScroll: this.onViewportUpdate },
                _react2.default.createElement(
                    "table",
                    null,
                    _react2.default.createElement(
                        "thead",
                        { ref: "head", style: { transform: transform } },
                        _react2.default.createElement(FlowTableHeadContainer, {
                            columns: _flowtableColumns2.default,
                            setSortKeyFun: this.props.setSortKeyFun,
                            setSort: this.props.setSort
                        })
                    ),
                    _react2.default.createElement(
                        "tbody",
                        null,
                        _react2.default.createElement("tr", { style: { height: vScroll.paddingTop } }),
                        flows.map(function (flow) {
                            return _react2.default.createElement(FlowRowContainer, {
                                key: flow.id,
                                flowId: flow.id,
                                columns: _flowtableColumns2.default,
                                selectFlow: _this3.props.selectFlow
                            });
                        }),
                        _react2.default.createElement("tr", { style: { height: vScroll.paddingBottom } })
                    )
                )
            );
        }
    }]);

    return FlowTable;
}(_react2.default.Component);

FlowTable.propTypes = {
    rowHeight: _react2.default.PropTypes.number
};
FlowTable.defaultProps = {
    rowHeight: 32
};


FlowTable = (0, _AutoScroll2.default)(FlowTable);

var parseFilter = _lodash2.default.memoize(_filt2.default.parse);

var FlowTableContainer = (0, _reactRedux.connect)(function (state) {
    return {
        flows: state.flows.view
    };
})(FlowTable);

exports.default = FlowTableContainer;

},{"../ducks/flows":24,"../filt/filt":29,"./flowtable-columns.js":9,"./helpers/AutoScroll":18,"./helpers/VirtualScroll":19,"classnames":"classnames","lodash":"lodash","react":"react","react-dom":"react-dom","react-redux":"react-redux","shallowequal":"shallowequal"}],11:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _lodash = require("lodash");

var _lodash2 = _interopRequireDefault(_lodash);

var _utils = require("../../flow/utils.js");

var _utils2 = require("../../utils.js");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var ViewImage = _react2.default.createClass({
    displayName: "ViewImage",

    propTypes: {
        flow: _react2.default.PropTypes.object.isRequired,
        message: _react2.default.PropTypes.object.isRequired
    },
    statics: {
        regex: /^image\/(png|jpe?g|gif|vnc.microsoft.icon|x-icon)$/i,
        matches: function matches(message) {
            return ViewImage.regex.test(_utils.MessageUtils.getContentType(message));
        }
    },
    render: function render() {
        var url = _utils.MessageUtils.getContentURL(this.props.flow, this.props.message);
        return _react2.default.createElement(
            "div",
            { className: "flowview-image" },
            _react2.default.createElement("img", { src: url, alt: "preview", className: "img-thumbnail" })
        );
    }
});

var ContentLoader = _react2.default.createClass({
    displayName: "ContentLoader",

    propTypes: {
        flow: _react2.default.PropTypes.object.isRequired,
        message: _react2.default.PropTypes.object.isRequired
    },
    getInitialState: function getInitialState() {
        return {
            content: undefined,
            request: undefined
        };
    },
    requestContent: function requestContent(nextProps) {
        if (this.state.request) {
            this.state.request.abort();
        }
        var request = _utils.MessageUtils.getContent(nextProps.flow, nextProps.message);
        this.setState({
            content: undefined,
            request: request
        });
        request.done(function (data) {
            this.setState({ content: data });
        }.bind(this)).fail(function (jqXHR, textStatus, errorThrown) {
            if (textStatus === "abort") {
                return;
            }
            this.setState({ content: "AJAX Error: " + textStatus + "\r\n" + errorThrown });
        }.bind(this)).always(function () {
            this.setState({ request: undefined });
        }.bind(this));
    },
    componentWillMount: function componentWillMount() {
        this.requestContent(this.props);
    },
    componentWillReceiveProps: function componentWillReceiveProps(nextProps) {
        if (nextProps.message !== this.props.message) {
            this.requestContent(nextProps);
        }
    },
    componentWillUnmount: function componentWillUnmount() {
        if (this.state.request) {
            this.state.request.abort();
        }
    },
    render: function render() {
        if (!this.state.content) {
            return _react2.default.createElement(
                "div",
                { className: "text-center" },
                _react2.default.createElement("i", { className: "fa fa-spinner fa-spin" })
            );
        }
        return _react2.default.cloneElement(this.props.children, {
            content: this.state.content
        });
    }
});

var ViewRaw = _react2.default.createClass({
    displayName: "ViewRaw",

    propTypes: {
        content: _react2.default.PropTypes.string.isRequired
    },
    statics: {
        textView: true,
        matches: function matches(message) {
            return true;
        }
    },
    render: function render() {
        return _react2.default.createElement(
            "pre",
            null,
            this.props.content
        );
    }
});

var ViewJSON = _react2.default.createClass({
    displayName: "ViewJSON",

    propTypes: {
        content: _react2.default.PropTypes.string.isRequired
    },
    statics: {
        textView: true,
        regex: /^application\/json$/i,
        matches: function matches(message) {
            return ViewJSON.regex.test(_utils.MessageUtils.getContentType(message));
        }
    },
    render: function render() {
        var json = this.props.content;
        try {
            json = JSON.stringify(JSON.parse(json), null, 2);
        } catch (e) {
            // @noop
        }
        return _react2.default.createElement(
            "pre",
            null,
            json
        );
    }
});

var ViewAuto = _react2.default.createClass({
    displayName: "ViewAuto",

    propTypes: {
        message: _react2.default.PropTypes.object.isRequired,
        flow: _react2.default.PropTypes.object.isRequired
    },
    statics: {
        matches: function matches() {
            return false; // don't match itself
        },
        findView: function findView(message) {
            for (var i = 0; i < all.length; i++) {
                if (all[i].matches(message)) {
                    return all[i];
                }
            }
            return all[all.length - 1];
        }
    },
    render: function render() {
        var _props = this.props;
        var message = _props.message;
        var flow = _props.flow;

        var View = ViewAuto.findView(this.props.message);
        if (View.textView) {
            return _react2.default.createElement(
                ContentLoader,
                { message: message, flow: flow },
                _react2.default.createElement(View, { content: "" })
            );
        } else {
            return _react2.default.createElement(View, { message: message, flow: flow });
        }
    }
});

var all = [ViewAuto, ViewImage, ViewJSON, ViewRaw];

var ContentEmpty = _react2.default.createClass({
    displayName: "ContentEmpty",

    render: function render() {
        var message_name = this.props.flow.request === this.props.message ? "request" : "response";
        return _react2.default.createElement(
            "div",
            { className: "alert alert-info" },
            "No ",
            message_name,
            " content."
        );
    }
});

var ContentMissing = _react2.default.createClass({
    displayName: "ContentMissing",

    render: function render() {
        var message_name = this.props.flow.request === this.props.message ? "Request" : "Response";
        return _react2.default.createElement(
            "div",
            { className: "alert alert-info" },
            message_name,
            " content missing."
        );
    }
});

var TooLarge = _react2.default.createClass({
    displayName: "TooLarge",

    statics: {
        isTooLarge: function isTooLarge(message) {
            var max_mb = ViewImage.matches(message) ? 10 : 0.2;
            return message.contentLength > 1024 * 1024 * max_mb;
        }
    },
    render: function render() {
        var size = (0, _utils2.formatSize)(this.props.message.contentLength);
        return _react2.default.createElement(
            "div",
            { className: "alert alert-warning" },
            _react2.default.createElement(
                "button",
                { onClick: this.props.onClick, className: "btn btn-xs btn-warning pull-right" },
                "Display anyway"
            ),
            size,
            " content size."
        );
    }
});

var ViewSelector = _react2.default.createClass({
    displayName: "ViewSelector",

    render: function render() {
        var views = [];
        for (var i = 0; i < all.length; i++) {
            var view = all[i];
            var className = "btn btn-default";
            if (view === this.props.active) {
                className += " active";
            }
            var text;
            if (view === ViewAuto) {
                text = "auto: " + ViewAuto.findView(this.props.message).displayName.toLowerCase().replace("view", "");
            } else {
                text = view.displayName.toLowerCase().replace("view", "");
            }
            views.push(_react2.default.createElement(
                "button",
                {
                    key: view.displayName,
                    onClick: this.props.selectView.bind(null, view),
                    className: className },
                text
            ));
        }

        return _react2.default.createElement(
            "div",
            { className: "view-selector btn-group btn-group-xs" },
            views
        );
    }
});

var ContentView = _react2.default.createClass({
    displayName: "ContentView",

    getInitialState: function getInitialState() {
        return {
            displayLarge: false,
            View: ViewAuto
        };
    },
    propTypes: {
        // It may seem a bit weird at the first glance:
        // Every view takes the flow and the message as props, e.g.
        // <Auto flow={flow} message={flow.request}/>
        flow: _react2.default.PropTypes.object.isRequired,
        message: _react2.default.PropTypes.object.isRequired
    },
    selectView: function selectView(view) {
        this.setState({
            View: view
        });
    },
    displayLarge: function displayLarge() {
        this.setState({ displayLarge: true });
    },
    componentWillReceiveProps: function componentWillReceiveProps(nextProps) {
        if (nextProps.message !== this.props.message) {
            this.setState(this.getInitialState());
        }
    },
    render: function render() {
        var _props2 = this.props;
        var flow = _props2.flow;
        var message = _props2.message;

        var message = this.props.message;
        if (message.contentLength === 0) {
            return _react2.default.createElement(ContentEmpty, this.props);
        } else if (message.contentLength === null) {
            return _react2.default.createElement(ContentMissing, this.props);
        } else if (!this.state.displayLarge && TooLarge.isTooLarge(message)) {
            return _react2.default.createElement(TooLarge, _extends({}, this.props, { onClick: this.displayLarge }));
        }

        var downloadUrl = _utils.MessageUtils.getContentURL(this.props.flow, message);

        return _react2.default.createElement(
            "div",
            null,
            this.state.View.textView ? _react2.default.createElement(
                ContentLoader,
                { flow: flow, message: message },
                _react2.default.createElement(this.state.View, { content: "" })
            ) : _react2.default.createElement(this.state.View, { flow: flow, message: message }),
            _react2.default.createElement(
                "div",
                { className: "view-options text-center" },
                _react2.default.createElement(ViewSelector, { selectView: this.selectView, active: this.state.View, message: message }),
                " ",
                _react2.default.createElement(
                    "a",
                    { className: "btn btn-default btn-xs", href: downloadUrl },
                    _react2.default.createElement("i", { className: "fa fa-download" })
                )
            )
        );
    }
});

exports.default = ContentView;

},{"../../flow/utils.js":30,"../../utils.js":32,"lodash":"lodash","react":"react"}],12:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _lodash = require("lodash");

var _lodash2 = _interopRequireDefault(_lodash);

var _utils = require("../../utils.js");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var TimeStamp = _react2.default.createClass({
    displayName: "TimeStamp",

    render: function render() {

        if (!this.props.t) {
            //should be return null, but that triggers a React bug.
            return _react2.default.createElement("tr", null);
        }

        var ts = (0, _utils.formatTimeStamp)(this.props.t);

        var delta;
        if (this.props.deltaTo) {
            delta = (0, _utils.formatTimeDelta)(1000 * (this.props.t - this.props.deltaTo));
            delta = _react2.default.createElement(
                "span",
                { className: "text-muted" },
                "(" + delta + ")"
            );
        } else {
            delta = null;
        }

        return _react2.default.createElement(
            "tr",
            null,
            _react2.default.createElement(
                "td",
                null,
                this.props.title + ":"
            ),
            _react2.default.createElement(
                "td",
                null,
                ts,
                " ",
                delta
            )
        );
    }
});

var ConnectionInfo = _react2.default.createClass({
    displayName: "ConnectionInfo",


    render: function render() {
        var conn = this.props.conn;
        var address = conn.address.address.join(":");

        var sni = _react2.default.createElement("tr", { key: "sni" }); //should be null, but that triggers a React bug.
        if (conn.sni) {
            sni = _react2.default.createElement(
                "tr",
                { key: "sni" },
                _react2.default.createElement(
                    "td",
                    null,
                    _react2.default.createElement(
                        "abbr",
                        { title: "TLS Server Name Indication" },
                        "TLS SNI:"
                    )
                ),
                _react2.default.createElement(
                    "td",
                    null,
                    conn.sni
                )
            );
        }
        return _react2.default.createElement(
            "table",
            { className: "connection-table" },
            _react2.default.createElement(
                "tbody",
                null,
                _react2.default.createElement(
                    "tr",
                    { key: "address" },
                    _react2.default.createElement(
                        "td",
                        null,
                        "Address:"
                    ),
                    _react2.default.createElement(
                        "td",
                        null,
                        address
                    )
                ),
                sni
            )
        );
    }
});

var CertificateInfo = _react2.default.createClass({
    displayName: "CertificateInfo",

    render: function render() {
        //TODO: We should fetch human-readable certificate representation
        // from the server
        var flow = this.props.flow;
        var client_conn = flow.client_conn;
        var server_conn = flow.server_conn;

        var preStyle = { maxHeight: 100 };
        return _react2.default.createElement(
            "div",
            null,
            client_conn.cert ? _react2.default.createElement(
                "h4",
                null,
                "Client Certificate"
            ) : null,
            client_conn.cert ? _react2.default.createElement(
                "pre",
                { style: preStyle },
                client_conn.cert
            ) : null,
            server_conn.cert ? _react2.default.createElement(
                "h4",
                null,
                "Server Certificate"
            ) : null,
            server_conn.cert ? _react2.default.createElement(
                "pre",
                { style: preStyle },
                server_conn.cert
            ) : null
        );
    }
});

var Timing = _react2.default.createClass({
    displayName: "Timing",

    render: function render() {
        var flow = this.props.flow;
        var sc = flow.server_conn;
        var cc = flow.client_conn;
        var req = flow.request;
        var resp = flow.response;

        var timestamps = [{
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
            t: req.timestamp_start
        }, {
            title: "Request complete",
            t: req.timestamp_end,
            deltaTo: req.timestamp_start
        }];

        if (flow.response) {
            timestamps.push({
                title: "First response byte",
                t: resp.timestamp_start,
                deltaTo: req.timestamp_start
            }, {
                title: "Response complete",
                t: resp.timestamp_end,
                deltaTo: req.timestamp_start
            });
        }

        //Add unique key for each row.
        timestamps.forEach(function (e) {
            e.key = e.title;
        });

        timestamps = _lodash2.default.sortBy(timestamps, 't');

        var rows = timestamps.map(function (e) {
            return _react2.default.createElement(TimeStamp, e);
        });

        return _react2.default.createElement(
            "div",
            null,
            _react2.default.createElement(
                "h4",
                null,
                "Timing"
            ),
            _react2.default.createElement(
                "table",
                { className: "timing-table" },
                _react2.default.createElement(
                    "tbody",
                    null,
                    rows
                )
            )
        );
    }
});

var Details = _react2.default.createClass({
    displayName: "Details",

    render: function render() {
        var flow = this.props.flow;
        var client_conn = flow.client_conn;
        var server_conn = flow.server_conn;
        return _react2.default.createElement(
            "section",
            null,
            _react2.default.createElement(
                "h4",
                null,
                "Client Connection"
            ),
            _react2.default.createElement(ConnectionInfo, { conn: client_conn }),
            _react2.default.createElement(
                "h4",
                null,
                "Server Connection"
            ),
            _react2.default.createElement(ConnectionInfo, { conn: server_conn }),
            _react2.default.createElement(CertificateInfo, { flow: flow }),
            _react2.default.createElement(Timing, { flow: flow })
        );
    }
});

exports.default = Details;

},{"../../utils.js":32,"lodash":"lodash","react":"react"}],13:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _nav = require("./nav.js");

var _nav2 = _interopRequireDefault(_nav);

var _messages = require("./messages.js");

var _details = require("./details.js");

var _details2 = _interopRequireDefault(_details);

var _prompt = require("../prompt.js");

var _prompt2 = _interopRequireDefault(_prompt);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var allTabs = {
    request: _messages.Request,
    response: _messages.Response,
    error: _messages.Error,
    details: _details2.default
};

var FlowView = _react2.default.createClass({
    displayName: "FlowView",

    getInitialState: function getInitialState() {
        return {
            prompt: false
        };
    },
    getTabs: function getTabs(flow) {
        var tabs = [];
        ["request", "response", "error"].forEach(function (e) {
            if (flow[e]) {
                tabs.push(e);
            }
        });
        tabs.push("details");
        return tabs;
    },
    nextTab: function nextTab(i) {
        var tabs = this.getTabs(this.props.flow);
        var currentIndex = tabs.indexOf(this.props.tab);
        // JS modulo operator doesn't correct negative numbers, make sure that we are positive.
        var nextIndex = (currentIndex + i + tabs.length) % tabs.length;
        this.selectTab(tabs[nextIndex]);
    },
    selectTab: function selectTab(panel) {
        this.props.updateLocation("/flows/" + this.props.flow.id + "/" + panel);
    },
    promptEdit: function promptEdit() {
        var options;
        switch (this.props.tab) {
            case "request":
                options = ["method", "url", { text: "http version", key: "v" }, "header"
                /*, "content"*/];
                break;
            case "response":
                options = [{ text: "http version", key: "v" }, "code", "message", "header"
                /*, "content"*/];
                break;
            case "details":
                return;
            default:
                throw "Unknown tab for edit: " + this.props.tab;
        }

        this.setState({
            prompt: {
                done: function (k) {
                    this.setState({ prompt: false });
                    if (k) {
                        this.refs.tab.edit(k);
                    }
                }.bind(this),
                options: options
            }
        });
    },
    render: function render() {
        var flow = this.props.flow;
        var tabs = this.getTabs(flow);
        var active = this.props.tab;

        if (tabs.indexOf(active) < 0) {
            if (active === "response" && flow.error) {
                active = "error";
            } else if (active === "error" && flow.response) {
                active = "response";
            } else {
                active = tabs[0];
            }
        }

        var prompt = null;
        if (this.state.prompt) {
            prompt = _react2.default.createElement(_prompt2.default, this.state.prompt);
        }

        var Tab = allTabs[active];
        return _react2.default.createElement(
            "div",
            { className: "flow-detail", onScroll: this.adjustHead },
            _react2.default.createElement(_nav2.default, { ref: "head",
                flow: flow,
                tabs: tabs,
                active: active,
                selectTab: this.selectTab }),
            _react2.default.createElement(Tab, { ref: "tab", flow: flow }),
            prompt
        );
    }
});

exports.default = FlowView;

},{"../prompt.js":20,"./details.js":12,"./messages.js":14,"./nav.js":15,"react":"react"}],14:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.Error = exports.Response = exports.Request = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _reactDom = require("react-dom");

var _reactDom2 = _interopRequireDefault(_reactDom);

var _lodash = require("lodash");

var _lodash2 = _interopRequireDefault(_lodash);

var _actions = require("../../actions.js");

var _utils = require("../../flow/utils.js");

var _utils2 = require("../../utils.js");

var _contentview = require("./contentview.js");

var _contentview2 = _interopRequireDefault(_contentview);

var _editor = require("../editor.js");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var Headers = _react2.default.createClass({
    displayName: "Headers",

    propTypes: {
        onChange: _react2.default.PropTypes.func.isRequired,
        message: _react2.default.PropTypes.object.isRequired
    },
    onChange: function onChange(row, col, val) {
        var nextHeaders = _lodash2.default.cloneDeep(this.props.message.headers);
        nextHeaders[row][col] = val;
        if (!nextHeaders[row][0] && !nextHeaders[row][1]) {
            // do not delete last row
            if (nextHeaders.length === 1) {
                nextHeaders[0][0] = "Name";
                nextHeaders[0][1] = "Value";
            } else {
                nextHeaders.splice(row, 1);
                // manually move selection target if this has been the last row.
                if (row === nextHeaders.length) {
                    this._nextSel = row - 1 + "-value";
                }
            }
        }
        this.props.onChange(nextHeaders);
    },
    edit: function edit() {
        this.refs["0-key"].focus();
    },
    onTab: function onTab(row, col, e) {
        var headers = this.props.message.headers;
        if (row === headers.length - 1 && col === 1) {
            e.preventDefault();

            var nextHeaders = _lodash2.default.cloneDeep(this.props.message.headers);
            nextHeaders.push(["Name", "Value"]);
            this.props.onChange(nextHeaders);
            this._nextSel = row + 1 + "-key";
        }
    },
    componentDidUpdate: function componentDidUpdate() {
        if (this._nextSel && this.refs[this._nextSel]) {
            this.refs[this._nextSel].focus();
            this._nextSel = undefined;
        }
    },
    onRemove: function onRemove(row, col, e) {
        if (col === 1) {
            e.preventDefault();
            this.refs[row + "-key"].focus();
        } else if (row > 0) {
            e.preventDefault();
            this.refs[row - 1 + "-value"].focus();
        }
    },
    render: function render() {

        var rows = this.props.message.headers.map(function (header, i) {

            var kEdit = _react2.default.createElement(HeaderEditor, {
                ref: i + "-key",
                content: header[0],
                onDone: this.onChange.bind(null, i, 0),
                onRemove: this.onRemove.bind(null, i, 0),
                onTab: this.onTab.bind(null, i, 0) });
            var vEdit = _react2.default.createElement(HeaderEditor, {
                ref: i + "-value",
                content: header[1],
                onDone: this.onChange.bind(null, i, 1),
                onRemove: this.onRemove.bind(null, i, 1),
                onTab: this.onTab.bind(null, i, 1) });
            return _react2.default.createElement(
                "tr",
                { key: i },
                _react2.default.createElement(
                    "td",
                    { className: "header-name" },
                    kEdit,
                    ":"
                ),
                _react2.default.createElement(
                    "td",
                    { className: "header-value" },
                    vEdit
                )
            );
        }.bind(this));
        return _react2.default.createElement(
            "table",
            { className: "header-table" },
            _react2.default.createElement(
                "tbody",
                null,
                rows
            )
        );
    }
});

var HeaderEditor = _react2.default.createClass({
    displayName: "HeaderEditor",

    render: function render() {
        return _react2.default.createElement(_editor.ValueEditor, _extends({ ref: "input" }, this.props, { onKeyDown: this.onKeyDown, inline: true }));
    },
    focus: function focus() {
        _reactDom2.default.findDOMNode(this).focus();
    },
    onKeyDown: function onKeyDown(e) {
        switch (e.keyCode) {
            case _utils2.Key.BACKSPACE:
                var s = window.getSelection().getRangeAt(0);
                if (s.startOffset === 0 && s.endOffset === 0) {
                    this.props.onRemove(e);
                }
                break;
            case _utils2.Key.TAB:
                if (!e.shiftKey) {
                    this.props.onTab(e);
                }
                break;
        }
    }
});

var RequestLine = _react2.default.createClass({
    displayName: "RequestLine",

    render: function render() {
        var flow = this.props.flow;
        var url = _utils.RequestUtils.pretty_url(flow.request);
        var httpver = flow.request.http_version;

        return _react2.default.createElement(
            "div",
            { className: "first-line request-line" },
            _react2.default.createElement(_editor.ValueEditor, {
                ref: "method",
                content: flow.request.method,
                onDone: this.onMethodChange,
                inline: true }),
            " ",
            _react2.default.createElement(_editor.ValueEditor, {
                ref: "url",
                content: url,
                onDone: this.onUrlChange,
                isValid: this.isValidUrl,
                inline: true }),
            " ",
            _react2.default.createElement(_editor.ValueEditor, {
                ref: "httpVersion",
                content: httpver,
                onDone: this.onHttpVersionChange,
                isValid: _utils.isValidHttpVersion,
                inline: true })
        );
    },
    isValidUrl: function isValidUrl(url) {
        var u = (0, _utils.parseUrl)(url);
        return !!u.host;
    },
    onMethodChange: function onMethodChange(nextMethod) {
        _actions.FlowActions.update(this.props.flow, { request: { method: nextMethod } });
    },
    onUrlChange: function onUrlChange(nextUrl) {
        var props = (0, _utils.parseUrl)(nextUrl);
        props.path = props.path || "";
        _actions.FlowActions.update(this.props.flow, { request: props });
    },
    onHttpVersionChange: function onHttpVersionChange(nextVer) {
        var ver = (0, _utils.parseHttpVersion)(nextVer);
        _actions.FlowActions.update(this.props.flow, { request: { http_version: ver } });
    }
});

var ResponseLine = _react2.default.createClass({
    displayName: "ResponseLine",

    render: function render() {
        var flow = this.props.flow;
        var httpver = flow.response.http_version;
        return _react2.default.createElement(
            "div",
            { className: "first-line response-line" },
            _react2.default.createElement(_editor.ValueEditor, {
                ref: "httpVersion",
                content: httpver,
                onDone: this.onHttpVersionChange,
                isValid: _utils.isValidHttpVersion,
                inline: true }),
            " ",
            _react2.default.createElement(_editor.ValueEditor, {
                ref: "code",
                content: flow.response.status_code + "",
                onDone: this.onCodeChange,
                isValid: this.isValidCode,
                inline: true }),
            " ",
            _react2.default.createElement(_editor.ValueEditor, {
                ref: "msg",
                content: flow.response.reason,
                onDone: this.onMsgChange,
                inline: true })
        );
    },
    isValidCode: function isValidCode(code) {
        return (/^\d+$/.test(code)
        );
    },
    onHttpVersionChange: function onHttpVersionChange(nextVer) {
        var ver = (0, _utils.parseHttpVersion)(nextVer);
        _actions.FlowActions.update(this.props.flow, { response: { http_version: ver } });
    },
    onMsgChange: function onMsgChange(nextMsg) {
        _actions.FlowActions.update(this.props.flow, { response: { msg: nextMsg } });
    },
    onCodeChange: function onCodeChange(nextCode) {
        nextCode = parseInt(nextCode);
        _actions.FlowActions.update(this.props.flow, { response: { code: nextCode } });
    }
});

var Request = exports.Request = _react2.default.createClass({
    displayName: "Request",

    render: function render() {
        var flow = this.props.flow;
        return _react2.default.createElement(
            "section",
            { className: "request" },
            _react2.default.createElement(RequestLine, { ref: "requestLine", flow: flow }),
            _react2.default.createElement(Headers, { ref: "headers", message: flow.request, onChange: this.onHeaderChange }),
            _react2.default.createElement("hr", null),
            _react2.default.createElement(_contentview2.default, { flow: flow, message: flow.request })
        );
    },
    edit: function edit(k) {
        switch (k) {
            case "m":
                this.refs.requestLine.refs.method.focus();
                break;
            case "u":
                this.refs.requestLine.refs.url.focus();
                break;
            case "v":
                this.refs.requestLine.refs.httpVersion.focus();
                break;
            case "h":
                this.refs.headers.edit();
                break;
            default:
                throw "Unimplemented: " + k;
        }
    },
    onHeaderChange: function onHeaderChange(nextHeaders) {
        _actions.FlowActions.update(this.props.flow, {
            request: {
                headers: nextHeaders
            }
        });
    }
});

var Response = exports.Response = _react2.default.createClass({
    displayName: "Response",

    render: function render() {
        var flow = this.props.flow;
        return _react2.default.createElement(
            "section",
            { className: "response" },
            _react2.default.createElement(ResponseLine, { ref: "responseLine", flow: flow }),
            _react2.default.createElement(Headers, { ref: "headers", message: flow.response, onChange: this.onHeaderChange }),
            _react2.default.createElement("hr", null),
            _react2.default.createElement(_contentview2.default, { flow: flow, message: flow.response })
        );
    },
    edit: function edit(k) {
        switch (k) {
            case "c":
                this.refs.responseLine.refs.status_code.focus();
                break;
            case "m":
                this.refs.responseLine.refs.msg.focus();
                break;
            case "v":
                this.refs.responseLine.refs.httpVersion.focus();
                break;
            case "h":
                this.refs.headers.edit();
                break;
            default:
                throw "Unimplemented: " + k;
        }
    },
    onHeaderChange: function onHeaderChange(nextHeaders) {
        _actions.FlowActions.update(this.props.flow, {
            response: {
                headers: nextHeaders
            }
        });
    }
});

var Error = exports.Error = _react2.default.createClass({
    displayName: "Error",

    render: function render() {
        var flow = this.props.flow;
        return _react2.default.createElement(
            "section",
            null,
            _react2.default.createElement(
                "div",
                { className: "alert alert-warning" },
                flow.error.msg,
                _react2.default.createElement(
                    "div",
                    null,
                    _react2.default.createElement(
                        "small",
                        null,
                        (0, _utils2.formatTimeStamp)(flow.error.timestamp)
                    )
                )
            )
        );
    }
});

},{"../../actions.js":2,"../../flow/utils.js":30,"../../utils.js":32,"../editor.js":7,"./contentview.js":11,"lodash":"lodash","react":"react","react-dom":"react-dom"}],15:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _actions = require("../../actions.js");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var NavAction = _react2.default.createClass({
    displayName: "NavAction",

    onClick: function onClick(e) {
        e.preventDefault();
        this.props.onClick();
    },
    render: function render() {
        return _react2.default.createElement(
            "a",
            { title: this.props.title,
                href: "#",
                className: "nav-action",
                onClick: this.onClick },
            _react2.default.createElement("i", { className: "fa fa-fw " + this.props.icon })
        );
    }
});

var Nav = _react2.default.createClass({
    displayName: "Nav",

    render: function render() {
        var flow = this.props.flow;

        var tabs = this.props.tabs.map(function (e) {
            var str = e.charAt(0).toUpperCase() + e.slice(1);
            var className = this.props.active === e ? "active" : "";
            var onClick = function (event) {
                this.props.selectTab(e);
                event.preventDefault();
            }.bind(this);
            return _react2.default.createElement(
                "a",
                { key: e,
                    href: "#",
                    className: className,
                    onClick: onClick },
                str
            );
        }.bind(this));

        var acceptButton = null;
        if (flow.intercepted) {
            acceptButton = _react2.default.createElement(NavAction, { title: "[a]ccept intercepted flow", icon: "fa-play", onClick: _actions.FlowActions.accept.bind(null, flow) });
        }
        var revertButton = null;
        if (flow.modified) {
            revertButton = _react2.default.createElement(NavAction, { title: "revert changes to flow [V]", icon: "fa-history", onClick: _actions.FlowActions.revert.bind(null, flow) });
        }

        return _react2.default.createElement(
            "nav",
            { ref: "head", className: "nav-tabs nav-tabs-sm" },
            tabs,
            _react2.default.createElement(NavAction, { title: "[d]elete flow", icon: "fa-trash", onClick: _actions.FlowActions.delete.bind(null, flow) }),
            _react2.default.createElement(NavAction, { title: "[D]uplicate flow", icon: "fa-copy", onClick: _actions.FlowActions.duplicate.bind(null, flow) }),
            _react2.default.createElement(NavAction, { disabled: true, title: "[r]eplay flow", icon: "fa-repeat", onClick: _actions.FlowActions.replay.bind(null, flow) }),
            acceptButton,
            revertButton
        );
    }
});

exports.default = Nav;

},{"../../actions.js":2,"react":"react"}],16:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = Footer;

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _utils = require("../utils.js");

var _common = require("./common.js");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

Footer.propTypes = {
    settings: _react2.default.PropTypes.object.isRequired
};

function Footer(_ref) {
    var settings = _ref.settings;
    var mode = settings.mode;
    var intercept = settings.intercept;
    var showhost = settings.showhost;
    var no_upstream_cert = settings.no_upstream_cert;
    var rawtcp = settings.rawtcp;
    var http2 = settings.http2;
    var anticache = settings.anticache;
    var anticomp = settings.anticomp;
    var stickyauth = settings.stickyauth;
    var stickycookie = settings.stickycookie;
    var stream = settings.stream;

    return _react2.default.createElement(
        "footer",
        null,
        mode && mode != "regular" && _react2.default.createElement(
            "span",
            { className: "label label-success" },
            mode,
            " mode"
        ),
        intercept && _react2.default.createElement(
            "span",
            { className: "label label-success" },
            "Intercept: ",
            intercept
        ),
        showhost && _react2.default.createElement(
            "span",
            { className: "label label-success" },
            "showhost"
        ),
        no_upstream_cert && _react2.default.createElement(
            "span",
            { className: "label label-success" },
            "no-upstream-cert"
        ),
        rawtcp && _react2.default.createElement(
            "span",
            { className: "label label-success" },
            "raw-tcp"
        ),
        !http2 && _react2.default.createElement(
            "span",
            { className: "label label-success" },
            "no-http2"
        ),
        anticache && _react2.default.createElement(
            "span",
            { className: "label label-success" },
            "anticache"
        ),
        anticomp && _react2.default.createElement(
            "span",
            { className: "label label-success" },
            "anticomp"
        ),
        stickyauth && _react2.default.createElement(
            "span",
            { className: "label label-success" },
            "stickyauth: ",
            stickyauth
        ),
        stickycookie && _react2.default.createElement(
            "span",
            { className: "label label-success" },
            "stickycookie: ",
            stickycookie
        ),
        stream && _react2.default.createElement(
            "span",
            { className: "label label-success" },
            "stream: ",
            (0, _utils.formatSize)(stream)
        )
    );
}

},{"../utils.js":32,"./common.js":6,"react":"react"}],17:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.Header = exports.OptionMenu = exports.MainMenu = undefined;

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _reactDom = require("react-dom");

var _reactDom2 = _interopRequireDefault(_reactDom);

var _jquery = require("jquery");

var _jquery2 = _interopRequireDefault(_jquery);

var _reactRedux = require("react-redux");

var _filt = require("../filt/filt.js");

var _filt2 = _interopRequireDefault(_filt);

var _utils = require("../utils.js");

var _common = require("./common.js");

var _actions = require("../actions.js");

var _eventlog = require("./eventlog");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var FilterDocs = _react2.default.createClass({
    displayName: "FilterDocs",

    statics: {
        xhr: false,
        doc: false
    },
    componentWillMount: function componentWillMount() {
        if (!FilterDocs.doc) {
            FilterDocs.xhr = _jquery2.default.getJSON("/filter-help").done(function (doc) {
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
    render: function render() {
        if (!FilterDocs.doc) {
            return _react2.default.createElement("i", { className: "fa fa-spinner fa-spin" });
        } else {
            var commands = FilterDocs.doc.commands.map(function (c) {
                return _react2.default.createElement(
                    "tr",
                    { key: c[1] },
                    _react2.default.createElement(
                        "td",
                        null,
                        c[0].replace(" ", " ")
                    ),
                    _react2.default.createElement(
                        "td",
                        null,
                        c[1]
                    )
                );
            });
            commands.push(_react2.default.createElement(
                "tr",
                { key: "docs-link" },
                _react2.default.createElement(
                    "td",
                    { colSpan: "2" },
                    _react2.default.createElement(
                        "a",
                        { href: "http://docs.mitmproxy.org/en/stable/features/filters.html",
                            target: "_blank" },
                        _react2.default.createElement("i", { className: "fa fa-external-link" }),
                        "  mitmproxy docs"
                    )
                )
            ));
            return _react2.default.createElement(
                "table",
                { className: "table table-condensed" },
                _react2.default.createElement(
                    "tbody",
                    null,
                    commands
                )
            );
        }
    }
});
var FilterInput = _react2.default.createClass({
    displayName: "FilterInput",

    contextTypes: {
        returnFocus: _react2.default.PropTypes.func
    },
    getInitialState: function getInitialState() {
        // Consider both focus and mouseover for showing/hiding the tooltip,
        // because onBlur of the input is triggered before the click on the tooltip
        // finalized, hiding the tooltip just as the user clicks on it.
        return {
            value: this.props.value,
            focus: false,
            mousefocus: false
        };
    },
    componentWillReceiveProps: function componentWillReceiveProps(nextProps) {
        this.setState({ value: nextProps.value });
    },
    onChange: function onChange(e) {
        var nextValue = e.target.value;
        this.setState({
            value: nextValue
        });
        // Only propagate valid filters upwards.
        if (this.isValid(nextValue)) {
            this.props.onChange(nextValue);
        }
    },
    isValid: function isValid(filt) {
        try {
            var str = filt || this.state.value;
            if (str) {
                _filt2.default.parse(filt || this.state.value);
            }
            return true;
        } catch (e) {
            return false;
        }
    },
    getDesc: function getDesc() {
        if (this.state.value) {
            try {
                return _filt2.default.parse(this.state.value).desc;
            } catch (e) {
                return "" + e;
            }
        }
        return _react2.default.createElement(FilterDocs, null);
    },
    onFocus: function onFocus() {
        this.setState({ focus: true });
    },
    onBlur: function onBlur() {
        this.setState({ focus: false });
    },
    onMouseEnter: function onMouseEnter() {
        this.setState({ mousefocus: true });
    },
    onMouseLeave: function onMouseLeave() {
        this.setState({ mousefocus: false });
    },
    onKeyDown: function onKeyDown(e) {
        if (e.keyCode === _utils.Key.ESC || e.keyCode === _utils.Key.ENTER) {
            this.blur();
            // If closed using ESC/ENTER, hide the tooltip.
            this.setState({ mousefocus: false });
        }
        e.stopPropagation();
    },
    blur: function blur() {
        _reactDom2.default.findDOMNode(this.refs.input).blur();
        this.context.returnFocus();
    },
    select: function select() {
        _reactDom2.default.findDOMNode(this.refs.input).select();
    },
    render: function render() {
        var isValid = this.isValid();
        var icon = "fa fa-fw fa-" + this.props.type;
        var groupClassName = "filter-input input-group" + (isValid ? "" : " has-error");

        var popover;
        if (this.state.focus || this.state.mousefocus) {
            popover = _react2.default.createElement(
                "div",
                { className: "popover bottom", onMouseEnter: this.onMouseEnter, onMouseLeave: this.onMouseLeave },
                _react2.default.createElement("div", { className: "arrow" }),
                _react2.default.createElement(
                    "div",
                    { className: "popover-content" },
                    this.getDesc()
                )
            );
        }

        return _react2.default.createElement(
            "div",
            { className: groupClassName },
            _react2.default.createElement(
                "span",
                { className: "input-group-addon" },
                _react2.default.createElement("i", { className: icon, style: { color: this.props.color } })
            ),
            _react2.default.createElement("input", { type: "text", placeholder: this.props.placeholder, className: "form-control",
                ref: "input",
                onChange: this.onChange,
                onFocus: this.onFocus,
                onBlur: this.onBlur,
                onKeyDown: this.onKeyDown,
                value: this.state.value }),
            popover
        );
    }
});

var MainMenu = exports.MainMenu = _react2.default.createClass({
    displayName: "MainMenu",

    propTypes: {
        settings: _react2.default.PropTypes.object.isRequired
    },
    statics: {
        title: "Start",
        route: "flows"
    },
    onSearchChange: function onSearchChange(val) {
        var d = {};
        d[_actions.Query.SEARCH] = val;
        this.props.updateLocation(undefined, d);
    },
    onHighlightChange: function onHighlightChange(val) {
        var d = {};
        d[_actions.Query.HIGHLIGHT] = val;
        this.props.updateLocation(undefined, d);
    },
    onInterceptChange: function onInterceptChange(val) {
        _actions.SettingsActions.update({ intercept: val });
    },
    render: function render() {
        var search = this.props.query[_actions.Query.SEARCH] || "";
        var highlight = this.props.query[_actions.Query.HIGHLIGHT] || "";
        var intercept = this.props.settings.intercept || "";

        return _react2.default.createElement(
            "div",
            null,
            _react2.default.createElement(
                "div",
                { className: "menu-row" },
                _react2.default.createElement(FilterInput, {
                    ref: "search",
                    placeholder: "Search",
                    type: "search",
                    color: "black",
                    value: search,
                    onChange: this.onSearchChange }),
                _react2.default.createElement(FilterInput, {
                    ref: "highlight",
                    placeholder: "Highlight",
                    type: "tag",
                    color: "hsl(48, 100%, 50%)",
                    value: highlight,
                    onChange: this.onHighlightChange }),
                _react2.default.createElement(FilterInput, {
                    ref: "intercept",
                    placeholder: "Intercept",
                    type: "pause",
                    color: "hsl(208, 56%, 53%)",
                    value: intercept,
                    onChange: this.onInterceptChange })
            ),
            _react2.default.createElement("div", { className: "clearfix" })
        );
    }
});

var ViewMenu = _react2.default.createClass({
    displayName: "ViewMenu",

    statics: {
        title: "View",
        route: "flows"
    },
    render: function render() {
        return _react2.default.createElement(
            "div",
            null,
            _react2.default.createElement(
                "div",
                { className: "menu-row" },
                _react2.default.createElement(_eventlog.ToggleEventLog, { text: "Show Event Log" })
            ),
            _react2.default.createElement("div", { className: "clearfix" })
        );
    }
});

var OptionMenu = exports.OptionMenu = function OptionMenu(props) {
    var _props$settings = props.settings;
    var mode = _props$settings.mode;
    var intercept = _props$settings.intercept;
    var showhost = _props$settings.showhost;
    var no_upstream_cert = _props$settings.no_upstream_cert;
    var rawtcp = _props$settings.rawtcp;
    var http2 = _props$settings.http2;
    var anticache = _props$settings.anticache;
    var anticomp = _props$settings.anticomp;
    var stickycookie = _props$settings.stickycookie;
    var stickyauth = _props$settings.stickyauth;
    var stream = _props$settings.stream;

    return _react2.default.createElement(
        "div",
        null,
        _react2.default.createElement(
            "div",
            { className: "menu-row" },
            _react2.default.createElement(_common.ToggleButton, { text: "showhost",
                checked: showhost,
                onToggle: function onToggle() {
                    return _actions.SettingsActions.update({ showhost: !showhost });
                }
            }),
            _react2.default.createElement(_common.ToggleButton, { text: "no_upstream_cert",
                checked: no_upstream_cert,
                onToggle: function onToggle() {
                    return _actions.SettingsActions.update({ no_upstream_cert: !no_upstream_cert });
                }
            }),
            _react2.default.createElement(_common.ToggleButton, { text: "rawtcp",
                checked: rawtcp,
                onToggle: function onToggle() {
                    return _actions.SettingsActions.update({ rawtcp: !rawtcp });
                }
            }),
            _react2.default.createElement(_common.ToggleButton, { text: "http2",
                checked: http2,
                onToggle: function onToggle() {
                    return _actions.SettingsActions.update({ http2: !http2 });
                }
            }),
            _react2.default.createElement(_common.ToggleButton, { text: "anticache",
                checked: anticache,
                onToggle: function onToggle() {
                    return _actions.SettingsActions.update({ anticache: !anticache });
                }
            }),
            _react2.default.createElement(_common.ToggleButton, { text: "anticomp",
                checked: anticomp,
                onToggle: function onToggle() {
                    return _actions.SettingsActions.update({ anticomp: !anticomp });
                }
            }),
            _react2.default.createElement(_common.ToggleInputButton, { name: "stickyauth", placeholder: "Sticky auth filter",
                checked: Boolean(stickyauth),
                txt: stickyauth || "",
                onToggleChanged: function onToggleChanged(txt) {
                    return _actions.SettingsActions.update({ stickyauth: !stickyauth ? txt : null });
                }
            }),
            _react2.default.createElement(_common.ToggleInputButton, { name: "stickycookie", placeholder: "Sticky cookie filter",
                checked: Boolean(stickycookie),
                txt: stickycookie || "",
                onToggleChanged: function onToggleChanged(txt) {
                    return _actions.SettingsActions.update({ stickycookie: !stickycookie ? txt : null });
                }
            }),
            _react2.default.createElement(_common.ToggleInputButton, { name: "stream", placeholder: "stream...",
                checked: Boolean(stream),
                txt: stream || "",
                inputType: "number",
                onToggleChanged: function onToggleChanged(txt) {
                    return _actions.SettingsActions.update({ stream: !stream ? txt : null });
                }
            })
        ),
        _react2.default.createElement("div", { className: "clearfix" })
    );
};
OptionMenu.title = "Options";

OptionMenu.propTypes = {
    settings: _react2.default.PropTypes.object.isRequired
};

var ReportsMenu = _react2.default.createClass({
    displayName: "ReportsMenu",

    statics: {
        title: "Visualization",
        route: "reports"
    },
    render: function render() {
        return _react2.default.createElement(
            "div",
            null,
            "Reports Menu"
        );
    }
});

var FileMenu = _react2.default.createClass({
    displayName: "FileMenu",

    getInitialState: function getInitialState() {
        return {
            showFileMenu: false
        };
    },
    handleFileClick: function handleFileClick(e) {
        e.preventDefault();
        if (!this.state.showFileMenu) {
            var close = function () {
                this.setState({ showFileMenu: false });
                document.removeEventListener("click", close);
            }.bind(this);
            document.addEventListener("click", close);

            this.setState({
                showFileMenu: true
            });
        }
    },
    handleNewClick: function handleNewClick(e) {
        e.preventDefault();
        if (confirm("Delete all flows?")) {
            _actions.FlowActions.clear();
        }
    },
    handleOpenClick: function handleOpenClick(e) {
        this.fileInput.click();
        e.preventDefault();
    },
    handleOpenFile: function handleOpenFile(e) {
        if (e.target.files.length > 0) {
            _actions.FlowActions.upload(e.target.files[0]);
            this.fileInput.value = "";
        }
        e.preventDefault();
    },
    handleSaveClick: function handleSaveClick(e) {
        e.preventDefault();
        _actions.FlowActions.download();
    },
    handleShutdownClick: function handleShutdownClick(e) {
        e.preventDefault();
        console.error("unimplemented: handleShutdownClick");
    },
    render: function render() {
        var _this = this;

        var fileMenuClass = "dropdown pull-left" + (this.state.showFileMenu ? " open" : "");

        return _react2.default.createElement(
            "div",
            { className: fileMenuClass },
            _react2.default.createElement(
                "a",
                { href: "#", className: "special", onClick: this.handleFileClick },
                " mitmproxy "
            ),
            _react2.default.createElement(
                "ul",
                { className: "dropdown-menu", role: "menu" },
                _react2.default.createElement(
                    "li",
                    null,
                    _react2.default.createElement(
                        "a",
                        { href: "#", onClick: this.handleNewClick },
                        _react2.default.createElement("i", { className: "fa fa-fw fa-file" }),
                        "New"
                    )
                ),
                _react2.default.createElement(
                    "li",
                    null,
                    _react2.default.createElement(
                        "a",
                        { href: "#", onClick: this.handleOpenClick },
                        _react2.default.createElement("i", { className: "fa fa-fw fa-folder-open" }),
                        "Open..."
                    ),
                    _react2.default.createElement("input", { ref: function ref(_ref) {
                            return _this.fileInput = _ref;
                        }, className: "hidden", type: "file", onChange: this.handleOpenFile })
                ),
                _react2.default.createElement(
                    "li",
                    null,
                    _react2.default.createElement(
                        "a",
                        { href: "#", onClick: this.handleSaveClick },
                        _react2.default.createElement("i", { className: "fa fa-fw fa-floppy-o" }),
                        "Save..."
                    )
                ),
                _react2.default.createElement("li", { role: "presentation", className: "divider" }),
                _react2.default.createElement(
                    "li",
                    null,
                    _react2.default.createElement(
                        "a",
                        { href: "http://mitm.it/", target: "_blank" },
                        _react2.default.createElement("i", { className: "fa fa-fw fa-external-link" }),
                        "Install Certificates..."
                    )
                )
            )
        );
    }
});

var header_entries = [MainMenu, ViewMenu, OptionMenu /*, ReportsMenu */];

var Header = exports.Header = _react2.default.createClass({
    displayName: "Header",

    propTypes: {
        settings: _react2.default.PropTypes.object.isRequired
    },
    getInitialState: function getInitialState() {
        return {
            active: header_entries[0]
        };
    },
    handleClick: function handleClick(active, e) {
        e.preventDefault();
        this.props.updateLocation(active.route);
        this.setState({ active: active });
    },
    render: function render() {
        var header = header_entries.map(function (entry, i) {
            var className;
            if (entry === this.state.active) {
                className = "active";
            } else {
                className = "";
            }
            return _react2.default.createElement(
                "a",
                { key: i,
                    href: "#",
                    className: className,
                    onClick: this.handleClick.bind(this, entry) },
                entry.title
            );
        }.bind(this));

        return _react2.default.createElement(
            "header",
            null,
            _react2.default.createElement(
                "nav",
                { className: "nav-tabs nav-tabs-lg" },
                _react2.default.createElement(FileMenu, null),
                header
            ),
            _react2.default.createElement(
                "div",
                { className: "menu" },
                _react2.default.createElement(this.state.active, {
                    settings: this.props.settings,
                    updateLocation: this.props.updateLocation,
                    query: this.props.query
                })
            )
        );
    }
});

},{"../actions.js":2,"../filt/filt.js":29,"../utils.js":32,"./common.js":6,"./eventlog":8,"jquery":"jquery","react":"react","react-dom":"react-dom","react-redux":"react-redux"}],18:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _get = function get(object, property, receiver) { if (object === null) object = Function.prototype; var desc = Object.getOwnPropertyDescriptor(object, property); if (desc === undefined) { var parent = Object.getPrototypeOf(object); if (parent === null) { return undefined; } else { return get(parent, property, receiver); } } else if ("value" in desc) { return desc.value; } else { var getter = desc.get; if (getter === undefined) { return undefined; } return getter.call(receiver); } };

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _reactDom = require("react-dom");

var _reactDom2 = _interopRequireDefault(_reactDom);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var symShouldStick = Symbol("shouldStick");
var isAtBottom = function isAtBottom(v) {
    return v.scrollTop + v.clientHeight === v.scrollHeight;
};

exports.default = function (Component) {
    var _class, _temp;

    return Object.assign((_temp = _class = function (_Component) {
        _inherits(AutoScrollWrapper, _Component);

        function AutoScrollWrapper() {
            _classCallCheck(this, AutoScrollWrapper);

            return _possibleConstructorReturn(this, Object.getPrototypeOf(AutoScrollWrapper).apply(this, arguments));
        }

        _createClass(AutoScrollWrapper, [{
            key: "componentWillUpdate",
            value: function componentWillUpdate() {
                var viewport = _reactDom2.default.findDOMNode(this);
                this[symShouldStick] = viewport.scrollTop && isAtBottom(viewport);
                _get(Object.getPrototypeOf(AutoScrollWrapper.prototype), "componentWillUpdate", this) && _get(Object.getPrototypeOf(AutoScrollWrapper.prototype), "componentWillUpdate", this).call(this);
            }
        }, {
            key: "componentDidUpdate",
            value: function componentDidUpdate() {
                var viewport = _reactDom2.default.findDOMNode(this);
                if (this[symShouldStick] && !isAtBottom(viewport)) {
                    viewport.scrollTop = viewport.scrollHeight;
                }
                _get(Object.getPrototypeOf(AutoScrollWrapper.prototype), "componentDidUpdate", this) && _get(Object.getPrototypeOf(AutoScrollWrapper.prototype), "componentDidUpdate", this).call(this);
            }
        }]);

        return AutoScrollWrapper;
    }(Component), _class.displayName = Component.name, _temp), Component);
};

},{"react":"react","react-dom":"react-dom"}],19:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.calcVScroll = calcVScroll;
/**
 * Calculate virtual scroll stuffs
 *
 * @param {?Object} opts Options for calculation
 *
 * @returns {Object} result
 *
 * __opts__ should have following properties:
 * - {number}         itemCount
 * - {number}         rowHeight
 * - {number}         viewportTop
 * - {number}         viewportHeight
 * - {Array<?number>} [itemHeights]
 *
 * __result__ have following properties:
 * - {number} start
 * - {number} end
 * - {number} paddingTop
 * - {number} paddingBottom
 */
function calcVScroll(opts) {
    if (!opts) {
        return { start: 0, end: 0, paddingTop: 0, paddingBottom: 0 };
    }

    var itemCount = opts.itemCount;
    var rowHeight = opts.rowHeight;
    var viewportTop = opts.viewportTop;
    var viewportHeight = opts.viewportHeight;
    var itemHeights = opts.itemHeights;

    var viewportBottom = viewportTop + viewportHeight;

    var start = 0;
    var end = 0;

    var paddingTop = 0;
    var paddingBottom = 0;

    if (itemHeights) {

        for (var i = 0, pos = 0; i < itemCount; i++) {
            var height = itemHeights[i] || rowHeight;

            if (pos <= viewportTop && i % 2 === 0) {
                paddingTop = pos;
                start = i;
            }

            if (pos <= viewportBottom) {
                end = i + 1;
            } else {
                paddingBottom += height;
            }

            pos += height;
        }
    } else {

        // Make sure that we start at an even row so that CSS `:nth-child(even)` is preserved
        start = Math.max(0, Math.floor(viewportTop / rowHeight) - 1) & ~1;
        end = Math.min(itemCount, start + Math.ceil(viewportHeight / rowHeight) + 2);

        // When a large trunk of elements is removed from the button, start may be far off the viewport.
        // To make this issue less severe, limit the top placeholder to the total number of rows.
        paddingTop = Math.min(start, itemCount) * rowHeight;
        paddingBottom = Math.max(0, itemCount - end) * rowHeight;
    }

    return { start: start, end: end, paddingTop: paddingTop, paddingBottom: paddingBottom };
}

},{}],20:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _reactDom = require("react-dom");

var _reactDom2 = _interopRequireDefault(_reactDom);

var _lodash = require("lodash");

var _lodash2 = _interopRequireDefault(_lodash);

var _utils = require("../utils.js");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var Prompt = _react2.default.createClass({
    displayName: "Prompt",

    contextTypes: {
        returnFocus: _react2.default.PropTypes.func
    },
    propTypes: {
        options: _react2.default.PropTypes.array.isRequired,
        done: _react2.default.PropTypes.func.isRequired,
        prompt: _react2.default.PropTypes.string
    },
    componentDidMount: function componentDidMount() {
        _reactDom2.default.findDOMNode(this).focus();
    },
    onKeyDown: function onKeyDown(e) {
        e.stopPropagation();
        e.preventDefault();
        var opts = this.getOptions();
        for (var i = 0; i < opts.length; i++) {
            var k = opts[i].key;
            if (_utils.Key[k.toUpperCase()] === e.keyCode) {
                this.done(k);
                return;
            }
        }
        if (e.keyCode === _utils.Key.ESC || e.keyCode === _utils.Key.ENTER) {
            this.done(false);
        }
    },
    onClick: function onClick(e) {
        this.done(false);
    },
    done: function done(ret) {
        this.props.done(ret);
        this.context.returnFocus();
    },
    getOptions: function getOptions() {
        var opts = [];

        var keyTaken = function keyTaken(k) {
            return _lodash2.default.includes(_lodash2.default.pluck(opts, "key"), k);
        };

        for (var i = 0; i < this.props.options.length; i++) {
            var opt = this.props.options[i];
            if (_lodash2.default.isString(opt)) {
                var str = opt;
                while (str.length > 0 && keyTaken(str[0])) {
                    str = str.substr(1);
                }
                opt = {
                    text: opt,
                    key: str[0]
                };
            }
            if (!opt.text || !opt.key || keyTaken(opt.key)) {
                throw "invalid options";
            } else {
                opts.push(opt);
            }
        }
        return opts;
    },
    render: function render() {
        var opts = this.getOptions();
        opts = _lodash2.default.map(opts, function (o) {
            var prefix, suffix;
            var idx = o.text.indexOf(o.key);
            if (idx !== -1) {
                prefix = o.text.substring(0, idx);
                suffix = o.text.substring(idx + 1);
            } else {
                prefix = o.text + " (";
                suffix = ")";
            }
            var onClick = function (e) {
                this.done(o.key);
                e.stopPropagation();
            }.bind(this);
            return _react2.default.createElement(
                "span",
                {
                    key: o.key,
                    className: "option",
                    onClick: onClick },
                prefix,
                _react2.default.createElement(
                    "strong",
                    { className: "text-primary" },
                    o.key
                ),
                suffix
            );
        }.bind(this));
        return _react2.default.createElement(
            "div",
            { tabIndex: "0", onKeyDown: this.onKeyDown, onClick: this.onClick, className: "prompt-dialog" },
            _react2.default.createElement(
                "div",
                { className: "prompt-content" },
                this.props.prompt || _react2.default.createElement(
                    "strong",
                    null,
                    "Select: "
                ),
                opts
            )
        );
    }
});

exports.default = Prompt;

},{"../utils.js":32,"lodash":"lodash","react":"react","react-dom":"react-dom"}],21:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = Connection;

var _actions = require("./actions.js");

var _dispatcher = require("./dispatcher.js");

var _websocket = require("./ducks/websocket");

var webSocketActions = _interopRequireWildcard(_websocket);

var _eventLog = require("./ducks/eventLog");

var eventLogActions = _interopRequireWildcard(_eventLog);

var _flows = require("./ducks/flows");

var flowActions = _interopRequireWildcard(_flows);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function Connection(url, dispatch) {
    if (url[0] === "/") {
        url = location.origin.replace("http", "ws") + url;
    }

    var ws = new WebSocket(url);
    ws.onopen = function () {
        dispatch(webSocketActions.connected());
        dispatch(flowActions.fetchFlows())
        // workaround to make sure that our state is already available.
        .then(function () {
            console.log("flows are loaded now");
            _actions.ConnectionActions.open();
        });
        dispatch(eventLogActions.fetchLogEntries());
    };
    ws.onmessage = function (m) {
        var message = JSON.parse(m.data);
        _dispatcher.AppDispatcher.dispatchServerAction(message);
        switch (message.type) {
            case eventLogActions.UPDATE_LOG:
                return dispatch(eventLogActions.updateLogEntries(message));
            case flowActions.UPDATE_FLOWS:
                return dispatch(flowActions.updateFlows(message));
            default:
                console.warn("unknown message", message);
        }
    };
    ws.onerror = function () {
        _actions.ConnectionActions.error();
        dispatch(eventLogActions.addLogEntry("WebSocket connection error."));
    };
    ws.onclose = function () {
        _actions.ConnectionActions.close();
        dispatch(eventLogActions.addLogEntry("WebSocket connection closed."));
        dispatch(webSocketActions.disconnected());
    };
    return ws;
}

},{"./actions.js":2,"./dispatcher.js":22,"./ducks/eventLog":23,"./ducks/flows":24,"./ducks/websocket":28}],22:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.AppDispatcher = undefined;

var _flux = require("flux");

var _flux2 = _interopRequireDefault(_flux);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var PayloadSources = {
    VIEW: "view",
    SERVER: "server"
};

var AppDispatcher = exports.AppDispatcher = new _flux2.default.Dispatcher();
AppDispatcher.dispatchViewAction = function (action) {
    action.source = PayloadSources.VIEW;
    this.dispatch(action);
};
AppDispatcher.dispatchServerAction = function (action) {
    action.source = PayloadSources.SERVER;
    this.dispatch(action);
};

},{"flux":"flux"}],23:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.fetchLogEntries = exports.updateLogEntries = exports.UPDATE_LOG = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reducer;
exports.toggleEventLogFilter = toggleEventLogFilter;
exports.toggleEventLogVisibility = toggleEventLogVisibility;
exports.addLogEntry = addLogEntry;

var _list = require("./utils/list");

var _list2 = _interopRequireDefault(_list);

var _view = require("./utils/view");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

var TOGGLE_FILTER = 'TOGGLE_EVENTLOG_FILTER';
var TOGGLE_VISIBILITY = 'TOGGLE_EVENTLOG_VISIBILITY';
var UPDATE_LOG = exports.UPDATE_LOG = "UPDATE_EVENTLOG";

var _makeList = (0, _list2.default)(UPDATE_LOG, "/events");

var reduceList = _makeList.reduceList;
var updateList = _makeList.updateList;
var fetchList = _makeList.fetchList;
var addItem = _makeList.addItem;


var defaultState = {
    visible: false,
    filter: {
        "debug": false,
        "info": true,
        "web": true
    },
    events: reduceList(),
    filteredEvents: []
};

function reducer() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {
        case TOGGLE_FILTER:
            var filter = _extends({}, state.filter, _defineProperty({}, action.filter, !state.filter[action.filter]));
            return _extends({}, state, {
                filter: filter,
                filteredEvents: (0, _view.updateViewFilter)(state.events, function (x) {
                    return filter[x.level];
                })
            });
        case TOGGLE_VISIBILITY:
            return _extends({}, state, {
                visible: !state.visible
            });
        case UPDATE_LOG:
            var events = reduceList(state.events, action);
            return _extends({}, state, {
                events: events,
                filteredEvents: (0, _view.updateViewList)(state.filteredEvents, state.events, events, action, function (x) {
                    return state.filter[x.level];
                })
            });
        default:
            return state;
    }
}

function toggleEventLogFilter(filter) {
    return { type: TOGGLE_FILTER, filter: filter };
}
function toggleEventLogVisibility() {
    return { type: TOGGLE_VISIBILITY };
}
var id = 0;
function addLogEntry(message) {
    var level = arguments.length <= 1 || arguments[1] === undefined ? "web" : arguments[1];

    return addItem({
        message: message,
        level: level,
        id: "log-" + id++
    });
}
exports.updateLogEntries = updateList;
exports.fetchLogEntries = fetchList;

},{"./utils/list":26,"./utils/view":27}],24:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.fetchFlows = exports.updateFlows = exports.SELECT_FLOW = exports.SET_SORT = exports.SET_HIGHLIGHT = exports.SET_FILTER = exports.UPDATE_FLOWS = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reducer;
exports.setFilter = setFilter;
exports.setHighlight = setHighlight;
exports.setSort = setSort;
exports.selectFlow = selectFlow;

var _list = require("./utils/list");

var _list2 = _interopRequireDefault(_list);

var _filt = require("../filt/filt");

var _filt2 = _interopRequireDefault(_filt);

var _view = require("./utils/view");

var _utils = require("../utils.js");

var _flowtableColumns = require("../components/flowtable-columns.js");

var flow_table_columns = _interopRequireWildcard(_flowtableColumns);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var UPDATE_FLOWS = exports.UPDATE_FLOWS = "UPDATE_FLOWS";
var SET_FILTER = exports.SET_FILTER = "SET_FLOW_FILTER";
var SET_HIGHLIGHT = exports.SET_HIGHLIGHT = "SET_FLOW_HIGHLIGHT";
var SET_SORT = exports.SET_SORT = "SET_FLOW_SORT";
var SELECT_FLOW = exports.SELECT_FLOW = "SELECT_FLOW";

var _makeList = (0, _list2.default)(UPDATE_FLOWS, "/flows");

var reduceList = _makeList.reduceList;
var updateList = _makeList.updateList;
var fetchList = _makeList.fetchList;


var defaultState = {
    all: reduceList(),
    selected: [],
    view: [],
    filter: undefined,
    highlight: undefined,
    sort: { sortColumn: undefined, sortDesc: false }
};

function makeFilterFn(filter) {
    return filter ? _filt2.default.parse(filter) : function () {
        return true;
    };
}

function makeSortFn(sort) {
    var column = flow_table_columns[sort.sortColumn];
    if (!column) return;

    var sortKeyFun = column.sortKeyFun;
    if (sort.sortDesc) {
        sortKeyFun = sortKeyFun && function (flow) {
            var k = column.sortKeyFun(flow);
            return _.isString(k) ? (0, _utils.reverseString)("" + k) : -k;
        };
    }
    return sortKeyFun;
}

function reducer() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {
        case UPDATE_FLOWS:
            var all = reduceList(state.all, action);
            return _extends({}, state, {
                all: all,
                view: (0, _view.updateViewList)(state.view, state.all, all, action, makeFilterFn(action.filter), makeSortFn(state.sort))
            });
        case SET_FILTER:
            return _extends({}, state, {
                filter: action.filter,
                view: (0, _view.updateViewFilter)(state.all, makeFilterFn(action.filter), makeSortFn(state.sort))
            });
        case SET_HIGHLIGHT:
            return _extends({}, state, {
                highlight: action.highlight
            });
        case SET_SORT:
            return _extends({}, state, {
                sort: action.sort,
                view: (0, _view.updateViewSort)(state.view, makeSortFn(action.sort))
            });
        case SELECT_FLOW:
            return _extends({}, state, {
                selected: [action.flowId]
            });
        default:
            return state;
    }
}

function setFilter(filter) {
    return {
        type: SET_FILTER,
        filter: filter
    };
}
function setHighlight(highlight) {
    return {
        type: SET_HIGHLIGHT,
        highlight: highlight
    };
}
function setSort(sort) {
    return {
        type: SET_SORT,
        sort: sort
    };
}
function selectFlow(flowId) {
    return {
        type: SELECT_FLOW,
        flowId: flowId
    };
}

exports.updateFlows = updateList;
exports.fetchFlows = fetchList;

},{"../components/flowtable-columns.js":9,"../filt/filt":29,"../utils.js":32,"./utils/list":26,"./utils/view":27}],25:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _redux = require('redux');

var _eventLog = require('./eventLog');

var _eventLog2 = _interopRequireDefault(_eventLog);

var _websocket = require('./websocket');

var _websocket2 = _interopRequireDefault(_websocket);

var _flows = require('./flows');

var _flows2 = _interopRequireDefault(_flows);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var rootReducer = (0, _redux.combineReducers)({
    eventLog: _eventLog2.default,
    websocket: _websocket2.default,
    flows: _flows2.default
});

exports.default = rootReducer;

},{"./eventLog":23,"./flows":24,"./websocket":28,"redux":"redux"}],26:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.RECEIVE_LIST = exports.REQUEST_LIST = exports.REMOVE = exports.UPDATE = exports.ADD = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = makeList;

var _utils = require("../../utils");

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _toConsumableArray(arr) { if (Array.isArray(arr)) { for (var i = 0, arr2 = Array(arr.length); i < arr.length; i++) { arr2[i] = arr[i]; } return arr2; } else { return Array.from(arr); } }

var ADD = exports.ADD = "ADD";
var UPDATE = exports.UPDATE = "UPDATE";
var REMOVE = exports.REMOVE = "REMOVE";
var REQUEST_LIST = exports.REQUEST_LIST = "REQUEST_LIST";
var RECEIVE_LIST = exports.RECEIVE_LIST = "RECEIVE_LIST";

var defaultState = {
    list: [],
    isFetching: false,
    actionsDuringFetch: [],
    byId: {},
    indexOf: {}
};

function makeList(actionType, fetchURL) {
    function reduceList() {
        var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
        var action = arguments.length <= 1 || arguments[1] === undefined ? {} : arguments[1];


        if (action.type !== actionType) {
            return state;
        }

        // Handle cases where we finished fetching or are still fetching.
        if (action.cmd === RECEIVE_LIST) {
            var s = {
                isFetching: false,
                actionsDuringFetch: [],
                list: action.list,
                byId: {},
                indexOf: {}
            };
            for (var i = 0; i < action.list.length; i++) {
                var item = action.list[i];
                s.byId[item.id] = item;
                s.indexOf[item.id] = i;
            }
            var _iteratorNormalCompletion = true;
            var _didIteratorError = false;
            var _iteratorError = undefined;

            try {
                for (var _iterator = state.actionsDuringFetch[Symbol.iterator](), _step; !(_iteratorNormalCompletion = (_step = _iterator.next()).done); _iteratorNormalCompletion = true) {
                    action = _step.value;

                    s = reduceList(s, action);
                }
            } catch (err) {
                _didIteratorError = true;
                _iteratorError = err;
            } finally {
                try {
                    if (!_iteratorNormalCompletion && _iterator.return) {
                        _iterator.return();
                    }
                } finally {
                    if (_didIteratorError) {
                        throw _iteratorError;
                    }
                }
            }

            return s;
        } else if (state.isFetching) {
            return _extends({}, state, {
                actionsDuringFetch: [].concat(_toConsumableArray(state.actionsDuringFetch), [action])
            });
        }

        var list = void 0,
            itemIndex = void 0;
        switch (action.cmd) {
            case ADD:
                return {
                    list: [].concat(_toConsumableArray(state.list), [action.item]),
                    byId: _extends({}, state.byId, _defineProperty({}, action.item.id, action.item)),
                    indexOf: _extends({}, state.indexOf, _defineProperty({}, action.item.id, state.list.length))
                };

            case UPDATE:

                list = [].concat(_toConsumableArray(state.list));
                itemIndex = state.indexOf[action.item.id];
                list[itemIndex] = action.item;
                return _extends({}, state, {
                    list: list,
                    byId: _extends({}, state.byId, _defineProperty({}, action.item.id, action.item))
                });

            case REMOVE:
                list = [].concat(_toConsumableArray(state.list));
                itemIndex = state.indexOf[action.item.id];
                list.splice(itemIndex, 1);
                return _extends({}, state, {
                    list: list,
                    byId: _extends({}, state.byId, _defineProperty({}, action.item.id, undefined)),
                    indexOf: _extends({}, state.indexOf, _defineProperty({}, action.item.id, undefined))
                });

            case REQUEST_LIST:
                return _extends({}, state, {
                    isFetching: true
                });

            default:
                console.debug("unknown action", action);
                return state;
        }
    }

    function addItem(item) {
        return {
            type: actionType,
            cmd: ADD,
            item: item
        };
    }

    function updateItem(item) {
        return {
            type: actionType,
            cmd: UPDATE,
            item: item
        };
    }

    function removeItem(item) {
        return {
            type: actionType,
            cmd: REMOVE,
            item: item
        };
    }

    function updateList(event) {
        /* This action creater takes all WebSocket events */
        return function (dispatch) {
            switch (event.cmd) {
                case "add":
                    return dispatch(addItem(event.data));
                case "update":
                    return dispatch(updateItem(event.data));
                case "remove":
                    return dispatch(removeItem(event.data));
                case "reset":
                    return dispatch(fetchList());
                default:
                    console.error("unknown list update", event);
            }
        };
    }

    function requestList() {
        return {
            type: actionType,
            cmd: REQUEST_LIST
        };
    }

    function receiveList(list) {
        return {
            type: actionType,
            cmd: RECEIVE_LIST,
            list: list
        };
    }

    function fetchList() {
        return function (dispatch) {

            dispatch(requestList());

            return (0, _utils.fetchApi)(fetchURL).then(function (response) {
                return response.json().then(function (json) {
                    dispatch(receiveList(json.data));
                });
            });
        };
    }

    return { reduceList: reduceList, updateList: updateList, fetchList: fetchList, addItem: addItem, updateItem: updateItem, removeItem: removeItem };
}

},{"../../utils":32}],27:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _typeof = typeof Symbol === "function" && typeof Symbol.iterator === "symbol" ? function (obj) { return typeof obj; } : function (obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol ? "symbol" : typeof obj; };

exports.sortedIndexOf = sortedIndexOf;
exports.updateViewList = updateViewList;
exports.updateViewFilter = updateViewFilter;
exports.updateViewSort = updateViewSort;

var _list = require("./list");

function _toConsumableArray(arr) { if (Array.isArray(arr)) { for (var i = 0, arr2 = Array(arr.length); i < arr.length; i++) { arr2[i] = arr[i]; } return arr2; } else { return Array.from(arr); } }

var defaultFilterFn = function defaultFilterFn(x) {
    return true;
};
var defaultSortFn = false;

var makeCompareFn = function makeCompareFn(sortFn) {
    var compareFn = function compareFn(a, b) {
        var akey = sortFn(a),
            bkey = sortFn(b);
        if (akey < bkey) {
            return -1;
        } else if (akey > bkey) {
            return 1;
        } else {
            return 0;
        }
    };
    // need to adjust sortedIndexOf as well
    // if (sortFn.reverse)
    //    return (a, b) => compareFn(b, a)
    return compareFn;
};

var sortedInsert = function sortedInsert(list, sortFn, item) {
    var l = [].concat(_toConsumableArray(list), [item]);
    l.indexOf = function (x) {
        return sortedIndexOf(l, x, sortFn);
    };
    var compareFn = makeCompareFn(sortFn);

    // only sort if sorting order is not correct yet
    if (sortFn && compareFn(list[list.length - 1], item) > 0) {
        // TODO: This is untested
        console.debug("sorting view...");
        l.sort(compareFn);
    }
    return l;
};

var sortedRemove = function sortedRemove(list, sortFn, item) {
    var itemId = item.id;
    var l = list.filter(function (x) {
        return x.id !== itemId;
    });
    l.indexOf = function (x) {
        return sortedIndexOf(l, x, sortFn);
    };
    return l;
};

function sortedIndexOf(list, value, sortFn) {
    if (!sortFn) {
        sortFn = function sortFn(x) {
            return 0;
        }; // This triggers the linear search for flows that have the same sort value.
    }

    var low = 0,
        high = list.length,
        val = sortFn(value),
        mid = void 0;
    while (low < high) {
        mid = low + high >>> 1;
        if (sortFn(list[mid]) < val) {
            low = mid + 1;
        } else {
            high = mid;
        }
    }

    // Two flows may have the same sort value.
    // we previously determined the leftmost flow with the same sort value,
    // so no we need to scan linearly
    while (list[low].id !== value.id && sortFn(list[low + 1]) === val) {
        low++;
    }
    return low;
}

// for when the list changes
function updateViewList(currentView, currentList, nextList, action) {
    var filterFn = arguments.length <= 4 || arguments[4] === undefined ? defaultFilterFn : arguments[4];
    var sortFn = arguments.length <= 5 || arguments[5] === undefined ? defaultSortFn : arguments[5];

    switch (action.cmd) {
        case _list.REQUEST_LIST:
            return currentView;
        case _list.RECEIVE_LIST:
            return updateViewFilter(nextList, filterFn, sortFn);
        case _list.ADD:
            if (filterFn(action.item)) {
                return sortedInsert(currentView, sortFn, action.item);
            }
            return currentView;
        case _list.UPDATE:
            // let's determine if it's in the view currently and if it should be in the view.
            var currentItemState = currentList.byId[action.item.id],
                nextItemState = action.item,
                isInView = filterFn(currentItemState),
                shouldBeInView = filterFn(nextItemState);

            if (!isInView && shouldBeInView) return sortedInsert(currentView, sortFn, action.item);
            if (isInView && !shouldBeInView) return sortedRemove(currentView, sortFn, action.item);
            if (isInView && shouldBeInView) {
                var _ret = function () {
                    var s = [].concat(_toConsumableArray(currentView));
                    s.indexOf = function (x) {
                        return sortedIndexOf(s, x, sortFn);
                    };
                    s[s.indexOf(currentItemState)] = nextItemState;
                    if (sortFn && sortFn(currentItemState) !== sortFn(nextItemState)) s.sort(makeCompareFn(sortFn));
                    return {
                        v: s
                    };
                }();

                if ((typeof _ret === "undefined" ? "undefined" : _typeof(_ret)) === "object") return _ret.v;
            }
            return currentView;
        case _list.REMOVE:
            var isInView_ = filterFn(currentList.byId[action.item.id]);
            if (isInView_) {
                return sortedRemove(currentView, sortFn, action.item);
            }
            return currentView;
        default:
            console.error("Unknown list action: ", action);
            return currentView;
    }
}

function updateViewFilter(list) {
    var filterFn = arguments.length <= 1 || arguments[1] === undefined ? defaultFilterFn : arguments[1];
    var sortFn = arguments.length <= 2 || arguments[2] === undefined ? defaultSortFn : arguments[2];

    var filtered = list.list.filter(filterFn);
    if (sortFn) {
        filtered.sort(makeCompareFn(sortFn));
    }
    filtered.indexOf = function (x) {
        return sortedIndexOf(filtered, x, sortFn);
    };

    return filtered;
}

function updateViewSort(list) {
    var sortFn = arguments.length <= 1 || arguments[1] === undefined ? defaultSortFn : arguments[1];

    var sorted = list.slice(0);
    if (sortFn) {
        sorted.sort(makeCompareFn(sortFn));
    }
    sorted.indexOf = function (x) {
        return sortedIndexOf(sorted, x, sortFn);
    };

    return sorted;
}

},{"./list":26}],28:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = reducer;
exports.connected = connected;
exports.disconnected = disconnected;
var CONNECTED = 'WEBSOCKET_CONNECTED';
var DISCONNECTED = 'WEBSOCKET_DISCONNECTED';

var defaultState = {
    connected: false
};
/* we may want to have an error message attribute here at some point */
function reducer() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {
        case CONNECTED:
            return {
                connected: true
            };
        case DISCONNECTED:
            return {
                connected: false
            };
        default:
            return state;
    }
}

function connected() {
    return { type: CONNECTED };
}
function disconnected() {
    return { type: DISCONNECTED };
}

},{}],29:[function(require,module,exports){
"use strict";

module.exports = function () {
  "use strict";

  /*
   * Generated by PEG.js 0.9.0.
   *
   * http://pegjs.org/
   */

  function peg$subclass(child, parent) {
    function ctor() {
      this.constructor = child;
    }
    ctor.prototype = parent.prototype;
    child.prototype = new ctor();
  }

  function peg$SyntaxError(message, expected, found, location) {
    this.message = message;
    this.expected = expected;
    this.found = found;
    this.location = location;
    this.name = "SyntaxError";

    if (typeof Error.captureStackTrace === "function") {
      Error.captureStackTrace(this, peg$SyntaxError);
    }
  }

  peg$subclass(peg$SyntaxError, Error);

  function peg$parse(input) {
    var options = arguments.length > 1 ? arguments[1] : {},
        parser = this,
        peg$FAILED = {},
        peg$startRuleFunctions = { start: peg$parsestart },
        peg$startRuleFunction = peg$parsestart,
        peg$c0 = { type: "other", description: "filter expression" },
        peg$c1 = function peg$c1(orExpr) {
      return orExpr;
    },
        peg$c2 = { type: "other", description: "whitespace" },
        peg$c3 = /^[ \t\n\r]/,
        peg$c4 = { type: "class", value: "[ \\t\\n\\r]", description: "[ \\t\\n\\r]" },
        peg$c5 = { type: "other", description: "control character" },
        peg$c6 = /^[|&!()~"]/,
        peg$c7 = { type: "class", value: "[|&!()~\"]", description: "[|&!()~\"]" },
        peg$c8 = { type: "other", description: "optional whitespace" },
        peg$c9 = "|",
        peg$c10 = { type: "literal", value: "|", description: "\"|\"" },
        peg$c11 = function peg$c11(first, second) {
      return or(first, second);
    },
        peg$c12 = "&",
        peg$c13 = { type: "literal", value: "&", description: "\"&\"" },
        peg$c14 = function peg$c14(first, second) {
      return and(first, second);
    },
        peg$c15 = "!",
        peg$c16 = { type: "literal", value: "!", description: "\"!\"" },
        peg$c17 = function peg$c17(expr) {
      return not(expr);
    },
        peg$c18 = "(",
        peg$c19 = { type: "literal", value: "(", description: "\"(\"" },
        peg$c20 = ")",
        peg$c21 = { type: "literal", value: ")", description: "\")\"" },
        peg$c22 = function peg$c22(expr) {
      return binding(expr);
    },
        peg$c23 = "~a",
        peg$c24 = { type: "literal", value: "~a", description: "\"~a\"" },
        peg$c25 = function peg$c25() {
      return assetFilter;
    },
        peg$c26 = "~e",
        peg$c27 = { type: "literal", value: "~e", description: "\"~e\"" },
        peg$c28 = function peg$c28() {
      return errorFilter;
    },
        peg$c29 = "~q",
        peg$c30 = { type: "literal", value: "~q", description: "\"~q\"" },
        peg$c31 = function peg$c31() {
      return noResponseFilter;
    },
        peg$c32 = "~s",
        peg$c33 = { type: "literal", value: "~s", description: "\"~s\"" },
        peg$c34 = function peg$c34() {
      return responseFilter;
    },
        peg$c35 = "true",
        peg$c36 = { type: "literal", value: "true", description: "\"true\"" },
        peg$c37 = function peg$c37() {
      return trueFilter;
    },
        peg$c38 = "false",
        peg$c39 = { type: "literal", value: "false", description: "\"false\"" },
        peg$c40 = function peg$c40() {
      return falseFilter;
    },
        peg$c41 = "~c",
        peg$c42 = { type: "literal", value: "~c", description: "\"~c\"" },
        peg$c43 = function peg$c43(s) {
      return responseCode(s);
    },
        peg$c44 = "~d",
        peg$c45 = { type: "literal", value: "~d", description: "\"~d\"" },
        peg$c46 = function peg$c46(s) {
      return domain(s);
    },
        peg$c47 = "~h",
        peg$c48 = { type: "literal", value: "~h", description: "\"~h\"" },
        peg$c49 = function peg$c49(s) {
      return header(s);
    },
        peg$c50 = "~hq",
        peg$c51 = { type: "literal", value: "~hq", description: "\"~hq\"" },
        peg$c52 = function peg$c52(s) {
      return requestHeader(s);
    },
        peg$c53 = "~hs",
        peg$c54 = { type: "literal", value: "~hs", description: "\"~hs\"" },
        peg$c55 = function peg$c55(s) {
      return responseHeader(s);
    },
        peg$c56 = "~m",
        peg$c57 = { type: "literal", value: "~m", description: "\"~m\"" },
        peg$c58 = function peg$c58(s) {
      return method(s);
    },
        peg$c59 = "~t",
        peg$c60 = { type: "literal", value: "~t", description: "\"~t\"" },
        peg$c61 = function peg$c61(s) {
      return contentType(s);
    },
        peg$c62 = "~tq",
        peg$c63 = { type: "literal", value: "~tq", description: "\"~tq\"" },
        peg$c64 = function peg$c64(s) {
      return requestContentType(s);
    },
        peg$c65 = "~ts",
        peg$c66 = { type: "literal", value: "~ts", description: "\"~ts\"" },
        peg$c67 = function peg$c67(s) {
      return responseContentType(s);
    },
        peg$c68 = "~u",
        peg$c69 = { type: "literal", value: "~u", description: "\"~u\"" },
        peg$c70 = function peg$c70(s) {
      return url(s);
    },
        peg$c71 = { type: "other", description: "integer" },
        peg$c72 = /^['"]/,
        peg$c73 = { type: "class", value: "['\"]", description: "['\"]" },
        peg$c74 = /^[0-9]/,
        peg$c75 = { type: "class", value: "[0-9]", description: "[0-9]" },
        peg$c76 = function peg$c76(digits) {
      return parseInt(digits.join(""), 10);
    },
        peg$c77 = { type: "other", description: "string" },
        peg$c78 = "\"",
        peg$c79 = { type: "literal", value: "\"", description: "\"\\\"\"" },
        peg$c80 = function peg$c80(chars) {
      return chars.join("");
    },
        peg$c81 = "'",
        peg$c82 = { type: "literal", value: "'", description: "\"'\"" },
        peg$c83 = /^["\\]/,
        peg$c84 = { type: "class", value: "[\"\\\\]", description: "[\"\\\\]" },
        peg$c85 = { type: "any", description: "any character" },
        peg$c86 = function peg$c86(char) {
      return char;
    },
        peg$c87 = "\\",
        peg$c88 = { type: "literal", value: "\\", description: "\"\\\\\"" },
        peg$c89 = /^['\\]/,
        peg$c90 = { type: "class", value: "['\\\\]", description: "['\\\\]" },
        peg$c91 = /^['"\\]/,
        peg$c92 = { type: "class", value: "['\"\\\\]", description: "['\"\\\\]" },
        peg$c93 = "n",
        peg$c94 = { type: "literal", value: "n", description: "\"n\"" },
        peg$c95 = function peg$c95() {
      return "\n";
    },
        peg$c96 = "r",
        peg$c97 = { type: "literal", value: "r", description: "\"r\"" },
        peg$c98 = function peg$c98() {
      return "\r";
    },
        peg$c99 = "t",
        peg$c100 = { type: "literal", value: "t", description: "\"t\"" },
        peg$c101 = function peg$c101() {
      return "\t";
    },
        peg$currPos = 0,
        peg$savedPos = 0,
        peg$posDetailsCache = [{ line: 1, column: 1, seenCR: false }],
        peg$maxFailPos = 0,
        peg$maxFailExpected = [],
        peg$silentFails = 0,
        peg$result;

    if ("startRule" in options) {
      if (!(options.startRule in peg$startRuleFunctions)) {
        throw new Error("Can't start parsing from rule \"" + options.startRule + "\".");
      }

      peg$startRuleFunction = peg$startRuleFunctions[options.startRule];
    }

    function text() {
      return input.substring(peg$savedPos, peg$currPos);
    }

    function location() {
      return peg$computeLocation(peg$savedPos, peg$currPos);
    }

    function expected(description) {
      throw peg$buildException(null, [{ type: "other", description: description }], input.substring(peg$savedPos, peg$currPos), peg$computeLocation(peg$savedPos, peg$currPos));
    }

    function error(message) {
      throw peg$buildException(message, null, input.substring(peg$savedPos, peg$currPos), peg$computeLocation(peg$savedPos, peg$currPos));
    }

    function peg$computePosDetails(pos) {
      var details = peg$posDetailsCache[pos],
          p,
          ch;

      if (details) {
        return details;
      } else {
        p = pos - 1;
        while (!peg$posDetailsCache[p]) {
          p--;
        }

        details = peg$posDetailsCache[p];
        details = {
          line: details.line,
          column: details.column,
          seenCR: details.seenCR
        };

        while (p < pos) {
          ch = input.charAt(p);
          if (ch === "\n") {
            if (!details.seenCR) {
              details.line++;
            }
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

          p++;
        }

        peg$posDetailsCache[pos] = details;
        return details;
      }
    }

    function peg$computeLocation(startPos, endPos) {
      var startPosDetails = peg$computePosDetails(startPos),
          endPosDetails = peg$computePosDetails(endPos);

      return {
        start: {
          offset: startPos,
          line: startPosDetails.line,
          column: startPosDetails.column
        },
        end: {
          offset: endPos,
          line: endPosDetails.line,
          column: endPosDetails.column
        }
      };
    }

    function peg$fail(expected) {
      if (peg$currPos < peg$maxFailPos) {
        return;
      }

      if (peg$currPos > peg$maxFailPos) {
        peg$maxFailPos = peg$currPos;
        peg$maxFailExpected = [];
      }

      peg$maxFailExpected.push(expected);
    }

    function peg$buildException(message, expected, found, location) {
      function cleanupExpected(expected) {
        var i = 1;

        expected.sort(function (a, b) {
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
          function hex(ch) {
            return ch.charCodeAt(0).toString(16).toUpperCase();
          }

          return s.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\x08/g, '\\b').replace(/\t/g, '\\t').replace(/\n/g, '\\n').replace(/\f/g, '\\f').replace(/\r/g, '\\r').replace(/[\x00-\x07\x0B\x0E\x0F]/g, function (ch) {
            return '\\x0' + hex(ch);
          }).replace(/[\x10-\x1F\x80-\xFF]/g, function (ch) {
            return '\\x' + hex(ch);
          }).replace(/[\u0100-\u0FFF]/g, function (ch) {
            return "\\u0" + hex(ch);
          }).replace(/[\u1000-\uFFFF]/g, function (ch) {
            return "\\u" + hex(ch);
          });
        }

        var expectedDescs = new Array(expected.length),
            expectedDesc,
            foundDesc,
            i;

        for (i = 0; i < expected.length; i++) {
          expectedDescs[i] = expected[i].description;
        }

        expectedDesc = expected.length > 1 ? expectedDescs.slice(0, -1).join(", ") + " or " + expectedDescs[expected.length - 1] : expectedDescs[0];

        foundDesc = found ? "\"" + stringEscape(found) + "\"" : "end of input";

        return "Expected " + expectedDesc + " but " + foundDesc + " found.";
      }

      if (expected !== null) {
        cleanupExpected(expected);
      }

      return new peg$SyntaxError(message !== null ? message : buildMessage(expected, found), expected, found, location);
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
            peg$savedPos = s0;
            s1 = peg$c1(s2);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$FAILED;
      }
      peg$silentFails--;
      if (s0 === peg$FAILED) {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c0);
        }
      }

      return s0;
    }

    function peg$parsews() {
      var s0, s1;

      peg$silentFails++;
      if (peg$c3.test(input.charAt(peg$currPos))) {
        s0 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s0 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c4);
        }
      }
      peg$silentFails--;
      if (s0 === peg$FAILED) {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c2);
        }
      }

      return s0;
    }

    function peg$parsecc() {
      var s0, s1;

      peg$silentFails++;
      if (peg$c6.test(input.charAt(peg$currPos))) {
        s0 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s0 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c7);
        }
      }
      peg$silentFails--;
      if (s0 === peg$FAILED) {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c5);
        }
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
        if (peg$silentFails === 0) {
          peg$fail(peg$c8);
        }
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
            s3 = peg$c9;
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c10);
            }
          }
          if (s3 !== peg$FAILED) {
            s4 = peg$parse__();
            if (s4 !== peg$FAILED) {
              s5 = peg$parseOrExpr();
              if (s5 !== peg$FAILED) {
                peg$savedPos = s0;
                s1 = peg$c11(s1, s5);
                s0 = s1;
              } else {
                peg$currPos = s0;
                s0 = peg$FAILED;
              }
            } else {
              peg$currPos = s0;
              s0 = peg$FAILED;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$FAILED;
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
            s3 = peg$c12;
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c13);
            }
          }
          if (s3 !== peg$FAILED) {
            s4 = peg$parse__();
            if (s4 !== peg$FAILED) {
              s5 = peg$parseAndExpr();
              if (s5 !== peg$FAILED) {
                peg$savedPos = s0;
                s1 = peg$c14(s1, s5);
                s0 = s1;
              } else {
                peg$currPos = s0;
                s0 = peg$FAILED;
              }
            } else {
              peg$currPos = s0;
              s0 = peg$FAILED;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$FAILED;
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
            s2 = peg$FAILED;
          }
          if (s2 !== peg$FAILED) {
            s3 = peg$parseAndExpr();
            if (s3 !== peg$FAILED) {
              peg$savedPos = s0;
              s1 = peg$c14(s1, s3);
              s0 = s1;
            } else {
              peg$currPos = s0;
              s0 = peg$FAILED;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
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
        s1 = peg$c15;
        peg$currPos++;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c16);
        }
      }
      if (s1 !== peg$FAILED) {
        s2 = peg$parse__();
        if (s2 !== peg$FAILED) {
          s3 = peg$parseNotExpr();
          if (s3 !== peg$FAILED) {
            peg$savedPos = s0;
            s1 = peg$c17(s3);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$FAILED;
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
        s1 = peg$c18;
        peg$currPos++;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c19);
        }
      }
      if (s1 !== peg$FAILED) {
        s2 = peg$parse__();
        if (s2 !== peg$FAILED) {
          s3 = peg$parseOrExpr();
          if (s3 !== peg$FAILED) {
            s4 = peg$parse__();
            if (s4 !== peg$FAILED) {
              if (input.charCodeAt(peg$currPos) === 41) {
                s5 = peg$c20;
                peg$currPos++;
              } else {
                s5 = peg$FAILED;
                if (peg$silentFails === 0) {
                  peg$fail(peg$c21);
                }
              }
              if (s5 !== peg$FAILED) {
                peg$savedPos = s0;
                s1 = peg$c22(s3);
                s0 = s1;
              } else {
                peg$currPos = s0;
                s0 = peg$FAILED;
              }
            } else {
              peg$currPos = s0;
              s0 = peg$FAILED;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$FAILED;
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
        if (input.substr(peg$currPos, 2) === peg$c23) {
          s1 = peg$c23;
          peg$currPos += 2;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c24);
          }
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c25();
        }
        s0 = s1;
        if (s0 === peg$FAILED) {
          s0 = peg$currPos;
          if (input.substr(peg$currPos, 2) === peg$c26) {
            s1 = peg$c26;
            peg$currPos += 2;
          } else {
            s1 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c27);
            }
          }
          if (s1 !== peg$FAILED) {
            peg$savedPos = s0;
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
              if (peg$silentFails === 0) {
                peg$fail(peg$c30);
              }
            }
            if (s1 !== peg$FAILED) {
              peg$savedPos = s0;
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
                if (peg$silentFails === 0) {
                  peg$fail(peg$c33);
                }
              }
              if (s1 !== peg$FAILED) {
                peg$savedPos = s0;
                s1 = peg$c34();
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
      if (input.substr(peg$currPos, 4) === peg$c35) {
        s1 = peg$c35;
        peg$currPos += 4;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c36);
        }
      }
      if (s1 !== peg$FAILED) {
        peg$savedPos = s0;
        s1 = peg$c37();
      }
      s0 = s1;
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.substr(peg$currPos, 5) === peg$c38) {
          s1 = peg$c38;
          peg$currPos += 5;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c39);
          }
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c40();
        }
        s0 = s1;
      }

      return s0;
    }

    function peg$parseUnaryExpr() {
      var s0, s1, s2, s3;

      s0 = peg$currPos;
      if (input.substr(peg$currPos, 2) === peg$c41) {
        s1 = peg$c41;
        peg$currPos += 2;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c42);
        }
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
          s2 = peg$FAILED;
        }
        if (s2 !== peg$FAILED) {
          s3 = peg$parseIntegerLiteral();
          if (s3 !== peg$FAILED) {
            peg$savedPos = s0;
            s1 = peg$c43(s3);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$FAILED;
      }
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.substr(peg$currPos, 2) === peg$c44) {
          s1 = peg$c44;
          peg$currPos += 2;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c45);
          }
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
            s2 = peg$FAILED;
          }
          if (s2 !== peg$FAILED) {
            s3 = peg$parseStringLiteral();
            if (s3 !== peg$FAILED) {
              peg$savedPos = s0;
              s1 = peg$c46(s3);
              s0 = s1;
            } else {
              peg$currPos = s0;
              s0 = peg$FAILED;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
        if (s0 === peg$FAILED) {
          s0 = peg$currPos;
          if (input.substr(peg$currPos, 2) === peg$c47) {
            s1 = peg$c47;
            peg$currPos += 2;
          } else {
            s1 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c48);
            }
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
              s2 = peg$FAILED;
            }
            if (s2 !== peg$FAILED) {
              s3 = peg$parseStringLiteral();
              if (s3 !== peg$FAILED) {
                peg$savedPos = s0;
                s1 = peg$c49(s3);
                s0 = s1;
              } else {
                peg$currPos = s0;
                s0 = peg$FAILED;
              }
            } else {
              peg$currPos = s0;
              s0 = peg$FAILED;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
          if (s0 === peg$FAILED) {
            s0 = peg$currPos;
            if (input.substr(peg$currPos, 3) === peg$c50) {
              s1 = peg$c50;
              peg$currPos += 3;
            } else {
              s1 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c51);
              }
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
                s2 = peg$FAILED;
              }
              if (s2 !== peg$FAILED) {
                s3 = peg$parseStringLiteral();
                if (s3 !== peg$FAILED) {
                  peg$savedPos = s0;
                  s1 = peg$c52(s3);
                  s0 = s1;
                } else {
                  peg$currPos = s0;
                  s0 = peg$FAILED;
                }
              } else {
                peg$currPos = s0;
                s0 = peg$FAILED;
              }
            } else {
              peg$currPos = s0;
              s0 = peg$FAILED;
            }
            if (s0 === peg$FAILED) {
              s0 = peg$currPos;
              if (input.substr(peg$currPos, 3) === peg$c53) {
                s1 = peg$c53;
                peg$currPos += 3;
              } else {
                s1 = peg$FAILED;
                if (peg$silentFails === 0) {
                  peg$fail(peg$c54);
                }
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
                  s2 = peg$FAILED;
                }
                if (s2 !== peg$FAILED) {
                  s3 = peg$parseStringLiteral();
                  if (s3 !== peg$FAILED) {
                    peg$savedPos = s0;
                    s1 = peg$c55(s3);
                    s0 = s1;
                  } else {
                    peg$currPos = s0;
                    s0 = peg$FAILED;
                  }
                } else {
                  peg$currPos = s0;
                  s0 = peg$FAILED;
                }
              } else {
                peg$currPos = s0;
                s0 = peg$FAILED;
              }
              if (s0 === peg$FAILED) {
                s0 = peg$currPos;
                if (input.substr(peg$currPos, 2) === peg$c56) {
                  s1 = peg$c56;
                  peg$currPos += 2;
                } else {
                  s1 = peg$FAILED;
                  if (peg$silentFails === 0) {
                    peg$fail(peg$c57);
                  }
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
                    s2 = peg$FAILED;
                  }
                  if (s2 !== peg$FAILED) {
                    s3 = peg$parseStringLiteral();
                    if (s3 !== peg$FAILED) {
                      peg$savedPos = s0;
                      s1 = peg$c58(s3);
                      s0 = s1;
                    } else {
                      peg$currPos = s0;
                      s0 = peg$FAILED;
                    }
                  } else {
                    peg$currPos = s0;
                    s0 = peg$FAILED;
                  }
                } else {
                  peg$currPos = s0;
                  s0 = peg$FAILED;
                }
                if (s0 === peg$FAILED) {
                  s0 = peg$currPos;
                  if (input.substr(peg$currPos, 2) === peg$c59) {
                    s1 = peg$c59;
                    peg$currPos += 2;
                  } else {
                    s1 = peg$FAILED;
                    if (peg$silentFails === 0) {
                      peg$fail(peg$c60);
                    }
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
                      s2 = peg$FAILED;
                    }
                    if (s2 !== peg$FAILED) {
                      s3 = peg$parseStringLiteral();
                      if (s3 !== peg$FAILED) {
                        peg$savedPos = s0;
                        s1 = peg$c61(s3);
                        s0 = s1;
                      } else {
                        peg$currPos = s0;
                        s0 = peg$FAILED;
                      }
                    } else {
                      peg$currPos = s0;
                      s0 = peg$FAILED;
                    }
                  } else {
                    peg$currPos = s0;
                    s0 = peg$FAILED;
                  }
                  if (s0 === peg$FAILED) {
                    s0 = peg$currPos;
                    if (input.substr(peg$currPos, 3) === peg$c62) {
                      s1 = peg$c62;
                      peg$currPos += 3;
                    } else {
                      s1 = peg$FAILED;
                      if (peg$silentFails === 0) {
                        peg$fail(peg$c63);
                      }
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
                        s2 = peg$FAILED;
                      }
                      if (s2 !== peg$FAILED) {
                        s3 = peg$parseStringLiteral();
                        if (s3 !== peg$FAILED) {
                          peg$savedPos = s0;
                          s1 = peg$c64(s3);
                          s0 = s1;
                        } else {
                          peg$currPos = s0;
                          s0 = peg$FAILED;
                        }
                      } else {
                        peg$currPos = s0;
                        s0 = peg$FAILED;
                      }
                    } else {
                      peg$currPos = s0;
                      s0 = peg$FAILED;
                    }
                    if (s0 === peg$FAILED) {
                      s0 = peg$currPos;
                      if (input.substr(peg$currPos, 3) === peg$c65) {
                        s1 = peg$c65;
                        peg$currPos += 3;
                      } else {
                        s1 = peg$FAILED;
                        if (peg$silentFails === 0) {
                          peg$fail(peg$c66);
                        }
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
                          s2 = peg$FAILED;
                        }
                        if (s2 !== peg$FAILED) {
                          s3 = peg$parseStringLiteral();
                          if (s3 !== peg$FAILED) {
                            peg$savedPos = s0;
                            s1 = peg$c67(s3);
                            s0 = s1;
                          } else {
                            peg$currPos = s0;
                            s0 = peg$FAILED;
                          }
                        } else {
                          peg$currPos = s0;
                          s0 = peg$FAILED;
                        }
                      } else {
                        peg$currPos = s0;
                        s0 = peg$FAILED;
                      }
                      if (s0 === peg$FAILED) {
                        s0 = peg$currPos;
                        if (input.substr(peg$currPos, 2) === peg$c68) {
                          s1 = peg$c68;
                          peg$currPos += 2;
                        } else {
                          s1 = peg$FAILED;
                          if (peg$silentFails === 0) {
                            peg$fail(peg$c69);
                          }
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
                            s2 = peg$FAILED;
                          }
                          if (s2 !== peg$FAILED) {
                            s3 = peg$parseStringLiteral();
                            if (s3 !== peg$FAILED) {
                              peg$savedPos = s0;
                              s1 = peg$c70(s3);
                              s0 = s1;
                            } else {
                              peg$currPos = s0;
                              s0 = peg$FAILED;
                            }
                          } else {
                            peg$currPos = s0;
                            s0 = peg$FAILED;
                          }
                        } else {
                          peg$currPos = s0;
                          s0 = peg$FAILED;
                        }
                        if (s0 === peg$FAILED) {
                          s0 = peg$currPos;
                          s1 = peg$parseStringLiteral();
                          if (s1 !== peg$FAILED) {
                            peg$savedPos = s0;
                            s1 = peg$c70(s1);
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
      if (peg$c72.test(input.charAt(peg$currPos))) {
        s1 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c73);
        }
      }
      if (s1 === peg$FAILED) {
        s1 = null;
      }
      if (s1 !== peg$FAILED) {
        s2 = [];
        if (peg$c74.test(input.charAt(peg$currPos))) {
          s3 = input.charAt(peg$currPos);
          peg$currPos++;
        } else {
          s3 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c75);
          }
        }
        if (s3 !== peg$FAILED) {
          while (s3 !== peg$FAILED) {
            s2.push(s3);
            if (peg$c74.test(input.charAt(peg$currPos))) {
              s3 = input.charAt(peg$currPos);
              peg$currPos++;
            } else {
              s3 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c75);
              }
            }
          }
        } else {
          s2 = peg$FAILED;
        }
        if (s2 !== peg$FAILED) {
          if (peg$c72.test(input.charAt(peg$currPos))) {
            s3 = input.charAt(peg$currPos);
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c73);
            }
          }
          if (s3 === peg$FAILED) {
            s3 = null;
          }
          if (s3 !== peg$FAILED) {
            peg$savedPos = s0;
            s1 = peg$c76(s2);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$FAILED;
      }
      peg$silentFails--;
      if (s0 === peg$FAILED) {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c71);
        }
      }

      return s0;
    }

    function peg$parseStringLiteral() {
      var s0, s1, s2, s3;

      peg$silentFails++;
      s0 = peg$currPos;
      if (input.charCodeAt(peg$currPos) === 34) {
        s1 = peg$c78;
        peg$currPos++;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c79);
        }
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
            s3 = peg$c78;
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c79);
            }
          }
          if (s3 !== peg$FAILED) {
            peg$savedPos = s0;
            s1 = peg$c80(s2);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$FAILED;
      }
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 39) {
          s1 = peg$c81;
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c82);
          }
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
              s3 = peg$c81;
              peg$currPos++;
            } else {
              s3 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c82);
              }
            }
            if (s3 !== peg$FAILED) {
              peg$savedPos = s0;
              s1 = peg$c80(s2);
              s0 = s1;
            } else {
              peg$currPos = s0;
              s0 = peg$FAILED;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
        if (s0 === peg$FAILED) {
          s0 = peg$currPos;
          s1 = peg$currPos;
          peg$silentFails++;
          s2 = peg$parsecc();
          peg$silentFails--;
          if (s2 === peg$FAILED) {
            s1 = void 0;
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
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
              s2 = peg$FAILED;
            }
            if (s2 !== peg$FAILED) {
              peg$savedPos = s0;
              s1 = peg$c80(s2);
              s0 = s1;
            } else {
              peg$currPos = s0;
              s0 = peg$FAILED;
            }
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        }
      }
      peg$silentFails--;
      if (s0 === peg$FAILED) {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c77);
        }
      }

      return s0;
    }

    function peg$parseDoubleStringChar() {
      var s0, s1, s2;

      s0 = peg$currPos;
      s1 = peg$currPos;
      peg$silentFails++;
      if (peg$c83.test(input.charAt(peg$currPos))) {
        s2 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s2 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c84);
        }
      }
      peg$silentFails--;
      if (s2 === peg$FAILED) {
        s1 = void 0;
      } else {
        peg$currPos = s1;
        s1 = peg$FAILED;
      }
      if (s1 !== peg$FAILED) {
        if (input.length > peg$currPos) {
          s2 = input.charAt(peg$currPos);
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c85);
          }
        }
        if (s2 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c86(s2);
          s0 = s1;
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$FAILED;
      }
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 92) {
          s1 = peg$c87;
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c88);
          }
        }
        if (s1 !== peg$FAILED) {
          s2 = peg$parseEscapeSequence();
          if (s2 !== peg$FAILED) {
            peg$savedPos = s0;
            s1 = peg$c86(s2);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
      }

      return s0;
    }

    function peg$parseSingleStringChar() {
      var s0, s1, s2;

      s0 = peg$currPos;
      s1 = peg$currPos;
      peg$silentFails++;
      if (peg$c89.test(input.charAt(peg$currPos))) {
        s2 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s2 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c90);
        }
      }
      peg$silentFails--;
      if (s2 === peg$FAILED) {
        s1 = void 0;
      } else {
        peg$currPos = s1;
        s1 = peg$FAILED;
      }
      if (s1 !== peg$FAILED) {
        if (input.length > peg$currPos) {
          s2 = input.charAt(peg$currPos);
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c85);
          }
        }
        if (s2 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c86(s2);
          s0 = s1;
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$FAILED;
      }
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 92) {
          s1 = peg$c87;
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c88);
          }
        }
        if (s1 !== peg$FAILED) {
          s2 = peg$parseEscapeSequence();
          if (s2 !== peg$FAILED) {
            peg$savedPos = s0;
            s1 = peg$c86(s2);
            s0 = s1;
          } else {
            peg$currPos = s0;
            s0 = peg$FAILED;
          }
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
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
        s1 = void 0;
      } else {
        peg$currPos = s1;
        s1 = peg$FAILED;
      }
      if (s1 !== peg$FAILED) {
        if (input.length > peg$currPos) {
          s2 = input.charAt(peg$currPos);
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c85);
          }
        }
        if (s2 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c86(s2);
          s0 = s1;
        } else {
          peg$currPos = s0;
          s0 = peg$FAILED;
        }
      } else {
        peg$currPos = s0;
        s0 = peg$FAILED;
      }

      return s0;
    }

    function peg$parseEscapeSequence() {
      var s0, s1;

      if (peg$c91.test(input.charAt(peg$currPos))) {
        s0 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s0 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c92);
        }
      }
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 110) {
          s1 = peg$c93;
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c94);
          }
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c95();
        }
        s0 = s1;
        if (s0 === peg$FAILED) {
          s0 = peg$currPos;
          if (input.charCodeAt(peg$currPos) === 114) {
            s1 = peg$c96;
            peg$currPos++;
          } else {
            s1 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c97);
            }
          }
          if (s1 !== peg$FAILED) {
            peg$savedPos = s0;
            s1 = peg$c98();
          }
          s0 = s1;
          if (s0 === peg$FAILED) {
            s0 = peg$currPos;
            if (input.charCodeAt(peg$currPos) === 116) {
              s1 = peg$c99;
              peg$currPos++;
            } else {
              s1 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c100);
              }
            }
            if (s1 !== peg$FAILED) {
              peg$savedPos = s0;
              s1 = peg$c101();
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

    var ASSET_TYPES = [new RegExp("text/javascript"), new RegExp("application/x-javascript"), new RegExp("application/javascript"), new RegExp("text/css"), new RegExp("image/.*"), new RegExp("application/x-shockwave-flash")];
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
    function responseCode(code) {
      function responseCodeFilter(flow) {
        return flow.response && flow.response.status_code === code;
      }
      responseCodeFilter.desc = "resp. code is " + code;
      return responseCodeFilter;
    }
    function domain(regex) {
      regex = new RegExp(regex, "i");
      function domainFilter(flow) {
        return flow.request && regex.test(flow.request.host);
      }
      domainFilter.desc = "domain matches " + regex;
      return domainFilter;
    }
    function errorFilter(flow) {
      return !!flow.error;
    }
    errorFilter.desc = "has error";
    function header(regex) {
      regex = new RegExp(regex, "i");
      function headerFilter(flow) {
        return flow.request && flowutils.RequestUtils.match_header(flow.request, regex) || flow.response && flowutils.ResponseUtils.match_header(flow.response, regex);
      }
      headerFilter.desc = "header matches " + regex;
      return headerFilter;
    }
    function requestHeader(regex) {
      regex = new RegExp(regex, "i");
      function requestHeaderFilter(flow) {
        return flow.request && flowutils.RequestUtils.match_header(flow.request, regex);
      }
      requestHeaderFilter.desc = "req. header matches " + regex;
      return requestHeaderFilter;
    }
    function responseHeader(regex) {
      regex = new RegExp(regex, "i");
      function responseHeaderFilter(flow) {
        return flow.response && flowutils.ResponseUtils.match_header(flow.response, regex);
      }
      responseHeaderFilter.desc = "resp. header matches " + regex;
      return responseHeaderFilter;
    }
    function method(regex) {
      regex = new RegExp(regex, "i");
      function methodFilter(flow) {
        return flow.request && regex.test(flow.request.method);
      }
      methodFilter.desc = "method matches " + regex;
      return methodFilter;
    }
    function noResponseFilter(flow) {
      return flow.request && !flow.response;
    }
    noResponseFilter.desc = "has no response";
    function responseFilter(flow) {
      return !!flow.response;
    }
    responseFilter.desc = "has response";

    function contentType(regex) {
      regex = new RegExp(regex, "i");
      function contentTypeFilter(flow) {
        return flow.request && regex.test(flowutils.RequestUtils.getContentType(flow.request)) || flow.response && regex.test(flowutils.ResponseUtils.getContentType(flow.response));
      }
      contentTypeFilter.desc = "content type matches " + regex;
      return contentTypeFilter;
    }
    function requestContentType(regex) {
      regex = new RegExp(regex, "i");
      function requestContentTypeFilter(flow) {
        return flow.request && regex.test(flowutils.RequestUtils.getContentType(flow.request));
      }
      requestContentTypeFilter.desc = "req. content type matches " + regex;
      return requestContentTypeFilter;
    }
    function responseContentType(regex) {
      regex = new RegExp(regex, "i");
      function responseContentTypeFilter(flow) {
        return flow.response && regex.test(flowutils.ResponseUtils.getContentType(flow.response));
      }
      responseContentTypeFilter.desc = "resp. content type matches " + regex;
      return responseContentTypeFilter;
    }
    function url(regex) {
      regex = new RegExp(regex, "i");
      function urlFilter(flow) {
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

      throw peg$buildException(null, peg$maxFailExpected, peg$maxFailPos < input.length ? input.charAt(peg$maxFailPos) : null, peg$maxFailPos < input.length ? peg$computeLocation(peg$maxFailPos, peg$maxFailPos + 1) : peg$computeLocation(peg$maxFailPos, peg$maxFailPos));
    }
  }

  return {
    SyntaxError: peg$SyntaxError,
    parse: peg$parse
  };
}();

},{"../flow/utils.js":30}],30:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.parseHttpVersion = exports.isValidHttpVersion = exports.parseUrl = exports.ResponseUtils = exports.RequestUtils = exports.MessageUtils = undefined;

var _lodash = require("lodash");

var _lodash2 = _interopRequireDefault(_lodash);

var _jquery = require("jquery");

var _jquery2 = _interopRequireDefault(_jquery);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var defaultPorts = {
    "http": 80,
    "https": 443
};

var MessageUtils = exports.MessageUtils = {
    getContentType: function getContentType(message) {
        var ct = this.get_first_header(message, /^Content-Type$/i);
        if (ct) {
            return ct.split(";")[0].trim();
        }
    },
    get_first_header: function get_first_header(message, regex) {
        //FIXME: Cache Invalidation.
        if (!message._headerLookups) Object.defineProperty(message, "_headerLookups", {
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
    match_header: function match_header(message, regex) {
        var headers = message.headers;
        var i = headers.length;
        while (i--) {
            if (regex.test(headers[i].join(" "))) {
                return headers[i];
            }
        }
        return false;
    },
    getContentURL: function getContentURL(flow, message) {
        if (message === flow.request) {
            message = "request";
        } else if (message === flow.response) {
            message = "response";
        }
        return "/flows/" + flow.id + "/" + message + "/content";
    },
    getContent: function getContent(flow, message) {
        var url = MessageUtils.getContentURL(flow, message);
        return _jquery2.default.get(url);
    }
};

var RequestUtils = exports.RequestUtils = _lodash2.default.extend(MessageUtils, {
    pretty_host: function pretty_host(request) {
        //FIXME: Add hostheader
        return request.host;
    },
    pretty_url: function pretty_url(request) {
        var port = "";
        if (defaultPorts[request.scheme] !== request.port) {
            port = ":" + request.port;
        }
        return request.scheme + "://" + this.pretty_host(request) + port + request.path;
    }
});

var ResponseUtils = exports.ResponseUtils = _lodash2.default.extend(MessageUtils, {});

var parseUrl_regex = /^(?:(https?):\/\/)?([^\/:]+)?(?::(\d+))?(\/.*)?$/i;
var parseUrl = exports.parseUrl = function parseUrl(url) {
    //there are many correct ways to parse a URL,
    //however, a mitmproxy user may also wish to generate a not-so-correct URL. ;-)
    var parts = parseUrl_regex.exec(url);
    if (!parts) {
        return false;
    }

    var scheme = parts[1],
        host = parts[2],
        port = parseInt(parts[3]),
        path = parts[4];
    if (scheme) {
        port = port || defaultPorts[scheme];
    }
    var ret = {};
    if (scheme) {
        ret.scheme = scheme;
    }
    if (host) {
        ret.host = host;
    }
    if (port) {
        ret.port = port;
    }
    if (path) {
        ret.path = path;
    }
    return ret;
};

var isValidHttpVersion_regex = /^HTTP\/\d+(\.\d+)*$/i;
var isValidHttpVersion = exports.isValidHttpVersion = function isValidHttpVersion(httpVersion) {
    return isValidHttpVersion_regex.test(httpVersion);
};

var parseHttpVersion = exports.parseHttpVersion = function parseHttpVersion(httpVersion) {
    httpVersion = httpVersion.replace("HTTP/", "").split(".");
    return _lodash2.default.map(httpVersion, function (x) {
        return parseInt(x);
    });
};

},{"jquery":"jquery","lodash":"lodash"}],31:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.SettingsStore = SettingsStore;

var _lodash = require("lodash");

var _lodash2 = _interopRequireDefault(_lodash);

var _jquery = require("jquery");

var _jquery2 = _interopRequireDefault(_jquery);

var _events = require("events");

var _actions = require("../actions.js");

var _dispatcher = require("../dispatcher.js");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function DictStore() {
    _events.EventEmitter.call(this);
    this.reset();
}
_lodash2.default.extend(DictStore.prototype, _events.EventEmitter.prototype, {
    update: function update(dict) {
        _lodash2.default.merge(this.dict, dict);
        this.emit("recalculate");
    },
    reset: function reset(dict) {
        this.dict = dict || {};
        this.emit("recalculate");
    }
});

function LiveStoreMixin(type) {
    this.type = type;

    this._updates_before_fetch = undefined;
    this._fetchxhr = false;

    this.handle = this.handle.bind(this);
    _dispatcher.AppDispatcher.register(this.handle);

    // Avoid double-fetch on startup.
    if (!(window.ws && window.ws.readyState === WebSocket.CONNECTING)) {
        this.fetch();
    }
}
_lodash2.default.extend(LiveStoreMixin.prototype, {
    handle: function handle(event) {
        if (event.type === _actions.ActionTypes.CONNECTION_OPEN) {
            return this.fetch();
        }
        if (event.type === this.type) {
            if (event.cmd === _actions.StoreCmds.RESET) {
                this.fetch(event.data);
            } else if (this._updates_before_fetch) {
                console.log("defer update", event);
                this._updates_before_fetch.push(event);
            } else {
                this[event.cmd](event.data);
            }
        }
    },
    close: function close() {
        _dispatcher.AppDispatcher.unregister(this.handle);
    },
    fetch: function fetch(data) {
        console.log("fetch " + this.type);
        if (this._fetchxhr) {
            this._fetchxhr.abort();
        }
        this._updates_before_fetch = []; // (JS: empty array is true)
        if (data) {
            this.handle_fetch(data);
        } else {
            this._fetchxhr = _jquery2.default.getJSON("/" + this.type).done(function (message) {
                this.handle_fetch(message.data);
            }.bind(this)).fail(function () {
                console.error("Could not fetch " + this.type);
            }.bind(this));
        }
    },
    handle_fetch: function handle_fetch(data) {
        this._fetchxhr = false;
        console.log(this.type + " fetched.", this._updates_before_fetch);
        this.reset(data);
        var updates = this._updates_before_fetch;
        this._updates_before_fetch = false;
        for (var i = 0; i < updates.length; i++) {
            this.handle(updates[i]);
        }
    }
});

function LiveDictStore(type) {
    DictStore.call(this);
    LiveStoreMixin.call(this, type);
}
_lodash2.default.extend(LiveDictStore.prototype, DictStore.prototype, LiveStoreMixin.prototype);

function SettingsStore() {
    return new LiveDictStore(_actions.ActionTypes.SETTINGS_STORE);
}

},{"../actions.js":2,"../dispatcher.js":22,"events":1,"jquery":"jquery","lodash":"lodash"}],32:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.formatTimeStamp = exports.formatTimeDelta = exports.formatSize = exports.Key = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.reverseString = reverseString;
exports.fetchApi = fetchApi;

var _jquery = require("jquery");

var _jquery2 = _interopRequireDefault(_jquery);

var _lodash = require("lodash");

var _lodash2 = _interopRequireDefault(_lodash);

var _actions = require("./actions.js");

var _actions2 = _interopRequireDefault(_actions);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

window.$ = _jquery2.default;
window._ = _lodash2.default;
window.React = require("react");

var Key = exports.Key = {
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
    SHIFT: 16
};
// Add A-Z
for (var i = 65; i <= 90; i++) {
    Key[String.fromCharCode(i)] = i;
}

var formatSize = exports.formatSize = function formatSize(bytes) {
    if (bytes === 0) return "0";
    var prefix = ["b", "kb", "mb", "gb", "tb"];
    for (var i = 0; i < prefix.length; i++) {
        if (Math.pow(1024, i + 1) > bytes) {
            break;
        }
    }
    var precision;
    if (bytes % Math.pow(1024, i) === 0) precision = 0;else precision = 1;
    return (bytes / Math.pow(1024, i)).toFixed(precision) + prefix[i];
};

var formatTimeDelta = exports.formatTimeDelta = function formatTimeDelta(milliseconds) {
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

var formatTimeStamp = exports.formatTimeStamp = function formatTimeStamp(seconds) {
    var ts = new Date(seconds * 1000).toISOString();
    return ts.replace("T", " ").replace("Z", "");
};

// At some places, we need to sort strings alphabetically descending,
// but we can only provide a key function.
// This beauty "reverses" a JS string.
var end = String.fromCharCode(0xffff);
function reverseString(s) {
    return String.fromCharCode.apply(String, _lodash2.default.map(s.split(""), function (c) {
        return 0xffff - c.charCodeAt(0);
    })) + end;
}

function getCookie(name) {
    var r = document.cookie.match(new RegExp("\\b" + name + "=([^;]*)\\b"));
    return r ? r[1] : undefined;
}
var xsrf = "_xsrf=" + getCookie("_xsrf");

//Tornado XSRF Protection.
_jquery2.default.ajaxPrefilter(function (options) {
    if (["post", "put", "delete"].indexOf(options.type.toLowerCase()) >= 0 && options.url[0] === "/") {
        if (options.url.indexOf("?") === -1) {
            options.url += "?" + xsrf;
        } else {
            options.url += "&" + xsrf;
        }
    }
});
// Log AJAX Errors
(0, _jquery2.default)(document).ajaxError(function (event, jqXHR, ajaxSettings, thrownError) {
    if (thrownError === "abort") {
        return;
    }
    var message = jqXHR.responseText;
    console.error(thrownError, message, arguments);
    alert(message);
});

function fetchApi(url, options) {
    if (url.indexOf("?") === -1) {
        url += "?" + xsrf;
    } else {
        url += "&" + xsrf;
    }
    return fetch(url, _extends({}, options, {
        credentials: 'same-origin'
    }));
}

},{"./actions.js":2,"jquery":"jquery","lodash":"lodash","react":"react"}]},{},[3])

