/** @jsx React.DOM */

//TODO: Move out of here, just a stub.
var Reports = React.createClass({
   render(){
       return (<div>Report Editor</div>);
   }
});



var ProxyAppMain = React.createClass({
    getInitialState(){
      return { settings: SettingsStore.getAll() };
    },
    componentDidMount(){
      SettingsStore.addListener("change", this.onSettingsChange);
    },
    componentWillUnmount(){
      SettingsStore.removeListener("change", this.onSettingsChange);
    },
    onSettingsChange(){
      console.log("onSettingsChange");
      this.setState({settings: SettingsStore.getAll()});
    },
    render() {
      return (
        <div id="container">
          <Header settings={this.state.settings}/>
          <div id="main"><this.props.activeRouteHandler/></div>
          {this.state.settings.showEventLog ? <EventLog/> : null}
          <Footer/>
        </div>
      );
    }
});


var ProxyApp = (
  <ReactRouter.Routes location="hash">
    <ReactRouter.Route name="app" path="/" handler={ProxyAppMain}>
        <ReactRouter.Route name="main" handler={TrafficTable}/>
        <ReactRouter.Route name="reports" handler={Reports}/>
        <ReactRouter.Redirect to="main"/>
    </ReactRouter.Route>
  </ReactRouter.Routes>
);
