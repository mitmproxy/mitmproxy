// http://blog.vjeux.com/2013/javascript/scroll-position-with-react.html (also contains inverse example)
var AutoScrollMixin = {
    componentWillUpdate: function () {
        var node = this.getDOMNode();
        this._shouldScrollBottom = node.scrollTop + node.clientHeight === node.scrollHeight;
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

var Key = {
    UP: 38,
    DOWN: 40,
    PAGE_UP: 33,
    PAGE_DOWN: 34,
    LEFT: 37,
    RIGHT: 39,
    ENTER: 13,
    ESC: 27,
    TAB: 9,
    SPACE: 32,
    J: 74,
    K: 75,
    H: 72,
    L: 76
};

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
    var index = this.callbacks.indexOf(f);
    if (index >= 0) {
        this.callbacks.splice(this.callbacks.indexOf(f), 1);
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

var ActionTypes = {
    //Settings
    UPDATE_SETTINGS: "update_settings",

    //EventLog
    ADD_EVENT: "add_event",

    //Flow
    ADD_FLOW: "add_flow",
    UPDATE_FLOW: "update_flow",
};

var SettingsActions = {
    update: function (settings) {
        settings = _.merge({}, SettingsStore.getAll(), settings);
        //TODO: Update server.

        //Facebook Flux: We do an optimistic update on the client already.
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.UPDATE_SETTINGS,
            settings: settings
        });
    }
};

var event_id = 0;
var EventLogActions = {
    add_event: function (message) {
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.ADD_EVENT,
            data: {
                message: message,
                level: "web",
                id: "viewAction-" + event_id++
            }
        });
    }
};
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

function _SettingsStore() {
    EventEmitter.call(this);

    //FIXME: What do we do if we haven't requested anything from the server yet?
    this.settings = {
        version: "0.12",
        showEventLog: true,
        mode: "transparent",
    };
}
_.extend(_SettingsStore.prototype, EventEmitter.prototype, {
    getAll: function () {
        return this.settings;
    },
    handle: function (action) {
        switch (action.type) {
            case ActionTypes.UPDATE_SETTINGS:
                this.settings = action.settings;
                this.emit("change");
                break;
            default:
                return;
        }
    }
});

var SettingsStore = new _SettingsStore();
AppDispatcher.register(SettingsStore.handle.bind(SettingsStore));

//
// We have an EventLogView and an EventLogStore:
// The basic architecture is that one can request views on the event log
// from the store, which returns a view object and then deals with getting the data required for the view.
// The view object is accessed by React components and distributes updates etc.
//
// See also: components/EventLog.react.js
function EventLogView(store, live) {
    EventEmitter.call(this);
    this._store = store;
    this.live = live;
    this.log = [];

    this.add = this.add.bind(this);

    if (live) {
        this._store.addListener(ActionTypes.ADD_EVENT, this.add);
    }
}
_.extend(EventLogView.prototype, EventEmitter.prototype, {
    close: function () {
        this._store.removeListener(ActionTypes.ADD_EVENT, this.add);
    },
    getAll: function () {
        return this.log;
    },
    add: function (entry) {
        this.log.push(entry);
        if (this.log.length > 200) {
            this.log.shift();
        }
        this.emit("change");
    },
    add_bulk: function (messages) {
        var log = messages;
        var last_id = log[log.length - 1].id;
        var to_add = _.filter(this.log, function (entry) {
            return entry.id > last_id;
        });
        this.log = log.concat(to_add);
        this.emit("change");
    }
});


function _EventLogStore() {
    EventEmitter.call(this);
}
_.extend(_EventLogStore.prototype, EventEmitter.prototype, {
    getView: function (since) {
        var view = new EventLogView(this, !since);
        return view;
        /*
         //TODO: Really do bulk retrieval of last messages.
         window.setTimeout(function () {
         view.add_bulk([
         {
         id: 1,
         message: "Hello World"
         },
         {
         id: 2,
         message: "I was already transmitted as an event."
         }
         ]);
         }, 100);

         var id = 2;
         view.add({
         id: id++,
         message: "I was already transmitted as an event."
         });
         view.add({
         id: id++,
         message: "I was only transmitted as an event before the bulk was added.."
         });
         window.setInterval(function () {
         view.add({
         id: id++,
         message: "."
         });
         }, 1000);
         return view;
         */
    },
    handle: function (action) {
        switch (action.type) {
            case ActionTypes.ADD_EVENT:
                this.emit(ActionTypes.ADD_EVENT, action.data);
                break;
            default:
                return;
        }
    }
});


