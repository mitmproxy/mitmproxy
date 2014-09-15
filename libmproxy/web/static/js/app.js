const PayloadSources = {
  VIEW_ACTION: "VIEW_ACTION",
  SERVER_ACTION: "SERVER_ACTION"
};



  function Dispatcher() {"use strict";
    this.callbacks = [];
  }

  Dispatcher.prototype.register=function(callback){"use strict";
    this.callbacks.push(callback);
  };

  Dispatcher.prototype.unregister=function(callback){"use strict";
    var index = this.callbacks.indexOf(f);
    if (index >= 0) {
      this.callbacks.splice(this.callbacks.indexOf(f), 1);
    }
  };

  Dispatcher.prototype.dispatch=function(payload){"use strict";
    console.debug("dispatch", payload);
    this.callbacks.forEach(function(callback)  {
        callback(payload);
    });
  };



AppDispatcher = new Dispatcher();
AppDispatcher.dispatchViewAction = function(action){
  action.actionSource = PayloadSources.VIEW_ACTION;
  this.dispatch(action);
};
var ActionTypes = {
  SETTINGS_UPDATE: "SETTINGS_UPDATE",
  LOG_ADD: "LOG_ADD"
};

var SettingsActions = {
  update:function(settings) {
  	settings = _.merge({}, SettingsStore.getSettings(), settings);
    AppDispatcher.dispatchViewAction({
      actionType: ActionTypes.SETTINGS_UPDATE,
      settings: settings
    });
  }
};

	function EventEmitter() {"use strict";
		this.listeners = {};
	}
	EventEmitter.prototype.emit=function(event) {"use strict";
		if (!(event in this.listeners)) {
			return;
		}
		this.listeners[event].forEach(function(listener) {
			listener(event, this);
		}.bind(this));
	};
	EventEmitter.prototype.addListener=function(event, f) {"use strict";
		this.listeners[event] = this.listeners[event] || [];
		this.listeners[event].push(f);
	};
	EventEmitter.prototype.removeListener=function(event, f) {"use strict";
		if (!(event in this.listeners)) {
			return false;
		}
		var index = this.listeners[event].indexOf(f);
		if (index >= 0) {
			this.listeners[event].splice(index, 1);
		}
	};

for(var EventEmitter____Key in EventEmitter){if(EventEmitter.hasOwnProperty(EventEmitter____Key)){_SettingsStore[EventEmitter____Key]=EventEmitter[EventEmitter____Key];}}var ____SuperProtoOfEventEmitter=EventEmitter===null?null:EventEmitter.prototype;_SettingsStore.prototype=Object.create(____SuperProtoOfEventEmitter);_SettingsStore.prototype.constructor=_SettingsStore;_SettingsStore.__superConstructor__=EventEmitter;
	function _SettingsStore() {"use strict";
		/*jshint validthis: true */
		EventEmitter.call(this);
		this.settings = { version: "0.12", showEventLog: true }; //FIXME: Need to get that from somewhere.
	}
	_SettingsStore.prototype.getSettings=function() {"use strict";
		return this.settings;
	};
	_SettingsStore.prototype.handle=function(action) {"use strict";
		switch (action.actionType) {
			case ActionTypes.SETTINGS_UPDATE:
				this.settings = action.settings;
				this.emit("change");
				break;
			default:
				return;
		}
	};

var SettingsStore = new _SettingsStore();
AppDispatcher.register(SettingsStore.handle.bind(SettingsStore));


