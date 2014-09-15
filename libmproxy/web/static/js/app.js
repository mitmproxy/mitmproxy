
    function EventEmitter(){"use strict";
        this.listeners = {};
    }
    EventEmitter.prototype.emit=function(event){"use strict";
        if(!(event in this.listeners)){
            return;
        }
        this.listeners[event].forEach(function (listener) {
            listener(event, this);
        }.bind(this));
    };
    EventEmitter.prototype.addListener=function(event, f){"use strict";
        this.listeners[event] = this.listeners[event] || [];
        this.listeners[event].push(f);
    };
    EventEmitter.prototype.removeListener=function(event, f){"use strict";
        if(!(event in this.listeners)){
            return false;
        }
        var index = this.listeners.indexOf(f);
        if (index >= 0) {
            this.listeners.splice(this.listeners.indexOf(f), 1);
        }
    };


var FLOW_CHANGED = "flow.changed";

for(var EventEmitter____Key in EventEmitter){if(EventEmitter.hasOwnProperty(EventEmitter____Key)){FlowStore[EventEmitter____Key]=EventEmitter[EventEmitter____Key];}}var ____SuperProtoOfEventEmitter=EventEmitter===null?null:EventEmitter.prototype;FlowStore.prototype=Object.create(____SuperProtoOfEventEmitter);FlowStore.prototype.constructor=FlowStore;FlowStore.__superConstructor__=EventEmitter;
    function FlowStore() {"use strict";
        EventEmitter.call(this);
        this.flows = [];
    }

    FlowStore.prototype.getAll=function() {"use strict";
        return this.flows;
    };

    FlowStore.prototype.close=function(){"use strict";
        console.log("FlowStore.close()");
        this.listeners = [];
    };

    FlowStore.prototype.emitChange=function() {"use strict";
        return this.emit(FLOW_CHANGED);
    };

    FlowStore.prototype.addChangeListener=function(f) {"use strict";
        this.addListener(FLOW_CHANGED, f);
    };

    FlowStore.prototype.removeChangeListener=function(f) {"use strict";
        this.removeListener(FLOW_CHANGED, f);
    };


for(var FlowStore____Key in FlowStore){if(FlowStore.hasOwnProperty(FlowStore____Key)){DummyFlowStore[FlowStore____Key]=FlowStore[FlowStore____Key];}}var ____SuperProtoOfFlowStore=FlowStore===null?null:FlowStore.prototype;DummyFlowStore.prototype=Object.create(____SuperProtoOfFlowStore);DummyFlowStore.prototype.constructor=DummyFlowStore;DummyFlowStore.__superConstructor__=FlowStore;
    function DummyFlowStore(flows) {"use strict";
        FlowStore.call(this);
        this.flows = flows;
    }

    DummyFlowStore.prototype.addFlow=function(flow) {"use strict";
        this.flows.push(flow);
        this.emitChange();
    };



var SETTINGS_CHANGED = "settings.changed";

for(EventEmitter____Key in EventEmitter){if(EventEmitter.hasOwnProperty(EventEmitter____Key)){Settings[EventEmitter____Key]=EventEmitter[EventEmitter____Key];}}Settings.prototype=Object.create(____SuperProtoOfEventEmitter);Settings.prototype.constructor=Settings;Settings.__superConstructor__=EventEmitter;
    function Settings(){"use strict";
        EventEmitter.call(this);
        this.settings = false;
    }

    Settings.prototype.getAll=function(){"use strict";
        return this.settings;
    };

    Settings.prototype.emitChange=function() {"use strict";
        return this.emit(SETTINGS_CHANGED);
    };

    Settings.prototype.addChangeListener=function(f) {"use strict";
        this.addListener(SETTINGS_CHANGED, f);
    };

    Settings.prototype.removeChangeListener=function(f) {"use strict";
        this.removeListener(SETTINGS_CHANGED, f);
    };


