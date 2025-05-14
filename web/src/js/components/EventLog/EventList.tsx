import React, { Component } from "react";
import * as autoscroll from "../helpers/AutoScroll";
import { calcVScroll, VScroll } from "../helpers/VirtualScroll";
import { EventLogItem } from "../../ducks/eventLog";
import { shallowEqual } from "react-redux";

type EventLogListProps = {
    events: EventLogItem[];
    rowHeight: number;
};
type EventLogListState = {
    vScroll: VScroll;
};

export default class EventLogList extends Component<
    EventLogListProps,
    EventLogListState
> {
    static defaultProps = {
        rowHeight: 18,
    };

    heights: { [id: string]: number };

    viewport = React.createRef<HTMLPreElement>();

    constructor(props) {
        super(props);

        this.heights = {};
        this.state = { vScroll: calcVScroll() };

        this.onViewportUpdate = this.onViewportUpdate.bind(this);
    }

    componentDidMount() {
        window.addEventListener("resize", this.onViewportUpdate);
        this.onViewportUpdate();
    }

    componentWillUnmount() {
        window.removeEventListener("resize", this.onViewportUpdate);
    }

    getSnapshotBeforeUpdate() {
        return autoscroll.isAtBottom(this.viewport);
    }

    componentDidUpdate(prevProps, prevState, snapshot) {
        if (snapshot) {
            autoscroll.adjustScrollTop(this.viewport);
        }
        this.onViewportUpdate();
    }

    onViewportUpdate() {
        const viewport = this.viewport.current!;

        const vScroll = calcVScroll({
            itemCount: this.props.events.length,
            rowHeight: this.props.rowHeight,
            viewportTop: viewport.scrollTop,
            viewportHeight: viewport.offsetHeight,
            itemHeights: this.props.events.map(
                (entry) => this.heights[entry.id],
            ),
        });

        if (!shallowEqual(this.state.vScroll, vScroll)) {
            this.setState({ vScroll });
        }
    }

    setHeight(id, node) {
        if (node && !this.heights[id]) {
            const height = node.offsetHeight;
            if (this.heights[id] !== height) {
                this.heights[id] = height;
                this.onViewportUpdate();
            }
        }
    }

    render() {
        const { vScroll } = this.state;
        const { events } = this.props;

        return (
            <pre ref={this.viewport} onScroll={this.onViewportUpdate}>
                <div style={{ height: vScroll.paddingTop }} />
                {events.slice(vScroll.start, vScroll.end).map((event) => (
                    <div
                        key={event.id}
                        ref={(node) => {
                            this.setHeight(event.id, node);
                        }}
                    >
                        <LogIcon event={event} />
                        {event.message}
                    </div>
                ))}
                <div style={{ height: vScroll.paddingBottom }} />
            </pre>
        );
    }
}

function LogIcon({ event }: { event: EventLogItem }) {
    const icon =
        {
            web: "html5",
            debug: "bug",
            warn: "exclamation-triangle",
            error: "ban",
        }[event.level] || "info";
    return <i className={`fa fa-fw fa-${icon}`} />;
}
