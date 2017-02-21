(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
// shim for using process in browser

var process = module.exports = {};

// cached from whatever global is present so that test runners that stub it
// don't break things.  But we need to wrap it in a try catch in case it is
// wrapped in strict mode code which doesn't define any globals.  It's inside a
// function because try/catches deoptimize in certain engines.

var cachedSetTimeout;
var cachedClearTimeout;

(function () {
  try {
    cachedSetTimeout = setTimeout;
  } catch (e) {
    cachedSetTimeout = function () {
      throw new Error('setTimeout is not defined');
    }
  }
  try {
    cachedClearTimeout = clearTimeout;
  } catch (e) {
    cachedClearTimeout = function () {
      throw new Error('clearTimeout is not defined');
    }
  }
} ())
var queue = [];
var draining = false;
var currentQueue;
var queueIndex = -1;

function cleanUpNextTick() {
    if (!draining || !currentQueue) {
        return;
    }
    draining = false;
    if (currentQueue.length) {
        queue = currentQueue.concat(queue);
    } else {
        queueIndex = -1;
    }
    if (queue.length) {
        drainQueue();
    }
}

function drainQueue() {
    if (draining) {
        return;
    }
    var timeout = cachedSetTimeout(cleanUpNextTick);
    draining = true;

    var len = queue.length;
    while(len) {
        currentQueue = queue;
        queue = [];
        while (++queueIndex < len) {
            if (currentQueue) {
                currentQueue[queueIndex].run();
            }
        }
        queueIndex = -1;
        len = queue.length;
    }
    currentQueue = null;
    draining = false;
    cachedClearTimeout(timeout);
}

process.nextTick = function (fun) {
    var args = new Array(arguments.length - 1);
    if (arguments.length > 1) {
        for (var i = 1; i < arguments.length; i++) {
            args[i - 1] = arguments[i];
        }
    }
    queue.push(new Item(fun, args));
    if (queue.length === 1 && !draining) {
        cachedSetTimeout(drainQueue, 0);
    }
};

// v8 likes predictible objects
function Item(fun, array) {
    this.fun = fun;
    this.array = array;
}
Item.prototype.run = function () {
    this.fun.apply(null, this.array);
};
process.title = 'browser';
process.browser = true;
process.env = {};
process.argv = [];
process.version = ''; // empty string to avoid regexp issues
process.versions = {};

function noop() {}

process.on = noop;
process.addListener = noop;
process.once = noop;
process.off = noop;
process.removeListener = noop;
process.removeAllListeners = noop;
process.emit = noop;

process.binding = function (name) {
    throw new Error('process.binding is not supported');
};

process.cwd = function () { return '/' };
process.chdir = function (dir) {
    throw new Error('process.chdir is not supported');
};
process.umask = function() { return 0; };

},{}],2:[function(require,module,exports){
(function (process){
'use strict';

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactDom = require('react-dom');

var _redux = require('redux');

var _reactRedux = require('react-redux');

var _reduxThunk = require('redux-thunk');

var _reduxThunk2 = _interopRequireDefault(_reduxThunk);

var _ProxyApp = require('./components/ProxyApp');

var _ProxyApp2 = _interopRequireDefault(_ProxyApp);

var _index = require('./ducks/index');

var _index2 = _interopRequireDefault(_index);

var _eventLog = require('./ducks/eventLog');

var _urlState = require('./urlState');

var _urlState2 = _interopRequireDefault(_urlState);

var _websocket = require('./backends/websocket');

var _websocket2 = _interopRequireDefault(_websocket);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var middlewares = [_reduxThunk2.default];

if (process.env.NODE_ENV !== 'production') {
    var createLogger = require('redux-logger');
    middlewares.push(createLogger());
}

// logger must be last
var store = (0, _redux.createStore)(_index2.default, _redux.applyMiddleware.apply(undefined, middlewares));

(0, _urlState2.default)(store);
window.backend = new _websocket2.default(store);

window.addEventListener('error', function (msg) {
    store.dispatch((0, _eventLog.add)(msg));
});

document.addEventListener('DOMContentLoaded', function () {
    (0, _reactDom.render)(_react2.default.createElement(
        _reactRedux.Provider,
        { store: store },
        _react2.default.createElement(_ProxyApp2.default, null)
    ), document.getElementById("mitmproxy"));
});

}).call(this,require('_process'))

},{"./backends/websocket":3,"./components/ProxyApp":37,"./ducks/eventLog":48,"./ducks/index":50,"./urlState":59,"_process":1,"react":"react","react-dom":"react-dom","react-redux":"react-redux","redux":"redux","redux-logger":"redux-logger","redux-thunk":"redux-thunk"}],3:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }(); /**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      *  The WebSocket backend is responsible for updating our knowledge of flows and events
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      *  from the REST API and live updates delivered via a WebSocket connection.
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      *  An alternative backend may use the REST API only to host static instances.
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      */


var _utils = require('../utils');

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

var CMD_RESET = 'reset';

var WebsocketBackend = function () {
    function WebsocketBackend(store) {
        _classCallCheck(this, WebsocketBackend);

        this.activeFetches = {};
        this.store = store;
        this.connect();
    }

    _createClass(WebsocketBackend, [{
        key: 'connect',
        value: function connect() {
            var _this = this;

            this.socket = new WebSocket(location.origin.replace('http', 'ws') + '/updates');
            this.socket.addEventListener('open', function () {
                return _this.onOpen();
            });
            this.socket.addEventListener('close', function () {
                return _this.onClose();
            });
            this.socket.addEventListener('message', function (msg) {
                return _this.onMessage(JSON.parse(msg.data));
            });
            this.socket.addEventListener('error', function (error) {
                return _this.onError(error);
            });
        }
    }, {
        key: 'onOpen',
        value: function onOpen() {
            this.fetchData("settings");
            this.fetchData("flows");
            this.fetchData("events");
        }
    }, {
        key: 'fetchData',
        value: function fetchData(resource) {
            var _this2 = this;

            var queue = [];
            this.activeFetches[resource] = queue;
            (0, _utils.fetchApi)('/' + resource).then(function (res) {
                return res.json();
            }).then(function (json) {
                // Make sure that we are not superseded yet by the server sending a RESET.
                if (_this2.activeFetches[resource] === queue) _this2.receive(resource, json);
            });
        }
    }, {
        key: 'onMessage',
        value: function onMessage(msg) {

            if (msg.cmd === CMD_RESET) {
                return this.fetchData(msg.resource);
            }
            if (msg.resource in this.activeFetches) {
                this.activeFetches[msg.resource].push(msg);
            } else {
                var type = (msg.resource + '_' + msg.cmd).toUpperCase();
                this.store.dispatch(_extends({ type: type }, msg));
            }
        }
    }, {
        key: 'receive',
        value: function receive(resource, data) {
            var _this3 = this;

            var type = (resource + '_RECEIVE').toUpperCase();
            this.store.dispatch({ type: type, cmd: "receive", resource: resource, data: data });
            var queue = this.activeFetches[resource];
            delete this.activeFetches[resource];
            queue.forEach(function (msg) {
                return _this3.onMessage(msg);
            });
        }
    }, {
        key: 'onClose',
        value: function onClose() {
            // FIXME
            console.error("onClose", arguments);
        }
    }, {
        key: 'onError',
        value: function onError() {
            // FIXME
            console.error("onError", arguments);
        }
    }]);

    return WebsocketBackend;
}();

exports.default = WebsocketBackend;

},{"../utils":60}],4:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _ContentViews = require('./ContentView/ContentViews');

var ContentViews = _interopRequireWildcard(_ContentViews);

var _MetaViews = require('./ContentView/MetaViews');

var MetaViews = _interopRequireWildcard(_MetaViews);

var _ShowFullContentButton = require('./ContentView/ShowFullContentButton');

var _ShowFullContentButton2 = _interopRequireDefault(_ShowFullContentButton);

var _flow = require('../ducks/ui/flow');

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

ContentView.propTypes = {
    // It may seem a bit weird at the first glance:
    // Every view takes the flow and the message as props, e.g.
    // <Auto flow={flow} message={flow.request}/>
    flow: _react2.default.PropTypes.object.isRequired,
    message: _react2.default.PropTypes.object.isRequired
};

ContentView.isContentTooLarge = function (msg) {
    return msg.contentLength > 1024 * 1024 * (ContentViews.ViewImage.matches(msg) ? 10 : 0.2);
};

function ContentView(props) {
    var flow = props.flow;
    var message = props.message;
    var contentView = props.contentView;
    var isDisplayLarge = props.isDisplayLarge;
    var displayLarge = props.displayLarge;
    var onContentChange = props.onContentChange;
    var readonly = props.readonly;


    if (message.contentLength === 0 && readonly) {
        return _react2.default.createElement(MetaViews.ContentEmpty, props);
    }

    if (message.contentLength === null && readonly) {
        return _react2.default.createElement(MetaViews.ContentMissing, props);
    }

    if (!isDisplayLarge && ContentView.isContentTooLarge(message)) {
        return _react2.default.createElement(MetaViews.ContentTooLarge, _extends({}, props, { onClick: displayLarge }));
    }

    var View = ContentViews[contentView] || ContentViews['ViewServer'];
    return _react2.default.createElement(
        'div',
        { className: 'contentview' },
        _react2.default.createElement(View, { flow: flow, message: message, contentView: contentView, readonly: readonly, onChange: onContentChange }),
        _react2.default.createElement(_ShowFullContentButton2.default, null)
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        contentView: state.ui.flow.contentView,
        isDisplayLarge: state.ui.flow.displayLarge
    };
}, {
    displayLarge: _flow.displayLarge,
    updateEdit: _flow.updateEdit
})(ContentView);

},{"../ducks/ui/flow":52,"./ContentView/ContentViews":8,"./ContentView/MetaViews":10,"./ContentView/ShowFullContentButton":11,"react":"react","react-redux":"react-redux"}],5:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = CodeEditor;

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactCodemirror = require('react-codemirror');

var _reactCodemirror2 = _interopRequireDefault(_reactCodemirror);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

CodeEditor.propTypes = {
    content: _react.PropTypes.string.isRequired,
    onChange: _react.PropTypes.func.isRequired
};

function CodeEditor(_ref) {
    var content = _ref.content;
    var onChange = _ref.onChange;


    var options = {
        lineNumbers: true
    };
    return _react2.default.createElement(
        'div',
        { className: 'codeeditor', onKeyDown: function onKeyDown(e) {
                return e.stopPropagation();
            } },
        _react2.default.createElement(_reactCodemirror2.default, { value: content, onChange: onChange, options: options })
    );
}

},{"react":"react","react-codemirror":"react-codemirror"}],6:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _utils = require('../../flow/utils.js');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

exports.default = function (View) {
    var _class, _temp;

    return _temp = _class = function (_React$Component) {
        _inherits(_class, _React$Component);

        function _class(props) {
            _classCallCheck(this, _class);

            var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(_class).call(this, props));

            _this.state = {
                content: undefined,
                request: undefined
            };
            return _this;
        }

        _createClass(_class, [{
            key: 'componentWillMount',
            value: function componentWillMount() {
                this.updateContent(this.props);
            }
        }, {
            key: 'componentWillReceiveProps',
            value: function componentWillReceiveProps(nextProps) {
                if (nextProps.message.content !== this.props.message.content || nextProps.message.contentHash !== this.props.message.contentHash || nextProps.contentView !== this.props.contentView) {
                    this.updateContent(nextProps);
                }
            }
        }, {
            key: 'componentWillUnmount',
            value: function componentWillUnmount() {
                if (this.state.request) {
                    this.state.request.abort();
                }
            }
        }, {
            key: 'updateContent',
            value: function updateContent(props) {
                if (this.state.request) {
                    this.state.request.abort();
                }
                // We have a few special cases where we do not need to make an HTTP request.
                if (props.message.content !== undefined) {
                    return this.setState({ request: undefined, content: props.message.content });
                }
                if (props.message.contentLength === 0 || props.message.contentLength === null) {
                    return this.setState({ request: undefined, content: "" });
                }

                var requestUrl = _utils.MessageUtils.getContentURL(props.flow, props.message, View.name == 'ViewServer' ? props.contentView : undefined);

                // We use XMLHttpRequest instead of fetch() because fetch() is not (yet) abortable.
                var request = new XMLHttpRequest();
                request.addEventListener("load", this.requestComplete.bind(this, request));
                request.addEventListener("error", this.requestFailed.bind(this, request));
                request.open("GET", requestUrl);
                request.send();
                this.setState({ request: request, content: undefined });
            }
        }, {
            key: 'requestComplete',
            value: function requestComplete(request, e) {
                if (request !== this.state.request) {
                    return; // Stale request
                }
                this.setState({
                    content: request.responseText,
                    request: undefined
                });
            }
        }, {
            key: 'requestFailed',
            value: function requestFailed(request, e) {
                if (request !== this.state.request) {
                    return; // Stale request
                }
                console.error(e);
                // FIXME: Better error handling
                this.setState({
                    content: "Error getting content.",
                    request: undefined
                });
            }
        }, {
            key: 'render',
            value: function render() {
                return this.state.content !== undefined ? _react2.default.createElement(View, _extends({ content: this.state.content }, this.props)) : _react2.default.createElement(
                    'div',
                    { className: 'text-center' },
                    _react2.default.createElement('i', { className: 'fa fa-spinner fa-spin' })
                );
            }
        }]);

        return _class;
    }(_react2.default.Component), _class.displayName = View.displayName || View.name, _class.matches = View.matches, _class.propTypes = _extends({}, View.propTypes, {
        content: _react.PropTypes.string, // mark as non-required
        flow: _react.PropTypes.object.isRequired,
        message: _react.PropTypes.object.isRequired
    }), _temp;
};

},{"../../flow/utils.js":58,"react":"react"}],7:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _ViewSelector = require('./ViewSelector');

var _ViewSelector2 = _interopRequireDefault(_ViewSelector);

var _UploadContentButton = require('./UploadContentButton');

var _UploadContentButton2 = _interopRequireDefault(_UploadContentButton);

var _DownloadContentButton = require('./DownloadContentButton');

var _DownloadContentButton2 = _interopRequireDefault(_DownloadContentButton);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

ContentViewOptions.propTypes = {
    flow: _react2.default.PropTypes.object.isRequired,
    message: _react2.default.PropTypes.object.isRequired
};

function ContentViewOptions(_ref) {
    var flow = _ref.flow;
    var message = _ref.message;
    var uploadContent = _ref.uploadContent;
    var readonly = _ref.readonly;
    var contentViewDescription = _ref.contentViewDescription;

    return _react2.default.createElement(
        'div',
        { className: 'view-options' },
        readonly ? _react2.default.createElement(_ViewSelector2.default, { message: message }) : _react2.default.createElement(
            'span',
            null,
            _react2.default.createElement(
                'b',
                null,
                'View:'
            ),
            ' edit'
        ),
        ' ',
        _react2.default.createElement(_DownloadContentButton2.default, { flow: flow, message: message }),
        ' ',
        !readonly && _react2.default.createElement(_UploadContentButton2.default, { uploadContent: uploadContent }),
        ' ',
        readonly && _react2.default.createElement(
            'span',
            null,
            contentViewDescription
        )
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        contentViewDescription: state.ui.flow.viewDescription,
        readonly: !state.ui.flow.modifiedFlow
    };
})(ContentViewOptions);

},{"./DownloadContentButton":9,"./UploadContentButton":12,"./ViewSelector":13,"react":"react","react-redux":"react-redux"}],8:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.ViewImage = exports.ViewServer = exports.Edit = undefined;

var _slicedToArray = function () { function sliceIterator(arr, i) { var _arr = []; var _n = true; var _d = false; var _e = undefined; try { for (var _i = arr[Symbol.iterator](), _s; !(_n = (_s = _i.next()).done); _n = true) { _arr.push(_s.value); if (i && _arr.length === i) break; } } catch (err) { _d = true; _e = err; } finally { try { if (!_n && _i["return"]) _i["return"](); } finally { if (_d) throw _e; } } return _arr; } return function (arr, i) { if (Array.isArray(arr)) { return arr; } else if (Symbol.iterator in Object(arr)) { return sliceIterator(arr, i); } else { throw new TypeError("Invalid attempt to destructure non-iterable instance"); } }; }();

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _flow = require('../../ducks/ui/flow');

var _ContentLoader = require('./ContentLoader');

var _ContentLoader2 = _interopRequireDefault(_ContentLoader);

var _utils = require('../../flow/utils');

var _CodeEditor = require('./CodeEditor');

var _CodeEditor2 = _interopRequireDefault(_CodeEditor);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var isImage = /^image\/(png|jpe?g|gif|vnc.microsoft.icon|x-icon)$/i;
ViewImage.matches = function (msg) {
    return isImage.test(_utils.MessageUtils.getContentType(msg));
};
ViewImage.propTypes = {
    flow: _react.PropTypes.object.isRequired,
    message: _react.PropTypes.object.isRequired
};
function ViewImage(_ref) {
    var flow = _ref.flow;
    var message = _ref.message;

    return _react2.default.createElement(
        'div',
        { className: 'flowview-image' },
        _react2.default.createElement('img', { src: _utils.MessageUtils.getContentURL(flow, message), alt: 'preview', className: 'img-thumbnail' })
    );
}

Edit.propTypes = {
    content: _react2.default.PropTypes.string.isRequired
};

function Edit(_ref2) {
    var content = _ref2.content;
    var onChange = _ref2.onChange;

    return _react2.default.createElement(_CodeEditor2.default, { content: content, onChange: onChange });
}
exports.Edit = Edit = (0, _ContentLoader2.default)(Edit);

var ViewServer = function (_Component) {
    _inherits(ViewServer, _Component);

    function ViewServer() {
        _classCallCheck(this, ViewServer);

        return _possibleConstructorReturn(this, Object.getPrototypeOf(ViewServer).apply(this, arguments));
    }

    _createClass(ViewServer, [{
        key: 'componentWillMount',
        value: function componentWillMount() {
            this.setContentView(this.props);
        }
    }, {
        key: 'componentWillReceiveProps',
        value: function componentWillReceiveProps(nextProps) {
            if (nextProps.content != this.props.content) {
                this.setContentView(nextProps);
            }
        }
    }, {
        key: 'setContentView',
        value: function setContentView(props) {
            try {
                this.data = JSON.parse(props.content);
            } catch (err) {
                this.data = { lines: [], description: err.message };
            }

            props.setContentViewDescription(props.contentView != this.data.description ? this.data.description : '');
            props.setContent(this.data.lines);
        }
    }, {
        key: 'render',
        value: function render() {
            var _props = this.props;
            var content = _props.content;
            var contentView = _props.contentView;
            var message = _props.message;
            var maxLines = _props.maxLines;

            var lines = this.props.showFullContent ? this.data.lines : this.data.lines.slice(0, maxLines);
            return _react2.default.createElement(
                'div',
                null,
                ViewImage.matches(message) && _react2.default.createElement(ViewImage, this.props),
                _react2.default.createElement(
                    'pre',
                    null,
                    lines.map(function (line, i) {
                        return _react2.default.createElement(
                            'div',
                            { key: 'line' + i },
                            line.map(function (element, j) {
                                var _element = _slicedToArray(element, 2);

                                var style = _element[0];
                                var text = _element[1];

                                return _react2.default.createElement(
                                    'span',
                                    { key: 'tuple' + j, className: style },
                                    text
                                );
                            })
                        );
                    })
                )
            );
        }
    }]);

    return ViewServer;
}(_react.Component);

ViewServer.propTypes = {
    showFullContent: _react.PropTypes.bool.isRequired,
    maxLines: _react.PropTypes.number.isRequired,
    setContentViewDescription: _react.PropTypes.func.isRequired,
    setContent: _react.PropTypes.func.isRequired
};


exports.ViewServer = ViewServer = (0, _reactRedux.connect)(function (state) {
    return {
        showFullContent: state.ui.flow.showFullContent,
        maxLines: state.ui.flow.maxContentLines
    };
}, {
    setContentViewDescription: _flow.setContentViewDescription,
    setContent: _flow.setContent
})((0, _ContentLoader2.default)(ViewServer));

exports.Edit = Edit;
exports.ViewServer = ViewServer;
exports.ViewImage = ViewImage;

},{"../../ducks/ui/flow":52,"../../flow/utils":58,"./CodeEditor":5,"./ContentLoader":6,"react":"react","react-redux":"react-redux"}],9:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = DownloadContentButton;

var _utils = require("../../flow/utils");

var _react = require("react");

DownloadContentButton.propTypes = {
    flow: _react.PropTypes.object.isRequired,
    message: _react.PropTypes.object.isRequired
};

function DownloadContentButton(_ref) {
    var flow = _ref.flow;
    var message = _ref.message;


    return React.createElement(
        "a",
        { className: "btn btn-default btn-xs",
            href: _utils.MessageUtils.getContentURL(flow, message),
            title: "Download the content of the flow." },
        React.createElement("i", { className: "fa fa-download" })
    );
}

},{"../../flow/utils":58,"react":"react"}],10:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.ContentEmpty = ContentEmpty;
exports.ContentMissing = ContentMissing;
exports.ContentTooLarge = ContentTooLarge;

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _utils = require('../../utils.js');

var _UploadContentButton = require('./UploadContentButton');

var _UploadContentButton2 = _interopRequireDefault(_UploadContentButton);

var _DownloadContentButton = require('./DownloadContentButton');

var _DownloadContentButton2 = _interopRequireDefault(_DownloadContentButton);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function ContentEmpty(_ref) {
    var flow = _ref.flow;
    var message = _ref.message;

    return _react2.default.createElement(
        'div',
        { className: 'alert alert-info' },
        'No ',
        flow.request === message ? 'request' : 'response',
        ' content.'
    );
}

function ContentMissing(_ref2) {
    var flow = _ref2.flow;
    var message = _ref2.message;

    return _react2.default.createElement(
        'div',
        { className: 'alert alert-info' },
        flow.request === message ? 'Request' : 'Response',
        ' content missing.'
    );
}

