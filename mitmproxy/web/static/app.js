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
function runTimeout(fun) {
    if (cachedSetTimeout === setTimeout) {
        return setTimeout(fun, 0);
    } else {
        return cachedSetTimeout.call(null, fun, 0);
    }
}
function runClearTimeout(marker) {
    if (cachedClearTimeout === clearTimeout) {
        clearTimeout(marker);
    } else {
        cachedClearTimeout.call(null, marker);
    }
}
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
    var timeout = runTimeout(cleanUpNextTick);
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
    runClearTimeout(timeout);
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
        runTimeout(drainQueue);
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
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.Query = exports.ConnectionActions = exports.StoreCmds = exports.ActionTypes = undefined;

var _dispatcher = require("./dispatcher.js");

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

var Query = exports.Query = {
    SEARCH: "s",
    HIGHLIGHT: "h",
    SHOW_EVENTLOG: "e"
};

},{"./dispatcher.js":46}],3:[function(require,module,exports){
(function (process){
'use strict';

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactDom = require('react-dom');

var _redux = require('redux');

var _reactRedux = require('react-redux');

var _reduxThunk = require('redux-thunk');

var _reduxThunk2 = _interopRequireDefault(_reduxThunk);

var _reactRouter = require('react-router');

var _ProxyApp = require('./components/ProxyApp');

var _ProxyApp2 = _interopRequireDefault(_ProxyApp);

var _MainView = require('./components/MainView');

var _MainView2 = _interopRequireDefault(_MainView);

var _index = require('./ducks/index');

var _index2 = _interopRequireDefault(_index);

var _eventLog = require('./ducks/eventLog');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var middlewares = [_reduxThunk2.default];

if (process.env.NODE_ENV !== 'production') {
    var createLogger = require('redux-logger');
    middlewares.push(createLogger());
}

// logger must be last
var store = (0, _redux.createStore)(_index2.default, _redux.applyMiddleware.apply(undefined, middlewares));

// @todo move to ProxyApp
window.addEventListener('error', function (msg) {
    store.dispatch((0, _eventLog.add)(msg));
});

// @todo remove this
document.addEventListener('DOMContentLoaded', function () {
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

}).call(this,require('_process'))

},{"./components/MainView":35,"./components/ProxyApp":37,"./ducks/eventLog":48,"./ducks/index":51,"_process":1,"react":"react","react-dom":"react-dom","react-redux":"react-redux","react-router":"react-router","redux":"redux","redux-logger":"redux-logger","redux-thunk":"redux-thunk"}],4:[function(require,module,exports){
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

},{"../ducks/ui/flow":54,"./ContentView/ContentViews":8,"./ContentView/MetaViews":10,"./ContentView/ShowFullContentButton":11,"react":"react","react-redux":"react-redux"}],5:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = CodeEditor;

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactDom = require('react-dom');

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

},{"react":"react","react-codemirror":"react-codemirror","react-dom":"react-dom"}],6:[function(require,module,exports){
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

},{"../../flow/utils.js":62,"react":"react"}],7:[function(require,module,exports){
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

function ContentViewOptions(props) {
    var flow = props.flow;
    var message = props.message;
    var uploadContent = props.uploadContent;
    var readonly = props.readonly;
    var contentViewDescription = props.contentViewDescription;

    return _react2.default.createElement(
        'div',
        { className: 'view-options' },
        _react2.default.createElement(_ViewSelector2.default, { message: message }),
        ' ',
        _react2.default.createElement(_DownloadContentButton2.default, { flow: flow, message: message }),
        ' ',
        _react2.default.createElement(_UploadContentButton2.default, { uploadContent: uploadContent }),
        ' ',
        _react2.default.createElement(
            'span',
            null,
            contentViewDescription
        )
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        contentViewDescription: state.ui.flow.viewDescription
    };
})(ContentViewOptions);

},{"./DownloadContentButton":9,"./UploadContentButton":12,"./ViewSelector":13,"react":"react","react-redux":"react-redux"}],8:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.ViewImage = exports.ViewServer = exports.Edit = undefined;

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
            this.setContentView(nextProps);
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

            var isFullContentShown = this.data.lines.length < props.maxLines;
            if (isFullContentShown) props.setShowFullContent(true);
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
                _react2.default.createElement(
                    'pre',
                    null,
                    lines.map(function (line, i) {
                        return _react2.default.createElement(
                            'div',
                            { key: 'line' + i },
                            line.map(function (tuple, j) {
                                return _react2.default.createElement(
                                    'span',
                                    { key: 'tuple' + j, className: tuple[0] },
                                    tuple[1]
                                );
                            })
                        );
                    })
                ),
                ViewImage.matches(message) && _react2.default.createElement(ViewImage, this.props)
            );
        }
    }]);

    return ViewServer;
}(_react.Component);

ViewServer.defaultProps = {
    maxLines: 80
};


exports.ViewServer = ViewServer = (0, _reactRedux.connect)(function (state) {
    return {
        showFullContent: state.ui.flow.showFullContent
    };
}, {
    setContentViewDescription: _flow.setContentViewDescription,
    setShowFullContent: _flow.setShowFullContent
})((0, _ContentLoader2.default)(ViewServer));

exports.Edit = Edit;
exports.ViewServer = ViewServer;
exports.ViewImage = ViewImage;

},{"../../ducks/ui/flow":54,"../../flow/utils":62,"./CodeEditor":5,"./ContentLoader":6,"react":"react","react-redux":"react-redux"}],9:[function(require,module,exports){
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

},{"../../flow/utils":62,"react":"react"}],10:[function(require,module,exports){
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

},{"../../utils.js":63,"./DownloadContentButton":9,"./UploadContentButton":12,"react":"react"}],11:[function(require,module,exports){
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


    return !showFullContent && _react2.default.createElement(_Button2.default, { className: 'view-all-content-btn btn-xs', onClick: function onClick() {
            return setShowFullContent(true);
        }, text: 'Show full content' });
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        showFullContent: state.ui.flow.showFullContent
    };
}, {
    setShowFullContent: _flow.setShowFullContent
})(ShowFullContentButton);

},{"../../ducks/ui/flow":54,"../common/Button":40,"react":"react","react-dom":"react-dom","react-redux":"react-redux"}],12:[function(require,module,exports){
"use strict";

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = UploadContentButton;

var _react = require("react");

UploadContentButton.propTypes = {
    uploadContent: _react.PropTypes.func.isRequired
};

function UploadContentButton(_ref) {
    var uploadContent = _ref.uploadContent;


    var fileInput = void 0;

    return React.createElement(
        "a",
        { className: "btn btn-default btn-xs",
            onClick: function onClick() {
                return fileInput.click();
            },
            title: "Upload a file to replace the content." },
        React.createElement("i", { className: "fa fa-upload" }),
        React.createElement("input", {
            ref: function ref(_ref2) {
                return fileInput = _ref2;
            },
            className: "hidden",
            type: "file",
            onChange: function onChange(e) {
                if (e.target.files.length > 0) uploadContent(e.target.files[0]);
            }
        })
    );
}

},{"react":"react"}],13:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _classnames = require('classnames');

var _classnames2 = _interopRequireDefault(_classnames);

var _reactRedux = require('react-redux');

var _ContentViews = require('./ContentViews');

var ContentViews = _interopRequireWildcard(_ContentViews);

var _flow = require('../../ducks/ui/flow');

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

function ViewItem(_ref) {
    var name = _ref.name;
    var setContentView = _ref.setContentView;
    var children = _ref.children;

    return _react2.default.createElement(
        'li',
        null,
        _react2.default.createElement(
            'a',
            { href: '#', onClick: function onClick() {
                    return setContentView(name);
                } },
            children
        )
    );
}

/*ViewSelector.propTypes = {
    contentViews: PropTypes.array.isRequired,
    activeView: PropTypes.string.isRequired,
    isEdit: PropTypes.bool.isRequired,
    isContentViewSelectorOpen: PropTypes.bool.isRequired,
    setContentViewSelectorOpen: PropTypes.func.isRequired
}*/

