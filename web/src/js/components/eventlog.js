import React from "react"
import ReactDOM from "react-dom"
import {connect} from 'react-redux'
import shallowEqual from "shallowequal"
import {toggleEventLogFilter, toggleEventLogVisibility} from "../ducks/eventLog"
import AutoScroll from "./helpers/AutoScroll";
import {calcVScroll} from "./helpers/VirtualScroll"
import {ToggleButton} from "./common";

function LogIcon({event}) {
    let icon = {web: "html5", debug: "bug"}[event.level] || "info";
    return <i className={`fa fa-fw fa-${icon}`}></i>
}

function LogEntry({event, registerHeight}) {
    return <div ref={registerHeight}>
        <LogIcon event={event}/>
        {event.message}
    </div>;
}

class EventLogContents extends React.Component {

    static defaultProps = {
        rowHeight: 18,
    };

    constructor(props) {
        super(props);

        this.heights = {};
        this.state = {vScroll: calcVScroll()};

        this.onViewportUpdate = this.onViewportUpdate.bind(this);
    }

    componentDidMount() {
        window.addEventListener("resize", this.onViewportUpdate);
        this.onViewportUpdate();
    }

    componentWillUnmount() {
        window.removeEventListener("resize", this.onViewportUpdate);
    }

    componentDidUpdate() {
        this.onViewportUpdate();
    }

    onViewportUpdate() {
        const viewport = ReactDOM.findDOMNode(this);

        const vScroll = calcVScroll({
            itemCount: this.props.events.length,
            rowHeight: this.props.rowHeight,
            viewportTop: viewport.scrollTop,
            viewportHeight: viewport.offsetHeight,
            itemHeights: this.props.events.map(entry => this.heights[entry.id]),
        });

        if (!shallowEqual(this.state.vScroll, vScroll)) {
            this.setState({vScroll});
        }
    }

    setHeight(id, node) {
        console.log("setHeight", id, node);
        if (node && !this.heights[id]) {
            const height = node.offsetHeight;
            if (this.heights[id] !== height) {
                this.heights[id] = height;
                this.onViewportUpdate();
            }
        }
    }

    render() {
        const vScroll = this.state.vScroll;
        const events = this.props.events
            .slice(vScroll.start, vScroll.end)
            .map(event =>
                <LogEntry
                    event={event}
                    key={event.id}
                    registerHeight={(node) => this.setHeight(event.id, node)}
                />
            );

        return (
            <pre onScroll={this.onViewportUpdate}>
                <div style={{ height: vScroll.paddingTop }}></div>
                {events}
                <div style={{ height: vScroll.paddingBottom }}></div>
            </pre>
        );
    }
}

EventLogContents = AutoScroll(EventLogContents);


const EventLogContentsContainer = connect(
    state => ({
        events: state.eventLog.filteredEvents
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
