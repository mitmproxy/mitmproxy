/** @jsx React.DOM */

var EventLog = React.createClass({
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
        //var messages = this.state.log.map(row => (<div key={row.id}>{row.message}</div>));
        var messages = [];
        return (
            <div className="eventlog">
                <pre>
                    <i className="fa fa-close close-button" onClick={this.close}></i>
                    {messages}
                </pre>
            </div>
            );
    }
});
