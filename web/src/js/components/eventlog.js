var React = require("react");
var common = require("./common.js");
var Query = require("../actions.js").Query;
var VirtualScrollMixin = require("./virtualscroll.js");
var views = require("../store/view.js");
var _ = require("lodash");

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
    contextTypes: {
        eventStore: React.PropTypes.object.isRequired
    },
    mixins: [common.AutoScrollMixin, VirtualScrollMixin],
    getInitialState: function () {
        var filterFn = function (entry) {
            return this.props.filter[entry.level];
        };
        var view = new views.StoreView(this.context.eventStore, filterFn.bind(this));
        view.addListener("add", this.onEventLogChange);
        view.addListener("recalculate", this.onEventLogChange);

        return {
            view: view
        };
    },
    componentWillUnmount: function () {
        this.state.view.close();
    },
    filter: function (entry) {
        return this.props.filter[entry.level];
    },
    onEventLogChange: function () {
        this.forceUpdate();
    },
    componentWillReceiveProps: function (nextProps) {
        if (nextProps.filter !== this.props.filter) {
            this.props.filter = nextProps.filter; // Dirty: Make sure that view filter sees the update.
            this.state.view.recalculate();
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
        var entries = this.state.view.list;
        var rows = this.renderRows(entries);

        return <pre onScroll={this.onScroll}>
            { this.getPlaceholderTop(entries.length) }
            {rows}
            { this.getPlaceholderBottom(entries.length) }
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
                <EventLogContents filter={this.state.filter}/>
            </div>
        );
    }
});

module.exports = EventLog;