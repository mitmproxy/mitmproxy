import React from "react"
import ReactDOM from "react-dom"
import {connect} from 'react-redux'
import shallowEqual from "shallowequal"
import {toggleEventLogFilter, toggleEventLogVisibility} from "../ducks/eventLog"
import AutoScroll from "./helpers/AutoScroll";
import {calcVScroll} from "./helpers/VirtualScroll"
import {StoreView} from "../store/view.js"
import {ToggleButton} from "./common";

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
        this.state = {entries: this.view.list, vScroll: calcVScroll()};

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
            this.setState({vScroll});
        }
    }

    onChange() {
        this.setState({entries: this.view.list});
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
        return {web: "html5", debug: "bug"}[level] || "info";
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

EventLogContents = AutoScroll(EventLogContents);


const EventLogContentsContainer = connect(
    state => ({
        filter: state.eventLog.filter
    })
)(EventLogContents);


export const ToggleEventLog = connect(
    state => ({
        checked: state.eventLog.visible
    }),
    dispatch => ({
        onToggle: () => dispatch(toggleEventLogVisibility())
    })
)(ToggleButton);


const ToggleFilter = connect(
    (state, ownProps) => ({
        checked: state.eventLog.filter[ownProps.text]
    }),
    (dispatch, ownProps) => ({
        onToggle: () => dispatch(toggleEventLogFilter(ownProps.text))
    })
)(ToggleButton);


const EventLog = ({close}) =>
    <div className="eventlog">
        <div>
            Eventlog
            <div className="pull-right">
                <ToggleFilter text="debug"/>
                <ToggleFilter text="info"/>
                <ToggleFilter text="web"/>
                <i onClick={close} className="fa fa-close"></i>
            </div>
        </div>
        <EventLogContentsContainer/>
    </div>;

EventLog.propTypes = {
    close: React.PropTypes.func.isRequired
};

const EventLogContainer = connect(
    undefined,
    dispatch => ({
        close: () => dispatch(toggleEventLogVisibility())
    })
)(EventLog);

export default EventLogContainer;
