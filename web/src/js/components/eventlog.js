import React from "react"
import ReactDOM from "react-dom"
import { connect } from 'react-redux'
import shallowEqual from "shallowequal"
import {Query} from "../actions.js"
import {toggleEventLogFilter} from "../reduxActions"
import AutoScroll from "./helpers/AutoScroll";
import {calcVScroll} from "./helpers/VirtualScroll"
import {StoreView} from "../store/view.js"

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
        toggleLevel();
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

const mapStateToProps = (state, ownProps) => {
  return {
    active: state.eventLog.visibilityFilter[ownProps.name]
  }
};

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    toggleLevel: () => {
      dispatch(toggleEventLogFilter(ownProps.name))
    }
  }
};

const ToggleEventLogFilter = connect(
  mapStateToProps,
  mapDispatchToProps
)(ToggleFilter);


const AutoScrollEventLog = AutoScroll(EventLogContents);


const VisibleAutoScrollEventLog = connect(
    function mapStateToProps(state, ownProps) {
        return {filter: state.eventLog.visibilityFilter}
    })(AutoScrollEventLog);


var EventLog = React.createClass({
    close() {
        var d = {};
        d[Query.SHOW_EVENTLOG] = undefined;
        this.props.updateLocation(undefined, d);
    },
    render() {
        return (
            <div className="eventlog">
                <div>
                    Eventlog
                    <div className="pull-right">
                        <ToggleEventLogFilter name="debug"/>
                        <ToggleEventLogFilter name="info"/>
                        <ToggleEventLogFilter name="web"/>
                        <i onClick={this.close} className="fa fa-close"></i>
                    </div>

                </div>
                <VisibleAutoScrollEventLog/>
            </div>
        );
    }
});

export default EventLog;