var SettingsMixin = {
	getInitialState:function(){
		return {
			settings: SettingsStore.getSettings()
		};
	},
    componentDidMount:function(){
        SettingsStore.addListener("change", this._onSettingsChange);
    },
    componentWillUnmount:function(){
        SettingsStore.removeListener("change", this._onSettingsChange);
    },
    _onSettingsChange:function(){
    	this.setState({
    		settings: SettingsStore.getSettings()
    	});
    }
};
for(var EventEmitter____Key in EventEmitter){if(EventEmitter.hasOwnProperty(EventEmitter____Key)){_EventLogStore[EventEmitter____Key]=EventEmitter[EventEmitter____Key];}}var ____SuperProtoOfEventEmitter=EventEmitter===null?null:EventEmitter.prototype;_EventLogStore.prototype=Object.create(____SuperProtoOfEventEmitter);_EventLogStore.prototype.constructor=_EventLogStore;_EventLogStore.__superConstructor__=EventEmitter;
	function _EventLogStore() {"use strict";
		/*jshint validthis: true */
		EventEmitter.call(this);
		this.log = [];
	}
	_EventLogStore.prototype.getAll=function() {"use strict";
		return this.log;
	};
	_EventLogStore.prototype.handle=function(action) {"use strict";
		switch (action.actionType) {
			case ActionTypes.LOG_ADD:
				this.log.push(action.message);
				this.emit("change");
				break;
			default:
				return;
		}
	};

var EventLogStore = new _EventLogStore();
AppDispatcher.register(EventLogStore.handle.bind(EventLogStore));


var EventLogMixin = {
	getInitialState:function(){
		return {
			log: EventLog.getAll()
		};
	},
    componentDidMount:function(){
        SettingsStore.addListener("change", this._onEventLogChange);
    },
    componentWillUnmount:function(){
        SettingsStore.removeListener("change", this._onEventLogChange);
    },
    _onEventLogChange:function(){
    	this.setState({
    		log: EventLog.getAll()
    	});
    }
};

    function Connection(root){"use strict";
        if(!root){
            root = location.origin + "/api/v1";
        }
        this.root = root;
        this.openWebSocketConnection();
    }

    Connection.prototype.openWebSocketConnection=function(){"use strict";
        this.ws = new WebSocket(this.root.replace("http","ws") + "/ws");
        var ws = this.ws;

        ws.onopen = this.onopen.bind(this);
        ws.onmessage = this.onmessage.bind(this);
        ws.onerror = this.onerror.bind(this);
        ws.onclose = this.onclose.bind(this);
    };

    Connection.prototype.onopen=function(open){"use strict";
        console.log("onopen", this, arguments);
    };
    Connection.prototype.onmessage=function(message){"use strict";
        console.log("onmessage", this, arguments);
    };
    Connection.prototype.onerror=function(error){"use strict";
        console.log("onerror", this, arguments);
    };
    Connection.prototype.onclose=function(close){"use strict";
        console.log("onclose", this, arguments);
    };




    function Connection(root){"use strict";
        if(!root){
            root = location.origin + "/api/v1";
        }
        this.root = root;
        this.openWebSocketConnection();
    }

    Connection.prototype.openWebSocketConnection=function(){"use strict";
        this.ws = new WebSocket(this.root.replace("http","ws") + "/ws");
        var ws = this.ws;

        ws.onopen = this.onopen.bind(this);
        ws.onmessage = this.onmessage.bind(this);
        ws.onerror = this.onerror.bind(this);
        ws.onclose = this.onclose.bind(this);
    };

    Connection.prototype.onopen=function(open){"use strict";
        console.log("onopen", this, arguments);
    };
    Connection.prototype.onmessage=function(message){"use strict";
        console.log("onmessage", this, arguments);
    };
    Connection.prototype.onerror=function(error){"use strict";
        console.log("onerror", this, arguments);
    };
    Connection.prototype.onclose=function(close){"use strict";
        console.log("onclose", this, arguments);
    };



/** @jsx React.DOM */

