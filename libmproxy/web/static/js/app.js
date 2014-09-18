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
    adjustHead: function(){
        // Abusing CSS transforms to set the element
        // referenced as head into some kind of position:sticky.
        var head = this.refs.head.getDOMNode();
        head.style.transform = "translate(0,"+this.getDOMNode().scrollTop+"px)";
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
    ESC: 27
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
               flow.id = "uuid-" + id++;
           });
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

//React utils. For other utilities, see ../utils.js

var Splitter = React.createClass({displayName: 'Splitter',
    getDefaultProps: function () {
    return {
        axis: "x"
        }
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
    },
    onMouseUp: function(e){
        window.removeEventListener("mouseup",this.onMouseUp);
        window.removeEventListener("mousemove",this.onMouseMove);

        var node = this.getDOMNode();
        var prev = node.previousElementSibling;
        var next = node.nextElementSibling;
        this.getDOMNode().style.transform="";

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
    reset: function(){
        if(!this.state.applied){
            return;
        }
        var node = this.getDOMNode();
        var prev = node.previousElementSibling;
        var next = node.nextElementSibling;
        
        prev.style.flex = "";
        next.style.flex = "";
    },
    render: function(){
        var className = "splitter";
        if(this.props.axis === "x"){
            className += " splitter-x";
        } else {
            className += " splitter-y";
        }
        return React.DOM.div({className: className, onMouseDown: this.onMouseDown});
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
        var header = header_entries.map(function(entry){
            var classes = React.addons.classSet({
                active: entry == this.state.active
            });
            return (
                React.DOM.a({key: entry.title, 
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
        var classes = React.addons.classSet({
            "col-tls": true,
            "col-tls-https": ssl,
            "col-tls-http": !ssl
        });
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
        return React.DOM.td({className: "col-icon"}, React.DOM.div({className: "resource-icon resource-icon-plain"}));
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
        return React.DOM.td({className: "col-time"}, time);
    }
});


var all_columns = [TLSColumn, IconColumn, PathColumn, MethodColumn, StatusColumn, TimeColumn];


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
        return React.DOM.tbody({onKeyDown: this.props.onKeyDown, tabIndex: "0"}, rows);
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
    selectFlowRelative: function(i){
        var index;
        if(!this.props.selected){
            if(i > 0){
                index = this.props.flows.length-1;
            } else {
                index = 0;
            }
        } else {
            index = _.findIndex(this.props.flows, function(f){
                return f === this.props.selected;
            }.bind(this));
            index = Math.min(Math.max(0, index+i), this.props.flows.length-1);
        }
        this.props.selectFlow(this.props.flows[index]);
    },
    onKeyDown: function(e){
        switch(e.keyCode){
            case Key.DOWN:
                this.selectFlowRelative(+1);
                break;
            case Key.UP:
                this.selectFlowRelative(-1);
                break;
            case Key.PAGE_DOWN:
                this.selectFlowRelative(+10);
                break;
            case Key.PAGE_UP:
                this.selectFlowRelative(-10);
                break;
            case Key.ESC:
                this.props.selectFlow(null);
                break;
            default:
                console.debug("keydown", e.keyCode);
                return;
        }
        return false;
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
                                   columns: this.state.columns, 
                                   onKeyDown: this.onKeyDown})
                )
            )
            );
    }
});

/** @jsx React.DOM */

var FlowDetailNav = React.createClass({displayName: 'FlowDetailNav',
    render: function(){

        var items = ["request", "response", "details"].map(function(e){
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

var FlowDetailRequest = React.createClass({displayName: 'FlowDetailRequest',
    render: function(){
        return React.DOM.div(null, "request");
    }
});

var FlowDetailResponse = React.createClass({displayName: 'FlowDetailResponse',
    render: function(){
        return React.DOM.div(null, "response");
    }
});

var FlowDetailConnectionInfo = React.createClass({displayName: 'FlowDetailConnectionInfo',
    render: function(){
        return React.DOM.div(null, "details");
    }
});

var tabs = {
    request: FlowDetailRequest,
    response: FlowDetailResponse,
    details: FlowDetailConnectionInfo
};

var FlowDetail = React.createClass({displayName: 'FlowDetail',
    mixins: [StickyHeadMixin],
    render: function(){
        var flow = JSON.stringify(this.props.flow, null, 2);
        var Tab = tabs[this.props.active];
        return (
            React.DOM.div({className: "flow-detail", onScroll: this.adjustHead}, 
                FlowDetailNav({active: this.props.active, selectTab: this.props.selectTab}), 
                Tab(null)
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
        console.log("get view");
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
    selectDetailTab: function(panel) {
        ReactRouter.replaceWith(
            "flow", 
            {
                flowId: this.props.params.flowId,
                detailTab: panel
            }
        );
    },
    render: function() {
        var selected = _.find(this.state.flows, { id: this.props.params.flowId });

        var details = null;
        if(selected){
            details = (
                FlowDetail({ref: "flowDetails", 
                            flow: selected, 
                            selectTab: this.selectDetailTab, 
                            active: this.props.params.detailTab})
            );
        }

        return (
            React.DOM.div({className: "main-view"}, 
                FlowTable({ref: "flowTable", 
                           flows: this.state.flows, 
                           selectFlow: this.selectFlow, 
                           selected: selected}), 
                Splitter(null), 
                details
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
                this.props.activeRouteHandler({settings: this.state.settings}), 
                Splitter({axis: "y"}), 
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
    Connection.init();
    app = React.renderComponent(ProxyApp, document.body);
});
//# sourceMappingURL=app.js.map