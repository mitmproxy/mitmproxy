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
    UPDATE_SETTINGS: "update_settings",
    ADD_EVENT: "add_event"
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
    console.log("onerror", this, arguments);
};
_Connection.prototype.onclose = function (close) {
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

var TrafficTable = React.createClass({displayName: 'TrafficTable',
    getInitialState: function () {
        return {
            flows: []
        };
    },
    componentDidMount: function () {
        //this.flowStore = FlowStore.getView();
        //this.flowStore.addListener("change",this.onFlowChange);
    },
    componentWillUnmount: function () {
        //this.flowStore.removeListener("change",this.onFlowChange);
        //this.flowStore.close();
    },
    onFlowChange: function () {
        this.setState({
            //flows: this.flowStore.getAll()
        });
    },
    render: function () {
        /*var flows = this.state.flows.map(function(flow){
         return <div>{flow.request.method} {flow.request.scheme}://{flow.request.host}{flow.request.path}</div>;
         }); */
        //Dummy Text for layout testing
        x = "Flow";
        i = 12;
        while (i--) x += x;
        return (
            React.DOM.div(null, "Flow") 
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
            return (React.DOM.div({key: row.id}, row.message));
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
                React.DOM.div({id: "main"}, this.props.activeRouteHandler(null)), 
                this.state.settings.showEventLog ? EventLog(null) : null, 
                Footer({settings: this.state.settings})
            )
            );
    }
});


var ProxyApp = (
    ReactRouter.Routes({location: "hash"}, 
        ReactRouter.Route({name: "app", path: "/", handler: ProxyAppMain}, 
            ReactRouter.Route({name: "main", handler: TrafficTable}), 
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