function ContentTooLarge(_ref3) {
    var message = _ref3.message;
    var onClick = _ref3.onClick;
    var uploadContent = _ref3.uploadContent;
    var flow = _ref3.flow;

    return _react2.default.createElement(
        'div',
        null,
        _react2.default.createElement(
            'div',
            { className: 'alert alert-warning' },
            _react2.default.createElement(
                'button',
                { onClick: onClick, className: 'btn btn-xs btn-warning pull-right' },
                'Display anyway'
            ),
            (0, _utils.formatSize)(message.contentLength),
            ' content size.'
        ),
        _react2.default.createElement(
            'div',
            { className: 'view-options text-center' },
            _react2.default.createElement(_UploadContentButton2.default, { uploadContent: uploadContent }),
            ' ',
            _react2.default.createElement(_DownloadContentButton2.default, { flow: flow, message: message })
        )
    );
}

},{"../../utils.js":60,"./DownloadContentButton":9,"./UploadContentButton":12,"react":"react"}],11:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _reactDom = require('react-dom');

var _Button = require('../common/Button');

var _Button2 = _interopRequireDefault(_Button);

var _flow = require('../../ducks/ui/flow');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

ShowFullContentButton.propTypes = {
    setShowFullContent: _react.PropTypes.func.isRequired,
    showFullContent: _react.PropTypes.bool.isRequired
};

function ShowFullContentButton(_ref) {
    var setShowFullContent = _ref.setShowFullContent;
    var showFullContent = _ref.showFullContent;
    var visibleLines = _ref.visibleLines;
    var contentLines = _ref.contentLines;


    return !showFullContent && _react2.default.createElement(
        'div',
        null,
        _react2.default.createElement(
            _Button2.default,
            { className: 'view-all-content-btn btn-xs', onClick: function onClick() {
                    return setShowFullContent();
                } },
            'Show full content'
        ),
        _react2.default.createElement(
            'span',
            { className: 'pull-right' },
            ' ',
            visibleLines,
            '/',
            contentLines,
            ' are visible   '
        )
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        showFullContent: state.ui.flow.showFullContent,
        visibleLines: state.ui.flow.maxContentLines,
        contentLines: state.ui.flow.content.length

    };
}, {
    setShowFullContent: _flow.setShowFullContent
})(ShowFullContentButton);

},{"../../ducks/ui/flow":52,"../common/Button":40,"react":"react","react-dom":"react-dom","react-redux":"react-redux"}],12:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = UploadContentButton;

var _react = require('react');

var _FileChooser = require('../common/FileChooser');

var _FileChooser2 = _interopRequireDefault(_FileChooser);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

UploadContentButton.propTypes = {
    uploadContent: _react.PropTypes.func.isRequired
};

function UploadContentButton(_ref) {
    var uploadContent = _ref.uploadContent;


    return React.createElement(_FileChooser2.default, {
        icon: 'fa-upload',
        title: 'Upload a file to replace the content.',
        onOpenFile: uploadContent,
        className: 'btn btn-default btn-xs' });
}

},{"../common/FileChooser":43,"react":"react"}],13:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _flow = require('../../ducks/ui/flow');

var _Dropdown = require('../common/Dropdown');

var _Dropdown2 = _interopRequireDefault(_Dropdown);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

ViewSelector.propTypes = {
    contentViews: _react.PropTypes.array.isRequired,
    activeView: _react.PropTypes.string.isRequired,
    setContentView: _react.PropTypes.func.isRequired
};

function ViewSelector(_ref) {
    var contentViews = _ref.contentViews;
    var activeView = _ref.activeView;
    var setContentView = _ref.setContentView;

    var inner = _react2.default.createElement(
        'span',
        null,
        ' ',
        _react2.default.createElement(
            'b',
            null,
            'View:'
        ),
        ' ',
        activeView.toLowerCase(),
        ' ',
        _react2.default.createElement('span', { className: 'caret' }),
        ' '
    );

    return _react2.default.createElement(
        _Dropdown2.default,
        { dropup: true, className: 'pull-left', btnClass: 'btn btn-default btn-xs', text: inner },
        contentViews.map(function (name) {
            return _react2.default.createElement(
                'a',
                { href: '#', key: name, onClick: function onClick(e) {
                        e.preventDefault();setContentView(name);
                    } },
                name.toLowerCase().replace('_', ' ')
            );
        })
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        contentViews: state.settings.contentViews,
        activeView: state.ui.flow.contentView
    };
}, {
    setContentView: _flow.setContentView
})(ViewSelector);

},{"../../ducks/ui/flow":52,"../common/Dropdown":42,"react":"react","react-redux":"react-redux"}],14:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _eventLog = require('../ducks/eventLog');

var _ToggleButton = require('./common/ToggleButton');

var _ToggleButton2 = _interopRequireDefault(_ToggleButton);

var _EventList = require('./EventLog/EventList');

var _EventList2 = _interopRequireDefault(_EventList);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var EventLog = function (_Component) {
    _inherits(EventLog, _Component);

    function EventLog(props, context) {
        _classCallCheck(this, EventLog);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(EventLog).call(this, props, context));

        _this.state = { height: _this.props.defaultHeight };

        _this.onDragStart = _this.onDragStart.bind(_this);
        _this.onDragMove = _this.onDragMove.bind(_this);
        _this.onDragStop = _this.onDragStop.bind(_this);
        return _this;
    }

    _createClass(EventLog, [{
        key: 'onDragStart',
        value: function onDragStart(event) {
            event.preventDefault();
            this.dragStart = this.state.height + event.pageY;
            window.addEventListener('mousemove', this.onDragMove);
            window.addEventListener('mouseup', this.onDragStop);
            window.addEventListener('dragend', this.onDragStop);
        }
    }, {
        key: 'onDragMove',
        value: function onDragMove(event) {
            event.preventDefault();
            this.setState({ height: this.dragStart - event.pageY });
        }
    }, {
        key: 'onDragStop',
        value: function onDragStop(event) {
            event.preventDefault();
            window.removeEventListener('mousemove', this.onDragMove);
        }
    }, {
        key: 'render',
        value: function render() {
            var height = this.state.height;
            var _props = this.props;
            var filters = _props.filters;
            var events = _props.events;
            var toggleFilter = _props.toggleFilter;
            var close = _props.close;


            return _react2.default.createElement(
                'div',
                { className: 'eventlog', style: { height: height } },
                _react2.default.createElement(
                    'div',
                    { onMouseDown: this.onDragStart },
                    'Eventlog',
                    _react2.default.createElement(
                        'div',
                        { className: 'pull-right' },
                        ['debug', 'info', 'web'].map(function (type) {
                            return _react2.default.createElement(_ToggleButton2.default, { key: type, text: type, checked: filters[type], onToggle: function onToggle() {
                                    return toggleFilter(type);
                                } });
                        }),
                        _react2.default.createElement('i', { onClick: close, className: 'fa fa-close' })
                    )
                ),
                _react2.default.createElement(_EventList2.default, { events: events })
            );
        }
    }]);

    return EventLog;
}(_react.Component);

EventLog.propTypes = {
    filters: _react.PropTypes.object.isRequired,
    events: _react.PropTypes.array.isRequired,
    toggleFilter: _react.PropTypes.func.isRequired,
    close: _react.PropTypes.func.isRequired,
    defaultHeight: _react.PropTypes.number
};
EventLog.defaultProps = {
    defaultHeight: 200
};
exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        filters: state.eventLog.filters,
        events: state.eventLog.view
    };
}, {
    close: _eventLog.toggleVisibility,
    toggleFilter: _eventLog.toggleFilter
})(EventLog);

},{"../ducks/eventLog":48,"./EventLog/EventList":15,"./common/ToggleButton":45,"react":"react","react-redux":"react-redux"}],15:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactDom = require('react-dom');

var _reactDom2 = _interopRequireDefault(_reactDom);

var _shallowequal = require('shallowequal');

var _shallowequal2 = _interopRequireDefault(_shallowequal);

var _AutoScroll = require('../helpers/AutoScroll');

var _AutoScroll2 = _interopRequireDefault(_AutoScroll);

var _VirtualScroll = require('../helpers/VirtualScroll');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var EventLogList = function (_Component) {
    _inherits(EventLogList, _Component);

    function EventLogList(props) {
        _classCallCheck(this, EventLogList);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(EventLogList).call(this, props));

        _this.heights = {};
        _this.state = { vScroll: (0, _VirtualScroll.calcVScroll)() };

        _this.onViewportUpdate = _this.onViewportUpdate.bind(_this);
        return _this;
    }

    _createClass(EventLogList, [{
        key: 'componentDidMount',
        value: function componentDidMount() {
            window.addEventListener('resize', this.onViewportUpdate);
            this.onViewportUpdate();
        }
    }, {
        key: 'componentWillUnmount',
        value: function componentWillUnmount() {
            window.removeEventListener('resize', this.onViewportUpdate);
        }
    }, {
        key: 'componentDidUpdate',
        value: function componentDidUpdate() {
            this.onViewportUpdate();
        }
    }, {
        key: 'onViewportUpdate',
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
        key: 'setHeight',
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
        key: 'render',
        value: function render() {
            var _this3 = this;

            var vScroll = this.state.vScroll;
            var events = this.props.events;


            return _react2.default.createElement(
                'pre',
                { onScroll: this.onViewportUpdate },
                _react2.default.createElement('div', { style: { height: vScroll.paddingTop } }),
                events.slice(vScroll.start, vScroll.end).map(function (event) {
                    return _react2.default.createElement(
                        'div',
                        { key: event.id, ref: function ref(node) {
                                return _this3.setHeight(event.id, node);
                            } },
                        _react2.default.createElement(LogIcon, { event: event }),
                        event.message
                    );
                }),
                _react2.default.createElement('div', { style: { height: vScroll.paddingBottom } })
            );
        }
    }]);

    return EventLogList;
}(_react.Component);

EventLogList.propTypes = {
    events: _react.PropTypes.array.isRequired,
    rowHeight: _react.PropTypes.number
};
EventLogList.defaultProps = {
    rowHeight: 18
};


function LogIcon(_ref) {
    var event = _ref.event;

    var icon = { web: 'html5', debug: 'bug' }[event.level] || 'info';
    return _react2.default.createElement('i', { className: 'fa fa-fw fa-' + icon });
}

exports.default = (0, _AutoScroll2.default)(EventLogList);

},{"../helpers/AutoScroll":46,"../helpers/VirtualScroll":47,"react":"react","react-dom":"react-dom","shallowequal":"shallowequal"}],16:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactDom = require('react-dom');

var _reactDom2 = _interopRequireDefault(_reactDom);

var _shallowequal = require('shallowequal');

var _shallowequal2 = _interopRequireDefault(_shallowequal);

var _AutoScroll = require('./helpers/AutoScroll');

var _AutoScroll2 = _interopRequireDefault(_AutoScroll);

var _VirtualScroll = require('./helpers/VirtualScroll');

var _FlowTableHead = require('./FlowTable/FlowTableHead');

var _FlowTableHead2 = _interopRequireDefault(_FlowTableHead);

var _FlowRow = require('./FlowTable/FlowRow');

var _FlowRow2 = _interopRequireDefault(_FlowRow);

var _filt = require('../filt/filt');

var _filt2 = _interopRequireDefault(_filt);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

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
        key: 'componentWillMount',
        value: function componentWillMount() {
            window.addEventListener('resize', this.onViewportUpdate);
        }
    }, {
        key: 'componentWillUnmount',
        value: function componentWillUnmount() {
            window.removeEventListener('resize', this.onViewportUpdate);
        }
    }, {
        key: 'componentDidUpdate',
        value: function componentDidUpdate() {
            this.onViewportUpdate();

            if (!this.shouldScrollIntoView) {
                return;
            }

            this.shouldScrollIntoView = false;

            var _props = this.props;
            var rowHeight = _props.rowHeight;
            var flows = _props.flows;
            var selected = _props.selected;

            var viewport = _reactDom2.default.findDOMNode(this);
            var head = _reactDom2.default.findDOMNode(this.refs.head);

            var headHeight = head ? head.offsetHeight : 0;

            var rowTop = flows.indexOf(selected) * rowHeight + headHeight;
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
        key: 'componentWillReceiveProps',
        value: function componentWillReceiveProps(nextProps) {
            if (nextProps.selected && nextProps.selected !== this.props.selected) {
                this.shouldScrollIntoView = true;
            }
        }
    }, {
        key: 'onViewportUpdate',
        value: function onViewportUpdate() {
            var viewport = _reactDom2.default.findDOMNode(this);
            var viewportTop = viewport.scrollTop;

            var vScroll = (0, _VirtualScroll.calcVScroll)({
                viewportTop: viewportTop,
                viewportHeight: viewport.offsetHeight,
                itemCount: this.props.flows.length,
                rowHeight: this.props.rowHeight
            });

            if (this.state.viewportTop !== viewportTop || !(0, _shallowequal2.default)(this.state.vScroll, vScroll)) {
                this.setState({ vScroll: vScroll, viewportTop: viewportTop });
            }
        }
    }, {
        key: 'render',
        value: function render() {
            var _this2 = this;

            var _state = this.state;
            var vScroll = _state.vScroll;
            var viewportTop = _state.viewportTop;
            var _props2 = this.props;
            var flows = _props2.flows;
            var selected = _props2.selected;
            var highlight = _props2.highlight;

            var isHighlighted = highlight ? _filt2.default.parse(highlight) : function () {
                return false;
            };

            return _react2.default.createElement(
                'div',
                { className: 'flow-table', onScroll: this.onViewportUpdate },
                _react2.default.createElement(
                    'table',
                    null,
                    _react2.default.createElement(
                        'thead',
                        { ref: 'head', style: { transform: 'translateY(' + viewportTop + 'px)' } },
                        _react2.default.createElement(_FlowTableHead2.default, null)
                    ),
                    _react2.default.createElement(
                        'tbody',
                        null,
                        _react2.default.createElement('tr', { style: { height: vScroll.paddingTop } }),
                        flows.slice(vScroll.start, vScroll.end).map(function (flow) {
                            return _react2.default.createElement(_FlowRow2.default, {
                                key: flow.id,
                                flow: flow,
                                selected: flow === selected,
                                highlighted: isHighlighted(flow),
                                onSelect: _this2.props.onSelect
                            });
                        }),
                        _react2.default.createElement('tr', { style: { height: vScroll.paddingBottom } })
                    )
                )
            );
        }
    }]);

    return FlowTable;
}(_react2.default.Component);

FlowTable.propTypes = {
    onSelect: _react.PropTypes.func.isRequired,
    flows: _react.PropTypes.array.isRequired,
    rowHeight: _react.PropTypes.number,
    highlight: _react.PropTypes.string,
    selected: _react.PropTypes.object
};
FlowTable.defaultProps = {
    rowHeight: 32
};
exports.default = (0, _AutoScroll2.default)(FlowTable);

},{"../filt/filt":57,"./FlowTable/FlowRow":18,"./FlowTable/FlowTableHead":19,"./helpers/AutoScroll":46,"./helpers/VirtualScroll":47,"react":"react","react-dom":"react-dom","shallowequal":"shallowequal"}],17:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.TLSColumn = TLSColumn;
exports.IconColumn = IconColumn;
exports.PathColumn = PathColumn;
exports.MethodColumn = MethodColumn;
exports.StatusColumn = StatusColumn;
exports.SizeColumn = SizeColumn;
exports.TimeColumn = TimeColumn;

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _classnames = require('classnames');

var _classnames2 = _interopRequireDefault(_classnames);

var _utils = require('../../flow/utils.js');

var _utils2 = require('../../utils.js');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function TLSColumn(_ref) {
    var flow = _ref.flow;

    return _react2.default.createElement('td', { className: (0, _classnames2.default)('col-tls', flow.request.scheme === 'https' ? 'col-tls-https' : 'col-tls-http') });
}

TLSColumn.headerClass = 'col-tls';
TLSColumn.headerName = '';

function IconColumn(_ref2) {
    var flow = _ref2.flow;

    return _react2.default.createElement(
        'td',
        { className: 'col-icon' },
        _react2.default.createElement('div', { className: (0, _classnames2.default)('resource-icon', IconColumn.getIcon(flow)) })
    );
}

IconColumn.headerClass = 'col-icon';
IconColumn.headerName = '';

IconColumn.getIcon = function (flow) {
    if (!flow.response) {
        return 'resource-icon-plain';
    }

    var contentType = _utils.ResponseUtils.getContentType(flow.response) || '';

    // @todo We should assign a type to the flow somewhere else.
    if (flow.response.status_code === 304) {
        return 'resource-icon-not-modified';
    }
    if (300 <= flow.response.status_code && flow.response.status_code < 400) {
        return 'resource-icon-redirect';
    }
    if (contentType.indexOf('image') >= 0) {
        return 'resource-icon-image';
    }
    if (contentType.indexOf('javascript') >= 0) {
        return 'resource-icon-js';
    }
    if (contentType.indexOf('css') >= 0) {
        return 'resource-icon-css';
    }
    if (contentType.indexOf('html') >= 0) {
        return 'resource-icon-document';
    }

    return 'resource-icon-plain';
};

function PathColumn(_ref3) {
    var flow = _ref3.flow;


    var err = void 0;
    if (flow.error) {
        if (flow.error.msg === "Connection killed") {
            err = _react2.default.createElement('i', { className: 'fa fa-fw fa-times pull-right' });
        } else {
            err = _react2.default.createElement('i', { className: 'fa fa-fw fa-exclamation pull-right' });
        }
    }
    return _react2.default.createElement(
        'td',
        { className: 'col-path' },
        flow.request.is_replay && _react2.default.createElement('i', { className: 'fa fa-fw fa-repeat pull-right' }),
        flow.intercepted && _react2.default.createElement('i', { className: 'fa fa-fw fa-pause pull-right' }),
        err,
        _utils.RequestUtils.pretty_url(flow.request)
    );
}

PathColumn.headerClass = 'col-path';
PathColumn.headerName = 'Path';

function MethodColumn(_ref4) {
    var flow = _ref4.flow;

    return _react2.default.createElement(
        'td',
        { className: 'col-method' },
        flow.request.method
    );
}

MethodColumn.headerClass = 'col-method';
MethodColumn.headerName = 'Method';

function StatusColumn(_ref5) {
    var flow = _ref5.flow;

    return _react2.default.createElement(
        'td',
        { className: 'col-status' },
        flow.response && flow.response.status_code
    );
}

StatusColumn.headerClass = 'col-status';
StatusColumn.headerName = 'Status';

function SizeColumn(_ref6) {
    var flow = _ref6.flow;

    return _react2.default.createElement(
        'td',
        { className: 'col-size' },
        (0, _utils2.formatSize)(SizeColumn.getTotalSize(flow))
    );
}

SizeColumn.getTotalSize = function (flow) {
    var total = flow.request.contentLength;
    if (flow.response) {
        total += flow.response.contentLength || 0;
    }
    return total;
};

SizeColumn.headerClass = 'col-size';
SizeColumn.headerName = 'Size';

function TimeColumn(_ref7) {
    var flow = _ref7.flow;

    return _react2.default.createElement(
        'td',
        { className: 'col-time' },
        flow.response ? (0, _utils2.formatTimeDelta)(1000 * (flow.response.timestamp_end - flow.server_conn.timestamp_start)) : '...'
    );
}

TimeColumn.headerClass = 'col-time';
TimeColumn.headerName = 'Time';

exports.default = [TLSColumn, IconColumn, PathColumn, MethodColumn, StatusColumn, SizeColumn, TimeColumn];

},{"../../flow/utils.js":58,"../../utils.js":60,"classnames":"classnames","react":"react"}],18:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _classnames = require('classnames');

var _classnames2 = _interopRequireDefault(_classnames);

var _FlowColumns = require('./FlowColumns');

var _FlowColumns2 = _interopRequireDefault(_FlowColumns);

var _utils = require('../../utils');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

FlowRow.propTypes = {
    onSelect: _react.PropTypes.func.isRequired,
    flow: _react.PropTypes.object.isRequired,
    highlighted: _react.PropTypes.bool,
    selected: _react.PropTypes.bool
};

function FlowRow(_ref) {
    var flow = _ref.flow;
    var selected = _ref.selected;
    var highlighted = _ref.highlighted;
    var onSelect = _ref.onSelect;

    var className = (0, _classnames2.default)({
        'selected': selected,
        'highlighted': highlighted,
        'intercepted': flow.intercepted,
        'has-request': flow.request,
        'has-response': flow.response
    });

    return _react2.default.createElement(
        'tr',
        { className: className, onClick: function onClick() {
                return onSelect(flow.id);
            } },
        _FlowColumns2.default.map(function (Column) {
            return _react2.default.createElement(Column, { key: Column.name, flow: flow });
        })
    );
}

exports.default = (0, _utils.pure)(FlowRow);

},{"../../utils":60,"./FlowColumns":17,"classnames":"classnames","react":"react"}],19:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _classnames = require('classnames');

var _classnames2 = _interopRequireDefault(_classnames);

var _FlowColumns = require('./FlowColumns');

var _FlowColumns2 = _interopRequireDefault(_FlowColumns);

var _flows = require('../../ducks/flows');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

FlowTableHead.propTypes = {
    setSort: _react.PropTypes.func.isRequired,
    sortDesc: _react2.default.PropTypes.bool.isRequired,
    sortColumn: _react2.default.PropTypes.string
};

