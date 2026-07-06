import React, { Component } from "react";
import * as autoscroll from "../helpers/AutoScroll";
import type { VScroll } from "../helpers/VirtualScroll";
import { calcVScroll } from "../helpers/VirtualScroll";
import { LogLevel, type EventLogItem } from "../../ducks/eventLog";
import { shallowEqual } from "react-redux";
import Icon, { type IconName } from "../common/Icon";

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

    constructor(props: EventLogListProps) {
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

    componentDidUpdate(
        prevProps: EventLogListProps,
        _prevState: EventLogListState,
        snapshot: boolean,
    ) {
        if (snapshot) {
            autoscroll.adjustScrollTop(this.viewport);
        }
        // Only recompute the virtual-scroll window when the event list or the
        // row height actually changed. Calling onViewportUpdate on every
        // update (including the setState it produces itself) let
        // setState -> componentDidUpdate -> setState spin without converging
        // once measured row heights differed from the assumed rowHeight,
        // surfacing as "Maximum update depth exceeded" while scrolling the
        // event log. The same fix was applied to FlowTable in #8233. The
        // other call sites still drive updates as needed: componentDidMount,
        // the resize listener, the viewport onScroll, and setHeight when a
        // row is first measured.
        if (
            prevProps.events !== this.props.events ||
            prevProps.rowHeight !== this.props.rowHeight
        ) {
            this.onViewportUpdate();
        }
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

    setHeight(id: string, node: HTMLDivElement | null) {
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
    const iconsByLevel: Record<LogLevel, IconName> = {
        [LogLevel.web]: "browser",
        [LogLevel.debug]: "debug",
        [LogLevel.info]: "info",
        [LogLevel.warn]: "warning",
        [LogLevel.error]: "error",
    };
    const icon = iconsByLevel[event.level] ?? "info";
    return <Icon name={icon} />;
}
