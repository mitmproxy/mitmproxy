/** @jsx React.DOM */

var EventLog = React.createClass({
    mixins:[AutoScrollMixin],
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
        var messages = this.state.log.map(function(row) {
            var indicator = null;
            if(row.source === "ui"){
                indicator = <i className="fa fa-html5"></i>;
            }
            return (
                <div key={row.id}>
                    { indicator } {row.message}
                </div>);
        });
        return <pre className="eventlog">{messages}</pre>;
    }
});