function FlowTableHead(_ref) {
    var sortColumn = _ref.sortColumn;
    var sortDesc = _ref.sortDesc;
    var setSort = _ref.setSort;

    var sortType = sortDesc ? 'sort-desc' : 'sort-asc';

    return _react2.default.createElement(
        'tr',
        null,
        _FlowColumns2.default.map(function (Column) {
            return _react2.default.createElement(
                'th',
                { className: (0, _classnames2.default)(Column.headerClass, sortColumn === Column.name && sortType),
                    key: Column.name,
                    onClick: function onClick() {
                        return setSort(Column.name, Column.name !== sortColumn ? false : !sortDesc);
                    } },
                Column.headerName
            );
        })
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        sortDesc: state.flows.sort.desc,
        sortColumn: state.flows.sort.column
    };
}, {
    setSort: _flows.setSort
})(FlowTableHead);

},{"../../ducks/flows":49,"./FlowColumns":17,"classnames":"classnames","react":"react","react-redux":"react-redux"}],20:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _lodash = require('lodash');

var _lodash2 = _interopRequireDefault(_lodash);

var _Nav = require('./FlowView/Nav');

var _Nav2 = _interopRequireDefault(_Nav);

var _Messages = require('./FlowView/Messages');

var _Details = require('./FlowView/Details');

var _Details2 = _interopRequireDefault(_Details);

var _Prompt = require('./Prompt');

var _Prompt2 = _interopRequireDefault(_Prompt);

var _flow = require('../ducks/ui/flow');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var FlowView = function (_Component) {
    _inherits(FlowView, _Component);

    function FlowView(props, context) {
        _classCallCheck(this, FlowView);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(FlowView).call(this, props, context));

        _this.onPromptFinish = _this.onPromptFinish.bind(_this);
        return _this;
    }

    _createClass(FlowView, [{
        key: 'onPromptFinish',
        value: function onPromptFinish(edit) {
            this.props.setPrompt(false);
            if (edit && this.tabComponent) {
                this.tabComponent.edit(edit);
            }
        }
    }, {
        key: 'getPromptOptions',
        value: function getPromptOptions() {
            switch (this.props.tab) {

                case 'request':
                    return ['method', 'url', { text: 'http version', key: 'v' }, 'header'];
                    break;

                case 'response':
                    return [{ text: 'http version', key: 'v' }, 'code', 'message', 'header'];
                    break;

                case 'details':
                    return;

                default:
                    throw 'Unknown tab for edit: ' + this.props.tab;
            }
        }
    }, {
        key: 'render',
        value: function render() {
            var _this2 = this;

            var _props = this.props;
            var flow = _props.flow;
            var active = _props.tab;
            var updateFlow = _props.updateFlow;

            var tabs = ['request', 'response', 'error'].filter(function (k) {
                return flow[k];
            }).concat(['details']);

            if (tabs.indexOf(active) < 0) {
                if (active === 'response' && flow.error) {
                    active = 'error';
                } else if (active === 'error' && flow.response) {
                    active = 'response';
                } else {
                    active = tabs[0];
                }
            }

            var Tab = FlowView.allTabs[_lodash2.default.capitalize(active)];

            return _react2.default.createElement(
                'div',
                { className: 'flow-detail' },
                _react2.default.createElement(_Nav2.default, {
                    flow: flow,
                    tabs: tabs,
                    active: active,
                    onSelectTab: this.props.selectTab
                }),
                _react2.default.createElement(Tab, { ref: function ref(tab) {
                        return _this2.tabComponent = tab;
                    }, flow: flow, updateFlow: updateFlow }),
                this.props.promptOpen && _react2.default.createElement(_Prompt2.default, { options: this.getPromptOptions(), done: this.onPromptFinish })
            );
        }
    }]);

    return FlowView;
}(_react.Component);

FlowView.allTabs = { Request: _Messages.Request, Response: _Messages.Response, Error: _Messages.ErrorView, Details: _Details2.default };
exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        promptOpen: state.ui.promptOpen,
        tab: state.ui.flow.tab
    };
}, {
    selectTab: _flow.selectTab
})(FlowView);

},{"../ducks/ui/flow":52,"./FlowView/Details":21,"./FlowView/Messages":23,"./FlowView/Nav":24,"./Prompt":36,"lodash":"lodash","react":"react","react-redux":"react-redux"}],21:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.TimeStamp = TimeStamp;
exports.ConnectionInfo = ConnectionInfo;
exports.CertificateInfo = CertificateInfo;
exports.Timing = Timing;
exports.default = Details;

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _lodash = require('lodash');

var _lodash2 = _interopRequireDefault(_lodash);

var _utils = require('../../utils.js');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function TimeStamp(_ref) {
    var t = _ref.t;
    var deltaTo = _ref.deltaTo;
    var title = _ref.title;

    return t ? _react2.default.createElement(
        'tr',
        null,
        _react2.default.createElement(
            'td',
            null,
            title,
            ':'
        ),
        _react2.default.createElement(
            'td',
            null,
            (0, _utils.formatTimeStamp)(t),
            deltaTo && _react2.default.createElement(
                'span',
                { className: 'text-muted' },
                '(',
                (0, _utils.formatTimeDelta)(1000 * (t - deltaTo)),
                ')'
            )
        )
    ) : _react2.default.createElement('tr', null);
}

function ConnectionInfo(_ref2) {
    var conn = _ref2.conn;

    return _react2.default.createElement(
        'table',
        { className: 'connection-table' },
        _react2.default.createElement(
            'tbody',
            null,
            _react2.default.createElement(
                'tr',
                { key: 'address' },
                _react2.default.createElement(
                    'td',
                    null,
                    'Address:'
                ),
                _react2.default.createElement(
                    'td',
                    null,
                    conn.address.address.join(':')
                )
            ),
            conn.sni && _react2.default.createElement(
                'tr',
                { key: 'sni' },
                _react2.default.createElement(
                    'td',
                    null,
                    _react2.default.createElement(
                        'abbr',
                        { title: 'TLS Server Name Indication' },
                        'TLS SNI:'
                    )
                ),
                _react2.default.createElement(
                    'td',
                    null,
                    conn.sni
                )
            )
        )
    );
}

function CertificateInfo(_ref3) {
    var flow = _ref3.flow;

    // @todo We should fetch human-readable certificate representation from the server
    return _react2.default.createElement(
        'div',
        null,
        flow.client_conn.cert && [_react2.default.createElement(
            'h4',
            { key: 'name' },
            'Client Certificate'
        ), _react2.default.createElement(
            'pre',
            { key: 'value', style: { maxHeight: 100 } },
            flow.client_conn.cert
        )],
        flow.server_conn.cert && [_react2.default.createElement(
            'h4',
            { key: 'name' },
            'Server Certificate'
        ), _react2.default.createElement(
            'pre',
            { key: 'value', style: { maxHeight: 100 } },
            flow.server_conn.cert
        )]
    );
}

function Timing(_ref4) {
    var flow = _ref4.flow;
    var sc = flow.server_conn;
    var cc = flow.client_conn;
    var req = flow.request;
    var res = flow.response;


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
    }, res && {
        title: "First response byte",
        t: res.timestamp_start,
        deltaTo: req.timestamp_start
    }, res && {
        title: "Response complete",
        t: res.timestamp_end,
        deltaTo: req.timestamp_start
    }];

    return _react2.default.createElement(
        'div',
        null,
        _react2.default.createElement(
            'h4',
            null,
            'Timing'
        ),
        _react2.default.createElement(
            'table',
            { className: 'timing-table' },
            _react2.default.createElement(
                'tbody',
                null,
                timestamps.filter(function (v) {
                    return v;
                }).sort(function (a, b) {
                    return a.t - b.t;
                }).map(function (item) {
                    return _react2.default.createElement(TimeStamp, _extends({ key: item.title }, item));
                })
            )
        )
    );
}

function Details(_ref5) {
    var flow = _ref5.flow;

    return _react2.default.createElement(
        'section',
        { className: 'detail' },
        _react2.default.createElement(
            'h4',
            null,
            'Client Connection'
        ),
        _react2.default.createElement(ConnectionInfo, { conn: flow.client_conn }),
        _react2.default.createElement(
            'h4',
            null,
            'Server Connection'
        ),
        _react2.default.createElement(ConnectionInfo, { conn: flow.server_conn }),
        _react2.default.createElement(CertificateInfo, { flow: flow }),
        _react2.default.createElement(Timing, { flow: flow })
    );
}

},{"../../utils.js":60,"lodash":"lodash","react":"react"}],22:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactDom = require('react-dom');

var _reactDom2 = _interopRequireDefault(_reactDom);

var _ValueEditor = require('../ValueEditor/ValueEditor');

var _ValueEditor2 = _interopRequireDefault(_ValueEditor);

var _utils = require('../../utils');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _objectWithoutProperties(obj, keys) { var target = {}; for (var i in obj) { if (keys.indexOf(i) >= 0) continue; if (!Object.prototype.hasOwnProperty.call(obj, i)) continue; target[i] = obj[i]; } return target; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var HeaderEditor = function (_Component) {
    _inherits(HeaderEditor, _Component);

    function HeaderEditor(props) {
        _classCallCheck(this, HeaderEditor);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(HeaderEditor).call(this, props));

        _this.onKeyDown = _this.onKeyDown.bind(_this);
        return _this;
    }

    _createClass(HeaderEditor, [{
        key: 'render',
        value: function render() {
            var _props = this.props;
            var onTab = _props.onTab;

            var props = _objectWithoutProperties(_props, ['onTab']);

            return _react2.default.createElement(_ValueEditor2.default, _extends({}, props, {
                onKeyDown: this.onKeyDown
            }));
        }
    }, {
        key: 'focus',
        value: function focus() {
            _reactDom2.default.findDOMNode(this).focus();
        }
    }, {
        key: 'onKeyDown',
        value: function onKeyDown(e) {
            switch (e.keyCode) {
                case _utils.Key.BACKSPACE:
                    var s = window.getSelection().getRangeAt(0);
                    if (s.startOffset === 0 && s.endOffset === 0) {
                        this.props.onRemove(e);
                    }
                    break;
                case _utils.Key.ENTER:
                case _utils.Key.TAB:
                    if (!e.shiftKey) {
                        this.props.onTab(e);
                    }
                    break;
            }
        }
    }]);

    return HeaderEditor;
}(_react.Component);

var Headers = function (_Component2) {
    _inherits(Headers, _Component2);

    function Headers() {
        _classCallCheck(this, Headers);

        return _possibleConstructorReturn(this, Object.getPrototypeOf(Headers).apply(this, arguments));
    }

    _createClass(Headers, [{
        key: 'onChange',
        value: function onChange(row, col, val) {
            var nextHeaders = _.cloneDeep(this.props.message.headers);

            nextHeaders[row][col] = val;

            if (!nextHeaders[row][0] && !nextHeaders[row][1]) {
                // do not delete last row
                if (nextHeaders.length === 1) {
                    nextHeaders[0][0] = 'Name';
                    nextHeaders[0][1] = 'Value';
                } else {
                    nextHeaders.splice(row, 1);
                    // manually move selection target if this has been the last row.
                    if (row === nextHeaders.length) {
                        this._nextSel = row - 1 + '-value';
                    }
                }
            }

            this.props.onChange(nextHeaders);
        }
    }, {
        key: 'edit',
        value: function edit() {
            this.refs['0-key'].focus();
        }
    }, {
        key: 'onTab',
        value: function onTab(row, col, e) {
            var headers = this.props.message.headers;

            if (col === 0) {
                this._nextSel = row + '-value';
                return;
            }
            if (row !== headers.length - 1) {
                this._nextSel = row + 1 + '-key';
                return;
            }

            e.preventDefault();

            var nextHeaders = _.cloneDeep(this.props.message.headers);
            nextHeaders.push(['Name', 'Value']);
            this.props.onChange(nextHeaders);
            this._nextSel = row + 1 + '-key';
        }
    }, {
        key: 'componentDidUpdate',
        value: function componentDidUpdate() {
            if (this._nextSel && this.refs[this._nextSel]) {
                this.refs[this._nextSel].focus();
                this._nextSel = undefined;
            }
        }
    }, {
        key: 'onRemove',
        value: function onRemove(row, col, e) {
            if (col === 1) {
                e.preventDefault();
                this.refs[row + '-key'].focus();
            } else if (row > 0) {
                e.preventDefault();
                this.refs[row - 1 + '-value'].focus();
            }
        }
    }, {
        key: 'render',
        value: function render() {
            var _this3 = this;

            var _props2 = this.props;
            var message = _props2.message;
            var readonly = _props2.readonly;


            return _react2.default.createElement(
                'table',
                { className: 'header-table' },
                _react2.default.createElement(
                    'tbody',
                    null,
                    message.headers.map(function (header, i) {
                        return _react2.default.createElement(
                            'tr',
                            { key: i },
                            _react2.default.createElement(
                                'td',
                                { className: 'header-name' },
                                _react2.default.createElement(HeaderEditor, {
                                    ref: i + '-key',
                                    content: header[0],
                                    readonly: readonly,
                                    onDone: function onDone(val) {
                                        return _this3.onChange(i, 0, val);
                                    },
                                    onRemove: function onRemove(event) {
                                        return _this3.onRemove(i, 0, event);
                                    },
                                    onTab: function onTab(event) {
                                        return _this3.onTab(i, 0, event);
                                    }
                                }),
                                _react2.default.createElement(
                                    'span',
                                    { className: 'header-colon' },
                                    ':'
                                )
                            ),
                            _react2.default.createElement(
                                'td',
                                { className: 'header-value' },
                                _react2.default.createElement(HeaderEditor, {
                                    ref: i + '-value',
                                    content: header[1],
                                    readonly: readonly,
                                    onDone: function onDone(val) {
                                        return _this3.onChange(i, 1, val);
                                    },
                                    onRemove: function onRemove(event) {
                                        return _this3.onRemove(i, 1, event);
                                    },
                                    onTab: function onTab(event) {
                                        return _this3.onTab(i, 1, event);
                                    }
                                })
                            )
                        );
                    })
                )
            );
        }
    }]);

    return Headers;
}(_react.Component);

Headers.propTypes = {
    onChange: _react.PropTypes.func.isRequired,
    message: _react.PropTypes.object.isRequired
};
exports.default = Headers;

},{"../../utils":60,"../ValueEditor/ValueEditor":39,"react":"react","react-dom":"react-dom"}],23:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.Response = exports.Request = undefined;

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.ErrorView = ErrorView;

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _utils = require('../../flow/utils.js');

var _utils2 = require('../../utils.js');

var _ContentView = require('../ContentView');

var _ContentView2 = _interopRequireDefault(_ContentView);

var _ContentViewOptions = require('../ContentView/ContentViewOptions');

var _ContentViewOptions2 = _interopRequireDefault(_ContentViewOptions);

var _ValidateEditor = require('../ValueEditor/ValidateEditor');

var _ValidateEditor2 = _interopRequireDefault(_ValidateEditor);

var _ValueEditor = require('../ValueEditor/ValueEditor');

var _ValueEditor2 = _interopRequireDefault(_ValueEditor);

var _Headers = require('./Headers');

var _Headers2 = _interopRequireDefault(_Headers);

var _flow = require('../../ducks/ui/flow');

var _flows = require('../../ducks/flows');

var FlowActions = _interopRequireWildcard(_flows);

var _ToggleEdit = require('./ToggleEdit');

var _ToggleEdit2 = _interopRequireDefault(_ToggleEdit);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

function RequestLine(_ref) {
    var flow = _ref.flow;
    var readonly = _ref.readonly;
    var updateFlow = _ref.updateFlow;

    return _react2.default.createElement(
        'div',
        { className: 'first-line request-line' },
        _react2.default.createElement(
            'div',
            null,
            _react2.default.createElement(_ValueEditor2.default, {
                content: flow.request.method,
                readonly: readonly,
                onDone: function onDone(method) {
                    return updateFlow({ request: { method: method } });
                }
            }),
            ' ',
            _react2.default.createElement(_ValidateEditor2.default, {
                content: _utils.RequestUtils.pretty_url(flow.request),
                readonly: readonly,
                onDone: function onDone(url) {
                    return updateFlow({ request: _extends({ path: '' }, (0, _utils.parseUrl)(url)) });
                },
                isValid: function isValid(url) {
                    return !!(0, _utils.parseUrl)(url).host;
                }
            }),
            ' ',
            _react2.default.createElement(_ValidateEditor2.default, {
                content: flow.request.http_version,
                readonly: readonly,
                onDone: function onDone(http_version) {
                    return updateFlow({ request: { http_version: http_version } });
                },
                isValid: _utils.isValidHttpVersion
            })
        )
    );
}

function ResponseLine(_ref2) {
    var flow = _ref2.flow;
    var readonly = _ref2.readonly;
    var updateFlow = _ref2.updateFlow;

    return _react2.default.createElement(
        'div',
        { className: 'first-line response-line' },
        _react2.default.createElement(_ValidateEditor2.default, {
            content: flow.response.http_version,
            readonly: readonly,
            onDone: function onDone(nextVer) {
                return updateFlow({ response: { http_version: nextVer } });
            },
            isValid: _utils.isValidHttpVersion
        }),
        ' ',
        _react2.default.createElement(_ValidateEditor2.default, {
            content: flow.response.status_code + '',
            readonly: readonly,
            onDone: function onDone(code) {
                return updateFlow({ response: { code: parseInt(code) } });
            },
            isValid: function isValid(code) {
                return (/^\d+$/.test(code)
                );
            }
        }),
        ' ',
        _react2.default.createElement(_ValueEditor2.default, {
            content: flow.response.reason,
            readonly: readonly,
            onDone: function onDone(msg) {
                return updateFlow({ response: { msg: msg } });
            }
        })
    );
}

var Message = (0, _reactRedux.connect)(function (state) {
    return {
        flow: state.ui.flow.modifiedFlow || state.flows.byId[state.flows.selected[0]],
        isEdit: !!state.ui.flow.modifiedFlow
    };
}, {
    updateFlow: _flow.updateEdit,
    uploadContent: FlowActions.uploadContent
});

var Request = exports.Request = function (_Component) {
    _inherits(Request, _Component);

    function Request() {
        _classCallCheck(this, Request);

        return _possibleConstructorReturn(this, Object.getPrototypeOf(Request).apply(this, arguments));
    }

    _createClass(Request, [{
        key: 'render',
        value: function render() {
            var _props = this.props;
            var flow = _props.flow;
            var isEdit = _props.isEdit;
            var updateFlow = _props.updateFlow;
            var _uploadContent = _props.uploadContent;

            var noContent = !isEdit && (flow.request.contentLength == 0 || flow.request.contentLength == null);
            return _react2.default.createElement(
                'section',
                { className: 'request' },
                _react2.default.createElement(
                    'article',
                    null,
                    _react2.default.createElement(_ToggleEdit2.default, null),
                    _react2.default.createElement(RequestLine, {
                        flow: flow,
                        readonly: !isEdit,
                        updateFlow: updateFlow }),
                    _react2.default.createElement(_Headers2.default, {
                        message: flow.request,
                        readonly: !isEdit,
                        onChange: function onChange(headers) {
                            return updateFlow({ request: { headers: headers } });
                        }
                    }),
                    _react2.default.createElement('hr', null),
                    _react2.default.createElement(_ContentView2.default, {
                        readonly: !isEdit,
                        flow: flow,
                        onContentChange: function onContentChange(content) {
                            return updateFlow({ request: { content: content } });
                        },
                        message: flow.request })
                ),
                !noContent && _react2.default.createElement(
                    'footer',
                    null,
                    _react2.default.createElement(_ContentViewOptions2.default, {
                        flow: flow,
                        readonly: !isEdit,
                        message: flow.request,
                        uploadContent: function uploadContent(content) {
                            return _uploadContent(flow, content, "request");
                        } })
                )
            );
        }
    }, {
        key: 'edit',
        value: function edit(k) {
            throw "unimplemented";
            /*
             switch (k) {
             case 'm':
             this.refs.requestLine.refs.method.focus()
             break
             case 'u':
             this.refs.requestLine.refs.url.focus()
             break
             case 'v':
             this.refs.requestLine.refs.httpVersion.focus()
             break
             case 'h':
             this.refs.headers.edit()
             break
             default:
             throw new Error(`Unimplemented: ${k}`)
             }
             */
        }
    }]);

    return Request;
}(_react.Component);

exports.Request = Request = Message(Request);

var Response = exports.Response = function (_Component2) {
    _inherits(Response, _Component2);

    function Response() {
        _classCallCheck(this, Response);

        return _possibleConstructorReturn(this, Object.getPrototypeOf(Response).apply(this, arguments));
    }

    _createClass(Response, [{
        key: 'render',
        value: function render() {
            var _props2 = this.props;
            var flow = _props2.flow;
            var isEdit = _props2.isEdit;
            var updateFlow = _props2.updateFlow;
            var _uploadContent2 = _props2.uploadContent;

            var noContent = !isEdit && (flow.response.contentLength == 0 || flow.response.contentLength == null);

            return _react2.default.createElement(
                'section',
                { className: 'response' },
                _react2.default.createElement(
                    'article',
                    null,
                    _react2.default.createElement(_ToggleEdit2.default, null),
                    _react2.default.createElement(ResponseLine, {
                        flow: flow,
                        readonly: !isEdit,
                        updateFlow: updateFlow }),
                    _react2.default.createElement(_Headers2.default, {
                        message: flow.response,
                        readonly: !isEdit,
                        onChange: function onChange(headers) {
                            return updateFlow({ response: { headers: headers } });
                        }
                    }),
                    _react2.default.createElement('hr', null),
                    _react2.default.createElement(_ContentView2.default, {
                        readonly: !isEdit,
                        flow: flow,
                        onContentChange: function onContentChange(content) {
                            return updateFlow({ response: { content: content } });
                        },
                        message: flow.response
                    })
                ),
                !noContent && _react2.default.createElement(
                    'footer',
                    null,
                    _react2.default.createElement(_ContentViewOptions2.default, {
                        flow: flow,
                        message: flow.response,
                        uploadContent: function uploadContent(content) {
                            return _uploadContent2(flow, content, "response");
                        },
                        readonly: !isEdit })
                )
            );
        }
    }, {
        key: 'edit',
        value: function edit(k) {
            throw "unimplemented";
            /*
             switch (k) {
             case 'c':
             this.refs.responseLine.refs.status_code.focus()
             break
             case 'm':
             this.refs.responseLine.refs.msg.focus()
             break
             case 'v':
             this.refs.responseLine.refs.httpVersion.focus()
             break
             case 'h':
             this.refs.headers.edit()
             break
             default:
             throw new Error(`'Unimplemented: ${k}`)
             }
             */
        }
    }]);

    return Response;
}(_react.Component);

