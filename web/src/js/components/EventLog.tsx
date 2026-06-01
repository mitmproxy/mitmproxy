import React, { Component } from "react";
import { connect } from "react-redux";
import type { EventLogItem } from "../ducks/eventLog";
import { LogLevel, toggleFilter, toggleVisibility } from "../ducks/eventLog";
import ToggleButton from "./common/ToggleButton";
import EventList from "./EventLog/EventList";
import type { RootState } from "../ducks";
import Icon from "./common/Icon";

type EventLogState = {
    height: number;
};

type EventLogProps = {
    events: EventLogItem[];
    filters: { [level in LogLevel]: boolean };
    toggleFilter: (filter: LogLevel) => void;
    close: () => void;
    defaultHeight: number;
};

export class PureEventLog extends Component<EventLogProps, EventLogState> {
    static defaultProps = {
        defaultHeight: 200,
    };
    private dragStart = 0;

    constructor(props: EventLogProps) {
        super(props);

        this.state = { height: this.props.defaultHeight };

        this.onDragStart = this.onDragStart.bind(this);
        this.onDragMove = this.onDragMove.bind(this);
        this.onDragStop = this.onDragStop.bind(this);
    }

    onDragStart(event: React.MouseEvent) {
        event.preventDefault();
        this.dragStart = this.state.height + event.pageY;
        window.addEventListener("mousemove", this.onDragMove);
        window.addEventListener("mouseup", this.onDragStop);
        window.addEventListener("dragend", this.onDragStop);
    }

    onDragMove(event: MouseEvent) {
        event.preventDefault();
        this.setState({ height: this.dragStart - event.pageY });
    }

    onDragStop(event: MouseEvent | DragEvent) {
        event.preventDefault();
        window.removeEventListener("mousemove", this.onDragMove);
    }

    render() {
        const { height } = this.state;
        const { filters, events, toggleFilter, close } = this.props;

        return (
            <div className="eventlog" style={{ height }}>
                <div onMouseDown={this.onDragStart}>
                    Eventlog
                    <div className="eventlog-actions float-right">
                        {Object.values(LogLevel).map((type) => (
                            <ToggleButton
                                key={type}
                                text={type}
                                checked={filters[type]}
                                onToggle={() => toggleFilter(type)}
                            />
                        ))}
                        <Icon name="close" onClick={close} />
                    </div>
                </div>
                <EventList events={events} />
            </div>
        );
    }
}

export default connect(
    (state: RootState) => ({
        filters: state.eventLog.filters,
        events: state.eventLog.view,
    }),
    {
        close: toggleVisibility,
        toggleFilter: toggleFilter,
    },
)(PureEventLog);
