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


var Key = {
    UP: 38,
    DOWN: 40,
    LEFT: 37,
    RIGHT: 39,
    ENTER: 13,
    ESC: 27
}
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
    this.callbacks.forEach(function (callback) {
        callback(payload);
    });
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

var EventLogActions = {
    add_event: function(message, level){
        AppDispatcher.dispatchViewAction({
            type: ActionTypes.ADD_EVENT,
            data: {
                message: message,
                level: level || "info",
                source: "ui"
            }
        });
    }
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

function FlowView(store, live) {
    EventEmitter.call(this);
    this._store = store;
    this.live = live;
    this.flows = [];

    this.add = this.add.bind(this);
    this.update = this.update.bind(this);

    if (live) {
        this._store.addListener(ActionTypes.ADD_FLOW, this.add);
        this._store.addListener(ActionTypes.UPDATE_FLOW, this.update);
    }
}

_.extend(FlowView.prototype, EventEmitter.prototype, {
    close: function () {
        this._store.removeListener(ActionTypes.ADD_FLOW, this.add);
        this._store.removeListener(ActionTypes.UPDATE_FLOW, this.update);
    },
    getAll: function () {
        return this.flows;
    },
    add: function (flow) {
        return this.update(flow);
    },
    add_bulk: function (flows) {
        //Treat all previously received updates as newer than the bulk update.
        //If they weren't newer, we're about to receive an update for them very soon.
        var updates = this.flows;
        this.flows = flows;
        updates.forEach(function(flow){
            this._update(flow);
        }.bind(this));
        this.emit("change");
    },
    _update: function(flow){
        var idx = _.findIndex(this.flows, function(f){
            return flow.id === f.id;
        });

        if(idx < 0){
            this.flows.push(flow);
        } else {
            this.flows[idx] = flow;
        }
    },
    update: function(flow){
        this._update(flow);
        this.emit("change");
    },
});


function _FlowStore() {
    EventEmitter.call(this);
}
_.extend(_FlowStore.prototype, EventEmitter.prototype, {
    getView: function (since) {
        var view = new FlowView(this, !since);

        $.getJSON("/static/flows.json", function(flows){
           flows = flows.concat(_.cloneDeep(flows)).concat(_.cloneDeep(flows));
           var id = 1;
           flows.forEach(function(flow){
               flow.id = "uuid-"+id++;
           })
           view.add_bulk(flows); 

        });

        return view;
    },
    handle: function (action) {
        switch (action.type) {
            case ActionTypes.ADD_FLOW:
            case ActionTypes.UPDATE_FLOW:
                this.emit(action.type, action.data);
                break;
            default:
                return;
        }
    }
});


var FlowStore = new _FlowStore();
AppDispatcher.register(FlowStore.handle.bind(FlowStore));

function _Connection(url) {
    this.url = url;
}
_Connection.prototype.init = function () {
    this.openWebSocketConnection();
};
_Connection.prototype.openWebSocketConnection = function () {
    this.ws = new WebSocket(this.url.replace("http", "ws"));
    var ws = this.ws;

    ws.onopen = this.onopen.bind(this);
    ws.onmessage = this.onmessage.bind(this);
    ws.onerror = this.onerror.bind(this);
    ws.onclose = this.onclose.bind(this);
};
_Connection.prototype.onopen = function (open) {
    console.log("onopen", this, arguments);
};
_Connection.prototype.onmessage = function (message) {
    //AppDispatcher.dispatchServerAction(...);
    var m = JSON.parse(message.data);
    AppDispatcher.dispatchServerAction(m);
};
_Connection.prototype.onerror = function (error) {
    EventLogActions.add_event("WebSocket Connection Error.");
    console.log("onerror", this, arguments);
};
_Connection.prototype.onclose = function (close) {
    EventLogActions.add_event("WebSocket Connection closed.");
    console.log("onclose", this, arguments);
};

var Connection = new _Connection(location.origin + "/updates");

/** @jsx React.DOM */

var MainMenu = React.createClass({displayName: 'MainMenu',
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
    render: function () {
        return React.DOM.div(null, "Tools Menu");
    }
});
var ReportsMenu = React.createClass({displayName: 'ReportsMenu',
    render: function () {
        return React.DOM.div(null, "Reports Menu");
    }
});


var _Header_Entries = {
    main: {
        title: "Traffic",
        route: "main",
        menu: MainMenu
    },
    tools: {
        title: "Tools",
        route: "main",
        menu: ToolsMenu
    },
    reports: {
        title: "Visualization",
        route: "reports",
        menu: ReportsMenu
    }
};

var Header = React.createClass({displayName: 'Header',
    getInitialState: function () {
        return {
            active: "main"
        };
    },
    handleClick: function (active) {
        this.setState({active: active});
        ReactRouter.transitionTo(_Header_Entries[active].route);
        return false;
    },
    handleFileClick: function () {
        console.log("File click");
    },
    render: function () {
        var header = [];
        for (var item in _Header_Entries) {
            var classes = this.state.active == item ? "active" : "";
            header.push(React.DOM.a({key: item, href: "#", className: classes, 
                onClick: this.handleClick.bind(this, item)},  _Header_Entries[item].title));
        }

        var menu = _Header_Entries[this.state.active].menu({
            settings: this.props.settings
        });
        return (
            React.DOM.header(null, 
                React.DOM.div({className: "title-bar"}, 
                    "mitmproxy ",  this.props.settings.version
                ), 
                React.DOM.nav(null, 
                    React.DOM.a({href: "#", className: "special", onClick: this.handleFileClick}, " File "), 
                    header
                ), 
                React.DOM.div({className: "menu"}, 
                    menu 
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
        return React.DOM.td({className: ssl ? "col-tls-https" : "col-tls-http"});
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
        return React.DOM.td({className: "resource-icon resource-icon-plain"});
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
        return React.DOM.td(null, flow.request.scheme + "://" + flow.request.host + flow.request.path);
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
        return React.DOM.td(null, flow.request.method);
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
        return React.DOM.td(null, status);
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
            time = Math.round(1000 * (flow.response.timestamp_end - flow.request.timestamp_start))+"ms";
        } else {
            time = "...";
        }
        return React.DOM.td(null, time);
    }
});


var all_columns = [TLSColumn, IconColumn, PathColumn, MethodColumn, StatusColumn, TimeColumn];


/** @jsx React.DOM */

var FlowRow = React.createClass({displayName: 'FlowRow',
    render: function(){
        var flow = this.props.flow;
        var columns = this.props.columns.map(function(column){
            return column({
                key: column.displayName,
                flow: flow
            });
        }.bind(this));
        var className = "";
        if(this.props.selected){
            className += "selected";
        }
        return (
            React.DOM.tr({className: className, onClick: this.props.selectFlow.bind(null, flow)}, 
                columns
            ));
    }
});

var FlowTableHead = React.createClass({displayName: 'FlowTableHead',
    render: function(){
        var columns = this.props.columns.map(function(column){
            return column.renderTitle();
        }.bind(this));
        return React.DOM.thead(null, columns);
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
        return React.DOM.tbody({onKeyDown: this.props.onKeyDown, tabIndex: "0"}, rows);
    }
});


var FlowTable = React.createClass({displayName: 'FlowTable',
    getInitialState: function () {
        return {
            flows: [],
            columns: all_columns
        };
    },
    componentDidMount: function () {
        this.flowStore = FlowStore.getView();
        this.flowStore.addListener("change",this.onFlowChange);
    },
    componentWillUnmount: function () {
        this.flowStore.removeListener("change",this.onFlowChange);
        this.flowStore.close();
    },
    onFlowChange: function () {
        this.setState({
            flows: this.flowStore.getAll()
        });
    },
    selectFlow: function(flow){
        this.setState({
            selected: flow
        });

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
    selectRowRelative: function(i){
        var index;
        if(!this.state.selected){
            if(i > 0){
                index = this.flows.length-1;
            } else {
                index = 0;
            }
        } else {
            index = _.findIndex(this.state.flows, function(f){
                return f === this.state.selected;
            }.bind(this));
            index = Math.min(Math.max(0, index+i), this.state.flows.length-1);
        }
        this.selectFlow(this.state.flows[index]);
    },
    onKeyDown: function(e){
        switch(e.keyCode){
            case Key.DOWN:
                this.selectRowRelative(+1);
                return false;
                break;
            case Key.UP:
                this.selectRowRelative(-1);
                return false;
                break;
            case Key.ENTER:
                console.log("Open details pane...", this.state.selected);
                break;
            case Key.ESC:
                console.log("")
            default:
                console.debug("keydown", e.keyCode);
                return;
        }
        return false;
    },
    onScroll: function(e){
        //Abusing CSS transforms to set thead into position:fixed.
        var head = this.refs.head.getDOMNode();
        head.style.transform = "translate(0,"+this.getDOMNode().scrollTop+"px)";
    },
    render: function () {
        var flows = this.state.flows.map(function(flow){
         return React.DOM.div(null, flow.request.method, " ", flow.request.scheme, "://", flow.request.host, flow.request.path);
        });
        return (
        React.DOM.main({onScroll: this.onScroll}, 
            React.DOM.table({className: "flow-table"}, 
                FlowTableHead({ref: "head", 
                               columns: this.state.columns}), 
                FlowTableBody({ref: "body", 
                               selectFlow: this.selectFlow, 
                               onKeyDown: this.onKeyDown, 
                               selected: this.state.selected, 
                               columns: this.state.columns, 
                               flows: this.state.flows})
            )
        )
            );
    }
});

/** @jsx React.DOM */

var EventLog = React.createClass({displayName: 'EventLog',
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
    close: function () {
        SettingsActions.update({
            showEventLog: false
        });
    },
    render: function () {
        var messages = this.state.log.map(function(row) {
            var indicator = null;
            if(row.source === "ui"){
                indicator = React.DOM.i({className: "fa fa-html5"});
            }
            return (
                React.DOM.div({key: row.id}, 
                    indicator, " ", row.message
                ));
        });
        return React.DOM.pre({className: "eventlog"}, messages);
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
        console.log("onSettingsChange");
        this.setState({settings: SettingsStore.getAll()});
    },
    render: function () {
        return (
            React.DOM.div({id: "container"}, 
                Header({settings: this.state.settings}), 
                this.props.activeRouteHandler(null), 
                this.state.settings.showEventLog ? EventLog(null) : null, 
                Footer({settings: this.state.settings})
            )
            );
    }
});


var ProxyApp = (
    ReactRouter.Routes({location: "hash"}, 
        ReactRouter.Route({name: "app", path: "/", handler: ProxyAppMain}, 
            ReactRouter.Route({name: "main", handler: FlowTable}), 
            ReactRouter.Route({name: "reports", handler: Reports}), 
            ReactRouter.Redirect({to: "main"})
        )
    )
    );

$(function () {
    Connection.init();
    app = React.renderComponent(ProxyApp, document.body);
});
//# sourceMappingURL=app.js.map