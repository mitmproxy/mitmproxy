var LogMessage = React.createClass({
    render: function () {
        var entry = this.props.entry;
        var indicator;
        switch (entry.level) {
            case "web":
                indicator = <i className="fa fa-fw fa-html5"></i>;
                break;
            case "debug":
                indicator = <i className="fa fa-fw fa-bug"></i>;
                break;
            default:
                indicator = <i className="fa fa-fw fa-info"></i>;
        }
        return (
            <div>
                { indicator } {entry.message}
            </div>
        );
    },
    shouldComponentUpdate: function () {
        return false; // log entries are immutable.
    }
});

var EventLogContents = React.createClass({
    mixins: [AutoScrollMixin, VirtualScrollMixin],
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
        var log = this.log.getAll().filter(function (entry) {
            return this.props.filter[entry.level];
        }.bind(this));
        this.setState({
            log: log
        });
    },
    componentWillReceiveProps: function () {
        if (this.log) {
            this.onEventLogChange();
        }

    },
    getDefaultProps: function () {
        return {
            rowHeight: 45,
            rowHeightMin: 15,
            placeholderTagName: "div"
        };
    },
    renderRow: function(elem){
        return <LogMessage key={elem.id} entry={elem}/>;
    },
    render: function () {
        var rows = this.renderRows(this.state.log);

        return <pre onScroll={this.onScroll}>
            { this.getPlaceholderTop() }
            {rows}
            { this.getPlaceholderBottom(this.state.log.length) }
        </pre>;
    }
});

var ToggleFilter = React.createClass({
    toggle: function (e) {
        e.preventDefault();
        return this.props.toggleLevel(this.props.name);
    },
    render: function () {
        var className = "label ";
        if (this.props.active) {
            className += "label-primary";
        } else {
            className += "label-default";
        }
        return (
            <a
                href="#"
                className={className}
                onClick={this.toggle}>
                {this.props.name}
            </a>
        );
    }
});

var EventLog = React.createClass({
    getInitialState: function () {
        return {
            filter: {
                "debug": false,
                "info": true,
                "web": true
            }
        };
    },
    close: function () {
        SettingsActions.update({
            showEventLog: false
        });
    },
    toggleLevel: function (level) {
        var filter = this.state.filter;
        filter[level] = !filter[level];
        this.setState({filter: filter});
    },
    render: function () {
        return (
            <div className="eventlog">
                <div>
                    Eventlog
                    <div className="pull-right">
                        <ToggleFilter name="debug" active={this.state.filter.debug} toggleLevel={this.toggleLevel}/>
                        <ToggleFilter name="info" active={this.state.filter.info} toggleLevel={this.toggleLevel}/>
                        <ToggleFilter name="web" active={this.state.filter.web} toggleLevel={this.toggleLevel}/>
                        <i onClick={this.close} className="fa fa-close"></i>
                    </div>

                </div>
                <EventLogContents filter={this.state.filter}/>
            </div>
        );
    }
});