var EventLogStore = new _EventLogStore();
AppDispatcher.register(EventLogStore.handle.bind(EventLogStore));
function FlowStore(endpoint) {
    this._views = [];
    this.reset();
}
_.extend(FlowStore.prototype, {
    add: function (flow) {
        this._pos_map[flow.id] = this._flow_list.length;
        this._flow_list.push(flow);
        for (var i = 0; i < this._views.length; i++) {
            this._views[i].add(flow);
        }
    },
    update: function (flow) {
        this._flow_list[this._pos_map[flow.id]] = flow;
        for (var i = 0; i < this._views.length; i++) {
            this._views[i].update(flow);
        }
    },
    remove: function (flow_id) {
        this._flow_list.splice(this._pos_map[flow_id], 1);
        this._build_map();
        for (var i = 0; i < this._views.length; i++) {
            this._views[i].remove(flow_id);
        }
    },
    reset: function (flows) {
        this._flow_list = flows || [];
        this._build_map();
        for (var i = 0; i < this._views.length; i++) {
            this._views[i].recalculate(this._flow_list);
        }
    },
    _build_map: function () {
        this._pos_map = {};
        for (var i = 0; i < this._flow_list.length; i++) {
            var flow = this._flow_list[i];
            this._pos_map[flow.id] = i;
        }
    },
    get: function (flow_id) {
        return this._flow_list[this._pos_map[flow_id]];
    }
});


function LiveFlowStore(endpoint) {
    FlowStore.call(this);
    this.updates_before_init = []; // (empty array is true in js)
    this.endpoint = endpoint || "/flows";
    this.conn = new Connection(this.endpoint + "/updates");
    this.conn.onopen = this._onopen.bind(this);
    this.conn.onmessage = function (e) {
        var message = JSON.parse(e.data);
        this.handle_update(message.type, message.data);
    }.bind(this);
}
_.extend(LiveFlowStore.prototype, FlowStore.prototype, {
    close: function () {
        this.conn.close();
    },
    add: function (flow) {
        // Make sure that deferred adds don't add an element twice.
        if (!this._pos_map[flow.id]) {
            FlowStore.prototype.add.call(this, flow);
        }
    },
    handle_update: function (type, data) {
        console.log("LiveFlowStore.handle_update", type, data);
        if (this.updates_before_init) {
            console.log("defer update", type, data);
            this.updates_before_init.push(arguments);
        } else {
            this[type](data);
        }
    },
    handle_fetch: function (data) {
        console.log("Flows fetched.");
        this.reset(data.flows);
        var updates = this.updates_before_init;
        this.updates_before_init = false;
        for (var i = 0; i < updates.length; i++) {
            this.handle_update.apply(this, updates[i]);
        }
    },
    _onopen: function () {
        //Update stream openend, fetch list of flows.
        console.log("Update Connection opened, fetching flows...");
        $.getJSON(this.endpoint, this.handle_fetch.bind(this));
    },
});

function SortByInsertionOrder() {
    this.i = 0;
    this.map = {};
    this.key = this.key.bind(this);
}
SortByInsertionOrder.prototype.key = function (flow) {
    if (!(flow.id in this.map)) {
        this.i++;
        this.map[flow.id] = this.i;
    }
    return this.map[flow.id];
};

var default_sort = (new SortByInsertionOrder()).key;

function FlowView(store, filt, sortfun) {
    EventEmitter.call(this);
    filt = filt || function (flow) {
        return true;
    };
    sortfun = sortfun || default_sort;

    this.store = store;
    this.store._views.push(this);
    this.recalculate(this.store._flow_list, filt, sortfun);
}