var ViewSelector = function (_Component) {
    _inherits(ViewSelector, _Component);

    function ViewSelector(props, context) {
        _classCallCheck(this, ViewSelector);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(ViewSelector).call(this, props, context));

        _this.close = _this.close.bind(_this);
        _this.state = { open: false };
        return _this;
    }

    _createClass(ViewSelector, [{
        key: 'close',
        value: function close() {
            this.setState({ open: false });
            document.removeEventListener('click', this.close);
        }
    }, {
        key: 'onDropdown',
        value: function onDropdown(e) {
            e.preventDefault();
            this.setState({ open: !this.state.open });
            document.addEventListener('click', this.close);
        }
    }, {
        key: 'render',
        value: function render() {
            var _this2 = this;

            var _props = this.props;
            var contentViews = _props.contentViews;
            var activeView = _props.activeView;
            var isEdit = _props.isEdit;
            var setContentView = _props.setContentView;

            var edit = ContentViews.Edit.displayName;

            return _react2.default.createElement(
                'div',
                { className: (0, _classnames2.default)('dropup pull-left', { open: this.state.open }) },
                _react2.default.createElement(
                    'a',
                    { className: 'btn btn-default btn-xs',
                        onClick: function onClick(e) {
                            return _this2.onDropdown(e);
                        },
                        href: '#' },
                    _react2.default.createElement(
                        'b',
                        null,
                        'View:'
                    ),
                    ' ',
                    activeView,
                    _react2.default.createElement('span', { className: 'caret' })
                ),
                _react2.default.createElement(
                    'ul',
                    { className: 'dropdown-menu', role: 'menu' },
                    contentViews.map(function (name) {
                        return _react2.default.createElement(
                            ViewItem,
                            { key: name, setContentView: setContentView, name: name },
                            name.toLowerCase().replace('_', ' ')
                        );
                    }),
                    isEdit && _react2.default.createElement(
                        ViewItem,
                        { key: edit, setContentView: setContentView, name: edit },
                        edit.toLowerCase()
                    )
                )
            );
        }
    }]);

    return ViewSelector;
}(_react.Component);

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        contentViews: state.settings.contentViews,
        activeView: state.ui.flow.contentView,
        isEdit: !!state.ui.flow.modifiedFlow
    };
}, {
    setContentView: _flow.setContentView
})(ViewSelector);

},{"../../ducks/ui/flow":54,"./ContentViews":8,"classnames":"classnames","react":"react","react-redux":"react-redux"}],14:[function(require,module,exports){
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
        events: state.eventLog.view.data
    };
}, {
    close: _eventLog.toggleVisibility,
    toggleFilter: _eventLog.toggleFilter
})(EventLog);

},{"../ducks/eventLog":48,"./EventLog/EventList":15,"./common/ToggleButton":42,"react":"react","react-redux":"react-redux"}],15:[function(require,module,exports){
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

},{"../helpers/AutoScroll":44,"../helpers/VirtualScroll":45,"react":"react","react-dom":"react-dom","shallowequal":"shallowequal"}],16:[function(require,module,exports){
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

},{"../filt/filt":61,"./FlowTable/FlowRow":18,"./FlowTable/FlowTableHead":19,"./helpers/AutoScroll":44,"./helpers/VirtualScroll":45,"react":"react","react-dom":"react-dom","shallowequal":"shallowequal"}],17:[function(require,module,exports){
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

    return _react2.default.createElement(
        'td',
        { className: 'col-path' },
        flow.request.is_replay && _react2.default.createElement('i', { className: 'fa fa-fw fa-repeat pull-right' }),
        flow.intercepted && _react2.default.createElement('i', { className: 'fa fa-fw fa-pause pull-right' }),
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
        flow.response ? (0, _utils2.formatTimeDelta)(1000 * (flow.response.timestamp_end - flow.request.timestamp_start)) : '...'
    );
}

TimeColumn.headerClass = 'col-time';
TimeColumn.headerName = 'Time';

exports.default = [TLSColumn, IconColumn, PathColumn, MethodColumn, StatusColumn, SizeColumn, TimeColumn];

},{"../../flow/utils.js":62,"../../utils.js":63,"classnames":"classnames","react":"react"}],18:[function(require,module,exports){
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

},{"../../utils":63,"./FlowColumns":17,"classnames":"classnames","react":"react"}],19:[function(require,module,exports){
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

var _flowView = require('../../ducks/flowView');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

FlowTableHead.propTypes = {
    updateSort: _react.PropTypes.func.isRequired,
    sortDesc: _react2.default.PropTypes.bool.isRequired,
    sortColumn: _react2.default.PropTypes.string
};

function FlowTableHead(_ref) {
    var sortColumn = _ref.sortColumn;
    var sortDesc = _ref.sortDesc;
    var updateSort = _ref.updateSort;

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
                        return updateSort(Column.name, Column.name !== sortColumn ? false : !sortDesc);
                    } },
                Column.headerName
            );
        })
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        sortDesc: state.flowView.sort.desc,
        sortColumn: state.flowView.sort.column
    };
}, {
    updateSort: _flowView.updateSort
})(FlowTableHead);

},{"../../ducks/flowView":49,"./FlowColumns":17,"classnames":"classnames","react":"react","react-redux":"react-redux"}],20:[function(require,module,exports){
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
exports.default = FlowView;
exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        promptOpen: state.ui.promptOpen,
        tab: state.ui.flow.tab
    };
}, {
    selectTab: _flow.selectTab
})(FlowView);

},{"../ducks/ui/flow":54,"./FlowView/Details":21,"./FlowView/Messages":23,"./FlowView/Nav":24,"./Prompt":36,"lodash":"lodash","react":"react","react-redux":"react-redux"}],21:[function(require,module,exports){
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
        null,
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

},{"../../utils.js":63,"lodash":"lodash","react":"react"}],22:[function(require,module,exports){
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

},{"../../utils":63,"../ValueEditor/ValueEditor":39,"react":"react","react-dom":"react-dom"}],23:[function(require,module,exports){
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
        null,
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

},{"../../ducks/flows":50,"../../ducks/ui/flow":54,"../../flow/utils.js":62,"../../utils.js":63,"../ContentView":4,"../ContentView/ContentViewOptions":7,"../ValueEditor/ValidateEditor":38,"../ValueEditor/ValueEditor":39,"./Headers":22,"./ToggleEdit":25,"react":"react","react-redux":"react-redux"}],24:[function(require,module,exports){
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
            { className: 'edit-flow', onClick: function onClick() {
                    return stopEdit(flow, modifiedFlow);
                } },
            _react2.default.createElement('i', { className: 'fa fa-check' })
        ) : _react2.default.createElement(
            'a',
            { className: 'edit-flow', onClick: function onClick() {
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

},{"../../ducks/ui/flow":54,"react":"react","react-redux":"react-redux"}],26:[function(require,module,exports){
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

    return _react2.default.createElement(
        'footer',
        null,
        settings.mode && settings.mode != "regular" && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            settings.mode,
            ' mode'
        ),
        settings.intercept && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'Intercept: ',
            settings.intercept
        ),
        settings.showhost && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'showhost'
        ),
        settings.no_upstream_cert && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'no-upstream-cert'
        ),
        settings.rawtcp && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'raw-tcp'
        ),
        !settings.http2 && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'no-http2'
        ),
        settings.anticache && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'anticache'
        ),
        settings.anticomp && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'anticomp'
        ),
        settings.stickyauth && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'stickyauth: ',
            settings.stickyauth
        ),
        settings.stickycookie && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'stickycookie: ',
            settings.stickycookie
        ),
        settings.stream && _react2.default.createElement(
            'span',
            { className: 'label label-success' },
            'stream: ',
            (0, _utils.formatSize)(settings.stream)
        )
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        settings: state.settings
    };
})(Footer);

},{"../utils.js":63,"react":"react","react-redux":"react-redux"}],27:[function(require,module,exports){
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

var _ViewMenu = require('./Header/ViewMenu');

var _ViewMenu2 = _interopRequireDefault(_ViewMenu);

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

            var Active = _.find(entries, function (e) {
                return e.title == activeMenu;
            });

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
                    'div',
                    { className: 'menu' },
                    _react2.default.createElement(Active, null)
                )
            );
        }
    }]);

    return Header;
}(_react.Component);

Header.entries = [_MainMenu2.default, _ViewMenu2.default, _OptionMenu2.default];
exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        selectedFlowId: state.flows.selected[0],
        activeMenu: state.ui.header.activeMenu
    };
}, {
    setActiveMenu: _header.setActiveMenu
})(Header);

},{"../ducks/ui/header":55,"./Header/FileMenu":28,"./Header/FlowMenu":31,"./Header/MainMenu":32,"./Header/OptionMenu":33,"./Header/ViewMenu":34,"classnames":"classnames","react":"react","react-redux":"react-redux"}],28:[function(require,module,exports){
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

var _flows = require('../../ducks/flows');

var flowsActions = _interopRequireWildcard(_flows);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var FileMenu = function (_Component) {
    _inherits(FileMenu, _Component);

    function FileMenu(props, context) {
        _classCallCheck(this, FileMenu);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(FileMenu).call(this, props, context));

        _this.state = { show: false };

        _this.close = _this.close.bind(_this);
        _this.onFileClick = _this.onFileClick.bind(_this);
        _this.onNewClick = _this.onNewClick.bind(_this);
        _this.onOpenClick = _this.onOpenClick.bind(_this);
        _this.onOpenFile = _this.onOpenFile.bind(_this);
        _this.onSaveClick = _this.onSaveClick.bind(_this);
        return _this;
    }

    _createClass(FileMenu, [{
        key: 'close',
        value: function close() {
            this.setState({ show: false });
            document.removeEventListener('click', this.close);
        }
    }, {
        key: 'onFileClick',
        value: function onFileClick(e) {
            e.preventDefault();

            if (this.state.show) {
                return;
            }

            document.addEventListener('click', this.close);
            this.setState({ show: true });
        }
    }, {
        key: 'onNewClick',
        value: function onNewClick(e) {
            e.preventDefault();
            if (confirm('Delete all flows?')) {
                this.props.clearFlows();
            }
        }
    }, {
        key: 'onOpenClick',
        value: function onOpenClick(e) {
            e.preventDefault();
            this.fileInput.click();
        }
    }, {
        key: 'onOpenFile',
        value: function onOpenFile(e) {
            e.preventDefault();
            if (e.target.files.length > 0) {
                this.props.loadFlows(e.target.files[0]);
                this.fileInput.value = '';
            }
        }
    }, {
        key: 'onSaveClick',
        value: function onSaveClick(e) {
            e.preventDefault();
            this.props.saveFlows();
        }
    }, {
        key: 'render',
        value: function render() {
            var _this2 = this;

            return _react2.default.createElement(
                'div',
                { className: (0, _classnames2.default)('dropdown pull-left', { open: this.state.show }) },
                _react2.default.createElement(
                    'a',
                    { href: '#', className: 'special', onClick: this.onFileClick },
                    'mitmproxy'
                ),
                _react2.default.createElement(
                    'ul',
                    { className: 'dropdown-menu', role: 'menu' },
                    _react2.default.createElement(
                        'li',
                        null,
                        _react2.default.createElement(
                            'a',
                            { href: '#', onClick: this.onNewClick },
                            _react2.default.createElement('i', { className: 'fa fa-fw fa-file' }),
                            'New'
                        )
                    ),
                    _react2.default.createElement(
                        'li',
                        null,
                        _react2.default.createElement(
                            'a',
                            { href: '#', onClick: this.onOpenClick },
                            _react2.default.createElement('i', { className: 'fa fa-fw fa-folder-open' }),
                            'Open...'
                        ),
                        _react2.default.createElement('input', {
                            ref: function ref(_ref) {
                                return _this2.fileInput = _ref;
                            },
                            className: 'hidden',
                            type: 'file',
                            onChange: this.onOpenFile
                        })
                    ),
                    _react2.default.createElement(
                        'li',
                        null,
                        _react2.default.createElement(
                            'a',
                            { href: '#', onClick: this.onSaveClick },
                            _react2.default.createElement('i', { className: 'fa fa-fw fa-floppy-o' }),
                            'Save...'
                        )
                    ),
                    _react2.default.createElement('li', { role: 'presentation', className: 'divider' }),
                    _react2.default.createElement(
                        'li',
                        null,
                        _react2.default.createElement(
                            'a',
                            { href: 'http://mitm.it/', target: '_blank' },
                            _react2.default.createElement('i', { className: 'fa fa-fw fa-external-link' }),
                            'Install Certificates...'
                        )
                    )
                )
            );
        }
    }]);

    return FileMenu;
}(_react.Component);

exports.default = (0, _reactRedux.connect)(null, {
    clearFlows: flowsActions.clear,
    loadFlows: flowsActions.upload,
    saveFlows: flowsActions.download
})(FileMenu);

},{"../../ducks/flows":50,"classnames":"classnames","react":"react","react-redux":"react-redux"}],29:[function(require,module,exports){
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
                                '&nbsp mitmproxy docs'
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

},{"../../utils":63,"react":"react"}],30:[function(require,module,exports){
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

},{"../../filt/filt":61,"../../utils.js":63,"./FilterDocs":29,"classnames":"classnames","react":"react","react-dom":"react-dom"}],31:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _Button = require('../common/Button');