exports.Response = Response = Message(Response);

ErrorView.propTypes = {
    flow: _react.PropTypes.object.isRequired
};

function ErrorView(_ref3) {
    var flow = _ref3.flow;

    return _react2.default.createElement(
        'section',
        { className: 'error' },
        _react2.default.createElement(
            'div',
            { className: 'alert alert-warning' },
            flow.error.msg,
            _react2.default.createElement(
                'div',
                null,
                _react2.default.createElement(
                    'small',
                    null,
                    (0, _utils2.formatTimeStamp)(flow.error.timestamp)
                )
            )
        )
    );
}

},{"../../ducks/flows":49,"../../ducks/ui/flow":52,"../../flow/utils.js":58,"../../utils.js":60,"../ContentView":4,"../ContentView/ContentViewOptions":7,"../ValueEditor/ValidateEditor":38,"../ValueEditor/ValueEditor":39,"./Headers":22,"./ToggleEdit":25,"react":"react","react-redux":"react-redux"}],24:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = Nav;

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _classnames = require('classnames');

var _classnames2 = _interopRequireDefault(_classnames);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

NavAction.propTypes = {
    icon: _react.PropTypes.string.isRequired,
    title: _react.PropTypes.string.isRequired,
    onClick: _react.PropTypes.func.isRequired
};

function NavAction(_ref) {
    var icon = _ref.icon;
    var title = _ref.title;
    var _onClick = _ref.onClick;

    return _react2.default.createElement(
        'a',
        { title: title,
            href: '#',
            className: 'nav-action',
            onClick: function onClick(event) {
                event.preventDefault();
                _onClick(event);
            } },
        _react2.default.createElement('i', { className: 'fa fa-fw ' + icon })
    );
}

Nav.propTypes = {
    active: _react.PropTypes.string.isRequired,
    tabs: _react.PropTypes.array.isRequired,
    onSelectTab: _react.PropTypes.func.isRequired
};

function Nav(_ref2) {
    var active = _ref2.active;
    var tabs = _ref2.tabs;
    var onSelectTab = _ref2.onSelectTab;

    return _react2.default.createElement(
        'nav',
        { className: 'nav-tabs nav-tabs-sm' },
        tabs.map(function (tab) {
            return _react2.default.createElement(
                'a',
                { key: tab,
                    href: '#',
                    className: (0, _classnames2.default)({ active: active === tab }),
                    onClick: function onClick(event) {
                        event.preventDefault();
                        onSelectTab(tab);
                    } },
                _.capitalize(tab)
            );
        })
    );
}

},{"classnames":"classnames","react":"react","react-redux":"react-redux"}],25:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _flow = require('../../ducks/ui/flow');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

ToggleEdit.propTypes = {
    isEdit: _react.PropTypes.bool.isRequired,
    flow: _react.PropTypes.object.isRequired,
    startEdit: _react.PropTypes.func.isRequired,
    stopEdit: _react.PropTypes.func.isRequired
};

function ToggleEdit(_ref) {
    var isEdit = _ref.isEdit;
    var startEdit = _ref.startEdit;
    var stopEdit = _ref.stopEdit;
    var flow = _ref.flow;
    var modifiedFlow = _ref.modifiedFlow;

    return _react2.default.createElement(
        'div',
        { className: 'edit-flow-container' },
        isEdit ? _react2.default.createElement(
            'a',
            { className: 'edit-flow', title: 'Finish Edit', onClick: function onClick() {
                    return stopEdit(flow, modifiedFlow);
                } },
            _react2.default.createElement('i', { className: 'fa fa-check' })
        ) : _react2.default.createElement(
            'a',
            { className: 'edit-flow', title: 'Edit Flow', onClick: function onClick() {
                    return startEdit(flow);
                } },
            _react2.default.createElement('i', { className: 'fa fa-pencil' })
        )
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        isEdit: !!state.ui.flow.modifiedFlow,
        modifiedFlow: state.ui.flow.modifiedFlow || state.flows.byId[state.flows.selected[0]],
        flow: state.flows.byId[state.flows.selected[0]]
    };
}, {
    startEdit: _flow.startEdit,
    stopEdit: _flow.stopEdit
})(ToggleEdit);

},{"../../ducks/ui/flow":52,"react":"react","react-redux":"react-redux"}],26:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _utils = require('../utils.js');

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
    var websocket = settings.websocket;
    var anticache = settings.anticache;
    var anticomp = settings.anticomp;
    var stickyauth = settings.stickyauth;
    var stickycookie = settings.stickycookie;
    var stream_large_bodies = settings.stream_large_bodies;
    var listen_host = settings.listen_host;
    var listen_port = settings.listen_port;
    var version = settings.version;

    return _react2.default.createElement(
        'footer',
        null,
        mode && mode != "regular" && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            mode,
            ' mode'
        ),
        intercept && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'Intercept: ',
            intercept
        ),
        showhost && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'showhost'
        ),
        no_upstream_cert && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'no-upstream-cert'
        ),
        rawtcp && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'raw-tcp'
        ),
        !http2 && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'no-http2'
        ),
        !websocket && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'no-websocket'
        ),
        anticache && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'anticache'
        ),
        anticomp && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'anticomp'
        ),
        stickyauth && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'stickyauth: ',
            stickyauth
        ),
        stickycookie && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'stickycookie: ',
            stickycookie
        ),
        stream_large_bodies && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'stream: ',
            (0, _utils.formatSize)(stream_large_bodies)
        ),
        _react2.default.createElement(
            'div',
            { className: 'pull-right' },
            _react2.default.createElement(
                'span',
                { className: 'label label-primary', title: 'HTTP Proxy Server Address' },
                listen_host || "*",
                ':',
                listen_port
            ),
            _react2.default.createElement(
                'span',
                { className: 'label label-info', title: 'Mitmproxy Version' },
                'v',
                version
            )
        )
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        settings: state.settings
    };
})(Footer);

},{"../utils.js":60,"react":"react","react-redux":"react-redux"}],27:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _classnames = require('classnames');

var _classnames2 = _interopRequireDefault(_classnames);

var _MainMenu = require('./Header/MainMenu');

var _MainMenu2 = _interopRequireDefault(_MainMenu);

var _OptionMenu = require('./Header/OptionMenu');

var _OptionMenu2 = _interopRequireDefault(_OptionMenu);

var _FileMenu = require('./Header/FileMenu');

var _FileMenu2 = _interopRequireDefault(_FileMenu);

var _FlowMenu = require('./Header/FlowMenu');

var _FlowMenu2 = _interopRequireDefault(_FlowMenu);

var _header = require('../ducks/ui/header');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _toConsumableArray(arr) { if (Array.isArray(arr)) { for (var i = 0, arr2 = Array(arr.length); i < arr.length; i++) { arr2[i] = arr[i]; } return arr2; } else { return Array.from(arr); } }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var Header = function (_Component) {
    _inherits(Header, _Component);

    function Header() {
        _classCallCheck(this, Header);

        return _possibleConstructorReturn(this, Object.getPrototypeOf(Header).apply(this, arguments));
    }

    _createClass(Header, [{
        key: 'handleClick',
        value: function handleClick(active, e) {
            e.preventDefault();
            this.props.setActiveMenu(active.title);
        }
    }, {
        key: 'render',
        value: function render() {
            var _this2 = this;

            var _props = this.props;
            var selectedFlowId = _props.selectedFlowId;
            var activeMenu = _props.activeMenu;


            var entries = [].concat(_toConsumableArray(Header.entries));
            if (selectedFlowId) entries.push(_FlowMenu2.default);

            // Make sure to have a fallback in case FlowMenu is selected but we don't have any flows
            // (e.g. because they are all deleted or not yet received)
            var Active = _.find(entries, function (e) {
                return e.title == activeMenu;
            }) || _MainMenu2.default;

            return _react2.default.createElement(
                'header',
                null,
                _react2.default.createElement(
                    'nav',
                    { className: 'nav-tabs nav-tabs-lg' },
                    _react2.default.createElement(_FileMenu2.default, null),
                    entries.map(function (Entry) {
                        return _react2.default.createElement(
                            'a',
                            { key: Entry.title,
                                href: '#',
                                className: (0, _classnames2.default)({ active: Entry === Active }),
                                onClick: function onClick(e) {
                                    return _this2.handleClick(Entry, e);
                                } },
                            Entry.title
                        );
                    })
                ),
                _react2.default.createElement(
                    'menu',
                    null,
                    _react2.default.createElement(Active, null)
                )
            );
        }
    }]);

    return Header;
}(_react.Component);

Header.entries = [_MainMenu2.default, _OptionMenu2.default];
exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        selectedFlowId: state.flows.selected[0],
        activeMenu: state.ui.header.activeMenu
    };
}, {
    setActiveMenu: _header.setActiveMenu
})(Header);

},{"../ducks/ui/header":53,"./Header/FileMenu":28,"./Header/FlowMenu":31,"./Header/MainMenu":32,"./Header/OptionMenu":34,"classnames":"classnames","react":"react","react-redux":"react-redux"}],28:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _FileChooser = require('../common/FileChooser');

var _FileChooser2 = _interopRequireDefault(_FileChooser);

var _Dropdown = require('../common/Dropdown');

var _Dropdown2 = _interopRequireDefault(_Dropdown);

var _flows = require('../../ducks/flows');

var flowsActions = _interopRequireWildcard(_flows);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

FileMenu.propTypes = {
    clearFlows: _react.PropTypes.func.isRequired,
    loadFlows: _react.PropTypes.func.isRequired,
    saveFlows: _react.PropTypes.func.isRequired
};

FileMenu.onNewClick = function (e, clearFlows) {
    e.preventDefault();
    if (confirm('Delete all flows?')) clearFlows();
};

function FileMenu(_ref) {
    var clearFlows = _ref.clearFlows;
    var loadFlows = _ref.loadFlows;
    var saveFlows = _ref.saveFlows;

    return _react2.default.createElement(
        _Dropdown2.default,
        { className: 'pull-left', btnClass: 'special', text: 'mitmproxy' },
        _react2.default.createElement(
            'a',
            { href: '#', onClick: function onClick(e) {
                    return FileMenu.onNewClick(e, clearFlows);
                } },
            _react2.default.createElement('i', { className: 'fa fa-fw fa-file' }),
            ' New'
        ),
        _react2.default.createElement(_FileChooser2.default, {
            icon: 'fa-folder-open',
            text: ' Open...',
            onOpenFile: function onOpenFile(file) {
                return loadFlows(file);
            }
        }),
        _react2.default.createElement(
            'a',
            { href: '#', onClick: function onClick(e) {
                    e.preventDefault();saveFlows();
                } },
            _react2.default.createElement('i', { className: 'fa fa-fw fa-floppy-o' }),
            ' Save...'
        ),
        _react2.default.createElement(_Dropdown.Divider, null),
        _react2.default.createElement(
            'a',
            { href: 'http://mitm.it/', target: '_blank' },
            _react2.default.createElement('i', { className: 'fa fa-fw fa-external-link' }),
            ' Install Certificates...'
        )
    );
}

exports.default = (0, _reactRedux.connect)(null, {
    clearFlows: flowsActions.clear,
    loadFlows: flowsActions.upload,
    saveFlows: flowsActions.download
})(FileMenu);

},{"../../ducks/flows":49,"../common/Dropdown":42,"../common/FileChooser":43,"react":"react","react-redux":"react-redux"}],29:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _utils = require('../../utils');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var FilterDocs = function (_Component) {
    _inherits(FilterDocs, _Component);

    // @todo move to redux

    function FilterDocs(props, context) {
        _classCallCheck(this, FilterDocs);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(FilterDocs).call(this, props, context));

        _this.state = { doc: FilterDocs.doc };
        return _this;
    }

    _createClass(FilterDocs, [{
        key: 'componentWillMount',
        value: function componentWillMount() {
            var _this2 = this;

            if (!FilterDocs.xhr) {
                FilterDocs.xhr = (0, _utils.fetchApi)('/filter-help').then(function (response) {
                    return response.json();
                });
                FilterDocs.xhr.catch(function () {
                    FilterDocs.xhr = null;
                });
            }
            if (!this.state.doc) {
                FilterDocs.xhr.then(function (doc) {
                    FilterDocs.doc = doc;
                    _this2.setState({ doc: doc });
                });
            }
        }
    }, {
        key: 'render',
        value: function render() {
            var doc = this.state.doc;

            return !doc ? _react2.default.createElement('i', { className: 'fa fa-spinner fa-spin' }) : _react2.default.createElement(
                'table',
                { className: 'table table-condensed' },
                _react2.default.createElement(
                    'tbody',
                    null,
                    doc.commands.map(function (cmd) {
                        return _react2.default.createElement(
                            'tr',
                            { key: cmd[1] },
                            _react2.default.createElement(
                                'td',
                                null,
                                cmd[0].replace(' ', ' ')
                            ),
                            _react2.default.createElement(
                                'td',
                                null,
                                cmd[1]
                            )
                        );
                    }),
                    _react2.default.createElement(
                        'tr',
                        { key: 'docs-link' },
                        _react2.default.createElement(
                            'td',
                            { colSpan: '2' },
                            _react2.default.createElement(
                                'a',
                                { href: 'http://docs.mitmproxy.org/en/stable/features/filters.html',
                                    target: '_blank' },
                                _react2.default.createElement('i', { className: 'fa fa-external-link' }),
                                '  mitmproxy docs'
                            )
                        )
                    )
                )
            );
        }
    }]);

    return FilterDocs;
}(_react.Component);

FilterDocs.xhr = null;
FilterDocs.doc = null;
exports.default = FilterDocs;

},{"../../utils":60,"react":"react"}],30:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactDom = require('react-dom');

var _reactDom2 = _interopRequireDefault(_reactDom);

var _classnames = require('classnames');

var _classnames2 = _interopRequireDefault(_classnames);

var _utils = require('../../utils.js');

var _filt = require('../../filt/filt');

var _filt2 = _interopRequireDefault(_filt);

var _FilterDocs = require('./FilterDocs');

var _FilterDocs2 = _interopRequireDefault(_FilterDocs);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var FilterInput = function (_Component) {
    _inherits(FilterInput, _Component);

    function FilterInput(props, context) {
        _classCallCheck(this, FilterInput);

        // Consider both focus and mouseover for showing/hiding the tooltip,
        // because onBlur of the input is triggered before the click on the tooltip
        // finalized, hiding the tooltip just as the user clicks on it.

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(FilterInput).call(this, props, context));

        _this.state = { value: _this.props.value, focus: false, mousefocus: false };

        _this.onChange = _this.onChange.bind(_this);
        _this.onFocus = _this.onFocus.bind(_this);
        _this.onBlur = _this.onBlur.bind(_this);
        _this.onKeyDown = _this.onKeyDown.bind(_this);
        _this.onMouseEnter = _this.onMouseEnter.bind(_this);
        _this.onMouseLeave = _this.onMouseLeave.bind(_this);
        return _this;
    }

    _createClass(FilterInput, [{
        key: 'componentWillReceiveProps',
        value: function componentWillReceiveProps(nextProps) {
            this.setState({ value: nextProps.value });
        }
    }, {
        key: 'isValid',
        value: function isValid(filt) {
            try {
                var str = filt == null ? this.state.value : filt;
                if (str) {
                    _filt2.default.parse(str);
                }
                return true;
            } catch (e) {
                return false;
            }
        }
    }, {
        key: 'getDesc',
        value: function getDesc() {
            if (!this.state.value) {
                return _react2.default.createElement(_FilterDocs2.default, null);
            }
            try {
                return _filt2.default.parse(this.state.value).desc;
            } catch (e) {
                return '' + e;
            }
        }
    }, {
        key: 'onChange',
        value: function onChange(e) {
            var value = e.target.value;
            this.setState({ value: value });

            // Only propagate valid filters upwards.
            if (this.isValid(value)) {
                this.props.onChange(value);
            }
        }
    }, {
        key: 'onFocus',
        value: function onFocus() {
            this.setState({ focus: true });
        }
    }, {
        key: 'onBlur',
        value: function onBlur() {
            this.setState({ focus: false });
        }
    }, {
        key: 'onMouseEnter',
        value: function onMouseEnter() {
            this.setState({ mousefocus: true });
        }
    }, {
        key: 'onMouseLeave',
        value: function onMouseLeave() {
            this.setState({ mousefocus: false });
        }
    }, {
        key: 'onKeyDown',
        value: function onKeyDown(e) {
            if (e.keyCode === _utils.Key.ESC || e.keyCode === _utils.Key.ENTER) {
                this.blur();
                // If closed using ESC/ENTER, hide the tooltip.
                this.setState({ mousefocus: false });
            }
            e.stopPropagation();
        }
    }, {
        key: 'blur',
        value: function blur() {
            _reactDom2.default.findDOMNode(this.refs.input).blur();
        }
    }, {
        key: 'select',
        value: function select() {
            _reactDom2.default.findDOMNode(this.refs.input).select();
        }
    }, {
        key: 'render',
        value: function render() {
            var _props = this.props;
            var type = _props.type;
            var color = _props.color;
            var placeholder = _props.placeholder;
            var _state = this.state;
            var value = _state.value;
            var focus = _state.focus;
            var mousefocus = _state.mousefocus;

            return _react2.default.createElement(
                'div',
                { className: (0, _classnames2.default)('filter-input input-group', { 'has-error': !this.isValid() }) },
                _react2.default.createElement(
                    'span',
                    { className: 'input-group-addon' },
                    _react2.default.createElement('i', { className: 'fa fa-fw fa-' + type, style: { color: color } })
                ),
                _react2.default.createElement('input', {
                    type: 'text',
                    ref: 'input',
                    placeholder: placeholder,
                    className: 'form-control',
                    value: value,
                    onChange: this.onChange,
                    onFocus: this.onFocus,
                    onBlur: this.onBlur,
                    onKeyDown: this.onKeyDown
                }),
                (focus || mousefocus) && _react2.default.createElement(
                    'div',
                    { className: 'popover bottom',
                        onMouseEnter: this.onMouseEnter,
                        onMouseLeave: this.onMouseLeave },
                    _react2.default.createElement('div', { className: 'arrow' }),
                    _react2.default.createElement(
                        'div',
                        { className: 'popover-content' },
                        this.getDesc()
                    )
                )
            );
        }
    }]);

    return FilterInput;
}(_react.Component);

exports.default = FilterInput;

},{"../../filt/filt":57,"../../utils.js":60,"./FilterDocs":29,"classnames":"classnames","react":"react","react-dom":"react-dom"}],31:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require("react-redux");

var _Button = require("../common/Button");

var _Button2 = _interopRequireDefault(_Button);

var _utils = require("../../flow/utils.js");

var _flows = require("../../ducks/flows");

var flowsActions = _interopRequireWildcard(_flows);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

FlowMenu.title = 'Flow';

FlowMenu.propTypes = {
    flow: _react.PropTypes.object,
    resumeFlow: _react.PropTypes.func.isRequired,
    killFlow: _react.PropTypes.func.isRequired,
    replayFlow: _react.PropTypes.func.isRequired,
    duplicateFlow: _react.PropTypes.func.isRequired,
    removeFlow: _react.PropTypes.func.isRequired,
    revertFlow: _react.PropTypes.func.isRequired
};

function FlowMenu(_ref) {
    var flow = _ref.flow;
    var resumeFlow = _ref.resumeFlow;
    var killFlow = _ref.killFlow;
    var replayFlow = _ref.replayFlow;
    var duplicateFlow = _ref.duplicateFlow;
    var removeFlow = _ref.removeFlow;
    var revertFlow = _ref.revertFlow;

    if (!flow) return _react2.default.createElement("div", null);
    return _react2.default.createElement(
        "div",
        null,
        _react2.default.createElement(
            "div",
            { className: "menu-group" },
            _react2.default.createElement(
                "div",
                { className: "menu-content" },
                _react2.default.createElement(
                    _Button2.default,
                    { title: "[r]eplay flow", icon: "fa-repeat text-primary",
                        onClick: function onClick() {
                            return replayFlow(flow);
                        } },
                    "Replay"
                ),
                _react2.default.createElement(
                    _Button2.default,
                    { title: "[D]uplicate flow", icon: "fa-copy text-info",
                        onClick: function onClick() {
                            return duplicateFlow(flow);
                        } },
                    "Duplicate"
                ),
                _react2.default.createElement(
                    _Button2.default,
                    { disabled: !flow || !flow.modified, title: "revert changes to flow [V]",
                        icon: "fa-history text-warning", onClick: function onClick() {
                            return revertFlow(flow);
                        } },
                    "Revert"
                ),
                _react2.default.createElement(
                    _Button2.default,
                    { title: "[d]elete flow", icon: "fa-trash text-danger",
                        onClick: function onClick() {
                            return removeFlow(flow);
                        } },
                    "Delete"
                )
            ),
            _react2.default.createElement(
                "div",
                { className: "menu-legend" },
                "Flow Modification"
            )
        ),
        _react2.default.createElement(
            "div",
            { className: "menu-group" },
            _react2.default.createElement(
                "div",
                { className: "menu-content" },
                _react2.default.createElement(
                    _Button2.default,
                    { title: "download", icon: "fa-download",
                        onClick: function onClick() {
                            return window.location = _utils.MessageUtils.getContentURL(flow, flow.response);
                        } },
                    "Download"
                )
            ),
            _react2.default.createElement(
                "div",
                { className: "menu-legend" },
                "Export"
            )
        ),
        _react2.default.createElement(
            "div",
            { className: "menu-group" },
            _react2.default.createElement(
                "div",
                { className: "menu-content" },
                _react2.default.createElement(
                    _Button2.default,
                    { disabled: !flow || !flow.intercepted, title: "[a]ccept intercepted flow",
                        icon: "fa-play text-success", onClick: function onClick() {
                            return resumeFlow(flow);
                        } },
                    "Resume"
                ),
                _react2.default.createElement(
                    _Button2.default,
                    { disabled: !flow || !flow.intercepted, title: "kill intercepted flow [x]",
                        icon: "fa-times text-danger", onClick: function onClick() {
                            return killFlow(flow);
                        } },
                    "Abort"
                )
            ),
            _react2.default.createElement(
                "div",
                { className: "menu-legend" },
                "Interception"
            )
        )
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        flow: state.flows.byId[state.flows.selected[0]]
    };
}, {
    resumeFlow: flowsActions.resume,
    killFlow: flowsActions.kill,
    replayFlow: flowsActions.replay,
    duplicateFlow: flowsActions.duplicate,
    removeFlow: flowsActions.remove,
    revertFlow: flowsActions.revert
})(FlowMenu);

},{"../../ducks/flows":49,"../../flow/utils.js":58,"../common/Button":40,"react":"react","react-redux":"react-redux"}],32:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = MainMenu;

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require("react-redux");

