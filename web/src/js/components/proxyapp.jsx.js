/** @jsx React.DOM */

//TODO: Move out of here, just a stub.
var Reports = React.createClass({
    render: function () {
        return <div>ReportEditor</div>;
    }
});


var ProxyAppMain = React.createClass({
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
            <div id="container">
                <Header settings={this.state.settings}/>
                <this.props.activeRouteHandler/>
                {this.state.settings.showEventLog ? <EventLog/> : null}
                <Footer settings={this.state.settings}/>
            </div>
            );
    }
});


var ProxyApp = (
    <ReactRouter.Routes location="hash">
        <ReactRouter.Route name="app" path="/" handler={ProxyAppMain}>
            <ReactRouter.Route name="main" handler={FlowTable}/>
            <ReactRouter.Route name="reports" handler={Reports}/>
            <ReactRouter.Redirect to="main"/>
        </ReactRouter.Route>
    </ReactRouter.Routes>
    );