var _Button2 = _interopRequireDefault(_Button);

var _utils = require('../../flow/utils.js');

var _flows = require('../../ducks/flows');

var flowsActions = _interopRequireWildcard(_flows);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

FlowMenu.title = 'Flow';

FlowMenu.propTypes = {
    flow: _react.PropTypes.object.isRequired
};

function FlowMenu(_ref) {
    var flow = _ref.flow;
    var acceptFlow = _ref.acceptFlow;
    var replayFlow = _ref.replayFlow;
    var duplicateFlow = _ref.duplicateFlow;
    var removeFlow = _ref.removeFlow;
    var revertFlow = _ref.revertFlow;


    return _react2.default.createElement(
        'div',
        null,
        _react2.default.createElement(
            'div',
            { className: 'menu-row' },
            _react2.default.createElement(_Button2.default, { disabled: !flow || !flow.intercepted, title: '[a]ccept intercepted flow', text: 'Accept', icon: 'fa-play', onClick: function onClick() {
                    return acceptFlow(flow);
                } }),
            _react2.default.createElement(_Button2.default, { title: '[r]eplay flow', text: 'Replay', icon: 'fa-repeat', onClick: function onClick() {
                    return replayFlow(flow);
                } }),
            _react2.default.createElement(_Button2.default, { title: '[D]uplicate flow', text: 'Duplicate', icon: 'fa-copy', onClick: function onClick() {
                    return duplicateFlow(flow);
                } }),
            _react2.default.createElement(_Button2.default, { title: '[d]elete flow', text: 'Delete', icon: 'fa-trash', onClick: function onClick() {
                    return removeFlow(flow);
                } }),
            _react2.default.createElement(_Button2.default, { disabled: !flow || !flow.modified, title: 'revert changes to flow [V]', text: 'Revert', icon: 'fa-history', onClick: function onClick() {
                    return revertFlow(flow);
                } }),
            _react2.default.createElement(_Button2.default, { title: 'download', text: 'Download', icon: 'fa-download', onClick: function onClick() {
                    return window.location = _utils.MessageUtils.getContentURL(flow, flow.response);
                } })
        ),
        _react2.default.createElement('div', { className: 'clearfix' })
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        flow: state.flows.byId[state.flows.selected[0]]
    };
}, {
    acceptFlow: flowsActions.accept,
    replayFlow: flowsActions.replay,
    duplicateFlow: flowsActions.duplicate,
    removeFlow: flowsActions.remove,
    revertFlow: flowsActions.revert
})(FlowMenu);

},{"../../ducks/flows":50,"../../flow/utils.js":62,"../common/Button":40,"react":"react","react-redux":"react-redux"}],32:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = MainMenu;

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _FilterInput = require('./FilterInput');

var _FilterInput2 = _interopRequireDefault(_FilterInput);

var _settings = require('../../ducks/settings');

var _flowView = require('../../ducks/flowView');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

MainMenu.title = "Start";

function MainMenu() {
    return _react2.default.createElement(
        'div',
        null,
        _react2.default.createElement(
            'div',
            { className: 'menu-row' },
            _react2.default.createElement(FlowFilterInput, null),
            _react2.default.createElement(HighlightInput, null),
            _react2.default.createElement(InterceptInput, null)
        ),
        _react2.default.createElement('div', { className: 'clearfix' })
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
        value: state.flowView.filter || '',
        placeholder: 'Search',
        type: 'search',
        color: 'black'
    };
}, { onChange: _flowView.updateFilter })(_FilterInput2.default);

var HighlightInput = (0, _reactRedux.connect)(function (state) {
    return {
        value: state.flowView.highlight || '',
        placeholder: 'Highlight',
        type: 'tag',
        color: 'hsl(48, 100%, 50%)'
    };
}, { onChange: _flowView.updateHighlight })(_FilterInput2.default);

},{"../../ducks/flowView":49,"../../ducks/settings":53,"./FilterInput":30,"react":"react","react-redux":"react-redux"}],33:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _ToggleButton = require('../common/ToggleButton');

var _ToggleButton2 = _interopRequireDefault(_ToggleButton);

var _ToggleInputButton = require('../common/ToggleInputButton');

var _ToggleInputButton2 = _interopRequireDefault(_ToggleInputButton);

var _settings = require('../../ducks/settings');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

OptionMenu.title = 'Options';

OptionMenu.propTypes = {
    settings: _react.PropTypes.object.isRequired,
    updateSettings: _react.PropTypes.func.isRequired
};

function OptionMenu(_ref) {
    var settings = _ref.settings;
    var updateSettings = _ref.updateSettings;

    return _react2.default.createElement(
        'div',
        null,
        _react2.default.createElement(
            'div',
            { className: 'menu-row' },
            _react2.default.createElement(_ToggleButton2.default, { text: 'showhost',
                checked: settings.showhost,
                onToggle: function onToggle() {
                    return updateSettings({ showhost: !settings.showhost });
                }
            }),
            _react2.default.createElement(_ToggleButton2.default, { text: 'no_upstream_cert',
                checked: settings.no_upstream_cert,
                onToggle: function onToggle() {
                    return updateSettings({ no_upstream_cert: !settings.no_upstream_cert });
                }
            }),
            _react2.default.createElement(_ToggleButton2.default, { text: 'rawtcp',
                checked: settings.rawtcp,
                onToggle: function onToggle() {
                    return updateSettings({ rawtcp: !settings.rawtcp });
                }
            }),
            _react2.default.createElement(_ToggleButton2.default, { text: 'http2',
                checked: settings.http2,
                onToggle: function onToggle() {
                    return updateSettings({ http2: !settings.http2 });
                }
            }),
            _react2.default.createElement(_ToggleButton2.default, { text: 'anticache',
                checked: settings.anticache,
                onToggle: function onToggle() {
                    return updateSettings({ anticache: !settings.anticache });
                }
            }),
            _react2.default.createElement(_ToggleButton2.default, { text: 'anticomp',
                checked: settings.anticomp,
                onToggle: function onToggle() {
                    return updateSettings({ anticomp: !settings.anticomp });
                }
            }),
            _react2.default.createElement(_ToggleInputButton2.default, { name: 'stickyauth', placeholder: 'Sticky auth filter',
                checked: !!settings.stickyauth,
                txt: settings.stickyauth || '',
                onToggleChanged: function onToggleChanged(txt) {
                    return updateSettings({ stickyauth: !settings.stickyauth ? txt : null });
                }
            }),
            _react2.default.createElement(_ToggleInputButton2.default, { name: 'stickycookie', placeholder: 'Sticky cookie filter',
                checked: !!settings.stickycookie,
                txt: settings.stickycookie || '',
                onToggleChanged: function onToggleChanged(txt) {
                    return updateSettings({ stickycookie: !settings.stickycookie ? txt : null });
                }
            }),
            _react2.default.createElement(_ToggleInputButton2.default, { name: 'stream', placeholder: 'stream...',
                checked: !!settings.stream,
                txt: settings.stream || '',
                inputType: 'number',
                onToggleChanged: function onToggleChanged(txt) {
                    return updateSettings({ stream: !settings.stream ? txt : null });
                }
            })
        ),
        _react2.default.createElement('div', { className: 'clearfix' })
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        settings: state.settings
    };
}, {
    updateSettings: _settings.update
})(OptionMenu);

},{"../../ducks/settings":53,"../common/ToggleButton":42,"../common/ToggleInputButton":43,"react":"react","react-redux":"react-redux"}],34:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _ToggleButton = require('../common/ToggleButton');