_.extend(FlowView.prototype, EventEmitter.prototype, {
    close: function () {
        this.store._views = _.without(this.store._views, this);
    },
    recalculate: function (flows, filt, sortfun) {
        if (filt) {
            this.filt = filt;
        }
        if (sortfun) {
            this.sortfun = sortfun;
        }

        //Ugly workaround: Call .sortfun() for each flow once in order,
        //so that SortByInsertionOrder make sense.
        var i = flows.length;
        while(i--){
            this.sortfun(flows[i]);
        }

        this.flows = flows.filter(this.filt);
        this.flows.sort(function (a, b) {
            return this.sortfun(b) - this.sortfun(a);
        }.bind(this));
        this.emit("recalculate");
    },
    add: function (flow) {
        if (this.filt(flow)) {
            var idx = _.sortedIndex(this.flows, flow, this.sortfun);
            if (idx === this.flows.length) { //happens often, .push is way faster.
                this.flows.push(flow);
            } else {
                this.flows.splice(idx, 0, flow);
            }
            this.emit("add", flow, idx);
        }
    },
    update: function (flow) {
        var idx;
        var i = this.flows.length;
        // Search from the back, we usually update the latest flows.
        while (i--) {
            if (this.flows[i].id === flow.id) {
                idx = i;
                break;
            }
        }

        if (idx === -1) { //not contained in list
            this.add(flow);
        } else if (!this.filt(flow)) {
            this.remove(flow.id);
        } else {
            if (this.sortfun(this.flows[idx]) !== this.sortfun(flow)) { //sortpos has changed
                this.remove(this.flows[idx]);
                this.add(flow);
            } else {
                this.flows[idx] = flow;
                this.emit("update", flow, idx);
            }
        }
    },
    remove: function (flow_id) {
        var i = this.flows.length;
        while (i--) {
            if (this.flows[i].id === flow_id) {
                this.flows.splice(i, 1);
                this.emit("remove", flow_id, i);
                break;
            }
        }
    }
});
function Connection(url) {
    if (url[0] != "/") {
        this.url = url;
    } else {
        this.url = location.origin.replace("http", "ws") + url;
    }
    var ws = new WebSocket(this.url);
    ws.onopen = function () {
        this.onopen.apply(this, arguments);
    }.bind(this);
    ws.onmessage = function () {
        this.onmessage.apply(this, arguments);
    }.bind(this);
    ws.onerror = function () {
        this.onerror.apply(this, arguments);
    }.bind(this);
    ws.onclose = function () {
        this.onclose.apply(this, arguments);
    }.bind(this);
    this.ws = ws;
}
Connection.prototype.onopen = function (open) {
    console.debug("onopen", this, arguments);
};
Connection.prototype.onmessage = function (message) {
    console.warn("onmessage (not implemented)", this, message.data);
};
Connection.prototype.onerror = function (error) {
    EventLogActions.add_event("WebSocket Connection Error.");
    console.debug("onerror", this, arguments);
};
Connection.prototype.onclose = function (close) {
    EventLogActions.add_event("WebSocket Connection closed.");
    console.debug("onclose", this, arguments);
};
Connection.prototype.close = function () {
    this.ws.close();
};
//React utils. For other utilities, see ../utils.js

var Splitter = React.createClass({displayName: 'Splitter',
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
var MainMenu = React.createClass({displayName: 'MainMenu',
    statics: {
        title: "Traffic",
        route: "flows"
    },
    toggleEventLog: function () {
        SettingsActions.update({
            showEventLog: !this.props.settings.showEventLog
        });
    },
    render: function () {
        return (
            React.createElement("div", null, 
                React.createElement("button", {className: "btn " + (this.props.settings.showEventLog ? "btn-primary" : "btn-default"), onClick: this.toggleEventLog}, 
                    React.createElement("i", {className: "fa fa-database"}), 
                "Display Event Log"
                )
            )
        );
    }
});


var ToolsMenu = React.createClass({displayName: 'ToolsMenu',
    statics: {
        title: "Tools",
        route: "flows"
    },
    render: function () {
        return React.createElement("div", null, "Tools Menu");
    }
});


var ReportsMenu = React.createClass({displayName: 'ReportsMenu',
    statics: {
        title: "Visualization",
        route: "reports"
    },
    render: function () {
        return React.createElement("div", null, "Reports Menu");
    }
});


var header_entries = [MainMenu, ToolsMenu, ReportsMenu];


var Header = React.createClass({displayName: 'Header',
    mixins: [ReactRouter.Navigation],
    getInitialState: function () {
        return {
            active: header_entries[0]
        };
    },
    handleClick: function (active, e) {
        e.preventDefault();
        this.transitionTo(active.route);
        this.setState({active: active});
    },
    handleFileClick: function () {
        console.log("File click");
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
                    React.createElement("a", {href: "#", className: "special", onClick: this.handleFileClick}, " File "), 
                    header
                ), 
                React.createElement("div", {className: "menu"}, 
                    React.createElement(this.state.active, {settings: this.props.settings})
                )
            )
        );
    }
});