var _FilterInput = require("./FilterInput");

var _FilterInput2 = _interopRequireDefault(_FilterInput);

var _settings = require("../../ducks/settings");

var _flows = require("../../ducks/flows");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

MainMenu.title = "Start";

function MainMenu() {
    return _react2.default.createElement(
        "div",
        { className: "menu-main" },
        _react2.default.createElement(FlowFilterInput, null),
        _react2.default.createElement(HighlightInput, null),
        _react2.default.createElement(InterceptInput, null)
    );
}

var InterceptInput = (0, _reactRedux.connect)(function (state) {
    return {
        value: state.settings.intercept || '',
        placeholder: 'Intercept',
        type: 'pause',
        color: 'hsl(208, 56%, 53%)'
    };
}, { onChange: function onChange(intercept) {
        return (0, _settings.update)({ intercept: intercept });
    } })(_FilterInput2.default);

var FlowFilterInput = (0, _reactRedux.connect)(function (state) {
    return {
        value: state.flows.filter || '',
        placeholder: 'Search',
        type: 'search',
        color: 'black'
    };
}, { onChange: _flows.setFilter })(_FilterInput2.default);

var HighlightInput = (0, _reactRedux.connect)(function (state) {
    return {
        value: state.flows.highlight || '',
        placeholder: 'Highlight',
        type: 'tag',
        color: 'hsl(48, 100%, 50%)'
    };
}, { onChange: _flows.setHighlight })(_FilterInput2.default);

},{"../../ducks/flows":49,"../../ducks/settings":51,"./FilterInput":30,"react":"react","react-redux":"react-redux"}],33:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.MenuToggle = MenuToggle;
exports.SettingsToggle = SettingsToggle;
exports.EventlogToggle = EventlogToggle;

var _react = require("react");

var _reactRedux = require("react-redux");

var _settings = require("../../ducks/settings");

var _eventLog = require("../../ducks/eventLog");

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

MenuToggle.propTypes = {
    value: _react.PropTypes.bool.isRequired,
    onChange: _react.PropTypes.func.isRequired,
    children: _react.PropTypes.node.isRequired
};

function MenuToggle(_ref) {
    var value = _ref.value;
    var onChange = _ref.onChange;
    var children = _ref.children;

    return React.createElement(
        "div",
        { className: "menu-entry" },
        React.createElement(
            "label",
            null,
            React.createElement("input", { type: "checkbox",
                checked: value,
                onChange: onChange }),
            children
        )
    );
}

SettingsToggle.propTypes = {
    setting: _react.PropTypes.string.isRequired,
    children: _react.PropTypes.node.isRequired
};

function SettingsToggle(_ref2) {
    var setting = _ref2.setting;
    var children = _ref2.children;
    var settings = _ref2.settings;
    var updateSettings = _ref2.updateSettings;

    return React.createElement(
        MenuToggle,
        {
            value: settings[setting] || false // we don't have settings initially, so just pass false.
            , onChange: function onChange() {
                return updateSettings(_defineProperty({}, setting, !settings[setting]));
            }
        },
        children
    );
}
exports.SettingsToggle = SettingsToggle = (0, _reactRedux.connect)(function (state) {
    return {
        settings: state.settings
    };
}, {
    updateSettings: _settings.update
})(SettingsToggle);

function EventlogToggle(_ref3) {
    var toggleVisibility = _ref3.toggleVisibility;
    var eventLogVisible = _ref3.eventLogVisible;

    return React.createElement(
        MenuToggle,
        {
            value: eventLogVisible,
            onChange: toggleVisibility
        },
        "Display Event Log"
    );
}
exports.EventlogToggle = EventlogToggle = (0, _reactRedux.connect)(function (state) {
    return {
        eventLogVisible: state.eventLog.visible
    };
}, {
    toggleVisibility: _eventLog.toggleVisibility
})(EventlogToggle);

},{"../../ducks/eventLog":48,"../../ducks/settings":51,"react":"react","react-redux":"react-redux"}],34:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = OptionMenu;

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require("react-redux");

var _MenuToggle = require("./MenuToggle");

var _DocsLink = require("../common/DocsLink");

var _DocsLink2 = _interopRequireDefault(_DocsLink);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

OptionMenu.title = 'Options';

function OptionMenu() {
    return _react2.default.createElement(
        "div",
        null,
        _react2.default.createElement(
            "div",
            { className: "menu-group" },
            _react2.default.createElement(
                "div",
                { className: "menu-content" },
                _react2.default.createElement(
                    _MenuToggle.SettingsToggle,
                    { setting: "http2" },
                    "HTTP/2.0"
                ),
                _react2.default.createElement(
                    _MenuToggle.SettingsToggle,
                    { setting: "websocket" },
                    "WebSockets"
                ),
                _react2.default.createElement(
                    _MenuToggle.SettingsToggle,
                    { setting: "rawtcp" },
                    "Raw TCP"
                )
            ),
            _react2.default.createElement(
                "div",
                { className: "menu-legend" },
                "Protocol Support"
            )
        ),
        _react2.default.createElement(
            "div",
            { className: "menu-group" },
            _react2.default.createElement(
                "div",
                { className: "menu-content" },
                _react2.default.createElement(
                    _MenuToggle.SettingsToggle,
                    { setting: "anticache" },
                    "Disable Caching ",
                    _react2.default.createElement(_DocsLink2.default, { resource: "features/anticache.html" })
                ),
                _react2.default.createElement(
                    _MenuToggle.SettingsToggle,
                    { setting: "anticomp" },
                    "Disable Compression ",
                    _react2.default.createElement("i", { className: "fa fa-question-circle",
                        title: "Do not forward Accept-Encoding headers to the server to force an uncompressed response." })
                )
            ),
            _react2.default.createElement(
                "div",
                { className: "menu-legend" },
                "HTTP Options"
            )
        ),
        _react2.default.createElement(
            "div",
            { className: "menu-group" },
            _react2.default.createElement(
                "div",
                { className: "menu-content" },
                _react2.default.createElement(
                    _MenuToggle.SettingsToggle,
                    { setting: "showhost" },
                    "Use Host Header ",
                    _react2.default.createElement("i", { className: "fa fa-question-circle",
                        title: "Use the Host header to construct URLs for display." })
                ),
                _react2.default.createElement(_MenuToggle.EventlogToggle, null)
            ),
            _react2.default.createElement(
                "div",
                { className: "menu-legend" },
                "View Options"
            )
        )
    );
}

},{"../common/DocsLink":41,"./MenuToggle":33,"react":"react","react-redux":"react-redux"}],35:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _Splitter = require('./common/Splitter');

var _Splitter2 = _interopRequireDefault(_Splitter);

var _FlowTable = require('./FlowTable');

var _FlowTable2 = _interopRequireDefault(_FlowTable);

var _FlowView = require('./FlowView');

var _FlowView2 = _interopRequireDefault(_FlowView);

var _flows = require('../ducks/flows');

var flowsActions = _interopRequireWildcard(_flows);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

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
        key: 'render',
        value: function render() {
            var _this2 = this;

            var _props = this.props;
            var flows = _props.flows;
            var selectedFlow = _props.selectedFlow;
            var highlight = _props.highlight;

            return _react2.default.createElement(
                'div',
                { className: 'main-view' },
                _react2.default.createElement(_FlowTable2.default, {
                    ref: 'flowTable',
                    flows: flows,
                    selected: selectedFlow,
                    highlight: highlight,
                    onSelect: this.props.selectFlow
                }),
                selectedFlow && [_react2.default.createElement(_Splitter2.default, { key: 'splitter' }), _react2.default.createElement(_FlowView2.default, {
                    key: 'flowDetails',
                    ref: 'flowDetails',
                    tab: this.props.tab,
                    updateFlow: function updateFlow(data) {
                        return _this2.props.updateFlow(selectedFlow, data);
                    },
                    flow: selectedFlow
                })]
            );
        }
    }]);

    return MainView;
}(_react.Component);

MainView.propTypes = {
    highlight: _react.PropTypes.string,
    sort: _react.PropTypes.object
};
exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        flows: state.flows.view,
        filter: state.flows.filter,
        highlight: state.flows.highlight,
        selectedFlow: state.flows.byId[state.flows.selected[0]],
        tab: state.ui.flow.tab
    };
}, {
    selectFlow: flowsActions.select,
    updateFlow: flowsActions.update
})(MainView);

},{"../ducks/flows":49,"./FlowTable":16,"./FlowView":20,"./common/Splitter":44,"react":"react","react-redux":"react-redux"}],36:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = Prompt;

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactDom = require('react-dom');

var _reactDom2 = _interopRequireDefault(_reactDom);

var _lodash = require('lodash');

var _lodash2 = _interopRequireDefault(_lodash);

var _utils = require('../utils.js');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

Prompt.propTypes = {
    options: _react.PropTypes.array.isRequired,
    done: _react.PropTypes.func.isRequired,
    prompt: _react.PropTypes.string
};

function Prompt(_ref) {
    var prompt = _ref.prompt;
    var done = _ref.done;
    var options = _ref.options;

    var opts = [];

    for (var i = 0; i < options.length; i++) {
        var opt = options[i];
        if (_lodash2.default.isString(opt)) {
            var str = opt;
            while (str.length > 0 && keyTaken(str[0])) {
                str = str.substr(1);
            }
            opt = { text: opt, key: str[0] };
        }
        if (!opt.text || !opt.key || keyTaken(opt.key)) {
            throw 'invalid options';
        }
        opts.push(opt);
    }

    function keyTaken(k) {
        return _lodash2.default.map(opts, 'key').includes(k);
    }

    function onKeyDown(event) {
        event.stopPropagation();
        event.preventDefault();
        var key = opts.find(function (opt) {
            return _utils.Key[opt.key.toUpperCase()] === event.keyCode;
        });
        if (!key && event.keyCode !== _utils.Key.ESC && event.keyCode !== _utils.Key.ENTER) {
            return;
        }
        done(key.key || false);
    }

    return _react2.default.createElement(
        'div',
        { tabIndex: '0', onKeyDown: onKeyDown, className: 'prompt-dialog' },
        _react2.default.createElement(
            'div',
            { className: 'prompt-content' },
            prompt || _react2.default.createElement(
                'strong',
                null,
                'Select: '
            ),
            opts.map(function (opt) {
                var idx = opt.text.indexOf(opt.key);
                function onClick(event) {
                    done(opt.key);
                    event.stopPropagation();
                }
                return _react2.default.createElement(
                    'span',
                    { key: opt.key, className: 'option', onClick: onClick },
                    idx !== -1 ? opt.text.substring(0, idx) : opt.text + '(',
                    _react2.default.createElement(
                        'strong',
                        { className: 'text-primary' },
                        opt.key
                    ),
                    idx !== -1 ? opt.text.substring(idx + 1) : ')'
                );
            })
        )
    );
}

},{"../utils.js":60,"lodash":"lodash","react":"react","react-dom":"react-dom"}],37:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _keyboard = require('../ducks/ui/keyboard');

var _MainView = require('./MainView');

var _MainView2 = _interopRequireDefault(_MainView);

var _Header = require('./Header');

var _Header2 = _interopRequireDefault(_Header);

var _EventLog = require('./EventLog');

var _EventLog2 = _interopRequireDefault(_EventLog);

var _Footer = require('./Footer');

var _Footer2 = _interopRequireDefault(_Footer);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var ProxyAppMain = function (_Component) {
    _inherits(ProxyAppMain, _Component);

    function ProxyAppMain() {
        _classCallCheck(this, ProxyAppMain);

        return _possibleConstructorReturn(this, Object.getPrototypeOf(ProxyAppMain).apply(this, arguments));
    }

    _createClass(ProxyAppMain, [{
        key: 'componentWillMount',
        value: function componentWillMount() {
            window.addEventListener('keydown', this.props.onKeyDown);
        }
    }, {
        key: 'componentWillUnmount',
        value: function componentWillUnmount() {
            window.removeEventListener('keydown', this.props.onKeyDown);
        }
    }, {
        key: 'render',
        value: function render() {
            var _props = this.props;
            var showEventLog = _props.showEventLog;
            var location = _props.location;
            var filter = _props.filter;
            var highlight = _props.highlight;

            return _react2.default.createElement(
                'div',
                { id: 'container', tabIndex: '0' },
                _react2.default.createElement(_Header2.default, null),
                _react2.default.createElement(_MainView2.default, null),
                showEventLog && _react2.default.createElement(_EventLog2.default, { key: 'eventlog' }),
                _react2.default.createElement(_Footer2.default, null)
            );
        }
    }]);

    return ProxyAppMain;
}(_react.Component);

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        showEventLog: state.eventLog.visible
    };
}, {
    onKeyDown: _keyboard.onKeyDown
})(ProxyAppMain);

},{"../ducks/ui/keyboard":55,"./EventLog":14,"./Footer":26,"./Header":27,"./MainView":35,"react":"react","react-redux":"react-redux"}],38:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _ValueEditor = require('./ValueEditor');

var _ValueEditor2 = _interopRequireDefault(_ValueEditor);

var _classnames = require('classnames');

var _classnames2 = _interopRequireDefault(_classnames);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var ValidateEditor = function (_Component) {
    _inherits(ValidateEditor, _Component);

    function ValidateEditor(props) {
        _classCallCheck(this, ValidateEditor);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(ValidateEditor).call(this, props));

        _this.state = { valid: props.isValid(props.content) };
        _this.onInput = _this.onInput.bind(_this);
        _this.onDone = _this.onDone.bind(_this);
        return _this;
    }

    _createClass(ValidateEditor, [{
        key: 'componentWillReceiveProps',
        value: function componentWillReceiveProps(nextProps) {
            this.setState({ valid: nextProps.isValid(nextProps.content) });
        }
    }, {
        key: 'onInput',
        value: function onInput(content) {
            this.setState({ valid: this.props.isValid(content) });
        }
    }, {
        key: 'onDone',
        value: function onDone(content) {
            if (!this.props.isValid(content)) {
                this.editor.reset();
                content = this.props.content;
            }
            this.props.onDone(content);
        }
    }, {
        key: 'render',
        value: function render() {
            var _this2 = this;

            var className = (0, _classnames2.default)(this.props.className, {
                'has-success': this.state.valid,
                'has-warning': !this.state.valid
            });
            return _react2.default.createElement(_ValueEditor2.default, {
                content: this.props.content,
                readonly: this.props.readonly,
                onDone: this.onDone,
                onInput: this.onInput,
                className: className,
                ref: function ref(e) {
                    return _this2.editor = e;
                }
            });
        }
    }]);

    return ValidateEditor;
}(_react.Component);

ValidateEditor.propTypes = {
    content: _react.PropTypes.string.isRequired,
    readonly: _react.PropTypes.bool,
    onDone: _react.PropTypes.func.isRequired,
    className: _react.PropTypes.string,
    isValid: _react.PropTypes.func.isRequired
};
exports.default = ValidateEditor;

},{"./ValueEditor":39,"classnames":"classnames","react":"react"}],39:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _lodash = require('lodash');

var _lodash2 = _interopRequireDefault(_lodash);

var _classnames = require('classnames');

var _classnames2 = _interopRequireDefault(_classnames);

var _utils = require('../../utils');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var ValueEditor = function (_Component) {
    _inherits(ValueEditor, _Component);

    function ValueEditor(props) {
        _classCallCheck(this, ValueEditor);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(ValueEditor).call(this, props));

        _this.state = { editable: false };

        _this.onPaste = _this.onPaste.bind(_this);
        _this.onMouseDown = _this.onMouseDown.bind(_this);
        _this.onMouseUp = _this.onMouseUp.bind(_this);
        _this.onFocus = _this.onFocus.bind(_this);
        _this.onClick = _this.onClick.bind(_this);
        _this.blur = _this.blur.bind(_this);
        _this.onBlur = _this.onBlur.bind(_this);
        _this.reset = _this.reset.bind(_this);
        _this.onKeyDown = _this.onKeyDown.bind(_this);
        _this.onInput = _this.onInput.bind(_this);
        return _this;
    }

    _createClass(ValueEditor, [{
        key: 'blur',
        value: function blur() {
            // a stop would cause a blur as a side-effect.
            // but a blur event must trigger a stop as well.
            // to fix this, make stop = blur and do the actual stop in the onBlur handler.
            this.input.blur();
        }
    }, {
        key: 'reset',
        value: function reset() {
            this.input.innerHTML = _lodash2.default.escape(this.props.content);
        }
    }, {
        key: 'render',
        value: function render() {
            var _this2 = this;

            var className = (0, _classnames2.default)('inline-input', {
                'readonly': this.props.readonly,
                'editable': !this.props.readonly
            }, this.props.className);
            return _react2.default.createElement('div', {
                ref: function ref(input) {
                    return _this2.input = input;
                },
                tabIndex: this.props.readonly ? undefined : 0,
                className: className,
                contentEditable: this.state.editable || undefined,
                onFocus: this.onFocus,
                onMouseDown: this.onMouseDown,
                onClick: this.onClick,
                onBlur: this.onBlur,
                onKeyDown: this.onKeyDown,
                onInput: this.onInput,
                onPaste: this.onPaste,
                dangerouslySetInnerHTML: { __html: _lodash2.default.escape(this.props.content) }
            });
        }
    }, {
        key: 'onPaste',
        value: function onPaste(e) {
            e.preventDefault();
            var content = e.clipboardData.getData('text/plain');
            document.execCommand('insertHTML', false, content);
        }
    }, {
        key: 'onMouseDown',
        value: function onMouseDown(e) {
            this._mouseDown = true;
            window.addEventListener('mouseup', this.onMouseUp);
        }
    }, {
        key: 'onMouseUp',
        value: function onMouseUp() {
            if (this._mouseDown) {
                this._mouseDown = false;
                window.removeEventListener('mouseup', this.onMouseUp);
            }
        }
    }, {
        key: 'onClick',
        value: function onClick(e) {
            this.onMouseUp();
            this.onFocus(e);
        }
    }, {
        key: 'onFocus',
        value: function onFocus(e) {
            var _this3 = this;

            if (this._mouseDown || this._ignore_events || this.state.editable || this.props.readonly) {
                return;
            }

            // contenteditable in FireFox is more or less broken.
            // - we need to blur() and then focus(), otherwise the caret is not shown.
            // - blur() + focus() == we need to save the caret position before
            //   Firefox sometimes just doesn't set a caret position => use caretPositionFromPoint
            var sel = window.getSelection();
            var range = void 0;
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
                range.selectNodeContents(this.input);
            }

            this._ignore_events = true;
            this.setState({ editable: true }, function () {
                _this3.input.blur();
                _this3.input.focus();
                _this3._ignore_events = false;
                range.selectNodeContents(_this3.input);
                sel.removeAllRanges();
                sel.addRange(range);
            });
        }
    }, {
        key: 'onBlur',
        value: function onBlur(e) {
            if (this._ignore_events || this.props.readonly) {
                return;
            }
            window.getSelection().removeAllRanges(); //make sure that selection is cleared on blur
            this.setState({ editable: false });
            this.props.onDone(this.input.textContent);
        }
    }, {
        key: 'onKeyDown',
        value: function onKeyDown(e) {
            e.stopPropagation();
            switch (e.keyCode) {
                case _utils.Key.ESC:
                    e.preventDefault();
                    this.reset();
                    this.blur();
                    break;
                case _utils.Key.ENTER:
                    if (!e.shiftKey) {
                        e.preventDefault();
                        this.blur();
                    }
                    break;
                default:
                    break;
            }
            this.props.onKeyDown(e);
        }
    }, {
        key: 'onInput',
        value: function onInput() {
            this.props.onInput(this.input.textContent);
        }
    }]);

    return ValueEditor;
}(_react.Component);

ValueEditor.propTypes = {
    content: _react.PropTypes.string.isRequired,
    readonly: _react.PropTypes.bool,
    onDone: _react.PropTypes.func.isRequired,
    className: _react.PropTypes.string,
    onInput: _react.PropTypes.func,
    onKeyDown: _react.PropTypes.func
};
ValueEditor.defaultProps = {
    onInput: function onInput() {},
    onKeyDown: function onKeyDown() {}
};
exports.default = ValueEditor;

},{"../../utils":60,"classnames":"classnames","lodash":"lodash","react":"react"}],40:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = Button;

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

var _classnames = require("classnames");

var _classnames2 = _interopRequireDefault(_classnames);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

Button.propTypes = {
    onClick: _react.PropTypes.func.isRequired,
    children: _react.PropTypes.node.isRequired,
    icon: _react.PropTypes.string,
    title: _react.PropTypes.string
};