var _ToggleButton2 = _interopRequireDefault(_ToggleButton);

var _eventLog = require('../../ducks/eventLog');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

ViewMenu.title = 'View';
ViewMenu.route = 'flows';

ViewMenu.propTypes = {
    eventLogVisible: _react.PropTypes.bool.isRequired,
    toggleEventLog: _react.PropTypes.func.isRequired
};

function ViewMenu(_ref) {
    var eventLogVisible = _ref.eventLogVisible;
    var toggleEventLog = _ref.toggleEventLog;

    return _react2.default.createElement(
        'div',
        null,
        _react2.default.createElement(
            'div',
            { className: 'menu-row' },
            _react2.default.createElement(_ToggleButton2.default, { text: 'Show Event Log', checked: eventLogVisible, onToggle: toggleEventLog })
        ),
        _react2.default.createElement('div', { className: 'clearfix' })
    );
}

exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        eventLogVisible: state.eventLog.visible
    };
}, {
    toggleEventLog: _eventLog.toggleVisibility
})(ViewMenu);

},{"../../ducks/eventLog":48,"../common/ToggleButton":42,"react":"react","react-redux":"react-redux"}],35:[function(require,module,exports){
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

var _flowView = require('../ducks/flowView');

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
                    tab: this.props.routeParams.detailTab,
                    query: this.props.query,
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
        flows: state.flowView.data,
        filter: state.flowView.filter,
        highlight: state.flowView.highlight,
        selectedFlow: state.flows.byId[state.flows.selected[0]]
    };
}, {
    selectFlow: flowsActions.select,
    updateFilter: _flowView.updateFilter,
    updateHighlight: _flowView.updateHighlight,
    updateFlow: flowsActions.update
})(MainView);

},{"../ducks/flowView":49,"../ducks/flows":50,"./FlowTable":16,"./FlowView":20,"./common/Splitter":41,"react":"react","react-redux":"react-redux"}],36:[function(require,module,exports){
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

},{"../utils.js":63,"lodash":"lodash","react":"react","react-dom":"react-dom"}],37:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _reactRedux = require('react-redux');

var _app = require('../ducks/app');

var _keyboard = require('../ducks/ui/keyboard');

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
            this.props.appInit(this.context.router);
            window.addEventListener('keydown', this.props.onKeyDown);
        }
    }, {
        key: 'componentWillUnmount',
        value: function componentWillUnmount() {
            this.props.appDestruct(this.context.router);
            window.removeEventListener('keydown', this.props.onKeyDown);
        }
    }, {
        key: 'componentWillReceiveProps',
        value: function componentWillReceiveProps(nextProps) {
            /*
            FIXME: improve react-router -> redux integration.
            if (nextProps.location.query[Query.SEARCH] !== nextProps.filter) {
                this.props.updateFilter(nextProps.location.query[Query.SEARCH], false)
            }
            if (nextProps.location.query[Query.HIGHLIGHT] !== nextProps.highlight) {
                this.props.updateHighlight(nextProps.location.query[Query.HIGHLIGHT], false)
            }
            */
            if (nextProps.query === this.props.query && nextProps.selectedFlowId === this.props.selectedFlowId && nextProps.panel === this.props.panel) {
                return;
            }
            if (nextProps.selectedFlowId) {
                this.context.router.replace({ pathname: '/flows/' + nextProps.selectedFlowId + '/' + nextProps.panel, query: nextProps.query });
            } else {
                this.context.router.replace({ pathname: '/flows', query: nextProps.query });
            }
        }
    }, {
        key: 'render',
        value: function render() {
            var _props = this.props;
            var showEventLog = _props.showEventLog;
            var location = _props.location;
            var children = _props.children;
            var query = _props.query;

            return _react2.default.createElement(
                'div',
                { id: 'container', tabIndex: '0' },
                _react2.default.createElement(_Header2.default, null),
                _react2.default.cloneElement(children, { ref: 'view', location: location, query: query }),
                showEventLog && _react2.default.createElement(_EventLog2.default, { key: 'eventlog' }),
                _react2.default.createElement(_Footer2.default, null)
            );
        }
    }]);

    return ProxyAppMain;
}(_react.Component);

ProxyAppMain.contextTypes = {
    router: _react.PropTypes.object.isRequired
};
exports.default = (0, _reactRedux.connect)(function (state) {
    return {
        showEventLog: state.eventLog.visible,
        query: state.flowView.filter,
        panel: state.ui.flow.tab,
        selectedFlowId: state.flows.selected[0]
    };
}, {
    appInit: _app.init,
    appDestruct: _app.destruct,
    onKeyDown: _keyboard.onKeyDown
})(ProxyAppMain);

},{"../ducks/app":47,"../ducks/ui/keyboard":57,"./EventLog":14,"./Footer":26,"./Header":27,"react":"react","react-redux":"react-redux"}],38:[function(require,module,exports){
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

},{"../../utils":63,"classnames":"classnames","lodash":"lodash","react":"react"}],40:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.default = Button;

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _classnames = require('classnames');

var _classnames2 = _interopRequireDefault(_classnames);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

Button.propTypes = {
    onClick: _react.PropTypes.func.isRequired,
    text: _react.PropTypes.string,
    icon: _react.PropTypes.string
};

function Button(_ref) {
    var onClick = _ref.onClick;
    var text = _ref.text;
    var icon = _ref.icon;
    var disabled = _ref.disabled;
    var className = _ref.className;

    return _react2.default.createElement(
        'div',
        { className: (0, _classnames2.default)(className, 'btn btn-default'),
            onClick: onClick,
            disabled: disabled },
        icon && _react2.default.createElement('i', { className: "fa fa-fw " + icon }),
        text && text
    );
}

},{"classnames":"classnames","react":"react"}],41:[function(require,module,exports){
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

},{"classnames":"classnames","react":"react","react-dom":"react-dom"}],42:[function(require,module,exports){
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

},{"react":"react"}],43:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _classnames = require('classnames');

var _classnames2 = _interopRequireDefault(_classnames);

var _utils = require('../../utils');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var ToggleInputButton = function (_Component) {
    _inherits(ToggleInputButton, _Component);

    function ToggleInputButton(props) {
        _classCallCheck(this, ToggleInputButton);

        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(ToggleInputButton).call(this, props));

        _this.state = { txt: props.txt };
        return _this;
    }

    _createClass(ToggleInputButton, [{
        key: 'onChange',
        value: function onChange(e) {
            this.setState({ txt: e.target.value });
        }
    }, {
        key: 'onKeyDown',
        value: function onKeyDown(e) {
            e.stopPropagation();
            if (e.keyCode === _utils.Key.ENTER) {
                this.props.onToggleChanged(this.state.txt);
            }
        }
    }, {
        key: 'render',
        value: function render() {
            var _this2 = this;

            return _react2.default.createElement(
                'div',
                { className: 'input-group toggle-input-btn' },
                _react2.default.createElement(
                    'span',
                    { className: 'input-group-btn',
                        onClick: function onClick() {
                            return _this2.props.onToggleChanged(_this2.state.txt);
                        } },
                    _react2.default.createElement(
                        'div',
                        { className: (0, _classnames2.default)('btn', this.props.checked ? 'btn-primary' : 'btn-default') },
                        _react2.default.createElement('span', { className: (0, _classnames2.default)('fa', this.props.checked ? 'fa-check-square-o' : 'fa-square-o') }),
                        ' ',
                        this.props.name
                    )
                ),
                _react2.default.createElement('input', {
                    className: 'form-control',
                    placeholder: this.props.placeholder,
                    disabled: this.props.checked,
                    value: this.state.txt,
                    type: this.props.inputType,
                    onChange: function onChange(e) {
                        return _this2.onChange(e);
                    },
                    onKeyDown: function onKeyDown(e) {
                        return _this2.onKeyDown(e);
                    }
                })
            );
        }
    }]);

    return ToggleInputButton;
}(_react.Component);

ToggleInputButton.propTypes = {
    name: _react.PropTypes.string.isRequired,
    txt: _react.PropTypes.string.isRequired,
    onToggleChanged: _react.PropTypes.func.isRequired
};
exports.default = ToggleInputButton;

},{"../../utils":63,"classnames":"classnames","react":"react"}],44:[function(require,module,exports){
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

},{"react":"react","react-dom":"react-dom"}],45:[function(require,module,exports){
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

},{}],46:[function(require,module,exports){
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

},{"flux":"flux"}],47:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.INIT = undefined;
exports.reduce = reduce;
exports.init = init;
exports.destruct = destruct;

var _websocket = require('./websocket');

var INIT = exports.INIT = 'APP_INIT';

var defaultState = {};

function reduce() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {

        default:
            return state;
    }
}

function init() {
    return function (dispatch) {
        dispatch((0, _websocket.connect)());
        dispatch({ type: INIT });
    };
}

