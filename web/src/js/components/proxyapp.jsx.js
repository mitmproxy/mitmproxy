//TODO: Move out of here, just a stub.
var Reports = React.createClass({
    render: function () {
        return <div>ReportEditor</div>;
    }
});


var ProxyAppMain = React.createClass({
    getInitialState: function () {
        return {
            settings: SettingsStore.getAll(),
            flowStore: new FlowStore()
        };
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
            <div id="container">
                <Header settings={this.state.settings}/>
                <RouteHandler settings={this.state.settings} flowStore={this.state.flowStore}/>
                {this.state.settings.showEventLog ? <Splitter axis="y"/> : null}
                {this.state.settings.showEventLog ? <EventLog/> : null}
                <Footer settings={this.state.settings}/>
            </div>
        );
    }
});


var Route = ReactRouter.Route;
var RouteHandler = ReactRouter.RouteHandler;
var Redirect = ReactRouter.Redirect;
var DefaultRoute = ReactRouter.DefaultRoute;
var NotFoundRoute = ReactRouter.NotFoundRoute;


var routes = (
    <Route path="/" handler={ProxyAppMain}>
        <Route name="flows" path="flows" handler={MainView}/>
        <Route name="flow" path="flows/:flowId/:detailTab" handler={MainView}/>
        <Route name="reports" handler={Reports}/>
        <Redirect path="/" to="flows" />
    </Route>
);