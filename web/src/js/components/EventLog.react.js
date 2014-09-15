/** @jsx React.DOM */

var EventLog = React.createClass({
    getInitialState() {
        return {
            log: []
        };
    },
    componentDidMount() {
        this.log = EventLogStore.getView();
        this.log.addListener("change", this.onEventLogChange);
    },
    componentWillUnmount() {
        this.log.removeListener("change", this.onEventLogChange);
        this.log.close();
    },
    onEventLogChange() {
        this.setState({
            log: this.log.getAll()
        });
    },
    close() {
        SettingsActions.update({
            showEventLog: false
        });
    },
    render() {
        var messages = this.state.log.map(row => (<div key={row.id}>{row.message}</div>));
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