function destruct() {
    return function (dispatch) {
        dispatch((0, _websocket.disconnect)());
        dispatch({ type: DESTRUCT });
    };
}

},{"./websocket":60}],48:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.FETCH_ERROR = exports.UNKNOWN_CMD = exports.TOGGLE_FILTER = exports.TOGGLE_VISIBILITY = exports.RECEIVE = exports.ADD = exports.DATA_URL = exports.MSG_TYPE = undefined;

var _typeof = typeof Symbol === "function" && typeof Symbol.iterator === "symbol" ? function (obj) { return typeof obj; } : function (obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol ? "symbol" : typeof obj; };

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reduce;
exports.toggleFilter = toggleFilter;
exports.toggleVisibility = toggleVisibility;
exports.add = add;
exports.handleWsMsg = handleWsMsg;
exports.fetchData = fetchData;
exports.receiveData = receiveData;

var _list = require('./utils/list');

var listActions = _interopRequireWildcard(_list);

var _view = require('./utils/view');

var viewActions = _interopRequireWildcard(_view);

var _websocket = require('./websocket');

var websocketActions = _interopRequireWildcard(_websocket);

var _msgQueue = require('./msgQueue');

var msgQueueActions = _interopRequireWildcard(_msgQueue);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

var MSG_TYPE = exports.MSG_TYPE = 'UPDATE_EVENTLOG';
var DATA_URL = exports.DATA_URL = '/events';

var ADD = exports.ADD = 'EVENTLOG_ADD';
var RECEIVE = exports.RECEIVE = 'EVENTLOG_RECEIVE';
var TOGGLE_VISIBILITY = exports.TOGGLE_VISIBILITY = 'EVENTLOG_TOGGLE_VISIBILITY';
var TOGGLE_FILTER = exports.TOGGLE_FILTER = 'EVENTLOG_TOGGLE_FILTER';
var UNKNOWN_CMD = exports.UNKNOWN_CMD = 'EVENTLOG_UNKNOWN_CMD';
var FETCH_ERROR = exports.FETCH_ERROR = 'EVENTLOG_FETCH_ERROR';

var defaultState = {
    logId: 0,
    visible: false,
    filters: { debug: false, info: true, web: true },
    list: (0, listActions.default)(undefined, {}),
    view: (0, viewActions.default)(undefined, {})
};

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
                        filters: filters,
                        view: (0, viewActions.default)(state.view, viewActions.updateFilter(state.list.data, function (log) {
                            return filters[log.level];
                        }))
                    })
                };

            case ADD:
                var item = {
                    id: state.logId,
                    message: action.message,
                    level: action.level
                };
                return {
                    v: _extends({}, state, {
                        logId: state.logId + 1,
                        list: (0, listActions.default)(state.list, listActions.add(item)),
                        view: (0, viewActions.default)(state.view, viewActions.add(item, function (log) {
                            return state.filters[log.level];
                        }))
                    })
                };

            case RECEIVE:
                return {
                    v: _extends({}, state, {
                        list: (0, listActions.default)(state.list, listActions.receive(action.list)),
                        view: (0, viewActions.default)(state.view, viewActions.receive(action.list, function (log) {
                            return state.filters[log.level];
                        }))
                    })
                };

            default:
                return {
                    v: state
                };
        }
    }();

    if ((typeof _ret === 'undefined' ? 'undefined' : _typeof(_ret)) === "object") return _ret.v;
}

/**
 * @public
 */
function toggleFilter(filter) {
    return { type: TOGGLE_FILTER, filter: filter };
}

/**
 * @public
 *
 * @todo move to ui?
 */
function toggleVisibility() {
    return { type: TOGGLE_VISIBILITY };
}

/**
 * @public
 */
function add(message) {
    var level = arguments.length <= 1 || arguments[1] === undefined ? 'web' : arguments[1];

    return { type: ADD, message: message, level: level };
}

/**
 * This action creater takes all WebSocket events
 *
 * @public websocket
 */
function handleWsMsg(msg) {
    switch (msg.cmd) {

        case websocketActions.CMD_ADD:
            return add(msg.data.message, msg.data.level);

        case websocketActions.CMD_RESET:
            return fetchData();

        default:
            return { type: UNKNOWN_CMD, msg: msg };
    }
}

/**
 * @public websocket
 */
function fetchData() {
    return msgQueueActions.fetchData(MSG_TYPE);
}

/**
 * @public msgQueue
 */
function receiveData(list) {
    return { type: RECEIVE, list: list };
}

},{"./msgQueue":52,"./utils/list":58,"./utils/view":59,"./websocket":60}],49:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.UPDATE_HIGHLIGHT = exports.UPDATE_SORT = exports.UPDATE_FILTER = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.makeFilter = makeFilter;
exports.makeSort = makeSort;
exports.default = reduce;
exports.updateFilter = updateFilter;
exports.updateHighlight = updateHighlight;
exports.updateSort = updateSort;
exports.selectRelative = selectRelative;

var _view = require('./utils/view');

var viewActions = _interopRequireWildcard(_view);

var _flows = require('./flows');

var flowActions = _interopRequireWildcard(_flows);

var _filt = require('../filt/filt');

var _filt2 = _interopRequireDefault(_filt);

var _utils = require('../flow/utils');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

var UPDATE_FILTER = exports.UPDATE_FILTER = 'FLOWVIEW_UPDATE_FILTER';
var UPDATE_SORT = exports.UPDATE_SORT = 'FLOWVIEW_UPDATE_SORT';
var UPDATE_HIGHLIGHT = exports.UPDATE_HIGHLIGHT = 'FLOWVIEW_UPDATE_HIGHLIGHT';

var sortKeyFuns = {

    TLSColumn: function TLSColumn(flow) {
        return flow.request.scheme;
    },

    PathColumn: function PathColumn(flow) {
        return _utils.RequestUtils.pretty_url(flow.request);
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

var defaultState = _extends({
    highlight: null,
    filter: null,
    sort: { column: null, desc: false }
}, (0, viewActions.default)(undefined, {}));

function reduce() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {

        case UPDATE_HIGHLIGHT:
            return _extends({}, state, {
                highlight: action.highlight
            });

        case UPDATE_FILTER:
            return _extends({}, (0, viewActions.default)(state, viewActions.updateFilter(action.flows, makeFilter(action.filter), makeSort(state.sort))), {
                filter: action.filter
            });

        case UPDATE_SORT:
            var sort = { column: action.column, desc: action.desc };
            return _extends({}, (0, viewActions.default)(state, viewActions.updateSort(makeSort(sort))), {
                sort: sort
            });

        case flowActions.ADD:
            return _extends({}, (0, viewActions.default)(state, viewActions.add(action.item, makeFilter(state.filter), makeSort(state.sort))));

        case flowActions.UPDATE:
            return _extends({}, (0, viewActions.default)(state, viewActions.update(action.item, makeFilter(state.filter), makeSort(state.sort))));

        case flowActions.REMOVE:
            return _extends({}, (0, viewActions.default)(state, viewActions.remove(action.id)));

        case flowActions.RECEIVE:
            return _extends({}, (0, viewActions.default)(state, viewActions.receive(action.list, makeFilter(state.filter), makeSort(state.sort))));

        default:
            return _extends({}, (0, viewActions.default)(state, action));
    }
}

/**
 * @public
 */
function updateFilter(filter) {
    return function (dispatch, getState) {
        dispatch({ type: UPDATE_FILTER, filter: filter, flows: getState().flows.data });
    };
}

/**
 * @public
 */
function updateHighlight(highlight) {
    return { type: UPDATE_HIGHLIGHT, highlight: highlight };
}

/**
 * @public
 */
function updateSort(column, desc) {
    return { type: UPDATE_SORT, column: column, desc: desc };
}

/**
 * @public
 */
function selectRelative(shift) {
    return function (dispatch, getState) {
        var currentSelectionIndex = getState().flowView.indexOf[getState().flows.selected[0]];
        var minIndex = 0;
        var maxIndex = getState().flowView.data.length - 1;
        var newIndex = void 0;
        if (currentSelectionIndex === undefined) {
            newIndex = shift < 0 ? minIndex : maxIndex;
        } else {
            newIndex = currentSelectionIndex + shift;
            newIndex = Math.max(newIndex, minIndex);
            newIndex = Math.min(newIndex, maxIndex);
        }
        var flow = getState().flowView.data[newIndex];
        dispatch(flowActions.select(flow ? flow.id : undefined));
    };
}

},{"../filt/filt":61,"../flow/utils":62,"./flows":50,"./utils/view":59}],50:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.SELECT = exports.FETCH_ERROR = exports.UNKNOWN_CMD = exports.REQUEST_ACTION = exports.RECEIVE = exports.REMOVE = exports.UPDATE = exports.ADD = exports.DATA_URL = exports.MSG_TYPE = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reduce;
exports.accept = accept;
exports.acceptAll = acceptAll;
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
exports.handleWsMsg = handleWsMsg;
exports.fetchFlows = fetchFlows;
exports.receiveData = receiveData;
exports.addFlow = addFlow;
exports.updateFlow = updateFlow;
exports.removeFlow = removeFlow;

var _utils = require('../utils');

var _list = require('./utils/list');

var listActions = _interopRequireWildcard(_list);

var _msgQueue = require('./msgQueue');

var msgQueueActions = _interopRequireWildcard(_msgQueue);

var _websocket = require('./websocket');

var websocketActions = _interopRequireWildcard(_websocket);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

var MSG_TYPE = exports.MSG_TYPE = 'UPDATE_FLOWS';
var DATA_URL = exports.DATA_URL = '/flows';

