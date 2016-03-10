import React from "react"
import ReactDOM from "react-dom"
import shallowEqual from "shallowequal"
import {Router} from "./common.js"
import {Query} from "../actions.js"
import AutoScroll from "./helpers/AutoScroll";
import {calcVScroll} from "./helpers/VirtualScroll"
import {StoreView} from "../store/view.js"
import _ from "lodash"

class EventLogContents extends React.Component {

    static contextTypes = {
        eventStore: React.PropTypes.object.isRequired,
    };

    static defaultProps = {
        rowHeight: 18,
    };

    constructor(props, context) {
        super(props, context);

        this.view = new StoreView(
            this.context.eventStore,
            entry => this.props.filter[entry.level]
        );

        this.heights = {};
        this.state = { entries: this.view.list, vScroll: calcVScroll() };

        this.onChange = this.onChange.bind(this);
        this.onViewportUpdate = this.onViewportUpdate.bind(this);
    }

    componentDidMount() {
        window.addEventListener("resize", this.onViewportUpdate);
        this.view.addListener("add", this.onChange);
        this.view.addListener("recalculate", this.onChange);
        this.onViewportUpdate();
    }

    componentWillUnmount() {
        window.removeEventListener("resize", this.onViewportUpdate);
        this.view.removeListener("add", this.onChange);
        this.view.removeListener("recalculate", this.onChange);
        this.view.close();
    }

    componentDidUpdate() {
        this.onViewportUpdate();
    }

    componentWillReceiveProps(nextProps) {
        if (nextProps.filter !== this.props.filter) {
            this.view.recalculate(
                entry => nextProps.filter[entry.level]
            );
        }
    }

    onViewportUpdate() {
        const viewport = ReactDOM.findDOMNode(this);

        const vScroll = calcVScroll({
            itemCount: this.state.entries.length,
            rowHeight: this.props.rowHeight,
            viewportTop: viewport.scrollTop,
            viewportHeight: viewport.offsetHeight,
            itemHeights: this.state.entries.map(entry => this.heights[entry.id]),
        });

        if (!shallowEqual(this.state.vScroll, vScroll)) {
            this.setState({ vScroll });
        }
    }

    onChange() {
        this.setState({ entries: this.view.list });
    }

    setHeight(id, ref) {
        if (ref && !this.heights[id]) {
            const height = ReactDOM.findDOMNode(ref).offsetHeight;
            if (this.heights[id] !== height) {
                this.heights[id] = height;
                this.onViewportUpdate();
            }
        }
    }

    getIcon(level) {
        return { web: "html5", debug: "bug" }[level] || "info";
    }

    render() {
        const vScroll = this.state.vScroll;
        const entries = this.state.entries.slice(vScroll.start, vScroll.end);

        return (
            <pre onScroll={this.onViewportUpdate}>
                <div style={{ height: vScroll.paddingTop }}></div>
                {entries.map((entry, index) => (
                    <div key={entry.id} ref={this.setHeight.bind(this, entry.id)}>
                        <i className={`fa fa-fw fa-${this.getIcon(entry.level)}`}></i>
                        {entry.message}
                    </div>
                ))}
                <div style={{ height: vScroll.paddingBottom }}></div>
            </pre>
        );
    }
}

ToggleFilter.propTypes = {
    name: React.PropTypes.string.isRequired,
    toggleLevel: React.PropTypes.func.isRequired,
    active: React.PropTypes.bool,
};

function ToggleFilter ({ name, active, toggleLevel }) {
    let className = "label ";
    if (active) {
        className += "label-primary";
    } else {
        className += "label-default";
    }

    function onClick(event) {
        event.preventDefault();
        toggleLevel(name);
    }

    return (
        <a
            href="#"
            className={className}
            onClick={onClick}>
            {name}
        </a>
    );
}

const AutoScrollEventLog = AutoScroll(EventLogContents);

var EventLog = React.createClass({
    mixins: [Router],
    getInitialState() {
        return {
            filter: {
                "debug": false,
                "info": true,
                "web": true
            }
        };
    },
    close() {
        var d = {};
        d[Query.SHOW_EVENTLOG] = undefined;
        this.updateLocation(undefined, d);
    },
    toggleLevel(level) {
        var filter = _.extend({}, this.state.filter);
        filter[level] = !filter[level];
        this.setState({filter: filter});
    },
    render() {
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
                <AutoScrollEventLog filter={this.state.filter}/>
            </div>
        );
    }
});

export default EventLog;
