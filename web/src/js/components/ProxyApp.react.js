/** @jsx React.DOM */

//TODO: Move out of here, just a stub.
var Reports = React.createClass({
   render(){
       return (<div>Report Editor</div>);
   }
});



var ProxyAppMain = React.createClass({
    mixins: [SettingsMixin],
    render() {
      return (
        <div id="container">
          <Header/>
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