var TLSColumn = React.createClass({displayName: 'TLSColumn',
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


var IconColumn = React.createClass({displayName: 'IconColumn',
    statics: {
        renderTitle: function () {
            return React.createElement("th", {key: "icon", className: "col-icon"});
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
        return React.createElement("td", {className: "col-icon"}, 
            React.createElement("div", {className: icon})
        );
    }
});

var PathColumn = React.createClass({displayName: 'PathColumn',
    statics: {
        renderTitle: function () {
            return React.createElement("th", {key: "path", className: "col-path"}, "Path");
        }
    },
    render: function () {
        var flow = this.props.flow;
        return React.createElement("td", {className: "col-path"}, flow.request.scheme + "://" + flow.request.host + flow.request.path);
    }
});


var MethodColumn = React.createClass({displayName: 'MethodColumn',
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


var StatusColumn = React.createClass({displayName: 'StatusColumn',
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


var SizeColumn = React.createClass({displayName: 'SizeColumn',
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
        var size = formatSize(total);
        return React.createElement("td", {className: "col-size"}, size);
    }
});


var TimeColumn = React.createClass({displayName: 'TimeColumn',
    statics: {
        renderTitle: function () {
            return React.createElement("th", {key: "time", className: "col-time"}, "Time");
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


var FlowRow = React.createClass({displayName: 'FlowRow',
    render: function () {
        var flow = this.props.flow;
        var columns = this.props.columns.map(function (Column) {
            return React.createElement(Column, {key: Column.displayName, flow: flow});
        }.bind(this));
        var className = "";
        if (this.props.selected) {
            className += "selected";
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

var FlowTableHead = React.createClass({displayName: 'FlowTableHead',
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

var FlowTable = React.createClass({displayName: 'FlowTable',
    mixins: [StickyHeadMixin, AutoScrollMixin],
    getInitialState: function () {
        return {
            columns: all_columns,
            start: 0,
            stop: 0
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
    componentDidMount: function () {
        this.onScroll();
    },
    onScroll: function () {
        this.adjustHead();

        var viewport = this.getDOMNode();
        var top = viewport.scrollTop;
        var height = viewport.offsetHeight;
        var start = Math.floor(top / ROW_HEIGHT);
        var stop = start + Math.ceil(height / ROW_HEIGHT);
        this.setState({
            start: start,
            stop: stop
        });
    },
    onChange: function () {
        console.log("onChange");
        this.forceUpdate();
    },
    scrollIntoView: function (flow) {
        // Now comes the fun part: Scroll the flow into the view.
        var viewport = this.getDOMNode();
        var flowNode = this.refs.body.refs[flow.id].getDOMNode();
        var viewport_top = viewport.scrollTop;
        var viewport_bottom = viewport_top + viewport.offsetHeight;
        var flowNode_top = flowNode.offsetTop;
        var flowNode_bottom = flowNode_top + flowNode.offsetHeight;

        // Account for pinned thead by pretending that the flowNode starts
        // -thead_height pixel earlier.
        flowNode_top -= this.refs.body.getDOMNode().offsetTop;

        if (flowNode_top < viewport_top) {
            viewport.scrollTop = flowNode_top;
        } else if (flowNode_bottom > viewport_bottom) {
            viewport.scrollTop = flowNode_bottom - viewport.offsetHeight;
        }
    },
    render: function () {
        var space_top = 0, space_bottom = 0, fix_nth_row = null;
        var rows = [];
        if (this.props.view) {
            var flows = this.props.view.flows;
            var max = Math.min(flows.length, this.state.stop);
            console.log("render", this.props.view.flows.length, this.state.start, max - this.state.start, flows.length - this.state.stop);

            for (var i = this.state.start; i < max; i++) {
                var flow = flows[i];
                var selected = (flow === this.props.selected);
                rows.push(
                    React.createElement(FlowRow, {key: flow.id, 
                        ref: flow.id, 
                        flow: flow, 
                        columns: this.state.columns, 
                        selected: selected, 
                        selectFlow: this.props.selectFlow}
                    )
                );
            }

            space_top = this.state.start * ROW_HEIGHT;
            space_bottom = Math.max(0, flows.length - this.state.stop) * ROW_HEIGHT;
            if(this.state.start % 2 === 1){
                fix_nth_row = React.createElement("tr", null);
            }
        }


        return (
            React.createElement("div", {className: "flow-table", onScroll: this.onScroll}, 
                React.createElement("table", null, 
                    React.createElement(FlowTableHead, {ref: "head", 
                        columns: this.state.columns}), 
                    React.createElement("tbody", null, 
                        React.createElement("tr", {style: {height: space_top}}), 
                        fix_nth_row, 
                        rows, 
                        React.createElement("tr", {style: {height: space_bottom}})
                    )
                )
            )
        );
    }
});

var FlowDetailNav = React.createClass({displayName: 'FlowDetailNav',
    render: function () {

        var items = this.props.tabs.map(function (e) {
            var str = e.charAt(0).toUpperCase() + e.slice(1);
            var className = this.props.active === e ? "active" : "";
            var onClick = function (e) {
                this.props.selectTab(e);
                e.preventDefault();
            }.bind(this);
            return React.createElement("a", {key: e, 
                href: "#", 
                className: className, 
                onClick: onClick}, str);
        }.bind(this));
        return (
            React.createElement("nav", {ref: "head", className: "nav-tabs nav-tabs-sm"}, 
                items
            )
        );
    }
});

var Headers = React.createClass({displayName: 'Headers',
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

var FlowDetailRequest = React.createClass({displayName: 'FlowDetailRequest',
    render: function () {
        var flow = this.props.flow;
        var first_line = [
            flow.request.method,
            RequestUtils.pretty_url(flow.request),
            "HTTP/" + flow.response.httpversion.join(".")
        ].join(" ");
        var content = null;
        if (flow.request.contentLength > 0) {
            content = "Request Content Size: " + formatSize(flow.request.contentLength);
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

var FlowDetailResponse = React.createClass({displayName: 'FlowDetailResponse',
    render: function () {
        var flow = this.props.flow;
        var first_line = [
            "HTTP/" + flow.response.httpversion.join("."),
            flow.response.code,
            flow.response.msg
        ].join(" ");
        var content = null;
        if (flow.response.contentLength > 0) {
            content = "Response Content Size: " + formatSize(flow.response.contentLength);
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

var TimeStamp = React.createClass({displayName: 'TimeStamp',
    render: function () {

        if (!this.props.t) {
            //should be return null, but that triggers a React bug.
            return React.createElement("tr", null);
        }

        var ts = (new Date(this.props.t * 1000)).toISOString();
        ts = ts.replace("T", " ").replace("Z", "");

        var delta;
        if (this.props.deltaTo) {
            delta = formatTimeDelta(1000 * (this.props.t - this.props.deltaTo));
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

var ConnectionInfo = React.createClass({displayName: 'ConnectionInfo',

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

var CertificateInfo = React.createClass({displayName: 'CertificateInfo',
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

var Timing = React.createClass({displayName: 'Timing',
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

var FlowDetailConnectionInfo = React.createClass({displayName: 'FlowDetailConnectionInfo',
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

var tabs = {
    request: FlowDetailRequest,
    response: FlowDetailResponse,
    details: FlowDetailConnectionInfo
};

var FlowDetail = React.createClass({displayName: 'FlowDetail',
    getDefaultProps: function () {
        return {
            tabs: ["request", "response", "details"]
        };
    },
    mixins: [StickyHeadMixin, ReactRouter.Navigation, ReactRouter.State],
    nextTab: function (i) {
        var currentIndex = this.props.tabs.indexOf(this.props.active);
        // JS modulo operator doesn't correct negative numbers, make sure that we are positive.
        var nextIndex = (currentIndex + i + this.props.tabs.length) % this.props.tabs.length;
        this.selectTab(this.props.tabs[nextIndex]);
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
        var flow = JSON.stringify(this.props.flow, null, 2);
        var Tab = tabs[this.props.active];
        return (
            React.createElement("div", {className: "flow-detail", onScroll: this.adjustHead}, 
                React.createElement(FlowDetailNav, {ref: "head", 
                    tabs: this.props.tabs, 
                    active: this.props.active, 
                    selectTab: this.selectTab}), 
                React.createElement(Tab, {flow: this.props.flow})
            )
        );
    }
});
var MainView = React.createClass({displayName: 'MainView',
    mixins: [ReactRouter.Navigation, ReactRouter.State],
    getInitialState: function () {
        return {
            flows: []
        };
    },
    componentWillReceiveProps: function (nextProps) {
        if (nextProps.flowStore !== this.props.flowStore) {
            this.closeView();
            this.openView(nextProps.flowStore);
        }
    },
    openView: function (store) {
        var view = new FlowView(store);
        this.setState({
            view: view
        });
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
            console.log("TODO: Scroll into view");
            //this.refs.flowTable.scrollIntoView(flow);
        } else {
            this.replaceWith("flows");
        }
    },
    selectFlowRelative: function (shift) {
        var flows = this.state.view.flows;
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
            default:
                console.debug("keydown", e.keyCode);
                return;
        }
        e.preventDefault();
    },
    render: function () {
        var selected = this.props.flowStore.get(this.getParams().flowId);

        var details;
        if (selected) {
            details = (
                React.createElement(FlowDetail, {ref: "flowDetails", 
                    flow: selected, 
                    active: this.getParams().detailTab})
            );
        } else {
            details = null;
        }

        return (
            React.createElement("div", {className: "main-view", onKeyDown: this.onKeyDown, tabIndex: "0"}, 
                React.createElement(FlowTable, {ref: "flowTable", 
                    view: this.state.view, 
                    selectFlow: this.selectFlow, 
                    selected: selected}), 
                 details ? React.createElement(Splitter, null) : null, 
                details
            )
        );
    }
});
var LogMessage = React.createClass({displayName: 'LogMessage',
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

var EventLogContents = React.createClass({displayName: 'EventLogContents',
    mixins: [AutoScrollMixin],
    getInitialState: function () {
        return {
            log: []
        };
    },
    componentDidMount: function () {
        this.log = EventLogStore.getView();
        this.log.addListener("change", this.onEventLogChange);
    },
    componentWillUnmount: function () {
        this.log.removeListener("change", this.onEventLogChange);
        this.log.close();
    },
    onEventLogChange: function () {
        this.setState({
            log: this.log.getAll()
        });
    },
    render: function () {
        var messages = this.state.log.map(function (row) {
            if (!this.props.filter[row.level]) {
                return null;
            }
            return React.createElement(LogMessage, {key: row.id, entry: row});
        }.bind(this));
        return React.createElement("pre", null, messages);
    }
});

var ToggleFilter = React.createClass({displayName: 'ToggleFilter',
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

var EventLog = React.createClass({displayName: 'EventLog',
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
        SettingsActions.update({
            showEventLog: false
        });
    },
    toggleLevel: function (level) {
        var filter = this.state.filter;
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
                React.createElement(EventLogContents, {filter: this.state.filter})
            )
        );
    }
});
var Footer = React.createClass({displayName: 'Footer',
    render: function () {
        var mode = this.props.settings.mode;
        return (
            React.createElement("footer", null, 
                mode != "regular" ? React.createElement("span", {className: "label label-success"}, mode, " mode") : null
            )
        );
    }
});

//TODO: Move out of here, just a stub.
var Reports = React.createClass({displayName: 'Reports',
    render: function () {
        return React.createElement("div", null, "ReportEditor");
    }
});


var ProxyAppMain = React.createClass({displayName: 'ProxyAppMain',
    getInitialState: function () {
        return {
            settings: SettingsStore.getAll(),
            flowStore: new LiveFlowStore()
        };
    },
    componentDidMount: function () {
        SettingsStore.addListener("change", this.onSettingsChange);
    },
    componentWillUnmount: function () {
        SettingsStore.removeListener("change", this.onSettingsChange);
    },
    onSettingsChange: function () {
        this.setState({settings: SettingsStore.getAll()});
    },
    render: function () {
        return (
            React.createElement("div", {id: "container"}, 
                React.createElement(Header, {settings: this.state.settings}), 
                React.createElement(RouteHandler, {settings: this.state.settings, flowStore: this.state.flowStore}), 
                this.state.settings.showEventLog ? React.createElement(Splitter, {axis: "y"}) : null, 
                this.state.settings.showEventLog ? React.createElement(EventLog, null) : null, 
                React.createElement(Footer, {settings: this.state.settings})
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
$(function () {
    ReactRouter.run(routes, function (Handler) {
        React.render(React.createElement(Handler, null), document.body);
    });
    var UpdateConnection = new Connection("/updates");
    UpdateConnection.onmessage = function (message) {
        var m = JSON.parse(message.data);
        AppDispatcher.dispatchServerAction(m);
    };
});
//# sourceMappingURL=app.js.map