var ADD = exports.ADD = 'FLOWS_ADD';
var UPDATE = exports.UPDATE = 'FLOWS_UPDATE';
var REMOVE = exports.REMOVE = 'FLOWS_REMOVE';
var RECEIVE = exports.RECEIVE = 'FLOWS_RECEIVE';
var REQUEST_ACTION = exports.REQUEST_ACTION = 'FLOWS_REQUEST_ACTION';
var UNKNOWN_CMD = exports.UNKNOWN_CMD = 'FLOWS_UNKNOWN_CMD';
var FETCH_ERROR = exports.FETCH_ERROR = 'FLOWS_FETCH_ERROR';
var SELECT = exports.SELECT = 'FLOWS_SELECT';

var defaultState = _extends({
    selected: []
}, (0, listActions.default)(undefined, {}));

function reduce() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {

        case ADD:
            return _extends({}, state, (0, listActions.default)(state, listActions.add(action.item)));

        case UPDATE:
            return _extends({}, state, (0, listActions.default)(state, listActions.update(action.item)));

        case REMOVE:
            return _extends({}, state, (0, listActions.default)(state, listActions.remove(action.id)));

        case RECEIVE:
            return _extends({}, state, (0, listActions.default)(state, listActions.receive(action.list)));

        case SELECT:
            return _extends({}, state, {
                selected: action.flowIds
            });

        default:
            return _extends({}, state, (0, listActions.default)(state, action));
    }
}

/**
 * @public
 */
function accept(flow) {
    return function (dispatch) {
        return (0, _utils.fetchApi)('/flows/' + flow.id + '/accept', { method: 'POST' });
    };
}

/**
 * @public
 */
function acceptAll() {
    return function (dispatch) {
        return (0, _utils.fetchApi)('/flows/accept', { method: 'POST' });
    };
}

/**
 * @public
 */
function remove(flow) {
    return function (dispatch) {
        return (0, _utils.fetchApi)('/flows/' + flow.id, { method: 'DELETE' });
    };
}

/**
 * @public
 */
function duplicate(flow) {
    return function (dispatch) {
        return (0, _utils.fetchApi)('/flows/' + flow.id + '/duplicate', { method: 'POST' });
    };
}

/**
 * @public
 */
function replay(flow) {
    return function (dispatch) {
        return (0, _utils.fetchApi)('/flows/' + flow.id + '/replay', { method: 'POST' });
    };
}

/**
 * @public
 */
function revert(flow) {
    return function (dispatch) {
        return (0, _utils.fetchApi)('/flows/' + flow.id + '/revert', { method: 'POST' });
    };
}

/**
 * @public
 */
function update(flow, data) {
    return function (dispatch) {
        return _utils.fetchApi.put('/flows/' + flow.id, data);
    };
}

function uploadContent(flow, file, type) {
    var body = new FormData();
    file = new Blob([file], { type: 'plain/text' });
    body.append('file', file);
    return function (dispatch) {
        return (0, _utils.fetchApi)('/flows/' + flow.id + '/' + type + '/content', { method: 'post', body: body });
    };
}

/**
 * @public
 */
function clear() {
    return function (dispatch) {
        return (0, _utils.fetchApi)('/clear', { method: 'POST' });
    };
}

/**
 * @public
 */
function download() {
    window.location = '/flows/dump';
    return { type: REQUEST_ACTION };
}

/**
 * @public
 */
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

/**
 * This action creater takes all WebSocket events
 *
 * @public websocket
 */
function handleWsMsg(msg) {
    switch (msg.cmd) {

        case websocketActions.CMD_ADD:
            return addFlow(msg.data);

        case websocketActions.CMD_UPDATE:
            return updateFlow(msg.data);

        case websocketActions.CMD_REMOVE:
            return removeFlow(msg.data.id);

        case websocketActions.CMD_RESET:
            return fetchFlows();

        default:
            return { type: UNKNOWN_CMD, msg: msg };
    }
}

/**
 * @public websocket
 */
function fetchFlows() {
    return msgQueueActions.fetchData(MSG_TYPE);
}

/**
 * @public msgQueue
 */
function receiveData(list) {
    return { type: RECEIVE, list: list };
}

/**
 * @private
 */
function addFlow(item) {
    return { type: ADD, item: item };
}

/**
 * @private
 */
function updateFlow(item) {
    return { type: UPDATE, item: item };
}

/**
 * @private
 */
function removeFlow(id) {
    return { type: REMOVE, id: id };
}

},{"../utils":63,"./msgQueue":52,"./utils/list":58,"./websocket":60}],51:[function(require,module,exports){
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

var _flowView = require('./flowView');

var _flowView2 = _interopRequireDefault(_flowView);

var _settings = require('./settings');

var _settings2 = _interopRequireDefault(_settings);

var _index = require('./ui/index');

var _index2 = _interopRequireDefault(_index);

var _msgQueue = require('./msgQueue');

var _msgQueue2 = _interopRequireDefault(_msgQueue);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

exports.default = (0, _redux.combineReducers)({
    eventLog: _eventLog2.default,
    websocket: _websocket2.default,
    flows: _flows2.default,
    flowView: _flowView2.default,
    settings: _settings2.default,
    ui: _index2.default,
    msgQueue: _msgQueue2.default
});

},{"./eventLog":48,"./flowView":49,"./flows":50,"./msgQueue":52,"./settings":53,"./ui/index":56,"./websocket":60,"redux":"redux"}],52:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.FETCH_ERROR = exports.CLEAR = exports.ENQUEUE = exports.INIT = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _handlers;

exports.default = reduce;
exports.handleWsMsg = handleWsMsg;
exports.fetchData = fetchData;
exports.receive = receive;
exports.init = init;
exports.clear = clear;
exports.fetchError = fetchError;

var _utils = require('../utils');

var _websocket = require('./websocket');

var websocketActions = _interopRequireWildcard(_websocket);

var _eventLog = require('./eventLog');

var eventLogActions = _interopRequireWildcard(_eventLog);

var _flows = require('./flows');

var flowsActions = _interopRequireWildcard(_flows);

var _settings = require('./settings');

var settingsActions = _interopRequireWildcard(_settings);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function _toConsumableArray(arr) { if (Array.isArray(arr)) { for (var i = 0, arr2 = Array(arr.length); i < arr.length; i++) { arr2[i] = arr[i]; } return arr2; } else { return Array.from(arr); } }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

var INIT = exports.INIT = 'MSG_QUEUE_INIT';
var ENQUEUE = exports.ENQUEUE = 'MSG_QUEUE_ENQUEUE';
var CLEAR = exports.CLEAR = 'MSG_QUEUE_CLEAR';
var FETCH_ERROR = exports.FETCH_ERROR = 'MSG_QUEUE_FETCH_ERROR';

var handlers = (_handlers = {}, _defineProperty(_handlers, eventLogActions.MSG_TYPE, eventLogActions), _defineProperty(_handlers, flowsActions.MSG_TYPE, flowsActions), _defineProperty(_handlers, settingsActions.MSG_TYPE, settingsActions), _handlers);

var defaultState = {};

function reduce() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {

        case INIT:
            return _extends({}, state, _defineProperty({}, action.queue, []));

        case ENQUEUE:
            return _extends({}, state, _defineProperty({}, action.queue, [].concat(_toConsumableArray(state[action.queue]), [action.msg])));

        case CLEAR:
            return _extends({}, state, _defineProperty({}, action.queue, null));

        default:
            return state;
    }
}

/**
 * @public websocket
 */
function handleWsMsg(msg) {
    return function (dispatch, getState) {
        var handler = handlers[msg.type];
        if (msg.cmd === websocketActions.CMD_RESET) {
            return dispatch(fetchData(handler.MSG_TYPE));
        }
        if (getState().msgQueue[handler.MSG_TYPE]) {
            return dispatch({ type: ENQUEUE, queue: handler.MSG_TYPE, msg: msg });
        }
        return dispatch(handler.handleWsMsg(msg));
    };
}

/**
 * @public
 */
function fetchData(type) {
    return function (dispatch) {
        var handler = handlers[type];

        dispatch(init(handler.MSG_TYPE));

        (0, _utils.fetchApi)(handler.DATA_URL).then(function (res) {
            return res.json();
        }).then(function (json) {
            return dispatch(receive(type, json));
        }).catch(function (error) {
            return dispatch(fetchError(type, error));
        });
    };
}

/**
 * @private
 */
function receive(type, res) {
    return function (dispatch, getState) {
        var handler = handlers[type];
        var queue = getState().msgQueue[handler.MSG_TYPE] || [];

        dispatch(clear(handler.MSG_TYPE));
        dispatch(handler.receiveData(res.data));
        var _iteratorNormalCompletion = true;
        var _didIteratorError = false;
        var _iteratorError = undefined;

        try {
            for (var _iterator = queue[Symbol.iterator](), _step; !(_iteratorNormalCompletion = (_step = _iterator.next()).done); _iteratorNormalCompletion = true) {
                var msg = _step.value;

                dispatch(handler.handleWsMsg(msg));
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
    };
}

/**
 * @private
 */
function init(queue) {
    return { type: INIT, queue: queue };
}

/**
 * @private
 */
function clear(queue) {
    return { type: CLEAR, queue: queue };
}

/**
 * @private
 */
function fetchError(type, error) {
    var _ref;

    return _ref = { type: FETCH_ERROR }, _defineProperty(_ref, 'type', type), _defineProperty(_ref, 'error', error), _ref;
}

},{"../utils":63,"./eventLog":48,"./flows":50,"./settings":53,"./websocket":60}],53:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.UNKNOWN_CMD = exports.REQUEST_UPDATE = exports.UPDATE = exports.RECEIVE = exports.DATA_URL = exports.MSG_TYPE = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reducer;
exports.handleWsMsg = handleWsMsg;
exports.update = update;
exports.fetchData = fetchData;
exports.receiveData = receiveData;
exports.updateSettings = updateSettings;

