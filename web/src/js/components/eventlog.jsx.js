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
    componentWillMount: function () {
        this.openView(this.props.eventStore);
    },
    componentWillUnmount: function () {
        this.closeView();
    },
    openView: function (store) {
        var view = new StoreView(store, function (entry) {
            return this.props.filter[entry.level];
        }.bind(this));
        this.setState({
            view: view
        });

        view.addListener("add recalculate", this.onEventLogChange);
    },
    closeView: function () {
        this.state.view.close();
    },
    onEventLogChange: function () {
        this.setState({
            log: this.state.view.list
        });
    },
    componentWillReceiveProps: function (nextProps) {
        if (nextProps.filter !== this.props.filter) {
            this.props.filter = nextProps.filter; // Dirty: Make sure that view filter sees the update.
            this.state.view.recalculate();
        }
        if (nextProps.eventStore !== this.props.eventStore) {
            this.closeView();
            this.openView(nextProps.eventStore);
        }
    },
    getDefaultProps: function () {
        return {
            rowHeight: 45,
            rowHeightMin: 15,
            placeholderTagName: "div"
        };
    },
    renderRow: function (elem) {
        return <LogMessage key={elem.id} entry={elem}/>;
    },
    render: function () {
        var rows = this.renderRows(this.state.log);

        return <pre onScroll={this.onScroll}>
            { this.getPlaceholderTop(this.state.log.length) }
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
        var d = {};
        d[Query.SHOW_EVENTLOG] = undefined;
        this.setQuery(d);
    },
    toggleLevel: function (level) {
        var filter = _.extend({}, this.state.filter);
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
                <EventLogContents filter={this.state.filter} eventStore={this.props.eventStore}/>
            </div>
        );
    }
});