function Button(_ref) {
    var onClick = _ref.onClick;
    var children = _ref.children;
    var icon = _ref.icon;
    var disabled = _ref.disabled;
    var className = _ref.className;
    var title = _ref.title;

    return _react2.default.createElement(
        "div",
        { className: (0, _classnames2.default)(className, 'btn btn-default'),
            onClick: !disabled && onClick,
            disabled: disabled,
            title: title },
        icon && _react2.default.createElement("i", { className: "fa fa-fw " + icon }),
        children
    );
}

},{"classnames":"classnames","react":"react"}],41:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = DocsLink;

var _react = require("react");

DocsLink.propTypes = {
    resource: _react.PropTypes.string.isRequired
};

function DocsLink(_ref) {
    var children = _ref.children;
    var resource = _ref.resource;

    var url = "http://docs.mitmproxy.org/en/stable/" + resource;
    return React.createElement(
        "a",
        { target: "_blank", href: url },
        children || React.createElement("i", { className: "fa fa-question-circle" })
    );
}

},{"react":"react"}],42:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.Divider = undefined;

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _classnames = require('classnames');

var _classnames2 = _interopRequireDefault(_classnames);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var Divider = exports.Divider = function Divider() {
    return _react2.default.createElement('hr', { className: 'divider' });
};

var Dropdown = function (_Component) {
    _inherits(Dropdown, _Component);

    function Dropdown(props, context) {
        _classCallCheck(this, Dropdown);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(Dropdown).call(this, props, context));

        _this.state = { open: false };
        _this.close = _this.close.bind(_this);
        _this.open = _this.open.bind(_this);
        return _this;
    }

    _createClass(Dropdown, [{
        key: 'close',
        value: function close() {
            this.setState({ open: false });
            document.removeEventListener('click', this.close);
        }
    }, {
        key: 'open',
        value: function open(e) {
            e.preventDefault();
            if (this.state.open) {
                return;
            }
            this.setState({ open: !this.state.open });
            document.addEventListener('click', this.close);
        }
    }, {
        key: 'render',
        value: function render() {
            var _props = this.props;
            var dropup = _props.dropup;
            var className = _props.className;
            var btnClass = _props.btnClass;
            var text = _props.text;
            var children = _props.children;

            return _react2.default.createElement(
                'div',
                { className: (0, _classnames2.default)(dropup ? 'dropup' : 'dropdown', className, { open: this.state.open }) },
                _react2.default.createElement(
                    'a',
                    { href: '#', className: btnClass,
                        onClick: this.open },
                    text
                ),
                _react2.default.createElement(
                    'ul',
                    { className: 'dropdown-menu', role: 'menu' },
                    children.map(function (item, i) {
                        return _react2.default.createElement(
                            'li',
                            { key: i },
                            ' ',
                            item,
                            ' '
                        );
                    })
                )
            );
        }
    }]);

    return Dropdown;
}(_react.Component);

Dropdown.propTypes = {
    dropup: _react.PropTypes.bool,
    className: _react.PropTypes.string,
    btnClass: _react.PropTypes.string.isRequired
};
Dropdown.defaultProps = {
    dropup: false
};
exports.default = Dropdown;

},{"classnames":"classnames","react":"react"}],43:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = FileChooser;

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

FileChooser.propTypes = {
    icon: _react.PropTypes.string,
    text: _react.PropTypes.string,
    className: _react.PropTypes.string,
    title: _react.PropTypes.string,
    onOpenFile: _react.PropTypes.func.isRequired
};

function FileChooser(_ref) {
    var icon = _ref.icon;
    var text = _ref.text;
    var className = _ref.className;
    var title = _ref.title;
    var onOpenFile = _ref.onOpenFile;

    var fileInput = void 0;
    return _react2.default.createElement(
        'a',
        { href: '#', onClick: function onClick() {
                return fileInput.click();
            },
            className: className,
            title: title },
        _react2.default.createElement('i', { className: 'fa fa-fw ' + icon }),
        text,
        _react2.default.createElement('input', {
            ref: function ref(_ref2) {
                return fileInput = _ref2;
            },
            className: 'hidden',
            type: 'file',
            onChange: function onChange(e) {
                e.preventDefault();if (e.target.files.length > 0) onOpenFile(e.target.files[0]);fileInput = "";
            }
        })
    );
}

},{"react":"react"}],44:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactDom = require('react-dom');

var _reactDom2 = _interopRequireDefault(_reactDom);

var _classnames = require('classnames');

var _classnames2 = _interopRequireDefault(_classnames);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var Splitter = function (_Component) {
    _inherits(Splitter, _Component);

    function Splitter(props, context) {
        _classCallCheck(this, Splitter);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(Splitter).call(this, props, context));

        _this.state = { applied: false, startX: false, startY: false };

        _this.onMouseMove = _this.onMouseMove.bind(_this);
        _this.onMouseDown = _this.onMouseDown.bind(_this);
        _this.onMouseUp = _this.onMouseUp.bind(_this);
        _this.onDragEnd = _this.onDragEnd.bind(_this);
        return _this;
    }

    _createClass(Splitter, [{
        key: 'onMouseDown',
        value: function onMouseDown(e) {
            this.setState({ startX: e.pageX, startY: e.pageY });

            window.addEventListener('mousemove', this.onMouseMove);
            window.addEventListener('mouseup', this.onMouseUp);
            // Occasionally, only a dragEnd event is triggered, but no mouseUp.
            window.addEventListener('dragend', this.onDragEnd);
        }
    }, {
        key: 'onDragEnd',
        value: function onDragEnd() {
            _reactDom2.default.findDOMNode(this).style.transform = '';

            window.removeEventListener('dragend', this.onDragEnd);
            window.removeEventListener('mouseup', this.onMouseUp);
            window.removeEventListener('mousemove', this.onMouseMove);
        }
    }, {
        key: 'onMouseUp',
        value: function onMouseUp(e) {
            this.onDragEnd();

            var node = _reactDom2.default.findDOMNode(this);
            var prev = node.previousElementSibling;

            var flexBasis = prev.offsetHeight + e.pageY - this.state.startY;

            if (this.props.axis === 'x') {
                flexBasis = prev.offsetWidth + e.pageX - this.state.startX;
            }

            prev.style.flex = '0 0 ' + Math.max(0, flexBasis) + 'px';
            node.nextElementSibling.style.flex = '1 1 auto';

            this.setState({ applied: true });
            this.onResize();
        }
    }, {
        key: 'onMouseMove',
        value: function onMouseMove(e) {
            var dX = 0;
            var dY = 0;
            if (this.props.axis === 'x') {
                dX = e.pageX - this.state.startX;
            } else {
                dY = e.pageY - this.state.startY;
            }
            _reactDom2.default.findDOMNode(this).style.transform = 'translate(' + dX + 'px, ' + dY + 'px)';
        }
    }, {
        key: 'onResize',
        value: function onResize() {
            // Trigger a global resize event. This notifies components that employ virtual scrolling
            // that their viewport may have changed.
            window.setTimeout(function () {
                return window.dispatchEvent(new CustomEvent('resize'));
            }, 1);
        }
    }, {
        key: 'reset',
        value: function reset(willUnmount) {
            if (!this.state.applied) {
                return;
            }

            var node = _reactDom2.default.findDOMNode(this);

            node.previousElementSibling.style.flex = '';
            node.nextElementSibling.style.flex = '';

            if (!willUnmount) {
                this.setState({ applied: false });
            }
            this.onResize();
        }
    }, {
        key: 'componentWillUnmount',
        value: function componentWillUnmount() {
            this.reset(true);
        }
    }, {
        key: 'render',
        value: function render() {
            return _react2.default.createElement(
                'div',
                { className: (0, _classnames2.default)('splitter', this.props.axis === 'x' ? 'splitter-x' : 'splitter-y') },
                _react2.default.createElement('div', { onMouseDown: this.onMouseDown, draggable: 'true' })
            );
        }
    }]);

    return Splitter;
}(_react.Component);

Splitter.defaultProps = { axis: 'x' };
exports.default = Splitter;

},{"classnames":"classnames","react":"react","react-dom":"react-dom"}],45:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = ToggleButton;

var _react = require("react");

var _react2 = _interopRequireDefault(_react);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

ToggleButton.propTypes = {
    checked: _react.PropTypes.bool.isRequired,
    onToggle: _react.PropTypes.func.isRequired,
    text: _react.PropTypes.string.isRequired
};

function ToggleButton(_ref) {
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
}

},{"react":"react"}],46:[function(require,module,exports){
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

},{"react":"react","react-dom":"react-dom"}],47:[function(require,module,exports){
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

},{}],48:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.TOGGLE_FILTER = exports.TOGGLE_VISIBILITY = exports.RECEIVE = exports.ADD = undefined;

var _typeof = typeof Symbol === "function" && typeof Symbol.iterator === "symbol" ? function (obj) { return typeof obj; } : function (obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol ? "symbol" : typeof obj; };

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reduce;
exports.toggleFilter = toggleFilter;
exports.toggleVisibility = toggleVisibility;
exports.add = add;

var _store = require("./utils/store");

var storeActions = _interopRequireWildcard(_store);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

var ADD = exports.ADD = 'EVENTS_ADD';
var RECEIVE = exports.RECEIVE = 'EVENTS_RECEIVE';
var TOGGLE_VISIBILITY = exports.TOGGLE_VISIBILITY = 'EVENTS_TOGGLE_VISIBILITY';
var TOGGLE_FILTER = exports.TOGGLE_FILTER = 'EVENTS_TOGGLE_FILTER';

var defaultState = _extends({
    visible: false,
    filters: { debug: false, info: true, web: true }
}, (0, storeActions.default)(undefined, {}));

function reduce() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    var _ret = function () {
        switch (action.type) {

            case TOGGLE_VISIBILITY:
                return {
                    v: _extends({}, state, {
                        visible: !state.visible
                    })
                };

            case TOGGLE_FILTER:
                var filters = _extends({}, state.filters, _defineProperty({}, action.filter, !state.filters[action.filter]));
                return {
                    v: _extends({}, state, {
                        filters: filters
                    }, (0, storeActions.default)(state, storeActions.setFilter(function (log) {
                        return filters[log.level];
                    })))
                };

            case ADD:
            case RECEIVE:
                return {
                    v: _extends({}, state, (0, storeActions.default)(state, storeActions[action.cmd](action.data, function (log) {
                        return state.filters[log.level];
                    })))
                };

            default:
                return {
                    v: state
                };
        }
    }();

    if ((typeof _ret === "undefined" ? "undefined" : _typeof(_ret)) === "object") return _ret.v;
}

function toggleFilter(filter) {
    return { type: TOGGLE_FILTER, filter: filter };
}

function toggleVisibility() {
    return { type: TOGGLE_VISIBILITY };
}

function add(message) {
    var level = arguments.length <= 1 || arguments[1] === undefined ? 'web' : arguments[1];

    var data = {
        id: Math.random().toString(),
        message: message,
        level: level
    };
    return {
        type: ADD,
        cmd: "add",
        data: data
    };
}

},{"./utils/store":56}],49:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.REQUEST_ACTION = exports.SET_HIGHLIGHT = exports.SET_SORT = exports.SET_FILTER = exports.SELECT = exports.RECEIVE = exports.REMOVE = exports.UPDATE = exports.ADD = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reduce;
exports.makeFilter = makeFilter;
exports.makeSort = makeSort;
exports.setFilter = setFilter;
exports.setHighlight = setHighlight;
exports.setSort = setSort;
exports.selectRelative = selectRelative;
exports.resume = resume;
exports.resumeAll = resumeAll;
exports.kill = kill;
exports.killAll = killAll;
exports.remove = remove;
exports.duplicate = duplicate;
exports.replay = replay;
exports.revert = revert;
exports.update = update;
exports.uploadContent = uploadContent;
exports.clear = clear;
exports.download = download;
exports.upload = upload;
exports.select = select;

var _utils = require("../utils");

var _store = require("./utils/store");

var storeActions = _interopRequireWildcard(_store);

var _filt = require("../filt/filt");

var _filt2 = _interopRequireDefault(_filt);

var _utils2 = require("../flow/utils");

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

var ADD = exports.ADD = 'FLOWS_ADD';
var UPDATE = exports.UPDATE = 'FLOWS_UPDATE';
var REMOVE = exports.REMOVE = 'FLOWS_REMOVE';
var RECEIVE = exports.RECEIVE = 'FLOWS_RECEIVE';
var SELECT = exports.SELECT = 'FLOWS_SELECT';
var SET_FILTER = exports.SET_FILTER = 'FLOWS_SET_FILTER';
var SET_SORT = exports.SET_SORT = 'FLOWS_SET_SORT';
var SET_HIGHLIGHT = exports.SET_HIGHLIGHT = 'FLOWS_SET_HIGHLIGHT';
var REQUEST_ACTION = exports.REQUEST_ACTION = 'FLOWS_REQUEST_ACTION';

var defaultState = _extends({
    highlight: null,
    filter: null,
    sort: { column: null, desc: false },
    selected: []
}, (0, storeActions.default)(undefined, {}));

function reduce() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {

        case ADD:
        case UPDATE:
        case REMOVE:
        case RECEIVE:
            // FIXME: Update state.selected on REMOVE:
            // The selected flow may have been removed, we need to select the next one in the view.
            var storeAction = storeActions[action.cmd](action.data, makeFilter(state.filter), makeSort(state.sort));

            var selected = state.selected;
            if (action.type === REMOVE && state.selected.includes(action.data)) {
                if (state.selected.length > 1) {
                    selected = selected.filter(function (x) {
                        return x !== action.data;
                    });
                } else {
                    selected = [];
                    if (action.data in state.viewIndex && state.view.length > 1) {
                        var currentIndex = state.viewIndex[action.data],
                            nextSelection = void 0;
                        if (currentIndex === state.view.length - 1) {
                            // last row
                            nextSelection = state.view[currentIndex - 1];
                        } else {
                            nextSelection = state.view[currentIndex + 1];
                        }
                        selected.push(nextSelection.id);
                    }
                }
            }

            return _extends({}, state, {
                selected: selected
            }, (0, storeActions.default)(state, storeAction));

        case SET_FILTER:
            return _extends({}, state, {
                filter: action.filter
            }, (0, storeActions.default)(state, storeActions.setFilter(makeFilter(action.filter), makeSort(state.sort))));

        case SET_HIGHLIGHT:
            return _extends({}, state, {
                highlight: action.highlight
            });

        case SET_SORT:
            return _extends({}, state, {
                sort: action.sort
            }, (0, storeActions.default)(state, storeActions.setSort(makeSort(action.sort))));

        case SELECT:
            return _extends({}, state, {
                selected: action.flowIds
            });

        default:
            return state;
    }
}

var sortKeyFuns = {

    TLSColumn: function TLSColumn(flow) {
        return flow.request.scheme;
    },

    PathColumn: function PathColumn(flow) {
        return _utils2.RequestUtils.pretty_url(flow.request);
    },

    MethodColumn: function MethodColumn(flow) {
        return flow.request.method;
    },

    StatusColumn: function StatusColumn(flow) {
        return flow.response && flow.response.status_code;
    },

    TimeColumn: function TimeColumn(flow) {
        return flow.response && flow.response.timestamp_end - flow.request.timestamp_start;
    },

    SizeColumn: function SizeColumn(flow) {
        var total = flow.request.contentLength;
        if (flow.response) {
            total += flow.response.contentLength || 0;
        }
        return total;
    }
};

function makeFilter(filter) {
    if (!filter) {
        return;
    }
    return _filt2.default.parse(filter);
}

function makeSort(_ref) {
    var column = _ref.column;
    var desc = _ref.desc;

    var sortKeyFun = sortKeyFuns[column];
    if (!sortKeyFun) {
        return;
    }
    return function (a, b) {
        var ka = sortKeyFun(a);
        var kb = sortKeyFun(b);
        if (ka > kb) {
            return desc ? -1 : 1;
        }
        if (ka < kb) {
            return desc ? 1 : -1;
        }
        return 0;
    };
}

function setFilter(filter) {
    return { type: SET_FILTER, filter: filter };
}

function setHighlight(highlight) {
    return { type: SET_HIGHLIGHT, highlight: highlight };
}

function setSort(column, desc) {
    return { type: SET_SORT, sort: { column: column, desc: desc } };
}

function selectRelative(shift) {
    return function (dispatch, getState) {
        var currentSelectionIndex = getState().flows.viewIndex[getState().flows.selected[0]];
        var minIndex = 0;
        var maxIndex = getState().flows.view.length - 1;
        var newIndex = void 0;
        if (currentSelectionIndex === undefined) {
            newIndex = shift < 0 ? minIndex : maxIndex;
        } else {
            newIndex = currentSelectionIndex + shift;
            newIndex = window.Math.max(newIndex, minIndex);
            newIndex = window.Math.min(newIndex, maxIndex);
        }
        var flow = getState().flows.view[newIndex];
        dispatch(select(flow ? flow.id : undefined));
    };
}

function resume(flow) {
    return function (dispatch) {
        return (0, _utils.fetchApi)("/flows/" + flow.id + "/resume", { method: 'POST' });
    };
}

function resumeAll() {
    return function (dispatch) {
        return (0, _utils.fetchApi)('/flows/resume', { method: 'POST' });
    };
}

function kill(flow) {
    return function (dispatch) {
        return (0, _utils.fetchApi)("/flows/" + flow.id + "/kill", { method: 'POST' });
    };
}

function killAll() {
    return function (dispatch) {
        return (0, _utils.fetchApi)('/flows/kill', { method: 'POST' });
    };
}

function remove(flow) {
    return function (dispatch) {
        return (0, _utils.fetchApi)("/flows/" + flow.id, { method: 'DELETE' });
    };
}

function duplicate(flow) {
    return function (dispatch) {
        return (0, _utils.fetchApi)("/flows/" + flow.id + "/duplicate", { method: 'POST' });
    };
}

function replay(flow) {
    return function (dispatch) {
        return (0, _utils.fetchApi)("/flows/" + flow.id + "/replay", { method: 'POST' });
    };
}

function revert(flow) {
    return function (dispatch) {
        return (0, _utils.fetchApi)("/flows/" + flow.id + "/revert", { method: 'POST' });
    };
}

function update(flow, data) {
    return function (dispatch) {
        return _utils.fetchApi.put("/flows/" + flow.id, data);
    };
}

function uploadContent(flow, file, type) {
    var body = new FormData();
    file = new window.Blob([file], { type: 'plain/text' });
    body.append('file', file);
    return function (dispatch) {
        return (0, _utils.fetchApi)("/flows/" + flow.id + "/" + type + "/content", { method: 'post', body: body });
    };
}

function clear() {
    return function (dispatch) {
        return (0, _utils.fetchApi)('/clear', { method: 'POST' });
    };
}

function download() {
    window.location = '/flows/dump';
    return { type: REQUEST_ACTION };
}

function upload(file) {
    var body = new FormData();
    body.append('file', file);
    return function (dispatch) {
        return (0, _utils.fetchApi)('/flows/dump', { method: 'post', body: body });
    };
}

function select(id) {
    return {
        type: SELECT,
        flowIds: id ? [id] : []
    };
}

},{"../filt/filt":57,"../flow/utils":58,"../utils":60,"./utils/store":56}],50:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _redux = require('redux');

var _eventLog = require('./eventLog');

var _eventLog2 = _interopRequireDefault(_eventLog);

var _flows = require('./flows');

var _flows2 = _interopRequireDefault(_flows);

var _settings = require('./settings');

var _settings2 = _interopRequireDefault(_settings);

var _index = require('./ui/index');

var _index2 = _interopRequireDefault(_index);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

exports.default = (0, _redux.combineReducers)({
    eventLog: _eventLog2.default,
    flows: _flows2.default,
    settings: _settings2.default,
    ui: _index2.default
});

},{"./eventLog":48,"./flows":49,"./settings":51,"./ui/index":54,"redux":"redux"}],51:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.UNKNOWN_CMD = exports.REQUEST_UPDATE = exports.UPDATE = exports.RECEIVE = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reducer;
exports.update = update;

var _utils = require('../utils');

var RECEIVE = exports.RECEIVE = 'SETTINGS_RECEIVE';
var UPDATE = exports.UPDATE = 'SETTINGS_UPDATE';
var REQUEST_UPDATE = exports.REQUEST_UPDATE = 'REQUEST_UPDATE';
var UNKNOWN_CMD = exports.UNKNOWN_CMD = 'SETTINGS_UNKNOWN_CMD';

var defaultState = {};

function reducer() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {

        case RECEIVE:
            return action.data;

        case UPDATE:
            return _extends({}, state, action.data);

        default:
            return state;
    }
}

function update(settings) {
    _utils.fetchApi.put('/settings', settings);
    return { type: REQUEST_UPDATE };
}

},{"../utils":60}],52:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.SET_CONTENT = exports.SET_CONTENT_VIEW_DESCRIPTION = exports.SET_SHOW_FULL_CONTENT = exports.UPLOAD_CONTENT = exports.UPDATE_EDIT = exports.START_EDIT = exports.SET_TAB = exports.DISPLAY_LARGE = exports.SET_CONTENT_VIEW = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reducer;
exports.setContentView = setContentView;
exports.displayLarge = displayLarge;
exports.selectTab = selectTab;
exports.startEdit = startEdit;
exports.updateEdit = updateEdit;
exports.setContentViewDescription = setContentViewDescription;
exports.setShowFullContent = setShowFullContent;
exports.setContent = setContent;
exports.stopEdit = stopEdit;

var _flows = require('../flows');

var flowsActions = _interopRequireWildcard(_flows);

var _utils = require('../../utils');

var _lodash = require('lodash');

var _lodash2 = _interopRequireDefault(_lodash);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

