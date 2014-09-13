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
        //TODO: Is there a sensible place where we can store this?
        var settings = new DummySettings({
            version: "0.12"
        });
        settings.addChangeListener(this._onSettingsChange);

        //This would be async in some way or another.
        this._onSettingsChange(null, settings);
    },
    _onSettingsChange: function(event, settings){
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

var Traffic = React.createClass({
   render: function(){
       var json = JSON.stringify(this.props, null, 4);
       var i = 5;
       while(i--) json += json;
       return (<pre>{json}</pre>);
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
        <ReactRouter.Route name="main" handler={Traffic}/>
        <ReactRouter.Route name="reports" handler={Reports}/>
        <ReactRouter.Redirect to="main"/>
    </ReactRouter.Route>
  </ReactRouter.Routes>
);