var _utils = require('../utils');

var _websocket = require('./websocket');

var websocketActions = _interopRequireWildcard(_websocket);

var _msgQueue = require('./msgQueue');

var msgQueueActions = _interopRequireWildcard(_msgQueue);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

var MSG_TYPE = exports.MSG_TYPE = 'UPDATE_SETTINGS';
var DATA_URL = exports.DATA_URL = '/settings';

var RECEIVE = exports.RECEIVE = 'RECEIVE';
var UPDATE = exports.UPDATE = 'UPDATE';
var REQUEST_UPDATE = exports.REQUEST_UPDATE = 'REQUEST_UPDATE';
var UNKNOWN_CMD = exports.UNKNOWN_CMD = 'SETTINGS_UNKNOWN_CMD';

var defaultState = {};

function reducer() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {

        case RECEIVE:
            return action.settings;

        case UPDATE:
            return _extends({}, state, action.settings);

        default:
            return state;
    }
}

/**
 * @public msgQueue
 */
function handleWsMsg(msg) {
    switch (msg.cmd) {

        case websocketActions.CMD_UPDATE:
            return updateSettings(msg.data);

        default:
            console.error('unknown settings update', msg);
            return { type: UNKNOWN_CMD, msg: msg };
    }
}

/**
 * @public
 */
function update(settings) {
    _utils.fetchApi.put('/settings', settings);
    return { type: REQUEST_UPDATE };
}

/**
 * @public websocket
 */
function fetchData() {
    return msgQueueActions.fetchData(MSG_TYPE);
}

/**
 * @public msgQueue
 */
function receiveData(settings) {
    return { type: RECEIVE, settings: settings };
}

/**
 * @private
 */
function updateSettings(settings) {
    return { type: UPDATE, settings: settings };
}

},{"../utils":63,"./msgQueue":52,"./websocket":60}],54:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.SET_CONTENT_VIEW_DESCRIPTION = exports.SET_SHOW_FULL_CONTENT = exports.UPLOAD_CONTENT = exports.UPDATE_EDIT = exports.START_EDIT = exports.SET_TAB = exports.DISPLAY_LARGE = exports.SET_CONTENT_VIEW = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reducer;
exports.setContentView = setContentView;
exports.displayLarge = displayLarge;
exports.selectTab = selectTab;
exports.startEdit = startEdit;
exports.updateEdit = updateEdit;
exports.setContentViewDescription = setContentViewDescription;
exports.setShowFullContent = setShowFullContent;
exports.updateEdit = updateEdit;
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
    SET_CONTENT_VIEW_DESCRIPTION = exports.SET_CONTENT_VIEW_DESCRIPTION = "UI_SET_CONTENT_VIEW_DESCRIPTION";

var defaultState = {
    displayLarge: false,
    contentViewDescription: '',
    showFullContent: false,
    modifiedFlow: false,
    contentView: 'Auto',
    tab: 'request'
};

function reducer() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    var wasInEditMode = !!state.modifiedFlow;
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
                viewDescription: '',
                showFullContent: false
            });

        case flowsActions.UPDATE:
            // There is no explicit "stop edit" event.
            // We stop editing when we receive an update for
            // the currently edited flow from the server
            if (action.item.id === state.modifiedFlow.id) {
                return _extends({}, state, {
                    modifiedFlow: false,
                    displayLarge: false,
                    contentView: wasInEditMode ? 'Auto' : state.contentView,
                    viewDescription: '',
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
                showFullContent: action.show
            });

        case SET_TAB:
            return _extends({}, state, {
                tab: action.tab,
                displayLarge: false,
                showFullContent: false
            });

        case SET_CONTENT_VIEW:
            return _extends({}, state, {
                contentView: action.contentView,
                showFullContent: action.contentView == 'Edit'
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

function setShowFullContent(show) {
    return { type: SET_SHOW_FULL_CONTENT, show: show };
}

function updateEdit(update) {
    return { type: UPDATE_EDIT, update: update };
}

function stopEdit(flow, modifiedFlow) {
    var diff = (0, _utils.getDiff)(flow, modifiedFlow);
    return flowsActions.update(flow, diff);
}

},{"../../utils":63,"../flows":50,"lodash":"lodash"}],55:[function(require,module,exports){
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
            if (action.flowIds.length && !state.isFlowSelected) {
                return _extends({}, state, {
                    activeMenu: 'Flow',
                    isFlowSelected: true
                });
            }

            // Deselect
            if (!action.flowIds.length && state.isFlowSelected) {
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

},{"../flows":50}],56:[function(require,module,exports){
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

exports.default = (0, _redux.combineReducers)({
    flow: _flow2.default,
    header: _header2.default
});

},{"./flow":54,"./header":55,"redux":"redux"}],57:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.onKeyDown = onKeyDown;

var _utils = require('../../utils');

var _flowView = require('../flowView');

var _flow = require('./flow');

var _flows = require('../flows');

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
                dispatch((0, _flowView.selectRelative)(-1));
                break;

            case _utils.Key.J:
            case _utils.Key.DOWN:
                dispatch((0, _flowView.selectRelative)(+1));
                break;

            case _utils.Key.SPACE:
            case _utils.Key.PAGE_DOWN:
                dispatch((0, _flowView.selectRelative)(+10));
                break;

            case _utils.Key.PAGE_UP:
                dispatch((0, _flowView.selectRelative)(-10));
                break;

            case _utils.Key.END:
                dispatch((0, _flowView.selectRelative)(+1e10));
                break;

            case _utils.Key.HOME:
                dispatch((0, _flowView.selectRelative)(-1e10));
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

            case _utils.Key.C:
                if (shiftKey) {
                    dispatch(flowsActions.clear());
                }
                break;

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
                        dispatch(flowsActions.acceptAll());
                    } else if (flow && flow.intercepted) {
                        dispatch(flowsActions.accept(flow));
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

            default:
                return;
        }
    };
}

},{"../../utils":63,"../flowView":49,"../flows":50,"./flow":54}],58:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.RECEIVE = exports.REMOVE = exports.UPDATE = exports.ADD = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reduce;
exports.add = add;
exports.update = update;
exports.remove = remove;
exports.receive = receive;

var _lodash = require('lodash');

var _lodash2 = _interopRequireDefault(_lodash);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _toConsumableArray(arr) { if (Array.isArray(arr)) { for (var i = 0, arr2 = Array(arr.length); i < arr.length; i++) { arr2[i] = arr[i]; } return arr2; } else { return Array.from(arr); } }

var ADD = exports.ADD = 'LIST_ADD';
var UPDATE = exports.UPDATE = 'LIST_UPDATE';
var REMOVE = exports.REMOVE = 'LIST_REMOVE';
var RECEIVE = exports.RECEIVE = 'LIST_RECEIVE';

var defaultState = {
    data: [],
    byId: {},
    indexOf: {}
};

function reduce() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {

        case ADD:
            return _extends({}, state, {
                data: [].concat(_toConsumableArray(state.data), [action.item]),
                byId: _extends({}, state.byId, _defineProperty({}, action.item.id, action.item)),
                indexOf: _extends({}, state.indexOf, _defineProperty({}, action.item.id, state.data.length))
            });

        case UPDATE:
            {
                var index = state.indexOf[action.item.id];

                if (index == null) {
                    return state;
                }

                var data = [].concat(_toConsumableArray(state.data));

                data[index] = action.item;

                return _extends({}, state, {
                    data: data,
                    byId: _extends({}, state.byId, _defineProperty({}, action.item.id, action.item))
                });
            }

        case REMOVE:
            {
                var _index = state.indexOf[action.id];

                if (_index == null) {
                    return state;
                }

                var _data = [].concat(_toConsumableArray(state.data));
                var indexOf = _extends({}, state.indexOf, _defineProperty({}, action.id, null));

                _data.splice(_index, 1);
                for (var i = _data.length - 1; i >= _index; i--) {
                    indexOf[_data[i].id] = i;
                }

                return _extends({}, state, {
                    data: _data,
                    indexOf: indexOf,
                    byId: _extends({}, state.byId, _defineProperty({}, action.id, null))
                });
            }

        case RECEIVE:
            return _extends({}, state, {
                data: action.list,
                byId: _lodash2.default.fromPairs(action.list.map(function (item) {
                    return [item.id, item];
                })),
                indexOf: _lodash2.default.fromPairs(action.list.map(function (item, index) {
                    return [item.id, index];
                }))
            });

        default:
            return state;
    }
}

/**
 * @public
 */
function add(item) {
    return { type: ADD, item: item };
}

/**
 * @public
 */
function update(item) {
    return { type: UPDATE, item: item };
}

/**
 * @public
 */
function remove(id) {
    return { type: REMOVE, id: id };
}

/**
 * @public
 */