var SET_CONTENT_VIEW = exports.SET_CONTENT_VIEW = 'UI_FLOWVIEW_SET_CONTENT_VIEW',
    DISPLAY_LARGE = exports.DISPLAY_LARGE = 'UI_FLOWVIEW_DISPLAY_LARGE',
    SET_TAB = exports.SET_TAB = "UI_FLOWVIEW_SET_TAB",
    START_EDIT = exports.START_EDIT = 'UI_FLOWVIEW_START_EDIT',
    UPDATE_EDIT = exports.UPDATE_EDIT = 'UI_FLOWVIEW_UPDATE_EDIT',
    UPLOAD_CONTENT = exports.UPLOAD_CONTENT = 'UI_FLOWVIEW_UPLOAD_CONTENT',
    SET_SHOW_FULL_CONTENT = exports.SET_SHOW_FULL_CONTENT = 'UI_SET_SHOW_FULL_CONTENT',
    SET_CONTENT_VIEW_DESCRIPTION = exports.SET_CONTENT_VIEW_DESCRIPTION = "UI_SET_CONTENT_VIEW_DESCRIPTION",
    SET_CONTENT = exports.SET_CONTENT = "UI_SET_CONTENT";

var defaultState = {
    displayLarge: false,
    viewDescription: '',
    showFullContent: false,
    modifiedFlow: false,
    contentView: 'Auto',
    tab: 'request',
    content: [],
    maxContentLines: 80
};

function reducer() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    var wasInEditMode = !!state.modifiedFlow;

    var content = action.content || state.content;
    var isFullContentShown = content && content.length <= state.maxContentLines;

    switch (action.type) {

        case START_EDIT:
            return _extends({}, state, {
                modifiedFlow: action.flow,
                contentView: 'Edit',
                showFullContent: true
            });

        case UPDATE_EDIT:
            return _extends({}, state, {
                modifiedFlow: _lodash2.default.merge({}, state.modifiedFlow, action.update)
            });

        case flowsActions.SELECT:
            return _extends({}, state, {
                modifiedFlow: false,
                displayLarge: false,
                contentView: wasInEditMode ? 'Auto' : state.contentView,
                showFullContent: isFullContentShown
            });

        case flowsActions.UPDATE:
            // There is no explicit "stop edit" event.
            // We stop editing when we receive an update for
            // the currently edited flow from the server
            if (action.data.id === state.modifiedFlow.id) {
                return _extends({}, state, {
                    modifiedFlow: false,
                    displayLarge: false,
                    contentView: wasInEditMode ? 'Auto' : state.contentView,
                    showFullContent: false
                });
            } else {
                return state;
            }

        case SET_CONTENT_VIEW_DESCRIPTION:
            return _extends({}, state, {
                viewDescription: action.description
            });

        case SET_SHOW_FULL_CONTENT:
            return _extends({}, state, {
                showFullContent: true
            });

        case SET_TAB:
            return _extends({}, state, {
                tab: action.tab ? action.tab : 'request',
                displayLarge: false,
                showFullContent: state.contentView == 'Edit'
            });

        case SET_CONTENT_VIEW:
            return _extends({}, state, {
                contentView: action.contentView,
                showFullContent: action.contentView == 'Edit'
            });

        case SET_CONTENT:
            return _extends({}, state, {
                content: action.content,
                showFullContent: isFullContentShown
            });

        case DISPLAY_LARGE:
            return _extends({}, state, {
                displayLarge: true
            });
        default:
            return state;
    }
}

function setContentView(contentView) {
    return { type: SET_CONTENT_VIEW, contentView: contentView };
}

function displayLarge() {
    return { type: DISPLAY_LARGE };
}

function selectTab(tab) {
    return { type: SET_TAB, tab: tab };
}

function startEdit(flow) {
    return { type: START_EDIT, flow: flow };
}

function updateEdit(update) {
    return { type: UPDATE_EDIT, update: update };
}

function setContentViewDescription(description) {
    return { type: SET_CONTENT_VIEW_DESCRIPTION, description: description };
}

function setShowFullContent() {
    return { type: SET_SHOW_FULL_CONTENT };
}

function setContent(content) {
    return { type: SET_CONTENT, content: content };
}

function stopEdit(flow, modifiedFlow) {
    return flowsActions.update(flow, (0, _utils.getDiff)(flow, modifiedFlow));
}

},{"../../utils":60,"../flows":49,"lodash":"lodash"}],53:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.SET_ACTIVE_MENU = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reducer;
exports.setActiveMenu = setActiveMenu;

var _flows = require('../flows');

var flowsActions = _interopRequireWildcard(_flows);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

var SET_ACTIVE_MENU = exports.SET_ACTIVE_MENU = 'UI_SET_ACTIVE_MENU';

var defaultState = {
    activeMenu: 'Start',
    isFlowSelected: false
};

function reducer() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {

        case SET_ACTIVE_MENU:
            return _extends({}, state, {
                activeMenu: action.activeMenu
            });

        case flowsActions.SELECT:
            // First Select
            if (action.flowIds.length > 0 && !state.isFlowSelected) {
                return _extends({}, state, {
                    activeMenu: 'Flow',
                    isFlowSelected: true
                });
            }

            // Deselect
            if (action.flowIds.length === 0 && state.isFlowSelected) {
                var activeMenu = state.activeMenu;
                if (activeMenu == 'Flow') {
                    activeMenu = 'Start';
                }
                return _extends({}, state, {
                    activeMenu: activeMenu,
                    isFlowSelected: false
                });
            }
            return state;
        default:
            return state;
    }
}

function setActiveMenu(activeMenu) {
    return { type: SET_ACTIVE_MENU, activeMenu: activeMenu };
}

},{"../flows":49}],54:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _redux = require('redux');

var _flow = require('./flow');

var _flow2 = _interopRequireDefault(_flow);

var _header = require('./header');

var _header2 = _interopRequireDefault(_header);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

// TODO: Just move ducks/ui/* into ducks/?
exports.default = (0, _redux.combineReducers)({
    flow: _flow2.default,
    header: _header2.default
});

},{"./flow":52,"./header":53,"redux":"redux"}],55:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.onKeyDown = onKeyDown;

var _utils = require("../../utils");

var _flow = require("./flow");

var _flows = require("../flows");

var flowsActions = _interopRequireWildcard(_flows);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function onKeyDown(e) {
    console.debug("onKeyDown", e);
    if (e.ctrlKey) {
        return function () {};
    }
    var key = e.keyCode;
    var shiftKey = e.shiftKey;
    e.preventDefault();
    return function (dispatch, getState) {

        var flow = getState().flows.byId[getState().flows.selected[0]];

        switch (key) {
            case _utils.Key.K:
            case _utils.Key.UP:
                dispatch(flowsActions.selectRelative(-1));
                break;

            case _utils.Key.J:
            case _utils.Key.DOWN:
                dispatch(flowsActions.selectRelative(+1));
                break;

            case _utils.Key.SPACE:
            case _utils.Key.PAGE_DOWN:
                dispatch(flowsActions.selectRelative(+10));
                break;

            case _utils.Key.PAGE_UP:
                dispatch(flowsActions.selectRelative(-10));
                break;

            case _utils.Key.END:
                dispatch(flowsActions.selectRelative(+1e10));
                break;

            case _utils.Key.HOME:
                dispatch(flowsActions.selectRelative(-1e10));
                break;

            case _utils.Key.ESC:
                dispatch(flowsActions.select(null));
                break;

            case _utils.Key.LEFT:
                {
                    if (!flow) break;
                    var tabs = ['request', 'response', 'error'].filter(function (k) {
                        return flow[k];
                    }).concat(['details']),
                        currentTab = getState().ui.flow.tab,
                        nextTab = tabs[(tabs.indexOf(currentTab) - 1 + tabs.length) % tabs.length];
                    dispatch((0, _flow.selectTab)(nextTab));
                    break;
                }

            case _utils.Key.TAB:
            case _utils.Key.RIGHT:
                {
                    if (!flow) break;
                    var _tabs = ['request', 'response', 'error'].filter(function (k) {
                        return flow[k];
                    }).concat(['details']),
                        _currentTab = getState().ui.flow.tab,
                        _nextTab = _tabs[(_tabs.indexOf(_currentTab) + 1) % _tabs.length];
                    dispatch((0, _flow.selectTab)(_nextTab));
                    break;
                }

            case _utils.Key.D:
                {
                    if (!flow) {
                        return;
                    }
                    if (shiftKey) {
                        dispatch(flowsActions.duplicate(flow));
                    } else {
                        dispatch(flowsActions.remove(flow));
                    }
                    break;
                }

            case _utils.Key.A:
                {
                    if (shiftKey) {
                        dispatch(flowsActions.resumeAll());
                    } else if (flow && flow.intercepted) {
                        dispatch(flowsActions.resume(flow));
                    }
                    break;
                }

            case _utils.Key.R:
                {
                    if (!shiftKey && flow) {
                        dispatch(flowsActions.replay(flow));
                    }
                    break;
                }

            case _utils.Key.V:
                {
                    if (!shiftKey && flow && flow.modified) {
                        dispatch(flowsActions.revert(flow));
                    }
                    break;
                }

            case _utils.Key.X:
                {
                    if (shiftKey) {
                        dispatch(flowsActions.killAll());
                    } else if (flow && flow.intercepted) {
                        dispatch(flowsActions.kill(flow));
                    }
                    break;
                }

            case _utils.Key.Z:
                {
                    if (!shiftKey) {
                        dispatch(flowsActions.clear());
                    }
                    break;
                }

            default:
                return;
        }
    };
}

},{"../../utils":60,"../flows":49,"./flow":52}],56:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reduce;
exports.setFilter = setFilter;
exports.setSort = setSort;
exports.add = add;
exports.update = update;
exports.remove = remove;
exports.receive = receive;

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _toConsumableArray(arr) { if (Array.isArray(arr)) { for (var i = 0, arr2 = Array(arr.length); i < arr.length; i++) { arr2[i] = arr[i]; } return arr2; } else { return Array.from(arr); } }

var SET_FILTER = exports.SET_FILTER = 'LIST_SET_FILTER';
var SET_SORT = exports.SET_SORT = 'LIST_SET_SORT';
var ADD = exports.ADD = 'LIST_ADD';
var UPDATE = exports.UPDATE = 'LIST_UPDATE';
var REMOVE = exports.REMOVE = 'LIST_REMOVE';
var RECEIVE = exports.RECEIVE = 'LIST_RECEIVE';

var defaultState = {
    byId: {},
    list: [],
    listIndex: {},
    view: [],
    viewIndex: {}
};

/**
 * The store reducer can be used as a mixin to another reducer that always returns a
 * new { byId, list, listIndex, view, viewIndex } object. The reducer using the store
 * usually has to map its action to the matching store action and then call the mixin with that.
 *
 * Example Usage:
 *
 *      import reduceStore, * as storeActions from "./utils/store"
 *
 *      case EVENTLOG_ADD:
 *          return {
 *              ...state,
 *              ...reduceStore(state, storeActions.add(action.data))
 *          }
 *
 */
function reduce() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];
    var byId = state.byId;
    var list = state.list;
    var listIndex = state.listIndex;
    var view = state.view;
    var viewIndex = state.viewIndex;


    switch (action.type) {
        case SET_FILTER:
            view = list.filter(action.filter).sort(action.sort);
            viewIndex = {};
            view.forEach(function (item, index) {
                viewIndex[item.id] = index;
            });
            break;

        case SET_SORT:
            view = [].concat(_toConsumableArray(view)).sort(action.sort);
            viewIndex = {};
            view.forEach(function (item, index) {
                viewIndex[item.id] = index;
            });
            break;

        case ADD:
            if (action.item.id in byId) {
                // we already had that.
                break;
            }
            byId = _extends({}, byId, _defineProperty({}, action.item.id, action.item));
            listIndex = _extends({}, listIndex, _defineProperty({}, action.item.id, list.length));
            list = [].concat(_toConsumableArray(list), [action.item]);
            if (action.filter(action.item)) {
                var _sortedInsert = sortedInsert(state, action.item, action.sort);

                view = _sortedInsert.view;
                viewIndex = _sortedInsert.viewIndex;
            }
            break;

        case UPDATE:
            byId = _extends({}, byId, _defineProperty({}, action.item.id, action.item));
            list = [].concat(_toConsumableArray(list));
            list[listIndex[action.item.id]] = action.item;

            var hasOldItem = action.item.id in viewIndex;
            var hasNewItem = action.filter(action.item);
            if (hasNewItem && !hasOldItem) {
                var _sortedInsert2 = sortedInsert(state, action.item, action.sort);

                view = _sortedInsert2.view;
                viewIndex = _sortedInsert2.viewIndex;
            } else if (!hasNewItem && hasOldItem) {
                var _removeData = removeData(view, viewIndex, action.item.id);

                view = _removeData.data;
                viewIndex = _removeData.dataIndex;
            } else if (hasNewItem && hasOldItem) {
                var _sortedUpdate = sortedUpdate(state, action.item, action.sort);

                view = _sortedUpdate.view;
                viewIndex = _sortedUpdate.viewIndex;
            }
            break;

        case REMOVE:
            if (!(action.id in byId)) {
                break;
            }
            byId = _extends({}, byId);
            delete byId[action.id];

            var _removeData2 = removeData(list, listIndex, action.id);

            list = _removeData2.data;
            listIndex = _removeData2.dataIndex;


            if (action.id in viewIndex) {
                var _removeData3 = removeData(view, viewIndex, action.id);

                view = _removeData3.data;
                viewIndex = _removeData3.dataIndex;
            }
            break;

        case RECEIVE:
            list = action.list;
            listIndex = {};
            byId = {};
            list.forEach(function (item, i) {
                byId[item.id] = item;
                listIndex[item.id] = i;
            });
            view = list.filter(action.filter).sort(action.sort);
            viewIndex = {};
            view.forEach(function (item, index) {
                viewIndex[item.id] = index;
            });
            break;
    }
    return { byId: byId, list: list, listIndex: listIndex, view: view, viewIndex: viewIndex };
}

function setFilter() {
    var filter = arguments.length <= 0 || arguments[0] === undefined ? defaultFilter : arguments[0];
    var sort = arguments.length <= 1 || arguments[1] === undefined ? defaultSort : arguments[1];

    return { type: SET_FILTER, filter: filter, sort: sort };
}

function setSort() {
    var sort = arguments.length <= 0 || arguments[0] === undefined ? defaultSort : arguments[0];

    return { type: SET_SORT, sort: sort };
}

function add(item) {
    var filter = arguments.length <= 1 || arguments[1] === undefined ? defaultFilter : arguments[1];
    var sort = arguments.length <= 2 || arguments[2] === undefined ? defaultSort : arguments[2];

    return { type: ADD, item: item, filter: filter, sort: sort };
}

function update(item) {
    var filter = arguments.length <= 1 || arguments[1] === undefined ? defaultFilter : arguments[1];
    var sort = arguments.length <= 2 || arguments[2] === undefined ? defaultSort : arguments[2];

    return { type: UPDATE, item: item, filter: filter, sort: sort };
}

function remove(id) {
    return { type: REMOVE, id: id };
}

function receive(list) {
    var filter = arguments.length <= 1 || arguments[1] === undefined ? defaultFilter : arguments[1];
    var sort = arguments.length <= 2 || arguments[2] === undefined ? defaultSort : arguments[2];

    return { type: RECEIVE, list: list, filter: filter, sort: sort };
}

function sortedInsert(state, item, sort) {
    var index = sortedIndex(state.view, item, sort);
    var view = [].concat(_toConsumableArray(state.view));
    var viewIndex = _extends({}, state.viewIndex);

    view.splice(index, 0, item);
    for (var i = view.length - 1; i >= index; i--) {
        viewIndex[view[i].id] = i;
    }

    return { view: view, viewIndex: viewIndex };
}

function removeData(currentData, currentDataIndex, id) {
    var index = currentDataIndex[id];
    var data = [].concat(_toConsumableArray(currentData));
    var dataIndex = _extends({}, currentDataIndex);
    delete dataIndex[id];

    data.splice(index, 1);
    for (var i = data.length - 1; i >= index; i--) {
        dataIndex[data[i].id] = i;
    }

    return { data: data, dataIndex: dataIndex };
}

function sortedUpdate(state, item, sort) {
    var view = [].concat(_toConsumableArray(state.view));
    var viewIndex = _extends({}, state.viewIndex);
    var index = viewIndex[item.id];
    view[index] = item;
    while (index + 1 < view.length && sort(view[index], view[index + 1]) > 0) {
        view[index] = view[index + 1];
        view[index + 1] = item;
        viewIndex[item.id] = index + 1;
        viewIndex[view[index].id] = index;
        ++index;
    }
    while (index > 0 && sort(view[index], view[index - 1]) < 0) {
        view[index] = view[index - 1];
        view[index - 1] = item;
        viewIndex[item.id] = index - 1;
        viewIndex[view[index].id] = index;
        --index;
    }
    return { view: view, viewIndex: viewIndex };
}

function sortedIndex(list, item, sort) {
    var low = 0;
    var high = list.length;

    while (low < high) {
        var middle = low + high >>> 1;
        if (sort(item, list[middle]) >= 0) {
            low = middle + 1;
        } else {
            high = middle;
        }
    }

    return low;
}

function defaultFilter() {
    return true;
}

