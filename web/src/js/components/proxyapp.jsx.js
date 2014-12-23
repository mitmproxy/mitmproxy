//TODO: Move out of here, just a stub.
var Reports = React.createClass({
    render: function () {
        return <div>ReportEditor</div>;
    }
});


var ProxyAppMain = React.createClass({
    mixins: [State],
    getInitialState: function () {
        var eventStore = new EventLogStore();
        var flowStore = new FlowStore();
        var settings = new SettingsStore();

        // Default Settings before fetch
        _.extend(settings.dict,{
        });
        return {
            settings: settings,
            flowStore: flowStore,
            eventStore: eventStore
        };
    },
    componentDidMount: function () {
        this.state.settings.addListener("recalculate", this.onSettingsChange);
        window.app = this;
    },
    componentWillUnmount: function () {
        this.state.settings.removeListener("recalculate", this.onSettingsChange);
    },
    onSettingsChange: function(){
        this.setState({
            settings: this.state.settings
        });
    },
    render: function () {

        var eventlog;
        if (this.getQuery()[Query.SHOW_EVENTLOG]) {
            eventlog = [
                <Splitter key="splitter" axis="y"/>,
                <EventLog key="eventlog" eventStore={this.state.eventStore}/>
            ];
        } else {
            eventlog = null;
        }

        return (
            <div id="container">
                <Header settings={this.state.settings.dict}/>
                <RouteHandler settings={this.state.settings.dict} flowStore={this.state.flowStore}/>
                {eventlog}
                <Footer settings={this.state.settings.dict}/>
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