for(var Settings____Key in Settings){if(Settings.hasOwnProperty(Settings____Key)){DummySettings[Settings____Key]=Settings[Settings____Key];}}var ____SuperProtoOfSettings=Settings===null?null:Settings.prototype;DummySettings.prototype=Object.create(____SuperProtoOfSettings);DummySettings.prototype.constructor=DummySettings;DummySettings.__superConstructor__=Settings;
    function DummySettings(settings){"use strict";
        Settings.call(this);
        this.settings = settings;
    }
    DummySettings.prototype.update=function(obj){"use strict";
        _.merge(this.settings, obj);
        this.emitChange();
    };

/** @jsx React.DOM */

var Footer = React.createClass({displayName: 'Footer',
    render : function(){
        return (React.DOM.footer(null, 
            React.DOM.span({className: "label label-success"}, "transparent mode")
            ));
    }
});
/** @jsx React.DOM */

var MainMenu = React.createClass({displayName: 'MainMenu',
    render : function(){
        return (React.DOM.div(null, "Main Menu"));
    }
});
var ToolsMenu = React.createClass({displayName: 'ToolsMenu',
    render : function(){
        return (React.DOM.div(null, "Tools Menu"));
    }
});
var ReportsMenu = React.createClass({displayName: 'ReportsMenu',
    render : function(){
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
    getInitialState: function(){
      return {active: "main"};
    },
    handleClick: function(active){
        this.setState({active: active});
        ReactRouter.transitionTo(_Header_Entries[active].route);
        return false;
    },
    handleFileClick: function(){
        console.log("File click");
    },
    render: function(){

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
              "mitmproxy ",  this.props.settings.version
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

var App = React.createClass({displayName: 'App',
    getInitialState: function () {
        return {
            settings: {} //TODO: How explicit should we get here?
                         //List all subattributes?
        };
    },
    componentDidMount: function () {
        //TODO: Replace DummyStore with real settings over WS (https://facebook.github.io/react/tips/initial-ajax.html)
        var settingsStore = new DummySettings({
            version: "0.12"
        });
        this.setState({settingsStore: settingsStore});
        settingsStore.addChangeListener(this.onSettingsChange);
    },
    onSettingsChange: function(event, settings){
        this.setState({settings: settings.getAll()});
    },
    render: function () {
      return (
        React.DOM.div({id: "container"}, 
          Header({settings: this.state.settings}), 
          React.DOM.div({id: "main"}, 
              this.props.activeRouteHandler({settings: this.state.settings})
          ), 
          Footer(null)
        )
      );
    }
});

var TrafficTable = React.createClass({displayName: 'TrafficTable',
    getInitialState: function(){
        return {
            flows: []
        };
    },
    componentDidMount: function () {
        var flowStore = new DummyFlowStore([]);
        this.setState({flowStore: flowStore});

        flowStore.addChangeListener(this.onFlowsChange);

        $.getJSON("/flows.json").success(function (flows) {
            flows.forEach(function (flow, i) {
                window.setTimeout(function () {
                    flowStore.addFlow(flow);
                }, _.random(i*400,i*400+1000));
            });
        }.bind(this));
    },
    componentWillUnmount: function(){
        this.state.flowStore.close();
    },
    onFlowsChange: function(event, flows){
        this.setState({flows: flows.getAll()});
    },
    render: function () {
       var flows = this.state.flows.map(function(flow){
           return React.DOM.div(null, flow.request.method, " ", flow.request.scheme, "://", flow.request.host, flow.request.path);
       });
       return React.DOM.pre(null, flows);
   }
});

var Reports = React.createClass({displayName: 'Reports',
   render: function(){
       return (React.DOM.div(null, "Report Editor"));
   }
});

var routes = (
  ReactRouter.Routes({location: "hash"}, 
    ReactRouter.Route({name: "app", path: "/", handler: App}, 
        ReactRouter.Route({name: "main", handler: TrafficTable}), 
        ReactRouter.Route({name: "reports", handler: Reports}), 
        ReactRouter.Redirect({to: "main"})
    )
  )
);
//# sourceMappingURL=app.js.map