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
    var i=0;
    while (Math.abs(size) >= 1024 && i < prefix.length-1) {
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
    for(var i = 0; i < this.callbacks.length; i++){
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
    add_event: function(message){
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.ADD_EVENT,
            data: {
                message: message,
                level: "web",
                id: "viewAction-"+event_id++
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
EventEmitter.prototype.addListener = function (event, f) {
    this.listeners[event] = this.listeners[event] || [];
    this.listeners[event].push(f);
};
EventEmitter.prototype.removeListener = function (event, f) {
    if (!(event in this.listeners)) {
        return false;
    }
    var index = this.listeners[event].indexOf(f);
    if (index >= 0) {
        this.listeners[event].splice(index, 1);
    }
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
        if(this.log.length > 200){
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
    open_view: function (filt, sort) {
        var view = new FlowView(this._flow_list, filt, sort);
        this._views.push(view);
        return view;
    },
    close_view: function (view) {
        this._views = _.without(this._views, view);
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

function FlowView(flows, filt, sort) {
    EventEmitter.call(this);
    filt = filt || function (flow) {
        return true;
    };
    sort = sort || default_sort;
    this.recalculate(flows, filt, sort);
}

_.extend(FlowView.prototype, EventEmitter.prototype, {
    recalculate: function (flows, filt, sort) {
        if (filt) {
            this.filt = filt;
        }
        if (sort) {
            this.sort = sort;
        }
        this.flows = flows.filter(this.filt);
        this.flows.sort(function (a, b) {
            return this.sort(a) - this.sort(b);
        }.bind(this));
        this.emit("recalculate");
    },
    add: function (flow) {
        if (this.filt(flow)) {
            var idx = _.sortedIndex(this.flows, flow, this.sort);
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
            if (this.sort(this.flows[idx]) !== this.sort(flow)) { //sortpos has changed
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
    if(url[0] != "/"){
        this.url = url;
    } else {
        this.url = location.origin.replace("http", "ws") + url;
    }
    var ws = new WebSocket(this.url);
    ws.onopen = function(){
        this.onopen.apply(this, arguments);
    }.bind(this);
    ws.onmessage = function(){
        this.onmessage.apply(this, arguments);
    }.bind(this);
    ws.onerror = function(){
        this.onerror.apply(this, arguments);
    }.bind(this);
    ws.onclose = function(){
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
Connection.prototype.close = function(){
    this.ws.close();
};
/** @jsx React.DOM */

//React utils. For other utilities, see ../utils.js

var Splitter = React.createClass({displayName: 'Splitter',
    getDefaultProps: function () {
        return {
            axis: "x"
        };
    },
    getInitialState: function(){
        return {
            applied: false,
            startX: false,
            startY: false
        };
    },
    onMouseDown: function(e){
        this.setState({
            startX: e.pageX,
            startY: e.pageY
        });
        window.addEventListener("mousemove",this.onMouseMove);
        window.addEventListener("mouseup",this.onMouseUp);
        // Occasionally, only a dragEnd event is triggered, but no mouseUp.
        window.addEventListener("dragend",this.onDragEnd);
    },
    onDragEnd: function(){
        this.getDOMNode().style.transform="";
        window.removeEventListener("dragend",this.onDragEnd);
        window.removeEventListener("mouseup",this.onMouseUp);
        window.removeEventListener("mousemove",this.onMouseMove);
    },
    onMouseUp: function(e){
        this.onDragEnd();

        var node = this.getDOMNode();
        var prev = node.previousElementSibling;
        var next = node.nextElementSibling;

        var dX = e.pageX-this.state.startX;
        var dY = e.pageY-this.state.startY;
        var flexBasis;
        if(this.props.axis === "x"){
            flexBasis = prev.offsetWidth + dX;
        } else {
            flexBasis = prev.offsetHeight + dY;
        }

        prev.style.flex = "0 0 "+Math.max(0, flexBasis)+"px";   
        next.style.flex = "1 1 auto";

        this.setState({
            applied: true
        });
    },
    onMouseMove: function(e){
        var dX = 0, dY = 0;
        if(this.props.axis === "x"){
            dX = e.pageX-this.state.startX;
        } else {
            dY = e.pageY-this.state.startY;
        }
        this.getDOMNode().style.transform = "translate("+dX+"px,"+dY+"px)";
    },
    reset: function(willUnmount) {
        if (!this.state.applied) {
            return;
        }
        var node = this.getDOMNode();
        var prev = node.previousElementSibling;
        var next = node.nextElementSibling;
        
        prev.style.flex = "";
        next.style.flex = "";

        if(!willUnmount){
            this.setState({
                applied: false
            });
        }

    },
    componentWillUnmount: function(){
        this.reset(true);
    },
    render: function(){
        var className = "splitter";
        if(this.props.axis === "x"){
            className += " splitter-x";
        } else {
            className += " splitter-y";
        }
        return (
            React.DOM.div({className: className}, 
                React.DOM.div({onMouseDown: this.onMouseDown, draggable: "true"})
            )
        );
    }
});
/** @jsx React.DOM */

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
            React.DOM.div(null, 
                React.DOM.button({className: "btn " + (this.props.settings.showEventLog ? "btn-primary" : "btn-default"), onClick: this.toggleEventLog}, 
                React.DOM.i({className: "fa fa-database"}), " Display Event Log"
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
        return React.DOM.div(null, "Tools Menu");
    }
});


var ReportsMenu = React.createClass({displayName: 'ReportsMenu',
    statics: {
        title: "Visualization",
        route: "reports"
    },
    render: function () {
        return React.DOM.div(null, "Reports Menu");
    }
});


var header_entries = [MainMenu, ToolsMenu, ReportsMenu];


var Header = React.createClass({displayName: 'Header',
    getInitialState: function () {
        return {
            active: header_entries[0]
        };
    },
    handleClick: function (active) {
        ReactRouter.transitionTo(active.route);
        this.setState({active: active});
        return false;
    },
    handleFileClick: function () {
        console.log("File click");
    },
    render: function () {
        var header = header_entries.map(function(entry, i){
            var classes = React.addons.classSet({
                active: entry == this.state.active
            });
            return (
                React.DOM.a({key: i, 
                   href: "#", 
                   className: classes, 
                   onClick: this.handleClick.bind(this, entry)
                }, 
                     entry.title
                )
                );
        }.bind(this));
        
        return (
            React.DOM.header(null, 
                React.DOM.div({className: "title-bar"}, 
                    "mitmproxy ",  this.props.settings.version
                ), 
                React.DOM.nav({className: "nav-tabs nav-tabs-lg"}, 
                    React.DOM.a({href: "#", className: "special", onClick: this.handleFileClick}, " File "), 
                    header
                ), 
                React.DOM.div({className: "menu"}, 
                    this.state.active({settings: this.props.settings})
                )
            )
            );
    }
});

/** @jsx React.DOM */


var TLSColumn = React.createClass({displayName: 'TLSColumn',
    statics: {
        renderTitle: function(){
            return React.DOM.th({key: "tls", className: "col-tls"});
        }
    },
    render: function(){
        var flow = this.props.flow;
        var ssl = (flow.request.scheme == "https");
        var classes;
        if(ssl){
            classes = "col-tls col-tls-https";
        } else {
            classes = "col-tls col-tls-http";
        }
        return React.DOM.td({className: classes});
    }
});


var IconColumn = React.createClass({displayName: 'IconColumn',
    statics: {
        renderTitle: function(){
            return React.DOM.th({key: "icon", className: "col-icon"});
        }
    },
    render: function(){
        var flow = this.props.flow;

        var icon;
        if(flow.response){
            var contentType = ResponseUtils.getContentType(flow.response);

            //TODO: We should assign a type to the flow somewhere else.
            if(flow.response.code == 304) {
                icon = "resource-icon-not-modified";
            } else if(300 <= flow.response.code && flow.response.code < 400) {
                icon = "resource-icon-redirect";
            } else if(contentType && contentType.indexOf("image") >= 0) {
                icon = "resource-icon-image";
            } else if (contentType && contentType.indexOf("javascript") >= 0) {
                icon = "resource-icon-js";
            } else if (contentType && contentType.indexOf("css") >= 0) {
                icon = "resource-icon-css";
            } else if (contentType && contentType.indexOf("html") >= 0) {
                icon = "resource-icon-document";
            }
        }
        if(!icon){
            icon = "resource-icon-plain";
        }


        icon += " resource-icon";
        return React.DOM.td({className: "col-icon"}, React.DOM.div({className: icon}));
    }
});

var PathColumn = React.createClass({displayName: 'PathColumn',
    statics: {
        renderTitle: function(){
            return React.DOM.th({key: "path", className: "col-path"}, "Path");
        }
    },
    render: function(){
        var flow = this.props.flow;
        return React.DOM.td({className: "col-path"}, flow.request.scheme + "://" + flow.request.host + flow.request.path);
    }
});


var MethodColumn = React.createClass({displayName: 'MethodColumn',
    statics: {
        renderTitle: function(){
            return React.DOM.th({key: "method", className: "col-method"}, "Method");
        }
    },
    render: function(){
        var flow = this.props.flow;
        return React.DOM.td({className: "col-method"}, flow.request.method);
    }
});


var StatusColumn = React.createClass({displayName: 'StatusColumn',
    statics: {
        renderTitle: function(){
            return React.DOM.th({key: "status", className: "col-status"}, "Status");
        }
    },
    render: function(){
        var flow = this.props.flow;
        var status;
        if(flow.response){
            status = flow.response.code;
        } else {
            status = null;
        }
        return React.DOM.td({className: "col-status"}, status);
    }
});


var SizeColumn = React.createClass({displayName: 'SizeColumn',
    statics: {
        renderTitle: function(){
            return React.DOM.th({key: "size", className: "col-size"}, "Size");
        }
    },
    render: function(){
        var flow = this.props.flow;

        var total = flow.request.contentLength;
        if(flow.response){
            total += flow.response.contentLength || 0;
        }
        var size = formatSize(total);
        return React.DOM.td({className: "col-size"}, size);
    }
});


var TimeColumn = React.createClass({displayName: 'TimeColumn',
    statics: {
        renderTitle: function(){
            return React.DOM.th({key: "time", className: "col-time"}, "Time");
        }
    },
    render: function(){
        var flow = this.props.flow;
        var time;
        if(flow.response){
            time = formatTimeDelta(1000 * (flow.response.timestamp_end - flow.request.timestamp_start));
        } else {
            time = "...";
        }
        return React.DOM.td({className: "col-time"}, time);
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


/** @jsx React.DOM */

var FlowRow = React.createClass({displayName: 'FlowRow',
    render: function(){
        var flow = this.props.flow;
        var columns = this.props.columns.map(function(column){
            return column({key: column.displayName, flow: flow});
        }.bind(this));
        var className = "";
        if(this.props.selected){
            className += "selected";
        }
        return (
            React.DOM.tr({className: className, onClick: this.props.selectFlow.bind(null, flow)}, 
                columns
            ));
    },
    shouldComponentUpdate: function(nextProps){
        var isEqual = (
            this.props.columns.length === nextProps.columns.length && 
            this.props.selected === nextProps.selected &&
            this.props.flow.response === nextProps.flow.response);
        return !isEqual;
    }
});

var FlowTableHead = React.createClass({displayName: 'FlowTableHead',
    render: function(){
        var columns = this.props.columns.map(function(column){
            return column.renderTitle();
        }.bind(this));
        return React.DOM.thead(null, React.DOM.tr(null, columns));
    }
});

var FlowTableBody = React.createClass({displayName: 'FlowTableBody',
    render: function(){
        var rows = this.props.flows.map(function(flow){
            var selected = (flow == this.props.selected);
            return FlowRow({key: flow.id, 
                            ref: flow.id, 
                            flow: flow, 
                            columns: this.props.columns, 
                            selected: selected, 
                            selectFlow: this.props.selectFlow}
                            );
        }.bind(this));
        return React.DOM.tbody(null, rows);
    }
});


var FlowTable = React.createClass({displayName: 'FlowTable',
    mixins: [StickyHeadMixin, AutoScrollMixin],
    getInitialState: function () {
        return {
            columns: all_columns
        };
    },
    scrollIntoView: function(flow){
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

        if(flowNode_top < viewport_top){
            viewport.scrollTop = flowNode_top;
        } else if(flowNode_bottom > viewport_bottom) {
            viewport.scrollTop = flowNode_bottom - viewport.offsetHeight;
        }
    },
    render: function () {
        return (
            React.DOM.div({className: "flow-table", onScroll: this.adjustHead}, 
                React.DOM.table(null, 
                    FlowTableHead({ref: "head", 
                                   columns: this.state.columns}), 
                    FlowTableBody({ref: "body", 
                                   flows: this.props.flows, 
                                   selected: this.props.selected, 
                                   selectFlow: this.props.selectFlow, 
                                   columns: this.state.columns})
                )
            )
            );
    }
});

/** @jsx React.DOM */

var FlowDetailNav = React.createClass({displayName: 'FlowDetailNav',
    render: function(){

        var items = this.props.tabs.map(function(e){
            var str = e.charAt(0).toUpperCase() + e.slice(1);
            var className = this.props.active === e ? "active" : "";
            var onClick = function(){
                this.props.selectTab(e);
                return false;
            }.bind(this);
            return React.DOM.a({key: e, 
                      href: "#", 
                      className: className, 
                      onClick: onClick}, str);
        }.bind(this));
        return (
            React.DOM.nav({ref: "head", className: "nav-tabs nav-tabs-sm"}, 
                items
            )
        );
    } 
});

var Headers = React.createClass({displayName: 'Headers',
    render: function(){
        var rows = this.props.message.headers.map(function(header, i){
            return (
                React.DOM.tr({key: i}, 
                    React.DOM.td({className: "header-name"}, header[0]+":"), 
                    React.DOM.td({className: "header-value"}, header[1])
                )
            );
        });
        return (
            React.DOM.table({className: "header-table"}, 
                React.DOM.tbody(null, 
                    rows
                )
            )
        );
    }
});

var FlowDetailRequest = React.createClass({displayName: 'FlowDetailRequest',
    render: function(){
        var flow = this.props.flow;
        var first_line = [
                flow.request.method,
                RequestUtils.pretty_url(flow.request),
                "HTTP/"+ flow.response.httpversion.join(".")
            ].join(" ");
        var content = null;
        if(flow.request.contentLength > 0){
            content = "Request Content Size: "+ formatSize(flow.request.contentLength);
        } else {
            content = React.DOM.div({className: "alert alert-info"}, "No Content");
        }

        //TODO: Styling

        return (
            React.DOM.section(null, 
                React.DOM.div({className: "first-line"}, first_line ), 
                Headers({message: flow.request}), 
                React.DOM.hr(null), 
                content
            )
        );
    }
});

var FlowDetailResponse = React.createClass({displayName: 'FlowDetailResponse',
    render: function(){
        var flow = this.props.flow;
        var first_line = [
                "HTTP/"+ flow.response.httpversion.join("."),
                flow.response.code,
                flow.response.msg
            ].join(" ");
        var content = null;
        if(flow.response.contentLength > 0){
            content = "Response Content Size: "+ formatSize(flow.response.contentLength);
        } else {
            content = React.DOM.div({className: "alert alert-info"}, "No Content");
        }

        //TODO: Styling

        return (
            React.DOM.section(null, 
                React.DOM.div({className: "first-line"}, first_line ), 
                Headers({message: flow.response}), 
                React.DOM.hr(null), 
                content
            )
        );
    }
});

var TimeStamp = React.createClass({displayName: 'TimeStamp',
    render: function() {

        if(!this.props.t){
            //should be return null, but that triggers a React bug.
            return React.DOM.tr(null);
        }

        var ts = (new Date(this.props.t * 1000)).toISOString();
        ts = ts.replace("T", " ").replace("Z","");

        var delta;
        if(this.props.deltaTo){
            delta = formatTimeDelta(1000 * (this.props.t-this.props.deltaTo));
            delta = React.DOM.span({className: "text-muted"}, "(" + delta + ")");
        } else {
            delta = null;
        }

        return React.DOM.tr(null, React.DOM.td(null, this.props.title + ":"), React.DOM.td(null, ts, " ", delta));
    }
});

var ConnectionInfo = React.createClass({displayName: 'ConnectionInfo',

    render: function() {
        var conn = this.props.conn;
        var address = conn.address.address.join(":");

        var sni = React.DOM.tr({key: "sni"}); //should be null, but that triggers a React bug.
        if(conn.sni){
            sni = React.DOM.tr({key: "sni"}, React.DOM.td(null, React.DOM.abbr({title: "TLS Server Name Indication"}, "TLS SNI:")), React.DOM.td(null, conn.sni));
        }
        return (
            React.DOM.table({className: "connection-table"}, 
                React.DOM.tbody(null, 
                    React.DOM.tr({key: "address"}, React.DOM.td(null, "Address:"), React.DOM.td(null, address)), 
                    sni
                )
            )
        );
    }
});

var CertificateInfo = React.createClass({displayName: 'CertificateInfo',
    render: function(){
        //TODO: We should fetch human-readable certificate representation
        // from the server
        var flow = this.props.flow;
        var client_conn = flow.client_conn;
        var server_conn = flow.server_conn;

        var preStyle = {maxHeight: 100};
        return (
            React.DOM.div(null, 
            client_conn.cert ? React.DOM.h4(null, "Client Certificate") : null, 
            client_conn.cert ? React.DOM.pre({style: preStyle}, client_conn.cert) : null, 

            server_conn.cert ? React.DOM.h4(null, "Server Certificate") : null, 
            server_conn.cert ? React.DOM.pre({style: preStyle}, server_conn.cert) : null
            )
        );
    }
});

var Timing = React.createClass({displayName: 'Timing',
    render: function(){
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
        timestamps.forEach(function(e){
            e.key = e.title;
        });

        timestamps = _.sortBy(timestamps, 't');

        var rows = timestamps.map(function(e){
            return TimeStamp(e);
        });

        return (
            React.DOM.div(null, 
            React.DOM.h4(null, "Timing"), 
            React.DOM.table({className: "timing-table"}, 
                React.DOM.tbody(null, 
                    rows
                )
            )
            )
        );
    }
});

var FlowDetailConnectionInfo = React.createClass({displayName: 'FlowDetailConnectionInfo',
    render: function(){
        var flow = this.props.flow;
        var client_conn = flow.client_conn;
        var server_conn = flow.server_conn;
        return (
            React.DOM.section(null, 

            React.DOM.h4(null, "Client Connection"), 
            ConnectionInfo({conn: client_conn}), 

            React.DOM.h4(null, "Server Connection"), 
            ConnectionInfo({conn: server_conn}), 

            CertificateInfo({flow: flow}), 

            Timing({flow: flow})

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
    getDefaultProps: function(){
        return {
            tabs: ["request","response", "details"]
        };
    },
    mixins: [StickyHeadMixin],
    nextTab: function(i) {
        var currentIndex = this.props.tabs.indexOf(this.props.active);
        // JS modulo operator doesn't correct negative numbers, make sure that we are positive.
        var nextIndex = (currentIndex + i + this.props.tabs.length) % this.props.tabs.length;
        this.props.selectTab(this.props.tabs[nextIndex]);
    },
    render: function(){
        var flow = JSON.stringify(this.props.flow, null, 2);
        var Tab = tabs[this.props.active];
        return (
            React.DOM.div({className: "flow-detail", onScroll: this.adjustHead}, 
                FlowDetailNav({ref: "head", 
                               tabs: this.props.tabs, 
                               active: this.props.active, 
                               selectTab: this.props.selectTab}), 
                Tab({flow: this.props.flow})
            )
            );
    } 
});
/** @jsx React.DOM */

var MainView = React.createClass({displayName: 'MainView',
    getInitialState: function() {
        return {
            flows: [],
        };
    },
    componentDidMount: function () {
        //FIXME: The store should be global, move out of here.
        window.flowstore = new LiveFlowStore();

        this.flowStore = window.flowstore.open_view();
        this.flowStore.addListener("add",this.onFlowChange);
        this.flowStore.addListener("update",this.onFlowChange);
        this.flowStore.addListener("remove",this.onFlowChange);
        this.flowStore.addListener("recalculate",this.onFlowChange);
    },
    componentWillUnmount: function () {
        this.flowStore.removeListener("change",this.onFlowChange);
        this.flowStore.close();
    },
    onFlowChange: function () {
        this.setState({
            flows: this.flowStore.flows
        });
    },
    selectDetailTab: function(panel) {
        ReactRouter.replaceWith(
            "flow",
            {
                flowId: this.props.params.flowId,
                detailTab: panel
            }
        );
    },
    selectFlow: function(flow) {
        if(flow){
            ReactRouter.replaceWith(
                "flow", 
                {
                    flowId: flow.id,
                    detailTab: this.props.params.detailTab || "request"
                }
            );
            this.refs.flowTable.scrollIntoView(flow);
        } else {
            ReactRouter.replaceWith("flows");
        }
    },
    selectFlowRelative: function(i){
        var index;
        if(!this.props.params.flowId){
            if(i > 0){
                index = this.state.flows.length-1;
            } else {
                index = 0;
            }
        } else {
            index = _.findIndex(this.state.flows, function(f){
                return f.id === this.props.params.flowId;
            }.bind(this));
            index = Math.min(Math.max(0, index+i), this.state.flows.length-1);
        }
        this.selectFlow(this.state.flows[index]);
    },
    onKeyDown: function(e){
        switch(e.keyCode){
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
                if(this.refs.flowDetails){
                    this.refs.flowDetails.nextTab(-1);
                }
                break;
            case Key.L:
            case Key.TAB:
            case Key.RIGHT:
                if(this.refs.flowDetails){
                    this.refs.flowDetails.nextTab(+1);
                }
                break;
            default:
                console.debug("keydown", e.keyCode);
                return;
        }
        return false;
    },
    render: function() {
        var selected = _.find(this.state.flows, { id: this.props.params.flowId });

        var details;
        if(selected){
            details = (
                FlowDetail({ref: "flowDetails", 
                            flow: selected, 
                            selectTab: this.selectDetailTab, 
                            active: this.props.params.detailTab})
            );
        } else {
            details = null;
        }

        return (
            React.DOM.div({className: "main-view", onKeyDown: this.onKeyDown, tabIndex: "0"}, 
                FlowTable({ref: "flowTable", 
                           flows: this.state.flows, 
                           selectFlow: this.selectFlow, 
                           selected: selected}), 
                 details ? Splitter(null) : null, 
                details
            )
        );
    }
});
/** @jsx React.DOM */

var LogMessage = React.createClass({displayName: 'LogMessage',
    render: function(){
        var entry = this.props.entry;
        var indicator;
        switch(entry.level){
            case "web":
                indicator = React.DOM.i({className: "fa fa-fw fa-html5"});
                break;
            case "debug":
                indicator = React.DOM.i({className: "fa fa-fw fa-bug"});
                break;
            default:
                indicator = React.DOM.i({className: "fa fa-fw fa-info"});
        }
        return (
            React.DOM.div(null, 
                indicator, " ", entry.message
            )
        );
    },
    shouldComponentUpdate: function(){
        return false; // log entries are immutable.
    }
});

var EventLogContents = React.createClass({displayName: 'EventLogContents',
    mixins:[AutoScrollMixin],
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
        var messages = this.state.log.map(function(row) {
            if(!this.props.filter[row.level]){
                return null;
            }
            return LogMessage({key: row.id, entry: row});
        }.bind(this));
        return React.DOM.pre(null, messages);
    }
});

var ToggleFilter = React.createClass({displayName: 'ToggleFilter',
    toggle: function(){
        return this.props.toggleLevel(this.props.name);
    },
    render: function(){
        var className = "label ";
        if (this.props.active) {
            className += "label-primary";
        } else {
            className += "label-default";
        }
        return (
            React.DOM.a({
                href: "#", 
                className: className, 
                onClick: this.toggle}, 
                this.props.name
            )
        );
   } 
});

var EventLog = React.createClass({displayName: 'EventLog',
    getInitialState: function(){
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
    toggleLevel: function(level){
        var filter = this.state.filter;
        filter[level] = !filter[level];
        this.setState({filter: filter});
        return false;
    },
    render: function () {
        return (
            React.DOM.div({className: "eventlog"}, 
                React.DOM.div(null, 
                    "Eventlog", 
                    React.DOM.div({className: "pull-right"}, 
                        ToggleFilter({name: "debug", active: this.state.filter.debug, toggleLevel: this.toggleLevel}), 
                        ToggleFilter({name: "info", active: this.state.filter.info, toggleLevel: this.toggleLevel}), 
                        ToggleFilter({name: "web", active: this.state.filter.web, toggleLevel: this.toggleLevel}), 
                        React.DOM.i({onClick: this.close, className: "fa fa-close"})
                    )

                ), 
                EventLogContents({filter: this.state.filter})
            )
        );
    }
});
/** @jsx React.DOM */

var Footer = React.createClass({displayName: 'Footer',
    render: function () {
        var mode = this.props.settings.mode;
        return (
            React.DOM.footer(null, 
                mode != "regular" ? React.DOM.span({className: "label label-success"}, mode, " mode") : null
            )
            );
    }
});

/** @jsx React.DOM */

//TODO: Move out of here, just a stub.
var Reports = React.createClass({displayName: 'Reports',
    render: function () {
        return React.DOM.div(null, "ReportEditor");
    }
});


var ProxyAppMain = React.createClass({displayName: 'ProxyAppMain',
    getInitialState: function () {
        return { settings: SettingsStore.getAll() };
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
            React.DOM.div({id: "container"}, 
                Header({settings: this.state.settings}), 
                this.props.activeRouteHandler({settings: this.state.settings}), 
                this.state.settings.showEventLog ? Splitter({axis: "y"}) : null, 
                this.state.settings.showEventLog ? EventLog(null) : null, 
                Footer({settings: this.state.settings})
            )
            );
    }
});


var Routes = ReactRouter.Routes;
var Route = ReactRouter.Route;
var Redirect = ReactRouter.Redirect;
var DefaultRoute = ReactRouter.DefaultRoute;
var NotFoundRoute = ReactRouter.NotFoundRoute;


var ProxyApp = (
    Routes({location: "hash"}, 
        Route({path: "/", handler: ProxyAppMain}, 
            Route({name: "flows", path: "flows", handler: MainView}), 
            Route({name: "flow", path: "flows/:flowId/:detailTab", handler: MainView}), 
            Route({name: "reports", handler: Reports}), 
            Redirect({path: "/", to: "flows"})
        )
    )
    );
$(function () {
    window.app = React.renderComponent(ProxyApp, document.body);
    var UpdateConnection = new Connection("/updates");
    UpdateConnection.onmessage = function (message) {
        var m = JSON.parse(message.data);
        AppDispatcher.dispatchServerAction(m);
    };
});
//# sourceMappingURL=app.js.map