function receive(list) {
    return { type: RECEIVE, list: list };
}

},{"lodash":"lodash"}],59:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.RECEIVE = exports.REMOVE = exports.UPDATE = exports.ADD = exports.UPDATE_SORT = exports.UPDATE_FILTER = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reduce;
exports.updateFilter = updateFilter;
exports.updateSort = updateSort;
exports.add = add;
exports.update = update;
exports.remove = remove;
exports.receive = receive;

var _lodash = require('lodash');

var _lodash2 = _interopRequireDefault(_lodash);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _toConsumableArray(arr) { if (Array.isArray(arr)) { for (var i = 0, arr2 = Array(arr.length); i < arr.length; i++) { arr2[i] = arr[i]; } return arr2; } else { return Array.from(arr); } }

var UPDATE_FILTER = exports.UPDATE_FILTER = 'VIEW_UPDATE_FILTER';
var UPDATE_SORT = exports.UPDATE_SORT = 'VIEW_UPDATE_SORT';
var ADD = exports.ADD = 'VIEW_ADD';
var UPDATE = exports.UPDATE = 'VIEW_UPDATE';
var REMOVE = exports.REMOVE = 'VIEW_REMOVE';
var RECEIVE = exports.RECEIVE = 'VIEW_RECEIVE';

var defaultState = {
    data: [],
    indexOf: {}
};

function reduce() {
    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {

        case UPDATE_FILTER:
            {
                var data = action.list.filter(action.filter).sort(action.sort);
                return _extends({}, state, {
                    data: data,
                    indexOf: _lodash2.default.fromPairs(data.map(function (item, index) {
                        return [item.id, index];
                    }))
                });
            }

        case UPDATE_SORT:
            {
                var _data = [].concat(_toConsumableArray(state.data)).sort(action.sort);
                return _extends({}, state, {
                    data: _data,
                    indexOf: _lodash2.default.fromPairs(_data.map(function (item, index) {
                        return [item.id, index];
                    }))
                });
            }

        case ADD:
            if (state.indexOf[action.item.id] != null || !action.filter(action.item)) {
                return state;
            }
            return _extends({}, state, sortedInsert(state, action.item, action.sort));

        case REMOVE:
            if (state.indexOf[action.id] == null) {
                return state;
            }
            return _extends({}, state, sortedRemove(state, action.id));

        case UPDATE:
            if (state.indexOf[action.item.id] == null) {
                return;
            }
            var nextState = _extends({}, state, sortedRemove(state, action.item.id));
            if (!action.filter(action.item)) {
                return nextState;
            }
            return _extends({}, nextState, sortedInsert(nextState, action.item, action.sort));

        case RECEIVE:
            {
                var _data2 = action.list.filter(action.filter).sort(action.sort);
                return _extends({}, state, {
                    data: _data2,
                    indexOf: _lodash2.default.fromPairs(_data2.map(function (item, index) {
                        return [item.id, index];
                    }))
                });
            }

        default:
            return state;
    }
}

function updateFilter(list) {
    var filter = arguments.length <= 1 || arguments[1] === undefined ? defaultFilter : arguments[1];
    var sort = arguments.length <= 2 || arguments[2] === undefined ? defaultSort : arguments[2];

    return { type: UPDATE_FILTER, list: list, filter: filter, sort: sort };
}

function updateSort() {
    var sort = arguments.length <= 0 || arguments[0] === undefined ? defaultSort : arguments[0];

    return { type: UPDATE_SORT, sort: sort };
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
    var index = sortedIndex(state.data, item, sort);
    var data = [].concat(_toConsumableArray(state.data));
    var indexOf = _extends({}, state.indexOf);

    data.splice(index, 0, item);
    for (var i = data.length - 1; i >= index; i--) {
        indexOf[data[i].id] = i;
    }

    return { data: data, indexOf: indexOf };
}

function sortedRemove(state, id) {
    var index = state.indexOf[id];
    var data = [].concat(_toConsumableArray(state.data));
    var indexOf = _extends({}, state.indexOf, _defineProperty({}, id, null));

    data.splice(index, 1);
    for (var i = data.length - 1; i >= index; i--) {
        indexOf[data[i].id] = i;
    }

    return { data: data, indexOf: indexOf };
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

},{"lodash":"lodash"}],60:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.MESSAGE = exports.ERROR = exports.DISCONNECTED = exports.DISCONNECT = exports.CONNECTED = exports.CONNECT = exports.SYM_SOCKET = exports.CMD_RESET = exports.CMD_REMOVE = exports.CMD_UPDATE = exports.CMD_ADD = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

exports.default = reduce;
exports.connect = connect;
exports.disconnect = disconnect;
exports.onConnect = onConnect;
exports.onMessage = onMessage;
exports.onDisconnect = onDisconnect;
exports.onError = onError;

var _actions = require('../actions.js');

var _dispatcher = require('../dispatcher.js');

var _msgQueue = require('./msgQueue');

var msgQueueActions = _interopRequireWildcard(_msgQueue);

var _eventLog = require('./eventLog');

var eventLogActions = _interopRequireWildcard(_eventLog);

var _flows = require('./flows');

var flowsActions = _interopRequireWildcard(_flows);

var _settings = require('./settings');

var settingsActions = _interopRequireWildcard(_settings);

function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

var CMD_ADD = exports.CMD_ADD = 'add';
var CMD_UPDATE = exports.CMD_UPDATE = 'update';
var CMD_REMOVE = exports.CMD_REMOVE = 'remove';
var CMD_RESET = exports.CMD_RESET = 'reset';

var SYM_SOCKET = exports.SYM_SOCKET = Symbol('WEBSOCKET_SYM_SOCKET');

var CONNECT = exports.CONNECT = 'WEBSOCKET_CONNECT';
var CONNECTED = exports.CONNECTED = 'WEBSOCKET_CONNECTED';
var DISCONNECT = exports.DISCONNECT = 'WEBSOCKET_DISCONNECT';
var DISCONNECTED = exports.DISCONNECTED = 'WEBSOCKET_DISCONNECTED';
var ERROR = exports.ERROR = 'WEBSOCKET_ERROR';
var MESSAGE = exports.MESSAGE = 'WEBSOCKET_MESSAGE';

/* we may want to have an error message attribute here at some point */
var defaultState = { connected: false, socket: null };

function reduce() {
    var _extends3;

    var state = arguments.length <= 0 || arguments[0] === undefined ? defaultState : arguments[0];
    var action = arguments[1];

    switch (action.type) {

        case CONNECT:
            return _extends({}, state, _defineProperty({}, SYM_SOCKET, action.socket));

        case CONNECTED:
            return _extends({}, state, { connected: true });

        case DISCONNECT:
            return _extends({}, state, { connected: false });

        case DISCONNECTED:
            return _extends({}, state, (_extends3 = {}, _defineProperty(_extends3, SYM_SOCKET, null), _defineProperty(_extends3, 'connected', false), _extends3));

        default:
            return state;
    }
}

function connect() {
    return function (dispatch) {
        var socket = new WebSocket(location.origin.replace('http', 'ws') + '/updates');

        socket.addEventListener('open', function () {
            return dispatch(onConnect());
        });
        socket.addEventListener('close', function () {
            return dispatch(onDisconnect());
        });
        socket.addEventListener('message', function (msg) {
            return dispatch(onMessage(JSON.parse(msg.data)));
        });
        socket.addEventListener('error', function (error) {
            return dispatch(onError(error));
        });

        dispatch({ type: CONNECT, socket: socket });
    };
}

function disconnect() {
    return function (dispatch, getState) {
        getState().settings[SYM_SOCKET].close();
        dispatch({ type: DISCONNECT });
    };
}

function onConnect() {
    // workaround to make sure that our state is already available.
    return function (dispatch) {
        dispatch({ type: CONNECTED });
        dispatch(settingsActions.fetchData());
        dispatch(flowsActions.fetchFlows());
        dispatch(eventLogActions.fetchData());
    };
}

function onMessage(msg) {
    return msgQueueActions.handleWsMsg(msg);
}

function onDisconnect() {
    return function (dispatch) {
        dispatch(eventLogActions.add('WebSocket connection closed.'));
        dispatch({ type: DISCONNECTED });
    };
}

function onError(error) {
    // @todo let event log subscribe WebSocketActions.ERROR
    return function (dispatch) {
        dispatch(eventLogActions.add('WebSocket connection error.'));
        dispatch({ type: ERROR, error: error });
    };
}

},{"../actions.js":2,"../dispatcher.js":46,"./eventLog":48,"./flows":50,"./msgQueue":52,"./settings":53}],61:[function(require,module,exports){
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

},{"../flow/utils.js":62}],62:[function(require,module,exports){
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

},{"lodash":"lodash"}],63:[function(require,module,exports){
'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
exports.pure = exports.formatTimeStamp = exports.formatTimeDelta = exports.formatSize = exports.Key = undefined;

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _typeof = typeof Symbol === "function" && typeof Symbol.iterator === "symbol" ? function (obj) { return typeof obj; } : function (obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol ? "symbol" : typeof obj; };

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

function getDiff(obj1, obj2) {
    var result = _extends({}, obj2);
    for (var key in obj1) {
        if (_lodash2.default.isEqual(obj2[key], obj1[key])) result[key] = undefined;else if (!(Array.isArray(obj2[key]) && Array.isArray(obj1[key])) && _typeof(obj2[key]) == 'object' && _typeof(obj1[key]) == 'object') result[key] = getDiff(obj1[key], obj2[key]);
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

},{"lodash":"lodash","react":"react","shallowequal":"shallowequal"}]},{},[3])


//# sourceMappingURL=app.js.map