var MainMenu = React.createClass({displayName: 'MainMenu',
    mixins: [SettingsMixin],
    handleSettingsChange:function() {
        SettingsActions.update({
            showEventLog: !this.state.settings.showEventLog
        });
    },
    render:function(){
        return React.DOM.div(null, 
            React.DOM.button({className: "btn " + (this.state.settings.showEventLog ? "btn-primary" : "btn-default"), onClick: this.handleSettingsChange}, 
                React.DOM.i({className: "fa fa-database"}), " Display Event Log"
            )
            );
    }
});
var ToolsMenu = React.createClass({displayName: 'ToolsMenu',
    render:function(){
        return (React.DOM.div(null, "Tools Menu"));
    }
});
var ReportsMenu = React.createClass({displayName: 'ReportsMenu',
    render:function(){
        return (React.DOM.div(null, "Reports Menu"));
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
    mixins: [SettingsMixin],
    getInitialState:function(){
        return {
            active: "main"
        };
    },
    handleClick:function(active){
        this.setState({active: active});
        ReactRouter.transitionTo(_Header_Entries[active].route);
        return false;
    },
    handleFileClick:function(){
        console.log("File click");
    },

    render:function(){
        var header = [];
        for(var item in _Header_Entries){
            var classes = this.state.active == item ? "active" : "";
            header.push(React.DOM.a({key: item, href: "#", className: classes, 
                onClick: this.handleClick.bind(this, item)},  _Header_Entries[item].title));
        }

        var menu = _Header_Entries[this.state.active].menu();
        return (
            React.DOM.header(null, 
                React.DOM.div({className: "title-bar"}, 
                    "mitmproxy ",  this.state.settings.version
                ), 
                React.DOM.nav(null, 
                    React.DOM.a({href: "#", className: "special", onClick: this.handleFileClick}, " File "), 
                    header
                ), 
                React.DOM.div({className: "menu"}, 
                    menu 
                )
            ));
    }
});
/** @jsx React.DOM */

var TrafficTable = React.createClass({displayName: 'TrafficTable',
    /*getInitialState: function(){
        return {
            flows: []
        };
    },*/
    componentDidMount: function () {
        /*var flowStore = new DummyFlowStore([]);
        this.setState({flowStore: flowStore});

        flowStore.addChangeListener(this.onFlowsChange);

        $.getJSON("/flows.json").success(function (flows) {
            flows.forEach(function (flow, i) {
                window.setTimeout(function () {
                    flowStore.addFlow(flow);
                }, _.random(i*400,i*400+1000));
            });
        }.bind(this));*/
    },
    componentWillUnmount: function(){
        //this.state.flowStore.close();
    },
    onFlowsChange: function(event, flows){
        //this.setState({flows: flows.getAll()});
    },
    render: function () {
       /*var flows = this.state.flows.map(function(flow){
           return <div>{flow.request.method} {flow.request.scheme}://{flow.request.host}{flow.request.path}</div>;
       }); *//**/
       x = "WTF";
       i = 12;
       while(i--) x += x;
       return React.DOM.div(null, React.DOM.pre(null, x));
   }
});
/** @jsx React.DOM */

var EventLog = React.createClass({displayName: 'EventLog',
	close:function(){
		SettingsActions.update({
			showEventLog: false
		});
	},
    render:function(){
        return (
            React.DOM.div({className: "eventlog"}, 
            React.DOM.pre(null, 
            React.DOM.i({className: "fa fa-close close-button", onClick: this.close}), 
            "much log."
            )
            )
        );
    }
});
/** @jsx React.DOM */

var Footer = React.createClass({displayName: 'Footer',
    render:function(){
        return (
            React.DOM.footer(null, 
                React.DOM.span({className: "label label-success"}, "transparent mode")
            )
        );
    }
});
/** @jsx React.DOM */

//TODO: Move out of here, just a stub.
var Reports = React.createClass({displayName: 'Reports',
   render:function(){
       return (React.DOM.div(null, "Report Editor"));
   }
});



var ProxyAppMain = React.createClass({displayName: 'ProxyAppMain',
    mixins: [SettingsMixin],
    render:function() {
      return (
        React.DOM.div({id: "container"}, 
          Header(null), 
          React.DOM.div({id: "main"}, this.props.activeRouteHandler(null)), 
          this.state.settings.showEventLog ? EventLog(null) : null, 
          Footer(null)
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

$(function(){

  app = React.renderComponent(ProxyApp, document.body);

});
//# sourceMappingURL=app.js.map