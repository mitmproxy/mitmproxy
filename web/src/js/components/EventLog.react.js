/** @jsx React.DOM */

var EventLog = React.createClass({
	close(){
		SettingsActions.update({
			showEventLog: false
		});
	},
    render(){
        return (
            <div className="eventlog">
            <pre>
            <i className="fa fa-close close-button" onClick={this.close}></i>
            much log.
            </pre>
            </div>
        );
    }
});