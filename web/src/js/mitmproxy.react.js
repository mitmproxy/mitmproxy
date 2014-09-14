/** @jsx React.DOM */

var App = React.createClass({
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
      <div id="container">
        <Header settings={this.state.settings}/>
        <div id="main">
            <this.props.activeRouteHandler settings={this.state.settings}/>
        </div>
        <Footer/>
      </div>
    );
    }
});

var TrafficTable = React.createClass({
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
           return <div>{flow.request.method} {flow.request.scheme}://{flow.request.host}{flow.request.path}</div>;
       });
       return <pre>{flows}</pre>;
   }
});

var Reports = React.createClass({
   render: function(){
       return (<div>Report Editor</div>);
   }
});

var routes = (
  <ReactRouter.Routes location="hash">
    <ReactRouter.Route name="app" path="/" handler={App}>
        <ReactRouter.Route name="main" handler={TrafficTable}/>
        <ReactRouter.Route name="reports" handler={Reports}/>
        <ReactRouter.Redirect to="main"/>
    </ReactRouter.Route>
  </ReactRouter.Routes>
);