function defaultSort(a, b) {
    return 0;
}

},{}],57:[function(require,module,exports){
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
        peg$c23 = "true",
        peg$c24 = { type: "literal", value: "true", description: "\"true\"" },
        peg$c25 = function peg$c25() {
      return trueFilter;
    },
        peg$c26 = "false",
        peg$c27 = { type: "literal", value: "false", description: "\"false\"" },
        peg$c28 = function peg$c28() {
      return falseFilter;
    },
        peg$c29 = "~a",
        peg$c30 = { type: "literal", value: "~a", description: "\"~a\"" },
        peg$c31 = function peg$c31() {
      return assetFilter;
    },
        peg$c32 = "~b",
        peg$c33 = { type: "literal", value: "~b", description: "\"~b\"" },
        peg$c34 = function peg$c34(s) {
      return body(s);
    },
        peg$c35 = "~bq",
        peg$c36 = { type: "literal", value: "~bq", description: "\"~bq\"" },
        peg$c37 = function peg$c37(s) {
      return requestBody(s);
    },
        peg$c38 = "~bs",
        peg$c39 = { type: "literal", value: "~bs", description: "\"~bs\"" },
        peg$c40 = function peg$c40(s) {
      return responseBody(s);
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
        peg$c47 = "~dst",
        peg$c48 = { type: "literal", value: "~dst", description: "\"~dst\"" },
        peg$c49 = function peg$c49(s) {
      return destination(s);
    },
        peg$c50 = "~e",
        peg$c51 = { type: "literal", value: "~e", description: "\"~e\"" },
        peg$c52 = function peg$c52() {
      return errorFilter;
    },
        peg$c53 = "~h",
        peg$c54 = { type: "literal", value: "~h", description: "\"~h\"" },
        peg$c55 = function peg$c55(s) {
      return header(s);
    },
        peg$c56 = "~hq",
        peg$c57 = { type: "literal", value: "~hq", description: "\"~hq\"" },
        peg$c58 = function peg$c58(s) {
      return requestHeader(s);
    },
        peg$c59 = "~hs",
        peg$c60 = { type: "literal", value: "~hs", description: "\"~hs\"" },
        peg$c61 = function peg$c61(s) {
      return responseHeader(s);
    },
        peg$c62 = "~http",
        peg$c63 = { type: "literal", value: "~http", description: "\"~http\"" },
        peg$c64 = function peg$c64() {
      return httpFilter;
    },
        peg$c65 = "~m",
        peg$c66 = { type: "literal", value: "~m", description: "\"~m\"" },
        peg$c67 = function peg$c67(s) {
      return method(s);
    },
        peg$c68 = "~marked",
        peg$c69 = { type: "literal", value: "~marked", description: "\"~marked\"" },
        peg$c70 = function peg$c70() {
      return markedFilter;
    },
        peg$c71 = "~q",
        peg$c72 = { type: "literal", value: "~q", description: "\"~q\"" },
        peg$c73 = function peg$c73() {
      return noResponseFilter;
    },
        peg$c74 = "~src",
        peg$c75 = { type: "literal", value: "~src", description: "\"~src\"" },
        peg$c76 = function peg$c76(s) {
      return source(s);
    },
        peg$c77 = "~s",
        peg$c78 = { type: "literal", value: "~s", description: "\"~s\"" },
        peg$c79 = function peg$c79() {
      return responseFilter;
    },
        peg$c80 = "~t",
        peg$c81 = { type: "literal", value: "~t", description: "\"~t\"" },
        peg$c82 = function peg$c82(s) {
      return contentType(s);
    },
        peg$c83 = "~tcp",
        peg$c84 = { type: "literal", value: "~tcp", description: "\"~tcp\"" },
        peg$c85 = function peg$c85() {
      return tcpFilter;
    },
        peg$c86 = "~tq",
        peg$c87 = { type: "literal", value: "~tq", description: "\"~tq\"" },
        peg$c88 = function peg$c88(s) {
      return requestContentType(s);
    },
        peg$c89 = "~ts",
        peg$c90 = { type: "literal", value: "~ts", description: "\"~ts\"" },
        peg$c91 = function peg$c91(s) {
      return responseContentType(s);
    },
        peg$c92 = "~u",
        peg$c93 = { type: "literal", value: "~u", description: "\"~u\"" },
        peg$c94 = function peg$c94(s) {
      return url(s);
    },
        peg$c95 = { type: "other", description: "integer" },
        peg$c96 = /^['"]/,
        peg$c97 = { type: "class", value: "['\"]", description: "['\"]" },
        peg$c98 = /^[0-9]/,
        peg$c99 = { type: "class", value: "[0-9]", description: "[0-9]" },
        peg$c100 = function peg$c100(digits) {
      return parseInt(digits.join(""), 10);
    },
        peg$c101 = { type: "other", description: "string" },
        peg$c102 = "\"",
        peg$c103 = { type: "literal", value: "\"", description: "\"\\\"\"" },
        peg$c104 = function peg$c104(chars) {
      return chars.join("");
    },
        peg$c105 = "'",
        peg$c106 = { type: "literal", value: "'", description: "\"'\"" },
        peg$c107 = /^["\\]/,
        peg$c108 = { type: "class", value: "[\"\\\\]", description: "[\"\\\\]" },
        peg$c109 = { type: "any", description: "any character" },
        peg$c110 = function peg$c110(char) {
      return char;
    },
        peg$c111 = "\\",
        peg$c112 = { type: "literal", value: "\\", description: "\"\\\\\"" },
        peg$c113 = /^['\\]/,
        peg$c114 = { type: "class", value: "['\\\\]", description: "['\\\\]" },
        peg$c115 = /^['"\\]/,
        peg$c116 = { type: "class", value: "['\"\\\\]", description: "['\"\\\\]" },
        peg$c117 = "n",
        peg$c118 = { type: "literal", value: "n", description: "\"n\"" },
        peg$c119 = function peg$c119() {
      return "\n";
    },
        peg$c120 = "r",
        peg$c121 = { type: "literal", value: "r", description: "\"r\"" },
        peg$c122 = function peg$c122() {
      return "\r";
    },
        peg$c123 = "t",
        peg$c124 = { type: "literal", value: "t", description: "\"t\"" },
        peg$c125 = function peg$c125() {
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
      var s0, s1, s2, s3;

      s0 = peg$currPos;
      if (input.substr(peg$currPos, 4) === peg$c23) {
        s1 = peg$c23;
        peg$currPos += 4;
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
        if (input.substr(peg$currPos, 5) === peg$c26) {
          s1 = peg$c26;
          peg$currPos += 5;
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
                  s1 = peg$c34(s3);
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
              if (input.substr(peg$currPos, 3) === peg$c35) {
                s1 = peg$c35;
                peg$currPos += 3;
              } else {
                s1 = peg$FAILED;
                if (peg$silentFails === 0) {
                  peg$fail(peg$c36);
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
                    s1 = peg$c37(s3);
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
                if (input.substr(peg$currPos, 3) === peg$c38) {
                  s1 = peg$c38;
                  peg$currPos += 3;
                } else {
                  s1 = peg$FAILED;
                  if (peg$silentFails === 0) {
                    peg$fail(peg$c39);
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
                      s1 = peg$c40(s3);
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
                      if (input.substr(peg$currPos, 4) === peg$c47) {
                        s1 = peg$c47;
                        peg$currPos += 4;
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
                        if (input.substr(peg$currPos, 2) === peg$c50) {
                          s1 = peg$c50;
                          peg$currPos += 2;
                        } else {
                          s1 = peg$FAILED;
                          if (peg$silentFails === 0) {
                            peg$fail(peg$c51);
                          }
                        }
                        if (s1 !== peg$FAILED) {
                          peg$savedPos = s0;
                          s1 = peg$c52();
                        }
                        s0 = s1;
                        if (s0 === peg$FAILED) {
                          s0 = peg$currPos;
                          if (input.substr(peg$currPos, 2) === peg$c53) {
                            s1 = peg$c53;
                            peg$currPos += 2;
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
                            if (input.substr(peg$currPos, 3) === peg$c56) {
                              s1 = peg$c56;
                              peg$currPos += 3;
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
                              if (input.substr(peg$currPos, 3) === peg$c59) {
                                s1 = peg$c59;
                                peg$currPos += 3;
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
                                if (input.substr(peg$currPos, 5) === peg$c62) {
                                  s1 = peg$c62;
                                  peg$currPos += 5;
                                } else {
                                  s1 = peg$FAILED;
                                  if (peg$silentFails === 0) {
                                    peg$fail(peg$c63);
                                  }
                                }
                                if (s1 !== peg$FAILED) {
                                  peg$savedPos = s0;
                                  s1 = peg$c64();
                                }
                                s0 = s1;
                                if (s0 === peg$FAILED) {
                                  s0 = peg$currPos;
                                  if (input.substr(peg$currPos, 2) === peg$c65) {
                                    s1 = peg$c65;
                                    peg$currPos += 2;
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
                                    if (input.substr(peg$currPos, 7) === peg$c68) {
                                      s1 = peg$c68;
                                      peg$currPos += 7;
                                    } else {
                                      s1 = peg$FAILED;
                                      if (peg$silentFails === 0) {
                                        peg$fail(peg$c69);
                                      }
                                    }
                                    if (s1 !== peg$FAILED) {
                                      peg$savedPos = s0;
                                      s1 = peg$c70();
                                    }
                                    s0 = s1;
                                    if (s0 === peg$FAILED) {
                                      s0 = peg$currPos;
                                      if (input.substr(peg$currPos, 2) === peg$c71) {
                                        s1 = peg$c71;
                                        peg$currPos += 2;
                                      } else {
                                        s1 = peg$FAILED;
                                        if (peg$silentFails === 0) {
                                          peg$fail(peg$c72);
                                        }
                                      }
                                      if (s1 !== peg$FAILED) {
                                        peg$savedPos = s0;
                                        s1 = peg$c73();
                                      }
                                      s0 = s1;
                                      if (s0 === peg$FAILED) {
                                        s0 = peg$currPos;
                                        if (input.substr(peg$currPos, 4) === peg$c74) {
                                          s1 = peg$c74;
                                          peg$currPos += 4;
                                        } else {
                                          s1 = peg$FAILED;
                                          if (peg$silentFails === 0) {
                                            peg$fail(peg$c75);
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
                                              s1 = peg$c76(s3);
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
                                          if (input.substr(peg$currPos, 2) === peg$c77) {
                                            s1 = peg$c77;
                                            peg$currPos += 2;
                                          } else {
                                            s1 = peg$FAILED;
                                            if (peg$silentFails === 0) {
                                              peg$fail(peg$c78);
                                            }
                                          }
                                          if (s1 !== peg$FAILED) {
                                            peg$savedPos = s0;
                                            s1 = peg$c79();
                                          }
                                          s0 = s1;
                                          if (s0 === peg$FAILED) {
                                            s0 = peg$currPos;
                                            if (input.substr(peg$currPos, 2) === peg$c80) {
                                              s1 = peg$c80;
                                              peg$currPos += 2;
                                            } else {
                                              s1 = peg$FAILED;
                                              if (peg$silentFails === 0) {
                                                peg$fail(peg$c81);
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
                                                  s1 = peg$c82(s3);
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
                                              if (input.substr(peg$currPos, 4) === peg$c83) {
                                                s1 = peg$c83;
                                                peg$currPos += 4;
                                              } else {
                                                s1 = peg$FAILED;
                                                if (peg$silentFails === 0) {
                                                  peg$fail(peg$c84);
                                                }
                                              }
                                              if (s1 !== peg$FAILED) {
                                                peg$savedPos = s0;
                                                s1 = peg$c85();
                                              }
                                              s0 = s1;
                                              if (s0 === peg$FAILED) {
                                                s0 = peg$currPos;
                                                if (input.substr(peg$currPos, 3) === peg$c86) {
                                                  s1 = peg$c86;
                                                  peg$currPos += 3;
                                                } else {
                                                  s1 = peg$FAILED;
                                                  if (peg$silentFails === 0) {
                                                    peg$fail(peg$c87);
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
                                                      s1 = peg$c88(s3);
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
                                                  if (input.substr(peg$currPos, 3) === peg$c89) {
                                                    s1 = peg$c89;
                                                    peg$currPos += 3;
                                                  } else {
                                                    s1 = peg$FAILED;
                                                    if (peg$silentFails === 0) {
                                                      peg$fail(peg$c90);
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
                                                        s1 = peg$c91(s3);
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
                                                    if (input.substr(peg$currPos, 2) === peg$c92) {
                                                      s1 = peg$c92;
                                                      peg$currPos += 2;
                                                    } else {
                                                      s1 = peg$FAILED;
                                                      if (peg$silentFails === 0) {
                                                        peg$fail(peg$c93);
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
                                                          s1 = peg$c94(s3);
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
                                                        s1 = peg$c94(s1);
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
      if (peg$c96.test(input.charAt(peg$currPos))) {
        s1 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c97);
        }
      }
      if (s1 === peg$FAILED) {
        s1 = null;
      }
      if (s1 !== peg$FAILED) {
        s2 = [];
        if (peg$c98.test(input.charAt(peg$currPos))) {
          s3 = input.charAt(peg$currPos);
          peg$currPos++;
        } else {
          s3 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c99);
          }
        }
        if (s3 !== peg$FAILED) {
          while (s3 !== peg$FAILED) {
            s2.push(s3);
            if (peg$c98.test(input.charAt(peg$currPos))) {
              s3 = input.charAt(peg$currPos);
              peg$currPos++;
            } else {
              s3 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c99);
              }
            }
          }
        } else {
          s2 = peg$FAILED;
        }
        if (s2 !== peg$FAILED) {
          if (peg$c96.test(input.charAt(peg$currPos))) {
            s3 = input.charAt(peg$currPos);
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c97);
            }
          }
          if (s3 === peg$FAILED) {
            s3 = null;
          }
          if (s3 !== peg$FAILED) {
            peg$savedPos = s0;
            s1 = peg$c100(s2);
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
          peg$fail(peg$c95);
        }
      }

      return s0;
    }

    function peg$parseStringLiteral() {
      var s0, s1, s2, s3;

      peg$silentFails++;
      s0 = peg$currPos;
      if (input.charCodeAt(peg$currPos) === 34) {
        s1 = peg$c102;
        peg$currPos++;
      } else {
        s1 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c103);
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
            s3 = peg$c102;
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c103);
            }
          }
          if (s3 !== peg$FAILED) {
            peg$savedPos = s0;
            s1 = peg$c104(s2);
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
          s1 = peg$c105;
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c106);
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
              s3 = peg$c105;
              peg$currPos++;
            } else {
              s3 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c106);
              }
            }
            if (s3 !== peg$FAILED) {
              peg$savedPos = s0;
              s1 = peg$c104(s2);
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
              s1 = peg$c104(s2);
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
          peg$fail(peg$c101);
        }
      }

      return s0;
    }

    function peg$parseDoubleStringChar() {
      var s0, s1, s2;

      s0 = peg$currPos;
      s1 = peg$currPos;
      peg$silentFails++;
      if (peg$c107.test(input.charAt(peg$currPos))) {
        s2 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s2 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c108);
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
            peg$fail(peg$c109);
          }
        }
        if (s2 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c110(s2);
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
          s1 = peg$c111;
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c112);
          }
        }
        if (s1 !== peg$FAILED) {
          s2 = peg$parseEscapeSequence();
          if (s2 !== peg$FAILED) {
            peg$savedPos = s0;
            s1 = peg$c110(s2);
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
      if (peg$c113.test(input.charAt(peg$currPos))) {
        s2 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s2 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c114);
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
            peg$fail(peg$c109);
          }
        }
        if (s2 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c110(s2);
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
          s1 = peg$c111;
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c112);
          }
        }
        if (s1 !== peg$FAILED) {
          s2 = peg$parseEscapeSequence();
          if (s2 !== peg$FAILED) {
            peg$savedPos = s0;
            s1 = peg$c110(s2);
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
            peg$fail(peg$c109);
          }
        }
        if (s2 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c110(s2);
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

      if (peg$c115.test(input.charAt(peg$currPos))) {
        s0 = input.charAt(peg$currPos);
        peg$currPos++;
      } else {
        s0 = peg$FAILED;
        if (peg$silentFails === 0) {
          peg$fail(peg$c116);
        }
      }
      if (s0 === peg$FAILED) {
        s0 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 110) {
          s1 = peg$c117;
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c118);
          }
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c119();
        }
        s0 = s1;
        if (s0 === peg$FAILED) {
          s0 = peg$currPos;
          if (input.charCodeAt(peg$currPos) === 114) {
            s1 = peg$c120;
            peg$currPos++;
          } else {
            s1 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c121);
            }
          }
          if (s1 !== peg$FAILED) {
            peg$savedPos = s0;
            s1 = peg$c122();
          }
          s0 = s1;
          if (s0 === peg$FAILED) {
            s0 = peg$currPos;
            if (input.charCodeAt(peg$currPos) === 116) {
              s1 = peg$c123;
              peg$currPos++;
            } else {
              s1 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c124);
              }
            }
            if (s1 !== peg$FAILED) {
              peg$savedPos = s0;
              s1 = peg$c125();
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
    function body(regex) {
      regex = new RegExp(regex, "i");
      function bodyFilter(flow) {
        return True;
      }
      bodyFilter.desc = "body filters are not implemented yet, see https://github.com/mitmproxy/mitmweb/issues/10";
      return bodyFilter;
    }
    function requestBody(regex) {
      regex = new RegExp(regex, "i");
      function requestBodyFilter(flow) {
        return True;
      }
      requestBodyFilter.desc = "body filters are not implemented yet, see https://github.com/mitmproxy/mitmweb/issues/10";
      return requestBodyFilter;
    }
    function responseBody(regex) {
      regex = new RegExp(regex, "i");
      function responseBodyFilter(flow) {
        return True;
      }
      responseBodyFilter.desc = "body filters are not implemented yet, see https://github.com/mitmproxy/mitmweb/issues/10";
      return responseBodyFilter;
    }
    function domain(regex) {
      regex = new RegExp(regex, "i");
      function domainFilter(flow) {
        return flow.request && regex.test(flow.request.host);
      }
      domainFilter.desc = "domain matches " + regex;
      return domainFilter;
    }
    function destination(regex) {
      regex = new RegExp(regex, "i");
      function destinationFilter(flow) {
        return !!flow.server_conn.address && regex.test(flow.server_conn.address.address[0] + ":" + flow.server_conn.address.address[1]);
      }
      destinationFilter.desc = "destination address matches " + regex;
      return destinationFilter;
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
    function httpFilter(flow) {
      return flow.type === "http";
    }
    httpFilter.desc = "is an HTTP Flow";
    function method(regex) {
      regex = new RegExp(regex, "i");
      function methodFilter(flow) {
        return flow.request && regex.test(flow.request.method);
      }
      methodFilter.desc = "method matches " + regex;
      return methodFilter;
    }
    function markedFilter(flow) {
      return flow.marked;
    }
    markedFilter.desc = "is marked";
    function noResponseFilter(flow) {
      return flow.request && !flow.response;
    }
    noResponseFilter.desc = "has no response";
    function responseFilter(flow) {
      return !!flow.response;
    }
    responseFilter.desc = "has response";
    function source(regex) {
      regex = new RegExp(regex, "i");
      function sourceFilter(flow) {
        return !!flow.client_conn.address && regex.test(flow.client_conn.address.address[0] + ":" + flow.client_conn.address.address[1]);
      }
      sourceFilter.desc = "source address matches " + regex;
      return sourceFilter;
    }
    function contentType(regex) {
      regex = new RegExp(regex, "i");
      function contentTypeFilter(flow) {
        return flow.request && regex.test(flowutils.RequestUtils.getContentType(flow.request)) || flow.response && regex.test(flowutils.ResponseUtils.getContentType(flow.response));
      }
      contentTypeFilter.desc = "content type matches " + regex;
      return contentTypeFilter;
    }
    function tcpFilter(flow) {
      return flow.type === "tcp";
    }
    tcpFilter.desc = "is a TCP Flow";
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

},{"../flow/utils.js":58}],58:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.isValidHttpVersion = exports.parseUrl = exports.ResponseUtils = exports.RequestUtils = exports.MessageUtils = undefined;

var _lodash = require("lodash");

var _lodash2 = _interopRequireDefault(_lodash);

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
    getContentURL: function getContentURL(flow, message, view) {
        if (message === flow.request) {
            message = "request";
        } else if (message === flow.response) {
            message = "response";
        }
        return "/flows/" + flow.id + "/" + message + "/content" + (view ? "/" + view : '');
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

},{"lodash":"lodash"}],59:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _slicedToArray = function () { function sliceIterator(arr, i) { var _arr = []; var _n = true; var _d = false; var _e = undefined; try { for (var _i = arr[Symbol.iterator](), _s; !(_n = (_s = _i.next()).done); _n = true) { _arr.push(_s.value); if (i && _arr.length === i) break; } } catch (err) { _d = true; _e = err; } finally { try { if (!_n && _i["return"]) _i["return"](); } finally { if (_d) throw _e; } } return _arr; } return function (arr, i) { if (Array.isArray(arr)) { return arr; } else if (Symbol.iterator in Object(arr)) { return sliceIterator(arr, i); } else { throw new TypeError("Invalid attempt to destructure non-iterable instance"); } }; }(); /**
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          * Instead of dealing with react-router's ever-changing APIs,
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          * we use a simple url state manager where we only
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          *
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          * - read the initial URL state on page load
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          * - push updates to the URL later on.
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          */


exports.default = initialize;

var _flows = require("./ducks/flows");

var _flow = require("./ducks/ui/flow");

var _eventLog = require("./ducks/eventLog");

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

var Query = {
    SEARCH: "s",
    HIGHLIGHT: "h",
    SHOW_EVENTLOG: "e"
};

function updateStoreFromUrl(store) {
    var _window$location$hash = window.location.hash.substr(1).split("?", 2);

    var _window$location$hash2 = _slicedToArray(_window$location$hash, 2);

    var path = _window$location$hash2[0];
    var query = _window$location$hash2[1];

    var path_components = path.substr(1).split("/");

    if (path_components[0] === "flows") {
        if (path_components.length == 3) {
            var _path_components$slic = path_components.slice(1);

            var _path_components$slic2 = _slicedToArray(_path_components$slic, 2);

            var flowId = _path_components$slic2[0];
            var tab = _path_components$slic2[1];

            store.dispatch((0, _flows.select)(flowId));
            store.dispatch((0, _flow.selectTab)(tab));
        }
    }

    if (query) {
        query.split("&").forEach(function (x) {
            var _x$split = x.split("=", 2);

            var _x$split2 = _slicedToArray(_x$split, 2);

            var key = _x$split2[0];
            var value = _x$split2[1];

            switch (key) {
                case Query.SEARCH:
                    store.dispatch((0, _flows.setFilter)(value));
                    break;
                case Query.HIGHLIGHT:
                    store.dispatch((0, _flows.setHighlight)(value));
                    break;
                case Query.SHOW_EVENTLOG:
                    if (!store.getState().eventLog.visible) store.dispatch((0, _eventLog.toggleVisibility)());
                    break;
                default:
                    console.error("unimplemented query arg: " + x);
            }
        });
    }
}

function updateUrlFromStore(store) {
    var _query;

    var state = store.getState();
    var query = (_query = {}, _defineProperty(_query, Query.SEARCH, state.flows.filter), _defineProperty(_query, Query.HIGHLIGHT, state.flows.highlight), _defineProperty(_query, Query.SHOW_EVENTLOG, state.eventLog.visible), _query);
    var queryStr = Object.keys(query).filter(function (k) {
        return query[k];
    }).map(function (k) {
        return k + "=" + query[k];
    }).join("&");

    var url = void 0;
    if (state.flows.selected.length > 0) {
        url = "/flows/" + state.flows.selected[0] + "/" + state.ui.flow.tab;
    } else {
        url = "/flows";
    }

    if (queryStr) {
        url += "?" + queryStr;
    }
    if (window.location.hash.substr(1) !== url) {
        history.replaceState(undefined, "", "/#" + url);
    }
}

function initialize(store) {
    updateStoreFromUrl(store);
    store.subscribe(function () {
        return updateUrlFromStore(store);
    });
}

},{"./ducks/eventLog":48,"./ducks/flows":49,"./ducks/ui/flow":52}],60:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.pure = exports.formatTimeStamp = exports.formatTimeDelta = exports.formatSize = exports.Key = undefined;

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.reverseString = reverseString;
exports.fetchApi = fetchApi;
exports.getDiff = getDiff;

var _lodash = require('lodash');

var _lodash2 = _interopRequireDefault(_lodash);

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _shallowequal = require('shallowequal');

var _shallowequal2 = _interopRequireDefault(_shallowequal);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

window._ = _lodash2.default;
window.React = _react2.default;

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
var xsrf = '_xsrf=' + getCookie("_xsrf");

function fetchApi(url) {
    var options = arguments.length <= 1 || arguments[1] === undefined ? {} : arguments[1];

    if (options.method && options.method !== "GET") {
        if (url.indexOf("?") === -1) {
            url += "?" + xsrf;
        } else {
            url += "&" + xsrf;
        }
    }

    return fetch(url, _extends({
        credentials: 'same-origin'
    }, options));
}

fetchApi.put = function (url, json, options) {
    return fetchApi(url, _extends({
        method: "PUT",
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(json)
    }, options));
};
// deep comparison of two json objects (dicts). arrays are handeled as a single value.
// return: json object including only the changed keys value pairs.
function getDiff(obj1, obj2) {
    var result = _extends({}, obj2);
    for (var key in obj1) {
        if (_lodash2.default.isEqual(obj2[key], obj1[key])) result[key] = undefined;else if (Object.prototype.toString.call(obj2[key]) === '[object Object]' && Object.prototype.toString.call(obj1[key]) === '[object Object]') result[key] = getDiff(obj1[key], obj2[key]);
    }
    return result;
}

var pure = exports.pure = function pure(renderFn) {
    var _class, _temp;

    return _temp = _class = function (_React$Component) {
        _inherits(_class, _React$Component);

        function _class() {
            _classCallCheck(this, _class);

            return _possibleConstructorReturn(this, Object.getPrototypeOf(_class).apply(this, arguments));
        }

        _createClass(_class, [{
            key: 'shouldComponentUpdate',
            value: function shouldComponentUpdate(nextProps) {
                return !(0, _shallowequal2.default)(this.props, nextProps);
            }
        }, {
            key: 'render',
            value: function render() {
                return renderFn(this.props);
            }
        }]);

        return _class;
    }(_react2.default.Component), _class.displayName = renderFn.name, _temp;
};

},{"lodash":"lodash","react":"react","shallowequal":"shallowequal"}]},{},[2])


//# sourceMappingURL=app.js.map
